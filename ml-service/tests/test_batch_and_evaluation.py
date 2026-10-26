"""Tests for batch scoring, on-demand SHAP explanations, and model evaluation endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.models.user import User


def test_batch_score_transactions_success(
    client: TestClient,
    sample_transaction: dict,
    sample_fraudulent_like_transaction: dict,
):
    """Test batch scoring of multiple valid transactions with atomic persistence."""
    batch_payload = {
        "transactions": [
            sample_transaction,
            sample_fraudulent_like_transaction,
        ],
        "threshold": 0.56,
        "explain": False,
    }

    response = client.post("/api/v1/transactions/batch-score", json=batch_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["total_received"] == 2
    assert data["persisted_count"] == 2
    assert len(data["created_transaction_ids"]) == 2
    assert data["low_risk_count"] + data["medium_risk_count"] + data["high_risk_count"] == 2

    # Verify that the transactions appear in the transaction list
    list_resp = client.get("/api/v1/transactions")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 2


def test_batch_score_transactions_validation_limits(client: TestClient, sample_transaction: dict):
    """Test batch scoring rejects batches with negative amount or forbidden ground-truth fields."""
    # Negative amount
    invalid_tx = dict(sample_transaction)
    invalid_tx["Amount"] = -10.0
    bad_payload = {"transactions": [invalid_tx]}
    resp = client.post("/api/v1/transactions/batch-score", json=bad_payload)
    assert resp.status_code == 422

    # Forbidden 'Class' field (ground-truth must not be passed)
    tx_with_class = dict(sample_transaction)
    tx_with_class["Class"] = 0
    bad_class_payload = {"transactions": [tx_with_class]}
    resp2 = client.post("/api/v1/transactions/batch-score", json=bad_class_payload)
    assert resp2.status_code == 422


def test_batch_score_role_authorization(unauthenticated_client: TestClient, db_session, sample_transaction: dict):
    """Test that batch scoring enforces RBAC: Auditor role is forbidden."""
    auditor = User(
        email="auditor_test@fraudshield.ai",
        name="Auditor User",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
        is_active=True,
    )
    db_session.add(auditor)
    db_session.commit()

    token = create_access_token(subject=auditor.email, user_id=auditor.id, role=auditor.role)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"transactions": [sample_transaction]}
    resp = unauthenticated_client.post("/api/v1/transactions/batch-score", json=payload, headers=headers)
    assert resp.status_code == 403


def test_on_demand_explain_transaction(
    client: TestClient,
    sample_fraudulent_like_transaction: dict,
):
    """Test on-demand SHAP computation for a stored transaction."""
    # First score without explanation
    score_resp = client.post("/api/v1/transactions/score", json={**sample_fraudulent_like_transaction, "explain": False})
    assert score_resp.status_code == 201
    tx_id = score_resp.json()["transaction_id"]

    # Call on-demand explain
    explain_resp = client.post(f"/api/v1/transactions/{tx_id}/explain?top_k=5")
    assert explain_resp.status_code == 200
    attributions = explain_resp.json()
    assert isinstance(attributions, list)
    assert len(attributions) > 0
    assert "feature" in attributions[0]
    assert "attribution" in attributions[0]
    assert "value" in attributions[0]

    # Verify that detail view now contains the explanation
    detail_resp = client.get(f"/api/v1/transactions/{tx_id}")
    assert detail_resp.status_code == 200
    pred = detail_resp.json()["latest_prediction"]
    assert pred["explanation"] is not None
    assert len(pred["explanation"]) >= len(attributions)


def test_model_evaluation_endpoint(client: TestClient):
    """Test public model evaluation endpoint returns verified Random Forest and Logistic Regression metrics."""
    response = client.get("/api/v1/models/evaluation")
    assert response.status_code == 200
    data = response.json()

    # Deployed model: Random Forest
    deployed = data["deployed_model"]
    assert deployed["model_name"] == "RandomForest"
    assert deployed["model_version"] == "fraud-model-v1"
    assert deployed["is_deployed"] is True
    assert deployed["optimal_threshold"] == 0.56

    test_metrics = deployed["test_metrics"]
    assert test_metrics is not None
    assert test_metrics["precision"] == 0.8837
    assert test_metrics["recall"] == 0.7308
    assert test_metrics["f1_score"] == 0.8000
    assert test_metrics["pr_auc"] == 0.7661
    assert test_metrics["roc_auc"] == 0.9611
    assert test_metrics["confusion_matrix"]["true_negatives"] == 42665
    assert test_metrics["confusion_matrix"]["false_positives"] == 5
    assert test_metrics["confusion_matrix"]["false_negatives"] == 14
    assert test_metrics["confusion_matrix"]["true_positives"] == 38

    # Baseline model: Logistic Regression (Not Deployed)
    baseline = data["baseline_model"]
    assert baseline["model_name"] == "LogisticRegression"
    assert baseline["is_deployed"] is False
    assert baseline["optimal_threshold"] == 0.95
    assert baseline["test_metrics"] is None  # Must not claim test evaluation
    assert baseline["validation_metrics"]["precision"] == 0.3551
    assert baseline["validation_metrics"]["recall"] == 0.8750
    assert baseline["validation_metrics"]["f1_score"] == 0.5052

    # Comprehensive candidate model evaluation list
    candidates = data.get("candidate_models", [])
    candidate_names = [c["model_name"] for c in candidates]
    assert "RandomForest" in candidate_names
    assert "XGBoost" in candidate_names
    assert "DecisionTree" in candidate_names
    assert "KNN" in candidate_names
    assert "Clustering" in candidate_names
    assert "NaiveBayes" in candidate_names
    assert "LogisticRegression" in candidate_names
    assert len(candidate_names) >= 7
