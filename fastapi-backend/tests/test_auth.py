"""Tests for the auth module: signup, login, JWT-protected routes, and RBAC."""

from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ADMIN_PAYLOAD = {
    "name": "Alice Admin",
    "email": "alice@example.com",
    "password": "secret123",
    "role": "admin",
    "user_image": "",
    "user_login": 0,
}

STUDENT_PAYLOAD = {
    "name": "Bob Student",
    "email": "bob@example.com",
    "password": "secret456",
    "role": "student",
    "user_image": "",
    "user_login": 0,
}

EXAM_PAYLOAD = {
    "title": "Test Exam",
    "duration": 60,
    "startTime": "2030-01-01T10:00:00",
    "rules": "No cheating",
    "status": "draft",
}


def _signup(client, payload):
    return client.post("/api/v1/auth/signup", json=payload)


def _login(client, email, password):
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Signup tests
# ---------------------------------------------------------------------------


class TestSignup:
    def test_signup_success(self, client):
        resp = _signup(client, ADMIN_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == ADMIN_PAYLOAD["email"]
        assert data["role"] == "admin"
        assert "userId" in data
        # Password must NOT be returned
        assert "password" not in data
        assert "password_hash" not in data

    def test_signup_duplicate_email(self, client):
        _signup(client, ADMIN_PAYLOAD)
        resp = _signup(client, ADMIN_PAYLOAD)
        assert resp.status_code == 409

    def test_signup_invalid_email(self, client):
        bad = {**ADMIN_PAYLOAD, "email": "not-an-email"}
        resp = _signup(client, bad)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------


class TestLogin:
    def test_login_success(self, client):
        _signup(client, STUDENT_PAYLOAD)
        resp = _login(client, STUDENT_PAYLOAD["email"], STUDENT_PAYLOAD["password"])
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        _signup(client, STUDENT_PAYLOAD)
        resp = _login(client, STUDENT_PAYLOAD["email"], "wrongpassword")
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = _login(client, "nobody@example.com", "anything")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# JWT-protected route tests
# ---------------------------------------------------------------------------


class TestJWTProtection:
    def test_unprotected_route_accessible_without_token(self, client):
        """Listing endpoint requires authentication — returns 401 without token."""
        resp = client.get("/api/v1/users/")
        assert resp.status_code == 401

    def test_protected_me_requires_token(self, client):
        """Accessing /auth/me without a token should return 401."""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_invalid_token_rejected(self, client):
        """A tampered / invalid token should be rejected on a protected endpoint."""
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_valid_token_accepted(self, client):
        """A valid JWT lets us reach the /auth/me endpoint."""
        _signup(client, ADMIN_PAYLOAD)
        login_resp = _login(client, ADMIN_PAYLOAD["email"], ADMIN_PAYLOAD["password"])
        token = login_resp.json()["access_token"]

        resp = client.get("/api/v1/auth/me", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == ADMIN_PAYLOAD["email"]
        assert "userId" in data
        assert "created_at" in data


# ---------------------------------------------------------------------------
# Role-based access control (RBAC) tests
# ---------------------------------------------------------------------------


class TestRBAC:
    def _get_token(self, client, payload):
        _signup(client, payload)
        resp = _login(client, payload["email"], payload["password"])
        return resp.json()["access_token"]

    def test_admin_can_access_admin_only_route(self, client):
        token = self._get_token(client, ADMIN_PAYLOAD)
        resp = client.get("/api/v1/auth/admin-only", headers=_auth_header(token))
        assert resp.status_code == 200

    def test_student_cannot_access_admin_only_route(self, client):
        token = self._get_token(client, STUDENT_PAYLOAD)
        resp = client.get("/api/v1/auth/admin-only", headers=_auth_header(token))
        assert resp.status_code == 403

    def test_student_can_access_student_only_route(self, client):
        token = self._get_token(client, STUDENT_PAYLOAD)
        resp = client.get("/api/v1/auth/student-only", headers=_auth_header(token))
        assert resp.status_code == 200

    def test_admin_cannot_access_student_only_route(self, client):
        token = self._get_token(client, ADMIN_PAYLOAD)
        resp = client.get("/api/v1/auth/student-only", headers=_auth_header(token))
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access_role_route(self, client):
        resp = client.get("/api/v1/auth/admin-only")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Exam endpoint RBAC tests
# ---------------------------------------------------------------------------


class TestExamRBAC:
    def _get_token(self, client, payload):
        _signup(client, payload)
        resp = _login(client, payload["email"], payload["password"])
        return resp.json()["access_token"]

    def test_admin_can_create_exam(self, client):
        token = self._get_token(client, ADMIN_PAYLOAD)
        resp = client.post(
            "/api/v1/exam/create",
            json=EXAM_PAYLOAD,
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == EXAM_PAYLOAD["title"]
        assert "examId" in data

    def test_student_cannot_create_exam(self, client):
        token = self._get_token(client, STUDENT_PAYLOAD)
        resp = client.post(
            "/api/v1/exam/create",
            json=EXAM_PAYLOAD,
            headers=_auth_header(token),
        )
        assert resp.status_code == 403
