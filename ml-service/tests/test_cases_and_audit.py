"""Unit and Integration Tests for Phase 3: Investigation Cases, Notes, and Audit Trail APIs."""

from datetime import UTC, datetime, timedelta

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.db.repositories.case_repository import CaseRepository
from app.db.repositories.prediction_repository import PredictionRepository
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


def create_test_transaction(db: Session, ref: str = "CASE-TX-001") -> int:
    """Helper to create a standard scored transaction for case tests."""
    features = {f"V{i}": 0.05 * i for i in range(1, 29)}
    tx = TransactionRepository.create(
        db=db,
        transaction_time=100.0,
        amount=125.50,
        features=features,
        external_reference=ref,
        submitted_by="system",
    )
    db.flush()

    PredictionRepository.create(
        db=db,
        transaction_id=tx.id,
        fraud_probability=0.82,
        risk_score=82.0,
        predicted_class=1,
        risk_level="HIGH",
        decision_threshold=0.56,
        model_version="fraud-model-v1",
    )
    db.commit()
    return tx.id


# ---------------------------------------------------------------------------
# 1. Case Creation Tests
# ---------------------------------------------------------------------------


def test_admin_create_case_success(unauthenticated_client: TestClient, db_session: Session):
    """Verify Admin can open an investigation case and atomic audit event is recorded."""
    tx_id = create_test_transaction(db_session, "ADMIN-OPEN-01")
    admin = UserRepository.create(
        db=db_session,
        email="case.admin@fraudshield.test",
        name="Case Admin",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    response = unauthenticated_client.post(
        "/api/v1/cases",
        json={"transaction_id": tx_id, "description": "Flagged by random forest model."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["transaction_id"] == tx_id
    assert data["status"] == "OPEN"
    assert data["description"] == "Flagged by random forest model."
    assert data["assigned_user_id"] is None
    assert data["transaction"]["amount"] == 125.50
    assert data["latest_prediction"]["risk_score"] == 82.0

    # Verify audit event
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "CASE_CREATED", AuditLog.entity_id == str(data["id"]))
        .first()
    )
    assert audit is not None
    assert audit.actor_id == str(admin.id)
    assert audit.details["transaction_id"] == tx_id


def test_analyst_create_case_success(unauthenticated_client: TestClient, db_session: Session):
    """Verify Analyst can open an investigation case."""
    tx_id = create_test_transaction(db_session, "ANALYST-OPEN-01")
    analyst = UserRepository.create(
        db=db_session,
        email="case.analyst1@fraudshield.test",
        name="Case Analyst 1",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()
    token = make_user_token(analyst)

    response = unauthenticated_client.post(
        "/api/v1/cases",
        json={"transaction_id": tx_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["status"] == "OPEN"


def test_auditor_create_case_forbidden(unauthenticated_client: TestClient, db_session: Session):
    """Verify Auditor role is denied (403 Forbidden) from creating cases."""
    tx_id = create_test_transaction(db_session, "AUDITOR-DENY-01")
    auditor = UserRepository.create(
        db=db_session,
        email="case.auditor@fraudshield.test",
        name="Case Auditor",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
    )
    db_session.commit()
    token = make_user_token(auditor)

    response = unauthenticated_client.post(
        "/api/v1/cases",
        json={"transaction_id": tx_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_case_nonexistent_transaction_returns_404(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify opening a case for nonexistent transaction returns 404."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.404@fraudshield.test",
        name="Admin 404",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    response = unauthenticated_client.post(
        "/api/v1/cases",
        json={"transaction_id": 999999},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_duplicate_case_returns_409(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify duplicate case for the same transaction is rejected with 409 Conflict."""
    tx_id = create_test_transaction(db_session, "DUP-TX-01")
    admin = UserRepository.create(
        db=db_session,
        email="dup.admin@fraudshield.test",
        name="Dup Admin",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    # First creation: 201
    res1 = unauthenticated_client.post(
        "/api/v1/cases",
        json={"transaction_id": tx_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == status.HTTP_201_CREATED

    # Second creation attempt: 409 Conflict
    res2 = unauthenticated_client.post(
        "/api/v1/cases",
        json={"transaction_id": tx_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# 2. Case Listing & Visibility Tests
# ---------------------------------------------------------------------------


def test_case_listing_rbac_visibility(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify Admin and Auditor see all cases; Analyst only sees assigned or unassigned cases."""
    tx1 = create_test_transaction(db_session, "LIST-TX-01")
    tx2 = create_test_transaction(db_session, "LIST-TX-02")
    tx3 = create_test_transaction(db_session, "LIST-TX-03")

    analyst1 = UserRepository.create(
        db=db_session,
        email="analyst1.list@fraudshield.test",
        name="Analyst 1",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    analyst2 = UserRepository.create(
        db=db_session,
        email="analyst2.list@fraudshield.test",
        name="Analyst 2",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    auditor = UserRepository.create(
        db=db_session,
        email="auditor.list@fraudshield.test",
        name="Auditor List",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
    )
    admin = UserRepository.create(
        db=db_session,
        email="admin.list@fraudshield.test",
        name="Admin List",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()

    # Case 1: Unassigned
    c1 = CaseRepository.create(db_session, transaction_id=tx1)
    # Case 2: Assigned to Analyst 1
    c2 = CaseRepository.create(
        db_session,
        transaction_id=tx2,
        assigned_user_id=analyst1.id,
        assigned_to=analyst1.email,
    )
    # Case 3: Assigned to Analyst 2
    c3 = CaseRepository.create(
        db_session,
        transaction_id=tx3,
        assigned_user_id=analyst2.id,
        assigned_to=analyst2.email,
    )
    db_session.commit()

    token_admin = make_user_token(admin)
    token_auditor = make_user_token(auditor)
    token_analyst1 = make_user_token(analyst1)

    # 1. Admin sees all 3 cases
    res_admin = unauthenticated_client.get(
        "/api/v1/cases", headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert res_admin.status_code == status.HTTP_200_OK
    assert res_admin.json()["total"] >= 3

    # 2. Auditor sees all cases
    res_auditor = unauthenticated_client.get(
        "/api/v1/cases", headers={"Authorization": f"Bearer {token_auditor}"}
    )
    assert res_auditor.status_code == status.HTTP_200_OK
    assert res_auditor.json()["total"] >= 3

    # 3. Analyst 1 sees Case 1 (unassigned) and Case 2 (assigned to them), but NOT Case 3
    res_analyst = unauthenticated_client.get(
        "/api/v1/cases", headers={"Authorization": f"Bearer {token_analyst1}"}
    )
    assert res_analyst.status_code == status.HTTP_200_OK
    visible_ids = {c["id"] for c in res_analyst.json()["items"]}
    assert c1.id in visible_ids
    assert c2.id in visible_ids
    assert c3.id not in visible_ids


def test_case_detail_forbidden_for_other_analyst(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify Analyst cannot inspect detail of a case assigned to another analyst."""
    tx_id = create_test_transaction(db_session, "DETAIL-FORBID-01")
    analyst1 = UserRepository.create(
        db=db_session,
        email="analyst1.det@fraudshield.test",
        name="Analyst 1",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    analyst2 = UserRepository.create(
        db=db_session,
        email="analyst2.det@fraudshield.test",
        name="Analyst 2",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()

    case = CaseRepository.create(
        db_session,
        transaction_id=tx_id,
        assigned_user_id=analyst2.id,
        assigned_to=analyst2.email,
    )
    db_session.commit()

    token_analyst1 = make_user_token(analyst1)
    response = unauthenticated_client.get(
        f"/api/v1/cases/{case.id}",
        headers={"Authorization": f"Bearer {token_analyst1}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_case_list_date_range_validation(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify created_from > created_to raises 400 Bad Request."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.date@fraudshield.test",
        name="Admin Date",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    future = (datetime.now(UTC) + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    past = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

    response = unauthenticated_client.get(
        f"/api/v1/cases?created_from={future}&created_to={past}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# 3. Case Assignment & State Transitions Tests
# ---------------------------------------------------------------------------


def test_admin_assign_case_success(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify Admin can assign an unassigned case to an eligible active analyst."""
    tx_id = create_test_transaction(db_session, "ASSIGN-TX-01")
    admin = UserRepository.create(
        db=db_session,
        email="assign.admin@fraudshield.test",
        name="Assign Admin",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    analyst = UserRepository.create(
        db=db_session,
        email="assigned.analyst@fraudshield.test",
        name="Target Analyst",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
        is_active=True,
    )
    db_session.commit()

    case = CaseRepository.create(db_session, transaction_id=tx_id)
    db_session.commit()

    token = make_user_token(admin)
    response = unauthenticated_client.patch(
        f"/api/v1/cases/{case.id}",
        json={"assigned_user_id": analyst.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["assigned_user_id"] == analyst.id
    assert data["assigned_to"] == analyst.email
    assert data["assigned_user"]["name"] == "Target Analyst"

    # Verify audit log
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "CASE_ASSIGNED", AuditLog.entity_id == str(case.id))
        .first()
    )
    assert audit is not None
    assert audit.details["new_assigned_user_id"] == analyst.id


def test_analyst_claim_unassigned_case(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify Analyst can claim an unassigned case for themselves."""
    tx_id = create_test_transaction(db_session, "CLAIM-TX-01")
    analyst = UserRepository.create(
        db=db_session,
        email="claim.analyst@fraudshield.test",
        name="Claim Analyst",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()

    case = CaseRepository.create(db_session, transaction_id=tx_id)
    db_session.commit()

    token = make_user_token(analyst)
    response = unauthenticated_client.patch(
        f"/api/v1/cases/{case.id}",
        json={"assigned_user_id": analyst.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["assigned_user_id"] == analyst.id


def test_analyst_cannot_reassign_other_analyst_case(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify Analyst receives 403 when trying to reassign another analyst's case."""
    tx_id = create_test_transaction(db_session, "REASSIGN-FORBID-01")
    analyst1 = UserRepository.create(
        db=db_session,
        email="analyst1.re@fraudshield.test",
        name="Analyst 1",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    analyst2 = UserRepository.create(
        db=db_session,
        email="analyst2.re@fraudshield.test",
        name="Analyst 2",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()

    # Case assigned to analyst 2
    case = CaseRepository.create(
        db_session,
        transaction_id=tx_id,
        assigned_user_id=analyst2.id,
        assigned_to=analyst2.email,
    )
    db_session.commit()

    # Analyst 1 attempts to steal/reassign case
    token1 = make_user_token(analyst1)
    response = unauthenticated_client.patch(
        f"/api/v1/cases/{case.id}",
        json={"assigned_user_id": analyst1.id},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_assign_inactive_analyst_rejected(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify assigning inactive analyst returns 400 Bad Request."""
    tx_id = create_test_transaction(db_session, "INACTIVE-ASSIGN-01")
    admin = UserRepository.create(
        db=db_session,
        email="admin.inactive@fraudshield.test",
        name="Admin Inactive",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    inactive_analyst = UserRepository.create(
        db=db_session,
        email="inactive.user@fraudshield.test",
        name="Inactive Analyst",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
        is_active=False,
    )
    db_session.commit()

    case = CaseRepository.create(db_session, transaction_id=tx_id)
    db_session.commit()

    token = make_user_token(admin)
    response = unauthenticated_client.patch(
        f"/api/v1/cases/{case.id}",
        json={"assigned_user_id": inactive_analyst.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "inactive" in response.json()["detail"].lower()


def test_assign_auditor_rejected(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify assigning non-analyst (e.g. AUDITOR) returns 400 Bad Request."""
    tx_id = create_test_transaction(db_session, "AUDITOR-ASSIGN-01")
    admin = UserRepository.create(
        db=db_session,
        email="admin.audassign@fraudshield.test",
        name="Admin AudAssign",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    auditor = UserRepository.create(
        db=db_session,
        email="auditor.assignee@fraudshield.test",
        name="Auditor Assignee",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
        is_active=True,
    )
    db_session.commit()

    case = CaseRepository.create(db_session, transaction_id=tx_id)
    db_session.commit()

    token = make_user_token(admin)
    response = unauthenticated_client.patch(
        f"/api/v1/cases/{case.id}",
        json={"assigned_user_id": auditor.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "eligible" in response.json()["detail"].lower() or "role" in response.json()["detail"].lower()


def test_state_machine_valid_transitions(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify full valid lifecycle: OPEN -> IN_REVIEW -> CONFIRMED_FRAUD -> CLOSED."""
    tx_id = create_test_transaction(db_session, "LIFECYCLE-TX-01")
    admin = UserRepository.create(
        db=db_session,
        email="admin.sm@fraudshield.test",
        name="SM Admin",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    case = CaseRepository.create(db_session, transaction_id=tx_id)
    db_session.commit()
    assert case.status == "OPEN"
    assert case.resolved_at is None

    # Step 1: OPEN -> IN_REVIEW
    res1 = unauthenticated_client.patch(
        f"/api/v1/cases/{case.id}",
        json={"status": "IN_REVIEW"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == status.HTTP_200_OK
    assert res1.json()["status"] == "IN_REVIEW"
    assert res1.json()["resolved_at"] is None

    # Step 2: IN_REVIEW -> CONFIRMED_FRAUD (should set resolved_at)
    res2 = unauthenticated_client.patch(
        f"/api/v1/cases/{case.id}",
        json={"status": "CONFIRMED_FRAUD"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == status.HTTP_200_OK
    assert res2.json()["status"] == "CONFIRMED_FRAUD"
    assert res2.json()["resolved_at"] is not None

    # Step 3: CONFIRMED_FRAUD -> CLOSED
    res3 = unauthenticated_client.patch(
        f"/api/v1/cases/{case.id}",
        json={"status": "CLOSED"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res3.status_code == status.HTTP_200_OK
    assert res3.json()["status"] == "CLOSED"


def test_state_machine_invalid_transition_returns_422(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify direct jump OPEN -> CONFIRMED_FRAUD returns 422 Unprocessable Entity."""
    tx_id = create_test_transaction(db_session, "INVALID-SM-01")
    admin = UserRepository.create(
        db=db_session,
        email="admin.badsm@fraudshield.test",
        name="Bad SM Admin",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    case = CaseRepository.create(db_session, transaction_id=tx_id)
    db_session.commit()

    # Invalid: OPEN -> CONFIRMED_FRAUD (must go through IN_REVIEW)
    response = unauthenticated_client.patch(
        f"/api/v1/cases/{case.id}",
        json={"status": "CONFIRMED_FRAUD"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "invalid status transition" in response.json()["detail"].lower()


def test_state_machine_terminal_closed_reopen_rejected(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify reopening CLOSED case (CLOSED -> OPEN) returns 422 Unprocessable Entity."""
    tx_id = create_test_transaction(db_session, "CLOSED-TERM-01")
    admin = UserRepository.create(
        db=db_session,
        email="admin.term@fraudshield.test",
        name="Term Admin",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    case = CaseRepository.create(db_session, transaction_id=tx_id)
    CaseRepository.update_status(case, "CLOSED")
    db_session.commit()

    response = unauthenticated_client.patch(
        f"/api/v1/cases/{case.id}",
        json={"status": "OPEN"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "terminal" in response.json()["detail"].lower() or "invalid status transition" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 4. Investigation Notes Tests
# ---------------------------------------------------------------------------


def test_add_case_note_and_chronological_listing(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify adding notes records author profile, emits audit event, and lists in chronological order."""
    tx_id = create_test_transaction(db_session, "NOTES-TX-01")
    analyst = UserRepository.create(
        db=db_session,
        email="notes.analyst@fraudshield.test",
        name="Notes Analyst",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()

    case = CaseRepository.create(
        db_session,
        transaction_id=tx_id,
        assigned_user_id=analyst.id,
        assigned_to=analyst.email,
    )
    db_session.commit()
    token = make_user_token(analyst)

    # 1. Add Note 1
    res1 = unauthenticated_client.post(
        f"/api/v1/cases/{case.id}/notes",
        json={"body": "Initial investigation note: contacted merchant."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == status.HTTP_201_CREATED
    data1 = res1.json()
    assert data1["body"] == "Initial investigation note: contacted merchant."
    assert data1["author_name"] == "Notes Analyst"
    assert data1["author_role"] == "ANALYST"

    # 2. Add Note 2
    res2 = unauthenticated_client.post(
        f"/api/v1/cases/{case.id}/notes",
        json={"body": "Follow-up note: confirmed cardholder dispute."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == status.HTTP_201_CREATED

    # 3. Retrieve notes
    list_res = unauthenticated_client.get(
        f"/api/v1/cases/{case.id}/notes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == status.HTTP_200_OK
    items = list_res.json()["items"]
    assert len(items) == 2
    # Chronological check
    assert items[0]["id"] == data1["id"]
    assert items[1]["body"] == "Follow-up note: confirmed cardholder dispute."

    # 4. Audit event check
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "CASE_NOTE_ADDED", AuditLog.entity_id == str(case.id))
        .first()
    )
    assert audit is not None


def test_cannot_add_note_to_closed_case(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify adding notes to a CLOSED case returns 422 Unprocessable Entity."""
    tx_id = create_test_transaction(db_session, "CLOSED-NOTE-01")
    admin = UserRepository.create(
        db=db_session,
        email="admin.closednote@fraudshield.test",
        name="Admin Closed",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()

    case = CaseRepository.create(db_session, transaction_id=tx_id)
    CaseRepository.update_status(case, "CLOSED")
    db_session.commit()

    token = make_user_token(admin)
    response = unauthenticated_client.post(
        f"/api/v1/cases/{case.id}/notes",
        json={"body": "Attempting note on closed case."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "closed" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 5. Audit Trail Read API Tests (/api/v1/audit-logs)
# ---------------------------------------------------------------------------


def test_audit_log_rbac_permissions(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify Admin and Auditor can read audit logs; Analyst is forbidden (403)."""
    admin = UserRepository.create(
        db=db_session,
        email="audit.admin@fraudshield.test",
        name="Audit Admin",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    auditor = UserRepository.create(
        db=db_session,
        email="audit.auditor@fraudshield.test",
        name="Audit Auditor",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
    )
    analyst = UserRepository.create(
        db=db_session,
        email="audit.analyst@fraudshield.test",
        name="Audit Analyst",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()

    token_admin = make_user_token(admin)
    token_auditor = make_user_token(auditor)
    token_analyst = make_user_token(analyst)

    # 1. Admin: 200 OK
    res_admin = unauthenticated_client.get(
        "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert res_admin.status_code == status.HTTP_200_OK
    assert "items" in res_admin.json()

    # 2. Auditor: 200 OK
    res_auditor = unauthenticated_client.get(
        "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token_auditor}"}
    )
    assert res_auditor.status_code == status.HTTP_200_OK

    # 3. Analyst: 403 Forbidden
    res_analyst = unauthenticated_client.get(
        "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token_analyst}"}
    )
    assert res_analyst.status_code == status.HTTP_403_FORBIDDEN

    # 4. Unauthenticated: 401 Unauthorized
    res_unauth = unauthenticated_client.get("/api/v1/audit-logs")
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED


def test_note_body_empty_or_whitespace_rejected(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify adding an empty or whitespace-only note returns 422 Unprocessable Entity."""
    tx_id = create_test_transaction(db_session, "NOTE-EMPTY-01")
    analyst = UserRepository.create(
        db=db_session,
        email="analyst.empty@fraudshield.test",
        name="Empty Analyst",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    db_session.commit()

    case = CaseRepository.create(
        db_session,
        transaction_id=tx_id,
        assigned_user_id=analyst.id,
        assigned_to=analyst.email,
    )
    db_session.commit()
    token = make_user_token(analyst)

    # Empty string
    res_empty = unauthenticated_client.post(
        f"/api/v1/cases/{case.id}/notes",
        json={"body": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_empty.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Whitespace only returns 400 Bad Request (or 422)
    res_ws = unauthenticated_client.post(
        f"/api/v1/cases/{case.id}/notes",
        json={"body": "   \n\t  "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_ws.status_code in {status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY}


def test_note_and_audit_route_immutability(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify notes and audit log records have NO mutation endpoints (PUT/PATCH/DELETE return 405/404)."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.immut@fraudshield.test",
        name="Admin Immut",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    # Audit logs cannot be posted, patched, or deleted
    res_audit_post = unauthenticated_client.post(
        "/api/v1/audit-logs",
        json={"action": "HACK"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_audit_post.status_code in {status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED}

    res_audit_delete = unauthenticated_client.delete(
        "/api/v1/audit-logs/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_audit_delete.status_code in {status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED}


def test_audit_log_date_range_validation(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify created_from > created_to raises 400 Bad Request on /api/v1/audit-logs."""
    admin = UserRepository.create(
        db=db_session,
        email="admin.auditdate@fraudshield.test",
        name="Admin AuditDate",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    token = make_user_token(admin)

    future = (datetime.now(UTC) + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    past = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

    response = unauthenticated_client.get(
        f"/api/v1/audit-logs?created_from={future}&created_to={past}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

