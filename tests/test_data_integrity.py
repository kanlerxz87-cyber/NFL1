import sys, pathlib, unittest, json
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nfl import ingest, verify, ratings, availability, signals, luck


class TestIngest(unittest.TestCase):
    def test_thirty_two_standings_rows(self):
        self.assertEqual(len(ingest.standings()), 32)

    def test_fourteen_week_ten_games(self):
        self.assertEqual(len(ingest.schedule()), 14)

    def test_four_byes(self):
        self.assertEqual(len(ingest.byes()), 4)

    def test_254_injury_entries(self):
        self.assertEqual(len(ingest.injuries()), 254)

    def test_no_inferred_injury_designation(self):
        # A blank injury cell must stay None. If anything ever fills it in from a
        # player name or a news headline, this test fails.
        blanks = [e for e in ingest.injuries() if e["injury"] is None]
        self.assertGreater(len(blanks), 200)
        for e in blanks:
            self.assertIsNone(e["injury"])

    def test_no_inferred_game_status(self):
        for e in ingest.injuries():
            self.assertIn(e["game_status"], (None, "Out", "Doubtful", "Questionable"))

    def test_practice_codes_expand_to_official_labels(self):
        self.assertEqual(ingest.PRACTICE_LABELS["DNP"], "Did Not Participate In Practice")
        for e in ingest.injuries():
            if e["practice_code"]:
                self.assertEqual(e["practice_label"],
                                 ingest.PRACTICE_LABELS[e["practice_code"]])

    def test_every_row_has_a_source_url(self):
        registered = {s["url"] for s in ingest.sources()["sources"]}
        for e in ingest.injuries():
            self.assertEqual(e["source_url"], ingest.INJURY_REPORT_URL)
            self.assertIn(e["source_url"], registered)
            self.assertTrue(e["player_url"].startswith("https://www.nfl.com/players/"))
        for r in ingest.standings():
            self.assertEqual(r["source_url"], ingest.STANDINGS_URL)
            self.assertIn(r["source_url"], registered)
        for r in ingest.schedule():
            self.assertEqual(r["source_url"], ingest.WEEK10_SCHEDULE_URL)
            self.assertEqual(r["source_urls"],
                             [ingest.WEEK10_SCHEDULE_URL, ingest.INJURY_REPORT_URL])
            self.assertTrue(set(r["source_urls"]) <= registered)
        for r in ingest.byes():
            self.assertEqual(r["source_url"], ingest.WEEK10_SCHEDULE_URL)
            self.assertIn(r["source_url"], registered)
        for r in ingest.team_report_status():
            expected_sources = ([ingest.INJURY_REPORT_URL, ingest.WEEK10_SCHEDULE_URL]
                                if r["report_status"] == "on bye (no report)"
                                else [ingest.INJURY_REPORT_URL])
            self.assertEqual(r["source_urls"], expected_sources)
            self.assertEqual(r["source_url"], expected_sources[-1])
            self.assertTrue(set(expected_sources) <= registered)
        for r in ingest.news():
            self.assertTrue(r["url"].startswith("https://www.nfl.com/news/"))
            self.assertIn(r["url"], registered)
        for r in ingest.teams_reference():
            self.assertEqual(r["source_url"], ingest.TEAM_REF_URL)
            self.assertIn(r["source_url"], registered)

    def test_official_schedule_supplies_fixtures_and_the_bye_list(self):
        self.assertEqual({r["team_abbr"] for r in ingest.byes()},
                         {"CHI", "DEN", "PHI", "TB"})
        self.assertEqual(len(ingest.schedule()), 14)
        source = next(s for s in ingest.sources()["sources"]
                      if s["url"] == ingest.WEEK10_SCHEDULE_URL)
        self.assertEqual(source["tier"], "OFFICIAL")
        uses = " ".join(source["used_for"])
        self.assertIn("schedule_2026_week10.tsv", uses)
        self.assertIn("bye_week10.tsv", uses)
        injury_source = next(s for s in ingest.sources()["sources"]
                             if s["url"] == ingest.INJURY_REPORT_URL)
        self.assertIn("broadcast metadata", " ".join(injury_source["used_for"]))

    def test_schedule_fixture_snapshot_matches_official_nfl_schedule(self):
        c = next(x for x in verify.run()["checks"] if x["check_id"] == "V33")
        self.assertEqual(c["result"], "PASS", c["actual"])
        self.assertEqual(c["actual"], [])
        self.assertEqual(c["source_url"], ingest.WEEK10_SCHEDULE_URL)


class TestVerification(unittest.TestCase):
    def setUp(self):
        self.r = verify.run()

    def test_no_failures(self):
        fails = [c for c in self.r["checks"] if c["result"] == "FAIL"]
        self.assertEqual(fails, [], f"verification FAILs: {fails}")

    def test_league_totals_balance(self):
        self.assertEqual(self.r["team_games"] % 2, 0)
        self.assertEqual(self.r["league_wins"], self.r["league_losses"])

    def test_136_completed_games(self):
        self.assertEqual(self.r["completed_games"], 136)

    def test_disputed_cells_are_flagged_not_silently_fixed(self):
        fields = {(f["team_abbr"], f["field"]) for f in self.r["flags"]}
        self.assertEqual(fields, {("IND", "div"), ("PHI", "div"), ("WAS", "non_conf")})

    def test_cross_source_record_agreement(self):
        c = next(x for x in self.r["checks"] if x["check_id"] == "V28")
        self.assertEqual(c["result"], "PASS")
        self.assertEqual(len(verify.INJURY_PAGE_RECORDS), 28)

    def test_schedule_checks_link_to_the_official_nfl_schedule(self):
        for check_id in ("V14", "V15", "V16", "V17", "V18", "V29", "V33"):
            c = next(x for x in self.r["checks"] if x["check_id"] == check_id)
            self.assertEqual(c["source_url"], ingest.WEEK10_SCHEDULE_URL)

    def test_schedule_duplicate_team_check_reports_duplicate_codes(self):
        c = next(x for x in self.r["checks"] if x["check_id"] == "V18")
        self.assertEqual(c["expected"], [])
        self.assertEqual(c["actual"], [])
        self.assertEqual(c["result"], "PASS")

    def test_byes_are_checked_against_the_official_schedule_snapshot(self):
        c = next(x for x in self.r["checks"] if x["check_id"] == "V29")
        self.assertEqual(c["result"], "PASS")
        self.assertEqual(c["expected"], ["CHI", "DEN", "PHI", "TB"])
        self.assertEqual(c["actual"], ["CHI", "DEN", "PHI", "TB"])

    def test_provenance_check_covers_all_registered_source_rows(self):
        c = next(x for x in self.r["checks"] if x["check_id"] == "V30")
        self.assertEqual(c["result"], "PASS")
        self.assertEqual(c["actual"], [])

    def test_every_check_names_registered_https_sources(self):
        registered = {s["url"] for s in ingest.sources()["sources"]}
        for c in self.r["checks"]:
            urls = c.get("source_urls") or [c["source_url"]]
            self.assertTrue(urls)
            for url in urls:
                self.assertTrue(url.startswith("https://"))
                self.assertIn(url, registered)


class TestDerived(unittest.TestCase):
    def setUp(self):
        self.b = ratings.build()

    def test_pythagorean_fit_is_fitted_not_imported(self):
        pf = self.b["pythagorean_fit"]
        self.assertEqual(pf["status"], "FITTED")
        self.assertEqual(pf["n"], 32)
        self.assertLess(pf["ci95"][0], pf["exponent"])
        self.assertGreater(pf["ci95"][1], pf["exponent"])

    def test_home_advantage_points_is_blank(self):
        hap = self.b["home_advantage_points"]
        self.assertIsNone(hap["value"])
        self.assertEqual(hap["tier"], "UNAVAILABLE")
        self.assertTrue(hap["resolving_source"])

    def test_home_win_rate_is_computable_and_near_half(self):
        ha = self.b["home_advantage_win_rate"]
        self.assertEqual(ha["home_games"], 136)
        self.assertTrue(0.40 < ha["home_win_rate"] < 0.60)

    def test_disputed_division_record_is_excluded(self):
        m = {r["team_abbr"]: r for r in self.b["metrics"]}
        self.assertIsNone(m["IND"]["div_win_pct"])
        self.assertIsNone(m["PHI"]["div_win_pct"])
        self.assertIsNotNone(m["BUF"]["div_win_pct"])

    def test_no_spread_is_ever_published(self):
        for g in self.b["week10_board"]:
            self.assertIsNone(g["spread"])
            self.assertIsNone(g["win_probability"])
            self.assertIsNone(g["market_line"])
            self.assertEqual(g["spread_blocked_by"], "home_advantage_points")

    def test_rating_gap_is_arithmetic_on_verified_cells(self):
        m = {r["team_abbr"]: r for r in self.b["metrics"]}
        for g in self.b["week10_board"]:
            self.assertAlmostEqual(g["rating_gap_home_minus_away"],
                                   round(m[g["home_abbr"]]["net_pg"] - m[g["away_abbr"]]["net_pg"], 3))


class TestAvailability(unittest.TestCase):
    def setUp(self):
        self.a = availability.build()

    def test_bye_teams_have_no_availability_values(self):
        t = {r["team_abbr"]: r for r in self.a["teams"]}
        for team in ("CHI", "DEN", "PHI", "TB"):
            self.assertEqual(t[team]["report_status"], "on bye (no report)")
            self.assertEqual(t[team]["source_url"], ingest.WEEK10_SCHEDULE_URL)
            self.assertEqual(t[team]["source_urls"],
                             [ingest.INJURY_REPORT_URL, ingest.WEEK10_SCHEDULE_URL])

    def test_no_injuries_reported_is_distinct_from_bye(self):
        t = {r["team_abbr"]: r for r in self.a["teams"]}
        for team in ("SEA", "CIN", "LAC", "BAL"):
            self.assertEqual(t[team]["report_status"], "no injuries reported")
            self.assertEqual(t[team]["entries"], 0)

    def test_depth_chart_is_unavailable_not_guessed(self):
        self.assertEqual(self.a["depth_chart_status"]["tier"], "UNAVAILABLE")
        self.assertIsNone(self.a["depth_chart_status"]["value"])
        self.assertIn("sportradar", self.a["depth_chart_status"]["resolving_source"].lower())

    def test_index_is_labelled_modeled(self):
        for r in self.a["teams"]:
            self.assertEqual(r["availability_pressure_tier"], "MODELED")

    def test_qb_facts_carry_official_urls(self):
        self.assertGreaterEqual(len(self.a["qb_and_key_availability"]), 8)
        for k in self.a["qb_and_key_availability"]:
            self.assertTrue(k["url"].startswith("https://www.nfl.com/"))
            self.assertEqual(k["tier"], "VERIFIED")

    def test_designation_coverage_is_reported(self):
        lg = self.a["league"]
        self.assertEqual(lg["injury_designation_present"] + lg["injury_designation_blank"],
                         lg["total_report_entries"])


class TestLuck(unittest.TestCase):
    def test_luck_table_covers_every_team_with_a_record(self):
        t = luck.pythagorean_luck_table(ratings.build()["metrics"])
        self.assertEqual(len(t), 32)

    def test_sign_convention(self):
        t = {r["team_abbr"]: r for r in
             luck.pythagorean_luck_table(ratings.build()["metrics"])}
        for r in t.values():
            if r["pyth_delta"] > 0:
                self.assertIn("UNLUCKY", r["direction"])
            elif r["pyth_delta"] < 0:
                self.assertIn("LUCKY", r["direction"])

    def test_instruments_refuse_to_run_without_data(self):
        self.assertEqual(luck.bootstrap_roi([0.1] * 5)["status"], "NOT_RUN")
        self.assertEqual(luck.permutation_placebo([0.1] * 5, 0.1, lambda x: 0)["status"], "NOT_RUN")
        self.assertEqual(luck.skill_vs_luck_variance([0.1] * 5)["status"], "NOT_RUN")
        self.assertEqual(luck.clv_report([])["status"], "NOT_RUN")

    def test_instruments_run_when_data_exists(self):
        rets = [0.9, -1.0] * 30
        self.assertEqual(luck.bootstrap_roi(rets)["status"], "RUN")
        self.assertEqual(luck.permutation_placebo(rets, 0.0, lambda x: sum(x) / len(x))["status"], "RUN")
        self.assertEqual(luck.clv_report([(3.0, 3.4)] * 20)["status"], "RUN")


if __name__ == "__main__":
    unittest.main()
