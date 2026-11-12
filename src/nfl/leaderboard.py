"""Leaderboard: skill-ranked, luck-adjusted, with a reward ladder.

The ranking statistic is deliberately a t-statistic rather than raw ROI. Raw ROI
ranks noise: a strategy that made 80% on eleven bets beats a strategy that made
9% on nine hundred, which is exactly backwards. Ranking on
    t = mean(no-vig ROI) / standard_error
means a strategy must be both good AND proven, and the sample size enters the
score directly. Two further multipliers punish instability and reward capacity.
"""
from __future__ import annotations

from typing import Any

from . import gates

#: Reward ladder. This is a PROPOSAL requiring owner sign-off, not a fact, and
#: it is published on the Suggestions page for review before it is enacted.
REWARD_TIERS: list[dict[str, Any]] = [
    dict(tier=1, name="Promote to live paper trading",
         requirement="All nine gates PASS, t >= 3.0, n >= 300, mean CLV >= +0.20 pts",
         reward="Allocated a live paper-trading bankroll in the tracking ledger; "
                "results published weekly on the Leaderboard page.",
         status="PROPOSAL - needs owner sign-off"),
    dict(tier=2, name="Extended validation",
         requirement="Gates G1-G7 PASS, t >= 2.0, n >= 200",
         reward="Granted a second held-out season of data for confirmation before "
                "any promotion.",
         status="PROPOSAL - needs owner sign-off"),
    dict(tier=3, name="Watchlist",
         requirement="Gates G1-G4 PASS",
         reward="Kept in the catalogue and re-scored weekly; no stake.",
         status="PROPOSAL - needs owner sign-off"),
    dict(tier=4, name="Retire",
         requirement="G3 FAIL (lookahead) or G5 FAIL (luck not removed) or "
                     "placebo p > 0.05",
         reward="Removed from the catalogue and archived with the reason recorded, "
                "so a rejected idea is never silently re-proposed.",
         status="PROPOSAL - needs owner sign-off"),
]

SCORING_FORMULA = (
    "leaderboard_score = t_statistic(no_vig_roi) x stability_multiplier x capacity_factor\n"
    "  t_statistic          = mean(no-vig ROI) / (sd(returns) / sqrt(n))\n"
    "  stability_multiplier = share of leave-one-week-out and leave-one-team-out\n"
    "                           folds that retain the sign of the edge, clipped to [0,1]\n"
    "  capacity_factor      = min(1, average posted limit / model stake)\n"
    "Gating: score is only published when gates G1-G7 PASS. A strategy that is\n"
    "NOT_STAKEABLE or REJECTED shows a blank score, never a zero, so that 'not\n"
    "measured' is never confused with 'measured and worthless'."
)


def score(strategy: dict[str, Any]) -> dict[str, Any]:
    g = strategy["gate_summary"]["verdict"]
    t = strategy.get("roi_t")
    stability = strategy.get("stability_multiplier")
    capacity = strategy.get("capacity_factor")
    if g != "APPROVED":
        return {"score": None, "tier": None, "published": False,
                "reason": f"gate verdict is {g}; score withheld, not zeroed",
                "gate_verdict": g}
    if None in (t, stability, capacity):
        return {"score": None, "tier": None, "published": False,
                "reason": "APPROVED but a scoring input is missing",
                "gate_verdict": g}
    s = round(t * max(0.0, min(1.0, stability)) * min(1.0, capacity), 4)
    tier = (1 if (t >= 3.0 and strategy.get("n", 0) >= 300
                  and (strategy.get("clv_points") or 0) >= gates.MIN_CLV_POINTS)
            else 2 if (t >= 2.0 and strategy.get("n", 0) >= 200)
            else 3 if t > 0 else 4)
    return {"score": s, "tier": tier, "published": True,
            "reason": "all fatal gates PASS", "gate_verdict": g}


def rank(strategies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for s in strategies:
        sc = score(s)
        scored.append({
            "strategy_id": s["id"], "name": s["name"], "market": s["market"],
            "gate_verdict": s["gate_summary"]["verdict"],
            "n_settled_wagers": s.get("n_settled_wagers", 0),
            "roi_no_vig": s.get("roi_no_vig"),
            "roi_t": s.get("roi_t"),
            "clv_points": s.get("clv_points"),
            "leaderboard_score": sc["score"],
            "reward_tier": sc["tier"],
            "score_withheld_reason": sc["reason"],
            "first_blocking_gate": next(
                (g["gate_id"] for g in s["gate_summary"]["gates"]
                 if g["status"] in ("FAIL", "BLOCKED") and g["fatal"]), None),
        })
    scored.sort(key=lambda r: (r["leaderboard_score"] is None,
                               -(r["leaderboard_score"] or 0.0), r["strategy_id"]))
    for i, r in enumerate(scored, 1):
        r["rank"] = i if r["leaderboard_score"] is not None else None
    return scored


def build(strategies: list[dict[str, Any]]) -> dict[str, Any]:
    return {"board": rank(strategies), "reward_tiers": REWARD_TIERS,
            "reward_tier_status": "PROPOSAL",
            "scoring_formula": SCORING_FORMULA,
            "scored_count": sum(1 for r in rank(strategies)
                                if r["leaderboard_score"] is not None),
            "withheld_count": sum(1 for r in rank(strategies)
                                  if r["leaderboard_score"] is None)}
