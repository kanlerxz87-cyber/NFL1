#!/usr/bin/env python3
"""Unit tests for the official transactions register (session 1d824ec2-nfl1).

The HTML fixtures carry two rows transcribed verbatim from
https://www.nfl.com/transactions/league/reserve-list/2026/11 as it printed on 2026-11-16
(NOA: Christen Miller, Reserve/Injured, 11/14; MIA: Malik Willis, Reserve/Injured, 11/10), so
the parser is pinned to real official content, not to a guess about the markup.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("collect_transactions",
                                              ROOT / "pipeline" / "collect_transactions.py")
ct = importlib.util.module_from_spec(spec)
sys.modules["collect_transactions"] = ct
spec.loader.exec_module(ct)

ROW_MILLER = """
      <tr>
        <td><a href="https://www.nfl.com/teams/new-orleans-saints/"><img src="https://static.www.nfl.com/t_q-best/league/api/clubs/logos/NO"/><br><br>Saints<br><br>Saints</a></td>
        <td><a href="https://www.nfl.com/teams/new-orleans-saints/"><img src="https://static.www.nfl.com/t_q-best/league/api/clubs/logos/NO"/><br><br>Saints<br><br>Saints</a></td>
        <td>11/14</td>
        <td><a href="https://www.nfl.com/players/christen-miller/">Christen Miller</a></td>
        <td></td>
        <td>Reserve/Injured</td>
      </tr>"""
ROW_WILLIS = """
      <tr>
        <td><a href="https://www.nfl.com/teams/miami-dolphins/"><img src="https://static.www.nfl.com/t_q-best/league/api/clubs/logos/MIA"/><br><br>Dolphins<br><br>Dolphins</a></td>
        <td><a href="https://www.nfl.com/teams/miami-dolphins/"><img src="https://static.www.nfl.com/t_q-best/league/api/clubs/logos/MIA"/><br><br>Dolphins<br><br>Dolphins</a></td>
        <td>11/10</td>
        <td><a href="https://www.nfl.com/players/malik-willis/">Malik Willis</a></td>
        <td></td>
        <td>Reserve/Injured</td>
      </tr>"""
HEAD = """<thead><tr><th>From</th><th>To</th><th>Date</th><th>Name</th><th>Position</th>
        <th>Transaction</th></tr></thead>"""


def page(rows: list[str], head: str = HEAD) -> str:
    return f"<html><body><table>{head}<tbody>{''.join(rows)}</tbody></table></body></html>"


class ParseTest(unittest.TestCase):
    def test_two_verbatim_rows(self):
        rows, headers, flags = ct.parse_rows(page([ROW_MILLER, ROW_WILLIS]), 2026, 11, "u")
        self.assertEqual(flags, [], f"unexpected flags {flags}")
        self.assertEqual(len(rows), 2)
        miller = rows[0]
        self.assertEqual(miller["player"], "Christen Miller")
        self.assertEqual(miller["date"], "2026-11-14")
        self.assertEqual(miller["date_printed"], "11/14")
        self.assertEqual(miller["club_from"], "NO")
        self.assertEqual(miller["club_to"], "NO")
        self.assertEqual(miller["transaction"], "Reserve/Injured")
        self.assertEqual(miller["player_url"], "https://www.nfl.com/players/christen-miller/")
        self.assertEqual(miller["source_url"], "u")
        self.assertIsNone(miller["position_printed"], "a blank printed cell must stay blank")
        self.assertEqual(rows[1]["player"], "Malik Willis")
        self.assertEqual(rows[1]["date"], "2026-11-10")

    def test_header_names_not_positions(self):
        """A reordered table still fills the right fields; a missing required header fails loudly."""
        reordered = ("<thead><tr><th>Date</th><th>Name</th><th>From</th><th>To</th>"
                     "<th>Transaction</th><th>Position</th></tr></thead>")
        row = """<tr><td>11/14</td><td><a href="https://www.nfl.com/players/christen-miller/">Christen Miller</a></td>
                   <td><img src="https://static.www.nfl.com/league/api/clubs/logos/NO"/></td>
                   <td><img src="https://static.www.nfl.com/league/api/clubs/logos/NO"/></td>
                   <td>Reserve/Injured</td><td></td></tr>"""
        rows, _h, flags = ct.parse_rows(f"<table>{reordered}<tbody>{row}</tbody></table>",
                                        2026, 11, "u")
        self.assertEqual(flags, [])
        self.assertEqual(rows[0]["player"], "Christen Miller")
        self.assertEqual(rows[0]["transaction"], "Reserve/Injured")
        # Now drop the Name header: the parser must flag, not shift columns.
        bad = ("<thead><tr><th>From</th><th>To</th><th>Date</th><th>Position</th>"
               "<th>Transaction</th></tr></thead>")
        rows, _h, flags = ct.parse_rows(f"<table>{bad}<tbody>{ROW_MILLER}</tbody></table>",
                                        2026, 11, "u")
        self.assertTrue(any("required header" in f for f in flags), flags)
        self.assertEqual(rows, [], "a table with no Name column must publish nothing, not a shift")

    def test_club_alias_recorded_not_silent(self):
        """The printed register uses AZ and LA; the repo code is ARI and LA (Rams)."""
        tr = ROW_MILLER.replace("logos/NO", "logos/AZ").replace("new-orleans-saints",
                                                                "arizona-cardinals")
        rows, _h, flags = ct.parse_rows(page([tr]), 2026, 11, "u")
        self.assertEqual(flags, [])
        self.assertEqual(rows[0]["club_to"], "AZ", "the printed code must survive")
        mapped, aliased = ct.normalise_club("AZ")
        self.assertEqual((mapped, aliased), ("ARI", True))
        self.assertEqual(ct.normalise_club("KC"), ("KC", False))
        self.assertEqual(ct.normalise_club(None), (None, False))

    def test_unknown_club_code_is_flagged(self):
        tr = ROW_MILLER.replace("logos/NO", "logos/XXX")
        _rows, _h, flags = ct.parse_rows(page([tr]), 2026, 11, "u")
        self.assertTrue(any("not one of the 32" in f for f in flags), flags)

    def test_no_club_code_at_all_is_flagged(self):
        tr = ROW_MILLER.replace('<img src="https://static.www.nfl.com/t_q-best/league/api/'
                                'clubs/logos/NO"/><br><br>Saints<br><br>Saints', '')
        _rows, _h, flags = ct.parse_rows(page([tr]), 2026, 11, "u")
        self.assertTrue(any("no club code" in f for f in flags), flags)

    def test_unparseable_date_keeps_the_row_and_flags(self):
        tr = ROW_MILLER.replace("<td>11/14</td>", "<td>Nov 14</td>")
        rows, _h, flags = ct.parse_rows(page([tr]), 2026, 11, "u")
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["date"])
        self.assertTrue(any("unparseable date" in f for f in flags), flags)

    def test_no_tables(self):
        rows, _h, flags = ct.parse_rows("<html><body><p>Ad only</p></body></html>", 2026, 11, "u")
        self.assertEqual(rows, [])
        self.assertTrue(any("no <table>" in f for f in flags), flags)


class HashTest(unittest.TestCase):
    def test_canonical_hash_ignores_order_and_punishes_value_change(self):
        rows, _h, _f = ct.parse_rows(page([ROW_MILLER, ROW_WILLIS]), 2026, 11, "u")
        rev, _h, _f = ct.parse_rows(page([ROW_WILLIS, ROW_MILLER]), 2026, 11, "u")
        self.assertEqual(ct.canonical(rows), ct.canonical(rev))
        changed = [dict(rows[0], transaction="Reserve/Injured - Designated to Return")] + rows[1:]
        self.assertNotEqual(ct.canonical(rows), ct.canonical(changed))

    def test_markup_churn_does_not_change_the_content_hash(self):
        a, _h, _f = ct.parse_rows(page([ROW_MILLER]), 2026, 11, "u")
        b, _h, _f = ct.parse_rows(
            page([ROW_MILLER.replace("<br><br>Saints", " Saints").replace("<br><br>", "")]),
            2026, 11, "u")
        self.assertEqual(ct.canonical(a), ct.canonical(b))


class StateTest(unittest.TestCase):
    def test_open_reserve_and_return(self):
        base = {"date": "2026-11-10", "club_from": "MIA", "club_to": "MIA",
                "player": "Malik Willis", "position_printed": None,
                "transaction": "Reserve/Injured", "source_url": "u", "player_url": None}
        back = dict(base, date="2026-12-05",
                    transaction="Active (from Injured Reserve)")
        st = ct.reserve_state([base])
        self.assertTrue(st["players"]["Malik Willis"]["on_reserve_as_of_capture"])
        self.assertEqual(st["by_club"]["MIA"]["n_on_reserve"], 1)
        st2 = ct.reserve_state([base, back])
        self.assertFalse(st2["players"]["Malik Willis"]["on_reserve_as_of_capture"],
                         "a later activation must close the designation")
        self.assertEqual(st2["by_club"]["MIA"]["n_on_reserve"], 0)

    def test_trade_moves_the_club(self):
        a = {"date": "2026-11-06", "club_from": "AZ", "club_to": "BAL", "player": "Jacoby Brissett",
             "position_printed": None, "transaction": "Traded", "source_url": "u",
             "player_url": None}
        st = ct.reserve_state([a])
        p = st["players"]["Jacoby Brissett"]
        self.assertEqual(p["club"], "BAL")
        self.assertFalse(p["on_reserve_as_of_capture"])
        self.assertEqual(st["by_club"]["BAL"]["players_with_turnover"], 1)


class JoinTest(unittest.TestCase):
    def test_join_counts_and_labels(self):
        state = {"by_club": {"MIA": {"club": "MIA", "n_on_reserve": 2,
                                     "players_on_reserve": [
                                         {"player": "Malik Willis", "opened": "2026-11-10",
                                          "designation": "Reserve/Injured",
                                          "position_printed": None, "source_urls": ["u"]},
                                         {"player": "Zach Sieler", "opened": "2026-11-10",
                                          "designation": "Reserve/Injured",
                                          "position_printed": None, "source_urls": ["u"]}]},
                           "NE": {"club": "NE", "n_on_reserve": 1,
                                  "players_on_reserve": [
                                      {"player": "TreVeyon Henderson", "opened": "2026-11-14",
                                       "designation": "Reserve/Injured", "position_printed": None,
                                       "source_urls": ["u"]}]}}}
        report = {"source_url": "https://www.nfl.com/injuries/", "week": 10, "season": 2026,
                  "rows": [{"team": "NE", "player": "TreVeyon Henderson", "position": "RB"},
                           {"team": "NE", "player": "Drake Maye", "position": "QB"},
                           {"team": "MIA", "player": "Tyreek Hill", "position": "WR"}]}
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "official_injuries.json"
            f.write_text(json.dumps(report), encoding="utf-8")
            old = ct.INJURY_REPORT
            ct.INJURY_REPORT = f
            try:
                out = ct.report_vs_reserve(state)
            finally:
                ct.INJURY_REPORT = old
        self.assertEqual(out["clubs"]["NE"]["named_in_both"], 1,
                         "Henderson is on the report for the game AND on IR two days later")
        self.assertEqual(out["clubs"]["NE"]["on_reserve_not_in_report"], 0)
        self.assertEqual(out["clubs"]["MIA"]["on_reserve_not_in_report"], 2,
                         "Willis and Sieler are unavailable but never appear on the report")
        self.assertEqual(out["clubs"]["MIA"]["unavailable_total_report_plus_reserve"], 3)
        self.assertEqual(out["totals"]["on_reserve_not_in_report"], 2)

    def test_missing_report_is_reported_not_zeroed(self):
        old = ct.INJURY_REPORT
        ct.INJURY_REPORT = old.parent / "definitely-not-here-1d824ec2.json"
        try:
            out = ct.report_vs_reserve({"by_club": {}})
        finally:
            ct.INJURY_REPORT = old
        self.assertIn("error", out)
        self.assertNotIn("totals", out, "no report file means no counts are published")



class StalenessTest(unittest.TestCase):
    """The staleness comparison must not invent a contradiction from a shared name or a move
    that the artifact postdates."""

    @classmethod
    def setUpClass(cls):
        cls.d = importlib.util.spec_from_file_location(
            "check_depth_staleness_1d824ec2",
            ROOT / "tools" / "check_depth_staleness_1d824ec2.py")
        cls.mod = importlib.util.module_from_spec(cls.d)
        sys.modules["check_depth_staleness_1d824ec2"] = cls.mod
        cls.d.loader.exec_module(cls.mod)

    def _row(self, club, player, date, nature="current-roster-claim"):
        return {"club": club, "player": player, "date": date, "where": "Offense/WR s1",
                "source_url": "https://www.packers.com/team/depth-chart", "_nature": nature}

    def _ev(self, date, frm, to, txt, cat="trades"):
        return {"date": date, "club_from": frm, "club_to": to, "transaction": txt,
                "category": cat, "source_url": "https://www.nfl.com/transactions/",
                "player_url": "https://www.nfl.com/players/x/"}

    def test_trade_away_flags_the_old_club_only(self):
        evs = [self._ev("2026-11-10", "IND", "SF", "Traded")]
        f_ind = self.mod.classify(self._row("IND", "Keenan Allen", "2026-11-15"), evs)
        self.assertIsNotNone(f_ind)
        self.assertEqual(f_ind["kind"], "moved away from the club")
        self.assertIn("captured after the move", f_ind["artifact_timing"])
        self.assertIsNone(self.mod.classify(self._row("SF", "Keenan Allen", "2026-11-15"), evs),
                          "the receiving club printing him is correct, not stale")

    def test_artifact_predating_the_move_is_a_refresh_not_a_contradiction(self):
        evs = [self._ev("2026-11-14", "GB", "GB", "Reserve/Injured", cat="reserve-list")]
        f = self.mod.classify(self._row("GB", "Josh Whyle", "2026-11-12"), evs)
        self.assertIsNotNone(f)
        self.assertEqual(f["kind"], "on a reserve list")
        self.assertIn("predates the move", f["artifact_timing"])

    def test_a_later_return_cancels_the_reserve_finding(self):
        evs = [self._ev("2026-11-14", "GB", "GB", "Reserve/Injured", cat="reserve-list"),
               self._ev("2026-12-03", "GB", "GB", "Active - Designated to Return from "
                                              "Injured Reserve", cat="other")]
        self.assertIsNone(self.mod.classify(self._row("GB", "Josh Whyle", "2026-12-05",
                                                       ), evs))

    def test_shared_name_cannot_flag_the_wrong_club(self):
        """Two players, one printed name: only the club the event names is compared."""
        evs = [self._ev("2026-11-09", "NYJ", "DET", "Traded")]
        self.assertIsNotNone(self.mod.classify(self._row("NYJ", "Andre Cisco", "2026-11-15"), evs))
        self.assertIsNone(self.mod.classify(self._row("SEA", "Andre Cisco", "2026-11-15"), evs))

    def test_reader_handles_the_repo_chart_shape(self):
        doc = [{"code": "KC", "unit": "Offense", "pos": "WR", "s1": "Rashee Rice",
                "s2": "Jalen Royals", "s3": "", "s4": "", "retrieved": "2026-11-12"},
               {"code": "GB", "unit": "Offense", "pos": "TE", "s1": "Josh Whyle", "s2": "",
                "s3": "", "s4": "", "retrieved": "2026-11-12"}]
        pairs = self.mod.read_depth_chart(doc)
        self.assertEqual([(p["club"], p["player"]) for p in pairs],
                         [("KC", "Rashee Rice"), ("KC", "Jalen Royals"), ("GB", "Josh Whyle")],
                         "blank columns must not become rows")
        self.assertEqual(pairs[0]["date"], "2026-11-12")

    def test_name_key_normalises_suffixes_and_punctuation(self):
        k = self.mod.name_key
        self.assertEqual(k("Tyrone Tracy Jr."), k("tyrone tracy jr"),
                         "punctuation is normalised, the suffix itself is kept")
        self.assertNotEqual(k("Tyrone Tracy Jr."), k("Tyrone Tracy"),
                            "dropping a suffix to force a match would invent a finding")
        self.assertEqual(k("L'Jarius Sneed"), k("L Jarius Sneed"))
        self.assertNotEqual(k("Chris Johnson"), k("Christian Johnson"))


class InjuryTsvReaderTest(unittest.TestCase):
    def test_reads_the_printed_columns(self):
        import importlib.util as iu
        spec = iu.spec_from_file_location("cs2", ROOT / "tools" / "check_depth_staleness_1d824ec2.py")
        m = iu.module_from_spec(spec)
        sys.modules.setdefault("cs2", m)
        spec.loader.exec_module(m)
        text = ("team_abbr\tplayer\tposition\tinjury\tpractice\tgame_status\tplayer_slug\n"
                "GB\tJosh Whyle\tTE\t\tDNP\t\tjosh-whyle\n"
                "GB\t\t\t\t\t\n")
        pairs = m.read_injury_tsv(text)
        self.assertEqual(len(pairs), 1, "a row with no name is skipped, not invented")
        self.assertEqual((pairs[0]["club"], pairs[0]["player"]), ("GB", "Josh Whyle"))


class WorkflowLintTest(unittest.TestCase):
    """A step name or run line containing ': ' must be quoted or block-scalar.

    The first run of this session's workflow died on the YAML scanner, not on the code: a step
    called `Gate: hashes, pins, ...` is read as a nested mapping. The check is textual on purpose
    - pyyaml is not installed by every job in this repository, and a gate cannot depend on a
    package the job it gates does not install.
    """

    PAT = re.compile(r"^(\s*-?\s*)(name|run|if)\s*:\s+(?![|>&\"])(.*)$")

    def test_no_unquoted_colon_in_workflow_scalars(self):
        bad = []
        for f in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                m = self.PAT.match(line)
                if m and ": " in m.group(3) and not m.group(3).startswith("'"):
                    bad.append(f"{f.name}:{i}: {line.strip()[:90]}")
        self.assertEqual(bad, [], "unquoted scalar containing ': ' breaks the workflow parse:\n"
                         + "\n".join(bad))


if __name__ == "__main__":
    unittest.main(verbosity=2)
