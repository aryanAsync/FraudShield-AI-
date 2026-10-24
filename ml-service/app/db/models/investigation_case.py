"""SQLAlchemy model for fraud investigation cases."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.case_note import CaseNote
    from app.db.models.transaction import Transaction
    from app.db.models.user import User


class InvestigationCase(Base):
    """Case management entity tracking manual analyst reviews and fraud adjudications."""

    __tablename__ = "investigation_cases"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'IN_REVIEW', 'CONFIRMED_FRAUD', 'LEGITIMATE', 'CLOSED')",
            name="ck_investigation_cases_status_valid",
        ),
        Index("ix_investigation_cases_status", "status"),
        Index("ix_investigation_cases_assigned_to", "assigned_to"),
        Index("ix_investigation_cases_assigned_user_id", "assigned_user_id"),
        Index("ix_investigation_cases_created_at_desc", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        doc="One-to-one link to the transaction under investigation",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="OPEN",
        nullable=False,
        doc="Case status: OPEN, IN_REVIEW, CONFIRMED_FRAUD, LEGITIMATE, or CLOSED",
    )
    assigned_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Foreign key to assigned analyst User record",
    )
    assigned_to: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Assigned analyst username or email for display/compatibility",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional case summary or opening notes provided by creator",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Legacy free-text findings and notes, retained for backward compatibility",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when case was finalized/resolved",
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="investigation_case",
    )
    assigned_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_user_id],
        back_populates="assigned_cases",
    )
    case_notes: Mapped[list["CaseNote"]] = relationship(
        "CaseNote",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseNote.created_at.asc()",
    )
