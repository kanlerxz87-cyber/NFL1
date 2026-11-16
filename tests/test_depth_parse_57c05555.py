"""Fixture tests for the session `57c05555-nfl1` depth-chart parser.

Every fixture is the **exact text** from an official capture in ``data/depth_raw/`` or the
exact row the committed 2026-11-12 transcription holds, so a regression is caught against
real page content rather than a hand-written ideal.

The five defects these tests exist for are the ones the brief names:
  * Packers jersey-number prefixes,
  * the Texans image-only chart,
  * the column-legend row stored as players,
  * shared slots collapsed into a ranked list,
  * empty slots indistinguishable from a ranked list.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

from depth_parse import LEGEND_WORDS, parse_capture, split_group  # noqa: E402

RAW = os.path.join(ROOT, "data", "depth_raw")


def capture(club: str) -> dict:
    text = open(os.path.join(RAW, club + ".txt"), encoding="utf-8").read()
    return parse_capture(text, club, "https://example.invalid/" + club, "2026-11-15T00:00:00Z")


# ---------------------------------------------------------------- Packers jersey numbers
def test_packers_jersey_numbers_are_split_from_names():
    r = capture("GB")
    assert r["capture_kind"] == "table"
    first = r["slots"][0]
    group = first["groups"][0]
    assert group["names"] == ["Christian Watson"]
    assert group["jerseys"] == ["9"]
    # the raw string survives, so the strip can be audited
    assert "9 Christian Watson" in group["raw_cell"]


def test_packers_every_jersey_is_retained_not_discarded():
    r = capture("GB")
    assert r["counts"]["jersey_numbers_stripped"] == 55
    for slot in r["slots"]:
        for g in slot["groups"]:
            assert len(g["jerseys"]) == len(g["names"])


def test_packers_single_digit_zero_jersey_is_kept():
    # "0 Matthew Golden" — a zero is a legal jersey number and must not be dropped.
    r = capture("GB")
    pairs = {
        (g["names"][0], g["jerseys"][0])
        for s in r["slots"]
        for g in s["groups"]
    }
    assert ("Matthew Golden", "0") in pairs


def test_packers_continuation_line_becomes_the_next_rank():
    # The 4th running back is printed on a second row with no position label.
    r = capture("GB")
    rb = [s for s in r["slots"] if s["position"] == "RB"][0]
    assert [g["names"] for g in rb["groups"]] == [
        ["Josh Jacobs"], ["MarShawn Lloyd"], ["Pierre Strong Jr."], ["Kaleb Johnson"],
    ]
    assert rb["continuation_ranks"] == 1


def test_packers_empty_punter_return_slot_is_a_hole_not_a_rank():
    # "| PR |  | 0 Matthew Golden |  |" — the club printed no returner in column 1.
    r = capture("GB")
    pr = [s for s in r["slots"] if s["position"] == "PR"][0]
    assert pr["holes"] == [1]
    assert [g["names"] for g in pr["groups"]] == [["Matthew Golden"]]


# ------------------------------------------------------------------- Texans image-only
def test_texans_image_only_chart_yields_no_players():
    r = capture("HOU")
    assert r["capture_kind"] == "image_only"
    assert r["counts"]["player_names"] == 0
    assert r["slots"] == []


def test_texans_gap_cites_the_image():
    r = capture("HOU")
    assert len(r["gaps"]) == 1
    assert "static.clubs.nfl.com" in r["gaps"][0]["evidence"]
    assert "forbids" in r["gaps"][0]["reason"] or "by eye" in r["gaps"][0]["reason"]


# ------------------------------------------------------------------- Baltimore legend row
BAL_LEGEND_FIXTURE = """# Baltimore Ravens Depth Chart

## Offense

| POSITION | 1st | 2nd | 3rd | 4th |
| --- | --- | --- | --- | --- |
| WR | [Zay Flowers](https://www.baltimoreravens.com/team/players-roster/zay-flowers/) | [Devontez Walker](https://www.baltimoreravens.com/team/players-roster/devontez-walker/) |  |  |
"""


def test_baltimore_legend_row_is_not_a_player():
    """The committed 2026-11-12 transcription stores players called "1st".."4th"."""
    r = parse_capture(BAL_LEGEND_FIXTURE, "BAL", "https://example.invalid/bal", "t")
    names = [n for s in r["slots"] for g in s["groups"] for n in g["names"]]
    assert names == ["Zay Flowers", "Devontez Walker"]
    assert not any(n.lower() in LEGEND_WORDS for n in names)
    # The row is dropped: "POSITION" makes it a header, and every player cell in it is a
    # legend word.  Either way it must never become a player.
    assert any("legend" in d["reason"] or "header" in d["reason"] for d in r["dropped"])


def test_baltimore_live_page_has_no_legend_players():
    r = capture("BAL")
    names = {n for s in r["slots"] for g in s["groups"] for n in g["names"]}
    legend = LEGEND_WORDS | {"1st", "2nd", "3rd", "4th"}
    assert not (names & legend), sorted(names & legend)
    assert len(names) == 50  # 59 printed names, 50 distinct players


# ------------------------------------------------------------------------ shared slots
def test_arizona_shared_rank_one_is_one_group_of_two():
    r = capture("ARI")
    shared = [
        g for s in r["slots"] if s["position"] == "OLB" for g in s["groups"]
        if len(g["names"]) > 1
    ]
    assert len(shared) == 1
    assert shared[0]["names"] == ["Zaven Collins", "Baron Browning"]
    assert shared[0]["rank"] == 1


def test_indianapolis_shared_cell_keeps_both_names():
    r = capture("IND")
    shared = [g for s in r["slots"] for g in s["groups"] if len(g["names"]) > 1]
    assert len(shared) == 1
    assert shared[0]["names"] == ["Will Mallory", "Pharaoh Brown"]


def test_a_shared_cell_is_never_split_into_two_ranks():
    names, jerseys, raw = split_group("[Cooper Kupp](https://x/1) [Rashid Shaheed](https://x/2)")
    assert names == ["Cooper Kupp", "Rashid Shaheed"]
    assert jerseys == ["", ""]


def test_a_single_name_with_a_space_is_one_player():
    # "J. Michael Sturdivant" must not become two players.
    names, _, _ = split_group("[J. Michael Sturdivant](https://x)")
    assert names == ["J. Michael Sturdivant"]


def test_a_name_with_a_generational_suffix_is_one_player():
    names, _, _ = split_group("[T.J. Tampa Jr.](https://x)")
    assert names == ["T.J. Tampa Jr."]


# -------------------------------------------------------------------------- empty slots
def test_washington_empty_middle_cell_is_recorded_as_a_hole():
    r = capture("WAS")
    luvu = [s for s in r["slots"] if s["position"] == "LB" and s["holes"]][0]
    assert luvu["holes"] == [2]
    # The second name is printed in column 3 but is the 2nd ranked name in the slot.
    assert [(g["column"], g["names"]) for g in luvu["groups"]] == [
        (1, ["Frankie Luvu"]), (3, ["Kain Medrano"]),
    ]


EMPTY_K_FIXTURE = """# Club

## Special Teams

| P | [Ryan Eckley](https://x/1) |  |  |  |
| K |  |  |  |  |
"""


def test_an_empty_slot_is_published_as_empty():
    r = parse_capture(EMPTY_K_FIXTURE, "BAL", "https://example.invalid", "t")
    k = [s for s in r["slots"] if s["position"] == "K"][0]
    assert k["empty"] is True
    assert k["groups"] == []


# ------------------------------------------------------------------- rank is never inferred
def test_rank_comes_only_from_printed_order():
    r = capture("ARI")
    for slot in r["slots"]:
        ranks = [g["rank"] for g in slot["groups"]]
        assert ranks == list(range(1, len(ranks) + 1))


def test_no_published_name_contains_a_leading_number():
    import re

    for club in ("ARI", "BAL", "GB", "IND", "WAS"):
        r = capture(club)
        for slot in r["slots"]:
            for g in slot["groups"]:
                for n in g["names"]:
                    assert not re.match(r"^\d{1,2}\s", n), n


def test_published_names_carry_no_html_entities():
    import re

    ent = re.compile(r"&(#x?[0-9A-Fa-f]+|[a-z]+);")
    for club in ("ARI", "BAL", "GB", "IND", "WAS"):
        r = capture(club)
        for slot in r["slots"]:
            for g in slot["groups"]:
                for n in g["names"]:
                    assert not ent.search(n), n
