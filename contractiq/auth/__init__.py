"""Authentication & user management (SRS 4.4 — OAuth 2.0 JWT).

Provides signup/signin with JWT bearer tokens, a SQLite-backed user store, and
an admin user-management surface. Contracts are owned by the authenticated user.
"""
from .dependencies import get_current_user, require_admin
from .models import Role, UserPublic

__all__ = ["get_current_user", "require_admin", "Role", "UserPublic"]
