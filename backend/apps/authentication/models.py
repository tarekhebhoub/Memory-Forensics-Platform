"""User model with role-based access control."""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    """Platform roles. Higher roles inherit lower-role capabilities at the view layer."""
    ADMIN = "admin", "Administrator"
    LEAD = "lead", "Lead Investigator"
    ANALYST = "analyst", "Forensic Analyst"
    VIEWER = "viewer", "Read-only Viewer"


class User(AbstractUser):
    """Custom user model.

    `role` drives RBAC across the platform. Email is treated as a contactable identity
    but `username` remains the canonical identifier (compatible with Django auth).
    """

    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.ANALYST,
        db_index=True,
    )
    full_name = models.CharField(max_length=150, blank=True)
    title = models.CharField(max_length=150, blank=True, help_text="Job title / position")
    phone = models.CharField(max_length=32, blank=True)
    mfa_enabled = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ("username",)

    # Convenience helpers used throughout the codebase / templates
    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_lead(self) -> bool:
        return self.role in {Role.ADMIN, Role.LEAD} or self.is_superuser

    @property
    def can_write(self) -> bool:
        return self.role in {Role.ADMIN, Role.LEAD, Role.ANALYST} or self.is_superuser

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.username} ({self.get_role_display()})"
