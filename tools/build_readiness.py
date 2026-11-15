#!/usr/bin/env python3
"""Build data/readiness.json: the decision-readiness table shown on the landing page.

Session 90c2b454-nfl1, task P4. One row per requirement, each with:

* the gate that blocks it,
* the number that is true now (computed here from a named repository file), and
* the number that would clear the gate (computed from the same file, or left blank and flagged
  when the threshold has not been set by anyone yet).

Nothing is typed in by hand. A row that cannot be computed from a file in the repository says so
in its `number_now` cell instead of guessing. `status` follows a fixed rule (see `_status`).

Usage (from the repository root):
    python3 tools/build_readiness.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "readiness.json"

NFL_INJURIES = "https://www.nfl.com/injuries/"
NFL_SCHEDULE_2026 = "https://www.nfl.com/schedules/2026/by-week/week-10"
REPO_BLOB = "https://github.com/kanlerxz87-cyber/NFL1/blob/main/"
INTERNAL_ROWS = {"R1", "R2", "R3", "R4", "R9", "R10"}


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def read_jsonl(rel: str) -> list[dict]:
    p = ROOT / rel
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _status(met: bool | None, partial: bool = False) -> str:
    if met is None:
        return "unverified"
    if met:
        return "met"
    return "partial" if partial else "blocked"


def build() -> dict:
    lb = load("data/s9cb/leaderboard.json")
    strategies = lb["leaderboard"]
    n = int(lb["n_strategies"])
    gates_of = lambda s: s.get("gates") or {}  # noqa: E731
    all8 = sum(1 for s in strategies if s.get("n_gates_passed") == 8)
    best = max(strategies, key=lambda s: s.get("n_gates_passed", 0))
    g5 = sum(1 for s in strategies if gates_of(s).get("G5") is True)
    g8 = sum(1 for s in strategies if gates_of(s).get("G8") is True)

    top = strategies[0]
    luck = {r["strategy"]: r for r in lb["luck_accounting"]["rows"]}
    top_luck = luck.get(top["strategy"], {})

    par = load("data/s9cb/parlays.json")
    n_pairs, n_surv = par["n_pairs_scored"], par["n_pairs_surviving_bh_5pct"]

    beats = read_jsonl("data/snapshots/injury_report/heartbeat.jsonl")
    changes = read_jsonl("data/snapshots/injury_report/changes.jsonl")
    ok_days = sorted({b["fetched_at_utc"][:10] for b in beats if b.get("status") == "ok"})
    n_changes = sum(c["changes"] for c in changes)
    captures = json.loads((ROOT / "data/snapshots/injury_report/manifest.json").read_text())["captures"] \
        if (ROOT / "data/snapshots/injury_report/manifest.json").exists() else []
    past_season_captures = sum(1 for c in captures if c["season"] < 2026)

    depth = load("data/depth_ladder.json")["counts"]
    with_chart, total_clubs = depth["clubs_with_chart"], depth["clubs_total"]

    games = list(csv.DictReader((ROOT / "data/s9cb/games.csv").open(newline="", encoding="utf-8")))
    played_2026 = sum(1 for g in games if g["season"] == "2026" and (g.get("home_score") or "").strip())

    registered = 0
    for s in strategies:
        keys = " ".join(s.keys()).lower()
        if "hash" in keys or "registration" in keys or "prereg" in keys:
            registered += 1

    statuses = {}
    for s in strategies:
        statuses[s.get("status", "")] = statuses.get(s.get("status", ""), 0) + 1
    live = statuses.get("LIVE", 0) + statuses.get("PROMOTED", 0)

    prices_all = lb["totals"].get("all_prices_observed")

    rows = [
        {
            "id": "R1",
            "requirement": "Originate own lines and show a real edge against the market",
            "blocking_gate": "G5 multiple-testing (BH-adjusted p < 0.05) and G8 (95% ROI lower bound above 0)",
            "number_now": f"{g5} of {n} strategies pass G5; {g8} of {n} pass G8",
            "number_to_clear": (f"{top_luck.get('bets_needed_for_80pct_power')} bets for 80% power at the top "
                                f"strategy's edge; {top_luck.get('n_bets')} placed"),
            "status": _status(g5 > 0),
            "computed_from": "data/s9cb/leaderboard.json",
            "source_label": "nfl.com schedule (fixtures)",
            "source_url": NFL_SCHEDULE_2026,
        },
        {
            "id": "R2",
            "requirement": "Strategies pass all eight validation gates before they rank",
            "blocking_gate": "G5 and G8 (the gates no strategy clears together)",
            "number_now": f"{all8} of {n} pass all 8; best is {best.get('n_gates_passed')} of 8 ({best['strategy'].split(' ')[0]})",
            "number_to_clear": "8 of 8 gates on at least one strategy",
            "status": _status(all8 > 0),
            "computed_from": "data/s9cb/leaderboard.json",
            "source_label": "nfl.com schedule (fixtures)",
            "source_url": NFL_SCHEDULE_2026,
        },
        {
            "id": "R3",
            "requirement": "Parlays and combos ranked only on a validated joint probability",
            "blocking_gate": "Joint-evidence gate: directly validated joint probability and the operator's void/push rules",
            "number_now": f"{n_surv} of {n_pairs} tested two-leg pairs survive BH at 5%",
            "number_to_clear": "at least 1 surviving pair, with void/push rules recorded (rules: not yet recorded)",
            # Partial, never met: the void/push rules that the gate also requires are not recorded.
            "status": _status(False, partial=n_surv > 0),
            "computed_from": "data/s9cb/parlays.json",
            "source_label": "nfl.com schedule (fixtures)",
            "source_url": NFL_SCHEDULE_2026,
        },
        {
            "id": "R4",
            "requirement": "Every strategy pre-registered before results are seen",
            "blocking_gate": "A registration hash recorded before evaluation (commit hash of the frozen rule)",
            "number_now": f"{registered} of {n} strategies carry a registration hash",
            "number_to_clear": f"{n} of {n}",
            "status": _status(registered == n),
            "computed_from": "data/s9cb/leaderboard.json",
            "source_label": "nfl.com schedule (fixtures)",
            "source_url": NFL_SCHEDULE_2026,
        },
        {
            "id": "R5",
            "requirement": "Injury designations tracked as a timestamped series (the surprise, not the level)",
            "blocking_gate": "At least 2 capture days, with at least 1 recorded designation change",
            "number_now": f"{len(ok_days)} capture day(s); {n_changes} designation change(s) recorded",
            "number_to_clear": "2 capture days and 1 recorded change",
            "status": _status(len(ok_days) >= 2 and n_changes >= 1, partial=len(ok_days) >= 1),
            "computed_from": "data/snapshots/injury_report/heartbeat.jsonl and changes.jsonl",
            "source_label": "nfl.com/injuries",
            "source_url": NFL_INJURIES,
        },
        {
            "id": "R6",
            "requirement": "Official depth chart for all 32 clubs (2nd to 4th string)",
            "blocking_gate": "A published club depth chart for every club; nfl.com publishes none",
            "number_now": f"{with_chart} of {total_clubs} clubs with a chart",
            "number_to_clear": f"{total_clubs} of {total_clubs} clubs",
            "status": _status(with_chart == total_clubs, partial=with_chart > 0),
            "computed_from": "data/depth_ladder.json",
            "source_label": "nfl.com/injuries",
            "source_url": NFL_INJURIES,
        },
        {
            "id": "R7",
            "requirement": "Official Game Books for actual starters and game-day status",
            "blocking_gate": "A Game Book archived for each played game (none is archived in this repository)",
            "number_now": f"0 of {played_2026} played 2026 games archived",
            "number_to_clear": f"{played_2026} of {played_2026} played games",
            "status": "blocked",
            "computed_from": ("data/s9cb/games.csv (games with a final score). 137 includes WAS @ NYG (Nov 12), "
                              "which the 136-game official snapshot predates; see flag F41"),
            "source_label": "nfl.com schedule (fixtures)",
            "source_url": NFL_SCHEDULE_2026,
        },
        {
            "id": "R8",
            "requirement": "Injury designation reliability measured before it becomes a feature",
            "blocking_gate": "Past-season injury reports joined to official inactive lists",
            "number_now": f"{past_season_captures} past-season captures archived",
            "number_to_clear": "threshold not yet set (flagged for review)",
            "status": "blocked",
            "computed_from": "data/snapshots/injury_report/manifest.json",
            "source_label": "nfl.com/injuries",
            "source_url": NFL_INJURIES,
        },
        {
            "id": "R9",
            "requirement": "Demotion gate that sends a live strategy back to paper",
            "blocking_gate": "A written demotion rule, frozen before it is applied",
            "number_now": f"{live} live strategies; demotion rule not written",
            "number_to_clear": "rule frozen (1 of 1)",
            "status": "blocked",
            "computed_from": "data/s9cb/leaderboard.json (status field)",
            "source_label": "nfl.com schedule (fixtures)",
            "source_url": NFL_SCHEDULE_2026,
        },
        {
            "id": "R10",
            "requirement": "Price-data policy decided before any backtest is published",
            "blocking_gate": "A recorded policy decision (prices observed on every scored bet)",
            "number_now": ("every scored bet has an observed price" if prices_all
                           else "not every scored bet has an observed price"),
            "number_to_clear": "policy recorded (not yet recorded)",
            "status": "partial" if prices_all else "blocked",
            "computed_from": "data/s9cb/leaderboard.json (totals.all_prices_observed)",
            "source_label": "nfl.com schedule (fixtures)",
            "source_url": NFL_SCHEDULE_2026,
        },
    ]
    # The build time is the newest data timestamp, not the wall clock, so a rebuild of unchanged
    # data is byte-identical (the --check gate depends on this).
    data_time = max((b["fetched_at_utc"] for b in beats if b.get("fetched_at_utc")), default="")
    # Source correction (session 90c2b454-nfl1, flag F52). The schedule page was cited for rows whose
    # evidence is a backtest, a registration, or a price record. No official page holds those numbers,
    # so these rows link to the repository file that computes them, labelled as internal. R5, R7
    # and R8 keep their official nfl.com links because they count records from that page.
    for r in rows:
        if r["id"] in INTERNAL_ROWS:
            r["source_label"] = "internal computation: no official source applies (flag F52)"
            r["source_url"] = REPO_BLOB + r["computed_from"].split(" ")[0]
    for r in rows:
        if r["id"] == "R6":
            r["source_label"] = "club depth charts (per-club official links in the file, flag F42)"
            r["source_url"] = REPO_BLOB + "data/depth_ladder.json"
    return {
        "generated_at": data_time or lb.get("generated_at", ""),
        "note": ("Every number is computed from the file named in computed_from. A blank threshold is "
                 "a decision nobody has made yet, and is flagged rather than filled in."),
        "legend": {"met": "the number that clears the gate is reached",
                   "partial": "some of the evidence exists, the gate is not reached",
                   "blocked": "the gate is not reached and no evidence closes it",
                   "unverified": "cannot be computed from the repository"},
        "rows": rows,
    }


def main() -> int:
    data = build()
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['rows'])} rows")
    for r in data["rows"]:
        print(f"  {r['id']} {r['status']:<10} {r['number_now']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
