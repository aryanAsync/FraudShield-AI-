"""Automated Unit Tests for Pydantic V2 Schemas.

Validates that schemas strictly enforce finite numbers, forbid unexpected fields
(especially 'Class'), require all features, and prevent invalid input values.
"""

import pytest
from pydantic import ValidationError

from app.schemas.prediction import PredictionResponse, RiskLevel
from app.schemas.transaction import BatchTransactionInput, TransactionInput


@pytest.fixture
def valid_transaction_payload() -> dict:
    """Return a complete, valid dictionary of transaction features."""
    payload = {"Time": 100.0, "Amount": 45.50}
    for i in range(1, 29):
        payload[f"V{i}"] = 0.05 * i
    return payload


def test_valid_transaction_schema(valid_transaction_payload: dict):
    """Verify that a standard valid payload parses correctly."""
    tx = TransactionInput(**valid_transaction_payload)
    assert tx.Time == 100.0
    assert tx.Amount == 45.50
    assert tx.V1 == 0.05
    assert tx.V28 == 0.05 * 28


def test_forbid_target_field_class(valid_transaction_payload: dict):
    """Verify that incoming payloads containing the target field 'Class' are strictly rejected."""
    payload_with_class = valid_transaction_payload.copy()
    payload_with_class["Class"] = 0

    with pytest.raises(ValidationError) as exc_info:
        TransactionInput(**payload_with_class)

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("Class",) and err["type"] == "extra_forbidden" for err in errors)


def test_forbid_arbitrary_extra_fields(valid_transaction_payload: dict):
    """Verify that random unexpected fields are rejected."""
    payload_with_extra = valid_transaction_payload.copy()
    payload_with_extra["card_number"] = "4111222233334444"

    with pytest.raises(ValidationError) as exc_info:
        TransactionInput(**payload_with_extra)

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("card_number",) for err in errors)


def test_missing_feature_rejected(valid_transaction_payload: dict):
    """Verify that omission of any feature raises ValidationError."""
    incomplete_payload = valid_transaction_payload.copy()
    del incomplete_payload["V14"]

    with pytest.raises(ValidationError) as exc_info:
        TransactionInput(**incomplete_payload)

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("V14",) for err in errors)


def test_reject_nan_values(valid_transaction_payload: dict):
    """Verify that NaN is rejected."""
    nan_payload = valid_transaction_payload.copy()
    nan_payload["V5"] = float("nan")

    with pytest.raises(ValidationError) as exc_info:
        TransactionInput(**nan_payload)

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("V5",) for err in errors)


def test_reject_infinite_values(valid_transaction_payload: dict):
    """Verify that positive and negative infinity are rejected."""
    for inf_val in [float("inf"), float("-inf")]:
        inf_payload = valid_transaction_payload.copy()
        inf_payload["Amount"] = inf_val

        with pytest.raises(ValidationError) as exc_info:
            TransactionInput(**inf_payload)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("Amount",) for err in errors)


def test_negative_amount_rejected(valid_transaction_payload: dict):
    """Verify that negative transaction amounts are rejected."""
    neg_payload = valid_transaction_payload.copy()
    neg_payload["Amount"] = -10.0

    with pytest.raises(ValidationError) as exc_info:
        TransactionInput(**neg_payload)

    errors = exc_info.value.errors()
    assert any(err["loc"] == ("Amount",) for err in errors)


def test_batch_transaction_empty_rejected():
    """Verify that empty batch lists are rejected."""
    with pytest.raises(ValidationError):
        BatchTransactionInput(transactions=[])


def test_batch_transaction_valid(valid_transaction_payload: dict):
    """Verify that valid batch transaction lists are accepted."""
    batch = BatchTransactionInput(
        transactions=[
            TransactionInput(**valid_transaction_payload),
            TransactionInput(**valid_transaction_payload),
        ]
    )
    assert len(batch.transactions) == 2


def test_prediction_response_schema():
    """Verify PredictionResponse fields, constraints, and ranges."""
    res = PredictionResponse(
        fraud_probability=0.75,
        risk_score=75.0,
        predicted_class=1,
        risk_level=RiskLevel.HIGH,
        threshold=0.50,
        model_version="test-model-v1",
    )
    assert res.fraud_probability == 0.75
    assert res.risk_score == 75.0
    assert res.risk_level == RiskLevel.HIGH
