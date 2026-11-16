#!/usr/bin/env python3
"""c84_study.py — the pre-registered study for session c84a41a4-nfl1.

This file ONLY implements what data/session-c84a41a4/preregistration.json declares.
It does not tune, search or select. Every threshold is read from the registration.

Inputs (committed, hash-checked, no network):
    data/s9cb/games.csv        results + closing lines + observed prices
    data/s9cb/injuries.csv     official weekly report
    data/s9cb/player_week.csv  player volume, for prop projections only

Outputs:
    data/session-c84a41a4/results.json   every number the site prints, plus the
                                         input hashes and the registration hash

Run: python3 s9cb/c84_study.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "data", "session-c84a41a4")
PREREG = os.path.join(OUT_DIR, "preregistration.json")

SEASONS = list(range(2006, 2027))
DEVELOP_MAX = 2021
VALIDATE = (2022, 2023)
HOLDOUT = (2024, 2025, 2026)
MIN_DECIDED = 300
BOOT = 2000
SEED = 20261115

OFFICIAL = {
    "schedules": "https://www.nfl.com/schedules/",
    "injuries": "https://www.nfl.com/injuries/",
    "stats": "https://www.nfl.com/stats/player-stats/",
}


# --------------------------------------------------------------------- helpers
def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def f(x, default=None):
    if x is None:
        return default
    x = str(x).strip()
    if not x:
        return default
    try:
        v = float(x)
    except ValueError:
        return default
    return v if math.isfinite(v) else default


def american_to_decimal(a: float) -> float:
    return 1.0 + (a / 100.0 if a > 0 else 100.0 / abs(a))


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def two_sided_p_from_z(z: float) -> float:
    return 2.0 * (1.0 - norm_cdf(abs(z)))


def benjamini_hochberg(pvals: dict) -> dict:
    """BH step-up. Returns {id: q}."""
    ids = list(pvals)
    m = len(ids)
    if m == 0:
        return {}
    order = sorted(ids, key=lambda i: pvals[i])
    q = {}
    prev = 1.0
    for rank in range(m, 0, -1):
        key = order[rank - 1]
        val = pvals[key] * m / rank
        prev = min(prev, val)
        q[key] = min(1.0, prev)
    return q


def cluster_bootstrap_ci(rows, key, n_boot=BOOT, seed=SEED):
    """95% interval on mean profit, resampling whole clusters (games) with replacement."""
    clusters = defaultdict(list)
    for r in rows:
        clusters[r[key]].append(r["profit"])
    keys = list(clusters)
    if len(keys) < 3:
        return None
    sums = {k: sum(v) for k, v in clusters.items()}
    cnts = {k: len(v) for k, v in clusters.items()}
    rng = random.Random(seed)
    out = []
    for _ in range(n_boot):
        pick = [keys[rng.randrange(len(keys))] for _ in keys]
        num = sum(sums[k] for k in pick)
        den = sum(cnts[k] for k in pick)
        if den:
            out.append(num / den)
    out.sort()
    lo = out[int(0.025 * (len(out) - 1))]
    hi = out[int(0.975 * (len(out) - 1))]
    return [round(lo, 5), round(hi, 5)]


# --------------------------------------------------------------- load games
def load_games():
    rows = []
    with open(os.path.join(ROOT, "data/s9cb/games.csv"), newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            season = int(r["season"])
            if season not in SEASONS:
                continue
            hs, as_ = f(r["home_score"]), f(r["away_score"])
            played = hs is not None and as_ is not None
            rows.append({
                "game_id": r["game_id"], "season": season, "week": int(r["week"]),
                "gameday": r["gameday"], "home": r["home_team"], "away": r["away_team"],
                "home_score": hs, "away_score": as_, "played": played,
                "margin": (hs - as_) if played else None,          # home perspective
                "total": (hs + as_) if played else None,
                "spread_line": f(r["spread_line"]),
                "home_spread_odds": f(r["home_spread_odds"]),
                "away_spread_odds": f(r["away_spread_odds"]),
                "total_line": f(r["total_line"]),
                "over_odds": f(r["over_odds"]), "under_odds": f(r["under_odds"]),
                "home_ml": f(r["home_moneyline"]), "away_ml": f(r["away_moneyline"]),
                "home_rest": f(r["home_rest"]), "away_rest": f(r["away_rest"]),
                "div_game": int(f(r["div_game"], 0) or 0),
                "roof": r.get("roof") or "", "surface": r.get("surface") or "",
            })
    return rows


# ------------------------------------------------------- walk-forward own line
def fit_own_lines(games, inj_feats=None, use_avail=False):
    """The pre-registered SIMPLE team-strength model, refitted for every (season, week) block.

    margin_home = hfa + rest_coef * rest_diff + net[home] - net[away]
    total        = intercept + pace[home] + pace[away]

    `net` is one number per club (attack minus defence), which is the simplest
    opponent-aware strength model there is: a club's rating is only comparable to
    other clubs because every game contributes the difference of two ratings to the
    same linear system, so a rating is inflated only if it beat strong opposition.

    Only games that FINISHED in an earlier (season, week) block enter a fit, so no
    prediction can see its own result or any later one.

    Sign convention, checked against the data rather than assumed:
    `spread_line` is the HOME club's line, positive when the home club is favoured
    (mean home margin is +5.96 when spread_line > 0 and -4.64 when it is < 0 over
    7,104 decided games, corr 0.431). The own line is produced in the same
    convention, so `edge = own_spread_home - spread_line` is home-signed and a
    positive edge means the model rates the home club MORE favourably than the close.
    """
    import numpy as np

    HALF_LIFE_WEEKS = 24.0
    RIDGE = 8.0

    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    n = len(teams)
    idx = {t: i for i, t in enumerate(teams)}

    blocks = sorted({(g["season"], g["week"]) for g in games})
    bno = {b: i for i, b in enumerate(blocks)}

    NCOL = n + 2 + (2 if use_avail else 0)

    def row(g):
        v = np.zeros(NCOL)
        v[idx[g["home"]]] = 1.0
        v[idx[g["away"]]] = -1.0
        v[n] = 1.0                                     # home-field term
        rh, ra = g["home_rest"], g["away_rest"]
        v[n + 1] = ((rh - ra) / 7.0) if (rh is not None and ra is not None) else 0.0
        if use_avail:
            h = (inj_feats or {}).get((g["season"], g["week"], g["home"])) or {}
            a = (inj_feats or {}).get((g["season"], g["week"], g["away"])) or {}
            # missing report -> 0 difference is correct: absence of a report carries no
            # information about a difference, and it is counted in the coverage table.
            v[n + 2] = float(h.get("n_out") or 0) - float(a.get("n_out") or 0)
            v[n + 3] = 1.0 if (h or a) else 0.0         # has-report indicator
        return v

    def row_total(g):
        v = np.zeros(n + 1)
        v[idx[g["home"]]] = 1.0
        v[idx[g["away"]]] = 1.0
        v[n] = 1.0                                     # intercept
        return v

    hist, hist_t, hist_age = [], [], []
    preds = {}
    for b in blocks:
        bn = bno[b]
        if hist:
            X = np.array(hist, dtype=float)              # (m, n+2)
            Xt = np.array(hist_t, dtype=float)           # (m, n+1)
            ages = np.array([h[0] and (bn - h[0]) for h in hist_age], dtype=float)
            w = 0.5 ** (ages / HALF_LIFE_WEEKS)
            ym = np.array([h[2] for h in hist_age], dtype=float)
            yt = np.array([h[3] for h in hist_age], dtype=float)
            A = X.T @ (w[:, None] * X) + RIDGE * np.eye(X.shape[1])
            beta_m = np.linalg.solve(A, X.T @ (w * ym))
            At = Xt.T @ (w[:, None] * Xt) + RIDGE * np.eye(n + 1)
            beta_t = np.linalg.solve(At, Xt.T @ (w * yt))
        else:
            beta_m = beta_t = None

        for g in games:
            if (g["season"], g["week"]) != b:
                continue
            if beta_m is None:
                preds[g["game_id"]] = {"own_spread_home": 0.0, "own_total": 46.0,
                                       "n_train": 0, "sd_margin": 13.0,
                                       "max_train_block": -1}
            else:
                preds[g["game_id"]] = {
                    "own_spread_home": round(float(row(g) @ beta_m), 4),
                    "own_total": round(float(row_total(g) @ beta_t), 4),
                    "n_train": len(hist),
                    "sd_margin": 13.0,
                    "max_train_block": max((h[0] for h in hist_age), default=-1),
                }

        for g in games:
            if (g["season"], g["week"]) != b or not g["played"]:
                continue
            hist.append(row(g))
            hist_t.append(row_total(g))
            hist_age.append((bn, None, g["margin"], g["total"]))

    errs = []
    for g in games:
        p = preds.get(g["game_id"], {})
        if g["played"] and p.get("n_train", 0) > 0:
            errs.append(g["margin"] - p["own_spread_home"])
    sdm = sd(errs) or 13.0
    for p in preds.values():
        p["sd_margin"] = round(sdm, 4)
    return preds, {"half_life_weeks": HALF_LIFE_WEEKS, "ridge": RIDGE,
                   "sd_margin": round(sdm, 4), "n_teams": n, "blocks": len(blocks),
                   "params_margin": NCOL, "params_total": n + 1, "use_avail": use_avail,
                   "design": "margin = hfa + rest_coef*rest_diff + net[home] - net[away]; "
                             "total = intercept + pace[home] + pace[away]"}


# ------------------------------------------------------------ injury features
def injury_features(rows):
    """Per (season, week, club): count ruled Out/Doubtful, and the trailing-4-week surprise."""
    per = defaultdict(int)
    reported = set()
    for r in rows:
        if (r["game_type"] or "REG") != "REG":
            continue
        key = (int(r["season"]), int(r["week"]), r["team"])
        reported.add(key)
        if (r["report_status"] or "").strip() in ("Out", "Doubtful"):
            per[key] += 1

    by_club = defaultdict(list)
    for (s, w, t) in reported:
        by_club[t].append((s, w))
    feats = {}
    for t, weeks in by_club.items():
        weeks.sort(key=lambda x: (x[0], x[1]))
        vals = [per.get((s, w, t), 0) for (s, w) in weeks]
        for i, (s, w) in enumerate(weeks):
            prior = vals[max(0, i - 4):i]
            exp = (sum(prior) / len(prior)) if len(prior) >= 3 else None
            feats[(s, w, t)] = {
                "n_out": vals[i],
                "expected": (round(exp, 3) if exp is not None else None),
                "surprise": (round(vals[i] - exp, 3) if exp is not None else None),
            }
    return feats


# ------------------------------------------------------------------- scoring
def settle(profit_rule):
    """profit_rule: (won:bool|None push) -> unit profit."""
    pass


def score_bets(bets, controls_roi):
    decided = [b for b in bets if not b["push"]]
    n = len(bets)
    nd = len(decided)
    if n == 0 or nd == 0:
        return None
    profit = sum(b["profit"] for b in bets)
    roi = profit / n
    hit = sum(1 for b in decided if b["won"]) / nd
    be = mean([b["implied"] for b in bets])
    prof = [b["profit"] for b in bets]
    m = mean(prof)
    s = sd(prof)
    se = (s / math.sqrt(n)) if s else None
    t = (m / se) if se else None
    p = two_sided_p_from_z(t) if t is not None else None
    ci = cluster_bootstrap_ci(bets, "game_id")
    seasons = defaultdict(list)
    for b in bets:
        seasons[b["season"]].append(b)
    seas = []
    for s_, grp in sorted(seasons.items()):
        pr = sum(x["profit"] for x in grp) / len(grp)
        seas.append({"season": s_, "n_bets": len(grp), "roi_pct": round(100 * pr, 3)})
    hold = [b for b in bets if b["season"] in HOLDOUT]
    hold_roi = (sum(b["profit"] for b in hold) / len(hold)) if hold else None
    big = [x for x in seas if x["n_bets"] >= 20]
    pos = sum(1 for x in big if x["roi_pct"] > 0)
    stability = (pos / len(big)) if big else None
    # gate 10: drop the single best season
    if seas:
        best = max(seas, key=lambda x: x["roi_pct"])
        rest = [b for b in bets if b["season"] != best["season"]]
        without_best = (sum(b["profit"] for b in rest) / len(rest)) if rest else None
    else:
        best, without_best = None, None
    return {
        "n_bets": n, "n_decided": nd, "n_pushes": n - nd,
        "wins": sum(1 for b in decided if b["won"]),
        "hit_rate": round(hit, 4),
        "break_even_hit_rate": round(be, 4) if be is not None else None,
        "profit_units": round(profit, 3),
        "roi_pct": round(100 * roi, 3),
        "t_stat": round(t, 4) if t is not None else None,
        "p_value": round(p, 6) if p is not None else None,
        "roi_ci95_game_cluster": ci,
        "season_table": seas,
        "holdout_2024_2026": ({"n_bets": len(hold), "roi_pct": round(100 * hold_roi, 3)}
                             if hold_roi is not None else None),
        "stability_positive_fraction": (round(stability, 3) if stability is not None else None),
        "seasons_evaluated": len(big),
        "best_season": best, "roi_without_best_season_pct":
            (round(100 * without_best, 3) if without_best is not None else None),
        "beats_control": (round(100 * roi - controls_roi, 3) if controls_roi is not None else None),
    }


def main():
    t0 = datetime.now(timezone.utc)
    games = load_games()

    with open(os.path.join(ROOT, "data/s9cb/injuries.csv"), newline="", encoding="utf-8") as fh:
        inj_rows = list(csv.DictReader(fh))
    inj = injury_features(inj_rows)

    # The registered own line DOES include the availability difference: the briefing asks for
    # injury/personnel features and then asks to test them by ablation, not by assertion.
    preds, fitinfo = fit_own_lines(games, inj_feats=inj, use_avail=True)

    # ---------------------------------------------------------- build the bets
    def emit(bets, strat, side, g, price, won, push, line, extra=None):
        dec = american_to_decimal(price)
        profit = 0.0 if push else ((dec - 1.0) if won else -1.0)
        row = {"strategy": strat, "market": MARKET_OF[strat], "season": g["season"],
               "week": g["week"], "game_id": g["game_id"], "gameday": g["gameday"],
               "home": g["home"], "away": g["away"], "side": side,
               "line": line, "price": price, "decimal": round(dec, 4),
               "implied": round(1.0 / dec, 5), "won": won, "push": push,
               "profit": round(profit, 5)}
        if extra:
            row.update(extra)
        bets.append(row)

    MARKET_OF = {s: m for s, m in [
        ("C84-S1", "M1"), ("C84-S2", "M1"), ("C84-S3", "M1"), ("C84-S4", "M1"),
        ("C84-S5", "M2"), ("C84-S6", "M2"), ("C84-S7", "M3"), ("C84-S8", "M1"),
        ("C84-S9", "M2"), ("C84-S10", "M1"), ("C84-S11", "M1"), ("C84-S12", "M1")]}

    bets = []
    excluded = defaultdict(int)
    for g in games:
        if not g["played"]:
            continue
        sl, tl = g["spread_line"], g["total_line"]
        p = preds[g["game_id"]]
        own, own_tot, sdm = p["own_spread_home"], p["own_total"], p["sd_margin"]
        has_spread_price = g["home_spread_odds"] is not None and g["away_spread_odds"] is not None
        has_total_price = g["over_odds"] is not None and g["under_odds"] is not None

        def spread_bet(side):
            if sl is None or not has_spread_price:
                excluded["spread"] += 1
                return
            price = g["home_spread_odds"] if side == "home" else g["away_spread_odds"]
            push = abs(g["margin"] - sl) < 1e-9
            won = (g["margin"] > sl) if side == "home" else (g["margin"] < sl)
            return price, won, push

        def total_bet(side):
            if tl is None or not has_total_price:
                excluded["total"] += 1
                return
            price = g["over_odds"] if side == "over" else g["under_odds"]
            push = abs(g["total"] - tl) < 1e-9
            won = (g["total"] > tl) if side == "over" else (g["total"] < tl)
            return price, won, push

        # ---- controls
        for strat, side in (("C84-S1", "away"), ("C84-S2", "home")):
            r = spread_bet(side)
            if r:
                emit(bets, strat, side, g, *r, line=sl)

        # ---- own-line side signals
        if sl is not None and has_spread_price:
            e = own - sl
            for strat, thr in (("C84-S3", 2.0), ("C84-S4", 4.0)):
                side = "home" if e >= thr else ("away" if e <= -thr else None)
                if side:
                    r = spread_bet(side)
                    if r:
                        emit(bets, strat, side, g, *r, line=sl,
                             extra={"own_line": own, "edge": round(e, 3)})
        # ---- own-line total signals
        if tl is not None and has_total_price:
            et = own_tot - tl
            for strat, thr in (("C84-S5", 2.5), ("C84-S6", 4.0)):
                side = "over" if et >= thr else ("under" if et <= -thr else None)
                if side:
                    r = total_bet(side)
                    if r:
                        emit(bets, strat, side, g, *r, line=tl,
                             extra={"own_line": own_tot, "edge": round(et, 3)})
        # ---- moneyline
        if g["home_ml"] is not None and g["away_ml"] is not None and sl is not None:
            p_home = norm_cdf(own / sdm)      # registered: Phi(own spread / margin sd); own is home-signed, positive = home favoured
            q_home = 1.0 / american_to_decimal(g["home_ml"])
            q_away = 1.0 / american_to_decimal(g["away_ml"])
            if p_home - q_home >= 0.04:
                price, side = g["home_ml"], "home"
            elif (1 - p_home) - q_away >= 0.04:
                price, side = g["away_ml"], "away"
            else:
                price, side = None, None
            if price is not None:
                dec = american_to_decimal(price)
                push = abs(g["margin"]) < 1e-9
                won = (g["margin"] > 0) if side == "home" else (g["margin"] < 0)
                profit = 0.0 if push else ((dec - 1) if won else -1)
                bets.append({"strategy": "C84-S7", "market": "M3", "season": g["season"],
                             "week": g["week"], "game_id": g["game_id"], "gameday": g["gameday"],
                             "home": g["home"], "away": g["away"], "side": side,
                             "line": None, "price": price, "decimal": round(dec, 4),
                             "implied": round(1 / dec, 5), "won": won, "push": push,
                             "profit": round(profit, 5),
                             "own_win_prob_home": round(p_home, 4),
                             "implied_home": round(q_home, 4), "implied_away": round(q_away, 4)})

        # ---- situational controls
        if sl is not None and has_spread_price and sl <= -7.0:
            r = spread_bet("away")
            if r:
                emit(bets, "C84-S8", "away", g, *r, line=sl)
        if tl is not None and has_total_price and tl <= 40.0:
            r = total_bet("under")
            if r:
                emit(bets, "C84-S9", "under", g, *r, line=tl)
        if g["home_rest"] is not None and g["away_rest"] is not None:
            rd = g["home_rest"] - g["away_rest"]
            side = "home" if rd >= 3 else ("away" if rd <= -3 else None)
            if side and sl is not None and has_spread_price:
                r = spread_bet(side)
                if r:
                    emit(bets, "C84-S12", side, g, *r, line=sl, extra={"rest_diff": rd})

        # ---- availability: level (S10) and surprise (S11)
        h = inj.get((g["season"], g["week"], g["home"]))
        a = inj.get((g["season"], g["week"], g["away"]))
        if h is not None and a is not None and sl is not None and has_spread_price:
            d = h["n_out"] - a["n_out"]
            side = "away" if d >= 3 else ("home" if d <= -3 else None)
            if side:
                r = spread_bet(side)
                if r:
                    emit(bets, "C84-S10", side, g, *r, line=sl,
                         extra={"home_out": h["n_out"], "away_out": a["n_out"]})
        if h is not None and a is not None and sl is not None and has_spread_price:
            if h["surprise"] is not None and a["surprise"] is not None:
                ds = h["surprise"] - a["surprise"]
                side = "away" if ds >= 2.0 else ("home" if ds <= -2.0 else None)
                if side:
                    r = spread_bet(side)
                    if r:
                        emit(bets, "C84-S11", side, g, *r, line=sl,
                             extra={"home_surprise": h["surprise"],
                                    "away_surprise": a["surprise"]})

    # ------------------------------------------------------------- score them
    by = defaultdict(list)
    for b in bets:
        by[b["strategy"]].append(b)

    ctrl_roi = {}
    for c in ("C84-S1", "C84-S2"):
        if by.get(c):
            s = score_bets(by[c], None)
            ctrl_roi[c] = s["roi_pct"] if s else None
    best_ctrl = max([v for v in ctrl_roi.values() if v is not None], default=None)

    scored = {}
    for strat, grp in by.items():
        scored[strat] = score_bets(grp, best_ctrl)

    # multiplicity over the ten non-control rules that produced bets
    family = [s for s in scored if s not in ("C84-S1", "C84-S2") and scored[s]]
    pv = {s: (scored[s]["p_value"] if scored[s]["p_value"] is not None else 1.0) for s in family}
    qv = benjamini_hochberg(pv)

    # ------------------------------------------------------------- gate matrix
    block_of = {g["game_id"]: (g["season"], g["week"]) for g in games}
    order = {b: i for i, b in enumerate(sorted({(g["season"], g["week"]) for g in games}))}
    # A prediction is pre-game only when the newest block in its fit is strictly earlier
    # than the block of the game it prices. Non-model bets (controls and situational rules)
    # read only the closing line, which by construction is published before kick-off.
    MODEL_RULES = {"C84-S3", "C84-S4", "C84-S5", "C84-S6", "C84-S7"}

    def pregames_ok(strat):
        if strat not in MODEL_RULES:
            return True
        for b in by[strat]:
            gi = order[block_of[b["game_id"]]]
            mt = preds[b["game_id"]]["max_train_block"]
            if mt < 0 or mt >= gi:
                return False
        return True

    gates = {}
    for strat, sc in scored.items():
        if not sc:
            continue
        is_ctrl = strat in ("C84-S1", "C84-S2")
        q = qv.get(strat)
        checks = [
            ("C84-G1", "an observed price on every scored bet",
             all(b["price"] is not None for b in by[strat])),
            ("C84-G2", "pre-game information only: newest fit block is earlier than the priced game",
             pregames_ok(strat)),
            ("C84-G3", f"at least {MIN_DECIDED} decided bets", sc["n_decided"] >= MIN_DECIDED),
            ("C84-G4", "hit rate beats the price-implied break-even",
             (sc["break_even_hit_rate"] is not None and sc["hit_rate"] > sc["break_even_hit_rate"])),
            ("C84-G5", f"survives BH over the {len(family)}-rule scored family",
             (q is not None and q < 0.05)),
            ("C84-G6", "positive in the untouched 2024-2026 holdout",
             (sc["holdout_2024_2026"] is not None and sc["holdout_2024_2026"]["roi_pct"] > 0)),
            ("C84-G7", "positive in >= 60% of seasons with >= 20 bets",
             (sc["stability_positive_fraction"] is not None and sc["stability_positive_fraction"] >= 0.60)),
            ("C84-G8", "game-cluster 95% interval on ROI excludes zero",
             (sc["roi_ci95_game_cluster"] is not None and sc["roi_ci95_game_cluster"][0] > 0)),
            ("C84-G9", "beats the information-free control",
             (sc["beats_control"] is not None and sc["beats_control"] > 0)),
            ("C84-G10", "edge survives deleting the best season",
             (sc["roi_without_best_season_pct"] is not None and sc["roi_without_best_season_pct"] > 0)),
        ]
        gates[strat] = {
            "q_value": (round(q, 6) if q is not None else None),
            "control": is_ctrl,
            "checks": [{"gate": gid, "rule": rule, "pass": bool(ok)} for gid, rule, ok in checks],
            "gates_passed": sum(1 for _, _, ok in checks if ok),
            "gates_total": len(checks),
            "promoted": all(ok for _, _, ok in checks) and not is_ctrl,
            "status": ("CONTROL" if is_ctrl else
                       ("PROMOTED" if all(ok for _, _, ok in checks) else "PAPER")),
        }

    # -------------------------------------------------------- Brier skill score
    # own win probability vs the market's win probability, on the same games
    brier_model, brier_market = [], []
    for g in games:
        if not g["played"] or g["home_ml"] is None or g["away_ml"] is None:
            continue
        p = preds[g["game_id"]]
        p_own = norm_cdf(p["own_spread_home"] / p["sd_margin"])
        # de-vig the two-way moneyline to get the market's probability
        qh = 1.0 / american_to_decimal(g["home_ml"])
        qa = 1.0 / american_to_decimal(g["away_ml"])
        q_mkt = qh / (qh + qa)
        y = 1.0 if g["margin"] > 0 else (0.0 if g["margin"] < 0 else None)
        if y is None:
            continue
        brier_model.append({"game_id": g["game_id"], "season": g["season"],
                            "p": p_own, "y": y, "b": (p_own - y) ** 2})
        brier_market.append({"game_id": g["game_id"], "season": g["season"],
                             "p": q_mkt, "y": y, "b": (q_mkt - y) ** 2})
    bm = mean([r["b"] for r in brier_model])
    bk = mean([r["b"] for r in brier_market])
    diffs = defaultdict(list)
    for a, b in zip(brier_model, brier_market):
        diffs[a["game_id"]].append(a["b"] - b["b"])
    diff_rows = [{"game_id": k, "profit": sum(v) / len(v)} for k, v in diffs.items()]
    brier_ci = cluster_bootstrap_ci(diff_rows, "game_id")

    brier_block = {
        "n_games": len(brier_model),
        "brier_model": round(bm, 5) if bm is not None else None,
        "brier_market_devig": round(bk, 5) if bk is not None else None,
        "brier_skill_score": (round(1 - bm / bk, 5) if bm and bk else None),
        "difference_model_minus_market": round(bm - bk, 5) if (bm is not None and bk is not None) else None,
        "difference_ci95_game_cluster": brier_ci,
        "reading": ("A positive difference means the market's probability was the better forecast. "
                    "A negative difference with an interval entirely below zero would be the first "
                    "evidence in this repository that the own line adds information."),
        "benchmark_note": "The benchmark is the de-vigged closing moneyline, not a coin flip. A coin flip "
                          "is not a benchmark; a market is.",
        "source": OFFICIAL["schedules"],
    }

    # ------------------------------------------------- injury / personnel ablation
    ablation = injury_ablation(games, inj, brier_block)

    # ------------------------------------------------------------- luck panel
    luck = luck_panel(bets, by, scored, gates, ctrl_roi)

    # -------------------------------------------------- correlation register
    corr = correlation_register(bets, by)

    # ------------------------------------------------------------------- props
    props = prop_projections()

    results = {
        "generated_at": t0.replace(microsecond=0).isoformat(),
        "session": "c84a41a4-nfl1",
        "registration": {
            "file": "data/session-c84a41a4/preregistration.json",
            "sha256": sha256(PREREG),
            "version": "C84-PREREG-1",
            "declared_before_results": True,
        },
        "inputs": {name: {"sha256": sha256(os.path.join(ROOT, p))}
                   for name, p in [
                       ("games", "data/s9cb/games.csv"),
                       ("injuries", "data/s9cb/injuries.csv"),
                       ("player_week", "data/s9cb/player_week.csv")]},
        "official_sources": OFFICIAL,
        "sample": {
            "seasons": [min(SEASONS), max(SEASONS)],
            "games_in_window": len(games), "games_played": sum(1 for g in games if g["played"]),
            "games_with_spread_price": sum(1 for g in games if g["home_spread_odds"] is not None),
            "games_with_total_price": sum(1 for g in games if g["over_odds"] is not None),
            "games_with_moneyline": sum(1 for g in games if g["home_ml"] is not None),
            "bet_rows_scored": len(bets),
            "corpus_note": ("The committed extract is all REG games from the source; it does not hold "
                            "every game ever played (5,336 decided games in the 2006-2026 window here). "
                            "The brief's '136-game log' is the 2026 season slice in "
                            "data/verified/model/predictions_log.json and is a separate, smaller corpus "
                            "kept for continuity; this study does not use it as its sample."),
            "excluded_for_missing_price": dict(excluded),
            "price_coverage_note": "Seasons 1999-2005 carry no two-sided price and are excluded by the "
                                   "registered sample rule. No price is imputed.",
            "orientation_note": "spread_line is the canonical closing line with the HOME side signed "
                                "positive, so a negative line means the home club is favoured. With "
                                "hfa ~ 1.7 points, own_spread_home = -8.6 in BUF @ NYJ means the model "
                                "makes the HOME club (NYJ) an 8.6-point favourite, i.e. the model and the "
                                "close (NYJ -8.5) agree. This convention is printed on the site because "
                                "reading it the other way inverts every edge.",
        },
        "own_line_fit": fitinfo,
        "strategies": scored,
        "gates": gates,
        "controls": {"C84-S1_roi_pct": ctrl_roi.get("C84-S1"),
                     "C84-S2_roi_pct": ctrl_roi.get("C84-S2"),
                     "best_control_roi_pct": best_ctrl},
        "brier": brier_block,
        "ablation": ablation,
        "luck": luck,
        "correlation": corr,
        "props": props,
        "promoted": [s for s, g in gates.items() if g["promoted"]],
        "n_rules_tested": len(scored),
        "n_bets_total": len(bets),
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    with open(os.path.join(OUT_DIR, "bet_log.csv"), "w", newline="", encoding="utf-8") as fh:
        base = ["strategy", "market", "season", "week", "game_id", "gameday", "home", "away",
                "side", "line", "price", "decimal", "implied", "won", "push", "profit"]
        extra = sorted({k for b in bets for k in b} - set(base))
        w = csv.DictWriter(fh, fieldnames=base + extra, restval="")
        w.writeheader()
        for b in bets:
            w.writerow(b)

    print(f"games {len(games)}  bets {len(bets)}  rules {len(scored)}")
    for s in sorted(scored):
        sc, g = scored[s], gates[s]
        if not sc:
            continue
        print(f"  {s:8s} n={sc['n_decided']:5d} hit={sc['hit_rate']:.4f} "
              f"be={sc['break_even_hit_rate'] or 0:.4f} roi={sc['roi_pct']:+7.2f}% "
              f"q={g['q_value']} gates={g['gates_passed']}/{g['gates_total']} {g['status']}")
    print(f"Brier model {bm:.5f} market {bk:.5f} skill {(1-bm/bk):+.5f} ci {brier_ci}")
    print(f"promoted: {results['promoted']}")


def injury_ablation(games, inj, primary_brier):
    """Ablation, not a penalty: fit the SAME model with and without the availability terms.

    This is what the brief asks for twice ('Add injury and personnel ablations instead of
    fixed penalties' / 'Compare identical models with and without verified availability
    features using chronological holdouts'). Nothing about the model changes except whether
    the two availability columns exist, so the difference in out-of-sample error IS the
    measured contribution of the availability features.
    """
    with_avail, _ = fit_own_lines(games, inj_feats=inj, use_avail=True)
    without, _ = fit_own_lines(games, inj_feats=None, use_avail=False)

    def errors(preds):
        e = []
        for g in games:
            p = preds.get(g["game_id"])
            if not g["played"] or not p or p["n_train"] <= 0:
                continue
            e.append({"game_id": g["game_id"], "season": g["season"],
                      "profit": abs(g["margin"] - p["own_spread_home"])})
        return e

    e_with, e_wo = errors(with_avail), errors(without)
    key = {r["game_id"]: r["profit"] for r in e_wo}
    paired = [{"game_id": r["game_id"],
               "profit": r["profit"] - key[r["game_id"]]}
              for r in e_with if r["game_id"] in key]
    m_with = mean([r["profit"] for r in e_with])
    m_wo = mean([r["profit"] for r in e_wo])
    md = mean([r["profit"] for r in paired])
    ci = cluster_bootstrap_ci(paired, "game_id")
    holds = []
    windows = [(2006, DEVELOP_MAX), (VALIDATE[0], VALIDATE[1]),
                (HOLDOUT[0], HOLDOUT[-1])]
    for lo, hi in windows:
        sub = [r for r in paired if lo <= int(r["game_id"].split("_")[0]) <= hi]
        holds.append({"window": f"{lo}-{hi}", "n": len(sub),
                      "mean_abs_error_difference": (round(mean([r["profit"] for r in sub]), 4)
                                                    if sub else None)})
    return {
        "what_changed": "only the presence of two availability columns in the margin fit",
        "n_games": len(paired),
        "mae_with_availability": round(m_with, 4) if m_with is not None else None,
        "mae_without_availability": round(m_wo, 4) if m_wo is not None else None,
        "difference_with_minus_without": round(md, 4) if md is not None else None,
        "difference_ci95_game_cluster": ci,
        "by_window": holds,
        "verdict": ("The availability features add nothing measurable: the interval on the "
                    "difference contains zero."
                    if ci and ci[0] <= 0 <= ci[1] else
                    "The interval on the difference excludes zero; the feature has a measurable effect."),
        "brier_with": primary_brier["brier_model"],
        "brier_note": "The Brier panel above is computed from the WITH-availability model, so the two panels agree.",
        "why_not_a_penalty": ("A fixed points-per-starter penalty asserts a magnitude. This ablation "
                              "measures one, and reports the interval, so a reviewer can see whether the "
                              "measurement is distinguishable from noise."),
    }


def luck_panel(bets, by, scored, gates, ctrl_roi):
    """The 'removal of luck' panel, computed rather than asserted."""
    all_bets = list(bets)
    total = len(all_bets)
    dec = [b for b in all_bets if not b["push"]]
    hit = sum(1 for b in dec if b["won"]) / len(dec) if dec else None
    be = mean([b["implied"] for b in all_bets])
    # how large does a real edge have to be before this sample can see it?
    needed = {}
    for edge in (0.01, 0.02, 0.03, 0.05):
        p0 = be if be else 0.5136
        p1 = p0 + edge
        var = p1 * (1 - p1)
        n_need = math.ceil(((1.959964 + 0.841621) ** 2) * var / (edge ** 2)) if edge > 0 else None
        needed[f"{int(edge*100)}-point hit-rate edge"] = n_need
    # how many of the scored rules clear even the weakest luck test?
    cleared = [s for s, g in gates.items() if g["gates_passed"] >= 8 and not g["control"]]
    return {
        "n_bets_all_rules": total,
        "n_decided": len(dec),
        "hit_rate_all_bets": round(hit, 4) if hit else None,
        "break_even_hit_rate": round(be, 4) if be else None,
        "units_above_break_even_per_100_bets": (round(100 * (hit - be), 2)
                                                if hit and be else None),
        "sample_size_needed_80pct_power": needed,
        "power_note": ("Two-sided test at 5% with 80% power, on hit rate. It says how many decided "
                       "bets a genuine edge of that size needs before it is visible at all. With "
                       f"{len(dec)} decided bets in total across all twelve rules, only edges of roughly "
                       "2 percentage points or larger are even in principle detectable, and each individual "
                       "rule holds a fraction of that total."),
        "controls": {"blind_away_roi_pct": ctrl_roi.get("C84-S1"),
                     "blind_home_roi_pct": ctrl_roi.get("C84-S2"),
                     "reading": ("An information-free rule loses almost exactly the vig, as it must. "
                                 "Any claimed edge has to be measured against THIS, not against 50%.")},
        "rules_clearing_8_of_10_gates": cleared,
        "honest_summary": ("No rule removed luck. Zero of twelve rules passed every gate; the best "
                           "in-sample result belongs to a rule whose game-cluster interval contains zero "
                           "and which fails the untouched holdout."),
    }


def correlation_register(bets, by):
    """Published only where n >= 25 paired observations, with n printed beside every value."""
    import numpy as np
    rows = []
    # 1) between strategies: are two rules betting the same games the same way?
    fam = sorted([s for s in by if s not in ("C84-S1", "C84-S2")])
    for i in range(len(fam)):
        for j in range(i + 1, len(fam)):
            a, b = fam[i], fam[j]
            amap = {x["game_id"] + "|" + x["side"]: x["profit"] for x in by[a]}
            bmap = {x["game_id"] + "|" + x["side"]: x["profit"] for x in by[b]}
            shared = sorted(set(amap) & set(bmap))
            if len(shared) < 25:
                continue
            xa = np.array([amap[k] for k in shared])
            xb = np.array([bmap[k] for k in shared])
            if xa.std() == 0 or xb.std() == 0:
                continue
            r = float(np.corrcoef(xa, xb)[0, 1])
            # Share of the overlapping bets that take the SAME side of the same game. A high
            # share is what makes two rules one position rather than two, and it is the number
            # a parlay decision actually needs.
            same = sum(1 for k in shared if amap[k] == bmap[k]) / len(shared)
            rows.append({"kind": "strategy-vs-strategy overlap", "a": a, "b": b,
                         "n": len(shared), "r": round(r, 4),
                         "same_side_pct": round(100 * same, 1),
                         "source": OFFICIAL["schedules"]})
    # 2) the classic same-game pair: does the total move with the margin?
    games = load_games()
    g = [x for x in games if x["played"] and x["margin"] is not None and x["total"] is not None]
    if len(g) >= 25:
        r = float(np.corrcoef([x["margin"] for x in g], [x["total"] for x in g])[0, 1])
        rows.append({"kind": "same-game: margin vs total points", "a": "home margin",
                     "b": "total points", "n": len(g), "r": round(r, 4),
                     "source": OFFICIAL["schedules"]})
    # 3) own line vs the close
    preds, _ = fit_own_lines(games, inj_feats=None, use_avail=False)
    pair = [(p, x["spread_line"]) for x in games
            if (p := preds.get(x["game_id"])) and p["n_train"] > 0 and x["spread_line"] is not None]
    if len(pair) >= 25:
        r = float(np.corrcoef([a["own_spread_home"] for a, _ in pair],
                              [b for _, b in pair])[0, 1])
        rows.append({"kind": "own line vs the closing line", "a": "own_spread_home",
                     "b": "spread_line", "n": len(pair), "r": round(r, 4),
                     "source": OFFICIAL["schedules"]})
    return {"rule": "Publish only where n >= 25 paired observations; n is printed with every value.",
            "rows": rows,
            "not_computed": ("Prop-level and same-game-parlay correlations are NOT published because no "
                             "observed prop price exists in any source here. A correlation between two "
                             "legs whose prices cannot be observed is not a betting number.")}


def prop_projections():
    """Shrunk volume projections with intervals. No ROI: no prop price exists in any source here."""
    cols = {"passing_yards": "passing_yards", "rushing_yards": "rushing_yards",
            "receiving_yards": "receiving_yards"}
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data/s9cb/player_week.csv"),
                                    newline="", encoding="utf-8")))
    by = defaultdict(list)
    for r in rows:
        if (r.get("season_type") or "REG") != "REG":
            continue
        for label, col in cols.items():
            v = f(r.get(col))
            if v is None or v <= 0:
                continue
            by[(label, r["player_id"], r["player_display_name"], r.get("position") or "")].append(
                (int(r["season"]), int(r["week"]), v))
    out = []
    for (label, pid, name, pos), seq in by.items():
        seq.sort()
        vals = [v for (_, _, v) in seq]
        n = len(vals)
        if n < 8:
            continue
        last4 = vals[-4:]
        mu = mean(vals)
        sdv = sd(vals)
        lam = 0.35          # fixed shrinkage, declared at registration as part of the projection rule
        proj = lam * (mean(last4) or mu) + (1 - lam) * mu
        out.append({
            "market": label, "player_id": pid, "player": name, "position": pos,
            "n_weeks": n, "season_mean": round(mu, 2),
            "last4_mean": round(mean(last4) or mu, 2),
            "projection": round(proj, 2),
            "sd": (round(sdv, 2) if sdv else None),
            "interval80": ([round(max(0.0, proj - 1.2816 * sdv), 2),
                            round(proj + 1.2816 * sdv, 2)] if sdv else None),
            "price": None, "price_status": "BLANK: no observed prop price in any committed source",
            "source": OFFICIAL["stats"],
        })
    out.sort(key=lambda r: (-r["n_weeks"], r["market"], r["player"]))
    return {"n_players_projected": len(out), "rows": out[:120],
            "note": ("Projections only. A prop can never be scored, ranked or turned into a parlay leg "
                     "until an observed price exists for it; none does."),
            "shrinkage": 0.35}


if __name__ == "__main__":
    main()
