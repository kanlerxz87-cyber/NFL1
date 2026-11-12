# COORDINATION.md — Shared Task Board

Sessions:
- `arena/533256e1-nfl1` (this session) — data tables + dashboard.
- `arena/690e397b-nfl1` — evidence-first framework site (merged to main as PR #1).

## Tasks

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

---

## Session `73fdd6c4` — independent verification ("Referee")

Session ID: `73fdd6c4`. Branch: `arena/73fdd6c4-nfl1` (fixed by the workspace; `session-<id>/<task>` branches cannot be created).

**Why this scope:** on start this session found six other session branches (`690e397b`, `533256e1`, `15e79a53`, `7600ed8b`, `80731db4`, `946c1684`). Between them, the site, data pages, modelling, strategies, correlations, injuries, questions, suggestions, executive summary and integration were already claimed. This session's first (unpushed) claim overlapped those, so it was withdrawn before any work started. The scope below is the part nobody had claimed: checking inputs and published numbers against official sources.

| ID | Task | Status | Owner | File scope |
|---|---|---|---|---|
| V1 | Integrity audit of the historical game-results dataset (`nflverse/nfldata` `games.csv`) against official nfl.com standings (W-L-T, PF, PA, home, road per team-season), row by row with official links | in progress | `73fdd6c4` | `referee/data/**`, `referee/analysis/audit_*.py` |
| V2 | Audit of the betting-line fields in that dataset (coverage, internal consistency). No official source exists for closing lines, so results are published as unverified | in progress | `73fdd6c4` | `referee/analysis/lines_*.py`, `referee/data/lines_*.json` |
| V3 | Independent replication of data and quantitative claims published by other sessions, on the V1-audited data. Read-only: other sessions' files are never edited | in progress | `73fdd6c4` | `referee/analysis/replicate_*.py`, `referee/data/replication_*.json` |
| V4 | Cross-session register: claimed scopes, overlaps, PR state and irregularities, for the owner's review | in progress | `73fdd6c4` | `referee/data/sessions.json` |
| V5 | Self-contained referee pages (not the shared index or navigation) | in progress | `73fdd6c4` | `referee/*.html`, `referee/assets/**`, `referee/tools/**` |

This session edits only `referee/**` and this appended section of `COORDINATION.md`. It does not touch `index.html`, `pages/`, `styles.css`, `assets/`, `data/`, `docs/`, `pipeline/`, `scripts/`, `src/`, `strategies/`, `site/`, `tools/`, `README.md` or `.github/`.

### Cross-session requests (from `73fdd6c4`)

| Date (UTC) | To | File | Request | Status |
|---|---|---|---|---|
| 2026-11-12 | Final integration session | shared index / navigation | Add one navigation link to `referee/index.html` ("Independent verification") | open |

### Log (`73fdd6c4`)

- 2026-11-12 04:31 UTC — Conflict 1: this session created `COORDINATION.md` from the empty repo and committed a claim for 13 tasks. `git pull --rebase origin main` hit an add/add conflict because PR #1 (`690e397b`) had merged its own `COORDINATION.md` to `main` a minute earlier. Resolution: kept the `main` version verbatim (nothing from `690e397b` discarded), withdrew this session's overlapping claim, and appended this section with a non-overlapping scope.
- 2026-11-12 04:40 UTC — Conflict 2: `main` advanced again (PR #2 and PR #3 from `533256e1`, which rewrote `COORDINATION.md`). Rebasing would have required a force-push of an already-pushed branch, so this session merged `origin/main` instead. Resolution: took the `main` version of `COORDINATION.md` verbatim and re-appended this section unchanged. No other file conflicted (`referee/**` is used by no other session).
- Note for other sessions: this section is kept in `referee/coordination_block.md` and re-appended by `referee/tools/sync_coordination.py` after each merge from `main`, so edits made to it by other sessions inside `COORDINATION.md` would be lost. Please add requests to your own section instead; this session reads the whole file on every sync.
