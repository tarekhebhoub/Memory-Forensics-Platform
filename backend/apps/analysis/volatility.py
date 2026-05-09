"""Volatility 3 runner.

Invokes the `vol` CLI in JSON-renderer mode and returns a structured result.
This intentionally uses a subprocess rather than calling Volatility's Python
internals so the analysis can run in an isolated worker container with
restricted privileges and a hard timeout.

The runner is also resilient: if the JSON renderer fails (some plugins return
warnings or non-JSON banners), it falls back to a tabular text parser so the
analyst still sees something useful.
"""
from __future__ import annotations

import json
import logging
import re
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings

logger = logging.getLogger("mfp.analysis.volatility")


@dataclass
class PluginRun:
    plugin: str
    ok: bool
    duration_ms: int
    raw_output: str = ""
    rows: list[dict] = field(default_factory=list)
    error: str = ""


def _build_command(image: str, plugin: str, *, renderer: str = "json") -> list[str]:
    """
    Build a Volatility 3 CLI invocation. We use:
      vol -q -s <writable-symbol-dir> -r <renderer> -f <image> <plugin>
    """
    bin_ = settings.VOLATILITY_BIN
    parts = shlex.split(bin_) if " " in bin_ else [bin_]
    sym_dir = getattr(settings, "VOLATILITY_SYMBOLS_DIR", "") or ""
    extra = ["-s", sym_dir] if sym_dir else []
    return [*parts, "-q", *extra, "-r", renderer, "-f", image, plugin]


def _parse_text_table(text: str) -> list[dict]:
    """Best-effort parser for Volatility's default tabular output."""
    lines = [l.rstrip() for l in text.splitlines() if l.strip()]
    if len(lines) < 2:
        return []
    # Find header line — usually the first line with multiple words separated by 2+ spaces
    header_idx = 0
    for i, line in enumerate(lines):
        if re.search(r"\S\s{2,}\S", line):
            header_idx = i
            break
    header = re.split(r"\s{2,}", lines[header_idx].strip())
    rows: list[dict] = []
    for line in lines[header_idx + 1:]:
        if set(line.strip()) <= {"-", "*", "="}:  # divider lines
            continue
        cols = re.split(r"\s{2,}", line.strip())
        if len(cols) < 2:
            continue
        # Pad/truncate to header length
        if len(cols) < len(header):
            cols = cols + [""] * (len(header) - len(cols))
        rows.append(dict(zip(header, cols[: len(header)])))
    return rows


def run_plugin(image_path: str | Path, plugin: str,
               *, timeout: int | None = None) -> PluginRun:
    """Execute a single Volatility 3 plugin against `image_path`."""
    image = str(image_path)
    if not Path(image).exists():
        return PluginRun(plugin=plugin, ok=False, duration_ms=0,
                         error=f"Image not found: {image}")

    timeout = timeout or settings.VOLATILITY_TIMEOUT
    started = time.monotonic()

    # First attempt: JSON renderer
    cmd = _build_command(image, plugin, renderer="json")
    logger.info("Running Volatility: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return PluginRun(plugin=plugin, ok=False,
                         duration_ms=int((time.monotonic() - started) * 1000),
                         error=f"Timeout after {timeout}s")
    except FileNotFoundError as exc:
        return PluginRun(plugin=plugin, ok=False, duration_ms=0,
                         error=f"Volatility binary not found ({exc}).")

    duration_ms = int((time.monotonic() - started) * 1000)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    rows: list[dict] = []
    if stdout.strip():
        try:
            data = json.loads(stdout)
            if isinstance(data, list):
                rows = [r for r in data if isinstance(r, dict)]
            elif isinstance(data, dict):
                rows = [data]
        except json.JSONDecodeError:
            rows = []

    # If JSON parsing produced nothing usable, fall back to text renderer.
    if not rows and proc.returncode == 0:
        cmd_text = _build_command(image, plugin, renderer="pretty")
        try:
            proc_text = subprocess.run(
                cmd_text, capture_output=True, text=True, timeout=timeout, check=False,
            )
            stdout = proc_text.stdout or stdout
            stderr = (stderr + "\n" + (proc_text.stderr or "")).strip()
            rows = _parse_text_table(stdout)
        except subprocess.TimeoutExpired:
            pass  # keep the original output

    if proc.returncode != 0 and not rows:
        return PluginRun(
            plugin=plugin, ok=False, duration_ms=duration_ms,
            raw_output=stdout, error=stderr.strip() or f"Exit {proc.returncode}",
        )

    return PluginRun(
        plugin=plugin, ok=True, duration_ms=duration_ms,
        raw_output=stdout, rows=rows, error=stderr.strip() if proc.returncode else "",
    )


def detect_os(image_path: str | Path) -> str:
    """Heuristic OS detection — try `windows.info`, then `linux.banner`."""
    for plugin, label in (("windows.info", "windows"),
                          ("linux.banners", "linux"),
                          ("mac.mount", "mac")):
        run = run_plugin(image_path, plugin, timeout=300)
        if run.ok and (run.rows or run.raw_output):
            return label
    return "unknown"
