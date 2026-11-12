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
| T11 | Integration & PR/merge | in progress | arena/533256e1-nfl1 |  | final |

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
