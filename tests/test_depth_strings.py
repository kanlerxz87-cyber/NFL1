import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "analysis"))
import depth_strings  # noqa: E402


def chain(team="NE", unit="Defense", slot=1, position="CB",
          slot_name="Left Cornerback", names=("Carlton Davis III", "Charles Woods",
                                              "Marcus Jones", "A.J. Finley")):
    return {
        "team": team, "unit": unit, "slot": slot, "position": position,
        "slot_name": slot_name,
        "players": [{"name": n, "rank": i + 1} for i, n in enumerate(names)],
    }


def status(team, name, game=None, practice=None, source="https://www.nfl.com/players/x/"):
    return (team, depth_strings.norm_name(name)), {
        "game_status": game, "practice_status": practice, "source": source}


class TestDepthStrings(unittest.TestCase):
    def test_name_normalisation_matches_punctuation_variants(self):
        self.assertEqual(depth_strings.norm_name("D.J. Reed"), "dj reed")
        self.assertEqual(depth_strings.norm_name("dj  reed"), "dj reed")
        self.assertEqual(depth_strings.norm_name(None), "")

    def test_healthy_starter_is_first_string(self):
        rows = depth_strings.build_depth_strings([chain()], {})
        self.assertEqual(rows[0]["projected_string"], 1)
        self.assertEqual(rows[0]["projected_string_label"], "1st string (starter not Out)")
        self.assertFalse(rows[0]["starter_unavailable"])
        self.assertTrue(rows[0]["starter_listed"])
        # The next man up is the player who would take over: the second string.
        self.assertEqual(rows[0]["next_man_up"], "Charles Woods")

    def test_out_starter_promotes_the_second_string(self):
        st = dict([status("NE", "Carlton Davis III", game="Out")])
        rows = depth_strings.build_depth_strings([chain()], st)
        r = rows[0]
        self.assertEqual(r["projected_string"], 2)
        self.assertEqual(r["projected_string_label"], "2nd string (starter out)")
        self.assertEqual(r["next_man_up"], "Marcus Jones")
        self.assertEqual(r["out_ranks"], [1])
        self.assertTrue(r["starter_unavailable"])

    def test_two_out_pushes_the_club_to_the_third_string(self):
        st = dict([status("NE", "Carlton Davis III", game="Out"),
                   status("NE", "Charles Woods", game="Out")])
        r = depth_strings.build_depth_strings([chain()], st)[0]
        self.assertEqual(r["projected_string"], 3)
        self.assertEqual(r["projected_string_label"], "3rd string (two down)")
        self.assertEqual(r["next_man_up"], "A.J. Finley")

    def test_three_out_reaches_the_fourth_string(self):
        st = dict([status("NE", "Carlton Davis III", game="Out"),
                   status("NE", "Charles Woods", game="Out"),
                   status("NE", "Marcus Jones", game="Out")])
        r = depth_strings.build_depth_strings([chain()], st)[0]
        self.assertEqual(r["projected_string"], 4)
        self.assertEqual(r["projected_string_label"], "4th string (three down)")
        self.assertIsNone(r["next_man_up"])  # no fifth string is invented

    def test_questionable_starter_still_projects_to_play(self):
        st = dict([status("NE", "Carlton Davis III", game="Questionable")])
        r = depth_strings.build_depth_strings([chain()], st)[0]
        self.assertEqual(r["projected_string"], 1)
        self.assertEqual(r["string_if_doubtful_sits"], 2)
        self.assertEqual(r["uncertain_ranks"], [1])

    def test_practice_status_is_not_an_out(self):
        st = dict([status("NE", "Carlton Davis III", practice="Did Not Participate In Practice")])
        r = depth_strings.build_depth_strings([chain()], st)[0]
        self.assertEqual(r["projected_string"], 1)
        self.assertEqual(r["starter_designation"], "Did Not Participate In Practice")

    def test_no_designation_is_never_turned_into_a_status(self):
        r = depth_strings.build_depth_strings([chain()], {})[0]
        self.assertIsNone(r["starter_designation"])
        for c in r["chain"]:
            self.assertIsNone(c["game_status"])
            self.assertIsNone(c["practice_status"])

    def test_every_row_carries_the_official_source(self):
        r = depth_strings.build_depth_strings([chain()], {})[0]
        self.assertEqual(r["source"], "https://www.nfl.com/injuries/")
        self.assertEqual(r["chain"][0]["player_source"], None)

    def test_only_the_first_four_strings_are_published(self):
        ch = chain(names=("A", "B", "C", "D", "E", "F"))
        r = depth_strings.build_depth_strings([ch], {})[0]
        self.assertEqual(r["strings_published"], 4)
        self.assertEqual([c["rank"] for c in r["chain"]], [1, 2, 3, 4])

    def test_club_summary_counts_offence_and_defence_separately(self):
        chains = [
            chain(team="NE", unit="Defense", slot=1, names=("A", "B", "C", "D")),
            chain(team="NE", unit="Offense", slot=1, position="WR",
                  slot_name="Wide Receiver", names=("W1", "W2", "W3", "W4")),
            chain(team="BUF", unit="Defense", slot=1, names=("X", "Y", "Z", "Q")),
        ]
        st = dict([status("NE", "A", game="Out"), status("NE", "W1", game="Out")])
        summary = depth_strings.summarise_by_club(
            depth_strings.build_depth_strings(chains, st))
        ne = [c for c in summary if c["team"] == "NE"][0]
        self.assertEqual(ne["positions_tracked"], 2)
        self.assertEqual(ne["defensive_positions_starter_unavailable"], 1)
        self.assertEqual(ne["offensive_positions_starter_unavailable"], 1)
        self.assertEqual(ne["positions_down_to_2nd"], 2)
        buf = [c for c in summary if c["team"] == "BUF"][0]
        self.assertEqual(buf["positions_starter_unavailable"], 0)

    def test_empty_chain_is_skipped(self):
        self.assertEqual(depth_strings.build_depth_strings([chain(names=())], {}), [])

    def test_missing_rank_one_is_reported_not_inferred(self):
        # A chart that starts at rank 2 must not call the rank-2 player "the starter"
        # and must not claim the starter is out.
        ch = chain(names=("Second CB", "Third CB", "Fourth CB"))
        ch["players"] = [{"name": "Second CB", "rank": 2},
                         {"name": "Third CB", "rank": 3},
                         {"name": "Fourth CB", "rank": 4}]
        r = depth_strings.build_depth_strings([ch], {})[0]
        self.assertIsNone(r["starter"])
        self.assertFalse(r["starter_listed"])
        self.assertFalse(r["starter_unavailable"])
        self.assertEqual(r["projected_string"], 2)
        self.assertIn("rank 1 not listed", r["projected_string_label"])
        self.assertNotIn("starter out", r["projected_string_label"])

    def test_projected_string_skips_a_missing_rank(self):
        # rank 1 Out, rank 2 absent from the chart -> the answer is rank 3, and the
        # label must say rank 2 is missing rather than pretend two players are out.
        ch = chain(names=("A", "B", "C", "D"))
        ch["players"] = [{"name": "A", "rank": 1}, {"name": "C", "rank": 3},
                         {"name": "D", "rank": 4}]
        st = dict([status("NE", "A", game="Out")])
        r = depth_strings.build_depth_strings([ch], st)[0]
        self.assertEqual(r["projected_string"], 3)
        self.assertEqual(r["out_ranks"], [1])
        self.assertIn("rank 2 not listed", r["projected_string_label"])
        self.assertNotIn("two down", r["projected_string_label"])

    def test_doubtful_starter_label_uses_certain_view(self):
        st = dict([status("NE", "Carlton Davis III", game="Doubtful")])
        r = depth_strings.build_depth_strings([chain()], st)[0]
        self.assertEqual(r["projected_string_label"], "1st string (starter not Out)")
        self.assertEqual(r["string_if_doubtful_sits_label"], "2nd string (1 listed unavailable)")


if __name__ == "__main__":
    unittest.main()
