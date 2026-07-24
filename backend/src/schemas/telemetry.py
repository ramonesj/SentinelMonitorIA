"""
Pydantic schemas for telemetry data validation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum


class MetricType(str, Enum):
    """Metric types"""
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    UNTYPED = "untyped"


class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"
    TRACE = "trace"


class EventSeverity(str, Enum):
    """Event severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricSchema(BaseModel):
    """Schema for metric data"""
    
    name: str = Field(
        ...,
        description="Metric name",
        max_length=255,
        examples=["system.cpu.usage", "system.memory.used_bytes"]
    )
    
    value: Union[float, int] = Field(
        ...,
        description="Metric value",
        examples=[45.2, 1024, 0.75]
    )
    
    type: MetricType = Field(
        default=MetricType.GAUGE,
        description="Metric type"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Metric timestamp"
    )
    
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Metric labels",
        examples=[{"instance": "server-01", "job": "node"}]
    )
    
    unit: Optional[str] = Field(
        default=None,
        description="Metric unit",
        max_length=50,
        examples=["percent", "bytes", "seconds"]
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Metric description"
    )
    
    @validator("value")
    def validate_value(cls, v):
        """Validate metric value"""
        if not isinstance(v, (int, float)):
            raise ValueError("Metric value must be numeric")
        return float(v)
    
    @validator("labels")
    def validate_labels(cls, v):
        """Validate metric labels"""
        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Label keys and values must be strings")
        return v


class LogEntrySchema(BaseModel):
    """Schema for log entry"""
    
    message: str = Field(
        ...,
        description="Log message"
    )
    
    level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Log level"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Log timestamp"
    )
    
    service: Optional[str] = Field(
        default=None,
        description="Service name",
        max_length=255,
        examples=["nginx", "postgres", "api"]
    )
    
    component: Optional[str] = Field(
        default=None,
        description="Component name",
        max_length=255,
        examples=["auth", "database", "cache"]
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    parsed_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parsed fields from log message"
    )
    
    @validator("message")
    def validate_message(cls, v):
        """Validate log message"""
        if not v or not v.strip():
            raise ValueError("Log message cannot be empty")
        return v.strip()


class EventSchema(BaseModel):
    """Schema for event data"""
    
    type: str = Field(
        ...,
        description="Event type",
        max_length=100,
        examples=["container.start", "deployment.success", "alert.triggered"]
    )
    
    source: str = Field(
        ...,
        description="Event source",
        max_length=255,
        examples=["docker", "kubernetes", "monitoring"]
    )
    
    summary: str = Field(
        ...,
        description="Event summary"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event timestamp"
    )
    
    severity: EventSeverity = Field(
        default=EventSeverity.INFO,
        description="Event severity"
    )
    
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event details"
    )
    
    correlation_id: Optional[str] = Field(
        default=None,
        description="Correlation ID for related events",
        max_length=100
    )
    
    @validator("type")
    def validate_type(cls, v):
        """Validate event type"""
        if not v or not v.strip():
            raise ValueError("Event type cannot be empty")
        return v.strip()
    
    @validator("source")
    def validate_source(cls, v):
        """Validate event source"""
        if not v or not v.strip():
            raise ValueError("Event source cannot be empty")
        return v.strip()


class MetadataSchema(BaseModel):
    """Schema for telemetry metadata"""
    
    agent_id: str = Field(
        ...,
        description="Agent identifier",
        max_length=100,
        examples=["agent-123456", "server-01-vector"]
    )
    
    hostname: str = Field(
        ...,
        description="Hostname",
        max_length=255,
        examples=["server-01", "web-01.production"]
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Metadata timestamp"
    )
    
    agent_version: str = Field(
        ...,
        description="Agent version",
        max_length=50,
        examples=["1.0.0", "2.1.3"]
    )
    
    platform: Optional[str] = Field(
        default=None,
        description="Platform",
        max_length=50,
        examples=["linux", "windows", "darwin"]
    )
    
    architecture: Optional[str] = Field(
        default=None,
        description="Architecture",
        max_length=50,
        examples=["x86_64", "arm64", "amd64"]
    )
    
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional tags"
    )
    
    @validator("agent_id")
    def validate_agent_id(cls, v):
        """Validate agent ID"""
        if not v or not v.strip():
            raise ValueError("Agent ID cannot be empty")
        return v.strip()
    
    @validator("hostname")
    def validate_hostname(cls, v):
        """Validate hostname"""
        if not v or not v.strip():
            raise ValueError("Hostname cannot be empty")
        return v.strip()


class TelemetryBatchSchema(BaseModel):
    """Schema for telemetry batch"""
    
    metadata: MetadataSchema = Field(
        ...,
        description="Batch metadata"
    )
    
    metrics: List[MetricSchema] = Field(
        default_factory=list,
        description="List of metrics"
    )
    
    logs: List[LogEntrySchema] = Field(
        default_factory=list,
        description="List of log entries"
    )
    
    events: List[EventSchema] = Field(
        default_factory=list,
        description="List of events"
    )
    
    batch_id: Optional[str] = Field(
        default=None,
        description="Batch identifier for deduplication",
        max_length=100
    )
    
    @root_validator(skip_on_failure=True)
    def validate_batch_content(cls, values):
        """Validate that batch contains at least some data"""
        metrics = values.get("metrics", [])
        logs = values.get("logs", [])
        events = values.get("events", [])
        
        if not metrics and not logs and not events:
            raise ValueError("Telemetry batch must contain at least metrics, logs, or events")
        
        # Limit batch size for validation
        total_items = len(metrics) + len(logs) + len(events)
        if total_items > 10000:
            raise ValueError("Telemetry batch exceeds maximum size of 10,000 items")
        
        return values
    
    @validator("metrics")
    def validate_metrics_size(cls, v):
        """Validate metrics list size"""
        if len(v) > 5000:
            raise ValueError("Metrics list exceeds maximum size of 5,000 items")
        return v
    
    @validator("logs")
    def validate_logs_size(cls, v):
        """Validate logs list size"""
        if len(v) > 5000:
            raise ValueError("Logs list exceeds maximum size of 5,000 items")
        return v
    
    @validator("events")
    def validate_events_size(cls, v):
        """Validate events list size"""
        if len(v) > 1000:
            raise ValueError("Events list exceeds maximum size of 1,000 items")
        return v


class TelemetryResponseSchema(BaseModel):
    """Schema for telemetry API response"""
    
    status: str = Field(
        ...,
        description="Response status",
        examples=["success", "partial_success", "error"]
    )
    
    message: str = Field(
        ...,
        description="Response message"
    )
    
    batch_id: str = Field(
        ...,
        description="Batch identifier"
    )
    
    received_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the batch was received"
    )
    
    processed_items: Dict[str, int] = Field(
        ...,
        description="Number of items processed by type"
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="List of errors (if any)"
    )
    
    latency_ms: Optional[float] = Field(
        default=None,
        description="Processing latency in milliseconds"
    )


class TelemetryHealthSchema(BaseModel):
    """Schema for telemetry health check"""
    
    status: str = Field(
        ...,
        description="Health status",
        examples=["healthy", "degraded", "unhealthy"]
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )
    
    uptime_seconds: float = Field(
        ...,
        description="Service uptime in seconds"
    )
    
    version: str = Field(
        ...,
        description="Service version"
    )
    
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Service metrics"
    )