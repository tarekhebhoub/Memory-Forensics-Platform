from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.cases.models import Case


class Report(models.Model):
    """Generated forensic report."""

    class Format(models.TextChoices):
        PDF = "pdf", "PDF"
        HTML = "html", "HTML"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        GENERATING = "generating", "Generating"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="reports")
    title = models.CharField(max_length=200)
    format = models.CharField(max_length=8, choices=Format.choices, default=Format.PDF)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="reports_created",
    )
    file_path = models.CharField(max_length=1024, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
