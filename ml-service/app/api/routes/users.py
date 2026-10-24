"""User administration API routes (restricted to Administrator role)."""

import logging
import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.security import hash_password
from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.db.session import get_db
from app.schemas.user import (
    PaginatedUsersResponse,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)

logger = logging.getLogger("user_routes")

router = APIRouter(prefix="/api/v1/users", tags=["User Administration"])


@router.get(
    "",
    response_model=PaginatedUsersResponse,
    summary="List all users with pagination and filters (Admin only)",
    description="Returns a paginated collection of registered user accounts.",
)
def list_users(
    page: int = Query(default=1, ge=1, description="Page index (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    role: Literal["ANALYST", "ADMIN", "AUDITOR"] | None = Query(
        default=None, description="Filter by assigned role"
    ),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaginatedUsersResponse:
    """Retrieve users list with pagination."""
    users, total_count = UserRepository.list_users(
        db=db,
        page=page,
        page_size=page_size,
        role=role,
        is_active=is_active,
    )

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    return PaginatedUsersResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account (Admin only)",
    description="Registers an Analyst, Auditor, or Admin account with modern password hashing.",
    responses={
        201: {"description": "User created successfully."},
        409: {"description": "Email address already registered."},
    },
)
def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Create a new user with unique normalized email and role."""
    normalized_email = request.email.strip().lower()
    existing_user = UserRepository.get_by_email(db, normalized_email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{normalized_email}' already exists.",
        )

    # Hash password securely
    hashed = hash_password(request.password)

    new_user = UserRepository.create(
        db=db,
        email=normalized_email,
        name=request.name,
        password_hash=hashed,
        role=request.role,
        is_active=True,
    )

    # Record audit trail event
    audit_entry = AuditLog(
        actor_id=str(current_user.id),
        action="USER_CREATED",
        entity_type="user",
        entity_id=str(new_user.id),
        details={
            "email": new_user.email,
            "role": new_user.role,
            "created_by": current_user.email,
        },
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(new_user)

    logger.info("Admin %s created user %s (%s)", current_user.email, new_user.email, new_user.role)
    return UserResponse.model_validate(new_user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user details by ID (Admin only)",
    description="Returns public profile information for a specific user.",
)
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Retrieve user details."""
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} was not found.",
        )
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user profile, role, or active status (Admin only)",
    description="Allows updating user role, activating/deactivating, or updating password. Prevents deactivating the last active admin.",
)
def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Update user details with safety checks."""
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} was not found.",
        )

    # Safety check: prevent deactivating the last active admin
    if request.is_active is False and user.role == "ADMIN" and user.is_active:
        active_admins = UserRepository.count_active_admins(db)
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active administrator account.",
            )

    # Safety check: prevent demoting the last active admin
    if request.role is not None and request.role != "ADMIN" and user.role == "ADMIN":
        active_admins = UserRepository.count_active_admins(db)
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last active administrator account.",
            )

    password_hash = hash_password(request.password) if request.password else None

    updated_user = UserRepository.update(
        db=db,
        user=user,
        name=request.name,
        role=request.role,
        is_active=request.is_active,
        password_hash=password_hash,
    )

    # Record audit trail event
    audit_entry = AuditLog(
        actor_id=str(current_user.id),
        action="USER_UPDATED",
        entity_type="user",
        entity_id=str(user.id),
        details={
            "updated_by": current_user.email,
            "role_changed": request.role is not None,
            "status_changed": request.is_active is not None,
            "password_reset": request.password is not None,
        },
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(updated_user)

    logger.info("Admin %s updated user ID %d", current_user.email, user_id)
    return UserResponse.model_validate(updated_user)
