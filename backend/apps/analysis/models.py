"""Analysis-result data model.

We deliberately store plugin output in three forms:
* `raw_output`   — Volatility's raw text (always preserved).
* `parsed_rows`  — JSON list-of-records, easy to render as a table.
* `summary`      — Aggregate counts / interesting metrics.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.evidence.models import Evidence


class AnalysisJob(models.Model):
    """One full analysis run over a piece of evidence (a batch of plugins)."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    evidence = models.ForeignKey(Evidence, on_delete=models.CASCADE, related_name="analysis_jobs")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="analysis_jobs",
    )
    plugins = models.JSONField(default=list,
                               help_text="List of Volatility 3 plugin names to run.")
    status = models.CharField(max_length=16, choices=Status.choices,
                              default=Status.QUEUED, db_index=True)
    error = models.TextField(blank=True)

    class Mode(models.TextChoices):
        STANDARD = "standard", "Standard"
        DEEP = "deep", "Deep"

    mode = models.CharField(max_length=16, choices=Mode.choices,
                            default=Mode.STANDARD, db_index=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    detected_os = models.CharField(max_length=64, blank=True)
    risk_score = models.IntegerField(default=0,
                                     help_text="0–100 aggregate maliciousness score.")
    detections = models.JSONField(default=list, blank=True,
                                  help_text="Persisted Detection records (post-processing).")
    mitre_techniques = models.JSONField(default=list, blank=True,
                                        help_text="Distinct ATT&CK technique IDs across all detections.")

    class Meta:
        ordering = ("-created_at",)


class PluginResult(models.Model):
    """Result of a single Volatility plugin invocation."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    job = models.ForeignKey(AnalysisJob, on_delete=models.CASCADE, related_name="plugin_results")
    plugin_name = models.CharField(max_length=128, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(default=0)
    error = models.TextField(blank=True)

    raw_output = models.TextField(blank=True)
    parsed_rows = models.JSONField(default=list, blank=True)
    summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("plugin_name",)
        unique_together = ("job", "plugin_name")
        indexes = [models.Index(fields=("plugin_name", "status"))]

    @property
    def row_count(self) -> int:
        return len(self.parsed_rows) if isinstance(self.parsed_rows, list) else 0
