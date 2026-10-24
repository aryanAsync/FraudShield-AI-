"""SQLAlchemy model for administrative and security audit logs."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

JSONType = JSONB().with_variant(JSON(), "sqlite")


class AuditLog(Base):
    """Immutable audit trail of security events, administrative operations, and score actions."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at_desc", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Actor ID who performed the action, reserved for future authentication phase",
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Action name (e.g., SCORE_TRANSACTION, UPDATE_INVESTIGATION_STATUS)",
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Target entity type (e.g., transaction, investigation_case)",
    )
    entity_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Primary identifier of target entity",
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
        doc="Structured event metadata or payload delta",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        doc="Timezone-aware log creation timestamp",
    )
