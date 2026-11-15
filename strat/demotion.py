#!/usr/bin/env python3
"""strat/demotion.py — the demotion gate (C2).

The question
------------
A strategy can be promoted from paper to live only if it has cleared every gate.  The
inverse question — *what sends a live strategy back to paper?* — is the one that actually
controls risk, and the repository had no answer for it (readiness register PR-07 *Not
started*).  Without a demotion gate a strategy that got lucky once keeps being followed
until the money is gone.

The rule, frozen before it is applied
-------------------------------------
A strategy is **demoted to paper** when, on its live (prospective, post-registration) sample,
*any* of the following holds:

    D1  the lower bound of the 90% interval on its Brier skill versus the price falls below 0
        on at least the last 50 settled bets
    D2  its realised return over the live sample is below -10% with at least 50 settled bets
        (a stop-loss, not a test of skill)
    D3  the observed hit rate falls below the price-implied break-even by more than 2 standard
        errors on at least 100 settled bets
    D4  the run of consecutive losses reaches 12 (a variance guard that fires before D2 can)
    D5  the strategy's own pre-registered text has changed since the registration commit

Re-promotion requires a fresh prospective sample that clears D1-D3 in the opposite direction
over at least 200 settled bets.  The thresholds were chosen now, before any live bet exists,
and are printed here so that a later change is visible as a diff.

Why these numbers
-----------------
* 50 and 100 are the smallest samples at which a 5% Brier interval or a 2-standard-error hit
  rate test has any power at the effect sizes this repository can plausibly detect.
* -10% is roughly four times the largest per-bet edge any rule in the backtest run showed
  (the best backtest ROI is about +6%), so a live run that is 10% negative is not noise on
  the same scale.
* 12 losses in a row is the 1-in-500 point of a fair coin at the prices these rules take
  (0.52^12 ≈ 1/3,300 at 52%, and much likelier at shorter prices), so it is a guard against a
  broken feed as much as against bad luck.

Honest state
------------
Every strategy in the registry is at status **paper**: no live bet has been recorded, because
no live bet can exist until prices are captured prospectively (the price store is blocked,
readiness PR-01).  The gate is therefore published as *armed and never yet triggered*, and the
table says so rather than leaving the reader to infer it.

Run: python3 strat/demotion.py
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

RULES = [
    {"id": "D1", "name": "skill interval collapses",
     "test": "90% interval on Brier skill vs the price has a lower bound < 0",
     "minimum_sample": 50, "measured_on": "live (post-registration, settled) bets",
     "rationale": "50 settled bets is the smallest sample at which the interval has any power at realistic edges."},
    {"id": "D2", "name": "stop-loss",
     "test": "realised return < -10%",
     "minimum_sample": 50, "measured_on": "live (post-registration, settled) bets",
     "rationale": "About four times the best backtest ROI in the run, so a live -10% is not the same scale of noise."},
    {"id": "D3", "name": "hit rate below break-even",
     "test": "hit rate < price-implied break-even - 2 standard errors",
     "minimum_sample": 100, "measured_on": "live (post-registration, settled) bets",
     "rationale": "100 bets is the smallest sample at which a 2-SE gap can resolve a 2-point edge."},
    {"id": "D4", "name": "losing streak",
     "test": "12 consecutive settled losses",
     "minimum_sample": 12, "measured_on": "live (post-registration, settled) bets",
     "rationale": "Roughly the 1-in-500 point of a fair sequence at the prices these rules take; fires before D2 can."},
    {"id": "D5", "name": "definition drift",
     "test": "the rule text or inputs differ from the registration commit",
     "minimum_sample": 0, "measured_on": "the registration record",
     "rationale": "A rule whose text changed after its result was seen is a new rule and must start at paper."},
]

REPROMOTION = {
    "requires": "a fresh prospective sample, 200 settled bets, clearing D1-D3 in the opposite direction",
    "why": "The same sample that demoted a strategy cannot also promote it; that is the definition of chasing.",
}


def main() -> int:
    pre = lib.load("preregistration.json")
    ps = lib.load("proper_score.json")
    scores = {r["strategy"]: r for r in ps["strategy_scores"]}

    rows = []
    for rec in pre["records"]:
        key = f"{rec['id']} {rec['name']}"
        sc = scores.get(key)
        # live sample: this repository has none.  Recorded as zero, not as "unknown".
        live_settled = 0
        status = "PAPER"
        reason = ("No live bet exists: the price-snapshot store is blocked (readiness PR-01), so no "
                  "prospective price has ever been captured. The gate has never been triggered.")
        backtest_note = None
        if sc and sc.get("status") == "scored":
            backtest_note = {
                "n_decided_backtest": sc["n_decided"],
                "bss_vs_price_backtest": sc.get("bss_vs_price"),
                "roi_pct_backtest": sc.get("roi_pct"),
                "reading": ("The backtest sample is not a live sample. It is shown so the reader can "
                            "see the scale of the rule's historical result, and it cannot promote or "
                            "demote anything under this gate."),
            }
        elif sc and sc.get("status") == "insufficient sample":
            backtest_note = {"n_decided_backtest": sc.get("n_decided"),
                             "reading": "Below the 200-bet floor; no skill claimed."}
        rows.append({
            "id": rec["id"], "strategy": key, "registration_status": rec["status"],
            "status": status,
            "live_bets_settled": live_settled,
            "triggered_by": None,
            "reason": reason,
            "backtest": backtest_note,
            "source": "schedules",
        })

    lib.write_json("demotion.json", {
        "generated_at": lib.now(),
        "rules": RULES,
        "repromotion": REPROMOTION,
        "any_strategy_live": False,
        "n_strategies": len(rows),
        "n_live": 0,
        "n_paper": len(rows),
        "n_demotions_ever": 0,
        "state_note": ("The gate is armed and has never fired, because nothing is live. This is a "
                       "statement about the repository, not about the strategies: a paper strategy "
                       "cannot be demoted, and calling one of these 'live' would be an unverified "
                       "claim."),
        "rows": rows,
    })

    # a compact register for the page: the rule itself, with its numbers
    lib.write_json("demotion_rules.json", {"generated_at": lib.now(), "rules": RULES,
                                           "repromotion": REPROMOTION})
    return 0


if __name__ == "__main__":
    sys.exit(main())
