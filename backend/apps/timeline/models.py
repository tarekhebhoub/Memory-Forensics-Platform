from __future__ import annotations

from django.db import models

from apps.cases.models import Case
from apps.evidence.models import Evidence


class TimelineEvent(models.Model):
    """A correlated forensic event used in the interactive timeline."""

    class Kind(models.TextChoices):
        PROCESS_CREATE = "process_create", "Process Created"
        PROCESS_EXIT = "process_exit", "Process Exited"
        SESSION = "session", "User Session"
        NETWORK = "network", "Network Activity"
        SERVICE = "service", "Service Event"
        MALWARE = "malware", "Malware Event"
        COMMAND = "command", "Command Execution"
        REGISTRY = "registry", "Registry Activity"
        OTHER = "other", "Other"

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="timeline_events")
    evidence = models.ForeignKey(Evidence, on_delete=models.CASCADE,
                                 related_name="timeline_events", null=True, blank=True)

    kind = models.CharField(max_length=24, choices=Kind.choices, db_index=True)
    occurred_at = models.DateTimeField(null=True, blank=True, db_index=True,
                                       help_text="Parsed UTC timestamp if available.")
    occurred_at_text = models.CharField(max_length=64, blank=True,
                                        help_text="Original timestamp string from Volatility.")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=16, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("occurred_at", "id")
        indexes = [models.Index(fields=("case", "kind"))]
