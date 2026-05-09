# Memory Forensics Platform (MFP)

An enterprise-grade Digital Forensics & Incident Response (DFIR) platform for investigating
RAM dumps from Windows and Linux systems using the **Volatility 3 Framework**.

> Designed and built like a real SOC / DFIR investigation platform.

---

## ✨ Features

- **Case Management** — Investigations, evidence chain-of-custody, notes, timelines, assignment.
- **Memory Dump Upload** — Chunked uploads, SHA-256 integrity, supports `.raw`, `.mem`, `.dmp`, `.lime`, compressed.
- **Automated Volatility 3 Analysis** — Async Celery workers run `pslist`, `pstree`, `netscan`, `cmdline`, `dlllist`, `handles`, `malfind`, `filescan`, `hashdump`, `sessions`, `svcscan`.
- **Process Investigation Dashboard** — Parent/child trees, hidden process detection, suspicious process highlighting, risk scoring.
- **Network Forensics** — Active connections, external IPs, suspicious ports, geolocation hooks.
- **Malware Detection Engine** — Heuristic + IOC-based detection (injection, hollowing, credential dumping, persistence).
- **Interactive Timeline** — Correlated forensic events.
- **Reporting Engine** — Professional PDF / HTML reports with executive summary, IOCs, risk assessment.
- **AI-Assisted Investigation** — Optional LLM-powered behavior summarization & threat classification.
- **RBAC + JWT + Audit Logging + Rate Limiting**.
- **Dockerized** with Nginx reverse proxy.

---

## 🏗️ Architecture

```
┌──────────────┐    ┌────────────────────┐    ┌────────────────┐
│  React SPA   │───▶│  Nginx (Reverse    │───▶│  Django + DRF  │
│  (Tailwind)  │    │     Proxy + TLS)   │    │   (Gunicorn)   │
└──────────────┘    └────────────────────┘    └────────┬───────┘
                                                       │
                          ┌────────────────────────────┼────────────────────────┐
                          ▼                            ▼                        ▼
                   ┌──────────────┐            ┌────────────────┐       ┌──────────────┐
                   │   SQLite /   │            │   Redis Broker │       │ Celery Worker│
                   │   Postgres   │            │                │◀─────▶│ + Volatility3│
                   └──────────────┘            └────────────────┘       └──────────────┘
```

Backend apps: `authentication`, `cases`, `evidence`, `analysis`, `reports`, `timeline`, `ioc`, `ai_engine`, `audit`.

---

## 🚀 Quickstart (Docker)

```bash
git clone <repo> mfp && cd mfp
cp .env.example .env
docker compose up --build
```

Access:
- Web UI:   http://localhost
- API:      http://localhost/api/
- Admin:    http://localhost/admin/

Default superuser is created on first boot from `.env`:
```
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=ChangeMe!2026
DJANGO_SUPERUSER_EMAIL=admin@mfp.local
```

---

## 📚 Documentation

- [`docs/INSTALL.md`](docs/INSTALL.md) — Local & Docker installation.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Production deployment guide.
- [`docs/API.md`](docs/API.md) — REST API reference.
- [`docs/SECURITY.md`](docs/SECURITY.md) — Security hardening.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System architecture & data model.

---

## ⚖️ License

For internal SOC / DFIR use. See `LICENSE`.
