"""Automated integration, metric precision, and RBAC tests for Phase 4 Analytics APIs."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.prediction import Prediction
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.db.repositories.case_repository import CaseRepository
from app.db.repositories.transaction_repository import TransactionRepository
from app.db.repositories.user_repository import UserRepository


def make_user_token(user: User) -> str:
    """Helper to generate JWT bearer access token for a test user."""
    return create_access_token(
        subject=user.email,
        user_id=user.id,
        role=user.role,
        name=user.name,
    )


def seed_test_tx_and_prediction(
    db: Session,
    ref: str,
    amount: float = 100.0,
    fraud_probability: float = 0.1,
    risk_score: float = 10.0,
    predicted_class: int = 0,
    risk_level: str = "LOW",
    explanation: list[dict[str, Any]] | None = None,
    predicted_at: datetime | None = None,
    created_at: datetime | None = None,
) -> tuple[Transaction, Prediction]:
    """Helper to seed a transaction and its prediction record."""
    features = {f"V{i}": 0.01 * i for i in range(1, 29)}
    tx = Transaction(
        external_reference=ref,
        transaction_time=50.0,
        amount=amount,
        features=features,
        submitted_by="test_system",
    )
    if created_at is not None:
        tx.created_at = created_at
    db.add(tx)
    db.flush()

    pred = Prediction(
        transaction_id=tx.id,
        fraud_probability=fraud_probability,
        risk_score=risk_score,
        predicted_class=predicted_class,
        risk_level=risk_level,
        decision_threshold=0.56,
        model_version="fraud-model-v1",
        explanation=explanation,
    )
    if predicted_at is not None:
        pred.predicted_at = predicted_at
    db.add(pred)
    db.flush()
    db.commit()
    return tx, pred


# ---------------------------------------------------------------------------
# 1. Overview Analytics Tests
# ---------------------------------------------------------------------------


def test_analytics_overview_empty_database(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify overview endpoint returns valid zero metrics on an empty dataset."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.empty@fraudshield.test",
        name="Admin Empty",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    response = unauthenticated_client.get(
        "/api/v1/analytics/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["transactions"]["total_transactions"] == 0
    assert data["transactions"]["transactions_with_predictions"] == 0
    assert data["transactions"]["predicted_fraud_count"] == 0
    assert data["transactions"]["predicted_legitimate_count"] == 0
    assert data["transactions"]["predicted_fraud_percentage"] == 0.0

    assert data["predictions"]["total_predictions"] == 0
    assert data["risk"]["average_risk_score"] == 0.0
    assert data["risk"]["average_fraud_probability"] == 0.0
    assert data["risk"]["high_risk_transactions"] == 0

    assert data["cases"]["total_cases"] == 0
    assert data["cases"]["open"] == 0
    assert data["cases"]["unresolved"] == 0
    assert data["cases"]["resolved"] == 0


def test_analytics_overview_metrics_and_latest_prediction_rule(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify latest prediction selection rule: multiple predictions on 1 transaction use latest."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.overview@fraudshield.test",
        name="Admin Overview",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    now = datetime.now(UTC)

    # Tx 1: Evaluated twice.
    # Older prediction (2 hours ago): LOW risk, class 0
    # Newer prediction (1 hour ago): HIGH risk, class 1 -> MUST BE USED BY OVERVIEW
    tx1, _ = seed_test_tx_and_prediction(
        db_session,
        ref="TX-MULTI-01",
        fraud_probability=0.15,
        risk_score=15.0,
        predicted_class=0,
        risk_level="LOW",
        predicted_at=now - timedelta(hours=2),
    )
    pred_latest_tx1 = Prediction(
        transaction_id=tx1.id,
        fraud_probability=0.85,
        risk_score=85.0,
        predicted_class=1,
        risk_level="HIGH",
        decision_threshold=0.56,
        model_version="fraud-model-v1",
        predicted_at=now - timedelta(hours=1),
    )
    db_session.add(pred_latest_tx1)

    # Tx 2: Evaluated once, MEDIUM risk, class 0
    tx2, _ = seed_test_tx_and_prediction(
        db_session,
        ref="TX-SINGLE-02",
        fraud_probability=0.45,
        risk_score=45.0,
        predicted_class=0,
        risk_level="MEDIUM",
        predicted_at=now - timedelta(minutes=30),
    )

    # Tx 3: Transaction with NO predictions
    TransactionRepository.create(
        db=db_session,
        transaction_time=200.0,
        amount=50.0,
        features={f"V{i}": 0.0 for i in range(1, 29)},
        external_reference="TX-NOPRED-03",
        submitted_by="user",
    )

    # Cases: Tx 1 has OPEN case; Tx 2 has CONFIRMED_FRAUD case
    CaseRepository.create(db_session, transaction_id=tx1.id)
    c2 = CaseRepository.create(db_session, transaction_id=tx2.id)
    CaseRepository.update_status(c2, "IN_REVIEW")
    CaseRepository.update_status(c2, "CONFIRMED_FRAUD")
    db_session.commit()

    response = unauthenticated_client.get(
        "/api/v1/analytics/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Total distinct transactions: tx1, tx2, tx3 = 3
    assert data["transactions"]["total_transactions"] == 3
    # Transactions evaluated: tx1, tx2 = 2
    assert data["transactions"]["transactions_with_predictions"] == 2
    # Total predictions logged: 2 for tx1 + 1 for tx2 = 3
    assert data["predictions"]["total_predictions"] == 3

    # Latest predictions: tx1 is HIGH (class 1), tx2 is MEDIUM (class 0)
    assert data["transactions"]["predicted_fraud_count"] == 1
    assert data["transactions"]["predicted_legitimate_count"] == 1
    assert data["transactions"]["predicted_fraud_percentage"] == 50.0

    # Risk metrics: average of latest (85 + 45)/2 = 65.0
    assert data["risk"]["average_risk_score"] == 65.0
    # Average fraud probability: (0.85 + 0.45)/2 = 0.65
    assert data["risk"]["average_fraud_probability"] == 0.65
    assert data["risk"]["high_risk_transactions"] == 1
    assert data["risk"]["medium_risk_transactions"] == 1
    assert data["risk"]["low_risk_transactions"] == 0

    # Cases
    assert data["cases"]["total_cases"] == 2
    assert data["cases"]["open"] == 1
    assert data["cases"]["confirmed_fraud"] == 1
    assert data["cases"]["unresolved"] == 1
    assert data["cases"]["resolved"] == 1


def test_analytics_date_range_validation_bad_request(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify start_date > end_date returns 400 Bad Request on all analytics routes."""
    analyst = UserRepository.create(
        db=db_session,
        email="analyst.dates@fraudshield.test",
        name="Analyst Dates",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()
    token = make_user_token(analyst)

    future = (datetime.now(UTC) + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    past = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        f"/api/v1/analytics/overview?start_date={future}&end_date={past}",
        f"/api/v1/analytics/risk-distribution?start_date={future}&end_date={past}",
        f"/api/v1/analytics/trends?start_date={future}&end_date={past}",
        f"/api/v1/analytics/case-status-distribution?start_date={future}&end_date={past}",
        f"/api/v1/analytics/feature-importance?start_date={future}&end_date={past}",
    ]

    for ep in endpoints:
        res = unauthenticated_client.get(ep, headers=headers)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid date range" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 2. Risk Distribution Analytics Tests
# ---------------------------------------------------------------------------


def test_risk_distribution_breakdown(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify risk distribution breaks down LOW, MEDIUM, and HIGH tiers cleanly."""
    auditor = UserRepository.create(
        db=db_session,
        email="auditor.risk@fraudshield.test",
        name="Auditor Risk",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
    )
    db_session.commit()
    token = make_user_token(auditor)

    # 1 LOW risk tx
    seed_test_tx_and_prediction(db_session, "DIST-LOW", risk_level="LOW", predicted_class=0)
    # 2 MEDIUM risk txs
    seed_test_tx_and_prediction(db_session, "DIST-MED-1", risk_level="MEDIUM", predicted_class=0)
    seed_test_tx_and_prediction(db_session, "DIST-MED-2", risk_level="MEDIUM", predicted_class=0)
    # 1 HIGH risk tx
    seed_test_tx_and_prediction(db_session, "DIST-HIGH-1", risk_level="HIGH", predicted_class=1)

    response = unauthenticated_client.get(
        "/api/v1/analytics/risk-distribution",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_transactions"] == 4
    tier_map = {item["risk_level"]: item for item in data["items"]}

    assert tier_map["LOW"]["count"] == 1
    assert tier_map["LOW"]["percentage"] == 25.0

    assert tier_map["MEDIUM"]["count"] == 2
    assert tier_map["MEDIUM"]["percentage"] == 50.0

    assert tier_map["HIGH"]["count"] == 1
    assert tier_map["HIGH"]["percentage"] == 25.0

    assert data["classification"]["predicted_fraud_count"] == 1
    assert data["classification"]["predicted_fraud_percentage"] == 25.0
    assert data["classification"]["predicted_legitimate_count"] == 3
    assert data["classification"]["predicted_legitimate_percentage"] == 75.0


def test_risk_distribution_empty_dataset(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify risk distribution handles empty database gracefully."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.distempty@fraudshield.test",
        name="Admin DistEmpty",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    response = unauthenticated_client.get(
        "/api/v1/analytics/risk-distribution",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_transactions"] == 0
    assert len(data["items"]) == 3
    for it in data["items"]:
        assert it["count"] == 0
        assert it["percentage"] == 0.0


# ---------------------------------------------------------------------------
# 3. Time-Series Trends Tests
# ---------------------------------------------------------------------------


def test_trends_daily_aggregation(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify daily aggregation groups inference events chronologically."""
    analyst = UserRepository.create(
        db=db_session,
        email="analyst.trends@fraudshield.test",
        name="Analyst Trends",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()
    token = make_user_token(analyst)

    day1 = datetime(2026, 10, 10, 12, 0, 0, tzinfo=UTC)
    day2 = datetime(2026, 10, 11, 14, 0, 0, tzinfo=UTC)

    # Day 1: 2 predictions, 1 fraud
    seed_test_tx_and_prediction(
        db_session, "TREND-D1-1", risk_score=90.0, risk_level="HIGH", predicted_class=1, predicted_at=day1
    )
    seed_test_tx_and_prediction(
        db_session, "TREND-D1-2", risk_score=20.0, risk_level="LOW", predicted_class=0, predicted_at=day1
    )

    # Day 2: 1 prediction, legitimate
    seed_test_tx_and_prediction(
        db_session, "TREND-D2-1", risk_score=30.0, risk_level="LOW", predicted_class=0, predicted_at=day2
    )

    response = unauthenticated_client.get(
        "/api/v1/analytics/trends?interval=day",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["interval"] == "day"
    items = data["items"]
    assert len(items) >= 2

    # Verify chronological order
    timestamps = [it["timestamp"] for it in items]
    assert timestamps == sorted(timestamps)

    d1_bucket = next(it for it in items if "2026-10-10" in it["timestamp"])
    assert d1_bucket["prediction_count"] == 2
    assert d1_bucket["predicted_fraud_count"] == 1
    assert d1_bucket["predicted_legitimate_count"] == 1
    assert d1_bucket["high_risk_count"] == 1
    assert d1_bucket["average_risk_score"] == 55.0


def test_trends_invalid_interval_or_max_range_rejected(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify invalid interval returns 400 Bad Request and excessive range returns 400."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.trendval@fraudshield.test",
        name="Admin TrendVal",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Invalid interval
    res_inv = unauthenticated_client.get(
        "/api/v1/analytics/trends?interval=minute",
        headers=headers,
    )
    assert res_inv.status_code == status.HTTP_400_BAD_REQUEST

    # 2. Hourly range exceeding 30 days
    start = datetime(2026, 1, 1, tzinfo=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = datetime(2026, 2, 15, tzinfo=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    res_range = unauthenticated_client.get(
        f"/api/v1/analytics/trends?interval=hour&start_date={start}&end_date={end}",
        headers=headers,
    )
    assert res_range.status_code == status.HTTP_400_BAD_REQUEST
    assert "30 days" in res_range.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 4. Case Status Distribution & Resolution Time Tests
# ---------------------------------------------------------------------------


def test_case_status_distribution_and_resolution_metrics(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify case status breakdown and average resolution seconds calculation."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.casestat@fraudshield.test",
        name="Admin CaseStat",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    analyst = UserRepository.create(
        db=db_session,
        email="analyst.casestat@fraudshield.test",
        name="Analyst CaseStat",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()
    token = make_user_token(admin)

    tx1, _ = seed_test_tx_and_prediction(db_session, "CASE-STAT-01")
    tx2, _ = seed_test_tx_and_prediction(db_session, "CASE-STAT-02")
    tx3, _ = seed_test_tx_and_prediction(db_session, "CASE-STAT-03")

    now = datetime.now(UTC)

    # Case 1: OPEN, unassigned
    c1 = CaseRepository.create(db_session, transaction_id=tx1.id)
    c1.created_at = now - timedelta(hours=5)

    # Case 2: CONFIRMED_FRAUD, assigned to analyst, resolved 2 hours after creation
    c2 = CaseRepository.create(
        db_session,
        transaction_id=tx2.id,
        assigned_user_id=analyst.id,
        assigned_to=analyst.email,
    )
    CaseRepository.update_status(c2, "IN_REVIEW")
    CaseRepository.update_status(c2, "CONFIRMED_FRAUD")
    c2.created_at = now - timedelta(hours=4)
    c2.resolved_at = now - timedelta(hours=2)  # Duration: 2 hours = 7200s

    # Case 3: LEGITIMATE, resolved 1 hour after creation
    c3 = CaseRepository.create(db_session, transaction_id=tx3.id)
    CaseRepository.update_status(c3, "IN_REVIEW")
    CaseRepository.update_status(c3, "LEGITIMATE")
    c3.created_at = now - timedelta(hours=2)
    c3.resolved_at = now - timedelta(hours=1)  # Duration: 1 hour = 3600s

    db_session.commit()

    response = unauthenticated_client.get(
        "/api/v1/analytics/case-status-distribution",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_cases"] == 3
    status_map = {item["status"]: item for item in data["items"]}

    assert status_map["OPEN"]["count"] == 1
    assert status_map["CONFIRMED_FRAUD"]["count"] == 1
    assert status_map["LEGITIMATE"]["count"] == 1
    assert status_map["IN_REVIEW"]["count"] == 0
    assert status_map["CLOSED"]["count"] == 0

    summary = data["summary"]
    assert summary["assigned_count"] == 1
    assert summary["unassigned_count"] == 2
    assert summary["unresolved_count"] == 1
    assert summary["resolved_fraud_count"] == 1
    assert summary["resolved_legitimate_count"] == 1

    # Average resolution time: (7200 + 3600) / 2 = 5400 seconds
    assert summary["average_resolution_time_seconds"] is not None
    assert abs(summary["average_resolution_time_seconds"] - 5400.0) < 10.0


# ---------------------------------------------------------------------------
# 5. Feature Importance (SHAP Model Explanations Aggregation) Tests
# ---------------------------------------------------------------------------


def test_feature_importance_aggregation_success(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify aggregated SHAP feature importance ranks top absolute contributions."""
    analyst = UserRepository.create(
        db=db_session,
        email="analyst.shap@fraudshield.test",
        name="Analyst Shap",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()
    token = make_user_token(analyst)

    # Seed 2 predictions with explanations for HIGH risk
    expl1 = [
        {"feature": "V14", "attribution": -0.85, "value": -3.2},
        {"feature": "Amount", "attribution": 0.45, "value": 1500.0},
        {"feature": "V10", "attribution": -0.25, "value": -1.5},
    ]
    expl2 = [
        {"feature": "V14", "attribution": -0.75, "value": -2.8},
        {"feature": "Amount", "attribution": 0.55, "value": 2200.0},
        {"feature": "V4", "attribution": 0.60, "value": 2.1},
    ]

    seed_test_tx_and_prediction(
        db_session, "SHAP-TX-01", risk_level="HIGH", predicted_class=1, explanation=expl1
    )
    seed_test_tx_and_prediction(
        db_session, "SHAP-TX-02", risk_level="HIGH", predicted_class=1, explanation=expl2
    )

    response = unauthenticated_client.get(
        "/api/v1/analytics/feature-importance?risk_level=HIGH&limit=3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["sample_size"] == 2
    assert data["target_risk_level"] == "HIGH"
    assert "anonymized pca" in data["disclaimer"].lower()

    features = data["features"]
    assert len(features) == 3

    # Rank 1: V14 (| -0.85 | + | -0.75 |)/2 = 0.80
    assert features[0]["rank"] == 1
    assert features[0]["feature"] == "V14"
    assert features[0]["mean_absolute_attribution"] == 0.80
    assert features[0]["sample_count"] == 2

    # Rank 2: V4 (|0.60| / 1) = 0.60
    assert features[1]["rank"] == 2
    assert features[1]["feature"] == "V4"
    assert features[1]["mean_absolute_attribution"] == 0.60

    # Rank 3: Amount (|0.45| + |0.55|)/2 = 0.50
    assert features[2]["rank"] == 3
    assert features[2]["feature"] == "Amount"
    assert features[2]["mean_absolute_attribution"] == 0.50


def test_feature_importance_missing_explanations_graceful_fallback(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify feature importance gracefully returns empty list if explanations are absent."""
    auditor = UserRepository.create(
        db=db_session,
        email="auditor.noexpl@fraudshield.test",
        name="Auditor NoExpl",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
    )
    db_session.commit()
    token = make_user_token(auditor)

    # Seed without explanation
    seed_test_tx_and_prediction(db_session, "NO-EXPL-TX", risk_level="HIGH", explanation=None)

    response = unauthenticated_client.get(
        "/api/v1/analytics/feature-importance?risk_level=HIGH",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["sample_size"] == 0
    assert data["features"] == []


def test_feature_importance_invalid_risk_level_rejected(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify invalid risk level returns 400 Bad Request."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.badrisk@fraudshield.test",
        name="Admin BadRisk",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    response = unauthenticated_client.get(
        "/api/v1/analytics/feature-importance?risk_level=EXTREME",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "invalid risk_level" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 6. Authentication and RBAC Role Access Tests
# ---------------------------------------------------------------------------


def test_analytics_rbac_all_authenticated_roles_allowed(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify ADMIN, ANALYST, and AUDITOR can all access analytics read endpoints."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.rbac@fraudshield.test",
        name="Admin RBAC",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    analyst = UserRepository.create(
        db=db_session,
        email="analyst.rbac@fraudshield.test",
        name="Analyst RBAC",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    auditor = UserRepository.create(
        db=db_session,
        email="auditor.rbac@fraudshield.test",
        name="Auditor RBAC",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
    )
    db_session.commit()

    tokens = [
        make_user_token(admin),
        make_user_token(analyst),
        make_user_token(auditor),
    ]

    for tok in tokens:
        headers = {"Authorization": f"Bearer {tok}"}
        res_overview = unauthenticated_client.get("/api/v1/analytics/overview", headers=headers)
        assert res_overview.status_code == status.HTTP_200_OK

        res_risk = unauthenticated_client.get("/api/v1/analytics/risk-distribution", headers=headers)
        assert res_risk.status_code == status.HTTP_200_OK

        res_trends = unauthenticated_client.get("/api/v1/analytics/trends", headers=headers)
        assert res_trends.status_code == status.HTTP_200_OK

        res_cases = unauthenticated_client.get("/api/v1/analytics/case-status-distribution", headers=headers)
        assert res_cases.status_code == status.HTTP_200_OK

        res_shap = unauthenticated_client.get("/api/v1/analytics/feature-importance", headers=headers)
        assert res_shap.status_code == status.HTTP_200_OK


def test_analytics_unauthenticated_requests_return_401(
    unauthenticated_client: TestClient,
):
    """Verify unauthenticated requests to all analytics endpoints are rejected with 401."""
    routes = [
        "/api/v1/analytics/overview",
        "/api/v1/analytics/risk-distribution",
        "/api/v1/analytics/trends",
        "/api/v1/analytics/case-status-distribution",
        "/api/v1/analytics/feature-importance",
    ]
    for r in routes:
        res = unauthenticated_client.get(r)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_analytics_deactivated_user_forbidden(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify deactivated user account receives 403 Forbidden across analytics."""
    user = UserRepository.create(
        db=db_session,
        email="deact.analytics@fraudshield.test",
        name="Deactivated Analyst",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
        is_active=False,
    )
    db_session.commit()
    token = make_user_token(user)

    response = unauthenticated_client.get(
        "/api/v1/analytics/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "deactivated" in response.json()["detail"].lower()


def test_overview_date_filtering_precision(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify start_date and end_date filters precisely bound overview transaction metrics."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.dateprec@fraudshield.test",
        name="Admin DatePrec",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    t_in_range = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
    t_out_range = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

    # 1 Tx inside range
    seed_test_tx_and_prediction(
        db_session,
        ref="TX-IN-RANGE",
        fraud_probability=0.9,
        risk_score=90.0,
        predicted_class=1,
        risk_level="HIGH",
        predicted_at=t_in_range,
        created_at=t_in_range,
    )
    # 1 Tx outside range
    seed_test_tx_and_prediction(
        db_session,
        ref="TX-OUT-RANGE",
        fraud_probability=0.1,
        risk_score=10.0,
        predicted_class=0,
        risk_level="LOW",
        predicted_at=t_out_range,
        created_at=t_out_range,
    )

    start = "2026-06-01T00:00:00Z"
    end = "2026-06-30T23:59:59Z"

    response = unauthenticated_client.get(
        f"/api/v1/analytics/overview?start_date={start}&end_date={end}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["transactions"]["total_transactions"] == 1
    assert data["transactions"]["transactions_with_predictions"] == 1
    assert data["transactions"]["predicted_fraud_count"] == 1
    assert data["risk"]["high_risk_transactions"] == 1
    assert data["risk"]["low_risk_transactions"] == 0


def test_trends_hourly_aggregation(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify hourly aggregation produces bucketed trends over an hour interval."""
    analyst = UserRepository.create(
        db=db_session,
        email="analyst.hourly@fraudshield.test",
        name="Analyst Hourly",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()
    token = make_user_token(analyst)

    h1 = datetime(2026, 7, 10, 10, 15, 0, tzinfo=UTC)
    h2 = datetime(2026, 7, 10, 11, 45, 0, tzinfo=UTC)

    seed_test_tx_and_prediction(db_session, "TX-H1", predicted_at=h1, risk_score=75.0, risk_level="HIGH", predicted_class=1)
    seed_test_tx_and_prediction(db_session, "TX-H2", predicted_at=h2, risk_score=25.0, risk_level="LOW", predicted_class=0)

    start = "2026-07-10T00:00:00Z"
    end = "2026-07-10T23:59:59Z"

    response = unauthenticated_client.get(
        f"/api/v1/analytics/trends?interval=hour&start_date={start}&end_date={end}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["interval"] == "hour"
    assert len(data["items"]) >= 2


def test_case_status_distribution_empty_database(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify case status distribution endpoint handles empty database gracefully."""
    auditor = UserRepository.create(
        db=db_session,
        email="auditor.casedistempty@fraudshield.test",
        name="Auditor CaseDistEmpty",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
    )
    db_session.commit()
    token = make_user_token(auditor)

    response = unauthenticated_client.get(
        "/api/v1/analytics/case-status-distribution",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_cases"] == 0
    assert len(data["items"]) == 5
    for it in data["items"]:
        assert it["count"] == 0
        assert it["percentage"] == 0.0
    assert data["summary"]["average_resolution_time_seconds"] is None


# ---------------------------------------------------------------------------
# 7. Audit Verification & Regression Tests (Phase 4 Final Audit)
# ---------------------------------------------------------------------------


def test_audit_1_risk_distribution_latest_prediction_deduplication(
    unauthenticated_client: TestClient, db_session: Session
):
    """Audit 1: Verify transaction with multiple predictions is counted exactly ONCE in risk distribution."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.audit1@fraudshield.test",
        name="Admin Audit1",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)
    now = datetime.now(UTC)

    # Tx with 3 predictions:
    # 1. Oldest (3h ago): HIGH risk, class 1
    # 2. Middle (2h ago): MEDIUM risk, class 0
    # 3. Latest (1h ago): LOW risk, class 0 (MUST BE USED)
    tx, _ = seed_test_tx_and_prediction(
        db_session,
        ref="TX-AUDIT1-MULTI",
        fraud_probability=0.90,
        risk_score=90.0,
        predicted_class=1,
        risk_level="HIGH",
        predicted_at=now - timedelta(hours=3),
    )
    pred_mid = Prediction(
        transaction_id=tx.id,
        fraud_probability=0.45,
        risk_score=45.0,
        predicted_class=0,
        risk_level="MEDIUM",
        decision_threshold=0.56,
        model_version="fraud-model-v1",
        predicted_at=now - timedelta(hours=2),
    )
    pred_latest = Prediction(
        transaction_id=tx.id,
        fraud_probability=0.10,
        risk_score=10.0,
        predicted_class=0,
        risk_level="LOW",
        decision_threshold=0.56,
        model_version="fraud-model-v1",
        predicted_at=now - timedelta(hours=1),
    )
    db_session.add(pred_mid)
    db_session.add(pred_latest)
    db_session.commit()

    response = unauthenticated_client.get(
        "/api/v1/analytics/risk-distribution",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Must count exactly 1 transaction total, NOT 3!
    assert data["total_transactions"] == 1
    tier_map = {item["risk_level"]: item for item in data["items"]}

    # Only latest prediction (LOW) should be counted
    assert tier_map["LOW"]["count"] == 1
    assert tier_map["LOW"]["percentage"] == 100.0
    assert tier_map["MEDIUM"]["count"] == 0
    assert tier_map["HIGH"]["count"] == 0
    assert data["classification"]["predicted_fraud_count"] == 0
    assert data["classification"]["predicted_legitimate_count"] == 1


def test_audit_2_timezone_offsets_and_boundary_timestamps(
    unauthenticated_client: TestClient, db_session: Session
):
    """Audit 2: Test timezone offset conversion (e.g. +05:30) and inclusive boundary filtering."""
    analyst = UserRepository.create(
        db=db_session,
        email="analyst.audit2@fraudshield.test",
        name="Analyst Audit2",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()
    token = make_user_token(analyst)

    # Seed events at specific UTC times
    # 2026-10-15 12:30:00 UTC = 2026-10-15 18:00:00 +05:30
    t_utc = datetime(2026, 10, 15, 12, 30, 0, tzinfo=UTC)
    seed_test_tx_and_prediction(
        db_session,
        ref="TX-TZ-01",
        predicted_at=t_utc,
        created_at=t_utc,
        risk_level="HIGH",
        predicted_class=1,
    )

    # 1. Query with IST offset (+05:30) covering 18:00:00 IST
    start_ist = "2026-10-15T17:00:00%2B05:30"
    end_ist = "2026-10-15T19:00:00%2B05:30"
    res1 = unauthenticated_client.get(
        f"/api/v1/analytics/overview?start_date={start_ist}&end_date={end_ist}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == status.HTTP_200_OK
    assert res1.json()["transactions"]["total_transactions"] == 1

    # 2. Query with boundary timestamp exactly equal to predicted_at (inclusive <= test)
    exact_ts = "2026-10-15T12:30:00Z"
    res_exact = unauthenticated_client.get(
        f"/api/v1/analytics/overview?start_date={exact_ts}&end_date={exact_ts}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_exact.status_code == status.HTTP_200_OK
    assert res_exact.json()["transactions"]["total_transactions"] == 1

    # 3. Query just outside boundary
    before_ts = "2026-10-15T12:00:00Z"
    res_outside = unauthenticated_client.get(
        f"/api/v1/analytics/overview?start_date={before_ts}&end_date={before_ts}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_outside.status_code == status.HTTP_200_OK
    assert res_outside.json()["transactions"]["total_transactions"] == 0


def test_audit_2_mixed_timezone_and_naive_inputs_handled_safely(
    unauthenticated_client: TestClient, db_session: Session
):
    """Audit 2: Ensure mixing naive and timezone-aware parameters does not crash with TypeError."""
    auditor = UserRepository.create(
        db=db_session,
        email="auditor.audit2@fraudshield.test",
        name="Auditor Audit2",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
    )
    db_session.commit()
    token = make_user_token(auditor)

    # Naive start, aware end (URL encoded)
    start_naive = "2026-10-01T00:00:00"
    end_aware = "2026-10-31T23:59:59Z"
    res = unauthenticated_client.get(
        f"/api/v1/analytics/overview?start_date={start_naive}&end_date={end_aware}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == status.HTTP_200_OK

    # Aware start > naive end (triggers 400 without TypeError crash)
    start_future = "2026-12-01T00:00:00Z"
    end_past = "2026-01-01T00:00:00"
    res_bad = unauthenticated_client.get(
        f"/api/v1/analytics/overview?start_date={start_future}&end_date={end_past}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_bad.status_code == status.HTTP_400_BAD_REQUEST


def test_audit_3_closed_case_adjudication_limitation_and_resolution_time(
    unauthenticated_client: TestClient, db_session: Session
):
    """Audit 3: Verify closed cases count under 'closed' and resolution time uses valid resolved_at."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.audit3@fraudshield.test",
        name="Admin Audit3",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)
    now = datetime.now(UTC)

    tx1, _ = seed_test_tx_and_prediction(db_session, "CASE-ADJ-01")
    tx2, _ = seed_test_tx_and_prediction(db_session, "CASE-ADJ-02")

    # Case 1: CONFIRMED_FRAUD, then transitioned to CLOSED
    # created 3h ago, confirmed 2h ago, closed 1h ago
    c1 = CaseRepository.create(db_session, transaction_id=tx1.id)
    c1.created_at = now - timedelta(hours=3)
    CaseRepository.update_status(c1, "IN_REVIEW")
    CaseRepository.update_status(c1, "CONFIRMED_FRAUD")
    c1.resolved_at = now - timedelta(hours=2)
    CaseRepository.update_status(c1, "CLOSED")

    # Case 2: OPEN, unresolved (resolved_at is NULL)
    c2 = CaseRepository.create(db_session, transaction_id=tx2.id)
    c2.created_at = now - timedelta(hours=1)
    db_session.commit()

    response = unauthenticated_client.get(
        "/api/v1/analytics/case-status-distribution",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_cases"] == 2
    status_map = {it["status"]: it for it in data["items"]}

    # Case 1 is now in CLOSED status; confirmed_fraud only tracks currently open confirmed cases
    assert status_map["CLOSED"]["count"] == 1
    assert status_map["CONFIRMED_FRAUD"]["count"] == 0
    assert status_map["OPEN"]["count"] == 1

    # Resolution time: Only Case 1 had resolved_at (duration = 1 hour = 3600 seconds)
    # Case 2 has resolved_at = NULL and must be excluded from average
    avg_sec = data["summary"]["average_resolution_time_seconds"]
    assert avg_sec is not None
    assert abs(avg_sec - 3600.0) < 5.0


def test_audit_4_feature_importance_malformed_and_edge_case_explanations(
    unauthenticated_client: TestClient, db_session: Session
):
    """Audit 4: Verify feature importance gracefully handles missing, malformed, and non-numeric attributions."""
    analyst = UserRepository.create(
        db=db_session,
        email="analyst.audit4@fraudshield.test",
        name="Analyst Audit4",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()
    token = make_user_token(analyst)

    # 1. Valid explanation
    valid_expl = [{"feature": "V14", "attribution": -0.8, "value": -2.5}]
    seed_test_tx_and_prediction(db_session, "FEAT-VAL", risk_level="HIGH", explanation=valid_expl)

    # 2. Malformed explanations: string attribution, non-dict item, missing keys, empty dict
    malformed_expl = [
        {"feature": "V10", "attribution": "NOT_A_FLOAT", "value": 1.0},
        "not_even_a_dict",
        {"only_feature": "V12"},
        {"feature": "V17", "attribution": float("nan")},
        {"feature": "V14", "attribution": -0.4, "value": -1.2},  # Valid item inside mixed list
    ]
    seed_test_tx_and_prediction(db_session, "FEAT-MAL", risk_level="HIGH", explanation=malformed_expl)

    # 3. Empty list explanation
    seed_test_tx_and_prediction(db_session, "FEAT-EMPTY", risk_level="HIGH", explanation=[])

    response = unauthenticated_client.get(
        "/api/v1/analytics/feature-importance?risk_level=HIGH",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Evaluated sample_size = 2 (valid_expl + malformed_expl with valid items)
    assert data["sample_size"] == 2
    feats = {f["feature"]: f for f in data["features"]}

    # V14 was present in valid_expl (| -0.8 |) and in malformed_expl (| -0.4 |) -> avg = 0.60
    assert "V14" in feats
    assert feats["V14"]["mean_absolute_attribution"] == 0.60
    assert feats["V14"]["sample_count"] == 2


