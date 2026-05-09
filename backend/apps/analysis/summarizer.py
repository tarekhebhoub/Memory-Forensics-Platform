"""Per-plugin summarization helpers."""
from __future__ import annotations

from collections import Counter


def _take(rows, key, n=10):
    vals = [str(r.get(key, "")) for r in rows if r.get(key)]
    return Counter(vals).most_common(n)


def summarize_plugin(plugin: str, rows: list[dict]) -> dict:
    rows = rows or []
    base = {"row_count": len(rows)}

    if plugin in ("windows.pslist", "windows.pstree"):
        base["top_processes"] = _take(rows, "ImageFileName") or _take(rows, "Name")
        return base

    if plugin == "windows.netscan":
        proto = Counter(str(r.get("Proto") or r.get("Protocol") or "") for r in rows)
        states = Counter(str(r.get("State") or "") for r in rows)
        base["by_proto"] = proto.most_common()
        base["by_state"] = states.most_common()
        return base

    if plugin == "windows.malfind":
        base["affected_processes"] = _take(rows, "Process") or _take(rows, "ImageFileName")
        return base

    if plugin == "windows.svcscan":
        base["service_states"] = _take(rows, "State")
        base["service_starts"] = _take(rows, "Start")
        return base

    if plugin == "windows.cmdline":
        base["top_cmdlines"] = _take(rows, "ImageFileName")
        return base

    return base
