#!/usr/bin/env python3
"""Unit tests for the strength-of-schedule study.

The first test exists because a sign-convention bug once produced four PASSes
with hit rates above 90%. A rule set that cannot be tested for that defect is
worse than no rule set.

Run: python3 -m unittest tests.test_strength -v
"""
from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))

try:
    import numpy as np
    import pandas as pd
    HAVE_DEPS = True
except ImportError:                                    # pragma: no cover
    HAVE_DEPS = False

DATA = os.path.join(ROOT, "data", "strength")


@unittest.skipUnless(HAVE_DEPS, "numpy/pandas not installed")
class TestSpreadResolution(unittest.TestCase):
    """nflverse spread_line is the home club's expected margin."""

    def setUp(self):
        import strength
        self.mod = strength

    def test_home_cover(self):
        row = {"spread_line": -3.0, "margin": 7.0, "home_spread_odds": -110, "away_spread_odds": -110}
        dec, won, push = self.mod._resolve(row, "home", "spread")
        self.assertTrue(won, "home -3 winning by 7 must cover")
        self.assertFalse(push)
        self.assertGreater(dec, 1.0)

    def test_home_favourite_fails_when_it_loses(self):
        # home favoured by 3 (spread_line +3) loses by 1: this discriminates the
        # correct convention from the buggy one, which would call it a cover.
        row = {"spread_line": 3.0, "margin": -1.0, "home_spread_odds": -110, "away_spread_odds": -110}
        _, won, _ = self.mod._resolve(row, "home", "spread")
        self.assertFalse(won)
        _, away_won, _ = self.mod._resolve(row, "away", "spread")
        self.assertTrue(away_won)

    def test_home_underdog_cover(self):
        # home club is a 7-point underdog (spread_line -7) and loses by 3: it covers.
        row = {"spread_line": -7.0, "margin": -3.0, "home_spread_odds": -110, "away_spread_odds": -110}
        _, won, _ = self.mod._resolve(row, "home", "spread")
        self.assertTrue(won)

    def test_push(self):
        row = {"spread_line": 3.0, "margin": 3.0, "home_spread_odds": -110, "away_spread_odds": -110}
        _, won, push = self.mod._resolve(row, "home", "spread")
        self.assertTrue(push)
        self.assertIsNone(won)

    def test_missing_price_is_not_scored(self):
        row = {"spread_line": -3.0, "margin": 7.0, "home_spread_odds": None, "away_spread_odds": None}
        self.assertIsNone(self.mod._resolve(row, "home", "spread"))

    def test_totals(self):
        row = {"total_line": 45.0, "total": 52.0, "over_odds": -110, "under_odds": -110}
        _, over_won, _ = self.mod._resolve(row, "over", "total")
        _, under_won, _ = self.mod._resolve(row, "under", "total")
        self.assertTrue(over_won)
        self.assertFalse(under_won)


@unittest.skipUnless(HAVE_DEPS, "numpy/pandas not installed")
class TestStatistics(unittest.TestCase):
    def setUp(self):
        import strength
        self.mod = strength

    def test_pearson_perfect(self):
        r = self.mod.pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        self.assertAlmostEqual(r["r"], 1.0, places=4)
        self.assertEqual(r["n"], 5)

    def test_pearson_needs_variance(self):
        self.assertIsNone(self.mod.pearson([1, 1, 1, 1], [1, 2, 3, 4]))

    def test_benjamini_hochberg_monotone(self):
        q = self.mod.benjamini_hochberg([0.01, 0.04, 0.03, 0.20])
        self.assertEqual(len(q), 4)
        self.assertGreaterEqual(q[1], q[0])
        self.assertTrue(all(0 <= x <= 1 for x in q))

    def test_decimal_conversion_roundtrip(self):
        for ml in (-110, 100, -450, 350):
            dec = self.mod.american_to_decimal(ml)
            self.assertGreater(dec, 1.0)
            self.assertAlmostEqual(self.mod.decimal_to_american(dec), ml, delta=1)

    def test_blank_moneyline_stays_blank(self):
        self.assertIsNone(self.mod.american_to_decimal(None))
        self.assertIsNone(self.mod.american_to_decimal(float("nan")))


class TestPublishedData(unittest.TestCase):
    """The published JSON must stay internally consistent."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(DATA):
            raise unittest.SkipTest("data/strength not built")
        cls.meta = json.load(open(os.path.join(DATA, "meta.json")))
        cls.strat = json.load(open(os.path.join(DATA, "strategies.json")))
        cls.state = json.load(open(os.path.join(DATA, "current_state.json")))
        cls.official = json.load(open(os.path.join(DATA, "official_week10.json")))
        cls.flags = json.load(open(os.path.join(DATA, "flags.json")))

    def test_official_standings_reconcile(self):
        rows = self.official["standings"]["rows"]
        self.assertEqual(len(rows), 32)
        self.assertEqual(sum(r["w"] for r in rows), sum(r["l"] for r in rows))
        self.assertEqual(sum(r["pf"] for r in rows), sum(r["pa"] for r in rows))
        for r in rows:
            self.assertEqual(r["net"], r["pf"] - r["pa"], r["abbr"])
            games = r["w"] + r["l"] + r["t"]
            self.assertAlmostEqual(r["pct"], (r["w"] + r["t"] / 2) / games, places=3, msg=r["abbr"])

    def test_week10_snapshot_matches_official_counts(self):
        w10 = self.official["week10"]
        self.assertEqual(len(w10["games"]), 14)
        self.assertEqual(len(w10["byes"]), 4)
        pairs = [(g["away"], g["home"]) for g in w10["games"]]
        self.assertEqual(len(pairs), len(set(pairs)), "a club cannot play twice in one week")
        clubs = [c for p in pairs for c in p]
        self.assertEqual(len(clubs), len(set(clubs)), "a club cannot appear twice")

    def test_every_strategy_has_eight_gates(self):
        for r in self.strat["strategies"]:
            if "gates" in r:
                self.assertEqual(len(r["gates"]), 8, r["strategy"])
                self.assertEqual(r["gates_passed"], sum(1 for v in r["gates"].values() if v))

    def test_no_strategy_passes_without_significance(self):
        for r in self.strat["strategies"]:
            if r.get("status") == "PASS":
                self.assertTrue(r["gates"]["G5"], "PASS requires the multiple-testing gate")
                self.assertTrue(r["gates"]["G6"], "PASS requires a positive holdout")

    def test_rating_ranks_are_a_permutation(self):
        ranks = sorted(t["rating_rank"] for t in self.state["teams"])
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))

    def test_every_flag_has_a_source(self):
        for f in self.flags["flags"]:
            self.assertTrue(f["source"].startswith("https://"), f["id"])

    def test_blanks_are_null_not_zero(self):
        for t in self.state["teams"]:
            if t["sos_to_date"] is None:
                self.assertGreaterEqual(t["sos_games"], 0)
            if t["next_opponent_rating"] is None:
                # only acceptable when there is no scheduled opponent in the snapshot
                for opp in t["next_opponents"]:
                    self.assertNotEqual(opp, t["team"], "a club cannot be its own next opponent")
                    self.assertNotIn(opp, {x["team"] for x in self.state["teams"]},
                                     "an unresolved club code leaked into the table")


class TestSite(unittest.TestCase):
    def test_gate_script_passes(self):
        import subprocess
        res = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_strength_site.py")],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("PASS", res.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
