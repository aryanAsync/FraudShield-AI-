"""Unit and Integration Tests for Phase 2: Authentication, Users, and Server-Side RBAC."""

from datetime import timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository


def make_token(user: User, expires_delta: timedelta | None = None) -> str:
    """Helper to generate a valid access token for a test user."""
    return create_access_token(
        subject=user.email,
        user_id=user.id,
        role=user.role,
        name=user.name,
        expires_delta=expires_delta,
    )


# ---------------------------------------------------------------------------
# 1. Core Security & Password Hashing Unit Tests
# ---------------------------------------------------------------------------


def test_password_hashing_and_verification():
    """Verify bcrypt hashes passwords reliably and verifies matches correctly."""
    plain = "SuperSecretPassword123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert hashed.startswith("$2b$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_password_hashing_handles_long_passwords():
    """Verify bcrypt handles passwords over 72 bytes gracefully via byte slicing."""
    long_pass = "A" * 100
    hashed = hash_password(long_pass)
    assert verify_password(long_pass, hashed) is True
    assert verify_password("A" * 71, hashed) is False


def test_jwt_token_generation_and_decoding():
    """Verify access token generation and claims decoding."""
    token = create_access_token(
        subject="analyst@fraudshield.ai",
        user_id=42,
        role="ANALYST",
        name="Analyst User",
        expires_delta=timedelta(minutes=15),
    )
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == "analyst@fraudshield.ai"
    assert payload["user_id"] == 42
    assert payload["role"] == "ANALYST"
    assert "exp" in payload


def test_jwt_token_expired_fails_decoding():
    """Verify expired token raises jwt.JWTError."""
    expired_token = create_access_token(
        subject="expired@fraudshield.ai",
        user_id=1,
        role="ANALYST",
        expires_delta=timedelta(minutes=-5),
    )
    with pytest.raises(jwt.JWTError):
        decode_access_token(expired_token)


def test_jwt_token_tampered_signature_fails_decoding():
    """Verify tampered signature raises jwt.JWTError."""
    token = create_access_token(
        subject="user@test.ai",
        user_id=1,
        role="ANALYST",
    )
    tampered = token[:-4] + "xyz1"
    with pytest.raises(jwt.JWTError):
        decode_access_token(tampered)


# ---------------------------------------------------------------------------
# 2. User Model & Repository Unit Tests
# ---------------------------------------------------------------------------


def test_user_repository_email_normalization(db_session: Session):
    """Verify UserRepository normalizes email to lowercase upon creation and lookup."""
    user = UserRepository.create(
        db=db_session,
        email="MiXeD.CaSe@FraudShield.AI",
        name="Mixed Case User",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    assert user.email == "mixed.case@fraudshield.ai"

    found = UserRepository.get_by_email(db_session, "MIXED.CASE@FRAUDSHIELD.AI")
    assert found is not None
    assert found.id == user.id


def test_user_model_role_check_constraint(db_session: Session):
    """Verify invalid role string is rejected by database check constraint."""
    invalid_user = User(
        email="hacker@fraudshield.ai",
        name="Hacker",
        password_hash="fake",
        role="SUPERUSER",  # Not in ('ANALYST', 'ADMIN', 'AUDITOR')
    )
    db_session.add(invalid_user)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_count_active_admins(db_session: Session):
    """Verify count_active_admins accurately tallies active administrators."""
    initial_admins = UserRepository.count_active_admins(db_session)

    UserRepository.create(
        db=db_session,
        email="admin_test_1@fs.ai",
        name="Admin 1",
        password_hash="fake",
        role="ADMIN",
        is_active=True,
    )
    UserRepository.create(
        db=db_session,
        email="admin_test_2@fs.ai",
        name="Admin 2",
        password_hash="fake",
        role="ADMIN",
        is_active=False,  # Inactive admin should not count
    )
    UserRepository.create(
        db=db_session,
        email="analyst_test_1@fs.ai",
        name="Analyst 1",
        password_hash="fake",
        role="ANALYST",
        is_active=True,
    )
    db_session.flush()

    assert UserRepository.count_active_admins(db_session) == initial_admins + 1


# ---------------------------------------------------------------------------
# 3. Authentication API Routes Tests (/api/v1/auth)
# ---------------------------------------------------------------------------


def test_login_successful_flow(unauthenticated_client: TestClient, db_session: Session):
    """Verify valid login returns 200, JWT token, safe user profile, and logs audit event."""
    raw_pass = "SecurePass2026!"
    user = UserRepository.create(
        db=db_session,
        email="lead.analyst@fraudshield.ai",
        name="Lead Analyst",
        password_hash=hash_password(raw_pass),
        role="ANALYST",
        is_active=True,
    )
    db_session.commit()

    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "LEAD.ANALYST@fraudshield.ai", "password": raw_pass},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in_minutes"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES
    assert data["email"] == "lead.analyst@fraudshield.ai"
    assert data["role"] == "ANALYST"
    assert "password" not in data
    assert "password_hash" not in data

    # Verify last_login_at updated
    db_session.refresh(user)
    assert user.last_login_at is not None

    # Verify audit log recorded
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "LOGIN_SUCCESS", AuditLog.actor_id == str(user.id))
        .first()
    )
    assert audit is not None


def test_login_invalid_password(unauthenticated_client: TestClient, db_session: Session):
    """Verify wrong password returns 401 with generic error message and logs audit failure."""
    UserRepository.create(
        db=db_session,
        email="auth.test@fraudshield.ai",
        name="Auth Test",
        password_hash=hash_password("RightPassword123!"),
        role="ANALYST",
        is_active=True,
    )
    db_session.commit()

    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "auth.test@fraudshield.ai", "password": "WrongPassword!"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid email or password."

    # Verify failed login audit log
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "LOGIN_FAILED", AuditLog.entity_id == "auth.test@fraudshield.ai")
        .first()
    )
    assert audit is not None


def test_login_nonexistent_email(unauthenticated_client: TestClient, db_session: Session):
    """Verify nonexistent email returns identical generic 401 error to prevent enumeration."""
    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "does.not.exist@fraudshield.ai", "password": "AnyPassword123!"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid email or password."


def test_login_deactivated_account_forbidden(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify deactivated account returns 403 Forbidden even with correct password."""
    raw_pass = "ActiveOnce123!"
    UserRepository.create(
        db=db_session,
        email="deactivated.user@fraudshield.ai",
        name="Deactivated User",
        password_hash=hash_password(raw_pass),
        role="ANALYST",
        is_active=False,
    )
    db_session.commit()

    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "deactivated.user@fraudshield.ai", "password": raw_pass},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "deactivated" in response.json()["detail"].lower()


def test_auth_me_endpoint(unauthenticated_client: TestClient, db_session: Session):
    """Verify GET /api/v1/auth/me returns current user profile with valid token."""
    user = UserRepository.create(
        db=db_session,
        email="me.user@fraudshield.ai",
        name="Current User",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
        is_active=True,
    )
    db_session.commit()

    token = make_token(user)

    # Success with Bearer token
    response = unauthenticated_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "me.user@fraudshield.ai"
    assert response.json()["role"] == "AUDITOR"

    # Missing token returns 401
    missing_resp = unauthenticated_client.get("/api/v1/auth/me")
    assert missing_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # Invalid token returns 401
    invalid_resp = unauthenticated_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert invalid_resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_endpoint(unauthenticated_client: TestClient, db_session: Session):
    """Verify POST /api/v1/auth/logout records audit event."""
    user = UserRepository.create(
        db=db_session,
        email="logout.user@fraudshield.ai",
        name="Logout User",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
        is_active=True,
    )
    db_session.commit()

    token = make_token(user)
    response = unauthenticated_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert "logged out" in response.json()["message"].lower()

    # Check audit log
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "LOGOUT", AuditLog.actor_id == str(user.id))
        .first()
    )
    assert audit is not None


# ---------------------------------------------------------------------------
# 4. User Administration & RBAC Tests (/api/v1/users)
# ---------------------------------------------------------------------------


def test_user_management_role_enforcement(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify only ADMIN can access /api/v1/users; ANALYST and AUDITOR are rejected with 403."""
    admin = UserRepository.create(
        db=db_session,
        email="admin_role@fs.ai",
        name="Admin User",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    analyst = UserRepository.create(
        db=db_session,
        email="analyst_role@fs.ai",
        name="Analyst User",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    auditor = UserRepository.create(
        db=db_session,
        email="auditor_role@fs.ai",
        name="Auditor User",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
    )
    db_session.commit()

    admin_token = make_token(admin)
    analyst_token = make_token(analyst)
    auditor_token = make_token(auditor)

    # Admin: 200 OK
    res_admin = unauthenticated_client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin.status_code == status.HTTP_200_OK
    assert "items" in res_admin.json()

    # Analyst: 403 Forbidden
    res_analyst = unauthenticated_client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert res_analyst.status_code == status.HTTP_403_FORBIDDEN

    # Auditor: 403 Forbidden
    res_auditor = unauthenticated_client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert res_auditor.status_code == status.HTTP_403_FORBIDDEN

    # Unauthenticated: 401 Unauthorized
    res_no_auth = unauthenticated_client.get("/api/v1/users")
    assert res_no_auth.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_create_user(unauthenticated_client: TestClient, db_session: Session):
    """Verify ADMIN can create new users and password hash is never exposed."""
    admin = UserRepository.create(
        db=db_session,
        email="creator.admin@fs.ai",
        name="Creator Admin",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    db_session.commit()
    admin_token = make_token(admin)

    new_user_payload = {
        "email": "new.hire@fraudshield.ai",
        "name": "New Hire Analyst",
        "password": "TemporaryPassword2026!",
        "role": "ANALYST",
    }
    response = unauthenticated_client.post(
        "/api/v1/users",
        json=new_user_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "new.hire@fraudshield.ai"
    assert data["role"] == "ANALYST"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data

    # Verify duplicate email conflict
    conflict_resp = unauthenticated_client.post(
        "/api/v1/users",
        json=new_user_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert conflict_resp.status_code == status.HTTP_409_CONFLICT


def test_admin_cannot_deactivate_last_admin(
    unauthenticated_client: TestClient, db_session: Session
):
    """Verify admin guard prevents deactivating or demoting the last active administrator."""
    # Ensure only 1 active admin exists
    db_session.query(User).filter(User.role == "ADMIN").update({"role": "ANALYST"})
    db_session.flush()

    sole_admin = UserRepository.create(
        db=db_session,
        email="sole.admin@fs.ai",
        name="Sole Admin",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
        is_active=True,
    )
    db_session.commit()
    token = make_token(sole_admin)

    # Attempt to deactivate sole admin
    deactivate_res = unauthenticated_client.patch(
        f"/api/v1/users/{sole_admin.id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deactivate_res.status_code == status.HTTP_400_BAD_REQUEST
    assert "last active administrator" in deactivate_res.json()["detail"]

    # Attempt to demote sole admin to analyst
    demote_res = unauthenticated_client.patch(
        f"/api/v1/users/{sole_admin.id}",
        json={"role": "ANALYST"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert demote_res.status_code == status.HTTP_400_BAD_REQUEST
    assert "last active administrator" in demote_res.json()["detail"]


# ---------------------------------------------------------------------------
# 5. RBAC Integration on Transaction Endpoints
# ---------------------------------------------------------------------------


def test_transaction_scoring_rbac(
    unauthenticated_client: TestClient,
    sample_transaction: dict,
    db_session: Session,
):
    """Verify scoring requires ANALYST or ADMIN; AUDITOR receives 403; unauthenticated receives 401."""
    admin = UserRepository.create(
        db=db_session,
        email="tx.admin@fs.ai",
        name="TX Admin",
        password_hash=hash_password("Pass123!"),
        role="ADMIN",
    )
    analyst = UserRepository.create(
        db=db_session,
        email="tx.analyst@fs.ai",
        name="TX Analyst",
        password_hash=hash_password("Pass123!"),
        role="ANALYST",
    )
    auditor = UserRepository.create(
        db=db_session,
        email="tx.auditor@fs.ai",
        name="TX Auditor",
        password_hash=hash_password("Pass123!"),
        role="AUDITOR",
    )
    db_session.commit()

    admin_token = make_token(admin)
    analyst_token = make_token(analyst)
    auditor_token = make_token(auditor)

    # 1. Analyst: 201 Created and submitted_by defaults to analyst email
    analyst_res = unauthenticated_client.post(
        "/api/v1/transactions/score",
        json=sample_transaction,
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert analyst_res.status_code == status.HTTP_201_CREATED
    tx_data = analyst_res.json()
    assert tx_data["submitted_by"] == analyst.email
    tx_id = tx_data["transaction_id"]

    # 2. Admin: 201 Created
    sample_tx_admin = {**sample_transaction, "external_reference": "ADMIN-TX-001"}
    admin_res = unauthenticated_client.post(
        "/api/v1/transactions/score",
        json=sample_tx_admin,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == status.HTTP_201_CREATED

    # 3. Auditor: 403 Forbidden (Auditor cannot trigger scoring)
    sample_tx_auditor = {**sample_transaction, "external_reference": "AUDITOR-TX-001"}
    auditor_res = unauthenticated_client.post(
        "/api/v1/transactions/score",
        json=sample_tx_auditor,
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert auditor_res.status_code == status.HTTP_403_FORBIDDEN

    # 4. Unauthenticated: 401 Unauthorized
    unauth_res = unauthenticated_client.post(
        "/api/v1/transactions/score",
        json=sample_transaction,
    )
    assert unauth_res.status_code == status.HTTP_401_UNAUTHORIZED

    # 5. Auditor CAN read transactions, details, and predictions (Read-Only access)
    auditor_read_list = unauthenticated_client.get(
        "/api/v1/transactions",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert auditor_read_list.status_code == status.HTTP_200_OK

    auditor_read_detail = unauthenticated_client.get(
        f"/api/v1/transactions/{tx_id}",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert auditor_read_detail.status_code == status.HTTP_200_OK

    auditor_read_preds = unauthenticated_client.get(
        f"/api/v1/transactions/{tx_id}/predictions",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert auditor_read_preds.status_code == status.HTTP_200_OK
