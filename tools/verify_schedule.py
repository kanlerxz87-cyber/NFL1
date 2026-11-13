#!/usr/bin/env python3
"""Check the published model lines against the official schedule transcription.

The audit compares the model's CURRENT week (data/model/lines.json `week`) against the
official schedule transcription for that week in data/audit/4c043747/. When the model
rolls to a new week, the transcription for that week must be added there (retrieval
recorded in the file header) — this tool fails loudly rather than comparing different
weeks silently. A game matches when away, home and date are identical.
Club codes: nfl.com uses LAR and AZ; the pipeline uses LA and ARI (mapped here).
Output: data/dashboard/schedule_check.json (consumed by the dashboard data layer).
"""
import json
import os
import csv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE = {"LAR": "LA", "AZ": "ARI"}


def read_tsv(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            rows.append(line.split("\t"))
    header = rows[0]
    return [dict(zip(header, r)) for r in rows[1:]]


def main():
    lines_doc = json.load(open(os.path.join(ROOT, "data/model/lines.json"), encoding="utf-8"))
    week = lines_doc["week"]
    sched_path = os.path.join(ROOT, "data/audit/4c043747", f"schedule_week{week}_20261113.tsv")
    if not os.path.exists(sched_path):
        raise SystemExit(
            f"no official schedule transcription for week {week} ({sched_path}). "
            "Add one to data/audit/4c043747/ before auditing this week's lines.")
    raw_rows = read_tsv(sched_path)
    byes_row = next((r for r in raw_rows if r.get("away") == "bye_teams"), None)
    games = [r for r in raw_rows
             if r.get("away") and r.get("home") and r["away"] != "bye_teams"]
    off = {(CODE.get(g["away"], g["away"]), CODE.get(g["home"], g["home"]), g["gameday"])
           for g in games}
    mod = {(g["away"], g["home"], g["gameday"]) for g in lines_doc["lines"]}
    result = {
        "checked_on": "2026-11-13",
        "week": week,
        "official_games": len(off),
        "model_games": len(mod),
        "matched": len(off & mod),
        "official_not_in_model": sorted(off - mod),
        "model_not_in_official": sorted(mod - off),
        "bye_teams_official": sorted(byes_row["home"].split()) if byes_row else [],
        "result": "PASS" if off == mod else "FAIL",
    }
    with open(os.path.join(ROOT, "data/dashboard/schedule_check.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
