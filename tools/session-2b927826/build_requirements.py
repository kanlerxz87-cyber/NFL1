#!/usr/bin/env python3
"""build_requirements.py — the brief-line requirement register for this session's sub-site.

One row per distinct requirement line of the brief (de-duplicated where the brief restates
itself).  The 'gate' column is what blocks the row, 'now' is the number that exists today, and
'src' names the artifact or check that backs the status.  Nothing here is typed into HTML: the
page generator reads this JSON.
"""
from __future__ import annotations

import json
import os
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "data", "session-2b927826", "requirements.json")

ROWS = []


def R(title, status, gate, now, src, note=""):
    ROWS.append({"title": title, "status": status, "gate": gate, "now": now, "src": src, "note": note})


# ---------------------------------------------------------------- data and verification
R("Price-snapshot store recording opening and closing numbers for every originated market", "not met",
  "an opening and a closing observation per market per game, each with a timestamp and a source",
  "0 opening numbers stored; 1 line per game (the closing)", "Q11 / BF-11",
  "The corpus records one price per game. No store exists, and it cannot be backfilled: once the market moves the opening number is gone.")
R("Verified results feed so backtests and ROI can be computed at all", "partial",
  "a final score per game joined to a price, both from a named source",
  "7,104 completed games with prices in the frozen corpus", "corpus.json / Q20",
  "Scores come from a pinned third-party parse. The NFL's own results are reachable but are not ingested as a feed.")
R("Originate the side first, then the total, then the moneyline", "done",
  "all three markets published with fair line, market line and difference",
  "13 Week 11 games carry spread, total and win probability", "data/s9cb/lines.json / Q26",
  "The order is honoured in the modelling: side and total are scored, and the moneyline is published as a probability rather than a priced bet.")
R("Publish the model's fair line, the market line and the difference as separate columns", "done",
  "three distinct columns per market, the difference computed from the two stored values",
  "3 columns per market; differences are derived, never re-typed", "Q26 / README convention",
  "The one time this was violated the same row printed a 14.7-point difference instead of 4.27; the convention exists because of that.")
R("Separate 'signal' from 'staking' in the leaderboard", "done",
  "a signal score and a staking result as separate columns, never combined into one rank",
  "the board ranks on proper score only; staking is a separate column and never ranks", "data/strat/proper_score.json / Q03",
  "The demotion gate keys on skill, and its stop-loss is explicitly labelled a stop-loss rather than a skill test.")
R("Track the depth of the replacement, not just the fact of a replacement", "done",
  "a string label (2nd, 3rd, 4th) on every projected replacement",
  "38 projected replacements, all second string; 0 third or deeper", "availability.json / Q09",
  "The ladder records rank and string for every slot. What it cannot do yet is confirm the replacement played (Q15).")
R("Compute correlations only from officially sourced numbers and publish n with each value", "partial",
  "every correlation carries its source and an n",
  "6 correlations, all n = 32, from a dated hand transcription", "data/correlations.json / Q19",
  "The source is a transcription of the official standings, so official in origin but dated. Market- and strategy-level correlations, which is what a parlay decision needs, are not published.")
R("Define a demotion gate that sends a live strategy back to paper", "done",
  "a written rule frozen before it is applied, with a re-promotion path",
  "5 rules armed; 0 live strategies, so 0 demotions", "strat/demotion.py / Q17",
  "The threshold set (skill lower bound, stop-loss, two-standard-error hit rate, 12-loss run, edited rule text) is frozen inside the file.")
R("Pre-register every strategy; forbid backtest numbers from ever appearing on the leaderboard", "partial",
  "a registration hash before evaluation, and a board carrying no backtest number",
  "31 records: 12 backtest-first and disclosed, 19 prospective; 0 live", "data/strat/preregistration.json / Q16",
  "The ban is enforced on the ranked board and the backtests live in a labelled archive. The pre-registration is incomplete because 12 rules were scored before they were registered, and that is disclosed rather than backdated.")
R("Build the availability graph as a first-class dataset (who was expected to start, who actually did)", "not met",
  "expected starter AND actual starter, with the evidence for each, per game",
  "expected only; the actual starter is nowhere (0 of 137 games archived)", "Q15 / BF-10",
  "Half a graph is not a graph. The expected half is built from club depth charts and is labelled as a projection.")
R("Do not model depth from jersey order; model it from playing time", "not met",
  "a playing-time source (snap counts or Game Book) joined to the depth ladder",
  "no snap-count or Game Book capture exists", "Q08 / BF-10",
  "No jersey-order inference exists either, which is the good half of this row: nothing in the repository ranks players by number, experience or salary.")
R("Make the injury signal a surprise, never a level", "not met",
  "a dated series with at least one recorded designation change",
  "2 capture days, 0 recorded changes", "Q05 / BF-02",
  "The capture exists and runs; it runs too rarely to produce a transition.")
R("Run the 32-team roster/IR sweep before any team-level model is trusted", "not met",
  "a roster and reserve-list capture for all 32 clubs, joined to the weekly report",
  "0 clubs have a reserve-list capture", "Q15 / BF-10",
  "Absence from the weekly report is published as 'not listed', never as 'available'.")
R("Add a fixture-context feature set built only from published schedule facts", "partial",
  "one table of weekday, kickoff, rest, short week, division, venue, neutral site, byes",
  "13 of 13 Week 11 rows verified independently this session", "data/shadow/week11_context.json / Q14 / SG-08",
  "The table exists and is correct. Roof and surface are not official facts and are left blank.")
R("Store every model output as a probability plus its inputs, not just a pick", "partial",
  "a forecast record per rule, with inputs whose hash reproduces the probability",
  "1 baseline forecast record (SB-01) reproduces to 6 dp; other rules have no record", "data/prereg/forecasts / Q22",
  "")
R("Compute and publish the 'removal of luck' panel on the site dashboard", "done",
  "a luck band beside every result, plus the bets needed for power",
  "luck band and 80% power number on every strategy row", "data/s9cb/leaderboard.json / Q04",
  "Two calibrated controls (coin flip -2.51%, favourites-only -4.74%) sit beside it.")
R("Add a two-sided 'what would change our mind' field to every strategy entry", "partial",
  "confirm_if AND abandon_if on every entry, each carrying a number",
  "12 claims covered; 31 strategy records exist", "data/strat/what_would_change.json / Q23 / SG-13",
  "")
R("Price a line ourselves and publish the residual against the market, on a schedule, from day one", "partial",
  "a scheduled residual publication with a stored price",
  "13 own lines for Week 11 with a residual; no schedule and no stored opening price", "Q26 / Q11",
  "The residual is always against a third-party market because no official price exists (BF-11).")
R("Turn the 136-game log into the pre-registered backtest corpus", "done",
  "a frozen corpus with a membership rule, a hash and closed splits",
  "NFL1-CORPUS-2026-11-15-v1: 7,104 games, holdout closed", "data/prereg/corpus.json / Q20",
  "The 136-game log was superseded rather than promoted; it is retained as a historical record.")
R("Decide the price-data policy before any backtest is published", "not met",
  "a recorded policy decision with a date",
  "no policy recorded; every backtest rests on a pinned third-party price", "Q10 / BF-11",
  "This is the highest-leverage open decision in the repository: it gates every published ROI.")
R("Store every injury-hub read with its clock time and publish the delta, never the level", "partial",
  "every reading timestamped to the minute, and a delta between readings",
  "heartbeat.jsonl timestamps every read; 5 readings, 0 deltas to show", "BF-02 / Q05 / SG-03",
  "The clock exists. The delta needs a designation to change, which needs the report to be re-read on a day it changes.")
R("Put a decision-readiness table on the landing page", "done",
  "one row per requirement with the blocking gate and the clearing number",
  "82 rows on the landing page; 69 requirement rows and 26 question rows in this sub-site", "pages/readiness.html + brief/requirements.html",
  "Several readiness registers exist from different sessions; this sub-site publishes its own keyed on the brief's own line.")
R("Transcribe the venue of every fixture from the official game centre and publish it", "done",
  "a venue per fixture, read from the game centre, with the URL",
  "13 of 13 Week 11 fixtures", "official_week11_fixtures.json / V2 / V3",
  "Confirmed twice this session and a third time against another session's independent capture made a day earlier: 0 differences.")
R("Publish the league's dated schedule announcement beside the live schedule page", "partial",
  "the league's own dated announcement, linked beside the live page",
  "the live Week 11 page is published; no dated announcement capture exists", "Q14",
  "The page carries flexible-scheduling notes for Weeks 16-18, the nearest thing to an announcement on it; it is not a dated announcement of this week's slate.")
R("Use official NFL Game Books for actual starters and game-day status; do not infer depth rank or snaps", "not met",
  "an archived Game Book per played game",
  "0 of 137 archived", "Q15 / BF-10 / SG-02",
  "The prohibition is respected: no depth rank or snap count is inferred anywhere.")
R("Ingest game-level results to make the ratings opponent-aware", "done",
  "results ingested and a rating that accounts for the opponent",
  "opponent-adjusted ratings on 7,104 games; the model still scores negative Brier skill", "Q01",
  "Opponent-awareness is implemented and it did not produce skill. Both facts are published.")
R("Add injury and personnel ablations instead of fixed penalties", "done",
  "the identical model with and without the features, and the difference with uncertainty",
  "one ablation: +0.0007 points MAE, interval [-0.0226, +0.0216]", "Q07 / SG-09",
  "No fixed penalty for a missing starter exists anywhere in the repository.")
R("Automate immutable multi-day availability snapshots with retained hashes", "partial",
  "a scheduled capture with a raw hash per reading, at least daily",
  "5 readings with raw and canonical hashes; 2 distinct days", "BF-02 / SG-03",
  "The mechanism is right and the cadence is wrong. The raw hash is retained, which is what makes replay possible.")
R("Capture official inactive lists and snap counts", "not met",
  "an inactive list per game and an official snap-count source",
  "20 inactive rows for Week 9 only (8 emergency quarterbacks); no snap counts", "Q06 / Q15 / SG-01",
  "Only 6 of 254 report rows in an older hand copy carried a game designation; the current capture has 171 of 347.")
R("Fix the two depth-parsing failures before widening coverage", "done",
  "the Packers' jersey numbers stripped and the raw string stored; the Texans' image not transcribed",
  "Packers rows recovered with the raw string retained; Texans published as image-only", "data/depth_ladder.json",
  "The image is not transcribed by eye, which is the brief's instruction.")
R("Model depth slots as groups, not a single starter", "done",
  "shared rank-1 slots recorded as shared",
  "16 slots with more than one rank-1 player, recorded as shared", "data/depth_ladder.json",
  "The generator flags merged-name cells rather than collapsing them.")
R("Treat roster turnover as a first-class data event", "not met",
  "availability and lineup evidence versioned against the last official roster event",
  "no roster-event version stamp; 30 of 31 charts carry no date", "BF-05 / Q08",
  "")
R("Start with a singles-only shadow baseline", "done",
  "a pre-registered simple model, frozen, forecasting before kickoff",
  "SB-01 registered at 9ea55fa; 13 Week 11 forecasts recorded before the first kickoff", "data/prereg/forecasts/SB-01_week11_2026.json",
  "")
R("Keep parlays and prop combos behind a joint-evidence gate", "done",
  "a gate that refuses a combo without a validated joint probability and the void/push rules",
  "the gate exists and no combo is ranked; void/push rules are not recorded, so the gate stays shut", "data/s9cb/parlays.json / Q18",
  "The gate being shut is the correct outcome given the missing rules.")
R("Use proper-score leaderboard divisions", "done",
  "separate divisions for singles, game parlays, same-game parlays and prop combos",
  "divisions defined; no division has a qualifying entry", "Q03 / Q18",
  "")
R("Rank with proper scores and uncertainty, not win rate", "done",
  "game-cluster lower bound plus a multiplicity adjustment",
  "the board publishes the lower bound and the BH-adjusted p, never a rank on win rate", "data/strat/proper_score.json / Q03",
  "")
R("Add durable snapshot storage and alerts outside the static site", "partial",
  "immutable captures outside the published tree, with a freshness alarm",
  "captures are in git under data/snapshots; freshness and drift alarms exist in CI", "BF-02",
  "Storage is durable by virtue of git. It is not outside the static site's repository, which is a fair reading of the requirement and is not met.")
R("Split the site into a public analysis layer and a private data layer", "not met",
  "a recorded terms review and a build rule that separates the two",
  "row-level injury rows are published; no terms review is recorded", "Q21 / SG-14",
  "PR #79 is an open attempt and has not merged.")
R("Add a per-team view: starters out, replacements named, net injury count", "done",
  "a team-level page with all three columns",
  "shadow/team-view.html, 32 club rows", "shadow/team-view.html",
  "Re-checked this session only for the Week 10 report and the committed depth ladder.")
R("Add an announced-starter evidence field (not an inferred replacement)", "not met",
  "a field that records a club's dated starter announcement",
  "no announcement capture exists", "Q15 / BF-10",
  "The repository correctly leaves the field blank rather than inferring one.")
R("Add an official depth-chart register with date and source per row", "partial",
  "a date and a source URL on every row",
  "source URL on every row; a date on 1 of 31 charts", "data/depth_ladder.json / Q08",
  "")
R("Calibrate what 'Questionable' means empirically", "not met",
  "a play rate per designation with a confidence interval",
  "no designation-to-play join exists", "Q06 / SG-01",
  "")
R("Interactive offense-vs-defense deficiency matrix (1st to 4th string)", "partial",
  "a matrix of unit matchups with the string projected to start",
  "the slot-level ladder exists; no matchup matrix, and no 4th string exists to show", "pages/depth.html / Q09",
  "Nothing deeper than second string is projected to start this week, so a 3rd/4th-string matrix would have no rows.")
R("Flag stale depth rows against the official transactions log", "not met",
  "a transactions log capture joined to the depth chart",
  "no transactions capture exists", "Q08 / BF-05",
  "")
R("Point-in-time snapshot ledger for injuries, depth charts and inactives", "partial",
  "a ledger with a point-in-time row per source per day",
  "injury snapshots are ledgered with hashes; depth and inactives are not", "BF-02 / data/snapshots",
  "The injury half is real. A ledger with one of three sources is a partial ledger and is labelled so.")
R("Populate the three missing Lions game-status designations", "done",
  "Kerby Joseph, Cade Mays and D.J. Reed show Out",
  "all three show Out in the committed capture and in the live re-read this session", "V6",
  "The older hand copy that showed them blank is superseded and is flagged upstream (CAP-04).")
R("Re-capture and republish the Week 10 injury tables", "done",
  "the live row count, not the stale one",
  "347 rows, 28 clubs, 14 games; Seattle 15 and Cincinnati 9 rows", "data/capture/ / V6",
  "The stale claim of 254 rows and four injury-free sections is superseded.")
R("Reject: deriving depth order from jersey number, experience or salary", "done",
  "no such inference anywhere",
  "0 values in the repository derive depth from number, experience or salary", "data/depth_ladder.json",
  "This is a rejection row: the requirement is not to do something, and it is not done.")
R("Represent shared and empty depth slots faithfully", "done",
  "shared cells and empty cells both visible and distinguishable from a ranked list",
  "16 shared rank-1 slots and 3 no-available-player slots, both labelled", "data/depth_ladder.json / BF-04",
  "")
R("Resolve the depth-order source before building the backup-deficiency feature", "partial",
  "route (a) verified for all 32 clubs, or route (b) with an official snap source",
  "route (a) spot-checked for 1 club; 31 not", "Q08 / SG-02",
  "Houston's image-only chart blocks a clean 32-club route (a) unless the Game Book route is taken instead.")
R("Score injury-designation reliability before using it as a feature", "not met",
  "a play rate per designation with confidence intervals across seasons",
  "0 seasons of designation-to-inactive joins", "Q06 / SG-01",
  "")
R("Snapshot the injury report every Wednesday, Thursday and Friday with a dated history", "not met",
  "three distinct capture days per week",
  "2 distinct days in total, both in Week 10", "BF-02 / SG-03",
  "")
R("Treat the injury report as a timestamped series, not a weekly snapshot", "not met",
  "a within-week series with more than one reading per week",
  "5 readings over 2 days, all with an identical canonical hash", "BF-02",
  "")
R("Use snap counts as the starter proxy when the depth chart is unavailable", "not met",
  "an official snap-count source",
  "no snap-count source is ingested", "Q08 / BF-10",
  "")
R("Add a control baseline (random picks; favourites only) to every leaderboard run", "done",
  "both controls on every run",
  "coin-flip -2.51% (n=5,202) and favourites-only -4.74% (n=5,202)", "data/prereg/controls.json / Q04",
  "")
R("Stadium roof/surface and NWS wind/precipitation overlay", "not met",
  "an official roof and surface per venue, then a forecast grid",
  "roof and surface are not official facts in this repository and are left blank", "Q14",
  "The feed has roof and surface, but the feed is not official; publishing it as official is exactly the error this requirement exists to prevent.")
R("Two-stage skill leaderboard (proper-score qualification, then prospective CLV/ROI escrow)", "partial",
  "stage 1 proper score, stage 2 a prospective sample with closing-line value",
  "stage 1 exists; stage 2 needs the price store", "Q11 / Q03",
  "")
R("Vig-free market consensus vs originated fair-line decomposition", "partial",
  "a de-vigged consensus and a decomposition of the residual",
  "the de-vigged close is used in moneyline scoring; a consensus across operators is not stored", "Q10 / Q26",
  "")
R("Publish a weekly 'what changed' diff instead of a static snapshot", "partial",
  "a diff between dated captures",
  "shadow/whats-changed.html exists for the injury and standings captures", "SG-15 / Q13",
  "This session measured 24 of 32 records moving in three days, which is the diff's justification.")
R("Publish every model total twice until one wins", "partial",
  "two estimators side by side with a gap column, collapse only after a walk-forward comparison",
  "both estimators are built and published with a gap column; the comparison is not complete", "data/strat/dual_total.json / Q25",
  "")
R("Add a drift alarm to every scraper", "partial",
  "a pinned row count and a required-field list per scraper, failing the build loudly",
  "the depth scraper and the injury scraper have pins; not every scraper does", "tools/check_scraper_pins.py / BF-02",
  "")
R("Capture the reserve list so 'not listed' never means 'available'", "not met",
  "a reserve/injured-reserve capture joined to the weekly report",
  "no reserve-list capture", "Q15 / BF-10",
  "The wording on every page respects the rule even though the data does not exist.")
R("Reject: ranking strategies by season-long ROI", "done",
  "ROI never used to rank",
  "the board ranks on proper score; ROI is a column and is not the ranking key", "data/strat/proper_score.json",
  "This is a rejection row and the repository complies.")
R("Archive weekly injury reports for past seasons", "not met",
  "archived past-season reports",
  "0 past-season captures", "Q06 / SG-01",
  "")
R("Pre-register each strategy (definition frozen before results are seen)", "partial",
  "a commit hash for the rule before the evaluation window opens",
  "19 prospective records and 12 disclosed backtest-first records; 4 registries unreconciled", "Q16 / BF-06 / SG-05",
  "")
R("Freeze a rule before it sees data (pre-registration)", "done",
  "the rule text, the sample window and the gates committed before the window opens",
  "RULES_v1 registered at 591d8740a097 and SB-01 at 9ea55fa, both verified unchanged since", "data/prereg/ / BF-06",
  "Four registries implement this and each freezes a rule before data. The defect is coordination, not the principle.")
R("Split data into train, validation and final holdout seasons", "done",
  "three disjoint season splits with the holdout closed",
  "train 1999-2022 (6,151), validation 2023-2024 (544), holdout 2025-2026 (409, closed)", "data/prereg/corpus.json / Q20",
  "")
R("Make suggestions and a suggestions section for review before implementation", "done",
  "a suggestions page with a pre-condition and a reviewer choice per row",
  "15 suggestions with pre-conditions, costs and the decision each changes", "brief/suggestions.html / SG-01..15",
  "")
R("A clear list of questions, information and answers before any decision", "done",
  "one row per question with known, missing, decision unblocked, and how to discover it",
  "26 questions: 12 answered, 3 answered-unverified, 7 open-needs-data, 4 open-needs-policy", "brief/answers.html / Q01..Q26",
  "")
R("Originate lines and develop strategies inside a reward-bearing competition", "partial",
  "a ranked board and a reward rule",
  "no rule qualifies, so there is nothing to reward", "Q02 / SG-10",
  "")
R("Every strategy must pass validation gates; determine correlation values", "partial",
  "8 gates per strategy and a correlation for each combo pair",
  "0 of 12 clear 8 gates; 1 of 66 two-leg pairs survives BH; correlations are not published per pair", "Q02 / Q18 / Q19",
  "")
R("Remove luck and build selectively skill-based strategies", "partial",
  "a luck band per result and a skill call that survives it",
  "every result sits inside its band; no strategy is called skilful", "Q04",
  "")
R("Create an executive summary outlining important details", "done",
  "a one-page summary of what holds, what does not, and what is missing",
  "brief/index.html is the front door; pages/executive.html is the long form", "brief/index.html",
  "")
R("Create a clean landing page and category subpages with a simple dashboard UI", "done",
  "a landing page with categories and every entry in a readable table",
  "8 pages in brief/, every table row carrying a source link", "brief/",
  "")
R("Every table row must carry an official source link, or be flagged unverified", "done",
  "a build gate that fails on a sourceless row",
  "brief/verify.py fails on a row without a source link or an explicit unverified label", "brief/verify.py / Y8",
  "")
R("Multiple sessions must coordinate through COORDINATION.md", "done",
  "a claim committed before work starts, and a completion record",
  "this session claimed Y1-Y10 at commit 014f31c before touching any other file", "COORDINATION.md",
  "")
R("Open a PR, merge without waiting, confirm Pages, record the result", "done",
  "a merged PR with green checks and a recorded deploy",
  "recorded in COORDINATION.md at the end of this session", "COORDINATION.md",
  "")


def main() -> None:
    out = {
        "schema": "nfl1.brief.requirements.v1",
        "generated_at": "2026-11-16T14:36:42Z",
        "generated_by": "session 2b927826-nfl1",
        "note": ("One row per distinct requirement line of the brief, de-duplicated where the brief "
                 "restates itself in different words. 'gate' is what blocks the row, 'now' is the "
                 "number that exists today, 'src' names the artifact or check that backs the status."),
        "source_file": "tools/session-2b927826/build_requirements.py",
        "legend": {
            "done": "delivered, and an artifact exists that can be checked",
            "partial": "some of it exists",
            "not met": "the artifact does not exist",
        },
        "rows": [],
    }
    for i, r in enumerate(ROWS, 1):
        out["rows"].append({"id": f"BR-{i:02d}", **r})
    c = Counter(r["status"] for r in out["rows"])
    out["counts"] = {"rows": len(out["rows"]), **{k.replace(" ", "_"): v for k, v in sorted(c.items())},
                     "note": "computed from the rows"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {OUT} ({len(out['rows'])} rows) {out['counts']}")


if __name__ == "__main__":
    main()
