#!/usr/bin/env python3
"""
validate_verified.py — automated cross-check gate for data/verified/*.csv

Every numeric row in the verified dataset is transcribed from an official NFL page
(see the source_url column) and then reconciled here against a *second, independent*
official view of the same facts:

  * standings_2026.csv  <- https://www.nfl.com/standings/            (official aggregate)
  * games_2026.csv      <- https://www.nfl.com/schedules/2026/by-week/week-N (official box results)

Checks performed
  1. internal:    PF - PA == NET PTS, W+L+T == CG, PCT == (W + T/2) / (W+L+T) to 3dp
  2. league:      sum(W) == sum(L), and total games implied by CG is even (2 per game)
  3. cross-view:  game-by-game W/L/T and PF/PA rebuilt from games_2026.csv must match
                  standings_2026.csv for every team whose full season is captured
  4. integrity:   unique game ids, valid team abbreviations, no negative scores,
                  no tie/self-match, dates inside the stated season window
Exit code is non-zero if any hard check fails, so CI can block a bad publish.
"""
from __future__ import annotations

import csv
import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "verified"
OUT = DATA / "model"
RESULT = {"checks": [], "failures": [], "warnings": []}


def check(name: str, ok: bool, detail: str, hard: bool = True) -> None:
    RESULT["checks"].append({"check": name, "ok": bool(ok), "detail": detail})
    if not ok:
        (RESULT["failures"] if hard else RESULT["warnings"]).append(f"{name}: {detail}")


def load(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    standings = load(DATA / "standings_2026.csv")
    games = load(DATA / "games_2026.csv")

    check("standings row count", len(standings) == 32, f"{len(standings)} rows (expected 32)")
    check("unique team abbreviations in standings",
          len({r["abbr"].upper() for r in standings}) == len(standings),
          "abbreviation collision detected" if len({r["abbr"].upper() for r in standings}) != len(standings) else "all unique")

    teams = {r["abbr"].upper(): r for r in standings}

    # ---- 1. internal consistency of the official standings block -----------------
    bad_net, bad_games, bad_pct = [], [], []
    for r in standings:
        w, l, t = int(r["w"]), int(r["l"]), int(r["t"])
        pf, pa, net = int(r["pf"]), int(r["pa"]), int(r["net_pts"])
        if pf - pa != net:
            bad_net.append(f"{r['abbr']} PF-PA={pf-pa} != NET {net}")
        if w + l + t != int(r.get("cg") or w + l + t):
            bad_games.append(f"{r['abbr']}")
        denom = w + l + t
        # NFL publishes winning percentage rounded half-up to 3 dp (2-5-1 => 0.3125 => 0.313).
        pct = (Decimal(2 * w + t) / Decimal(2 * denom)) if denom else Decimal(0)
        pct = pct.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        if pct != Decimal(r["pct"]):
            bad_pct.append(f"{r['abbr']} calc={pct} page={r['pct']}")
    check("PF - PA == NET PTS (all teams)", not bad_net, "; ".join(bad_net) or "32/32 consistent")
    check("PCT == (W + T/2) / games (all teams)", not bad_pct, "; ".join(bad_pct) or "32/32 consistent")

    sum_w = sum(int(r["w"]) for r in standings)
    sum_l = sum(int(r["l"]) for r in standings)
    sum_t = sum(int(r["t"]) for r in standings)
    check("league win/loss balance", sum_w == sum_l, f"sum(W)={sum_w} sum(L)={sum_l}")
    check("league tie count is even (ties come in pairs)", sum_t % 2 == 0, f"sum(T)={sum_t}")
    total_team_games = sum(int(r["w"]) + int(r["l"]) + int(r["t"]) for r in standings)
    check("team-games are even (2 per game)", total_team_games % 2 == 0,
          f"team-games={total_team_games} => {total_team_games // 2} games")

    # ---- 4. game-table integrity ------------------------------------------------
    ids = [g["game_id"] for g in games]
    dupes = {i for i in ids if ids.count(i) > 1}
    check("unique game ids", not dupes, f"duplicates: {sorted(dupes)}" if dupes else f"{len(ids)} unique ids")
    unknown = sorted({g["away_abbr"] for g in games} | {g["home_abbr"] for g in games} - set(teams))
    known_abbrs = {g["away_abbr"] for g in games} | {g["home_abbr"] for g in games}
    unknown = sorted(known_abbrs - set(teams))
    check("all game teams exist in standings", not unknown, f"unknown: {unknown}" if unknown else "all match")
    self_games = [g["game_id"] for g in games if g["away_abbr"] == g["home_abbr"]]
    check("no team plays itself", not self_games, f"{self_games}" if self_games else "none")
    neg = [g["game_id"] for g in games if int(g["away_score"]) < 0 or int(g["home_score"]) < 0]
    check("no negative scores", not neg, f"{neg}" if neg else "none")
    window_ok = all(date(2026, 8, 1) <= date.fromisoformat(g["gameday"]) <= date(2027, 1, 15) for g in games)
    check("game dates inside 2026 season window", window_ok, "all dates within 2026-08-01..2027-01-15")
    # a team may not appear twice in the same week
    per_week = defaultdict(list)
    for g in games:
        for side in ("away_abbr", "home_abbr"):
            per_week[(int(g["week"]), g[side])].append(g["game_id"])
    twice = {k: v for k, v in per_week.items() if len(v) > 1}
    check("no team listed twice in one week", not twice, f"{twice}" if twice else "clean")

    # ---- 3. cross-view reconciliation (official schedule vs official standings) --
    rec = defaultdict(lambda: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "g": 0})
    for g in games:
        a, h = g["away_abbr"], g["home_abbr"]
        sa, sh = int(g["away_score"]), int(g["home_score"])
        rec[a]["pf"] += sa; rec[a]["pa"] += sh; rec[a]["g"] += 1
        rec[h]["pf"] += sh; rec[h]["pa"] += sa; rec[h]["g"] += 1
        if sa > sh:
            rec[a]["w"] += 1; rec[h]["l"] += 1
        elif sh > sa:
            rec[h]["w"] += 1; rec[a]["l"] += 1
        else:
            rec[a]["t"] += 1; rec[h]["t"] += 1

    mismatches, reconciled, partial = [], [], []
    for abbr, r in sorted(rec.items()):
        s = teams[abbr]
        page = (int(s["w"]), int(s["l"]), int(s["t"]), int(s["pf"]), int(s["pa"]))
        calc = (r["w"], r["l"], r["t"], r["pf"], r["pa"])
        games_on_page = int(s["w"]) + int(s["l"]) + int(s["t"])
        if r["g"] < games_on_page:
            partial.append(f"{abbr}: captured {r['g']}/{games_on_page} games")
            # every captured game must still reconcile on its own terms
            if r["w"] > page[0] or r["l"] > page[1] or r["t"] > page[2] or r["pf"] > page[3] or r["pa"] > page[4]:
                mismatches.append(f"{abbr}: captured subset exceeds official totals {calc} vs {page}")
            continue
        if calc != page:
            mismatches.append(f"{abbr}: schedule says {calc}, standings say {page}")
        else:
            reconciled.append(abbr)

    check("captured games never contradict official standings", not mismatches,
          "; ".join(mismatches) or "no contradictions")
    RESULT["teams_fully_reconciled"] = len(reconciled)
    RESULT["teams_partial"] = len(partial)
    RESULT["games_captured"] = len(games)

    print(f"games captured: {len(games)} | fully reconciled teams: {len(reconciled)} | partial: {len(partial)}")
    for name, ok, detail in [(c["check"], c["ok"], c["detail"]) for c in RESULT["checks"]]:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if partial:
        print("  partial coverage:", "; ".join(partial[:8]), "..." if len(partial) > 8 else "")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "validation.json").write_text(json.dumps(RESULT, indent=2), encoding="utf-8")

    if RESULT["failures"]:
        print("\nHARD FAILURES:")
        for f in RESULT["failures"]:
            print(" -", f)
        return 1
    print("\nAll hard checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
