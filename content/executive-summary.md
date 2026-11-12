## Purpose

This repository exists to collect, organise and analyse NFL information well enough to
originate its own betting lines, and to do so under an audit trail where every published
number can be traced to an official source or is visibly blank.

This page is the short version. Everything on it is reproduced with full working, source
links and verification status on the linked pages.

## What was in the repository before this session

One commit and one file: `README.md`, containing the six characters `# NFL1`. There was no
code, no data, no site and no task board. Everything described below was built in this
session, so the "repo review" task had no pre-existing content to verify - that is itself
recorded as a finding rather than quietly assumed away.

## What is now verified

All of the following was transcribed from **NFL.com**, the league's official website, in a
single retrieval session, and is published row by row with its source link.

| Dataset | Size | Source |
| --- | --- | --- |
| 2026 regular-season standings | 32 teams x 16 published columns | [nfl.com/standings](https://www.nfl.com/standings/) |
| Week 10 schedule | 14 games with date, kickoff and broadcast | [nfl.com/injuries](https://www.nfl.com/injuries/) |
| Week 10 bye list | 4 teams (CHI, DEN, PHI, TB) | [nfl.com/injuries](https://www.nfl.com/injuries/) |
| Week 10 injury report | 254 player entries across 24 teams | [nfl.com/injuries](https://www.nfl.com/injuries/) |
| Teams printing "No Injuries Reported" | 4 (SEA, CIN, LAC, BAL) | [nfl.com/injuries](https://www.nfl.com/injuries/) |
| Official news items bearing on availability | 8 items, each with its own URL | [nfl.com/news](https://www.nfl.com/news/) |

The standings snapshot covers **136 completed games** through Week 9 of the 2026 season.
Week 10 had not kicked off at retrieval time.

## Verification result

An automated harness runs **34 checks** over the transcribed data - arithmetic identities,
league-wide balance checks, vocabulary checks, cross-page agreement checks, provenance
checks and reference-mirror coverage checks.

- **29 PASS**
- **5 FLAG** - four are official cells that contradict themselves; the fifth is the
  community team mirror carrying four retired club codes alongside the 32 active ones
- **0 FAIL** - no transcription or harness error was found

Every check names its source, and every flagged item is published verbatim with the
arithmetic that proves the inconsistency rather than being quietly corrected.

Every one of the 32 team records printed beside the club logos on the official injury
report agrees exactly with the official standings page. That is a genuine cross-check
between two separately-rendered NFL.com pages retrieved in the same session, and it is the
strongest single piece of evidence that the transcription is faithful.

**Three official cells are internally inconsistent.** They are published verbatim, excluded
from every computation, left blank in the site tables, and listed on the Flagged for Review
page with the arithmetic that proves the inconsistency. No value was overwritten with a
guess.

## Real analysis produced from verified data

These are computations, not estimates, and each is reproducible from the cited source.

- **Fitted Pythagorean exponent: 3.5073** (95% bootstrap CI 2.7498-4.3113, n=32,
  R²=0.7715, calibration slope 0.9991). Fitted by least squares on the 32 official rows,
  not borrowed from any external study. The interval is wide and the exponent is high
  because it is fitted on roughly 8.5 games per team rather than a full season - stated as
  a limitation, not hidden.
- **League home win rate: 49.63%** (Wilson 95% CI 41.36%-57.93%, n=136 home games). Home
  teams are *not* winning more than half their games in 2026 so far. The interval includes
  50%, so this does not yet establish that home advantage has disappeared - it establishes
  that the usual ~2.5-point home-field assumption cannot be asserted from this data.
- **Luck table**: the gap between each team's Pythagorean expectation and its actual
  winning percentage, expressed in games. Tampa Bay is the most under-performing team
  relative to its scoring (+2.48 games of bad luck); Denver (-2.01) and Cleveland (-2.00)
  are the most over-performing.
- **Correlation screen**: 38 hypothesis tests across 21 signals and 2 targets, with
  Benjamini-Hochberg false-discovery-rate control. At p<0.05 alone, 1.9 false positives
  would be expected purely by chance. Nine tests survive FDR control at α=0.10 - and
  **all nine are definitional**, relating win percentage to other expressions of the same
  game outcomes. **Zero non-mechanical findings survive multiple-testing control.** That is
  the honest headline, and it is the single most important number on this site.

## What the injury data can and cannot support

The Week 10 report is real and complete, but it was retrieved on the Thursday of game week,
and at that point it is barely populated:

- **Injury designation coverage: 2.36%** - only 6 of 254 entries name a body part.
- **Game-status coverage: 2.36%** - only 6 entries carry Out/Doubtful/Questionable, all of
  them for the two games with the earliest reporting deadlines.
- Practice participation is fully populated: 93 DNP, 89 LP, 72 FP.

Consequence for operations: practice status is usable early in the week, but *designations*
are not. Any availability model must re-fetch after the Friday 4:00pm ET deadline, and the
system is built to timestamp each retrieval so a strategy can never be evaluated against
information that was not yet public.

Separately, and importantly: **NFL.com does not publish a public depth chart.** The league's
sanctioned weekly depth-chart feed is Sportradar's NFL Official API, which requires an API
key. String level - whether a 2nd, 3rd or 4th string backup is replacing a starter - is
therefore reported as UNAVAILABLE and never guessed. The specific starter changes that
*are* officially confirmed are captured from NFL.com news instead.

## Confirmed Week 10 availability facts

Each of these comes from an official NFL.com news item and each has its own link on the
Verified Data pages.

- Cleveland to start QB Deshaun Watson vs. Houston
- Arizona's Carson Beck to start vs. the Rams
- Miami placed QB Malik Willis (groin) on injured reserve; Kyle McCord in line for a first start
- Sam Darnold ruled out for Seattle's Week 10 game; Drew Lock expected to start again
- J.J. McCarthy expected to play for the Giants
- Justin Herbert avoided a finger fracture
- Rams WR Puka Nacua likely to be placed on injured reserve (turf toe, sprained MCL and PCL)
- Packers RB Josh Jacobs to undergo finger surgery; timeline to be determined

## Line origination status

The origination board for all 14 Week 10 games is published on the Week 10 Board page. It
shows what can honestly be computed and what cannot.

**Published (DERIVED - arithmetic on verified cells):** rating gap between the two clubs,
Pythagorean expectation for each club, and a naive total equal to the sum of the two clubs'
verified points-per-game.

**Left blank on purpose:** point spread, betting total, win probability, market line and
every measure of edge. Two inputs are missing and neither can be invented:

1. **Home-field advantage expressed in points.** Needs game-level final scores with
   home/away designation across a season.
2. **Closing market lines.** No licensed odds or market-data provider is reachable or
   credentialed from this environment.

The engine is written to refuse: when a required input is `None` the dependent output is
`None` plus a named blocking input, rather than a plausible-looking number. No line on this
site is a betting recommendation.

## Strategy programme status

Thirteen strategies are catalogued: four singles, two totals, three parlays, two player
props and two prop combos. Each states its hypothesis, its required inputs, its skill basis
and how luck is to be removed from its evaluation.

Every one of the thirteen currently returns **NOT_STAKEABLE**. The leaderboard shows
**0 scored, 13 withheld**. Scores are withheld rather than zeroed, so "not yet measured"
can never be confused with "measured and worthless".

Nine validation gates stand between a strategy and a stake. They are implemented and
unit-tested: the harness demonstrably approves a well-formed strategy and rejects one with
lookahead, one whose edge is within noise, and one whose profit comes from a single fold.
Today they all block, because there are no settled wagers, no odds history and no
timestamped feature history.

## The three things that unblock everything

1. **A closing-odds feed** - at least three full seasons of closing spreads, totals and
   moneylines, plus opening lines so closing-line value can be measured. Without this there
   is no ROI, no edge, no CLV and no leaderboard.
2. **Official depth charts** - Sportradar's NFL Official API, or an equivalent sanctioned
   feed. Without this, string level cannot be attached to any absence.
3. **Game-level results and play-by-play** - to fit home-field advantage in points, to run
   walk-forward backtests, and to build EPA-based ratings that are far stronger than
   points-per-game.

Each is specified with the exact source that would resolve it on the Open Questions page,
and each has a corresponding item on the Suggestions Board.

## Bottom line

The system, the verification discipline and the site are complete and working, and the
current-season data is genuinely verified against official sources. What does not exist yet
is any evidence that a betting edge exists, because the two datasets an edge is measured
against - closing odds and depth charts - are not obtainable from this environment. Nothing
on this site should be staked on, and no number has been invented to make it look otherwise.
