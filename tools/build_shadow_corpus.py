#!/usr/bin/env python3
"""build_shadow_corpus.py — the frozen 2026 results corpus for the shadow baseline (P1/P2).

Session 55dc53f4-nfl1. Inputs (all in the repository):
  * data/verified/games_2026.csv   136 regular-season finals, weeks 1-9, transcribed from the
                                   official nfl.com week pages (source_url column on every row).
  * WAS-NYG Week 10 final           Commanders 24, Giants 21, read this session from
                                   https://www.nfl.com/schedules/2026/by-week/week-10 (FINAL line).
                                   Added here as an explicit row; it is the only game added.
  * data/s9cb/games.csv            nflverse release copy (third party). Used ONLY as a second
                                   source to cross-check every score; never as the input.

Output: data/shadow/corpus_v1.csv plus data/shadow/corpus_v1.sha256. Re-running must reproduce
the same bytes; the forecast tool refuses to run if the corpus hash differs from the one recorded
in prereg/shadow-v1.json.

    python3 tools/build_shadow_corpus.py
"""
from __future__ import annotations

import csv
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFICIAL = os.path.join(ROOT, "data/verified/games_2026.csv")
NFLVERSE = os.path.join(ROOT, "data/s9cb/games.csv")
OUT = os.path.join(ROOT, "data/shadow/corpus_v1.csv")
HASH_OUT = os.path.join(ROOT, "data/shadow/corpus_v1.sha256")

WAS_NYG = {
    "game_id": "2026_REG_10_WAS_NYG",
    "week": "10",
    "gameday": "2026-11-12",
    "away_abbr": "WAS",
    "home_abbr": "NYG",
    "away_score": "24",
    "home_score": "21",
    "source_url": "https://www.nfl.com/schedules/2026/by-week/week-10",
    "retrieved_at": "2026-11-15 (date only; the fetch tool records no time of day)",
    "note": "Thursday Night Football; official FINAL line 'Commanders 24, Giants 21, FINAL' read 2026-11-15",
}

# nflverse abbreviations differ from nfl.com for two clubs; map nfl.com -> nflverse for the check only.
NFLVERSE_CODE = {"AZ": "ARI", "LA": "LA", "LAR": "LA"}


def load_official() -> list[dict]:
    with open(OFFICIAL, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["verification"] = "nfl.com week page transcription (games_2026.csv); cross-checked to nflverse; not re-read line by line"
    return rows


def load_nflverse_2026() -> dict:
    out = {}
    with open(NFLVERSE, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["season"] != "2026" or r["away_score"] in ("", "nan"):
                continue
            key = (r["gameday"], r["away_team"], r["home_team"])
            out[key] = (int(float(r["away_score"])), int(float(r["home_score"])))
    return out


def main() -> int:
    official = load_official()
    rows = [dict(r) for r in official]
    war = dict(WAS_NYG)
    war["season"] = "2026"
    war["verification"] = "nfl.com week 10 page, FINAL line read 2026-11-15 (this session); not in games_2026.csv"
    rows.append(war)
    rows.sort(key=lambda r: (int(r["week"]), r["game_id"]))

    nfv = load_nflverse_2026()
    agree = disagree = missing = 0
    mismatches = []
    for r in rows:
        key = (r["gameday"], NFLVERSE_CODE.get(r["away_abbr"], r["away_abbr"]),
               NFLVERSE_CODE.get(r["home_abbr"], r["home_abbr"]))
        if key not in nfv:
            missing += 1
            r["nflverse_check"] = "not found"
            continue
        a, h = nfv[key]
        if (a, h) == (int(r["away_score"]), int(r["home_score"])):
            agree += 1
            r["nflverse_check"] = "agrees"
        else:
            disagree += 1
            r["nflverse_check"] = f"DIFFERS nflverse {a}-{h}"
            mismatches.append((r["game_id"], r["away_abbr"], r["away_score"], r["home_abbr"], r["home_score"], a, h))

    fields = ["game_id", "week", "gameday", "away_abbr", "home_abbr", "away_score", "home_score",
              "source_url", "retrieved_at", "verification", "nflverse_check", "note"]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            r.setdefault("note", "")
            w.writerow(r)
    digest = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    with open(HASH_OUT, "w", encoding="utf-8") as fh:
        fh.write(f"{digest}  corpus_v1.csv\n")

    print(f"corpus rows: {len(rows)}  (weeks: {sorted(set(int(r['week']) for r in rows))})")
    print(f"nflverse agree: {agree}   differ: {disagree}   not found: {missing}")
    for m in mismatches:
        print("  DIFF", m)
    print(f"sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
