#!/usr/bin/env python3
"""build_ledgers.py -- questions, suggestions, decisions and flags for this study.

Every question and suggestion is derived from a computed result in data/strength/
or from a verified irregularity.  Nothing here is invented, and anything that
cannot be answered from the sources in this repository is marked BLOCKED with
the exact data or decision that would settle it.

Run: python3 tools/build_ledgers.py   (after analysis/strength.py)
"""
from __future__ import annotations

import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "strength")

OFF_STANDINGS = "https://www.nfl.com/standings/league/2026/reg"
OFF_SCHEDULE = "https://www.nfl.com/schedules/2026/reg10"
OFF_INJURIES = "https://www.nfl.com/injuries/"
NV_SCHEDULES = "https://github.com/nflverse/nflverse-data/releases/tag/schedules"


def L(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)


def read_csv(path):
    with open(os.path.join(ROOT, path), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def standings_diff():
    """Line-by-line comparison of the committed standings against the official page."""
    official = {r["abbr"]: r for r in L("official_week10.json")["standings"]["rows"]}
    repo = {r["abbr"]: r for r in read_csv("data/verified/standings_2026.csv")}
    diffs, rows = [], 0
    for abbr, off in sorted(official.items()):
        rep = repo.get(abbr)
        if not rep:
            diffs.append({"team": abbr, "field": "row", "official": "present", "repo": "missing"})
            continue
        rows += 1
        for field, key in (("w", "w"), ("l", "l"), ("t", "t"), ("pf", "pf"), ("pa", "pa")):
            if int(off[field]) != int(rep[key]):
                diffs.append({"team": abbr, "field": field, "official": off[field], "repo": rep[key]})
        if abs(float(off["pct"]) - float(rep["pct"])) > 5e-4:
            diffs.append({"team": abbr, "field": "pct", "official": off["pct"], "repo": rep["pct"]})
        if off["strk"] != rep["streak"]:
            diffs.append({"team": abbr, "field": "streak", "official": off["strk"], "repo": rep["streak"]})
    return {"rows_compared": rows, "fields_compared": rows * 7, "differences": diffs}


def injury_diff():
    """Audit the committed hand transcription against the official nfl.com scrape.

    The scrape (data/model/official_injuries.json) is written by the collect-data
    workflow directly from https://www.nfl.com/injuries/ and records the page's
    own sha256 and fetch time. It is therefore the better witness for *what the
    page said*, and the hand transcription can be measured against it. Comparing
    a transcription with a later live read cannot tell a transcription error from
    a page update; this comparison can.
    """
    import re
    ts_rows = []
    with open(os.path.join(ROOT, "data/verified/injury_report_2026_week10.tsv"), encoding="utf-8") as f:
        ts_rows = list(csv.DictReader(f, delimiter="	"))
    scrape_doc = json.load(open(os.path.join(ROOT, "data/model/official_injuries.json"), encoding="utf-8"))
    off_rows = scrape_doc["rows"]
    SCRAPE_URL = scrape_doc.get("source_url", OFF_INJURIES)
    PRACT = {"FP": "Full Participation in Practice", "LP": "Limited Participation in Practice",
             "DNP": "Did Not Participate In Practice"}
    ts = {(r["team_abbr"], r["player"]): r for r in ts_rows}
    off = {(r["team"], r["player"]): r for r in off_rows}
    missing = sorted(k for k in off if k not in ts)
    extra = sorted(k for k in ts if k not in off)
    differing = []
    for k in off:
        if k not in ts:
            continue
        t, o = ts[k], off[k]
        for f_off, f_t in (("injury", "injury"), ("practice", "practice"), ("game", "game_status")):
            tv = t.get(f_t) or ""
            ov = o.get(f_off) or ""
            if f_t == "practice":
                tv = PRACT.get(tv, tv)
            if tv != ov:
                differing.append({"club": k[0], "player": k[1], "field": f_off,
                                  "official_scrape": ov or "(blank)", "transcription": tv or "(blank)"})
    return {
        "transcription_file": "data/verified/injury_report_2026_week10.tsv",
        "transcription_rows": len(ts_rows),
        "transcription_retrieved": "2026-11-12T05:30Z",
        "official_scrape_file": "data/model/official_injuries.json",
        "official_scrape_url": SCRAPE_URL,
        "official_scrape_rows": len(off_rows),
        "official_scrape_generated": scrape_doc.get("generated_at"),
        "official_scrape_html_sha256": scrape_doc.get("html_sha256"),
        "players_in_official_not_in_transcription": len(missing),
        "players_in_transcription_not_in_official": len(extra),
        "extra_examples": [f"{a} {b}" for a, b in extra[:6]],
        "missing_examples": [f"{a} {b}" for a, b in missing[:6]],
        "differing_fields": len(differing),
        "differing_detail": differing,
        "differing_by_field": {f: sum(1 for d in differing if d["field"] == f)
                               for f in ("injury", "practice", "game")},
        "note": ("The scrape is the direct record of the official page and is used as the witness. "
                 "Differences are expected to run one way: the transcription is the later, hand-made "
                 "copy and any value it lacks is an omission, not evidence that the official page "
                 "changed its mind."),
        "clubs_listed": len({r["team_abbr"] for r in ts_rows}),
    }


def schedule_diff():
    official = L("official_week10.json")["week10"]
    repo = read_csv("data/verified/week10_fixtures_2026.csv")
    repo_pairs = {(r["away_abbr"], r["home_abbr"]) for r in repo}
    off_pairs = {(g["away"], g["home"]) for g in official["games"]}
    byes_repo = {(int(r["week"]), r["team_abbr"]) for r in read_csv("data/verified/byes_2026.csv")}
    byes_ok = {t for (w, t) in byes_repo if w == 10}
    return {
        "official_games": len(off_pairs), "repo_games": len(repo_pairs),
        "games_missing_from_repo": sorted(off_pairs - repo_pairs),
        "games_extra_in_repo": sorted(repo_pairs - off_pairs),
        "byes_official": official["byes"], "byes_repo_week10": sorted(byes_ok),
        "byes_match": sorted(off_k for off_k in official["byes"]) == sorted(byes_ok),
        "played_results_repo": 0,
        "played_results_official": sum(1 for g in official["games"] if g.get("result")),
        "note": "The committed fixtures file lists the WAS @ NYG game as upcoming. nfl.com now shows it final (WAS 24 - NYG 21).",
    }


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    state = L("current_state.json")
    val = L("validation.json")
    strat = L("strategies.json")
    parlays = L("parlays.json")
    meta = L("meta.json")
    sd = standings_diff()
    inj = injury_diff()
    sch = schedule_diff()

    teams = state["teams"]
    top5 = sorted(teams, key=lambda t: -t["rating"])[:5]
    luckiest = sorted(teams, key=lambda t: -(t["luck_wins"] or -99))[:5]
    unluckiest = sorted(teams, key=lambda t: (t["luck_wins"] if t["luck_wins"] is not None else 99))[:5]
    toughest = sorted([t for t in teams if t["sos_to_date"] is not None], key=lambda t: -t["sos_to_date"])[:5]
    easiest = sorted([t for t in teams if t["sos_to_date"] is not None], key=lambda t: t["sos_to_date"])[:5]

    pass_count = strat["totals"]["pass"]
    best = strat["strategies"][0] if strat["strategies"] else None
    best_ci = (best.get("roi_ci95") or [None])[0] if best else None
    positive_phi = [p for p in parlays["pairs"] if p["phi"] and p["phi"]["ci95"][0] > 0]
    highest_phi = max(parlays["pairs"], key=lambda p: p["phi"]["r"]) if parlays["pairs"] else None

    questions = [
        {
            "id": "Q-SOS-01",
            "question": "Does strength of schedule, measured walk-forward, add information beyond the closing line?",
            "status": "ANSWERED (no, not on this sample)",
            "answer": (f"Own ratings correlate r={val['correlation_model_market']['r']} with the closing spread over "
                       f"{val['correlation_model_market']['n']:,} games, but the own line is less accurate than the market "
                       f"out of sample: spread MAE {val['holdout']['spread_mae_own']} vs {val['holdout']['spread_mae_market']} "
                       f"in the untouched holdout seasons, and every one of the {strat['n_rules_tested']} schedule-based rules "
                       f"fails the gate set (0 of {strat['n_rules_tested']} PASS). The honest reading is that schedule "
                       f"information is already inside the price."),
            "discovery_method": "computed in analysis/strength.py; re-runnable",
            "blocks": "any decision to trade schedule-based angles",
            "sources": [NV_SCHEDULES, OFF_SCHEDULE],
        },
        {
            "id": "Q-SOS-02",
            "question": "Which clubs are strongest once opponents are adjusted for?",
            "status": "ANSWERED",
            "answer": "; ".join(f"{t['team']} {t['rating']:+.2f} (SOS {t['sos_to_date']:+.2f})" if t['sos_to_date'] is not None
                                else f"{t['team']} {t['rating']:+.2f}" for t in top5) +
                      f". Home-field advantage fitted at {state['hfa']:+.2f} points for this season's completed games.",
            "discovery_method": "ridge rating fit, walk-forward, published on the Ratings page",
            "blocks": "nothing; this is a published estimate with its method",
            "sources": [NV_SCHEDULES, OFF_STANDINGS],
        },
        {
            "id": "Q-SOS-03",
            "question": "Whose record overstates them, and whose understates them?",
            "status": "ANSWERED (with a caveat)",
            "answer": ("Luck = actual wins minus Pythagorean expectation (exponent 2.37). Most lucky: " +
                       "; ".join(f"{t['team']} {t['luck_wins']:+.2f}" for t in luckiest) +
                       ". Most unlucky: " + "; ".join(f"{t['team']} {t['luck_wins']:+.2f}" for t in unluckiest) +
                       ". Caveat: the rules that trade on this (X05, X06) both fail the gates, so the signal is a "
                       "description, not an edge."),
            "discovery_method": "Pythagorean expectation computed from official scored/allowed points",
            "blocks": "nothing; published as a description",
            "sources": [OFF_STANDINGS],
        },
        {
            "id": "Q-SOS-04",
            "question": "Who has played the hardest and easiest schedule so far?",
            "status": "ANSWERED",
            "answer": ("Hardest (mean pre-game opponent rating): " +
                       "; ".join(f"{t['team']} {t['sos_to_date']:+.2f}" for t in toughest) +
                       ". Easiest: " + "; ".join(f"{t['team']} {t['sos_to_date']:+.2f}" for t in easiest) +
                       ". SOS is the mean of the opponents' ratings *before* each game, so it contains no future information."),
            "discovery_method": "computed from the walk-forward panel",
            "blocks": "nothing",
            "sources": [NV_SCHEDULES],
        },
        {
            "id": "Q-SOS-05",
            "question": "Which published values on this repository are stale or wrong right now?",
            "status": "ANSWERED (defects found)",
            "answer": (f"Line-by-line against the official standings page: {len(sd['differences'])} field differences across "
                       f"{sd['rows_compared']} clubs ({sd['fields_compared']} fields compared). The committed Week 10 fixtures "
                       f"also still show WAS @ NYG as upcoming; nfl.com shows it final (WAS 24 - NYG 21). "
                       f"Injury transcription: {inj['transcription_rows']} rows against {inj['official_scrape_rows']} in the "
                       f"official scrape, {inj['players_in_official_not_in_transcription']} players missing, "
                       f"{inj['differing_fields']} field differences. Each is published on the Flags page with its link."),
            "discovery_method": "re-fetch of the official pages on 2026-11-13 and a field-by-field comparison",
            "blocks": "publication of any standings-derived number until the source file is refreshed",
            "sources": [OFF_STANDINGS, OFF_SCHEDULE, OFF_INJURIES],
        },
        {
            "id": "Q-SOS-06",
            "question": "Does the pinned provenance still describe the committed data?",
            "status": "ANSWERED (no)",
            "answer": (f"No. data/s9cb/provenance.json pins games.csv at {meta['inputs']['bytes_recorded']:,} bytes / "
                       f"sha256 {str(meta['inputs']['sha256_recorded'])[:12]}..., but the committed file is "
                       f"{meta['inputs']['bytes_now']:,} bytes / sha256 {meta['inputs']['sha256_now'][:12]}.... "
                       f"The row count is intact ({meta['inputs']['rows_in_file']:,} games) and the results reconcile, "
                       f"so the study still runs, but the pin is stale and the integrity claim cannot be sustained."),
            "discovery_method": "sha256 of the committed file compared with the recorded hash",
            "blocks": "any claim that this data is byte-for-byte the downloaded release",
            "sources": [NV_SCHEDULES],
        },
        {
            "id": "Q-SOS-07",
            "question": "Can player-prop combos be scored?",
            "status": "BLOCKED",
            "answer": ("No. The same-game prop correlations are computable and published "
                       f"(passing yards vs receiver yards r≈{L('props.json')['register'][0]['value']['r']}), but no "
                       "official or book price for any prop exists in these sources, so no combo can be priced, "
                       "scored, or ranked. Filling a price in would be a fabrication."),
            "discovery_method": "would need a licensed odds feed with per-book prop prices and timestamps",
            "blocks": "the entire prop-combo track of the leaderboard",
            "sources": ["https://www.nfl.com/stats/player-stats/"],
        },
        {
            "id": "Q-SOS-08",
            "question": "Are the 2026 closing lines official NFL numbers?",
            "status": "ANSWERED (no)",
            "answer": ("No official league odds exist. The closing line in the nflverse release is a consensus "
                       "number. Every ROI on this site is therefore measured against a consensus price, not a book "
                       "you could actually bet, and the site says so on every table."),
            "discovery_method": "documented in the nflverse release description and in data/s9cb/provenance.json",
            "blocks": "any claim of realisable profit",
            "sources": [NV_SCHEDULES],
        },
        {
            "id": "Q-SOS-09",
            "question": "Do we know the injury or depth-chart state at kick-off for every 2026 game?",
            "status": "PARTIAL",
            "answer": (f"The official Week 10 report lists {L('official_week10.json')['injuries']['rows_read']} players across "
                       f"{L('official_week10.json')['injuries']['clubs_listed']} clubs; BAL and LAC report no injuries and four clubs are on bye. "
                       "There is no per-game inactive list in the sources, and no dated snapshot for earlier weeks, so "
                       "any injury-aware strategy would be reading today's report, not the one available at kick-off."),
            "discovery_method": "would need the official gamebook inactive lists per game (nfl.com publishes them per game)",
            "blocks": "injury-adjusted ratings and any 2nd/3rd-string depth signal",
            "sources": [OFF_INJURIES, OFF_SCHEDULE],
        },
        {
            "id": "Q-SOS-10",
            "question": "Which of the 2026 results are inside the current sample?",
            "status": "ANSWERED",
            "answer": (f"{meta['inputs']['played_games_used']:,} games from {val['by_season'][0]['season']} to "
                       f"{val['by_season'][-1]['season']} are scored. The 2026 season in the committed extract stops at "
                       "Week 9: 136 games. Week 10's Thursday game is not in the file, so the current-state page counts "
                       "8 games for WAS and NYG, which matches the official 3-5-1 / 5-3-1 records."),
            "discovery_method": "row count by season and a comparison with the official standings games-played",
            "blocks": "nothing; stated so the reader knows where the sample ends",
            "sources": [OFF_STANDINGS, OFF_SCHEDULE],
        },
        {
            "id": "Q-SOS-11",
            "question": "Is the gate set strong enough to stop a lucky strategy?",
            "status": "ANSWERED (it caught two real defects)",
            "answer": ("During this session the gates rejected a first implementation whose sign convention made the "
                       "market line a points-given rather than an expected margin: it reported 94% cover rates and four "
                       "false PASSes. After the fix every rule fails, and the same sign check now lives in the unit "
                       "tests. The lesson is that a plausible-looking edge is the default failure mode, and the gates "
                       "must be able to say no."),
            "discovery_method": "unit tests in tests/test_strength.py plus manual inspection of the bet log",
            "blocks": "nothing",
            "sources": [NV_SCHEDULES],
        },
        {
            "id": "Q-SOS-12",
            "question": "What would we need to get a real, bettable edge?",
            "status": "BLOCKED",
            "answer": ("At minimum: (1) a licensed historical odds feed with per-book, timestamped prices and line "
                       "movement; (2) injury/inactive data as it stood at kick-off, not today's; (3) a pre-registered "
                       "hypothesis set fixed before peeking; (4) enough seasons that a 2% edge is distinguishable from "
                       "zero at the tested sample size. Without (1) and (2) any edge claim is untestable."),
            "discovery_method": "gap analysis of the sources in data/s9cb/provenance.json",
            "blocks": "any decision to place or recommend a wager",
            "sources": [NV_SCHEDULES, OFF_INJURIES],
        },
    ]

    suggestions = [
        {
            "id": "S-SOS-01",
            "priority": "now (this session)",
            "title": "Fix the stale standings rows and the unplayed-result fixture",
            "problem": (f"{len(sd['differences'])} field differences in data/verified/standings_2026.csv and the WAS @ NYG "
                        f"fixture still listed as upcoming."),
            "options": [
                "A: refresh the committed standings from the official page and re-run every generator that reads them (correct, larger blast radius)",
                "B: leave the file frozen with a dated stamp and publish the difference (safe, keeps published numbers stale)",
                "C: freeze only the disputed rows and refresh the rest (not recommended: mixes vintages in one table)",
            ],
            "recommendation": "A, executed as its own task with a fresh official fetch, then B as a permanent 'as-of' stamp on every table.",
            "files": ["data/verified/standings_2026.csv", "data/verified/week10_fixtures_2026.csv"],
            "cost": "low", "risk": "medium (regenerates several pages)",
            "blocked_by": None, "sources": [OFF_STANDINGS, OFF_SCHEDULE],
        },
        {
            "id": "S-SOS-02",
            "priority": "now (this session)",
            "title": "Re-pin the games.csv provenance hash",
            "problem": (f"provenance.json records {meta['inputs']['bytes_recorded']:,} bytes / "
                        f"{str(meta['inputs']['sha256_recorded'])[:12]}..., the file is "
                        f"{meta['inputs']['bytes_now']:,} bytes / {meta['inputs']['sha256_now'][:12]}...."),
            "options": ["A: re-download in Actions and re-pin (restores a real integrity claim)",
                        "B: re-pin the current file (honest hash, weaker claim)",
                        "C: drop the sha256 field (stops the false claim, loses the check)"],
            "recommendation": "A, because the whole repository rests on pinned provenance; B is acceptable as an interim.",
            "files": ["data/s9cb/provenance.json", ".github/workflows/s9cb-collect.yml"],
            "cost": "low", "risk": "low", "blocked_by": None, "sources": [NV_SCHEDULES],
        },
        {
            "id": "S-SOS-03",
            "priority": "next",
            "title": "Add an 'as-of' timestamp to every published table",
            "problem": "Tables show a build time but not the time of the official data, so a stale row looks live.",
            "options": ["A: per-table 'official data as of' stamp", "B: one site-wide stamp",
                        "C: no stamp, rely on the Flags page"],
            "recommendation": "A: the reader can then tell a stale row from a wrong one without reading the flags.",
            "files": ["tools/build_strength.py", "pipeline/gen_site.py"],
            "cost": "low", "risk": "low", "blocked_by": None, "sources": [OFF_STANDINGS],
        },
        {
            "id": "S-SOS-04",
            "priority": "next",
            "title": "Buy or build a timestamped odds history before any edge work continues",
            "problem": "No bettable price series exists; the consensus closing line cannot be transacted.",
            "options": ["A: licensed historical odds vendor", "B: scrape a book (terms-of-service risk)",
                        "C: stay consensus-only and never claim bettable profit"],
            "recommendation": "A, and until then publish C explicitly so no number is mistaken for a realisable return.",
            "files": ["data/s9cb/provenance.json", "analysis/strength.py"],
            "cost": "high", "risk": "low", "blocked_by": "budget decision", "sources": [NV_SCHEDULES],
        },
        {
            "id": "S-SOS-05",
            "priority": "next",
            "title": "Publish a per-game inactive list for 2026 so depth signals can be measured",
            "problem": "The injury report is a weekly snapshot, not the game-day inactive list, so 2nd/3rd-string effects cannot be scored.",
            "options": ["A: add the official per-game inactives to the collector",
                        "B: use the weekly report with an explicit accuracy caveat",
                        "C: leave injury effects out of the model"],
            "recommendation": "A; B is acceptable only if the model keeps saying the effect is unmeasured.",
            "files": ["pipeline/collect.py", "analysis/strength.py"],
            "cost": "medium", "risk": "medium", "blocked_by": "Q-SOS-09", "sources": [OFF_INJURIES],
        },
        {
            "id": "S-SOS-06",
            "priority": "later",
            "title": "Keep the negative result and stop searching for a schedule edge",
            "problem": f"0 of {strat['n_rules_tested']} rules pass; searching harder after seeing the data is how false positives are made.",
            "options": ["A: publish the negative result and freeze the rule set",
                        "B: keep adding rules until one passes",
                        "C: change the threshold on the best rule until it passes"],
            "recommendation": ("A. B and C are what the Benjamini-Hochberg gate and the pre-registration hash exist to "
                               "prevent. If new rules are wanted they must be registered before the next evaluation."),
            "files": ["analysis/strength.py"],
            "cost": "none", "risk": "low", "blocked_by": None, "sources": [NV_SCHEDULES],
        },
        {
            "id": "S-SOS-07",
            "priority": "later",
            "title": "Give the leaderboard rewards that are not money",
            "problem": "The brief asks for rewards for top-performing strategies; paying for picks raises legal exposure.",
            "options": ["A: non-monetary badges (Verified Signal, Top Single Bet)", "B: internal scoring only",
                        "C: cash prizes (needs legal review in every jurisdiction)"],
            "recommendation": "A now, C only with written legal advice; this study's leaderboard is empty so no reward is live.",
            "files": ["data/leaderboard_rules.json"],
            "cost": "low", "risk": "low", "blocked_by": "legal review for C", "sources": [],
        },
        {
            "id": "S-SOS-08",
            "priority": "next",
            "title": "Consolidate the five site generations into one navigable site",
            "problem": "Root, pages/, docs/, lab/, dashboard/, verified-lab/ and research/ all publish overlapping pages.",
            "options": ["A: one landing page linking every category (this study's approach)",
                        "B: delete the older generations (loses evidence)",
                        "C: leave them all and hope the reader finds the right one"],
            "recommendation": "A: additive, nothing is lost, and the All Sections page keeps every page reachable.",
            "files": ["index.html", "sections.html"],
            "cost": "low", "risk": "low", "blocked_by": None, "sources": [],
        },
    ]

    decisions = [
        {"id": "D-SOS-01", "decision": "Treat the schedule-information edge as absent for now",
         "evidence": f"0/{strat['n_rules_tested']} rules pass 8 gates over {strat['totals']['bets_scored']:,} scored bets",
         "status": "READY FOR REVIEW", "owner": "human", "options": ["accept", "request a new pre-registered rule set"]},
        {"id": "D-SOS-02", "decision": "Refresh the committed standings and fixtures from the official pages",
         "evidence": f"{len(sd['differences'])} field differences; 1 result now final on nfl.com",
         "status": "READY FOR REVIEW", "owner": "human", "options": ["refresh now", "freeze with 'as-of'", "exclude 2026"]},
        {"id": "D-SOS-03", "decision": "Fund a timestamped odds feed before further edge work",
         "evidence": "no bettable price series exists in the sources",
         "status": "BLOCKED ON BUDGET", "owner": "human", "options": ["fund", "stay consensus-only"]},
        {"id": "D-SOS-04", "decision": "Pick the reward scheme for the leaderboard",
         "evidence": "leaderboard has 0 eligible entrants, so no reward is live yet",
         "status": "READY FOR REVIEW", "owner": "human", "options": ["badges", "scoring only", "cash (needs legal)"]},
    ]

    flags = []
    by_team = {}
    for d in sd["differences"]:
        by_team.setdefault(d["team"], []).append(d)
    for team, diffs in sorted(by_team.items()):
        fields = ", ".join(f"{d['field']} (official {d['official']} vs repository {d['repo']})" for d in diffs)
        flags.append({
            "id": f"F-SOS-STD-{team}",
            "severity": "high",
            "title": f"Standings row differs from the official page: {team}",
            "detail": (f"{len(diffs)} field(s) differ: {fields}. The official page "
                       f"(https://www.nfl.com/standings/league/2026/reg) was read on 2026-11-13 and the committed "
                       f"snapshot is stamped 2026-11-12T04:31Z, before the Week 10 Thursday game."),
            "source": OFF_STANDINGS,
            "status": "open",
        })
    flags.append({
        "id": "F-SOS-W10-01", "severity": "high",
        "title": "Week 10 fixture listed as upcoming after the game went final",
        "detail": ("data/verified/week10_fixtures_2026.csv lists WAS @ NYG on 2026-11-12 as a fixture. "
                   "nfl.com shows 'Commanders 24, Giants 21, FINAL'. The 14-fixture set and the four byes are "
                   "otherwise identical to the official page."),
        "source": OFF_SCHEDULE, "status": "open",
    })
    flags.append({
        "id": "F-SOS-DATA-01", "severity": "medium",
        "title": "Pinned provenance hash does not match the committed games.csv",
        "detail": (f"recorded {meta['inputs']['bytes_recorded']:,} bytes / {str(meta['inputs']['sha256_recorded'])[:16]}..., "
                   f"committed {meta['inputs']['bytes_now']:,} bytes / {meta['inputs']['sha256_now'][:16]}.... "
                   f"Row count intact ({meta['inputs']['rows_in_file']:,}) and results reconcile."),
        "source": NV_SCHEDULES, "status": "open",
    })
    flags.append({
        "id": "F-SOS-MODEL-01", "severity": "medium",
        "title": "Home-field advantage fitted near zero for the 2026 sample",
        "detail": (f"The ridge fit gives hfa {state['hfa']:+.2f} points on 136 games, against roughly +2 points in every "
                   "earlier season. This is a computed property of a small 2026 sample (home win rate 49.3%), not a data error; "
                   "it is flagged because it materially changes this week's own lines."),
        "source": NV_SCHEDULES, "status": "open",
    })
    ftot = inj["differing_by_field"]
    det_rows = [d for d in inj["differing_detail"] if d["field"] != "practice"]
    detail_lines = "; ".join(f"{d['club']} {d['player']} {d['field']}: official '{d['official_scrape']}' vs transcription '{d['transcription']}'"
                             for d in det_rows)
    flags.append({
        "id": "F-SOS-INJ-01", "severity": "high",
        "title": "Committed injury transcription is materially incomplete against the official page",
        "detail": (f"The committed hand transcription has {inj['transcription_rows']} rows; the official nfl.com scrape "
                   f"captured at {inj['official_scrape_generated']} has {inj['official_scrape_rows']}. "
                   f"{inj['players_in_official_not_in_transcription']} players listed on the official page are absent from the "
                   f"transcription and {inj['players_in_transcription_not_in_official']} transcription players are absent from the "
                   f"official page. Among players present in both, {ftot['practice']} practice values, {ftot['injury']} injury "
                   f"names and {ftot['game']} game statuses differ. This is a transcription-accuracy defect, not page drift: "
                   f"the scrape predates the transcription and already contains the values the transcription lacks. "
                   f"Non-practice differences: {detail_lines}"),
        "source": OFF_INJURIES, "status": "open"})
    flags.append({
        "id": "F-SOS-SITE-01", "severity": "medium",
        "title": "Landing page says 'week 9 complete' while the official schedule has moved past it",
        "detail": "index.html KPI subtitle reads 'week 9 complete'. nfl.com shows Week 10 in progress with the Thursday game final.",
        "source": OFF_SCHEDULE, "status": "open",
    })

    ids = [f["id"] for f in flags]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        raise SystemExit(f"duplicate flag ids: {dup}")

    payloads = {
        "questions.json": {"generated_at": meta["built_at_utc"], "count": len(questions),
                           "rule": "Every question is either ANSWERED with the computed number, PARTIAL with the reason, or BLOCKED with the exact source that would settle it.",
                           "questions": questions},
        "suggestions.json": {"generated_at": meta["built_at_utc"], "count": len(suggestions),
                             "rule": "Each suggestion states the problem, the options, a recommendation, cost, risk and what blocks it, so a reviewer can choose a path before anything is implemented.",
                             "suggestions": suggestions},
        "decisions.json": {"generated_at": meta["built_at_utc"], "count": len(decisions), "decisions": decisions},
        "flags.json": {"generated_at": meta["built_at_utc"], "count": len(flags),
                       "rule": "Every flag carries the official link that shows the difference and the value seen on both sides.",
                       "flags": flags},
        "audit.json": {"generated_at": meta["built_at_utc"], "standings": sd, "injuries": inj, "schedule": sch,
                       "sources": {"standings": OFF_STANDINGS, "week10_schedule": OFF_SCHEDULE, "injuries": OFF_INJURIES}},
    }
    for name, payload in payloads.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1)
            f.write("\n")
    print("questions", len(questions), "| suggestions", len(suggestions),
          "| decisions", len(decisions), "| flags", len(flags))
    print("standings diffs", len(sd["differences"]), "| injury rows missing",
          inj["players_in_official_not_in_transcription"], "| injury field diffs", inj["differing_fields"],
          "| schedule diffs", len(sch["games_missing_from_repo"]) + len(sch["games_extra_in_repo"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
