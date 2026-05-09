"""Case / investigation management models."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Case(models.Model):
    """A forensic investigation / incident."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        ON_HOLD = "on_hold", "On Hold"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    code = models.CharField(max_length=32, unique=True, help_text="Human-readable case code, e.g. INC-2026-0001")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.MEDIUM, db_index=True)
    classification = models.CharField(max_length=64, blank=True, help_text="TLP / sensitivity tag, e.g. TLP:AMBER")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="cases_created",
    )
    lead_analyst = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cases_led",
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="cases_assigned",
    )

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    tags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("-opened_at",)
        indexes = [models.Index(fields=("status", "severity"))]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} – {self.title}"


class CaseNote(models.Model):
    """Free-form investigation note attached to a case."""
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="case_notes",
    )
    body = models.TextField()
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-pinned", "-created_at")


class ChainOfCustody(models.Model):
    """Chain-of-custody log entry. Append-only, never edited after creation."""

    class Action(models.TextChoices):
        CREATED = "created", "Created"
        ASSIGNED = "assigned", "Assigned"
        TRANSFERRED = "transferred", "Transferred"
        EVIDENCE_ADDED = "evidence_added", "Evidence Added"
        EVIDENCE_REMOVED = "evidence_removed", "Evidence Removed"
        ANALYSIS_RUN = "analysis_run", "Analysis Run"
        REPORT_GENERATED = "report_generated", "Report Generated"
        STATUS_CHANGED = "status_changed", "Status Changed"
        CLOSED = "closed", "Closed"
        REOPENED = "reopened", "Reopened"

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="custody_log")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="custody_actions",
    )
    actor_username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=32, choices=Action.choices)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-timestamp",)
