#!/usr/bin/env python3
"""Run the whole session-9cb71eb8 research build and write data/s9cb/*.json.

    cd s9cb/analysis && python3 run.py

Outputs:
    lines.json         own-line accuracy, incremental-information test, current board
    leaderboard.json   scored strategies, eight validation gates, luck accounting
    parlays.json       every two-leg combination, priced from the observed legs
    correlations.json  game-level and prop-level correlation register, with CIs
    props.json         walk-forward player projections, calibration, prop correlations
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common as C
import lines as LN
import props as PR
import strategies as ST


# ---------------------------------------------------------------- game correlations
def game_correlations(M: pd.DataFrame) -> list[dict]:
    d = M[M["played"] & M["spread_line"].notna() & M["model_margin"].notna()].copy()
    d["abs_margin"] = d["result"].abs()
    d["home_cover"] = (d["result"] > d["spread_line"]).astype(float)
    d["over"] = (d["total"] > d["total_line"]).astype(float)
    d["rest_diff"] = d["home_rest"].fillna(7) - d["away_rest"].fillna(7)
    d["model_minus_market"] = d["model_margin"] - d["spread_line"]
    d["result_minus_market"] = d["result"] - d["spread_line"]

    out = []

    def add(rel, x, y, note, source="https://www.nfl.com/schedules/"):
        r = C.pearson(d[x], d[y])
        if r:
            out.append({"id": f"C{len(out)+1}", "relationship": rel, "kind": "continuous",
                        "note": note, "source": source, **r})

    add("Closing spread vs the actual home margin", "spread_line", "result",
        "How much of the result the market line already explains. This is the bar any "
        "own line has to beat.")
    add("Own model line vs the actual home margin", "model_margin", "result",
        "The same measure for our own line.")
    add("Own line minus market line vs result minus market line",
        "model_minus_market", "result_minus_market",
        "The edge test: if the model's disagreement with the market is informative this "
        "is positive. If it is zero the model adds nothing beyond the closing line.")
    add("Point margin vs total points, same game", "result", "total",
        "Whether blowouts travel with high scoring.")
    add("Absolute point margin vs total points, same game", "abs_margin", "total",
        "The parlay question: close games and low totals tend to arrive together.")
    add("Closing total vs the actual total points", "total_line", "total",
        "How much of the realised total the market total explains.")
    add("Rest-days advantage (home minus away) vs the home margin", "rest_diff", "result",
        "Whether the rest edge is already in the price.")
    add("Temperature vs total points", "temp", "total",
        "Weather effect on scoring; only games with a recorded temperature are used.")
    add("Wind speed vs total points", "wind", "total",
        "Wind effect on scoring; only games with a recorded wind reading are used.")

    # the two legs of the most common same-game parlay
    r = C.pearson(d["home_cover"], d["over"])
    if r:
        out.append({"id": f"C{len(out)+1}", "kind": "binary phi",
                    "relationship": "Home team covers vs the game goes over, same game",
                    "note": ("The favourite covering and the over landing together. A non-zero "
                             "phi is why the product of two leg prices is the wrong price for "
                             "a same-game parlay."),
                    "source": "https://www.nfl.com/schedules/", **r})

    # week-to-week persistence of a team's scoring
    tm = []
    for (season, team), grp in _team_weeks(M).groupby(["season", "team"]):
        pts = grp.sort_values("week")["points"].to_numpy(float)
        if len(pts) >= 4:
            tm.append((pts[:-1], pts[1:]))
    if tm:
        x = np.concatenate([a for a, _ in tm])
        y = np.concatenate([b for _, b in tm])
        r = C.pearson(x, y)
        if r:
            out.append({"id": f"C{len(out)+1}", "kind": "lag-1 autocorrelation",
                        "relationship": "A team's points scored in week t vs its points in week t+1",
                        "note": ("If this were strongly positive, form would be real and worth "
                                 "betting on. A value near zero is why 'hot team' systems do not "
                                 "survive."),
                        "source": "https://www.nfl.com/schedules/", **r})
    return out


def _team_weeks(M: pd.DataFrame) -> pd.DataFrame:
    p = M[M["played"]][["season", "week", "home_team", "away_team",
                        "home_score", "away_score"]].copy()
    a = p[["season", "week", "home_team", "home_score"]].rename(
        columns={"home_team": "team", "home_score": "points"})
    b = p[["season", "week", "away_team", "away_score"]].rename(
        columns={"away_team": "team", "away_score": "points"})
    return pd.concat([a, b], ignore_index=True)


# ------------------------------------------------------------------- luck removal
def luck_accounting(B: pd.DataFrame, leaderboard: dict) -> dict:
    """How much of every result could be luck?

    Under the null that the observed prices are fair, a 1-unit bet at decimal d has
    mean profit 0 and variance d - 1. That gives an exact reference distribution for
    the realised profit with no simulation and no distributional assumption beyond
    independence of bets.
    """
    rows = []
    for entry in leaderboard["leaderboard"]:
        g = B[B["strategy"] == entry["strategy"]]
        decided = g[~g["push"]]
        if decided.empty:
            continue
        var = float((decided["decimal"] - 1.0).sum())
        sd = math.sqrt(var)
        profit = float(g["profit"].sum())
        z = profit / sd if sd else float("nan")
        # mid-95% band of the null distribution of total profit
        band = 1.96 * sd
        mean_edge = profit / len(g)
        var_per = float((decided["decimal"] - 1.0).mean())
        required_n = None
        if mean_edge > 0 and var_per > 0:
            required_n = int(math.ceil(((1.96 + 0.8416) ** 2) * var_per / (mean_edge ** 2)))
        rows.append({
            "strategy": entry["strategy"],
            "n_bets": int(len(g)),
            "profit_units": round(profit, 3),
            "null_sd_of_total_profit_units": round(sd, 3),
            "luck_band_95_units": [round(-band, 2), round(band, 2)],
            "profit_outside_luck_band": bool(abs(profit) > band),
            "z_vs_fair_price": round(z, 4) if z == z else None,
            "p_value_two_sided": round(2 * (1 - C._student_t_cdf(abs(z), 1e9)), 6) if z == z else None,
            "mean_edge_per_bet": round(mean_edge, 5),
            "bets_needed_for_80pct_power": required_n,
            "reading": (
                f"With {int(len(g))} bets at these prices, a purely lucky run would land "
                f"inside +/-{band:.1f} units 95% of the time. The strategy made "
                f"{profit:.1f} units."),
        })
    rows.sort(key=lambda r: -(r["z_vs_fair_price"] or -99))
    return {
        "method": ("Null: the observed prices are fair, so a 1-unit bet at decimal d has "
                   "mean profit 0 and variance d-1. The standard deviation of total profit "
                   "is then sqrt(sum(d_i - 1)) over the bets actually placed. No simulation "
                   "and no assumption beyond independence of bets."),
        "note": ("The last column is the number of bets the strategy would need before an "
                 "edge of the observed size could be detected 80% of the time at the 5% "
                 "level. Where that number is larger than any realistic season, the honest "
                 "answer is that the sample cannot settle the question."),
        "rows": rows,
    }


# ------------------------------------------------------------------------ main
def main() -> None:
    print("loading extract ...")
    g = C.load_games()
    prov = C.load_prov()
    inj = pd.read_csv(os.path.join(C.DATA, "injuries.csv"))
    print(f"  games {len(g)}, played {int(g['played'].sum())}, "
          f"priced {int(g['has_price'].sum())}")

    print("building walk-forward own lines ...")
    M, fit_log, probe = LN.build(g)
    ev = LN.evaluate(M)
    print(f"  scored {ev.get('n_scored')} games; spread MAE model "
          f"{ev.get('spread_mae_model')} vs market {ev.get('spread_mae_market')}")

    print("current board ...")
    board = LN.current_board(M)

    C.write_json("lines.json", {
        "generated_at": C.now(),
        "official_source": C.OFFICIAL["schedules"],
        "source_extract": "data/s9cb/games.csv",
        "upstream": prov.get("source_repo"),
        "provenance_note": ("Game results and closing lines are the nflverse parse of the "
                            "NFL's GSIS feed; nfl.com is the official entry point and the "
                            "2026 results in this repository were checked against it."),
        "method": {
            "ratings": ("Ridge regression on recency-weighted team attack and defence "
                        "terms, fitted separately for margin and total, refitted for every "
                        "(season, week) block using only games that finished earlier."),
            "walk_forward": True,
            "half_life_grid_weeks": LN.HALF_LIVES,
            "ridge": LN.RIDGE,
            "nested_selection": ("The recency half-life is chosen on the newest 15% of the "
                                 "training games only, never on the games being scored."),
        },
        "lookahead_probe": probe,
        "accuracy": ev,
        "current_board": board,
        "fit_log_sample": fit_log[::12],
        "n_blocks_fitted": len(fit_log),
    })

    print("generating and scoring strategies ...")
    B = ST.generate(M, inj)
    print(f"  {len(B)} bets across {B['strategy'].nunique()} strategies")
    lb = ST.evaluate(B)
    lb["generated_at"] = C.now()
    lb["official_source"] = C.OFFICIAL["schedules"]
    lb["price_source"] = ("Observed prices taken from the source file for every scored bet. "
                          "Games without a price are not scored and are counted below.")
    lb["unscored_games_no_price"] = int((g["played"] & ~g["has_price"]).sum())
    lb["luck_accounting"] = luck_accounting(B, lb)
    C.write_json("leaderboard.json", lb)

    print("parlays ...")
    par = ST.parlay_analysis(B, lb["leaderboard"])
    par["generated_at"] = C.now()
    par["method"] = ("Every unordered pair of strategies is combined whenever both fired in "
                     "the same week in DIFFERENT games. The parlay price is the product of "
                     "the two observed decimal prices. The whole matrix is published, so no "
                     "pair is chosen after seeing the result.")
    par["pricing_note"] = ("The product of two legs is what a book would pay on a standard "
                           "parlay. Because the legs are correlated, that price is only fair "
                           "if the correlation is zero; the correlation_ratio column shows "
                           "how far from zero it is.")
    C.write_json("parlays.json", par)

    print("correlations ...")
    gc = game_correlations(M)
    C.write_json("correlations.json", {
        "generated_at": C.now(),
        "sample": {
            "games": int(M["played"].sum()),
            "games_with_both_lines": ev.get("n_scored"),
            "seasons": [int(s) for s in sorted(M.loc[M["played"], "season"].unique())],
            "source": C.OFFICIAL["schedules"],
        },
        "method": "Pearson r with a Fisher-z 95% confidence interval and a two-sided t test.",
        "publication_rule": ("A relationship is only published when at least 25 paired "
                             "observations exist; otherwise it is reported as blank."),
        "game_level": gc,
    })

    print("props ...")
    pw = PR.load()
    prop_reports, proj_tables = [], {}
    for stat, pos, label in PR.MARKETS:
        P = PR.projections(pw, stat, pos)
        rep = PR.projection_report(P, stat, label)
        prop_reports.append(rep)
        proj_tables[stat] = P
        print(f"  {stat}: n={rep.get('n')} mae={rep.get('mae_projection')} "
              f"vs naive {rep.get('mae_naive_season_mean')}")
    prop_corr = PR.same_game_correlations(pw, M)
    C.write_json("props.json", {
        "generated_at": C.now(),
        "source": C.OFFICIAL["stats"],
        "price_status": ("UNVERIFIED / BLANK: no official or book-level price exists for any "
                         "player prop in this repository's sources, so no prop bet is scored "
                         "and no profit is claimed. Projections and correlations only."),
        "markets": prop_reports,
        "same_game_correlations": prop_corr,
        "anytime_td_base_rates": PR.anytime_td_rates(pw),
        "sample": {
            "player_weeks": int(len(pw)),
            "seasons": [int(s) for s in sorted(pw["season"].unique())],
            "players": int(pw["player_id"].nunique()),
        },
    })

    print("\ndone.")


if __name__ == "__main__":
    main()
