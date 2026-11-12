"""Strategy catalogue: singles, parlays and player-prop combos.

Each entry states its hypothesis, the exact inputs it needs, and its live gate
verdict. Nothing here is a tip. A strategy is a testable claim, and until it
passes every gate its verdict reads NOT_STAKEABLE.
"""
from __future__ import annotations

from typing import Any

from . import gates

#: market_type, hypothesis, inputs, skill_basis, luck_removal, current verdict
CATALOGUE: list[dict[str, Any]] = [
    # ---------------- SINGLES ----------------
    dict(id="S1", market="single", market_type="single",
         name="Pythagorean regression (fade the lucky)",
         hypothesis="Teams whose published win percentage exceeds their "
                    "Pythagorean expectation are being over-rated by the market; "
                    "teams below expectation are under-rated. Betting against the "
                    "lucky and with the unlucky captures mean reversion.",
         inputs=["pyth_delta", "closing_spread"],
         skill_basis="Point differential is the skill component of a record; the "
                     "gap to actual wins is the luck component. This is the most "
                     "direct available implementation of 'remove luck'.",
         luck_removal="The signal IS a luck estimate, so the strategy must also "
                      "pass the placebo test: shuffled pyth_delta must produce no "
                      "edge.",
         blockers=["closing_spread"],
         inputs_available_now=["pyth_delta"]),
    dict(id="S2", market="single", market_type="single",
         name="Confirmed QB disruption",
         hypothesis="When an official NFL.com news item confirms a starting-QB "
                    "change, IR placement or a starter ruled out, the market "
                    "under-reacts to the size of the downgrade when the replacement "
                    "is a 3rd/4th-string or first-career-start player.",
         inputs=["qb_disruption", "string_level_drop", "closing_spread"],
         skill_basis="QB is the highest-leverage position in the sport; a verified "
                     "starter change is a discrete, timestampable, non-random event.",
         luck_removal="Permutation test on QB-change games only; edge must survive "
                      "leave-one-team-out so it is not one franchise's season.",
         blockers=["string_level_drop", "closing_spread"],
         inputs_available_now=["qb_disruption"],
         verified_instances_week10=["CLE (Watson to start)", "AZ (Beck to start)",
                                    "MIA (Willis to IR, McCord in line)",
                                    "SEA (Darnold ruled out, Lock to start)"]),
    dict(id="S3", market="single", market_type="single",
         name="Defensive absence cluster",
         hypothesis="A team with an unusually large cluster of defensive DNPs "
                    "relative to its own season baseline concedes more than the "
                    "market expects; bet the opponent's team total over.",
         inputs=["def_dnp", "closing_spread", "snap_share"],
         skill_basis="Deficiency tracking is mechanical and available before kickoff.",
         luck_removal="Baseline-relative z-score, then bootstrap CI across weeks.",
         blockers=["closing_spread", "snap_share"],
         inputs_available_now=["def_dnp"]),
    dict(id="S4", market="single", market_type="single",
         name="Streak fade (public-bias contrarian)",
         hypothesis="Recreational money chases visible streaks, so teams on long "
                    "win streaks are over-priced and teams on long losing streaks "
                    "are under-priced.",
         inputs=["streak_signed", "closing_spread"],
         skill_basis="A behavioural bias, not a performance signal - the most "
                     "durable class of edge because it does not decay with data.",
         luck_removal="Must hold separately in each of the last three seasons; a "
                      "one-season result is indistinguishable from noise.",
         blockers=["closing_spread"], inputs_available_now=["streak_signed"]),
    dict(id="S5", market="total", market_type="total",
         name="Home-advantage mispricing",
         hypothesis="In the 2026 season to date home teams win 49.63% of games "
                    "(Wilson 95% CI 41.4%-57.9%, n=136 home games). If the market "
                    "still prices home field near the historical ~2.5 points, home "
                    "favourites are over-priced.",
         inputs=["home_win_pct", "closing_spread"],
         skill_basis="Uses a verified league-wide statistic rather than a "
                     "single-team story.",
         luck_removal="Wilson interval already published; the CI currently includes "
                      "50%, so this hypothesis is NOT yet supported and must not be "
                      "staked on. Stated as a research lead only.",
         blockers=["closing_spread"],
         inputs_available_now=["home_win_pct", "home_win_rate_league"]),
    dict(id="S6", market="total", market_type="total",
         name="Divisional rematch under",
         hypothesis="Third and fourth meetings between divisional opponents in the "
                    "same season produce lower totals than the market line.",
         inputs=["game_level_totals", "closing_total", "schedule"],
         skill_basis="Familiarity effect; testable on schedule structure alone.",
         luck_removal="Split by meeting number; require monotonic pattern.",
         blockers=["game_level_totals", "closing_total"], inputs_available_now=[]),
    # ---------------- PARLAYS ----------------
    dict(id="P1", market="parlay", market_type="parlay",
         name="Same-game script: favourite + under",
         hypothesis="When a strong favourite is also expected to control the clock, "
                    "the moneyline and the under are positively correlated, and the "
                    "book's independent-product parlay price under-states the joint "
                    "probability.",
         inputs=["closing_spread", "closing_total", "measured_leg_correlation",
                 "game_script_features"],
         skill_basis="Correlation is the ONLY legitimate source of parlay edge; a "
                     "parlay of independent legs always inherits the multiplied vig.",
         luck_removal="Joint probability must be recomputed with the MEASURED rho "
                      "(odds.parlay_fair_prob), never the independent product.",
         blockers=["closing_spread", "closing_total", "measured_leg_correlation"],
         inputs_available_now=[]),
    dict(id="P2", market="parlay", market_type="parlay",
         name="QB-change stack",
         hypothesis="Pair a fade of the team losing its starting QB with the "
                    "opponent's team-total over; the two legs share one causal "
                    "driver and are positively correlated.",
         inputs=["qb_disruption", "string_level_drop", "closing_spread",
                 "team_total_odds", "measured_leg_correlation"],
         skill_basis="Shared causal driver is the cleanest form of legitimate "
                     "parlay correlation.",
         luck_removal="Requires the measured rho between the two legs; without it "
                      "G8 blocks the bet.",
         blockers=["string_level_drop", "closing_spread", "team_total_odds",
                   "measured_leg_correlation"],
         inputs_available_now=["qb_disruption"]),
    dict(id="P3", market="parlay", market_type="parlay",
         name="Low-correlation diversifier",
         hypothesis="Two edges whose signals are measured to be near-independent "
                    "can be parlayed purely to reduce variance, provided the "
                    "combined price still beats the multiplied vig.",
         inputs=["pairwise_signal_correlation", "closing odds on both legs"],
         skill_basis="Explicitly correlation-controlled: only pairs with measured "
                     "|rho| below the pricing threshold are eligible.",
         luck_removal="Variance reduction is the point, so the gate is that the "
                      "measured CI narrows rather than the point estimate rising.",
         blockers=["closing odds on both legs"],
         inputs_available_now=["pairwise_signal_correlation"]),
    # ---------------- PLAYER PROPS AND COMBOS ----------------
    dict(id="X1", market="player_prop", market_type="player_prop",
         name="Opportunity transfer",
         hypothesis="When a starter is officially designated Out, the market "
                    "under-adjusts the replacement's prop line, especially when the "
                    "replacement is a 3rd or 4th string whose snap share is not yet "
                    "priced in.",
         inputs=["out_count", "string_level_drop", "snap_share", "player_prop_line",
                 "player_game_logs"],
         skill_basis="Opportunity is the primary driver of prop output; a confirmed "
                     "Out is a verified, non-random event.",
         luck_removal="Requires prop-line history to compute CLV on the prop itself.",
         blockers=["string_level_drop", "snap_share", "player_prop_line",
                   "player_game_logs"], inputs_available_now=["out_count"]),
    dict(id="X2", market="prop_combo", market_type="prop_combo",
         name="Pass-volume stack vs missing cornerback",
         hypothesis="When an opposing starting cornerback is Out, the QB passing-yard "
                    "over and the lead WR reception over are positively correlated "
                    "and the combo is mispriced as independent.",
         inputs=["out_count by position", "string_level_drop", "player_prop_line",
                 "measured_leg_correlation"],
         skill_basis="Position-specific absence plus a shared causal driver.",
         luck_removal="G8 requires the measured rho; independent pricing is forbidden.",
         blockers=["string_level_drop", "player_prop_line", "measured_leg_correlation"],
         inputs_available_now=["out_count", "position_breakdown"]),
    dict(id="X3", market="player_prop", market_type="player_prop",
         name="Rush-attempt transfer",
         hypothesis="With the lead back Out, the backup's rush-attempt prop is "
                    "under-priced because the market anchors on the backup's "
                    "season-to-date volume rather than the transferred opportunity.",
         inputs=["out_count by position", "snap_share", "player_prop_line",
                 "player_game_logs"],
         skill_basis="Direct opportunity accounting.",
         luck_removal="Bootstrap over games, not over yards.",
         blockers=["snap_share", "player_prop_line", "player_game_logs"],
         inputs_available_now=["out_count"]),
    dict(id="X4", market="prop_combo", market_type="prop_combo",
         name="Negative-correlation guard",
         hypothesis="Not an edge - a veto. Any combo whose legs are measured to be "
                    "negatively correlated must be refused regardless of headline "
                    "payout, because the true joint probability is below the "
                    "independent product.",
         inputs=["measured_leg_correlation"],
         skill_basis="Loss avoidance is a skill; this gate stops the most common "
                     "parlay mistake.",
         luck_removal="Deterministic arithmetic, no sampling error.",
         blockers=["measured_leg_correlation"], inputs_available_now=[]),
]


def build(correlation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Attach a live gate verdict to every catalogue entry."""
    out = []
    for s in CATALOGUE:
        # Today's honest evaluation: no settled wagers, no odds, no timestamped
        # feature history. Some inputs depend on MODELED priors.
        tiers = ["DERIVED"]
        if s["id"] in ("S3", "X1", "X2", "X3"):
            tiers.append("MODELED")
        if s["inputs_available_now"]:
            tiers.append("VERIFIED")
        ev = gates.Evaluation(
            market_type=s["market_type"], bets=[], odds_available=False,
            provenance_tiers=tiers,
            features_timestamped_before_kickoff=None,
            walk_forward_split_documented=None,
            measured_leg_correlations=(correlation or {}).get("leg_pairs", []),
        )
        verdict = gates.evaluate(ev)
        out.append({**s, "gate_summary": verdict,
                    "n_settled_wagers": 0,
                    "roi_no_vig": None, "clv_points": None,
                    "leaderboard_score": None,
                    "blocked_inputs": s["blockers"],
                    "inputs_available_now": s["inputs_available_now"]})
    return {"strategies": out,
            "counts": {
                "total": len(out),
                "singles": sum(1 for s in out if s["market"] == "single"),
                "totals": sum(1 for s in out if s["market"] == "total"),
                "parlays": sum(1 for s in out if s["market"] == "parlay"),
                "player_props": sum(1 for s in out if s["market"] == "player_prop"),
                "prop_combos": sum(1 for s in out if s["market"] == "prop_combo"),
                "approved": sum(1 for s in out if s["gate_summary"]["verdict"] == "APPROVED"),
                "rejected": sum(1 for s in out if s["gate_summary"]["verdict"] == "REJECTED"),
                "not_stakeable": sum(1 for s in out
                                     if s["gate_summary"]["verdict"] == "NOT_STAKEABLE"),
            }}
