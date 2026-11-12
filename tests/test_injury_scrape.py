"""Reporting contract for official injury ingestion and mirrored-feed fallback."""
from __future__ import annotations

import unittest

from pipeline.report_ingestion import render_summary


class TestInjuryIngestionSummary(unittest.TestCase):
    def test_current_official_report_is_reported_as_model_source(self):
        official = {
            "status": "ok",
            "week": 10,
            "counts": {"rows": 254, "teams": 26},
        }
        availability = {
            "week": 10,
            "source": {
                "label": "official nfl.com injury report (scraped)",
                "warning": None,
            },
        }

        summary, warning = render_summary(official, availability)

        self.assertFalse(warning)
        self.assertIn("Official report week: 10", summary)
        self.assertIn("254 / 26", summary)
        self.assertIn("official nfl.com injury report (scraped)", summary)
        self.assertIn("Official report accepted", summary)

    def test_failed_scrape_and_mirrored_fallback_are_explicit(self):
        official = {
            "status": "failed",
            "error": "network timeout",
            "rows": [],
        }
        availability = {
            "week": 9,
            "source": {
                "label": "mirrored feed, latest complete week (9)",
                "warning": "The official current-week report could not be scraped.",
            },
        }

        summary, warning = render_summary(official, availability)

        self.assertTrue(warning)
        self.assertIn("Official scrape status: **failed**", summary)
        self.assertIn("Week used by availability model: 9", summary)
        self.assertIn("mirrored feed, latest complete week (9)", summary)
        self.assertIn("checking the official report", summary)

    def test_valid_scrape_that_model_rejects_for_week_mismatch_warns(self):
        official = {"status": "ok", "week": 10, "counts": {"rows": 254, "teams": 26}}
        availability = {
            "week": 9,
            "source": {
                "label": "mirrored feed, latest complete week (9)",
                "warning": "The official report did not match the target week.",
            },
        }

        summary, warning = render_summary(official, availability)

        self.assertTrue(warning)
        self.assertIn("Official scrape status: **ok**", summary)
        self.assertIn("Action required", summary)
        self.assertIn("The official report did not match the target week.", summary)

    def test_missing_outputs_are_not_presented_as_success(self):
        summary, warning = render_summary({}, {})

        self.assertTrue(warning)
        self.assertIn("Official scrape status: **missing**", summary)
        self.assertIn("availability output unavailable", summary)


if __name__ == "__main__":
    unittest.main()
