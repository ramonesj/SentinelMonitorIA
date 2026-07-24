"""Shared queue message contract used by mock and Redis providers."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class QueueType(str, Enum):
    """Supported telemetry queue names."""

    TELEMETRY = "telemetry"
    METRICS = "metrics"
    LOGS = "logs"
    EVENTS = "events"
    ALERTS = "alerts"
    DEAD_LETTER = "dead_letter"


@dataclass
class QueueMessage:
    """Provider-neutral serialized queue message."""

    id: str
    queue_type: QueueType
    data: Dict[str, Any]
    priority: int = 0
    created_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "queue_type": self.queue_type.value,
            "data": self.data,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueMessage":
        return cls(
            id=data["id"],
            queue_type=QueueType(data["queue_type"]),
            data=data["data"],
            priority=data.get("priority", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )
