#!/usr/bin/env python3
"""V2 - Audit the betting-line columns of nflverse/nfldata games.csv.

There is no official NFL source for betting lines, so nothing here can be "verified".
The script measures (a) coverage, (b) internal consistency, (c) agreement with closing_lines.csv
from the same repository, and (d) market benchmarks that any originated line or strategy would
have to beat. Every number it produces is derived from unverified line data.

Sign convention (documented in DATASETS.md of the source repo): spread_line > 0 means the home
team was favoured by that many points; result = home score - away score.

Run from the repository root:  python3 referee/analysis/lines_audit.py
Output: referee/data/lines_audit.json     (standard library only)
"""
import collections
import csv
import json
import math
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
GAMES = os.path.join(ROOT, "data", "raw", "games.csv")
CLOSING = os.path.join(ROOT, "data", "raw", "closing_lines.csv")
OUT = os.path.join(ROOT, "data", "lines_audit.json")


def has(r, f):
    return r[f] not in ("", "NA")


def implied(american):
    a = float(american)
    return 100.0 / (a + 100.0) if a > 0 else -a / (-a + 100.0)


def pct(a, b):
    return round(100.0 * a / b, 2) if b else None


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy)


def check(name, description, items, bad):
    bad = list(bad)
    return {"check": name, "description": description, "checked": len(items), "violations": len(bad),
            "examples": bad[:8]}


def benchmarks(rs):
    """Market benchmarks for a list of played games that have spread_line and total_line."""
    n = len(rs)
    if not n:
        return None
    hc = sum(1 for r in rs if r["_res"] > r["_sp"])
    ps = sum(1 for r in rs if r["_res"] == r["_sp"])
    fav = [r for r in rs if r["_sp"] != 0]
    fc = sum(1 for r in fav if (r["_res"] - r["_sp"]) * r["_sp"] > 0)
    fp = sum(1 for r in fav if r["_res"] == r["_sp"])
    fw = sum(1 for r in fav if r["_res"] * r["_sp"] > 0)
    ft = sum(1 for r in fav if r["_res"] == 0)
    ov = sum(1 for r in rs if r["_tot"] > r["_tl"])
    tp = sum(1 for r in rs if r["_tot"] == r["_tl"])
    return {
        "games": n,
        "home_cover_pct": pct(hc, n - ps), "spread_push_pct": pct(ps, n),
        "favorite_cover_pct": pct(fc, len(fav) - fp), "favorite_win_pct": pct(fw, len(fav) - ft),
        "over_pct": pct(ov, n - tp), "total_push_pct": pct(tp, n),
        "spread_mae": round(sum(abs(r["_res"] - r["_sp"]) for r in rs) / n, 3),
        "total_mae": round(sum(abs(r["_tot"] - r["_tl"]) for r in rs) / n, 3),
        "home_margin_mean": round(sum(r["_res"] for r in rs) / n, 3),
        "spread_mean": round(sum(r["_sp"] for r in rs) / n, 3),
        "naive_margin_mae": round(sum(abs(r["_res"]) for r in rs) / n, 3),
    }


def main():
    with open(GAMES, newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if has(r, "home_score")]
    for r in rows:
        r["_res"], r["_tot"] = int(r["result"]), int(r["total"])
        r["_sp"] = float(r["spread_line"]) if has(r, "spread_line") else None
        r["_tl"] = float(r["total_line"]) if has(r, "total_line") else None
        r["_season"] = int(r["season"])

    # ---- coverage ------------------------------------------------------------------------
    fields = ["spread_line", "total_line", "home_moneyline", "away_moneyline",
              "home_spread_odds", "away_spread_odds", "over_odds", "under_odds"]
    cov = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        cov[r["_season"]]["played"] += 1
        for f in fields:
            cov[r["_season"]][f] += has(r, f)
    coverage = [{"season": s, "played": c["played"], **{f: c[f] for f in fields}} for s, c in sorted(cov.items(), reverse=True)]

    # ---- consistency ---------------------------------------------------------------------
    lined = [r for r in rows if r["_sp"] is not None and r["_tl"] is not None]
    ml = [r for r in rows if has(r, "home_moneyline") and has(r, "away_moneyline")]
    so = [r for r in rows if has(r, "home_spread_odds") and has(r, "away_spread_odds")]
    to = [r for r in rows if has(r, "over_odds") and has(r, "under_odds")]
    gid = lambda r, extra="": f"{r['game_id']}{extra}"
    checks = [
        check("C1 spread on half-point grid", "spread_line x 2 is a whole number", lined,
              (gid(r, f" spread={r['spread_line']}") for r in lined if (r["_sp"] * 2) % 1 != 0)),
        check("C2 total on half-point grid", "total_line x 2 is a whole number", lined,
              (gid(r, f" total={r['total_line']}") for r in lined if (r["_tl"] * 2) % 1 != 0)),
        check("C3 spread within 0-28 points", "absolute spread_line is at most 28", lined,
              (gid(r, f" spread={r['spread_line']}") for r in lined if abs(r["_sp"]) > 28)),
        check("C4 total within 28-65 points", "total_line is between 28 and 65", lined,
              (gid(r, f" total={r['total_line']}") for r in lined if not 28 <= r["_tl"] <= 65)),
        check("C5 moneyline favourite agrees with spread sign",
              "when spread_line is not 0, the team it favours has the lower (more negative) moneyline", [r for r in ml if r["_sp"]],
              (gid(r, f" spread={r['spread_line']} ml={r['home_moneyline']}/{r['away_moneyline']}") for r in ml
               if r["_sp"] and (float(r["home_moneyline"]) - float(r["away_moneyline"])) * r["_sp"] > 0)),
        check("C6 moneyline pair has a bookmaker margin of 0-12%",
              "implied probabilities of the two moneylines sum to more than 1.00 and at most 1.12", ml,
              (gid(r, f" sum={implied(r['home_moneyline']) + implied(r['away_moneyline']):.3f}") for r in ml
               if not 1.0 < implied(r["home_moneyline"]) + implied(r["away_moneyline"]) <= 1.12)),
        check("C7 spread-odds pair has a bookmaker margin of 0-12%",
              "implied probabilities of the two spread prices sum to more than 1.00 and at most 1.12", so,
              (gid(r, f" sum={implied(r['home_spread_odds']) + implied(r['away_spread_odds']):.3f}") for r in so
               if not 1.0 < implied(r["home_spread_odds"]) + implied(r["away_spread_odds"]) <= 1.12)),
        check("C8 total-odds pair has a bookmaker margin of 0-12%",
              "implied probabilities of the over and under prices sum to more than 1.00 and at most 1.12", to,
              (gid(r, f" sum={implied(r['over_odds']) + implied(r['under_odds']):.3f}") for r in to
               if not 1.0 < implied(r["over_odds"]) + implied(r["under_odds"]) <= 1.12)),
    ]

    # ---- cross-file agreement with closing_lines.csv --------------------------------------
    by_id = {r["game_id"]: r for r in rows}
    cl_spread, cl_total, cl_ml = {}, {}, {}
    with open(CLOSING, newline="") as fh:
        for c in csv.DictReader(fh):
            g = by_id.get(c["alt_game_id"])
            if not g:
                continue
            if c["type"] == "SPREAD" and c["side"] == g["home_team"] and c["line"] not in ("", "NA"):
                cl_spread[c["alt_game_id"]] = -float(c["line"])  # home line -3 means home favoured by 3
            elif c["type"] == "TOTAL" and c["side"] == "Over" and c["line"] not in ("", "NA"):
                cl_total[c["alt_game_id"]] = float(c["line"])
            elif c["type"] == "MONEYLINE" and c["side"] == g["home_team"] and c["odds"] not in ("", "NA"):
                cl_ml[c["alt_game_id"]] = float(c["odds"])

    def agree(pairs):
        n = len(pairs)
        return {"games_in_both": n, "exact": sum(1 for a, b in pairs if a == b),
                "within_half_point": sum(1 for a, b in pairs if abs(a - b) <= 0.5),
                "within_one_point": sum(1 for a, b in pairs if abs(a - b) <= 1.0),
                "exact_pct": pct(sum(1 for a, b in pairs if a == b), n)}
    cross = {
        "spread": agree([(by_id[g]["_sp"], v) for g, v in cl_spread.items() if by_id[g]["_sp"] is not None]),
        "total": agree([(by_id[g]["_tl"], v) for g, v in cl_total.items() if by_id[g]["_tl"] is not None]),
        "home_moneyline": agree([(float(by_id[g]["home_moneyline"]), v) for g, v in cl_ml.items() if has(by_id[g], "home_moneyline")]),
        "seasons_in_closing_file": sorted({int(g[:4]) for g in cl_spread}),
    }
    cross["spread_examples_differing"] = [f"{g} games.csv={by_id[g]['_sp']} closing_lines.csv={v}" for g, v in sorted(cl_spread.items())
                                          if by_id[g]["_sp"] is not None and by_id[g]["_sp"] != v][:8]

    # ---- sign-convention evidence ----------------------------------------------------------
    r_spread = pearson([r["_sp"] for r in lined], [float(r["_res"]) for r in lined])
    r_total = pearson([r["_tl"] for r in lined], [float(r["_tot"]) for r in lined])

    # ---- benchmarks ------------------------------------------------------------------------
    eras = [("1999-2005", 1999, 2005), ("2006-2014", 2006, 2014), ("2015-2020", 2015, 2020),
            ("2021-2025", 2021, 2025), ("2026 (through Week 9)", 2026, 2026), ("All seasons", 1999, 2026)]
    era_rows = []
    for name, a, b in eras:
        bm = benchmarks([r for r in lined if a <= r["_season"] <= b])
        era_rows.append({"era": name, **bm})
    season_rows = []
    for s in sorted({r["_season"] for r in lined}, reverse=True):
        season_rows.append({"season": s, **benchmarks([r for r in lined if r["_season"] == s])})

    # moneyline calibration (two-way de-vig by normalisation), favourite side only
    bins = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 0.75), (0.75, 0.80), (0.80, 0.90), (0.90, 1.001)]
    cal = []
    obs = []
    for r in ml:
        ph, pa = implied(r["home_moneyline"]), implied(r["away_moneyline"])
        ph = ph / (ph + pa)
        if r["_res"] == 0:
            continue
        p_fav, won = (ph, r["_res"] > 0) if ph >= 0.5 else (1 - ph, r["_res"] < 0)
        obs.append((p_fav, won))
    for lo, hi in bins:
        sel = [(p, w) for p, w in obs if lo <= p < hi]
        if sel:
            cal.append({"bin": f"{int(lo*100)}-{min(int(hi*100),100)}%", "games": len(sel),
                        "mean_market_probability_pct": round(100 * sum(p for p, _ in sel) / len(sel), 2),
                        "actual_win_pct": pct(sum(1 for _, w in sel if w), len(sel))})
    brier = sum((p - (1.0 if w else 0.0)) ** 2 for p, w in obs) / len(obs)

    out = {
        "generated_by": "referee/analysis/lines_audit.py",
        "status": "UNVERIFIED - no official source exists for betting lines",
        "games_played": len(rows), "games_with_spread_and_total": len(lined), "games_with_moneylines": len(ml),
        "coverage": coverage, "checks": checks, "cross_file": cross,
        "sign_convention": {"pearson_spread_line_vs_result": round(r_spread, 4), "pearson_total_line_vs_total": round(r_total, 4)},
        "benchmarks_by_era": era_rows, "benchmarks_by_season": season_rows,
        "moneyline_calibration": {"games": len(obs), "brier_score": round(brier, 4), "bins": cal},
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)

    print("played", len(rows), "with spread+total", len(lined), "with ML", len(ml))
    for c in checks:
        print(f"{c['check']}: {c['violations']}/{c['checked']}  {c['examples'][:4]}")
    print("cross-file", json.dumps({k: v for k, v in cross.items() if k != 'spread_examples_differing'}))
    print(cross["spread_examples_differing"][:5])
    print("pearson spread~result", round(r_spread, 4), "total~total", round(r_total, 4))
    for e in era_rows:
        print(e)
    print("calibration brier", round(brier, 4))
    for c in cal:
        print(c)


if __name__ == "__main__":
    main()
