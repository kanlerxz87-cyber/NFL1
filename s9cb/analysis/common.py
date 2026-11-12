#!/usr/bin/env python3
"""Shared helpers for the session-9cb71eb8 research build.

Everything here is deliberately explicit and small enough to read line by line.
No value is invented: when the source has no price, a bet is not scored, and the
count of unscored games is published next to every result.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data", "s9cb")
OUT = os.path.join(ROOT, "data", "s9cb")

OFFICIAL = {
    "schedules": "https://www.nfl.com/schedules/",
    "standings": "https://www.nfl.com/standings/league/2026/reg",
    "injuries": "https://www.nfl.com/injuries/",
    "stats": "https://www.nfl.com/stats/player-stats/",
    "teams": "https://www.nfl.com/teams/",
}
SOURCE_REPO = "https://github.com/nflverse/nflverse-data"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(name: str, obj) -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(clean(obj), f, indent=1)
    print(f"wrote data/s9cb/{name}")


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.isoformat()
    return o


# ------------------------------------------------------------------ odds maths
def american_to_decimal(a: float) -> float:
    """Decimal return per 1 unit staked, including the stake."""
    a = float(a)
    if a == 0 or a is None or (isinstance(a, float) and math.isnan(a)):
        return float("nan")
    return 1.0 + (a / 100.0 if a > 0 else 100.0 / abs(a))


def implied_prob(a: float) -> float:
    d = american_to_decimal(a)
    return 1.0 / d if d == d else float("nan")


def profit_row(american: float, won: int, pushed: bool = False, stake: float = 1.0) -> float:
    if pushed:
        return 0.0
    if won:
        return stake * (american_to_decimal(american) - 1.0)
    return -stake


# ------------------------------------------------------------------ statistics
def pearson(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    n = len(x)
    if n < 5:
        return None
    if np.std(x) == 0 or np.std(y) == 0:
        return None
    r = float(np.corrcoef(x, y)[0, 1])
    if n <= 3 or abs(r) >= 1.0:
        return {"n": n, "r": r, "ci95": None, "p_value": None, "method": "Pearson r"}
    # Fisher z confidence interval and two-sided t test
    z = np.arctanh(r)
    se = 1.0 / math.sqrt(n - 3)
    lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    t = r * math.sqrt((n - 2) / max(1e-12, 1 - r * r))
    p = 2.0 * (1.0 - _student_t_cdf(abs(t), n - 2))
    return {
        "n": n, "r": round(r, 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "p_value": round(float(p), 6), "t_stat": round(float(t), 4),
        "method": "Pearson r, Fisher-z 95% CI, two-sided t test",
    }


def _student_t_cdf(t: float, df: float) -> float:
    """Student t CDF. Uses scipy and is asserted against it in s9cb/analysis/selftest.py."""
    from scipy.stats import t as _t
    return float(_t.cdf(float(t), float(df)))


def binomial_p_two_sided(k: int, n: int, p0: float) -> float:
    """Exact two-sided binomial test (sum of tail probabilities <= observed)."""
    if n == 0 or not (0.0 < p0 < 1.0):
        return float("nan")
    from scipy.stats import binomtest
    return float(binomtest(int(k), int(n), float(p0), alternative="two-sided").pvalue)


def benjamini_hochberg(pvals):
    """Return BH-adjusted p-values (same order as input). NaN stays NaN."""
    p = np.asarray(pvals, dtype=float)
    out = np.full(p.shape, np.nan)
    idx = np.where(np.isfinite(p))[0]
    if idx.size == 0:
        return out
    m = idx.size
    order = idx[np.argsort(p[idx])]
    ranked = p[order]
    adj = ranked * m / (np.arange(1, m + 1))
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.minimum(adj, 1.0)
    out[order] = adj
    return out


def bootstrap_ci(values, n_boot: int = 10000, alpha: float = 0.05, seed: int = 20261112):
    """Percentile bootstrap CI for the MEAN of `values`.

    Resamples the bet log with replacement and reports the 2.5th and 97.5th percentile
    of the resampled mean. Ten thousand resamples of the actual bets actually placed.
    """
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    n = len(v)
    if n < 20:
        return None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = v[idx].mean(axis=1)
    lo = float(np.percentile(means, 100 * alpha / 2))
    hi = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return [round(lo, 6), round(hi, 6)]


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# ------------------------------------------------------------------ data load
def load_games() -> pd.DataFrame:
    g = pd.read_csv(os.path.join(DATA, "games.csv"))
    g = g.sort_values(["season", "week", "gameday", "game_id"]).reset_index(drop=True)
    g["played"] = g["home_score"].notna() & g["away_score"].notna()
    g["has_price"] = g["home_spread_odds"].notna() & g["away_spread_odds"].notna()
    return g


def load_prov() -> dict:
    with open(os.path.join(DATA, "provenance.json")) as f:
        return json.load(f)
