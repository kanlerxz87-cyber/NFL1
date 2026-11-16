"""Regression test: current standings must use the dated live capture, not historical T3."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import audit_official  # noqa: E402


class CurrentStandingsAuditTests(unittest.TestCase):
    def test_current_snapshot_audits_against_the_latest_official_read(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(audit_official.main(), 0, output.getvalue())
        with open(os.path.join(ROOT, "data", "audit", "4c043747", "official_audit.json"),
                  encoding="utf-8") as fh:
            audit = json.load(fh)
        with open(os.path.join(ROOT, "data", "live", "standings_2026_crosscheck.json"),
                  encoding="utf-8") as fh:
            capture = json.load(fh)
        self.assertEqual(audit["checks_failed"], 0)
        self.assertEqual(audit["retrievals"]["T5 (current standings crosscheck)"],
                         capture["read_utc"])
        self.assertTrue(any(c["check"] == "current official standings capture has 32 clubs"
                            and c["result"] == "PASS" for c in audit["checks"]))


if __name__ == "__main__":
    unittest.main()
