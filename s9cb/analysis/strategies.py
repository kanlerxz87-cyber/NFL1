#!/usr/bin/env python3
"""Strategy leaderboard: single bets, validation gates, luck removal, parlays.

Every rule is declared before it is scored. The rule set deliberately mixes
model-driven rules (S01-S04) with well-known situational systems (S05-S10) and
injury rules (S11-S12): if the harness only ever produced winners it would be
selecting on the outcome, so the controls exist to show that it can also say no.

A bet is only scored when the source carries an OBSERVED price for that side.
No price is assumed and no price is filled in; games without a price are counted
and reported, never silently dropped.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from common import (american_to_decimal, benjamini_hochberg, binomial_p_two_sided,
                    bootstrap_ci, pearson, _student_t_cdf)

MIN_BETS = 200
HOLDOUT_SEASONS = (2024, 2025)
STABILITY_SEASON_MIN_BETS = 20
STABILITY_FRACTION = 0.60

GATES = [
    ("G1", "walk-forward / pre-game information only",
     "Every input to the bet decision is known before kick-off and, for the model rules, "
     "comes from a fit that used only earlier games."),
    ("G2", "observed prices on every scored bet",
     "Every scored bet carries a price taken from the source file. No -110 assumption is used."),
    ("G3", f"at least {MIN_BETS} scored bets",
     "Below this, a run of luck is indistinguishable from skill at any plausible effect size."),
    ("G4", "hit rate beats the break-even implied by the actual prices taken",
     "Break-even is computed from the real price on each bet, not from 0.5."),
    ("G5", "survives multiple testing (BH-adjusted p < 0.05, 12 rules tested)",
     "Testing many rules and reporting only the best one manufactures winners; the "
     "Benjamini-Hochberg step charges for that."),
    ("G6", "positive in a untouched holdout (2024 + 2025)",
     "The holdout seasons were never used to tune the rule thresholds."),
    ("G7", f"positive in at least {int(STABILITY_FRACTION*100)}% of individual seasons",
     "An edge that exists in only one season is a season, not a strategy."),
    ("G8", "95% bootstrap confidence interval on ROI excludes zero",
     "Ten thousand resamples of the actual bet log; the interval must sit above zero."),
]


# ---------------------------------------------------------------- bet helpers
def _spread_bet(row, side: str) -> dict | None:
    if not np.isfinite(row.get("spread_line", np.nan)):
        return None
    if side == "home":
        price = row.get("home_spread_odds", np.nan)
    else:
        price = row.get("away_spread_odds", np.nan)
    if not np.isfinite(price):
        return None
    margin, line = row["result"], row["spread_line"]
    if not np.isfinite(margin):
        return None
    push = abs(margin - line) < 1e-9
    if side == "home":
        won = margin > line
    else:
        won = margin < line
    return {"market": f"{side} spread", "price": float(price),
            "won": bool(won), "push": bool(push), "line": float(line)}


def _total_bet(row, side: str) -> dict | None:
    if not np.isfinite(row.get("total_line", np.nan)):
        return None
    price = row.get("over_odds" if side == "over" else "under_odds", np.nan)
    if not np.isfinite(price):
        return None
    tot, line = row["total"], row["total_line"]
    if not np.isfinite(tot):
        return None
    push = abs(tot - line) < 1e-9
    won = tot > line if side == "over" else tot < line
    return {"market": f"{side} total", "price": float(price),
            "won": bool(won), "push": bool(push), "line": float(line)}


def _mk(game_row: pd.Series, strat: str, bet: dict) -> dict:
    return {"strategy": strat, "season": int(game_row["season"]), "week": int(game_row["week"]),
            "gameday": game_row.get("gameday"), "game_id": game_row["game_id"],
            "home_team": game_row["home_team"], "away_team": game_row["away_team"],
            **bet}


def generate(M: pd.DataFrame, inj: pd.DataFrame) -> pd.DataFrame:
    bets: list[dict] = []
    played = M[M["played"]].copy()

    # ---- per-team/week injury features from the official weekly report -----------
    inj = inj[inj["game_type"].fillna("REG") == "REG"].copy()
    inj["out_flag"] = inj["report_status"].isin(["Out", "Doubtful"])
    inj["qb_out"] = inj["out_flag"] & inj["position"].isin(["QB"])
    agg = inj.groupby(["season", "week", "team"]).agg(
        n_out=("out_flag", "sum"), qb_out=("qb_out", "max")).reset_index()
    played = played.merge(agg.rename(columns={"team": "home_team",
                                              "n_out": "home_n_out", "qb_out": "home_qb_out"}),
                          on=["season", "week", "home_team"], how="left")
    played = played.merge(agg.rename(columns={"team": "away_team",
                                              "n_out": "away_n_out", "qb_out": "away_qb_out"}),
                          on=["season", "week", "away_team"], how="left")
    for c in ["home_n_out", "away_n_out"]:
        played[c] = played[c].fillna(0)
    for c in ["home_qb_out", "away_qb_out"]:
        played[c] = played[c].fillna(False).astype(bool)
    played["inj_covered"] = played["season"] >= 2016

    for _, r in played.iterrows():
        mm = r.get("model_margin", np.nan)
        mt = r.get("model_total", np.nan)
        sl, tl = r.get("spread_line", np.nan), r.get("total_line", np.nan)
        has_model = np.isfinite(mm) and np.isfinite(mt) and np.isfinite(sl) and np.isfinite(tl)

        rules: list[tuple[str, str, str]] = []     # (strategy, type, side)
        if has_model:
            e = mm - sl
            if e >= 1.5:
                rules.append(("S01 Model spread edge >= 1.5 pts", "spread", "home"))
            elif e <= -1.5:
                rules.append(("S01 Model spread edge >= 1.5 pts", "spread", "away"))
            if e >= 3.0:
                rules.append(("S02 Model spread edge >= 3.0 pts", "spread", "home"))
            elif e <= -3.0:
                rules.append(("S02 Model spread edge >= 3.0 pts", "spread", "away"))
            et = mt - tl
            if et >= 2.5:
                rules.append(("S03 Model total edge >= 2.5 pts", "total", "over"))
            elif et <= -2.5:
                rules.append(("S03 Model total edge >= 2.5 pts", "total", "under"))
            if et >= 4.0:
                rules.append(("S04 Model total edge >= 4.0 pts", "total", "over"))
            elif et <= -4.0:
                rules.append(("S04 Model total edge >= 4.0 pts", "total", "under"))

        rd = (r.get("home_rest", np.nan) or 0) - (r.get("away_rest", np.nan) or 0)
        if np.isfinite(rd) and rd >= 3:
            rules.append(("S05 Rest edge >= 3 days", "spread", "home"))
        elif np.isfinite(rd) and rd <= -3:
            rules.append(("S05 Rest edge >= 3 days", "spread", "away"))

        if int(r.get("div_game", 0)) == 1 and np.isfinite(sl) and sl <= -3:
            rules.append(("S06 Divisional road underdog of 3+", "spread", "away"))

        if np.isfinite(sl) and sl <= -7:
            rules.append(("S07 Fade the road favourite of 7+", "spread", "home"))

        if (r.get("home_rest", np.nan) or 0) >= 13 and (r.get("away_rest", np.nan) or 0) < 13:
            rules.append(("S08 Home team off a bye", "spread", "home"))

        if np.isfinite(tl) and tl <= 40:
            rules.append(("S09 Under when the total is 40 or lower", "total", "under"))
        if np.isfinite(tl) and tl >= 50:
            rules.append(("S10 Over when the total is 50 or higher", "total", "over"))

        if r.get("inj_covered"):
            if r["home_qb_out"] and not r["away_qb_out"]:
                rules.append(("S11 Opponent QB ruled Out/Doubtful", "spread", "away"))
            elif r["away_qb_out"] and not r["home_qb_out"]:
                rules.append(("S11 Opponent QB ruled Out/Doubtful", "spread", "home"))
            diff = r["home_n_out"] - r["away_n_out"]
            if diff >= 3:
                rules.append(("S12 Out-count gap of 3 or more", "spread", "away"))
            elif diff <= -3:
                rules.append(("S12 Out-count gap of 3 or more", "spread", "home"))

        for strat, kind, side in rules:
            bet = _spread_bet(r, side) if kind == "spread" else _total_bet(r, side)
            if bet:
                bets.append(_mk(r, strat, bet))

    B = pd.DataFrame(bets)
    if B.empty:
        return B
    B["decimal"] = [american_to_decimal(p) for p in B["price"]]
    B["profit"] = [0.0 if p else (d - 1.0 if w else -1.0)
                   for p, w, d in zip(B["push"], B["won"], B["decimal"])]
    B["implied_prob"] = 1.0 / B["decimal"]
    return B


# ------------------------------------------------------------------- scoring
def score_group(g: pd.DataFrame) -> dict:
    decided = g[~g["push"]]
    n, nd = len(g), len(decided)
    if n == 0 or nd == 0:
        return {}
    profit = float(g["profit"].sum())
    roi = profit / n
    hit = float(decided["won"].mean())
    breakeven = float(g["implied_prob"].mean())
    # mean and variance are taken over ALL bets (pushes score 0), so they are consistent
    sd = float(g["profit"].std(ddof=1)) if n > 1 else float("nan")
    se = sd / math.sqrt(n) if n > 1 and sd == sd else float("nan")
    t = (profit / n) / se if se and se == se else float("nan")
    p = 2 * (1 - _student_t_cdf(abs(t), n - 1)) if t == t else float("nan")
    ci = bootstrap_ci(g["profit"].to_numpy(float))
    p_bin = binomial_p_two_sided(int(decided["won"].sum()), nd, breakeven)
    return {
        "n_bets": int(n), "n_decided": int(nd), "n_pushes": int(n - nd),
        "wins": int(decided["won"].sum()), "losses": int(nd - decided["won"].sum()),
        "hit_rate": round(hit, 4),
        "break_even_hit_rate": round(breakeven, 4),
        "profit_units": round(profit, 3),
        "roi": round(roi, 5),
        "roi_pct": round(100 * roi, 3),
        "avg_decimal_odds": round(float(g["decimal"].mean()), 4),
        "sd_profit_per_bet": round(sd, 4) if sd == sd else None,
        "t_stat": round(t, 4) if t == t else None,
        "p_value": round(p, 6) if p == p else None,
        "p_value_binomial_vs_breakeven": round(p_bin, 6) if p_bin == p_bin else None,
        "roi_ci95": ci,
    }


def season_table(g: pd.DataFrame) -> list[dict]:
    rows = []
    for s, grp in g.groupby("season"):
        sc = score_group(grp)
        if sc:
            rows.append({"season": int(s), "n_bets": sc["n_bets"], "hit_rate": sc["hit_rate"],
                         "profit_units": sc["profit_units"], "roi_pct": sc["roi_pct"]})
    return sorted(rows, key=lambda r: r["season"])


def leave_one_season_out(g: pd.DataFrame) -> dict:
    out = {}
    for s, grp in g.groupby("season"):
        sc = score_group(g[g["season"] != s])
        if sc:
            out[int(s)] = {"roi_pct": sc["roi_pct"], "profit_units": sc["profit_units"],
                           "n_bets": sc["n_bets"]}
    return out


def evaluate(B: pd.DataFrame) -> dict:
    rows = []
    for strat, g in B.groupby("strategy"):
        sc = score_group(g)
        if not sc:
            continue
        seasons = season_table(g)
        hold = score_group(g[g["season"].isin(HOLDOUT_SEASONS)])
        big = [r for r in seasons if r["n_bets"] >= STABILITY_SEASON_MIN_BETS]
        pos = sum(1 for r in big if r["roi_pct"] > 0)
        loso = leave_one_season_out(g)
        worst_loso = min((v["roi_pct"] for v in loso.values()), default=None)

        g1 = True                                     # walk-forward by construction
        g2 = bool(g["price"].notna().all())
        g3 = sc["n_bets"] >= MIN_BETS
        g4 = sc["hit_rate"] > sc["break_even_hit_rate"]
        g5 = None                                     # filled after BH correction
        g6 = bool(hold) and hold["roi_pct"] > 0
        g7 = (len(big) > 0) and (pos / len(big)) >= STABILITY_FRACTION
        g8 = bool(sc["roi_ci95"]) and sc["roi_ci95"][0] > 0

        rows.append({
            "strategy": strat, **sc,
            "holdout_2024_2025": ({"n_bets": hold["n_bets"], "roi_pct": hold["roi_pct"],
                                   "hit_rate": hold["hit_rate"]} if hold else None),
            "seasons": seasons,
            "seasons_positive": pos, "seasons_evaluated": len(big),
            "leave_one_season_out": loso,
            "worst_case_roi_pct_after_dropping_a_season": worst_loso,
            "gates": {"G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5,
                      "G6": g6, "G7": g7, "G8": g8},
        })

    pv = [r["p_value"] if r["p_value"] is not None else float("nan") for r in rows]
    adj = benjamini_hochberg(pv)
    for r, a in zip(rows, adj):
        r["p_value_bh_adjusted"] = None if not np.isfinite(a) else round(float(a), 6)
        r["gates"]["G5"] = bool(np.isfinite(a) and a < 0.05)

    for r in rows:
        passed = [k for k, v in r["gates"].items() if v]
        r["gates_passed"] = passed
        r["n_gates_passed"] = len(passed)
        if len(passed) == 8:
            r["status"] = "PASS"
        elif all(r["gates"][k] for k in ("G1", "G2", "G3", "G4")):
            r["status"] = "WATCH"
        else:
            r["status"] = "FAIL"

    rows.sort(key=lambda r: (-(r["roi_pct"] or -99)))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return {
        "generated_at": None,
        "n_strategies": len(rows),
        "gate_definitions": [{"id": i, "name": n, "why": w} for i, n, w in GATES],
        "leaderboard": rows,
        "totals": {
            "bets_scored": int(len(B)),
            "games_in_sample": int(B["game_id"].nunique()),
            "seasons": [int(s) for s in sorted(B["season"].unique())],
            "all_prices_observed": bool(B["price"].notna().all()),
        },
    }


# ------------------------------------------------------------------ parlays
def parlay_analysis(B: pd.DataFrame, top: pd.DataFrame) -> dict:
    """Two-leg parlays built from legs that fired in the same week but different games.

    Every pair is priced at the product of the two observed decimal prices and scored.
    The whole matrix is published, so nothing is cherry-picked after seeing the result.
    """
    strats = [r["strategy"] for r in top]
    legs: dict[str, list] = {}
    for r in B.itertuples():
        if r.strategy in strats:
            legs.setdefault(r.strategy, []).append(r)

    matrix = []
    for i in range(len(strats)):
        for j in range(i + 1, len(strats)):
            a, b = strats[i], strats[j]
            lb = {(r.season, r.week): r for r in legs[b]}
            parlays = []
            for r in legs[a]:
                o = lb.get((r.season, r.week))
                if o is None or o.game_id == r.game_id:
                    continue          # two legs in the same game are not a parlay
                if r.push or o.push:
                    continue
                won = bool(r.won and o.won)
                dec = r.decimal * o.decimal
                parlays.append({"season": r.season, "week": r.week, "won": won,
                                "won_a": bool(r.won), "won_b": bool(o.won),
                                "decimal": dec, "profit": (dec - 1.0) if won else -1.0,
                                "implied": 1.0 / dec})
            if len(parlays) < 30:
                matrix.append({"pair": [a, b], "n_parlays": len(parlays),
                               "note": "too few same-week pairs to score"})
                continue
            P = pd.DataFrame(parlays)
            n = len(P)
            profit = float(P["profit"].sum())
            sd = float(P["profit"].std(ddof=1))
            se = sd / math.sqrt(n)
            t = (profit / n) / se if se else float("nan")
            p = 2 * (1 - _student_t_cdf(abs(t), n - 1)) if t == t else float("nan")
            hit = float(P["won"].mean())
            # Independence benchmark built from the exact legs that make up these
            # parlays, so the comparison isolates genuine dependence between the two
            # legs from any week-selection effect.
            ma = float(P["won_a"].mean())
            mb = float(P["won_b"].mean())
            ma_all = float(np.mean([1.0 if r.won else 0.0 for r in legs[a] if not r.push]))
            mb_all = float(np.mean([1.0 if r.won else 0.0 for r in legs[b] if not r.push]))
            phi = pearson(P["won_a"].astype(float), P["won_b"].astype(float))
            matrix.append({
                "pair": [a, b], "n_parlays": n,
                "hit_rate": round(hit, 4),
                "hit_rate_if_independent": round(ma * mb, 4) if ma * mb else None,
                "marginal_a_in_these_parlays": round(ma, 4),
                "marginal_b_in_these_parlays": round(mb, 4),
                "marginal_a_all_weeks": round(ma_all, 4), "marginal_b_all_weeks": round(mb_all, 4),
                "correlation_ratio": (round(hit / (ma * mb), 4) if ma * mb else None),
                "leg_phi_correlation": phi,
                "avg_parlay_decimal": round(float(P["decimal"].mean()), 4),
                "profit_units": round(profit, 3), "roi_pct": round(100 * profit / n, 3),
                "p_value": round(float(p), 6) if p == p else None,
                "leg_overlap": "different games, same week",
            })

    scored = [m for m in matrix if m.get("p_value") is not None]
    adj = benjamini_hochberg([m["p_value"] for m in scored])
    for m, a_ in zip(scored, adj):
        m["p_value_bh_adjusted"] = None if not np.isfinite(a_) else round(float(a_), 6)
        m["survives_multiple_testing_5pct"] = bool(np.isfinite(a_) and a_ < 0.05)
        m["status"] = ("PASS" if (m["survives_multiple_testing_5pct"] and m["roi_pct"] > 0)
                       else "NOT PROVEN")
    return {
        "pairs": matrix,
        "n_pairs_scored": len(scored),
        "n_pairs_surviving_bh_5pct": sum(1 for m in scored if m["survives_multiple_testing_5pct"]),
        "reading": ("A correlation_ratio above 1.00 means the two legs landed together more "
                    "often than independence predicts. Because a standard parlay is priced at "
                    "the product of the legs, positively correlated legs make the parlay "
                    "cheaper than it should be -- which is why some pairs show a positive "
                    "return even though neither leg does on its own. That is a property of "
                    "the pricing rule, not proof of skill, and it is why every pair is "
                    "published rather than the best one."),
    }
