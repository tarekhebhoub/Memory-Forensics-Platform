# Deployment Guide

Production guidance for hardening, scaling and operating MFP.

---

## 1. Topology

```
            ┌──────────────────────────┐
   HTTPS ──▶│  TLS termination (Caddy/  │──┐
            │  Nginx/Traefik/cloud LB)  │  │
            └──────────────────────────┘  │
                                          ▼
                            ┌──────────────────────┐
                            │  mfp-nginx (edge)    │
                            └─────────┬────────────┘
                          ┌───────────┴────────────┐
                          ▼                        ▼
                ┌──────────────────┐     ┌────────────────┐
                │ mfp-backend      │     │ mfp-frontend   │
                │ (gunicorn x N)   │     │ (Nginx + SPA)  │
                └────┬─────────────┘     └────────────────┘
                     │
        ┌────────────┼────────────────┐
        ▼            ▼                ▼
   Postgres     mfp-worker x N    Redis (broker)
                 (Celery + vol)
```

Run **at least 2 backend replicas** and **N workers** sized for analysis throughput.

---

## 2. Required `.env` changes for production

| Variable                  | Production value                                     |
|---------------------------|------------------------------------------------------|
| `DJANGO_DEBUG`            | `0`                                                  |
| `DJANGO_SECRET_KEY`       | 64-char random; rotate periodically                  |
| `DJANGO_ALLOWED_HOSTS`    | exact FQDN(s), comma-separated                       |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://mfp.example.com`                       |
| `SECURE_SSL_REDIRECT`     | `1`                                                  |
| `SESSION_COOKIE_SECURE`   | `1`                                                  |
| `CSRF_COOKIE_SECURE`      | `1`                                                  |
| `DATABASE_URL`            | `postgres://user:pwd@db:5432/mfp`                    |
| `MFP_SUPERUSER_PASSWORD`  | unset after first boot, then disable seeding         |
| `AI_ENABLED`              | `0` if no outbound network from worker               |

---

## 3. TLS termination

Place a reverse proxy in front of `nginx` (compose service). Two common options:

### Caddy (recommended, automatic Let's Encrypt)

```caddy
mfp.example.com {
    reverse_proxy nginx:80
    encode gzip zstd
    request_body { max_size 16GB }
}
```

### Nginx (manual certs)

```nginx
server {
    listen 443 ssl http2;
    server_name mfp.example.com;
    ssl_certificate     /etc/ssl/mfp.crt;
    ssl_certificate_key /etc/ssl/mfp.key;
    client_max_body_size 16G;
    location / { proxy_pass http://nginx:80; proxy_set_header Host $host; }
}
server { listen 80; server_name mfp.example.com; return 301 https://$host$request_uri; }
```

---

## 4. Switching to PostgreSQL

1. Add a `db` service to `docker-compose.yml`:
   ```yaml
   db:
     image: postgres:16-alpine
     environment: { POSTGRES_DB: mfp, POSTGRES_USER: mfp, POSTGRES_PASSWORD: secret }
     volumes: [pg_data:/var/lib/postgresql/data]
   ```
2. Set `DATABASE_URL=postgres://mfp:secret@db:5432/mfp` in `.env`.
3. `docker compose up -d db` then `docker compose run --rm backend manage migrate`.

---

## 5. Scaling workers

```bash
docker compose up -d --scale worker=4
```

Each worker runs Volatility serially per task; scale horizontally for parallelism. For very large dumps,
increase `VOLATILITY_TIMEOUT` and ensure the worker container has enough RAM (≥ 2× the dump size is a
safe rule of thumb for some plugins).

---

## 6. Backups

| Asset             | Path / mechanism                                                |
|-------------------|-----------------------------------------------------------------|
| Database          | `pg_dump` (or copy `db_data/db.sqlite3`)                        |
| Evidence          | `evidence_data` volume — back up to immutable storage           |
| Reports           | `reports_data` volume — regenerable but large; back up monthly  |
| Audit log         | included in DB backup; consider periodic export to SIEM         |

Suggested cron-style backup (host):

```bash
0 2 * * * docker run --rm -v mfp_db_data:/d -v /backup:/b alpine \
  tar czf /b/db-$(date +\%F).tgz -C /d .
```

---

## 7. Monitoring & observability

- `/api/schema/`, `/api/docs/`, `/api/redoc/` — OpenAPI surfaces
- Backend logs go to stdout (JSON-friendly via `LOGGING` config)
- Celery exposes events you can pipe into Flower:
  ```bash
  docker compose run --rm worker celery -A mfp flower --port=5555
  ```
- Hook the audit log into your SIEM via DRF webhook or DB streaming.

---

## 8. Upgrades

1. Pull the new code: `git pull`.
2. Rebuild: `docker compose build --pull`.
3. Apply migrations: `docker compose run --rm backend manage migrate`.
4. Roll backend & worker: `docker compose up -d backend worker`.
5. Verify with `docker compose ps` and smoke-test login + a test analysis.

For zero-downtime, run two backend replicas behind the edge proxy and roll one at a time.
