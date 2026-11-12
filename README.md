# NFL1

A verified NFL analytics and strategy workspace: proprietary line origination, a strategy
leaderboard with validation gates, injury and lineup-depth tracking, and a decision register
that separates what we know from what we do not.

**Live site:** GitHub Pages — built from `/docs`. Every table row links to the official source
it came from.

---

## What is in here

| Path | What it is |
| --- | --- |
| `COORDINATION.md` | Shared task board for parallel agent sessions. Claim before you edit. |
| `data/` | The data layer. Every register lives here as JSON; the site is generated from it. |
| `tools/build_site.py` | Generates the static site into `docs/`. Fails the build if any data row lacks a source URL. |
| `docs/` | The published site (GitHub Pages). Generated — edit the data, not these files. |

## The site

| Page | Contents |
| --- | --- |
| `index.html` | Dashboard: KPIs, at-a-glance register table, Week 10 snapshot. |
| `executive-summary.html` | The important details, what is blocked, what to do next. |
| `requirements.html` | 52 requirements extracted line by line from the brief. |
| `questions.html` | 24 questions: answered, partially answered, open-blocking. |
| `suggestions.html` | 15 improvements with options, trade-offs and a decision path. |
| `strategy-lab.html` | Line-origination pipeline, six validation gates, leaderboard, skill-vs-luck tests. |
| `signals.html` | 18 candidate signals with hypotheses and blockers. |
| `correlation.html` | Correlation register plus the algebra of combining legs. |
| `injury-depth.html` | Official Week 10 injury report in full; the depth-chart gap. |
| `standings.html` | Official 2026 standings, all 32 clubs. |
| `data-sources.html` | Every source used, tiered by authority. |
| `verification.html` | Checks performed and the rules the build enforces. |
| `flagged.html` | Everything unverified or irregular, with source links. |

## Build

```bash
python3 tools/build_site.py
```

Reads `data/*.json`, writes `docs/*.html`. Requires Python 3.9+; no dependencies.

## Rules

1. **Every data row carries a source link.** The generator refuses to emit a page otherwise.
   The only exemption is the requirement register, which is governance sourced from the brief
   (published as flag F-006).
2. **Never infer or fill in a value.** Unconfirmed values render as `UNVERIFIED` and are listed
   on the Flagged for Review page.
3. **Derived values are labelled.** A total or tally computed from official values is badged
   `DERIVED` so it is never mistaken for a read value.
4. **Source tiers.** Tier 1 (league/government official) and Tier 2 (primary issuer) may
   populate values. Tier 3 (community) may be referenced but never populates a value.

## Current state

The framework is complete and specified. The **evidence** it needs is not all available:
there is no official odds feed, so no strategy has been backtested, no correlation has been
measured, and no strategy has passed a gate. Every correlation magnitude is deliberately
blank. See `docs/flagged.html` (or the Flagged for Review page on the site) for the full list.
