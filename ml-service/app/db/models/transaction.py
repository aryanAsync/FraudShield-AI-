"""SQLAlchemy model for financial transactions."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, CheckConstraint, DateTime, Float, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.investigation_case import InvestigationCase
    from app.db.models.prediction import Prediction

JSONType = JSONB().with_variant(JSON(), "sqlite")


class Transaction(Base):
    """Financial transaction entity storing raw anonymized features for reproducible inference."""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount >= 0.0", name="ck_transactions_amount_non_negative"),
        Index("ix_transactions_created_at_desc", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_reference: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
        doc="Optional client-supplied unique transaction reference or idempotent key",
    )
    transaction_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Dataset Time value (seconds elapsed since first transaction)",
    )
    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Transaction amount in currency units",
    )
    features: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        doc="Validated anonymized model input features (V1 through V28)",
    )
    submitted_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Nullable user or service account identifier, reserved for authentication phase",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        doc="Timezone-aware creation timestamp",
    )

    # Relationships
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction",
        back_populates="transaction",
        cascade="all, delete-orphan",
        order_by="desc(Prediction.predicted_at)",
    )
    investigation_case: Mapped["InvestigationCase | None"] = relationship(
        "InvestigationCase",
        back_populates="transaction",
        cascade="all, delete-orphan",
        uselist=False,
    )
