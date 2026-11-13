#!/usr/bin/env python3
"""The question register: what must be answered before a decision can be made.

Each row separates four things that get muddled in normal analysis:

  * `known`   - what we actually have, with where it came from;
  * `missing` - what we do not have;
  * `discovery` - the concrete step that would produce the missing thing (who/what/how long);
  * `blocks`  - which decisions cannot be taken until it is answered.

`answerable_now` is the field that matters most: "yes" means the missing piece can be
collected with tools already available, "no" means it needs money, a contract or a human
decision, and "unknown" means nobody has checked yet. A question that is answerable now and
still unanswered is a task, not a question, and the page says so.

Ids Q01-Q28 are the existing repository ledger; Q29 onward are added by this session and
every one of them is new, not a restatement.
"""

QUESTIONS = [
    # ---------------------------------------------------------------- carried over
    {"id": "Q28", "area": "Architecture",
     "question": "Which of the published site generations is authoritative, and do they stay in sync?",
     "known": "Seven generations exist and are all live; pages/sections.html lists them.",
     "missing": "A single declared authority.",
     "answerable_now": "yes",
     "discovery": "Owner names one generation; the others get a banner and a redirect (decision D01).",
     "blocks": "D01, and any claim that a published number is 'the' number.",
     "origin": "existing ledger", "source": "pages/sections.html"},
    {"id": "Q01", "area": "Pricing",
     "question": "Which price, at which book, at what timestamp, is being evaluated?",
     "known": "A mirrored consensus closing spread/total for 5,228 of 7,103 played games, with American odds.",
     "missing": "Book-level quotes, limits, and open/close snapshots.",
     "answerable_now": "no",
     "discovery": "A licensed odds API with 15-minute snapshots, stored append-only (decision D02).",
     "blocks": "Every ROI, closing-line-value and reward claim.",
     "origin": "existing ledger", "source": "https://github.com/nflverse/nflverse-data"},
    {"id": "Q04", "area": "Player props",
     "question": "Are player props priced at all, and with what correlation for combos?",
     "known": "Model projections for four markets with error bands; measured leg correlation from results.",
     "missing": "Any prop price.",
     "answerable_now": "no",
     "discovery": "Licensed prop feed; until then props stay model-only and are labelled as such.",
     "blocks": "Prop and same-game-parlay strategies.",
     "origin": "existing ledger", "source": "pages/props.html"},
    {"id": "Q25", "area": "Deployment",
     "question": "What is the GitHub Pages publishing source for this repository?",
     "known": "Legacy branch build from main at /, build_type legacy, https enforced (checked this session through the GitHub API).",
     "missing": "Nothing.",
     "answerable_now": "yes",
     "discovery": "Already answered: repos/kanlerxz87-cyber/NFL1/pages.",
     "blocks": "Nothing.",
     "origin": "existing ledger", "source": "https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages"},

    # ------------------------------------------------------ added by this session
    {"id": "Q29", "area": "Signals",
     "question": "Do personnel losses carry information the closing line has not already priced?",
     "known": ("Answered this session and revisited once the QB-continuity definition was "
               "corrected: the measures were tested against the closing spread and corrected "
               "for the whole family. The counts, coefficients and corrected p-values are read "
               "live from the data file on the Signals page rather than typed here, so this "
               "entry cannot drift out of date."),
     "missing": ("Anything measured at player level on defence: the committed extract has no "
                 "defensive player statistics, so defensive deficiency is counted in names on "
                 "the report, not in lost production."),
     "answerable_now": "yes",
     "discovery": ("Add per-player defensive snaps and statistics to the extract and rerun the "
                   "same regression (decision D04 option B)."),
     "blocks": "Any personnel-driven betting rule; decision D04.",
     "origin": "this session", "source": "review-room/evidence.html"},
    {"id": "Q30", "area": "Signals",
     "question": "Does the market move on injury news, and how fast?",
     "known": "Nothing. The extract carries one closing price per game, with no history.",
     "missing": "Timestamped odds history around each designation.",
     "answerable_now": "no",
     "discovery": "The same feed as Q01, queried at T-24h, T-1h and close around each report.",
     "blocks": ("The only version of the personnel question with a plausible route to an edge: "
                "the information is public, so speed is the only place an edge can live."),
     "origin": "this session", "source": "pages/strategies.html"},
    {"id": "Q31", "area": "Competition",
     "question": "Who is allowed to enter the leaderboard, and can a strategy be changed after it scores?",
     "known": "Twelve lab rules plus five new rules are scored under eight gates and a whole-family correction.",
     "missing": "An entry process, an identity rule, and a frozen rulebook per season.",
     "answerable_now": "yes",
     "discovery": "Freeze a dated rulebook in git before the season; publish the hash (suggestion S11).",
     "blocks": "Any reward ranking (D03), and the credibility of the gate matrix.",
     "origin": "this session", "source": "pages/strategies.html"},
    {"id": "Q32", "area": "Availability",
     "question": "Who actually replaced a ruled-out starter, and how many snaps did the replacement play?",
     "known": ("The official per-club depth charts name the next man up for 31 of 32 clubs "
               "(Houston's chart was unavailable when scraped), and the week-10 official report "
               "gives the game status."),
     "missing": ("Game-day inactives as published, and the replacement's actual snap share. "
                 "The two facts are never joined automatically: the join is by inference, so it "
                 "is shown separately and labelled."),
     "answerable_now": "yes",
     "discovery": ("Scrape the official inactives page on game day and join nflverse snap counts; "
                   "both are already collected in other parts of this repository."),
     "blocks": "Turning the deficiency register into a measurable replacement effect.",
     "origin": "this session", "source": "pages/injuries.html"},
    {"id": "Q33", "area": "Integrity",
     "question": "How stale is each published number, and how fast does its source change?",
     "known": ("Measured this session: the committed 2026 standings were one game behind the "
               "official page because the Week 10 Thursday game (WAS 24, NYG 21) had finished; "
               "30 of 32 clubs still matched, and the two that differed are exactly the two "
               "clubs that played. The official injury page was confirmed to change during the "
               "day in an earlier session."),
     "missing": "A published refresh window per source, and a build gate on age.",
     "answerable_now": "yes",
     "discovery": "Show the retrieval timestamp and the source's update cadence; fail the build past a threshold (decision D06).",
     "blocks": "Any table whose value can change between verification and reading.",
     "origin": "this session", "source": "review-room/verification.html"},
    {"id": "Q34", "area": "Pricing",
     "question": "Is the closing line in the extract the consensus close, and from which books?",
     "known": "The field is documented as a closing line in the mirror's field dictionary.",
     "missing": ("The book list, the weighting and the capture time. No official league source "
                 "publishes odds at all, so this can only be answered by the mirror's own "
                 "documentation."),
     "answerable_now": "yes",
     "discovery": "Read the nflverse field dictionary for the schedules release and cite it per column.",
     "blocks": "Any statement of the form 'we beat the closing line'.",
     "origin": "this session", "source": "https://nflreadr.nflverse.com/articles/dictionary_schedules.html"},
    {"id": "Q35", "area": "Availability",
     "question": "Is 'Unofficial Depth Chart' an official statement of the lineup?",
     "known": ("Two clubs label their own published chart 'Unofficial' (Kansas City, Green Bay); "
               "one states an as-of date (San Francisco, 11/10/26); nfl.com itself publishes no "
               "depth chart and returns 404 at the club-style URL."),
     "missing": "A statement from the league or a club that the chart is authoritative.",
     "answerable_now": "no",
     "discovery": "Ask the clubs; until then treat the chart as a snapshot, not a lineup.",
     "blocks": "Presenting depth rank as fact rather than as the club's own publication.",
     "origin": "this session", "source": "https://www.nfl.com/teams/"},
]
