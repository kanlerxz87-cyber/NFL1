"""Signal library.

A signal is a named, reproducible transformation of VERIFIED data. Each entry
declares its inputs, its provenance tier, and - critically - what it would take
to validate it. Signals whose required input does not exist are registered with
status BLOCKED and never produce a number.
"""
from __future__ import annotations

from typing import Any

from .provenance import DERIVED, MODELED, UNAVAILABLE, VERIFIED

SIGNAL_SPECS: list[dict[str, Any]] = [
    # ---- team efficiency, from official standings --------------------------
    dict(id="net_pg", name="Net points per game",
         definition="(PF - PA) / games played", inputs=["pf", "pa", "w", "l", "t"],
         tier=DERIVED, status="ACTIVE", unit="points",
         rationale="The single most stable public predictor of future margin; "
                   "point differential survives schedule noise far better than "
                   "win-loss record.",
         validation_needs="Game-level closing spreads to measure edge vs market."),
    dict(id="ppg", name="Points per game (offence)",
         definition="PF / games played", inputs=["pf", "w", "l", "t"],
         tier=DERIVED, status="ACTIVE", unit="points",
         rationale="Offensive output level; input to totals modelling.",
         validation_needs="Game-level totals and closing odds."),
    dict(id="papg", name="Points allowed per game (defence)",
         definition="PA / games played", inputs=["pa", "w", "l", "t"],
         tier=DERIVED, status="ACTIVE", unit="points",
         rationale="Defensive output level; input to totals and to team-total props.",
         validation_needs="Game-level totals and closing odds."),
    dict(id="pyth_win_pct", name="Pythagorean win percentage",
         definition="PF**k / (PF**k + PA**k), k fitted on the 32 official rows",
         inputs=["pf", "pa"], tier=DERIVED, status="ACTIVE", unit="proportion",
         rationale="Expected win rate given scoring, i.e. the skill component of "
                   "a team's record.",
         validation_needs="Full-season refit; k fitted on 8.5 games is unstable."),
    dict(id="pyth_delta", name="Pythagorean residual (luck proxy)",
         definition="pyth_win_pct - published win_pct", inputs=["pf", "pa", "w", "l", "t"],
         tier=DERIVED, status="ACTIVE", unit="proportion",
         rationale="Positive = under-performing its scoring (unlucky); negative = "
                   "over-performing (lucky). This is the primary luck-removal "
                   "instrument available from official data.",
         validation_needs="Game-level results to separate variance from bias."),
    dict(id="win_pct", name="Published winning percentage",
         definition="(W + 0.5*T) / (W + L + T) as printed by NFL.com",
         inputs=["w", "l", "t", "pct"], tier=VERIFIED, status="ACTIVE", unit="proportion",
         rationale="The market's most over-weighted statistic; used as a "
                   "contrast variable, not as an edge.",
         validation_needs="None - verified."),
    dict(id="home_win_pct", name="Home winning percentage",
         definition="HOME cell recomputed", inputs=["home"], tier=DERIVED,
         status="ACTIVE", unit="proportion",
         rationale="Splits home/road form; feeds venue adjustment.",
         validation_needs="Game-level venue results."),
    dict(id="road_win_pct", name="Road winning percentage",
         definition="ROAD cell recomputed", inputs=["road"], tier=DERIVED,
         status="ACTIVE", unit="proportion",
         rationale="Splits home/road form; feeds venue adjustment.",
         validation_needs="Game-level venue results."),
    dict(id="conf_win_pct", name="Conference winning percentage",
         definition="CONF PCT as printed", inputs=["conf", "conf_pct"], tier=VERIFIED,
         status="ACTIVE", unit="proportion", rationale="Strength of record context.",
         validation_needs="None - verified."),
    dict(id="div_win_pct", name="Division winning percentage",
         definition="DIV PCT as printed", inputs=["div", "div_pct"], tier=VERIFIED,
         status="PARTIAL", unit="proportion",
         rationale="Division form; the NFL's most schedule-correlated split.",
         caveat="The official DIV cell contradicts its own DIV PCT cell for IND "
                "and PHI (see Flagged for Review). Left blank for those two clubs.",
         validation_needs="Re-retrieval of the official standings page."),
    dict(id="streak_signed", name="Signed streak length",
         definition="+n for n consecutive wins, -n for n consecutive losses",
         inputs=["strk"], tier=DERIVED, status="ACTIVE", unit="games",
         rationale="Public-bias proxy: streaks are systematically over-priced by "
                   "recreational money.",
         validation_needs="Odds history to test the contrarian hypothesis."),
    # ---- availability, from the official injury report ---------------------
    dict(id="report_entries", name="Injury-report entries",
         definition="count of rows on nfl.com/injuries for the club this week",
         inputs=["injury_report"], tier=DERIVED, status="ACTIVE", unit="count",
         rationale="Report size is itself information: a large report usually "
                   "means a short week, a bad loss, or a real injury cluster.",
         validation_needs="Multiple weeks to separate report size from noise."),
    dict(id="dnp_count", name="Did-not-practice entries",
         definition="count of DNP rows", inputs=["injury_report"], tier=DERIVED,
         status="ACTIVE", unit="count", rationale="Strongest early-week absence signal.",
         validation_needs="Outcome data by week."),
    dict(id="lp_count", name="Limited-practice entries",
         definition="count of LP rows", inputs=["injury_report"], tier=DERIVED,
         status="ACTIVE", unit="count", rationale="Intermediate availability signal.",
         validation_needs="Outcome data by week."),
    dict(id="off_dnp", name="Offensive DNP entries",
         definition="count of DNP rows at an offensive position",
         inputs=["injury_report"], tier=DERIVED, status="ACTIVE", unit="count",
         rationale="Unit-specific absence load; feeds team-total and player-prop "
                   "adjustment.", validation_needs="Snap counts and depth charts."),
    dict(id="def_dnp", name="Defensive DNP entries",
         definition="count of DNP rows at a defensive position",
         inputs=["injury_report"], tier=DERIVED, status="ACTIVE", unit="count",
         rationale="Defensive absence load - the specific deficiency the brief "
                   "asks to track.", validation_needs="Snap counts and depth charts."),
    dict(id="out_count", name="Players designated Out",
         definition="count of rows with Game Status = Out", inputs=["injury_report"],
         tier=VERIFIED, status="ACTIVE", unit="count",
         rationale="Confirmed absences; the only availability fact that is certain "
                   "before kickoff.", validation_needs="None - verified."),
    dict(id="qb_entries", name="Quarterbacks on the report",
         definition="count of rows with position QB", inputs=["injury_report"],
         tier=DERIVED, status="ACTIVE", unit="count",
         rationale="QB availability dominates NFL variance more than any other "
                   "single position.", validation_needs="Depth charts for string level."),
    dict(id="qb_disruption", name="Confirmed QB disruption",
         definition="1 if an official NFL.com news item confirms a Week 10 starter "
                    "change, an IR placement or a starter ruled out; else 0",
         inputs=["nfl_news"], tier=VERIFIED, status="ACTIVE", unit="binary",
         rationale="Verified, binary, and the highest-leverage availability fact "
                   "obtainable without a depth chart.",
         validation_needs="Historical QB-change outcomes to size the line move."),
    dict(id="key_position_entries", name="Key-position entries",
         definition="count of rows at QB/T/C/DE/EDGE/CB/WR/RB",
         inputs=["injury_report"], tier=DERIVED, status="ACTIVE", unit="count",
         rationale="Weights the report toward positions that move lines.",
         validation_needs="Snap-share weighting."),
    dict(id="availability_pressure", name="Availability pressure index (unstringed)",
         definition="sum over entries of severity_weight x position_weight, plus "
                    "officially-confirmed QB/marquee news items",
         inputs=["injury_report", "nfl_news"], tier=MODELED, status="PROVISIONAL",
         unit="index",
         rationale="Single ranked number for 'how much talent is in doubt'.",
         caveat="Both weight tables are analyst priors, not fitted. No string-level "
                "weighting is applied because official depth charts are unavailable.",
         validation_needs="Depth charts + fitted weights on historical outcomes."),
    # ---- blocked: cannot be produced at all -------------------------------
    dict(id="string_level_drop", name="Depth-chart string drop",
         definition="1st-string starter replaced by 2nd/3rd/4th string",
         inputs=["depth_chart"], tier=UNAVAILABLE, status="BLOCKED", unit="levels",
         rationale="Directly answers the brief's request to know when a 2nd, 3rd "
                   "or 4th string backup replaces a starter.",
         blocked_reason="NFL.com publishes no public depth chart. The NFL's "
                        "official weekly depth-chart feed is Sportradar's "
                        "credential-gated NFL Official API.",
         resolving_source="https://developer.sportradar.com/football/reference/nfl-weekly-depth-charts"),
    dict(id="closing_spread", name="Closing point spread",
         definition="market closing line", inputs=["odds_feed"], tier=UNAVAILABLE,
         status="BLOCKED", unit="points",
         rationale="Without the closing line no edge, no CLV and no vig-adjusted "
                   "ROI can be computed - the whole leaderboard depends on it.",
         blocked_reason="No licensed odds/market-data provider is reachable or "
                        "credentialed from this environment.",
         resolving_source="A licensed odds API, or the NFL's own odds display on "
                          "individual game pages"),
    dict(id="closing_total", name="Closing total", definition="market closing over/under",
         inputs=["odds_feed"], tier=UNAVAILABLE, status="BLOCKED", unit="points",
         rationale="Required for totals strategies and for prop-combo pricing.",
         blocked_reason="No licensed odds feed reachable.",
         resolving_source="A licensed odds API"),
    dict(id="player_prop_line", name="Player projection line",
         definition="market line for a player prop (yards, TDs, receptions)",
         inputs=["odds_feed", "player_stats"], tier=UNAVAILABLE, status="BLOCKED",
         unit="varies", rationale="Required for every player-prop combo strategy.",
         blocked_reason="No prop odds feed and no per-game player stat log reachable.",
         resolving_source="A licensed prop odds API plus official NFL.com player "
                          "game logs"),
    dict(id="snap_share", name="Snap share", definition="offensive/defensive snap percentage",
         inputs=["snap_counts"], tier=UNAVAILABLE, status="BLOCKED", unit="proportion",
         rationale="Converts a depth-chart absence into an expected opportunity "
                   "transfer - the missing link for prop-combo correlation.",
         blocked_reason="NFL Next Gen Stats and official snap counts are not "
                        "reachable from this environment.",
         resolving_source="https://www.nfl.com/nextgenstats/ and the official "
                          "NFL game-centre feed"),
    dict(id="epa_per_play", name="EPA per play", definition="expected points added per play",
         inputs=["play_by_play"], tier=UNAVAILABLE, status="BLOCKED", unit="points",
         rationale="The standard play-level efficiency measure; far stronger than "
                   "points per game.",
         blocked_reason="Bulk play-by-play is distributed as GitHub release assets "
                        "which redirect to a host outside this environment's "
                        "network allowlist.",
         resolving_source="https://github.com/nflverse/nflverse-data releases "
                          "(pbp / stats_player)"),
]

#: Which signals are used as the target (y) in correlation screening.
TARGETS = ["win_pct", "pyth_delta"]


def build(ratings: dict[str, Any], avail: dict[str, Any]) -> dict[str, Any]:
    """Materialise every ACTIVE signal into a team x signal matrix."""
    m = {r["team_abbr"]: dict(r) for r in ratings["metrics"]}
    a = {r["team_abbr"]: dict(r) for r in avail["teams"]}
    teams = sorted(m)
    matrix: dict[str, dict[str, float | None]] = {t: {} for t in teams}
    for t in teams:
        r, v = m[t], a.get(t, {})
        c = v.get("counts", {})
        gs = v.get("game_status", {})
        du = v.get("dnp_by_unit", {})
        matrix[t].update({
            "net_pg": r.get("net_pg"), "ppg": r.get("ppg"), "papg": r.get("papg"),
            "pyth_win_pct": r.get("pyth_win_pct"), "pyth_delta": r.get("pyth_delta"),
            "win_pct": r.get("win_pct"), "home_win_pct": r.get("home_win_pct"),
            "road_win_pct": r.get("road_win_pct"), "conf_win_pct": r.get("conf_win_pct"),
            "div_win_pct": r.get("div_win_pct"),
            "streak_signed": r.get("streak_signed"),
            "report_entries": v.get("entries") if v else None,
            "dnp_count": c.get("DNP") if c else None,
            "lp_count": c.get("LP") if c else None,
            "off_dnp": du.get("OFF") if du else None,
            "def_dnp": du.get("DEF") if du else None,
            "out_count": gs.get("Out") if gs else None,
            "qb_entries": v.get("qb_entries") if v else None,
            "key_position_entries": v.get("key_position_entries") if v else None,
            "availability_pressure": v.get("availability_pressure_unstringed") if v else None,
            "qb_disruption": (1.0 if v.get("qb_disruption") else 0.0) if v else None,
        })
        # Availability is undefined for a club on bye: there is no report to read.
        if v.get("report_status") == "on bye (no report)":
            for f in ("report_entries", "dnp_count", "lp_count", "off_dnp", "def_dnp",
                      "out_count", "qb_entries", "key_position_entries",
                      "availability_pressure", "qb_disruption"):
                matrix[t][f] = None
    active = [s for s in SIGNAL_SPECS if s["status"] in ("ACTIVE", "PARTIAL", "PROVISIONAL")]
    return {"matrix": matrix, "teams": teams,
            "signal_ids": [s["id"] for s in active],
            "specs": SIGNAL_SPECS,
            "active": active,
            "blocked": [s for s in SIGNAL_SPECS if s["status"] == "BLOCKED"]}
