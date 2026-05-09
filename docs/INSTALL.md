# Installation Guide

This guide covers two paths: **Docker (recommended)** and **local development**.

---

## 1. Prerequisites

| Component         | Version | Notes                                       |
|-------------------|---------|---------------------------------------------|
| Docker Engine     | ≥ 24    | with Compose v2 (`docker compose`)          |
| Python            | 3.12    | only for local dev                          |
| Node.js           | 20 LTS  | only for local dev                          |
| Volatility 3      | 2.7+    | bundled in backend image; install locally if running outside Docker |
| RAM               | ≥ 8 GB  | Volatility plugins are memory-hungry        |
| Disk              | ≥ 50 GB free | for storing memory images                |

---

## 2. Quick start (Docker)

```bash
git clone <your-repo-url> mfp && cd mfp
cp .env.example .env
# 🔐 EDIT .env — change DJANGO_SECRET_KEY and the default admin password!
docker compose up --build -d
```

Then open: **http://localhost:8080** (default; configurable via `MFP_HTTP_PORT`).

Default credentials are seeded from `.env` (`MFP_SUPERUSER_*`). Sign in and **change the password immediately**.

### Tailing logs

```bash
docker compose logs -f backend worker
```

### Running a one-off command

```bash
docker compose run --rm backend manage createsuperuser
docker compose run --rm backend manage shell
```

---

## 3. Local development (no Docker)

### 3.1 System dependencies

```bash
# Debian / Ubuntu
sudo apt install -y python3.12 python3.12-venv libmagic1 redis-server

# Volatility 3
pipx install volatility3   # or: pip install --user volatility3
which vol                  # confirm `vol` is on PATH
```

### 3.2 Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp ../.env.example ../.env       # then edit
export $(grep -v '^#' ../.env | xargs)

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

In a second terminal:

```bash
cd backend && source .venv/bin/activate
celery -A mfp worker -l info
```

### 3.3 Frontend

```bash
cd frontend
npm install
npm run dev          # → http://localhost:5173 (proxies /api to :8000)
```

---

## 4. Verifying the install

1. Visit the app → log in as the seeded admin.
2. Create a new case (`Cases → New case`).
3. Open the case, switch to the **Evidence** tab and upload a small `.raw` memory image.
4. Click **Analyze** — the Celery worker will pick the job up; refresh the page or open the analysis link to watch plugin results stream in.
5. Generate a PDF report from **Overview → Generate PDF**, then download it from the **Reports** page.

If any step fails, check `docker compose logs backend worker` (or your local Celery / Django logs).

---

## 5. Common issues

| Symptom                                            | Cause / Fix                                                                                |
|----------------------------------------------------|--------------------------------------------------------------------------------------------|
| `vol: command not found` in worker logs            | Set `VOLATILITY_BIN` in `.env` to an absolute path, or rebuild the image.                  |
| 413 on upload                                      | Edit `client_max_body_size` in `docker/nginx/default.conf` (default 16G).                  |
| Celery tasks stuck in `pending`                    | Worker not running, or Redis unreachable. `docker compose ps` and check broker URL.        |
| `cors error` from the SPA                          | In dev, ensure Vite proxy is up. In prod, all traffic flows through one Nginx → no CORS.   |
| Volatility hangs                                   | Increase `VOLATILITY_TIMEOUT` (seconds) in `.env`.                                         |
