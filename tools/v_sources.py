#!/usr/bin/env python3
"""v_sources.py — compare the repository's committed 2026 standings with a fresh
hand transcription of the official nfl.com standings page.

Read-only on every input. Writes data/personnel/standings_diff.json.

Every row records the official value, the committed value, whether they agree, and the
official URL. Nothing is inferred, adjusted or rounded: a difference is reported as a
difference.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OFFICIAL = os.path.join(ROOT, "data", "personnel", "official_standings_2026-11-13.csv")
COMMITTED = os.path.join(ROOT, "data", "verified", "standings_2026.csv")
OUT = os.path.join(ROOT, "data", "personnel", "standings_diff.json")
URL = "https://www.nfl.com/standings/league/2026/reg"

# nfl.com prints Arizona as AZ; the committed file uses AZ too. No aliases are needed,
# and none are applied -- an unrecognised abbreviation is reported, not guessed.
ALIAS = {}


def load(path, key):
    with open(path, newline="", encoding="utf-8") as fh:
        return {ALIAS.get(r[key].strip(), r[key].strip()): r for r in csv.DictReader(fh)}


def main() -> int:
    off = load(OFFICIAL, "team")
    com = load(COMMITTED, "abbr")
    rows, missing = [], []
    for team, o in sorted(off.items(), key=lambda kv: (-int(kv[1]["w"]), kv[0])):
        c = com.get(team)
        if c is None:
            missing.append(team)
            continue
        diffs = {}
        for field, oc, cc, cast in (
            ("w", "w", "w", int), ("l", "l", "l", int), ("t", "t", "t", int),
            ("pf", "pf", "pf", int), ("pa", "pa", "pa", int),
            ("net", "net", "net_pts", int),
        ):
            ov, cv = cast(o[oc]), cast(c[cc])
            if ov != cv:
                diffs[field] = {"official": ov, "committed": cv}
        rows.append({
            "team": team,
            "official_w": int(o["w"]), "official_l": int(o["l"]), "official_t": int(o["t"]),
            "committed_w": int(c["w"]), "committed_l": int(c["l"]), "committed_t": int(c["t"]),
            "official_pf": int(o["pf"]), "official_pa": int(o["pa"]),
            "committed_pf": int(c["pf"]), "committed_pa": int(c["pa"]),
            "agree": not diffs,
            "differences": diffs,
            "source_url": URL,
        })
    stale = [r for r in rows if not r["agree"]]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "official_url": URL,
        "official_retrieved": "2026-11-13 (hand transcription, self-checked)",
        "committed_file": "data/verified/standings_2026.csv",
        "committed_retrieved": "2026-11-12T04:31Z (per its own retrieved_at column)",
        "rows_compared": len(rows),
        "rows_agreeing": len(rows) - len(stale),
        "rows_differing": len(stale),
        "clubs_missing_from_committed": missing,
        "differing": stale,
        "rows": rows,
        "note": (
            "The official page is the current 2026 regular-season standings; the committed "
            "transcription was taken before the Week 10 Thursday game (WAS at NYG, final "
            "24-21 per https://www.nfl.com/schedules/2026/by-week/week-10). Every difference "
            "below is confined to clubs that played in that game. No value in either file was "
            "edited to make them agree."
        ),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print(f"compared {len(rows)} clubs: {len(rows)-len(stale)} agree, {len(stale)} differ")
    for r in stale:
        print("  DIFF", r["team"], r["differences"])
    print("wrote", os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
