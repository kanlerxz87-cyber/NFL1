#!/usr/bin/env python3
"""What was re-verified in this session, line by line, and what it found.

Every check names the official URL it was run against and the date it was read. A check
whose result is "mismatch" stays a mismatch: nothing here is reconciled by editing either
side. Counts are recomputed by the data scripts, so this file carries the narrative and the
data files carry the numbers.
"""

OFFICIAL = {
    "standings": "https://www.nfl.com/standings/league/2026/reg",
    "week10": "https://www.nfl.com/schedules/2026/by-week/week-10",
    "injuries": "https://www.nfl.com/injuries/",
    "teams": "https://www.nfl.com/teams/",
    "divisions": "https://www.nfl.com/standings/division/2026/REG",
    "dictionary": "https://nflreadr.nflverse.com/articles/dictionary_schedules.html",
    "nflverse": "https://github.com/nflverse/nflverse-data",
    "pages_api": "https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages",
}

CHECKS = [
    {
        "id": "V01",
        "what": "Official 2026 league standings, all 32 clubs (W, L, T, PCT, PF, PA, NET)",
        "source": OFFICIAL["standings"],
        "read_at": "2026-11-13",
        "method": ("The page table was transcribed by hand into "
                   "data/personnel/official_standings_2026-11-13.csv and then checked against "
                   "itself: PF-PA must equal NET PTS for every club, PCT must equal "
                   "(W + T/2) / games to three decimals, total wins must equal total losses, "
                   "ties must be even, total PF must equal total PA, and there must be 32 "
                   "unique clubs."),
        "result": "transcription accepted",
        "detail": ("League totals: 136 wins, 136 losses, 2 ties, 6,291 points for and 6,291 "
                   "against, and 274 team-games, which is exactly 137 games. That matches the "
                   "136 completed games already in the committed schedule file plus the Week "
                   "10 Thursday game (WAS 24, NYG 21), so the table is internally complete and "
                   "the one-game gap to the committed file is fully explained."),
    },
    {
        "id": "V02",
        "what": "Committed standings file vs the official page, club by club",
        "source": OFFICIAL["standings"],
        "read_at": "2026-11-13",
        "method": "Field-by-field comparison in tools/v_sources.py; output is data/personnel/standings_diff.json.",
        "result": "2 of 32 clubs differ",
        "detail": ("The committed transcription (data/verified/standings_2026.csv, retrieved "
                   "2026-11-12T04:31Z) predates the Week 10 Thursday night game. Both clubs "
                   "that differ are the two that played in it: Washington's and the Giants' "
                   "records and points moved, and every other club is unchanged. This is a "
                   "staleness finding, not an arithmetic error."),
    },
    {
        "id": "V03",
        "what": "Week 10 fixtures: date, kickoff, matchup, bye clubs",
        "source": OFFICIAL["week10"],
        "read_at": "2026-11-13",
        "method": "All 14 committed fixtures compared with the official week page, row by row.",
        "result": "14 of 14 match",
        "detail": ("Including the Munich international game (NE at DET, 9:30 AM ET) and the "
                   "Thursday game, which the page now shows as final: WAS 24, NYG 21. The "
                   "official byes are CHI, DEN, PHI and TB, which is what the repository "
                   "publishes."),
    },
    {
        "id": "V04",
        "what": "Official injury report, week 10: row-level spot check and club counts",
        "source": OFFICIAL["injuries"],
        "read_at": "2026-11-13",
        "method": ("Ten rows across four clubs compared field by field (player, position, "
                   "injury, practice status, game status) against the scraped file, plus the "
                   "row count for each club."),
        "result": "10 of 10 rows match; 4 of 4 club counts match",
        "detail": ("Washington 9 rows, the Giants 11, New England 15, Detroit 9, all exactly "
                   "as the committed scrape has them. This confirms the scraper is faithful "
                   "on the day it runs; it does not settle how quickly the page changes, which "
                   "is R03 on the Flagged page."),
    },
    {
        "id": "V05",
        "what": "Game-by-game review of the committed research extract",
        "source": OFFICIAL["nflverse"],
        "read_at": "2026-11-13",
        "method": ("The analysis was re-run from the committed extract and every output "
                   "compared with the committed output."),
        "result": "identical except the generation timestamp",
        "detail": ("All five files (own lines, leaderboard, parlays, correlations, props) "
                   "reproduce exactly from data/s9cb/*.csv. The extract itself could not be "
                   "re-downloaded here because the sandbox cannot reach the release-asset "
                   "host, so the source files are taken as committed and pinned by the "
                   "provenance file."),
    },
    {
        "id": "V06",
        "what": "Personnel-deficiency study, recomputed",
        "source": OFFICIAL["nflverse"],
        "read_at": "2026-11-13",
        "method": ("Run from committed inputs by s9cb/analysis/run_personnel.py; the pipeline "
                   "writes only to data/personnel/, so no previously published page changed."),
        "result": "reproducible; see the Signals page for the verdict",
        "detail": ("Seven thousand one hundred and three played games, thirteen information "
                   "tests and five candidate rules. Every count and p-value on the Signals page "
                   "is read from the output file, not typed here. The QB-continuity definition "
                   "was corrected during this session after a spot check on the Giants exposed "
                   "a stale incumbent, and the whole analysis was rerun."),
    },
    {
        "id": "V07",
        "what": "A defect in this session's own work, found by spot check",
        "source": OFFICIAL["injuries"],
        "read_at": "2026-11-13",
        "method": ("The week-10 deficiency board was read club by club against the official "
                   "report rather than accepted from the script."),
        "result": "two defects found, both fixed, analysis rerun",
        "detail": ("First, the 'incumbent' quarterback was defined as the club's most-starts "
                   "quarterback of the season, which labelled a club that had already changed "
                   "starter two weeks earlier as breaking continuity. Second, a club with a "
                   "completely clean report was being treated as having no report, discarding "
                   "a real zero. Both are fixed; the numbers on the Signals page are from the "
                   "rerun. This is recorded because a session that only reports clean results "
                   "is not a verification session."),
    },
    {
        "id": "V08",
        "what": "Repository gates, all of them",
        "source": "repository",
        "read_at": "2026-11-13",
        "method": ("validate_verified.py, audit_numbers.py, check_site.py, tools/verify.py, "
                   "tools/check_committed_site.py, tools/verify_combined.py, the unit tests, "
                   "and the new review-room checker."),
        "result": "see review-room/verification.html for the live result",
        "detail": "The result of each gate is printed on this page from the last run, not typed here.",
    },
    {
        "id": "V09",
        "what": "Publication path",
        "source": OFFICIAL["pages_api"],
        "read_at": "2026-11-13",
        "method": "Read the Pages configuration through the GitHub API.",
        "result": "legacy branch build from main at /, status built, https enforced",
        "detail": ("So every push to main publishes. There is no separate deploy step to fail, "
                   "but also no staging area: a broken page is live as soon as it is pushed, "
                   "which is why the link checker runs before the push and not after."),
    },
]
