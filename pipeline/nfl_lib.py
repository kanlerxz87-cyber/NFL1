#!/usr/bin/env python3
"""Shared helpers: IO, play filtering, team-EPA ratings, market math, betting stats.

Every model here is deliberately small and auditable. No value is filled in when the
upstream file lacks it; missing values stay missing and are reported as such.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Callable, Iterable

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(ROOT, "build", "raw")
OUT = os.path.join(ROOT, "data", "model")

# Standard American odds pricing used for evaluation unless a file carries real prices.
JUICE = -110.0
BREAKEVEN = 110.0 / 210.0  # 0.523809...


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load(name: str, **kw) -> pd.DataFrame:
    path = os.path.join(RAW, name)
    if not os.path.exists(path):
        raise FileNotFoundError(name)
    if name.endswith(".parquet"):
        return pd.read_parquet(path, **kw)
    return pd.read_csv(path, low_memory=False, **kw)


def write_json(name: str, obj) -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(obj, f, indent=1, default=str)
    print(f"wrote data/model/{name}")


def american_to_decimal(a) -> float:
    a = float(a)
    return 1.0 + (a / 100.0 if a > 0 else 100.0 / abs(a))


# ---------------------------------------------------------------- play filtering
GARBAGE_WP = 0.05


def clean_plays(pbp: pd.DataFrame) -> pd.DataFrame:
    """Drop non-snap plays, specials, aborted plays, kneels/spikes and garbage time.

    Garbage-time rule: win probability outside [0.05, 0.95] (nflfastR's wp model).
    This is the same convention used by public EPA splits; it is a documented choice,
    not an official NFL rule.
    """
    df = pbp.copy()
    df = df[df.get("season_type", "REG") == "REG"]
    df = df[df["play_type"].isin(["pass", "run"])]
    df = df[df["epa"].notna()]
    for flag in ("aborted_play", "qb_kneel", "qb_spike"):
        if flag in df.columns:
            df = df[df[flag].fillna(0) != 1]
    if "penalty" in df.columns:
        df = df[df["penalty"].fillna(0) != 1]
    if "wp" in df.columns:
        df = df[(df["wp"] >= GARBAGE_WP) & (df["wp"] <= 1 - GARBAGE_WP)]
    return df


# ---------------------------------------------------------------- EPA ratings
def fit_epa_ratings(plays: pd.DataFrame, teams: Iterable[str], lam: float = 40.0,
                    weights: np.ndarray | None = None) -> dict[str, dict[str, float]]:
    """Two-way fixed-effect ridge fit: epa ~ offense_team + defense_team + home.

    Returns {team: {off, def, net, n_off, n_def}}. `def` is sign-flipped so a
    positive number always means "good for that team".
    Plays are centred implicitly by the ridge penalty; the home coefficient is
    unpenalised so it absorbs the league-wide home edge.
    """
    teams = sorted(teams)
    idx = {t: i for i, t in enumerate(teams)}
    k = len(teams)
    df = plays[plays["posteam"].isin(idx) & plays["defteam"].isin(idx)]
    if len(df) < 200:
        return {}
    n = len(df)
    X = np.zeros((n, 2 * k + 1), dtype=np.float64)
    rows = np.arange(n)
    X[rows, [idx[t] for t in df["posteam"]]] = 1.0
    X[rows, k + np.array([idx[t] for t in df["defteam"]])] = 1.0
    X[:, -1] = (df["posteam"] == df["home_team"]).astype(float)
    y = df["epa"].to_numpy(dtype=np.float64)
    w = np.ones(n) if weights is None else np.asarray(weights, dtype=np.float64)

    Xw = X * w[:, None]
    A = X.T @ Xw
    b = Xw.T @ y
    pen = np.full(2 * k + 1, lam)
    pen[-1] = 1e-8  # home field unpenalised
    A[np.diag_indices_from(A)] += pen
    try:
        beta = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        beta, *_ = np.linalg.lstsq(A, b, rcond=None)

    off_n = df["posteam"].value_counts().to_dict()
    def_n = df["defteam"].value_counts().to_dict()
    out = {}
    for t in teams:
        off = float(beta[idx[t]])
        dfn = float(-beta[k + idx[t]])
        out[t] = {
            "off": off,
            "def": dfn,
            "net": off + dfn,
            "n_off": int(off_n.get(t, 0)),
            "n_def": int(def_n.get(t, 0)),
        }
    return out


def week_ratings(pbp_all: pd.DataFrame, teams: list[str], season: int, week: int,
                 prior_weight: float = 0.4) -> dict[str, dict[str, float]]:
    """Ratings known BEFORE `week` of `season` (no leakage).

    Current-season plays (weeks < week) get weight 1.0. The whole previous season is
    included with weight `prior_weight` so early-season ratings are shrunk toward a
    team's prior-year form instead of being driven by two games.
    """
    cur = pbp_all[(pbp_all["season"] == season) & (pbp_all["week"] < week)]
    prior = pbp_all[(pbp_all["season"] == season - 1)]
    if len(cur) == 0 and len(prior) == 0:
        return {}
    frames, weights = [], []
    if len(prior):
        frames.append(prior)
        weights.append(np.full(len(prior), prior_weight))
    if len(cur):
        frames.append(cur)
        weights.append(np.ones(len(cur)))
    plays = pd.concat(frames, ignore_index=True)
    w = np.concatenate(weights)
    return fit_epa_ratings(plays, teams, weights=w)


# ---------------------------------------------------------------- market / grading
def cover_result(margin: float, spread_line: float, side: str) -> str:
    """Graded against the closing line. spread_line is from the home team's view."""
    v = margin + spread_line
    if abs(v) < 1e-9:
        return "push"
    home_covers = v > 0
    if side == "home":
        return "win" if home_covers else "loss"
    return "loss" if home_covers else "win"


def total_result(total: float, line: float, side: str) -> str:
    if abs(total - line) < 1e-9:
        return "push"
    over = total > line
    if side == "over":
        return "win" if over else "loss"
    return "loss" if over else "win"


def payout(price: float = JUICE) -> float:
    return american_to_decimal(price) - 1.0


def roi(returns: np.ndarray) -> float:
    return float(np.mean(returns)) if len(returns) else float("nan")


def summarize_bets(bets: pd.DataFrame, n_boot: int = 10000, seed: int = 7) -> dict:
    """Win rate, ROI, bootstrap CI, exact binomial p-value, per-season split, drawdown."""
    graded = bets[bets["result"].isin(["win", "loss", "push"])].copy()
    gw = graded[graded["result"] != "push"]
    wins = int((gw["result"] == "win").sum())
    losses = int((gw["result"] == "loss").sum())
    pushes = int((graded["result"] == "push").sum())
    n = wins + losses
    p = payout()
    rets = np.where(gw["result"] == "win", p, -1.0)
    out = {
        "n_bets": int(len(graded)),
        "n_graded": n,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_pct": round(wins / n, 4) if n else None,
        "roi": round(float(rets.mean()), 4) if n else None,
        "units": round(float(rets.sum()), 2) if n else None,
        "breakeven_win_pct": round(BREAKEVEN, 4),
        "price_used": JUICE,
    }
    if n:
        rng = np.random.default_rng(seed)
        boot = rng.choice(rets, size=(n_boot, n), replace=True).mean(axis=1)
        out["roi_ci95"] = [round(float(np.percentile(boot, 2.5)), 4),
                           round(float(np.percentile(boot, 97.5)), 4)]
        out["boot_p_roi_le_0"] = round(float((boot <= 0).mean()), 4)
        try:
            from scipy.stats import binomtest
            out["binom_p_vs_breakeven"] = round(
                float(binomtest(wins, n, BREAKEVEN, alternative="greater").pvalue), 4)
        except Exception:  # noqa: BLE001
            out["binom_p_vs_breakeven"] = None
        # max drawdown in units, ordered by date/week
        order = gw.sort_values(["season", "week"]).index
        curve = np.cumsum(np.where(gw.loc[order, "result"] == "win", p, -1.0))
        peak = np.maximum.accumulate(np.concatenate([[0.0], curve]))[1:]
        out["max_drawdown_units"] = round(float(np.min(curve - peak)), 2)
        by_season = {}
        for s, grp in gw.groupby("season"):
            g = np.where(grp["result"] == "win", p, -1.0)
            by_season[str(int(s))] = {"n": int(len(grp)), "roi": round(float(g.mean()), 4)}
        out["by_season"] = by_season
        out["seasons_positive"] = int(sum(1 for v in by_season.values() if v["roi"] > 0))
        out["seasons_tested"] = len(by_season)
    return out


def benjamini_hochberg(pvals: list[float]) -> list[float]:
    """BH-adjusted q-values; used so the leaderboard does not reward multiple testing."""
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    prev = 1.0
    for rank, i in enumerate(order[::-1], start=1):
        q = min(prev, pvals[i] * m / (m - rank + 1))
        adj[i] = q
        prev = q
    return [round(float(min(1.0, max(0.0, q))), 4) for q in adj]


def spearman(a: Iterable[float], b: Iterable[float]) -> float | None:
    s = pd.Series(a).rank()
    t = pd.Series(b).rank()
    if s.std() == 0 or t.std() == 0:
        return None
    return round(float(np.corrcoef(s, t)[0, 1]), 4)


def phi(x: Iterable[int], y: Iterable[int]) -> float | None:
    a, b = np.asarray(list(x), dtype=float), np.asarray(list(y), dtype=float)
    if len(a) < 3 or a.std() == 0 or b.std() == 0:
        return None
    return round(float(np.corrcoef(a, b)[0, 1]), 4)


def parlay_prob(ps: list[float], rhos: list[float] | None = None) -> float:
    """Win probability of a parlay. Independent legs multiply; same-game legs use phi.

    For one correlated pair: P = p1p2 + rho*sqrt(p1(1-p1)p2(1-p2)).
    """
    probs = [float(p) for p in ps]
    if rhos is None or not rhos:
        return float(np.prod(probs))
    base = float(np.prod(probs))
    adj = 0.0
    for (p1, p2), rho in zip(zip(probs, probs[1:]), rhos):
        adj += rho * np.sqrt(p1 * (1 - p1) * p2 * (1 - p2))
    return float(base + adj)


def rel(path: str) -> Callable[[str], str]:
    return lambda s: f"{path}{s}"
