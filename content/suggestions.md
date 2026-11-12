## What this board is for

Nothing on this page has been implemented. Each item is a proposal, written so a reviewer can
read the reasoning, weigh the cost against the benefit, and choose a path **before** any code
changes. The Decision column is deliberately blank and is the reviewer's to fill in.

To decide an item, record one of: **Approve**, **Reject**, **Defer**, or **Needs more
information** (naming what). Approved items become tasks on `COORDINATION.md` with an owner
and a file scope. Rejected items stay on the board with the reason recorded, so the same idea
is not silently re-proposed later.

**Effort** is the reviewer's cost in focused working sessions: S = under half a day,
M = one to three days, L = a week or more, XL = depends on an external contract or vendor.
**Impact** is how much better a decision would be afterwards: 1 = marginal, 3 = material,
5 = unblocks work that is currently impossible.

---

## A. Data acquisition - the work that unblocks everything else

### S-01 · Connect a licensed closing-odds feed
**Effort XL · Impact 5 · Priority P0 · Decision: ______**
Nothing about betting can be measured without market prices. Three full seasons of closing
spreads, totals and moneylines - plus opening lines, so closing-line value can be measured -
is the minimum credible history. Closing-line value is the single most reliable early
indicator of genuine skill, because it is measurable long before ROI accumulates enough
sample to be statistically meaningful. The arithmetic to consume such a feed already exists
and is unit-tested in `src/nfl/odds.py`; only the connection is missing.

### S-02 · Obtain official depth-chart credentials
**Effort L · Impact 5 · Priority P0 · Decision: ______**
Sportradar's NFL Official API is the NFL's sanctioned weekly depth-chart feed. Without it,
string level is unknown for every player in the dataset and the specific requirement -
knowing when a 2nd, 3rd or 4th string backup replaces a starter - cannot be met by any
honest means. Scraping 32 club websites is the fallback, but charts there are unversioned
and inconsistently formatted, which makes them unsuitable for gate G3's no-lookahead
requirement.

### S-03 · Build a game-level results archive from official per-week score pages
**Effort L · Impact 5 · Priority P0 · Decision: ______**
Game-by-game final scores with home/away designation are needed to fit home-field advantage
in points, to run walk-forward backtests, and to validate any rating model. The official
per-week score pages are reachable but verbose, so this should be a scheduled retriever
writing compact structured rows, not a one-off manual transcription.

### S-04 · Snapshot the injury report on a schedule, every version, timestamped
**Effort M · Impact 5 · Priority P0 · Decision: ______**
The current snapshot proves the problem: retrieved on the Thursday of game week, only 2.36%
of entries carried an injury designation and 2.36% carried a game status. Practice
participation was fully populated. That means an early-week snapshot and a Friday-evening
snapshot describe materially different worlds. Capturing Wednesday, Thursday, Friday
post-deadline and Saturday versions produces the first real measurement of information
arrival - which is itself a tradeable signal, and is a hard prerequisite for gate G3.

### S-05 · Add a per-retrieval content hash and a change log
**Effort S · Impact 3 · Priority P1 · Decision: ______**
Every snapshot should record a hash of its raw content and a diff against the previous
version. This makes it possible to prove later that a value was available at a given moment,
which is the difference between a defensible backtest and an unfalsifiable one. It also
catches silent source-format changes before they corrupt the data.

### S-06 · Re-retrieve the three inconsistent standings cells from a second official view
**Effort S · Impact 3 · Priority P1 · Decision: ______**
The DIV records for Indianapolis and Philadelphia and the NON-CONF record for Washington
each contradict their own adjacent percentage cell. In all three cases the printed cell is
character-identical to a neighbouring cell, which points at a rendering duplication defect
rather than a real record. Re-retrieving the parameterised division view and cross-checking
against the conference view would establish whether the defect is in the source or in the
retrieval. Until then the cells stay excluded and flagged, which is correct but leaves a
known hole.

## B. Modelling

### S-07 · Replace points-per-game ratings with an EPA-based rating
**Effort L · Impact 4 · Priority P1 · Decision: ______**
Net points per game is the best rating obtainable from the standings alone, and it is a
coarse instrument: it treats a 40-point blowout and a 3-point win as different amounts of
the same thing, and it says nothing about whether a score came against a first-string
defence in the first quarter or a prevent unit in the fourth. Expected points added per play
is materially stronger and is the standard in serious NFL modelling. It requires
play-by-play, which is currently unreachable from this environment.

### S-08 · Fit a proper Elo or state-space rating instead of a season-to-date average
**Effort M · Impact 4 · Priority P1 · Decision: ______**
A season-to-date average weights Week 1 as heavily as Week 9. An Elo-style rating with a
recency factor, or a Kalman filter over game margins, tracks a team's *current* strength far
better and handles roster turnover mid-season. Needs S-03 first.

### S-09 · Fit the availability weight tables instead of assuming them
**Effort M · Impact 4 · Priority P1 · Decision: ______**
The severity weights (Out 1.00, Doubtful 0.80, Questionable 0.50, DNP 0.45, LP 0.25, FP 0.05)
and the position weights (QB 1.00 down to FB 0.10) are analyst priors, published in full on
the Methodology page and labelled MODELED everywhere they appear. They should be fitted
against observed line movement once S-01 and S-02 exist. Until then every number that
depends on them is a ranking aid, not an estimate.

### S-10 · Model totals from team-level scoring rates rather than summing points per game
**Effort M · Impact 3 · Priority P2 · Decision: ______**
The published naive total is the arithmetic sum of two clubs' verified points-per-game. It is
honest and it is reproducible, but it ignores pace, opponent strength, venue and weather, and
it double-counts: both teams' points-per-game already includes the points they conceded to
each other's quality of opponent. A regression on game-level totals would replace it.

### S-11 · Add a weather and venue layer
**Effort M · Impact 2 · Priority P2 · Decision: ______**
Wind matters more than temperature for totals and passing props, and the Week 10
international game in Munich is a genuine venue outlier with no home crowd advantage in the
usual sense. Needs an official venue identifier per game and a weather source. Low priority
relative to S-01 to S-04, but it is a real omission for totals work.

## C. Decision support and the site

### S-12 · Add a per-decision "what would change my mind" panel
**Effort S · Impact 4 · Priority P1 · Decision: ______**
Each analysis page should state the specific observation that would falsify its conclusion.
This is the cheapest available defence against confirmation bias, and it converts the site
from a report into a decision aid. Example: on the Luck Table, "if Tampa Bay's point
differential is driven by one or two outlier games, the unlucky label is an artefact - check
the margin distribution."

### S-13 · Surface the provenance tier as a site-wide filter
**Effort M · Impact 4 · Priority P1 · Decision: ______**
Every value already carries VERIFIED, DERIVED, MODELED or UNAVAILABLE. Adding a control that
dims or hides everything below a chosen tier would let a reviewer see, in one click, exactly
which conclusions rest on verified data and which rest on an assumption. This directly serves
the "improve decision making" goal and makes the discipline visible rather than merely
documented.

### S-14 · Ratify the reward ladder
**Effort S · Impact 3 · Priority P2 · Decision: ______**
The four-tier ladder in `src/nfl/leaderboard.py` - promote to live paper trading, extended
validation, watchlist, retire - is marked PROPOSAL. It needs an owner decision on what a
reward concretely means: bankroll allocation, promotion to live tracking, or something else
entirely. The scoring formula is also worth reviewing: ranking on a t-statistic rather than
raw ROI means sample size enters the score directly, which is intentional, but the
stability and capacity multipliers are judgement calls.

### S-15 · Name a governance owner and a review cadence
**Effort S · Impact 3 · Priority P2 · Decision: ______**
Gate failures currently retire a strategy automatically, but nobody owns the decision to
override a gate, and there is no scheduled review. Propose: a weekly review of the
leaderboard and the Flagged page, with any gate override recorded in `COORDINATION.md`
together with the reason. An override that is not written down is indistinguishable from a
bug.

### S-16 · Add an explicit "no bet" default to the origination board
**Effort S · Impact 4 · Priority P1 · Decision: ______**
The Week 10 board already publishes rating gaps and leaves spreads blank. It should go
further and state the recommended action for each game, which today is uniformly **no action
possible** because no market line exists to compare against. Making the default action
explicit, rather than implied by a blank cell, removes any chance that a blank is read as a
pass or as an approval.

### S-17 · Publish the retrieval diff on the dashboard
**Effort S · Impact 3 · Priority P2 · Decision: ______**
Show what changed since the previous run - new injury entries, status changes, newly
confirmed absences. A dashboard that shows only the current state hides the thing that is
most decision-relevant, which is movement. Depends on S-04 and S-05.

## D. Risk and integrity

### S-18 · Adopt a written staking policy before any money is involved
**Effort S · Impact 5 · Priority P0 · Decision: ______**
No bankroll, unit size, maximum exposure or cross-wager correlation limit is defined
anywhere in this repository, and the system deliberately does not assume one. A written
policy - fractional Kelly with a hard per-wager and per-slate cap, plus a stop-loss rule -
should exist and be owner-approved before the first wager is placed, including a paper wager,
because a paper-trading record with no staking rule produces a number that cannot be
interpreted.

### S-19 · Make the placebo test mandatory rather than advisory
**Effort S · Impact 4 · Priority P1 · Decision: ______**
Gate G5 already requires a permutation placebo p ≤ 0.05. It should additionally require that
the *same* strategy code, run on sign-flipped returns, produces no edge - which catches the
commonest failure mode, where an edge is real in the code path but is actually an artefact of
how the sample was assembled. Cheap to add, and it is the difference between "passed a test"
and "survived an attempt to break it".

### S-20 · Add a pre-registration step for every new strategy
**Effort M · Impact 4 · Priority P1 · Decision: ______**
Require each strategy to record its hypothesis, its inputs and its success criteria *before*
it is evaluated, in a file that is committed and never edited afterwards. This is the only
reliable defence against the garden of forking paths: with 21 signals and 13 strategies, the
number of implicit comparisons is large enough that something will look significant by
chance, and post-hoc rationalisation is invisible in the results. The correlation screen
already controls for this within a single screen; pre-registration controls for it across
time.

### S-21 · Track every rejected hypothesis, not just the survivors
**Effort S · Impact 3 · Priority P2 · Decision: ______**
A published archive of what was tried and failed is more valuable than a list of what works,
because it stops the same dead end being re-explored. Tier 4 of the reward ladder already
archives rejections with a reason; this proposes making that archive a first-class page on
the site.

### S-22 · Confirm the legal position before any deployment
**Effort S · Impact 5 · Priority P0 · Decision: ______**
The system has no idea what jurisdiction its owner is in and makes no attempt to guess.
Whether sports wagering is legal there, whether any intended operator is licensed there, and
whether automated collection from each data source complies with that source's terms of use
are all owner questions that must be answered before deployment. Everything in this
repository should be treated as research until they are.
