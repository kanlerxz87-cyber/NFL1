# COORDINATION.md — Shared Task Board

Sessions:
- `arena/533256e1-nfl1` (this session) — data tables + dashboard.
- `arena/690e397b-nfl1` — evidence-first framework site (merged to main as PR #1).

## Tasks


- Work is confined to the active Arena branch `arena/690e397b-nfl1`; this branch name is fixed by the workspace.
- Initial repository audit: only a six-byte README (`# NFL`) existed; no app, data, tests, or prior coordination board were present.
- Added static dashboard and category pages: Overview, Evidence, Strategy Lab, Suggestions, and Flagged for Review. Unknown numeric/current NFL values are blank; no performance or injury claims were fabricated.
- Research sources linked in the pages: NFL official injury reports (https://www.nfl.com/injuries/), NFL stats (https://www.nfl.com/stats/), NFL schedule (https://operations.nfl.com/gameday/nfl-schedule/), NFL Football Operations (https://operations.nfl.com/gameday/), official rules (https://operations.nfl.com/the-rules/), and NFL team directory (https://www.nfl.com/teams/). Used official source pages as data-source pointers only, not as proof of uncollected row-level records. No live/lineup/odds data was collected.
- Verification performed: inspected every initial repository file; checked internal anchors/navigation links for all HTML pages using Python; `git diff --check` passed. GitHub Actions workflow repeats local navigation-link checking and uploads static site for Pages deployment.
- Irregularities: source-level official odds not identified; official injury reports do not by themselves establish depth order or replacement usage; no price data, stats dataset, outcomes, correlations, sample sizes, or backtests existed. All are published on Flagged for Review. Legal/prize terms and source licensing remain undecided.
- Site not yet live/deployed from this active feature branch. Deployment workflow triggers on `main` or manual dispatch; PR/merge and GitHub Pages provisioning/CI status remain platform actions, not verified outcomes in this session.

---

## Session `arena/7600ed8b-nfl1` claim (2026-11-12)

Session ID: `7600ed8b-nfl1`. Branch: `arena/7600ed8b-nfl1` (fixed by workspace, cannot create
`session-<id>/<task>` branches). Base after rebase: `c755a45` (main).

Scope claimed (non-overlapping with sessions `690e397b`, `533256e1`, `80731db4`, `946c1684`):

| ID | Task | Status | Owner | File scope |
|---|---|---|---|---|
| Q1 | Quantitative data pipeline (nflverse release ingestion via GitHub Actions; no manual input) | in progress | `7600ed8b-nfl1` | `pipeline/`, `.github/workflows/collect-data.yml`, `data/model/` |
| Q2 | Own-line generation: power ratings, spread/total model, calibration & backtest vs closing lines | in progress | `7600ed8b-nfl1` | `pipeline/model_*.py`, `data/model/lines.json` |
| Q3 | Strategy leaderboard with validation gates, correlation values, luck-removal tests | in progress | `7600ed8b-nfl1` | `pipeline/strategies.py`, `data/model/strategies.json` |
| Q4 | Injury / depth-chart deficiency model (starter → backup attrition) | in progress | `7600ed8b-nfl1` | `pipeline/injuries.py`, `data/model/availability.json` |
| Q5 | Player-prop lines from role + usage distributions | in progress | `7600ed8b-nfl1` | `pipeline/props.py`, `data/model/props.json` |
| Q6 | Question / information / answer ledger + suggestion decision records | in progress | `7600ed8b-nfl1` | `docs/`, `data/decisions.json` |
| Q7 | Final site integration, link checks, PR + merge, Pages verification | in progress | `7600ed8b-nfl1` | `index.html`, `pages/`, `styles.css`, `assets/`, `COORDINATION.md` |

Requests to other sessions: none yet. Other sessions' scopes (`data/teams.csv`,
`data/standings.csv`, `data/injuries.csv`, `docs/repo-audit.md`, `data/requirements.json`,
`data/sources.json`) are NOT edited by this session; if they land on `main` first I will
integrate them read-only at merge time.

---

## Board carried forward from session `533256e1-nfl1` (merged to main, PR #2 / #3)

| ID | Task | Status | Owner | Files | Notes |
|----|------|--------|-------|-------|-------|
| T1 | Repo review & structure | done | arena/533256e1-nfl1 + arena/690e397b-nfl1 | all | Two parallel sessions; merged |
| T2 | COORDINATION.md setup | done | both | COORDINATION.md | merged |
| T3 | NFL teams data (official) | done | arena/533256e1-nfl1 | data/teams.csv, pages/teams.html | 32 teams verified from nfl.com/teams |
| T4 | NFL standings data | done | arena/533256e1-nfl1 | data/standings.csv, pages/standings.html | Snapshot 2026-11-12 from nfl.com |
| T5 | Injury tracking | done | arena/533256e1-nfl1 | data/injuries.csv, pages/injuries.html | Week 10 Thursday game snapshot |
| T6 | Suggestions section | done | both | pages/suggestions.html | merged both tables |
| T7 | Questions/answers | done | arena/533256e1-nfl1 | pages/questions.html | 8 open questions |
| T8 | Strategy/leaderboard | done | both | pages/strategies.html, pages/models.html | validation gates |
| T9 | Executive summary | done | arena/533256e1-nfl1 | pages/executive-summary.html |  |
| T10 | GitHub Pages site | done | both | index.html, pages/*, assets/*, styles.css, .github/workflows/pages.yml | combined |
| T11 | Integration & PR/merge | done | arena/533256e1-nfl1 |  | PR #2 merged to main (ffe1b9d). Pages build success. |

## Sources (session 533256e1)
- Teams: https://www.nfl.com/teams/
- Divisions: https://www.nfl.com/standings/division/2026/REG
- Standings: https://www.nfl.com/standings/league/2026/reg
- Injuries: https://www.nfl.com/injuries/
- Schedule reference: https://www.nfl.com/schedules/2026/by-team

## Sources (session 690e397b)
- NFL injury reports: https://www.nfl.com/injuries/
- NFL stats: https://www.nfl.com/stats/
- NFL schedule: https://operations.nfl.com/gameday/nfl-schedule/
- NFL Football Operations: https://operations.nfl.com/gameday/
- Official rules: https://operations.nfl.com/the-rules/
- NFL team directory: https://www.nfl.com/teams/

## Verification performed
- All 32 teams listed from official nfl.com teams page; divisions cross-checked against division standings.
- Standings values copied from official nfl.com standings page (snapshot 2026-11-12); source link on every row.
- Injury rows copied from official nfl.com injury report (Week 10, Thursday game); source link on every row.
- Internal links checked: no broken links.
- Unverified/missing items flagged on pages/flagged.html and pages/review.html.

## Irregularities
- F6: Standings include unusual records (e.g., Chargers 0-8). Data is as published on nfl.com; flagged for review before any betting use.
- Injury snapshot limited to Thursday game; full week not captured (flagged F1).
- Schedule, player stats, depth charts not captured (flagged F2-F4).
- Source-level official odds not identified; no price data, stats dataset, outcomes, correlations, sample sizes, or backtests existed (session 690e397b).
- Official injury reports do not by themselves establish depth order or replacement usage.

## Log
- 2026-11-12: Session arena/533256e1-nfl1 started. Claimed all tasks as single integration session.
- 2026-11-12: Session arena/690e397b-nfl1 merged PR #1 to main.
- 2026-11-12: Merge conflict encountered on COORDINATION.md, index.html, pages/suggestions.html. Resolving by combining both sessions' work without discarding either.
- 2026-11-12: PR #2 created and merged to main. GitHub Pages build (legacy) succeeded for commit ffe1b9d. Site: https://kanlerxz87-cyber.github.io/NFL1/

