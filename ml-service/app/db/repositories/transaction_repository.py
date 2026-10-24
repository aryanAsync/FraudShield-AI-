"""Repository for Transaction database queries and persistence."""

from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.prediction import Prediction
from app.db.models.transaction import Transaction


class TransactionRepository:
    """Encapsulates database operations for transactions."""

    @staticmethod
    def create(
        db: Session,
        transaction_time: float,
        amount: float,
        features: dict[str, Any],
        external_reference: str | None = None,
        submitted_by: str | None = None,
    ) -> Transaction:
        """Create and add a new transaction entity to the current session (uncommitted)."""
        tx = Transaction(
            transaction_time=transaction_time,
            amount=amount,
            features=features,
            external_reference=external_reference,
            submitted_by=submitted_by,
        )
        db.add(tx)
        db.flush()  # Populates tx.id within current transaction without committing
        return tx

    @staticmethod
    def get_by_id(db: Session, transaction_id: int) -> Transaction | None:
        """Retrieve transaction by primary key with predictions eagerly loaded."""
        stmt = (
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .options(
                selectinload(Transaction.predictions),
                selectinload(Transaction.investigation_case),
            )
        )
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_external_reference(db: Session, external_reference: str) -> Transaction | None:
        """Retrieve transaction by external reference key."""
        stmt = (
            select(Transaction)
            .where(Transaction.external_reference == external_reference)
            .options(
                selectinload(Transaction.predictions),
                selectinload(Transaction.investigation_case),
            )
        )
        return db.scalars(stmt).first()

    @staticmethod
    def list_transactions(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        risk_level: str | None = None,
        predicted_class: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Transaction], int]:
        """List transactions with pagination, deterministic ordering, and risk filters."""
        stmt = select(Transaction).options(
            selectinload(Transaction.predictions),
            selectinload(Transaction.investigation_case),
        )
        count_stmt = select(func.count(distinct(Transaction.id)))

        # Apply joins if filtering by prediction attributes
        if risk_level is not None or predicted_class is not None:
            stmt = stmt.join(Transaction.predictions)
            count_stmt = count_stmt.select_from(Transaction).join(Transaction.predictions)

            if risk_level is not None:
                normalized_risk = risk_level.upper()
                stmt = stmt.where(Prediction.risk_level == normalized_risk)
                count_stmt = count_stmt.where(Prediction.risk_level == normalized_risk)

            if predicted_class is not None:
                stmt = stmt.where(Prediction.predicted_class == predicted_class)
                count_stmt = count_stmt.where(Prediction.predicted_class == predicted_class)

        # Total matching records count
        total_count = db.scalar(count_stmt) or 0

        # Deterministic sorting
        sort_attr = getattr(Transaction, sort_by, Transaction.created_at)
        if sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_attr.asc(), Transaction.id.asc())
        else:
            stmt = stmt.order_by(sort_attr.desc(), Transaction.id.desc())

        # Eliminate duplicates from join and apply pagination
        stmt = stmt.distinct()
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        records = list(db.scalars(stmt).all())
        return records, total_count
