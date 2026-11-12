#!/usr/bin/env python3
"""Recompute strategy gates and the standings correlations from the committed JSON.

Reads (committed, not fetched):
  data/model/strategies.json   leaderboard, gate results, pairwise correlations
  data/model/snapshot.json     2026 standings (32 rows, from nfl.com standings in the pipeline)
  data/correlations.json       the six published correlation values C-01..C-06

Writes:
  data/dashboard/recomputed.json

Gates G1 (provenance) and G2 (pre-specified rule) are documentary; they are reported as
'not recomputed' rather than re-judged here.
"""
import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data/dashboard/recomputed.json")


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy)


def main():
    strat = json.load(open(os.path.join(ROOT, "data/model/strategies.json"), encoding="utf-8"))
    snap = json.load(open(os.path.join(ROOT, "data/model/snapshot.json"), encoding="utf-8"))
    pub_corr = json.load(open(os.path.join(ROOT, "data/correlations.json"), encoding="utf-8"))

    pairs = strat["pairwise_correlation"]

    def pair_corr(a, b):
        key = f"{a} | {b}"
        if key in pairs:
            return pairs[key]["corr"], pairs[key]["n_overlap"]
        key = f"{b} | {a}"
        if key in pairs:
            return pairs[key]["corr"], pairs[key]["n_overlap"]
        return None, None

    names = [x["strategy"] for x in strat["leaderboard"]]
    out_strats = []
    for x in strat["leaderboard"]:
        seasons = x["by_season"]
        n_seasons = len(seasons)
        pos_seasons = sum(1 for v in seasons.values() if v["roi"] > 0)
        sum_n = sum(v["n"] for v in seasons.values())
        # Max |corr| across other strategies, using the published pairwise values
        corrs = []
        for other in names:
            if other == x["strategy"]:
                continue
            c, n_ov = pair_corr(x["strategy"], other)
            if c is not None:
                corrs.append((abs(c), other, n_ov))
        max_abs = max(corrs)[0] if corrs else None
        latest_roi = x["holdout_roi"]
        recomputed = {
            "G3": x["n_graded"] >= 100,
            "G4": (latest_roi is not None and latest_roi > 0),
            "G5": x["q_value"] is not None and x["q_value"] < 0.10,
            "G6": pos_seasons / n_seasons >= 0.60 if n_seasons else False,
            "G7": x["max_drawdown_units"] >= -25,
            "G8": (max_abs is not None and max_abs < 0.7),
        }
        published = {g["id"]: g["pass"] for g in x["gates"]}
        mismatches = [g for g in recomputed if recomputed[g] != published.get(g)]
        passed_recomputed = 2 + sum(1 for v in recomputed.values() if v)  # G1, G2 documentary, taken as published
        passed_published = sum(1 for g in x["gates"] if g["pass"])
        if passed_recomputed >= 8:
            status = "PASS"
        elif passed_recomputed >= 5:
            status = "WATCH"
        else:
            status = "FAIL"
        out_strats.append({
            "strategy": x["strategy"],
            "published_status": x["status"],
            "published_gates_passed": passed_published,
            "recomputed_gates_passed": passed_recomputed,
            "recomputed_status_from_rule": status,
            "n_graded": x["n_graded"],
            "sum_of_season_n": sum_n,
            "seasons": n_seasons,
            "seasons_positive": pos_seasons,
            "holdout_roi": latest_roi,
            "q_value": x["q_value"],
            "max_drawdown_units": x["max_drawdown_units"],
            "max_abs_corr_published_pairs": round(max_abs, 3) if max_abs is not None else None,
            "max_abs_corr_partner": max(corrs)[1] if corrs else None,
            "gate_mismatches_vs_published": mismatches,
            "status_rule_note": (
                "WATCH is assigned by gate count (5-7). A strategy can therefore be WATCH while failing G5 (significance)."
                if x["status"] == "WATCH" and not published.get("G5") else ""
            ),
        })

    # Standings correlations C-01..C-06 recomputed from the 32 standings rows in snapshot.json
    rows = snap["standings"]
    cols = {
        "w": [r["w"] for r in rows], "pf": [r["pf"] for r in rows], "pa": [r["pa"] for r in rows],
        "l": [r["l"] for r in rows], "pct": [r["pct"] for r in rows], "diff": [r["diff"] for r in rows],
        "gp": [r["w"] + r["l"] + r["t"] for r in rows],
    }
    cols["diff_pg"] = [r["diff"] / (r["w"] + r["l"] + r["t"]) for r in rows]
    recomp_corr = []
    specs = {
        "C-01": ("pf", "w"), "C-02": ("pa", "l"), "C-03": ("diff", "pct"),
        "C-04": ("pf", "pa"), "C-05": ("diff_pg", "pct"), "C-06": ("gp", "diff"),
    }
    published = {c["id"]: c for c in pub_corr}
    for cid, (a, b) in specs.items():
        r_val = pearson(cols[a], cols[b])
        pub = published.get(cid, {})
        recomp_corr.append({
            "id": cid,
            "pair": pub.get("pair"),
            "n": len(rows),
            "r_recomputed": round(r_val, 4),
            "r_published": pub.get("r"),
            "agrees_to_3dp": (pub.get("r") is not None and round(r_val, 3) == round(pub.get("r"), 3)),
            "note": "Pearson r over the 32 standings rows; C-05 uses net points per game (diff / games played).",
        })

    result = {
        "checked_on": "2026-11-12",
        "inputs": ["data/model/strategies.json", "data/model/snapshot.json", "data/correlations.json"],
        "strategies": out_strats,
        "standings_correlations": recomp_corr,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    for s in out_strats:
        print(s["strategy"][:40].ljust(41), s["published_status"], s["published_gates_passed"], "->", s["recomputed_status_from_rule"], s["recomputed_gates_passed"], "mismatch", s["gate_mismatches_vs_published"], "maxcorr", s["max_abs_corr_published_pairs"])
    for c in recomp_corr:
        print(c["id"], c["r_published"], c["r_recomputed"], c["agrees_to_3dp"])


if __name__ == "__main__":
    main()
