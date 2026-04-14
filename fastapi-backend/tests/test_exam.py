"""Tests for exam creation endpoint: success, validation, and RBAC."""

import pytest

ADMIN_PAYLOAD = {
    "name": "ExamAdmin",
    "email": "examadmin@example.com",
    "password": "adminpass",
    "role": "admin",
    "user_image": "",
    "user_login": 0,
}

STUDENT_PAYLOAD = {
    "name": "ExamStudent",
    "email": "examstudent@example.com",
    "password": "studentpass",
    "role": "student",
    "user_image": "",
    "user_login": 0,
}

VALID_EXAM = {
    "title": "Midterm Exam",
    "duration": 90,
    "startTime": "2030-06-15T09:00:00",
    "rules": "No open-book materials allowed.",
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


def _get_admin_token(client):
    _signup(client, ADMIN_PAYLOAD)
    resp = _login(client, ADMIN_PAYLOAD["email"], ADMIN_PAYLOAD["password"])
    return resp.json()["access_token"]


def _get_student_token(client):
    _signup(client, STUDENT_PAYLOAD)
    resp = _login(client, STUDENT_PAYLOAD["email"], STUDENT_PAYLOAD["password"])
    return resp.json()["access_token"]


def _create_exam(client, token, exam_data=None):
    """Helper to create an exam and return the response."""
    data = exam_data or VALID_EXAM
    resp = client.post(
        "/api/v1/exam/create",
        json=data,
        headers=_auth_header(token),
    )
    return resp


class TestExamCreation:
    """Tests for POST /api/v1/exam/create."""

    def test_create_exam_success(self, client):
        """Admin can create an exam; response contains expected fields."""
        token = _get_admin_token(client)
        resp = client.post(
            "/api/v1/exam/create",
            json=VALID_EXAM,
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == VALID_EXAM["title"]
        assert data["duration"] == VALID_EXAM["duration"]
        assert data["rules"] == VALID_EXAM["rules"]
        assert data["status"] == "draft"
        assert "examId" in data

    def test_create_exam_default_status_is_draft(self, client):
        """If status is omitted it defaults to 'draft'."""
        token = _get_admin_token(client)
        payload = {k: v for k, v in VALID_EXAM.items() if k != "status"}
        resp = client.post(
            "/api/v1/exam/create",
            json=payload,
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "draft"

    def test_create_exam_scheduled_status(self, client):
        """Admin can create an exam with 'scheduled' status."""
        token = _get_admin_token(client)
        payload = {**VALID_EXAM, "status": "scheduled", "title": "Scheduled Exam"}
        resp = client.post(
            "/api/v1/exam/create",
            json=payload,
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "scheduled"

    def test_student_forbidden_from_creating_exam(self, client):
        """Students must receive 403 when attempting to create an exam."""
        token = _get_student_token(client)
        resp = client.post(
            "/api/v1/exam/create",
            json=VALID_EXAM,
            headers=_auth_header(token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_exam(self, client):
        """Unauthenticated requests must be rejected with 401."""
        resp = client.post("/api/v1/exam/create", json=VALID_EXAM)
        assert resp.status_code == 401

    def test_create_exam_missing_title(self, client):
        """Missing required field 'title' should return 422."""
        token = _get_admin_token(client)
        payload = {k: v for k, v in VALID_EXAM.items() if k != "title"}
        resp = client.post(
            "/api/v1/exam/create",
            json=payload,
            headers=_auth_header(token),
        )
        assert resp.status_code == 422

    def test_create_exam_missing_duration(self, client):
        """Missing required field 'duration' should return 422."""
        token = _get_admin_token(client)
        payload = {k: v for k, v in VALID_EXAM.items() if k != "duration"}
        resp = client.post(
            "/api/v1/exam/create",
            json=payload,
            headers=_auth_header(token),
        )
        assert resp.status_code == 422

    def test_create_exam_missing_start_time(self, client):
        """Missing required field 'startTime' should return 422."""
        token = _get_admin_token(client)
        payload = {k: v for k, v in VALID_EXAM.items() if k != "startTime"}
        resp = client.post(
            "/api/v1/exam/create",
            json=payload,
            headers=_auth_header(token),
        )
        assert resp.status_code == 422

    def test_create_exam_invalid_status(self, client):
        """An unrecognised status value should return 422."""
        token = _get_admin_token(client)
        payload = {**VALID_EXAM, "status": "unknown_status"}
        resp = client.post(
            "/api/v1/exam/create",
            json=payload,
            headers=_auth_header(token),
        )
        assert resp.status_code == 422

    def test_create_exam_invalid_start_time_format(self, client):
        """An unparseable startTime should return 422."""
        token = _get_admin_token(client)
        payload = {**VALID_EXAM, "startTime": "not-a-date"}
        resp = client.post(
            "/api/v1/exam/create",
            json=payload,
            headers=_auth_header(token),
        )
        assert resp.status_code == 422

    def test_created_exam_has_unique_id(self, client):
        """Each exam creation yields a distinct examId."""
        token = _get_admin_token(client)
        resp1 = client.post(
            "/api/v1/exam/create",
            json={**VALID_EXAM, "title": "Exam A"},
            headers=_auth_header(token),
        )
        resp2 = client.post(
            "/api/v1/exam/create",
            json={**VALID_EXAM, "title": "Exam B"},
            headers=_auth_header(token),
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["examId"] != resp2.json()["examId"]


class TestExamListing:
    """Tests for GET /api/v1/exam/list."""

    def test_list_exams_returns_empty_for_no_exams(self, client):
        """When no exams exist, list endpoint returns empty array."""
        token = _get_admin_token(client)
        resp = client.get("/api/v1/exam/list", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_exams_returns_created_exams(self, client):
        """Created exams appear in the list endpoint."""
        token = _get_admin_token(client)
        # Create two exams
        _create_exam(client, token, {**VALID_EXAM, "title": "Exam 1"})
        _create_exam(client, token, {**VALID_EXAM, "title": "Exam 2"})

        resp = client.get("/api/v1/exam/list", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        titles = [exam["title"] for exam in data]
        assert "Exam 1" in titles
        assert "Exam 2" in titles

    def test_student_can_list_exams(self, client):
        """Students can access the exam list endpoint."""
        admin_token = _get_admin_token(client)
        student_token = _get_student_token(client)

        # Admin creates an exam
        _create_exam(client, admin_token)

        # Student can list exams
        resp = client.get("/api/v1/exam/list", headers=_auth_header(student_token))
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestExamRetrieval:
    """Tests for GET /api/v1/exam/{exam_id}."""

    def test_get_exam_by_id_success(self, client):
        """Admin can retrieve a specific exam by ID."""
        token = _get_admin_token(client)
        create_resp = _create_exam(client, token)
        exam_id = create_resp.json()["examId"]

        resp = client.get(f"/api/v1/exam/{exam_id}", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["examId"] == exam_id
        assert data["title"] == VALID_EXAM["title"]

    def test_get_exam_by_id_not_found(self, client):
        """Request for non-existent exam returns 404."""
        token = _get_admin_token(client)
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/v1/exam/{fake_id}", headers=_auth_header(token))
        assert resp.status_code == 404


class TestExamQuestions:
    """Tests for exam question endpoints."""

    def test_add_question_to_exam_success(self, client):
        """Admin can add a question to an exam."""
        admin_token = _get_admin_token(client)
        admin_resp = client.get("/api/v1/auth/me", headers=_auth_header(admin_token))
        admin_user_id = admin_resp.json()["userId"]

        # Create exam
        create_resp = _create_exam(client, admin_token)
        exam_id = create_resp.json()["examId"]

        # Add question
        question_data = {
            "qid": "Q1",
            "q": "What is 2+2?",
            "a": "3",
            "b": "4",
            "c": "5",
            "d": "6",
            "ans": "B",
            "marks": 1,
            "uid": admin_user_id,
            "examId": exam_id,
        }
        resp = client.post(
            f"/api/v1/exam/{exam_id}/questions",
            json=question_data,
            headers=_auth_header(admin_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["qid"] == "Q1"
        assert data["q"] == "What is 2+2?"
        assert data["examId"] == exam_id

    def test_list_exam_questions(self, client):
        """Can list questions for a specific exam."""
        admin_token = _get_admin_token(client)
        admin_resp = client.get("/api/v1/auth/me", headers=_auth_header(admin_token))
        admin_user_id = admin_resp.json()["userId"]

        # Create exam
        create_resp = _create_exam(client, admin_token)
        exam_id = create_resp.json()["examId"]

        # Add two questions
        for i in range(1, 3):
            question_data = {
                "qid": f"Q{i}",
                "q": f"Question {i}",
                "a": "A",
                "b": "B",
                "c": "C",
                "d": "D",
                "ans": "A",
                "marks": 1,
                "uid": admin_user_id,
                "examId": exam_id,
            }
            client.post(
                f"/api/v1/exam/{exam_id}/questions",
                json=question_data,
                headers=_auth_header(admin_token),
            )

        # List questions
        resp = client.get(
            f"/api/v1/exam/{exam_id}/questions",
            headers=_auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_student_cannot_add_questions(self, client):
        """Students are forbidden from adding questions to exams."""
        admin_token = _get_admin_token(client)
        student_token = _get_student_token(client)
        student_resp = client.get(
            "/api/v1/auth/me", headers=_auth_header(student_token)
        )
        student_user_id = student_resp.json()["userId"]

        # Admin creates exam
        create_resp = _create_exam(client, admin_token)
        exam_id = create_resp.json()["examId"]

        # Student tries to add question
        question_data = {
            "qid": "Q1",
            "q": "Question",
            "a": "A",
            "b": "B",
            "c": "C",
            "d": "D",
            "ans": "A",
            "marks": 1,
            "uid": student_user_id,
            "examId": exam_id,
        }
        resp = client.post(
            f"/api/v1/exam/{exam_id}/questions",
            json=question_data,
            headers=_auth_header(student_token),
        )
        assert resp.status_code == 403


class TestExamSubmission:
    """Tests for exam submission endpoint."""

    def test_student_can_submit_exam(self, client):
        """Student can submit answers for an exam."""
        admin_token = _get_admin_token(client)
        student_token = _get_student_token(client)
        admin_resp = client.get("/api/v1/auth/me", headers=_auth_header(admin_token))
        admin_user_id = admin_resp.json()["userId"]

        # Admin creates exam with questions
        create_resp = _create_exam(
            client, admin_token, {**VALID_EXAM, "status": "active"}
        )
        exam_id = create_resp.json()["examId"]

        # Add a question
        question_data = {
            "qid": "Q1",
            "q": "What is 2+2?",
            "a": "3",
            "b": "4",
            "c": "5",
            "d": "6",
            "ans": "B",
            "marks": 1,
            "uid": admin_user_id,
            "examId": exam_id,
        }
        client.post(
            f"/api/v1/exam/{exam_id}/questions",
            json=question_data,
            headers=_auth_header(admin_token),
        )

        # Student submits answers
        submission_data = {"examId": exam_id, "answers": [{"qid": "Q1", "answer": "B"}]}
        resp = client.post(
            f"/api/v1/exam/{exam_id}/submit",
            json=submission_data,
            headers=_auth_header(student_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Exam submitted successfully"
        assert data["submitted_count"] == 1

    def test_admin_cannot_submit_exam(self, client):
        """Admins are forbidden from submitting exams."""
        admin_token = _get_admin_token(client)

        create_resp = _create_exam(client, admin_token)
        exam_id = create_resp.json()["examId"]

        submission_data = {"examId": exam_id, "answers": [{"qid": "Q1", "answer": "A"}]}
        resp = client.post(
            f"/api/v1/exam/{exam_id}/submit",
            json=submission_data,
            headers=_auth_header(admin_token),
        )
        assert resp.status_code == 403
