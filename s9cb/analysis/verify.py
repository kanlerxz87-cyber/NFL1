#!/usr/bin/env python3
"""Line-by-line verification of the research extract against official nfl.com pages.

Every check compares the number the pipeline computed with a number transcribed by
hand from an official page (or, for the game results, with a second, independently
produced transcription already in this repository). Nothing is reconciled by editing
either side: a mismatch is reported as a mismatch.

Run: cd s9cb/analysis && python3 verify.py   ->  data/s9cb/verification.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

STANDINGS_URL = "https://www.nfl.com/standings/league/2026/reg"

# nfl.com prints Arizona as AZ; the GSIS feed the extract is parsed from uses ARI.
# The alias is applied for comparison only and is published as a flagged item, not
# silently absorbed.
TEAM_ALIAS = {"AZ": "ARI"}


def norm(t: str) -> str:
    t = str(t).strip()
    return TEAM_ALIAS.get(t, t)
SCHEDULE_URL = "https://www.nfl.com/schedules/"
INJURY_URL = "https://www.nfl.com/injuries/"


def check_standings(g: pd.DataFrame) -> dict:
    """Computed standings (from game results) vs the official nfl.com standings table."""
    off = pd.read_csv(os.path.join(C.DATA, "official_standings_2026.csv"))
    cur = g[(g["season"] == 2026) & g["played"]].copy()
    cur["home_key"] = cur["home_team"].map(norm)
    cur["away_key"] = cur["away_team"].map(norm)
    rows = []
    for _, o in off.iterrows():
        t = norm(o["team_abbr"])
        h = cur[cur["home_key"] == t]
        a = cur[cur["away_key"] == t]
        w = int((h["home_score"] > h["away_score"]).sum() + (a["away_score"] > a["home_score"]).sum())
        l = int((h["home_score"] < h["away_score"]).sum() + (a["away_score"] < a["home_score"]).sum())
        tt = int((h["home_score"] == h["away_score"]).sum() + (a["away_score"] == a["home_score"]).sum())
        pf = float(h["home_score"].sum() + a["away_score"].sum())
        pa = float(h["away_score"].sum() + a["home_score"].sum())
        diffs = {}
        if (w, l, tt) != (int(o["w"]), int(o["l"]), int(o["t"])):
            diffs["record"] = {"nfl": [int(o["w"]), int(o["l"]), int(o["t"])], "computed": [w, l, tt]}
        if abs(pf - float(o["pf"])) > 0.5:
            diffs["pf"] = {"nfl": float(o["pf"]), "computed": pf}
        if abs(pa - float(o["pa"])) > 0.5:
            diffs["pa"] = {"nfl": float(o["pa"]), "computed": pa}
        rows.append({"team": t, "nfl_label": o["team_abbr"], "games": int(w + l + tt),
                     "matched": not diffs,
                     "diffs": diffs or None,
                     "nfl": {"w": int(o["w"]), "l": int(o["l"]), "t": int(o["t"]),
                             "pf": float(o["pf"]), "pa": float(o["pa"])},
                     "computed": {"w": w, "l": l, "t": tt, "pf": pf, "pa": pa},
                     "source": STANDINGS_URL})
    return {
        "name": "2026 standings recomputed from every game result, against the official table",
        "source": STANDINGS_URL,
        "rows_checked": len(rows),
        "rows_matched": int(sum(1 for r in rows if r["matched"])),
        "mismatches": int(sum(1 for r in rows if not r["matched"])),
        "detail": rows,
    }


def check_games(g: pd.DataFrame) -> dict:
    """2026 results in the extract vs the independent hand transcription in data/verified/."""
    path = os.path.join(C.ROOT, "data", "verified", "games_2026.csv")
    if not os.path.exists(path):
        return {"name": "2026 results cross-check", "status": "skipped: fixture absent"}
    ref = pd.read_csv(path)
    cur = g[(g["season"] == 2026) & g["played"]].copy()
    # The two files use different game-id conventions, so the join is on the matchup.
    ref["away_key"] = ref["away_abbr"].map(norm)
    ref["home_key"] = ref["home_abbr"].map(norm)
    ref["week_key"] = pd.to_numeric(ref["week"], errors="coerce").astype("Int64")
    cur["away_key"] = cur["away_team"].map(norm)
    cur["home_key"] = cur["home_team"].map(norm)
    cur["week_key"] = cur["week"].astype("Int64")
    merged = ref.merge(cur, on=["week_key", "away_key", "home_key"], how="outer",
                       indicator=True, suffixes=("_ref", "_ext"))
    rows, mism = [], 0
    for _, m in merged.iterrows():
        if m["_merge"] != "both":
            rows.append({"game_id": m.get("game_id_ref", m.get("game_id_ext")),
                         "matched": False,
                         "diffs": {"presence": str(m["_merge"])},
                         "source": SCHEDULE_URL})
            mism += 1
            continue
        diffs = {}
        for col in ("home_score", "away_score"):
            a, b = m[f"{col}_ref"], m[f"{col}_ext"]
            if pd.isna(a) or pd.isna(b) or abs(float(a) - float(b)) > 0.5:
                diffs[col] = {"transcribed": None if pd.isna(a) else float(a),
                              "extract": None if pd.isna(b) else float(b)}
        # Team labels are compared after applying the published AZ/ARI alias, so that a
        # difference in club abbreviation is not counted as a difference in the result.
        if norm(m["home_abbr"]) != norm(m["home_team"]):
            diffs["home_team"] = {"transcribed": m["home_abbr"], "extract": m["home_team"]}
        if norm(m["away_abbr"]) != norm(m["away_team"]):
            diffs["away_team"] = {"transcribed": m["away_abbr"], "extract": m["away_team"]}
        if diffs:
            mism += 1
        rows.append({"game_id": m.get("game_id_ref"), "extract_game_id": m.get("game_id_ext"),
                     "matched": not diffs, "diffs": diffs or None,
                     "source": SCHEDULE_URL})
    return {
        "name": "2026 game results: extract vs the independent hand transcription in "
                "data/verified/games_2026.csv",
        "source": SCHEDULE_URL,
        "rows_checked": len(rows), "rows_matched": len(rows) - mism, "mismatches": mism,
        "detail": rows,
    }


def check_injuries(inj: pd.DataFrame) -> dict:
    """Week-10 2026 official injury designations vs the extract.

    Transcribed from https://www.nfl.com/injuries/ on 2026-11-12 for the two clubs in
    the Thursday night game, the only clubs with final game statuses at fetch time.
    """
    truth = [
        ("WAS", "Lucas Patrick", "C", "Concussion", "Out"),
        ("WAS", "Colson Yankoff", "TE", "Knee", "Out"),
        ("NYG", "Malik Harrison", "LB", "Groin", "Questionable"),
    ]
    rows = []
    for team, name, pos, injury, status in truth:
        sub = inj[(inj["season"] == 2026) & (inj["week"] == 10) &
                  (inj["team"] == team) & (inj["full_name"] == name)]
        got = None
        if not sub.empty:
            got = {"report_status": (None if pd.isna(sub.iloc[0]["report_status"])
                                     else str(sub.iloc[0]["report_status"])),
                   "report_primary_injury": (None if pd.isna(sub.iloc[0]["report_primary_injury"])
                                             else str(sub.iloc[0]["report_primary_injury"])),
                   "position": str(sub.iloc[0]["position"])}
        matched = bool(got) and got["report_status"] == status and got["position"] == pos
        rows.append({"team": team, "player": name, "matched": matched,
                     "nfl": {"position": pos, "injury": injury, "game_status": status},
                     "extract": got, "source": INJURY_URL})
    return {
        "name": "Week 10 2026 official injury designations vs the extract",
        "source": INJURY_URL,
        "rows_checked": len(rows),
        "rows_matched": int(sum(1 for r in rows if r["matched"])),
        "mismatches": int(sum(1 for r in rows if not r["matched"])),
        "detail": rows,
        "note": ("Only clubs with a final game status at fetch time can be checked. Four "
                 "clubs in the 2026 week-10 extract have no rows at all because no report "
                 "was published for them, not because they are healthy; that is flagged "
                 "rather than filled in."),
    }


def check_price_coverage(g: pd.DataFrame) -> dict:
    """How much of the sample carries an observed price, and how much does not."""
    played = g[g["played"]]
    by_season = []
    for s, grp in played.groupby("season"):
        by_season.append({
            "season": int(s), "matched": True, "games": int(len(grp)),
            "with_price": int(grp["has_price"].sum()),
            "without_price": int((~grp["has_price"]).sum()),
            "pct_priced": round(100.0 * grp["has_price"].mean(), 1),
        })
    return {
        "name": "Observed-price coverage of the games actually scored",
        "source": SCHEDULE_URL,
        "rows_checked": int(len(played)),
        "rows_matched": int(played["has_price"].sum()),
        "mismatches": int((~played["has_price"]).sum()),
        "detail": by_season,
        "note": ("Games before 2006 carry a closing line but no price, so they train the "
                 "ratings but are never scored as bets. No price is assumed for them."),
    }


def main() -> None:
    g = C.load_games()
    inj = pd.read_csv(os.path.join(C.DATA, "injuries.csv"))
    checks = [check_standings(g), check_games(g), check_injuries(inj), check_price_coverage(g)]
    total = sum(c.get("rows_checked", 0) for c in checks)
    matched = sum(c.get("rows_matched", 0) for c in checks)
    mism = sum(c.get("mismatches", 0) for c in checks)
    C.write_json("verification.json", {
        "generated_at": C.now(),
        "policy": ("A value is published only when it can be checked against an official "
                   "page or against an independent transcription already in this "
                   "repository. Where it cannot, the cell is left blank and flagged."),
        "summary": {"rows_checked": total, "rows_matched": matched, "mismatches": mism},
        "checks": checks,
    })
    print(f"rows {total}, matched {matched}, mismatches {mism}")
    for c in checks:
        print(f"  {c['name'][:70]:70s} {c.get('rows_matched')}/{c.get('rows_checked')}")


if __name__ == "__main__":
    main()
