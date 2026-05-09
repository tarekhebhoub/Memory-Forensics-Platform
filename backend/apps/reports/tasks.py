"""Reports Celery task + service helpers."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task

from apps.cases.models import ChainOfCustody

from .engine import write_report
from .models import Report

logger = logging.getLogger("mfp.reports")


@shared_task(bind=True, name="reports.generate")
def generate_report_task(self, report_id: int) -> dict:
    report = Report.objects.select_related("case", "created_by").get(pk=report_id)
    report.status = Report.Status.GENERATING
    report.save(update_fields=["status"])
    try:
        path = write_report(report)
        size = Path(path).stat().st_size
        report.file_path = path
        report.size_bytes = size
        report.status = Report.Status.READY
        report.completed_at = datetime.now(timezone.utc)
        report.save()

        ChainOfCustody.objects.create(
            case=report.case, actor=report.created_by,
            actor_username=getattr(report.created_by, "username", "system"),
            action=ChainOfCustody.Action.REPORT_GENERATED,
            description=f"Report '{report.title}' ({report.format}) generated.",
            metadata={"report_id": report.id, "size_bytes": size},
        )
        return {"report": report.id, "status": "ready", "size": size}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Report generation failed")
        report.status = Report.Status.FAILED
        report.error = str(exc)[:4000]
        report.save(update_fields=["status", "error"])
        raise
