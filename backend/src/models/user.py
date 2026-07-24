"""
User model for SentinelMonitorIA
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid
from src.models.base import Base, AuditMixin


class User(Base, AuditMixin):
    """User model for authentication and authorization"""
    
    # Personal information
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False
    )
    
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Authentication
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    # Security
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )
    
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Preferences
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
    
    # Relationships
    organizations: Mapped[List["UserOrganization"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    tokens: Mapped[List["Token"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User {self.username} ({self.email})>"
    
    @property
    def is_locked(self) -> bool:
        """Check if user account is locked"""
        if not self.locked_until:
            return False
        return self.locked_until > datetime.now(timezone.utc)


class UserOrganization(Base):
    """Many-to-many relationship between users and organizations"""
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # Role in organization
    role: Mapped[str] = mapped_column(
        String(50),
        default="member",
        nullable=False
    )
    
    # Permissions (JSON serialized)
    permissions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="organizations"
    )
    
    organization: Mapped["Organization"] = relationship(
        back_populates="users"
    )
    
    __table_args__ = (
        Index("ix_user_organization_user_id", "user_id"),
        Index("ix_user_organization_org_id", "organization_id"),
    )
    
    def __repr__(self) -> str:
        return f"<UserOrganization user_id={self.user_id} org_id={self.organization_id} role={self.role}>"


class JwtSession(Base):
    """Persisted JWT state used for revocation and refresh-token rotation."""

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    jti: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
    )

    token_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    replaced_by_jti: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<JwtSession {self.jti} ({self.token_type})>"

    @property
    def is_revoked(self) -> bool:
        """Return whether this JWT can no longer be used."""
        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        """Return whether this persisted JWT session is currently valid."""
        return not self.is_revoked and self.expires_at > datetime.now(timezone.utc)


class Token(Base):
    """Authentication token metadata; API keys are stored as SHA-256 digests."""
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Token digest for API keys; legacy rows may contain plaintext until first use.
    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        index=True
    )
    
    token_type: Mapped[str] = mapped_column(
        String(50),
        default="bearer",
        nullable=False
    )
    
    name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Security
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # JSON-serialized scopes for API keys. Legacy rows remain nullable and
    # receive the backwards-compatible telemetry:write scope at validation.
    scopes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    replaced_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("token.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # Supports IPv6
        nullable=True
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Rate limiting
    rate_limit_requests: Mapped[int] = mapped_column(
        default=100,
        nullable=False
    )
    
    rate_limit_period: Mapped[int] = mapped_column(
        default=60,  # seconds
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="tokens"
    )
    
    organization: Mapped[Optional["Organization"]] = relationship(
        back_populates="tokens"
    )
    
    def __repr__(self) -> str:
        return f"<Token {self.id} ({self.token_type})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        if not self.expires_at:
            return False
        return self.expires_at < datetime.now(timezone.utc)
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid"""
        return self.is_active and self.revoked_at is None and not self.is_expired