#!/usr/bin/env python3
"""tests/test_gamebooks.py — unit tests for the Game Book parser and matcher.

Run: python3 -m pytest tests/test_gamebooks.py -q   (or python3 tests/test_gamebooks.py)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_gamebooks as bg  # noqa: E402


class TestPlayerRows(unittest.TestCase):
    def test_eight_cell(self):
        row = "| WR | 14 A.Williams | OLB | 98 O.Oweh | WR | 17 D.Mooney | OLB | 5 K.Thibodeaux |  |"
        players = bg.parse_player_cells(bg.cells(row))
        self.assertIsNotNone(players)
        self.assertEqual(len(players), 4)
        self.assertEqual(players[0], {"pos": "WR", "num": "14", "name": "A.Williams"})
        self.assertEqual(players[3]["name"], "K.Thibodeaux")

    def test_four_cell_inline(self):
        row = "| TE 88 D.Waller | OLB 91 P.Jones | TE 83 J.Johnson | DE 99 C.Young |"
        players = bg.parse_player_cells(bg.cells(row))
        self.assertIsNotNone(players)
        self.assertEqual(players[2]["name"], "J.Johnson")

    def test_twelve_cell_triples(self):
        row = "| QB | 13 | B.Purdy | S | 27 | J.Brown | QB | 4 | D.Prescott | S | 14 | E.Parham |"
        players = bg.parse_player_cells(bg.cells(row))
        self.assertIsNotNone(players)
        self.assertEqual(players[0]["name"], "B.Purdy")
        self.assertEqual(players[3]["num"], "14")

    def test_eleven_cell_missing_name_stays_blank(self):
        # San Francisco extraction: the fourth player's name is absent from the PDF text.
        row = "| WR | 19 | D.Samuel | DL | 97 | N.Bosa | WR | 88 | C.Lamb | OLB | 40 |"
        players = bg.parse_player_cells(bg.cells(row))
        self.assertIsNotNone(players)
        self.assertEqual(len(players), 4)
        self.assertEqual(players[3], {"pos": "OLB", "num": "40", "name": ""})

    def test_header_rows_rejected(self):
        for row in ("| Offense | Defense | Offense | Defense |",
                    "| Offense |  | Defense |  | Offense |  | Defense |  |  |",
                    "| VISITOR: | Washington Commanders |  | 1 | 2 | 3 | 4 | OT | Total |",
                    "| HOME: | New York Giants |  | 0 | 10 | 7 | 7 | 0 | 24 |"):
            self.assertIsNone(bg.parse_player_cells(bg.cells(row)), row)


class TestNameKeys(unittest.TestCase):
    def test_book_key(self):
        self.assertEqual(bg.book_name_key("D.Allar"), ("d", "allar"))
        self.assertEqual(bg.book_name_key("S.Murphy-Bunting"), ("s", "murphy-bunting"))
        self.assertIsNone(bg.book_name_key("NoDot"))

    def test_injury_key_strips_suffix(self):
        self.assertEqual(bg.injury_name_key("Ronnie Hickman Jr."), ("r", "hickman"))
        self.assertEqual(bg.injury_name_key("Carlton Davis III"), ("c", "davis"))
        self.assertEqual(bg.injury_name_key("Jon Gaines II"), ("j", "gaines"))
        self.assertEqual(bg.injury_name_key("A.J. Terrell"), ("a", "terrell"))


class TestMatch(unittest.TestCase):
    def _match(self, na_entries, inj_rows):
        parsed = [{
            "game": "x-at-y-2026-reg-10",
            "away": {"abbr": "AAA"}, "home": {"abbr": "BBB"},
            "not_active": {"away": na_entries, "home": []},
        }]
        injury = {"rows": inj_rows, "captured_at_utc": "t", "source_url": "u",
                  "canonical_sha256": "h"}
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(injury, f)
            path = f.name
        try:
            return bg.match_injury_read(parsed, path)
        finally:
            os.unlink(path)

    def test_matched_with_suffix(self):
        m = self._match(
            ["OL 71 J.Gaines"],
            [{"club": "AAA", "player": "Jon Gaines II", "position": "OL",
              "injury": "Ankle", "game_status": "Out", "player_url": "http://p"}],
        )
        self.assertEqual(m["totals"]["matched"], 1)
        self.assertEqual(m["matches"][0]["game_status"], "Out")

    def test_initial_mismatch_is_not_a_match(self):
        # book says N.Reed; the read only has D.J. Reed / Jarran Reed — different players.
        m = self._match(
            ["CB 35 N.Reed"],
            [{"club": "AAA", "player": "D.J. Reed", "position": "CB",
              "injury": "Knee", "game_status": "Out", "player_url": "http://p1"},
             {"club": "AAA", "player": "Jarran Reed", "position": "DT",
              "injury": "Toe", "game_status": "Out", "player_url": "http://p2"}],
        )
        self.assertEqual(m["totals"]["matched"], 0)
        self.assertEqual(m["totals"]["not_in_report"], 1)

    def test_same_initial_multi_candidate_is_ambiguous(self):
        m = self._match(
            ["OL 74 J.Davis"],
            [{"club": "AAA", "player": "Jalen Davis", "position": "CB",
              "injury": "Knee", "game_status": "Out", "player_url": "http://p1"},
             {"club": "AAA", "player": "Jordan Davis", "position": "DT",
              "injury": "Toe", "game_status": "Out", "player_url": "http://p2"}],
        )
        self.assertEqual(m["totals"]["ambiguous"], 1)
        self.assertEqual(m["totals"]["matched"], 0)

    def test_cross_club_candidate_not_matched(self):
        m = self._match(
            ["CB 21 P.Adebo"],
            [{"club": "ZZZ", "player": "Paul Adebo", "position": "CB",
              "injury": "Knee", "game_status": "Out", "player_url": "http://p"}],
        )
        self.assertEqual(m["totals"]["matched"], 0)
        self.assertEqual(m["totals"]["not_in_report"], 1)


class TestCaptureIntegrity(unittest.TestCase):
    """The committed capture must match the committed hashes — no silent edits."""

    def test_manifest_hashes(self):
        base = os.path.join(ROOT, "data", "gamebooks")
        manifest = json.load(open(os.path.join(base, "manifest.json")))
        source = json.load(open(os.path.join(base, "source.json")))
        self.assertEqual(len(manifest["files"]), 13)
        self.assertEqual(len(source["games"]), 13)
        by_path = {f["path"]: f["sha256"] for f in manifest["files"]}
        for g in source["games"]:
            rel = g["raw_file"]
            with open(os.path.join(ROOT, rel), "rb") as f:
                actual = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(by_path[rel], actual, rel)
            self.assertEqual(g["raw_sha256"], actual, rel)
            self.assertIn("extraction_note", open(os.path.join(ROOT, rel), encoding="utf-8").read())

    def test_parsed_flags_cover_label_loss(self):
        parsed = json.load(open(os.path.join(ROOT, "data", "gamebooks", "parsed.json")))
        by_game = {g["game"]: g for g in parsed["games"]}
        car = by_game["panthers-at-saints-2026-reg-10"]
        self.assertIsNone(car["not_active"]["away"])
        self.assertTrue(any(f["code"] == "STATUS_LABELS_ABSENT" for f in car["flags"]))
        kc = by_game["chiefs-at-falcons-2026-reg-10"]
        self.assertTrue(any(f["code"] == "STATUS_UNATTRIBUTED" for f in kc["flags"]))
        self.assertEqual(len(kc["status_unattributed"]), 7)
        sf = by_game["49ers-at-cowboys-2026-reg-10"]
        blanks = [f for f in sf["flags"] if f["code"] == "LINEUP_NAME_BLANK"]
        self.assertEqual(len(blanks), 11)


if __name__ == "__main__":
    unittest.main(verbosity=2)
