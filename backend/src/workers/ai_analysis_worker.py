"""Redis Streams worker for deterministic analysis and optional LLM explanations."""

import asyncio
import json
import os
import signal
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import select

from src.config.logging import configure_logging, logger
from src.config.settings import settings
from src.database.database import DatabaseContext, db_manager
from src.database.redis import redis_manager
from src.models.intelligence import AIAnalysis, Alert, NotificationDelivery
from src.services.ai.analyzer import IntelligenceAnalyzer
from src.services.queue_contract import QueueMessage, QueueType
from src.services.redis_streams import RedisStreamQueueProducer


class AIAnalysisWorker:
    """Consume persisted telemetry references and create analyses/alerts."""

    def __init__(
        self,
        producer: Optional[RedisStreamQueueProducer] = None,
        group_name: Optional[str] = None,
        consumer_name: Optional[str] = None,
        batch_size: int = 10,
        block_ms: int = 1000,
    ):
        self.producer = producer or RedisStreamQueueProducer()
        self.group_name = group_name or settings.ai_analysis_consumer_group
        self.consumer_name = consumer_name or f"ai-worker-{os.getenv('HOSTNAME', os.getpid())}"
        self.batch_size = batch_size
        self.block_ms = block_ms
        self.analyzer = IntelligenceAnalyzer()
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        await self.producer.start()
        await self.producer.ensure_group(QueueType.AI_ANALYSIS, self.group_name)
        logger.info("AI analysis worker started", group=self.group_name, provider=self.analyzer.provider.name)

    async def stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        await self.start()
        try:
            while not self._stop_event.is_set():
                messages = await self.producer.claim_pending(
                    QueueType.AI_ANALYSIS, self.group_name, self.consumer_name, count=self.batch_size
                )
                if not messages:
                    messages = await self.producer.read_group(
                        QueueType.AI_ANALYSIS,
                        self.group_name,
                        self.consumer_name,
                        count=self.batch_size,
                        block_ms=self.block_ms,
                    )
                for stream_id, fields in messages:
                    await self.process_entry(str(stream_id), fields)
        finally:
            await self.producer.stop()

    async def process_entry(self, stream_id: str, fields: Dict[str, str]) -> None:
        raw_payload = fields.get("payload")
        if not raw_payload:
            await self.producer.acknowledge(QueueType.AI_ANALYSIS, self.group_name, stream_id)
            return
        message = QueueMessage.from_dict(json.loads(raw_payload))
        try:
            await self._process_message(message)
            await self.producer.acknowledge(QueueType.AI_ANALYSIS, self.group_name, stream_id)
        except Exception as exc:
            logger.error("AI analysis worker failed", message_id=message.id, error=str(exc))
            await self._retry_or_dead_letter(message, str(exc), stream_id)

    async def _process_message(self, message: QueueMessage) -> None:
        data = message.data
        organization_id = UUID(data["organization_id"])
        batch_id = UUID(data["batch_id"])
        analysis_key = f"{organization_id}:{batch_id}"
        result = await self.analyzer.analyze(data)
        alert_to_queue: list[tuple[str, UUID]] = []

        async with DatabaseContext() as db:
            existing_result = await db.execute(select(AIAnalysis).where(AIAnalysis.analysis_key == analysis_key))
            analysis = existing_result.scalar_one_or_none()
            alert = None
            if not analysis:
                analysis = AIAnalysis(
                    organization_id=organization_id,
                    telemetry_batch_id=batch_id,
                    analysis_key=analysis_key,
                    provider=result["provider"],
                    model_name=result.get("model_name"),
                    status=result["status"],
                    severity=result["severity"],
                    findings=result["findings"],
                    explanation=result.get("explanation"),
                    recommendations=result["recommendations"],
                    context_metadata=result.get("context_metadata", {}),
                    error_message=result.get("provider_error"),
                    completed_at=datetime.utcnow(),
                )
                db.add(analysis)
                await db.flush()

                if result["findings"]:
                    first = result["findings"][0]
                    alert = Alert(
                        organization_id=organization_id,
                        analysis_id=analysis.id,
                        dedupe_key=analysis_key,
                        rule_id=first["rule_id"],
                        title=first["title"],
                        description=result.get("explanation") or first["description"],
                        severity=result["severity"],
                        payload={
                            "batch_id": str(batch_id),
                            "agent_id": data.get("agent_id"),
                            "findings": result["findings"],
                            "recommendations": result["recommendations"],
                            "actions_enabled": False,
                        },
                    )
                    db.add(alert)
                    await db.flush()
                    for channel in settings.notification_channel_list:
                        db.add(NotificationDelivery(alert_id=alert.id, channel=channel, destination=channel, status="pending"))
            else:
                alert_result = await db.execute(select(Alert).where(Alert.analysis_id == analysis.id))
                alert = alert_result.scalar_one_or_none()

            if alert:
                pending_result = await db.execute(
                    select(NotificationDelivery).where(
                        (NotificationDelivery.alert_id == alert.id)
                        & (NotificationDelivery.status == "pending")
                    )
                )
                for delivery in pending_result.scalars().all():
                    alert_to_queue.append((delivery.channel, alert.id))
            await db.commit()

        for channel, alert_id in alert_to_queue:
            await self.producer.send(
                QueueType.NOTIFICATIONS,
                {
                    "alert_id": str(alert_id),
                    "channel": channel,
                    "organization_id": str(organization_id),
                },
            )

    async def _retry_or_dead_letter(self, message: QueueMessage, error: str, stream_id: str) -> None:
        next_retry = message.retry_count + 1
        if next_retry <= message.max_retries:
            await self.producer.send(
                QueueType.AI_ANALYSIS,
                message.data,
                priority=message.priority,
                retry_count=next_retry,
                max_retries=message.max_retries,
            )
        else:
            await self.producer.dead_letter(message, error)
        await self.producer.acknowledge(QueueType.AI_ANALYSIS, self.group_name, stream_id)


def _install_signal_handlers(worker: AIAnalysisWorker) -> None:
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, worker._stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass


async def main() -> None:
    configure_logging()
    worker = AIAnalysisWorker()
    _install_signal_handlers(worker)
    try:
        await db_manager.initialize()
        await worker.run()
    finally:
        await redis_manager.close()
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
