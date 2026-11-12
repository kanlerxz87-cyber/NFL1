"""Luck removal.

Four independent instruments, in increasing order of strength:
  1. Pythagorean residual      - team-level, computable from official data TODAY.
  2. Bootstrap interval        - strategy-level, needs settled outcomes.
  3. Permutation placebo test  - strategy-level, needs settled outcomes.
  4. Closing-line value        - the gold standard, needs a closing odds feed.
Instruments 2-4 are implemented and unit-tested but return NOT_RUN until their
input exists. Instrument 1 runs now on verified data.
"""
from __future__ import annotations

import random
from typing import Any, Callable, Sequence

from . import stats


def pythagorean_luck_table(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank teams by the gap between expected and actual wins.

    pyth_delta > 0  -> scoring says the team should have won MORE than it did
                       (unlucky; a buy candidate for regression strategies).
    pyth_delta < 0  -> the team has won more than its scoring justifies
                       (lucky; a fade candidate).
    """
    rows = []
    for m in metrics:
        if m.get("pyth_delta") is None:
            continue
        d = m["pyth_delta"]
        gp = m["gp"] or 0
        rows.append({
            "team_abbr": m["team_abbr"], "gp": gp,
            "actual_win_pct": m["win_pct"], "pyth_win_pct": m["pyth_win_pct"],
            "pyth_delta": d,
            "games_of_luck": round(d * gp, 2) if gp else None,
            "net_pg": m["net_pg"], "pf": m["pf"], "pa": m["pa"],
            "direction": "UNLUCKY (under-performing scoring)" if d > 0
                         else "LUCKY (over-performing scoring)" if d < 0 else "NEUTRAL",
            "source_url": m["source_url"], "tier": "DERIVED",
        })
    rows.sort(key=lambda r: -r["pyth_delta"])
    return rows


def bootstrap_roi(returns: Sequence[float], draws: int = 5000,
                  seed: int = 20261112, alpha: float = 0.05) -> dict[str, Any]:
    """Percentile bootstrap on per-wager returns."""
    n = len(returns)
    if n < 10:
        return {"status": "NOT_RUN", "reason": f"n={n} < 10 settled wagers"}
    rng = random.Random(seed)
    means = []
    for _ in range(draws):
        means.append(sum(returns[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int((alpha / 2) * draws)]
    hi = means[int((1 - alpha / 2) * draws)]
    mu = sum(returns) / n
    sd = stats.stdev(list(returns))
    t = mu / (sd / n ** 0.5) if sd else float("nan")
    return {"status": "RUN", "n": n, "roi": round(mu, 6),
            "ci95": [round(lo, 6), round(hi, 6)],
            "t_statistic": None if t != t else round(t, 4),
            "excludes_zero": bool(lo > 0 or hi < 0)}


def permutation_placebo(returns: Sequence[float], observed_stat: float,
                        stat_fn: Callable[[Sequence[float]], float],
                        draws: int = 5000, seed: int = 20261112) -> dict[str, Any]:
    """Sign-flip permutation test.

    Under the null of no skill, each wager's return is equally likely positive or
    negative. Flipping signs destroys any real edge while preserving the return
    distribution, so the fraction of permutations beating the observed statistic
    is an honest p-value.
    """
    n = len(returns)
    if n < 10:
        return {"status": "NOT_RUN", "reason": f"n={n} < 10 settled wagers"}
    rng = random.Random(seed)
    hits = 0
    for _ in range(draws):
        flipped = [r * (1 if rng.random() < 0.5 else -1) for r in returns]
        if stat_fn(flipped) >= observed_stat:
            hits += 1
    return {"status": "RUN", "n": n, "draws": draws,
            "placebo_p": round((hits + 1) / (draws + 1), 5)}


def skill_vs_luck_variance(returns: Sequence[float]) -> dict[str, Any]:
    """Decompose observed return variance into the coin-flip floor and the rest.

    A bettor with zero skill staking at even-money odds has per-wager variance
    of 1.0. Any variance ABOVE that floor is attributable to the strategy's own
    signal (or to stake sizing); any skill claim must survive removing the floor.
    """
    n = len(returns)
    if n < 10:
        return {"status": "NOT_RUN", "reason": f"n={n} < 10 settled wagers"}
    var = stats.stdev(list(returns)) ** 2
    floor = 1.0
    return {"status": "RUN", "n": n, "observed_variance": round(var, 6),
            "coinflip_variance_floor": floor,
            "excess_variance": round(var - floor, 6),
            "skill_share_of_variance": round(max(0.0, (var - floor)) / var, 4)
            if var else None}


def closing_line_value(model_line: float, closing_line: float) -> float:
    """CLV in points: positive means the model beat the closing number."""
    return round(model_line - closing_line, 4)


def clv_report(pairs: Sequence[tuple[float, float]]) -> dict[str, Any]:
    if len(pairs) < 10:
        return {"status": "NOT_RUN",
                "reason": f"n={len(pairs)} < 10 (model line, closing line) pairs; "
                          "no closing odds feed is available in this environment"}
    vals = [closing_line_value(m, c) for m, c in pairs]
    return {"status": "RUN", "n": len(vals), "mean_clv_points": round(sum(vals) / len(vals), 4),
            "positive_share": round(sum(1 for v in vals if v > 0) / len(vals), 4)}
