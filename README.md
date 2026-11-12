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

---

## The independent verification subsystem (`verified-lab/`)

Session `a2cea255-nfl1` built a second, deliberately independent implementation of the same
brief: a transcription of the official nfl.com pages done by hand rather than scraped, a
verification harness, a provenance-and-gates engine, and a 20-page dashboard.

**Sub-site: <https://kanlerxz87-cyber.github.io/NFL1/verified-lab/>**

It is published in its own directory rather than at the repository root because the root is
this lab's live site, and overwriting `index.html`, `executive-summary.html`, `flagged.html`,
`suggestions.html` or `verification.html` would have destroyed merged work. Its CI footprint
is nil: `scripts/verified/check_site.py` scans only `index.html` and `pages/`.

| Path | What it is |
|---|---|
| `src/nfl/` | 16 **standard-library-only** modules — no third-party dependency at all |
| `data/verified/*.tsv` | Hand transcription of nfl.com: 32 standings rows, 254 injury entries, 14 Week 10 games, byes, report status, 8 news items |
| `data/processed/site_data.json` | Generated artifact; the sub-site's single input |
| `content/*.md` | Hand-written prose: executive summary, 22 open questions, 22 suggestions with blank Decision columns, methodology |
| `scripts/build_site.py` | 20 page builders. **Contains no numbers** — every value comes from the JSON artifact |
| `tests/` | 103 unit tests, including a link checker and a per-row source-link enforcer |

### What it adds that the main pipeline does not

- **A 34-check verification harness** (`src/nfl/verify.py`) run over hand-transcribed cells:
  **29 PASS, 5 FLAG, 0 FAIL**. It recomputes the tie-aware `PCT = (W + 0.5·T)/(W+L+T)` with
  half-up `Decimal` rounding, checks league-wide balance, slate integrity, injury vocabulary,
  and — its strongest check — that all 28 records printed beside club logos on the official
  injury page agree exactly with the official standings page.
- **Three official cells that contradict themselves**, found by that harness and never
  silently corrected: WAS `non_conf` (2-5-1 is 8 games, CONF 3-2-1 is 6, so NON-CONF must be
  2 games but the page prints `1-3-1`), IND `div` (`1-3-0` ⇒ 0.250, page prints 0.333), and
  PHI `div` (`1-4-0` ⇒ 0.200, page prints 0.250). Published verbatim, excluded from derived
  maths, flagged with the arithmetic proof.
- **A provenance tier on every value** — `VERIFIED`, `DERIVED`, `MODELED`, `UNAVAILABLE` — and
  a refusal path: when a required input is `None` the dependent output is `None` plus a named
  blocking input, never a plausible-looking number.
- **Nine validation gates proven bidirectional.** The harness *approves* a well-formed
  strategy and *rejects* lookahead, an edge inside the noise, a confidence interval spanning
  zero, and profit concentrated in one fold. A gate that only ever says no is not evidence.
- **Two publication rules enforced by tests rather than by convention**: every `href` in all
  20 pages must resolve, and every row of every table declaring a `Source` column must carry a
  link to an official host. Both caught real defects during development.

### Where the two systems disagree, and why that matters

This subsystem reports **no spread, no total, no win probability and no edge**, and concludes
that **zero non-mechanical findings survive** its correlation screen (38 tests, BH-FDR at
α = 0.10; 9 survive and all 9 are definitional; 1.9 false positives expected at p < 0.05 by
chance alone). That is not a contradiction of the main pipeline — it is a consequence of
running inside the Arena sandbox, where GitHub **release assets cannot be downloaded** (302 to
`release-assets.githubusercontent.com`, then exit 35 / 0 bytes), so the nflverse closing lines,
depth charts and play-by-play that `pipeline/collect.py` fetches **in GitHub Actions** were
never obtainable here. Blanks were left blank rather than filled from an unofficial
aggregator. The main lab, running in CI, has that data and this subsystem does not.

Read the two together: the lab for what the data supports, `verified-lab/` for an
independent audit of the official pages themselves.

Reproduce the subsystem with no dependencies installed:

```bash
PYTHONPATH=src python3 -m nfl.pipeline        # -> data/processed/site_data.json
PYTHONPATH=src python3 scripts/build_site.py  # -> verified-lab/
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
