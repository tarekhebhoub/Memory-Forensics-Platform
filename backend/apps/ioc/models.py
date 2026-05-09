"""Indicators of Compromise (IOCs)."""
from __future__ import annotations

from django.db import models

from apps.cases.models import Case


class IOC(models.Model):
    """Single indicator extracted/observed during investigation."""

    class Kind(models.TextChoices):
        IP = "ip", "IP Address"
        DOMAIN = "domain", "Domain"
        URL = "url", "URL"
        HASH_MD5 = "md5", "MD5 Hash"
        HASH_SHA1 = "sha1", "SHA-1 Hash"
        HASH_SHA256 = "sha256", "SHA-256 Hash"
        PATH = "path", "File Path"
        PROCESS = "process", "Process"
        REGISTRY = "registry", "Registry Key"
        EMAIL = "email", "Email Address"
        OTHER = "other", "Other"

    SEVERITY_CHOICES = [
        ("info", "Info"), ("low", "Low"), ("medium", "Medium"),
        ("high", "High"), ("critical", "Critical"),
    ]

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="iocs")
    kind = models.CharField(max_length=16, choices=Kind.choices, db_index=True)
    value = models.CharField(max_length=512, db_index=True)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="medium")
    confidence = models.PositiveSmallIntegerField(default=70, help_text="0–100 confidence")
    description = models.TextField(blank=True)
    source_plugin = models.CharField(max_length=128, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=list, blank=True)
    mitre_techniques = models.JSONField(default=list, blank=True,
                                        help_text="e.g. ['T1055', 'T1003.001']")

    first_seen_evidence = models.ForeignKey(
        "evidence.Evidence", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="iocs",
    )
    discovered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-discovered_at",)
        unique_together = ("case", "kind", "value")
        indexes = [models.Index(fields=("kind", "value"))]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.kind}:{self.value}"
