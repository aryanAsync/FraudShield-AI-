"""Repository for Prediction database queries and persistence."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.prediction import Prediction


class PredictionRepository:
    """Encapsulates database operations for predictions."""

    @staticmethod
    def create(
        db: Session,
        transaction_id: int,
        fraud_probability: float,
        risk_score: float,
        predicted_class: int,
        risk_level: str,
        decision_threshold: float,
        model_version: str,
        explanation: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> Prediction:
        """Create and add a new prediction entity to the current session (uncommitted)."""
        prediction = Prediction(
            transaction_id=transaction_id,
            fraud_probability=fraud_probability,
            risk_score=risk_score,
            predicted_class=predicted_class,
            risk_level=risk_level,
            decision_threshold=decision_threshold,
            model_version=model_version,
            explanation=explanation,
        )
        db.add(prediction)
        db.flush()
        return prediction

    @staticmethod
    def get_by_id(db: Session, prediction_id: int) -> Prediction | None:
        """Retrieve prediction by its primary key."""
        stmt = select(Prediction).where(Prediction.id == prediction_id)
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_transaction_id(db: Session, transaction_id: int) -> list[Prediction]:
        """Retrieve all historical predictions for a given transaction, ordered newest first."""
        stmt = (
            select(Prediction)
            .where(Prediction.transaction_id == transaction_id)
            .order_by(Prediction.predicted_at.desc(), Prediction.id.desc())
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_latest_for_transaction(db: Session, transaction_id: int) -> Prediction | None:
        """Retrieve the most recent prediction for a given transaction."""
        stmt = (
            select(Prediction)
            .where(Prediction.transaction_id == transaction_id)
            .order_by(Prediction.predicted_at.desc(), Prediction.id.desc())
            .limit(1)
        )
        return db.scalars(stmt).first()
