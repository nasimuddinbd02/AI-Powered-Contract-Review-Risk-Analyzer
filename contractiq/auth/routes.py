"""Auth + user-management REST routes (SRS 4.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..core.logging import get_logger
from .dependencies import get_current_user, require_admin
from .models import (
    LoginRequest, Role, SignupRequest, Token, UpdateUserRequest, User, UserPublic,
)
from .security import create_access_token
from .service import AuthError, authenticate, register
from .store import get_user_store

log = get_logger("auth.routes")

# --- authentication ---------------------------------------------------------

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token(user: User) -> Token:
    token, expires_in = create_access_token(subject=user.id, role=user.role.value, email=user.email)
    return Token(access_token=token, expires_in=expires_in, user=UserPublic.from_user(user))


@auth_router.post("/signup", response_model=Token, status_code=201)
def signup(req: SignupRequest) -> Token:
    try:
        user = register(req)
    except AuthError as exc:
        raise HTTPException(exc.status_code, exc.message)
    return _issue_token(user)


@auth_router.post("/login", response_model=Token)
def login(req: LoginRequest) -> Token:
    try:
        user = authenticate(req.email, req.password)
    except AuthError as exc:
        raise HTTPException(exc.status_code, exc.message)
    return _issue_token(user)


@auth_router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.from_user(user)


# --- user management (admin only) ------------------------------------------

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("", response_model=list[UserPublic])
def list_users(_: User = Depends(require_admin)) -> list[UserPublic]:
    return [UserPublic.from_user(u) for u in get_user_store().list_all()]


@users_router.patch("/{user_id}", response_model=UserPublic)
def update_user(user_id: str, req: UpdateUserRequest, admin: User = Depends(require_admin)) -> UserPublic:
    store = get_user_store()
    target = store.get_by_id(user_id)
    if target is None:
        raise HTTPException(404, "User not found.")
    # Guard rails: an admin cannot lock themselves out or demote the last admin.
    if target.id == admin.id and (req.is_active is False or req.role == Role.USER):
        raise HTTPException(400, "You cannot deactivate or demote your own admin account.")
    if target.role == Role.ADMIN and req.role == Role.USER:
        admins = [u for u in store.list_all() if u.role == Role.ADMIN]
        if len(admins) <= 1:
            raise HTTPException(400, "Cannot demote the last remaining admin.")
    updated = store.update(user_id, role=req.role, is_active=req.is_active)
    return UserPublic.from_user(updated)  # type: ignore[arg-type]


@users_router.delete("/{user_id}")
def delete_user(user_id: str, admin: User = Depends(require_admin)) -> dict:
    if user_id == admin.id:
        raise HTTPException(400, "You cannot delete your own account.")
    if not get_user_store().delete(user_id):
        raise HTTPException(404, "User not found.")
    return {"deleted": user_id}
