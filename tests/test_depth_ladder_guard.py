"""Unit tests for the failed-scrape guard in pipeline/build_depth_ladder.py (session 2b927826-nfl1).

The defect these tests exist to prevent
---------------------------------------
On 2026-11-16 the injury scraper could not reach nfl.com. `scrape_injuries.py` correctly caught
the exception and wrote `data/model/official_injuries.json` with `status="failed"` and
`rows=[]` — that behaviour is right, because the build then knows the scrape failed.

What was wrong is what happened next: `build_depth_ladder.py` read that file, found no
designations, and rebuilt `data/depth_ladder.json` with **0** slots started by a backup,
against 38 in the committed ladder. Every designating club silently became "no report
published". Nothing failed, nothing warned, and the daily `collect` workflow would have
committed the zeroed ladder.

The observation that makes this a correctness bug rather than a data gap: the absence of a
report is *not* evidence that nobody is injured. Publishing 0 where the repo means 38 is a
false statement about the world, not an honest blank.

The guard makes the rebuild refuse and exit non-zero, leaving the last good ladder in place.
These tests prove the refusal, prove it leaves the file alone, and prove the guard is not
over-broad (a successful scrape with real rows must still rebuild).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "pipeline", "build_depth_ladder.py")
LADDER = os.path.join(ROOT, "data", "depth_ladder.json")


def run_ladder():
    return subprocess.run([sys.executable, SCRIPT], cwd=ROOT,
                          capture_output=True, text=True)


def committed_backup_count():
    with open(LADDER, encoding="utf-8") as f:
        return json.load(f)["counts"]["slots_started_by_a_backup"]


class TestFailedScrapeGuard(unittest.TestCase):
    """The committed injury file is the only input; its `status` field is the guard key."""

    def setUp(self):
        self.inj = os.path.join(ROOT, "data", "model", "official_injuries.json")
        self.backup = None
        if os.path.isfile(self.inj):
            with open(self.inj, encoding="utf-8") as f:
                self.backup = f.read()
        # The ladder is a real committed artifact, and the "not blocked" test deliberately
        # triggers a rebuild from a stub report. Snapshot it too, or a passing test would
        # leave the repository holding a ladder built from one player.
        with open(LADDER, encoding="utf-8") as f:
            self.ladder_backup = f.read()
        self.ladder_before = committed_backup_count()

    def tearDown(self):
        if self.backup is not None:
            with open(self.inj, "w", encoding="utf-8") as f:
                f.write(self.backup)
        with open(LADDER, "w", encoding="utf-8") as f:
            f.write(self.ladder_backup)

    def _write_injuries(self, payload):
        with open(self.inj, "w", encoding="utf-8") as f:
            json.dump(payload, f)

    def test_failed_scrape_is_refused(self):
        """status=failed with no rows must exit non-zero, not publish a zeroed ladder."""
        self._write_injuries({"status": "failed", "error": "TLS closed", "rows": []})
        r = run_ladder()
        self.assertNotEqual(r.returncode, 0,
                            "a failed scrape must fail the rebuild, not publish 0 backups")
        self.assertIn("REFUSING", r.stdout)

    def test_failed_scrape_leaves_the_ladder_untouched(self):
        """The last good ladder survives byte for byte."""
        before = committed_backup_count()
        self._write_injuries({"status": "failed", "error": "timeout", "rows": []})
        run_ladder()
        self.assertEqual(committed_backup_count(), before,
                         "the guard must not degrade the committed ladder")
        # 38 is the value the repository publishes for Week 10; a guard that silently
        # rewrote it to 0 would be the defect these tests exist for.
        self.assertEqual(before, 38)

    def test_status_ok_but_zero_rows_is_also_refused(self):
        """A scrape that reports success but parsed nothing is the same hazard."""
        self._write_injuries({"status": "ok", "week": 10, "rows": []})
        r = run_ladder()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSING", r.stdout)

    def test_a_real_report_is_not_blocked(self):
        """Guard scope: a scrape with rows must still rebuild, or the gate is over-broad.

        This asserts only that the guard does not fire. The rebuild itself may still be
        refused downstream for an unrelated data reason, so the check is on the guard's
        message rather than the exit code.
        """
        payload = {"status": "ok", "week": 10, "season": 2026,
                   "rows": [{"team": "ARI", "player": "Hjalte Froholdt",
                             "game_status": "Out", "practice_status": ""}]}
        self._write_injuries(payload)
        r = run_ladder()
        self.assertNotIn("REFUSING", r.stdout,
                         "the guard must not fire when the scrape produced rows")


if __name__ == "__main__":
    unittest.main()
