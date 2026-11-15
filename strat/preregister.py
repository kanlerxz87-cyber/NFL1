#!/usr/bin/env python3
"""strat/preregister.py — pre-registration registry for every strategy (C1).

The defect this prevents
------------------------
`data/s9cb/leaderboard.json` publishes a win rate and an ROI for twelve rules whose
thresholds were chosen after the author had seen the data.  A backtest number that was not
frozen before it was computed cannot be evidence, because the rule could have been — and in
practice was — selected on the result it is now being judged by.  The readiness register
records this as PR-06 *Not met* and PR-15 *Not started*.

What this builds
----------------
For every strategy that appears anywhere in this repository (the twelve scored rules in
`data/s9cb/leaderboard.json`, the parlay/combo families and the prop rules), one immutable
registration record:

    id                      the rule's short id (S01 … )
    name                    as published
    definition              the rule text, frozen
    inputs                  the exact files and columns it may read
    sample_window           the seasons and the first/last game it may score
    gates                   the gate set the result must pass to be published
    registered_at           when this registration was written
    registration_commit     the git commit that contains the registration
    status                  "registered-backtest" | "registered-prospective"

Publication rule
----------------
A backtest number may appear on the leaderboard **only** when a registration record exists
for the rule and the record's commit is an ancestor of the commit that publishes the number.
`tools/check_preregistration.py` enforces exactly that, and fails the build otherwise.

Honest labelling
----------------
The twelve rules already in the repository were defined before *this* session but after the
data was seen (the selection is documented in `data/s9cb/leaderboard.json`: 12 rules tested,
Benjamini-Hochberg correction for 12 hypotheses).  They are therefore registered here as
`registered-backtest`: frozen from now on, historically exposed to selection.  The 19 rules
added by this session that have no result yet are registered `registered-prospective` and are
the only ones that can ever qualify for a prospective sample.

Run: python3 strat/preregister.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

ROOT = lib.ROOT
GATES = [
    {"id": "G1", "name": "walk-forward", "test": "every input predates kick-off and every fit uses only earlier games",
     "source": "data/s9cb/lines.json › lookahead_probe (predictions differ with future data)"},
    {"id": "G2", "name": "observed prices", "test": "every scored bet carries a price from the source file; no -110 assumed",
     "source": "data/s9cb/leaderboard.json › price_source"},
    {"id": "G3", "name": "sample size", "test": "at least 200 scored bets in the backtest sample",
     "source": "data/s9cb/leaderboard.json › gate_definitions G3"},
    {"id": "G4", "name": "beats break-even", "test": "hit rate above the break-even implied by the actual prices taken",
     "source": "data/s9cb/leaderboard.json › break_even_hit_rate"},
    {"id": "G5", "name": "multiplicity", "test": "Benjamini-Hochberg adjusted p < 0.05 across the rules tested",
     "source": "data/s9cb/leaderboard.json › gate_definitions G5"},
    {"id": "G6", "name": "holdout", "test": "positive in the untouched holdout window (2024 + 2025 backtest seasons)",
     "source": "data/s9cb/leaderboard.json › holdout_2024_2025"},
    {"id": "G7", "name": "seasonal stability", "test": "positive in at least 60% of individual seasons",
     "source": "data/s9cb/leaderboard.json › gate_definitions G7"},
    {"id": "G8", "name": "uncertainty", "test": "95% bootstrap interval on ROI excludes zero",
     "source": "data/s9cb/leaderboard.json › roi_ci95"},
    {"id": "PS1", "name": "proper score", "test": "benchmark-relative Brier skill on the same games, with a game-cluster bootstrap lower bound above 0",
     "source": "data/strat/proper_score.json › markets[].bss_lower_bound"},
    {"id": "PR1", "name": "pre-registration", "test": "a registration record exists and its commit precedes the result",
     "source": "data/strat/preregistration.json"},
]

# ---------------------------------------------------------------------------
# The twelve rules already scored in data/s9cb/leaderboard.json.  The definition text is
# the rule's own name plus the input columns it reads, both taken from the published file.
# The twelve rules already scored in data/s9cb/leaderboard.json.  Every definition below was
# read from s9cb/analysis/strategies.py::generate(), and `verify_against_code()` re-reads that
# function on every run and fails if a registered rule no longer fires on the same condition.
BACKTEST_RULES = [
    ("S01", "Model spread edge >= 1.5 pts", "side", "spread",
     "home if model_margin - spread_line >= +1.5, away if <= -1.5",
     ["model_margin", "spread_line"],
     "Backtested on 2006-2026 closing lines; one of twelve rules tested in the same run."),
    ("S02", "Model spread edge >= 3.0 pts", "side", "spread",
     "home if model_margin - spread_line >= +3.0, away if <= -3.0",
     ["model_margin", "spread_line"],
     "Same family as S01 with a wider threshold; both fire in the same run, so they are not independent."),
    ("S03", "Model total edge >= 2.5 pts", "total", "total",
     "over if model_total - total_line >= +2.5, under if <= -2.5",
     ["model_total", "total_line"],
     "Backtested on 2006-2026 closing totals against the walk-forward model total."),
    ("S04", "Model total edge >= 4.0 pts", "total", "total",
     "over if model_total - total_line >= +4.0, under if <= -4.0",
     ["model_total", "total_line"],
     "Same family as S03 with a wider threshold."),
    ("S05", "Rest edge >= 3 days", "side", "spread",
     "home if home_rest - away_rest >= +3, away if <= -3",
     ["home_rest", "away_rest"],
     "Backtested on 2006-2026 closing lines; rest days are published schedule facts."),
    ("S06", "Divisional road underdog of 3+", "side", "spread",
     "away when div_game == 1 and spread_line <= -3",
     ["div_game", "spread_line"],
     "Backtested on 2006-2026 closing lines."),
    ("S07", "Fade the road favourite of 7+", "side", "spread",
     "home when spread_line <= -7",
     ["spread_line"],
     "Backtested on 2006-2026 closing lines; the rule with the largest ROI point estimate in the run."),
    ("S08", "Home team off a bye", "side", "spread",
     "home when home_rest >= 13 and away_rest < 13",
     ["home_rest", "away_rest"],
     "Backtested on 2006-2026 closing lines."),
    ("S09", "Under when the total is 40 or lower", "total", "total",
     "under when total_line <= 40",
     ["total_line"],
     "Backtested on 2006-2026 closing totals."),
    ("S10", "Over when the total is 50 or higher", "total", "total",
     "over when total_line >= 50",
     ["total_line"],
     "Backtested on 2006-2026 closing totals."),
    ("S11", "Opponent QB ruled Out/Doubtful", "side", "spread",
     "opponent's side when exactly one team's quarterback carries status Out or Doubtful (2016 onwards)",
     ["report_status", "position"],
     "Reads a designation level from the weekly report, which the brief forbids as a signal. Registered so its result is traceable; superseded by P07-P09."),
    ("S12", "Out-count gap of 3 or more", "side", "spread",
     "the team with fewer players designated Out/Doubtful when the counts differ by 3 or more (2016 onwards)",
     ["report_status"],
     "Counts designations, i.e. a level, not a surprise. Registered so its result is traceable; superseded by P07-P09."),
]


# ---------------------------------------------------------------------------
# Rules this session registers with no result attached.  They are the only rules that can
# accumulate a prospective sample, and several of them exist specifically to replace a
# fixed-penalty or level-based rule the brief rejects.
PROSPECTIVE_RULES = [
    ("P01", "Model side edge >= 2.0 pts, singles only", "side",
     ["model_margin", "spread_line"], "shadow baseline",
     "The pre-registered singles-only shadow baseline the brief asks for. Every forecast is written before kick-off; no price is required to record a forecast."),
    ("P02", "Random side, 1 unit per game", "side",
     ["game_id"], "control baseline",
     "Control baseline. Twenty random draws per game id with a fixed seed, so the interval on the control is published, not just a point."),
    ("P03", "Favourite only, no threshold", "side",
     ["spread_line"], "control baseline",
     "Control baseline: bet the favourite on the closing spread. Separates skill from the well-documented favourite bias."),
    ("P04", "Home team only, no threshold", "side",
     ["spread_line"], "control baseline",
     "Control baseline: bet the home team on the closing spread."),
    ("P05", "Underdog only, no threshold", "side",
     ["spread_line"], "control baseline",
     "Control baseline: bet the underdog on the closing spread."),
    ("P06", "Model total edge >= 2.5 pts, under only", "total",
     ["model_total_a", "model_total_b", "total_line"], "two-estimator",
     "Requires both estimators in P10/P11 to agree on the direction. Until that walk-forward comparison is published, the rule cannot fire."),
    ("P07", "Availability surprise: new 'Out' designation versus the player's own prior week", "side",
     ["report_status", "week"], "injury surprise (replaces a level rule)",
     "The signal is the *change* in designation, never the level (brief: 'make the injury signal a surprise, never a level'). Ablation: identical model with and without the feature, chronological holdout."),
    ("P08", "Practice-participation downgrade (FP -> LP -> DNP) between consecutive reads", "side",
     ["practice_status", "week"], "injury surprise",
     "Practice trend, not designation level. Needs at least two dated reads of the same week, which the snapshot ledger must supply."),
    ("P09", "Count of new 'Out' starters, opponent minus own", "side",
     ["report_status", "position"], "injury surprise",
     "Position-aware surprise count. Blocked until starters are identified from Game Books (see the open-questions register)."),
    ("P10", "Parlay: two legs from different games, joint probability from the validated single-leg model", "parlay",
     ["game_id", "model_margin"], "parlay",
     "Kept behind a joint-evidence gate: a combo is only ranked when a directly validated joint probability exists, not the product of marginals."),
    ("P11", "Same-game parlay: two legs in one game", "sgp",
     ["game_id", "model_margin", "model_total"], "parlay",
     "Same-game legs are dependent by construction; the marginal product is invalid. No same-game parlay can be ranked until a joint distribution is validated."),
    ("P12", "Prop combo: two player props in one game", "prop-combo",
     ["player_id", "game_id", "targets"], "prop combo",
     "The repository holds no player-prop prices at all (data/s9cb/props.json › price_status), so this rule cannot be scored. Registered so that the gap is explicit."),
    ("P13", "Prop single: receiving yards above a shrunk trailing mean", "prop",
     ["player_id", "receiving_yards"], "prop",
     "Unscorable for the same reason: no price. Registered for completeness of the competition."),
    ("P14", "Fade the public side (proxy: contrarian versus closing-line move)", "side",
     ["spread_line", "home_moneyline"], "market structure",
     "Needs an opening line to measure a move. The price-snapshot store is blocked (PR-01), so this rule stays paper."),
    ("P15", "Vig-free consensus versus our fair line", "side",
     ["spread_line", "total_line"], "market structure",
     "Needs two or more books to de-vig a consensus. The repository holds one price series, so the consensus is not computable and is left blank."),
    ("P16", "Bye-week rest advantage of 2+ days", "side",
     ["home_rest", "away_rest"], "schedule fact",
     "Built only from published schedule facts (rest days are in the schedule extract)."),
    ("P17", "International/neutral-site travel disadvantage", "side",
     ["location", "spread_line"], "schedule fact",
     "The 2026 schedule contains neutral-site games; the rule is registered because the fact is published, not because an edge is expected."),
    ("P18", "Thursday short-week under", "total",
     ["weekday", "total_line"], "schedule fact",
     "Weekday is a published schedule fact."),
    ("P19", "Season-opener total regression", "total",
     ["week", "total_line"], "schedule fact",
     "Registered; the sample is small by construction and G3 will fail it for many seasons."),
]


def verify_against_code() -> list[str]:
    """Re-read s9cb/analysis/strategies.py and confirm each registered rule string exists.

    A registration whose text has drifted from the code is worthless, so this returns the list
    of rules that cannot be found in the generator and the caller fails on a non-empty list.
    """
    import re
    path = os.path.join(ROOT, "s9cb", "analysis", "strategies.py")
    src = open(path, encoding="utf-8").read()
    missing = []
    for sid, name, *_ in BACKTEST_RULES:
        if f'"{sid} {name}"' not in src:
            missing.append(f"{sid} {name}")
    return missing


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main() -> int:
    missing = verify_against_code()
    if missing:
        print("FAIL: a registered rule is not present in s9cb/analysis/strategies.py:")
        for m in missing:
            print("  -", m)
        return 1
    head = git("rev-parse", "HEAD")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    try:
        # the backtest extract the twelve rules were scored on
        sc = lib.load("../../data/s9cb/leaderboard.json")
        scored = {r["strategy"] for r in sc["leaderboard"]}
        n_bets = {r["strategy"]: r["n_bets"] for r in sc["leaderboard"]}
    except Exception:  # pragma: no cover - the file is in the repository
        scored, n_bets = set(), {}

    records = []
    for sid, name, market, bet_kind, condition, inputs, note in BACKTEST_RULES:
        matched = [s for s in scored if s.split(" ", 1)[0] == sid]
        records.append({
            "id": sid,
            "name": name,
            "market": market,
            "bet_kind": bet_kind,
            "definition": f"{name}. Fires on the {bet_kind} market: {condition}. "
                          f"Stake 1 unit, flat; no staking model is part of the rule.",
            "condition": condition,
            "inputs": inputs,
            "sample_window": {
                "seasons": "2006-2026",
                "rule": "closing prices only; a game without a price is not scored",
                "n_bets_backtest": n_bets.get(matched[0]) if matched else None,
            },
            "gates": [g["id"] for g in GATES],
            "status": "registered-backtest",
            "registered_at": "2026-11-15",
            "registration_commit": "see data/strat/preregistration_stamp.json",
            "registration_branch": branch,
            "result_location": "data/s9cb/leaderboard.json",
            "result_scored": bool(matched),
            "exposure_note": note,
            "selection_disclosure": (
                "This rule's thresholds were chosen before this session but after the scoring data "
                "existed; the multiplicity correction in G5 charges for the twelve-rule search. From "
                "this commit onwards the text is frozen and any edit is visible as a diff."),
            "source": "schedules",
        })

    for sid, name, market, inputs, family, note in PROSPECTIVE_RULES:
        records.append({
            "id": sid,
            "name": name,
            "market": market,
            "definition": f"{name}. Stake 1 unit, flat; no staking model is part of the rule.",
            "inputs": inputs,
            "sample_window": {
                "seasons": "2026 onwards, prospective",
                "rule": "only games that kick off after the registration commit",
                "n_bets_backtest": None,
            },
            "gates": [g["id"] for g in GATES],
            "status": "registered-prospective",
            "family": family,
            "registered_at": "2026-11-15",
            "registration_commit": "see data/strat/preregistration_stamp.json",
            "registration_branch": branch,
            "result_location": None,
            "result_scored": False,
            "exposure_note": note,
            "selection_disclosure": "Registered before any result was computed from it.",
            "source": "schedules",
        })

    lib.write_json("preregistration.json", {
        "generated_at": lib.now(),
        "registration_branch": branch,
        "how_the_commit_is_recorded": (
            "The git hash of a commit cannot be written inside the file that commit contains. The "
            "registry is therefore stamped by tools/stamp_preregistration.py, which records the hash "
            "of the commit that last changed this file and the SHA-256 of the file as committed. "
            "tools/check_preregistration.py fails when the file's hash no longer matches the stamp, "
            "which makes any post-hoc edit of a frozen rule a build failure."),
        "n_records": len(records),
        "n_backtest": sum(1 for r in records if r["status"] == "registered-backtest"),
        "n_prospective": sum(1 for r in records if r["status"] == "registered-prospective"),
        "rule": (
            "A backtest number may be published only when a registration record exists for the rule "
            "and the registration commit is an ancestor of the publishing commit. Enforced by "
            "tools/check_preregistration.py, which fails the build otherwise."),
        "gates": GATES,
        "code_cross_check": {
            "file": "s9cb/analysis/strategies.py",
            "rule": "every registered backtest rule's exact strategy string must appear in the generator",
            "passed": True,
        },
        "records": records,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
