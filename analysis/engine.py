#!/usr/bin/env python3
"""
engine.py — opponent-adjusted ratings, own lines, and a forward (out-of-sample) test
against explicit naive baselines, using only verified official results.

Design rules enforced here (these are the project's validation gates):
  G1  Time order: any prediction for week W uses only weeks < W.
  G2  Baselines are published, not hidden. A model that cannot beat them is reported as failing.
  G3  Hyper-parameters are chosen *inside* the training window (nested expanding CV),
      never on the test week.
  G4  Uncertainty is quantified (residual SD + bootstrap CI), not asserted.
  G5  No number appears without its input files and row counts.

Baselines (all computable from the same verified rows):
  B0  League average:  predict 0 margin, league-average total.
  B1  Home field only: predict the sample HFA for margin, league-average total.
  B2  Season-to-date scoring differential: (PF-PA)/GP of each team + HFA.
  B3  Recency-weighted differential: last 5 games only, + HFA.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "verified"
OUT = DATA / "model"
LAMBDAS = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0)
SEED = 20261112


def load(name: str) -> list[dict]:
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------- model fit
def _solve(games, teams, lam):
    if not games:
        return {"o": {t: 0.0 for t in teams}, "d": {t: 0.0 for t in teams},
                "h": 2.0, "mu": 22.0, "n": 0, "lam": lam}
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    pts = [int(g["home_score"]) for g in games] + [int(g["away_score"]) for g in games]
    mu = float(np.mean(pts))
    rows, rhs = [], []
    for g in games:
        a, h_ = g["away_abbr"], g["home_abbr"]
        r = np.zeros(2 * n + 1); r[idx[h_]] += 1; r[n + idx[a]] -= 1; r[-1] = 1
        rows.append(r); rhs.append(int(g["home_score"]) - mu)
        r = np.zeros(2 * n + 1); r[idx[a]] += 1; r[n + idx[h_]] -= 1
        rows.append(r); rhs.append(int(g["away_score"]) - mu)
    A = np.vstack([np.array(rows), np.eye(2 * n + 1) * math.sqrt(lam)])
    b = np.concatenate([np.array(rhs, dtype=float), np.zeros(2 * n + 1)])
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    return {"o": {t: sol[idx[t]] for t in teams}, "d": {t: sol[n + idx[t]] for t in teams},
            "h": float(sol[-1]), "mu": mu, "n": len(games), "lam": lam}


def predict(m, home, away):
    margin = (m["o"][home] - m["o"][away]) + (m["d"][away] - m["d"][home]) + m["h"]
    total = 2 * m["mu"] + (m["o"][home] + m["o"][away]) - (m["d"][home] + m["d"][away]) + m["h"]
    return float(margin), float(total)


def select_lambda(train, teams):
    """Nested expanding CV *within* the training window only (gate G3)."""
    if len(train) < 40:
        return 2.0
    ws = sorted({g["week"] for g in train})
    inner = [w for w in ws if w >= ws[len(ws) // 2]]
    best, best_mae = 2.0, float("inf")
    for lam in LAMBDAS:
        errs = []
        for w in inner:
            sub = [g for g in train if g["week"] < w]
            if len(sub) < 20:
                continue
            m = _solve(sub, teams, lam)
            for g in (g for g in train if g["week"] == w):
                pm, _ = predict(m, g["home_abbr"], g["away_abbr"])
                errs.append(abs((g["home_score"] - g["away_score"]) - pm))
        if errs:
            v = float(np.mean(errs))
            if v < best_mae:
                best, best_mae = lam, v
    return best


# ---------------------------------------------------------------- baselines
def team_season_to_date(games, upto_week):
    agg = {}
    for g in games:
        if g["week"] >= upto_week:
            continue
        for side, opp in (("home", "away"), ("away", "home")):
            t = g[f"{side}_abbr"]
            a = agg.setdefault(t, {"pf": 0, "pa": 0, "gp": 0, "last": []})
            a["pf"] += int(g[f"{side}_score"]); a["pa"] += int(g[f"{opp}_score"]); a["gp"] += 1
            a["last"].append(int(g[f"{side}_score"]) - int(g[f"{opp}_score"]))
    return agg


def baseline_differential(g, agg, hfa):
    a, h = g["away_abbr"], g["home_abbr"]
    da = (agg[a]["pf"] - agg[a]["pa"]) / agg[a]["gp"] if a in agg and agg[a]["gp"] else 0.0
    dh = (agg[h]["pf"] - agg[h]["pa"]) / agg[h]["gp"] if h in agg and agg[h]["gp"] else 0.0
    # home margin prediction = home differential - away differential + HFA, scaled by
    # the observed shrink factor 1.0 (no fitting to test weeks)
    return float(dh - da + hfa)


def baseline_recent(g, agg, hfa, k=5):
    a, h = g["away_abbr"], g["home_abbr"]
    ma = np.mean(agg[a]["last"][-k:]) if a in agg and agg[a]["last"] else 0.0
    mh = np.mean(agg[h]["last"][-k:]) if h in agg and agg[h]["last"] else 0.0
    return float(mh - ma + hfa)


def main() -> int:
    games = load("games_2026.csv")
    standings = load("standings_2026.csv")
    fixtures = load("week10_fixtures_2026.csv")
    teams = [r["abbr"] for r in standings]
    for g in games:
        g["week"] = int(g["week"])
        g["home_score"], g["away_score"] = int(g["home_score"]), int(g["away_score"])

    weeks = sorted({g["week"] for g in games})
    rows = []
    for w in weeks:
        train = [g for g in games if g["week"] < w]
        test = [g for g in games if g["week"] == w]
        if not test:
            continue
        lam = select_lambda(train, teams)
        m = _solve(train, teams, lam)
        agg = team_season_to_date(games, w)
        hfa = m["h"]
        tot_mean = (float(np.mean([g["home_score"] + g["away_score"] for g in train]))
                    if train else 45.0)
        for g in test:
            am = g["home_score"] - g["away_score"]
            at = g["home_score"] + g["away_score"]
            pm, pt = predict(m, g["home_abbr"], g["away_abbr"])
            rows.append({
                "week": w, "game_id": g["game_id"],
                "pred_model": pm, "pred_model_total": pt,
                "pred_b1_hfa": hfa, "pred_b1_total": tot_mean,
                "pred_b2_diff": baseline_differential(g, agg, hfa), "pred_b2_total": tot_mean,
                "pred_b3_recent": baseline_recent(g, agg, hfa), "pred_b3_total": tot_mean,
                "actual": am, "actual_total": at, "lam": lam, "n_train": len(train),
            })

    A = np.array([r["actual"] for r in rows]); AT = np.array([r["actual_total"] for r in rows])
    cands = {
        "model (opponent-adjusted, ridge)": ("pred_model", "pred_model_total"),
        "B1 home field only": ("pred_b1_hfa", "pred_b1_total"),
        "B2 season-to-date differential": ("pred_b2_diff", "pred_b2_total"),
        "B3 last-5 differential": ("pred_b3_recent", "pred_b3_total"),
    }
    def mae(x): return float(np.mean(np.abs(x)))

    leaderboard = []
    for name, (mk, tk) in cands.items():
        P = np.array([r[mk] for r in rows]); PT = np.array([r[tk] for r in rows])
        leaderboard.append({
            "strategy": name,
            "n": len(rows),
            "mae_margin": mae(A - P),
            "rmse_margin": float(np.sqrt(np.mean((A - P) ** 2))),
            "mae_total": mae(AT - PT),
            "side_accuracy": float(np.mean(np.sign(A) == np.sign(P))),
            "corr_margin": float(np.corrcoef(A, P)[0, 1]) if np.std(P) > 0 else None,
            "corr_total": float(np.corrcoef(AT, PT)[0, 1]) if np.std(PT) > 0 else None,
        })
    leaderboard.sort(key=lambda x: x["mae_margin"])

    # paired bootstrap vs the best baseline (gate G4)
    best_baseline = min((x for x in leaderboard if x["strategy"].startswith("B")),
                        key=lambda x: x["mae_margin"])
    b_key = dict((k, v) for k, v in cands.items())[best_baseline["strategy"]][0]
    err_model = np.abs(A - np.array([r["pred_model"] for r in rows]))
    err_base = np.abs(A - np.array([r[b_key] for r in rows]))
    rng = np.random.default_rng(SEED)
    d = np.array([np.mean((err_model - err_base)[s := rng.integers(0, len(rows), len(rows))])
                  for _ in range(10000)])
    boot = {"comparison": f"model vs {best_baseline['strategy']}",
            "mean_abs_err_difference": float(np.mean(err_model - err_base)),
            "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            "p_model_better": float(np.mean(d < 0))}

    gate_mae = boot["ci95"][1] < 0            # model significantly better
    gate_acc = leaderboard[0]["strategy"].startswith("model") and \
               leaderboard[0]["side_accuracy"] > 0.5
    summary = {
        "n_games_evaluated": len(rows),
        "weeks": sorted({r["week"] for r in rows}),
        "leaderboard": leaderboard,
        "paired_bootstrap_model_vs_best_baseline": boot,
        "gates": {
            "G1_time_ordered": True,
            "G2_baselines_published": True,
            "G3_nested_hyperparameter_selection": True,
            "G4_uncertainty_reported": True,
            "model_beats_best_baseline_with_95pct_confidence": bool(gate_mae),
            "model_side_accuracy_above_50pct": bool(gate_acc),
        },
        "verdict": ("PASS — model adds measurable predictive value over every baseline"
                    if gate_mae else
                    "FAIL — the opponent-adjusted model does not beat the published baselines "
                    "with 95% confidence; do not use these lines for decisions."),
        "hfa_points_estimate": None,  # filled below
        "inputs": ["data/verified/games_2026.csv", "data/verified/standings_2026.csv"],
        "residual_sd_margin": float(np.std(A - np.array([r["pred_model"] for r in rows]))),
        "residual_sd_total": float(np.std(AT - np.array([r["pred_model_total"] for r in rows]))),
    }

    # ------------------------------------------------- ratings + week-10 lines
    full = _solve(games, teams, select_lambda(games, teams))
    summary["hfa_points_estimate"] = round(full["h"], 3)
    summary["lambda_selected_full"] = full["lam"]
    ratings = []
    for r in standings:
        t = r["abbr"]; gp = int(r["w"]) + int(r["l"]) + int(r["t"])
        ratings.append({"team": r["team"], "abbr": t, "conference": r["conference"],
                        "division": r["division"], "w": int(r["w"]), "l": int(r["l"]),
                        "t": int(r["t"]), "gp": gp, "pf": int(r["pf"]), "pa": int(r["pa"]),
                        "net": int(r["net_pts"]),
                        "off_rating": round(full["o"][t], 2), "def_rating": round(full["d"][t], 2),
                        "power": round(full["o"][t] - full["d"][t], 2),
                        "source_url": r["source_url"]})
    ratings.sort(key=lambda x: -x["power"])

    sd_m = summary["residual_sd_margin"]; sd_t = summary["residual_sd_total"]
    lines = []
    for f in fixtures:
        pm, pt = predict(full, f["home_abbr"], f["away_abbr"])
        hr = next(x for x in ratings if x["abbr"] == f["home_abbr"])
        ar = next(x for x in ratings if x["abbr"] == f["away_abbr"])
        lines.append({"game_id": f["game_id"], "week": int(f["week"]), "gameday": f["gameday"],
                      "kickoff_et": f["kickoff_et"], "home": f["home_abbr"], "away": f["away_abbr"],
                      "model_margin_home": round(pm, 1), "model_total": round(pt, 1),
                      "home_power": hr["power"], "away_power": ar["power"],
                      "home_gp": hr["gp"], "away_gp": ar["gp"],
                      "margin_sd": round(sd_m, 2), "total_sd": round(sd_t, 2),
                      "market_line": None, "market_total": None, "market_source": None,
                      "note": f.get("note", ""), "source_url": f["source_url"]})

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ratings.json").write_text(json.dumps(
        {"meta": {"hfa_points": round(full["h"], 3), "lambda": full["lam"],
                  "league_mean_points_per_team": round(full["mu"], 3), "train_games": full["n"],
                  "inputs": ["data/verified/games_2026.csv", "data/verified/standings_2026.csv"],
                  "method": "ridge opponent-adjusted points model (analysis/engine.py)"},
         "ratings": ratings}, indent=2), encoding="utf-8")
    (OUT / "backtest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "lines_week10.json").write_text(json.dumps(
        {"meta": {"week": 10, "generated_from": "weeks 1-9 completed games only",
                  "market_lines_available": False,
                  "why_no_market": "No official NFL odds/closing-line source is reachable here and "
                                   "none is stored in the repo; model numbers are NOT edges against "
                                   "a market and must not be treated as such.",
                  "validation_verdict": summary["verdict"],
                  "inputs": ["data/verified/games_2026.csv", "data/verified/standings_2026.csv",
                             "data/verified/week10_fixtures_2026.csv"]},
         "games": lines}, indent=2), encoding="utf-8")
    (OUT / "predictions_log.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    for r in leaderboard:
        print(f"{r['strategy']:<38} MAE margin {r['mae_margin']:.2f}  side acc {r['side_accuracy']:.3f}  "
              f"corr {r['corr_margin'] if r['corr_margin'] is None else round(r['corr_margin'],3)}")
    print(f"\nbootstrap {boot['comparison']}: diff {boot['mean_abs_err_difference']:+.3f} "
          f"CI95 [{boot['ci95'][0]:.3f}, {boot['ci95'][1]:.3f}] P(model better)={boot['p_model_better']:.3f}")
    print("VERDICT:", summary["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
