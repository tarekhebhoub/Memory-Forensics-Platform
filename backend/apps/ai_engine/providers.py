"""Pluggable AI provider. When AI_ENABLED=0 (default), uses a deterministic
heuristic synthesizer so the platform always works offline.

When configured, it can call an OpenAI-compatible chat completion endpoint."""
from __future__ import annotations

import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger("mfp.ai")


def _heuristic_summary(prompt: str, context: dict) -> str:
    iocs = context.get("iocs", [])
    risk = context.get("max_risk_score", 0)
    bullets = []
    if risk >= 70:
        bullets.append(f"⚠️ High aggregate risk score ({risk}/100). Treat as a likely incident.")
    elif risk >= 40:
        bullets.append(f"Moderate risk score ({risk}/100). Investigate further.")
    else:
        bullets.append(f"Low risk score ({risk}/100). No strong indicators automatically detected.")

    if iocs:
        kinds = {}
        for i in iocs:
            kinds[i.get("kind", "?")] = kinds.get(i.get("kind", "?"), 0) + 1
        summary = ", ".join(f"{v} {k}" for k, v in kinds.items())
        bullets.append(f"Indicators observed: {summary}.")
    else:
        bullets.append("No IOCs were extracted from the available analyses.")

    bullets.append("Recommended next steps: validate suspicious processes against EDR telemetry, "
                   "pivot on observed IPs/hashes in your threat-intel platform, and preserve "
                   "the dump under chain-of-custody.")
    return "\n".join(f"• {b}" for b in bullets)


def generate(prompt: str, *, context: dict | None = None,
             system: str = "You are an expert DFIR analyst.") -> tuple[str, str]:
    """
    Returns (text, model_used).
    Falls back to a heuristic generator if AI_ENABLED is false or the call fails.
    """
    context = context or {}
    if not settings.AI_ENABLED or not settings.AI_API_KEY:
        return _heuristic_summary(prompt, context), "heuristic-v1"

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.AI_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        return text, settings.AI_MODEL
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI provider failed (%s); falling back to heuristic.", exc)
        return _heuristic_summary(prompt, context), "heuristic-v1-fallback"
