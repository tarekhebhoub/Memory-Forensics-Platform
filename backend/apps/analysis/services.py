"""Service layer for analysis orchestration."""
from __future__ import annotations

from django.conf import settings
from django.db import transaction

from apps.evidence.models import Evidence

from .models import AnalysisJob, PluginResult


@transaction.atomic
def enqueue_full_analysis(*, evidence: Evidence, requested_by,
                          plugins: list[str] | None = None,
                          mode: str = "standard") -> AnalysisJob:
    """Create an `AnalysisJob` and dispatch it to Celery.

    `mode` may be ``"standard"`` (default 11-plugin set) or ``"deep"`` (full
    kernel + persistence + credential plugin sweep).  An explicit ``plugins``
    list overrides the mode preset.
    """
    if plugins is None:
        if mode == "deep":
            plugins = list(settings.VOLATILITY_PLUGINS_DEEP)
        else:
            plugins = list(settings.VOLATILITY_PLUGINS)

    job_mode = (AnalysisJob.Mode.DEEP if mode == "deep"
                else AnalysisJob.Mode.STANDARD)

    job = AnalysisJob.objects.create(
        evidence=evidence, requested_by=requested_by, plugins=plugins,
        status=AnalysisJob.Status.QUEUED, mode=job_mode,
    )
    for name in plugins:
        PluginResult.objects.create(job=job, plugin_name=name)

    from .tasks import run_analysis_job
    run_analysis_job.delay(job.id)
    return job
