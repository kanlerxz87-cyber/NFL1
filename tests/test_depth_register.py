"""Unit tests for tools/build_depth_register.py (session d4027f66-nfl1)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_depth_register as bdr  # noqa: E402

HEADER = """# Official club depth chart, captured verbatim
club: XX
club_name: Test Club
url: https://www.example.com/team/depth-chart
page_title: Test
page_label: Unofficial
fetched: 2026-11-15
capture_method: test
---
"""


def _write(body: str) -> Path:
    d = tempfile.mkdtemp()
    p = Path(d) / "XX_2026-11-15.md"
    p.write_text(HEADER + body, encoding="utf-8")
    return p


GOOD = """## Offense
| WR | 9 Christian Watson | 16 Bo Melton |  |
| WR | 0 Matthew Golden |  |  |
|  |  |  | 26 Kaleb Johnson |
## Defense
| CB | [Devon Witherspoon] [Nehemiah Pritchett] |  |
## Special Teams
| PR |  | 0 Matthew Golden |  |
"""


class DepthRegisterTests(unittest.TestCase):
    def test_jersey_prefix_is_stripped_and_raw_kept(self):
        parsed = bdr.parse_raw(_write(GOOD))
        rows = bdr.build_rows(parsed)
        r = next(x for x in rows if x["name"] == "Christian Watson")
        self.assertEqual(r["jersey"], "9")
        self.assertEqual(r["raw_cell"], "9 Christian Watson")
        self.assertTrue(r["jersey_stripped"])

    def test_shared_slot_is_one_slot_with_two_players(self):
        rows = bdr.build_rows(bdr.parse_raw(_write(GOOD)))
        shared = [r for r in rows if r["shared_slot"]]
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0]["names"], ["Devon Witherspoon", "Nehemiah Pritchett"])
        self.assertEqual(shared[0]["column"], 1)

    def test_empty_gap_before_a_filled_cell_is_recorded(self):
        rows = bdr.build_rows(bdr.parse_raw(_write(GOOD)))
        gaps = [r for r in rows if r["empty_gap"]]
        # PR row: column 1 empty, column 2 filled -> one gap at column 1
        self.assertTrue(any(g["position"] == "PR" and g["column"] == 1 for g in gaps))
        # trailing empties are not recorded as gaps
        self.assertFalse(any(g["position"] == "WR" and g["column"] == 3 for g in gaps))

    def test_continuation_row_inherits_label_and_is_marked(self):
        rows = bdr.build_rows(bdr.parse_raw(_write(GOOD)))
        cont = [r for r in rows if r["continuation_row"] and not r["empty_gap"]]
        self.assertEqual([r["name"] for r in cont], ["Kaleb Johnson"])
        self.assertEqual(cont[0]["position"], "WR")

    def test_multiple_rank1_rows_form_one_group_not_one_starter(self):
        parsed = bdr.parse_raw(_write(GOOD))
        rows = bdr.build_rows(parsed)
        summary = bdr.summarise(rows, {"XX": parsed["meta"]})
        detail = summary["clubs"]["XX"]["groups_with_more_than_one_rank1_detail"]
        self.assertIn("XX|Offense|WR", detail)
        self.assertEqual(sorted(detail["XX|Offense|WR"]), ["Christian Watson", "Matthew Golden"])

    def test_schema_drift_missing_section_fails_loudly(self):
        bad = "## Offense\n| WR | 9 Christian Watson |\n## Defense\n| CB | Nobody |\n"
        with self.assertRaises(ValueError):
            bdr.parse_raw(_write(bad))

    def test_missing_metadata_fails_loudly(self):
        p = Path(tempfile.mkdtemp()) / "XX.md"
        p.write_text("# t\nclub: XX\n---\n## Offense\n## Defense\n## Special Teams\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            bdr.parse_raw(p)

    def test_committed_register_matches_captures(self):
        js, tsv, cmp_js = bdr.build()
        self.assertEqual((ROOT / "data/depth/official_register.json").read_text(encoding="utf-8"), js)
        self.assertEqual((ROOT / "data/depth/official_register.tsv").read_text(encoding="utf-8"), tsv)
        self.assertEqual((ROOT / "data/depth/comparison.json").read_text(encoding="utf-8"), cmp_js)


if __name__ == "__main__":
    unittest.main()
