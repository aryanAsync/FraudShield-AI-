"""SQLAlchemy model for fraud risk predictions."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.transaction import Transaction

JSONType = JSONB().with_variant(JSON(), "sqlite")


class Prediction(Base):
    """Fraud prediction result snapshot linked to a specific transaction."""

    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint(
            "fraud_probability >= 0.0 AND fraud_probability <= 1.0",
            name="ck_predictions_fraud_probability_range",
        ),
        CheckConstraint(
            "risk_score >= 0.0 AND risk_score <= 100.0",
            name="ck_predictions_risk_score_range",
        ),
        CheckConstraint(
            "predicted_class IN (0, 1)",
            name="ck_predictions_predicted_class_binary",
        ),
        CheckConstraint(
            "decision_threshold >= 0.0 AND decision_threshold <= 1.0",
            name="ck_predictions_threshold_range",
        ),
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH')",
            name="ck_predictions_risk_level_valid",
        ),
        Index("ix_predictions_transaction_id", "transaction_id"),
        Index("ix_predictions_predicted_at_desc", "predicted_at"),
        Index("ix_predictions_risk_class", "risk_level", "predicted_class"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key pointing to the evaluated transaction",
    )
    fraud_probability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Model calibrated probability that transaction is fraudulent [0.0 - 1.0]",
    )
    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Normalized operational risk score [0.0 - 100.0]",
    )
    predicted_class: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Binary classification decision: 1 = Flagged Fraud Risk, 0 = Legitimate",
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Categorical risk tier: LOW, MEDIUM, or HIGH",
    )
    decision_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Decision threshold applied for positive fraud classification",
    )
    model_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Artifact identifier used for this prediction",
    )
    explanation: Mapped[list[dict[str, Any]] | dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
        doc="SHAP feature attribution explanations if requested during inference",
    )
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        doc="Timezone-aware prediction timestamp",
    )

    # Relationship
    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="predictions",
    )
