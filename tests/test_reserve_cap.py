"""Tests for the publisher's printed cap and the union of reads.

Why these exist: the official transactions page shows only the 25 most recent rows of a
category-month, and offers no deeper window. Two failures follow from that and are invisible without
a test — a register that keeps "the newest read" would silently drop rows as the window slides, and
a reader could not tell a quiet month from a truncated one. Both are pinned here.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import collect_transactions as ct  # noqa: E402


def printed_rows(n, oldest_day, month="2026-11", club="MIA"):
    """Rows as the source prints them: newest first, n of them, spanning back to `oldest_day`."""
    y = int(month[:4])
    out = []
    for i in range(n):
        out.append({"date": f"{month}-{oldest_day + n - 1 - i:02d}", "player": f"Player {i}",
                    "position": "", "transaction": "Reserve/Injured",
                    "club_from": club, "club_to": club, "aliases": [],
                    "player_url": f"https://www.nfl.com/players/p-{i}/",
                    "source_url": "https://www.nfl.com/transactions/league/reserve-list/"
                                  f"{y}/{int(month[5:]):d}",
                    "where": f"table 0 row {i}", "flags": []})
    return out


class PrintedCapTest(unittest.TestCase):
    def test_a_full_page_is_marked_capped(self):
        facts = ct.cap_facts(printed_rows(25, 7), 2026, 11)
        self.assertTrue(facts["cap"])
        self.assertEqual(facts["cap_oldest_printed"], "2026-11-07")
        # 25 rows, none earlier than the 7th: the month is NOT fully printed.
        self.assertFalse(facts["cap_month_complete_as_printed"])
        self.assertIn("printed cap", facts["cap_note"])
        self.assertIn("?page=2", facts["cap_note"], "the note must record that no deeper window exists")

    def test_a_shorter_page_is_not_capped_and_is_complete(self):
        facts = ct.cap_facts(printed_rows(12, 6), 2026, 11)
        self.assertFalse(facts["cap"])
        self.assertTrue(facts["cap_month_complete_as_printed"])
        self.assertEqual(facts["cap_note"], "")

    def test_a_capped_page_reaching_the_first_of_the_month_is_complete(self):
        facts = ct.cap_facts(printed_rows(25, 1, month="2026-10"), 2026, 10)
        self.assertTrue(facts["cap"], "25 rows is still the cap, whatever the dates")
        self.assertTrue(facts["cap_month_complete_as_printed"],
                        "the oldest printed row is the 1st, so nothing can be missing above it")

    def test_a_page_of_25_undated_rows_cannot_claim_to_be_complete(self):
        rows = printed_rows(25, 1)
        for r in rows:
            r["date"] = None
        facts = ct.cap_facts(rows, 2026, 11)
        self.assertTrue(facts["cap"])
        self.assertFalse(facts["cap_month_complete_as_printed"],
                         "without a date there is no evidence the window reaches the 1st")


class UnionOfReadsTest(unittest.TestCase):
    """The register is the union of every capture of a page, not the newest capture's rows."""

    @staticmethod
    def _capture(stamp, rows):
        return {"captured_at_utc": stamp, "category": "reserve-list", "month": "2026-11",
                "status": "ok", "http_status": 200, "url": "https://www.nfl.com/transactions/",
                "canonical_sha256": ct.canonical(rows), "row_list": rows,
                "_file": f"data/reserve/captures/{stamp}_reserve-list_2026-11_x.json"}

    def test_a_row_that_left_the_printed_window_survives(self):
        first = printed_rows(25, 1)                     # reads the whole first fortnight
        later = printed_rows(25, 14)                    # window slid: days 1-13 are off the page
        rows, _ = ct.latest_rows_per_key([self._capture("2026-11-16T06:00:00Z", first),
                                          self._capture("2026-11-23T06:00:00Z", later)])
        dates = {r["date"] for r in rows}
        self.assertIn("2026-11-01", dates, "a printed fact must not vanish because the page moved on")
        self.assertIn("2026-11-25", dates)
        self.assertTrue(all(r["seen_in_captures"] for r in rows),
                        "every row must say which read(s) it came from")

    def test_identical_row_in_two_reads_is_one_row(self):
        overlap = printed_rows(25, 10)
        rows, _ = ct.latest_rows_per_key([self._capture("2026-11-16T06:00:00Z", overlap),
                                          self._capture("2026-11-17T06:00:00Z", overlap)])
        self.assertEqual(len(rows), 25, "re-reading a page must not double its rows")

    def test_an_unreadable_capture_does_not_empty_the_page(self):
        good = self._capture("2026-11-16T06:00:00Z", printed_rows(3, 20))
        rows, _ = ct.latest_rows_per_key([{"_unreadable": "x.json", "_file": "x.json"}, good])
        self.assertEqual(len(rows), 3)


class PublishesTheCapTest(unittest.TestCase):
    def test_coverage_and_pages_disclose_it(self):
        """The published page must carry the cap in words, not hide it in a count."""
        cov_path, idx = ROOT / "data" / "reserve" / "coverage.json", ROOT / "reserve" / "index.html"
        if not cov_path.exists() or not idx.exists():
            self.skipTest("no capture store on this branch (CI writes data/reserve/)")
        cov = json.loads(cov_path.read_text(encoding="utf-8"))
        self.assertEqual(cov.get("printed_cap"), ct.PRINTED_CAP)
        text = idx.read_text(encoding="utf-8")
        for key, page in (cov.get("pages") or {}).items():
            if (page.get("rows_last_read") or 0) >= ct.PRINTED_CAP:
                self.assertTrue(page.get("cap"), f"{key}: at the cap but not marked capped")
                self.assertIn("printed cap", text, "a capped page must be disclosed on the site")
                month_start = key.split("/")[1] + "-01"
                oldest = page.get("cap_oldest_printed")
                self.assertEqual(page.get("cap_month_complete_as_printed"),
                                 bool(oldest) and oldest <= month_start,
                                 f"{key}: completeness contradicts its own oldest row {oldest}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
