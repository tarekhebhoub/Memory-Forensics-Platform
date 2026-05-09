# Security Hardening Recommendations

MFP handles **forensic evidence** — by definition, sensitive material whose
integrity must be defensible in court. This document captures the security
posture shipped by default and the additional steps you should take in
production.

---

## 1. Defaults shipped in MFP

| Control                          | Where                                                    |
|----------------------------------|----------------------------------------------------------|
| JWT auth (access + rotating refresh) | `mfp.settings.SIMPLE_JWT`, `apps.authentication`     |
| Role-based access control        | `Role` enum + DRF permissions (`IsAdmin`, `IsLeadOrAdmin`, …) |
| Append-only chain-of-custody     | `apps.cases.models.ChainOfCustody`                        |
| Immutable audit log              | `apps.audit.models.AuditEvent` + `audit.middleware`       |
| File-extension allow-list        | `apps.evidence.services.validate_filename`                |
| SHA-256 + MD5 hashing on upload  | `apps.evidence.services.sha256_file`                      |
| Verify-on-demand integrity check | `POST /evidence/{id}/verify/`                            |
| Rate-limited auth endpoints      | DRF `throttle_classes`                                    |
| CSRF / session cookie hardening  | configurable via env (`SESSION_COOKIE_SECURE`, …)         |
| Security HTTP headers            | edge `nginx` config                                       |
| Non-root container user (uid 10001) | `backend/Dockerfile`                                  |
| Subprocess isolation per analysis | each plugin runs in its own `vol` subprocess via Celery   |

---

## 2. RBAC matrix

| Capability                 | viewer | analyst | lead | admin |
|----------------------------|:------:|:-------:|:----:|:-----:|
| View cases / evidence      | ✅     | ✅      | ✅   | ✅    |
| Create case / upload evidence | ❌  | ✅      | ✅   | ✅    |
| Run analysis               | ❌     | ✅      | ✅   | ✅    |
| Assign / close case        | ❌     | ❌      | ✅   | ✅    |
| Manage users & roles       | ❌     | ❌      | ❌   | ✅    |
| View audit log             | ❌     | ❌      | ❌   | ✅    |

---

## 3. Production hardening checklist

- [ ] Generate a fresh 64-char `DJANGO_SECRET_KEY` and store it in a secret manager.
- [ ] Set `DJANGO_DEBUG=0`, `SECURE_SSL_REDIRECT=1`, `SESSION_COOKIE_SECURE=1`, `CSRF_COOKIE_SECURE=1`.
- [ ] Scope `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` to your FQDN.
- [ ] Front the stack with TLS; reject HTTP at the edge.
- [ ] Disable the seeded superuser flow after first boot (`MFP_SUPERUSER_*` empty).
- [ ] Use Postgres with TLS instead of SQLite.
- [ ] Encrypt the `evidence_data` volume at rest (LUKS, EBS-encrypted, etc.).
- [ ] Restrict outbound traffic from the worker container (only Volatility symbols + Redis).
- [ ] Run workers in an isolated network namespace; consider gVisor / Kata for stronger sandboxing.
- [ ] Rotate JWT signing keys quarterly; invalidate refresh tokens on policy change.
- [ ] Enable MFA for admin accounts (`mfa_enabled` field is provisioned on `User`).
- [ ] Forward audit + Celery + Nginx logs to a tamper-evident SIEM.
- [ ] Configure file integrity monitoring on `/app/media/evidence`.
- [ ] Backup the audit log separately from operational backups (legal hold).

---

## 4. Threat model — selected

| Threat                                              | Mitigation                                                            |
|-----------------------------------------------------|------------------------------------------------------------------------|
| Malicious memory image escapes Volatility parser    | Worker runs as non-root, with no host network; consider gVisor.       |
| Tampering with stored evidence                      | SHA-256 captured at upload; `verify` endpoint re-hashes on demand.     |
| Privilege escalation via API                        | RBAC checked on every viewset; tested via DRF permission classes.     |
| Token theft                                         | Short access TTL (30 m); refresh rotation; cookie-secure flags.       |
| CSRF                                                | JWT-based + DRF `SessionAuthentication` only enabled for browsable API. |
| Path traversal in filenames                         | `validate_filename` allow-lists extensions; storage uses UUID-based names. |
| Audit log tampering                                 | Append-only model; export to external SIEM for tamper-evidence.        |
| AI exfiltration of case data                        | `AI_ENABLED=0` by default → deterministic local heuristic, no egress. |

---

## 5. Reporting a vulnerability

Please email `security@your-org.example` with a description, reproduction steps,
and (optionally) a PGP-encrypted payload. We aim to acknowledge within 48h and
ship fixes within 14 days for critical issues.
