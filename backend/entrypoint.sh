#!/usr/bin/env bash
# Backend container entrypoint.
# Usage:
#   ./entrypoint.sh web        → runs Gunicorn
#   ./entrypoint.sh worker     → runs Celery worker
#   ./entrypoint.sh beat       → runs Celery beat
#   ./entrypoint.sh manage ... → arbitrary manage.py command
set -euo pipefail

ROLE="${1:-${MFP_ROLE:-web}}"
shift || true

cd /app

mkdir -p /app/data /app/data/media /app/data/evidence /app/data/reports
mkdir -p /app/data/volatility_symbols 2>/dev/null || true
mkdir -p "$HOME/.cache/volatility3" 2>/dev/null || true

if [[ "$ROLE" == "web" ]]; then
  echo "[entrypoint] Generating migrations (if any models lack them)…"
  python manage.py makemigrations \
      authentication audit cases evidence analysis reports timeline ioc ai_engine \
      --noinput || true
  echo "[entrypoint] Applying database migrations…"
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput || true

  if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
    echo "[entrypoint] Ensuring default superuser '$DJANGO_SUPERUSER_USERNAME' exists…"
    python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
U = get_user_model()
u, created = U.objects.get_or_create(username=os.environ['DJANGO_SUPERUSER_USERNAME'],
                                     defaults={'email': os.environ.get('DJANGO_SUPERUSER_EMAIL', '')})
u.is_superuser = True
u.is_staff = True
u.role = 'admin'
u.set_password(os.environ['DJANGO_SUPERUSER_PASSWORD'])
u.save()
print('Default superuser ready.')
"
  fi

  exec gunicorn mfp.wsgi:application \
       --bind 0.0.0.0:8000 \
       --workers "${GUNICORN_WORKERS:-3}" \
       --timeout "${GUNICORN_TIMEOUT:-1800}" \
       --access-logfile - --error-logfile -
fi

if [[ "$ROLE" == "worker" ]]; then
  exec celery -A mfp worker -l info --concurrency "${CELERY_CONCURRENCY:-2}"
fi

if [[ "$ROLE" == "beat" ]]; then
  exec celery -A mfp beat -l info
fi

if [[ "$ROLE" == "manage" ]]; then
  exec python manage.py "$@"
fi

echo "[entrypoint] Unknown role: $ROLE" >&2
exit 1
