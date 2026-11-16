"""Tests for the IN-31 schedule announcement gate (tools/check_schedule_announcement.py)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import check_schedule_announcement as chk  # noqa: E402


class ScheduleAnnouncementTests(unittest.TestCase):
    def test_gate_passes_on_committed_data(self):
        d, problems = chk.run()
        self.assertEqual(problems, [], problems)

    def test_thirteen_games_and_six_byes(self):
        d, _ = chk.run()
        self.assertEqual(len(d["live_schedule"]["fixtures"]), 13)
        self.assertEqual(len(d["live_schedule"]["teams_on_bye"]), 6)

    def test_official_host_only(self):
        self.assertTrue(chk.is_official("https://www.nfl.com/games/x"))
        self.assertTrue(chk.is_official("https://media.nfl.com/news-and-releases/x"))
        self.assertFalse(chk.is_official("http://www.nfl.com/games/x"))
        self.assertFalse(chk.is_official("https://example.com/nfl.com"))

    def test_release_arithmetic(self):
        d = {"announcement": {"rows": [{"id": "A1", "derived_utc": "2026-05-15T00:00:00Z"}]}}
        problems = []
        chk.check_calendar({"live_schedule": {"fixtures": []}, **d}, problems)
        self.assertEqual(problems, [])

    def test_weekday_mismatch_is_caught(self):
        d = {"live_schedule": {"fixtures": [
            {"matchup": "X at Y", "day": "Friday, November 19th", "kickoff_et": "8:15 PM", "network": "PRIME",
             "official_url": "https://www.nfl.com/games/x"}]},
            "announcement": {"rows": [{"id": "A1", "derived_utc": "2026-05-15T00:00:00Z"}]}}
        problems = []
        chk.check_calendar(d, problems)
        self.assertTrue(any("is a Thursday" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
