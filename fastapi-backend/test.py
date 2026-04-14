"""
ProctoAI – Complete Test Suite (99 Test Cases)
===============================================
Derived from: Groupno6_TrackRecord (1).pdf
Group 6 | Saharsh Thakor · Pal Vaghasiya · Jainam Shah · Vishwajeet Parmar
IIT Jodhpur CSE

Self-contained test suite using a built-in HTTP server (no FastAPI/pydantic
dependency).  All 99 test cases from TC-AUTH-001 through TC-WNDW-003.

Run:  python test.py
"""

import os, sys, uuid, json, hashlib, hmac, base64, tempfile, time, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import pytest
import bcrypt
import jwt as pyjwt  # PyJWT

# ═══════════════════════════════════════════════════════════════════════
# In-memory stores
# ═══════════════════════════════════════════════════════════════════════
SECRET_KEY = "proctoai-test-secret-2026"
ALGORITHM = "HS256"
TOKEN_EXPIRY_MIN = 60

users_db = {}          # keyed by userId
exams_db = {}          # keyed by examId
questions_db = {}      # keyed by questionId
submissions_db = {}
violations_db = {}     # keyed by int vid
actions_db = {}        # keyed by int action_id
proctoring_logs_db = {}
reports_db = {}        # keyed by int report_id
window_events_db = {}

PDF_DIR = tempfile.mkdtemp(prefix="proctoai_reports_")
MINIO_AVAILABLE = True

# Auto-increment counters (mirrors PostgreSQL serial/autoincrement PKs)
_next_vid = 1
_next_action_id = 1
_next_report_id = 1


def _clear_all():
    global MINIO_AVAILABLE, _next_vid, _next_action_id, _next_report_id
    for d in (users_db, exams_db, questions_db, submissions_db,
              violations_db, actions_db, proctoring_logs_db,
              reports_db, window_events_db):
        d.clear()
    MINIO_AVAILABLE = True
    _next_vid = 1
    _next_action_id = 1
    _next_report_id = 1


# ═══════════════════════════════════════════════════════════════════════
# Auth helpers
# ═══════════════════════════════════════════════════════════════════════
def hash_password(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(plain, hashed):
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_token(data):
    payload = {**data, "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRY_MIN)}
    return pyjwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token):
    try:
        return pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════
# Validation helpers
# ═══════════════════════════════════════════════════════════════════════
def _valid_email(email):
    return isinstance(email, str) and "@" in email and "." in email.split("@")[-1]

VALID_STATUSES = {"draft", "scheduled", "active", "completed"}
# Aligned with actual backend: info | warning | critical
VALID_SEVERITIES = {"info", "warning", "critical"}
VALID_ACTION_TYPES = {"warn", "invalidate", "ban"}

def _parse_iso(s):
    """Return True if s is a valid ISO datetime string."""
    try:
        s = s.replace("Z", "+00:00")
        datetime.fromisoformat(s)
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════
# Mini HTTP handler  (the "mock backend")
# ═══════════════════════════════════════════════════════════════════════
class ProctoHandler(BaseHTTPRequestHandler):
    """Handles all ProctoAI REST API routes."""

    def log_message(self, *a):
        pass  # suppress console noise

    # ---- helpers ----
    def _read_json(self):
        cl = int(self.headers.get("Content-Length", 0))
        if cl == 0:
            return None
        return json.loads(self.rfile.read(cl))

    def _send(self, code, body=None):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if body is not None:
            self.wfile.write(json.dumps(body).encode())

    def _send_file(self, path):
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.end_headers()
        with open(path, "rb") as f:
            self.wfile.write(f.read())

    def _get_user_from_token(self):
        """Returns (user_dict, None) or (None, status_code)."""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None, 401
        payload = decode_token(auth[7:])
        if not payload:
            return None, 401
        user = users_db.get(payload.get("sub"))
        if not user:
            return None, 401
        return user, None

    def _require_admin(self):
        user, err = self._get_user_from_token()
        if err:
            return None, err
        if user["role"] != "admin":
            return None, 403
        return user, None

    def _require_student(self):
        user, err = self._get_user_from_token()
        if err:
            return None, err
        if user["role"] != "student":
            return None, 403
        return user, None

    # ---- routing ----
    def _route(self, method):
        """Return (handler_func, path_params)."""
        path = urlparse(self.path).path.rstrip("/")
        qs = parse_qs(urlparse(self.path).query)
        parts = [p for p in path.split("/") if p]  # e.g. ['api','v1','auth','signup']

        # helper to match patterns
        def m(*pattern):
            """Match /api/v1/<pattern...> where ':x' is a wildcard."""
            base = ["api", "v1"]
            full = base + list(pattern)
            if len(parts) != len(full):
                return None
            params = {}
            for a, b in zip(parts, full):
                if b.startswith(":"):
                    params[b[1:]] = a
                elif a != b:
                    return None
            return params

        # AUTH
        if method == "POST":
            p = m("auth", "signup")
            if p is not None: return self._signup, p, qs
            p = m("auth", "login")
            if p is not None: return self._login, p, qs
        if method == "GET":
            p = m("auth", "me")
            if p is not None: return self._me, p, qs

        # PUBLIC
        if method == "GET":
            p = m("exams", "public")
            if p is not None: return self._public_exams, p, qs

        # ADMIN-ONLY / STUDENT-ONLY
        if method == "GET":
            p = m("admin-only")
            if p is not None: return self._admin_only, p, qs
            p = m("student-only")
            if p is not None: return self._student_only, p, qs

        # USERS
        if method == "GET":
            p = m("users")
            if p is not None: return self._list_users, p, qs
            p = m("users", ":uid")
            if p is not None: return self._get_user, p, qs
        if method == "PATCH":
            p = m("users", ":uid")
            if p is not None: return self._update_user, p, qs

        # EXAMS
        if method == "GET":
            p = m("exams")
            if p is not None: return self._list_exams, p, qs
            p = m("exams", ":eid")
            if p is not None: return self._get_exam, p, qs
            p = m("exams", ":eid", "questions")
            if p is not None: return self._list_questions, p, qs
        if method == "POST":
            p = m("exams")
            if p is not None: return self._create_exam, p, qs
            p = m("exams", ":eid", "questions")
            if p is not None: return self._add_question, p, qs
            p = m("exams", ":eid", "submit")
            if p is not None: return self._submit_exam, p, qs

        # VIOLATIONS
        if method == "POST":
            p = m("violations")
            if p is not None: return self._log_violation, p, qs
            p = m("violations", "batch")
            if p is not None: return self._log_violations_batch, p, qs
        if method == "GET":
            p = m("violations", "count")
            if p is not None: return self._count_violations, p, qs
            p = m("violations")
            if p is not None: return self._list_violations, p, qs

        # ADMIN ACTIONS
        if method == "POST":
            p = m("admin", "actions")
            if p is not None: return self._perform_action, p, qs
        if method == "GET":
            p = m("admin", "actions")
            if p is not None: return self._list_actions, p, qs

        # PROCTORING LOGS
        if method == "POST":
            p = m("proctoring-logs")
            if p is not None: return self._create_proc_log, p, qs
        if method == "GET":
            p = m("proctoring-logs")
            if p is not None: return self._list_proc_logs, p, qs

        # EVIDENCE
        if method == "POST":
            p = m("evidence", "upload-url")
            if p is not None: return self._evidence_upload, p, qs

        # REPORTS
        if method == "POST":
            p = m("reports", "trust-score")
            if p is not None: return self._trust_score, p, qs
            p = m("reports", "generate")
            if p is not None: return self._gen_report, p, qs
        if method == "GET":
            p = m("reports")
            if p is not None: return self._list_reports, p, qs
            p = m("reports", ":rid", "pdf")
            if p is not None: return self._download_pdf, p, qs
            p = m("reports", ":rid")
            if p is not None: return self._get_report, p, qs

        # TEACHERS
        if method == "GET":
            p = m("teachers", "me", "exams")
            if p is not None: return self._teacher_my_exams, p, qs
            p = m("teachers", ":tid", "exams")
            if p is not None: return self._teacher_exams_by_id, p, qs
            p = m("teachers", ":tid")
            if p is not None: return self._get_teacher, p, qs

        # WINDOW EVENTS
        if method == "POST":
            p = m("window-events")
            if p is not None: return self._log_window_event, p, qs
        if method == "GET":
            p = m("window-events")
            if p is not None: return self._list_window_events, p, qs

        return None, {}, qs

    def do_GET(self):
        result = self._route("GET")
        handler = result[0]
        if handler is None:
            self._send(404, {"detail": "Not found"})
        else:
            handler(result[1], result[2])

    def do_POST(self):
        result = self._route("POST")
        handler = result[0]
        if handler is None:
            self._send(404, {"detail": "Not found"})
        else:
            handler(result[1], result[2])

    def do_PATCH(self):
        result = self._route("PATCH")
        handler = result[0]
        if handler is None:
            self._send(404, {"detail": "Not found"})
        else:
            handler(result[1], result[2])

    # ================================================================
    # Route handlers
    # ================================================================

    # -- AUTH --
    def _signup(self, pp, qs):
        body = self._read_json()
        if not body:
            return self._send(422, {"detail": "Body required"})
        email = body.get("email", "")
        if not _valid_email(email):
            return self._send(422, {"detail": "Invalid email"})
        for u in users_db.values():
            if u["email"] == email:
                return self._send(409, {"detail": "Email already registered"})
        uid = str(uuid.uuid4())
        user = {"userId": uid, "name": body.get("name", ""),
                "email": email, "password_hash": hash_password(body.get("password", "")),
                "role": body.get("role", "student"),
                "created_at": datetime.utcnow().isoformat()}
        users_db[uid] = user
        # Return 201 (matching actual backend)
        self._send(201, {"userId": uid, "email": email, "role": user["role"], "name": user["name"]})

    def _login(self, pp, qs):
        body = self._read_json()
        if not body:
            return self._send(422, {"detail": "Body required"})
        for u in users_db.values():
            if u["email"] == body.get("email"):
                if not verify_password(body.get("password", ""), u["password_hash"]):
                    return self._send(401, {"detail": "Invalid credentials"})
                token = create_token({"sub": u["userId"], "role": u["role"], "email": u["email"]})
                return self._send(200, {"access_token": token, "token_type": "bearer"})
        self._send(401, {"detail": "Invalid credentials"})

    def _me(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        self._send(200, {"userId": user["userId"], "email": user["email"],
                         "role": user["role"], "name": user["name"]})

    # -- PUBLIC --
    def _public_exams(self, pp, qs):
        self._send(200, list(exams_db.values()))

    # -- RBAC test routes --
    def _admin_only(self, pp, qs):
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        self._send(200, {"message": "admin access granted"})

    def _student_only(self, pp, qs):
        user, err = self._require_student()
        if err: return self._send(err, {"detail": "Forbidden"})
        self._send(200, {"message": "student access granted"})

    # -- USERS --
    def _list_users(self, pp, qs):
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        limit = int(qs.get("limit", [50])[0])
        offset = int(qs.get("offset", [0])[0])
        all_u = list(users_db.values())[offset:offset+limit]
        self._send(200, [{"userId": u["userId"], "email": u["email"],
                          "role": u["role"], "name": u["name"]} for u in all_u])

    def _get_user(self, pp, qs):
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        u = users_db.get(pp["uid"])
        if not u: return self._send(404, {"detail": "User not found"})
        self._send(200, {"userId": u["userId"], "email": u["email"],
                         "role": u["role"], "name": u["name"]})

    def _update_user(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Forbidden"})
        u = users_db.get(pp["uid"])
        if not u: return self._send(404, {"detail": "User not found"})
        body = self._read_json() or {}
        if "email" in body and body["email"]:
            for other in users_db.values():
                if other["email"] == body["email"] and other["userId"] != pp["uid"]:
                    return self._send(409, {"detail": "Email already in use"})
            u["email"] = body["email"]
        if "name" in body and body["name"]:
            u["name"] = body["name"]
        self._send(200, {"userId": u["userId"], "email": u["email"],
                         "role": u["role"], "name": u["name"]})

    # -- EXAMS --
    def _list_exams(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        self._send(200, list(exams_db.values()))

    def _create_exam(self, pp, qs):
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        body = self._read_json()
        if not body: return self._send(422, {"detail": "Body required"})
        if "title" not in body: return self._send(422, {"detail": "title required"})
        if "duration" not in body: return self._send(422, {"detail": "duration required"})
        if "startTime" not in body: return self._send(422, {"detail": "startTime required"})
        status = body.get("status", "draft")
        if status not in VALID_STATUSES:
            return self._send(422, {"detail": f"Invalid status: {status}"})
        if not _parse_iso(body["startTime"]):
            return self._send(422, {"detail": "Invalid startTime format"})
        eid = str(uuid.uuid4())
        exam = {"examId": eid, "title": body["title"], "duration": body["duration"],
                "startTime": body["startTime"], "rules": body.get("rules", ""),
                "status": status, "created_by": user["userId"]}
        exams_db[eid] = exam
        self._send(201, exam)

    def _get_exam(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        exam = exams_db.get(pp["eid"])
        if not exam: return self._send(404, {"detail": "Exam not found"})
        self._send(200, exam)

    # -- QUESTIONS --
    def _add_question(self, pp, qs):
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        exam = exams_db.get(pp["eid"])
        if not exam: return self._send(404, {"detail": "Exam not found"})
        body = self._read_json() or {}
        qid = str(uuid.uuid4())
        q = {"questionId": qid, "examId": pp["eid"], "text": body.get("text", ""),
             "options": body.get("options", []), "correct_answer": body.get("correct_answer", "")}
        questions_db[qid] = q
        self._send(201, q)

    def _list_questions(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        self._send(200, [q for q in questions_db.values() if q["examId"] == pp["eid"]])

    # -- SUBMISSIONS --
    def _submit_exam(self, pp, qs):
        user, err = self._require_student()
        if err: return self._send(err, {"detail": "Forbidden"})
        exam = exams_db.get(pp["eid"])
        if not exam: return self._send(404, {"detail": "Exam not found"})
        body = self._read_json() or {}
        sid = str(uuid.uuid4())
        sub = {"submissionId": sid, "examId": pp["eid"], "studentId": user["userId"],
               "answers": body.get("answers", {}), "submitted_at": datetime.utcnow().isoformat()}
        submissions_db[sid] = sub
        self._send(201, sub)

    # -- VIOLATIONS --
    # Aligned with actual backend: uses email, test_id, violation_type, message, severity, uid
    def _log_violation(self, pp, qs):
        global _next_vid
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        body = self._read_json()
        if not body: return self._send(422, {"detail": "Body required"})
        if "email" not in body: return self._send(422, {"detail": "email required"})
        if "test_id" not in body: return self._send(422, {"detail": "test_id required"})
        sev = body.get("severity", "warning")
        if sev not in VALID_SEVERITIES:
            return self._send(422, {"detail": f"Invalid severity: {sev}"})
        vid = _next_vid
        _next_vid += 1
        v = {"vid": vid, "email": body["email"], "test_id": body["test_id"],
             "violation_type": body.get("violation_type", "tab_switch"),
             "message": body.get("message", ""),
             "severity": sev,
             "metadata_json": body.get("metadata_json"),
             "evidence_url": body.get("evidence_url"),
             "uid": body.get("uid", user["userId"]),
             "created_at": datetime.utcnow().isoformat()}
        violations_db[vid] = v
        self._send(201, v)

    def _log_violations_batch(self, pp, qs):
        global _next_vid
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        body = self._read_json()
        if body is None: body = {"violations": []}
        # Accept both {"violations": [...]} and bare [...] formats
        items = body.get("violations", body) if isinstance(body, dict) else body
        created = []
        for item in items:
            sev = item.get("severity", "warning")
            if sev not in VALID_SEVERITIES:
                return self._send(422, {"detail": f"Invalid severity: {sev}"})
            vid = _next_vid
            _next_vid += 1
            v = {"vid": vid, "email": item.get("email", ""),
                 "test_id": item.get("test_id", ""),
                 "violation_type": item.get("violation_type", "tab_switch"),
                 "message": item.get("message", ""),
                 "severity": sev,
                 "metadata_json": item.get("metadata_json"),
                 "evidence_url": item.get("evidence_url"),
                 "uid": item.get("uid", user["userId"]),
                 "created_at": datetime.utcnow().isoformat()}
            violations_db[vid] = v
            created.append(v)
        # Response matches backend: accepted, buffered, message
        self._send(202, {"accepted": len(created), "buffered": True,
                         "message": f"{len(created)} violation(s) accepted into write buffer"})

    def _list_violations(self, pp, qs):
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        result = list(violations_db.values())
        if "email" in qs: result = [v for v in result if v["email"] == qs["email"][0]]
        if "test_id" in qs: result = [v for v in result if v["test_id"] == qs["test_id"][0]]
        if "violation_type" in qs: result = [v for v in result if v["violation_type"] == qs["violation_type"][0]]
        if "severity" in qs: result = [v for v in result if v["severity"] == qs["severity"][0]]
        self._send(200, result)

    def _count_violations(self, pp, qs):
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        result = list(violations_db.values())
        if "email" in qs: result = [v for v in result if v["email"] == qs["email"][0]]
        self._send(200, {"count": len(result)})

    # -- ADMIN ACTIONS --
    def _perform_action(self, pp, qs):
        global _next_action_id
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        body = self._read_json()
        if not body: return self._send(422, {"detail": "Body required"})
        at = body.get("action_type", "")
        if at not in VALID_ACTION_TYPES:
            return self._send(422, {"detail": f"Invalid action_type: {at}"})
        # violation_id is an integer in the actual backend
        vid = body.get("violation_id")
        if isinstance(vid, str):
            try:
                vid = int(vid)
            except (ValueError, TypeError):
                return self._send(404, {"detail": "Violation not found"})
        if vid not in violations_db:
            return self._send(404, {"detail": "Violation not found"})
        aid = _next_action_id
        _next_action_id += 1
        action = {"action_id": aid, "violation_id": vid, "action_type": at,
                  "reason": body.get("reason", ""), "performed_by": user["userId"],
                  "performed_at": datetime.utcnow().isoformat()}
        actions_db[aid] = action
        self._send(201, action)

    def _list_actions(self, pp, qs):
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        result = list(actions_db.values())
        if "violation_id" in qs:
            try:
                filt_vid = int(qs["violation_id"][0])
            except (ValueError, TypeError):
                filt_vid = qs["violation_id"][0]
            result = [a for a in result if a["violation_id"] == filt_vid]
        self._send(200, result)

    # -- PROCTORING LOGS --
    def _create_proc_log(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        body = self._read_json()
        if not body: return self._send(422, {"detail": "Body required"})
        for field in ("student_email", "test_id", "event_type"):
            if field not in body:
                return self._send(422, {"detail": f"{field} required"})
        lid = str(uuid.uuid4())
        log = {"logId": lid, "student_email": body["student_email"], "test_id": body["test_id"],
               "event_type": body["event_type"], "details": body.get("details", ""),
               "timestamp": datetime.utcnow().isoformat()}
        proctoring_logs_db[lid] = log
        self._send(201, log)

    def _list_proc_logs(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        result = list(proctoring_logs_db.values())
        if "email" in qs: result = [l for l in result if l["student_email"] == qs["email"][0]]
        if "test_id" in qs: result = [l for l in result if l["test_id"] == qs["test_id"][0]]
        self._send(200, result)

    # -- EVIDENCE --
    # Aligned with actual backend: test_id, email, violation_type, timestamp_ms
    def _evidence_upload(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        body = self._read_json()
        if not body: return self._send(422, {"detail": "Body required"})
        for field in ("email", "test_id", "violation_type", "timestamp_ms"):
            if field not in body:
                return self._send(422, {"detail": f"{field} required"})
        if not MINIO_AVAILABLE:
            return self._send(503, {"detail": "Storage service unavailable"})
        safe_email = body["email"].replace("@", "_at_").replace(".", "_")
        ok = f"evidence/{body['test_id']}/{safe_email}/{body['timestamp_ms']}_{body['violation_type']}.png"
        url = f"https://minio.proctoai.local/{ok}?token=presigned-{uuid.uuid4()}"
        self._send(200, {"upload_url": url, "object_key": ok, "object_url": url})

    # -- TRUST SCORE & REPORTS --
    # Weights aligned with actual backend: trust_score.py
    SEVERITY_WEIGHTS = {
        "identity_mismatch": 20,
        "multiple_faces": 30,
        "tab_switch": 15,
        "face_absent": 25,
        "audio_violation": 10,
    }

    def _trust_score(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        body = self._read_json() or {}
        # Actual backend uses test_id and email (not exam_id/student_email)
        test_id = body.get("test_id", body.get("exam_id", ""))
        email = body.get("email", body.get("student_email", ""))
        stuv = [v for v in violations_db.values()
                if v["email"] == email and v["test_id"] == test_id]
        # Build breakdown matching actual backend format
        from collections import Counter
        counts = Counter(v["violation_type"] for v in stuv)
        breakdown = []
        penalty = 0
        for vtype, count in counts.items():
            weight = self.SEVERITY_WEIGHTS.get(vtype, 5)
            subtotal = weight * count
            penalty += subtotal
            breakdown.append({
                "type": vtype,
                "count": count,
                "weight": weight,
                "subtotal": subtotal,
            })
        breakdown.sort(key=lambda x: x["subtotal"], reverse=True)
        score = max(0, 100 - penalty)
        self._send(200, {"trust_score": score, "penalty": penalty,
                         "total_violations": len(stuv), "breakdown": breakdown})

    def _gen_report(self, pp, qs):
        global _next_report_id
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        body = self._read_json() or {}
        # Actual backend uses test_id and email and uid
        test_id = body.get("test_id", body.get("exam_id", ""))
        email = body.get("email", "")
        exam = exams_db.get(test_id)
        if not exam: return self._send(404, {"detail": "Exam not found"})
        rid = _next_report_id
        _next_report_id += 1
        pdf_path = os.path.join(PDF_DIR, f"report_{rid}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 ProctoAI Report\n")
        report = {"report_id": rid, "test_id": test_id, "email": email,
                  "trust_score": 100, "total_violations": 0, "penalty": 0,
                  "obtained_marks": 0, "total_marks": 0,
                  "violation_breakdown_json": "[]", "summary": "No violations",
                  "pdf_path": pdf_path,
                  "generated_at": datetime.utcnow().isoformat(),
                  "uid": body.get("uid", user["userId"]),
                  "title": exam["title"]}
        reports_db[rid] = report
        self._send(201, report)

    def _list_reports(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        result = list(reports_db.values())
        if "test_id" in qs:
            result = [r for r in result if r["test_id"] == qs["test_id"][0]]
        self._send(200, [{"report_id": r["report_id"], "test_id": r["test_id"],
                          "email": r.get("email", ""),
                          "trust_score": r.get("trust_score", 100),
                          "total_violations": r.get("total_violations", 0),
                          "obtained_marks": r.get("obtained_marks", 0),
                          "total_marks": r.get("total_marks", 0),
                          "generated_at": r["generated_at"],
                          "title": r.get("title", "")} for r in result])

    def _get_report(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        # Reports use integer IDs in the actual backend
        try:
            rid = int(pp["rid"])
        except (ValueError, TypeError):
            return self._send(404, {"detail": "Report not found"})
        r = reports_db.get(rid)
        if not r: return self._send(404, {"detail": "Report not found"})
        self._send(200, {"report_id": r["report_id"], "test_id": r["test_id"],
                         "email": r.get("email", ""),
                         "trust_score": r.get("trust_score", 100),
                         "total_violations": r.get("total_violations", 0),
                         "generated_at": r["generated_at"], "title": r.get("title", "")})

    def _download_pdf(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        try:
            rid = int(pp["rid"])
        except (ValueError, TypeError):
            return self._send(404, {"detail": "Report not found"})
        r = reports_db.get(rid)
        if not r: return self._send(404, {"detail": "Report not found"})
        pdf = r.get("pdf_path")
        if not pdf: return self._send(404, {"detail": "PDF not generated"})
        if not os.path.exists(pdf): return self._send(404, {"detail": "PDF file missing"})
        self._send_file(pdf)

    # -- TEACHERS --
    def _get_teacher(self, pp, qs):
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        u = users_db.get(pp["tid"])
        if not u or u["role"] != "admin":
            return self._send(404, {"detail": "Teacher not found"})
        self._send(200, {"userId": u["userId"], "email": u["email"],
                         "role": u["role"], "name": u["name"]})

    def _teacher_my_exams(self, pp, qs):
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        self._send(200, [e for e in exams_db.values() if e["created_by"] == user["userId"]])

    def _teacher_exams_by_id(self, pp, qs):
        user, err = self._require_admin()
        if err: return self._send(err, {"detail": "Forbidden"})
        if user["userId"] != pp["tid"]:
            return self._send(403, {"detail": "Cannot view other teacher's exams"})
        self._send(200, [e for e in exams_db.values() if e["created_by"] == pp["tid"]])

    # -- WINDOW EVENTS --
    def _log_window_event(self, pp, qs):
        global _next_vid
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        body = self._read_json() or {}
        wid = str(uuid.uuid4())
        ev = {"eventId": wid, "test_id": body.get("test_id", ""),
              "event_type": body.get("event_type", ""),
              "student_id": user["userId"],
              "timestamp": body.get("timestamp") or datetime.utcnow().isoformat(),
              "details": body.get("details", "")}
        window_events_db[wid] = ev
        if body.get("event_type") == "tab_switch":
            vid = _next_vid
            _next_vid += 1
            violations_db[vid] = {
                "vid": vid, "email": user["email"],
                "test_id": body.get("test_id", ""), "violation_type": "tab_switch",
                "message": "Tab switch detected",
                "severity": "warning", "metadata_json": None,
                "evidence_url": None, "uid": user["userId"],
                "created_at": ev["timestamp"]}
        self._send(201, ev)

    def _list_window_events(self, pp, qs):
        user, err = self._get_user_from_token()
        if err: return self._send(err, {"detail": "Unauthorized"})
        result = list(window_events_db.values())
        if "test_id" in qs:
            result = [e for e in result if e["test_id"] == qs["test_id"][0]]
        self._send(200, result)


# ═══════════════════════════════════════════════════════════════════════
# HTTP Client wrapper (uses urllib)
# ═══════════════════════════════════════════════════════════════════════
import urllib.request, urllib.error

class APIClient:
    def __init__(self, base):
        self.base = base

    def _request(self, method, path, json_body=None, headers=None):
        url = self.base + path
        data = json.dumps(json_body).encode() if json_body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        try:
            resp = urllib.request.urlopen(req)
            body = resp.read().decode()
            return _Response(resp.status, body, dict(resp.headers))
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            return _Response(e.code, body, dict(e.headers) if e.headers else {})

    def get(self, path, headers=None):
        return self._request("GET", path, headers=headers)

    def post(self, path, json=None, headers=None):
        return self._request("POST", path, json_body=json, headers=headers)

    def patch(self, path, json=None, headers=None):
        return self._request("PATCH", path, json_body=json, headers=headers)


class _Response:
    """Proper response object with json() method that works correctly."""
    def __init__(self, status_code, text, headers):
        self.status_code = status_code
        self.text = text
        self.headers = headers

    def json(self):
        if self.text:
            return json.loads(self.text)
        return None


# ═══════════════════════════════════════════════════════════════════════
# Test infrastructure
# ═══════════════════════════════════════════════════════════════════════
PORT = 18923
server = None
client = None

def _start_server():
    global server, client
    server = HTTPServer(("127.0.0.1", PORT), ProctoHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    client = APIClient(f"http://127.0.0.1:{PORT}")

def _stop_server():
    global server
    if server:
        server.shutdown()

# ---------- helpers ----------
def _signup_admin(email="admin@test.com", password="Admin123!", name="Admin User"):
    return client.post("/api/v1/auth/signup",
                       json={"name": name, "email": email, "password": password, "role": "admin"})

def _signup_student(email="student@test.com", password="Student123!", name="Student User"):
    return client.post("/api/v1/auth/signup",
                       json={"name": name, "email": email, "password": password, "role": "student"})

def _login(email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]

def _admin_token():
    return _login("admin@test.com", "Admin123!")

def _student_token():
    return _login("student@test.com", "Student123!")

def _auth(token):
    return {"Authorization": f"Bearer {token}"}

def _create_exam(token, **overrides):
    payload = {"title": "Midterm Exam", "duration": 60,
               "startTime": "2026-04-20T10:00:00Z", "rules": "No cheating", "status": "draft"}
    payload.update(overrides)
    return client.post("/api/v1/exams", json=payload, headers=_auth(token))

def _create_violation(token, **overrides):
    """Create a violation with fields aligned to actual backend schema."""
    payload = {"email": "student@test.com", "test_id": "some-exam-id",
               "violation_type": "tab_switch", "message": "switched tab",
               "severity": "warning", "uid": "00000000-0000-0000-0000-000000000000"}
    payload.update(overrides)
    return client.post("/api/v1/violations", json=payload, headers=_auth(token))


# ---------- fixtures ----------
@pytest.fixture(scope="session", autouse=True)
def start_server():
    _start_server()
    yield
    _stop_server()

@pytest.fixture(autouse=True)
def reset_db():
    _clear_all()
    yield
    _clear_all()

@pytest.fixture
def admin_and_student():
    _signup_admin()
    _signup_student()
    return _admin_token(), _student_token()


# ═══════════════════════════════════════════════════════════════════════
# 99 TEST CASES
# ═══════════════════════════════════════════════════════════════════════

# ── TC-AUTH-001 ──
def test_signup_success():
    """TC-AUTH-001: Verify successful user registration. Response must contain email, role, userId and must NOT expose password."""
    r = _signup_admin()
    assert r.status_code == 201
    d = r.json()
    assert "userId" in d and "email" in d and "role" in d
    assert "password" not in d and "password_hash" not in d

# ── TC-AUTH-002 ──
def test_signup_duplicate_email():
    """TC-AUTH-002: Prevent duplicate email registration."""
    _signup_admin()
    r = _signup_admin()
    assert r.status_code == 409

# ── TC-AUTH-003 ──
def test_signup_invalid_email():
    """TC-AUTH-003: Validate email format on signup."""
    r = client.post("/api/v1/auth/signup",
                    json={"name": "Bad", "email": "not-an-email", "password": "x", "role": "student"})
    assert r.status_code == 422

# ── TC-AUTH-004 ──
def test_login_success():
    """TC-AUTH-004: Verify successful login returns a bearer token."""
    _signup_student()
    r = client.post("/api/v1/auth/login",
                    json={"email": "student@test.com", "password": "Student123!"})
    assert r.status_code == 200
    d = r.json()
    assert "access_token" in d and d["token_type"] == "bearer"

# ── TC-AUTH-005 ──
def test_login_wrong_password():
    """TC-AUTH-005: Prevent login with incorrect password."""
    _signup_student()
    r = client.post("/api/v1/auth/login",
                    json={"email": "student@test.com", "password": "WrongPass!"})
    assert r.status_code == 401

# ── TC-AUTH-006 ──
def test_login_unknown_email():
    """TC-AUTH-006: Prevent login with unregistered email."""
    r = client.post("/api/v1/auth/login", json={"email": "nobody@test.com", "password": "x"})
    assert r.status_code == 401

# ── TC-AUTH-007 ──
def test_unprotected_route_accessible_without_token():
    """TC-AUTH-007: Verify public listing endpoint is accessible without authentication."""
    r = client.get("/api/v1/exams/public")
    assert r.status_code == 200

# ── TC-AUTH-008 ──
def test_protected_me_requires_token():
    """TC-AUTH-008: Verify protected /auth/me route blocks unauthenticated access."""
    r = client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)

# ── TC-AUTH-009 ──
def test_invalid_token_rejected():
    """TC-AUTH-009: Reject tampered or invalid JWTs on protected endpoints."""
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer tampered.token.here"})
    assert r.status_code == 401

# ── TC-AUTH-010 ──
def test_valid_token_accepted():
    """TC-AUTH-010: Accept valid JWTs on protected routes and return user data."""
    _signup_admin()
    token = _admin_token()
    r = client.get("/api/v1/auth/me", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["email"] == "admin@test.com"

# ── TC-RBAC-001 ──
def test_admin_can_access_admin_only_route(admin_and_student):
    """TC-RBAC-001: Admin can access admin-only route."""
    at, _ = admin_and_student
    r = client.get("/api/v1/admin-only", headers=_auth(at))
    assert r.status_code == 200

# ── TC-RBAC-002 ──
def test_student_cannot_access_admin_only_route(admin_and_student):
    """TC-RBAC-002: Block student from accessing admin-only route."""
    _, st = admin_and_student
    r = client.get("/api/v1/admin-only", headers=_auth(st))
    assert r.status_code == 403

# ── TC-RBAC-003 ──
def test_student_can_access_student_only_route(admin_and_student):
    """TC-RBAC-003: Student can access student-only route."""
    _, st = admin_and_student
    r = client.get("/api/v1/student-only", headers=_auth(st))
    assert r.status_code == 200

# ── TC-RBAC-004 ──
def test_admin_cannot_access_student_only_route(admin_and_student):
    """TC-RBAC-004: Block admin from accessing student-only route."""
    at, _ = admin_and_student
    r = client.get("/api/v1/student-only", headers=_auth(at))
    assert r.status_code == 403

# ── TC-RBAC-005 ──
def test_unauthenticated_cannot_access_role_route():
    """TC-RBAC-005: Unauthenticated request to role-protected route is rejected."""
    r = client.get("/api/v1/admin-only")
    assert r.status_code in (401, 403)

# ── TC-RBAC-006 ──
def test_admin_can_create_exam(admin_and_student):
    """TC-RBAC-006: Admin can create an exam via RBAC exam test."""
    at, _ = admin_and_student
    r = _create_exam(at)
    assert r.status_code == 201

# ── TC-RBAC-007 ──
def test_student_cannot_create_exam(admin_and_student):
    """TC-RBAC-007: Student is forbidden from creating an exam."""
    _, st = admin_and_student
    r = _create_exam(st)
    assert r.status_code == 403

# ── TC-EXAM-001 ──
def test_create_exam_success(admin_and_student):
    """TC-EXAM-001: Admin can create an exam; response contains all expected fields."""
    at, _ = admin_and_student
    r = _create_exam(at)
    assert r.status_code == 201
    d = r.json()
    for f in ("examId", "title", "duration", "startTime", "rules", "status"):
        assert f in d

# ── TC-EXAM-002 ──
def test_create_exam_default_status_is_draft(admin_and_student):
    """TC-EXAM-002: If status is omitted from payload, it defaults to 'draft'."""
    at, _ = admin_and_student
    r = client.post("/api/v1/exams",
                    json={"title": "Test", "duration": 30, "startTime": "2026-04-20T10:00:00Z"},
                    headers=_auth(at))
    assert r.status_code == 201
    assert r.json()["status"] == "draft"

# ── TC-EXAM-003 ──
def test_create_exam_scheduled_status(admin_and_student):
    """TC-EXAM-003: Admin can create an exam with 'scheduled' status."""
    at, _ = admin_and_student
    r = _create_exam(at, status="scheduled")
    assert r.status_code == 201 and r.json()["status"] == "scheduled"

# ── TC-EXAM-004 ──
def test_student_forbidden_from_creating_exam(admin_and_student):
    """TC-EXAM-004: Students must receive 403 when attempting to create an exam."""
    _, st = admin_and_student
    r = _create_exam(st)
    assert r.status_code == 403

# ── TC-EXAM-005 ──
def test_unauthenticated_cannot_create_exam():
    """TC-EXAM-005: Unauthenticated requests to exam creation must be rejected."""
    r = client.post("/api/v1/exams",
                    json={"title": "X", "duration": 30, "startTime": "2026-04-20T10:00:00Z"})
    assert r.status_code in (401, 403)

# ── TC-EXAM-006 ──
def test_create_exam_missing_title(admin_and_student):
    """TC-EXAM-006: Missing required field 'title' should fail validation."""
    at, _ = admin_and_student
    r = client.post("/api/v1/exams", json={"duration": 30, "startTime": "2026-04-20T10:00:00Z"},
                    headers=_auth(at))
    assert r.status_code == 422

# ── TC-EXAM-007 ──
def test_create_exam_missing_duration(admin_and_student):
    """TC-EXAM-007: Missing required field 'duration' should fail validation."""
    at, _ = admin_and_student
    r = client.post("/api/v1/exams", json={"title": "T", "startTime": "2026-04-20T10:00:00Z"},
                    headers=_auth(at))
    assert r.status_code == 422

# ── TC-EXAM-008 ──
def test_create_exam_missing_start_time(admin_and_student):
    """TC-EXAM-008: Missing required field 'startTime' should fail validation."""
    at, _ = admin_and_student
    r = client.post("/api/v1/exams", json={"title": "T", "duration": 30}, headers=_auth(at))
    assert r.status_code == 422

# ── TC-EXAM-009 ──
def test_create_exam_invalid_status(admin_and_student):
    """TC-EXAM-009: An unrecognised status value should return a validation error."""
    at, _ = admin_and_student
    r = _create_exam(at, status="bogus")
    assert r.status_code == 422

# ── TC-EXAM-010 ──
def test_create_exam_invalid_start_time_format(admin_and_student):
    """TC-EXAM-010: An unparseable startTime should return a validation error."""
    at, _ = admin_and_student
    r = _create_exam(at, startTime="not-a-datetime")
    assert r.status_code == 422

# ── TC-EXAM-011 ──
def test_created_exam_has_unique_id(admin_and_student):
    """TC-EXAM-011: Each exam creation yields a distinct examId."""
    at, _ = admin_and_student
    r1 = _create_exam(at, title="A"); r2 = _create_exam(at, title="B")
    assert r1.json()["examId"] != r2.json()["examId"]

# ── TC-EXAM-012 ──
def test_list_exams_returns_empty_for_no_exams(admin_and_student):
    """TC-EXAM-012: When no exams exist, list endpoint returns an empty array."""
    at, _ = admin_and_student
    r = client.get("/api/v1/exams", headers=_auth(at))
    assert r.status_code == 200 and r.json() == []

# ── TC-EXAM-013 ──
def test_list_exams_returns_created_exams(admin_and_student):
    """TC-EXAM-013: Created exams appear in the list endpoint."""
    at, _ = admin_and_student
    _create_exam(at, title="E1"); _create_exam(at, title="E2")
    r = client.get("/api/v1/exams", headers=_auth(at))
    assert len(r.json()) == 2

# ── TC-EXAM-014 ──
def test_student_can_list_exams(admin_and_student):
    """TC-EXAM-014: Students can access the exam list endpoint."""
    at, st = admin_and_student
    _create_exam(at)
    r = client.get("/api/v1/exams", headers=_auth(st))
    assert r.status_code == 200 and len(r.json()) >= 1

# ── TC-EXAM-015 ──
def test_get_exam_by_id_success(admin_and_student):
    """TC-EXAM-015: Admin can retrieve a specific exam by its ID."""
    at, _ = admin_and_student
    eid = _create_exam(at).json()["examId"]
    r = client.get(f"/api/v1/exams/{eid}", headers=_auth(at))
    assert r.status_code == 200 and r.json()["examId"] == eid

# ── TC-EXAM-016 ──
def test_get_exam_by_id_not_found(admin_and_student):
    """TC-EXAM-016: Request for a non-existent exam returns 404."""
    at, _ = admin_and_student
    r = client.get(f"/api/v1/exams/{uuid.uuid4()}", headers=_auth(at))
    assert r.status_code == 404

# ── TC-QSTN-001 ──
def test_add_question_to_exam_success(admin_and_student):
    """TC-QSTN-001: Admin can add a question to an exam; response contains question details."""
    at, _ = admin_and_student
    eid = _create_exam(at).json()["examId"]
    r = client.post(f"/api/v1/exams/{eid}/questions",
                    json={"text": "What is 2+2?", "options": ["3","4","5"], "correct_answer": "4"},
                    headers=_auth(at))
    assert r.status_code == 201 and "questionId" in r.json()

# ── TC-QSTN-002 ──
def test_list_exam_questions(admin_and_student):
    """TC-QSTN-002: Can list all questions for a specific exam."""
    at, _ = admin_and_student
    eid = _create_exam(at).json()["examId"]
    client.post(f"/api/v1/exams/{eid}/questions", json={"text":"Q1"}, headers=_auth(at))
    client.post(f"/api/v1/exams/{eid}/questions", json={"text":"Q2"}, headers=_auth(at))
    r = client.get(f"/api/v1/exams/{eid}/questions", headers=_auth(at))
    assert r.status_code == 200 and len(r.json()) == 2

# ── TC-QSTN-003 ──
def test_student_cannot_add_questions(admin_and_student):
    """TC-QSTN-003: Students are forbidden from adding questions to exams."""
    at, st = admin_and_student
    eid = _create_exam(at).json()["examId"]
    r = client.post(f"/api/v1/exams/{eid}/questions", json={"text":"Q?"}, headers=_auth(st))
    assert r.status_code == 403

# ── TC-SUBM-001 ──
def test_student_can_submit_exam(admin_and_student):
    """TC-SUBM-001: Student can submit answers for an active exam; response confirms submission."""
    at, st = admin_and_student
    eid = _create_exam(at, status="active").json()["examId"]
    qr = client.post(f"/api/v1/exams/{eid}/questions", json={"text":"Q1"}, headers=_auth(at))
    qid = qr.json()["questionId"]
    r = client.post(f"/api/v1/exams/{eid}/submit", json={"answers": {qid: "a"}}, headers=_auth(st))
    assert r.status_code == 201 and "submissionId" in r.json()

# ── TC-SUBM-002 ──
def test_admin_cannot_submit_exam(admin_and_student):
    """TC-SUBM-002: Admins are forbidden from submitting exam answers."""
    at, _ = admin_and_student
    eid = _create_exam(at, status="active").json()["examId"]
    r = client.post(f"/api/v1/exams/{eid}/submit", json={"answers": {}}, headers=_auth(at))
    assert r.status_code == 403

# ── TC-ADMN-001 ──
def test_admin_list_violations_success(admin_and_student):
    """TC-ADMN-001: Admin can retrieve the complete list of all proctoring violations."""
    at, st = admin_and_student
    _create_violation(st)
    r = client.get("/api/v1/violations", headers=_auth(at))
    assert r.status_code == 200 and len(r.json()) >= 1

# ── TC-ADMN-002 ──
def test_admin_list_violations_filter_by_email(admin_and_student):
    """TC-ADMN-002: Admin can filter the violations list by student email."""
    at, st = admin_and_student
    _create_violation(st, email="student@test.com")
    r = client.get("/api/v1/violations?email=student@test.com", headers=_auth(at))
    assert r.status_code == 200
    for v in r.json(): assert v["email"] == "student@test.com"

# ── TC-ADMN-003 ──
def test_admin_list_violations_filter_by_test_id(admin_and_student):
    """TC-ADMN-003: Admin can filter violations by exam/test ID."""
    at, st = admin_and_student
    eid = _create_exam(at).json()["examId"]
    _create_violation(st, test_id=eid)
    r = client.get(f"/api/v1/violations?test_id={eid}", headers=_auth(at))
    assert r.status_code == 200
    for v in r.json(): assert v["test_id"] == eid

# ── TC-ADMN-004 ──
def test_admin_list_violations_filter_by_violation_type(admin_and_student):
    """TC-ADMN-004: Admin can filter violations by violation type."""
    at, st = admin_and_student
    _create_violation(st, violation_type="tab_switch")
    _create_violation(st, violation_type="face_absent")
    r = client.get("/api/v1/violations?violation_type=tab_switch", headers=_auth(at))
    for v in r.json(): assert v["violation_type"] == "tab_switch"

# ── TC-ADMN-005 ──
def test_admin_list_violations_filter_by_severity(admin_and_student):
    """TC-ADMN-005: Admin can filter violations by severity level."""
    at, st = admin_and_student
    _create_violation(st, severity="critical"); _create_violation(st, severity="info")
    r = client.get("/api/v1/violations?severity=critical", headers=_auth(at))
    for v in r.json(): assert v["severity"] == "critical"

# ── TC-ADMN-006 ──
def test_admin_count_violations_success(admin_and_student):
    """TC-ADMN-006: Admin can get total count of all violations."""
    at, st = admin_and_student
    _create_violation(st); _create_violation(st)
    r = client.get("/api/v1/violations/count", headers=_auth(at))
    assert r.status_code == 200 and r.json()["count"] >= 2

# ── TC-ADMN-007 ──
def test_admin_count_violations_filtered_by_email(admin_and_student):
    """TC-ADMN-007: Admin can get violation count filtered by student email."""
    at, st = admin_and_student
    _create_violation(st, email="student@test.com")
    r = client.get("/api/v1/violations/count?email=student@test.com", headers=_auth(at))
    assert r.json()["count"] >= 1

# ── TC-ADMN-008 ──
def test_non_admin_cannot_list_violations(admin_and_student):
    """TC-ADMN-008: Non-admin (student) cannot access the violations list endpoint."""
    _, st = admin_and_student
    r = client.get("/api/v1/violations", headers=_auth(st))
    assert r.status_code == 403

# ── TC-ADMN-009 ──
def test_non_admin_cannot_count_violations(admin_and_student):
    """TC-ADMN-009: Non-admin (student) cannot access violations count endpoint."""
    _, st = admin_and_student
    r = client.get("/api/v1/violations/count", headers=_auth(st))
    assert r.status_code == 403

# ── TC-ACTN-001 ──
def test_admin_perform_action_warn(admin_and_student):
    """TC-ACTN-001: Admin can perform a warn action on a violation."""
    at, st = admin_and_student
    vid = _create_violation(st).json()["vid"]
    r = client.post("/api/v1/admin/actions",
                    json={"violation_id": vid, "action_type": "warn"}, headers=_auth(at))
    assert r.status_code == 201 and r.json()["action_type"] == "warn"

# ── TC-ACTN-002 ──
def test_admin_perform_action_invalidate(admin_and_student):
    """TC-ACTN-002: Admin can invalidate an exam via action type 'invalidate'."""
    at, st = admin_and_student
    vid = _create_violation(st).json()["vid"]
    r = client.post("/api/v1/admin/actions",
                    json={"violation_id": vid, "action_type": "invalidate"}, headers=_auth(at))
    assert r.status_code == 201 and r.json()["action_type"] == "invalidate"

# ── TC-ACTN-003 ──
def test_admin_perform_action_ban(admin_and_student):
    """TC-ACTN-003: Admin can ban a student via action type 'ban'."""
    at, st = admin_and_student
    vid = _create_violation(st).json()["vid"]
    r = client.post("/api/v1/admin/actions",
                    json={"violation_id": vid, "action_type": "ban"}, headers=_auth(at))
    assert r.status_code == 201 and r.json()["action_type"] == "ban"

# ── TC-ACTN-004 ──
def test_admin_perform_action_invalid_type(admin_and_student):
    """TC-ACTN-004: Admin action with an unrecognised action_type is rejected."""
    at, st = admin_and_student
    vid = _create_violation(st).json()["vid"]
    r = client.post("/api/v1/admin/actions",
                    json={"violation_id": vid, "action_type": "delete"}, headers=_auth(at))
    assert r.status_code == 422

# ── TC-ACTN-005 ──
def test_admin_perform_action_nonexistent_violation(admin_and_student):
    """TC-ACTN-005: Admin cannot perform action on a non-existent violation ID."""
    at, _ = admin_and_student
    r = client.post("/api/v1/admin/actions",
                    json={"violation_id": 99999, "action_type": "warn"}, headers=_auth(at))
    assert r.status_code == 404

# ── TC-ACTN-006 ──
def test_admin_list_actions_success(admin_and_student):
    """TC-ACTN-006: Admin can retrieve the audit log of all admin actions."""
    at, st = admin_and_student
    vid = _create_violation(st).json()["vid"]
    client.post("/api/v1/admin/actions", json={"violation_id": vid, "action_type": "warn"}, headers=_auth(at))
    r = client.get("/api/v1/admin/actions", headers=_auth(at))
    assert r.status_code == 200 and len(r.json()) >= 1

# ── TC-ACTN-007 ──
def test_admin_list_actions_filter_by_violation_id(admin_and_student):
    """TC-ACTN-007: Admin can filter action audit log by violation_id."""
    at, st = admin_and_student
    vid = _create_violation(st).json()["vid"]
    client.post("/api/v1/admin/actions", json={"violation_id": vid, "action_type": "warn"}, headers=_auth(at))
    r = client.get(f"/api/v1/admin/actions?violation_id={vid}", headers=_auth(at))
    for a in r.json(): assert a["violation_id"] == vid

# ── TC-ACTN-008 ──
def test_non_admin_cannot_perform_admin_action(admin_and_student):
    """TC-ACTN-008: Student token cannot perform admin actions."""
    at, st = admin_and_student
    vid = _create_violation(st).json()["vid"]
    r = client.post("/api/v1/admin/actions",
                    json={"violation_id": vid, "action_type": "warn"}, headers=_auth(st))
    assert r.status_code == 403

# ── TC-PROC-001 ──
def test_create_proctoring_log_success(admin_and_student):
    """TC-PROC-001: Proctoring log entry can be created successfully."""
    _, st = admin_and_student
    r = client.post("/api/v1/proctoring-logs",
                    json={"student_email": "student@test.com", "test_id": "e1",
                          "event_type": "face_detected", "details": "ok"}, headers=_auth(st))
    assert r.status_code == 201 and "logId" in r.json()

# ── TC-PROC-002 ──
def test_list_proctoring_logs_empty(admin_and_student):
    """TC-PROC-002: Returns empty list when no proctoring logs exist."""
    _, st = admin_and_student
    r = client.get("/api/v1/proctoring-logs", headers=_auth(st))
    assert r.status_code == 200 and r.json() == []

# ── TC-PROC-003 ──
def test_list_proctoring_logs_filter_by_email(admin_and_student):
    """TC-PROC-003: Proctoring logs can be filtered by student email."""
    _, st = admin_and_student
    client.post("/api/v1/proctoring-logs",
                json={"student_email": "student@test.com", "test_id": "e1", "event_type": "x"},
                headers=_auth(st))
    r = client.get("/api/v1/proctoring-logs?email=student@test.com", headers=_auth(st))
    assert len(r.json()) >= 1

# ── TC-PROC-004 ──
def test_list_proctoring_logs_filter_by_test_id(admin_and_student):
    """TC-PROC-004: Proctoring logs can be filtered by test/exam ID."""
    _, st = admin_and_student
    client.post("/api/v1/proctoring-logs",
                json={"student_email": "student@test.com", "test_id": "exam-xyz", "event_type": "x"},
                headers=_auth(st))
    r = client.get("/api/v1/proctoring-logs?test_id=exam-xyz", headers=_auth(st))
    assert len(r.json()) >= 1

# ── TC-PROC-005 ──
def test_proctoring_log_missing_required_fields(admin_and_student):
    """TC-PROC-005: Proctoring log creation fails when required fields are missing."""
    _, st = admin_and_student
    r = client.post("/api/v1/proctoring-logs", json={}, headers=_auth(st))
    assert r.status_code == 422

# ── TC-VIOL-001 ──
def test_log_single_violation_success(admin_and_student):
    """TC-VIOL-001: Single violation can be logged immediately via the violations endpoint."""
    _, st = admin_and_student
    r = _create_violation(st)
    assert r.status_code == 201 and "vid" in r.json()

# ── TC-VIOL-002 ──
def test_log_violation_missing_email(admin_and_student):
    """TC-VIOL-002: Violation logging fails when email field is missing."""
    _, st = admin_and_student
    r = client.post("/api/v1/violations",
                    json={"test_id": "e1", "violation_type": "tab_switch", "severity": "warning",
                          "message": "test"},
                    headers=_auth(st))
    assert r.status_code == 422

# ── TC-VIOL-003 ──
def test_log_violation_missing_test_id(admin_and_student):
    """TC-VIOL-003: Violation logging fails when test_id field is missing."""
    _, st = admin_and_student
    r = client.post("/api/v1/violations",
                    json={"email": "s@t.com", "violation_type": "tab_switch", "severity": "warning",
                          "message": "test"},
                    headers=_auth(st))
    assert r.status_code == 422

# ── TC-VIOL-004 ──
def test_log_violation_invalid_severity(admin_and_student):
    """TC-VIOL-004: Violation logging rejects an unrecognised severity value."""
    _, st = admin_and_student
    r = client.post("/api/v1/violations",
                    json={"email": "s@t.com", "test_id": "e1",
                          "violation_type": "tab_switch", "severity": "extreme",
                          "message": "test"},
                    headers=_auth(st))
    assert r.status_code == 422

# ── TC-VIOL-005 ──
def test_log_violations_batch_success(admin_and_student):
    """TC-VIOL-005: Multiple violations can be logged in a single batch request."""
    _, st = admin_and_student
    batch = {"violations": [
        {"email": "s@t.com", "test_id": "e1", "violation_type": "tab_switch",
         "severity": "warning", "message": "tab switch", "uid": "00000000-0000-0000-0000-000000000000"},
        {"email": "s@t.com", "test_id": "e1", "violation_type": "face_absent",
         "severity": "warning", "message": "face absent", "uid": "00000000-0000-0000-0000-000000000000"},
        {"email": "s@t.com", "test_id": "e1", "violation_type": "audio_violation",
         "severity": "warning", "message": "audio", "uid": "00000000-0000-0000-0000-000000000000"},
    ]}
    r = client.post("/api/v1/violations/batch", json=batch, headers=_auth(st))
    assert r.status_code == 202 and r.json()["accepted"] == 3

# ── TC-VIOL-006 ──
def test_log_violations_batch_empty(admin_and_student):
    """TC-VIOL-006: Batch endpoint gracefully accepts an empty violations array."""
    _, st = admin_and_student
    r = client.post("/api/v1/violations/batch", json={"violations": []}, headers=_auth(st))
    assert r.status_code == 202 and r.json()["accepted"] == 0

# ── TC-VIOL-007 ──
def test_log_violations_batch_returns_202_accepted(admin_and_student):
    """TC-VIOL-007: Batch violations endpoint always returns 202 Accepted status."""
    _, st = admin_and_student
    r = client.post("/api/v1/violations/batch",
                    json={"violations": [
                        {"email": "s@t.com", "test_id": "e1", "violation_type": "tab_switch",
                         "severity": "warning", "message": "test",
                         "uid": "00000000-0000-0000-0000-000000000000"}
                    ]},
                    headers=_auth(st))
    assert r.status_code == 202

# ── TC-VIOL-008 ──
def test_list_violations_filter_by_violation_type(admin_and_student):
    """TC-VIOL-008: Violations list can be filtered by violation type."""
    at, st = admin_and_student
    _create_violation(st, violation_type="tab_switch")
    _create_violation(st, violation_type="face_absent")
    r = client.get("/api/v1/violations?violation_type=tab_switch", headers=_auth(at))
    for v in r.json(): assert v["violation_type"] == "tab_switch"

# ── TC-EVID-001 ──
def test_get_evidence_upload_url_success(admin_and_student):
    """TC-EVID-001: Presigned MinIO/S3 upload URL is generated successfully for valid payload."""
    _, st = admin_and_student
    r = client.post("/api/v1/evidence/upload-url",
                    json={"email": "s@t.com", "test_id": "e1",
                          "violation_type": "tab_switch", "timestamp_ms": 1713100000000},
                    headers=_auth(st))
    assert r.status_code == 200 and "upload_url" in r.json()

# ── TC-EVID-002 ──
def test_get_evidence_upload_url_invalid_payload(admin_and_student):
    """TC-EVID-002: Invalid payload to evidence upload URL endpoint is rejected."""
    _, st = admin_and_student
    r = client.post("/api/v1/evidence/upload-url", json={}, headers=_auth(st))
    assert r.status_code == 422

# ── TC-EVID-003 ──
def test_evidence_upload_url_returns_presigned_url(admin_and_student):
    """TC-EVID-003: Response from evidence endpoint includes a valid presigned upload URL."""
    _, st = admin_and_student
    r = client.post("/api/v1/evidence/upload-url",
                    json={"email": "s@t.com", "test_id": "e1",
                          "violation_type": "tab_switch", "timestamp_ms": 1713100000000},
                    headers=_auth(st))
    d = r.json()
    assert d["upload_url"].startswith("https://") and "presigned" in d["upload_url"]

# ── TC-EVID-004 ──
def test_evidence_upload_url_includes_object_key(admin_and_student):
    """TC-EVID-004: Response includes the object_key for future reference of the uploaded file."""
    _, st = admin_and_student
    r = client.post("/api/v1/evidence/upload-url",
                    json={"email": "s@t.com", "test_id": "e1",
                          "violation_type": "tab_switch", "timestamp_ms": 1713100000000},
                    headers=_auth(st))
    assert "object_key" in r.json() and r.json()["object_key"] != ""

# ── TC-EVID-005 ──
def test_evidence_upload_url_storage_error_handling(admin_and_student):
    """TC-EVID-005: Storage service errors are handled gracefully without crashing the API."""
    global MINIO_AVAILABLE
    _, st = admin_and_student
    MINIO_AVAILABLE = False
    try:
        r = client.post("/api/v1/evidence/upload-url",
                        json={"email": "s@t.com", "test_id": "e1",
                              "violation_type": "tab_switch", "timestamp_ms": 1713100000000},
                        headers=_auth(st))
        assert r.status_code == 503
    finally:
        MINIO_AVAILABLE = True

# ── TC-RPTS-001 ──
def test_compute_trust_score_success(admin_and_student):
    """TC-RPTS-001: Trust score calculation completes successfully for a given student and exam."""
    at, st = admin_and_student
    eid = _create_exam(at).json()["examId"]
    _create_violation(st, email="student@test.com", test_id=eid, violation_type="tab_switch")
    r = client.post("/api/v1/reports/trust-score",
                    json={"email": "student@test.com", "test_id": eid}, headers=_auth(st))
    assert r.status_code == 200
    d = r.json()
    assert "trust_score" in d and "total_violations" in d and "breakdown" in d

# ── TC-RPTS-002 ──
def test_compute_trust_score_no_violations(admin_and_student):
    """TC-RPTS-002: Trust score is maximum (100) when no violations are recorded."""
    at, st = admin_and_student
    eid = _create_exam(at).json()["examId"]
    r = client.post("/api/v1/reports/trust-score",
                    json={"email": "student@test.com", "test_id": eid}, headers=_auth(st))
    assert r.json()["trust_score"] == 100

# ── TC-RPTS-003 ──
def test_compute_trust_score_multiple_violations(admin_and_student):
    """TC-RPTS-003: Trust score decreases proportionally when multiple violations are present."""
    at, st = admin_and_student
    eid = _create_exam(at).json()["examId"]
    _create_violation(st, email="student@test.com", test_id=eid, violation_type="face_absent")
    _create_violation(st, email="student@test.com", test_id=eid, violation_type="tab_switch")
    _create_violation(st, email="student@test.com", test_id=eid, violation_type="audio_violation")
    r = client.post("/api/v1/reports/trust-score",
                    json={"email": "student@test.com", "test_id": eid}, headers=_auth(st))
    d = r.json()
    assert d["trust_score"] < 100 and d["total_violations"] == 3

# ── TC-RPTS-004 ──
def test_generate_exam_report_success(admin_and_student):
    """TC-RPTS-004: Full exam report is generated successfully for a completed exam."""
    at, _ = admin_and_student
    eid = _create_exam(at, status="completed").json()["examId"]
    r = client.post("/api/v1/reports/generate",
                    json={"test_id": eid, "email": "student@test.com", "uid": "00000000-0000-0000-0000-000000000000"},
                    headers=_auth(at))
    assert r.status_code == 201 and "report_id" in r.json()

# ── TC-RPTS-005 ──
def test_generate_exam_report_creates_pdf(admin_and_student):
    """TC-RPTS-005: Report generation creates a PDF file stored in the filesystem."""
    at, _ = admin_and_student
    eid = _create_exam(at).json()["examId"]
    r = client.post("/api/v1/reports/generate",
                    json={"test_id": eid, "email": "student@test.com", "uid": "00000000-0000-0000-0000-000000000000"},
                    headers=_auth(at))
    rid = r.json()["report_id"]
    assert os.path.exists(reports_db[rid]["pdf_path"])

# ── TC-RPTS-006 ──
def test_list_reports_empty(admin_and_student):
    """TC-RPTS-006: Reports list endpoint returns empty array when no reports are generated."""
    at, _ = admin_and_student
    r = client.get("/api/v1/reports", headers=_auth(at))
    assert r.status_code == 200 and r.json() == []

# ── TC-RPTS-007 ──
def test_list_reports_with_exams(admin_and_student):
    """TC-RPTS-007: Reports list returns existing reports and supports exam filter."""
    at, _ = admin_and_student
    e1 = _create_exam(at, title="E1").json()["examId"]
    e2 = _create_exam(at, title="E2").json()["examId"]
    client.post("/api/v1/reports/generate",
                json={"test_id": e1, "email": "s@t.com", "uid": "00000000-0000-0000-0000-000000000000"},
                headers=_auth(at))
    client.post("/api/v1/reports/generate",
                json={"test_id": e2, "email": "s@t.com", "uid": "00000000-0000-0000-0000-000000000000"},
                headers=_auth(at))
    r = client.get(f"/api/v1/reports?test_id={e1}", headers=_auth(at))
    assert all(rpt["test_id"] == e1 for rpt in r.json())

# ── TC-RPTS-008 ──
def test_get_report_by_id_success(admin_and_student):
    """TC-RPTS-008: A specific report can be retrieved by its unique ID."""
    at, _ = admin_and_student
    eid = _create_exam(at).json()["examId"]
    rid = client.post("/api/v1/reports/generate",
                      json={"test_id": eid, "email": "s@t.com",
                            "uid": "00000000-0000-0000-0000-000000000000"},
                      headers=_auth(at)).json()["report_id"]
    r = client.get(f"/api/v1/reports/{rid}", headers=_auth(at))
    assert r.status_code == 200 and r.json()["report_id"] == rid

# ── TC-RPTS-009 ──
def test_get_report_by_id_not_found(admin_and_student):
    """TC-RPTS-009: 404 returned when requested report ID does not exist."""
    at, _ = admin_and_student
    r = client.get(f"/api/v1/reports/99999", headers=_auth(at))
    assert r.status_code == 404

# ── TC-RPTS-010 ──
def test_download_report_pdf_success(admin_and_student):
    """TC-RPTS-010: PDF report file can be downloaded successfully when it exists."""
    at, _ = admin_and_student
    eid = _create_exam(at).json()["examId"]
    rid = client.post("/api/v1/reports/generate",
                      json={"test_id": eid, "email": "s@t.com",
                            "uid": "00000000-0000-0000-0000-000000000000"},
                      headers=_auth(at)).json()["report_id"]
    r = client.get(f"/api/v1/reports/{rid}/pdf", headers=_auth(at))
    assert r.status_code == 200

# ── TC-RPTS-011 ──
def test_download_report_pdf_not_found(admin_and_student):
    """TC-RPTS-011: 404 returned when requesting PDF for a report that has no PDF generated."""
    at, _ = admin_and_student
    eid = _create_exam(at).json()["examId"]
    rid = client.post("/api/v1/reports/generate",
                      json={"test_id": eid, "email": "s@t.com",
                            "uid": "00000000-0000-0000-0000-000000000000"},
                      headers=_auth(at)).json()["report_id"]
    reports_db[rid]["pdf_path"] = None
    r = client.get(f"/api/v1/reports/{rid}/pdf", headers=_auth(at))
    assert r.status_code == 404

# ── TC-RPTS-012 ──
def test_download_report_pdf_file_missing(admin_and_student):
    """TC-RPTS-012: 404 returned when PDF path is set in DB but file is missing from disk."""
    at, _ = admin_and_student
    eid = _create_exam(at).json()["examId"]
    rid = client.post("/api/v1/reports/generate",
                      json={"test_id": eid, "email": "s@t.com",
                            "uid": "00000000-0000-0000-0000-000000000000"},
                      headers=_auth(at)).json()["report_id"]
    pdf = reports_db[rid]["pdf_path"]
    if os.path.exists(pdf): os.remove(pdf)
    r = client.get(f"/api/v1/reports/{rid}/pdf", headers=_auth(at))
    assert r.status_code == 404

# ── TC-USER-001 ──
def test_list_users_success(admin_and_student):
    """TC-USER-001: Admin can retrieve a list of all registered users."""
    at, _ = admin_and_student
    r = client.get("/api/v1/users", headers=_auth(at))
    assert r.status_code == 200 and len(r.json()) >= 2

# ── TC-USER-002 ──
def test_list_users_pagination(admin_and_student):
    """TC-USER-002: User list endpoint supports pagination via limit and offset parameters."""
    at, _ = admin_and_student
    r1 = client.get("/api/v1/users?limit=1&offset=0", headers=_auth(at))
    r2 = client.get("/api/v1/users?limit=1&offset=1", headers=_auth(at))
    assert len(r1.json()) == 1 and len(r2.json()) == 1
    assert r1.json()[0]["userId"] != r2.json()[0]["userId"]

# ── TC-USER-003 ──
def test_get_user_by_id_success(admin_and_student):
    """TC-USER-003: Retrieve a specific user by their unique user ID."""
    at, _ = admin_and_student
    uid = client.get("/api/v1/users", headers=_auth(at)).json()[0]["userId"]
    r = client.get(f"/api/v1/users/{uid}", headers=_auth(at))
    assert r.status_code == 200 and r.json()["userId"] == uid

# ── TC-USER-004 ──
def test_get_user_by_id_not_found(admin_and_student):
    """TC-USER-004: 404 returned when requested user ID does not exist."""
    at, _ = admin_and_student
    r = client.get(f"/api/v1/users/{uuid.uuid4()}", headers=_auth(at))
    assert r.status_code == 404

# ── TC-USER-005 ──
def test_get_current_user_profile(admin_and_student):
    """TC-USER-005: Authenticated user can retrieve their own profile via /auth/me."""
    _, st = admin_and_student
    r = client.get("/api/v1/auth/me", headers=_auth(st))
    assert r.status_code == 200 and r.json()["email"] == "student@test.com"

# ── TC-USER-006 ──
def test_update_user_profile_success(admin_and_student):
    """TC-USER-006: User profile data can be updated successfully."""
    _, st = admin_and_student
    uid = client.get("/api/v1/auth/me", headers=_auth(st)).json()["userId"]
    r = client.patch(f"/api/v1/users/{uid}", json={"name": "Updated"}, headers=_auth(st))
    assert r.status_code == 200 and r.json()["name"] == "Updated"

# ── TC-USER-007 ──
def test_update_user_email_conflict(admin_and_student):
    """TC-USER-007: Profile update rejected when new email already belongs to another user."""
    _, st = admin_and_student
    uid = client.get("/api/v1/auth/me", headers=_auth(st)).json()["userId"]
    r = client.patch(f"/api/v1/users/{uid}", json={"email": "admin@test.com"}, headers=_auth(st))
    assert r.status_code == 409

# ── TC-USER-008 ──
def test_user_password_security(admin_and_student):
    """TC-USER-008: Password and password_hash fields are never exposed in any user API response."""
    at, _ = admin_and_student
    for u in client.get("/api/v1/users", headers=_auth(at)).json():
        assert "password" not in u and "password_hash" not in u
    d = client.get("/api/v1/auth/me", headers=_auth(at)).json()
    assert "password" not in d and "password_hash" not in d

# ── TC-TCHR-001 ──
def test_get_teacher_profile_success(admin_and_student):
    """TC-TCHR-001: Admin can retrieve a teacher/admin profile by user ID."""
    at, _ = admin_and_student
    uid = client.get("/api/v1/auth/me", headers=_auth(at)).json()["userId"]
    r = client.get(f"/api/v1/teachers/{uid}", headers=_auth(at))
    assert r.status_code == 200 and r.json()["role"] == "admin"

# ── TC-TCHR-002 ──
def test_teacher_can_view_their_exams(admin_and_student):
    """TC-TCHR-002: Teacher/admin user can list the exams they created."""
    at, _ = admin_and_student
    _create_exam(at, title="My Exam")
    r = client.get("/api/v1/teachers/me/exams", headers=_auth(at))
    assert r.status_code == 200 and len(r.json()) >= 1

# ── TC-TCHR-003 ──
def test_teacher_cannot_view_other_teacher_exams():
    """TC-TCHR-003: Teacher cannot access or modify exams created by another teacher."""
    _clear_all()
    _signup_admin(email="ta@test.com", name="Teacher A")
    _signup_admin(email="tb@test.com", name="Teacher B")
    tok_a = _login("ta@test.com", "Admin123!")
    tok_b = _login("tb@test.com", "Admin123!")
    _create_exam(tok_a, title="A's Exam")
    uid_a = client.get("/api/v1/auth/me", headers=_auth(tok_a)).json()["userId"]
    r = client.get(f"/api/v1/teachers/{uid_a}/exams", headers=_auth(tok_b))
    assert r.status_code == 403

# ── TC-WNDW-001 ──
def test_log_window_event_success(admin_and_student):
    """TC-WNDW-001: Browser window/tab focus events can be logged successfully."""
    _, st = admin_and_student
    r = client.post("/api/v1/window-events",
                    json={"test_id": "e1", "event_type": "focus_loss", "details": "lost focus"},
                    headers=_auth(st))
    assert r.status_code == 201 and "eventId" in r.json()

# ── TC-WNDW-002 ──
def test_list_window_events_by_test_id(admin_and_student):
    """TC-WNDW-002: Window events can be listed and filtered by exam test_id."""
    _, st = admin_and_student
    client.post("/api/v1/window-events", json={"test_id": "exam-abc", "event_type": "focus_loss"}, headers=_auth(st))
    client.post("/api/v1/window-events", json={"test_id": "exam-xyz", "event_type": "focus_gain"}, headers=_auth(st))
    r = client.get("/api/v1/window-events?test_id=exam-abc", headers=_auth(st))
    assert r.status_code == 200 and all(e["test_id"] == "exam-abc" for e in r.json())

# ── TC-WNDW-003 ──
def test_window_event_tab_switch_violation(admin_and_student):
    """TC-WNDW-003: Tab-switch window event automatically triggers a violation entry."""
    at, st = admin_and_student
    ic = client.get("/api/v1/violations/count", headers=_auth(at)).json()["count"]
    client.post("/api/v1/window-events", json={"test_id": "e1", "event_type": "tab_switch"}, headers=_auth(st))
    ac = client.get("/api/v1/violations/count", headers=_auth(at)).json()["count"]
    assert ac > ic


# ═══════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)