"""Integration Tests for Transaction APIs, Persistence, and Scoring Flow."""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.repositories.transaction_repository import TransactionRepository


def test_score_and_persist_valid_transaction(client: TestClient, sample_transaction: dict):
    """Verify POST /api/v1/transactions/score persists transaction and prediction atomically."""
    payload = sample_transaction.copy()
    payload["external_reference"] = "TXN-TEST-1001"
    payload["submitted_by"] = "test_analyst"

    response = client.post("/api/v1/transactions/score", json=payload)
    assert response.status_code == 201
    data = response.json()

    # Validate top-level transaction fields
    assert "transaction_id" in data
    assert data["transaction_id"] > 0
    assert data["external_reference"] == "TXN-TEST-1001"
    assert data["transaction_time"] == sample_transaction["Time"]
    assert data["amount"] == sample_transaction["Amount"]
    assert data["submitted_by"] == "test_analyst"
    assert "created_at" in data

    # Validate embedded prediction record
    pred = data["prediction"]
    assert pred["transaction_id"] == data["transaction_id"]
    assert 0.0 <= pred["fraud_probability"] <= 1.0
    assert 0.0 <= pred["risk_score"] <= 100.0
    assert pred["predicted_class"] in (0, 1)
    assert pred["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert pred["model_version"] is not None
    assert "predicted_at" in pred


def test_score_with_explanation(client: TestClient, sample_fraudulent_like_transaction: dict):
    """Verify scoring with explain=true persists and returns SHAP feature attributions."""
    payload = sample_fraudulent_like_transaction.copy()
    payload["explain"] = True
    payload["external_reference"] = "TXN-EXPLAIN-001"

    response = client.post("/api/v1/transactions/score", json=payload)
    assert response.status_code == 201
    data = response.json()

    pred = data["prediction"]
    assert pred["explanation"] is not None
    assert isinstance(pred["explanation"], list)
    if len(pred["explanation"]) > 0:
        factor = pred["explanation"][0]
        assert "feature" in factor
        assert "attribution" in factor
        assert "value" in factor


def test_score_threshold_override(client: TestClient, sample_transaction: dict):
    """Verify passing custom threshold alters classification in scoring endpoint."""
    payload = sample_transaction.copy()
    payload["threshold"] = 0.00
    payload["external_reference"] = "TXN-THRESH-LOW"

    res_low = client.post("/api/v1/transactions/score", json=payload)
    assert res_low.status_code == 201
    assert res_low.json()["prediction"]["predicted_class"] == 1
    assert res_low.json()["prediction"]["decision_threshold"] == 0.0

    payload_high = sample_transaction.copy()
    payload_high["threshold"] = 1.00
    payload_high["external_reference"] = "TXN-THRESH-HIGH"

    res_high = client.post("/api/v1/transactions/score", json=payload_high)
    assert res_high.status_code == 201
    assert res_high.json()["prediction"]["predicted_class"] == 0
    assert res_high.json()["prediction"]["decision_threshold"] == 1.0


def test_score_rejects_duplicate_external_reference(client: TestClient, sample_transaction: dict):
    """Verify duplicate external reference returns 409 Conflict."""
    payload = sample_transaction.copy()
    payload["external_reference"] = "TXN-DUPLICATE-ID"

    res1 = client.post("/api/v1/transactions/score", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/transactions/score", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_score_rejects_class_and_extra_fields(client: TestClient, sample_transaction: dict):
    """Verify input payload containing 'Class' or arbitrary fields returns 422."""
    payload_class = sample_transaction.copy()
    payload_class["Class"] = 1

    res = client.post("/api/v1/transactions/score", json=payload_class)
    assert res.status_code == 422

    payload_extra = sample_transaction.copy()
    payload_extra["card_number"] = "4111222233334444"
    res_extra = client.post("/api/v1/transactions/score", json=payload_extra)
    assert res_extra.status_code == 422


def test_score_rejects_nan_and_inf(client: TestClient, sample_transaction: dict):
    """Verify NaN and Infinity in features are rejected with 422."""
    payload_nan = sample_transaction.copy()
    payload_nan["V2"] = "NaN"
    assert client.post("/api/v1/transactions/score", json=payload_nan).status_code == 422

    payload_inf = sample_transaction.copy()
    payload_inf["Amount"] = "Infinity"
    assert client.post("/api/v1/transactions/score", json=payload_inf).status_code == 422


def test_score_rollback_on_database_failure(
    client: TestClient, sample_transaction: dict, db_session: Session
):
    """Verify transaction rolls back cleanly if database persistence encounters an error."""
    payload = sample_transaction.copy()
    payload["external_reference"] = "TXN-ROLLBACK-TEST"

    with patch(
        "app.api.routes.transactions.PredictionRepository.create",
        side_effect=RuntimeError("Simulated DB connection failure"),
    ):
        res = client.post("/api/v1/transactions/score", json=payload)
        assert res.status_code == 500
        assert "Failed to persist" in res.json()["detail"]

    # Verify no orphan transaction was persisted
    orphaned = TransactionRepository.get_by_external_reference(db_session, "TXN-ROLLBACK-TEST")
    assert orphaned is None


def test_get_transaction_details_success_and_404(client: TestClient, sample_transaction: dict):
    """Verify GET /api/v1/transactions/{id} retrieves detail and returns 404 for missing IDs."""
    payload = sample_transaction.copy()
    payload["external_reference"] = "TXN-DETAIL-001"

    score_res = client.post("/api/v1/transactions/score", json=payload)
    tx_id = score_res.json()["transaction_id"]

    # Valid ID
    detail_res = client.get(f"/api/v1/transactions/{tx_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == tx_id
    assert detail["external_reference"] == "TXN-DETAIL-001"
    assert "features" in detail
    assert "V1" in detail["features"]
    assert detail["latest_prediction"] is not None
    assert detail["predictions_count"] >= 1

    # Nonexistent ID
    res_404 = client.get("/api/v1/transactions/99999999")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()


def test_get_transaction_predictions_history(client: TestClient, sample_transaction: dict):
    """Verify GET /api/v1/transactions/{id}/predictions retrieves history."""
    payload = sample_transaction.copy()
    payload["external_reference"] = "TXN-HIST-001"

    score_res = client.post("/api/v1/transactions/score", json=payload)
    tx_id = score_res.json()["transaction_id"]

    hist_res = client.get(f"/api/v1/transactions/{tx_id}/predictions")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["transaction_id"] == tx_id
    assert hist["total_evaluations"] >= 1
    assert len(hist["predictions"]) >= 1

    # Nonexistent ID
    res_404 = client.get("/api/v1/transactions/99999999/predictions")
    assert res_404.status_code == 404


def test_list_transactions_pagination_and_filtering(
    client: TestClient, sample_transaction: dict, sample_fraudulent_like_transaction: dict
):
    """Verify GET /api/v1/transactions with pagination, sorting, and filters."""
    # Seed 1 legitimate transaction
    tx_legit = sample_transaction.copy()
    tx_legit["external_reference"] = "TXN-LIST-LEGIT"
    tx_legit["Amount"] = 15.0
    client.post("/api/v1/transactions/score", json=tx_legit)

    # Seed 1 high-risk transaction
    tx_fraud = sample_fraudulent_like_transaction.copy()
    tx_fraud["external_reference"] = "TXN-LIST-FRAUD"
    tx_fraud["Amount"] = 999.0
    client.post("/api/v1/transactions/score", json=tx_fraud)

    # 1. Unfiltered paginated list
    res = client.get("/api/v1/transactions?page=1&page_size=10&sort_by=amount&sort_order=asc")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2
    assert data["page"] == 1
    assert data["page_size"] == 10

    # 2. Filter by risk_level=HIGH
    res_high = client.get("/api/v1/transactions?risk_level=HIGH")
    assert res_high.status_code == 200
    for item in res_high.json()["items"]:
        assert item["latest_prediction"]["risk_level"] == "HIGH"

    # 3. Filter by predicted_class=1
    res_class1 = client.get("/api/v1/transactions?predicted_class=1")
    assert res_class1.status_code == 200
    for item in res_class1.json()["items"]:
        assert item["latest_prediction"]["predicted_class"] == 1
