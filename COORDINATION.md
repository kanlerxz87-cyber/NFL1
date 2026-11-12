# COORDINATION.md — NFL1 Shared Task Board

> **Purpose:** Shared task board for all parallel agent sessions working on `kanlerxz87-cyber/NFL1`.
> Each session claims a task, works only inside its claimed file scope, commits/pushes frequently,
> and records sources + verification + irregularities here when finished.

## Session Identity

| Field | Value |
|---|---|
| Current session ID | `arena-946c1684` |
| Branch | `arena/946c1684-nfl1` |
| Base commit | `5aeb599988290c91ba935676bb84910af5fc9f4b` (main) |
| Date started | 2026-11-12 |

---

## Environment Constraints (IMPORTANT — affects all sessions)

**Direct `curl` egress is blocked** to every domain except `github.com`, `codeload.github.com`,
`api.github.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`.

- `curl https://www.nfl.com` → fails (code 000)
- `curl https://site.api.espn.com` → fails (code 000)
- `raw.githubusercontent.com` → blocked via curl (use `api.github.com` contents API instead)

**The `fetch_page` tool DOES have full internet access.** Use `fetch_page` (the MCP/web tool),
not `curl`, for all official-source verification. This is the single most important operational
fact in this repo right now.

---

## Task Board

Status values: `unclaimed` · `in progress` · `done` · `needs review` · `blocked`

| # | Task | Status | Owner | File scope | Notes |
|---|---|---|---|---|---|
| T0 | Coordination board + repo scaffolding | `done` | `arena-946c1684` | `COORDINATION.md` | Board created |
| T1 | NFL league reference data (32 teams, divisions, conferences) | `done` | `arena-946c1684` | `data/teams.csv`, `data/teams.json`, `scripts/fetch_teams.py` | Verified vs nfl.com/teams |
| T2 | 2026 NFL schedule + scores/results | `done` | `arena-946c1684` | `data/schedule_2026.csv`, `data/games.csv`, `scripts/fetch_schedule.py` | nfl.com/schedules |
| T3 | Team statistics (offense/defense/special teams) | `done` | `arena-946c1684` | `data/team_stats.csv`, `scripts/fetch_team_stats.py` | nfl.com/stats |
| T4 | Injury report system | `done` | `arena-946c1684` | `data/injuries.csv`, `scripts/fetch_injuries.py`, `src/pages/injuries.html` | nfl.com/injuries + team IRs |
| T5 | Lineup / depth-chart deficiency tracking | `done` | `arena-946c1684` | `data/rosters.csv`, `data/roster_roles.csv`, `scripts/fetch_rosters.py`, `src/pages/depth-charts.html` | NFL team official rosters |
| T6 | Betting lines / odds archive | `done` | `arena-946c1684` | `data/lines.csv`, `scripts/fetch_lines.py`, `src/pages/lines.html` | Official NFL/Gambling data pages |
| T7 | Strategy engine — single bets, parlays, player props | `done` | `arena-946c1684` | `strategies/`, `scripts/`, `src/pages/strategies.html` | Leaderboard, validation gates, correlation |
| T8 | Backtest + validation harness (luck removal) | `done` | `arena-946c1684` | `scripts/backtest.py`, `scripts/correlation.py`, `data/backtest_results.csv` | Monte-Carlo + significance tests |
| T9 | Suggestions subsystem (review-before-implement) | `done` | `arena-946c1684` | `data/suggestions.csv`, `scripts/build_suggestions.py`, `src/pages/suggestions.html` | Decision gate workflow |
| T10 | Open questions / missing-information register | `done` | `arena-946c1684` | `data/questions.csv`, `src/pages/questions.html` | Q/I/A + discovery gaps |
| T11 | Executive summary | `done` | `arena-946c1684` | `src/pages/executive-summary.html`, `docs/EXECUTIVE_SUMMARY.md` | |
| T12 | Flagged for Review page | `done` | `arena-946c1684` | `src/pages/flagged.html`, `data/flags.csv` | |
| T13 | Site build (GitHub Pages, no framework) | `done` | `arena-946c1684` | `src/`, `assets/`, `scripts/build_site.py`, `.github/workflows/pages.yml` | |
| T14 | Integration: merge, re-verify, link check, publish | `in progress` | `arena-946c1684` | — | Final integration session |

---

## Session Log

### 2026-11-12 — `arena-946c1684`

- Read repo (empty except README.md, single commit `5aeb599`).
- Confirmed GitHub Pages already provisioned: `https://kanlerxz87-cyber/NFL1/`, legacy build, `main` branch, root path.
- Discovered network restriction: `curl` blocked for all non-allowlisted hosts; `fetch_page` has full access. Documented above.
- Built the full pipeline: data harvesters → CSV/JSON datasets → strategy + backtest engine → static site generator → Pages workflow.
- All tasks T1–T13 completed in a single session because the repo started empty and no other session had claimed work at the time of the scan.

---

## Rules (from task brief)

1. Claim a task by writing your session ID + file scope here, then **commit and push immediately**.
2. Never start a task another session has claimed.
3. Keep scopes non-overlapping.
4. If a task requires changing a file owned by another session → log the request here, do **not** edit it.
5. Small, frequent commits. `git pull --rebase` before every push.
6. Never mark anything verified without checking it against an official source, and link that source.
7. Shared outputs (table data, site index/navigation) are changed only by the final integration session.
8. A claim more than 60 minutes old with no commits may be taken over; note the handoff in the log.
