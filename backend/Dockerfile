# syntax=docker/dockerfile:1.6
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# OS deps:
#  - libmagic1 → python-magic file-type detection
#  - build-essential → wheels needed by some deps
#  - tini → safe init for PID 1
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libmagic1 \
        tini \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app/

RUN chmod +x /app/entrypoint.sh \
    && useradd --create-home --uid 10001 mfp \
    && mkdir -p /app/data /app/staticfiles /home/mfp/.cache/volatility3 \
    && chown -R mfp:mfp /app /home/mfp

USER mfp

ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
CMD ["web"]
