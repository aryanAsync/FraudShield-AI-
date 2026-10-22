"""Automated Tests for Health and Model-Info Endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.predictor import predictor_service


@pytest.fixture
def client():
    """Create test client with active application context."""
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint_healthy(client: TestClient):
    """Verify /health returns 200 and healthy status when model is loaded."""
    # Ensure model is loaded for this test
    if not predictor_service.is_ready():
        predictor_service.load_model()

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["model_version"] is not None
    assert data["model_type"] is not None


def test_health_endpoint_model_not_ready(client: TestClient, monkeypatch):
    """Verify /health returns 503 when model is not loaded."""
    monkeypatch.setattr(predictor_service, "is_ready", lambda: False)

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unavailable"
    assert data["model_loaded"] is False


def test_model_info_endpoint(client: TestClient):
    """Verify /internal/model-info returns expected non-sensitive metadata."""
    if not predictor_service.is_ready():
        predictor_service.load_model()

    response = client.get("/internal/model-info")
    assert response.status_code == 200
    data = response.json()

    assert "model_version" in data
    assert "model_type" in data
    assert "selected_threshold" in data
    assert "expected_features" in data
    assert len(data["expected_features"]) == 30  # Time + 28 PCA + Amount
    assert "risk_categories" in data

    # Verify no filesystem paths or environment secrets leaked
    dumped_str = str(data)
    assert "C:\\" not in dumped_str
    assert "Users" not in dumped_str
    assert "creditcard.csv" not in dumped_str or "/" not in dumped_str


def test_model_info_service_unavailable(client: TestClient, monkeypatch):
    """Verify /internal/model-info returns 503 if pipeline is unavailable."""
    monkeypatch.setattr(predictor_service, "is_ready", lambda: False)

    response = client.get("/internal/model-info")
    assert response.status_code == 503
