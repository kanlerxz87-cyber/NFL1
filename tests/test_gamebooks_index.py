from __future__ import annotations

import copy
import html
import unittest
from referee.tools.build_gamebooks import build_gamebooks_page, load_register, validate_register
from referee.tools.check_gamebooks import check_page


class GameBookIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = load_register()
        cls.rendered = cls.render_page()

    @staticmethod
    def render_page():
        captured = {}

        def escape(value):
            return "" if value is None else html.escape(str(value))

        def link(url, label):
            return f'<a href="{escape(url)}">{escape(label)}</a>'

        def badge(kind, label):
            return f'<span class="chip {escape(kind)}">{escape(label)}</span>'

        def tiles(items):
            return "<div>" + "".join(
                f"<div><b>{escape(value)}</b><span>{escape(label)}</span></div>"
                for _, value, label in items
            ) + "</div>"

        def table(columns, rows, caption=None):
            headers = "".join(f"<th>{escape(label)}</th>" for label, _ in columns)
            body = "".join(
                "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
                for row in rows
            )
            cap = f"<caption>{escape(caption)}</caption>" if caption else ""
            return f"{cap}<table><thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table>"

        def page(filename, title, body, as_of):
            captured["filename"] = filename
            captured["html"] = f"<title>{escape(title)}</title><main>{body}</main>"

        build_gamebooks_page(page=page, table=table, tiles=tiles, e=escape, a=link,
                             chip=badge, as_of="2026-11-12 05:03:04")
        return captured["html"]

    def test_register_is_valid_and_has_all_week10_fixtures(self):
        self.assertEqual(validate_register(self.register), [])
        self.assertEqual(len(self.register["rows"]), 14)
        self.assertEqual(self.register["summary"]["official_gamebook_links_observed"], 13)

    def test_each_row_uses_an_official_gamecenter_and_blank_player_fields(self):
        for row in self.register["rows"]:
            self.assertTrue(row["game_center_url"].startswith("https://www.nfl.com/games/"))
            self.assertFalse(row["gamebook_content_parsed"])
            self.assertIsNone(row["actual_starters"])
            self.assertIsNone(row["official_inactives"])
            self.assertIsNone(row["snap_counts"])

    def test_generator_output_has_a_source_link_for_every_fixture(self):
        self.assertEqual(check_page(self.rendered, self.register), [])

    def test_source_link_must_match_the_fixture_row(self):
        first_center = self.register["rows"][0]["game_center_url"]
        changed_html = self.rendered.replace(first_center, self.register["schedule_url"], 1)
        self.assertTrue(any("table row 1 must link its own official Game Center" in problem
                            for problem in check_page(changed_html, self.register)))

    def test_failed_pdf_fetch_is_attributed_to_the_observed_game(self):
        attempt = self.register["pdf_fetch_attempt"]
        fixture = next(row for row in self.register["rows"] if row["game_id"] == attempt["game_id"])
        self.assertEqual(fixture["gamebook_pdf_url"], attempt["url"])
        self.assertEqual(fixture["game_id"], "2026-reg10-sf-dal")
        self.assertIn("Dallas Cowboys Game Book PDF", self.rendered)
        self.assertNotIn("Washington-at-New-York", self.rendered)

    def test_fetch_attempt_cannot_point_at_an_unrelated_pdf(self):
        changed = copy.deepcopy(self.register)
        changed["pdf_fetch_attempt"]["url"] = changed["rows"][0]["gamebook_pdf_url"]
        self.assertTrue(any("pdf_fetch_attempt.url must match" in p
                            for p in validate_register(changed)))

    def test_wrong_summary_count_fails(self):
        changed = copy.deepcopy(self.register)
        changed["summary"]["official_gamebook_links_observed"] = 14
        self.assertTrue(any("summary.official_gamebook_links_observed" in p
                            for p in validate_register(changed)))

    def test_unverified_starter_cannot_be_filled(self):
        changed = copy.deepcopy(self.register)
        changed["rows"][0]["actual_starters"] = ["unverified player"]
        self.assertTrue(any("actual_starters must stay blank" in p
                            for p in validate_register(changed)))

    def test_blank_player_field_must_be_explicit_in_the_register(self):
        changed = copy.deepcopy(self.register)
        del changed["rows"][0]["actual_starters"]
        self.assertTrue(any("actual_starters must be present as a blank" in p
                            for p in validate_register(changed)))

    def test_non_nfl_game_center_is_rejected(self):
        changed = copy.deepcopy(self.register)
        changed["rows"][0]["game_center_url"] = "https://example.com/games/not-nfl"
        self.assertTrue(any("game_center_url must point to an official HTTPS NFL Game Center" in p
                            for p in validate_register(changed)))

    def test_schedule_has_one_pending_fixture_not_a_false_missing_pdf(self):
        pending = [r for r in self.register["rows"] if r["state_at_observation"] == "scheduled"]
        self.assertEqual(len(pending), 1)
        self.assertIsNone(pending[0]["gamebook_pdf_url"])
        self.assertEqual(pending[0]["gamebook_link_state"], "not_checked_pending_game")
        self.assertIn("Pending final game", self.rendered)


if __name__ == "__main__":
    unittest.main()
