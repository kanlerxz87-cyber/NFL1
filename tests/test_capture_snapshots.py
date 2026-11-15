"""Tests for pipeline/capture_snapshots.py (session 90c2b454-nfl1, task P2).

The HTML below is SYNTHETIC. It imitates the structure of the nfl.com injury page (a game block
with two club headings, each followed by a report table) so the parser's logic can be tested
offline. It is never used as evidence of an official value; the live capture workflow is.
"""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import capture_snapshots as cs  # noqa: E402


def _table(rows):
    head = ("<tr><th>Player</th><th>Position</th><th>Injuries</th>"
            "<th>Practice Status</th><th>Game Status</th></tr>")
    body = "".join(
        f'<tr><td><a href="/players/{p.lower().replace(" ", "-")}/">{p}</a></td><td>{pos}</td>'
        f"<td>{inj}</td><td>{prac}</td><td>{game}</td></tr>"
        for p, pos, inj, prac, game in rows)
    return f"<table>{head}{body}</table>"


def _page(week=10, season=2026, extra_game=None):
    game = (
        '<div><span>WAS</span> <a href="/teams/x/">Commanders</a> | '
        '<span>NYG</span> <a href="/teams/y/">Giants</a></div>'
        '<p>Commanders</p>'
        + _table([("Lucas Patrick", "C", "Concussion", "Did Not Participate In Practice", "Out"),
                  ("Jayden Daniels", "QB", "", "Full Participation in Practice", "")])
        + "<p>Giants</p>"
        + _table([("Malik Harrison", "LB", "Groin", "Limited Participation in Practice", "Questionable"),
                  ("Theo Johnson", "TE", "", "Full Participation in Practice", "")])
    )
    if extra_game:
        game += extra_game
    return ("<html><head><title>Official Latest NFL Injury Report for Players - "
            f"Week {week} of the {season} Season | NFL.com</title></head><body>"
            f"<h1>2026 NFL Injury Report</h1>{game}</body></html>").encode("utf-8")


NICK = cs.load_nicknames()


class TestNicknameMap(unittest.TestCase):
    def test_exactly_32_current_clubs(self):
        self.assertEqual(len(set(NICK.values())), 32)

    def test_historical_franchises_excluded(self):
        self.assertNotIn("OAK", NICK.values())
        self.assertNotIn("SD", NICK.values())
        self.assertNotIn("STL", NICK.values())
        self.assertNotIn("LAR", NICK.values())

    def test_shared_nicknames_resolve_to_current_club(self):
        self.assertEqual(NICK["rams"], "LA")
        self.assertEqual(NICK["chargers"], "LAC")
        self.assertEqual(NICK["raiders"], "LV")


class TestParse(unittest.TestCase):
    def _parse_with_tables(self, html):
        # The pinned minimum table count is for the real page; a synthetic page has 2 tables.
        with mock.patch.object(cs, "MIN_TABLES", 2), mock.patch.object(cs, "MIN_ROWS", 4):
            return cs.parse(html, NICK)

    def test_club_is_read_from_the_heading_before_each_table(self):
        out = self._parse_with_tables(_page())
        clubs = {(r["club"], r["player"]) for r in out["rows"]}
        self.assertIn(("WAS", "Lucas Patrick"), clubs)
        self.assertIn(("WAS", "Jayden Daniels"), clubs)
        self.assertIn(("NYG", "Malik Harrison"), clubs)
        self.assertIn(("NYG", "Theo Johnson"), clubs)

    def test_week_and_season_come_from_the_title(self):
        out = self._parse_with_tables(_page(week=11, season=2026))
        self.assertEqual((out["week"], out["season"]), (11, 2026))

    def test_blank_cells_stay_none_not_inferred(self):
        out = self._parse_with_tables(_page())
        daniels = next(r for r in out["rows"] if r["player"] == "Jayden Daniels")
        self.assertIsNone(daniels["injury"])
        self.assertIsNone(daniels["game_status"])
        self.assertEqual(daniels["practice_status"], "Full Participation in Practice")

    def test_designations_are_copied_verbatim(self):
        out = self._parse_with_tables(_page())
        patrick = next(r for r in out["rows"] if r["player"] == "Lucas Patrick")
        self.assertEqual((patrick["injury"], patrick["practice_status"], patrick["game_status"]),
                         ("Concussion", "Did Not Participate In Practice", "Out"))

    def test_missing_practice_column_fails_loudly(self):
        bad = _page().replace(b"Practice Status", b"Practice Notes")
        with self.assertRaises(cs.CaptureError):
            self._parse_with_tables(bad)

    def test_no_week_marker_fails_loudly(self):
        bad = _page().replace(b"Week 10 of the 2026 Season", b"Season report")
        with self.assertRaises(cs.CaptureError):
            self._parse_with_tables(bad.replace(b"Week 10", b"Wk"))

    def test_unknown_designation_wording_is_flagged_not_dropped(self):
        html = _page().replace(b"Questionable", b"Probable")
        out = self._parse_with_tables(html)
        self.assertTrue(any("game-status wording" in f for f in out["flags"]))
        self.assertEqual(len(out["rows"]), 4)

    def test_pinned_minimum_rows_is_enforced(self):
        with mock.patch.object(cs, "MIN_TABLES", 2):
            with self.assertRaises(cs.CaptureError):
                cs.parse(_page(), NICK)  # 4 rows is below the real pin of 100


class TestDeltaAndStorage(unittest.TestCase):
    def test_diff_reports_designation_evolution(self):
        old = [{"club": "NYG", "player": "Malik Harrison", "position": "LB", "injury": "Groin",
                "practice_status": "Limited Participation in Practice", "game_status": "Questionable"}]
        new = [{"club": "NYG", "player": "Malik Harrison", "position": "LB", "injury": "Groin",
                "practice_status": "Did Not Participate In Practice", "game_status": "Out"}]
        delta = cs.diff_rows(old, new)
        fields = {d["field"]: (d["from"], d["to"]) for d in delta if d["change"] == "changed"}
        self.assertEqual(fields["practice_status"],
                         ("Limited Participation in Practice", "Did Not Participate In Practice"))
        self.assertEqual(fields["game_status"], ("Questionable", "Out"))

    def test_diff_reports_added_and_removed_players(self):
        a = [{"club": "NYG", "player": "A", "position": "LB", "injury": None,
              "practice_status": None, "game_status": None}]
        b = [{"club": "NYG", "player": "B", "position": "LB", "injury": None,
              "practice_status": None, "game_status": None}]
        kinds = sorted(d["change"] for d in cs.diff_rows(a, b))
        self.assertEqual(kinds, ["added", "removed"])

    def test_capture_is_written_once_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            store = tmp / "injury_report"
            patches = {
                "STORE": store, "CAPTURES": store / "captures", "HEARTBEAT": store / "heartbeat.jsonl",
                "CHANGES": store / "changes.jsonl", "ALERTS": store / "alerts.jsonl",
                "MANIFEST": store / "manifest.json", "ROOT": tmp,
            }
            with mock.patch.multiple(cs, **patches), \
                    mock.patch.object(cs, "MIN_TABLES", 2), mock.patch.object(cs, "MIN_ROWS", 4), \
                    mock.patch.object(cs, "fetch", return_value=(200, _page(), "https://www.nfl.com/injuries/")):
                self.assertEqual(cs.capture(), 0)
                # Same page again: a heartbeat is written, no new capture file.
                self.assertEqual(cs.capture(), 0)
                beats = [json.loads(x) for x in (store / "heartbeat.jsonl").read_text().splitlines()]
                self.assertEqual(len(beats), 2)
                self.assertTrue(beats[0]["changed"])
                self.assertFalse(beats[1]["changed"])
                files = sorted((store / "captures").glob("*.json"))
                self.assertEqual(len(files), 1)
                # Changed page: a second capture file and a delta line.
                changed = _page().replace(b"Questionable", b"Out")
                with mock.patch.object(cs, "fetch", return_value=(200, changed, "u")):
                    self.assertEqual(cs.capture(), 0)
                files = sorted((store / "captures").glob("*.json"))
                self.assertEqual(len(files), 2)
                delta = [json.loads(x) for x in (store / "changes.jsonl").read_text().splitlines()]
                self.assertEqual(len(delta), 1)
                self.assertEqual(delta[0]["changes"], 1)
                manifest = json.loads((store / "manifest.json").read_text())
                self.assertEqual(len(manifest["captures"]), 2)
                self.assertEqual(cs.verify(max_age_hours=10 ** 6), 0)

    def test_failed_fetch_records_a_heartbeat_and_an_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            store = tmp / "injury_report"
            patches = {"STORE": store, "CAPTURES": store / "captures",
                       "HEARTBEAT": store / "heartbeat.jsonl", "CHANGES": store / "changes.jsonl",
                       "ALERTS": store / "alerts.jsonl", "MANIFEST": store / "manifest.json",
                       "ROOT": tmp}
            with mock.patch.multiple(cs, **patches), \
                    mock.patch.object(cs, "fetch", side_effect=cs.CaptureError("fetch returned HTTP 503")):
                self.assertEqual(cs.capture(), 1)
            beat = json.loads((store / "heartbeat.jsonl").read_text().splitlines()[0])
            self.assertEqual(beat["status"], "failed")
            alert = json.loads((store / "alerts.jsonl").read_text().splitlines()[0])
            self.assertEqual(alert["kind"], "fetch-or-parse-failed")


if __name__ == "__main__":
    unittest.main()
