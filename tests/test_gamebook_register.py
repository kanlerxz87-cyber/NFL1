"""Unit tests for the Game Book register: parser, math, pins, determinism, honesty rules.

Session `98a40411-nfl1`, task G6. These run in CI on every push and in the pull-request check, and
they read only files committed to the repository - no network, ever.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tools"))

import collect_gamebooks as cg                      # noqa: E402
import build_gamebook_register as bgr               # noqa: E402


class TestClubVocabulary(unittest.TestCase):
    def test_only_current_clubs_are_emitted(self):
        """The historical franchise rows in teams.csv must not leak: Rams -> LA, Raiders -> LV."""
        self.assertEqual(cg.nick_to_abbr("RAMS"), "LA")
        self.assertEqual(cg.nick_to_abbr("RAIDERS"), "LV")
        self.assertEqual(cg.nick_to_abbr("49ERS"), "SF")
        self.assertEqual(cg.nick_to_abbr("NEW ENGLAND PATRIOTS"), "NE")
        self.assertEqual(cg.nick_to_abbr("ARIZONA CARDINALS"), "ARI")
        self.assertIsNone(cg.nick_to_abbr("MUNICH GAME"))
        self.assertIsNone(cg.nick_to_abbr("SUNDAY NIGHT FOOTBALL"))

    def test_map_is_restricted_to_the_32(self):
        self.assertEqual(len(cg.CURRENT_CLUBS), 32)
        for abbr in set(cg.NICK_ABBR.values()):
            self.assertIn(abbr, cg.CURRENT_CLUBS, f"{abbr} is not a current club")


class TestInactivesParser(unittest.TestCase):
    """Pinned to the committed transcription of the league's own Week 10 article."""

    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "data/gamebook/official_inactives/wk10_2026_article_extract.txt").read_text()
        i = next(k for k, ln in enumerate(cls.raw.splitlines()) if ln.startswith("## MUNICH"))
        cls.text = "\n".join(cls.raw.splitlines()[i:]) + "\n"
        cls.rows, cls.flags = cg.parse_inactives_text(cls.text)

    def test_row_and_club_counts_are_pinned(self):
        self.assertEqual(len(self.rows), 147)
        self.assertEqual(len({r["club"] for r in self.rows}), 24)
        self.assertEqual(self.flags, [])

    def test_patriots_list_matches_the_article_exactly(self):
        ne = sorted(r["name"] for r in self.rows if r["club"] == "NE")
        self.assertEqual(ne, sorted(["Carlton Davis", "Brenden Schooler", "Dametrious Crownover",
                                     "Walter Rouse", "Ben Brown", "Behren Morton"]))

    def test_parenthetical_note_is_separated_from_the_name(self):
        row = [r for r in self.rows if r["club"] == "NE" and "Morton" in r["name"]][0]
        self.assertEqual(row["note"], "emergency third QB")
        self.assertNotIn("(", row["name"])

    def test_position_prefix_is_stripped_into_its_own_field(self):
        row = [r for r in self.rows if r["club"] == "DET" and "Reed" in r["name"]][0]
        self.assertEqual(row["position_raw"], "CB")

    def test_rome_and_suffixed_names_survive(self):
        names = {r["name"] for r in self.rows}
        self.assertIn("Jessie Bates III", names)
        self.assertIn("Thomas Booker IV", names)
        self.assertIn("Keith Abney II", names)

    def test_no_name_is_dropped_silently(self):
        """Every list line in the excerpt must produce a row - a lost row is the failure mode."""
        listed = [ln for ln in self.text.splitlines() if re.match(r"^- ", ln)]
        self.assertEqual(len(listed), len(self.rows))

    def test_empty_club_block_is_a_flag_not_a_skip(self):
        rows, flags = cg.parse_inactives_text("## EARLY GAMES\n### PATRIOTS\n### LIONS\n- CB X Y\n")
        self.assertTrue(any("no inactive names" in f for f in flags), flags)
        self.assertEqual(len(rows), 1)


class TestGameBookText(unittest.TestCase):
    """A verbatim excerpt of the Week 10 Game Book, as printed in the PDF's summary page."""

    EXCERPT = """National Football League Game Summary
Date: Sunday, 11/15/2026 New England Patriots at Detroit Lions at Allianz Arena, Munich, Germany
Referee: Martin, Clay (19)
Lineups
Offense Defense Offense Defense
LT 66 W.Campbell OLB 5 Dr.Jones WR 18 I.TeSlaa DE 97 A.Hutchinson
C 55 J.Wilson DT 97 M.Williams QB 16 J.Goff CB 23 R.Ya-Sin
Substitutions
WR 3 D.Douglas, QB 16 T.DeVito, RB 34 L.Larison, TE 36 C.Latu
Did Not Play
Not Active
CB 7 C.Davis, 3QB 15 B.Morton, S 41 B.Schooler, T 68 D.Crownover, OL 72 W.Rouse, C 77 B.Brown
Field Goals (made ( ) & missed)
Paid Attendance: 70,225
VISITOR: New England Patriots
"""

    def setUp(self):
        self.p = cg.parse_gamebook_text(self.EXCERPT)

    def test_not_active_names_are_parsed(self):
        got = sorted(n["name"] for n in self.p["Not Active"] if not n.get("unparsed"))
        self.assertEqual(got, sorted(["C.Davis", "B.Morton", "B.Schooler", "D.Crownover",
                                      "W.Rouse", "B.Brown"]))

    def test_empty_did_not_play_is_recorded_as_empty_not_absent(self):
        """The page prints 'Did Not Play' with no names under it.

        That is a fact about the game (every dressed player took a snap), not a missing section, and
        not a zero to be summed by a model: the register keeps the empty list, marks the section as
        printed-empty and flags it, so a reader sees which of the two it was.
        """
        self.assertEqual(self.p["Did Not Play"], [])
        self.assertTrue(self.p.get("Did Not Play_printed_empty"))
        self.assertIn("Did Not Play", self.p["sections_found"])
        self.assertTrue(any("printed with no names" in f for f in self.p["flags"]), self.p["flags"])
        self.assertEqual(self.p["parse_status"], "partial")

    def test_venue_and_referee_and_attendance_are_read(self):
        self.assertIn("Allianz Arena", self.p["venue_text"])
        self.assertEqual(self.p["referee"], "Martin, Clay (19)")
        self.assertEqual(self.p["attendance"], "70,225")

    def test_starters_are_attributed_only_when_the_line_splits_four_ways(self):
        """Two printed line-up lines, four columns each: away-offence, away-defence, home-offence,
        home-defence. A line that does not split exactly four ways is not attributed at all."""
        st = self.p.get("starters") or []
        self.assertEqual(len(st), 8)
        self.assertEqual(sorted((s["side"], s["unit"]) for s in st),
                         sorted([("away", "offence"), ("away", "defence"),
                                 ("home", "offence"), ("home", "defence")] * 2))
        self.assertTrue(all(s["surname"] for s in st))
        campbell = [s for s in st if s["surname"] == "Campbell"][0]
        self.assertEqual((campbell["position"], campbell["number"], campbell["initial"]),
                         ("LT", "66", "W"))
        jones = [s for s in st if s["surname"] == "Jones"][0]
        self.assertEqual(jones["initial"], "Dr")   # the document's own way of splitting surnames

    def test_emergency_qb_prefix_does_not_lose_a_row(self):
        """"3QB 15 B.Morton" is one of the eight printed forms that broke an earlier parser."""
        self.assertIn("B.Morton", [n["name"] for n in self.p["Not Active"]])

    def test_excerpt_hash_is_stored_for_audit(self):
        self.assertIn("Not Active", self.p["excerpt_sha"])
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", self.p["excerpt_sha"]["Not Active"]))

    def test_empty_text_is_a_failure_not_a_zero(self):
        p = cg.parse_gamebook_text("")
        self.assertEqual(p["parse_status"], "failed")


class TestStatistics(unittest.TestCase):
    def test_wilson_matches_the_published_construction(self):
        # k=15, n=82 is the Week 10 Questionable cell: check the endpoints, not just the shape
        lo, hi = bgr.wilson(15, 82)
        self.assertAlmostEqual(lo, 0.1141, places=3)
        self.assertAlmostEqual(hi, 0.2801, places=3)

    def test_zero_n_is_blank_never_zero(self):
        self.assertIsNone(bgr.wilson(0, 0))

    def test_interval_brackets_the_point(self):
        for k, n in ((1, 1), (1, 2), (48, 64), (7, 9), (0, 5), (5, 5)):
            lo, hi = bgr.wilson(k, n)
            self.assertLessEqual(lo, k / n)
            self.assertGreaterEqual(hi, k / n)
            self.assertGreaterEqual(lo, 0.0)
            self.assertLessEqual(hi, 1.0)

    def test_name_matching_is_conservative(self):
        self.assertEqual(bgr.name_key("Amon-Ra St. Brown"), "amon ra st brown")
        self.assertEqual(bgr.gamebook_token("Micah Parsons"), "M.Parsons")
        self.assertEqual(bgr.gamebook_token("TreVeyon Henderson"), "T.Henderson")
        self.assertEqual(bgr.gamebook_token(""), "")

    def test_a_different_first_name_is_not_a_match(self):
        self.assertNotEqual(bgr.name_key("Sam Darnold"), bgr.name_key("Sam Barber"))
        self.assertNotEqual(bgr.gamebook_token("Sam Darnold"), bgr.gamebook_token("Sam Barber"))


class TestRegisterBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = bgr.build(write_site=False)

    def test_week10_is_joined_and_the_counts_are_pinned(self):
        self.assertIn("2026_reg10", self.d["weeks"])
        cov = [c for c in self.d["coverage"] if c["season"] == 2026 and c["week"] == 10][0]
        self.assertEqual(cov["inactive_rows"], 147)
        self.assertEqual(cov["inactive_clubs"], 24)
        self.assertEqual(cov["report_clubs"], 28)
        self.assertEqual(cov["clubs_in_both"], 24)
        # four clubs play outside the article's Sunday round: the Thursday game and the Monday game
        self.assertEqual(cov["clubs_report_only"], ["BAL", "LAC", "NYG", "WAS"])

    def test_every_ledger_row_carries_an_official_link(self):
        led = json.loads((ROOT / "data/gamebook/derived/ledger.json").read_text())["rows"]
        self.assertGreater(len(led), 400)
        for r in led:
            link = r["inactive_url"] or r["report_url"]
            self.assertTrue(link and link.startswith("https://www.nfl.com/"), r)

    def test_designations_are_consistent_with_the_join(self):
        rows = {r["designation"]: r for r in self.d["designations"]}
        self.assertEqual(rows["Questionable"]["n"], 82)
        self.assertEqual(rows["Out"]["n"] + rows["Questionable"]["n"] + rows["Doubtful"]["n"], 156)
        for d, r in rows.items():
            self.assertAlmostEqual(r["declared_inactive_rate"], r["declared_inactive"] / r["n"],
                                   msg=d)

    def test_play_rate_stays_blank_until_a_game_book_exists(self):
        """Measure B may never be filled from measure A. This is the honesty test for the register."""
        if self.d["game_books_captured"] == 0:
            for r in self.d["designations"]:
                self.assertIsNone(r["play_rate"], r)
                self.assertEqual(r["game_book_n"], 0)

    def test_unjoinable_rows_are_never_read_as_available(self):
        led = json.loads((ROOT / "data/gamebook/derived/ledger.json").read_text())["rows"]
        no_src = [r for r in led if r["inactive_state"] == "no_inactive_source"]
        self.assertTrue(no_src)
        self.assertEqual({r["club"] for r in no_src}, {"BAL", "LAC", "NYG", "WAS"})

    def test_healthy_scratches_are_counted(self):
        self.assertGreater(self.d["trap_counts"]["inactives_with_no_report_row"], 50)

    def test_determinism_two_builds_are_identical(self):
        a = bgr.build(write_site=False)
        b = bgr.build(write_site=False)
        for k in ("coverage", "designations", "trap_counts", "results", "crosscheck"):
            self.assertEqual(json.dumps(a[k], sort_keys=True), json.dumps(b[k], sort_keys=True), k)

    def test_gate_accepts_a_wellformed_gamebook_capture_and_rejects_a_broken_one(self):
        """The gate must read the game-book capture shape as it is actually written (no `rows`, no
        `url`, no season/week) and still fail a capture with a blank field or a non-UTC stamp."""
        import shutil
        import tempfile
        fx = ROOT / "tests" / "fixtures" / "gamebook"
        with tempfile.TemporaryDirectory() as td:
            good = Path(td) / "captures" / "gamebook"
            good.mkdir(parents=True)
            shutil.copy(fx / "gamebook_capture_good.json", good / "patriots-at-lions-2026-reg-10.json")
            r = subprocess.run([sys.executable, str(ROOT / "tools/check_gamebook_register.py"),
                                "--captures-root", td], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("1 capture(s)", r.stdout)
            shutil.copy(fx / "gamebook_capture_bad.json", good / "bad.json")
            r2 = subprocess.run([sys.executable, str(ROOT / "tools/check_gamebook_register.py"),
                                 "--captures-root", td], capture_output=True, text=True)
            self.assertEqual(r2.returncode, 1, r2.stdout)
            out = r2.stdout
            self.assertIn("parser_version", out)
            self.assertIn("is not a UTC timestamp", out)

    def test_sweep_workflow_is_structured_to_report_what_it_read(self):
        """The first CI sweep failed its gate while writing nothing, and the log was not readable
        from the sandbox. The workflow must therefore (a) refuse to run without the modules its
        collector imports, (b) capture each sweep's stderr, and (c) commit a log file beside the
        captures, so a red run states what it actually read instead of being a red tick."""
        wf = (ROOT / ".github/workflows/gamebook-sweep.yml").read_text()
        self.assertIn("Refuse to run blind", wf)
        self.assertIn('want = ["requests", "bs4", "lxml", "pypdf"]', wf)
        self.assertIn("data/gamebook/sweep-log.txt", wf)
        self.assertIn("2>&1 | tee /tmp/books.log", wf)
        self.assertIn("tee /tmp/gate.txt", wf)          # the gate's own output must be published
        self.assertIn("GITHUB_STEP_SUMMARY", wf)
        try:
            import yaml                                            # noqa: PLC0415
        except Exception:                                          # noqa: BLE001
            self.skipTest("pyyaml is not installed in this environment")
        doc = yaml.safe_load(wf)
        steps = doc["jobs"]["sweep"]["steps"]
        names = [st.get("name", "") for st in steps]
        self.assertGreaterEqual(len(steps), 12)
        # the gate must run even when a sweep step failed, and the commit must still be reached
        self.assertIn("always()", [st.get("if", "") for st in steps if "Gate" in st.get("name", "")])
        commit = [st for st in steps if "Commit the captures" in st.get("name", "")][0]
        self.assertEqual(commit.get("if"), "always()")
        self.assertIn("git add data/gamebook gamebook", commit["run"])
        self.assertIn("--rebase", commit["run"])                   # small frequent commits protocol
        self.assertTrue(any("unittest tests.test_gamebook_register" in st.get("run", "")
                            for st in steps), names)

    def test_clamped_captures_are_never_joined_and_one_capture_wins_a_week(self):
        """The league serves its most recent report for any week without one of its own (F73), and a
        truncated render of the same page can hold the right rows under the wrong club headings (F74).
        Both traps are closed by construction: a clamped capture is skipped, and a week is joined from
        exactly one capture - the one stating the most clubs."""
        cands = bgr._report_candidates()
        keys = [k for k, _ in cands if k != "_unreadable"]
        self.assertTrue(keys, "no usable report capture on disk")
        for _k, cap in cands:
            self.assertFalse(cap.get("week_clamped"),
                             "a clamped capture reached the join")
        per_week = {}
        for k in keys:
            per_week[k] = per_week.get(k, 0) + 1
        # several candidates may exist for one week (that is the point of the selection); what must
        # hold is that the register records how many it *rejected*, and that its chosen source is one
        # of the candidates rather than a merge of them
        d = bgr.build(write_site=False)
        for k, n in per_week.items():
            chosen = d.get("report_selection", {}).get(k)
            self.assertTrue(chosen, f"{k}: no chosen capture recorded")
            files = [c.get("_file") for kk, c in cands if kk == k]
            self.assertIn(chosen, files, f"{k}: chosen capture {chosen} is not a candidate")
        glob_n = len(list((ROOT / "data/gamebook/captures/report").glob("*.json")))
        import json as _json
        n_clamped_here = sum(1 for f in (ROOT / "data/gamebook/captures/report").glob("*.json")
                             if _json.loads(f.read_text()).get("week_clamped"))
        self.assertEqual(d["report_captures_clamped"], n_clamped_here)
        self.assertGreaterEqual(n_clamped_here, 20, "the archive probe is what this row is about")
        # arithmetic that must hold: candidates = unclamped glob files + the committed CI file
        committed = 1 if (ROOT / "data/model/official_injuries.json").exists() else 0
        self.assertEqual(len(keys) + d["report_captures_clamped"], glob_n + committed)
        # the published cell must not move when a thinner capture of the same page exists
        rows = {r["designation"]: r for r in d["designations"]}
        self.assertEqual((rows["Questionable"]["n"], rows["Out"]["n"], rows["Doubtful"]["n"]),
                         (82, 64, 10))
        cov = [c for c in d["coverage"] if c["season"] == 2026 and c["week"] == 10][0]
        self.assertGreaterEqual(cov["report_captures_ignored"], 1)

    def test_gate_passes_on_the_committed_artifacts(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools/check_gamebook_register.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 failure(s)", r.stdout)


class TestCollectorOfflineSafety(unittest.TestCase):
    def test_derive_and_verify_need_no_network(self):
        """`verify` is the pull-request check, so it must not reach out."""
        src = (ROOT / "pipeline/collect_gamebooks.py").read_text()
        i = src.index("def cmd_verify")
        j = src.index("def main(")
        self.assertNotIn("http_get", src[i:j])
        self.assertNotIn("requests", src[i:j])

    def test_fetch_failure_records_an_alert_instead_of_a_blank(self):
        src = (ROOT / "pipeline/collect_gamebooks.py").read_text()
        self.assertIn('"alert": "fetch_failed"', src)
        self.assertIn('"alert": "centre_fetch_failed"', src)

    def test_report_capture_declares_its_point_in_time_limit(self):
        src = (ROOT / "pipeline/collect_gamebooks.py").read_text()
        self.assertIn("point_in_time", src)
        self.assertIn("retrospective calibration only", src)


class TestSiteIntegrity(unittest.TestCase):
    PAGES = ["index.html", "ledger.html", "designations.html", "results.html",
             "crosscheck.html", "starters.html", "summary.html", "method.html"]

    def test_summary_is_computed_not_typed(self):
        """Every row on the executive-summary page must come from a committed file."""
        rows = bgr.summary_numbers(self.d) if hasattr(self, "d") else bgr.summary_numbers(
            json.loads((ROOT / "data/gamebook/register.json").read_text()))
        self.assertGreaterEqual(len(rows), 12)
        for r in rows:
            self.assertTrue(r["files"], r["what"])
            self.assertIn(r["area"], {"Availability", "Calibration", "Trap", "Corpus",
                                      "Governance", "Site", "Review"})
        txt = (ROOT / "gamebook" / "summary.html").read_text()
        # the blank-not-zero rule: the play-rate row must not report a rate it cannot source
        play = [r for r in rows if r["what"].startswith("Play rate")][0]
        if json.loads((ROOT / "data/gamebook/register.json").read_text())["game_books_captured"] == 0:
            self.assertNotIn("%", str(play["value"]))
        # the per-row rule, not a page-wide average: no row may reach the table without a link
        # to an official page, whatever else it links to
        body = txt[txt.index("<tbody>"):]
        trs = re.findall(r"<tr>.*?</tr>", body, re.S)
        self.assertEqual(len(trs), len(rows), "table row count does not match the computed row count")
        for n, tr in enumerate(trs):
            self.assertTrue(re.search(r'href="https://([a-z0-9]+\.)*nfl\.com', tr),
                            f"summary row {n} has no official link")

    def test_all_pages_exist_and_link_to_official_sources(self):
        for name in self.PAGES:
            p = ROOT / "gamebook" / name
            self.assertTrue(p.exists(), name)
            txt = p.read_text()
            self.assertIn("nfl.com", txt, f"{name} cites no official source")
            self.assertIn('<a href="../index.html"', txt, f"{name} is not reachable from the landing page")

    def test_no_local_link_is_broken(self):
        for name in self.PAGES:
            txt = (ROOT / "gamebook" / name).read_text()
            for h in re.findall(r'href="([^"#]+)"', txt):
                if h.startswith(("http", "mailto:")):
                    continue
                self.assertTrue((ROOT / "gamebook" / h).resolve().exists(), f"{name} -> {h}")

    def test_pages_do_not_claim_a_snap_share(self):
        """The brief forbids deriving snaps or depth rank from a Game Book; the site must not imply it."""
        for name in self.PAGES:
            txt = (ROOT / "gamebook" / name).read_text()
            for m in re.finditer(r"[^.]*(snap share|share of snaps|snap count)[^.]*\.", txt):
                seg = m.group(0)
                self.assertRegex(seg, r"never|not |no |forbid|without|until",
                                 f"{name} asserts a forbidden measure: {seg[:120]}")


if __name__ == "__main__":
    unittest.main()
