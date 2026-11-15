#!/usr/bin/env python3
"""build_week11_context.py — fixture context for Week 11, built only from published schedule facts (P3).

Session 55dc53f4-nfl1. Recorded for later evaluation; shadow-v1 does NOT use these fields.
Inputs (all in the repository, all official or derived from official dates):
  * data/shadow/corpus_v1.csv          weeks 1-10 finals with official dates (nfl.com week pages)
  * data/verified/week10_fixtures_2026.csv  official Week 10 dates and kickoffs (nfl.com week-10 page)
  * data/shadow/week11_venues.csv      Week 11 dates, kickoffs and venues (nfl.com game centres)
  * referee/data/official/nflcom_divisions_2026.txt  official division groupings (nfl.com standings)
Cross-check: data/model/snapshot.json (earlier build) — kickoffs and rest days are compared, not copied.

Definitions (recorded in the output):
  rest_days   = calendar days from a club's previous game date to this game's date
  short_week  = rest_days <= 4 (a Thursday after a Sunday, or a Monday-after-Thursday style short turn)
  division    = both clubs in the same official four-club group

    python3 tools/build_week11_context.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "data/shadow/corpus_v1.csv")
WEEK10 = os.path.join(ROOT, "data/verified/week10_fixtures_2026.csv")
VENUES = os.path.join(ROOT, "data/shadow/week11_venues.csv")
DIVISIONS = os.path.join(ROOT, "referee/data/official/nflcom_divisions_2026.txt")
SNAPSHOT = os.path.join(ROOT, "data/model/snapshot.json")
OUT = os.path.join(ROOT, "data/shadow/week11_context.json")


def divisions() -> dict:
    group = {}
    with open(DIVISIONS, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split()
            conf, num, teams = parts[0], parts[1], parts[2:]
            for t in teams:
                group[t] = f"{conf}-{num}"
    return group


def last_dates() -> dict:
    """Team -> list of played-or-scheduled dates before Week 11 (corpus + official Week 10 schedule)."""
    dates: dict[str, set] = {}
    with open(CORPUS, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = dt.date.fromisoformat(r["gameday"])
            dates.setdefault(r["away_abbr"], set()).add(d)
            dates.setdefault(r["home_abbr"], set()).add(d)
    with open(WEEK10, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = dt.date.fromisoformat(r["gameday"])
            dates.setdefault(r["away_abbr"], set()).add(d)
            dates.setdefault(r["home_abbr"], set()).add(d)
    return dates


def main() -> int:
    grp = divisions()
    dates = last_dates()
    venues = list(csv.DictReader(open(VENUES, newline="", encoding="utf-8")))
    snap = {f["game_id"]: f for f in json.load(open(SNAPSHOT, encoding="utf-8"))["fixtures"]}

    games, checks = [], {"kickoff_match": 0, "rest_match": 0, "checked": 0, "mismatch": []}
    for v in sorted(venues, key=lambda r: (r["gameday"], r["game_id"])):
        gd = dt.date.fromisoformat(v["gameday"])
        rec = {"game_id": v["game_id"], "weekday": v["weekday"], "gameday": v["gameday"],
               "kickoff_et_as_printed": v["kickoff_et_as_printed"], "away": v["away"], "home": v["home"],
               "stadium_as_printed": v["stadium_as_printed"], "location_as_printed": v["location_as_printed"],
               "game_centre_url": v["game_centre_url"], "division_game": grp.get(v["away"]) is not None and grp.get(v["away"]) == grp.get(v["home"])}
        for side in ("away", "home"):
            team = v[side]
            prev = max((d for d in dates.get(team, set()) if d < gd), default=None)
            rest = (gd - prev).days if prev else None
            rec[f"{side}_previous_game_date"] = prev.isoformat() if prev else None
            rec[f"{side}_rest_days"] = rest
            rec[f"{side}_short_week"] = (rest is not None and rest <= 4)
        games.append(rec)
        s = snap.get(v["game_id"])
        if s:
            checks["checked"] += 1
            # compare kickoff as HH:MM 24h
            hhmm = _to24(v["kickoff_et_as_printed"])
            if s["gametime"] == hhmm:
                checks["kickoff_match"] += 1
            else:
                checks["mismatch"].append((v["game_id"], "kickoff", s["gametime"], hhmm))
            if s["home_rest"] == rec["home_rest_days"] and s["away_rest"] == rec["away_rest_days"]:
                checks["rest_match"] += 1
            else:
                checks["mismatch"].append((v["game_id"], "rest", (s["away_rest"], s["home_rest"]), (rec["away_rest_days"], rec["home_rest_days"])))

    out = {
        "what": "Week 11 fixture context from published schedule facts. Recorded, not used by shadow-v1.",
        "definitions": {"rest_days": "calendar days from the club's previous game date to this game",
                        "short_week": "rest_days <= 4", "division_game": "same official four-club group"},
        "sources": ["data/shadow/corpus_v1.csv (nfl.com week pages)", "data/verified/week10_fixtures_2026.csv (nfl.com week-10 page)",
                    "data/shadow/week11_venues.csv (nfl.com game centres)", "referee/data/official/nflcom_divisions_2026.txt (nfl.com standings)"],
        "cross_check_vs_snapshot": {"games_compared": checks["checked"], "kickoff_matches": checks["kickoff_match"],
                                    "rest_matches": checks["rest_match"], "mismatches": checks["mismatch"]},
        "games": games,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(games)} games; snapshot kickoff {checks['kickoff_match']}/{checks['checked']}, "
          f"rest {checks['rest_match']}/{checks['checked']}; mismatches {checks['mismatch']}")
    return 0


def _to24(s: str) -> str:
    t = s.strip().upper()
    hm, ap = t.split(" ")
    h, m = hm.split(":")
    h = int(h) % 12 + (12 if ap == "PM" else 0)
    return f"{h:02d}:{int(m):02d}"


if __name__ == "__main__":
    sys.exit(main())
