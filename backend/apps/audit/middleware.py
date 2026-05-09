"""Audit logging middleware — captures every authenticated API call."""
from __future__ import annotations

import logging
from typing import Callable

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("mfp.audit")

# Paths that we always skip to keep the audit trail meaningful.
SKIP_PREFIXES = ("/static/", "/media/", "/api/schema", "/api/docs", "/api/redoc",
                 "/favicon.ico", "/admin/jsi18n")


def _client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AuditLogMiddleware(MiddlewareMixin):
    """Persist an `AuditEvent` for non-trivial API requests.

    Only writes for state-changing methods (POST/PUT/PATCH/DELETE) or any failed call.
    Done lazily so unit tests / migrations are unaffected.
    """

    STATE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def process_response(self, request, response):
        try:
            path = request.path or ""
            if any(path.startswith(p) for p in SKIP_PREFIXES):
                return response

            method = request.method
            status = response.status_code
            should_log = method in self.STATE_METHODS or status >= 400
            if not should_log:
                return response

            # Avoid import-time / migration-time DB calls
            from .models import AuditEvent

            user = getattr(request, "user", None)
            actor = user if (user and getattr(user, "is_authenticated", False)) else None
            severity = AuditEvent.Severity.INFO
            if status >= 500:
                severity = AuditEvent.Severity.ALERT
            elif status >= 400:
                severity = AuditEvent.Severity.WARNING

            AuditEvent.objects.create(
                actor=actor,
                actor_username=(actor.username if actor else "anonymous"),
                action=f"http.{method.lower()}",
                method=method,
                path=path[:512],
                ip_address=_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
                status_code=status,
                severity=severity,
            )
        except Exception:  # never break the response cycle
            logger.exception("Failed to write audit event")
        return response


def record(action: str, *, actor=None, target=None, severity: str = "info",
           metadata: dict | None = None) -> None:
    """Programmatic audit helper for service-layer events (case create, evidence upload, etc.)."""
    from .models import AuditEvent
    target_type = target.__class__.__name__ if target is not None else ""
    target_id = str(getattr(target, "pk", "")) if target is not None else ""
    AuditEvent.objects.create(
        actor=actor if actor and getattr(actor, "is_authenticated", False) else None,
        actor_username=getattr(actor, "username", "") or "system",
        action=action,
        target_type=target_type,
        target_id=target_id,
        severity=severity,
        metadata=metadata or {},
    )
