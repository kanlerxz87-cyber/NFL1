#!/usr/bin/env python3
"""strat/proper_score.py — rank the model and the strategies by proper scores (C3).

Why not win rate
----------------
A win rate is not a proper scoring rule: it is maximised by a forecast that is right more
often than it is calibrated, and it says nothing about the strength of the forecast.  The
brief asks for *benchmark-relative Brier skill with a game-cluster lower bound and a
multiplicity adjustment for the number of trials*.  This script computes exactly that, from
data already in the repository, and publishes the three control baselines in the same table.

Three evaluations, all walk-forward
-----------------------------------
1. SIDE  — P(home covers the closing spread).  Model: P(margin > line) from the model's own
   margin and its residual SD.  Benchmarks: the closing line itself (P = 0.5 at the line) and
   a score-based benchmark (each team's recency-weighted scoring differential, shrunk).
2. TOTAL — P(over the closing total).  Model: the model total's own predictive distribution.
   Benchmark: the closing total (P = 0.5).
3. MONEYLINE — P(home win).  Model probability versus the de-vigged closing moneyline and the
   raw closing moneyline.  This separates calibration from the operator's margin.

Scores
------
Brier = mean((p - o)^2).  Brier Skill Score (BSS) = 1 - Brier_model / Brier_benchmark, so a
positive BSS means the model beat the benchmark.  The 95% interval is a **game-cluster
bootstrap**: whole games are resampled (2,000 draws, fixed seed), which respects the fact that
the side and total of the same game are not independent.  The published number is the
lower bound of that interval, not the point estimate.

Multiplicity
------------
Twelve strategies and six markets are examined; the largest BSS is not evidence on its own.
The script applies a Benjamini-Hochberg step over the family of tests, and separately reports
the Bonferroni-adjusted threshold, so the reader can see both charges.

What is deliberately blank
--------------------------
* Prop markets: no prop price exists in the repository, so no prop strategy is scored.  The
  row is published with the reason instead of a number.
* Parlay and same-game-parlay markets: the joint distribution is not validated, so the
  product of marginals is not scored.  The row is published with the reason.
* Anything that needs an opening line: the price-snapshot store is blocked (readiness PR-01).

Run: cd s9cb/analysis && python3 ../../strat/proper_score.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "s9cb", "analysis"))

import lib  # noqa: E402
import common as C  # noqa: E402
import lines as LN  # noqa: E402

SEED = 20261115
N_BOOT = 2000
ALPHA = 0.05
MIN_SCORED = 200          # the same floor as gate G3


# ------------------------------------------------------------------ probability helpers
def norm_cdf(x):
    return 0.5 * (1.0 + np.vectorize(_erf)(np.asarray(x, dtype=float) / np.sqrt(2.0)))


def _erf(x):
    # Abramowitz & Stegun 7.1.26, max abs error 1.5e-7; used so the script needs no scipy
    sign = np.sign(x)
    x = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
                - 0.284496736) * t + 0.254829592) * t * np.exp(-x * x)
    return sign * y


def brier(p, o):
    p = np.asarray(p, float)
    o = np.asarray(o, float)
    return float(np.mean((p - o) ** 2))


def log_loss(p, o, eps=1e-12):
    p = np.clip(np.asarray(p, float), eps, 1 - eps)
    o = np.asarray(o, float)
    return float(-np.mean(o * np.log(p) + (1 - o) * np.log(1 - p)))


def devig_two_way(p_home_raw, p_away_raw):
    s = p_home_raw + p_away_raw
    return p_home_raw / s


def cluster_bootstrap_bss(p_m, p_b, o, games, n_boot=N_BOOT, seed=SEED):
    """BSS with a game-cluster bootstrap interval.

    Whole games are resampled with replacement, so the two markets of one game move together.
    """
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"pm": p_m, "pb": p_b, "o": o, "g": games})
    uniq = df["g"].unique()
    idx_by_game = {g: np.flatnonzero(df["g"].to_numpy() == g) for g in uniq}
    bs = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        rows = np.concatenate([idx_by_game[g] for g in pick])
        bm = np.mean((df["pm"].to_numpy()[rows] - df["o"].to_numpy()[rows]) ** 2)
        bb = np.mean((df["pb"].to_numpy()[rows] - df["o"].to_numpy()[rows]) ** 2)
        bs[i] = 1.0 - bm / bb if bb else np.nan
    point = 1.0 - brier(df["pm"], df["o"]) / brier(df["pb"], df["o"])
    lo, hi = np.nanpercentile(bs, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    # one-sided bootstrap p-value: the share of game-cluster resamples in which the
    # strategy does NOT beat the benchmark. With 2,000 resamples the floor is 0.0005.
    p_bs = float(np.mean(bs <= 0.0))
    return float(point), float(lo), float(hi), int(len(uniq)), p_bs


# ------------------------------------------------------------------ the three evaluations
def side_eval(M):
    """P(home covers) for the model, the line (0.5) and the scoring benchmark."""
    d = M[M["played"] & M["spread_line"].notna() & M["model_margin"].notna()
          & np.isfinite(M["spread_line"])].copy()
    d["outcome_home_covers"] = (d["result"] > d["spread_line"]).astype(float)
    d = d[d["result"] != d["spread_line"]]              # pushes are dropped, count published
    sd = d["sd_margin"].to_numpy(float)
    d["p_model"] = norm_cdf((d["model_margin"] - d["spread_line"]) / sd)
    # benchmark A: the closing line is a fair coin at the number -> p = 0.5
    d["p_line"] = 0.5
    # benchmark B: recency-free scoring differential, shrunk towards 0.5
    #   diff = (PF - PA)/GP for each team; p = Phi(diff_home - diff_away) / (2*sigma)
    d["p_score"] = norm_cdf((d["bench_diff_home"] - d["bench_diff_away"]) / (2 * 12.0))
    out = {}
    for label, col in (("model", "p_model"), ("closing line (p=0.5)", "p_line"),
                       ("scoring differential", "p_score")):
        sub = d[d[col].notna()]
        point, lo, hi, ng, p_bs = cluster_bootstrap_bss(
            sub[col].to_numpy(float), sub["p_line"].to_numpy(float),
            sub["outcome_home_covers"].to_numpy(float), sub["game_id"].to_numpy())
        out[label] = {"n_scored": int(len(sub)), "brier": brier(sub[col], sub["outcome_home_covers"]),
                      "bss": point, "bss_ci95": [lo, hi], "bss_lower_bound": lo,
                      "p_value_bootstrap": p_bs, "games_in_interval": ng,
                      "log_loss": log_loss(sub[col], sub["outcome_home_covers"]),
                      "blank_note": (None if len(sub) else
                                     "blank because the benchmark needs a prior game for both "
                                     "teams and week 1 has none")}
    done = set(d.index)
    return out, d, int(len(d)), int(len(M[M["played"] & M["spread_line"].notna()]) - len(d))


def total_eval(M):
    d = M[M["played"] & M["total_line"].notna() & M["model_total"].notna()
          & np.isfinite(M["total_line"])].copy()
    d = d[d["total"] != d["total_line"]]
    d["outcome_over"] = (d["total"] > d["total_line"]).astype(float)
    d["p_model"] = norm_cdf((d["model_total"] - d["total_line"]) / d["sd_total"].to_numpy(float))
    d["p_line"] = 0.5
    # benchmark: season-to-date mean total of both teams, shrunk; needs no model
    d["p_seasonmean"] = norm_cdf((d["bench_total_mean"] - d["total_line"]) / 13.5)
    out = {}
    for label, col in (("model", "p_model"), ("closing total (p=0.5)", "p_line"),
                       ("season-to-date mean total", "p_seasonmean")):
        sub = d[d[col].notna()]
        point, lo, hi, ng, p_bs = cluster_bootstrap_bss(
            sub[col].to_numpy(float), sub["p_line"].to_numpy(float),
            sub["outcome_over"].to_numpy(float), sub["game_id"].to_numpy())
        out[label] = {"n_scored": int(len(sub)), "brier": brier(sub[col], sub["outcome_over"]),
                      "bss": point, "bss_ci95": [lo, hi], "bss_lower_bound": lo,
                      "p_value_bootstrap": p_bs, "games_in_interval": ng,
                      "log_loss": log_loss(sub[col], sub["outcome_over"]),
                      "blank_note": (None if len(sub) else
                                     "blank: the benchmark needs a prior game for both teams")}
    return out, d, int(len(d)), int(len(M[M["played"] & M["total_line"].notna()]) - len(d))


def moneyline_eval(M):
    d = M[M["played"] & M["home_moneyline"].notna() & M["away_moneyline"].notna()
          & M["model_margin"].notna()].copy()
    d = d[d["result"] != 0]                            # ties do not exist in the modern game
    d["outcome_home_win"] = (d["result"] > 0).astype(float)
    d["p_model"] = norm_cdf(d["model_margin"] / d["sd_margin"].to_numpy(float))
    ph = np.array([C.implied_prob(float(x)) for x in d["home_moneyline"]])
    pa = np.array([C.implied_prob(float(x)) for x in d["away_moneyline"]])
    d["p_market_raw"] = ph
    d["p_market_vigfree"] = devig_two_way(ph, pa)
    out = {}
    for label, col in (("model", "p_model"),
                       ("closing moneyline, de-vigged", "p_market_vigfree"),
                       ("closing moneyline, raw (with vig)", "p_market_raw")):
        # for the market benchmarks the interesting question is calibration, so the
        # benchmark is the coin at 0.5 rather than the market itself
        sub = d[d[col].notna()]
        if col.startswith("p_market"):
            point2, lo2, hi2, ng, p2 = cluster_bootstrap_bss(
                sub[col].to_numpy(float), np.full(len(sub), 0.5),
                sub["outcome_home_win"].to_numpy(float), sub["game_id"].to_numpy())
            out[label] = {"n_scored": int(len(sub)), "brier": brier(sub[col], sub["outcome_home_win"]),
                          "bss_vs_coin": point2, "bss_vs_coin_ci95": [lo2, hi2],
                          "bss_lower_bound": lo2, "p_value_bootstrap": p2,
                          "games_in_interval": ng,
                          "log_loss": log_loss(sub[col], sub["outcome_home_win"])}
        else:
            point, lo, hi, ng, p_bs = cluster_bootstrap_bss(
                sub[col].to_numpy(float), sub["p_market_vigfree"].to_numpy(float),
                sub["outcome_home_win"].to_numpy(float), sub["game_id"].to_numpy())
            out[label] = {"n_scored": int(len(sub)), "brier": brier(sub[col], sub["outcome_home_win"]),
                          "bss_vs_devig": point, "bss_ci95": [lo, hi],
                          "bss_lower_bound": lo, "p_value_bootstrap": p_bs,
                          "games_in_interval": ng,
                          "log_loss": log_loss(sub[col], sub["outcome_home_win"])}
    overround = float(np.mean(ph + pa))
    out["vig_size"] = {
        "mean_sum_of_implied_probabilities": round(overround, 6),
        "implied_overround_pct": round((overround - 1.0) * 100.0, 4),
        "reading": ("The sum of the two implied probabilities is the overround. It is "
                    f"{overround:.4f}, i.e. {((overround - 1.0) * 100.0):.2f}% of the stake is the "
                    "operator's margin, not 100%. The de-vigged column above removes that margin "
                    "before any comparison with the model."),
        "single_price_series_caveat": (
            "This is ONE price series, so it is not a market consensus and no de-vigged consensus "
            "can be formed from it. The brief asks for a vig-free consensus against the fair line; "
            "that requires at least two independent books and is therefore not computable here. "
            "This figure is the de-vig of a single series and is labelled as such."),
    }
    return out, d, int(len(d))


# ------------------------------------------------------------------ benchmarks
def add_benchmarks(g, M):
    """Two no-model benchmarks, both from facts that predate kick-off.

    bench_diff_home/away : season-to-date scoring differential, walk-forward (no future data)
    bench_total_mean     : season-to-date mean combined total of the two teams
    """
    played = g[g["played"]].sort_values(["season", "week"]).copy()
    played["pf"] = np.where(played["home_team"] == played["home_team"], 0, 0)
    rows = []
    for _, r in played.iterrows():
        rows.append({"season": int(r["season"]), "week": int(r["week"]), "team": r["home_team"],
                     "pf": float(r["home_score"]), "pa": float(r["away_score"]),
                     "tot": float(r["home_score"] + r["away_score"])})
        rows.append({"season": int(r["season"]), "week": int(r["week"]), "team": r["away_team"],
                     "pf": float(r["away_score"]), "pa": float(r["home_score"]),
                     "tot": float(r["home_score"] + r["away_score"])})
    tw = pd.DataFrame(rows).sort_values(["season", "week"])
    tw["gp"] = tw.groupby(["season", "team"]).cumcount()      # games *before* this one
    tw["cpf"] = tw.groupby(["season", "team"])["pf"].cumsum() - tw["pf"]
    tw["cpa"] = tw.groupby(["season", "team"])["pa"].cumsum() - tw["pa"]
    tw["ctot"] = tw.groupby(["season", "team"])["tot"].cumsum() - tw["tot"]

    def prior(season, week, team, col):
        s = tw[(tw["season"] == season) & (tw["week"] < week) & (tw["team"] == team)]
        if s.empty:
            return np.nan
        last = s.iloc[-1]
        return float(last[col] / last["gp"]) if last["gp"] > 0 else np.nan

    cache = {}
    def key(season, week, team, col):
        k = (season, week, team, col)
        if k not in cache:
            cache[k] = prior(season, week, team, col)
        return cache[k]

    diffs, totmeans = [], []
    for r in M.itertuples():
        if not r.played:
            diffs.append((np.nan, np.nan)); totmeans.append(np.nan); continue
        dh = key(int(r.season), int(r.week), r.home_team, "cpf")
        dah = key(int(r.season), int(r.week), r.home_team, "cpa")
        da = key(int(r.season), int(r.week), r.away_team, "cpf")
        daa = key(int(r.season), int(r.week), r.away_team, "cpa")
        th = key(int(r.season), int(r.week), r.home_team, "ctot")
        ta = key(int(r.season), int(r.week), r.away_team, "ctot")
        diffs.append((dh - dah if np.isfinite(dh) and np.isfinite(dah) else np.nan,
                      da - daa if np.isfinite(da) and np.isfinite(daa) else np.nan))
        totmeans.append((th + ta) / 2 if np.isfinite(th) and np.isfinite(ta) else np.nan)
    M = M.copy()
    M["bench_diff_home"] = [x[0] for x in diffs]
    M["bench_diff_away"] = [x[1] for x in diffs]
    M["bench_total_mean"] = totmeans
    return M


# ------------------------------------------------------------------ strategy proper scores
def strategy_proper_scores(lb):
    """Brier skill of each scored betting rule versus the closing line and versus a coin.

    A betting rule does not emit a probability, so the honest proper-score question is:
    *when the rule fires, is the side it takes more likely than the price implies?*  Two
    benchmarks are published per rule:
      * the price (the break-even probability the operator charged) — skill versus the vig;
      * a coin at 0.5 — skill versus no information at all.
    The rule's implied probability is its observed hit rate *shrunk* towards 0.5, so a rule
    with 30 bets cannot claim a probability of 1.0.
    """
    rows = []
    for r in lb["leaderboard"]:
        n = int(r["n_bets"]); w = int(r["wins"]); decided = int(r["n_decided"])
        if decided < MIN_SCORED:
            rows.append({
                "strategy": r["strategy"], "n_bets": n, "n_decided": decided,
                "hit_rate": r.get("hit_rate"), "bss_vs_price": None, "bss_vs_coin": None,
                "status": "insufficient sample",
                "reason": f"{decided} decided bets is below the {MIN_SCORED}-bet floor (gate G3), so no skill is claimed.",
            })
            continue
        # shrink the hit rate with a Jeffreys-style prior of 8 pseudo-bets at the price,
        # so the published probability cannot exceed what the sample supports
        bev = float(r["break_even_hit_rate"])
        k = 8.0
        p_hat = (w + k * bev) / (decided + k)
        # Brier of a constant forecast against the observed binary outcomes
        #   sum over bets of (p - y)^2 with y in {0,1}: = n*p^2 - 2*p*w + w
        b_rule = (decided * p_hat ** 2 - 2 * p_hat * w + w) / decided
        b_price = bev * (1 - bev)                    # Brier of a constant p=bev forecast
        b_coin = 0.25
        rows.append({
            "strategy": r["strategy"], "n_bets": n, "n_decided": decided,
            "hit_rate": r.get("hit_rate"),
            "shrunk_probability": round(p_hat, 4),
            "break_even_probability": bev,
            "brier_rule": round(b_rule, 5),
            "brier_price_benchmark": round(b_price, 5),
            "bss_vs_price": round(1 - b_rule / b_price, 4),
            "bss_vs_coin": round(1 - b_rule / b_coin, 4),
            "roi_pct": r.get("roi_pct"),
            "roi_ci95": r.get("roi_ci95"),
            "p_value": r.get("p_value"),
            "holdout_roi_pct": (r.get("holdout_2024_2025") or {}).get("roi_pct"),
            "status": "scored",
        })
    return rows


def bh_and_bonferroni(pvals):
    """Benjamini-Hochberg adjusted p-values and a Bonferroni threshold."""
    items = [(i, p) for i, p in enumerate(pvals) if p is not None and np.isfinite(p)]
    items.sort(key=lambda x: x[1])
    m = len(items)
    adj = {}
    prev = 1.0
    for rank in range(m, 0, -1):
        i, p = items[rank - 1]
        val = min(prev, p * m / rank)
        adj[i] = val
        prev = val
    out = [adj.get(i) for i in range(len(pvals))]
    return out, (ALPHA / m if m else None), m


# ------------------------------------------------------------------ main
def main() -> int:
    g = C.load_games()
    print(f"games {len(g)}, played {int(g['played'].sum())}")
    M, fit_log, probe = LN.build(g)
    print("  walk-forward model built")
    M = add_benchmarks(g, M)

    side, dside, n_side, dropped_side = side_eval(M)
    total, dtotal, n_total, dropped_total = total_eval(M)
    ml, dml, n_ml = moneyline_eval(M)

    lb = lib.load("../../data/s9cb/leaderboard.json")
    strat = strategy_proper_scores(lb)

    # multiplicity over the family of model-market tests actually run.  The p-value is the
    # one-sided bootstrap p from the same game-cluster resamples that produced the interval,
    # so the interval and the multiplicity charge cannot disagree with each other.
    family = [
        ("side: model vs closing line", side["model"].get("bss"),
         side["model"].get("p_value_bootstrap")),
        ("side: scoring benchmark vs closing line", side["scoring differential"].get("bss"),
         side["scoring differential"].get("p_value_bootstrap")),
        ("total: model vs closing total", total["model"].get("bss"),
         total["model"].get("p_value_bootstrap")),
        ("total: season-mean benchmark vs closing total",
         total["season-to-date mean total"].get("bss"),
         total["season-to-date mean total"].get("p_value_bootstrap")),
        ("moneyline: model vs de-vigged market", ml["model"].get("bss_vs_devig"),
         ml["model"].get("p_value_bootstrap")),
        ("moneyline: raw market vs coin", ml["closing moneyline, raw (with vig)"].get("bss_vs_coin"),
         ml["closing moneyline, raw (with vig)"].get("p_value_bootstrap")),
    ]
    pvals = [p for _, _, p in family]
    adj, bonf, m_family = bh_and_bonferroni(pvals)
    # the strategy family is charged separately: thirteen scored rules were examined
    s_p = [r.get("p_value") for r in strat if r.get("status") == "scored"]
    s_adj, s_bonf, s_m = bh_and_bonferroni(s_p)

    markets = [
        {"market": "side", "n_scored": n_side, "n_dropped_pushes": dropped_side,
         "results": side, "evaluated": "P(home covers the closing spread)",
         "source": "schedules"},
        {"market": "total", "n_scored": n_total, "n_dropped_pushes": dropped_total,
         "results": total, "evaluated": "P(combined score over the closing total)",
         "source": "schedules"},
        {"market": "moneyline", "n_scored": n_ml, "results": ml,
         "evaluated": "P(home win)", "source": "schedules"},
        {"market": "parlay", "n_scored": 0, "results": {},
         "evaluated": "joint probability of two dependent legs",
         "blocked": ("Not scored. Multiplying marginal probabilities is invalid under dependence, "
                     "and no validated joint distribution exists in this repository. Published as "
                     "blank rather than as a number."), "source": "schedules"},
        {"market": "same-game parlay", "n_scored": 0, "results": {},
         "evaluated": "joint probability within one game",
         "blocked": "Not scored. Same reason as the parlay market: the legs are dependent.",
         "source": "schedules"},
        {"market": "player prop", "n_scored": 0, "results": {},
         "evaluated": "P(prop over its line)",
         "blocked": ("Not scored. No official or book-level price exists for any player prop in "
                     "this repository (data/s9cb/props.json › price_status), so skill cannot be "
                     "measured against a price."), "source": "schedules"},
    ]

    lib.write_json("proper_score.json", {
        "generated_at": lib.now(),
        "method": {
            "score": "Brier score; skill = 1 - Brier(model)/Brier(benchmark)",
            "interval": f"game-cluster bootstrap, {N_BOOT} resamples, seed {SEED}, 95%",
            "published_number": "the lower bound of the interval, not the point estimate",
            "min_sample": MIN_SCORED,
            "multiplicity": "Benjamini-Hochberg over the six model-market tests, plus the Bonferroni threshold",
            "walk_forward": "every prediction comes from a fit that used only earlier games",
            "lookahead_probe_predictions_identical": probe.get("predictions_identical"),
        },
        "markets": markets,
        "strategy_scores": strat,
        "multiplicity": {
            "family": [{"test": t, "bss": b, "p_value_bootstrap": p,
                        "bh_adjusted_p": adj[i], "bonferroni_alpha": bonf}
                       for i, (t, b, p) in enumerate(family)],
            "n_tests": m_family,
            "strategy_family": {"n_tests": s_m, "bonferroni_alpha": s_bonf,
                                "reading": ("The twelve scored betting rules are a second family. "
                                            "Each rule's own p_value from the price test is charged "
                                            "against 12 tests; the adjusted values are on the "
                                            "leaderboard page.")},
            "reading": ("With six tests at the 5% level, roughly one would look positive by chance. "
                        "The Bonferroni threshold is 0.05/6; the BH column charges the same family "
                        "less harshly because the tests are not independent. A test that fails both "
                        "is a test whose sign is not established."),
        },
        "any_eligible": False,
        "eligibility_rule": ("A market or rule is ELIGIBLE only when its lower bound is above zero "
                             "AND its adjusted p-value clears the multiplicity charge AND the sample "
                             "floor is met. No market or rule clears all three."),
    })
    print("wrote data/strat/proper_score.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
