"""Tests for the session `57c05555-nfl1` repair of the verified injury filings.

The failure these guard against is concrete and was published: four clubs were shown as
having no injuries at all while the official page listed 15, 9, 19 and 10 players for them.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURE = os.path.join(ROOT, "data", "capture", "nflcom_injuries_reg10_2026-11-15_rows.tsv")
REPORT = os.path.join(ROOT, "data", "verified", "injury_report_2026_week10.tsv")
NONE_FILE = os.path.join(ROOT, "data", "verified", "no_injuries_week10.csv")
GAMES = os.path.join(ROOT, "data", "injury_games.json")
PAGE = os.path.join(ROOT, "injuries.html")

ALIAS = {"AZ": "ARI", "LAR": "LA"}


def capture_rows():
    return list(csv.DictReader(open(CAPTURE, encoding="utf-8"), delimiter="\t"))


def report_rows():
    return list(csv.DictReader(open(REPORT, encoding="utf-8"), delimiter="\t"))


def per_club(rows, key):
    out: dict[str, int] = {}
    for r in rows:
        club = ALIAS.get(r[key], r[key])
        out[club] = out.get(club, 0) + 1
    return out


# ------------------------------------------------------------------ the counts
def test_the_verified_report_holds_every_row_of_the_capture():
    assert len(report_rows()) == len(capture_rows()) == 347


def test_the_verified_report_covers_all_28_playing_clubs():
    assert len(per_club(report_rows(), "team_abbr")) == 28


def test_every_club_row_count_matches_the_capture():
    assert per_club(report_rows(), "team_abbr") == per_club(capture_rows(), "team")


def test_the_four_clubs_the_stale_file_called_injury_free_are_present():
    counts = per_club(report_rows(), "team_abbr")
    assert counts["SEA"] == 15
    assert counts["CIN"] == 9
    assert counts["LAC"] == 19
    assert counts["BAL"] == 10


def test_the_bye_clubs_still_have_no_table():
    counts = per_club(report_rows(), "team_abbr")
    for club in ("CHI", "DEN", "PHI", "TB"):
        assert counts.get(club, 0) == 0


# ------------------------------------------------------------- the corrections
def test_the_no_injuries_file_no_longer_claims_any_club_is_injury_free():
    rows = list(csv.DictReader(open(NONE_FILE, encoding="utf-8")))
    assert rows, "the file should record the correction"
    for r in rows:
        assert "No Injuries Reported" not in r["reported_state"]
        assert r["reported_state"].startswith("Reported injuries on the official page")
        assert r["source_url"].startswith("https://www.nfl.com/injuries/")
        assert r["retrieved_at"]


def test_the_per_game_file_carries_real_counts_not_a_no_injury_claim():
    games = json.load(open(GAMES, encoding="utf-8"))
    assert len(games) == 14
    for g in games:
        assert "No Injuries Reported" not in g["report_state"], g
        assert "injury table published" in g["report_state"]


def test_the_published_injuries_page_has_no_false_no_injury_claim():
    t = open(PAGE, encoding="utf-8").read()
    assert "No Injuries Reported" not in t


# --------------------------------------------------------------- the series
def test_the_evolution_record_is_a_series_with_increasing_coverage():
    evo = json.load(open(os.path.join(ROOT, "data", "ledger", "injury_report_evolution.json"),
                         encoding="utf-8"))
    series = evo["series"]
    assert len(series) >= 3
    rows = [p["rows"] for p in series]
    assert rows == sorted(rows), "the series must be in capture order"
    assert rows[-1] == 347
    assert series[-1]["clubs_printing_no_injuries"] == 0
    for p in series:
        assert p["captured"] and p["artifact"] and p["note"]


def test_the_evolution_delta_arithmetic_holds():
    evo = json.load(open(os.path.join(ROOT, "data", "ledger", "injury_report_evolution.json"),
                         encoding="utf-8"))
    series = evo["series"]
    d = evo["delta"]
    assert d["rows"] == series[-1]["rows"] - series[-2]["rows"]
    assert d["clubs"] == series[-1]["clubs"] - series[-2]["clubs"]


def test_every_contradiction_in_the_register_names_where_it_is_still_published():
    evo = json.load(open(os.path.join(ROOT, "data", "ledger", "injury_report_evolution.json"),
                         encoding="utf-8"))
    for c in evo["contradiction_register"]:
        assert c["claim"] and c["status"] and c["evidence_for_false"]
        assert c["who_still_publishes_it"], c["claim"]
        assert c["action_for_the_owning_session"]


# ------------------------------------------------------------------- the script
def test_the_repair_script_regenerates_the_same_files():
    before = open(REPORT, encoding="utf-8").read()
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "nfl1_57c05555", "repair_verified_injuries.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert open(REPORT, encoding="utf-8").read() == before
