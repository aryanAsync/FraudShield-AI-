"""Repository for User database operations and authentication lookups."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.user import User, UserRole


class UserRepository:
    """Encapsulates database operations for users."""

    @staticmethod
    def create(
        db: Session,
        email: str,
        name: str,
        password_hash: str,
        role: str = UserRole.ANALYST.value,
        is_active: bool = True,
    ) -> User:
        """Create a new user with normalized lowercase email address."""
        user = User(
            email=email.strip().lower(),
            name=name.strip(),
            password_hash=password_hash,
            role=role.upper(),
            is_active=is_active,
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        """Retrieve user by primary key ID."""
        stmt = select(User).where(User.id == user_id)
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        """Retrieve user by normalized lowercase email address."""
        stmt = select(User).where(User.email == email.strip().lower())
        return db.scalars(stmt).first()

    @staticmethod
    def update(
        db: Session,
        user: User,
        name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        password_hash: str | None = None,
    ) -> User:
        """Update user properties."""
        if name is not None:
            user.name = name.strip()
        if role is not None:
            user.role = role.upper()
        if is_active is not None:
            user.is_active = is_active
        if password_hash is not None:
            user.password_hash = password_hash
        user.updated_at = datetime.now(UTC)
        db.flush()
        return user

    @staticmethod
    def update_last_login(db: Session, user: User) -> None:
        """Update last login timestamp upon successful authentication."""
        user.last_login_at = datetime.now(UTC)
        db.flush()

    @staticmethod
    def count_active_admins(db: Session) -> int:
        """Count currently active administrators."""
        stmt = (
            select(func.count(User.id))
            .where(User.role == UserRole.ADMIN.value)
            .where(User.is_active.is_(True))
        )
        return db.scalar(stmt) or 0

    @staticmethod
    def list_users(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        """List users with pagination, role filters, and deterministic sorting."""
        stmt = select(User)
        count_stmt = select(func.count(User.id))

        if role is not None:
            normalized_role = role.upper()
            stmt = stmt.where(User.role == normalized_role)
            count_stmt = count_stmt.where(User.role == normalized_role)

        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
            count_stmt = count_stmt.where(User.is_active == is_active)

        total_count = db.scalar(count_stmt) or 0

        # Sort deterministically by id asc
        stmt = stmt.order_by(User.id.asc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        records = list(db.scalars(stmt).all())
        return records, total_count
