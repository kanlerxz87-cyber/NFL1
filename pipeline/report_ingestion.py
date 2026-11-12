#!/usr/bin/env python3
"""Summarize which injury feed the availability build actually used.

The official report is preferred only when it is complete and matches the target
week. The model deliberately falls back to the latest complete mirrored week when
that condition is not met. This report makes that choice visible in GitHub Actions
instead of letting a successful workflow conceal stale-source use.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_PATH = ROOT / "data" / "model" / "official_injuries.json"
AVAILABILITY_PATH = ROOT / "data" / "model" / "availability.json"


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def render_summary(official: dict[str, Any], availability: dict[str, Any]) -> tuple[str, bool]:
    """Return a Markdown summary and whether it needs a warning annotation."""
    status = official.get("status", "missing")
    week = official.get("week")
    counts = official.get("counts") or {}
    source = availability.get("source") or {}
    source_label = source.get("label") or "availability output unavailable"
    source_week = availability.get("week")
    warning = source.get("warning")

    lines = ["## Injury-data ingestion", f"- Official scrape status: **{status}**"]
    if week is not None:
        lines.append(f"- Official report week: {week}")
    if counts:
        lines.append(
            f"- Scraped rows / clubs: {counts.get('rows', 'blank')} / "
            f"{counts.get('teams', 'blank')}"
        )
    lines.append(f"- Availability model source: **{source_label}**")
    if source_week is not None:
        lines.append(f"- Week used by availability model: {source_week}")
    if warning:
        lines.append(f"- Model warning: {warning}")

    # A scrape can be structurally valid but still be for the wrong target week;
    # the authoritative choice is the source actually recorded by the model stage.
    used_fallback = not source_label.startswith("official nfl.com injury report")
    has_warning = status != "ok" or used_fallback or bool(warning)
    if has_warning:
        lines.append(
            "- **Action required:** do not treat injury statuses as current without "
            "checking the official report. The model is using a fallback or incomplete feed."
        )
    else:
        lines.append("- Official report accepted by the availability model.")
    return "\n".join(lines) + "\n", has_warning


def main() -> None:
    official = load_json(OFFICIAL_PATH)
    availability = load_json(AVAILABILITY_PATH)
    summary, warn = render_summary(official, availability)
    print(summary, end="")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(summary)
    if warn:
        source = (availability.get("source") or {}).get("label", "unavailable")
        print(f"::warning::Injury availability source needs review ({source}).")


if __name__ == "__main__":
    main()
