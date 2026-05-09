from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.cases.models import Case


class AIInsight(models.Model):
    """An AI-generated finding / explanation attached to a case."""

    class Kind(models.TextChoices):
        SUMMARY = "summary", "Behavior Summary"
        FINDING = "finding", "Forensic Finding"
        CLASSIFICATION = "classification", "Threat Classification"
        ANOMALY = "anomaly", "Process Anomaly"
        RECOMMENDATION = "recommendation", "Investigation Recommendation"

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="ai_insights")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    title = models.CharField(max_length=200)
    content = models.TextField()
    confidence = models.PositiveSmallIntegerField(default=70)
    model_used = models.CharField(max_length=64, blank=True)
    prompt_excerpt = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="ai_insights",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
