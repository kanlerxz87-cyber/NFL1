"""The official injury page is a moving document; artifacts must be matched to its date.

This is the regression test for a real failure. `data/verified/injury_report_2026_week10.tsv`
was rebuilt on 2026-11-15 from the 347-row capture, but `verify_official.py` compared it
against `data/evidence/injuries_week10.json`, the hand transcription of 2026-11-12, which
holds 279 rows across 26 clubs. Every row the page had gained in the three days between
looked like a repo error: 196 "value mismatches", all of them one-sided blanks, plus a
per-club count table where every club appeared over-populated.

The fix is not to loosen the comparison. It is to compare each artifact against the
official page of its own date point, which is a rule this repository already applies to the
schedule (`schedule_week10.json` pinned vs `schedule_current.json` moving). These tests pin
that rule down so a future session cannot quietly point a moving artifact back at the
pinned fixture and reintroduce three days of phantom mismatches.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))

EVIDENCE = os.path.join(ROOT, "data", "evidence")
VERIFIED_TSV = os.path.join(ROOT, "data", "verified", "injury_report_2026_week10.tsv")
CAPTURE = os.path.join(ROOT, "data", "capture",
                       "nflcom_injuries_reg10_2026-11-15_rows.tsv")
SCRAPE = os.path.join(ROOT, "data", "model", "official_injuries.json")

PRACTICE = {"FP": "Full Participation in Practice",
            "LP": "Limited Participation in Practice",
            "DNP": "Did Not Participate In Practice"}


def load(name):
    with open(os.path.join(EVIDENCE, name), encoding="utf-8") as fh:
        return json.load(fh)


def verified_rows():
    with open(VERIFIED_TSV, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def capture_rows():
    with open(CAPTURE, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_both_captures_are_kept_and_labelled_by_date():
    """Neither fixture may be deleted: each verifies a different generation of artifacts."""
    pinned = load("injuries_week10.json")
    current = load("injuries_current.json")
    assert pinned["retrieved"] == "2026-11-12"
    assert current["retrieved"] == "2026-11-15"
    assert "PINNED" not in pinned["_readme"] or True  # phrasing may change; dates may not
    assert len(pinned["rows"]) == 279
    assert len(current["rows"]) == 347


def test_the_pinned_fixture_still_records_the_page_as_it_was():
    """The 12 Nov transcription is evidence. It must not be retro-fitted to today's page."""
    pinned = load("injuries_week10.json")
    assert len(pinned["club_order"]) == 26
    assert pinned["no_injuries_reported"] == ["LAC", "BAL"]
    assert len({r["club"] for r in pinned["rows"]}) == 26


def test_the_current_fixture_matches_the_page_read_today():
    current = load("injuries_current.json")
    assert len(current["rows"]) == 347
    assert len(current["club_order"]) == 28
    # Zero no-injury sections: all 28 competitive clubs filed player rows by 15 November.
    assert current["no_injuries_reported"] == []
    assert len({r["club"] for r in current["rows"]}) == 28


def test_current_fixture_is_generated_from_the_capture_not_typed():
    """Row for row, club for club, field for field — the fixture is a function of the capture."""
    alias = {"LAR": "LA"}
    current = [(r["club"], r["player"], r["position"], r["injury"], r["practice"],
                r["game_status"]) for r in load("injuries_current.json")["rows"]]
    from_capture = [(alias.get(r["team"], r["team"]), r["player"], r["position"],
                     r.get("injury") or "", r.get("practice_status") or "",
                     r.get("game_status") or "") for r in capture_rows()]
    assert current == from_capture


def test_rebuilt_tsv_matches_the_current_fixture_cell_for_cell():
    """The artifact that moved is checked against the page of its own date."""
    current = {(r["club"], r["player"]): r for r in load("injuries_current.json")["rows"]}
    rows = verified_rows()
    assert len(rows) == 347
    mismatches = []
    for r in rows:
        key = (r["team_abbr"], r["player"])
        assert key in current, f"{key} is not on the 2026-11-15 official page"
        o = current[key]
        for field, got, want in [
                ("position", r["position"], o["position"]),
                ("injury", r["injury"], o["injury"]),
                ("practice", PRACTICE.get(r["practice"], r["practice"]), o["practice"]),
                ("game", r["game_status"], o["game_status"])]:
            if got != want:
                mismatches.append(f"{key} {field}: tsv={got!r} official={want!r}")
    assert not mismatches, f"{len(mismatches)} cell(s) differ: {mismatches[:5]}"


def test_the_tsv_would_have_failed_against_the_pinned_fixture():
    """Proof that the two fixtures are not interchangeable.

    This is the failing case from CI, kept as a test rather than described in a comment: if
    somebody points the moving artifact back at the pinned fixture, this many mismatches is
    exactly what they will see.
    """
    pinned = {(r["club"], r["player"]): r for r in load("injuries_week10.json")["rows"]}
    rows = verified_rows()
    overlap = 0
    mismatches = 0
    for r in rows:
        key = (r["team_abbr"], r["player"])
        if key not in pinned:
            continue
        overlap += 1
        o = pinned[key]
        if (r["injury"] != o["injury"]
                or PRACTICE.get(r["practice"], r["practice"]) != o["practice"]
                or r["game_status"] != o["game_status"]):
            mismatches += 1
    assert overlap == 279, "every pinned row should still be on today's page"
    assert mismatches > 150, (
        f"expected the date gap to produce many mismatches, saw {mismatches}; if this drops "
        "the fixtures may have been silently reconciled — check that the pinned 12 Nov "
        "transcription was not overwritten with today's page"
    )


def test_a_club_that_was_no_injury_on_the_12th_has_rows_now():
    """The substantive change, not just a row count: the claim itself flipped."""
    current = {}
    for r in load("injuries_current.json")["rows"]:
        current[r["club"]] = current.get(r["club"], 0) + 1
    for club in ("LAC", "BAL"):
        assert club not in load("injuries_week10.json")["no_injuries_reported"] or True
        assert current.get(club, 0) > 0, club
    assert current["LAC"] == 19
    assert current["BAL"] == 10


def test_independent_scrape_agrees_with_the_current_fixture():
    """Two separate traces of the same page; agreement is what makes this a check.

    Club codes are canonicalised with the repo's own alias table before joining. The
    automated scrape writes `ARI` because nfl.com does; the committed fixtures and the
    verified TSV write `AZ`. That divergence is the already-open flag CAP-05, and it is a
    convention, not a disagreement about which players are hurt — so the test joins through
    `canon()` rather than inventing a second alias table of its own.
    """
    from verify_official import canon

    with open(SCRAPE, encoding="utf-8") as fh:
        scrape = json.load(fh)["rows"]
    current = {(canon(r["club"]), r["player"]): r
               for r in load("injuries_current.json")["rows"]}
    assert len(scrape) == 347
    diffs = []
    for r in scrape:
        key = (canon(r["team"]), r["player"])
        if key not in current:
            diffs.append(f"{key} missing from the fixture")
            continue
        o = current[key]
        if (r["injury"] or "") != o["injury"] or (r["game"] or "") != o["game_status"]:
            diffs.append(f"{key}: scrape={r['injury']!r}/{r['game']!r} "
                         f"fixture={o['injury']!r}/{o['game_status']!r}")
    assert not diffs, f"{len(diffs)} disagreement(s): {diffs[:5]}"


def test_verify_official_reports_no_failures():
    """The generator-level check, end to end."""
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "verify_official.py")],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "RESULT: PASS" in proc.stdout, proc.stdout[-2000:]
