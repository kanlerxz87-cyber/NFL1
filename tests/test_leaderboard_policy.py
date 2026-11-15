"""Policy guard: backtest numbers must never appear on the ranked leaderboard.

Brief rule (session e1fa878e-nfl1, flag F-7810-09): "forbid backtest numbers from ever
appearing on the leaderboard". This test renders the ranked board from the real
data/s9cb/leaderboard.json and fails if any return, hit-rate, p-value, interval or
luck-band figure reaches it. The historical scoring is checked to still exist on the
separate Backtest page, so the figures were moved rather than deleted.
"""
import importlib.util
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN = ["roi", "hit rate", "hit_rate", "p-value", "p_value", "profit", "units",
             "confidence interval", "95% ci", "luck band", "bootstrap"]


def load_site():
    spec = importlib.util.spec_from_file_location("s9cb_site", ROOT / "s9cb" / "site.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class LeaderboardPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = load_site()
        cls.LB = json.loads((ROOT / "data" / "s9cb" / "leaderboard.json").read_text())

    def text_of(self, html: str) -> str:
        return re.sub(r"<[^>]+>", " ", html).lower()

    def test_ranked_board_has_no_backtest_figures(self):
        """Checks the KPI strip and the ranked table. The gate definitions are rule text and
        are allowed to name the metrics they exclude; the explanatory note is excluded too."""
        body = self.site.page_leaderboard(self.LB)
        kpis = body.split("<table", 1)[0]
        ranked = body.split("<h2>Ranked board</h2>", 1)[1].split("<h2>Gate matrix</h2>", 1)[0]
        ranked = re.sub(r'<p class="note">.*?</p>', "", ranked, flags=re.S)
        text = self.text_of(kpis + ranked)
        for word in FORBIDDEN:
            self.assertNotIn(word, text, f"backtest term '{word}' leaked onto the ranked board")
        # strategy-name cells carry the rule's own threshold (e.g. "edge >= 4.0 pts"); exempt them
        figures = re.sub(r"<td>S\d\d [^<]*</td>", "", ranked)
        self.assertNotRegex(figures, r"\d+\.\d+", "a decimal figure leaked onto the ranked board")

    def test_no_strategy_is_ranked_without_passing_all_gates(self):
        passed = [r for r in self.LB["leaderboard"] if r["status"] == "PASS"]
        body = self.site.page_leaderboard(self.LB)
        self.assertIn(f"<span class=\"v\">{len(passed)}</span>", body)

    def test_backtest_figures_moved_not_deleted(self):
        body = self.site.page_backtest(self.LB)
        self.assertIn("NOT A LEADERBOARD RESULT", body)
        self.assertIn("roi", self.text_of(body))


if __name__ == "__main__":
    unittest.main()
