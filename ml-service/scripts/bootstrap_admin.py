"""Bootstrap script to create the initial Administrator user safely."""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.security import hash_password
from app.db.models.audit_log import AuditLog
from app.db.models.user import UserRole
from app.db.repositories.user_repository import UserRepository
from app.db.session import get_session_factory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bootstrap_admin")


def bootstrap_admin(email: str, password: str, name: str, force: bool = False) -> None:
    """Create initial administrator user if none exists."""
    session_factory = get_session_factory()
    with session_factory() as db:
        active_admins = UserRepository.count_active_admins(db)
        if active_admins > 0 and not force:
            logger.info("Administrator accounts already exist (%d active). Bootstrap skipped.", active_admins)
            return

        normalized_email = email.strip().lower()
        existing = UserRepository.get_by_email(db, normalized_email)
        if existing:
            if force:
                logger.info("Updating existing user %s to ADMIN...", normalized_email)
                UserRepository.update(
                    db=db,
                    user=existing,
                    name=name,
                    role=UserRole.ADMIN.value,
                    is_active=True,
                    password_hash=hash_password(password),
                )
                db.commit()
                logger.info("Administrator %s updated successfully.", normalized_email)
                return
            logger.warning("User %s already exists but is not an admin. Use --force to promote.", normalized_email)
            return

        # Create new admin user
        admin_user = UserRepository.create(
            db=db,
            email=normalized_email,
            name=name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN.value,
            is_active=True,
        )

        audit_entry = AuditLog(
            actor_id="system_bootstrap",
            action="BOOTSTRAP_INITIAL_ADMIN",
            entity_type="user",
            entity_id=str(admin_user.id),
            details={"email": admin_user.email, "role": admin_user.role},
        )
        db.add(audit_entry)
        db.commit()
        logger.info("Initial Administrator account created successfully: %s (ID: %d)", admin_user.email, admin_user.id)


def main():
    parser = argparse.ArgumentParser(description="Create initial FraudShield AI administrator.")
    parser.add_argument(
        "--email",
        default=os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@fraudshield.ai"),
        help="Administrator email address",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "AdminSecret2026!"),
        help="Administrator password (min 8 characters)",
    )
    parser.add_argument(
        "--name",
        default=os.getenv("BOOTSTRAP_ADMIN_NAME", "System Administrator"),
        help="Administrator display name",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force promotion or update if user already exists",
    )

    args = parser.parse_args()
    if len(args.password) < 8:
        logger.error("Administrator password must be at least 8 characters.")
        sys.exit(1)

    bootstrap_admin(email=args.email, password=args.password, name=args.name, force=args.force)


if __name__ == "__main__":
    main()
