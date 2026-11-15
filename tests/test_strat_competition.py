"""Unit tests for the strategy-competition subsystem (session c7b65577-nfl1).

These test the gates themselves, not the published numbers: a gate that cannot fail is not a gate,
so every test here is written to prove that a defect is caught.
"""
import json
import os
import subprocess
import sys
import unittest


def _jload(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _rtext(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "strat"))
sys.path.insert(0, os.path.join(ROOT, "tools"))


class TestPreregistrationGate(unittest.TestCase):
    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "cpr", os.path.join(ROOT, "tools", "check_preregistration.py"))
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.reg = _jload(os.path.join(ROOT, "data/strat/preregistration.json"))
        self.scored = {r["strategy"] for r in
                       _jload(os.path.join(ROOT, "data/s9cb/leaderboard.json"))["leaderboard"]}
        self.gen = _rtext(os.path.join(ROOT, "s9cb/analysis/strategies.py"))

    def test_clean_tree_passes(self):
        self.assertEqual(self.mod.check(self.reg, self.scored, self.gen), [])

    def test_unregistered_result_fails(self):
        probs = self.mod.check(self.reg, self.scored | {"S99 Nobody registered me"}, self.gen)
        self.assertTrue(any("no registration" in p for p in probs))

    def test_text_drift_fails(self):
        reg = {**self.reg, "records": [{**self.reg["records"][0], "name": "invented rule name"}]
               + self.reg["records"][1:]}
        probs = self.mod.check(reg, self.scored, self.gen)
        self.assertTrue(any("drifted" in p for p in probs) or
                        any("no longer appears" in p for p in probs))

    def test_prospective_rule_with_a_result_fails(self):
        prom = next(r for r in self.reg["records"] if r["status"] == "registered-prospective")
        probs = self.mod.check(self.reg, self.scored | {f"{prom['id']} {prom['name']}"}, self.gen)
        self.assertTrue(any("prospective" in p for p in probs))

    def test_edited_registry_fails_the_stamp(self):
        stamp = _jload(os.path.join(ROOT, "data/strat/preregistration_stamp.json"))
        probs = []
        self.mod.check_stamp({**stamp, "file_sha256_as_committed": "0" * 64}, self.reg, probs)
        self.assertTrue(probs)


class TestDriftAlarm(unittest.TestCase):
    def test_self_test_proves_the_alarm_fires(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools/check_scraper_pins.py"),
                            "--self-test"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("FAILED as it must", r.stdout)


class TestPreRegistrationSelfTest(unittest.TestCase):
    def test_gate_self_test(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools/check_preregistration.py"),
                            "--self-test"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("MISSED", r.stdout)


class TestSiteGate(unittest.TestCase):
    def test_site_verifies(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "strat/verify.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class TestProperScoreArithmetic(unittest.TestCase):
    """The Brier arithmetic must be checkable by hand, or the leaderboard is unfalsifiable."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ps", os.path.join(ROOT, "strat", "proper_score.py"))
        self.ps = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.ps)

    def test_brier_of_a_perfect_forecast_is_zero(self):
        self.assertEqual(self.ps.brier([1.0, 0.0], [1.0, 0.0]), 0.0)

    def test_brier_of_a_coin_is_one_quarter(self):
        self.assertAlmostEqual(self.ps.brier([0.5, 0.5], [1.0, 0.0]), 0.25)

    def test_devig_sums_to_one(self):
        p = self.ps.devig_two_way(0.55, 0.55)
        self.assertAlmostEqual(p, 0.5)

    def test_norm_cdf_matches_known_values(self):
        self.assertAlmostEqual(float(self.ps.norm_cdf(0.0)), 0.5, places=6)
        self.assertAlmostEqual(float(self.ps.norm_cdf(1.959964)), 0.975, places=5)
        self.assertAlmostEqual(float(self.ps.norm_cdf(-1.959964)), 0.025, places=5)

    def test_benjamini_hochberg_is_monotone(self):
        adj, bonf, m = self.ps.bh_and_bonferroni([0.01, 0.04, 0.03])
        self.assertEqual(m, 3)
        vals = [a for a in adj if a is not None]
        self.assertEqual(vals, sorted(vals))
        self.assertAlmostEqual(bonf, 0.05 / 3)


class TestDemotionRuleIsArmed(unittest.TestCase):
    def test_rules_and_thresholds_exist(self):
        d = _jload(os.path.join(ROOT, "data/strat/demotion.json"))
        self.assertEqual(len(d["rules"]), 5)
        for r in d["rules"]:
            self.assertIn("minimum_sample", r)
            self.assertIn("rationale", r)
        self.assertFalse(d["any_strategy_live"])
        self.assertEqual(d["n_live"], 0)

    def test_no_strategy_is_claimed_live(self):
        d = _jload(os.path.join(ROOT, "data/strat/demotion.json"))
        self.assertTrue(all(r["status"] == "PAPER" for r in d["rows"]))


class TestFalsifiersAreTwoSided(unittest.TestCase):
    def test_every_claim_has_both_directions(self):
        d = _jload(os.path.join(ROOT, "data/strat/what_would_change.json"))
        self.assertGreaterEqual(d["n_claims"], 10)
        for r in d["rows"]:
            for field in ("confirm_if", "abandon_if", "next_measurement", "current"):
                self.assertTrue(r.get(field), f"{r['id']} has no {field}")


class TestTwoTotalsAreBothPublished(unittest.TestCase):
    def test_verdict_and_gap_column(self):
        d = _jload(os.path.join(ROOT, "data/strat/dual_total.json"))
        self.assertIn("winner", d["verdict"])
        self.assertIn("ci95", d["holdout"])
        self.assertGreater(d["n_board"], 0)
        self.assertTrue(any(b["gap"] is not None for b in d["board"]))


if __name__ == "__main__":
    unittest.main()
