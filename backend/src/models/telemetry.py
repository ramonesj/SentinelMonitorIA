"""
Telemetry models for storing and processing metrics and logs
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Float, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from src.models.base import Base, AuditMixin


class TelemetryBatch(Base):
    """Batch of telemetry data received from agents"""
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("agent.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Batch information
    batch_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # metrics, logs, events
    
    # Processing status
    status: Mapped[str] = mapped_column(
        String(50),
        default="received",
        nullable=False,
        index=True
    )  # received, processing, processed, failed
    
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Size and timing
    event_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )
    
    total_size_bytes: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )
    
    ingestion_latency_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )
    
    processing_latency_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    retry_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    analysis_enqueued_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    
    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        default=dict
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="telemetry_batches"
    )
    
    agent: Mapped["Agent"] = relationship(
        back_populates="telemetry_batches"
    )
    
    metrics: Mapped[List["Metric"]] = relationship(
        back_populates="batch"
    )
    
    logs: Mapped[List["LogEntry"]] = relationship(
        back_populates="batch"
    )
    
    events: Mapped[List["Event"]] = relationship(
        back_populates="batch"
    )
    
    def __repr__(self) -> str:
        return f"<TelemetryBatch {self.batch_id} ({self.source_type}, {self.status})>"
    
    @property
    def is_processed(self) -> bool:
        """Check if batch has been processed"""
        return self.status == "processed"
    
    @property
    def is_failed(self) -> bool:
        """Check if batch processing failed"""
        return self.status == "failed"


class Metric(Base):
    """Metric data from agents"""
    
    batch_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("telemetrybatch.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("agent.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Metric identification
    metric_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    metric_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # gauge, counter, histogram, summary
    
    # Value
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    
    value_raw: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # Labels and metadata
    labels: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    
    unit: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Processing
    is_anomaly: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    
    anomaly_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    
    # Relationships
    batch: Mapped["TelemetryBatch"] = relationship(
        back_populates="metrics"
    )
    
    def __repr__(self) -> str:
        return f"<Metric {self.metric_name}={self.value} ({self.metric_type})>"


class LogEntry(Base):
    """Log entry from agents"""
    
    batch_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("telemetrybatch.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("agent.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Log content
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # debug, info, warning, error, fatal
    
    # Source
    service: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    
    component: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        default=dict
    )
    
    # Parsed fields
    parsed_fields: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    
    # Processing
    is_alert: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    
    alert_rule_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    
    # Search optimization
    search_vector: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Relationships
    batch: Mapped["TelemetryBatch"] = relationship(
        back_populates="logs"
    )
    
    def __repr__(self) -> str:
        return f"<LogEntry {self.level}: {self.message[:50]}...>"


class Event(Base):
    """Event data from agents"""
    
    batch_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("telemetrybatch.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("agent.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Event identification
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    
    event_source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    # Content
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    details: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # Severity
    severity: Mapped[str] = mapped_column(
        String(50),
        default="info",
        nullable=False,
        index=True
    )  # info, warning, error, critical
    
    # Processing
    is_correlated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    
    # Alerting
    should_alert: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    alert_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    batch: Mapped["TelemetryBatch"] = relationship(
        back_populates="events"
    )
    
    def __repr__(self) -> str:
        return f"<Event {self.event_type}: {self.summary[:50]}...>"