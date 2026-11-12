import sys, pathlib, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from nfl import odds


class TestConversions(unittest.TestCase):
    def test_roundtrip_negative(self):
        for a in (-110, -105, -150, -200, -350):
            self.assertEqual(odds.decimal_to_american(odds.american_to_decimal(a)), a)

    def test_roundtrip_positive(self):
        for a in (100, 105, 150, 250, 400):
            self.assertEqual(odds.decimal_to_american(odds.american_to_decimal(a)), a)

    def test_known_values(self):
        self.assertAlmostEqual(odds.american_to_decimal(-110), 1.909091, places=5)
        self.assertAlmostEqual(odds.american_to_decimal(150), 2.5)
        self.assertAlmostEqual(odds.implied_probability(-110), 0.523809, places=5)
        self.assertEqual(odds.prob_to_american(0.5), 100)

    def test_zero_american_rejected(self):
        with self.assertRaises(ValueError):
            odds.american_to_decimal(0)


class TestDevig(unittest.TestCase):
    def test_fair_book_devigs_to_half(self):
        self.assertEqual(odds.devig_multiplicative([-110, -110]), [0.5, 0.5])
        self.assertEqual(odds.devig_power([-110, -110]), [0.5, 0.5])

    def test_overround_exceeds_one_for_a_real_book(self):
        self.assertGreater(odds.overround([-110, -110]), 1.0)

    def test_devigged_probabilities_sum_to_one(self):
        for book in ([-110, -110], [-250, 210], [-135, 115], [300, 500, -800]):
            self.assertAlmostEqual(sum(odds.devig_multiplicative(book)), 1.0, places=5)
            self.assertAlmostEqual(sum(odds.devig_power(book)), 1.0, places=5)

    def test_power_devig_pulls_longshots_down(self):
        m = odds.devig_multiplicative([-400, 320])
        p = odds.devig_power([-400, 320])
        self.assertNotEqual(m, p)


class TestParlay(unittest.TestCase):
    def test_independent_product(self):
        self.assertAlmostEqual(odds.parlay_fair_prob([0.6, 0.5]), 0.30)
        self.assertAlmostEqual(odds.parlay_fair_prob([0.5, 0.5, 0.5]), 0.125)

    def test_positive_correlation_raises_joint_probability(self):
        base = odds.parlay_fair_prob([0.6, 0.5])
        corr = odds.parlay_fair_prob([0.6, 0.5], [0.3])
        self.assertGreater(corr, base)

    def test_negative_correlation_lowers_joint_probability(self):
        base = odds.parlay_fair_prob([0.6, 0.5])
        corr = odds.parlay_fair_prob([0.6, 0.5], [-0.3])
        self.assertLess(corr, base)

    def test_zero_correlation_equals_independent(self):
        self.assertEqual(odds.parlay_fair_prob([0.6, 0.5], [0.0]),
                         odds.parlay_fair_prob([0.6, 0.5]))

    def test_bad_input_rejected(self):
        with self.assertRaises(ValueError):
            odds.parlay_fair_prob([])
        with self.assertRaises(ValueError):
            odds.parlay_fair_prob([1.5, 0.5])
        with self.assertRaises(ValueError):
            odds.parlay_fair_prob([0.6, 0.5], [2.0])


class TestEdge(unittest.TestCase):
    def test_known_edge(self):
        # 55% at -110 is exactly +5% expected value.
        self.assertAlmostEqual(odds.edge(0.55, -110), 0.05, places=6)

    def test_fair_bet_has_negative_edge_at_vig_prices(self):
        self.assertLess(odds.edge(0.50, -110), 0)

    def test_market_contract_is_unavailable_not_guessed(self):
        self.assertEqual(odds.MARKET_DATA_CONTRACT["status"], "UNAVAILABLE")
        self.assertIsNone(odds.MARKET_DATA_CONTRACT.get("value", None))


if __name__ == "__main__":
    unittest.main()
