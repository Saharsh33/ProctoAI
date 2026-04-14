from app.crud.admin import (
    count_violations,
)
from app.crud.admin import create_action as create_admin_action
from app.crud.admin import list_actions as list_admin_actions
from app.crud.admin import (
    list_violations_with_actions,
)
from app.crud.exam import create as create_exam
from app.crud.exam import delete as delete_exam
from app.crud.exam import get_by_id as get_exam_by_id
from app.crud.exam import (
    list_exams,
)
from app.crud.exam import update as update_exam
from app.crud.proctoring import create as create_proctoring_log
from app.crud.proctoring import list_logs
from app.crud.question import create as create_question
from app.crud.question import delete as delete_question
from app.crud.question import get_by_id as get_question_by_id
from app.crud.question import (
    list_questions,
    list_questions_by_exam,
)
from app.crud.question import update as update_question
from app.crud.report import create as create_report
from app.crud.report import get_by_exam_and_email as get_report_by_exam_and_email
from app.crud.report import get_by_id as get_report_by_id
from app.crud.report import (
    list_reports,
    update_pdf_path,
)
from app.crud.student import create_answer, get_student_answers
from app.crud.user import authenticate as authenticate_user
from app.crud.user import create as create_user
from app.crud.user import get_by_email as get_user_by_email
from app.crud.user import get_by_id as get_user_by_id
from app.crud.user import (
    list_users,
)
from app.crud.user import update as update_user
from app.crud.violation import create as create_violation
from app.crud.violation import list_violations
from app.crud.window_events import create as create_window_event
from app.crud.window_events import list_events

__all__ = [
    "get_user_by_id",
    "get_user_by_email",
    "list_users",
    "create_user",
    "update_user",
    "authenticate_user",
    "get_question_by_id",
    "list_questions",
    "list_questions_by_exam",
    "create_question",
    "update_question",
    "delete_question",
    "create_exam",
    "list_exams",
    "get_exam_by_id",
    "update_exam",
    "delete_exam",
    "create_answer",
    "get_student_answers",
    "create_proctoring_log",
    "list_logs",
    "create_window_event",
    "list_events",
    "create_violation",
    "list_violations",
    "create_report",
    "get_report_by_id",
    "get_report_by_exam_and_email",
    "list_reports",
    "update_pdf_path",
    "create_admin_action",
    "list_admin_actions",
    "list_violations_with_actions",
    "count_violations",
]
