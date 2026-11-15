"""Tests for tools/prereg.py (session 739408a8-nfl1, task P1).

Offline: reads only data/prereg/*. The arithmetic test checks that every transcribed standings
PCT equals (W + 0.5 T) / G to three decimals, and that every scheduled team is in the standings.
"""
import datetime as dt
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import prereg  # noqa: E402


class PreregTests(unittest.TestCase):
    def setUp(self):
        self.inputs = json.loads(prereg.INPUTS.read_text())

    def test_standings_pct_matches_record_arithmetic(self):
        for r in self.inputs["standings"]["rows"]:
            g = r["W"] + r["L"] + r["T"]
            self.assertEqual(round((r["W"] + 0.5 * r["T"]) / g, 3), r["PCT"], r["team"])

    def test_thirty_two_clubs_and_thirteen_games(self):
        self.assertEqual(len(self.inputs["standings"]["rows"]), 32)
        self.assertEqual(len(self.inputs["schedule"]["games"]), 13)
        teams = {r["team"] for r in self.inputs["standings"]["rows"]}
        for g in self.inputs["schedule"]["games"]:
            self.assertIn(g["home"], teams)
            self.assertIn(g["away"], teams)

    def test_pr02_is_record_share(self):
        led = json.loads(prereg.LEDGER.read_text())
        g = next(x for x in led["games"] if x["game_id"] == "W11-01")  # IND @ HOU
        self.assertAlmostEqual(g["p_home"]["PR-02"], 0.375 / (0.375 + 0.222), places=6)

    def test_random_control_is_deterministic_and_in_unit_interval(self):
        a, b = prereg.unit_draw("W11-05"), prereg.unit_draw("W11-05")
        self.assertEqual(a, b)
        self.assertTrue(0.0 <= a < 1.0)

    def test_kickoff_conversion_is_standard_time(self):
        self.assertEqual(prereg.parse_iso_et("2026-11-19T20:15"),
                         dt.datetime(2026, 11, 20, 1, 15, tzinfo=dt.timezone.utc))

    def test_late_forecast_is_refused(self):
        late = dt.datetime(2026, 11, 25, tzinfo=dt.timezone.utc)
        with self.assertRaises(SystemExit):
            prereg.build_forecasts(self.inputs, late)

    def test_frozen_rule_hash_detects_edits(self):
        rule = dict(prereg.FROZEN_RULES[1])
        h = prereg.canonical_hash(rule)
        rule["forecast"] = rule["forecast"] + " (edited)"
        self.assertNotEqual(h, prereg.canonical_hash(rule))

    def test_check_passes_on_committed_registration(self):
        self.assertEqual(prereg.cmd_check(None), 0)

    def test_every_not_registrable_row_has_reason_and_source(self):
        reg = json.loads(prereg.REGISTRY.read_text())
        for r in reg["not_registrable"]:
            self.assertTrue(r["reason"])
            self.assertTrue(r["src"])
            self.assertTrue(all(u.startswith("https://") for u in r["src"]))

    def test_no_backtest_admission(self):
        reg = json.loads(prereg.REGISTRY.read_text())
        self.assertEqual(reg["leaderboard_rules"][0]["id"], "LB-ADMIT")
        self.assertIn("Backtest", reg["leaderboard_rules"][0]["rule"])


if __name__ == "__main__":
    unittest.main()
