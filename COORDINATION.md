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
`session-<id>/<task>` branches or merge other sessions' branches. Therefore this session
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
| T01 | Repo inventory, line-by-line review, board creation | in progress | `80731db4-nfl1` | `COORDINATION.md`, `docs/repo-audit.md` | Pending |
| T02 | Official source registry + verification policy | unclaimed | — | `data/sources.json`, `docs/verification.md` | Pending |
| T03 | Full requirements inventory & analysis | unclaimed | — | `data/requirements.json`, `docs/requirements-analysis.md` | Pending |
| T04 | Decision gate: questions / known / unknown / answers / discovery suggestions | unclaimed | — | `data/questions.json`, `docs/decision-gate.md` | Pending |
| T05 | Site improvement suggestions + choose-a-path review section | unclaimed | — | `data/suggestions.json`, `docs/improvement-paths.md` | Pending |
| T06 | Own-lines research, strategy design, validation gates, correlation, skill vs luck | unclaimed | — | `data/strategies.json`, `data/validation-gates.json`, `data/correlations.json`, `docs/strategy-research.md` | Pending |
| T07 | Leaderboard competition + rewards (single bet / parlay / player-prop combos) | unclaimed | — | `data/leaderboard.json`, `docs/competition-rules.md` | Pending |
| T08 | Injury & depth/backup tracking (2nd/3rd/4th string, offense & defense) | unclaimed | — | `data/injuries.json`, `data/depth-chart.json`, `docs/injury-tracking.md` | Pending |
| T09 | Executive summary | unclaimed | — | `docs/executive-summary.md` | Pending |
| T10 | Site build: pages, tables, nav, assets, templates, generator, validators | unclaimed | — | `site/`, `tools/`, `index.html`, `*.html`, `.github/workflows/pages.yml` | Pending |
| T11 | Flagged for Review page + irregularities registry | unclaimed | — | `data/flags.json`, `docs/irregularities.md` | Pending |
| T12 | Final integration: re-verify combined data line by line, link check, build check, deploy | unclaimed | — | `COORDINATION.md`, `tools/verify.py`, `README.md` | Pending |
| T13 | PR to `main`, merge, confirm GitHub Pages deploy, record PR link/result | unclaimed | — | `COORDINATION.md`, `docs/deployment.md` | Pending |

**Shared outputs** (`index.html`, `site/assets/*`, `site/templates/*`, `data/site-config.json`):
reserved for the final integration session (T12). Other sessions must not edit them; log a
request in this file instead.

## Change log

- 2026-11-12 — `80731db4-nfl1`: created board. Repo contained exactly one tracked file,
  `README.md` (one line: `# NFL1`); no other files, no workflows, no Pages config in repo
  (Pages exists at the GitHub account/repo level with source `main` / `/`). Claimed T01.
