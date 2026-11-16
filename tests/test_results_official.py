#!/usr/bin/env python3
"""Tests for tools/check_results_official.py (session 9a1c5fa6-nfl1).

The real run pins the counts that the committed official read must produce. The negative
tests copy the inputs into a temporary directory, corrupt one value, and require the checker
to fail on that value, so the gate is shown to bite and not only to pass.
"""
from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_results_official", ROOT / "tools/check_results_official.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class RealRun(unittest.TestCase):
    def test_committed_read_passes_and_counts_are_pinned(self):
        # Writes the committed output files, as the tool does on every run.
        self.assertEqual(mod.main(), 0)
        import json
        report = json.loads(mod.OUT_JSON.read_text(encoding="utf-8"))
        self.assertTrue(report["verification_pass"])
        self.assertEqual(report["official_final_games"], 149)
        self.assertEqual(report["matched_exactly"], 136)
        self.assertEqual(report["mismatches"], [])
        self.assertEqual(len(report["coverage_gap_official_finals_not_in_results_file"]), 13)
        self.assertEqual(len(report["scheduled_not_final_at_read_time"]), 1)
        self.assertEqual(report["checks"]["V8_records_checked"], 32)
        self.assertTrue(all(r["equal"] for r in report["record_check"]))

    def test_every_official_game_has_an_official_link(self):
        import csv
        with mod.OUT_CSV.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 149)
        for r in rows:
            self.assertTrue(r["official_game_url"].startswith("https://www.nfl.com/games/"), r)


class Corrupted(unittest.TestCase):
    """Each test copies the inputs, changes one value, and runs the checker on the copy."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.official = self.tmp / "official.tsv"
        self.results = self.tmp / "games_2026.csv"
        shutil.copy(mod.OFFICIAL_TSV, self.official)
        shutil.copy(mod.CSV_RESULTS, self.results)
        self._saved = {k: getattr(mod, k) for k in ("OFFICIAL_TSV", "CSV_RESULTS", "OUT_CSV", "OUT_JSON", "OUT_MD")}
        mod.OFFICIAL_TSV = self.official
        mod.CSV_RESULTS = self.results
        mod.OUT_CSV = self.tmp / "out.csv"
        mod.OUT_JSON = self.tmp / "out.json"
        mod.OUT_MD = self.tmp / "out.md"

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(mod, k, v)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _edit(self, path, old, new):
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1, f"expected one occurrence of {old!r}")
        path.write_text(text.replace(old, new), encoding="utf-8")

    def test_header_and_columns_disagree(self):
        # Change a score column only: the header still says 10-13.
        self._edit(self.official, "1\tWed 2026-09-09\tNE\t10\tSEA\t13", "1\tWed 2026-09-09\tNE\t11\tSEA\t13")
        self.assertEqual(mod.main(), 1)

    def test_results_file_disagrees_with_official_page(self):
        # Change the results file only: both the official read and the header are unchanged.
        self._edit(self.results, "2026_REG_1_NE_SEA,1,2026-09-09,NE,10,SEA,13", "2026_REG_1_NE_SEA,1,2026-09-09,NE,10,SEA,14")
        self.assertEqual(mod.main(), 1)

    def test_wrong_club_in_row(self):
        self._edit(self.official, "1\tWed 2026-09-09\tNE\t10\tSEA\t13", "1\tWed 2026-09-09\tNYJ\t10\tSEA\t13")
        self.assertEqual(mod.main(), 1)


if __name__ == "__main__":
    unittest.main()
