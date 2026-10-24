"""Database session and connection management for FraudShield AI.

Provides centralized SQLAlchemy engine, session factory, and FastAPI get_db dependency.
"""

import logging
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger("fraudshield_db")

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def create_db_engine(db_url: str | None = None, **engine_kwargs: Any) -> Engine:
    """Create a configured SQLAlchemy engine."""
    settings = get_settings()
    target_url = db_url or settings.DATABASE_URL

    connect_args: dict[str, Any] = {}
    if target_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(target_url, connect_args=connect_args, **engine_kwargs)

    if "poolclass" in engine_kwargs:
        return create_engine(target_url, **engine_kwargs)

    # Production-ready PostgreSQL connection pool configuration
    pool_config: dict[str, Any] = {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800,
    }
    pool_config.update(engine_kwargs)
    return create_engine(target_url, **pool_config)


def get_engine() -> Engine:
    """Retrieve or initialize the global database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        logger.info("Initializing database engine for: %s", settings.get_safe_database_url())
        _engine = create_db_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Retrieve or initialize the global sessionmaker."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
            expire_on_commit=False,
        )
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a transaction-safe database session.

    Guarantees session cleanup upon request completion.
    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
