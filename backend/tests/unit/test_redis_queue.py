import json
from typing import Any

import pytest

from src.database.redis import redis_manager
from src.services.queue_contract import QueueMessage, QueueType
from src.services.redis_streams import RedisStreamQueueProducer
from src.workers.telemetry_worker import TelemetryWorker


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.hashes: dict[str, dict[str, Any]] = {}
        self.groups: set[tuple[str, str]] = set()
        self.acknowledged: list[tuple[str, str, str]] = []

    async def xadd(self, stream: str, fields: dict[str, str], **_: Any) -> str:
        entries = self.streams.setdefault(stream, [])
        stream_id = f"{len(entries) + 1}-0"
        entries.append((stream_id, fields))
        return stream_id

    async def hincrby(self, key: str, field: str, amount: int) -> int:
        values = self.hashes.setdefault(key, {})
        values[field] = int(values.get(field, 0)) + amount
        return values[field]

    async def hset(
        self,
        key: str,
        field: str | None = None,
        value: Any = None,
        mapping: dict[str, Any] | None = None,
    ) -> int:
        values = self.hashes.setdefault(key, {})
        if mapping is not None:
            values.update(mapping)
        elif field is not None:
            values[field] = value
        return 1

    async def xlen(self, stream: str) -> int:
        return len(self.streams.get(stream, []))

    async def xrevrange(self, stream: str, **kwargs: Any) -> list[Any]:
        entries = list(reversed(self.streams.get(stream, [])))
        count = kwargs.get("count")
        return entries[:count] if count else entries

    async def xrange(self, stream: str, **kwargs: Any) -> list[Any]:
        entries = self.streams.get(stream, [])
        stream_id = kwargs.get("min")
        if stream_id is None:
            return entries
        return [entry for entry in entries if entry[0] == stream_id]

    async def smembers(self, key: str) -> set[str]:
        return set(self.hashes.get(key, {}).get("members", set()))

    async def sismember(self, key: str, value: str) -> bool:
        return value in await self.smembers(key)

    async def sadd(self, key: str, value: str) -> int:
        values = self.hashes.setdefault(key, {}).setdefault("members", set())
        if value in values:
            return 0
        values.add(value)
        return 1

    async def srem(self, key: str, value: str) -> int:
        values = self.hashes.setdefault(key, {}).setdefault("members", set())
        if value not in values:
            return 0
        values.remove(value)
        return 1

    async def hgetall(self, key: str) -> dict[str, Any]:
        return self.hashes.get(key, {}).copy()

    async def xgroup_create(self, stream: str, group: str, **_: Any) -> None:
        group_key = (stream, group)
        if group_key in self.groups:
            raise RuntimeError("BUSYGROUP Consumer Group name already exists")
        self.groups.add(group_key)

    async def xreadgroup(self, **kwargs: Any) -> list[Any]:
        stream = next(iter(kwargs["streams"]))
        return [[stream, self.streams.get(stream, [])]]

    async def xautoclaim(self, *_: Any, **__: Any) -> list[Any]:
        return ["0-0", [], []]

    async def xack(self, stream: str, group: str, stream_id: str) -> int:
        self.acknowledged.append((stream, group, stream_id))
        return 1

    async def delete(self, stream: str) -> int:
        return int(self.streams.pop(stream, None) is not None)


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    client = FakeRedis()
    monkeypatch.setattr(redis_manager, "client", client)
    return client


def test_queue_message_round_trip() -> None:
    original = QueueMessage(
        id="message-1",
        queue_type=QueueType.TELEMETRY,
        data={"batch_id": "batch-1", "value": 42},
        priority=5,
        retry_count=1,
        max_retries=4,
    )

    restored = QueueMessage.from_dict(original.to_dict())

    assert restored == original
    assert restored.queue_type is QueueType.TELEMETRY


@pytest.mark.asyncio
async def test_redis_producer_send_and_get_stats(fake_redis: FakeRedis) -> None:
    producer = RedisStreamQueueProducer(stream_prefix="test:stream", max_stream_length=50)
    producer._running = True

    message_id = await producer.send(
        QueueType.TELEMETRY,
        {"batch_id": "batch-1"},
    )
    stats = await producer.get_stats()

    assert message_id
    assert stats["messages_sent"] == 1
    assert stats["current_queue_depths"]["telemetry"] == 1
    assert stats["current_queue_depths"]["dead_letter"] == 0
    assert fake_redis.streams["test:stream:telemetry"][0][1]["message_id"] == message_id


@pytest.mark.asyncio
async def test_consumer_group_read_and_ack(fake_redis: FakeRedis) -> None:
    producer = RedisStreamQueueProducer(stream_prefix="test:stream")
    producer._running = True
    await producer.send(QueueType.TELEMETRY, {"batch_id": "batch-1"})

    await producer.ensure_group(QueueType.TELEMETRY, "test-workers")
    entries = await producer.read_group(
        QueueType.TELEMETRY,
        "test-workers",
        "consumer-1",
    )
    await producer.acknowledge(QueueType.TELEMETRY, "test-workers", entries[0][0])

    assert entries[0][1]["message_id"]
    assert fake_redis.acknowledged == [
        ("test:stream:telemetry", "test-workers", entries[0][0])
    ]


class FakeWorkerProducer:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.dead_letters: list[tuple[QueueMessage, str]] = []
        self.acks: list[str] = []
        self.failed = 0

    async def record_failed(self) -> None:
        self.failed += 1

    async def send(self, queue_type: QueueType, data: dict[str, Any], **kwargs: Any) -> str:
        self.sent.append({"queue_type": queue_type, "data": data, **kwargs})
        return "retry-entry"

    async def dead_letter(self, message: QueueMessage, error: str) -> str:
        self.dead_letters.append((message, error))
        return "dead-letter-entry"

    async def acknowledge(self, _queue_type: QueueType, _group: str, stream_id: str) -> None:
        self.acks.append(stream_id)


@pytest.mark.asyncio
async def test_worker_retries_and_dead_letters_after_max_retries() -> None:
    producer = FakeWorkerProducer()
    worker = TelemetryWorker(producer=producer, group_name="test-workers")
    worker._persist_message = lambda _message: pytest.fail("persistence should fail")  # type: ignore[method-assign]

    async def fail_persistence(_message: QueueMessage) -> None:
        raise RuntimeError("database unavailable")

    worker._persist_message = fail_persistence  # type: ignore[method-assign]

    async def ignore_batch_failure(
        _message: QueueMessage,
        _error: str,
        _retry_count: int,
        _terminal: bool,
    ) -> None:
        return None

    worker._mark_batch_failure = ignore_batch_failure  # type: ignore[method-assign]
    first = QueueMessage(
        id="retry-1",
        queue_type=QueueType.TELEMETRY,
        data={"batch_id": "batch-1"},
        retry_count=0,
        max_retries=1,
    )
    terminal = QueueMessage(
        id="dead-1",
        queue_type=QueueType.TELEMETRY,
        data={"batch_id": "batch-2"},
        retry_count=1,
        max_retries=1,
    )

    await worker.process_entry("stream-1", {"payload": json.dumps(first.to_dict())})
    await worker.process_entry("stream-2", {"payload": json.dumps(terminal.to_dict())})

    assert producer.failed == 2
    assert producer.sent[0]["retry_count"] == 1
    assert producer.dead_letters[0][0].id == "dead-1"
    assert producer.acks == ["stream-1", "stream-2"]


@pytest.mark.asyncio
async def test_dead_letter_listing_and_replay_is_idempotent(fake_redis: FakeRedis) -> None:
    producer = RedisStreamQueueProducer(stream_prefix="test:stream")
    producer._running = True
    original = QueueMessage(
        id="failed-1",
        queue_type=QueueType.TELEMETRY,
        data={"batch_id": "batch-1"},
        max_retries=2,
    )

    dead_letter_id = await producer.dead_letter(original, "database unavailable")
    # send returns the message ID, while the Redis stream entry receives 1-0.
    entries = await producer.list_dead_letters()
    stream_id = entries[0]["id"]
    assert entries[0]["original_queue"] == "telemetry"
    assert entries[0]["replayed"] is False

    replay = await producer.replay_dead_letter(stream_id)
    replay_again = await producer.replay_dead_letter(stream_id)

    assert dead_letter_id
    assert replay["status"] == "replayed"
    assert replay["queue_type"] == "telemetry"
    assert replay_again["status"] == "already_replayed"
    assert len(fake_redis.streams["test:stream:telemetry"]) == 1
