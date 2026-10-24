"""SQLAlchemy 2.x Declarative Base for FraudShield AI."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all database models and Alembic migrations."""

    pass
