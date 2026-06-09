"""Password hashing (PBKDF2-HMAC-SHA256) and JWT issuance/verification.

Passwords use stdlib PBKDF2 with a per-user random salt and a high iteration
count — secure and dependency-free. Tokens are signed JWTs (HS256) via PyJWT.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from ..core.config import get_settings
from ..core.logging import get_logger

log = get_logger("auth.security")

_PBKDF2_ITERATIONS = 600_000
_ALGO = "pbkdf2_sha256"


# --- passwords --------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{_ALGO}${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:  # malformed hash
        return False


# --- JWT --------------------------------------------------------------------

def create_access_token(subject: str, role: str, email: str) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)`` for the given user."""
    settings = get_settings()
    if settings.jwt_secret == "dev-insecure-change-me":
        log.warning("JWT_SECRET is the insecure default — set a strong JWT_SECRET in production.")
    expire_seconds = settings.jwt_expire_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expire_seconds)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expire_seconds


def decode_token(token: str) -> dict:
    """Decode/verify a JWT, raising ``jwt.PyJWTError`` on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
