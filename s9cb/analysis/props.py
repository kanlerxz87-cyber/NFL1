#!/usr/bin/env python3
"""Player-prop research: walk-forward projections and the correlations that decide
whether two props can be combined.

There is NO official or book-level price for player props in this repository's sources,
so nothing here claims a profit. What is published instead is:

  * a walk-forward projection for each market, with its out-of-sample error;
  * the calibration of that projection (does a 60% projection come in 60% of the time?);
  * the correlations between props in the same game, which is the number that decides
    whether a two-prop combination is worth more or less than the product of its legs.

Every projection for week W uses only weeks strictly before W for that player and that
season. No value is back-filled; a player with no history has no projection.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from common import pearson, DATA

OFFICIAL_STATS = "https://www.nfl.com/stats/player-stats/"

MARKETS = [
    ("passing_yards", "QB", "Quarter-back passing yards"),
    ("rushing_yards", "RB", "Running-back rushing yards"),
    ("receiving_yards", "WR", "Receiver receiving yards"),
    ("receptions", "WR", "Receiver receptions"),
]


def load():
    pw = pd.read_csv(os.path.join(DATA, "player_week.csv"))
    pw = pw[pw["season_type"].fillna("REG") == "REG"].copy()
    return pw.sort_values(["season", "week"]).reset_index(drop=True)


# ------------------------------------------------------- walk-forward projection
def projections(pw: pd.DataFrame, stat: str, pos: str, window: int = 4,
                shrink_k: float = 3.0) -> pd.DataFrame:
    """Returns one row per player-week with a form-only projection, an opponent-adjusted
    projection, and the realised value. The form-only projection is the headline one; the
    adjusted column exists so the reader can see whether the adjustment earned its keep."""
    """Trailing form, shrunk toward the player's own season mean.

    projection = (sum of last `window` values + shrink_k * season_so_far_mean)
                 / (n_last + shrink_k)
    Opponent adjustment is applied afterwards using the defence's season-to-date
    average conceded in that market, computed from earlier weeks only.
    """
    d = pw[pw["position"] == pos][
        ["player_id", "player_display_name", "position", "season", "week", "game_id",
         "team", "opponent_team", stat]].copy()
    d = d.rename(columns={stat: "y"})
    d["y"] = pd.to_numeric(d["y"], errors="coerce").fillna(0.0)

    # Mean conceded by this defence in STRICTLY EARLIER weeks of the same season.
    # Computed with a shifted expanding mean inside each group, so week W never sees
    # week W or later.
    d = d.sort_values(["season", "opponent_team", "week"]).reset_index(drop=True)
    d["opp_conceded_prior"] = d.groupby(["season", "opponent_team"])["y"].transform(
        lambda s: s.shift(1).expanding().mean())
    d = d.sort_values(["season", "week"]).reset_index(drop=True)
    d["league_prior"] = d.groupby("season")["y"].transform(
        lambda s: s.shift(1).expanding().mean())

    proj, actual, rows = [], [], []
    hist: dict[str, list[float]] = {}
    for r in d.itertuples():
        key = f"{r.season}:{r.player_id}"
        prev = hist.get(key, [])
        if len(prev) >= 2:
            last = prev[-window:]
            season_mean = float(np.mean(prev))
            base = (float(np.sum(last)) + shrink_k * season_mean) / (len(last) + shrink_k)
            # opponent adjustment: scale by how much this defence has conceded relative
            # to the league in earlier weeks of the same season. Damped to 0.75-1.25.
            oc = r.opp_conceded_prior
            lg = r.league_prior
            adj = 1.0
            if oc is not None and lg is not None and np.isfinite(oc) and np.isfinite(lg) and lg > 0:
                adj = float(np.clip(0.75 + 0.25 * (oc / lg), 0.75, 1.25))
            p = base * adj
            proj.append(p)
            actual.append(r.y)
            rows.append({"season": r.season, "week": r.week, "game_id": r.game_id,
                         "player_id": r.player_id, "player": r.player_display_name,
                         "team": r.team, "opponent": r.opponent_team,
                         "projection": round(float(base), 2),
                         "projection_opponent_adjusted": round(float(p), 2),
                         "actual": float(r.y)})
        hist.setdefault(key, []).append(r.y)
    return pd.DataFrame(rows)


def projection_report(P: pd.DataFrame, stat: str, label: str) -> dict:
    if P.empty or len(P) < 200:
        return {"market": stat, "label": label, "n": int(len(P)), "note": "too few rows"}
    err = P["projection"] - P["actual"]
    naive = P.groupby("season")["actual"].transform("mean")
    # calibration: how often did the player beat his own projection?
    over = float((P["actual"] > P["projection"]).mean())
    cal = []
    q = pd.qcut(P["projection"], 5, duplicates="drop")
    for bucket, grp in P.groupby(q, observed=True):
        cal.append({"projection_band": f"{bucket.left:.0f} to {bucket.right:.0f}",
                    "n": int(len(grp)),
                    "mean_projection": round(float(grp["projection"].mean()), 2),
                    "mean_actual": round(float(grp["actual"].mean()), 2),
                    "observed_over_rate": round(float((grp["actual"] > grp["projection"]).mean()), 4)})
    return {
        "market": stat, "label": label, "n": int(len(P)),
        "seasons": [int(s) for s in sorted(P["season"].unique())],
        "mae_projection": round(float(err.abs().mean()), 3),
        "mae_projection_with_opponent_adjustment": round(
            float((P["projection_opponent_adjusted"] - P["actual"]).abs().mean()), 3),
        "opponent_adjustment_helped": bool(
            (P["projection_opponent_adjusted"] - P["actual"]).abs().mean() < err.abs().mean()),
        "rmse_projection": round(float(np.sqrt((err ** 2).mean())), 3),
        "bias_projection": round(float(err.mean()), 3),
        "mae_naive_season_mean": round(float((P["actual"] - naive).abs().mean()), 3),
        "skill_vs_naive_pct": round(100 * (1 - err.abs().mean() /
                                           (P["actual"] - naive).abs().mean()), 2),
        "observed_over_rate": round(over, 4),
        "calibration_note": ("If the projection were a fair line the over rate would be "
                             "0.50. It is not a market line; it is the model's own median "
                             "forecast."),
        "calibration_bands": cal,
        "source": OFFICIAL_STATS,
    }


# ------------------------------------------------------------------ correlation
def same_game_correlations(pw: pd.DataFrame, games: pd.DataFrame) -> list[dict]:
    """Correlations between props that share a game. These are the numbers that make
    a two-prop combination worth more or less than the product of its legs."""
    d = pw.copy()
    for c in ["passing_yards", "rushing_yards", "receiving_yards", "receptions",
              "attempts", "carries", "targets", "rushing_tds", "receiving_tds",
              "passing_tds"]:
        d[c] = pd.to_numeric(d.get(c), errors="coerce").fillna(0.0)

    # team-week aggregates
    tw = (d.groupby(["season", "week", "team"])
            .agg(pass_yds=("passing_yards", "sum"), rush_yds=("rushing_yards", "sum"),
                 pass_td=("passing_tds", "sum"), rush_td=("rushing_tds", "sum"))
            .reset_index())

    a = tw.rename(columns={"team": "home_team", "pass_yds": "home_pass",
                           "rush_yds": "home_rush", "pass_td": "home_pass_td",
                           "rush_td": "home_rush_td"})
    b = tw.rename(columns={"team": "away_team", "pass_yds": "away_pass",
                           "rush_yds": "away_rush", "pass_td": "away_pass_td",
                           "rush_td": "away_rush_td"})
    j = (games[["game_id", "season", "week", "home_team", "away_team", "total", "result",
                "total_line", "spread_line"]]
         .merge(a, on=["season", "week", "home_team"], how="inner")
         .merge(b, on=["season", "week", "away_team"], how="inner"))
    j = j[j["total"].notna()]

    out = []

    def add(rel, x, y, note, source=OFFICIAL_STATS, kind="continuous"):
        r = pearson(j[x], j[y])
        if not r:
            return
        out.append({"id": f"P{len(out)+1}", "relationship": rel, "kind": kind, "note": note,
                    "source": source, **r})

    add("Team passing yards vs the same team's rushing yards, same game",
        "home_pass", "home_rush",
        "The classic game-script negative correlation: a team that runs it well throws it less. "
        "A same-team pass-plus-rush prop combination is therefore worth less than the product "
        "of its legs.")
    add("Home passing yards vs away passing yards, same game",
        "home_pass", "away_pass",
        "Two quarter-backs in the same game share the same game script, so their passing "
        "yards are usually positively correlated, not independent.")
    add("Home passing yards vs the game total points",
        "home_pass", "total",
        "How much of the game total is driven by one team's passing game.")
    add("Team passing touchdowns vs the same team's rushing touchdowns",
        "home_pass_td", "home_rush_td",
        "Two scoring props from the same team compete for the same red-zone trips.")
    add("Game total points vs the closing total line",
        "total", "total_line",
        "How much of the realised total the market line already explains.")

    # player-level: top two receivers on the same team, and the running-back committee
    sk = d[d["position"].isin(["WR", "TE"])]
    top2 = (sk.sort_values(["season", "week", "team", "receiving_yards"], ascending=False)
              .groupby(["season", "week", "team"]).head(2))
    piv = (top2.assign(rank=top2.groupby(["season", "week", "team"]).cumcount() + 1)
              .pivot_table(index=["season", "week", "team"], columns="rank",
                           values="receiving_yards"))
    if {1, 2}.issubset(set(piv.columns)):
        r = pearson(piv[1], piv[2])
        if r:
            out.append({"id": f"P{len(out)+1}", "kind": "continuous",
                        "relationship": "Top receiver yards vs the second receiver's yards, "
                                        "same team and game",
                        "note": "Target competition inside one passing game. Two receiver "
                                "overs from the same team are usually negatively correlated.",
                        "source": OFFICIAL_STATS, **r})

    rb = d[d["position"] == "RB"]
    top2rb = (rb.sort_values(["season", "week", "team", "rushing_yards"], ascending=False)
                .groupby(["season", "week", "team"]).head(2))
    prv = (top2rb.assign(rank=top2rb.groupby(["season", "week", "team"]).cumcount() + 1)
                 .pivot_table(index=["season", "week", "team"], columns="rank",
                              values="rushing_yards"))
    if {1, 2}.issubset(set(prv.columns)):
        r = pearson(prv[1], prv[2])
        if r:
            out.append({"id": f"P{len(out)+1}", "kind": "continuous",
                        "relationship": "Lead back rushing yards vs the backup's rushing yards, "
                                        "same team and game",
                        "note": "Committee split: the backup's workload rises when the lead "
                                "back's falls.",
                        "source": OFFICIAL_STATS, **r})

    qb = d[d["position"] == "QB"].groupby(["season", "week", "team"])["passing_yards"].max()
    wr = d[d["position"].isin(["WR", "TE"])].groupby(["season", "week", "team"])["receiving_yards"].max()
    m = pd.concat([qb.rename("qb_yds"), wr.rename("wr_yds")], axis=1).dropna()
    r = pearson(m["qb_yds"], m["wr_yds"])
    if r:
        out.append({"id": f"P{len(out)+1}", "kind": "continuous",
                    "relationship": "Quarter-back passing yards vs his top receiver's "
                                    "receiving yards, same team and game",
                    "note": "The single most common same-game prop pairing. A strong positive "
                            "correlation means the parlay is worth MORE than the product of "
                            "its legs, which is why books price these specially.",
                    "source": OFFICIAL_STATS, **r})
    return out


def anytime_td_rates(pw: pd.DataFrame) -> list[dict]:
    d = pw.copy()
    d["td"] = (pd.to_numeric(d.get("rushing_tds"), errors="coerce").fillna(0)
               + pd.to_numeric(d.get("receiving_tds"), errors="coerce").fillna(0)) > 0
    rows = []
    for pos in ["RB", "WR", "TE"]:
        g = d[d["position"] == pos]
        if len(g) < 200:
            continue
        k, n = int(g["td"].sum()), int(len(g))
        rows.append({"position": pos, "player_weeks": n, "anytime_td": k,
                     "rate": round(k / n, 4),
                     "note": "Base rate over all qualifying player-weeks in the extract "
                             "(2019-2026, players with at least four opportunities).",
                     "source": OFFICIAL_STATS})
    return rows
