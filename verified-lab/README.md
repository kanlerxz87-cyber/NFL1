# `verified-lab/` — independent verification subsystem

Session `a2cea255-nfl1`. **Sub-site:
<https://kanlerxz87-cyber.github.io/NFL1/verified-lab/>**

This is a deliberately independent second implementation of the same brief as
the NFL Decision Lab published at the repository root. It was branched from the
initial commit `5aeb599` and built without sight of the other sessions' work,
then merged additively: **no file published by an earlier session was
overwritten, renamed or deleted.**

It exists to be read *alongside* the main lab, not instead of it. The lab
answers "what does the data support"; this subsystem answers "do the official
pages themselves hold up under audit".

---

## Why it is a subdirectory and not the root

The repository's Pages source is pinned to `main` at `/` and cannot be changed —
`PUT /repos/kanlerxz87-cyber/NFL1/pages` returns **403 "Resource not accessible by
integration"** because the available token lacks `pages:write`. A 20-page site
built at the root would have replaced five of the lab's own published pages
(`index.html`, `executive-summary.html`, `flagged.html`, `suggestions.html`,
`verification.html`).

So this subsystem publishes into a directory no other session owns, with
relative links throughout. Its **CI footprint is nil**:
`scripts/verified/check_site.py` and `scripts/verified/normalize_nav.py` scan
only `index.html` and `pages/`, and `tools/verify.py` uses an explicit page
list. `data/verified/*.tsv` cannot collide with `validate_verified.py`, which
targets `*.csv`.

The output location is one variable — `sitekit.SITE_OUT`, overridable via
`NFL1_SITE_OUT` — so relocating it is a one-line change if the board decides
otherwise.

## Layout

| Path | What it is |
|---|---|
| `src/nfl/` | 16 **standard-library-only** modules. No third-party dependency at all |
| `data/verified/*.tsv` | Hand transcription of nfl.com: 32 standings rows, 254 injury entries, 14 Week 10 games, byes, report status, 8 news items |
| `data/verified/sources.json` | 11 sources with tier, retrieval timestamp and `used_for` |
| `data/reference/teams.csv` | Community mirror, tier `COMMUNITY_MIRROR` — labels and colours only, never on-field values |
| `data/processed/site_data.json` | Generated artifact; the sub-site's single input |
| `content/*.md` | Hand-written prose: executive summary, 22 open questions, 22 suggestions with blank Decision columns, methodology |
| `scripts/build_site.py` | 20 page builders. **Contains no numbers** — every value comes from the JSON artifact |
| `tests/` | 103 unit tests |
| `verified-lab/` | The generated sub-site (20 pages) |

`src/nfl` and `scripts/build_site.py` are standard library only on purpose, so
the whole pipeline and site build run on any Python 3.11+ with nothing
installed.

## Reproduce

```bash
PYTHONPATH=src python3 -m nfl.pipeline        # -> data/processed/site_data.json
PYTHONPATH=src python3 scripts/build_site.py  # -> verified-lab/
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The pipeline is deterministic — every random routine is seeded (`20261112`), so
two runs produce byte-identical output.

---

## What it adds

**A 34-check verification harness** (`src/nfl/verify.py`) over hand-transcribed
cells: **29 PASS, 5 FLAG, 0 FAIL**. It recomputes the tie-aware
`PCT = (W + 0.5·T)/(W+L+T)` with half-up `Decimal` rounding, checks league-wide
balance (136 completed games, W == L == 134, T == 4, PF == PA == 6,267), slate
integrity (14 games, 28 distinct teams, playing ∪ bye == 32), injury vocabulary
over all 254 entries, and that 100% of published rows carry a source URL.

Its strongest check is a genuine cross-source agreement test: **all 28 records
printed beside club logos on the official injury page match the official
standings page exactly**, including both tied clubs.

**Three official cells that contradict themselves**, found by that harness and
never silently corrected:

| Cell | Published | Arithmetic says |
|---|---|---|
| WAS `non_conf` | `1-3-1` (5 games) | 2-5-1 is 8 games, CONF 3-2-1 is 6 ⇒ NON-CONF must be 2 games. The printed value is also character-identical to WAS LAST-5 |
| IND `div` | PCT `0.333` | `1-3-0` ⇒ 0.250 |
| PHI `div` | PCT `0.250` | `1-4-0` ⇒ 0.200 |

Each is published verbatim, excluded from every derived metric, left blank in
the site tables, and flagged with its proof.

**A provenance tier on every value** — `VERIFIED`, `DERIVED`, `MODELED`,
`UNAVAILABLE` — and a refusal path: when a required input is `None` the
dependent output is `None` plus a named blocking input, never a
plausible-looking number.

**Nine validation gates proven bidirectional.** The harness *approves* a
well-formed strategy and *rejects* lookahead, an edge inside the noise, a
confidence interval spanning zero, and profit concentrated in one fold. A gate
that only ever says no is not evidence of anything, so the ability to say yes is
unit-tested.

**Two publication rules enforced by tests rather than by convention:** every
`href` in all 20 pages must resolve, and every row of every table declaring a
`Source` column must carry a link to an official host (300+ rows). Both caught
real defects during development — a naive URL extractor emitting `href="A"`, and
the Source Register printing URLs as text instead of links.

## Headline result

**Zero non-mechanical findings survive multiple-testing control.** 38
correlation tests across 21 signals with Benjamini–Hochberg FDR at α = 0.10: 9
survive, and all 9 are definitional (win percentage against other expressions of
the same game outcomes). At p < 0.05 alone, **1.9 false positives would be
expected by chance**.

13 strategies are catalogued — **0 APPROVED, 13 NOT_STAKEABLE** — and the
leaderboard shows **0 scored / 13 withheld**. Scores are withheld rather than
zeroed so "not yet measured" can never be confused with "measured and
worthless". The four reward tiers are marked `PROPOSAL — needs owner sign-off`.

## Where the two systems disagree, and why

This subsystem publishes **no spread, no total, no win probability and no
edge**. That is not a contradiction of the main pipeline — it is a consequence
of where each one ran.

Inside the Arena sandbox, GitHub **release assets cannot be downloaded**:
`curl -L .../releases/download/...` returns 302 to
`release-assets.githubusercontent.com` and then exits 35 with 0 bytes. So the
nflverse closing lines, depth charts, play-by-play and snap counts that
`pipeline/collect.py` fetches **in GitHub Actions** were never obtainable here.
Unofficial odds aggregators were found and rejected rather than used, and no
official depth-chart endpoint is reachable without a Sportradar API key.

The main lab, running in CI with full network access, has that data. This
subsystem does not, and left the cells blank rather than filling them.

## Open cross-session request

`tools/build.py` regenerates `README.md` from an embedded template, so any
pointer to this subsystem added to the root README will be wiped the next time
that generator runs and is committed. The durable fix belongs in
`tools/build.py`'s README template, which this session does not own. Logged in
`COORDINATION.md` rather than edited.

