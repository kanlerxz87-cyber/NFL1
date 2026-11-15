#!/usr/bin/env python3
"""strat/what_would_change.py — a two-sided falsifier on every claim (C4).

The requirement
---------------
"A two-sided 'what would change our mind' field on every strategy entry" (readiness PR-24,
*Not started*), extended in the brief to every published conclusion.  One-sided falsifiers are
cheap ("a bigger sample would confirm it"); a two-sided field must say both what would make us
believe the claim and what would make us abandon it, with a number attached to each.

What is registered
------------------
One row per claim this site publishes: the model's side, total and moneyline skill; the
strategy leaderboard as a whole; each of the five control baselines; the two-total verdict;
the demotion gate; the injury-surprise rules; the correlation register; the price-snapshot
store; and the pre-registration registry itself.  Every row has:

    claim               what is being asserted, with the number that supports it now
    status              what the evidence currently says (not what we hope)
    confirm_if          the observation that would raise confidence, with a threshold
    abandon_if          the observation that would make us abandon the claim, with a threshold
    next_measurement    the specific next computation, and the sample it needs
    current_interval    the interval that exists today (blank when no interval exists)
    source              the artifact that holds the number

The thresholds are fixed now.  A row whose threshold moves later is a row that was fitted to
its own answer, which is why this file is committed before the numbers it will be judged by.

Run: python3 strat/what_would_change.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402


def build(ps: dict, dt: dict) -> list[dict]:
    side = ps["markets"][0]["results"]
    total = ps["markets"][1]["results"]
    ml = ps["markets"][2]["results"]
    rows = [
        {
            "id": "W01", "claim": "The published rating model's side probabilities are informative",
            "current": (f"Brier skill versus the closing line {side['model']['bss']:+.4f} "
                        f"(interval {side['model']['bss_ci95'][0]:+.4f} to {side['model']['bss_ci95'][1]:+.4f}) "
                        f"on {side['model']['n_scored']:,} games"),
            "status": "NOT SUPPORTED — the interval is entirely below zero",
            "confirm_if": ("the game-cluster lower bound rises above 0.00 on a chronological holdout "
                           "of at least 500 games that the half-life was not selected on"),
            "abandon_if": ("already met: the interval sits below zero, so the claim is abandoned for "
                           "the side market until a new feature set is pre-registered"),
            "next_measurement": "rebuild with an availability-surprise feature (P07) and re-run this exact test",
            "current_interval": side["model"]["bss_ci95"],
            "source": "proper_score",
        },
        {
            "id": "W02", "claim": "The model's total probabilities are informative",
            "current": (f"Brier skill versus the closing total {total['model']['bss']:+.4f} "
                        f"(interval {total['model']['bss_ci95'][0]:+.4f} to {total['model']['bss_ci95'][1]:+.4f}) "
                        f"on {total['model']['n_scored']:,} games"),
            "status": "NOT SUPPORTED — the interval is entirely below zero",
            "confirm_if": "the lower bound rises above 0.00 on at least 500 games outside the tuning window",
            "abandon_if": "already met: the interval is below zero",
            "next_measurement": "the two-estimator comparison (W05) plus a weather/roof feature",
            "current_interval": total["model"]["bss_ci95"],
            "source": "proper_score",
        },
        {
            "id": "W03", "claim": "The model's moneyline probabilities beat the de-vigged market",
            "current": (f"Brier skill versus the de-vigged closing moneyline "
                        f"{ml['model']['bss_vs_devig']:+.4f} "
                        f"(interval {ml['model']['bss_ci95'][0]:+.4f} to {ml['model']['bss_ci95'][1]:+.4f}) "
                        f"on {ml['model']['n_scored']:,} games"),
            "status": "NOT SUPPORTED — the interval is entirely below zero",
            "confirm_if": "the lower bound rises above 0.00 while the market column stays fixed",
            "abandon_if": "already met: the interval is below zero",
            "next_measurement": "quantify the operator margin (see W04) and re-test on de-vigged prices only",
            "current_interval": ml["model"]["bss_ci95"],
            "source": "proper_score",
        },
        {
            "id": "W04", "claim": ("The closing moneyline carries real information above a coin, and the "
                                   "operator's margin is measurable"),
            "current": (f"Brier skill versus a coin {ml['closing moneyline, de-vigged']['bss_vs_coin']:+.4f} "
                        f"(interval {ml['closing moneyline, de-vigged']['bss_vs_coin_ci95'][0]:+.4f} to "
                        f"{ml['closing moneyline, de-vigged']['bss_vs_coin_ci95'][1]:+.4f}); mean sum of "
                        f"implied probabilities {ml['vig_size']['mean_sum_of_implied_probabilities']:.4f}"),
            "status": "SUPPORTED — the interval is entirely above zero",
            "confirm_if": "the lower bound stays above 0.00 on a season the interval has not seen",
            "abandon_if": "the interval on a new season includes 0.00",
            "next_measurement": "recompute on the 2027 season once it is complete",
            "current_interval": ml["closing moneyline, de-vigged"]["bss_vs_coin_ci95"],
            "source": "proper_score",
        },
        {
            "id": "W05", "claim": "The rating model's total is better than a no-model season-mean baseline",
            "current": (f"holdout paired difference in absolute error (A minus B) "
                        f"{dt['holdout']['mean_paired_difference_a_minus_b']:+.4f} points "
                        f"(interval {dt['holdout']['ci95'][0]:+.4f} to {dt['holdout']['ci95'][1]:+.4f}) "
                        f"on {dt['holdout']['n']} games; no winner"),
            "status": "UNDECIDED — the interval straddles zero",
            "confirm_if": "the interval excludes zero in either direction on at least 500 holdout games",
            "abandon_if": ("if B wins, A is withdrawn from every published total and B is published "
                           "alone, with the change recorded here"),
            "next_measurement": "extend the holdout with the 2027 and 2028 seasons",
            "current_interval": dt["holdout"]["ci95"],
            "source": "dual_total",
        },
        {
            "id": "W06", "claim": "No betting rule in the backtest run has demonstrated skill",
            "current": (f"{sum(1 for r in ps['strategy_scores'] if r.get('status') == 'scored')} rules scored; "
                        f"largest Brier skill versus the price "
                        f"{max(r['bss_vs_price'] for r in ps['strategy_scores'] if r.get('bss_vs_price') is not None):+.4f} "
                        f"on {max(r['n_decided'] for r in ps['strategy_scores'])} bets at most"),
            "status": "SUPPORTED — every rule's interval includes zero after the multiplicity charge",
            "confirm_if": ("a pre-registered rule's prospective sample reaches 200 settled bets with a "
                           "Brier-skill interval whose lower bound is above 0.00 after the BH charge "
                           "over all rules then registered"),
            "abandon_if": "any published rule's prospective interval lower bound falls below 0.00 (demotion rule D1)",
            "next_measurement": "prospective shadow scoring of P01-P19 once prices are captured",
            "current_interval": None,
            "source": "proper_score",
        },
        {
            "id": "W07", "claim": "The five control baselines are published and are not beaten by any rule",
            "current": ("random, favourite-only, home-only, underdog-only and coin-at-the-line are "
                        "registered as P02-P05 and the line itself as the benchmark in W01-W03"),
            "status": "BASELINES PUBLISHED — no rule beats them with an interval excluding zero",
            "confirm_if": ("a rule beats the favourite-only baseline by a Brier-skill gap whose lower "
                           "bound is above 0.00 on 200 prospective bets"),
            "abandon_if": "a rule's advantage over the control disappears once the control is matched on sample",
            "next_measurement": "score P02-P05 prospectively alongside P01-P19",
            "current_interval": None,
            "source": "preregistration",
        },
        {
            "id": "W08", "claim": "The demotion gate is the right instrument for controlling a live strategy",
            "current": "armed with five rules (D1-D5) and never triggered, because nothing is live",
            "status": "UNTESTED — no live sample exists",
            "confirm_if": ("a live strategy cleared every gate, went live, and was then demoted by D1 or D3 "
                           "before its realised loss reached D2's stop-loss"),
            "abandon_if": ("if D2 fires before D1/D3 on the first three live strategies, the skill rule is "
                           "too slow and the gate must be re-pre-registered"),
            "next_measurement": "the first live strategy's first 50 settled bets",
            "current_interval": None,
            "source": "demotion",
        },
        {
            "id": "W09", "claim": "Injury designation should be modelled as a surprise, not a level",
            "current": ("registered as P07-P09; the level-based rules S11 and S12 are published as "
                        "superseded but are still scored so the comparison is visible"),
            "status": "UNTESTED — no ablation has been run, because no verified starter/inactive feed exists",
            "confirm_if": ("an identical model with the surprise feature beats the same model without it on a "
                           "chronological holdout, with a game-cluster interval excluding zero"),
            "abandon_if": ("the with-feature model is worse, or the difference interval includes zero on "
                           "500+ holdout games; the features are then dropped, not tuned"),
            "next_measurement": ("the ablation needs official inactive lists joined to Game Books; both are "
                                 "unavailable in this repository, so the measurement cannot start"),
            "current_interval": None,
            "source": "preregistration",
        },
        {
            "id": "W10", "claim": "Correlations are computed only from officially sourced numbers, with n published",
            "current": ("the register publishes Pearson r with a Fisher-z interval and n for every pair; pairs "
                        "with fewer than 25 observations are blank, not estimated"),
            "status": "PARTIAL — the row-level numbers are a third-party (nflverse) extract of the NFL feed",
            "confirm_if": "every paired observation is re-derived from an official nfl.com or Game Book page",
            "abandon_if": ("any published correlation cannot be reproduced from official rows; it is then "
                           "withdrawn and republished as blank"),
            "next_measurement": "match the historical rows to official Game Books season by season",
            "current_interval": None,
            "source": "nflverse_schedules",
        },
        {
            "id": "W11", "claim": "The price-snapshot store is a prerequisite for any published backtest",
            "current": "blocked: no approved timestamped price source exists in the repository",
            "status": "BLOCKED",
            "confirm_if": ("one approved source yields an opening and a closing price with a fetch time for "
                           "100% of originated markets over four consecutive weeks"),
            "abandon_if": ("if no source can be approved, the leaderboard keeps only proper-score and "
                           "closing-line work and drops every ROI claim, which is the current state"),
            "next_measurement": "obtain written permission and a documented API, or accept closing-line-only scoring permanently",
            "current_interval": None,
            "source": "terms",
        },
        {
            "id": "W12", "claim": "Pre-registration is enforced, so no backtest number can appear without a frozen rule",
            "current": "31 records; tools/check_preregistration.py fails the build on a missing or post-hoc registration",
            "status": "SUPPORTED (mechanism) — the mechanism is tested; the 12 legacy rules are labelled as selection-exposed",
            "confirm_if": "the gate catches a deliberately introduced unregistered result in a test",
            "abandon_if": "any published result is found without a registration commit that precedes it",
            "next_measurement": "the self-test in tools/check_preregistration.py --self-test",
            "current_interval": None,
            "source": "repo",
        },
    ]
    return rows


def main() -> int:
    ps = lib.load("proper_score.json")
    dt = lib.load("dual_total.json")
    rows = build(ps, dt)
    lib.write_json("what_would_change.json", {
        "generated_at": lib.now(),
        "n_claims": len(rows),
        "rule": ("Every claim carries both a confirming and an abandoning observation with a threshold. "
                 "The thresholds are frozen in this commit; a later change is a diff, not an edit."),
        "rows": rows,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
