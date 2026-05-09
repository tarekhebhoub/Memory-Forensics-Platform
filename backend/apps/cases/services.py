"""Service layer for case management. Encapsulates business rules + custody logging."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from django.db import transaction

from apps.audit.middleware import record as audit_record

from .models import Case, ChainOfCustody


@transaction.atomic
def create_case(*, code: str, title: str, description: str, severity: str,
                created_by, classification: str = "", tags: Optional[list] = None) -> Case:
    case = Case.objects.create(
        code=code, title=title, description=description,
        severity=severity, classification=classification,
        created_by=created_by, tags=tags or [],
    )
    ChainOfCustody.objects.create(
        case=case, actor=created_by, actor_username=created_by.username,
        action=ChainOfCustody.Action.CREATED,
        description=f"Case {code} created.",
    )
    audit_record("case.create", actor=created_by, target=case, severity="notice",
                 metadata={"code": code, "severity": severity})
    return case


@transaction.atomic
def change_status(case: Case, *, new_status: str, actor) -> Case:
    old = case.status
    case.status = new_status
    if new_status == Case.Status.CLOSED and case.closed_at is None:
        case.closed_at = datetime.now(timezone.utc)
    if new_status != Case.Status.CLOSED:
        case.closed_at = None
    case.save(update_fields=["status", "closed_at", "updated_at"])
    ChainOfCustody.objects.create(
        case=case, actor=actor, actor_username=getattr(actor, "username", ""),
        action=(ChainOfCustody.Action.CLOSED if new_status == Case.Status.CLOSED
                else ChainOfCustody.Action.STATUS_CHANGED),
        description=f"Status changed: {old} → {new_status}",
        metadata={"old": old, "new": new_status},
    )
    audit_record("case.status_change", actor=actor, target=case, severity="notice",
                 metadata={"old": old, "new": new_status})
    return case


@transaction.atomic
def assign_users(case: Case, *, user_ids: list[int], actor) -> Case:
    case.assignees.set(user_ids)
    ChainOfCustody.objects.create(
        case=case, actor=actor, actor_username=getattr(actor, "username", ""),
        action=ChainOfCustody.Action.ASSIGNED,
        description=f"Assigned {len(user_ids)} users.",
        metadata={"user_ids": list(user_ids)},
    )
    audit_record("case.assign", actor=actor, target=case, metadata={"user_ids": list(user_ids)})
    return case
