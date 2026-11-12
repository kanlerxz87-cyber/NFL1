import sys, pathlib, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from nfl import gates


def good(**over):
    base = dict(market_type="single", bets=[{}] * 400, odds_available=True,
                provenance_tiers=["VERIFIED", "DERIVED"],
                features_timestamped_before_kickoff=True,
                walk_forward_split_documented=True, insample_roi=0.06,
                oos_roi=0.045, oos_n=200, roi_t=3.4, roi_ci95=(0.012, 0.078),
                placebo_p=0.004, fold_profits=[1.0] * 9 + [0.4],
                measured_leg_correlations=[], clv_points=0.55,
                avg_stake_limit=5000, model_stake=500)
    base.update(over)
    return gates.Evaluation(**base)


class TestGates(unittest.TestCase):
    def test_a_well_formed_strategy_is_approved(self):
        # Proves the gates can say yes - a gate that only ever says no is not evidence.
        self.assertEqual(gates.evaluate(good())["verdict"], "APPROVED")

    def test_empty_evaluation_is_not_stakeable(self):
        r = gates.evaluate(gates.Evaluation(market_type="single"))
        self.assertEqual(r["verdict"], "NOT_STAKEABLE")
        self.assertGreater(r["blocked"], 0)

    def test_lookahead_is_rejected(self):
        self.assertEqual(gates.evaluate(good(features_timestamped_before_kickoff=False))["verdict"],
                         "REJECTED")

    def test_edge_within_noise_is_rejected(self):
        self.assertEqual(gates.evaluate(good(roi_t=1.4))["verdict"], "REJECTED")

    def test_placebo_failure_is_rejected(self):
        self.assertEqual(gates.evaluate(good(placebo_p=0.40))["verdict"], "REJECTED")

    def test_ci_spanning_zero_is_rejected(self):
        self.assertEqual(gates.evaluate(good(roi_ci95=(-0.01, 0.08)))["verdict"], "REJECTED")

    def test_profit_concentrated_in_one_fold_is_rejected(self):
        self.assertEqual(gates.evaluate(good(fold_profits=[9.0] + [0.1] * 9))["verdict"], "REJECTED")

    def test_unstable_sign_is_rejected(self):
        self.assertEqual(gates.evaluate(good(fold_profits=[1, -1, 1, -1, 1, -1, 1, -1, 1, 4]))["verdict"],
                         "REJECTED")

    def test_out_of_sample_degradation_is_rejected(self):
        self.assertEqual(gates.evaluate(good(insample_roi=0.10, oos_roi=0.01))["verdict"], "REJECTED")

    def test_modeled_input_blocks_rather_than_passes(self):
        self.assertEqual(gates.evaluate(good(provenance_tiers=["DERIVED", "MODELED"]))["verdict"],
                         "NOT_STAKEABLE")

    def test_unavailable_input_fails(self):
        self.assertEqual(gates.evaluate(good(provenance_tiers=["UNAVAILABLE"]))["verdict"], "REJECTED")

    def test_parlay_without_measured_correlation_is_blocked(self):
        r = gates.evaluate(good(market_type="parlay", measured_leg_correlations=[]))
        self.assertEqual(r["verdict"], "NOT_STAKEABLE")
        g8 = next(g for g in r["gates"] if g["gate_id"] == "G8")
        self.assertEqual(g8["status"], gates.BLOCKED)

    def test_parlay_with_measured_correlation_passes_g8(self):
        r = gates.evaluate(good(market_type="parlay", bets=[{}] * 200,
                                measured_leg_correlations=[0.22, 0.05]))
        g8 = next(g for g in r["gates"] if g["gate_id"] == "G8")
        self.assertEqual(g8["status"], gates.PASS)

    def test_g8_not_applicable_to_singles(self):
        r = gates.evaluate(good())
        g8 = next(g for g in r["gates"] if g["gate_id"] == "G8")
        self.assertEqual(g8["status"], gates.PASS)
        self.assertFalse(g8["fatal"])

    def test_negative_clv_is_rejected(self):
        self.assertEqual(gates.evaluate(good(clv_points=-0.3))["verdict"], "REJECTED")

    def test_limits_below_stake_is_rejected(self):
        self.assertEqual(gates.evaluate(good(avg_stake_limit=100, model_stake=500))["verdict"],
                         "REJECTED")

    def test_sample_thresholds_by_market_type(self):
        self.assertEqual(gates.MIN_SAMPLES["single"], 300)
        self.assertGreater(gates.MIN_SAMPLES["single"], gates.MIN_SAMPLES["parlay"])
        r = gates.evaluate(good(market_type="parlay", bets=[{}] * 100))
        self.assertEqual(r["verdict"], "NOT_STAKEABLE")

    def test_blocked_is_never_treated_as_pass(self):
        for fn in gates.ALL_GATES:
            r = fn(gates.Evaluation())
            self.assertIn(r.status, (gates.PASS, gates.FAIL, gates.BLOCKED))
            if r.status == gates.BLOCKED:
                self.assertNotEqual(r.status, gates.PASS)


if __name__ == "__main__":
    unittest.main()
