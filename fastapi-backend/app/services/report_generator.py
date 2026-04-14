"""
Exam Report Generator (Sprint 4 – REQ-12).

Provides:
  • generateReport() – aggregates score, violation counts, trust score
    and persists an ExamReport row.
  • exportPDF()       – renders a professional PDF via ReportLab.
  • Target: report available within 2 s of exam end.
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from sqlalchemy.orm import Session

from app.services.trust_score import calculate_trust_score
from app.services.score_calculator import calculate_exam_score
from app.crud.report import create as create_report, get_by_exam_and_email, update_pdf_path
from app.models.exam_report import ExamReport

logger = logging.getLogger(__name__)

# Directory for generated PDFs
PDF_DIR = Path(os.getenv("PDF_REPORT_DIR", "reports"))
PDF_DIR.mkdir(parents=True, exist_ok=True)


# ── Report generation ──────────────────────────────────

def generate_report(
    db: Session,
    test_id: str,
    email: str,
    uid: str,
    exam_title: str = "",
) -> ExamReport:
    """
    Generate (or regenerate) a proctoring report for a student exam session.

    1. Calculate trust score from violations table
    2. Calculate exam marks (obtained vs total)
    3. Build human-readable summary
    4. Persist ExamReport row
    5. Generate PDF and store path
    6. Return the ExamReport object

    Target: < 2 s total.
    """
    t0 = time.monotonic()

    # 1. Trust score
    score_data = calculate_trust_score(db, test_id, email)

    # 2. Calculate exam marks
    marks_data = calculate_exam_score(db, uid, test_id)

    # 3. Summary text
    summary = _build_summary(email, test_id, exam_title, score_data, marks_data)

    # 4. Check if report already exists (regenerate case)
    existing = get_by_exam_and_email(db, test_id, email)
    if existing:
        existing.trust_score = score_data["trust_score"]
        existing.total_violations = score_data["total_violations"]
        existing.penalty = score_data["penalty"]
        existing.violation_breakdown_json = json.dumps(score_data["breakdown"])
        existing.obtained_marks = marks_data["obtained_marks"]
        existing.total_marks = marks_data["total_marks"]
        existing.summary = summary
        db.commit()
        db.refresh(existing)
        report = existing
    else:
        report = create_report(
            db,
            test_id=test_id,
            email=email,
            uid=uid,
            trust_score=score_data["trust_score"],
            total_violations=score_data["total_violations"],
            penalty=score_data["penalty"],
            violation_breakdown_json=json.dumps(score_data["breakdown"]),
            obtained_marks=marks_data["obtained_marks"],
            total_marks=marks_data["total_marks"],
            summary=summary,
        )

    # 5. Generate PDF
    pdf_path = export_pdf(report, exam_title, score_data, marks_data)
    update_pdf_path(db, report.report_id, str(pdf_path))
    report.pdf_path = str(pdf_path)

    elapsed_ms = (time.monotonic() - t0) * 1000
    logger.info(
        "Report generated for %s on exam %s in %.0f ms (trust_score=%d, marks=%d/%d)",
        email, test_id, elapsed_ms, score_data["trust_score"],
        marks_data["obtained_marks"], marks_data["total_marks"],
    )

    return report


# ── PDF export via ReportLab ───────────────────────────

def export_pdf(
    report: ExamReport,
    exam_title: str,
    score_data: dict,
    marks_data: dict | None = None,
) -> Path:
    """
    Render a professional PDF proctoring report.
    Returns the path to the generated file.
    """
    filename = f"report_{report.test_id}_{report.email.replace('@', '_at_')}_{report.report_id}.pdf"
    filepath = PDF_DIR / filename

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Heading1"],
        fontSize=22,
        spaceAfter=6,
        textColor=colors.HexColor("#4f46e5"),
    ))
    styles.add(ParagraphStyle(
        name="SectionHead",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=14,
        spaceAfter=6,
        textColor=colors.HexColor("#1e293b"),
    ))
    styles.add(ParagraphStyle(
        name="Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    ))

    elements: list = []

    # ── Header ──
    elements.append(Paragraph("ProctoAI – Proctoring Report", styles["ReportTitle"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    elements.append(Spacer(1, 8))

    # ── Metadata table ──
    meta_data = [
        ["Exam", exam_title or report.test_id],
        ["Student", report.email],
        ["Generated", report.generated_at.strftime("%Y-%m-%d %H:%M:%S") if report.generated_at else datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Report ID", str(report.report_id)],
    ]
    meta_table = Table(meta_data, colWidths=[90, 380])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#64748b")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 12))

    # ── Trust Score ──
    elements.append(Paragraph("Trust Score", styles["SectionHead"]))
    trust = score_data["trust_score"]
    trust_color = "#10b981" if trust >= 70 else "#f59e0b" if trust >= 40 else "#ef4444"
    elements.append(Paragraph(
        f'<font size="28" color="{trust_color}"><b>{trust}</b></font>'
        f'<font size="12" color="#94a3b8"> / 100</font>'
        f'&nbsp;&nbsp;&nbsp;<font size="10" color="#64748b">'
        f'(penalty: −{score_data["penalty"]}  |  violations: {score_data["total_violations"]})</font>',
        styles["Body"],
    ))
    elements.append(Spacer(1, 10))

    # ── Exam Marks ──
    if marks_data and marks_data.get("total_marks", 0) > 0:
        elements.append(Paragraph("Exam Performance", styles["SectionHead"]))
        obtained = marks_data["obtained_marks"]
        total_marks = marks_data["total_marks"]
        percentage = marks_data.get("percentage", 0)
        correct = marks_data.get("correct_count", 0)
        total_questions = marks_data.get("total_count", 0)
        
        marks_color = "#10b981" if percentage >= 70 else "#f59e0b" if percentage >= 40 else "#ef4444"
        elements.append(Paragraph(
            f'<font size="24" color="{marks_color}"><b>{obtained}</b></font>'
            f'<font size="12" color="#94a3b8"> / {total_marks}</font>'
            f'&nbsp;&nbsp;&nbsp;<font size="10" color="#64748b">'
            f'({percentage}%  |  {correct}/{total_questions} correct)</font>',
            styles["Body"],
        ))
        elements.append(Spacer(1, 10))

    # ── Violation Breakdown Table ──
    elements.append(Paragraph("Violation Breakdown", styles["SectionHead"]))

    breakdown = score_data.get("breakdown", [])
    if breakdown:
        table_data = [["Violation Type", "Count", "Weight", "Penalty"]]
        for item in breakdown:
            table_data.append([
                item["type"].replace("_", " ").title(),
                str(item["count"]),
                str(item["weight"]),
                f'−{item["subtotal"]}',
            ])
        table_data.append(["", "", "Total", f'−{score_data["penalty"]}'])

        t = Table(table_data, colWidths=[180, 70, 70, 80])
        t.setStyle(TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            # Body
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#f8fafc"), colors.white]),
            # Total row
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph(
            '<font color="#10b981">No violations recorded – excellent conduct.</font>',
            styles["Body"],
        ))

    elements.append(Spacer(1, 14))

    # ── Summary ──
    elements.append(Paragraph("Summary", styles["SectionHead"]))
    elements.append(Paragraph(report.summary or "No summary available.", styles["Body"]))

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        '<font size="8" color="#94a3b8">Generated by ProctoAI – AI-powered proctoring platform</font>',
        styles["Body"],
    ))

    # Build PDF
    doc.build(elements)

    # Write to file
    filepath.write_bytes(buf.getvalue())
    logger.info("PDF written to %s (%d bytes)", filepath, filepath.stat().st_size)

    return filepath


# ── Helpers ────────────────────────────────────────────

def _build_summary(email: str, test_id: str, exam_title: str, score_data: dict, marks_data: dict | None = None) -> str:
    """Generate a human-readable summary paragraph."""
    trust = score_data["trust_score"]
    total = score_data["total_violations"]
    breakdown = score_data.get("breakdown", [])

    # Build summary with marks if available
    marks_str = ""
    if marks_data and marks_data.get("total_marks", 0) > 0:
        obtained = marks_data["obtained_marks"]
        total_marks = marks_data["total_marks"]
        percentage = marks_data.get("percentage", 0)
        marks_str = f" Obtained marks: {obtained}/{total_marks} ({percentage}%)."

    if total == 0:
        return (
            f"Student {email} completed exam '{exam_title or test_id}' with no violations. "
            f"Trust score: {trust}/100. Excellent conduct throughout the session.{marks_str}"
        )

    parts = [
        f"Student {email} completed exam '{exam_title or test_id}' with a trust score of {trust}/100.{marks_str}",
        f"A total of {total} violation(s) were detected during the session.",
    ]

    for item in breakdown:
        vtype = item["type"].replace("_", " ")
        parts.append(f"  • {vtype}: {item['count']} occurrence(s) (−{item['subtotal']} points)")

    if trust >= 70:
        parts.append("Overall conduct is acceptable, though some minor issues were flagged.")
    elif trust >= 40:
        parts.append("Conduct requires review – multiple violations detected.")
    else:
        parts.append("Low trust score – the session may require manual investigation.")

    return " ".join(parts)
