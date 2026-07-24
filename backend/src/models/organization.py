"""
Organization and Agent models for SentinelMonitorIA
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from src.models.base import Base, AuditMixin, SoftDeleteMixin


class Organization(Base, AuditMixin, SoftDeleteMixin):
    """Organization model for multi-tenancy"""
    
    # Organization information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Contact information
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    website: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Configuration
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False
    )
    
    locale: Mapped[str] = mapped_column(
        String(10),
        default="en-US",
        nullable=False
    )
    
    # Subscription and limits
    subscription_tier: Mapped[str] = mapped_column(
        String(50),
        default="free",
        nullable=False
    )
    
    max_agents: Mapped[int] = mapped_column(
        default=10,
        nullable=False
    )
    
    max_events_per_day: Mapped[int] = mapped_column(
        default=100000,
        nullable=False
    )
    
    retention_days: Mapped[int] = mapped_column(
        default=30,
        nullable=False
    )
    
    # Rate limiting
    rate_limit_requests: Mapped[int] = mapped_column(
        default=1000,
        nullable=False
    )
    
    rate_limit_period: Mapped[int] = mapped_column(
        default=60,  # seconds
        nullable=False
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    suspended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        default=dict
    )
    
    # Relationships
    users: Mapped[List["UserOrganization"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    agents: Mapped[List["Agent"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    tokens: Mapped[List["Token"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    telemetry_batches: Mapped[List["TelemetryBatch"]] = relationship(
        back_populates="organization"
    )
    
    def __repr__(self) -> str:
        return f"<Organization {self.name} ({self.slug})>"
    
    @property
    def is_suspended(self) -> bool:
        """Check if organization is suspended"""
        return self.suspended_at is not None
    
    @property
    def active_agent_count(self) -> int:
        """Get count of active agents"""
        return len([a for a in self.agents if a.is_active])


class Agent(Base, AuditMixin):
    """Agent model for tracking telemetry agents"""
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Agent identification
    agent_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    hostname: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    # Agent information
    agent_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    
    agent_type: Mapped[str] = mapped_column(
        String(50),
        default="vector",
        nullable=False
    )
    
    platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    
    architecture: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    last_telemetry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Connection information
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # Supports IPv6
        nullable=True
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Configuration
    configuration: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    
    tags: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    
    # Metrics
    total_events_sent: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )
    
    total_bytes_sent: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )
    
    average_latency_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )
    
    # Error tracking
    error_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )
    
    last_error_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    last_error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="agents"
    )
    
    telemetry_batches: Mapped[List["TelemetryBatch"]] = relationship(
        back_populates="agent"
    )
    
    def __repr__(self) -> str:
        return f"<Agent {self.name} ({self.agent_id})>"
    
    @property
    def is_online(self) -> bool:
        """Check if agent is currently online"""
        if not self.last_seen_at:
            return False
        
        # Consider agent online if seen in last 5 minutes
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        return self.last_seen_at > cutoff
    
    @property
    def uptime_seconds(self) -> Optional[int]:
        """Calculate agent uptime in seconds"""
        if not self.last_seen_at or not self.created_at:
            return None
        
        return int((self.last_seen_at - self.created_at).total_seconds())