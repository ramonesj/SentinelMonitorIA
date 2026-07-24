"""
Base SQLAlchemy models with common fields and utilities
"""

from datetime import datetime
from typing import Any
from uuid import uuid4, UUID
from sqlalchemy import MetaData, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr
from sqlalchemy.ext.asyncio import AsyncAttrs


# SQLAlchemy metadata with naming conventions
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    
    metadata = metadata
    
    # Common columns
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name"""
        return cls.__name__.lower()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update(self, **kwargs: Any) -> None:
        """Update model fields"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def get_columns(cls) -> list[str]:
        """Get all column names"""
        return [column.name for column in cls.__table__.columns]


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    def soft_delete(self) -> None:
        """Soft delete the record"""
        self.deleted_at = func.now()
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted"""
        return self.deleted_at is not None


class AuditMixin:
    """Mixin for audit tracking"""
    
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True
    )
    
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True
    )