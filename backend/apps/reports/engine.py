"""Report generation engine — produces HTML (Jinja2) and PDF (ReportLab) reports."""
from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from jinja2 import Environment, FileSystemLoader, select_autoescape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak,
)

from apps.cases.models import Case

logger = logging.getLogger("mfp.reports")

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_jinja = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True, lstrip_blocks=True,
)


# ──────────────────── Data assembly ────────────────────
def gather_case_context(case: Case) -> dict:
    """Pull together everything needed for a comprehensive case report."""
    evidence_qs = case.evidence.all()
    iocs = list(case.iocs.all().order_by("-severity", "kind"))
    timeline_qs = case.timeline_events.all()[:500]

    jobs = []
    detections_count = 0
    risk_max = 0
    for ev in evidence_qs:
        for job in ev.analysis_jobs.all().order_by("-created_at"):
            jobs.append(job)
            risk_max = max(risk_max, job.risk_score)

    detections_count = sum(1 for _ in iocs)

    return {
        "case": case,
        "now": datetime.now(timezone.utc),
        "evidence_list": list(evidence_qs),
        "analysis_jobs": jobs,
        "iocs": iocs,
        "timeline": list(timeline_qs),
        "summary": {
            "evidence_count": evidence_qs.count(),
            "ioc_count": detections_count,
            "max_risk_score": risk_max,
            "severity_counts": _severity_counts(iocs),
        },
    }


def _severity_counts(iocs):
    counts = {"info": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}
    for i in iocs:
        counts[i.severity] = counts.get(i.severity, 0) + 1
    return counts


# ──────────────────── HTML ────────────────────
def render_html(case: Case) -> bytes:
    ctx = gather_case_context(case)
    tmpl = _jinja.get_template("report.html")
    return tmpl.render(**ctx).encode("utf-8")


# ──────────────────── PDF ────────────────────
def render_pdf(case: Case) -> bytes:
    ctx = gather_case_context(case)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"Forensic Report — {case.code}",
        author="Memory Forensics Platform",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], textColor=colors.HexColor("#0f172a"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=colors.HexColor("#1e293b"))
    body = styles["BodyText"]
    small = ParagraphStyle("Small", parent=body, fontSize=8, textColor=colors.grey)

    story = []

    # Cover
    story.append(Paragraph("Memory Forensics Investigation Report", h1))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(f"<b>Case:</b> {case.code} — {case.title}", body))
    story.append(Paragraph(f"<b>Severity:</b> {case.get_severity_display()} &nbsp; "
                           f"<b>Status:</b> {case.get_status_display()}", body))
    story.append(Paragraph(f"<b>Generated:</b> {ctx['now']:%Y-%m-%d %H:%M UTC}", body))
    story.append(Paragraph(f"<b>Lead analyst:</b> "
                           f"{getattr(case.lead_analyst, 'username', '—')}", body))
    if case.classification:
        story.append(Paragraph(f"<b>Classification:</b> {case.classification}", body))
    story.append(Spacer(1, 0.6 * cm))

    # Executive summary
    story.append(Paragraph("Executive Summary", h2))
    s = ctx["summary"]
    story.append(Paragraph(
        f"This report covers <b>{s['evidence_count']}</b> piece(s) of evidence and "
        f"<b>{s['ioc_count']}</b> indicator(s) of compromise. "
        f"The maximum aggregate risk score across all analyses is "
        f"<b>{s['max_risk_score']}/100</b>.",
        body))
    sev = s["severity_counts"]
    story.append(Paragraph(
        f"Severity breakdown — Critical: {sev['critical']}, High: {sev['high']}, "
        f"Medium: {sev['medium']}, Low: {sev['low']}, Info: {sev['info']}.",
        body))
    story.append(Spacer(1, 0.4 * cm))

    # Evidence
    story.append(Paragraph("Evidence", h2))
    if ctx["evidence_list"]:
        rows = [["Name", "Size (MB)", "SHA-256", "Status", "Uploaded"]]
        for ev in ctx["evidence_list"]:
            rows.append([
                ev.name,
                f"{ev.size_bytes / (1024*1024):.1f}",
                ev.sha256[:16] + "…" if ev.sha256 else "",
                ev.get_status_display(),
                ev.uploaded_at.strftime("%Y-%m-%d %H:%M"),
            ])
        story.append(_table(rows))
    else:
        story.append(Paragraph("No evidence attached.", body))
    story.append(Spacer(1, 0.4 * cm))

    # Analyses
    story.append(Paragraph("Analyses", h2))
    if ctx["analysis_jobs"]:
        rows = [["Evidence", "OS", "Status", "Risk", "Plugins", "Completed"]]
        for j in ctx["analysis_jobs"]:
            rows.append([
                j.evidence.name,
                j.detected_os or "—",
                j.get_status_display(),
                str(j.risk_score),
                str(len(j.plugins)),
                j.completed_at.strftime("%Y-%m-%d %H:%M") if j.completed_at else "—",
            ])
        story.append(_table(rows))
    else:
        story.append(Paragraph("No analyses run yet.", body))
    story.append(Spacer(1, 0.4 * cm))

    # IOCs
    story.append(PageBreak())
    story.append(Paragraph("Indicators of Compromise", h2))
    if ctx["iocs"]:
        rows = [["Kind", "Value", "Severity", "Confidence", "Source"]]
        for i in ctx["iocs"][:200]:
            rows.append([
                i.get_kind_display(), i.value[:60],
                i.severity.upper(), str(i.confidence),
                i.source_plugin or "—",
            ])
        story.append(_table(rows))
    else:
        story.append(Paragraph("No IOCs identified.", body))
    story.append(Spacer(1, 0.4 * cm))

    # Timeline
    story.append(Paragraph("Timeline (top 50)", h2))
    if ctx["timeline"]:
        rows = [["When", "Kind", "Title"]]
        for t in ctx["timeline"][:50]:
            rows.append([
                t.occurred_at_text or (t.occurred_at and t.occurred_at.isoformat()) or "—",
                t.get_kind_display(),
                t.title[:80],
            ])
        story.append(_table(rows))
    else:
        story.append(Paragraph("No timeline events.", body))

    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph("— Generated by Memory Forensics Platform —", small))

    doc.build(story)
    return buffer.getvalue()


def _table(rows):
    t = Table(rows, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.whitesmoke, colors.HexColor("#f1f5f9")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ──────────────────── Persistence ────────────────────
def write_report(report) -> str:
    """Render and write the report file. Returns absolute path."""
    case = report.case
    out_dir = Path(settings.REPORT_ROOT) / str(case.uid)
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{case.code}-{report.uid}.{report.format}"
    out = out_dir / fname

    if report.format == report.Format.PDF:
        out.write_bytes(render_pdf(case))
    else:
        out.write_bytes(render_html(case))
    return str(out)
