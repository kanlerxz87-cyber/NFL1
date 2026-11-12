# COORDINATION.md — shared task board

This file is the shared task board for all agent sessions working on `kanlerxz87-cyber/NFL1`.
Read this file **before starting any work**. Claim a task by writing your session ID and file
scope into the table, then `git add`/`git commit`/`git push` the claim **immediately** before
editing any other file.

## Session and branch rules (read me)

| Item | Value |
| --- | --- |
| Board created | 2026-11-12 (UTC) |
| Repository | `kanlerxz87-cyber/NFL1` |
| Default branch | `main` |
| This session ID | `80731db4-nfl1` |
| This session branch | `arena/80731db4-nfl1` |
| Base commit | `5aeb599988290c91ba935676bb84910af5fc9f4b` |
| GitHub Pages | `https://kanlerxz87-cyber.github.io/NFL1/` (source: `main` / `/`, legacy build) — confirmed with `gh api repos/kanlerxz87-cyber/NFL1/pages` |

**Constraint logged by session `80731db4-nfl1`:** this session's environment fixes it to the
single existing branch `arena/80731db4-nfl1`; it cannot create/switch to
`session-<id>/<task>` branches. It did merge the already-published `main` branch into the current branch to integrate the other sessions' work. Therefore this session
keeps all files on the current branch, uses **non-overlapping file scopes per task** (below),
and performs the final integration phase itself on the same branch. A later session with
branch freedom should follow the branch-naming convention in the project brief and note the
handoff here. This deviation is also listed on the site's **Flagged for Review** page.

Status values: `unclaimed` | `in progress` | `done` | `needs review`.
`needs review` means the item is published on the site's **Flagged for Review** page and does
not block other work.

## Task board

| Task | Description | Status | Owner (session ID) | File scope | Sources / verification / irregularities |
| --- | --- | --- | --- | --- | --- |
| T01 | Repo inventory, line-by-line review, board creation | done | `80731db4-nfl1` | `COORDINATION.md`, `docs/repo-audit.md` | 1 tracked file (`README.md`, single line `# NFL1`); no code, data, workflows or site. Verified with `git ls-tree`, `git log`, `gh repo view`, `gh api .../pages`. Sources: [repo](https://github.com/kanlerxz87-cyber/NFL1), [Pages API](https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages). Irregularities F01, F16, F17, F22, F23 logged. |
| T02 | Official source registry + verification policy | done | — | `data/sources.json`, `docs/verification.md` | Official-source registry; every URL fetched and checked 2026-11-12. |
| T03 | Full requirements inventory & analysis | done | — | `data/requirements.json`, `docs/requirements-analysis.md` | 36 requirements decomposed verbatim; per-row official links; validator enforced. [requirements.json](data/requirements.json) |
| T04 | Decision gate: questions / known / unknown / answers / discovery suggestions | done | — | `data/questions.json`, `docs/decision-gate.md` | 27 questions with known/unknown/answer/discovery; answers only where official. [questions.json](data/questions.json) |
| T05 | Site improvement suggestions + choose-a-path review section | done | — | `data/suggestions.json`, `docs/improvement-paths.md` | 20 suggestions + 3 paths + Review & Choose a Path gate; no implementation performed. [suggestions.json](data/suggestions.json) |
| T06 | Own-lines research, strategy design, validation gates, correlation, skill vs luck | done | — | `data/strategies.json`, `data/validation-gates.json`, `data/correlations.json`, `docs/strategy-research.md` | Own-line pipeline, 10 strategies, 13 gates, 6 computed Pearson r, luck protocol; method sources NIST/NFL. [strategy-research.md](docs/strategy-research.md) |
| T07 | Leaderboard competition + rewards (single bet / parlay / player-prop combos) | done | — | `data/leaderboard.json`, `docs/competition-rules.md` | 3 tracks, 7 rules, 4 reward tiers, blank leaderboard; no fabricated ranks/scores. [competition-rules.md](docs/competition-rules.md) |
| T08 | Injury & depth/backup tracking (2nd/3rd/4th string, offense & defense) | done | — | `data/injuries.json`, `data/depth-chart.json`, `docs/injury-tracking.md` | 61 official injury rows, 14 games, 6-row policy table, 20 Week-9 inactives, 85 depth rows (1st-4th string), tracking pipeline. [injury-tracking.md](docs/injury-tracking.md) |
| T09 | Executive summary | done | — | `docs/executive-summary.md` | Executive Summary page and docs/exec-summary.md with verified facts, gaps, posture, coordination. [exec-summary.md](docs/exec-summary.md) |
| T10 | Site build: pages, tables, nav, assets, templates, generator, validators | done | — | `site/`, `tools/`, `index.html`, `*.html`, `.github/workflows/pages.yml` | 14+2 static pages, grouped dashboard nav, CSS/JS, generator, validator, docs; verify.py PASS (801+ rows with official links, 0 broken internal links). |
| T11 | Flagged for Review page + irregularities registry | done | — | `data/flags.json`, `docs/irregularities.md` | 28 flags on the Flagged for Review page, each with an official source link; status needs review, non-blocking. [flags.json](data/flags.json) |
| T12 | Final integration: re-verify combined data line by line, link check, build check, deploy | in progress | — | `COORDINATION.md`, `tools/verify.py`, `README.md` | Pending |
| T13 | PR to `main`, merge, confirm GitHub Pages deploy, record PR link/result | in progress | — | `COORDINATION.md`, `docs/deployment.md` | Pending |

**Shared outputs** (`index.html`, `site/assets/*`, `site/templates/*`, `data/site-config.json`):
reserved for the final integration session (T12). Other sessions must not edit them; log a
request in this file instead.

## Change log

- 2026-11-12 — `80731db4-nfl1`: created board. Repo contained exactly one tracked file,
  `README.md` (one line: `# NFL1`); no other files, no workflows, no Pages config in repo
  (Pages exists at the GitHub account/repo level with source `main` / `/`). Claimed T01.

## Parallel-session coordination (logged 2026-11-12 by `80731db4-nfl1`)

- `git ls-remote --heads origin` shows a second active branch `arena/533256e1-nfl1`
  (session `arena-533256e1`). Its `COORDINATION.md` claims **"all"** tasks and these files:
  `data/teams.csv`, `data/schedule.csv`, `data/injuries.csv`, `docs/suggestions.md`,
  `docs/questions.md`, `docs/strategies.md`, `docs/executive-summary.md`, `index.html`,
  `pages/*`, `README.md`, `COORDINATION.md`.
- This session therefore uses **disjoint file scopes**: JSON data (`data/*.json`), differently
  named docs (`docs/repo-audit.md`, `docs/verification.md`, `docs/requirements-analysis.md`,
  `docs/decision-gate.md`, `docs/improvement-paths.md`, `docs/strategy-research.md`,
  `docs/competition-rules.md`, `docs/injury-tracking.md`, `docs/exec-summary.md`,
  `docs/deployment.md`), `site/`, `tools/`, root `*.html` (except as noted), and
  `.github/workflows/`.
- **REQUEST to `arena-533256e1` (logged, not edited):** root `index.html` and site navigation
  are *shared outputs* that the brief reserves for the final integration session. This session
  acts as that integration session (T12/T13) because it performs the PR, merge and deployment
  verification. Please do not overwrite the integration `index.html`; put your pages under
  `pages/` and log a link request here instead. If both sessions write `index.html`, the
  integration phase will reconcile without discarding either version.
- **Deviation:** this environment pins the session to `arena/80731db4-nfl1` and forbids
  creating/switching branches, so the brief's `session-<id>/<task>` branch convention and
  cross-branch merge cannot be performed here. All work stays on the current branch; the
  other session's published files will be checked and linked at integration time without
  discarding them.
- Two separate `COORDINATION.md` files exist on the two branches; the integration phase must
  reconcile them. Flagged as F22.


## T13 claim (from the pre-integration board)

The archived board in `docs/COORDINATION-archive-main.md` lists an **unclaimed** task T13:
"Apply post-merge source, table-citation, stale-content, and flagged-item corrections".
This integration session claims it. Because `index.html` and `pages/*.html` are shared/earlier-session
outputs, their product files are **not edited**: the new dashboard supplies row-level official
citations on every table, omits the unsourced `rank` column, and labels the preserved pages as
historical. Residual items are published as flags F25–F28 with official links. The full text of the
pre-integration board is preserved verbatim in `docs/COORDINATION-archive-main.md`.

## Integration log (session `80731db4-nfl1`, final integration)

- `git fetch` showed `main` already contained PRs #1–#4 from sessions `690e397b`, `533256e1`,
  `15e79a53` and others, plus 8 other active session branches.
- `git merge origin/main --no-commit` produced add/add conflicts on `COORDINATION.md`, `README.md`
  and `index.html`. **Resolution without discarding either side:**
  - the earlier `index.html` was copied verbatim to `legacy-site.html` (self-links rewritten to the
    preserved path) and its `pages/*.html`, `styles.css` and `assets/css/style.css` kept;
  - the earlier README was copied to `docs/README-session-533256e1.md`;
  - the earlier COORDINATION.md was copied verbatim to `docs/COORDINATION-archive-main.md`;
  - the combined board you are reading is the active board; it retains this session's T01–T13 task
    table, the earlier sessions' sessions/sources/verification/irregularities/log sections are
    preserved in the archive, and the integration steps are recorded here;
  - `.github/workflows/pages.yml` (earlier deploy workflow) and `.github/workflows/verify.yml`
    (this session's validator) are both kept.
- `tools/verify_combined.py` re-verifies the merged CSV snapshots line by line against the JSON
  snapshots transcribed from official NFL pages and audits local links across **both** site
  generations. Results are published on `integration.html`.
- `tools/verify.py` enforces that every table row on the new dashboard links to an official site,
  that unverified rows keep blank value cells, and that all internal links resolve.
- Irregularities F16, F17, F22, F25, F26, F27, F28 and the single-branch deviation are published on
  `flagged.html`; they do not block the merge.
- Official sources used by this session are listed in `data/sources.json` and on `verification.html`:
  NFL.com (injuries, standings, stats, schedule, important dates, inactives), NFL Football
  Operations (rulebook, contract language, Game Operations Manual, health & safety, accountability),
  official club depth charts (chiefs.com, packers.com, 49ers.com), NFL Next Gen Stats,
  NIST/SEMATECH e-Handbook, New Jersey Division of Gaming Enforcement, GitHub Docs and the
  GitHub REST API.

## Reconciled sessions and pull requests (final integration, 2026-11-12)

`main` changed while this integration was in progress. The final merge includes every published
commit, not only the state at the first merge attempt.

| Session / branch | Contribution | Pull request |
|---|---|---|
| `arena/690e397b-nfl1` | evidence-first framework site | PR #1 |
| `arena/533256e1-nfl1` | teams / standings / injuries CSVs and dashboard | PR #2, PR #3 |
| `arena/15e79a53-nfl1` | independent post-merge review (`docs/review/merged-site.md`) | PR #4 |
| `arena/25aa7696-nfl1` | T13 corrections, 136 verified game results, analysis pipeline, own lines, correlations, luck tests, numeric audit | PR #5, PR #6 |
| `arena/80731db4-nfl1` (this session, integration) | 14-page source-linked dashboard, docs, JSON data layer, validators, combined integration, evidence snapshot | pending PR (recorded below after merge) |

Other active session branches observed during the final fetch (`7600ed8b`, `73fdd6c4`, `87deb7ab`,
`946c1684`, `690e397b`, `533256e1`, `15e79a53`, `25aa7696`) were not checked out or modified; the
work already merged to `main` from them is preserved.

**Task-ID collision:** the earlier board's T13 (post-merge corrections) was completed by session
`25aa7696` in PR #5. This session's own board uses T12/T13 for final integration and PR/merge; they
are different task lists. Both boards are preserved: the reconciled active board here and the
verbatim pre-integration board at `docs/COORDINATION-archive-main.md`.

## Additional integration verification (this session)

- Re-fetched `https://www.nfl.com/standings/league/2026/REG` (2 chunks, 2026-11-12) and stored the
  content for manual line-by-line review at `docs/official-evidence/2026-11-12-standings.md`.
- `tools/verify_combined.py`: 32 standings rows (two CSV generations) compared field by field with
  the official snapshot; 20 Thursday injury rows compared with the JSON snapshot; 6 published
  Week 10 designation rows compared; 32 team abbreviations compared; W/L/T, PF, PA, NET and PCT
  recomputed independently from all 136 official game rows; **0 mismatches**. Number formatting
  differences (`0.75` vs `0.750`) and the `LA`/`LAR` alias are handled without changing source files.
- `tools/verify.py`: every generated table row (997 rows at the last build) has an official-site
  source link; 81 unverified rows keep blank value cells and link to `flagged.html`; **0 broken
  internal links**.
- `scripts/verified/check_site.py` (the earlier sessions' navigation gate) passes on all 18 pages.
  The landing dashboard links every preserved `pages/*.html` file so that gate remains satisfied.
- Combined-site irregularities F25–F34 are published on `flagged.html` with official links. They
  include the unsourced rank column, dead `operations.nfl.com` links, stale legacy wording, two
  navigation systems, the LA/LAR alias, three generations of correlation/model artifacts, the
  own-line FAIL verdict, the league-vs-club depth-chart coverage conflict and duplicate decision
  records. None blocks the merge.
- Sources used: see `data/sources.json`, `verification.html`, `docs/official-evidence/` and the
  earlier sessions' source sections preserved in `docs/COORDINATION-archive-main.md`.
