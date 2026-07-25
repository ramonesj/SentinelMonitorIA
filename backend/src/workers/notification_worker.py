"""Redis Streams worker for idempotent alert notifications."""

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
from src.models.intelligence import Alert, NotificationDelivery
from src.services.notifications import notification_dispatcher
from src.services.queue_contract import QueueMessage, QueueType
from src.services.redis_streams import RedisStreamQueueProducer


class NotificationWorker:
    """Deliver alerts and persist each channel's attempt state."""

    def __init__(
        self,
        producer: Optional[RedisStreamQueueProducer] = None,
        group_name: Optional[str] = None,
        consumer_name: Optional[str] = None,
        batch_size: int = 10,
        block_ms: int = 1000,
    ):
        self.producer = producer or RedisStreamQueueProducer()
        self.group_name = group_name or settings.notification_consumer_group
        self.consumer_name = consumer_name or f"notification-worker-{os.getenv('HOSTNAME', os.getpid())}"
        self.batch_size = batch_size
        self.block_ms = block_ms
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        await self.producer.start()
        await self.producer.ensure_group(QueueType.NOTIFICATIONS, self.group_name)
        logger.info("Notification worker started", group=self.group_name, channels=settings.notification_channel_list)

    async def stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        await self.start()
        try:
            while not self._stop_event.is_set():
                messages = await self.producer.claim_pending(
                    QueueType.NOTIFICATIONS, self.group_name, self.consumer_name, count=self.batch_size
                )
                if not messages:
                    messages = await self.producer.read_group(
                        QueueType.NOTIFICATIONS,
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
            await self.producer.acknowledge(QueueType.NOTIFICATIONS, self.group_name, stream_id)
            return
        message = QueueMessage.from_dict(json.loads(raw_payload))
        try:
            await self._process_message(message)
            await self.producer.acknowledge(QueueType.NOTIFICATIONS, self.group_name, stream_id)
        except Exception as exc:
            logger.error("Notification worker failed", message_id=message.id, error=str(exc))
            await self._retry_or_dead_letter(message, str(exc), stream_id)

    async def _process_message(self, message: QueueMessage) -> None:
        alert_id = UUID(message.data["alert_id"])
        channel = str(message.data["channel"])
        async with DatabaseContext() as db:
            alert_result = await db.execute(select(Alert).where(Alert.id == alert_id))
            alert = alert_result.scalar_one_or_none()
            delivery_result = await db.execute(
                select(NotificationDelivery).where(
                    (NotificationDelivery.alert_id == alert_id)
                    & (NotificationDelivery.channel == channel)
                )
            )
            delivery = delivery_result.scalar_one_or_none()
            if not alert or not delivery or delivery.status == "sent":
                return

            delivery.attempt_count += 1
            alert_payload = {
                "id": str(alert.id),
                "organization_id": str(alert.organization_id),
                "title": alert.title,
                "description": alert.description,
                "severity": alert.severity,
                "status": alert.status,
                "source": alert.source,
                "payload": alert.payload,
            }
            result = await notification_dispatcher.send(channel, alert_payload)
            if result.delivered:
                delivery.status = "sent"
                delivery.external_id = result.external_id
                delivery.sent_at = datetime.utcnow()
                delivery.last_error = None
            else:
                delivery.status = "failed"
                delivery.last_error = result.error
                raise RuntimeError(result.error or "Notification delivery failed")
            await db.commit()

    async def _retry_or_dead_letter(self, message: QueueMessage, error: str, stream_id: str) -> None:
        next_retry = message.retry_count + 1
        if next_retry <= message.max_retries:
            await self.producer.send(
                QueueType.NOTIFICATIONS,
                message.data,
                priority=message.priority,
                retry_count=next_retry,
                max_retries=message.max_retries,
            )
        else:
            await self.producer.dead_letter(message, error)
        await self.producer.acknowledge(QueueType.NOTIFICATIONS, self.group_name, stream_id)


def _install_signal_handlers(worker: NotificationWorker) -> None:
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, worker._stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass


async def main() -> None:
    configure_logging()
    worker = NotificationWorker()
    _install_signal_handlers(worker)
    try:
        await db_manager.initialize()
        await worker.run()
    finally:
        await redis_manager.close()
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
