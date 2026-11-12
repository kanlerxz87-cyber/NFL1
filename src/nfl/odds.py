"""Odds arithmetic and the market-data contract.

The maths here is exact and unit-tested. What is NOT available is the market
data to feed it, so every market-dependent output is None with an explicit
BLOCKED reason. The module exists so that the moment an odds feed is connected
the whole leaderboard computes without further code changes.
"""
from __future__ import annotations

from typing import Any

from .provenance import UNAVAILABLE


def american_to_decimal(american: int) -> float:
    if american == 0:
        raise ValueError("American odds cannot be zero")
    if american > 0:
        return round(1.0 + american / 100.0, 6)
    return round(1.0 + 100.0 / abs(american), 6)


def decimal_to_american(decimal: float) -> int:
    if decimal <= 1.0:
        raise ValueError("Decimal odds must exceed 1.0")
    if decimal >= 2.0:
        return int(round((decimal - 1.0) * 100))
    return int(round(-100.0 / (decimal - 1.0)))


def implied_probability(american: int) -> float:
    return round(1.0 / american_to_decimal(american), 6)


def prob_to_american(p: float) -> int:
    if not 0.0 < p < 1.0:
        raise ValueError("probability must be strictly between 0 and 1")
    return decimal_to_american(1.0 / p)


def overround(book: list[int]) -> float:
    """Sum of implied probabilities. >1.0 is the bookmaker's hold."""
    return round(sum(implied_probability(a) for a in book), 6)


def devig_multiplicative(book: list[int]) -> list[float]:
    """Proportional (multiplicative) de-vig: scales every leg by the overround."""
    total = overround(book)
    return [round(implied_probability(a) / total, 6) for a in book]


def devig_power(book: list[int], tol: float = 1e-12) -> list[float]:
    """Shin/power de-vig: solves sum(p_i ** k) == 1 for the exponent k.

    Better than multiplicative on longshots, which is where parlay and prop
    pricing is most distorted.
    """
    probs = [implied_probability(a) for a in book]
    lo, hi = 0.05, 3.0
    for _ in range(300):
        mid = (lo + hi) / 2.0
        s = sum(p ** mid for p in probs)
        if abs(s - 1.0) < tol:
            break
        if s > 1.0:
            lo = mid
        else:
            hi = mid
    k = (lo + hi) / 2.0
    return [round(p ** k, 6) for p in probs]


def parlay_fair_prob(legs: list[float], correlations: list[float] | None = None) -> float:
    """Joint probability of a parlay.

    With no measured correlation this is the independent-product assumption the
    sportsbooks themselves use to price parlays. Passing measured pairwise
    correlations applies the first-order adjustment
        P(A and B) = P(A)P(B) + rho * sd(A) * sd(B)
    for each pair, which is the minimum honest correction for positively
    correlated legs. It is first-order only and is labelled as such.
    """
    if not legs:
        raise ValueError("a parlay needs at least one leg")
    for p in legs:
        if not 0.0 <= p <= 1.0:
            raise ValueError("leg probabilities must be in [0,1]")
    base = 1.0
    for p in legs:
        base *= p
    if not correlations:
        return round(base, 6)
    adj = base
    n = len(legs)
    idx = 0
    for i in range(n):
        for j in range(i + 1, n):
            rho = correlations[idx]
            idx += 1
            if not -1.0 <= rho <= 1.0:
                raise ValueError("correlations must be in [-1,1]")
            sdi = (legs[i] * (1 - legs[i])) ** 0.5
            sdj = (legs[j] * (1 - legs[j])) ** 0.5
            adj += rho * sdi * sdj
    return round(min(1.0, max(0.0, adj)), 6)


def edge(model_prob: float, american: int) -> float:
    """Expected value per unit staked at the posted price."""
    return round(model_prob * (american_to_decimal(american) - 1.0) - (1.0 - model_prob), 6)


MARKET_DATA_CONTRACT: dict[str, Any] = {
    "status": "UNAVAILABLE",
    "tier": UNAVAILABLE,
    "reason": "No licensed sportsbook odds or market-data provider is reachable "
              "or credentialed from this build environment, and NFL.com does not "
              "publish a machine-readable historical odds feed.",
    "required_fields": [
        "bookmaker, market (spread|total|moneyline|player_prop), selection, "
        "american_odds, timestamp, kickoff_time, stake_limit, "
        "is_closing (bool), player_prop_line, player_prop_stat"
    ],
    "minimum_history_for_validation": "3 full NFL regular seasons (~1,500 games) "
                                      "of closing lines, plus opening lines to "
                                      "measure closing-line value.",
    "consequence_if_absent": "Every ROI, edge, CLV and leaderboard score in this "
                             "repository is reported as NOT_RUN. No number is "
                             "substituted.",
    "resolving_sources": [
        "A licensed odds API (e.g. a regulated market-data vendor)",
        "https://github.com/nflverse/nflverse-data releases (odds tag) - "
        "community mirror, requires network access to release assets",
    ],
}
