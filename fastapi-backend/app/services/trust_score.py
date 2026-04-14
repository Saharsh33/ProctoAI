"""
Trust Score Calculator (Sprint 4 – REQ-11).

Formula:
    trustScore = max(0, 100 − Σ(weight × count))

Severity weights (from requirements):
    face_absent       = 30
    multiple_faces    = 40
    tab_switch        = 20
    audio_violation   = 10

The calculator queries the violations table, groups by type, and
computes the weighted penalty.  It is called by the Report Generator
and can also be invoked standalone via the API.
"""

from __future__ import annotations

import logging
from collections import Counter

from app.models.violation import Violation
from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Severity weight map (REQ-11) ──────────────────────
VIOLATION_WEIGHTS: dict[str, int] = {
    "identity_mismatch": 20,  # HIGH severity
    "multiple_faces": 30,  # HIGH severity
    "tab_switch": 15,  # MEDIUM severity
    "face_absent": 25,  # HIGH severity
    "audio_violation": 10,  # LOW severity
}

VIOLATION_SEVERITY: dict[str, str] = {
    "identity_mismatch": "HIGH",
    "multiple_faces": "HIGH",
    "tab_switch": "MEDIUM",
    "face_absent": "HIGH",
    "audio_violation": "LOW",
}

DEFAULT_WEIGHT = 5  # unknown violation types get a small penalty


def get_violation_counts(
    db: Session,
    test_id: str,
    email: str,
) -> dict[str, int]:
    """Return {violation_type: count} for a student's exam session."""
    stmt = (
        select(Violation.violation_type, sa_func.count())
        .where(Violation.test_id == test_id, Violation.email == email)
        .group_by(Violation.violation_type)
    )
    rows = db.execute(stmt).all()
    return {vtype: cnt for vtype, cnt in rows}


def calculate_trust_score(
    db: Session,
    test_id: str,
    email: str,
) -> dict:
    """
    Calculate the trust score for a student on a specific exam.

    Returns a dict with:
        trust_score    – int  0-100
        penalty        – int  total deducted
        breakdown      – list of {type, count, weight, severity, subtotal}
        total_violations – int
    """
    counts = get_violation_counts(db, test_id, email)
    total_violations = sum(counts.values())

    breakdown = []
    penalty = 0
    for vtype, count in counts.items():
        weight = VIOLATION_WEIGHTS.get(vtype, DEFAULT_WEIGHT)
        severity = VIOLATION_SEVERITY.get(vtype, "UNKNOWN")
        subtotal = weight * count
        penalty += subtotal
        breakdown.append(
            {
                "type": vtype,
                "count": count,
                "weight": weight,
                "severity": severity,
                "subtotal": subtotal,
            }
        )

    # Sort breakdown by subtotal descending for readability
    breakdown.sort(key=lambda x: x["subtotal"], reverse=True)

    trust_score = max(0, 100 - penalty)

    logger.info(
        "Trust score for %s on exam %s: %d (penalty=%d, violations=%d)",
        email,
        test_id,
        trust_score,
        penalty,
        total_violations,
    )

    return {
        "trust_score": trust_score,
        "penalty": penalty,
        "total_violations": total_violations,
        "breakdown": breakdown,
    }
