"""Celery application bootstrap."""
from __future__ import annotations

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mfp.settings")

app = Celery("mfp")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self) -> str:  # pragma: no cover
    return f"Request: {self.request!r}"
