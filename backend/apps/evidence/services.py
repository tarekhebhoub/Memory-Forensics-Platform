"""Service layer for evidence handling: streaming upload, hashing, integrity verification."""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

from django.conf import settings
from django.db import transaction

from apps.audit.middleware import record as audit_record
from apps.cases.models import Case, ChainOfCustody

from .models import Evidence, UploadSession

logger = logging.getLogger("mfp.evidence")

ALLOWED_EXTENSIONS = {".raw", ".mem", ".dmp", ".lime", ".vmem", ".bin",
                      ".gz", ".zip", ".7z", ".xz", ".bz2"}


def _evidence_dir(case: Case, evidence_uid) -> Path:
    """Per-case, per-evidence storage directory."""
    p = settings.EVIDENCE_ROOT / str(case.uid) / str(evidence_uid)
    p.mkdir(parents=True, exist_ok=True)
    return p


def validate_filename(filename: str) -> str:
    """Reject path traversal & disallowed extensions; return sanitized basename."""
    base = os.path.basename(filename).strip()
    if not base or base in {".", ".."}:
        raise ValueError("Invalid filename.")
    ext = Path(base).suffix.lower()
    # `.gz` etc. are allowed wrappers; require some extension at all.
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return base


def sha256_file(path: str | Path, *, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def md5_file(path: str | Path, *, chunk: int = 1024 * 1024) -> str:
    h = hashlib.md5(usedforsecurity=False)  # MD5 used here ONLY as a non-security identity hash
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


@transaction.atomic
def store_uploaded_file(*, case: Case, uploaded_file, uploader,
                        description: str = "", os_hint: str = "") -> Evidence:
    """
    Persist a single (small/medium) upload directly. For very large files,
    use the chunked `UploadSession` flow.
    """
    name = validate_filename(uploaded_file.name)
    evidence = Evidence.objects.create(
        case=case, name=name, description=description,
        size_bytes=uploaded_file.size,
        mime_type=getattr(uploaded_file, "content_type", "") or "application/octet-stream",
        os_profile_hint=os_hint,
        uploaded_by=uploader, status=Evidence.Status.UPLOADING,
    )
    target_dir = _evidence_dir(case, evidence.uid)
    target = target_dir / name

    sha = hashlib.sha256()
    with open(target, "wb") as out:
        for chunk in uploaded_file.chunks(chunk_size=4 * 1024 * 1024):
            out.write(chunk)
            sha.update(chunk)

    evidence.file_path = str(target)
    evidence.sha256 = sha.hexdigest()
    evidence.md5 = md5_file(target)
    evidence.status = Evidence.Status.UPLOADED
    evidence.verified_at = datetime.now(timezone.utc)
    evidence.save()

    ChainOfCustody.objects.create(
        case=case, actor=uploader, actor_username=getattr(uploader, "username", ""),
        action=ChainOfCustody.Action.EVIDENCE_ADDED,
        description=f"Evidence '{name}' uploaded ({evidence.size_bytes} bytes).",
        metadata={"sha256": evidence.sha256, "evidence_id": evidence.id},
    )
    audit_record("evidence.upload", actor=uploader, target=evidence, severity="notice",
                 metadata={"sha256": evidence.sha256, "size": evidence.size_bytes})
    return evidence


# ──────────────────────────── Chunked uploads ────────────────────────────
@transaction.atomic
def init_chunked_upload(*, case: Case, filename: str, total_size: int,
                        chunk_size: int, uploader, expected_sha256: str = "") -> UploadSession:
    name = validate_filename(filename)
    target_dir = settings.EVIDENCE_ROOT / "_uploads"
    target_dir.mkdir(parents=True, exist_ok=True)
    storage_path = target_dir / f"{case.uid}__{uploader.id}__{name}"
    # Truncate any existing file
    open(storage_path, "wb").close()

    session = UploadSession.objects.create(
        case=case, filename=name, total_size=total_size, chunk_size=chunk_size,
        expected_sha256=expected_sha256.lower(),
        storage_path=str(storage_path), initiated_by=uploader,
    )
    return session


def append_chunk(session: UploadSession, *, chunk_index: int, chunk: BinaryIO | bytes) -> UploadSession:
    if session.status != UploadSession.Status.OPEN:
        raise ValueError(f"Upload session {session.uid} is not open.")
    expected_offset = chunk_index * session.chunk_size
    data = chunk.read() if hasattr(chunk, "read") else chunk
    with open(session.storage_path, "r+b") as fh:
        fh.seek(expected_offset)
        fh.write(data)
    session.received_bytes = max(session.received_bytes, expected_offset + len(data))
    session.received_chunks += 1
    session.save(update_fields=["received_bytes", "received_chunks"])
    return session


@transaction.atomic
def finalize_chunked_upload(session: UploadSession, *, uploader,
                            description: str = "", os_hint: str = "") -> Evidence:
    if session.status != UploadSession.Status.OPEN:
        raise ValueError("Session already finalized.")
    if not Path(session.storage_path).exists():
        raise FileNotFoundError("Upload data missing on disk.")

    sha = sha256_file(session.storage_path)
    if session.expected_sha256 and sha != session.expected_sha256:
        session.status = UploadSession.Status.ABORTED
        session.save(update_fields=["status"])
        raise ValueError(
            f"SHA-256 mismatch — expected {session.expected_sha256}, got {sha}"
        )

    evidence = Evidence.objects.create(
        case=session.case, name=session.filename, description=description,
        size_bytes=session.total_size,
        mime_type="application/octet-stream",
        os_profile_hint=os_hint,
        uploaded_by=uploader,
        status=Evidence.Status.UPLOADING,
    )
    target_dir = _evidence_dir(session.case, evidence.uid)
    target = target_dir / session.filename
    shutil.move(session.storage_path, target)

    evidence.file_path = str(target)
    evidence.sha256 = sha
    evidence.md5 = md5_file(target)
    evidence.status = Evidence.Status.VERIFIED
    evidence.verified_at = datetime.now(timezone.utc)
    evidence.save()

    session.final_sha256 = sha
    session.status = UploadSession.Status.COMPLETED
    session.completed_at = datetime.now(timezone.utc)
    session.save()

    ChainOfCustody.objects.create(
        case=session.case, actor=uploader, actor_username=getattr(uploader, "username", ""),
        action=ChainOfCustody.Action.EVIDENCE_ADDED,
        description=f"Evidence '{session.filename}' uploaded via chunked session.",
        metadata={"sha256": sha, "evidence_id": evidence.id, "session": str(session.uid)},
    )
    audit_record("evidence.upload.chunked", actor=uploader, target=evidence, severity="notice",
                 metadata={"sha256": sha, "size": evidence.size_bytes})
    return evidence


def verify_integrity(evidence: Evidence) -> bool:
    """Re-hash on disk, compare to stored value. Updates status if mismatched."""
    if not evidence.exists_on_disk:
        evidence.status = Evidence.Status.QUARANTINED
        evidence.save(update_fields=["status"])
        return False
    current = sha256_file(evidence.file_path)
    ok = current == evidence.sha256
    if not ok:
        evidence.status = Evidence.Status.QUARANTINED
        evidence.save(update_fields=["status"])
    return ok
