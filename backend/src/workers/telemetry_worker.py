"""Persistent Redis Streams worker for telemetry batches."""

import asyncio
import json
import os
import signal
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select

from src.config.logging import configure_logging, logger
from src.config.settings import settings
from src.database.database import DatabaseContext, db_manager
from src.database.redis import redis_manager
from src.models.organization import Agent, Organization  # noqa: F401 - register relationship targets
from src.models.telemetry import Event, LogEntry, Metric, TelemetryBatch
from src.models.user import JwtSession, Token, User, UserOrganization  # noqa: F401
from src.services.queue_contract import QueueMessage, QueueType
from src.services.redis_streams import RedisStreamQueueProducer


class TelemetryWorker:
    """Consume telemetry messages and persist their items transactionally."""

    def __init__(
        self,
        producer: Optional[RedisStreamQueueProducer] = None,
        group_name: Optional[str] = None,
        consumer_name: Optional[str] = None,
        batch_size: int = 10,
        block_ms: int = 1000,
    ):
        self.producer = producer or RedisStreamQueueProducer()
        self.group_name = group_name or settings.redis_stream_consumer_group
        self.consumer_name = consumer_name or f"worker-{os.getenv('HOSTNAME', os.getpid())}"
        self.batch_size = batch_size
        self.block_ms = block_ms
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Initialize Redis and the telemetry consumer group."""
        await self.producer.start()
        await self.producer.ensure_group(QueueType.TELEMETRY, self.group_name)
        reconciled = await self.reconcile_stale_batches()
        logger.info(
            "Telemetry worker started",
            group=self.group_name,
            consumer=self.consumer_name,
            stale_batches_reconciled=reconciled,
        )

    async def reconcile_stale_batches(self) -> int:
        """Mark abandoned processing batches as failed without deleting data."""
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.telemetry_stale_batch_seconds
        )
        reconciled = 0
        async with DatabaseContext() as db:
            result = await db.execute(
                select(TelemetryBatch).where(
                    TelemetryBatch.status.in_(["processing", "retrying"]),
                    TelemetryBatch.updated_at < cutoff,
                )
            )
            batches = result.scalars().all()
            for batch in batches:
                batch.status = "failed"
                batch.error_message = (
                    "Batch marked failed by worker reconciliation because it "
                    "remained processing beyond the configured stale threshold."
                )
                reconciled += 1
            if reconciled:
                await db.commit()
        if reconciled:
            logger.warning(
                "Stale telemetry batches reconciled",
                count=reconciled,
                stale_after_seconds=settings.telemetry_stale_batch_seconds,
            )
        return reconciled

    async def stop(self) -> None:
        """Request a graceful worker shutdown."""
        self._stop_event.set()

    async def run(self) -> None:
        """Run until stopped, recovering stale pending messages first."""
        await self.start()
        try:
            while not self._stop_event.is_set():
                messages = await self.producer.claim_pending(
                    QueueType.TELEMETRY,
                    self.group_name,
                    self.consumer_name,
                    count=self.batch_size,
                )
                if not messages:
                    messages = await self.producer.read_group(
                        QueueType.TELEMETRY,
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
        """Process one stream entry and ACK only after final handling."""
        raw_payload = fields.get("payload")
        if not raw_payload:
            await self.producer.acknowledge(QueueType.TELEMETRY, self.group_name, stream_id)
            return

        message = QueueMessage.from_dict(json.loads(raw_payload))
        started = time.perf_counter()
        try:
            await self._persist_message(message)
            await self.producer.record_processed(time.perf_counter() - started)
            await self.producer.acknowledge(QueueType.TELEMETRY, self.group_name, stream_id)
        except Exception as exc:
            await self.producer.record_failed()
            logger.error(
                "Telemetry worker failed to process message",
                message_id=message.id,
                batch_id=message.data.get("batch_id"),
                retry_count=message.retry_count,
                error=str(exc),
            )
            await self._retry_or_dead_letter(message, str(exc), stream_id)

    async def _persist_message(self, message: QueueMessage) -> None:
        """Persist metrics/logs/events and mark the batch as processed."""
        data = message.data
        batch_uuid = UUID(data["batch_id"])
        async with DatabaseContext() as db:
            result = await db.execute(
                select(TelemetryBatch)
                .where(TelemetryBatch.id == batch_uuid)
                .with_for_update()
            )
            batch = result.scalar_one_or_none()
            if not batch:
                raise ValueError(f"Telemetry batch {batch_uuid} was not found")
            if batch.status == "processed":
                if batch.analysis_enqueued_at is None:
                    await self._enqueue_analysis(message)
                return

            organization_id = UUID(data["organization_id"])
            agent_id = UUID(data["agent_id"])
            batch_data = data.get("batch_data") or {}

            for item in batch_data.get("metrics", []):
                db.add(
                    Metric(
                        batch_id=batch.id,
                        organization_id=organization_id,
                        agent_id=agent_id,
                        metric_name=item["name"],
                        metric_type=item.get("type", "gauge"),
                        value=float(item["value"]),
                        value_raw=str(item["value"]),
                        timestamp=self._timestamp(item.get("timestamp")),
                        labels=item.get("labels", {}),
                        unit=item.get("unit"),
                        description=item.get("description"),
                    )
                )

            for item in batch_data.get("logs", []):
                db.add(
                    LogEntry(
                        batch_id=batch.id,
                        organization_id=organization_id,
                        agent_id=agent_id,
                        message=item["message"],
                        level=item.get("level", "info"),
                        timestamp=self._timestamp(item.get("timestamp")),
                        service=item.get("service"),
                        component=item.get("component"),
                        metadata_json=item.get("metadata", {}),
                        parsed_fields=item.get("parsed_fields", {}),
                    )
                )

            for item in batch_data.get("events", []):
                db.add(
                    Event(
                        batch_id=batch.id,
                        organization_id=organization_id,
                        agent_id=agent_id,
                        event_type=item["type"],
                        event_source=item["source"],
                        summary=item["summary"],
                        timestamp=self._timestamp(item.get("timestamp")),
                        severity=item.get("severity", "info"),
                        details=item.get("details", {}),
                        correlation_id=item.get("correlation_id"),
                    )
                )

            batch.status = "processed"
            batch.processed_at = datetime.utcnow()
            batch.retry_count = message.retry_count
            received_at = data.get("received_at")
            if received_at:
                received = self._timestamp(received_at)
                batch.processing_latency_ms = max(
                    0.0, (datetime.utcnow() - received.replace(tzinfo=None)).total_seconds() * 1000
                )
            await db.commit()
            await self._enqueue_analysis(message)

    async def _enqueue_analysis(self, message: QueueMessage) -> None:
        """Publish analysis work after telemetry is durable and mark it idempotently."""
        data = message.data
        await self.producer.send(
            QueueType.AI_ANALYSIS,
            {
                "batch_id": data["batch_id"],
                "organization_id": data["organization_id"],
                "agent_id": data["agent_id"],
                "batch_data": data.get("batch_data") or {},
                "received_at": data.get("received_at"),
            },
        )
        async with DatabaseContext() as db:
            result = await db.execute(
                select(TelemetryBatch).where(TelemetryBatch.id == UUID(data["batch_id"]))
            )
            batch = result.scalar_one_or_none()
            if batch and batch.analysis_enqueued_at is None:
                batch.analysis_enqueued_at = datetime.utcnow()
                await db.commit()

    async def _retry_or_dead_letter(
        self,
        message: QueueMessage,
        error: str,
        stream_id: str,
    ) -> None:
        """Retry with a new stream entry or persist the exhausted message in DLQ."""
        next_retry = message.retry_count + 1
        terminal = next_retry > message.max_retries
        await self._mark_batch_failure(message, error, next_retry, terminal)
        if not terminal:
            retry_message = QueueMessage(
                id=message.id,
                queue_type=QueueType.TELEMETRY,
                data=message.data,
                priority=message.priority,
                retry_count=next_retry,
                max_retries=message.max_retries,
            )
            await self.producer.send(
                QueueType.TELEMETRY,
                retry_message.data,
                priority=retry_message.priority,
                retry_count=retry_message.retry_count,
                max_retries=retry_message.max_retries,
            )
        else:
            await self.producer.dead_letter(message, error)
        await self.producer.acknowledge(QueueType.TELEMETRY, self.group_name, stream_id)

    async def _mark_batch_failure(
        self,
        message: QueueMessage,
        error: str,
        retry_count: int,
        terminal: bool,
    ) -> None:
        """Keep database status aligned with retry and dead-letter state."""
        batch_id = message.data.get("batch_id")
        if not batch_id:
            return
        async with DatabaseContext() as db:
            result = await db.execute(
                select(TelemetryBatch).where(TelemetryBatch.id == UUID(batch_id))
            )
            batch = result.scalar_one_or_none()
            if batch:
                batch.status = "failed" if terminal else "retrying"
                batch.error_message = error[:2000]
                batch.retry_count = retry_count
                await db.commit()

    @staticmethod
    def _timestamp(value: Any) -> datetime:
        if not value:
            return datetime.utcnow()
        if isinstance(value, datetime):
            return value
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed


def _install_signal_handlers(worker: TelemetryWorker) -> None:
    """Allow Ctrl+C and container termination to stop the event loop cleanly."""
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, worker._stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass


async def main() -> None:
    configure_logging()
    worker = TelemetryWorker()
    _install_signal_handlers(worker)
    try:
        await db_manager.initialize()
        await worker.run()
    finally:
        await redis_manager.close()
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
