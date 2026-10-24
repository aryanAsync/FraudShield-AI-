"""SQLAlchemy model for investigation case chronological notes."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.investigation_case import InvestigationCase
    from app.db.models.user import User


class CaseNote(Base):
    """Chronological, immutable investigation findings and notes logged by fraud analysts."""

    __tablename__ = "case_notes"
    __table_args__ = (
        Index("ix_case_notes_case_id_created_at", "case_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("investigation_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key referencing the parent investigation case",
    )
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Author user identifier, nullified if user is deleted to preserve investigation history",
    )
    author_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Display name of author at the time note was created",
    )
    author_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Email address of author at the time note was created",
    )
    author_role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="RBAC role of author at note creation (e.g. ANALYST, ADMIN)",
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Case findings, evidence summary, and investigation notes",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="Timezone-aware creation timestamp",
    )

    # Relationships
    case: Mapped["InvestigationCase"] = relationship(
        "InvestigationCase",
        back_populates="case_notes",
    )
    author: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[author_id],
    )
