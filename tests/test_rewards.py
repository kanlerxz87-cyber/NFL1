#!/usr/bin/env python3
"""Unit tests for the Reward Board (session c5444cc9-nfl1, readiness MO-04).

The reward rule is a pre-registered proposal frozen before grading. These tests pin the
things that would let the board lie: a drifted rule, a blank threshold, a backtest metric
smuggled in as a column, a row without a source, or a non-reproducible build.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REWARDS = ROOT / "rewards"
DATA = ROOT / "data" / "rewards"
RULE_FILE = REWARDS / "REWARDS-RULE.md"


def _load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def _run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


class ThresholdsTest(unittest.TestCase):
    def test_every_threshold_has_a_concrete_value(self):
        th = _load("thresholds.json")["thresholds"]
        self.assertGreater(len(th), 0)
        for t in th:
            val = str(t.get("value", "")).strip()
            self.assertTrue(val, f"threshold {t.get('id')} has no value")
            self.assertNotIn(val.lower(), {"blank", "tbd", "n/a", "todo", "placeholder"})
            self.assertIsNotNone(t.get("numeric"), f"threshold {t.get('id')} has no numeric")
            self.assertTrue(t.get("source_url", "").startswith("https://"))

    def test_expected_thresholds_present(self):
        ids = {t["id"] for t in _load("thresholds.json")["thresholds"]}
        self.assertEqual(ids, {"T1", "T2", "T3", "T4", "T5", "T6"})


class RegistrationTest(unittest.TestCase):
    def test_rule_sha256_matches_file(self):
        rule = _load("rewards.json")
        actual = hashlib.sha256(RULE_FILE.read_bytes()).hexdigest()
        self.assertEqual(actual, rule["rule_sha256"])

    def test_registration_commit_matches_git(self):
        rule = _load("rewards.json")
        r = _run(["git", "log", "--diff-filter=A", "--format=%H", "-1", "--",
                  "rewards/REWARDS-RULE.md"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), rule["registration_commit"])

    def test_rule_file_is_frozen_text(self):
        text = RULE_FILE.read_text(encoding="utf-8")
        for needle in ("Stage 1", "Stage 2", "Verified Signal", "non-monetary",
                       "what would change our mind"):
            self.assertIn(needle, text)


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = _run([sys.executable, "rewards/build.py"])
        cls.html = (REWARDS / "index.html").read_text(encoding="utf-8")

    def test_build_succeeds(self):
        self.assertEqual(self.build.returncode, 0, self.build.stderr)

    def test_build_is_reproducible(self):
        _run([sys.executable, "rewards/build.py"])
        self.assertEqual((REWARDS / "index.html").read_text(encoding="utf-8"), self.html)

    def test_no_backtest_metric_as_table_header(self):
        headers = re.findall(r"<th[^>]*>(.*?)</th>", self.html, re.S)
        pat = re.compile(r"\b(roi|win rate|hit rate|profit|return)\b", re.I)
        for h in headers:
            self.assertIsNone(pat.search(h), f"backtest metric in header: {h!r}")

    def test_every_data_table_row_has_https_source(self):
        # each <tr> in a <tbody> must contain at least one https:// link
        tbody = re.findall(r"<tbody>(.*?)</tbody>", self.html, re.S)
        self.assertTrue(tbody)
        for block in tbody:
            for tr in re.findall(r"<tr>(.*?)</tr>", block, re.S):
                if "<td" not in tr:
                    continue
                self.assertRegex(tr, r"https://", "a data row without an https source")

    def test_no_empty_cells(self):
        for cell in re.findall(r"<td[^>]*>\s*</td>", self.html):
            self.fail(f"empty table cell: {cell!r}")


class VerifyTest(unittest.TestCase):
    def test_verify_passes(self):
        r = _run([sys.executable, "rewards/verify.py"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)


if __name__ == "__main__":
    unittest.main()
