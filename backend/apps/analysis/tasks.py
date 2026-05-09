"""Celery tasks for asynchronous Volatility analysis."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from celery import shared_task
from django.db import transaction

from apps.audit.middleware import record as audit_record
from apps.cases.models import ChainOfCustody
from apps.evidence.models import Evidence
from apps.ioc.models import IOC
from apps.timeline.models import TimelineEvent

from .detection import DETECTORS, aggregate, correlate
from .models import AnalysisJob, PluginResult
from .summarizer import summarize_plugin
from .volatility import detect_os, run_plugin

logger = logging.getLogger("mfp.analysis.tasks")


@shared_task(bind=True, name="analysis.run_plugin", max_retries=0)
def run_plugin_task(self, plugin_result_id: int) -> dict:
    """Run a single plugin and persist its result."""
    pr = PluginResult.objects.select_related("job__evidence").get(pk=plugin_result_id)
    pr.status = PluginResult.Status.RUNNING
    pr.started_at = datetime.now(timezone.utc)
    pr.save(update_fields=["status", "started_at"])

    evidence = pr.job.evidence
    image = evidence.file_path

    run = run_plugin(image, pr.plugin_name)
    pr.duration_ms = run.duration_ms
    pr.raw_output = (run.raw_output or "")[:5_000_000]  # safety cap (~5MB text)
    pr.parsed_rows = run.rows
    pr.summary = summarize_plugin(pr.plugin_name, run.rows)
    pr.completed_at = datetime.now(timezone.utc)

    if run.ok:
        pr.status = PluginResult.Status.COMPLETED
    else:
        pr.status = PluginResult.Status.FAILED
        pr.error = run.error[:4000]

    pr.save()
    return {"plugin": pr.plugin_name, "status": pr.status, "rows": pr.row_count}


@shared_task(bind=True, name="analysis.run_job", max_retries=0)
def run_analysis_job(self, job_id: int) -> dict:
    """Run all plugins in a job sequentially, then post-process detections + IOCs."""
    job = AnalysisJob.objects.select_related("evidence", "evidence__case").get(pk=job_id)
    evidence = job.evidence

    job.status = AnalysisJob.Status.RUNNING
    job.started_at = datetime.now(timezone.utc)
    job.save(update_fields=["status", "started_at"])

    evidence.status = Evidence.Status.ANALYZING
    evidence.save(update_fields=["status"])

    # OS detection up-front
    try:
        job.detected_os = detect_os(evidence.file_path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("OS detection failed")
        job.detected_os = "unknown"
    job.save(update_fields=["detected_os"])

    failures = 0
    for pr in job.plugin_results.all():
        try:
            run_plugin_task.run(pr.id)  # synchronous within this worker
        except Exception as exc:  # noqa: BLE001
            logger.exception("Plugin %s failed", pr.plugin_name)
            pr.status = PluginResult.Status.FAILED
            pr.error = str(exc)[:4000]
            pr.save()
            failures += 1

    # Post-processing — detections & IOC extraction
    detections = _post_process(job)
    job.risk_score = aggregate(detections)

    total       = job.plugin_results.count()
    completed   = job.plugin_results.filter(status=PluginResult.Status.COMPLETED).count()
    failed      = job.plugin_results.filter(status=PluginResult.Status.FAILED).count()

    if total == 0:
        job.status = AnalysisJob.Status.FAILED
    elif completed == 0:
        job.status = AnalysisJob.Status.FAILED
    elif failed == 0:
        job.status = AnalysisJob.Status.COMPLETED
    else:
        job.status = AnalysisJob.Status.PARTIAL

    job.completed_at = datetime.now(timezone.utc)
    job.save()

    evidence.status = Evidence.Status.ANALYZED
    evidence.last_analyzed_at = datetime.now(timezone.utc)
    evidence.save(update_fields=["status", "last_analyzed_at"])

    ChainOfCustody.objects.create(
        case=evidence.case, actor=job.requested_by,
        actor_username=getattr(job.requested_by, "username", "system"),
        action=ChainOfCustody.Action.ANALYSIS_RUN,
        description=f"Analysis job {job.uid} completed with status={job.status}, "
                    f"risk={job.risk_score}.",
        metadata={"job_id": job.id, "plugins": job.plugins, "risk_score": job.risk_score},
    )
    audit_record("analysis.complete", actor=job.requested_by, target=job, severity="notice",
                 metadata={"risk_score": job.risk_score, "status": job.status})
    return {"job": job.id, "status": job.status, "risk_score": job.risk_score}


@transaction.atomic
def _post_process(job: AnalysisJob):
    """Run detection rules + cross-plugin correlation, persist detections + IOCs."""
    all_detections = []
    plugin_rows: dict[str, list] = {}

    for pr in job.plugin_results.all():
        if pr.status != PluginResult.Status.COMPLETED:
            continue
        plugin_rows[pr.plugin_name] = pr.parsed_rows or []

        det_fn = DETECTORS.get(pr.plugin_name)
        if not det_fn:
            continue
        try:
            dets = det_fn(pr.parsed_rows or [])
        except Exception:  # noqa: BLE001
            logger.exception("Detector for %s crashed", pr.plugin_name)
            continue
        all_detections.extend(dets)

    # Cross-plugin correlation
    try:
        all_detections.extend(correlate(plugin_rows))
    except Exception:  # noqa: BLE001
        logger.exception("Cross-plugin correlation crashed")

    # Persist detections + IOCs
    distinct_techniques: set[str] = set()
    serialized: list[dict] = []
    for d in all_detections:
        distinct_techniques.update(d.mitre or [])
        serialized.append({
            "plugin": d.plugin, "severity": d.severity, "score": d.score,
            "title": d.title, "message": d.message, "evidence": d.evidence,
            "mitre": d.mitre, "pid": d.pid,
        })
        ev = d.evidence
        ioc_kind, ioc_value = _ioc_from_detection(d.plugin, ev)
        if not ioc_value:
            continue
        IOC.objects.update_or_create(
            case=job.evidence.case, kind=ioc_kind, value=ioc_value,
            defaults={
                "severity": d.severity,
                "source_plugin": d.plugin,
                "description": d.message,
                "evidence": ev,
                "first_seen_evidence": job.evidence,
                "mitre_techniques": list(d.mitre or []),
            },
        )

    job.detections = serialized
    job.mitre_techniques = sorted(distinct_techniques)
    # `risk_score` and `save` happen in the caller, but persist these fields now too:
    job.save(update_fields=["detections", "mitre_techniques"])

    _emit_timeline(job)
    return all_detections


def _ioc_from_detection(plugin: str, ev: dict) -> tuple[str, str]:
    """Map a detection's evidence dict to a canonical IOC (kind, value)."""
    if not isinstance(ev, dict):
        return ("", "")
    if "foreign" in ev and ev.get("foreign"):
        return ("ip", str(ev["foreign"]))
    if "binary" in ev and ev.get("binary"):
        return ("path", str(ev["binary"]))
    if "dll" in ev and ev.get("dll"):
        return ("path", str(ev["dll"]))
    if "path" in ev and ev.get("path"):
        return ("path", str(ev["path"]))
    if "module" in ev and ev.get("module"):
        return ("other", f"module:{ev['module']}")
    if "name" in ev and ev.get("name"):
        if plugin == "windows.mutantscan":
            return ("other", f"mutex:{ev['name']}")
        return ("process", str(ev["name"]))
    if "process" in ev and ev.get("process"):
        return ("process", str(ev["process"]))
    if "cmdline" in ev and ev.get("cmdline"):
        return ("other", f"cmdline:{str(ev['cmdline'])[:480]}")
    return ("", "")


def _emit_timeline(job: AnalysisJob) -> None:
    """Create timeline events from pslist + netscan + svcscan."""
    case = job.evidence.case
    bulk: list[TimelineEvent] = []

    pslist = job.plugin_results.filter(plugin_name="windows.pslist").first()
    if pslist:
        for r in pslist.parsed_rows or []:
            ts = r.get("CreateTime") or r.get("Created") or r.get("create_time")
            if not ts:
                continue
            bulk.append(TimelineEvent(
                case=case, evidence=job.evidence,
                kind=TimelineEvent.Kind.PROCESS_CREATE,
                occurred_at_text=str(ts)[:64],
                title=str(r.get("ImageFileName") or r.get("Name") or "process")[:200],
                description=f"PID {r.get('PID') or r.get('Pid')} "
                            f"PPID {r.get('PPID') or r.get('Ppid')}",
                metadata=r,
            ))

    netscan = job.plugin_results.filter(plugin_name="windows.netscan").first()
    if netscan:
        for r in netscan.parsed_rows or []:
            foreign = r.get("ForeignAddr") or r.get("ForeignAddress")
            if not foreign or foreign in ("*", "::", "0.0.0.0"):
                continue
            bulk.append(TimelineEvent(
                case=case, evidence=job.evidence,
                kind=TimelineEvent.Kind.NETWORK,
                occurred_at_text=str(r.get("Created") or "")[:64],
                title=f"{r.get('Owner') or 'process'} → {foreign}:{r.get('ForeignPort')}",
                description=f"{r.get('State')} {r.get('Proto', '')}",
                metadata=r,
            ))

    svcscan = job.plugin_results.filter(plugin_name="windows.svcscan").first()
    if svcscan:
        for r in svcscan.parsed_rows or []:
            name = r.get("Name") or r.get("ServiceName")
            if not name:
                continue
            bulk.append(TimelineEvent(
                case=case, evidence=job.evidence,
                kind=TimelineEvent.Kind.SERVICE,
                occurred_at_text="",
                title=str(name)[:200],
                description=f"State={r.get('State')} Start={r.get('Start')} "
                            f"Bin={r.get('Binary') or r.get('BinaryPath')}",
                metadata=r,
            ))

    if bulk:
        TimelineEvent.objects.bulk_create(bulk, batch_size=500)
