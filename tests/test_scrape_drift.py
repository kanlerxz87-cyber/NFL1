"""Tests for tools/check_scrape_drift.py (P4). Each test injects one fault into a copy of the scrape."""
import copy
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_scrape_drift as d  # noqa: E402

SCRAPE = json.load(open(d.SCRAPE, encoding="utf-8"))


def run_with(mutate):
    data = copy.deepcopy(SCRAPE)
    mutate(data)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(data, fh)
        path = fh.name
    try:
        return d.run(path)
    finally:
        os.unlink(path)


class DriftAlarm(unittest.TestCase):
    def test_committed_scrape_passes(self):
        failures, warnings, n = d.run()
        self.assertEqual(failures, [])
        self.assertEqual(n, 347)

    def test_dropped_row_fails(self):
        f, _, _ = run_with(lambda s: s["rows"].pop(10))
        self.assertTrue(any("rows" in x and "pinned" in x for x in f), f[:3])

    def test_blank_required_field_fails(self):
        f, _, _ = run_with(lambda s: s["rows"][5].__setitem__("practice", ""))
        self.assertTrue(any("blank 'practice'" in x for x in f), f[:3])

    def test_error_status_fails(self):
        f, _, _ = run_with(lambda s: s.__setitem__("status", "parse-incomplete"))
        self.assertTrue(any("status is" in x for x in f), f[:3])

    def test_wrong_week_fails(self):
        f, _, _ = run_with(lambda s: s.__setitem__("week", 9))
        self.assertTrue(any("week" in x for x in f), f[:3])

    def test_designation_change_is_warning_not_failure(self):
        def mutate(s):
            s["rows"][0]["injury"] = "CHANGED-FOR-TEST"
        f, w, _ = run_with(mutate)
        self.assertEqual(f, [])
        self.assertTrue(any("CHANGED-FOR-TEST" in x for x in w), w[:3])


if __name__ == "__main__":
    unittest.main()
