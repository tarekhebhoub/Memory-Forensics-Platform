# API Reference

The MFP API is REST + JSON, mounted at `/api/v1/`. A live, authenticated explorer
is available at:

- **Swagger UI** — `/api/docs/`
- **ReDoc**     — `/api/redoc/`
- **OpenAPI**   — `/api/schema/` (consume from any client generator)

This document is a quick catalog of the most-used endpoints.

---

## 1. Authentication

All non-auth endpoints require `Authorization: Bearer <access_token>`.

| Method | Path                              | Description                              |
|--------|-----------------------------------|------------------------------------------|
| POST   | `/auth/token/`                    | Obtain access + refresh tokens           |
| POST   | `/auth/token/refresh/`            | Refresh access token                     |
| GET    | `/auth/users/me/`                 | Current user                             |
| POST   | `/auth/users/change-password/`    | Self-service password change             |
| GET    | `/auth/users/roles/`              | Available roles                          |
| GET    | `/auth/users/`                    | List users *(admin)*                     |
| POST   | `/auth/users/`                    | Create user *(admin)*                    |
| PATCH  | `/auth/users/{id}/`               | Update user / change role *(admin)*      |
| DELETE | `/auth/users/{id}/`               | Delete user *(admin)*                    |

### Login example

```http
POST /api/v1/auth/token/
Content-Type: application/json

{ "username": "admin", "password": "•••••••" }
```

```json
{ "access": "eyJ…", "refresh": "eyJ…" }
```

---

## 2. Cases

| Method | Path                              | Description                              |
|--------|-----------------------------------|------------------------------------------|
| GET    | `/cases/?search=&status=&severity=` | List / search cases                    |
| POST   | `/cases/`                         | Create case                              |
| GET    | `/cases/{id}/`                    | Case detail                              |
| PATCH  | `/cases/{id}/`                    | Update case                              |
| DELETE | `/cases/{id}/`                    | Delete case *(lead/admin)*               |
| POST   | `/cases/{id}/status/`             | `{ "status": "in_progress" }`            |
| POST   | `/cases/{id}/assign/`             | `{ "user_ids": [2, 5] }`                 |
| GET    | `/cases/{id}/custody/`            | Chain-of-custody log                     |
| GET    | `/cases/notes/?case={id}`         | List notes                               |
| POST   | `/cases/notes/`                   | Create note                              |

---

## 3. Evidence

| Method | Path                                   | Description                                 |
|--------|----------------------------------------|---------------------------------------------|
| GET    | `/evidence/?case={id}`                 | List evidence                               |
| POST   | `/evidence/upload/`                    | Multipart upload (`case`, `file`, optional `os_hint`) |
| GET    | `/evidence/{id}/`                      | Evidence detail (incl. SHA-256, MD5)        |
| POST   | `/evidence/{id}/verify/`               | Re-hash + compare against stored digest     |
| POST   | `/evidence/{id}/analyze/`              | Enqueue full Volatility analysis            |
| DELETE | `/evidence/{id}/`                      | Delete evidence *(lead/admin)*              |
| POST   | `/evidence/uploads/init/`              | Start chunked upload session                |
| POST   | `/evidence/uploads/{uid}/chunk/`       | Upload one chunk                            |
| POST   | `/evidence/uploads/{uid}/finalize/`    | Stitch + hash + register evidence           |

---

## 4. Analysis

| Method | Path                                            | Description                       |
|--------|-------------------------------------------------|-----------------------------------|
| GET    | `/analysis/jobs/?evidence={id}`                 | Jobs for an evidence              |
| GET    | `/analysis/jobs/{id}/`                          | Job detail incl. risk score, detections, plugin list |
| GET    | `/analysis/jobs/{job_id}/result/{plugin}/`      | Per-plugin result (parsed rows + summary + raw) |

### Plugin set
The analyzer runs (configurable via `VOLATILITY_PLUGINS`):

`windows.pslist`, `windows.pstree`, `windows.netscan`, `windows.cmdline`, `windows.dlllist`,
`windows.handles`, `windows.malfind`, `windows.filescan`, `windows.hashdump`, `windows.sessions`,
`windows.svcscan` (and the `linux.*` analogues, when Linux is detected).

---

## 5. IOCs, Timeline, Reports, AI, Audit

| Path                                  | Description                                       |
|---------------------------------------|---------------------------------------------------|
| `GET /ioc/?case=&kind=&severity=`     | Indicators of compromise                          |
| `GET /timeline/events/?case=&kind=`   | Timeline events                                   |
| `GET /reports/`                       | Reports list                                      |
| `POST /reports/`                      | `{case, title, format: "pdf"|"html"}`             |
| `POST /reports/{id}/regenerate/`      | Re-run generation                                 |
| `GET /reports/{id}/download/`         | Download artifact                                 |
| `GET /ai/insights/?case={id}`         | List AI insights for a case                       |
| `POST /ai/insights/summarize/{case_id}/` | Generate behaviour summary                     |
| `POST /ai/insights/classify/{case_id}/`  | Classify threat                                |
| `POST /ai/insights/recommend/{case_id}/` | Recommend next investigative steps             |
| `GET /audit/events/?action=&search=`  | Immutable audit trail *(admin)*                   |

---

## 6. Pagination & filtering

All list endpoints accept `?page=`, `?page_size=` (max 200). Most expose `?search=` plus
type-specific filters as documented in `/api/docs/`. Responses follow DRF's standard
`{"count", "next", "previous", "results"}` envelope.

---

## 7. Throttling

Defaults from `settings.py` (override via env):

| Scope         | Limit                  |
|---------------|------------------------|
| anon          | 60 / hour              |
| user          | 1000 / hour            |
| login burst   | 10 / minute            |

Returns HTTP `429` with `Retry-After` header when exceeded.

---

## 8. Errors

```json
{ "detail": "Invalid token", "code": "token_not_valid" }
```

Validation errors follow DRF's per-field shape:

```json
{ "code": ["case with this code already exists."], "title": ["This field is required."] }
```
