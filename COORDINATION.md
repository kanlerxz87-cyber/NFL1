# COORDINATION.md — Shared Task Board

## Sessions

- `arena/533256e1-nfl1` — data tables + dashboard; integration completed and merged.
- `arena/690e397b-nfl1` — evidence-first framework site; merged to main as PR #1.
- `arena/15e79a53-nfl1` — independent post-merge verification; review-only scope, no edits to the prior sessions' product files.

## Tasks

| ID | Task | Status | Owner | Files | Notes |
|----|------|--------|-------|-------|-------|
| T1 | Repo review & structure | done | arena/533256e1-nfl1 + arena/690e397b-nfl1 | all | Two parallel sessions; merged |
| T2 | COORDINATION.md setup | done | both | COORDINATION.md | merged |
| T3 | NFL teams data (official) | done | arena/533256e1-nfl1 | data/teams.csv, pages/teams.html | 32 teams listed; reviewed against official NFL directory/schedule |
| T4 | NFL standings data | done | arena/533256e1-nfl1 | data/standings.csv, pages/standings.html | Snapshot 2026-11-12; values reviewed against NFL standings; ordinal rank needs review |
| T5 | Injury tracking | done | arena/533256e1-nfl1 | data/injuries.csv, pages/injuries.html | Week 10 Thursday game snapshot only |
| T6 | Suggestions section | done | both | pages/suggestions.html | Merged proposal tables; per-row official links still need review |
| T7 | Questions/answers | done | arena/533256e1-nfl1 | pages/questions.html | 8 open questions; per-row sources still need review |
| T8 | Strategy/leaderboard | done | both | pages/strategies.html, pages/models.html | Validation framework; no measured edge, correlation, or leaderboard result |
| T9 | Executive summary | done | arena/533256e1-nfl1 | pages/executive-summary.html | Summary table source links need row-level review |
| T10 | GitHub Pages site | done | both | index.html, pages/*, assets/*, styles.css, .github/workflows/pages.yml | Combined and deployed |
| T11 | Integration & PR/merge | done | arena/533256e1-nfl1 |  | PR #2 merged; Pages workflow succeeded |
| T12 | Independent post-merge source/link/content/deployment review | done | arena/15e79a53-nfl1 | docs/review/merged-site.md | Findings, official references, row checks, and follow-up requests recorded; no product files edited |
| T13 | Apply post-merge source, table-citation, stale-content, and flagged-item corrections | unclaimed | — | index.html, pages/*.html, .github/workflows/pages.yml | Follow-up request from T12; see “Post-merge review requests.” Do not start until claimed. |

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

## Verification performed by integration sessions

- The 32 team rows are listed on the official NFL team directory; division assignments were cross-checked against NFL division standings.
- Standings values were captured from the official NFL league-standings page (snapshot 2026-11-12); each displayed standings data row links to that page.
- Injury rows were captured from the official Week 10 Thursday report; each displayed injury data row links to the NFL injury-report entry point.
- Internal links were checked by the site build and by the independent review; 0 missing local page/asset references were found across 12 HTML files.
- Unverified/missing items are presented on the site review pages; T12 identified stale/duplicated review content and additional per-row source gaps (below).

## Irregularities recorded by integration sessions

- F6: Standings include unusual records (e.g., Chargers 0-8). The value is as published on nfl.com; do not infer that it is simulated or erroneous.
- Injury snapshot is limited to the Thursday game; full week not captured.
- Schedule, player stats, depth charts, odds, outcomes, correlations, sample sizes, and backtests are not all present on the deployed main site.
- Source-level market access, licensing, and historical odds coverage remain unresolved. NFL injury reports do not by themselves establish depth order or replacement usage.

## Post-merge review and requests (session 15e79a53)

- Full review: `docs/review/merged-site.md`. It records verified official source links, row/value checks, deployment status, exact corrections requested, and proposed strategy design. No current line, odds value, injury effect, correlation, or performance result was invented.
- Direct fetches of `https://operations.nfl.com/gameday/nfl-schedule/`, `https://operations.nfl.com/gameday/`, and `https://operations.nfl.com/the-rules/` returned the NFL site's 404 page. Verified replacements are `https://www.nfl.com/schedules/2026/by-week/week-10`, `https://www.nfl.com/games/commanders-at-giants-2026-reg-10`, and `https://operations.nfl.com/rules-officiating/2026-nfl-rulebook` respectively.
- All 32 NFL standings records and the 20 Thursday injury rows were checked against official pages. `rank=1..32` is not an explicit NFL source field; leave blank or label it as site row order. Injury rows should cite the week-specific report and preserve report/capture time separately from game date.
- Findings for T13: old evidence/review pages now contradict the added data; multiple analysis/Q&A/suggestion rows lack row-level official citations; the weather row links to stats; F6's “synthetic/simulated” phrasing is unsupported; actual backup order and correlation values remain unavailable. See T13 scope and detailed file/row findings in the review report.
- Core verified sources: NFL teams (`https://www.nfl.com/teams/`), standings (`https://www.nfl.com/standings/league/2026/reg`), injury report (`https://www.nfl.com/injuries/league/2026/reg10`), schedule (`https://www.nfl.com/schedules/2026/by-week/week-10`) and game center (`https://www.nfl.com/games/commanders-at-giants-2026-reg-10`), player stats (`https://www.nfl.com/stats/`), Next Gen Stats (`https://operations.nfl.com/game-operations-logistics/technology/performance-tracking-data-next-gen-stats`), NFL's 2026 sportsbook/integrity announcement (`https://www.nfl.com/news/nfl-draftkings-fanduel-fanatics-sports-betting-partners`), the NFL–Genius Sports data-feed extension (`https://www.nfl.com/news/nfl-extends-strategic-partnership-with-genius-sports`), and the official 2026 rulebook (`https://operations.nfl.com/rules-officiating/2026-nfl-rulebook`).
- Validation-method references: scikit-learn's time-ordered split documentation (`https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html`), probability-calibration guide (`https://scikit-learn.org/stable/modules/calibration.html`), and metrics guide (`https://scikit-learn.org/stable/modules/model_evaluation.html`).
- A separate branch `arena/7600ed8b-nfl1` contains an additional data-collection workflow and generated model files; it is outside T12/T13 and has not been independently audited or merged by this session.

## Log

- 2026-11-12: Session arena/533256e1-nfl1 started and completed the data/dashboard integration tasks.
- 2026-11-12: Session arena/690e397b-nfl1 merged PR #1 to main.
- 2026-11-12: PR #2 merged the combined site to main; Pages build succeeded. PR #3 recorded the integration result.
- 2026-11-12: Session arena/15e79a53-nfl1 initially inspected the base before PR #1 had landed and pushed a task claim. `git pull --rebase origin main` then produced a coordination-board conflict because main already contained PR #1; a later rebase encountered the updated board after PR #2/#3. In each case the latest main board and completed sessions' notes were preserved. This session changed only the shared board and its own `docs/review/merged-site.md`; it did not change the earlier sessions' product files.
- 2026-11-12: T12 completed. The independent review checked official NFL team, standings, injury, schedule, stats, data-distribution, and rule references; all 32 standings rows and 20 stored Thursday injury entries; every review-table source link; local references; workflow status; and the published Pages endpoint. Findings and T13 correction requests are in `docs/review/merged-site.md`.
- 2026-11-12: GitHub Pages API reported `built` for public URL `https://kanlerxz87-cyber.github.io/NFL1/`; deployment workflow run 43155502970 and Pages build run 43155502654 completed successfully. A non-cache-busted fetch returned stale README text while a cache-busted fetch returned the current index; verify in a normal browser before attributing this to a deployment fault.
- 2026-11-12: Review findings and coordination status were recorded on `arena/15e79a53-nfl1`; T13 remains unclaimed so the reviewed site owners can apply corrections in a separately claimed task.
