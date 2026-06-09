"""Auth + user-management tests (SRS 4.4)."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from contractiq.api.main import app  # noqa: E402
from contractiq.auth.security import hash_password, verify_password  # noqa: E402

client = TestClient(app)


def test_password_hashing_roundtrip():
    h = hash_password("s3cret-password")
    assert h != "s3cret-password"
    assert verify_password("s3cret-password", h)
    assert not verify_password("wrong", h)


def test_signup_first_user_is_admin():
    r = client.post("/auth/signup", json={"email": "admin@x.com", "password": "password123", "full_name": "Admin"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "admin"
    assert "access_token" in body


def test_second_user_is_plain_user_and_login_works():
    client.post("/auth/signup", json={"email": "admin@x.com", "password": "password123", "full_name": "Admin"})
    r = client.post("/auth/signup", json={"email": "user@x.com", "password": "password123", "full_name": "User"})
    assert r.json()["user"]["role"] == "user"

    r = client.post("/auth/login", json={"email": "user@x.com", "password": "password123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@x.com"


def test_duplicate_email_rejected():
    client.post("/auth/signup", json={"email": "dup@x.com", "password": "password123", "full_name": "Dup"})
    r = client.post("/auth/signup", json={"email": "dup@x.com", "password": "password123", "full_name": "Dup2"})
    assert r.status_code == 409


def test_bad_login_rejected():
    client.post("/auth/signup", json={"email": "a@x.com", "password": "password123", "full_name": "A"})
    assert client.post("/auth/login", json={"email": "a@x.com", "password": "nope"}).status_code == 401
    assert client.post("/auth/login", json={"email": "ghost@x.com", "password": "password123"}).status_code == 401


def test_weak_password_and_bad_email_validation():
    assert client.post("/auth/signup", json={"email": "a@x.com", "password": "short", "full_name": "A"}).status_code == 422
    assert client.post("/auth/signup", json={"email": "not-an-email", "password": "password123", "full_name": "A"}).status_code == 422


def test_user_management_admin_only():
    admin = client.post("/auth/signup", json={"email": "admin@x.com", "password": "password123", "full_name": "Admin"}).json()
    user = client.post("/auth/signup", json={"email": "user@x.com", "password": "password123", "full_name": "User"}).json()
    admin_h = {"Authorization": f"Bearer {admin['access_token']}"}
    user_h = {"Authorization": f"Bearer {user['access_token']}"}

    # Admin can list users; a plain user is forbidden.
    assert client.get("/users", headers=admin_h).status_code == 200
    assert len(client.get("/users", headers=admin_h).json()) == 2
    assert client.get("/users", headers=user_h).status_code == 403

    # Admin can promote the user to admin.
    uid = user["user"]["id"]
    r = client.patch(f"/users/{uid}", json={"role": "admin"}, headers=admin_h)
    assert r.status_code == 200 and r.json()["role"] == "admin"

    # Admin cannot demote/deactivate themselves.
    aid = admin["user"]["id"]
    assert client.patch(f"/users/{aid}", json={"is_active": False}, headers=admin_h).status_code == 400

    # Admin can delete the other user, but not themselves.
    assert client.delete(f"/users/{aid}", headers=admin_h).status_code == 400
    assert client.delete(f"/users/{uid}", headers=admin_h).status_code == 200
