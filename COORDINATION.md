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

## Session `73fdd6c4` claim (2026-11-12) — independent verification ("Referee")

Session ID: `73fdd6c4`. Branch: `arena/73fdd6c4-nfl1` (fixed by the workspace; `session-<id>/<task>` branches cannot be created). Base after rebase: `c755a45` (main).

**Why this scope:** on start this session found six other session branches (`690e397b`, `533256e1`, `15e79a53`, `7600ed8b`, `80731db4`, `946c1684`). Between them, the site, data pages, modelling, strategies, correlations, injuries, questions, suggestions, executive summary and integration were already claimed. This session's first (unpushed) claim overlapped those, so it was withdrawn before any work started. The scope below is the part nobody had claimed: checking inputs and published numbers against official sources.

| ID | Task | Status | Owner | File scope |
|---|---|---|---|---|
| V1 | Integrity audit of the historical game-results dataset (`nflverse/nfldata` `games.csv`) against official nfl.com standings (W-L-T, PF, PA per team-season), row by row with official links | in progress | `73fdd6c4` | `referee/data/**`, `referee/analysis/audit_*.py` |
| V2 | Audit of the betting-line fields in that dataset (coverage, internal consistency). No official source exists for closing lines, so results are published as unverified | in progress | `73fdd6c4` | `referee/analysis/lines_*.py`, `referee/data/lines_*.json` |
| V3 | Independent replication of quantitative claims published by other sessions (model accuracy, strategy records, correlations) on the V1-audited data. Read-only: other sessions' files are never edited | in progress | `73fdd6c4` | `referee/analysis/replicate_*.py`, `referee/data/replication_*.json` |
| V4 | Cross-session register: claimed scopes, overlaps, PR state and irregularities, for the owner's review | in progress | `73fdd6c4` | `referee/data/sessions.json` |
| V5 | Self-contained referee pages (not the shared index or navigation) | in progress | `73fdd6c4` | `referee/*.html`, `referee/assets/**`, `referee/tools/**` |

This session edits only `referee/**` and appends to this section of `COORDINATION.md`. It does not touch `index.html`, `pages/`, `styles.css`, `assets/`, `data/`, `docs/`, `pipeline/`, `scripts/`, `src/`, `strategies/`, `site/`, `tools/`, `README.md` or `.github/`.

### Cross-session requests (from `73fdd6c4`)

| Date (UTC) | To | File | Request | Status |
|---|---|---|---|---|
| 2026-11-12 | Final integration session | shared index / navigation | Add one navigation link to `referee/index.html` ("Independent verification") | open |

### Log (`73fdd6c4`)

- 2026-11-12 04:31 UTC — Conflict: this session created `COORDINATION.md` from the empty repo and committed a claim for 13 tasks. `git pull --rebase origin main` then hit an add/add conflict because PR #1 (`690e397b`) had merged its own `COORDINATION.md` to `main` a minute earlier. Resolution: kept the `main` version verbatim (nothing from `690e397b` discarded), dropped this session's overlapping claim, and appended this section with a non-overlapping scope.
