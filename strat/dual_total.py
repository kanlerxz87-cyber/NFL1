#!/usr/bin/env python3
"""strat/dual_total.py — publish every model total twice, untile one wins (C5).

The brief's requirement
-----------------------
"Publish every model total twice until one wins. Keep both estimators visible with the gap
column, and only collapse to one after a walk-forward comparison."  (Readiness register PR-14,
*Not started*.)

Two estimators
--------------
  A  the published model: ridge regression on recency-weighted team attack/defence terms,
     fitted separately for margin and total, refitted for every (season, week) block
     (s9cb/analysis/lines.py::build — the same code that produced data/s9cb/lines.json);
  B  a no-ridge, no-recency baseline: the mean of the two teams' season-to-date combined
     totals, walk-forward, shrunk towards the league mean.  It uses no ratings at all, so if A
     cannot beat B then the ratings are not earning their keep on the total.

The comparison
--------------
Per game: absolute error of each estimator against the actual combined score.  The published
verdict is the **paired difference with a game-cluster bootstrap interval**, restricted to the
chronological holdout (2024, 2025 and 2026 only), because those seasons were not used to pick
the half-life.  "Wins" means the other estimator's error is larger with the interval excluding
zero.  Until that happens both are published, with the gap column.

Run: cd s9cb/analysis && python3 ../../strat/dual_total.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "s9cb", "analysis"))

import lib  # noqa: E402
import common as C  # noqa: E402
import lines as LN  # noqa: E402

SEED = 20261115
N_BOOT = 2000
HOLDOUT = (2024, 2025, 2026)


def _history(g: pd.DataFrame):
    """Season-to-date team totals from completed games only, plus the league mean by season."""
    played = g[g["played"]].sort_values(["season", "week"]).copy()
    rows = []
    for _, r in played.iterrows():
        tot = float(r["home_score"] + r["away_score"])
        rows.append({"season": int(r["season"]), "week": int(r["week"]), "team": r["home_team"], "tot": tot})
        rows.append({"season": int(r["season"]), "week": int(r["week"]), "team": r["away_team"], "tot": tot})
    tw = pd.DataFrame(rows).sort_values(["season", "week"]).reset_index(drop=True)
    tw["gp"] = tw.groupby(["season", "team"]).cumcount()
    tw["ctot"] = tw.groupby(["season", "team"])["tot"].cumsum() - tw["tot"]
    played["combined"] = played["home_score"] + played["away_score"]
    # the league mean as it stood at the START of each week, computed week by week so a
    # partially played week cannot leak the later games of the same week into an earlier one
    league = {}
    weekly = (played.groupby(["season", "week"])["combined"]
              .agg(["sum", "count"]).reset_index().sort_values(["season", "week"]))
    for season, grp in weekly.groupby("season"):
        csum, ccount = 0.0, 0
        for r in grp.itertuples():
            league[(int(season), int(r.week))] = (csum / ccount) if ccount else float("nan")
            csum += float(r.sum)
            ccount += int(r.count)
    return tw, league


def est_b(tw, league, season: int, week: int, home: str, away: str):
    """Estimator B for one fixture: shrunk mean of the two teams' prior combined totals.

    Returns None when either team has no completed game earlier in the season (week 1), so the
    cell is blank rather than guessed.
    """
    lm = league.get((int(season), int(week)))
    if lm is None or not np.isfinite(lm):
        return None
    parts = []
    for team in (home, away):
        s = tw[(tw["season"] == season) & (tw["week"] < week) & (tw["team"] == team)]
        if s.empty or s.iloc[-1]["gp"] == 0:
            return None
        last = s.iloc[-1]
        k = 4.0
        parts.append((last["ctot"] + k * lm) / (last["gp"] + k))
    return float(np.mean(parts))


def estimator_b(g: pd.DataFrame) -> pd.DataFrame:
    """Estimator B on every completed game, for the walk-forward comparison."""
    tw, league = _history(g)
    played = g[g["played"]]
    out = []
    for r in played.itertuples():
        e = est_b(tw, league, int(r.season), int(r.week), r.home_team, r.away_team)
        out.append({"game_id": r.game_id, "season": int(r.season), "week": int(r.week),
                    "total_actual": float(r.home_score + r.away_score),
                    "total_b": e if e is not None else np.nan})
    return pd.DataFrame(out)


def cluster_boot_diff(a, b, games, n_boot=N_BOOT, seed=SEED):
    """Mean(a - b) with a game-cluster bootstrap interval."""
    rng = np.random.default_rng(seed)
    uniq = np.unique(games)
    idx = {g: np.flatnonzero(games == g) for g in uniq}
    d = a - b
    draws = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        rows = np.concatenate([idx[g] for g in pick])
        draws[i] = float(np.mean(d[rows]))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(np.mean(d)), float(lo), float(hi)


def main() -> int:
    g = C.load_games()
    M, _, _ = LN.build(g)
    B = estimator_b(g)

    d = M[M["played"] & M["model_total"].notna()].merge(B, on=["game_id", "season", "week"])
    d = d[d["total_b"].notna()].copy()
    d["err_a"] = (d["total"] - d["model_total"]).abs()
    d["err_b"] = (d["total"] - d["total_b"]).abs()
    d["gap"] = d["model_total"] - d["total_b"]

    def summarise(sub: pd.DataFrame) -> dict:
        if len(sub) < 30:
            return {"n": int(len(sub))}
        diff, lo, hi = cluster_boot_diff(sub["err_a"].to_numpy(float),
                                         sub["err_b"].to_numpy(float),
                                         sub["game_id"].to_numpy())
        return {
            "n": int(len(sub)),
            "mae_a": round(float(sub["err_a"].mean()), 4),
            "mae_b": round(float(sub["err_b"].mean()), 4),
            "mean_paired_difference_a_minus_b": round(diff, 4),
            "ci95": [round(lo, 4), round(hi, 4)],
            "a_is_better": bool(lo > 0),
            "b_is_better": bool(hi < 0),
            "mean_gap": round(float(sub["gap"].mean()), 4),
            "gap_sd": round(float(sub["gap"].std(ddof=1)), 4),
        }

    overall = summarise(d)
    holdout = summarise(d[d["season"].isin(HOLDOUT)])
    by_season = []
    for s, grp in d.groupby("season"):
        row = summarise(grp)
        row["season"] = int(s)
        row["in_holdout"] = bool(s in HOLDOUT)
        by_season.append(row)

    winner = None
    if holdout.get("a_is_better"):
        winner = "A"
    elif holdout.get("b_is_better"):
        winner = "B"

    # the published board: every originated fixture, both totals, the gap, market beside them
    tw, league = _history(g)
    try:
        cur = lib.load("../../data/s9cb/lines.json")["current_board"]["games"]
    except Exception:
        cur = []
    board = []
    for r in cur:
        b = est_b(tw, league, int(r["season"]), int(r["week"]), r["home_team"], r["away_team"])
        gap = round(float(r["model_total"]) - b, 1) if b is not None else None
        board.append({
            "game_id": r["game_id"], "week": int(r["week"]), "gameday": r.get("gameday"),
            "matchup": f"{r['away_team']} @ {r['home_team']}",
            "total_a": round(float(r["model_total"]), 1),
            "total_b": None if b is None else round(b, 1),
            "gap": gap,
            "market_total": (round(float(r["market_total"]), 1)
                             if r.get("market_total") is not None else None),
            "note": (None if b is not None else
                     "Estimator B is blank: neither team has a completed game in this season yet."),
            "source": "schedules",
        })

    lib.write_json("dual_total.json", {
        "generated_at": lib.now(),
        "estimators": {
            "A": "ridge regression on recency-weighted team attack/defence, walk-forward, per (season, week) block",
            "B": "mean of the two teams' season-to-date combined totals, shrunk to the league mean with 4 pseudo-games; no ratings",
        },
        "verdict": {
            "winner": winner,
            "rule": ("An estimator wins only when the game-cluster bootstrap interval on the paired "
                     "absolute-error difference excludes zero on the chronological holdout."),
            "published": ("Both estimators are published with the gap column, because no verdict "
                          "has been reached." if winner is None else
                          f"Estimator {winner} cleared the rule."),
        },
        "holdout_seasons": list(HOLDOUT),
        "overall": overall,
        "holdout": holdout,
        "by_season": by_season,
        "board": board,
        "n_board": len(board),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
