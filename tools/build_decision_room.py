#!/usr/bin/env python3
"""build_decision_room.py — turn the repository's own evidence into a decision dashboard.

The brief asks for a place where somebody can review suggestions and choose a path *before*
implementing anything, plus a clear list of questions, knowns, unknowns and answers that
have to be settled before a decision is reasonable. The repository already contains that
evidence in a dozen files. This script does the one thing that was missing: it puts a
single, honest verdict next to each decision, derived from the data rather than written by
hand, and it separates three kinds of decision that were being mixed together:

  1. FILLABLE   — needs no new data; a human must simply choose (data/fillable_decisions.json)
  2. BLOCKED    — cannot be decided until a named piece of information exists
  3. CONTRADICTION — the repository disagrees with an official page (data/contradictions.json)

Everything printed is recomputed here from the committed files. Nothing is hand-typed into
the HTML: if a number changes in data/model/, the dashboard changes with it, and
tools/verify_decision_room.py fails the build if a published figure stops reproducing.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVID = os.path.join(ROOT, "data", "evidence")
OUT = os.path.join(ROOT, "data", "decision_room")
BACKTEST_CACHE = os.path.join(OUT, "backtest_cache.json")


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def load_optional(path, default=None):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return default
    return load(path)


# --------------------------------------------------------------- the evidence
def evidence_inventory():
    """What the repository actually holds, counted from the files themselves."""
    st = load("data/evidence/standings_2026.json")["rows"]
    inj = load("data/evidence/injuries_week10.json")
    sch = load("data/evidence/schedule_week10.json")
    dep = load("data/evidence/depth_charts.json")["rows"]
    lines = load("data/model/lines.json")
    strat = load("data/model/strategies.json")
    avail = load("data/model/availability.json")
    ver = load_optional("data/audit/official_verification.json", {})
    prov = load_optional("data/model/provenance.json", {}).get("files", [])
    games = sum(r["w"] + r["l"] + r["t"] for r in st) // 2
    designations = sum(1 for r in inj["rows"] if r["game_status"])
    return dict(
        season=2026,
        week_complete=load("data/model/snapshot.json")["last_completed_week"],
        week_next=load("data/model/snapshot.json")["last_completed_week"] + 1,
        games_played=games,
        clubs=len(st),
        injury_rows=len(inj["rows"]),
        injury_club_sections=len({r["club"] for r in inj["rows"]}),
        injury_clubs_no_report=len(inj["no_injuries_reported"]),
        game_designations=designations,
        practice_only=len(inj["rows"]) - designations,
        fixtures=len(sch["rows"]),
        byes=len(sch["byes"]),
        depth_clubs=sorted({r["club"] for r in dep}),
        depth_slots=len({(r["club"], r["unit"], r["position"], r["player"]) for r in dep}),
        own_lines=len(lines["lines"]),
        strategies=len(strat["leaderboard"]),
        strategies_pass=sum(1 for r in strat["leaderboard"] if r.get("status") == "PASS"),
        strategies_watch=sum(1 for r in strat["leaderboard"] if r.get("status") == "WATCH"),
        strategies_fail=sum(1 for r in strat["leaderboard"] if r.get("status") == "FAIL"),
        gates=len(strat["gate_definitions"]),
        starters_flagged=avail["counts"]["starters_impacted"],
        depth_matched_rows=avail["counts"]["injury_records"],
        unmatched_records=avail["counts"]["records_not_matched_to_depth_chart"],
        source_files_pinned=len(prov),
        verification_checks=len(ver.get("checks", [])),
        verification_pass=ver.get("counts", {}).get("passed", 0),
        verification_flag=ver.get("counts", {}).get("flagged", 0),
        verification_fail=ver.get("counts", {}).get("failed", 0),
    )


# ------------------------------------------------- where the model actually stands
def model_verdict():
    """Read the out-of-sample evidence for the own-line model and state the consequence."""
    lines = load("data/model/lines.json")
    cal = {c["label"]: c for c in lines.get("calibration", [])}
    blend = lines.get("blend_test") or {}
    test = cal.get("test 2026", {})
    diff = test.get("spread_mae_diff_ci95") or [None, None]
    beats_market = (test.get("spread_mae_model") is not None
                    and test.get("spread_mae_market") is not None
                    and test["spread_mae_model"] < test["spread_mae_market"]
                    and diff[0] is not None and diff[1] < 0)
    weight = blend.get("weight_model")
    adds_info = weight is not None and weight > 0 and (
        blend.get("test_mae_hybrid", 1e9) < blend.get("test_mae_market_only", -1e9))
    if beats_market or adds_info:
        state, plain = "FAVOURABLE", (
            "The model beat the closing line out of sample, or added information to it. "
            "A model-first publication policy is defensible.")
    else:
        state, plain = "NOT SUPPORTED", (
            "The model lost to the closing line out of sample and the fitted weight on the "
            "model is at or below zero, so its disagreement with the market carried no "
            "information in the test window. Publishing a model-vs-market difference as an "
            "'edge' is not supported by this evidence.")
    return dict(
        state=state, plain=plain,
        test_n=test.get("n"),
        model_mae=test.get("spread_mae_model"),
        market_mae=test.get("spread_mae_market"),
        diff_ci=diff,
        blend_weight_model=weight,
        blend_weight_market=blend.get("weight_market"),
        hybrid_mae=blend.get("test_mae_hybrid"),
        market_only_mae=blend.get("test_mae_market_only"),
        sign_corr=(lines.get("sign_convention_check") or {}).get("corr_market_line_vs_home_margin"),
        sign_n=(lines.get("sign_convention_check") or {}).get("n_games"),
        source="data/model/lines.json")


def strategy_verdict():
    strat = load("data/model/strategies.json")
    lb = strat["leaderboard"]
    if not lb:
        return dict(state="NO DATA", plain="No strategies have been evaluated.", rows=[])
    best = max(lb, key=lambda r: (r.get("score_lower_ci_roi_pct") if r.get("score_lower_ci_roi_pct") is not None else -999))
    passing = [r for r in lb if r.get("status") == "PASS"]
    q_best = min((r.get("q_value") for r in lb if r.get("q_value") is not None), default=None)
    return dict(
        state="NOT READY" if not passing else "HAS A PASS",
        plain=(
            f"{len(passing)} of {len(lb)} strategies passed every gate. The best paper score "
            f"is negative ({best.get('score_lower_ci_roi_pct')}% lower-bound ROI), which is the "
            "ranking's own way of saying no strategy is yet better than luck." )
        if not passing else
        (f"{len(passing)} strategy(ies) cleared every gate; a leaderboard can be opened."),
        best=best.get("strategy"), best_lower_ci=best.get("score_lower_ci_roi_pct"),
        best_roi=best.get("roi"), best_ci=best.get("roi_ci95"),
        best_n=best.get("n_graded"), best_q=best.get("q_value"),
        smallest_q=q_best, gates=strat.get("gate_definitions"),
        parlay=strat.get("parlay"), rewards=(strat.get("rewards") or {}).get("model"),
        source="data/model/strategies.json")


def availability_verdict(ev):
    """How much of the starter/backup question the official sources actually answer."""
    a = load("data/model/availability.json")
    inj = load("data/evidence/injuries_week10.json")["rows"]
    dep = load("data/evidence/depth_charts.json")["rows"]
    flagged_players = a["players"]
    flagged_with_designation = sum(1 for p in flagged_players if p.get("game_status"))
    flagged_practice_only = len(flagged_players) - flagged_with_designation
    dep_clubs = sorted({r["club"] for r in dep})
    publishing = sorted({r["club"] for r in inj})
    covered = [c for c in publishing if c in dep_clubs]
    return dict(
        state="PARTIAL",
        official_game_designations=sum(1 for r in inj if r["game_status"]),
        official_player_rows=len(inj),
        clubs_with_depth=dep_clubs,
        clubs_in_week10=publishing,
        clubs_with_both=covered,
        uncovered=[c for c in publishing if c not in dep_clubs],
        flagged_players=len(flagged_players),
        flagged_with_game_designation=flagged_with_designation,
        flagged_practice_only=flagged_practice_only,
        model_starters_flagged=a["counts"]["starters_impacted"],
        model_unmatched=a["counts"]["records_not_matched_to_depth_chart"],
        plain=(
            "The league publishes injury status for players but publishes no depth chart "
            "(the league URL 404s). Only club sites do. So a statement like 'the third-string "
            "corner is starting' can be verified for "
            f"{len(covered)} of {len(publishing)} clubs this week, and is an assumption "
            f"elsewhere. The model flags {len(flagged_players)} players as impacted starters; "
            f"only {flagged_with_designation} of them carry an official game designation, the "
            f"other {flagged_practice_only} are practice-only reports that the league has not "
            "yet converted into an availability ruling."),
        source="https://www.nfl.com/injuries/ and club depth-chart pages")


def prop_verdict():
    p = load("data/model/props.json")
    rows = p["props"]
    with_market = [r for r in rows if r.get("market_line") not in (None, "")]
    return dict(
        state="MODEL ONLY" if not with_market else "HAS MARKET",
        lines=len(rows),
        players=len({r["player"] for r in rows}),
        with_market=len(with_market),
        plain=(f"{len(rows)} prop lines for {len({r['player'] for r in rows})} players, all "
               "built from the player's own shrunk usage and the opponent's defensive rating. "
               "No prop price exists in any connected source, so no prop edge can be claimed "
               "and the market column is deliberately blank."),
        source="data/model/props.json")


def backtest_power(strategies=None, games=None):
    """How many games are needed to tell skill from luck at this effect size.

    Method: a two-sided one-sample test on per-bet units. With a 52.4% break-even rate
    (110/210 vig) an edge of e points of win probability moves the per-bet mean by roughly
    2e units and the per-bet standard deviation is about 0.95 units for a -110 bet. The
    sample needed to reach 80% power at alpha=0.05 is n = (1.96 + 0.84)^2 * sd^2 / mean^2.
    Everything is arithmetic on constants stated below; no fitted values are claimed.
    """
    import math
    sd = 0.95
    n_for = {}
    for edge in (0.01, 0.02, 0.03, 0.05):
        mean = 2 * edge
        n = ((1.96 + 0.84) ** 2) * (sd ** 2) / (mean ** 2)
        n_for[f"{int(edge*100)}% win-probability edge"] = int(math.ceil(n))
    return dict(
        assumptions=dict(sd_per_bet=sd, break_even_win_rate=round(110 / 210, 4),
                         alpha=0.05, power=0.80, juice=-110,
                         source="https://www.itl.nist.gov/div898/handbook/prc/section2/prc222.htm"),
        n_required=n_for,
        games_per_season=272,
        seasons_required={k: round(v / 272, 1) for k, v in n_for.items()},
        note=("This is the arithmetic that decides whether a leaderboard can be ranked on one "
              "season. It says a 1% edge cannot be separated from luck in a single season, so "
              "any reward scheme must use multi-season samples or lower its ambition."),
    )


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    ev = evidence_inventory()
    payload = dict(
        # placeholder; preserved from the committed file when the payload is unchanged
        # (d23c65ad fix: a fresh timestamp here changed web/*.html on every run, so the
        # pages could never be byte-reproducible).
        generated_at=None,
        evidence=ev,
        model=model_verdict(),
        strategies=strategy_verdict(),
        availability=availability_verdict(ev),
        props=prop_verdict(),
        power=backtest_power(),
        fillable=load("data/fillable_decisions.json")["decisions"],
        contradictions=load("data/contradictions.json")["items"],
        questions=load("data/questions.json"),
        suggestions=load("data/suggestions.json"),
        paths=load("data/paths.json"),
        gates=load("data/validation_gates.json"),
        flags=load("data/flags.json"),
    )
    out_path = os.path.join(OUT, "decision_room.json")
    prior = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as f:
                prior = json.load(f)
        except (OSError, ValueError):
            prior = {}
    prior_payload = {k: v for k, v in prior.items() if k != "generated_at"}
    new_payload = {k: v for k, v in payload.items() if k != "generated_at"}
    if prior_payload == new_payload and prior.get("generated_at"):
        payload["generated_at"] = prior["generated_at"]
    else:
        payload["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
        f.write("\n")
    print(f"wrote data/decision_room/decision_room.json")
    print(f"  evidence: {ev['games_played']} games, {ev['injury_rows']} injury rows, "
          f"{ev['own_lines']} own lines, {ev['strategies']} strategies")
    print(f"  model verdict: {payload['model']['state']} — {payload['model']['plain'][:80]}...")
    print(f"  strategy verdict: {payload['strategies']['state']}")
    print(f"  power: {payload['power']['n_required']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
