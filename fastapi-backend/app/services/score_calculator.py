"""
Score Calculator Service.

Calculates obtained marks and total marks for a student's exam submission.
"""

from __future__ import annotations

import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.student import Student
from app.models.question import Question

logger = logging.getLogger(__name__)


def calculate_exam_score(
    db: Session,
    uid: str,
    exam_id: str,
) -> dict:
    """
    Calculate obtained marks and total marks for a student's exam.

    Args:
        db: Database session
        uid: Student user ID
        exam_id: Exam ID (test_id)

    Returns:
        Dict with:
        - obtained_marks: Sum of marks for correct answers
        - total_marks: Sum of all question marks
        - correct_count: Number of correct answers
        - total_count: Total questions answered
        - percentage: (obtained_marks / total_marks) * 100 if total_marks > 0 else 0
    """
    try:
        # Get all student answers for this exam
        student_answers = (
            db.query(Student)
            .filter(
                Student.uid == uid,
                Student.test_id == exam_id,
            )
            .all()
        )

        if not student_answers:
            logger.warning(f"No answers found for student {uid} in exam {exam_id}")
            return {
                "obtained_marks": 0,
                "total_marks": 0,
                "correct_count": 0,
                "total_count": 0,
                "percentage": 0.0,
            }

        total_marks = 0
        obtained_marks = 0
        correct_count = 0

        for answer_record in student_answers:
            qid = answer_record.qid
            student_answer = answer_record.ans

            # Get question details
            question = (
                db.query(Question)
                .filter(
                    Question.qid == qid,
                    Question.examId == answer_record.examId,
                )
                .first()
            )

            if not question:
                logger.warning(f"Question {qid} not found for exam {exam_id}")
                continue

            # Add to total marks
            total_marks += question.marks

            # Check if answer is correct
            if (
                student_answer
                and student_answer.strip().upper() == question.ans.strip().upper()
            ):
                obtained_marks += question.marks
                correct_count += 1

        total_count = len(student_answers)
        percentage = (obtained_marks / total_marks * 100) if total_marks > 0 else 0.0

        return {
            "obtained_marks": obtained_marks,
            "total_marks": total_marks,
            "correct_count": correct_count,
            "total_count": total_count,
            "percentage": round(percentage, 2),
        }

    except Exception as e:
        logger.error(f"Error calculating exam score: {str(e)}")
        return {
            "obtained_marks": 0,
            "total_marks": 0,
            "correct_count": 0,
            "total_count": 0,
            "percentage": 0.0,
        }
