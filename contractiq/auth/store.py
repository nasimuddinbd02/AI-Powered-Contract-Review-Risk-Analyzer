"""SQLite-backed user store.

Lightweight persistence using the stdlib ``sqlite3`` module — no ORM, no extra
dependencies. Thread-safe for the dev server via a check_same_thread=False
connection guarded by a lock.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from ..core.config import get_settings
from ..core.logging import get_logger
from .models import Role, User

log = get_logger("auth.store")


class UserStore:
    def __init__(self, db_path: str | None = None) -> None:
        settings = get_settings()
        self.db_path = db_path or settings.auth_db_path
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id              TEXT PRIMARY KEY,
                    email           TEXT UNIQUE NOT NULL,
                    full_name       TEXT NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role            TEXT NOT NULL DEFAULT 'user',
                    is_active       INTEGER NOT NULL DEFAULT 1,
                    created_at      TEXT NOT NULL
                )
                """
            )
            self._conn.commit()

    # --- mapping helpers ---
    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            hashed_password=row["hashed_password"],
            role=Role(row["role"]),
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # --- queries ---
    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]

    def get_by_email(self, email: str) -> User | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
        return self._row_to_user(row) if row else None

    def get_by_id(self, user_id: str) -> User | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._row_to_user(row) if row else None

    def list_all(self) -> list[User]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM users ORDER BY created_at ASC").fetchall()
        return [self._row_to_user(r) for r in rows]

    # --- mutations ---
    def create(self, user: User) -> User:
        with self._lock:
            self._conn.execute(
                "INSERT INTO users (id, email, full_name, hashed_password, role, is_active, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user.id, user.email.lower(), user.full_name, user.hashed_password,
                 user.role.value, int(user.is_active), user.created_at.isoformat()),
            )
            self._conn.commit()
        return user

    def update(self, user_id: str, *, role: Role | None = None, is_active: bool | None = None) -> User | None:
        sets, params = [], []
        if role is not None:
            sets.append("role = ?"); params.append(role.value)
        if is_active is not None:
            sets.append("is_active = ?"); params.append(int(is_active))
        if not sets:
            return self.get_by_id(user_id)
        params.append(user_id)
        with self._lock:
            self._conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params)
            self._conn.commit()
        return self.get_by_id(user_id)

    def delete(self, user_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self._conn.commit()
        return cur.rowcount > 0


_store: UserStore | None = None


def get_user_store() -> UserStore:
    global _store
    if _store is None:
        _store = UserStore()
    return _store


def reset_user_store(db_path: str | None = None) -> None:
    """Reset the cached store (used by tests, e.g. with an in-memory DB)."""
    global _store
    _store = UserStore(db_path) if db_path is not None else None
