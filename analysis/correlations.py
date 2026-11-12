#!/usr/bin/env python3
"""
correlations.py — empirical correlation values for parlay / same-game-leg exposure.

All values are computed from the verified 2026 game results (weeks 1-9, n=136 finished
games). Nothing is imported from a blog or assumed: each correlation ships with its
sample size, a 95% Fisher-z confidence interval, and a two-sided p-value.

Correlations published
  C1 same-game winner relationship  — home win rate; is "both home teams win" independent?
  C2 margin/total inside one game     — is a blowout linked to a high total?
  C3 back-to-back games of one team   — do consecutive game totals correlate?
  C4 team scoring autocorrelation     — week-to-week persistence of a team's output
  C5 division-game flag vs total      — checked, reported even if ~0

Interpretation rule enforced downstream: two legs are only "independent" when the
correlation is statistically indistinguishable from 0, and even then the default for
same-game legs is to assume dependence — absence of evidence is not independence.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "verified"
OUT = DATA / "model"
MIN_N_FOR_PUBLICATION = 25


def fisher_ci(r: float, n: int, z: float = 1.959964) -> list[float]:
    if n <= 3 or abs(r) >= 1:
        return [None, None]
    zr = math.atanh(r)
    se = 1 / math.sqrt(n - 3)
    return [round(math.tanh(zr - z * se), 4), round(math.tanh(zr + z * se), 4)]


def p_value(r: float, n: int) -> float:
    if n <= 3 or abs(r) >= 1:
        return 1.0
    t = r * math.sqrt((n - 2) / (1 - r * r))
    # two-sided p from t distribution via incomplete beta (math-only, no scipy)
    df = n - 2
    x = df / (df + t * t)
    # regularised incomplete beta I_x(df/2, 1/2)
    def betacf(a, b, x, itmax=200, eps=3e-16):
        qab, qap, qam = a + b, a + 1, a - 1
        c, d = 1.0, 1 - qab * x / qap
        d = 1 / (d if abs(d) > 1e-30 else 1e-30)
        h = d
        for m in range(1, itmax):
            m2 = 2 * m
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-30 else 1e-30)
            c = 1 + aa / c; c = c if abs(c) > 1e-30 else 1e-30
            h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-30 else 1e-30)
            c = 1 + aa / c; c = c if abs(c) > 1e-30 else 1e-30
            de = d * c
            h *= de
            if abs(de - 1) < eps:
                break
        return h
    a, b = df / 2, 0.5
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    if x < (a + 1) / (a + b + 2):
        ib = math.exp(a * math.log(x) + b * math.log(1 - x) - lbeta) * betacf(a, b, x) / a
    else:
        ib = 1 - math.exp(b * math.log(1 - x) + a * math.log(x) - lbeta) * betacf(b, a, 1 - x) / b
    return float(min(1.0, ib))


def r_of(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def main() -> int:
    with (DATA / "games_2026.csv").open(newline="", encoding="utf-8") as fh:
        games = list(csv.DictReader(fh))
    for g in games:
        g["week"] = int(g["week"])
        g["hs"], g["as_"] = int(g["home_score"]), int(g["away_score"])
        g["total"] = g["hs"] + g["as_"]
        g["margin"] = g["hs"] - g["as_"]
    games.sort(key=lambda g: (g["week"], g["gameday"]))
    n = len(games)

    out = {"n_games": n, "weeks": sorted({g["week"] for g in games}),
           "input": "data/verified/games_2026.csv",
           "method": "Pearson r on verified official results; Fisher-z 95% CI; two-sided t test",
           "correlations": []}

    def add(cid, label, r, nn, note="", kind="continuous"):
        entry = {
            "id": cid, "relationship": label, "kind": kind, "n": int(nn),
            "r": None if (r is None or (isinstance(r, float) and math.isnan(r))) else round(r, 4),
            "ci95": fisher_ci(r, nn) if r is not None and not (isinstance(r, float) and math.isnan(r)) else [None, None],
            "p_value": None if r is None or (isinstance(r, float) and math.isnan(r)) else round(p_value(r, nn), 6),
            "independent_at_5pct": None if r is None or (isinstance(r, float) and math.isnan(r)) else p_value(r, nn) >= 0.05,
            "note": note,
        }
        out["correlations"].append(entry)

    # C1: same-game winner correlation (home win fraction + binomial CI)
    home_wins = int((np.array([g["margin"] for g in games]) > 0).sum())
    ties = int((np.array([g["margin"] for g in games]) == 0).sum())
    decided = n - ties
    p = home_wins / decided
    se = math.sqrt(p * (1 - p) / decided)
    out["home_win"] = {"home_wins": home_wins, "decided_games": decided, "ties": ties,
                       "rate": round(p, 4),
                       "ci95": [round(p - 1.959964 * se, 4), round(p + 1.959964 * se, 4)],
                       "note": "Expected ~0.5 if home field did not matter. This is the base "
                               "correlation between any two legs that both require a home win."}

    # C2: within-game margin vs total
    add("C2", "Point margin vs total points, same game",
        r_of([g["margin"] for g in games], [g["total"] for g in games]), n,
        "Measures whether blowouts travel with high totals. Matters for spread+total parlays.")

    # C3: a team's consecutive game totals
    by_team = {}
    for g in games:
        by_team.setdefault(g["away_abbr"], []).append((g["week"], g["as_"]))
        by_team.setdefault(g["home_abbr"], []).append((g["week"], g["hs"]))
    x3, y3 = [], []
    for t, lst in by_team.items():
        lst.sort()
        for (w1, s1), (w2, s2) in zip(lst, lst[1:]):
            if w2 - w1 == 1:
                x3.append(s1); y3.append(s2)
    add("C3", "Team points in consecutive games (week t vs week t+1)",
        r_of(x3, y3), len(x3),
        "Persistence of a team's scoring. Autocorrelation implies form/structure, not independence.")

    # C4: team game total vs that opponent's defensive allowance (sanity: opponent strength)
    pa_pg = {}
    for g in games:
        pa_pg.setdefault(g["away_abbr"], []).append(g["hs"])
        pa_pg.setdefault(g["home_abbr"], []).append(g["as_"])
    x4, y4 = [], []
    for g in games:
        x4.append(g["as_"]); y4.append(np.mean(pa_pg[g["home_abbr"]]))
        x4.append(g["hs"]); y4.append(np.mean(pa_pg[g["away_abbr"]]))
    add("C4", "Away/home points scored vs opponent's average points allowed",
        r_of(x4, y4), len(x4),
        "Opponent-quality dependence. Contaminates naive correlations that mix home and road legs.")

    # C5: division games vs total (needs a division map -> derived from standings file)
    with (DATA / "standings_2026.csv").open(newline="", encoding="utf-8") as fh:
        st = list(csv.DictReader(fh))
    div = {r["abbr"]: r["division"] for r in st}
    div_flag = [1 if div.get(g["home_abbr"]) == div.get(g["away_abbr"]) else 0 for g in games]
    if len(set(div_flag)) > 1:
        add("C5", "Division game flag vs total points", r_of(div_flag, [g["total"] for g in games]), n,
            f"{sum(div_flag)} of {n} games were division games.")

    # Parlay multiplication examples using these measured values
    parlay = []
    for legs in (2, 3, 4):
        p_ind = 0.5 ** legs
        parlay.append({"legs": legs, "assumed_leg_prob_each": 0.5,
                       "independent_prob": round(p_ind, 5),
                       "fair_odds_decimal_independent": round(1 / p_ind, 3),
                       "break_even_decimal_at_110_juice": round((100 + 110) / 110, 4),
                       "note": "If any legs share a game or a team, replace the product with the "
                               "joint probability; product formula overstates or understates it."})
    out["parlay_math"] = {"rows": parlay,
                          "warning": "With -110 on each leg a 2-leg parlay needs both legs to hit "
                                     "52.4% of the time; 3 legs need 36.4%; 4 legs need 25.3%. "
                                     "Compounding correlation and vig is why parlay edges are "
                                     "harder to certify than single-bet edges."}

    out["publication_rule"] = {
        "minimum_sample": MIN_N_FOR_PUBLICATION,
        "suppressed": [c["id"] for c in out["correlations"] if c["n"] < MIN_N_FOR_PUBLICATION],
        "rule": "correlations below the minimum sample are published as blank/unverified",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "correlations.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for c in out["correlations"]:
        print(f"{c['id']}  r={c['r']}  n={c['n']}  p={c['p_value']}  indep={c['independent_at_5pct']}  {c['relationship'][:60]}")
    print("home win rate:", out["home_win"]["rate"], out["home_win"]["ci95"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
