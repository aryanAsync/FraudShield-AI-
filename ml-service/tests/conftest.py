"""Shared pytest fixtures for unit and integration testing."""

import os
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_user
from app.core.security import hash_password
from app.db.base import Base
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from app.services.predictor import predictor_service

# Determine test database URL
_default_test_pg = "postgresql+psycopg://postgres:aryan123@localhost:5432/fraudshield_test"
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", _default_test_pg)


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine, creating tables if needed."""
    try:
        engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        # Fallback to SQLite in-memory with Foreign Keys enabled for portable environments
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=ON"))

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    yield engine
    # Cleanup at end of session
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Provide an isolated database session per test function with automatic rollback/clean."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def default_analyst_user(db_session: Session) -> User:
    """Create a default active Analyst user for existing test suites."""
    user = User(
        email="analyst@fraudshield.test",
        name="Default Test Analyst",
        password_hash=hash_password("AnalystPass123!"),
        role="ANALYST",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture(scope="function")
def client(db_session: Session, default_analyst_user: User) -> Generator[TestClient, None, None]:
    """Provide a TestClient with database and auth dependencies overridden for existing suite."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_get_current_user() -> User:
        return default_analyst_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Ensure model is ready
    if not predictor_service.is_ready():
        predictor_service.load_model()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def unauthenticated_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a TestClient without auth overrides to test raw JWT authentication and RBAC."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.pop(get_current_user, None)

    if not predictor_service.is_ready():
        predictor_service.load_model()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_transaction() -> dict[str, Any]:
    """Return a standard legitimate-profile transaction payload."""
    payload: dict[str, Any] = {"Time": 500.0, "Amount": 29.99}
    for i in range(1, 29):
        payload[f"V{i}"] = 0.01 * (i - 14)
    return payload


@pytest.fixture
def sample_fraudulent_like_transaction() -> dict[str, Any]:
    """Return a transaction payload containing typical fraud indicators."""
    payload: dict[str, Any] = {"Time": 406.0, "Amount": 0.0}
    for i in range(1, 29):
        payload[f"V{i}"] = 0.0
    payload["V14"] = -4.28
    payload["V17"] = -2.83
    payload["V12"] = -2.89
    payload["V10"] = -2.77
    payload["V4"] = 3.99
    payload["V11"] = 3.20
    return payload
