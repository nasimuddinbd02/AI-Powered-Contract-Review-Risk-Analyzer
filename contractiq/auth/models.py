"""Auth data models."""
from __future__ import annotations

import enum
import re
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL_RE.match(v):
        raise ValueError("invalid email address")
    return v


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _validate_email(v)

    @field_validator("full_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _validate_email(v)


class User(BaseModel):
    """Internal user record (includes the password hash)."""

    id: str = Field(default_factory=_uuid)
    email: str
    full_name: str
    hashed_password: str
    role: Role = Role.USER
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)


class UserPublic(BaseModel):
    """User record safe to return over the API (no password hash)."""

    id: str
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime

    @classmethod
    def from_user(cls, u: User) -> "UserPublic":
        return cls(
            id=u.id, email=u.email, full_name=u.full_name,
            role=u.role, is_active=u.is_active, created_at=u.created_at,
        )


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserPublic


class UpdateUserRequest(BaseModel):
    """Admin-only mutation of a user's role / active status."""

    role: Role | None = None
    is_active: bool | None = None
