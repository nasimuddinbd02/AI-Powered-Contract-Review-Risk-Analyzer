"""FastAPI auth dependencies — bearer-token extraction and role guards."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import Role, User
from .security import decode_token
from .store import get_user_store

# auto_error=False so we can return a clean 401 with a WWW-Authenticate header.
_bearer = HTTPBearer(auto_error=False)

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> User:
    """Resolve and validate the current user from the bearer token."""
    if creds is None or not creds.credentials:
        raise _UNAUTH
    try:
        payload = decode_token(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has expired.",
                            headers={"WWW-Authenticate": "Bearer"})
    except jwt.PyJWTError:
        raise _UNAUTH

    user = get_user_store().get_by_id(payload.get("sub", ""))
    if user is None or not user.is_active:
        raise _UNAUTH
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Allow only admins through."""
    if user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required.")
    return user
