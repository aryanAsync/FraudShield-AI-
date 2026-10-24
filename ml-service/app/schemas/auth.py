"""Pydantic V2 schemas for authentication requests and tokens."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Payload for user authentication."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "email": "analyst@fraudshield.ai",
                "password": "SecurePassword123!",
            }
        },
    )

    email: EmailStr = Field(..., description="Registered user email address")
    password: str = Field(..., min_length=1, max_length=128, description="User account password")


class TokenResponse(BaseModel):
    """Authentication response returning signed JWT access token and user metadata."""

    access_token: str = Field(..., description="Signed JWT bearer access token")
    token_type: str = Field(default="bearer", description="Token scheme identifier")
    expires_in_minutes: int = Field(..., description="Access token lifespan in minutes")
    user_id: int = Field(..., description="Unique user identifier")
    role: str = Field(..., description="Assigned authorization role")
    name: str = Field(..., description="Full display name of user")
    email: str = Field(..., description="User email address")
