"""Reusable DRF permissions implementing platform RBAC."""
from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role


class IsAdmin(BasePermission):
    """Only admins."""
    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsLeadOrAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        u = request.user
        return bool(u and u.is_authenticated and u.is_lead)


class IsAnalystOrAbove(BasePermission):
    """Analyst, Lead, or Admin can write; Viewer is read-only."""
    def has_permission(self, request, view) -> bool:
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return u.role in {Role.ADMIN, Role.LEAD, Role.ANALYST} or u.is_superuser


class ReadOnlyForViewers(BasePermission):
    """Viewers may only perform safe methods."""
    def has_permission(self, request, view) -> bool:
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if u.role == Role.VIEWER and request.method not in SAFE_METHODS:
            return False
        return True
