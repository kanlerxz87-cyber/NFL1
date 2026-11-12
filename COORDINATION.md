# Coordination board

| Task | Status | Owner session | Files in scope |
|---|---|---|---|
| Repository audit, evidence-backed NFL decision-support site, strategy research framework, suggestions and review register | done | arena/690e397b-nfl1 | COORDINATION.md, index.html, styles.css, pages/, .github/workflows/pages.yml |

## Session notes

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
