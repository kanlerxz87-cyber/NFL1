#!/usr/bin/env python3
"""V3b - Independently re-compute the numbers session 7600ed8b published in data/model/.

Read-only. Their JSON is read from a git ref (never from an edited copy) and every number that
depends only on the games file is re-derived here from this session's own audited snapshot
(referee/data/raw/games.csv), using code written without importing theirs.

Numbers that need play-by-play, injury or depth-chart files are listed as "not replicable here":
this session's sandbox cannot download those files, so it can neither confirm nor dispute them.

Run from the repository root:
    python3 referee/analysis/replicate_7600ed8b.py [git-ref]     (default: origin/arena/7600ed8b-nfl1)
Output: referee/data/replication_7600ed8b.json     (standard library only)
"""
import csv
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
REPO = os.path.join(ROOT, "..")
GAMES = os.path.join(ROOT, "data", "raw", "games.csv")
OUT = os.path.join(ROOT, "data", "replication_7600ed8b.json")
BREAKEVEN = 110.0 / 210.0
PAYOUT = 100.0 / 110.0


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, check=True).stdout


def num(x):
    return None if x in ("", "NA") else float(x)


def binom_tail(wins, n, p):
    """Exact P(X >= wins) for X ~ Binomial(n, p)."""
    lp, lq = math.log(p), math.log(1 - p)
    return sum(math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * lp + (n - k) * lq)
               for k in range(wins, n + 1))


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else None


def bh(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    prev = 1.0
    for rank, i in enumerate(reversed(order), start=1):
        q = min(prev, pvals[i] * m / (m - rank + 1))
        adj[i] = q
        prev = q
    return [min(1.0, max(0.0, q)) for q in adj]


def load_games():
    out = []
    with open(GAMES, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["game_type"] != "REG" or r["home_score"] in ("", "NA"):
                continue
            g = {"id": r["game_id"], "season": int(r["season"]), "week": int(r["week"]),
                 "margin": int(r["home_score"]) - int(r["away_score"]),
                 "total": int(r["home_score"]) + int(r["away_score"]),
                 "spread": num(r["spread_line"]), "total_line": num(r["total_line"]),
                 "home_rest": num(r["home_rest"]), "away_rest": num(r["away_rest"]), "div": r["div_game"] == "1"}
            out.append(g)
    return out


# ---- the eight rules, re-implemented from the published rule text and code ------------------
def favoured_by(g, side):          # points this side is favoured by (negative = underdog)
    return g["spread"] if side == "home" else -g["spread"]


def s04(g):
    for s in ("home", "away"):
        if g["div"] and favoured_by(g, s) <= -6.5:
            return ("ats", s)


def s05(g):
    for s in ("home", "away"):
        rest = g[f"{s}_rest"]
        if favoured_by(g, s) < 0 and rest is not None and rest <= 4:
            return ("ats", s)


def s06(g):
    if g["div"] and g["spread"] <= -6.5:
        return ("ats", "home")


def s07(g):
    if g["home_rest"] is not None and g["away_rest"] is not None and g["home_rest"] - g["away_rest"] >= 3:
        return ("ats", "home")


def s08(g):
    if g["away_rest"] is not None and g["away_rest"] >= 13:
        return ("ats", "home")


def s09(g):
    if g["spread"] >= 10:
        return ("ats", "home")


def s10(g):
    if g["total_line"] is not None and g["total_line"] <= 41:
        return ("tot", "over")


def s11(g):
    if g["total_line"] is not None and g["div"] and g["total_line"] >= 47:
        return ("tot", "under")


RULES = {"S04": s04, "S05": s05, "S06": s06, "S07": s07, "S08": s08, "S09": s09, "S10": s10, "S11": s11}


def grade(g, kind, side):
    if kind == "ats":
        v = g["margin"] - g["spread"]
        if v == 0:
            return "push"
        return "win" if (v > 0) == (side == "home") else "loss"
    v = g["total"] - g["total_line"]
    if v == 0:
        return "push"
    return "win" if (v > 0) == (side == "over") else "loss"


def run_rule(hist, rule):
    res = {}
    for g in hist:
        pick = rule(g)
        if pick:
            res[g["id"]] = grade(g, *pick)
    w = sum(v == "win" for v in res.values())
    l = sum(v == "loss" for v in res.values())
    p = sum(v == "push" for v in res.values())
    n = w + l
    return {"n_graded": n, "wins": w, "losses": l, "pushes": p, "win_pct": round(w / n, 4),
            "roi": round((w * PAYOUT - l) / n, 4), "units": round(w * PAYOUT - l, 2),
            "p_value": round(binom_tail(w, n, BREAKEVEN), 4), "_bets": res}


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/arena/7600ed8b-nfl1"
    sha = git("rev-parse", ref).strip()
    strat = json.loads(git("show", f"{ref}:data/model/strategies.json"))
    lines = json.loads(git("show", f"{ref}:data/model/lines.json"))

    games = load_games()
    lo = strat["window"]["start_season"]
    hist = [g for g in games if g["season"] >= lo and g["spread"] is not None]

    rows = []

    def add(section, item, published, ours, tol=0.0, note=""):
        if ours is None:
            status = "not replicable here"
        elif published is None:
            status = "nothing published"
        elif isinstance(published, (int, float)) and isinstance(ours, (int, float)):
            status = "replicated" if abs(published - ours) <= tol + 1e-9 else "NOT replicated"
        else:
            status = "replicated" if published == ours else "NOT replicated"
        rows.append({"section": section, "item": item, "published": published, "referee": ours, "tolerance": tol,
                     "status": status, "note": note})

    # ---- window and parlay correlation ----------------------------------------------------
    add("Backtest window", f"Regular-season games with a closing spread, {lo}-2026", strat["window"]["games_with_closing_spread"], len(hist))
    par = strat.get("parlay", {})
    add("Same-game correlation", "Games used", par.get("n_games"), len(hist))
    add("Same-game correlation", "Correlation of final margin with final total", par.get("corr_margin_vs_total"),
        round(pearson([g["margin"] for g in hist], [g["total"] for g in hist]), 3), 0.0005)
    h2 = [g for g in hist if g["total_line"] is not None]
    hc = [1.0 if g["margin"] - g["spread"] > 0 else 0.0 for g in h2]
    ov = [1.0 if g["total"] > g["total_line"] else 0.0 for g in h2]
    add("Same-game correlation", "Phi: home team covers vs game goes over", par.get("phi_home_cover_vs_over"),
        round(pearson(hc, ov), 4), 0.00005)

    # ---- lines.json: sign convention and market error --------------------------------------
    sc = lines.get("sign_convention_check", {})
    add("Line sign convention", "Games used", sc.get("n_games"), len(hist))
    add("Line sign convention", "Correlation of closing spread with home margin", sc.get("corr_market_line_vs_home_margin"),
        round(pearson([g["spread"] for g in hist], [float(g["margin"]) for g in hist]), 3), 0.0005)
    windows = {"train 2024": lambda g: g["season"] == 2024 and g["week"] >= 2,
               "validation 2025": lambda g: g["season"] == 2025, "test 2026": lambda g: g["season"] == 2026}
    for c in lines.get("calibration", []):
        sel = [g for g in games if windows.get(c["label"], lambda g: False)(g) and g["spread"] is not None]
        wk = " (weeks 2-18; their model has no rating for week 1)" if c["label"] == "train 2024" else ""
        add("Market error (closing line)", f"{c['label']}{wk}: games", c["n"], len(sel))
        if sel:
            add("Market error (closing line)", f"{c['label']}: spread mean absolute error, points", c["spread_mae_market"],
                round(sum(abs(g["margin"] - g["spread"]) for g in sel) / len(sel), 3), 0.0005)
            add("Market error (closing line)", f"{c['label']}: total mean absolute error, points", c["total_mae_market"],
                round(sum(abs(g["total"] - g["total_line"]) for g in sel) / len(sel), 3), 0.0005)
        add("Own-line model error", f"{c['label']}: spread mean absolute error of their model, points", c["spread_mae_model"], None,
            note="Needs play-by-play data (EPA ratings). Not downloadable in this session's sandbox.")
        add("Own-line model error", f"{c['label']}: total mean absolute error of their model, points", c["total_mae_model"], None,
            note="Needs play-by-play data (EPA ratings). Not downloadable in this session's sandbox.")

    # ---- strategies -------------------------------------------------------------------------
    ours = {}
    board = {r["strategy"]: r for r in strat["leaderboard"]}
    strategy_rows = []
    for name, pub in board.items():
        key = name.split()[0]
        if key in RULES:
            mine = run_rule(hist, RULES[key])
            ours[name] = mine
            for f, tol in (("n_graded", 0), ("wins", 0), ("losses", 0), ("pushes", 0), ("win_pct", 0.00005), ("roi", 0.00005),
                           ("units", 0.005), ("p_value", 0.00011)):
                add(f"Strategy {key}", f"{name}: {f}", pub.get(f), mine[f], tol)
            ok = all(r["status"] == "replicated" for r in rows if r["section"] == f"Strategy {key}")
            strategy_rows.append({"strategy": name, "window": pub.get("window"), "published_status": pub.get("status"),
                                  "published_record": f"{pub.get('wins')}-{pub.get('losses')}-{pub.get('pushes')}",
                                  "referee_record": f"{mine['wins']}-{mine['losses']}-{mine['pushes']}",
                                  "published_win_pct": pub.get("win_pct"), "referee_win_pct": mine["win_pct"],
                                  "published_roi": pub.get("roi"), "referee_roi": mine["roi"],
                                  "published_p": pub.get("p_value"), "referee_p": mine["p_value"],
                                  "result": "replicated" if ok else "NOT replicated", "reason": ""})
        else:
            reason = "Needs their play-by-play ratings or injury files, which this session's sandbox cannot download."
            add(f"Strategy {key}", f"{name}: record {pub.get('wins')}-{pub.get('losses')}-{pub.get('pushes')}", pub.get("win_pct"), None, note=reason)
            strategy_rows.append({"strategy": name, "window": pub.get("window"), "published_status": pub.get("status"),
                                  "published_record": f"{pub.get('wins')}-{pub.get('losses')}-{pub.get('pushes')}", "referee_record": None,
                                  "published_win_pct": pub.get("win_pct"), "referee_win_pct": None, "published_roi": pub.get("roi"),
                                  "referee_roi": None, "published_p": pub.get("p_value"), "referee_p": None,
                                  "result": "not replicable here", "reason": reason})

    # ---- multiple-testing correction: BH q-values recomputed from p-values ------------------
    names = list(board)
    pv = [ours[n]["p_value"] if n in ours else (board[n].get("p_value") or 1.0) for n in names]
    for n, q in zip(names, bh(pv)):
        add("Multiple-testing correction", f"{n.split()[0]}: Benjamini-Hochberg q-value", board[n].get("q_value"), round(q, 4), 0.00011,
            note="" if n in ours else "Uses their published p-value for this strategy (not replicable here).")

    # ---- pairwise correlation of bet returns -------------------------------------------------
    for pair, v in strat.get("pairwise_correlation", {}).items():
        a, b = pair.split(" | ")
        if a in ours and b in ours:
            ra = {k: (PAYOUT if x == "win" else -1.0) for k, x in ours[a]["_bets"].items() if x != "push"}
            rb = {k: (PAYOUT if x == "win" else -1.0) for k, x in ours[b]["_bets"].items() if x != "push"}
            common = sorted(set(ra) & set(rb))
            add("Correlation between strategies", f"{a.split()[0]} x {b.split()[0]}: overlapping graded bets", v.get("n_overlap"), len(common))
            c = pearson([ra[k] for k in common], [rb[k] for k in common]) if len(common) >= 3 else None
            add("Correlation between strategies", f"{a.split()[0]} x {b.split()[0]}: correlation of returns", v.get("corr"),
                None if c is None else round(c, 3), 0.0005)
        else:
            add("Correlation between strategies", f"{a.split()[0]} x {b.split()[0]}: correlation of returns", v.get("corr"), None,
                note="At least one side needs data this session cannot download.")

    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    out = {"generated_by": "referee/analysis/replicate_7600ed8b.py", "owner_session": "7600ed8b",
           "ref": ref, "commit": sha, "their_generated_at": strat.get("generated_at"),
           "files_read": ["data/model/strategies.json", "data/model/lines.json"],
           "counts": counts, "strategies": strategy_rows, "rows": rows,
           "gate_definitions": strat.get("gate_definitions"), "rewards": strat.get("rewards")}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print("ref", ref, sha[:10], "generated", strat.get("generated_at"))
    print("counts", counts)
    for r in rows:
        if r["status"] == "NOT replicated":
            print("  NOT REPLICATED:", r["section"], "|", r["item"], "| published", r["published"], "| referee", r["referee"])
    for s in strategy_rows:
        print(" ", s["strategy"][:48].ljust(48), s["published_record"], s["referee_record"], s["result"])


if __name__ == "__main__":
    main()
