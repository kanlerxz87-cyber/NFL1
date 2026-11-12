#!/usr/bin/env python3
"""V3d - How good does a record have to be before luck is an unlikely explanation?

Pure arithmetic (exact binomial distribution); no data file is read.
A bet at -110 breaks even at 110/210 = 52.38% wins. For a given number of graded bets, the table
gives the smallest win count (and win rate) for which a strategy with NO edge at all (true win
rate exactly 52.38%) would do that well less than 5% of the time. If several strategies are
tried, the best of them gets lucky more easily, so the bar is raised (Sidak correction:
per-strategy alpha = 1 - 0.95**(1/K)).

Run from the repository root:  python3 referee/analysis/replicate_luck_thresholds.py
Output: referee/data/replication_luck_thresholds.json     (standard library only)
"""
import json
import math
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "replication_luck_thresholds.json")
P0 = 110.0 / 210.0


def pmf(n, k, p):
    return math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log(1 - p))


def min_wins(n, alpha, p=P0):
    tail = 0.0
    for k in range(n, -1, -1):
        tail += pmf(n, k, p)
        if tail > alpha:
            return k + 1 if k < n else None
    return 0


def main():
    sizes = [50, 100, 250, 500, 1000, 2500, 5000]
    tried = [1, 12, 50, 200]
    rows = []
    for n in sizes:
        row = {"graded_bets": n}
        for k in tried:
            alpha = 1 - 0.95 ** (1.0 / k)
            w = min_wins(n, alpha)
            row[f"tried_{k}"] = None if w is None else {"min_wins": w, "min_win_pct": round(100.0 * w / n, 2)}
        rows.append(row)
    # power: chance that a strategy with a real 55% win rate clears the single-strategy bar
    power = []
    for n in sizes:
        w = min_wins(n, 0.05)
        power.append({"graded_bets": n, "true_win_pct": 55.0,
                      "chance_to_clear_bar_pct": round(100.0 * sum(pmf(n, k, 0.55) for k in range(w, n + 1)), 1)})
    out = {"generated_by": "referee/analysis/replicate_luck_thresholds.py", "breakeven_win_pct": round(100 * P0, 2),
           "strategies_tried": tried, "rows": rows, "power_at_55pct": power}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    for r in rows:
        print(r["graded_bets"], [(k, r[f"tried_{k}"]["min_wins"], r[f"tried_{k}"]["min_win_pct"]) for k in tried])
    for p in power:
        print(p)


if __name__ == "__main__":
    main()
