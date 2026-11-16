"""Regression tests for the dashboard line table (session 414a54c9-nfl1).

The "Model (away)" column on web/dashboard.html once printed the negated *market* home
number (``-mk``) instead of the model's away view (``-my``), silently mislabelling a
market number as model output (e.g. IND @ HOU 2026-11-19 showed -10.0 where the model's
away view is -5.7). These tests pin the invariant: the away column is the negation of the
model's home line, and every blank market cell corresponds to a null value in the data.
"""
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rows():
    dash = open(os.path.join(ROOT, "web", "dashboard.html"), encoding="utf-8").read()
    m = re.search(r'id="tbl-lines".*?</table>', dash, re.S)
    assert m, "line table missing from web/dashboard.html"
    rows = re.findall(r"<tr>(.*?)</tr>", m.group(0), re.S)[1:]
    out = []
    for r in rows:
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        out.append(cells)
    return out


class TestLineTableConventions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lines = json.load(
            open(os.path.join(ROOT, "data", "model", "lines.json"), encoding="utf-8"))["lines"]
        cls.rows = _rows()

    def test_row_count_matches_data(self):
        self.assertEqual(len(self.rows), len(self.lines))

    def test_model_away_is_negation_of_model_home_not_market(self):
        for cells, g in zip(self.rows, self.lines):
            my = g.get("my_home_line")
            if my is None:
                continue
            home_cell, away_cell = cells[1], cells[2]
            self.assertNotEqual(home_cell, "blank", g["game_id"])
            # the away view of the model is -my; it must never equal the market away
            # unless the market happens to equal the model (which the data decides)
            self.assertEqual(away_cell, f"{-float(home_cell):.1f}",
                             f"{g['game_id']}: Model (away) must be -model_home, "
                             f"got {away_cell!r} for home {home_cell!r}")
            mk = g.get("market_home_line")
            if mk is not None:
                self.assertEqual(cells[3], f"{mk:.1f}", g["game_id"])
                self.assertEqual(cells[4], f"{-mk:.1f}", g["game_id"])

    def test_blank_market_cells_only_where_data_is_null(self):
        for cells, g in zip(self.rows, self.lines):
            blanks = [c == "blank" for c in cells[3:6]]
            if g.get("market_home_line") is None:
                self.assertTrue(all(blanks),
                                f"{g['game_id']}: market unpublished in data, "
                                f"so market/difference cells must be blank: {cells[3:6]}")
            else:
                self.assertFalse(any(blanks),
                                 f"{g['game_id']}: data has market {g['market_home_line']}, "
                                 f"cells must be numeric: {cells[3:6]}")

    def test_difference_is_model_minus_market_where_both_exist(self):
        for cells, g in zip(self.rows, self.lines):
            if g.get("my_home_line") is None or g.get("market_home_line") is None:
                continue
            diff = round(g["my_home_line"] - g["market_home_line"], 2)
            self.assertAlmostEqual(float(cells[5]), diff, delta=0.011, msg=g["game_id"])


if __name__ == "__main__":
    unittest.main()
