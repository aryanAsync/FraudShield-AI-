"""Unit and Integration Tests for SQLAlchemy Database Models and Repositories."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AuditLog, InvestigationCase
from app.db.repositories.prediction_repository import PredictionRepository
from app.db.repositories.transaction_repository import TransactionRepository


def test_transaction_repository_create_and_get(db_session: Session):
    """Verify transaction creation and retrieval by ID."""
    features = {f"V{i}": 0.05 * i for i in range(1, 29)}
    tx = TransactionRepository.create(
        db=db_session,
        transaction_time=123.45,
        amount=50.00,
        features=features,
        external_reference="REF-001",
        submitted_by="analyst_1",
    )
    db_session.flush()

    retrieved = TransactionRepository.get_by_id(db_session, tx.id)
    assert retrieved is not None
    assert retrieved.id == tx.id
    assert retrieved.transaction_time == 123.45
    assert retrieved.amount == 50.00
    assert retrieved.external_reference == "REF-001"
    assert retrieved.submitted_by == "analyst_1"
    assert retrieved.features["V1"] == 0.05
    assert retrieved.created_at is not None


def test_transaction_unique_external_reference(db_session: Session):
    """Verify external_reference enforces uniqueness."""
    features = {f"V{i}": 0.0 for i in range(1, 29)}
    TransactionRepository.create(
        db=db_session,
        transaction_time=10.0,
        amount=10.0,
        features=features,
        external_reference="DUPLICATE_KEY",
    )
    db_session.flush()

    with pytest.raises(IntegrityError):
        TransactionRepository.create(
            db=db_session,
            transaction_time=20.0,
            amount=20.0,
            features=features,
            external_reference="DUPLICATE_KEY",
        )
        db_session.flush()

    db_session.rollback()


def test_transaction_prediction_atomic_link(db_session: Session):
    """Verify transaction and prediction records link correctly and preserve relationship."""
    features = {f"V{i}": 0.1 for i in range(1, 29)}
    tx = TransactionRepository.create(
        db=db_session,
        transaction_time=200.0,
        amount=99.99,
        features=features,
    )
    db_session.flush()

    pred = PredictionRepository.create(
        db=db_session,
        transaction_id=tx.id,
        fraud_probability=0.88,
        risk_score=88.0,
        predicted_class=1,
        risk_level="HIGH",
        decision_threshold=0.50,
        model_version="fraud-model-v1",
        explanation=[{"feature": "V14", "attribution": 0.45, "value": -3.2}],
    )
    db_session.flush()

    # Verify relationship navigation from transaction
    refetched_tx = TransactionRepository.get_by_id(db_session, tx.id)
    assert refetched_tx is not None
    assert len(refetched_tx.predictions) == 1
    assert refetched_tx.predictions[0].id == pred.id
    assert refetched_tx.predictions[0].risk_score == 88.0
    assert refetched_tx.predictions[0].explanation is not None


def test_multiple_predictions_history(db_session: Session):
    """Verify rescoring a transaction appends new prediction without overwriting earlier ones."""
    features = {f"V{i}": 0.0 for i in range(1, 29)}
    tx = TransactionRepository.create(
        db=db_session,
        transaction_time=300.0,
        amount=15.00,
        features=features,
    )
    db_session.flush()

    # Prediction 1 under Model V1
    pred_v1 = PredictionRepository.create(
        db=db_session,
        transaction_id=tx.id,
        fraud_probability=0.25,
        risk_score=25.0,
        predicted_class=0,
        risk_level="LOW",
        decision_threshold=0.50,
        model_version="fraud-model-v1",
    )
    db_session.flush()

    # Prediction 2 under Model V2 (rescored)
    pred_v2 = PredictionRepository.create(
        db=db_session,
        transaction_id=tx.id,
        fraud_probability=0.85,
        risk_score=85.0,
        predicted_class=1,
        risk_level="HIGH",
        decision_threshold=0.50,
        model_version="fraud-model-v2",
    )
    db_session.flush()

    history = PredictionRepository.get_by_transaction_id(db_session, tx.id)
    assert len(history) == 2
    # Verify both records exist and newest is first
    pred_ids = [p.id for p in history]
    assert pred_v1.id in pred_ids
    assert pred_v2.id in pred_ids
    assert history[0].model_version == "fraud-model-v2"

    latest = PredictionRepository.get_latest_for_transaction(db_session, tx.id)
    assert latest is not None
    assert latest.id == pred_v2.id


def test_cascade_delete_transaction_removes_predictions(db_session: Session):
    """Verify deleting a transaction cascades and deletes child prediction records."""
    features = {f"V{i}": 0.0 for i in range(1, 29)}
    tx = TransactionRepository.create(
        db=db_session,
        transaction_time=400.0,
        amount=12.00,
        features=features,
    )
    db_session.flush()

    pred = PredictionRepository.create(
        db=db_session,
        transaction_id=tx.id,
        fraud_probability=0.10,
        risk_score=10.0,
        predicted_class=0,
        risk_level="LOW",
        decision_threshold=0.50,
        model_version="fraud-model-v1",
    )
    db_session.flush()
    pred_id = pred.id

    # Delete transaction
    db_session.delete(tx)
    db_session.flush()

    assert PredictionRepository.get_by_id(db_session, pred_id) is None


def test_prediction_check_constraints(db_session: Session):
    """Verify check constraints prevent invalid probability, score, or predicted_class."""
    features = {f"V{i}": 0.0 for i in range(1, 29)}
    tx = TransactionRepository.create(
        db=db_session,
        transaction_time=500.0,
        amount=25.00,
        features=features,
    )
    db_session.flush()

    # Invalid probability > 1.0
    with pytest.raises(IntegrityError):
        PredictionRepository.create(
            db=db_session,
            transaction_id=tx.id,
            fraud_probability=1.5,
            risk_score=150.0,
            predicted_class=1,
            risk_level="HIGH",
            decision_threshold=0.5,
            model_version="v1",
        )
        db_session.flush()
    db_session.rollback()

    # Invalid predicted_class (must be 0 or 1)
    with pytest.raises(IntegrityError):
        PredictionRepository.create(
            db=db_session,
            transaction_id=tx.id,
            fraud_probability=0.5,
            risk_score=50.0,
            predicted_class=99,
            risk_level="MEDIUM",
            decision_threshold=0.5,
            model_version="v1",
        )
        db_session.flush()
    db_session.rollback()


def test_investigation_case_and_audit_log(db_session: Session):
    """Verify InvestigationCase and AuditLog creation and constraints."""
    features = {f"V{i}": 0.0 for i in range(1, 29)}
    tx = TransactionRepository.create(
        db=db_session,
        transaction_time=600.0,
        amount=1000.00,
        features=features,
    )
    db_session.flush()

    # Create investigation case
    case = InvestigationCase(
        transaction_id=tx.id,
        status="OPEN",
        assigned_to="lead_analyst",
        notes="High value suspicious transaction flagged for manual review.",
    )
    db_session.add(case)
    db_session.flush()

    assert case.id is not None
    assert case.status == "OPEN"
    assert case.assigned_to == "lead_analyst"

    # Create audit log
    audit = AuditLog(
        actor_id="system",
        action="SCORE_AND_PERSIST",
        entity_type="transaction",
        entity_id=str(tx.id),
        details={"risk_score": 88.5, "flagged": True},
    )
    db_session.add(audit)
    db_session.flush()

    assert audit.id is not None
    assert audit.action == "SCORE_AND_PERSIST"
    assert audit.entity_id == str(tx.id)
