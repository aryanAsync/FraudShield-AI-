"""Security and cryptographic operations for password hashing and JWT management."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.config import get_settings


def hash_password(password: str) -> str:
    """Securely hash a password using bcrypt."""
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    subject: str,
    user_id: int,
    role: str = "ANALYST",
    name: str = "",
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token containing standard claims."""
    settings = get_settings()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims = {
        "sub": subject.strip().lower(),
        "user_id": user_id,
        "role": role.upper(),
        "name": name,
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a signed JWT access token.

    Raises:
        JWTError: If signature is invalid, token is expired, or claims are malformed.
    """
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
