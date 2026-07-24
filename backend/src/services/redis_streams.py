"""Redis Streams producer for the local persistent queue provider."""

import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from src.config.logging import logger
from src.config.settings import settings
from src.database.redis import redis_manager
from src.services.queue_contract import QueueMessage, QueueType


class RedisStreamQueueProducer:
    """Durable Redis Streams producer compatible with QueueMessage."""

    def __init__(
        self,
        stream_prefix: Optional[str] = None,
        max_stream_length: Optional[int] = None,
    ):
        self.stream_prefix = stream_prefix or settings.redis_stream_prefix
        self.max_stream_length = max_stream_length or settings.redis_stream_max_length
        self._running = False
        self.queue_sizes = {
            queue_type: self.max_stream_length for queue_type in QueueType
        }
        self._stats_key = f"{self.stream_prefix}:stats"

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        """Convert Redis hash values without failing on missing/null fields."""
        try:
            return default if value is None else int(value)
        except (TypeError, ValueError):
            return default

    def stream_name(self, queue_type: QueueType) -> str:
        """Return the Redis stream key for a queue type."""
        return f"{self.stream_prefix}:{queue_type.value}"

    async def start(self) -> None:
        """Connect to Redis without starting a consumer in the API process."""
        if self._running:
            return
        await redis_manager.initialize()
        self._running = True
        logger.info("Redis Streams producer started", stream_prefix=self.stream_prefix)

    async def stop(self) -> None:
        """Stop producing; the shared Redis connection remains owned by the app."""
        self._running = False
        logger.info("Redis Streams producer stopped", stream_prefix=self.stream_prefix)

    async def send(
        self,
        queue_type: QueueType,
        data: Dict[str, Any],
        priority: int = 0,
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> str:
        """Append a serialized QueueMessage to a Redis stream."""
        if not self._running:
            await self.start()

        message = QueueMessage(
            id=str(uuid4()),
            queue_type=queue_type,
            data=data,
            priority=priority,
            retry_count=retry_count,
            max_retries=max_retries,
        )
        payload = json.dumps(message.to_dict(), separators=(",", ":"), default=str)
        stream_id = await redis_manager.client.xadd(
            self.stream_name(queue_type),
            {"payload": payload, "message_id": message.id},
            maxlen=self.max_stream_length,
            approximate=True,
        )
        await redis_manager.client.hincrby(self._stats_key, "messages_sent", 1)
        await redis_manager.client.hset(
            self._stats_key,
            "last_sent",
            datetime.utcnow().isoformat(),
        )
        logger.debug(
            "Message sent to Redis Stream",
            queue_type=queue_type.value,
            message_id=message.id,
            stream_id=stream_id,
        )
        return message.id

    async def _get_stream_depth(self, queue_type: QueueType) -> int:
        """Return unprocessed work, not the retained stream history."""
        stream = self.stream_name(queue_type)
        if queue_type != QueueType.TELEMETRY:
            return await redis_manager.client.xlen(stream)

        try:
            groups = await redis_manager.client.xinfo_groups(stream)
            group = next(
                (
                    item
                    for item in groups
                    if item.get("name") == settings.redis_stream_consumer_group
                ),
                None,
            )
            if group is not None:
                pending = self._safe_int(group.get("pending"))
                lag = group.get("lag")
                return pending + self._safe_int(lag)
        except Exception as exc:
            logger.debug("Unable to read Redis consumer lag", error=str(exc))

        # Before the worker creates its group, XLEN is the only available
        # approximation for messages that have not been consumed yet.
        return await redis_manager.client.xlen(stream)

    async def get_stats(self) -> Dict[str, Any]:
        """Return queue depths and durable producer statistics."""
        if not self._running:
            await self.start()
        depths = {}
        for queue_type in QueueType:
            depths[queue_type.value] = await self._get_stream_depth(queue_type)
        raw_stats = await redis_manager.client.hgetall(self._stats_key)
        stats: Dict[str, Any] = {
            "messages_sent": self._safe_int(raw_stats.get("messages_sent")),
            "messages_processed": self._safe_int(raw_stats.get("messages_processed")),
            "messages_failed": self._safe_int(raw_stats.get("messages_failed")),
            "current_queue_depths": depths,
            "queue_depths": depths,
            "processing_times": [],
            "avg_processing_time_seconds": 0,
            "last_processed": raw_stats.get("last_processed"),
        }
        return stats

    async def record_processed(self, processing_time_seconds: float) -> None:
        """Record worker completion metrics in Redis."""
        await redis_manager.client.hincrby(self._stats_key, "messages_processed", 1)
        await redis_manager.client.hset(
            self._stats_key,
            mapping={
                "last_processed": datetime.utcnow().isoformat(),
                "last_processing_time_seconds": str(processing_time_seconds),
            },
        )

    async def record_failed(self) -> None:
        """Record a failed worker attempt in Redis."""
        await redis_manager.client.hincrby(self._stats_key, "messages_failed", 1)

    async def clear_queue(self, queue_type: QueueType) -> None:
        """Delete one stream, used only by development reset endpoints."""
        if not self._running:
            await self.start()
        await redis_manager.client.delete(self.stream_name(queue_type))
        logger.info("Redis Stream cleared", queue_type=queue_type.value)

    async def ensure_group(self, queue_type: QueueType, group_name: str) -> None:
        """Create a consumer group once; MKSTREAM allows an empty queue."""
        if not self._running:
            await self.start()
        try:
            await redis_manager.client.xgroup_create(
                self.stream_name(queue_type),
                group_name,
                id="0-0",
                mkstream=True,
            )
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def read_group(
        self,
        queue_type: QueueType,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 1000,
    ) -> list[tuple[str, Dict[str, str]]]:
        """Read new messages from a consumer group."""
        result = await redis_manager.client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams={self.stream_name(queue_type): ">"},
            count=count,
            block=block_ms,
        )
        messages: list[tuple[str, Dict[str, str]]] = []
        for _, entries in result or []:
            messages.extend(entries)
        return messages

    async def claim_pending(
        self,
        queue_type: QueueType,
        group_name: str,
        consumer_name: str,
        min_idle_ms: int = 60000,
        count: int = 10,
    ) -> list[tuple[str, Dict[str, str]]]:
        """Recover messages left pending by a crashed worker."""
        try:
            result = await redis_manager.client.xautoclaim(
                self.stream_name(queue_type),
                group_name,
                consumer_name,
                min_idle_time=min_idle_ms,
                start_id="0-0",
                count=count,
            )
        except Exception as exc:
            logger.warning("Unable to claim pending Redis messages", error=str(exc))
            return []
        if not result or len(result) < 2:
            return []
        return result[1] or []

    async def acknowledge(
        self,
        queue_type: QueueType,
        group_name: str,
        stream_id: str,
    ) -> None:
        """ACK a stream entry after successful processing or dead-lettering."""
        await redis_manager.client.xack(
            self.stream_name(queue_type),
            group_name,
            stream_id,
        )

    async def list_dead_letters(self, limit: int = 50) -> list[dict[str, Any]]:
        """List dead-letter entries without removing their original records."""
        if not self._running:
            await self.start()
        safe_limit = max(1, min(limit, 100))
        entries = await redis_manager.client.xrevrange(
            self.stream_name(QueueType.DEAD_LETTER), count=safe_limit
        )
        replayed = await redis_manager.client.smembers(
            settings.redis_dead_letter_replay_key
        )
        result: list[dict[str, Any]] = []
        for stream_id, fields in entries:
            raw_payload = fields.get("payload")
            if not raw_payload:
                result.append({"id": stream_id, "malformed": True})
                continue
            try:
                message = QueueMessage.from_dict(json.loads(raw_payload))
                data = message.data
                result.append(
                    {
                        "id": stream_id,
                        "message_id": message.id,
                        "original_queue": data.get("original_queue"),
                        "error": data.get("error"),
                        "failed_at": data.get("failed_at"),
                        "replayed": stream_id in replayed,
                    }
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                result.append(
                    {"id": stream_id, "malformed": True, "error": str(exc)}
                )
        return result

    async def replay_dead_letter(self, stream_id: str) -> dict[str, Any]:
        """Requeue one DLQ message once while retaining its audit record."""
        if not self._running:
            await self.start()
        dead_letter_stream = self.stream_name(QueueType.DEAD_LETTER)
        entries = await redis_manager.client.xrange(
            dead_letter_stream, min=stream_id, max=stream_id, count=1
        )
        if not entries:
            raise ValueError(f"Dead-letter entry {stream_id} was not found")

        replay_key = settings.redis_dead_letter_replay_key
        if await redis_manager.client.sismember(replay_key, stream_id):
            return {"status": "already_replayed", "dead_letter_id": stream_id}

        _, fields = entries[0]
        raw_payload = fields.get("payload")
        if not raw_payload:
            raise ValueError(f"Dead-letter entry {stream_id} has no payload")
        dead_letter_message = QueueMessage.from_dict(json.loads(raw_payload))
        original_data = dead_letter_message.data.get("original_message")
        if not isinstance(original_data, dict):
            raise ValueError(f"Dead-letter entry {stream_id} has no original message")
        original_message = QueueMessage.from_dict(original_data)
        if original_message.queue_type == QueueType.DEAD_LETTER:
            raise ValueError("Dead-letter entries cannot be replayed into the dead-letter queue")

        reserved = await redis_manager.client.sadd(replay_key, stream_id)
        if not reserved:
            return {"status": "already_replayed", "dead_letter_id": stream_id}
        try:
            new_message_id = await self.send(
                original_message.queue_type,
                original_message.data,
                priority=original_message.priority,
                retry_count=0,
                max_retries=original_message.max_retries,
            )
        except Exception:
            await redis_manager.client.srem(replay_key, stream_id)
            raise
        return {
            "status": "replayed",
            "dead_letter_id": stream_id,
            "message_id": new_message_id,
            "queue_type": original_message.queue_type.value,
        }

    async def dead_letter(
        self,
        message: QueueMessage,
        error: str,
    ) -> str:
        """Append an exhausted message to the durable dead-letter stream."""
        dead_letter_data = {
            "original_queue": message.queue_type.value,
            "original_message": message.to_dict(),
            "error": error,
            "failed_at": datetime.utcnow().isoformat(),
        }
        return await self.send(QueueType.DEAD_LETTER, dead_letter_data)
