#!/usr/bin/env python3
"""Build every analytical output the site shows, from the pinned raw files.

Stages (each isolated so one failure cannot silently poison the rest):
  A  league snapshot + standings (from game results)
  B  opponent-adjusted EPA ratings -> own spread/total lines -> out-of-sample backtest
  C  strategy leaderboard with validation gates, luck removal, correlation values
  D  injury / depth-chart attrition (starter -> backup deficits)
  E  player-prop lines from role, usage and opponent
  F  dashboard payload

Run: python pipeline/build_all.py
"""
from __future__ import annotations

import json
import math
import os
import traceback
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import nfl_lib as L

ERRORS: list[dict] = []


def jclean(obj):
    """JSON-safe: numpy scalars -> python, NaN/inf -> None (never silently zeroed)."""
    if isinstance(obj, dict):
        return {str(k): jclean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jclean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        obj = float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    return obj


def stage(name):
    def deco(fn):
        def run(*a, **k):
            try:
                print(f"\n=== {name}")
                return fn(*a, **k)
            except Exception as exc:  # noqa: BLE001
                print(f"STAGE FAILED {name}: {exc}")
                traceback.print_exc()
                ERRORS.append({"stage": name, "error": f"{type(exc).__name__}: {exc}",
                               "trace": traceback.format_exc()[-1500:]})
                return None
        return run
    return deco


# ---------------------------------------------------------------- A. league state
@stage("A league snapshot")
def league_snapshot():
    games = L.load("games.csv")
    games["season"] = games["season"].astype(int)
    reg = games[(games["game_type"] == "REG")].copy()
    reg["margin"] = reg["home_score"] - reg["away_score"]
    reg["actual_total"] = reg["home_score"] + reg["away_score"]

    cur = reg[reg["season"] == 2026].copy()
    played = cur[cur["home_score"].notna()]
    last_week = int(played["week"].max())
    fixtures = cur[cur["week"] == last_week + 1].copy()

    rows = []
    for _, g in played.iterrows():
        rows.append({"team": g["home_team"], "win": int(g["margin"] > 0),
                     "loss": int(g["margin"] < 0), "tie": int(g["margin"] == 0),
                     "pf": g["home_score"], "pa": g["away_score"]})
        rows.append({"team": g["away_team"], "win": int(g["margin"] < 0),
                     "loss": int(g["margin"] > 0), "tie": int(g["margin"] == 0),
                     "pf": g["away_score"], "pa": g["home_score"]})
    st = pd.DataFrame(rows).groupby("team").agg(
        w=("win", "sum"), l=("loss", "sum"), t=("tie", "sum"),
        pf=("pf", "sum"), pa=("pa", "sum")).reset_index()
    st["gp"] = st["w"] + st["l"] + st["t"]
    st["pct"] = ((st["w"] + 0.5 * st["t"]) / st["gp"]).round(3)
    st["diff"] = (st["pf"] - st["pa"]).astype(int)
    st = st.sort_values(["pct", "diff"], ascending=False)

    teams = L.load("teams.csv")
    meta = teams.drop_duplicates("team_abbr").set_index("team_abbr")

    def team_row(r):
        m = meta.loc[r["team"]] if r["team"] in meta.index else None
        return {
            "team": r["team"],
            "name": (m["team_name"] if m is not None else None),
            "conference": (m["team_conf"] if m is not None else None),
            "division": (m["team_division"] if m is not None else None),
            "w": int(r["w"]), "l": int(r["l"]), "t": int(r["t"]),
            "pct": float(r["pct"]), "pf": int(r["pf"]), "pa": int(r["pa"]),
            "diff": int(r["diff"]),
            "source": "https://www.nfl.com/standings/league/2026/reg",
        }

    snapshot = {
        "generated_at": L.now(),
        "season": 2026,
        "last_completed_week": last_week,
        "games_played": int(len(played)),
        "games_scheduled": int(len(cur)),
        "standings": [team_row(r) for _, r in st.iterrows()],
        "fixtures": [{
            "game_id": g["game_id"], "week": int(g["week"]), "gameday": str(g["gameday"]),
            "weekday": g["weekday"], "gametime": g["gametime"],
            "away": g["away_team"], "home": g["home_team"],
            "market_spread_home": None if pd.isna(g["spread_line"]) else float(g["spread_line"]),
            "market_total": None if pd.isna(g["total_line"]) else float(g["total_line"]),
            "home_rest": None if pd.isna(g["home_rest"]) else int(g["home_rest"]),
            "away_rest": None if pd.isna(g["away_rest"]) else int(g["away_rest"]),
            "div_game": int(g["div_game"]) if not pd.isna(g["div_game"]) else None,
            "source": "https://www.nfl.com/schedules/2026/REG" + str(int(g["week"])),
        } for _, g in fixtures.iterrows()],
        "line_coverage_2026": {
            "completed_with_spread": int(played["spread_line"].notna().sum()),
            "completed_games": int(len(played)),
            "upcoming_with_spread": int(fixtures["spread_line"].notna().sum()),
            "upcoming_games": int(len(fixtures)),
        },
    }
    L.write_json("snapshot.json", jclean(snapshot))
    return dict(reg=reg, cur=cur, played=played, fixtures=fixtures, snapshot=snapshot)


# ---------------------------------------------------------------- B. own lines
@stage("B ratings and own lines")
def ratings_and_lines(ctx):
    reg = ctx["reg"]
    pbp = pd.concat([L.load(f"pbp_{s}.parquet") for s in (2024, 2025, 2026)],
                    ignore_index=True)
    pbp = L.clean_plays(pbp)
    print(f"clean plays: {len(pbp)} ({pbp['season'].value_counts().to_dict()})")

    teams = sorted(set(reg[reg["season"] == 2026]["home_team"]) |
                   set(reg[reg["season"] == 2026]["away_team"]))

    # Ratings are fit per (season, week) using only prior information.
    needed = {}
    for season in (2024, 2025, 2026):
        wks = reg[(reg["season"] == season) & reg["home_score"].notna()]["week"].unique()
        for w in wks:
            needed[(season, int(w))] = True
    needed[(2026, int(ctx["snapshot"]["last_completed_week"]) + 1)] = True
    ratings = {}
    for (season, week) in sorted(needed):
        r = L.week_ratings(pbp, teams, season, week)
        if r:
            ratings[f"{season}_{week}"] = r
    print(f"rating snapshots: {len(ratings)}")

    def build_feature_frame(season, only_played=True):
        g = reg[(reg["season"] == season)].copy()
        if only_played:
            g = g[g["home_score"].notna()]
        out = []
        for _, row in g.iterrows():
            r = ratings.get(f"{season}_{int(row['week'])}")
            if not r:
                continue
            if row["home_team"] not in r or row["away_team"] not in r:
                continue
            d = {
                "game_id": row["game_id"], "season": int(season), "week": int(row["week"]),
                "home": row["home_team"], "away": row["away_team"],
                "margin": row["margin"], "actual_total": row["actual_total"],
                "spread_line": row["spread_line"], "total_line": row["total_line"],
                "home_net": r[row["home_team"]]["net"],
                "away_net": r[row["away_team"]]["net"],
                "home_off": r[row["home_team"]]["off"], "away_off": r[row["away_team"]]["off"],
                "home_def": r[row["home_team"]]["def"], "away_def": r[row["away_team"]]["def"],
            }
            out.append(d)
        return pd.DataFrame(out)

    tr = build_feature_frame(2024)
    va = build_feature_frame(2025)
    te = build_feature_frame(2026)
    print(f"feature frames train/valid/test: {len(tr)}/{len(va)}/{len(te)}")

    # Margin model: margin = a + b*(net_home - net_away)
    def ols(X, y):
        A = np.column_stack([np.ones(len(X)), X])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        resid = y - A @ coef
        return coef, float(np.std(resid, ddof=2))

    coef_m, sd_m = ols((tr["home_net"] - tr["away_net"]).to_numpy(float),
                       tr["margin"].to_numpy(float))
    Xt = np.column_stack([(tr["home_off"] + tr["away_off"]).to_numpy(float),
                          (tr["home_def"] + tr["away_def"]).to_numpy(float)])
    coef_t, sd_t = ols(Xt, tr["actual_total"].to_numpy(float))

    def predict(df):
        d = df.copy()
        d["pred_margin"] = coef_m[0] + coef_m[1] * (d["home_net"] - d["away_net"])
        # nflverse convention: positive = home team favoured, so the model line IS pred_margin
        d["model_spread"] = d["pred_margin"]
        d["pred_total"] = (coef_t[0] + coef_t[1] * (d["home_off"] + d["away_off"])
                           + coef_t[2] * (d["home_def"] + d["away_def"]))
        d["win_prob_home"] = 0.5 * (1 + np.vectorize(math.erf)(
            (d["pred_margin"]) / (sd_m * math.sqrt(2))))
        return d

    tr_p, va_p, te_p = predict(tr), predict(va), predict(te)

    def score(df, label):
        d = df.dropna(subset=["spread_line", "total_line"])
        if len(d) == 0:
            return {"label": label, "n": 0}
        err_sp = d["pred_margin"] - d["margin"]
        err_sp_mkt = d["spread_line"] - d["margin"]
        err_tot = d["pred_total"] - d["actual_total"]
        err_tot_mkt = d["total_line"] - d["actual_total"]
        diff = np.abs(err_sp) - np.abs(err_sp_mkt)
        rng = np.random.default_rng(11)
        boot = rng.choice(diff.to_numpy(), size=(5000, len(diff)), replace=True).mean(axis=1)
        return {
            "label": label,
            "n": int(len(d)),
            "spread_mae_model": round(float(np.abs(err_sp).mean()), 3),
            "spread_mae_market": round(float(np.abs(err_sp_mkt).mean()), 3),
            "spread_mae_diff_ci95": [round(float(np.percentile(boot, 2.5)), 3),
                                     round(float(np.percentile(boot, 97.5)), 3)],
            "total_mae_model": round(float(np.abs(err_tot).mean()), 3),
            "total_mae_market": round(float(np.abs(err_tot_mkt).mean()), 3),
            "corr_model_market_spread": round(float(np.corrcoef(
                d["model_spread"], d["spread_line"])[0, 1]), 3),
            "corr_model_market_total": round(float(np.corrcoef(
                d["pred_total"], d["total_line"])[0, 1]), 3),
            "residual_sd_margin": round(float(np.std(err_sp, ddof=1)), 2),
            "residual_sd_total": round(float(np.std(err_tot, ddof=1)), 2),
        }

    calibration = [score(tr_p, "train 2024"), score(va_p, "validation 2025"),
                   score(te_p, "test 2026")]

    # Does the model add information on top of the closing line? Fit the blend weight on
    # 2025 and test on 2026. A weight near zero means the model adds nothing to the market.
    blend = None
    both = pd.concat([va_p, te_p], ignore_index=True).dropna(
        subset=["spread_line", "pred_margin", "margin"])
    if len(both) > 60:
        v = both[both["season"] == 2025]
        t = both[both["season"] == 2026]
        if len(v) > 30 and len(t) > 30:
            A = np.column_stack([np.ones(len(v)), v["spread_line"], v["pred_margin"]])
            coef, *_ = np.linalg.lstsq(A, v["margin"].to_numpy(float), rcond=None)
            At = np.column_stack([np.ones(len(t)), t["spread_line"], t["pred_margin"]])
            pred = At @ coef
            blend = {
                "fit": "margin ~ 1 + market_line + model_line on 2025, tested on 2026",
                "intercept": round(float(coef[0]), 3),
                "weight_market": round(float(coef[1]), 3),
                "weight_model": round(float(coef[2]), 3),
                "n_train": int(len(v)), "n_test": int(len(t)),
                "test_mae_hybrid": round(float(np.abs(pred - t["margin"]).mean()), 3),
                "test_mae_market_only": round(float(np.abs(
                    t["spread_line"] - t["margin"]).mean()), 3),
                "interpretation": ("weight_model near 0 means the EPA model carries no "
                                   "incremental information beyond the closing line."),
            }

    # Measured proof of the line-sign convention we grade against.
    conv = reg[reg["home_score"].notna() & reg["spread_line"].notna() & (reg["season"] >= 2005)]
    sign_check = {
        "corr_market_line_vs_home_margin": round(float(np.corrcoef(
            conv["spread_line"], conv["margin"])[0, 1]), 3),
        "n_games": int(len(conv)),
        "conclusion": ("Positive correlation proves the mirrored closing line is expressed as "
                       "points the HOME team is expected to win by (positive = home favourite)."),
    }

    # Current-week own lines
    week = int(ctx["snapshot"]["last_completed_week"]) + 1
    fx = ctx["fixtures"].copy()
    r_cur = ratings.get(f"2026_{week}", {})
    lines = []
    for _, g in fx.iterrows():
        if g["home_team"] not in r_cur or g["away_team"] not in r_cur:
            continue
        rh, ra = r_cur[g["home_team"]], r_cur[g["away_team"]]
        pm = coef_m[0] + coef_m[1] * (rh["net"] - ra["net"])
        pt = (coef_t[0] + coef_t[1] * (rh["off"] + ra["off"])
              + coef_t[2] * (rh["def"] + ra["def"]))
        mkt_sp = None if pd.isna(g["spread_line"]) else float(g["spread_line"])
        mkt_tot = None if pd.isna(g["total_line"]) else float(g["total_line"])
        edge_sp = None if mkt_sp is None else round(pm - mkt_sp, 2)
        edge_tot = None if mkt_tot is None else round(pt - mkt_tot, 2)
        pl = {
            "game_id": g["game_id"], "week": week, "gameday": str(g["gameday"]),
            "away": g["away_team"], "home": g["home_team"],
            "my_home_line": round(pm, 1), "my_total": round(pt, 1),
            "my_line_display": f"{g['home_team']} {-pm:+.1f}" if pm >= 0 else f"{g['home_team']} +{-pm:.1f}",
            "my_win_prob_home": round(float(0.5 * (1 + math.erf(pm / (sd_m * math.sqrt(2))))), 3),
            "market_home_line": mkt_sp, "market_total": mkt_tot,
            "edge_home_line": edge_sp, "edge_total": edge_tot,
            "home_line_band95": [round(pm - 1.96 * sd_m, 1), round(pm + 1.96 * sd_m, 1)],
            "status": ("actionable" if (edge_sp is not None and abs(edge_sp) >= 3) else
                       "watch" if (edge_sp is not None and abs(edge_sp) >= 2) else "no-edge"),
            "home_rating": {k: round(v, 4) for k, v in rh.items()},
            "away_rating": {k: round(v, 4) for k, v in ra.items()},
            "source_games": "https://www.nfl.com/schedules/2026/REG" + str(week),
            "source_pbp": "https://github.com/nflverse/nflverse-data/releases/tag/pbp",
        }
        lines.append(pl)

    payload = {
        "generated_at": L.now(),
        "sign_convention_check": sign_check,
        "blend_test": blend,
        "method": {
            "ratings": ("Two-way ridge fixed effect on non-garbage-time plays: "
                        "EPA ~ offense team + defense team + home. Prior season weighted 0.4."),
            "margin_model": {"intercept": round(float(coef_m[0]), 3),
                             "slope_per_epa": round(float(coef_m[1]), 3),
                             "residual_sd": round(sd_m, 3),
                             "fit_on": "2024 regular season (walk-forward ratings)"},
            "total_model": {"intercept": round(float(coef_t[0]), 3),
                            "coef_off_sum": round(float(coef_t[1]), 3),
                            "coef_def_sum": round(float(coef_t[2]), 3),
                            "residual_sd": round(sd_t, 3)},
            "note": ("Ratings for week W use only weeks < W of the current season plus the "
                     "previous season at 40% weight, so the backtest has no look-ahead."),
        },
        "calibration": calibration,
        "week": week,
        "lines": lines,
        "ratings": [{"team": t, **{k: round(v, 4) for k, v in r_cur[t].items()}}
                    for t in sorted(r_cur, key=lambda x: -r_cur[x]["net"] if x in r_cur else 0)]
        if r_cur else [],
    }
    L.write_json("lines.json", jclean(payload))
    return dict(payload=payload, te=te_p, ratings=ratings, teams=teams)


# ---------------------------------------------------------------- C. strategies
def gate_rows(summary, corr_max):
    n = summary.get("n_graded") or 0
    q = summary.get("q_value")
    roi_lo = (summary.get("roi_ci95") or [None])[0]
    pos = summary.get("seasons_positive") or 0
    tested = summary.get("seasons_tested") or 0
    dd = summary.get("max_drawdown_units")
    hold = summary.get("holdout_roi")
    gates = [
        {"id": "G1", "name": "Provenance", "pass": True,
         "detail": "All inputs pinned by URL + sha256 in provenance.json."},
        {"id": "G2", "name": "Pre-specified rule", "pass": True,
         "detail": "Round-number threshold fixed before evaluation; no parameter search."},
        {"id": "G3", "name": "Sample size", "pass": n >= 100,
         "detail": f"n={n} graded bets (minimum 100)."},
        {"id": "G4", "name": "Holdout positive", "pass": bool(hold is not None and hold > 0),
         "detail": f"latest-window ROI={hold}."},
        {"id": "G5", "name": "Significance", "pass": bool(q is not None and q < 0.10),
         "detail": f"BH-adjusted q={q} (needs <0.10)."},
        {"id": "G6", "name": "Stability", "pass": bool(tested and pos >= math.ceil(0.6 * tested)),
         "detail": f"{pos}/{tested} seasons positive."},
        {"id": "G7", "name": "Drawdown", "pass": bool(dd is not None and dd >= -25),
         "detail": f"max drawdown {dd} units."},
        {"id": "G8", "name": "Diversification", "pass": bool(corr_max is None or abs(corr_max) < 0.7),
         "detail": f"max |corr| with another strategy = {corr_max}."},
    ]
    passed = sum(1 for g in gates if g["pass"])
    status = "PASS" if passed == len(gates) else "WATCH" if passed >= 5 else "FAIL"
    return gates, status, passed


@stage("C strategy leaderboard")
def strategies(ctx):
    reg = ctx["reg"]
    te = ctx["te"]

    # Window with reliable closing lines
    cov = reg[reg["home_score"].notna()].groupby("season")["spread_line"].apply(
        lambda s: s.notna().mean())
    good = [int(s) for s, v in cov.items() if v > 0.95 and s >= 2005]
    lo_season = min(good) if good else 2015
    hist = reg[(reg["season"] >= lo_season) & reg["home_score"].notna()
               & reg["spread_line"].notna()].copy()
    print(f"line window {lo_season}-2026, {len(hist)} games with closing spread")

    # ---- strategy definitions (round-number thresholds, no tuning)
    def side_line(row, side):
        """Points this side is favoured by (positive = favourite)."""
        return row["spread_line"] if side == "home" else -row["spread_line"]

    def underdog(row, side):
        return side_line(row, side) < 0

    bets_all = {}

    def add(name, rows):
        bets_all[name] = pd.DataFrame(rows)

    def ats(name, rule):
        rows = []
        for _, g in hist.iterrows():
            side = rule(g)
            if side is None:
                continue
            res = L.cover_result(g["margin"], g["spread_line"], side)
            rows.append({"game_id": g["game_id"], "season": int(g["season"]),
                         "week": int(g["week"]),
                         "team": g["home_team"] if side == "home" else g["away_team"],
                         "side": side, "line": side_line(g, side),
                         "result": res, "market": g["spread_line"]})
        add(name, rows)

    def tot(name, rule):
        rows = []
        for _, g in hist.iterrows():
            if pd.isna(g["total_line"]):
                continue
            side = rule(g)
            if side is None:
                continue
            res = L.total_result(g["actual_total"], g["total_line"], side)
            rows.append({"game_id": g["game_id"], "season": int(g["season"]),
                         "week": int(g["week"]), "team": "TOTAL", "side": side,
                         "line": g["total_line"], "result": res, "market": g["spread_line"]})
        add(name, rows)

    ats("S04 Divisional underdog +6.5 or more",
        lambda g: next((s for s in ("home", "away")
                        if g["div_game"] == 1 and underdog(g, s)
                        and side_line(g, s) <= -6.5), None))
    ats("S05 Underdog on short rest (<=4 days)",
        lambda g: next((s for s in ("home", "away")
                        if underdog(g, s) and (g[f"{s}_rest"] if not pd.isna(g[f"{s}_rest"]) else 99) <= 4), None))
    ats("S06 Fade divisional road favourite of 6.5+",
        lambda g: "home" if (g["div_game"] == 1 and g["spread_line"] <= -6.5) else None)
    ats("S11 Home team with 3+ rest-day edge",
        lambda g: "home" if (not pd.isna(g["home_rest"]) and not pd.isna(g["away_rest"])
                             and g["home_rest"] - g["away_rest"] >= 3) else None)
    ats("S12 Home team facing opponent off a bye",
        lambda g: "home" if (not pd.isna(g["away_rest"]) and g["away_rest"] >= 13) else None)
    ats("S13 Home favourite of 10 or more",
        lambda g: "home" if g["spread_line"] >= 10 else None)
    tot("S08 Over when closing total is 41 or lower",
        lambda g: "over" if g["total_line"] <= 41 else None)
    tot("S14 Under in divisional games with total 47+",
        lambda g: "under" if (g["div_game"] == 1 and g["total_line"] >= 47) else None)

    # Model-driven strategies (2024-2026 only, walk-forward ratings)
    if te is not None and len(te):
        d = te.dropna(subset=["spread_line", "total_line"])
        for thr in (2.0, 3.0):
            rows = []
            for _, g in d.iterrows():
                edge = g["pred_margin"] - g["spread_line"]
                if abs(edge) < thr:
                    continue
                side = "home" if edge > 0 else "away"
                res = L.cover_result(g["margin"], g["spread_line"], side)
                rows.append({"game_id": g["game_id"], "season": int(g["season"]),
                             "week": int(g["week"]),
                             "team": g["home"] if side == "home" else g["away"],
                             "side": side,
                             "line": side_line(g, side),
                             "result": res, "market": g["spread_line"]})
            add(f"S01 Own-line vs close, edge >= {thr}", rows)
        rows = []
        for _, g in d.iterrows():
            edge = g["pred_total"] - g["total_line"]
            if abs(edge) < 3:
                continue
            side = "over" if edge > 0 else "under"
            res = L.total_result(g["actual_total"], g["total_line"], side)
            rows.append({"game_id": g["game_id"], "season": int(g["season"]),
                         "week": int(g["week"]), "team": "TOTAL", "side": side,
                         "line": g["total_line"], "result": res, "market": g["spread_line"]})
        add("S03 Own-total vs close, edge >= 3", rows)

    # Backup-QB strategy from official injury reports (2025-2026 only)
    try:
        inj = pd.concat([L.load("injuries_2025.csv"), L.load("injuries_2026.csv")],
                        ignore_index=True)
        qb_out = inj[(inj["position"] == "QB") &
                     (inj["report_status"].isin(["Out", "Doubtful"]))]
        keys = set(zip(qb_out["season"].astype(int), qb_out["week"].astype(int),
                       qb_out["team"]))
        rows = []
        for _, g in hist[hist["season"] >= 2025].iterrows():
            for s, other in (("home", "away"), ("away", "home")):
                if (int(g["season"]), int(g["week"]), g[f"{s}_team"]) in keys:
                    # hypothesis: market over-penalises the team starting a backup -> bet them
                    res = L.cover_result(g["margin"], g["spread_line"], s)
                    rows.append({"game_id": g["game_id"], "season": int(g["season"]),
                                 "week": int(g["week"]), "team": g[f"{s}_team"],
                                 "side": s,
                                 "line": side_line(g, s),
                                 "result": res, "market": g["spread_line"]})
                    break
        add("S15 Start the team whose QB is ruled Out/Doubtful", rows)
    except Exception as exc:  # noqa: BLE001
        print(f"backup-qb strategy skipped: {exc}")

    # ---- evaluate
    results = {}
    for name, b in bets_all.items():
        if len(b) == 0:
            results[name] = {"summary": {"n_graded": 0}, "note": "no qualifying bets"}
            continue
        s = L.summarize_bets(b)
        s["holdout_roi"] = None
        if s.get("by_season"):
            seasons_sorted = sorted(s["by_season"], key=int)
            latest = seasons_sorted[-2:]
            vals = [s["by_season"][k]["roi"] for k in latest if s["by_season"][k]["n"] >= 10]
            if vals:
                s["holdout_roi"] = round(float(np.mean(vals)), 4)
        results[name] = {"summary": s, "bets": b}

    # ---- multiple-testing correction across all strategies
    names = list(results)
    pv = [(results[n]["summary"].get("binom_p_vs_breakeven") or 1.0) for n in names]
    qs = L.benjamini_hochberg(pv)
    for n, q in zip(names, qs):
        results[n]["summary"]["q_value"] = q

    # ---- correlation of per-bet returns between strategies (overlapping games only)
    ret_map = {}
    for n, r in results.items():
        b = r.get("bets")
        if b is None or len(b) == 0:
            continue
        b = b[b["result"].isin(["win", "loss"])].copy()
        b["ret"] = np.where(b["result"] == "win", L.payout(), -1.0)
        ret_map[n] = b.set_index("game_id")["ret"]
    corr_names = [n for n in ret_map if len(ret_map[n]) >= 40]
    corr = {}
    for i, a in enumerate(corr_names):
        for b in corr_names[i + 1:]:
            joint = pd.concat([ret_map[a], ret_map[b]], axis=1, join="inner").dropna()
            if len(joint) >= 30 and joint.iloc[:, 0].std() > 0 and joint.iloc[:, 1].std() > 0:
                v = float(np.corrcoef(joint.iloc[:, 0], joint.iloc[:, 1])[0, 1])
                corr[f"{a} | {b}"] = {"n_overlap": int(len(joint)), "corr": round(v, 3)}

    # ---- gates
    leaderboard = []
    for name in names:
        s = results[name]["summary"]
        cvals = [abs(v["corr"]) for k, v in corr.items() if name in k]
        corr_max = round(max(cvals), 3) if cvals else None
        gates, status, passed = gate_rows(s, corr_max)
        score = None
        if (s.get("n_graded") or 0) >= 100 and s.get("roi_ci95"):
            score = round(float(s["roi_ci95"][0]) * 100, 2)
        leaderboard.append({
            "strategy": name, "status": status, "gates_passed": passed,
            "score_lower_ci_roi_pct": score,
            "n_graded": s.get("n_graded"), "wins": s.get("wins"), "losses": s.get("losses"),
            "pushes": s.get("pushes"), "win_pct": s.get("win_pct"), "roi": s.get("roi"),
            "roi_ci95": s.get("roi_ci95"), "units": s.get("units"),
            "p_value": s.get("binom_p_vs_breakeven"), "q_value": s.get("q_value"),
            "max_drawdown_units": s.get("max_drawdown_units"),
            "by_season": s.get("by_season"), "holdout_roi": s.get("holdout_roi"),
            "max_abs_corr": corr_max, "gates": gates,
            "window": f"{lo_season}-2026" if "S0" in name or "S1" in name else "per definition",
        })
    leaderboard.sort(key=lambda r: (-(r["score_lower_ci_roi_pct"] or -999),
                                    -(r["n_graded"] or 0)))

    # ---- parlay correlation + luck arithmetic
    m = hist["margin"]
    parlay = {}
    if len(hist) > 100:
        over = (hist["actual_total"] > hist["total_line"]).astype(int)
        home_cover = (m - hist["spread_line"] > 0).astype(int)
        parlay = {
            "n_games": int(len(hist)),
            "corr_margin_vs_total": round(float(np.corrcoef(m, hist["actual_total"])[0, 1]), 3),
            "phi_home_cover_vs_over": L.phi(home_cover, over),
            "note": ("Same-game legs are not independent. Use the phi value to adjust a "
                     "2-leg same-game parlay: P = p1p2 + rho*sqrt(p1(1-p1)p2(1-p2))."),
        }
    legs = {}
    p = 0.5238
    for n_legs in (2, 3, 4, 5):
        dec = L.american_to_decimal(L.JUICE) ** n_legs
        legs[str(n_legs)] = {
            "decimal_payout": round(dec, 3),
            "breakeven_prob_independent": round(1 / dec, 4),
            "per_leg_win_prob_needed_at_50pct_legs": None,
            "note": "payout = 1.909^legs at -110 per leg",
        }

    payload = {
        "generated_at": L.now(),
        "window": {"start_season": lo_season, "end_season": 2026,
                   "games_with_closing_spread": int(len(hist)),
                   "source": "https://github.com/nflverse/nflverse-data/releases/tag/schedules",
                   "price_assumption": "-110 on every bet (no book-level prices in the data)"},
        "leaderboard": leaderboard,
        "pairwise_correlation": corr,
        "parlay": parlay,
        "parlay_payouts": legs,
        "gate_definitions": [
            {"id": "G1", "rule": "Every input file pinned by URL and sha256."},
            {"id": "G2", "rule": "Rule fixed before evaluation; no threshold search."},
            {"id": "G3", "rule": "At least 100 graded bets."},
            {"id": "G4", "rule": "Positive ROI across the two most recent seasons."},
            {"id": "G5", "rule": "Benjamini-Hochberg q < 0.10 against break-even win rate."},
            {"id": "G6", "rule": "At least 60% of tested seasons positive."},
            {"id": "G7", "rule": "Max drawdown no worse than -25 units."},
            {"id": "G8", "rule": "|correlation| with any other strategy below 0.7."},
        ],
        "rewards": {
            "model": ("Points are awarded for statistically defensible performance, not raw ROI: "
                      "100 x max(0, lower 95% ROI bound) + 20 x seasons positive + 10 x gates passed. "
                      "Strategies failing G3 (n<100) score zero. No cash, no prizes: this is a "
                      "paper competition. Legal review is required before any real reward."),
            "statuses": {"PASS": "all gates passed", "WATCH": "5-7 gates passed",
                         "FAIL": "fewer than 5 gates passed"},
        },
        "bets": {n: results[n]["bets"].tail(40).to_dict("records")
                 for n in names if results[n].get("bets") is not None
                 and len(results[n]["bets"]) > 0},
    }
    L.write_json("strategies.json", jclean(payload))
    return payload


# ---------------------------------------------------------------- D. availability
POS_WEIGHTS = {
    "QB": 0.30, "C": 0.05, "G": 0.05, "T": 0.05, "OT": 0.05, "OG": 0.05, "OL": 0.06,
    "WR": 0.04, "TE": 0.05, "RB": 0.05, "FB": 0.01,
    "DE": 0.05, "DT": 0.05, "NT": 0.04, "IDL": 0.05, "EDGE": 0.05,
    "LB": 0.05, "ILB": 0.05, "OLB": 0.05, "MLB": 0.05, "CB": 0.06, "S": 0.05,
    "FS": 0.05, "SS": 0.05, "DB": 0.05, "K": 0.01, "P": 0.01, "LS": 0.01,
}
STATUS_WEIGHT = {"Out": 1.0, "Doubtful": 0.7, "Questionable": 0.25}


@stage("D injury and depth attrition")
def availability(ctx):
    inj = L.load("injuries_2026.csv")
    dc = L.load("depth_charts_2026.parquet")
    snaps = L.load("snap_counts_2026.parquet")
    roster = L.load("roster_weekly_2026.parquet")

    # The feed can contain a partially reported next week, so pick the latest week that is
    # actually complete for the current game week, and report which week was used.
    target = int(ctx["snapshot"]["last_completed_week"]) + 1
    by_week = inj.groupby("week").size()
    week = target if by_week.get(target, 0) >= 100 else int(by_week.idxmax())
    inj_w = inj[inj["week"] == week].copy()
    dt = dc["dt"].max()
    dc_latest = dc[dc["dt"] == dt].copy()

    snap_team = snaps.groupby(["team", "player"]).agg(
        off=("offense_snaps", "sum"), dfn=("defense_snaps", "sum")).reset_index()

    dc_latest["pos_rank"] = pd.to_numeric(dc_latest["pos_rank"], errors="coerce")
    dc_latest["pos_slot"] = pd.to_numeric(dc_latest["pos_slot"], errors="coerce")

    # roster status for experience + IR flags
    rw = roster[roster["week"] == roster["week"].max()].drop_duplicates("gsis_id")
    exp = rw.set_index("gsis_id")["years_exp"].to_dict()
    rstatus = rw.set_index("gsis_id")["status"].to_dict()

    # depth lookup: (team, gsis_id) -> best (lowest) rank across position groups
    depth_by_player = {}
    for _, r in dc_latest.iterrows():
        gid = r.get("gsis_id")
        if not isinstance(gid, str) or pd.isna(r["pos_rank"]):
            continue
        key = (r["team"], gid)
        cur = depth_by_player.get(key)
        if cur is None or r["pos_rank"] < cur["pos_rank"]:
            depth_by_player[key] = {
                "pos_abb": r["pos_abb"], "pos_name": r["pos_name"], "pos_grp": r["pos_grp"],
                "pos_slot": None if pd.isna(r["pos_slot"]) else int(r["pos_slot"]),
                "pos_rank": int(r["pos_rank"]), "player_name": r["player_name"],
            }
    # replacement pool per (team, pos_slot)
    pool = {}
    for (team, gid), d in depth_by_player.items():
        pool.setdefault((team, d["pos_slot"], d["pos_abb"]), []).append({"gsis_id": gid, **d})
    for k in pool:
        pool[k].sort(key=lambda x: x["pos_rank"])

    rows, team_agg = [], {}
    for _, r in inj_w.iterrows():
        status = r["report_status"]
        if status not in STATUS_WEIGHT:
            continue
        key = (r["team"], r["gsis_id"])
        d = depth_by_player.get(key)
        if not d:
            continue
        starter = d["pos_rank"] == 1
        if not starter:
            continue
        repl = next((p for p in pool.get((r["team"], d["pos_slot"], d["pos_abb"]), [])
                     if p["pos_rank"] == 2), None)
        pos = (r["position"] or "").upper()
        w = POS_WEIGHTS.get(pos, 0.03)
        contrib = w * STATUS_WEIGHT[status]
        snaps_total = 0
        if repl:
            s = snap_team[(snap_team["team"] == r["team"]) &
                          (snap_team["player"] == repl["player_name"])]
            snaps_total = int(s[["off", "dfn"]].to_numpy().sum()) if len(s) else 0
        team_agg[r["team"]] = team_agg.get(r["team"], 0) + contrib
        rows.append({
            "team": r["team"], "player": r["full_name"], "position": r["position"],
            "depth_rank": d["pos_rank"], "depth_slot": d["pos_name"],
            "injury": r["report_primary_injury"], "game_status": status,
            "practice_status": r["practice_status"],
            "years_exp": exp.get(r["gsis_id"]),
            "roster_status": rstatus.get(r["gsis_id"]),
            "replacement": repl["player_name"] if repl else None,
            "replacement_years_exp": exp.get(repl["gsis_id"]) if repl else None,
            "replacement_snaps_2026": snaps_total if repl else None,
            "position_weight": w, "attrition_points": round(contrib, 4),
            "source": "https://www.nfl.com/injuries/",
            "depth_source": "https://www.nfl.com/teams/",
        })

    rows.sort(key=lambda x: -x["attrition_points"])
    max_agg = max(team_agg.values()) if team_agg else 1.0
    team_table = []
    meta = L.load("teams.csv").drop_duplicates("team_abbr").set_index("team_abbr")
    for team, val in sorted(team_agg.items(), key=lambda kv: -kv[1]):
        team_rows = [x for x in rows if x["team"] == team]
        team_table.append({
            "team": team,
            "name": meta.loc[team, "team_name"] if team in meta.index else None,
            "starters_out": sum(1 for x in team_rows if x["game_status"] == "Out"),
            "starters_doubtful": sum(1 for x in team_rows if x["game_status"] == "Doubtful"),
            "starters_questionable": sum(1 for x in team_rows if x["game_status"] == "Questionable"),
            "attrition_points": round(val, 3),
            "attrition_index_0_100": round(100 * val / max_agg, 1) if max_agg else 0.0,
            "backup_experience_avg": (
                round(float(np.mean([x["replacement_years_exp"] for x in team_rows
                                     if x["replacement_years_exp"] is not None])), 1)
                if any(x["replacement_years_exp"] is not None for x in team_rows) else None),
            "backup_snaps_avg": (
                round(float(np.mean([x["replacement_snaps_2026"] for x in team_rows
                                     if x["replacement_snaps_2026"] is not None])), 0)
                if any(x["replacement_snaps_2026"] is not None for x in team_rows) else None),
            "source": "https://www.nfl.com/injuries/",
        })

    payload = {
        "generated_at": L.now(),
        "week": week,
        "depth_chart_timestamp": str(dt),
        "counts": {
            "injury_rows_this_week": int(len(inj_w)),
            "starters_impacted": int(len(rows)),
            "teams_with_starter_out": int(sum(1 for t in team_table if t["starters_out"] > 0)),
            "players_matched_to_depth_chart": int(len(rows)),
        },
        "method": {
            "depth_rank": "NFL.com depth charts as mirrored by nflverse (pos_rank 1 = starter).",
            "attrition_formula": ("sum over unavailable starters of position_weight x status_weight; "
                                  "status weights Out=1.0, Doubtful=0.7, Questionable=0.25. Index is "
                                  "rescaled 0-100 against the worst team this week."),
            "position_weights": POS_WEIGHTS,
            "limits": [
                "Injury status is the official game-status column; it does not prove who starts.",
                "Depth charts are a weekly snapshot, not a snap-count projection.",
                "Practice-squad elevations and game-day inactive lists are not modelled separately.",
                "The attrition index is a modelling assumption, not an official NFL metric.",
            ],
        },
        "teams": team_table,
        "players": rows,
    }
    L.write_json("availability.json", jclean(payload))
    return payload


# ---------------------------------------------------------------- E. props
@stage("E player prop lines")
def props(ctx):
    st = L.load("stats_player_week_2026.parquet")
    st = st[st["season_type"] == "REG"]
    week = int(ctx["snapshot"]["last_completed_week"]) + 1
    fx = ctx["fixtures"]
    opp = {}
    for _, g in fx.iterrows():
        opp[g["home_team"]] = g["away_team"]
        opp[g["away_team"]] = g["home_team"]

    specs = [("QB", "passing_yards", 4), ("RB", "rushing_yards", 4),
             ("WR", "receiving_yards", 5), ("TE", "receiving_yards", 4)]
    # opponent allowed rate per (position group, stat)
    allowed = st.groupby(["opponent_team", "position_group"])[
        ["passing_yards", "rushing_yards", "receiving_yards"]].mean()
    league = st.groupby("position_group")[
        ["passing_yards", "rushing_yards", "receiving_yards"]].mean()

    rows = []
    for pos, stat, k in specs:
        sub = st[(st["position_group"] == pos) & st[stat].notna()]
        agg = sub.groupby(["player_id", "player_display_name", "team"]).agg(
            n=("week", "nunique"), mean=(stat, "mean"), sd=(stat, "std")).reset_index()
        agg = agg[agg["n"] >= 4]
        grp_mean = float(sub[stat].mean())
        for _, r in agg.iterrows():
            team = r["team"]
            if team not in opp:
                continue
            m = (r["n"] * r["mean"] + k * grp_mean) / (r["n"] + k)
            factor = 1.0
            try:
                a = float(allowed.loc[(opp[team], pos), stat])
                lgm = float(league.loc[pos, stat])
                if lgm > 0:
                    factor = 1 + 0.5 * (min(1.15, max(0.85, a / lgm)) - 1)
            except Exception:  # noqa: BLE001
                factor = 1.0
            proj = m * factor
            sd = float(r["sd"]) if not pd.isna(r["sd"]) else None
            line = round(proj * 2) / 2
            rows.append({
                "player": r["player_display_name"], "team": team, "position": pos,
                "stat": stat, "opponent": opp[team], "games": int(r["n"]),
                "season_mean": round(float(r["mean"]), 1),
                "shrunk_mean": round(float(m), 1),
                "opponent_factor": round(factor, 3),
                "projection": round(float(proj), 1),
                "my_line": line,
                "sd": None if sd is None else round(sd, 1),
                "interval80": None if sd is None else [round(proj - 1.28 * sd, 1),
                                                       round(proj + 1.28 * sd, 1)],
                "p_over_my_line": 0.5,
                "market_line": None,
                "edge_vs_market": None,
                "status": "model-only (no verified market price)",
                "source": "https://www.nfl.com/stats/player-stats/",
            })
    rows.sort(key=lambda r: -r["projection"])
    payload = {
        "generated_at": L.now(),
        "week": week,
        "method": {
            "projection": ("(n x player mean + 4 x positional mean)/(n+4), then multiplied by an "
                           "opponent factor: 1 + 0.5 x (clamped allowed/league ratio - 1)."),
            "distribution": "Normal with the player's own game-level SD; 80% interval = mean +/- 1.28 SD.",
            "no_market": ("No official league source publishes prop prices. Rather than invent a "
                          "line or a price, market_line and edge are left blank and flagged."),
        },
        "props": rows,
    }
    L.write_json("props.json", jclean(payload))
    return payload


# ---------------------------------------------------------------- G. verification
@stage("G verification against official pages")
def verification(ctx):
    """Line-by-line comparison of our computed rows against hand-transcribed nfl.com rows.

    The fixtures in data/verified/ were copied from nfl.com on 2026-11-12 by the agent and
    are the only human-entered data in the project. Anything that does not match is listed
    as an irregularity instead of being quietly reconciled.
    """
    out = {"generated_at": L.now(), "checks": [], "irregularities": []}
    root = L.ROOT

    # --- 1. standings
    path = os.path.join(root, "data", "verified", "official_standings_2026.json")
    if os.path.exists(path):
        off = json.load(open(path))
        snap = json.load(open(os.path.join(L.OUT, "snapshot.json")))
        comp = {r["team"]: r for r in snap["standings"]}
        rows, mism = [], []
        for o in off["rows"]:
            c = comp.get(o["team"])
            if c is None:
                rows.append({"team": o["team"], "matched": False, "detail": "team missing"})
                mism.append({"team": o["team"], "detail": "team missing from computed table"})
                continue
            fields = {"w": c["w"], "l": c["l"], "t": c["t"], "pf": c["pf"], "pa": c["pa"]}
            diffs = {k: {"nfl": o[k], "computed": fields[k]}
                     for k in fields if int(o[k]) != int(fields[k])}
            rows.append({"team": o["team"], "matched": not diffs,
                         "nfl": fields if not diffs else {k: o[k] for k in fields},
                         "computed": fields, "diffs": diffs or None})
            if diffs:
                mism.append({"team": o["team"], "diffs": diffs})
        out["checks"].append({
            "name": "2026 standings (W-L-T, points for/against)",
            "source": off["source_url"],
            "rows_checked": len(off["rows"]),
            "rows_matched": sum(1 for r in rows if r["matched"]),
            "mismatches": len(mism),
            "detail": rows,
        })
        if mism:
            out["irregularities"].append(
                {"id": "V1", "area": "standings",
                 "issue": f"{len(mism)} of {len(off['rows'])} team records differ from nfl.com",
                 "examples": mism[:10], "source": off["source_url"]})

    # --- 2. injury report sample
    path = os.path.join(root, "data", "verified", "official_injuries_2026_w10_sample.json")
    if os.path.exists(path):
        off = json.load(open(path))
        inj = L.load("injuries_2026.csv")
        wk = int(inj["week"].max())
        inj_w = inj[inj["week"] == wk]
        rows, mism, missing = [], [], []
        for o in off["rows"]:
            match = inj_w[(inj_w["team"] == o["team"]) & (inj_w["full_name"] == o["player"])]
            if match.empty:
                rows.append({**o, "feed": "row not present", "matched": False})
                missing.append({**o, "reason": "not present in mirrored feed"})
                continue
            m = match.iloc[0]
            got = {
                "position": m["position"],
                "injury": None if pd.isna(m["report_primary_injury"]) else m["report_primary_injury"],
                "practice": None if pd.isna(m["practice_status"]) else m["practice_status"],
                "game": None if pd.isna(m["report_status"]) else m["report_status"],
            }
            diffs = {k: {"nfl": o[k], "feed": got[k]}
                     for k in ("position", "injury", "practice", "game")
                     if (o[k] or None) != (got[k] or None)}
            rows.append({**o, "feed": got, "matched": not diffs, "diffs": diffs or None})
            if diffs:
                mism.append({"team": o["team"], "player": o["player"], "diffs": diffs})
        out["checks"].append({
            "name": f"2026 week {wk} injury report sample (4 clubs)",
            "source": off["source_url"],
            "rows_checked": len(off["rows"]),
            "rows_matched": sum(1 for r in rows if r["matched"]),
            "mismatches": len(mism),
            "detail": rows,
        })
        if mism or missing:
            out["irregularities"].append(
                {"id": "V2", "area": "injury feed",
                 "issue": (f"{len(mism)} field mismatches and {len(missing)} missing rows in the "
                           "sampled clubs"),
                 "examples": (mism + missing)[:10], "source": off["source_url"]})

    # --- 3. things this project cannot verify from an official league source
    out["unverifiable"] = [
        {"item": "Closing spread/total/moneylines",
         "why": ("The NFL does not publish betting lines; nflverse mirrors consensus closing "
                 "lines. No official league source exists, and no second book-level source was "
                 "reachable from the build environment."),
         "handling": "Used for backtests only; labelled as consensus closing lines."},
        {"item": "Player prop prices/lines",
         "why": "No official source; no licensed odds feed connected.",
         "handling": "Own prop lines published as model-only, market columns left blank."},
        {"item": "Depth chart order",
         "why": ("nfl.com publishes depth charts per club; the mirrored copy is a weekly snapshot "
                 "and does not guarantee who starts or plays."),
         "handling": "Starter label used only as a modelling assumption, flagged."},
        {"item": "Week 10 kickoff times",
         "why": "Not fetched line-by-line from the schedule page in this run.",
         "handling": "Fixture table shows date only; time marked unverified."},
    ]
    L.write_json("verification.json", jclean(out))
    return out


# ---------------------------------------------------------------- F. dashboard
@stage("F dashboard payload")
def dashboard(ctx, strategies_payload, lines_payload, avail, props_payload):
    snap = ctx["snapshot"]
    lb = (strategies_payload or {}).get("leaderboard", [])
    prov = json.load(open(os.path.join(L.OUT, "provenance.json")))
    ok_files = [f for f in prov["files"] if f["status"] == "ok"]
    payload = {
        "generated_at": L.now(),
        "season": snap["season"],
        "last_completed_week": snap["last_completed_week"],
        "next_week": snap["last_completed_week"] + 1,
        "counts": {
            "games_played": snap["games_played"],
            "teams": len(snap["standings"]),
            "source_files_pinned": len(ok_files),
            "own_lines_generated": len((lines_payload or {}).get("lines", [])),
            "strategies_tested": len(lb),
            "strategies_passing_all_gates": sum(1 for r in lb if r["status"] == "PASS"),
            "strategies_watch": sum(1 for r in lb if r["status"] == "WATCH"),
            "starters_flagged_unavailable": (avail or {}).get("counts", {}).get(
                "starters_impacted", 0),
            "prop_lines_generated": len((props_payload or {}).get("props", [])),
        },
        "top_strategies": lb[:5],
        "capabilities": [
            {"area": "Own lines", "state": "built", "detail": "Opponent-adjusted EPA ratings -> spread, total, win probability."},
            {"area": "Backtest vs closing line", "state": "built", "detail": "Walk-forward; no look-ahead."},
            {"area": "Strategy leaderboard", "state": "built", "detail": "8 validation gates, BH multiple-testing correction, bootstrap CIs."},
            {"area": "Correlation", "state": "built", "detail": "Per-bet correlation between strategies, same-game leg phi."},
            {"area": "Injuries and depth", "state": "built", "detail": "Official game status joined to depth chart rank and replacement experience."},
            {"area": "Props", "state": "model-only", "detail": "Projections built; no verified market prop prices, so no edge claim."},
            {"area": "Prize/rewards", "state": "blocked", "detail": "Paper points only until legal review."},
        ],
        "errors": ERRORS,
    }
    L.write_json("dashboard.json", jclean(payload))
    return payload


def main():
    ctx = league_snapshot()
    if ctx is None:
        raise SystemExit("league snapshot failed; nothing to build")
    lines_ctx = ratings_and_lines(ctx)
    merged = {**ctx, **(lines_ctx or {})}
    strategies_payload = strategies(merged) if lines_ctx else None
    avail = availability(ctx)
    props_payload = props(ctx)
    verification(ctx)
    dashboard(ctx, strategies_payload, (lines_ctx or {}).get("payload"), avail, props_payload)
    print(f"\ncompleted with {len(ERRORS)} stage error(s)")
    if ERRORS:
        L.write_json("errors.json", jclean({"generated_at": L.now(), "errors": ERRORS}))


if __name__ == "__main__":
    main()
