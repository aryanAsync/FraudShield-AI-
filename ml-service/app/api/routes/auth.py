"""Authentication routes: login, current user profile, and session termination."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.core.security import create_access_token, verify_password
from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserResponse

logger = logging.getLogger("auth_routes")

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and issue JWT bearer token",
    description="Validates email and password, checks active status, and returns a signed access token.",
    responses={
        200: {"description": "Authentication successful."},
        401: {"description": "Invalid credentials."},
        403: {"description": "Account is deactivated."},
    },
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate with normalized email and password."""
    normalized_email = request.email.strip().lower()
    user = UserRepository.get_by_email(db, normalized_email)

    if not user or not verify_password(request.password, user.password_hash):
        logger.warning("Failed login attempt for email: %s", normalized_email)
        # Audit failed login attempt (never recording password)
        audit_entry = AuditLog(
            actor_id=None,
            action="LOGIN_FAILED",
            entity_type="user",
            entity_id=normalized_email,
            details={"reason": "invalid_credentials"},
        )
        db.add(audit_entry)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning("Login attempt for deactivated user: %s", normalized_email)
        audit_entry = AuditLog(
            actor_id=str(user.id),
            action="LOGIN_BLOCKED_INACTIVE",
            entity_type="user",
            entity_id=str(user.id),
            details={"email": normalized_email},
        )
        db.add(audit_entry)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact an administrator.",
        )

    # Update last login timestamp and record successful audit event
    UserRepository.update_last_login(db, user)
    audit_entry = AuditLog(
        actor_id=str(user.id),
        action="LOGIN_SUCCESS",
        entity_type="user",
        entity_id=str(user.id),
        details={"role": user.role},
    )
    db.add(audit_entry)
    db.commit()

    settings = get_settings()
    access_token = create_access_token(
        subject=user.email,
        user_id=user.id,
        role=user.role,
        name=user.name,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user_id=user.id,
        role=user.role,
        name=user.name,
        email=user.email,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get authenticated user profile",
    description="Returns public profile details and role of the currently logged-in user.",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Retrieve profile of currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    summary="Terminate session",
    description="Logs a logout audit event. For stateless JWT tokens, client must discard the token.",
)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Client logout and audit trail."""
    audit_entry = AuditLog(
        actor_id=str(current_user.id),
        action="LOGOUT",
        entity_type="user",
        entity_id=str(current_user.id),
        details={"email": current_user.email},
    )
    db.add(audit_entry)
    db.commit()
    return {"message": "Successfully logged out. Please discard your bearer token client-side."}
