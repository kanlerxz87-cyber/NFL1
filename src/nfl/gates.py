"""Validation gates.

A strategy may not be staked, published as a pick, or promoted on the
leaderboard until every gate passes. A gate whose evidence does not exist yet
returns BLOCKED, which is fatal - BLOCKED is never treated as PASS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PASS, FAIL, BLOCKED = "PASS", "FAIL", "BLOCKED"

#: Minimum settled wagers per market type before any statistic is believed.
MIN_SAMPLES = {"single": 300, "parlay": 150, "player_prop": 200,
               "prop_combo": 150, "total": 300}
#: Minimum average closing-line value (points) to believe an edge is skill.
MIN_CLV_POINTS = 0.20
#: Minimum t-statistic on no-vig ROI after luck adjustment.
MIN_T = 3.0
#: Maximum share of total profit one fold may contribute.
MAX_SINGLE_FOLD_PROFIT_SHARE = 0.35
#: Minimum share of leave-one-out folds retaining the sign of the edge.
MIN_FOLD_SIGN_STABILITY = 0.70
#: Above this measured |rho| the independent-product parlay price is forbidden.
CORRELATION_PRICING_THRESHOLD = 0.15
#: Maximum tolerated out-of-sample degradation versus in-sample.
MAX_OOS_DEGRADATION = 0.40


@dataclass
class GateResult:
    gate_id: str
    name: str
    requirement: str
    status: str
    evidence: str = ""
    fatal: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {"gate_id": self.gate_id, "name": self.name,
                "requirement": self.requirement, "status": self.status,
                "evidence": self.evidence, "fatal": self.fatal}


@dataclass
class Evaluation:
    """Everything a gate is allowed to look at. Absent data stays None."""
    market_type: str = "single"
    bets: list[dict[str, Any]] = field(default_factory=list)
    odds_available: bool = False
    provenance_tiers: list[str] = field(default_factory=list)
    features_timestamped_before_kickoff: bool | None = None
    walk_forward_split_documented: bool | None = None
    insample_roi: float | None = None
    oos_roi: float | None = None
    oos_n: int | None = None
    roi_t: float | None = None
    roi_ci95: tuple[float, float] | None = None
    placebo_p: float | None = None
    fold_profits: list[float] = field(default_factory=list)
    measured_leg_correlations: list[float] = field(default_factory=list)
    clv_points: float | None = None
    avg_stake_limit: float | None = None
    model_stake: float | None = None

    @property
    def n(self) -> int:
        return len(self.bets)


def g1_provenance(e: Evaluation) -> GateResult:
    g = GateResult("G1", "Data provenance",
                   "Every input tier is VERIFIED or DERIVED from an official "
                   "source. A MODELED input may not drive a stake without "
                   "explicit human sign-off recorded on the Suggestions page.",
                   PASS, f"input tiers: {sorted(set(e.provenance_tiers)) or 'none'}")
    if not e.provenance_tiers:
        g.status, g.evidence = BLOCKED, "no inputs registered"
    elif "UNAVAILABLE" in e.provenance_tiers:
        g.status, g.evidence = FAIL, "an UNAVAILABLE input was referenced"
    elif "MODELED" in e.provenance_tiers:
        g.status, g.evidence = BLOCKED, ("strategy depends on an un-fitted analyst "
                                         "prior; sign-off required before staking")
    return g


def g2_sample(e: Evaluation) -> GateResult:
    need = MIN_SAMPLES.get(e.market_type, 300)
    g = GateResult("G2", "Sample size",
                   f"at least {need} settled wagers for market type "
                   f"'{e.market_type}'", PASS, f"n = {e.n}")
    if e.n < need:
        # An insufficient sample is BLOCKED, not FAILED: collecting more data
        # resolves it. REJECTED is reserved for a defect that more data cannot
        # fix, such as lookahead or an edge inside the noise. Retiring a
        # strategy for having only 100 wagers so far would be wrong.
        g.status = BLOCKED
        g.evidence = (f"n = {e.n} < required {need}"
                      + (" (no settled wagers exist)" if e.n == 0
                         else " (partial sample - resolvable by collecting more data)"))
    return g


def g3_no_lookahead(e: Evaluation) -> GateResult:
    g = GateResult("G3", "No lookahead / information timing",
                   "Every feature must be timestamped strictly before kickoff and "
                   "the walk-forward split must be documented. Injury data must be "
                   "the version available at the time of the bet, not the final "
                   "Friday report.", PASS, "")
    if e.features_timestamped_before_kickoff is None or e.walk_forward_split_documented is None:
        g.status, g.evidence = BLOCKED, "no timestamped feature history exists"
    elif not (e.features_timestamped_before_kickoff and e.walk_forward_split_documented):
        g.status, g.evidence = FAIL, "lookahead detected or split undocumented"
    return g


def g4_out_of_sample(e: Evaluation) -> GateResult:
    g = GateResult("G4", "Out-of-sample measurement",
                   f"OOS no-vig ROI measured on held-out games, and degradation "
                   f"vs in-sample <= {MAX_OOS_DEGRADATION:.0%}", PASS, "")
    if e.oos_roi is None or e.insample_roi is None:
        g.status, g.evidence = BLOCKED, "no held-out results exist"
        return g
    if abs(e.insample_roi) < 1e-9:
        g.status, g.evidence = FAIL, "in-sample ROI is zero - nothing to compare"
        return g
    deg = 1.0 - e.oos_roi / e.insample_roi
    g.evidence = (f"in-sample {e.insample_roi:+.4f}, OOS {e.oos_roi:+.4f}, "
                  f"degradation {deg:.1%}")
    if deg > MAX_OOS_DEGRADATION or e.oos_roi <= 0:
        g.status = FAIL
    return g


def g5_luck_removed(e: Evaluation) -> GateResult:
    g = GateResult("G5", "Luck removed",
                   f"t-statistic on no-vig ROI >= {MIN_T}, the 95% bootstrap CI "
                   f"excludes zero, and the permutation placebo p <= 0.05", PASS, "")
    if e.roi_t is None or e.roi_ci95 is None or e.placebo_p is None:
        g.status, g.evidence = BLOCKED, "no settled outcomes to resample"
        return g
    lo, hi = e.roi_ci95
    reasons = []
    if e.roi_t < MIN_T:
        reasons.append(f"t = {e.roi_t:.2f} < {MIN_T}")
    if not (lo > 0 or hi < 0):
        reasons.append(f"95% CI [{lo:+.4f}, {hi:+.4f}] contains zero")
    if e.placebo_p > 0.05:
        reasons.append(f"placebo p = {e.placebo_p:.3f} > 0.05")
    g.evidence = "; ".join(reasons) or (
        f"t = {e.roi_t:.2f}, CI [{lo:+.4f}, {hi:+.4f}], placebo p = {e.placebo_p:.4f}")
    if reasons:
        g.status = FAIL
    return g


def g6_vig(e: Evaluation) -> GateResult:
    g = GateResult("G6", "Vig-adjusted edge",
                   "Edge must survive at POSTED prices, not only at de-vigged "
                   "fair prices. Beating the fair price while losing to the vig "
                   "is not an edge.", PASS, "")
    if not e.odds_available or e.n == 0:
        g.status, g.evidence = BLOCKED, "no posted odds were captured"
    return g


def g7_stability(e: Evaluation) -> GateResult:
    g = GateResult("G7", "Stability / no single-source dependence",
                   f"sign of edge retained in >= {MIN_FOLD_SIGN_STABILITY:.0%} of "
                   f"leave-one-out folds and no fold contributes more than "
                   f"{MAX_SINGLE_FOLD_PROFIT_SHARE:.0%} of total profit", PASS, "")
    if not e.fold_profits:
        g.status, g.evidence = BLOCKED, "no fold decomposition exists"
        return g
    total = sum(e.fold_profits)
    sign_ok = sum(1 for f in e.fold_profits if (f > 0) == (total > 0)) / len(e.fold_profits)
    share = max(abs(f) for f in e.fold_profits) / abs(total) if total else 1.0
    g.evidence = f"{len(e.fold_profits)} folds, sign stability {sign_ok:.1%}, max fold share {share:.1%}"
    if sign_ok < MIN_FOLD_SIGN_STABILITY or share > MAX_SINGLE_FOLD_PROFIT_SHARE:
        g.status = FAIL
    return g


def g8_correlation_control(e: Evaluation) -> GateResult:
    g = GateResult("G8", "Correlation control (multi-leg bets)",
                   f"for parlays and prop combos, every leg pair's correlation "
                   f"must be MEASURED and priced. Independent-product pricing is "
                   f"forbidden when |rho| > {CORRELATION_PRICING_THRESHOLD}.",
                   PASS, "")
    if e.market_type in ("single", "total"):
        g.status = PASS
        g.evidence = "single-leg market: gate not applicable"
        g.fatal = False
        return g
    if not e.measured_leg_correlations:
        g.status, g.evidence = BLOCKED, ("no measured leg correlations exist; "
                                         "independent-product pricing would be an "
                                         "unverified assumption")
        return g
    worst = max(abs(r) for r in e.measured_leg_correlations)
    g.evidence = f"{len(e.measured_leg_correlations)} leg pairs measured, max |rho| = {worst:.3f}"
    return g


def g9_execution(e: Evaluation) -> GateResult:
    g = GateResult("G9", "Execution / capacity",
                   f"average closing-line value >= {MIN_CLV_POINTS} points and "
                   f"posted limits must absorb the model stake", PASS, "")
    if e.clv_points is None or e.avg_stake_limit is None or e.model_stake is None:
        g.status, g.evidence = BLOCKED, "no closing-line or limit history captured"
        return g
    g.evidence = f"CLV {e.clv_points:+.3f} pts, limit/stake {e.avg_stake_limit / max(e.model_stake, 1e-9):.1f}x"
    if e.clv_points < MIN_CLV_POINTS or e.avg_stake_limit < e.model_stake:
        g.status = FAIL
    return g


ALL_GATES = [g1_provenance, g2_sample, g3_no_lookahead, g4_out_of_sample,
             g5_luck_removed, g6_vig, g7_stability, g8_correlation_control,
             g9_execution]


def evaluate(e: Evaluation) -> dict[str, Any]:
    results = [fn(e) for fn in ALL_GATES]
    blocked = [r for r in results if r.status == BLOCKED and r.fatal]
    failed = [r for r in results if r.status == FAIL and r.fatal]
    if failed:
        verdict, reason = "REJECTED", "a fatal gate FAILED: " + ", ".join(r.gate_id for r in failed)
    elif blocked:
        verdict, reason = ("NOT_STAKEABLE",
                           "fatal gate(s) BLOCKED for lack of evidence: "
                           + ", ".join(r.gate_id for r in blocked))
    else:
        verdict, reason = "APPROVED", "all fatal gates PASS"
    return {"gates": [r.as_dict() for r in results], "verdict": verdict,
            "reason": reason,
            "passed": sum(1 for r in results if r.status == PASS),
            "blocked": len(blocked), "failed": len(failed)}
