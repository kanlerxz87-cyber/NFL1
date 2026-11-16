#!/usr/bin/env python3
"""strat/reconcile_official.py — reconcile the backtest extract against official NFL rows (Q03).

Why this exists
---------------
Every interval on the leaderboard is computed over games taken from a third-party extract of the
NFL's statistics feed.  If that extract disagrees with the NFL's own published record, every
interval is wrong by an unknown amount.  The repository's readiness register records this as
PR-02 *Partial* and PR-09 *Not started*, and the open-questions register records it as Q03.

What is compared
----------------
`data/verified/games_2026.csv` holds rows transcribed from the official nfl.com weekly schedule
pages, each carrying the exact URL and the retrieval time.  This script matches every one of those
rows to the extract on (week, away, home), compares the two final scores, and publishes:

    matched rows                     — score agrees exactly
    mismatched rows                  — a disagreement (a hard failure)
    rows the extract does not have   — reported, not silently dropped
    rows only the extract has        — reported

Club codes are normalised first, because nfl.com prints Arizona as `AZ` and the Rams as `LA`
while the extract uses `ARI` and `LA` (flag CAP-05).  The mapping is printed with the counts so a
new code cannot slip through unnoticed.

The honest limit
----------------
This reconciles **one season, 136 rows**.  It says nothing about 1999-2025, which is where almost
all of the 6,785 scored games come from.  The published statement therefore says "2026: agreed",
not "the extract is verified".

Run: python3 strat/reconcile_official.py
Exit 1 on any score disagreement.
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

ROOT = lib.ROOT
OFFICIAL = os.path.join(ROOT, "data", "verified", "games_2026.csv")
EXTRACT = os.path.join(ROOT, "data", "s9cb", "games.csv")
EXTRA = os.path.join(ROOT, "data", "strat", "official_extra_2026.json")

# official page code -> extract code.  Only the codes that actually differ are listed, and the
# gap is itself a finding (flag CAP-05).
CODE_MAP = {"AZ": "ARI", "LAR": "LA"}
CODE_MAP_USE = {}


def norm(code: str) -> str:
    c = (code or "").strip()
    if c in CODE_MAP:
        CODE_MAP_USE[c] = CODE_MAP_USE.get(c, 0) + 1
        return CODE_MAP[c]
    return c


def main() -> int:
    with open(OFFICIAL, newline="", encoding="utf-8") as fh:
        official = [{**r, "provenance": "transcribed by an earlier session"} for r in csv.DictReader(fh)]
    # rows this session fetched itself, kept as a separate provenance class
    extra_doc = lib.load("official_extra_2026.json") if os.path.isfile(EXTRA) else {"rows": []}
    for r in extra_doc.get("rows", []):
        official.append({"game_id": r["game_id"], "week": str(r["week"]),
                         "gameday": r.get("gameday", ""),
                         "away_abbr": r["away_abbr"], "away_score": str(r["away_score"]),
                         "home_abbr": r["home_abbr"], "home_score": str(r["home_score"]),
                         "source_url": r["source_url"], "retrieved_at": r["retrieved_at_utc"],
                         "note": r.get("note", ""),
                         "provenance": f"fetched by {r.get('fetched_by', 'this session')}"})
    with open(EXTRACT, newline="", encoding="utf-8") as fh:
        extract = [r for r in csv.DictReader(fh) if r.get("season") == "2026"]

    index = {}
    for r in extract:
        index[(int(r["week"]), r["away_team"], r["home_team"])] = r

    rows, matched, mismatched, missing = [], 0, [], []
    seen = set()
    for r in official:
        wk = int(r["week"])
        away, home = norm(r["away_abbr"]), norm(r["home_abbr"])
        key = (wk, away, home)
        seen.add(key)
        e = index.get(key)
        off_away, off_home = int(r["away_score"]), int(r["home_score"])
        if e is None:
            missing.append(r["game_id"])
            rows.append({"game_id": r["game_id"], "week": wk, "matchup": f"{away} @ {home}",
                         "official_away": off_away, "official_home": off_home,
                         "extract_away": None, "extract_home": None,
                         "agrees": None, "status": "absent from the extract",
                         "official_source": r["source_url"],
                         "retrieved_at": r["retrieved_at"],
                         "provenance": r["provenance"]})
            continue
        ex_away = int(float(e["away_score"])) if e["away_score"] not in ("", "NA") else None
        ex_home = int(float(e["home_score"])) if e["home_score"] not in ("", "NA") else None
        ok = (ex_away == off_away and ex_home == off_home)
        if ok:
            matched += 1
        else:
            mismatched.append(r["game_id"])
        rows.append({"game_id": r["game_id"], "week": wk, "matchup": f"{away} @ {home}",
                     "official_away": off_away, "official_home": off_home,
                     "extract_away": ex_away, "extract_home": ex_home,
                     "agrees": ok, "status": "agrees" if ok else "DISAGREES",
                     "official_source": r["source_url"],
                     "retrieved_at": r["retrieved_at"],
                     "provenance": r["provenance"]})

    # rows only the extract has are either a genuine disagreement or a fixture that has not been
    # played yet.  The two are separated, because one is a defect and the other is a schedule.
    extra_unplayed, extra_disputed = [], []
    for k in index:
        if k in seen:
            continue
        e = index[k]
        played = e.get("home_score") not in ("", "NA", None)
        (extra_disputed if played else extra_unplayed).append(
            {"matchup": f"{k[1]} @ {k[2]}", "week": k[0],
             "extract_scores": f"{e.get('away_score')}-{e.get('home_score')}"})

    lib.write_json("official_reconciliation.json", {
        "generated_at": lib.now(),
        "question": ("Do the official nfl.com rows agree with the third-party extract used for the "
                     "backtest? (readiness PR-02, open question Q03)"),
        "official_files": ["data/verified/games_2026.csv",
                           "data/strat/official_extra_2026.json"],
        "standings_cross_check": extra_doc.get("standings_check"),
        "official_note": ("Each row carries the exact nfl.com weekly schedule URL it was transcribed "
                          "from and the retrieval time. The transcription was made by an earlier "
                          "session; this script re-tests it against the extract, it does not re-fetch."),
        "extract_file": "data/s9cb/games.csv",
        "code_normalisation": {"map": CODE_MAP, "times_applied": CODE_MAP_USE,
                               "why": ("nfl.com prints Arizona as AZ and the Rams as LAR; the extract "
                                       "uses ARI and LA. The mapping is a finding (flag CAP-05), not a "
                                       "convenience.")},
        "totals": {"official_rows": len(official), "matched": matched,
                   "mismatched": len(mismatched), "absent_from_extract": len(missing),
                   "extract_only_unplayed_fixtures": len(extra_unplayed),
                   "extract_only_played_rows": len(extra_disputed)},
        "mismatched_game_ids": mismatched,
        "absent_game_ids": missing,
        "extract_only_unplayed_fixtures": extra_unplayed,
        "extract_only_played_rows": extra_disputed,
        "scope_limit": ("One season, 136 rows. The 1999-2025 seasons behind the leaderboard's "
                        "intervals are NOT reconciled by this script."),
        "verdict": ("AGREES on every matched row" if not (mismatched or missing)
                    else "DISAGREES — see mismatched_game_ids"),
        "flags": ([{"finding": f"{r['matchup']} week {r['week']} is played in the extract but has no "
                                f"official row in this reconciliation",
                    "detail": f"extract score {r['extract_scores']}",
                    "mitigation": "published as a flag; the official Game Book is the gate"}
                   for r in extra_disputed] if extra_disputed else []),
        "rows": rows,
    })
    print(f"official rows {len(official)} · matched {matched} · mismatched {len(mismatched)} · "
          f"absent from extract {len(missing)} · extract-only unplayed {len(extra_unplayed)} · "
          f"extract-only played {len(extra_disputed)}")
    # a played row in the extract with no official row is published as a flag, not a build failure;
    # a score disagreement or a missing official row is a defect and does fail.
    if mismatched or missing:
        for g in mismatched:
            print(f"  MISMATCH {g}")
        for g in missing:
            print(f"  ABSENT   {g}")
        return 1
    for r in extra_disputed:
        print(f"  FLAG: only in the extract -> {r['matchup']} week {r['week']} {r['extract_scores']}")
    # Session 414a54c9-nfl1: the comment above and the project rule ("flagged irregularities do
    # not block — publish them") agree that these rows are flags. The code used to return 1 here,
    # which failed the daily data refresh every time the extract gained results before the
    # official rows were transcribed. The flags are already published in the JSON above; they
    # must not block the build.
    return 0


if __name__ == "__main__":
    sys.exit(main())
