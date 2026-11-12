#!/usr/bin/env python3
"""Compute Pearson correlation coefficients from the official standings data.

Input:  data/standings.json (32 rows transcribed from nfl.com, source S02)
Method: Pearson correlation coefficient as defined by the NIST/SEMATECH
        e-Handbook glossary (source S17). Pure arithmetic on published values;
        no value is inferred or imputed.

Output: data/correlations.json + data/derived_standings.json
Run:    python3 tools/compute_correlations.py
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")

standings = json.load(open(os.path.join(D, "standings.json"), encoding="utf-8"))


def pearson(xs, ys):
    n = len(xs)
    assert n == len(ys) and n > 1
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def col(name):
    return [r[name] for r in standings]


games = [r["w"] + r["l"] + r["t"] for r in standings]
derived = []
for r, g in zip(standings, games):
    derived.append(dict(
        code=r["code"], team=r["team"], games=g,
        pf_pg=round(r["pf"] / g, 3), pa_pg=round(r["pa"] / g, 3),
        net_pg=round(r["net"] / g, 3),
        method="PF / (W+L+T), PA / (W+L+T), NET PTS / (W+L+T)",
        src="S02", computed=True, retrieved="2026-11-12",
    ))
with open(os.path.join(D, "derived_standings.json"), "w", encoding="utf-8") as f:
    json.dump(derived, f, indent=2)
    f.write("\n")

PAIRS = [
    ("C-01", "Points For (PF) vs Wins (W)", "pf", "w"),
    ("C-02", "Points Against (PA) vs Losses (L)", "pa", "l"),
    ("C-03", "Net Points (NET) vs Winning Percentage (PCT)", "net", "pct"),
    ("C-04", "Points For (PF) vs Points Against (PA)", "pf", "pa"),
    ("C-05", "Net Points per Game vs Winning Percentage (PCT)", "derived:net_pg", "pct"),
    ("C-06", "Games Played vs Net Points (NET)", "derived:games", "net"),
]

rows = []
for cid, label, a, b in PAIRS:
    if a.startswith("derived:"):
        xs = [d[a.split(":")[1]] for d in derived]
    else:
        xs = col(a)
    ys = [float(v) if isinstance(v, str) else v for v in ([r[b] for r in standings] if not b.startswith("derived:") else [d[b.split(":")[1]] for d in derived])]
    xs = [float(v) if isinstance(v, str) else v for v in xs]
    r = pearson(xs, ys)
    rows.append(dict(id=cid, pair=label, x=a.replace("derived:", ""),
                     y=b.replace("derived:", ""), n=len(xs),
                     r=round(r, 4), method="Pearson correlation coefficient",
                     src="S17", data_src="S02", computed=True,
                     note="Correlation does not imply causality (NIST, S19).",
                     verified=True, retrieved="2026-11-12"))

with open(os.path.join(D, "correlations.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2)
    f.write("\n")
print("computed", len(rows), "correlations from", len(standings), "official standings rows")
for r in rows:
    print(" ", r["id"], r["pair"], "r =", r["r"])
