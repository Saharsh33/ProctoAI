from app.crud.user import (
    get_by_id as get_user_by_id,
    get_by_email as get_user_by_email,
    list_users,
    create as create_user,
    update as update_user,
    authenticate as authenticate_user,
)
from app.crud.question import (
    get_by_id as get_question_by_id,
    list_questions,
    list_questions_by_exam,
    create as create_question,
    update as update_question,
    delete as delete_question,
)
from app.crud.exam import (
    create as create_exam,
    list_exams,
    get_by_id as get_exam_by_id,
    update as update_exam,
    delete as delete_exam,
)
from app.crud.student import create_answer, get_student_answers
from app.crud.proctoring import create as create_proctoring_log, list_logs
from app.crud.window_events import create as create_window_event, list_events
from app.crud.violation import create as create_violation, list_violations
from app.crud.report import (
    create as create_report,
    get_by_id as get_report_by_id,
    get_by_exam_and_email as get_report_by_exam_and_email,
    list_reports,
    update_pdf_path,
)
from app.crud.admin import (
    create_action as create_admin_action,
    list_actions as list_admin_actions,
    list_violations_with_actions,
    count_violations,
)

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
