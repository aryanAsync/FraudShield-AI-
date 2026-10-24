from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.case_note import CaseNote
    from app.db.models.investigation_case import InvestigationCase


class UserRole(StrEnum):
    """User authorization roles."""

    ANALYST = "ANALYST"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"


class User(Base):
    """User account entity storing credentials, active status, and RBAC role."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('ANALYST', 'ADMIN', 'AUDITOR')",
            name="ck_users_role_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Full display name of user",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="Normalized lowercase email address used for login",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Securely hashed password (never exposed via API)",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default=UserRole.ANALYST.value,
        nullable=False,
        index=True,
        doc="Assigned system role: ANALYST, ADMIN, or AUDITOR",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Active flag. Inactive users are rejected upon login and token evaluation",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        doc="Account registration timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        doc="Account profile update timestamp",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of the most recent successful login",
    )

    # Relationships
    assigned_cases: Mapped[list["InvestigationCase"]] = relationship(
        "InvestigationCase",
        back_populates="assigned_user",
        foreign_keys="InvestigationCase.assigned_user_id",
    )
    case_notes: Mapped[list["CaseNote"]] = relationship(
        "CaseNote",
        back_populates="author",
        foreign_keys="CaseNote.author_id",
    )
