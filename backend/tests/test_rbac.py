"""Integration tests for RBAC: Role enum, require_admin, require_student."""
import uuid


def _signup_and_login(client, user_type: str) -> str:
    """Helper: register a user and return their access token."""
    email = f"{user_type}_{uuid.uuid4()}@example.com"
    client.post(
        "/auth/signup",
        json={
            "name": f"{user_type.capitalize()} User",
            "email": email,
            "password": "password123",
            "user_type": user_type,
        },
    )
    resp = client.post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# /exam/create  — admin-only
# ---------------------------------------------------------------------------


def test_exam_create_as_admin(client):
    """Admin user should be able to create an exam (200)."""
    token = _signup_and_login(client, "admin")
    resp = client.post(
        "/exam/create",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_exam_create_as_student_returns_403(client):
    """Student token must be rejected with 403 on /exam/create."""
    token = _signup_and_login(client, "student")
    resp = client.post(
        "/exam/create",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_exam_create_without_token_returns_401(client):
    """Unauthenticated request should return 401."""
    resp = client.post("/exam/create")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /exam/list  — student-only
# ---------------------------------------------------------------------------


def test_exam_list_as_student(client):
    """Student should be able to list exams (200)."""
    token = _signup_and_login(client, "student")
    resp = client.get(
        "/exam/list",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_exam_list_as_admin_returns_403(client):
    """Admin token must be rejected with 403 on /exam/list."""
    token = _signup_and_login(client, "admin")
    resp = client.get(
        "/exam/list",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Role enum values
# ---------------------------------------------------------------------------


def test_role_enum_values():
    """Role enum must expose the correct string values."""
    from app.models.user import Role

    assert Role.ROLE_ADMIN == "admin"
    assert Role.ROLE_STUDENT == "student"


# ---------------------------------------------------------------------------
# get_current_user returns a dict with 'role' key
# ---------------------------------------------------------------------------


def test_get_current_user_returns_role(client):
    """get_current_user should return user dict including the 'role' field."""
    token = _signup_and_login(client, "student")
    resp = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "role" in data
    assert data["role"] == "student"