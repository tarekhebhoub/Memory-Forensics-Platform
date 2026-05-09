"""Evidence (memory dump) models."""
from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from apps.cases.models import Case


def evidence_storage_path(instance: "Evidence", filename: str) -> str:  # pragma: no cover
    """Returns relative path used by Django's default file storage."""
    return f"evidence/{instance.case.uid}/{instance.uid}/{filename}"


class Evidence(models.Model):
    """A single piece of evidence — typically a memory dump."""

    class Kind(models.TextChoices):
        MEMORY_DUMP = "memory_dump", "Memory Dump"
        DISK_IMAGE = "disk_image", "Disk Image"
        ARTIFACT = "artifact", "Artifact"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        UPLOADED = "uploaded", "Uploaded"
        VERIFIED = "verified", "Verified"
        ANALYZING = "analyzing", "Analyzing"
        ANALYZED = "analyzed", "Analyzed"
        FAILED = "failed", "Failed"
        QUARANTINED = "quarantined", "Quarantined"

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="evidence")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.MEMORY_DUMP)

    name = models.CharField(max_length=255, help_text="Original filename")
    description = models.TextField(blank=True)

    file_path = models.CharField(max_length=1024, blank=True,
                                 help_text="Absolute path on disk in EVIDENCE_ROOT")
    size_bytes = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=128, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    md5 = models.CharField(max_length=32, blank=True)

    os_profile_hint = models.CharField(max_length=64, blank=True,
                                       help_text="Optional OS hint, e.g. windows, linux, mac")

    status = models.CharField(max_length=16, choices=Status.choices,
                              default=Status.UPLOADING, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="evidence_uploads",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    last_analyzed_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-uploaded_at",)
        indexes = [models.Index(fields=("case", "status"))]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.case.code})"

    @property
    def absolute_path(self) -> str:
        return self.file_path

    @property
    def exists_on_disk(self) -> bool:
        return bool(self.file_path) and Path(self.file_path).exists()


class UploadSession(models.Model):
    """Tracks a chunked upload session for very large memory dumps."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"
        ABORTED = "aborted", "Aborted"

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="upload_sessions")
    filename = models.CharField(max_length=255)
    total_size = models.BigIntegerField()
    chunk_size = models.IntegerField(default=8 * 1024 * 1024)
    received_bytes = models.BigIntegerField(default=0)
    received_chunks = models.IntegerField(default=0)
    expected_sha256 = models.CharField(max_length=64, blank=True)
    final_sha256 = models.CharField(max_length=64, blank=True)
    storage_path = models.CharField(max_length=1024)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="upload_sessions",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-started_at",)

    @property
    def progress(self) -> float:
        return round(self.received_bytes / self.total_size * 100, 2) if self.total_size else 0.0
