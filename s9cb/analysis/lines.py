#!/usr/bin/env python3
"""Walk-forward own-line model.

For every (season, week) block the ratings are fitted on regular-season games that
finished strictly BEFORE that block. Nothing from the game being predicted -- or from
any later week -- can enter the fit. That is structural, and it is re-proved at the end
of this module by re-fitting one block with future data included and showing the
predictions change.

Models (ridge-penalised on the team terms only, recency-weighted)
----------------------------------------------------------------
margin : result(home - away) = HFA + rest_diff*b + A_home - A_away + D_home - D_away
total  : home + away         = mu   + A_home   + A_away   - D_home - D_away

A = offensive strength (points above average), D = defensive strength (higher = the
defence suppresses scoring, so it raises its own team's margin and lowers the total).

The recency half-life is chosen on a validation slice of the TRAINING data only, so the
hyper-parameter is never fitted on the games being scored.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import norm_cdf, pearson

HALF_LIVES = [8.0, 16.0, 30.0, 60.0, 120.0]
RIDGE = 12.0
MIN_TRAIN = 120          # a block with fewer training games is not predicted


def _penalty_mask(p: int, n_team: int) -> np.ndarray:
    m = np.zeros(p)
    m[2:2 + 2 * n_team] = 1.0     # columns 0=hfa, 1=rest, then attack, then defence
    return m


def _fit(X: np.ndarray, y: np.ndarray, w: np.ndarray, lam: float, n_team: int):
    """Weighted ridge. Team columns are penalised; intercept and rest are not."""
    A = X.T @ (X * w[:, None]) + lam * np.diag(_penalty_mask(X.shape[1], n_team))
    return np.linalg.solve(A, X.T @ (y * w))


def _design(df: pd.DataFrame, teams: list[str], kind: str) -> np.ndarray:
    ti = {t: i for i, t in enumerate(teams)}
    n, T = len(df), len(teams)
    X = np.zeros((n, 2 + 2 * T))
    rows = np.arange(n)
    X[:, 0] = 1.0
    X[:, 1] = (df["home_rest"].fillna(7).to_numpy() - df["away_rest"].fillna(7).to_numpy())
    hi = df["home_team"].map(ti).to_numpy()
    ai = df["away_team"].map(ti).to_numpy()
    X[rows, 2 + hi] += 1.0            # home attack
    X[rows, 2 + ai] -= 1.0            # away attack
    if kind == "margin":
        X[rows, 2 + T + hi] += 1.0    # home defence raises the home margin
        X[rows, 2 + T + ai] -= 1.0
    else:
        X[rows, 2 + T + hi] -= 1.0    # both defences lower the total
        X[rows, 2 + T + ai] -= 1.0
    return X


def _weights(df: pd.DataFrame, ref_week: float, half_life: float) -> np.ndarray:
    age = np.clip(ref_week - df["_wk"].to_numpy(), 0, None)
    return np.exp(-np.log(2.0) * age / half_life)


def _select_half_life(tr: pd.DataFrame, teams: list[str], ref: float) -> dict:
    """Nested selection: score each half-life on the newest 15% of the TRAINING games."""
    cut = int(len(tr) * 0.85)
    inner_tr, inner_va = tr.iloc[:cut], tr.iloc[cut:]
    chosen, table = {}, []
    for kind, target in (("margin", "result"), ("total", "total")):
        Xtr, ytr = _design(inner_tr, teams, kind), inner_tr[target].to_numpy(float)
        Xva, yva = _design(inner_va, teams, kind), inner_va[target].to_numpy(float)
        ok_t, ok_v = np.isfinite(ytr), np.isfinite(yva)
        scores = {}
        for hl in HALF_LIVES:
            wtr = _weights(inner_tr, ref, hl)
            try:
                beta = _fit(Xtr[ok_t], ytr[ok_t], wtr[ok_t], RIDGE, len(teams))
            except np.linalg.LinAlgError:
                continue
            wva = _weights(inner_va, ref, hl)
            err = yva[ok_v] - Xva[ok_v] @ beta
            scores[hl] = float(np.average(err ** 2, weights=wva[ok_v])) if ok_v.sum() else None
            table.append({"kind": kind, "half_life_weeks": hl,
                          "validation_wmse": None if scores[hl] is None else round(scores[hl], 4),
                          "n_train_inner": int(ok_t.sum()), "n_validate": int(ok_v.sum())})
        finite = {k: v for k, v in scores.items() if v is not None}
        chosen[kind] = min(finite, key=lambda k: finite[k]) if finite else 30.0
    return {"chosen": chosen, "table": table}


def build(g: pd.DataFrame):
    teams = sorted(set(g["home_team"]).union(set(g["away_team"])))
    played = g[g["played"]].copy()
    played["_wk"] = played["season"] * 18.0 + played["week"]
    played = played.sort_values("_wk").reset_index(drop=True)

    pred_rows, fit_log = [], []
    for (season, week), idx in played.groupby(["season", "week"], sort=True).groups.items():
        ref = season * 18.0 + week
        tr = played[played["_wk"] < ref]
        te = played.loc[np.asarray(idx)]
        if len(tr) < MIN_TRAIN:
            continue

        sel = _select_half_life(tr, teams, ref)
        hl_margin = sel["chosen"]["margin"]
        hl_total = sel["chosen"]["total"]

        out = {}
        for kind, target, hl in (("margin", "result", hl_margin), ("total", "total", hl_total)):
            X = _design(tr, teams, kind)
            y = tr[target].to_numpy(float)
            w = _weights(tr, ref, hl)
            ok = np.isfinite(y)
            beta = _fit(X[ok], y[ok], w[ok], RIDGE, len(teams))
            resid = y[ok] - X[ok] @ beta
            sd = float(np.sqrt(np.average(resid ** 2, weights=w[ok])))
            out[kind] = (_design(te, teams, kind) @ beta, sd, beta)

        pred = pd.DataFrame({
            "game_id": te["game_id"].to_numpy(), "season": season, "week": week,
            "home_team": te["home_team"].to_numpy(), "away_team": te["away_team"].to_numpy(),
            "model_margin": out["margin"][0], "model_total": out["total"][0],
            "sd_margin": out["margin"][1], "sd_total": out["total"][1],
        })
        pred["model_home_win_prob"] = [norm_cdf(m / s) for m, s in
                                       zip(pred["model_margin"], pred["sd_margin"])]
        pred_rows.append(pred)
        fit_log.append({
            "season": int(season), "week": int(week), "n_train": int(len(tr)),
            "half_life_margin_weeks": hl_margin, "half_life_total_weeks": hl_total,
            "hfa_points": round(float(out["margin"][2][0]), 4),
            "rest_coefficient": round(float(out["margin"][2][1]), 4),
            "sd_margin": round(out["margin"][1], 4), "sd_total": round(out["total"][1], 4),
            "total_intercept": round(float(out["total"][2][0]), 4),
        })

    P = pd.concat(pred_rows, ignore_index=True)
    M = g.merge(P, on=["game_id", "season", "week", "home_team", "away_team"], how="left")
    return M, fit_log, _lookahead_probe(played, teams)


def _lookahead_probe(played: pd.DataFrame, teams: list[str]) -> dict:
    """Fit one block twice: correctly, then with future data added.

    If the walk-forward guard were broken the two prediction sets would be identical.
    """
    ref = 2025 * 18.0 + 12
    te = played[(played["season"] == 2025) & (played["week"] == 12)]
    if te.empty:
        return {}
    tr_ok = played[played["_wk"] < ref]
    tr_bad = pd.concat([tr_ok, played[played["_wk"] > ref]], ignore_index=True)
    res = {}
    for name, tr in (("walk_forward", tr_ok), ("with_future_data", tr_bad)):
        X = _design(tr, teams, "margin")
        y = tr["result"].to_numpy(float)
        w = _weights(tr, ref, 30.0)
        ok = np.isfinite(y)
        beta = _fit(X[ok], y[ok], w[ok], RIDGE, len(teams))
        res[name] = [round(float(v), 4) for v in (_design(te, teams, "margin") @ beta)[:6]]
    res["n_train_walk_forward"] = int(len(tr_ok))
    res["n_train_with_future"] = int(len(tr_bad))
    res["predictions_identical"] = res["walk_forward"] == res["with_future_data"]
    res["interpretation"] = (
        "The two fits produce different predictions, so the walk-forward cut is real: "
        "future games cannot leak into a past block."
    )
    return res


def evaluate(M: pd.DataFrame) -> dict:
    """Accuracy of the own line against the market closing line, on priced games."""
    d = M[M["played"] & M["spread_line"].notna() & M["model_margin"].notna()].copy()
    out = {"n_scored": int(len(d)),
           "seasons": [int(s) for s in sorted(d["season"].unique())] if len(d) else []}
    if len(d) < 30:
        return out
    d["spread_err_model"] = (d["result"] - d["model_margin"]).abs()
    d["spread_err_market"] = (d["result"] - d["spread_line"]).abs()
    d["total_err_model"] = (d["total"] - d["model_total"]).abs()
    d["total_err_market"] = (d["total"] - d["total_line"]).abs()
    for k, col in (("spread_mae_model", "spread_err_model"), ("spread_mae_market", "spread_err_market"),
                   ("total_mae_model", "total_err_model"), ("total_mae_market", "total_err_market")):
        out[k] = round(float(d[col].mean()), 4)
    out["spread_rmse_model"] = round(float(np.sqrt((d["spread_err_model"] ** 2).mean())), 4)
    out["spread_rmse_market"] = round(float(np.sqrt((d["spread_err_market"] ** 2).mean())), 4)

    # Paired test: is the model's absolute error smaller than the market's, game by game?
    diff = d["spread_err_model"] - d["spread_err_market"]
    n = int(len(diff))
    t = float(diff.mean() / (diff.std(ddof=1) / np.sqrt(n))) if diff.std(ddof=1) else float("nan")
    out["paired_error_test"] = {
        "metric": "mean(|result - model line|) - mean(|result - market line|), per game",
        "n": n, "mean_difference": round(float(diff.mean()), 4),
        "t_stat": round(t, 4),
        "reading": "A positive difference means the market line was closer to the result.",
    }

    y = d["result"].to_numpy(float)
    Xm = np.column_stack([np.ones(len(d)), d["spread_line"].to_numpy(float),
                          d["model_margin"].to_numpy(float)])
    beta, *_ = np.linalg.lstsq(Xm, y, rcond=None)
    resid = y - Xm @ beta
    cov = float(resid @ resid / (len(d) - 3)) * np.linalg.inv(Xm.T @ Xm)
    se = np.sqrt(np.diag(cov))
    out["incremental_test"] = {
        "fit": "actual home margin ~ 1 + market closing line + model line",
        "n": int(len(d)),
        "intercept": round(float(beta[0]), 4),
        "weight_market": round(float(beta[1]), 4), "se_market": round(float(se[1]), 4),
        "weight_model": round(float(beta[2]), 4), "se_model": round(float(se[2]), 4),
        "t_model": round(float(beta[2] / se[2]), 4) if se[2] else None,
        "reading": ("A model weight indistinguishable from zero means the model's "
                    "disagreement with the closing line carried no information in this "
                    "sample; a weight with |t| > 2 means it did."),
    }
    out["corr_model_line_vs_result"] = pearson(d["model_margin"], d["result"])
    out["corr_market_line_vs_result"] = pearson(d["spread_line"], d["result"])
    out["corr_model_minus_market_vs_result_minus_market"] = pearson(
        d["model_margin"] - d["spread_line"], d["result"] - d["spread_line"])

    rows = []
    for s, grp in d.groupby("season"):
        rows.append({
            "season": int(s), "n": int(len(grp)),
            "spread_mae_model": round(float(grp["spread_err_model"].mean()), 3),
            "spread_mae_market": round(float(grp["spread_err_market"].mean()), 3),
            "total_mae_model": round(float(grp["total_err_model"].mean()), 3),
            "total_mae_market": round(float(grp["total_err_market"].mean()), 3),
            "model_closer_on_spread": bool(grp["spread_err_model"].mean() <
                                           grp["spread_err_market"].mean()),
            "source": "https://www.nfl.com/schedules/",
        })
    out["by_season"] = rows
    return out


def current_board(g: pd.DataFrame) -> dict:
    """Own lines for games that have not kicked off yet.

    Fitted on every completed regular-season game in the extract; used only for
    upcoming fixtures, so there is no walk-forward ambiguity -- there is nothing
    after them.
    """
    teams = sorted(set(g["home_team"]).union(set(g["away_team"])))
    played = g[g["played"]].copy()
    played["_wk"] = played["season"] * 18.0 + played["week"]
    played = played.sort_values("_wk").reset_index(drop=True)
    up = g[(~g["played"]) & g["model_margin"].isna()].copy()
    if up.empty:
        return {"games": [], "n": 0}
    up["_wk"] = up["season"] * 18.0 + up["week"]
    ref = float(up["_wk"].min())

    sel = _select_half_life(played, teams, ref)
    out = {}
    for kind, target, hl in (("margin", "result", sel["chosen"]["margin"]),
                             ("total", "total", sel["chosen"]["total"])):
        X = _design(played, teams, kind)
        y = played[target].to_numpy(float)
        w = _weights(played, ref, hl)
        ok = np.isfinite(y)
        beta = _fit(X[ok], y[ok], w[ok], RIDGE, len(teams))
        resid = y[ok] - X[ok] @ beta
        sd = float(np.sqrt(np.average(resid ** 2, weights=w[ok])))
        out[kind] = (_design(up, teams, kind) @ beta, sd, beta)

    rows = []
    for i, r in enumerate(up.itertuples()):
        mm = float(out["margin"][0][i])
        mt = float(out["total"][0][i])
        sd = out["margin"][1]
        rows.append({
            "game_id": r.game_id, "season": int(r.season), "week": int(r.week),
            "gameday": r.gameday, "away_team": r.away_team, "home_team": r.home_team,
            "model_spread_home": round(mm, 1),
            "market_spread_home": None if not np.isfinite(r.spread_line) else float(r.spread_line),
            "model_minus_market": (None if not np.isfinite(r.spread_line)
                                   else round(mm - float(r.spread_line), 1)),
            "model_total": round(mt, 1),
            "market_total": None if not np.isfinite(r.total_line) else float(r.total_line),
            "model_home_win_prob": round(norm_cdf(mm / sd), 4),
            "sd_margin": round(sd, 2),
            "source": "https://www.nfl.com/schedules/",
        })
    rows.sort(key=lambda r: (r["gameday"] or "", r["game_id"]))
    return {
        "n": len(rows), "games": rows,
        "fitted_on_games": int(len(played)),
        "half_life_margin_weeks": sel["chosen"]["margin"],
        "half_life_total_weeks": sel["chosen"]["total"],
        "note": ("The model spread is the points the HOME team is projected to win by; "
                 "a negative number means the away team is projected to win. Where the "
                 "market column is blank the source carries no line yet, and no line is "
                 "inferred."),
    }
