# NFL1

A verified-data-first research system for the NFL: it collects official league
data, checks it line by line, computes only what the data supports, and refuses
to publish anything it cannot source.

**Live dashboard → https://kanlerxz87-cyber.github.io/NFL1/**

> **Nothing on this site is a betting recommendation.** No value has been
> estimated, interpolated or filled in to make a table look complete. Where an
> official source could not confirm a number, the cell is blank and the item is
> listed on the [Flagged for Review](https://kanlerxz87-cyber.github.io/NFL1/flagged.html)
> page together with the source that would resolve it.

---

## Start here

| Page | What it answers |
|---|---|
| [Dashboard](https://kanlerxz87-cyber.github.io/NFL1/) | Current state of the league and of the system, in one view |
| [Executive Summary](https://kanlerxz87-cyber.github.io/NFL1/executive-summary.html) | What is verified, what was found, what is missing |
| [Open Questions](https://kanlerxz87-cyber.github.io/NFL1/open-questions.html) | 22 questions that must be answered **before** any decision |
| [Suggestions Board](https://kanlerxz87-cyber.github.io/NFL1/suggestions.html) | 22 proposed improvements, each awaiting review — **none implemented** |
| [Flagged for Review](https://kanlerxz87-cyber.github.io/NFL1/flagged.html) | Every irregularity, blank and blocked value, with its source link |
| [Verification Report](https://kanlerxz87-cyber.github.io/NFL1/verification.html) | All 34 automated checks and their outcomes |
| [Source Register](https://kanlerxz87-cyber.github.io/NFL1/sources.html) | Every source, its tier, and exactly what it was used for |

Data pages: [Standings 2026](https://kanlerxz87-cyber.github.io/NFL1/data-standings.html) ·
[Week 10 Schedule](https://kanlerxz87-cyber.github.io/NFL1/data-schedule.html) ·
[Injury Report](https://kanlerxz87-cyber.github.io/NFL1/data-injuries.html) ·
[Official News](https://kanlerxz87-cyber.github.io/NFL1/data-news.html)

Analysis pages: [Team Ratings](https://kanlerxz87-cyber.github.io/NFL1/analysis-ratings.html) ·
[Luck Table](https://kanlerxz87-cyber.github.io/NFL1/analysis-luck.html) ·
[Correlations](https://kanlerxz87-cyber.github.io/NFL1/analysis-correlation.html) ·
[Availability & Depth](https://kanlerxz87-cyber.github.io/NFL1/availability-depth.html)

Line origination: [Week 10 Board](https://kanlerxz87-cyber.github.io/NFL1/lines-week10.html) ·
[Methodology](https://kanlerxz87-cyber.github.io/NFL1/methodology.html)

Strategies: [Leaderboard](https://kanlerxz87-cyber.github.io/NFL1/strategies-leaderboard.html) ·
[Catalogue](https://kanlerxz87-cyber.github.io/NFL1/strategies-catalogue.html) ·
[Validation Gates](https://kanlerxz87-cyber.github.io/NFL1/strategies-gates.html)

---

## The headline result

**Zero non-mechanical findings survive multiple-testing control.**

38 correlation tests were run across 21 signals with Benjamini–Hochberg
false-discovery-rate control at α = 0.10. At p < 0.05 alone, **1.9 false
positives would be expected purely by chance**. Nine tests survive — and all
nine are definitional (win percentage against other expressions of the same game
outcomes). Every availability and injury signal that looks interesting is, so
far, indistinguishable from a tautology or from noise.

Consequently: **13 strategies are catalogued, 0 are APPROVED, 13 are
NOT_STAKEABLE**, and the leaderboard shows **0 scored / 13 withheld**. Scores
are withheld rather than zeroed, so "not yet measured" can never be confused
with "measured and worthless".

Two datasets are missing and neither can be invented: **closing market lines**
(no licensed odds provider is reachable) and **official depth charts** (NFL.com
publishes none; Sportradar's sanctioned feed is credential-gated).

---

## Publication rules

These are enforced by the test suite, not by convention.

1. **Every table row carries a source link** to an official site.
   `tests/test_site.py` fails the build if any row of any table declaring a
   `Source` column lacks a link to an official host.
2. **Unconfirmable values stay blank.** Rendered as an explicit em-dash marker
   with a tooltip, never as `0` and never as a guess.
3. **Nothing is inferred.** A blank `Injuries` cell stays blank even when the
   player's practice status implies something.
4. **Disputed official cells are published verbatim** and excluded from all
   derived maths, with the arithmetic proof of the inconsistency shown.
5. **No broken links.** The build fails if any internal link, page anchor or
   navigation entry does not resolve.
6. **Every value carries a provenance tier** — `VERIFIED`, `DERIVED`,
   `MODELED` or `UNAVAILABLE` — and each tier is defined where it appears.

---

## Repository layout

```
data/verified/     transcribed corpus, all from official nfl.com pages
  standings_2026_reg.tsv          32 teams × 19 fields
  injury_report_2026_week10.tsv   254 entries
  schedule_2026_week10.tsv        14 games
  bye_week10.tsv                  CHI, DEN, PHI, TB
  team_report_status_week10.tsv   32 teams
  nfl_news_2026_week10.tsv        8 headlines + URLs
  sources.json                    11 sources with tier + used_for
data/reference/    teams.csv — community mirror, labels/colours only
data/processed/    site_data.json — generated; the site's single input
src/nfl/           16 stdlib-only modules (no third-party dependency)
content/           prose written by hand, rendered by markdown_lite
scripts/           build_site.py — 20 page builders, contains no numbers
*.html + .nojekyll generated site at the repository root, served by GitHub Pages
tests/             102 unit tests including link + source-link enforcement
COORDINATION.md    shared task board for parallel sessions
```

The site is generated into the **repository root**, not a `docs/` folder, because
this repository's Pages source is pinned to `main` at `/` and the API refuses to
change it (the integration token lacks `pages:write`). `.nojekyll` is written so
Pages serves the build verbatim instead of running it through Jekyll. Set
`NFL1_SITE_OUT=/some/scratch/dir` to build somewhere else.

`src/nfl` and `scripts/build_site.py` are deliberately **standard library
only**, so the entire pipeline and site build run on any Python 3.11+ without
installing anything.

---

## Reproduce

```bash
# 1. recompute every derived value from the transcribed corpus
PYTHONPATH=src python3 -m nfl.pipeline        # -> data/processed/site_data.json

# 2. rebuild all 20 pages
PYTHONPATH=src python3 scripts/build_site.py  # -> *.html at the repo root

# 3. run the verification harness and the full test suite
PYTHONPATH=src python3 -c "from nfl import verify; import json; \
r = verify.run(); print(r['total'], r['PASS'], r['FLAG'], r['FAIL'])"
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The pipeline is deterministic — every random routine is seeded
(`20261112`), so two runs produce byte-identical output.

---

## Working in this repository

Read [`COORDINATION.md`](COORDINATION.md) before editing anything. It is the
shared task board: claim a task and its file scope, commit the claim
immediately, never start work another session has claimed, and route
cross-file needs through a logged request rather than an edit.
