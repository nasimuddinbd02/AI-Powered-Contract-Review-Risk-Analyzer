"""Auth service — registration, authentication, and admin user management."""
from __future__ import annotations

from ..core.logging import get_logger
from .models import Role, SignupRequest, User
from .security import hash_password, verify_password
from .store import get_user_store

log = get_logger("auth.service")


class AuthError(Exception):
    """Domain error with an HTTP-friendly status code."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def register(req: SignupRequest) -> User:
    """Create a new user. The first user ever created becomes an admin."""
    store = get_user_store()
    if store.get_by_email(req.email):
        raise AuthError("An account with this email already exists.", 409)
    role = Role.ADMIN if store.count() == 0 else Role.USER
    user = User(
        email=req.email,
        full_name=req.full_name,
        hashed_password=hash_password(req.password),
        role=role,
    )
    store.create(user)
    log.info("Registered user %s (%s)", user.email, user.role.value)
    return user


def authenticate(email: str, password: str) -> User:
    """Verify credentials and return the user, or raise ``AuthError``."""
    store = get_user_store()
    user = store.get_by_email(email)
    # Constant-ish behaviour: always run a verify to reduce user-enumeration timing.
    if user is None:
        verify_password(password, "pbkdf2_sha256$1$00$00")
        raise AuthError("Invalid email or password.", 401)
    if not verify_password(password, user.hashed_password):
        raise AuthError("Invalid email or password.", 401)
    if not user.is_active:
        raise AuthError("This account has been deactivated.", 403)
    return user
