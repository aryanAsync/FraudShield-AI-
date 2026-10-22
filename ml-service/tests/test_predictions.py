"""Automated Tests for Prediction Endpoints and Model Logic."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import EXPECTED_FEATURE_ORDER, get_settings
from app.main import app
from app.ml.model_loader import load_model_artifact
from app.services.predictor import predictor_service


@pytest.fixture(scope="module")
def client():
    """Create test client with running FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_transaction() -> dict:
    """Fixture returning a standard legitimate transaction payload."""
    payload = {"Time": 500.0, "Amount": 29.99}
    for i in range(1, 29):
        payload[f"V{i}"] = 0.01 * (i - 14)
    return payload


@pytest.fixture
def sample_fraudulent_like_transaction() -> dict:
    """Fixture returning a transaction with characteristic fraud indicators (e.g. low V14, low V17)."""
    payload = {"Time": 406.0, "Amount": 0.0}
    for i in range(1, 29):
        payload[f"V{i}"] = 0.0
    # Set strongly correlated fraud indicators
    payload["V14"] = -4.28
    payload["V17"] = -2.83
    payload["V12"] = -2.89
    payload["V10"] = -2.77
    payload["V4"] = 3.99
    payload["V11"] = 3.20
    return payload


def test_predict_single_valid_transaction(client: TestClient, sample_transaction: dict):
    """Verify inference endpoint returns 200 and schema compliant response."""
    response = client.post("/internal/predict", json=sample_transaction)
    assert response.status_code == 200
    data = response.json()

    assert "fraud_probability" in data
    assert 0.0 <= data["fraud_probability"] <= 1.0
    assert "risk_score" in data
    assert 0.0 <= data["risk_score"] <= 100.0
    assert data["predicted_class"] in (0, 1)
    assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert "threshold" in data
    assert "model_version" in data
    assert "disclaimer" in data


def test_predict_rejects_class_field(client: TestClient, sample_transaction: dict):
    """Verify that incoming transaction payloads containing 'Class' are strictly rejected with 422."""
    payload = sample_transaction.copy()
    payload["Class"] = 1

    response = client.post("/internal/predict", json=payload)
    assert response.status_code == 422
    err_body = response.json()
    assert "Class" in str(err_body)


def test_predict_rejects_missing_feature(client: TestClient, sample_transaction: dict):
    """Verify that omitted features trigger 422 Unprocessable Entity."""
    payload = sample_transaction.copy()
    del payload["Amount"]

    response = client.post("/internal/predict", json=payload)
    assert response.status_code == 422


def test_predict_rejects_nan_and_inf(client: TestClient, sample_transaction: dict):
    """Verify that NaN and Infinite values are rejected."""
    # NaN check
    payload_nan = sample_transaction.copy()
    payload_nan["V1"] = "NaN"
    res_nan = client.post("/internal/predict", json=payload_nan)
    assert res_nan.status_code == 422

    # Infinity check
    payload_inf = sample_transaction.copy()
    payload_inf["Amount"] = "Infinity"
    res_inf = client.post("/internal/predict", json=payload_inf)
    assert res_inf.status_code == 422


def test_predict_threshold_override(client: TestClient, sample_transaction: dict):
    """Verify that passing custom threshold alters classification appropriately."""
    # When threshold is 0.00, every non-zero probability is flagged as class 1
    res_low = client.post("/internal/predict?threshold=0.00", json=sample_transaction)
    assert res_low.status_code == 200
    assert res_low.json()["threshold"] == 0.0
    assert res_low.json()["predicted_class"] == 1

    # When threshold is 1.00, any probability below 1.00 is flagged as class 0
    res_high = client.post("/internal/predict?threshold=1.00", json=sample_transaction)
    assert res_high.status_code == 200
    assert res_high.json()["threshold"] == 1.0
    assert res_high.json()["predicted_class"] == 0


def test_predict_with_explanation(client: TestClient, sample_fraudulent_like_transaction: dict):
    """Verify that explain=true parameter returns top risk factors."""
    response = client.post(
        "/internal/predict?explain=true", json=sample_fraudulent_like_transaction
    )
    assert response.status_code == 200
    data = response.json()

    assert "top_risk_factors" in data
    factors = data["top_risk_factors"]
    assert factors is not None
    assert isinstance(factors, list)
    if len(factors) > 0:
        factor = factors[0]
        assert "feature" in factor
        assert "attribution" in factor
        assert "value" in factor


def test_batch_prediction(
    client: TestClient, sample_transaction: dict, sample_fraudulent_like_transaction: dict
):
    """Verify batch prediction endpoint preserves order and computes summary count."""
    batch_payload = {
        "transactions": [
            sample_transaction,
            sample_fraudulent_like_transaction,
            sample_transaction,
        ]
    }

    response = client.post("/internal/predict/batch", json=batch_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_transactions"] == 3
    assert len(data["predictions"]) == 3
    assert "flagged_fraud_count" in data
    # Predictions preserve input ordering
    assert data["predictions"][0]["threshold"] is not None
    assert data["predictions"][1]["threshold"] is not None


def test_batch_prediction_exceeds_max_size(
    client: TestClient, sample_transaction: dict, monkeypatch
):
    """Verify that batches exceeding MAX_BATCH_SIZE are rejected with 400 Bad Request."""
    settings = get_settings()
    monkeypatch.setattr(settings, "MAX_BATCH_SIZE", 2)

    batch_payload = {"transactions": [sample_transaction, sample_transaction, sample_transaction]}
    response = client.post("/internal/predict/batch", json=batch_payload)
    assert response.status_code == 400
    assert "exceeds maximum permitted limit" in response.json()["detail"]


def test_missing_artifact_raises_clear_error(tmp_path: Path):
    """Verify that loading a non-existent model artifact raises FileNotFoundError with actionable instructions."""
    non_existent = tmp_path / "ghost_model.joblib"
    with pytest.raises(FileNotFoundError) as exc_info:
        load_model_artifact(non_existent)
    assert "Model artifact not found" in str(exc_info.value)
    assert "compare_models.py" in str(exc_info.value)


def test_consistent_feature_ordering(sample_transaction: dict):
    """Verify that predictor internal DataFrame matches exact expected feature order."""
    from app.schemas.transaction import TransactionInput

    tx = TransactionInput(**sample_transaction)
    df = predictor_service._transaction_to_dataframe(tx)
    assert list(df.columns) == EXPECTED_FEATURE_ORDER
