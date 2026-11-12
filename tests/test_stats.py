import sys, pathlib, unittest, math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from nfl import stats


class TestStats(unittest.TestCase):
    def test_pearson_perfect_positive(self):
        self.assertAlmostEqual(stats.pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)

    def test_pearson_perfect_negative(self):
        self.assertAlmostEqual(stats.pearson([1, 2, 3, 4], [8, 6, 4, 2]), -1.0)

    def test_pearson_degenerate_is_nan_not_zero(self):
        # A constant series must never masquerade as a measured correlation.
        self.assertTrue(math.isnan(stats.pearson([1, 1, 1, 1], [1, 2, 3, 4])))

    def test_pearson_too_small_is_nan(self):
        self.assertTrue(math.isnan(stats.pearson([1, 2], [1, 2])))

    def test_spearman_handles_ties(self):
        self.assertAlmostEqual(stats.spearman([1, 1, 2, 3], [5, 6, 7, 8]),
                               stats.pearson([1.5, 1.5, 3, 4], [5, 6, 7, 8]))

    def test_linfit_exact(self):
        a, b, r2 = stats.linfit([1, 2, 3, 4], [2, 4, 6, 8])
        self.assertAlmostEqual(a, 0.0); self.assertAlmostEqual(b, 2.0)
        self.assertAlmostEqual(r2, 1.0)

    def test_golden_section_finds_minimum(self):
        x, _ = stats.golden_section_min(lambda v: (v - 2.37) ** 2, 0, 5)
        self.assertAlmostEqual(x, 2.37, places=4)

    def test_bootstrap_is_seeded_and_reproducible(self):
        xs = [1, 2, 3, 4, 5, 6, 7, 8]; ys = [2, 4, 5, 4, 7, 8, 9, 11]
        self.assertEqual(stats.bootstrap_ci(xs, ys, stats.pearson),
                         stats.bootstrap_ci(xs, ys, stats.pearson))

    def test_bootstrap_refuses_tiny_samples(self):
        lo, hi = stats.bootstrap_ci([1, 2, 3], [1, 2, 3], stats.pearson)
        self.assertTrue(math.isnan(lo) and math.isnan(hi))

    def test_clean_pairs_never_imputes(self):
        out = stats.clean_pairs([1, None, 3], [1, 2, None])
        self.assertEqual(out, [(1.0, 1.0)])

    def test_rmse_mae(self):
        self.assertAlmostEqual(stats.rmse([1, 2], [2, 4]), math.sqrt(2.5))
        self.assertAlmostEqual(stats.mae([1, 2], [2, 4]), 1.5)


class TestBenjaminiHochberg(unittest.TestCase):
    def test_monotone_and_capped(self):
        from nfl import correlation
        q = correlation.benjamini_hochberg([0.001, 0.01, 0.03, 0.5, 0.9])
        self.assertTrue(all(0 <= x <= 1 for x in q))
        self.assertLessEqual(q[0], q[1]); self.assertLessEqual(q[1], q[2])

    def test_all_large_pvalues_give_large_q(self):
        from nfl import correlation
        q = correlation.benjamini_hochberg([0.8, 0.9, 0.95])
        self.assertTrue(all(x > 0.5 for x in q))

    def test_pvalue_matches_known_t(self):
        from nfl import correlation
        # t = 2.306 on 8 df is the two-sided 0.05 critical value.
        self.assertAlmostEqual(correlation._p_from_t(2.306, 8), 0.05, places=3)
        self.assertAlmostEqual(correlation._p_from_t(0.0, 10), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
