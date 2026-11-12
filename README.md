# NFL Decision Lab

An evidence-first NFL decision support site: it originates its own lines from opponent-adjusted
play-by-play, scores betting strategies against the closing line under eight validation gates,
tracks starter availability against the weekly depth chart, and publishes every table with a
source link and every gap as a flag.

Live site: <https://kanlerxz87-cyber.github.io/NFL1/>

## What the site contains

| Page | What it answers |
|---|---|
| Overview | Season state, this week's own lines, top of the leaderboard, availability pressure, verification summary |
| My Lines | Ratings, own spread/total/win probability with error bands, out-of-sample accuracy, model-vs-market blend test |
| Strategy Lab | Leaderboard with gate matrix, correlation between strategies, parlay maths, reward scoring |
| Injuries & Depth | Official game status joined to depth-chart rank, next man up, experience and snaps |
| Props | Shrunk usage projections with intervals; market columns deliberately blank |
| Questions | Twenty decision-gating questions: known, unknown, how to discover, what it blocks |
| Suggestions | Twelve ranked improvements, five decision records, review process |
| Evidence | Provenance (URL + sha256 per file) and line-by-line verification against nfl.com |
| Flagged for Review | Every irregularity, unverified value and blocked decision |
| Executive Summary | What was built, what the evidence says, what is unresolved, decisions requested |

## How the data gets here

The Arena sandbox can only reach a small host allow-list, so bulk downloads and the nfl.com
injury scrape run in GitHub Actions:

```
.github/workflows/collect-data.yml
  1. pipeline/collect.py          download nflverse release files, pin URL + sha256
  2. pipeline/scrape_injuries.py  scrape the official nfl.com injury report (current week)
  3. pipeline/schema.py           probe real column names (nothing is guessed)
  4. pipeline/build_all.py        ratings, own lines, strategies, availability, props, verification
  5. commit data/model/*.json     back to the branch
```

Render the site locally (after data exists):

```
python3 pipeline/gen_site.py      # writes index.html and pages/*.html
```

Everything on the site is static HTML generated from `data/model/*.json` plus
`pipeline/content.py` (questions, suggestions, decision records).

## Files

- `pipeline/` — collector, official injury scraper, schema probe, models, verification, renderer.
- `data/model/` — generated JSON: ratings and lines, strategy leaderboard, availability, props,
  provenance, verification, snapshot, dashboard.
- `data/verified/` — the only hand-entered values: nfl.com standings (32 rows) and an injury
  report sample (44 rows), used to verify the automated feeds.
- `data/*.csv` — independent transcriptions from a parallel session, kept and cross-checked.
- `pages/` — generated site pages plus companion pages from that session.
- `COORDINATION.md` — shared multi-session task board and integration log.
- `src/nfl/`, `tests/`, `content/`, `verified-lab/` — the independent
  verification subsystem added by session `a2cea255`; see below.

## Honesty rules used in this repository

- No value is inferred, interpolated or filled in. Unknown values render as a labelled blank.
- Every strategy rule is fixed before evaluation, the number of rules tested is published, and
  p-values are corrected for multiple testing.
- Ratings never use information from the game being predicted (walk-forward only).
- Anything that cannot be verified against an official source is published on the
  **Flagged for Review** page with an explanation of what would settle it.

## Sources and licences

- Data: [nflverse](https://github.com/nflverse/nflverse-data), licence verified CC-BY-4.0
  (attribution required, shown in the site footer).
- Official entry points cited throughout: nfl.com standings, injury report, schedules, player
  stats and club directory.
- No official league odds exist. Closing lines in the mirrored feed are consensus numbers and are
  labelled as such.

This is a research tool, not betting advice.

## Independent verification subsystem

Session `a2cea255-nfl1` added a deliberately independent second implementation of the same
brief in `verified-lab/`: a hand transcription of the official nfl.com pages, a 34-check
verification harness, a provenance-and-gates engine, and a 20-page sub-site.

**Sub-site: <https://kanlerxz87-cyber.github.io/NFL1/verified-lab/>** ·
details in [`verified-lab/README.md`](verified-lab/README.md).

It publishes into its own directory because the root is this lab's live site, and its CI
footprint is nil. Where the two disagree — the sub-site publishes no spread, total or edge —
the reason is that GitHub release assets cannot be downloaded from the Arena sandbox, so the
nflverse feeds `pipeline/collect.py` fetches in Actions were never obtainable there. Blanks
were left blank rather than filled from an unofficial aggregator.

