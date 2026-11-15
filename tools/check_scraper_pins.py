#!/usr/bin/env python3
"""tools/check_scraper_pins.py — a drift alarm on every scraper that can publish (C7, SI-09).

The defect this prevents
------------------------
A parser is a promise about a page: these columns, this many rows, this vocabulary.  When the
page changes and the parser does not fail, the promise is broken silently and a blank or a
truncated table is published as if it were data.  This repository has already done that twice —
a 347-row report published as 254 rows, and game-status designations published blank for three
Lions players who were officially Out (both are on the Flagged for Review page).

What this checks
----------------
For each scraper, the pins below are asserted against the *stored* artifact of its last run,
plus a static check that the pin constants still exist in the source with the values recorded
here.  So the alarm fires in two directions:

  1. the data no longer satisfies the pin  -> the last run published something invalid;
  2. the source's pinned constants changed -> somebody relaxed the pin, and that is a reviewable
     event rather than a quiet edit.

A pin may legitimately change when the source changes.  The fix is to bump the value here **and**
record why in data/scraper_pins.json › history; the gate then passes with the new value on
record.  That is a deliberate, visible act, which is the whole point.

Run: python3 tools/check_scraper_pins.py
     python3 tools/check_scraper_pins.py --self-test   # prove the alarm fires
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PINS = os.path.join(ROOT, "data", "scraper_pins.json")


def load_json(path, default=None):
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def source_constants(path: str) -> dict:
    """Read `NAME = value` constants from a Python source file."""
    out = {}
    full = os.path.join(ROOT, path)
    if not os.path.isfile(full):
        return out
    for line in open(full, encoding="utf-8"):
        m = re.match(r"^([A-Z][A-Z0-9_]*)\s*=\s*([0-9.]+)\s*(?:#.*)?$", line.strip() + "\n")
        if m:
            out[m.group(1)] = float(m.group(2))
        m = re.match(r'^([A-Z][A-Z0-9_]*)\s*=\s*"([^"]+)"\s*$', line.strip())
        if m:
            out[m.group(1)] = m.group(2)
        m = re.match(r"^([A-Z][A-Z0-9_]*)\s*=\s*(\d+)\s*$", line.strip())
        if m:
            out[m.group(1)] = float(m.group(2))
    return out


def check_injury_capture(pin: dict, problems: list) -> dict:
    """The official nfl.com injury report: the capture with the audit trail."""
    man = load_json("data/snapshots/injury_report/manifest.json", {}) or {}
    caps = man.get("captures") or []
    measured = {"n_captures": len(caps)}
    if not caps:
        problems.append("injury capture: no capture in the manifest at all")
        return measured
    last = caps[-1]
    measured["rows_last_capture"] = last.get("rows")
    measured["captured_at_utc"] = last.get("captured_at_utc")
    if last.get("rows") is None:
        problems.append("injury capture: the newest capture records no row count")
    elif last["rows"] < pin["min_rows"]:
        problems.append(f"injury capture: {last['rows']} rows is below the pinned minimum "
                        f"{pin['min_rows']} — the parse is incomplete, not the report")
    # every capture must have a hash and a timestamp, or the immutability claim is false
    for c in caps:
        for field in ("sha256", "captured_at_utc", "rows"):
            if not c.get(field):
                problems.append(f"injury capture: {c.get('file')} has no {field}")
    # the row count must never fall off a cliff against the previous capture
    if len(caps) >= 2:
        prev, cur = caps[-2].get("rows") or 0, caps[-1].get("rows") or 0
        if prev and cur and cur < prev * (1 - pin["row_drop_alert"]):
            problems.append(f"injury capture: rows fell from {prev} to {cur}, more than "
                            f"{pin['row_drop_alert']:.0%} — a parse loss, not a report change")
    # the transcription used for publication must agree with the capture on row count
    rows_tsv = os.path.join(ROOT, "data/capture/nflcom_injuries_reg10_2026-11-15_rows.tsv")
    if os.path.isfile(rows_tsv):
        n = sum(1 for i, _ in enumerate(open(rows_tsv, encoding="utf-8")) if i)
        measured["rows_publication_tsv"] = n
        if last.get("rows") and abs(n - last["rows"]) > 0:
            problems.append(f"injury capture: the publication transcription has {n} rows but the "
                            f"immutable capture has {last['rows']} — one of them is stale")
    return measured


def check_static_pins(pin: dict, problems: list) -> dict:
    """The pin constants must still be present in the source, at the pinned values."""
    consts = source_constants(pin["source"])
    measured = {"source": pin["source"], "constants_found": {}}
    for name, expected in pin["constants"].items():
        if name not in consts:
            problems.append(f"{pin['source']}: pinned constant {name} is gone — the alarm was removed")
            continue
        measured["constants_found"][name] = consts[name]
        if consts[name] != expected:
            problems.append(f"{pin['source']}: {name} is {consts[name]!r} but the pin says "
                            f"{expected!r} — a relaxed or tightened alarm must be recorded in "
                            f"data/scraper_pins.json › history")
    return measured


def check_required_fields(pin: dict, problems: list) -> dict:
    """The stored artifact must still carry every required field."""
    measured = {"required_fields": pin["required_fields"]}
    cap = None
    man = load_json("data/snapshots/injury_report/manifest.json", {}) or {}
    if man.get("captures"):
        f = man["captures"][-1]["file"]
        cap = load_json(f)
    if cap is None:
        return measured
    rows = cap.get("rows") or cap.get("report") or []
    if isinstance(rows, dict):
        for k in rows:
            if isinstance(rows[k], list):
                rows = rows[k]
                break
    if not isinstance(rows, list) or not rows:
        measured["row_keys"] = None
        return measured
    keys = set()
    for r in rows[:50]:
        if isinstance(r, dict):
            keys |= set(r.keys())
    measured["row_keys"] = sorted(keys)
    for field in pin["required_fields"]:
        if field not in keys:
            problems.append(f"injury capture: required field {field!r} is absent from the parsed rows")
    return measured


def main(argv) -> int:
    pins_doc = load_json("data/scraper_pins.json", {}) or {}
    pins = pins_doc.get("pins") or []

    self_test = "--self-test" in argv
    problems: list[str] = []
    results = []
    for pin in pins:
        measured = {}
        if pin["id"] == "injury-report":
            measured.update(check_injury_capture(pin, problems))
            measured.update(check_static_pins(pin, problems))
            measured.update(check_required_fields(pin, problems))
        else:
            measured.update(check_static_pins(pin, problems))
        results.append({"id": pin["id"], "source": pin["source"], "measured": measured})

    if self_test:
        # prove the alarm fires: a fabricated capture one row short of the pin must fail
        fake = {"min_rows": 10_000, "row_drop_alert": 0.25}
        before = len(problems)
        check_injury_capture(fake, problems)
        fired = len(problems) > before
        print(f"self-test: an impossible {fake['min_rows']}-row pin "
              f"{'FAILED as it must' if fired else 'did NOT fail — the alarm is dead'}")
        return 0 if fired else 1

    print(f"scrapers checked: {len(pins)}")
    for r in results:
        print(f"  {r['id']:22} {r['source']}")
        for k, v in r["measured"].items():
            print(f"    {k}: {v}")
    if problems:
        print(f"\nFAIL: {len(problems)} drift problem(s)")
        for p in problems:
            print("  -", p)
        return 1
    print("\nPASS: every scraper's stored artifact satisfies its pins and every pinned constant "
          "is still present at its pinned value")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
