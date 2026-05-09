# Architecture

A high-level walkthrough of how MFP is structured, where state lives, and how a
memory dump becomes an investigation report.

---

## 1. Big picture

```
┌──────────────────────────────────────────────────────────────────────┐
│                            React SPA (Vite)                         │
│  Pages: Dashboard · Cases · CaseDetail · Evidence · Analysis ·       │
│         Timeline · IOCs · Reports · Users · Audit                    │
└──────────────────────────┬───────────────────────────────────────────┘
                           │  REST + JWT
┌──────────────────────────▼───────────────────────────────────────────┐
│                    Django REST Framework backend                     │
│  apps/authentication · apps/cases · apps/evidence · apps/analysis    │
│  apps/reports · apps/timeline · apps/ioc · apps/ai_engine            │
│  apps/audit (middleware)                                             │
└────────┬─────────────────────────────┬───────────────────────────────┘
         │                             │
         ▼                             ▼
   ┌──────────┐                 ┌────────────┐
   │ DB (SQLite│                 │  Celery    │──┐
   │   / PG)  │                 │  workers   │  │ subprocess: `vol -r json …`
   └──────────┘                 └─────┬──────┘  ▼
                                      │   ┌──────────────┐
                                      │   │ Volatility 3 │
                                      │   └──────────────┘
                                      ▼
                                ┌────────────┐
                                │   Redis    │  broker + result backend
                                └────────────┘
```

---

## 2. Module layout

```
backend/
  mfp/                       # project config (settings, urls, celery, asgi)
  apps/
    authentication/          # User, roles, JWT views
    audit/                   # AuditEvent + middleware/record helper
    cases/                   # Case · CaseNote · ChainOfCustody · services
    evidence/                # Evidence · UploadSession · streaming + chunked upload
    analysis/                # AnalysisJob · PluginResult
        volatility.py        # subprocess runner (JSON + text-fallback parser)
        detection.py         # heuristic engine (malfind/pslist/netscan/svcscan)
        summarizer.py        # per-plugin row → summary distillation
        services.py          # enqueue analysis
        tasks.py             # Celery pipeline + IOC/timeline post-processing
    reports/                 # Report model + ReportLab PDF + Jinja2 HTML engine
    timeline/                # TimelineEvent
    ioc/                     # IOC (deduped per case+kind+value)
    ai_engine/               # AIInsight + pluggable provider (OpenAI / heuristic)

frontend/
  src/
    api/client.js            # central Axios + JWT auto-refresh
    auth/AuthContext.jsx     # AuthProvider + can(user, capability)
    components/              # Layout · UI primitives
    pages/                   # one .jsx per top-level route
```

---

## 3. Data model (key relationships)

```
User ─────┐
          │ (lead_analyst, assignees M2M)
          ▼
        Case ─── CaseNote
          │       ChainOfCustody  (append-only)
          │
          ├── Evidence ─── UploadSession (during upload)
          │     │
          │     └── AnalysisJob ─── PluginResult (one per plugin run)
          │            │
          │            ├──► IOC               (post-processing)
          │            └──► TimelineEvent     (post-processing)
          │
          ├── Report
          └── AIInsight

AuditEvent  (cross-cutting, immutable, written by middleware + services)
```

---

## 4. Request → analysis lifecycle

1. **Upload.** `POST /evidence/upload/` (or chunked variant) streams the file into
   `MEDIA_ROOT/evidence/<uuid>/<name>`, computes SHA-256 + MD5, persists `Evidence`
   in `pending` state, and writes a `ChainOfCustody` `UPLOAD` entry.
2. **Trigger analysis.** `POST /evidence/{id}/analyze/` creates an `AnalysisJob`
   and dispatches `analysis.tasks.run_analysis_job(job_id)` to Celery.
3. **OS detection.** Worker runs `windows.info` → `linux.banners` → `mac.mount`,
   stores `detected_os` on the job.
4. **Plugin execution.** For each configured plugin: spawn `vol -q -r json -f …`,
   parse JSON (falling back to a regex-based text-table parser), persist a
   `PluginResult` (raw + parsed rows + summary), update progress.
5. **Detection engine.** `detection.aggregate(results)` runs per-plugin heuristics,
   emits `Detection` records, and computes a sub-linear `risk_score = 100·(1−e^(−Σw/200))`.
6. **Post-processing.** Findings are normalised into deduplicated `IOC` rows
   (per case+kind+value), and key events become `TimelineEvent` entries.
7. **Audit.** Every state change writes an `AuditEvent` via
   `audit.middleware.record(...)`.
8. **Reporting.** `POST /reports/` queues `reports.tasks.generate_report_task`,
   which renders Jinja2 HTML or composes a ReportLab PDF and stores it under
   `MEDIA_ROOT/reports/`.
9. **AI insights.** Optional `POST /ai/insights/{summarize|classify|recommend}/{case}/`
   calls `ai_engine.providers.generate()`, which uses OpenAI when `AI_ENABLED=1`
   or a deterministic local heuristic otherwise.

---

## 5. Patterns & conventions

- **Service layer.** Business rules live in `services.py` modules (not in views),
  so they can be reused from Celery tasks, the admin, and management commands.
- **Custody = audit + business log.** `ChainOfCustody` is the user-visible,
  case-scoped log; `AuditEvent` is the platform-wide immutable record.
- **Idempotent pipeline.** Re-running an analysis cleanly replaces previous
  `PluginResult` rows for the job; IOCs are deduplicated.
- **Pluggable AI.** Provider is a single function `generate(prompt, context) → (text, model)`
  so swapping vendors (Anthropic, local LLM, vLLM) is a one-file change.
- **Frontend dark-by-default.** Tailwind is configured with `class` mode and a
  custom `ink/accent/sev` palette tuned for SOC dashboards.

---

## 6. Where to extend

| You want to…                            | Touch these files                                              |
|-----------------------------------------|----------------------------------------------------------------|
| Add a new Volatility plugin             | `mfp/settings.py:VOLATILITY_PLUGINS`, optionally `analysis/detection.py` |
| Add a new detection heuristic           | `analysis/detection.py` (`detect_*` function + register)       |
| Support a new evidence format           | `evidence/services.py:ALLOWED_EXTS`                            |
| Add a new report section                | `reports/engine.py` (PDF) and `reports/templates/report.html`  |
| Add an AI provider                      | `ai_engine/providers.py` (return `(text, model_used)`)         |
| Add a new RBAC capability               | `authentication/permissions.py` and `frontend/src/auth/AuthContext.jsx` |
| Add a new timeline event source         | emit `TimelineEvent` from `analysis/tasks._emit_timeline`      |
