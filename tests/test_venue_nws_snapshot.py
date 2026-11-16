"""NWS /points nearest-location comparison tests."""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "venue"))
import nws_snapshot  # noqa: E402


class NearestLocationTests(unittest.TestCase):
    def test_city_and_state_match_the_official_game_centre(self):
        self.assertTrue(nws_snapshot.nearest_location_match(
            "HOUSTON, TX", {"city": "Houston", "state": "TX"}))

    def test_city_or_state_mismatch_is_not_silently_accepted(self):
        self.assertFalse(nws_snapshot.nearest_location_match(
            "HOUSTON, TX", {"city": "Katy", "state": "TX"}))
        self.assertFalse(nws_snapshot.nearest_location_match(
            "HOUSTON, TX", {"city": "Houston", "state": "LA"}))

    def test_missing_api_location_or_unprinted_state_is_not_a_match(self):
        self.assertIsNone(nws_snapshot.nearest_location_match("HOUSTON, TX", None))
        self.assertIsNone(nws_snapshot.nearest_location_match(
            "MEXICO CITY", {"city": "Mexico City", "state": "CMX"}))
        self.assertIsNone(nws_snapshot.nearest_location_match(
            "HOUSTON, TX", {"city": "Houston", "state": None}))


if __name__ == "__main__":
    unittest.main()
