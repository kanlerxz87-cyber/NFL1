# Decision Room (`room/`)

A self-contained, static site for **reviewing and choosing a path before any change is
implemented**. It is built from the committed JSON in `room/data/` and published under
<https://kanlerxz87-cyber.github.io/NFL1/room/>. It is linked from the main landing page
navigation ("Decision Room").

| Page | What it is for |
|---|---|
| `index.html` | Overview: 15 verified numbers, the eight decisions ready for a choice, the three blocked ones, and where every section lives |
| `executive.html` | Executive summary: what holds up, what does not, what is missing, what a human must decide |
| `decisions.html` | **The review surface.** 14 decisions (8 ready, 3 blocked, 3 informational), 30 options with what each buys / costs / risks, evidence links, a recommendation, and the gate that would enforce the change |
| `suggestions.html` | 15 ranked improvements, each tied to a decision and a finding |
| `questions.html` | 22 questions that gate decisions: known, missing, how to discover it, what it blocks |
| `strategy.html` | Own lines, the 12 tested rules, the 8 gates, luck removal, correlations, next man up |
| `injuries.html` | Official designations, next man up, and depth-chart coverage for all 32 clubs |
| `data.html` | Today's official capture: 32 standings rows and 27 fixtures, reconciled arithmetically |
| `flagged.html` | Every finding, open or passing, with the official source that settles it |
| `about.html` | Method, source register, and what is deliberately blank |

## Build and gate

```bash
python3 room/build.py     # rewrite every page from room/data/*.json
python3 room/verify.py    # fail on: broken local link, unreachable page, table with no rows,
                          # empty cell, data table without an https source link, literal markdown,
                          # or a KPI card with no provenance note
```

`build.py` refuses to render a row whose source link is not `https://`. `verify.py` is run in
`.github/workflows/room.yml` and in `pages.yml`, together with a staleness check: if the
committed pages differ from a fresh rebuild, the build fails.

## Data

| File | Contents | Source |
|---|---|---|
| `data/executive.json` | KPIs, known / unknown / wrong, decisions requested | every KPI carries its own source URL |
| `data/decisions.json` | 14 decision cards | evidence links per option |
| `data/questions.json` | 22 gating questions | evidence links per question |
| `data/suggestions.json` | 15 ranked improvements | |
| `data/findings.json` | 17 findings (open and passing) | official URL per finding |
| `data/leaderboard.json` | Observed-price strategy board | `data/s9cb/leaderboard.json` |
| `data/next_man.json` | Week 10 designations joined to club charts | nfl.com + club site per row |
| `data/depth_coverage.json` | 32-club depth-chart coverage | club URL per row |
| `data/sources.json` | Register of every page fetched today | |

The official capture those files were derived from is committed verbatim under
`data/official/2026-11-13/` (standings, fixtures, injury designations, the per-club injury
count audit, and the source register), so a reviewer can check the transcription against
the live page.

## What this directory does not do

- It does not edit `index.html`, `pages/`, `docs/`, `lab/`, `dashboard/`, `verified-lab/` or
  `referee/`. Those belong to other sessions' generators. The only shared file touched is one
  navigation entry in `pipeline/gen_site.py`.
- It does not publish a number that has no source. Where a value could not be established it
  says so in words and points at what would settle it.
- It does not implement any suggestion. Every suggestion is a decision waiting for a choice.
