"""FastAPI dependencies for authentication, database session, and role-based access control (RBAC)."""

import logging
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.db.session import get_db

logger = logging.getLogger("fraudshield_auth")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate JWT bearer token and resolve authenticated active user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
    except JWTError as jwt_err:
        logger.warning("JWT validation failed: %s", jwt_err)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or tampered authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from jwt_err

    user_id: int | None = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing user identification claims.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Access denied.",
        )

    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """Dependency factory enforcing server-side role permissions."""
    normalized_roles = {r.upper() for r in allowed_roles}

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.upper() not in normalized_roles:
            logger.warning(
                "Access denied for user %s (role: %s). Required roles: %s",
                current_user.email,
                current_user.role,
                normalized_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role(s): {', '.join(sorted(normalized_roles))}.",
            )
        return current_user

    return role_checker


# Predefined convenience dependencies
require_admin = require_roles("ADMIN")
require_analyst_or_admin = require_roles("ANALYST", "ADMIN")
require_admin_or_auditor = require_roles("ADMIN", "AUDITOR")
require_any_authenticated = require_roles("ANALYST", "ADMIN", "AUDITOR")
