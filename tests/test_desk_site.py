#!/usr/bin/env python3
"""Tests for the Decision Desk sub-site (session ed736fc3-nfl1).

These pin the rules the brief asks for rather than the current numbers:

  * a table cell that is None is refused, and a Source column must carry a link;
  * a null price renders as a labelled blank, never as 0 or an invented number;
  * the transcription counts, the standings arithmetic and the Week-11 club coverage
    recompute from the raw transcription files;
  * the rendered pages are exactly what the data produces, and every local link resolves;
  * a claim the official page has retired is published as resolved, not as a live finding.

Run: python3 -m unittest tests.test_desk_site -v
"""
from __future__ import annotations

import csv
import html
import json
import os
import re
import sys
import unittest
from html.parser import HTMLParser

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DESK = os.path.join(ROOT, "data", "desk")
SITE = os.path.join(ROOT, "desk")
sys.path.insert(0, os.path.join(ROOT, "tools", "desk"))

import build_site  # noqa: E402


def J(name):
    with open(os.path.join(DESK, name), encoding="utf-8") as f:
        return json.load(f)


def psv(name):
    with open(os.path.join(DESK, name), encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="|"))


def tsv(name):
    with open(os.path.join(DESK, name), encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


class TestTranscriptions(unittest.TestCase):
    """The transcription files must be internally consistent before anything is published."""

    def test_standings_arithmetic_reproduces_in_all_32_rows(self):
        rows = psv("standings_2026-11-16.psv")
        self.assertEqual(len(rows), 32)
        for r in rows:
            self.assertEqual(int(r["pf"]) - int(r["pa"]), int(r["net"]), f'{r["code"]} net')
            pct = round((int(r["w"]) + 0.5 * int(r["t"])) / (int(r["w"]) + int(r["l"]) + int(r["t"])), 3)
            self.assertAlmostEqual(pct, float(r["pct"]), places=4, msg=f'{r["code"]} pct')

    def test_standings_games_are_even(self):
        rows = psv("standings_2026-11-16.psv")
        club_games = sum(int(r["w"]) + int(r["l"]) + int(r["t"]) for r in rows)
        self.assertEqual(club_games % 2, 0, "a club playing a game nobody played means a transcription slip")

    def test_injury_rows_match_the_published_counts(self):
        rows = tsv("injuries_w10_2026-11-16.tsv")
        c = J("injuries.json")["counts"]
        self.assertEqual(len(rows), c["rows"])
        self.assertEqual(len({r["club"] for r in rows}), c["clubs"])
        self.assertEqual(sum(1 for r in rows if r["game_status"] == "Out"), c["out"])
        self.assertEqual(sum(1 for r in rows if r["game_status"].strip()), c["with_game_status"])

    def test_every_injury_row_carries_an_official_player_url(self):
        for r in tsv("injuries_w10_2026-11-16.tsv"):
            self.assertTrue(r["player_url"].startswith("https://www.nfl.com/players/"), r["player_url"])

    def test_week11_covers_each_club_exactly_once(self):
        fx = psv("week11_fixtures_2026-11-16.psv")
        byes = {b["club"] for b in psv("week11_byes_2026-11-16.psv")}
        alias = {"LAR": "LA", "ARI": "AZ"}
        byes = {alias.get(c, c) for c in byes}
        playing = {f["away"] for f in fx} | {f["home"] for f in fx}
        self.assertEqual(playing & byes, set(), "a club cannot play and be on bye")
        self.assertEqual(len(playing | byes), 32)

    def test_a_final_score_is_never_blank_on_one_side(self):
        for r in psv("week10_results_2026-11-16.psv"):
            if r["status"] == "Final":
                self.assertTrue(r["away_score"] and r["home_score"], f'{r["away"]}@{r["home"]}')
            else:
                self.assertFalse(r["away_score"] or r["home_score"],
                                 "a scheduled game must not carry a score")

    def test_depth_cells_keep_the_printed_text(self):
        data = json.load(open(os.path.join(DESK, "depth_2026-11-16.json"), encoding="utf-8"))
        for club, chart in data.items():
            if club == "_readme":
                continue
            for u in chart["units"]:
                for s in u["slots"]:
                    for p in s["players"]:
                        self.assertTrue(p["raw"], f"{club} {s['position']} has a name with no raw cell")

    def test_depth_keeps_the_jersey_prefix_on_the_packers_chart(self):
        data = json.load(open(os.path.join(DESK, "depth_2026-11-16.json"), encoding="utf-8"))
        watson = [p for u in data["GB"]["units"] for s in u["slots"] for p in s["players"]
                  if p["name"] == "Christian Watson"][0]
        self.assertEqual(watson["raw"], "9 Christian Watson")
        self.assertNotIn("9", watson["name"])


class TestRendering(unittest.TestCase):
    """The renderer's own rules."""

    def test_a_none_cell_is_refused(self):
        with self.assertRaises(ValueError):
            build_site.table(["A", "B"], [["x", None]])

    def test_a_source_column_must_carry_a_link(self):
        with self.assertRaises(ValueError):
            build_site.table(["A", "Source"], [["x", "nfl.com"]])

    def test_a_null_price_is_a_labelled_blank_not_a_zero(self):
        self.assertEqual(build_site.num(None), "not published")
        self.assertNotEqual(build_site.num(None), "0")
        self.assertEqual(build_site.num(5.7), "+5.70")

    def test_every_declared_page_renders(self):
        for name, fn in build_site.PAGES.items():
            text = fn()
            self.assertIn("<!doctype html>", text, name)
            self.assertIn("<title>", text, name)

    def test_no_table_cell_renders_a_python_none(self):
        """'None' is a legitimate English word in our prose; it is never a legitimate table cell."""
        for name, fn in build_site.PAGES.items():
            text = fn()
            self.assertNotIn(">None<", text, name)
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", text, flags=re.S):
                self.assertNotEqual(cell.strip(), "None", f"{name} renders None in a cell")


class TestPublishedSite(unittest.TestCase):
    """What is committed must be what the data produces, and it must be navigable."""

    def test_committed_pages_are_current(self):
        build_site.GEN_AT = J("injuries.json")["retrieved"]
        for name, fn in build_site.PAGES.items():
            path = os.path.join(SITE, name)
            self.assertTrue(os.path.exists(path), f"desk/{name} missing")
            self.assertEqual(open(path, encoding="utf-8").read(), fn(), f"desk/{name} is stale")

    def test_local_links_resolve(self):
        class P(HTMLParser):
            def __init__(self):
                super().__init__()
                self.hrefs = []

            def handle_starttag(self, tag, attrs):
                d = dict(attrs)
                if tag == "a" and "href" in d:
                    self.hrefs.append(d["href"])

        for name in build_site.PAGES:
            parser = P()
            parser.feed(open(os.path.join(SITE, name), encoding="utf-8").read())
            for href in parser.hrefs:
                href = html.unescape(href.split("#")[0])
                if not href or href.startswith(("http://", "https://", "mailto:")):
                    continue
                target = os.path.normpath(os.path.join(SITE, href))
                if os.path.isdir(target):
                    target = os.path.join(target, "index.html")
                self.assertTrue(os.path.isfile(target), f"broken link in desk/{name}: {href}")


class TestClaims(unittest.TestCase):
    """A finding the live page has retired must be published as retired."""

    def test_the_lions_three_are_out_on_the_page(self):
        rows = {r["player"]: r["game_status"] for r in J("injuries.json")["rows"] if r["club"] == "DET"}
        for player in ("Kerby Joseph", "Cade Mays", "D.J. Reed"):
            self.assertEqual(rows[player], "Out", f"{player} should be Out on the page as read")

    def test_the_baltimore_claim_is_marked_resolved(self):
        claims = {r["id"]: r for r in J("claims.json")["rows"]}
        self.assertEqual(claims["D-C06"]["verdict"], "resolved at source")

    def test_no_claim_is_marked_confirmed_without_evidence_text(self):
        for r in J("claims.json")["rows"]:
            self.assertTrue(r["evidence"].strip(), r["id"])

    def test_readiness_rows_have_a_gate_and_a_number(self):
        for r in J("readiness.json")["rows"]:
            self.assertTrue(r["blocking_gate"].strip(), r["id"])
            self.assertTrue(r["number_now"].strip(), r["id"])
            self.assertTrue(r["clears_when"].strip(), r["id"])
            self.assertTrue(r["src"].startswith("https://"), r["id"])

    def test_questions_and_suggestions_carry_a_discovery_or_a_path(self):
        for r in J("questions.json")["rows"]:
            self.assertTrue(r["discovery"].strip(), r["id"])
            self.assertTrue(r["missing"].strip(), r["id"])
        for r in J("suggestions.json")["rows"]:
            self.assertTrue(r["recommended_path"].strip(), r["id"])
            self.assertTrue(r["alternative"].strip(), r["id"])


if __name__ == "__main__":
    unittest.main()
