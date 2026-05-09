"""Audit log models — immutable, append-only event trail."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """A single auditable platform event."""

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        NOTICE = "notice", "Notice"
        WARNING = "warning", "Warning"
        ALERT = "alert", "Alert"

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="audit_events",
    )
    actor_username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=64, db_index=True, help_text="e.g. case.create, evidence.upload")
    target_type = models.CharField(max_length=64, blank=True, db_index=True)
    target_id = models.CharField(max_length=64, blank=True, db_index=True)
    method = models.CharField(max_length=8, blank=True)
    path = models.CharField(max_length=512, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.INFO)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-timestamp",)
        indexes = [
            models.Index(fields=("action", "-timestamp")),
            models.Index(fields=("target_type", "target_id")),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.actor_username or '-'} {self.action}"
