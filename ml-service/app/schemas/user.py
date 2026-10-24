"""Pydantic V2 schemas for user management and profile views."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """Public user profile schema (never exposes password hashes or signing secrets)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique user identifier")
    name: str = Field(..., description="User full display name")
    email: str = Field(..., description="Normalized user email address")
    role: str = Field(..., description="System RBAC role: ANALYST, ADMIN, or AUDITOR")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Registration timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    last_login_at: datetime | None = Field(None, description="Last successful authentication timestamp")


class UserCreateRequest(BaseModel):
    """Payload for creating a new user by an Administrator."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Jane Analyst",
                "email": "jane@fraudshield.ai",
                "password": "StrongPassword123!",
                "role": "ANALYST",
            }
        },
    )

    name: str = Field(..., min_length=1, max_length=100, description="User full display name")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Initial account password")
    role: Literal["ANALYST", "ADMIN", "AUDITOR"] = Field(
        default="ANALYST",
        description="Assigned role: ANALYST, ADMIN, or AUDITOR",
    )


class UserUpdateRequest(BaseModel):
    """Payload for updating an existing user's profile, role, or active status."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=100, description="Updated display name")
    role: Literal["ANALYST", "ADMIN", "AUDITOR"] | None = Field(
        None, description="Updated role"
    )
    is_active: bool | None = Field(None, description="Activate or deactivate account")
    password: str | None = Field(
        None, min_length=8, max_length=128, description="Optional password reset"
    )


class PaginatedUsersResponse(BaseModel):
    """Paginated collection of users for administrative review."""

    items: list[UserResponse] = Field(..., description="List of user profiles")
    total: int = Field(..., description="Total matching user accounts")
    page: int = Field(..., description="Current page (1-based)")
    page_size: int = Field(..., description="Maximum items per page")
    total_pages: int = Field(..., description="Total available pages")
