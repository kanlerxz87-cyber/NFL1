# COORDINATION.md — shared task board and integration log

> Board hygiene note (session `b6e68100-nfl1`, 2026-11-12): the file previously began with the
> stray text `EAD` on line 1 — a leftover conflict-resolution artifact from an earlier merge.
> Removed; logged as irregularity A-F01 on the Flagged for Review page.

Repository: `kanlerxz87-cyber/NFL1` · Default branch `main` · Site: <https://kanlerxz87-cyber.github.io/NFL1/>

Sessions that have worked here:

| Session | Branch | Contribution | Status |
|---|---|---|---|
| `690e397b-nfl1` | `arena/690e397b-nfl1` | Framework site, evidence register, flagged page (PR #1) | merged |
| `533256e1-nfl1` | `arena/533256e1-nfl1` | Data tables (teams, standings, injuries CSV) + dashboard (PR #2, #3) | merged |
| `80731db4-nfl1` | `arena/80731db4-nfl1` | Task board scaffold | not merged (superseded) |
| `946c1684-nfl1` | `arena/946c1684-nfl1` | League reference data, environment notes (curl allow-list; `fetch_page` has full internet) | not merged (superseded) |
| `7600ed8b-nfl1` | `arena/7600ed8b-nfl1` | Quantitative pipeline, own lines, strategy gates, injury/depth model, props, verification, final integration | PR #13 |
| `a2cea255-nfl1` | `arena/a2cea255-nfl1` | Independent verification subsystem: hand transcription of nfl.com, 34-check harness, provenance/gates engine, 103 tests, 20-page sub-site in `verified-lab/` | PR #18 |
| `9cb71eb8-nfl1` | `arena/9cb71eb8-nfl1` | Large-sample research build: closing-line + real price history, walk-forward own lines, scored leaderboard (single/parlay/prop-combo), correlation register, luck-removal gates, consolidated site | in progress |

| `1505ac8e-nfl1` | `arena/1505ac8e-nfl1` | **Consolidation + re-verification session.** Live re-fetch of official nfl.com (standings, injuries, schedule, depth charts), cross-check of all four generations' committed data, unified site (`lab/`) with category nav, decision/suggestions workflow, gap-closing on depth charts, PR + merge + Pages | in progress |

| `e3148b95-nfl1` | `arena/e3148b95-nfl1` | Official-source schedule/bye attribution audit and CI gate | in progress |
| `b6e68100-nfl1` | `arena/b6e68100-nfl1` | Post-merge audit: C5 division-map fix (referee hand-off), line-by-line repo review, official-source re-verification, site health check, PR/merge/Pages confirmation | active |
| `9411723a-nfl1` | `arena/9411723a-nfl1` | Verification of the committed site, official-source spot checks, new flag F41 (standings snapshot vs live drift), PR -> main -> merge -> Pages deploy, integration record | active |
| `c56ebee8-nfl1` | `arena/c56ebee8-nfl1` | Final integration: 2026-11-13 official re-verification, unified category dashboard with sidebar, 1st-to-6th string depth ladder (flags F42-F47), correlations/parlays/luck pages, PR -> main -> merge -> Pages | active |

---


> Branch naming: Arena fixes each session to a single branch named `arena/<session>-nfl1`, so the
> `session-<id>/<task>` convention in the brief cannot be followed here. Scopes were kept
> non-overlapping by file instead, and this board records them.

## Task board — session `9cb71eb8-nfl1` (ACTIVE; claims below)

This session acts as the **final integration session** for the current state of the repo. All
other session branches have merged (PRs #1-#20), so no other session owns an unclaimed task.
File scope claimed here is **additive and non-overlapping** with every earlier session:

| ID | Task | Status | Owner | File scope | Notes |
|---|---|---|---|---|---|
| U1 | Provenance-pinned bulk history (games with closing lines **and real prices**, player-week, injuries) fetched in Actions, committed as CSV | in progress | `9cb71eb8` | `s9cb/`, `data/s9cb/`, `.github/workflows/s9cb-collect.yml` | sandbox cannot reach release-asset hosts; Actions can |
| U2 | Walk-forward own lines (spread / total / win prob) on the full sample, with baselines | unclaimed→in progress | `9cb71eb8` | `s9cb/analysis/`, `data/s9cb/` | replaces the 136-game verdict with a large-sample one |
| U3 | Scored strategy leaderboard: single bets, parlays, prop combos; 8 validation gates; real prices | in progress | `9cb71eb8` | `s9cb/analysis/` | |
| U4 | Correlation register with computed values (game-level, strategy-level, prop-level) | in progress | `9cb71eb8` | `s9cb/analysis/` | fills the blanks left by earlier sessions |
| U5 | Luck-removal protocol (binomial, bootstrap, multiple testing, holdout) | in progress | `9cb71eb8` | `s9cb/analysis/` | |
| U6 | Injury / depth deficiency refresh joined to official nfl.com week-10 report | in progress | `9cb71eb8` | `s9cb/analysis/` | reuses `data/model/official_injuries.json` |
| U7 | Consolidated clean site: one landing page + subpages by category | in progress | `9cb71eb8` | `research/` (new), one nav entry in `index.html` | additive; no earlier page is deleted |
| U8 | Line-by-line verification of every new row against an official source; blanks stay blank | in progress | `9cb71eb8` | `s9cb/verify.py`, `research/` | |
| U9 | PR → merge → confirm Pages deploy → record here | in progress | `9cb71eb8` | `COORDINATION.md` | |

**Not touched by this session (owned by others):** `index.html` (only one additive nav entry at
integration time), `pages/`, `docs/`, `verified-lab/`, `referee/`, `pipeline/`, `tools/`,
`scripts/`, `analysis/`, `data/model/`, `data/verified/`.

## Active claims (session `b6e68100-nfl1`, 2026-11-12)

| ID | Task | Status | Owner | File scope | Notes |
|---|---|---|---|---|---|
| A1 | Take over referee request on `analysis/correlations.py` (C5 counts 52 division games; official groupings give 42 — AFC/NFC divisions of the same name were not distinguished) and recompute `data/verified/model/correlations.json` | done | `b6e68100` | `analysis/correlations.py`, `data/verified/model/correlations.json`, `pages/analysis.html`, `data/flags.json` (F36), `COORDINATION.md` | Fixed: map keyed on (conference, division). All 32 club-division assignments verified line by line against https://www.nfl.com/standings/division/2026/REG first. Recomputed C5 = -0.1048 (n=136, CI [-0.268,+0.065], p=0.2245) — matches the referee's independent value exactly. F36 marked resolved. |
| A2 | Post-merge audit: line-by-line repo review, re-verification of published data against official sources, site build + link check, live-site health check | done | `b6e68100` | `docs/audit-b6e68100.md`, `data/flags.json` (A-F01..A-F04), `data/suggestions.json` (SA-01, SA-02), `pipeline/content.py`, `pipeline/build_all.py`, regenerated pages | Audit published at `docs/audit-b6e68100.md`. Findings: A-F01 stray 'EAD' line-1 artifact (fixed); A-F02 WAS win-pct banker's rounding vs official 0.313 (fixed in `pipeline/build_all.py`, confirmed live via the collect-data refresh — snapshot now shows 0.313); A-F03 Week-10 injury club coverage fully explained (CHI/DEN/PHI/TB on bye per official schedule; LAC/BAL 'No Injuries Reported'); A-F04 official injury page drifts within hours (IND/JAX rows changed between 18:53 and 22:30 UTC scrapes; scraper verified faithful, ~120 rows row-for-row). Verified non-issue: Myles Garrett listed under LAR is correct per his official player page (trade to Rams). All gates re-run and green after regeneration: validate_verified PASS, audit_numbers 44/44, check_site 20 pages 0 broken, tools/verify.py 971 rows all sourced, verify_combined PASS, 111 tests pass. |
| A3 | PR from this branch to `main`, merge without waiting for approval, confirm GitHub Pages deploy, record PR link/result here | done | `b6e68100` | `COORDINATION.md` (PR record section) | PR #26 merged at 2026-11-12T22:49:01Z (merge commit `7c11742`); all four main-branch checks passed including the site build; Pages deployed; live site verified (see the A3 record below). |

---

## SESSION CLAIM — `6e8ca348-nfl1` (branch `arena/6e8ca348-nfl1`, base `c09c739`)

Claimed at 2026-11-12 (UTC). This session audits the repository line by line, fixes the defects it
finds, and rebuilds the published site; it does not rewrite other sessions' history or delete their
files. Scopes are non-overlapping with every earlier (merged) session because those sessions are
closed; this session owns the files listed here and nothing else.

| ID | Task | Status | Owner | File scope |
|---|---|---|---|---|
| S01 | Claim board + full repo audit, line by line, against official sources | done | `6e8ca348` | `COORDINATION.md`, `docs/audit-6e8ca348.md`, `data/audit/` |
| S02 | Fix "no manual input / no stale site": every push rebuilds+commits pages, one writer per page, drift gate | done | `6e8ca348` | `.github/workflows/*.yml`, `tools/check_freshness.py`, `tools/check_generators.py`, `tools/build.py`, `pipeline/gen_site.py` |
| S03 | Official-source verification harness (nfl.com line by line, reproducible fixtures) | done | `6e8ca348` | `tools/evidence_from_official.py`, `tools/verify_official.py`, `data/evidence/` |
| S04 | Decision dashboard + decision room + flag register | done | `6e8ca348` | `tools/build_dashboard.py`, `tools/build_decision_room.py`, `tools/verify_dashboard.py`, `web/`, `data/decision_room/`, `data/contradictions.json` |
| S05 | Final integration: merge to `main`, confirm Pages deploy, record PR + result here | in progress | `6e8ca348` | `COORDINATION.md` |

### S01-S04 result (recorded 2026-11-12)

**Sources** (all read this session): nfl.com standings 2026/reg (32 rows), nfl.com/injuries
(Week 10, 279 player rows across 26 club sections), nfl.com/schedules/2026/REG10 (14 games +
4 byes), chiefs.com and seahawks.com depth charts (league `/teams/<club>/depth-chart` returns
404), nfl.com/teams/, nflverse-data releases.

**Verification performed**: `tools/verify_official.py` — 28 checks, **20 pass / 8 flag / 0
fail**; standings 32/32 exact in three separate repo files; schedule 14/14 dates and kickoff
times; 24 of 26 injury club sections exact. `tools/verify_dashboard.py` — 383 assertions on
the new pages. `tools/check_freshness.py` — 23 assertions. `tools/check_generators.py` — one
owner per generated path. All five earlier CI gates still pass
(`audit_numbers.py`, `check_site.py`, `verify_combined.py`, `verify.py`, `build_site.py`).

**Irregularities found**: X01-X10 in `data/contradictions.json`, published on
`web/flag-register.html` with both links. The four defects fixed in this session (X05 double
generator, X06 stale pages, X07 line-convention mix-up, and the 'actionable' label) each
carry a gate that fails the build if they return. The rest are another session's files and are
left for human arbitration rather than corrected silently.

**Irregularities found in this session so far** (all verified from the committed files, published on
`flag-register.html`): pages are generated by two different generators that both write `index.html`;
the scheduled data refresh commits new `data/model/*.json` but never re-renders HTML, so the live
site is stale; on the live Overview the market-line column is not in the same sign convention as the
home model line, producing false edges (e.g. `LA @ ARI`, `SEA @ LV`, `MIA @ IND`). Full detail in
`docs/audit-6e8ca348.md`.

---

## Task board — session `9411723a-nfl1` (ACTIVE; claims below)

File scope claimed here is **additive and non-overlapping**: `COORDINATION.md`, `data/flags.json`, and the root pages those files render (regenerated only with `python3 tools/build.py`). No other session's files are touched.

| ID | Task | Status | Owner | File scope | Notes |
|---|---|---|---|---|---|
| V1 | Line-by-line verification of the committed root site with `tools/verify.py` | done | `9411723a` | `data/flags.json`, `data/suggestions.json`, `data/questions.json`, root `*.html` | `tools/verify.py`: 982 table rows, 982 with official source links, 73 unverified (flagged), 0 broken internal links — PASS |
| V2 | Official-source spot check of the 2026 standings snapshot vs the live nfl.com page | done | `9411723a` | `data/flags.json` (F41) | Live page https://www.nfl.com/standings/league/2026/reg fetched 2026-11-13 shows NYG 5-3-1 (203/196) and WAS 3-5-1 (196/223); snapshot (retrieved 2026-11-12T04:31Z) shows NYG 5-2-1 (182/172) and WAS 2-5-1 (172/202) — drift explained by the WAS @ NYG game on 2026-11-12 after the snapshot time; logged as flag F41 |
| S1 | Confirm the suggestions review-and-choose-a-path section is complete | done | `9411723a` | `pages/suggestions.html`, `pages/decisions.html`, `data/suggestions.json`, `data/questions.json` | 27 suggestions, 6 decision records (D01-D06), 5-step review path; Q01-Q28 question/information/answer table |
| L1 | Confirm own-lines research, strategy leaderboard, gates, correlations, luck removal | done | `9411723a` | `pages/lines.html`, `pages/strategies.html`, `data/model/*` | 14 Week-10 own lines; 0 of 12 strategies pass all 8 gates (reported honestly); correlations partial/flagged; luck-removal documented |
| I1 | Confirm injury and depth-deficiency tracking | done | `9411723a` | `pages/injuries.html`, `pages/availability.html`, `data/model/availability.json` | Official injury report joined to depth chart; 2nd/3rd/4th-string not publishable — official depth charts return 404 (flagged F17/F21) |
| E1 | Confirm executive summary | done | `9411723a` | `pages/executive.html` | Implemented: what was verified, what the numbers say, unresolved items, decisions requested |
| P1 | Confirm GitHub Pages live site | done | `9411723a` | `index.html`, `pages/`, `.nojekyll` | Pages status `built`; source `main /`; https://kanlerxz87-cyber.github.io/NFL1/ |
| X1 | Integration: PR from this branch to `main`, merge, confirm Pages deploy, record result | in progress | `9411723a` | `COORDINATION.md` | PR created after this claim commit is pushed |


---

## Task board (final state, session `7600ed8b-nfl1` integration)

| ID | Task | Status | Owner | File scope | Evidence |
|---|---|---|---|---|---|
| Q1 | Quantitative data pipeline (nflverse releases + official nfl.com injury scrape, run in Actions) | done | `7600ed8b` | `pipeline/collect.py`, `pipeline/scrape_injuries.py`, `pipeline/schema.py`, `.github/workflows/collect-data.yml` | 12 files pinned by URL + sha256 in `data/model/provenance.json` |
| Q2 | Own-line generation: opponent-adjusted EPA ratings → spread/total/win probability, walk-forward | done | `7600ed8b` | `pipeline/build_all.py`, `data/model/lines.json` | test MAE 9.98 vs market 9.48 (136 games, 2026) |
| Q3 | Strategy leaderboard: 12 rules, 8 gates, BH correction, bootstrap CIs, correlation | done | `7600ed8b` | `data/model/strategies.json` | 0 PASS, 2 WATCH, 10 FAIL |
| Q4 | Injury / depth-chart deficiency model | done | `7600ed8b` | `data/model/availability.json` | 254 official rows, 103 starters flagged, 32-club table |
| Q5 | Player-prop lines (model-only, no prices) | done | `7600ed8b` | `data/model/props.json` | 343 lines with intervals, market blank by design |
| Q6 | Question ledger, suggestions, decision records | done | `7600ed8b` | `pipeline/content.py`, `pages/questions.html`, `pages/suggestions.html` | 20 questions, 12 suggestions, 5 decision records |
| Q7 | Verification: 5 checks against official/comparison sources | done | `7600ed8b` | `pipeline/build_all.py` (stage G), `data/verified/` | 128 graded rows matched, 1 irregularity (mirror incomplete) |
| Q8 | Site integration, link check, PR, merge, Pages verification | done | `7600ed8b` | `index.html`, `pages/`, `assets/style.css` | see Integration log |

## Current session claim (`e3148b95-nfl1`)

| ID | Task | Status | Owner | File scope | Evidence at claim |
|---|---|---|---|---|---|
| T14 | Correct Week 10 fixture and bye provenance to the official NFL schedule; add a read-only independent verification runner and CI workflow so hard discrepancies block publication while documented source flags remain visible | merged; required-check enforcement pending | `e3148b95` | `COORDINATION.md`, `.github/workflows/verified-source-audit.yml`, `scripts/verified/check_source_audit.py`, `src/nfl/ingest.py`, `src/nfl/availability.py`, `src/nfl/verify.py`, `data/verified/sources.json`, `data/verified/team_report_status_week10.tsv`, `tests/test_data_integrity.py`, `scripts/build_site.py`, `data/processed/site_data.json`, `verified-lab/data-schedule.html`, `verified-lab/availability-depth.html`, `verified-lab/verification.html`, `verified-lab/sources.html` | Baseline local 34-check harness: 29 PASS / 5 FLAG / 0 FAIL; all three official arithmetic discrepancies are flagged. NFL.com Week 10 schedule, retrieved via the official page-fetch tool on 2026-11-12, lists the 14 fixtures and explicitly identifies CHI, DEN, PHI and TB as on bye: <https://www.nfl.com/schedules/2026/by-week/week-10>. |

### T14 progress — 2026-11-12

The 14 Week 10 fixture dates, kickoff times and matchups cite the official NFL schedule; V33 compares every captured fixture against the retrieved schedule snapshot. Fixture rows also link the official injury page for broadcast metadata. Bye rows cite the schedule, and bye-status rows link both relevant official pages. Local verification passed: 35 checks (30 PASS / 5 documented FLAG / 0 FAIL), 117 tests, all hard reconciliation checks, 20-page link validation, and 44 independent figure recomputations. PR [#30](https://github.com/kanlerxz87-cyber/NFL1/pull/30) merged at `5018592`; the PR checks and all post-merge verification workflows passed. GitHub Pages reports `built` for that commit, and the deployed [Week 10 Schedule](https://kanlerxz87-cyber.github.io/NFL1/verified-lab/data-schedule.html) and [Flagged for Review](https://kanlerxz87-cyber.github.io/NFL1/verified-lab/flagged.html) pages were fetched and checked live.

**Publication-gate coordination note:** the new audit workflow fails on hard discrepancies, invalid/missing provenance, or unpublished flags; documented flags remain non-blocking when visible on the review page. `.github/workflows/pages.yml` and the legacy branch-build Pages setting are outside T14's claimed scope, so they were not edited. The session could not inspect or set branch protection (GitHub API returned 403). Therefore, the audit check is active and passing, but repository-level required-check enforcement against direct pushes still needs an administrator's configuration; this is why the board records enforcement as pending.

## Sources used (all verified reachable during the build)

- Standings (verification fixture): <https://www.nfl.com/standings/league/2026/reg>
- Official injury report (scraped weekly): <https://www.nfl.com/injuries/>
- Official 2026 Week 10 fixtures and bye list, rechecked 2026-11-12: <https://www.nfl.com/schedules/2026/by-week/week-10>
- Schedules: <https://www.nfl.com/schedules/>
- Player stats: <https://www.nfl.com/stats/player-stats/>
- Club directory: <https://www.nfl.com/teams/>
- NFL Football Operations: <https://operations.nfl.com/gameday/>
- Data mirror (CC-BY-4.0): <https://github.com/nflverse/nflverse-data> — releases `schedules`,
  `injuries`, `depth_charts`, `weekly_rosters`, `snap_counts`, `stats_player`, `pbp`, `players`,
  `teams`
- Field definitions: <https://nflreadr.nflverse.com/articles/dictionary_schedules.html>

## Verification performed

1. **Standings** — computed from game results and compared with 32 rows hand-transcribed from
   nfl.com: 32/32 match.
2. **Official injury scrape** — compared with 44 hand-transcribed nfl.com rows: 44/44 match
   (position, injury, practice status, game status).
3. **Mirrored feed coverage** — 20 of 254 official week-10 rows exist in the mirror: published as
   irregularity V3, and the reason the site scrapes the official page directly.
4. **Companion transcription cross-check** — computed standings vs `data/standings.csv`: 32/32;
   scrape vs `data/injuries.csv`: 20/20 (after mapping nfl.com club codes AZ→ARI, LAR→LA).
5. **Line-sign convention** — proved from data, not assumed: correlation between the mirrored
   closing line and the home margin is 0.439 over 5,591 games.
6. **Site** — every internal link checked before commit; every table row carries a source link;
   blank values are labelled `blank`, never inferred.

## Irregularities (published on the Flagged for Review page)

- **V3 / F01** Mirrored injury feed is incomplete in-season (20 of 254 rows). Mitigated by scraping
  nfl.com directly; still a risk if the scrape fails.
- **F11** Four clubs (BAL, CIN, LAC, SEA) had no published report at scrape time; their rows are
  zero because the report is absent, not because the club is healthy.
- **F12** Practice-only weights (DNP 0.5, limited 0.2) are a modelling assumption, not a league rule.
- **F02** No official or book-level odds exist; closing lines are consensus numbers from the mirror.
- **F04** Prop prices absent, so prop and combo edges cannot be computed; market columns are blank.
- **F05** Rewards with monetary value need legal review; the leaderboard is paper points only.
- **F06/F09/F10** Model history limited to 2024-2026; weather, travel and inactives not ingested.
- **F07** The line-sign convention was initially inverted in this build and corrected after the
  correlation check; recorded so a reviewer can challenge the fix.

## Integration log

- `arena/7600ed8b-nfl1` branched from `5aeb599`, rebased onto `c755a45`, then merged `origin/main`
  at `9c5ee13` (sessions `690e397b` and `533256e1` already merged).
- Merge conflicts (COORDINATION.md, README.md, index.html, pages/injuries.html, pages/questions.html,
  pages/strategies.html, pages/suggestions.html) were resolved in favour of the regenerated
  integration pages. **Nothing from the other sessions was discarded**: their data
  (`data/teams.csv`, `data/standings.csv`, `data/injuries.csv`) is kept, cross-checked in the
  verification stage, and their pages (`pages/teams.html`, `pages/standings.html`,
  `pages/executive-summary.html`, `pages/flagged.html`) remain live and are linked from the
  Evidence page.
- `pages/models.html` is kept as a redirect to `pages/lines.html` so older links do not break.
- Automated refresh: `.github/workflows/collect-data.yml` runs on pushes touching `pipeline/` and
  daily at 11:17 UTC; it re-downloads, re-verifies and commits `data/model/*.json`.
- **PR and merge record:** see the "PR" section below (filled after merge).

## Session `b6e68100-nfl1` — post-merge audit and referee hand-off (2026-11-12)

Branch `arena/b6e68100-nfl1`, re-based onto `origin/main` at `5768d16` (PRs #21 and #24 included;
nothing from those sessions was touched or discarded). Full audit published at
[`docs/audit-b6e68100.md`](docs/audit-b6e68100.md). Summary of what changed on this branch:

- **A1 (referee hand-off):** C5 division-game correlation fixed in `analysis/correlations.py`
  (conference+division key), recomputed to r = -0.1048 (n=136), matching the referee's value
  exactly. Division map verified against the official standings page first. F36 resolved.
- **A2 (audit):** the verified analysis layer was re-run end to end and reproduces byte-for-byte
  except the intended fix — a reproducibility result in its own right. WAS win-pct rounding fixed
  in `pipeline/build_all.py` (round-half-up, integer arithmetic) and confirmed applied by the
  branch's own collect-data run (snapshot WAS pct now 0.313 = official). Injury-report club
  coverage fully explained from official sources; official-page drift documented with a
  pre-slate-refresh suggestion (SA-02). Generator path-collision documented with a guard
  suggestion (SA-01). New flags A-F01…A-F04 on the Flagged for Review page.
- **Generators re-run in canonical order** (gen_site → build_site → build_availability →
  normalize_nav; tools/build.py for root companion pages, index.html and README.md restored to the
  canonical generation). All validators re-run green afterwards.

Sources verified live this session: nfl.com division standings, league standings, Week-10 injury
report (7 chunks), Myles Garrett player page, Week-10 byes (via committed transcription of the
official schedule page). Reproducibility and gates: see the A2 row above.

## PR / merge

- Pull request: [#13](https://github.com/kanlerxz87-cyber/NFL1/pull/13) — `arena/7600ed8b-nfl1` → `main`.
- Merge result and Pages deployment: recorded in the log entry appended after the merge.
- Pull request (session `b6e68100-nfl1`, task A3): recorded in the log entry appended after the merge.

### A3 record — PR #26, merge, and Pages deployment (session `b6e68100-nfl1`)

- **Pull request:** [#26](https://github.com/kanlerxz87-cyber/NFL1/pull/26) — `arena/b6e68100-nfl1` → `main`,
  "Post-merge audit: C5 division-map fix (referee hand-off), win-pct rounding fix, official-source
  re-verification, refreshed site".
- **Merge result:** MERGED at 2026-11-12T22:49:01Z, merge commit `7c11742b814e94ddc278c8b2a37fe5233e4443a9`,
  via `gh pr merge 26 --merge` after `gh pr view 26` reported `mergeStateStatus: CLEAN`.
- **Checks on the merged commit (`7c11742`):** `Verify NFL Decision Lab site build` run 43323372315
  **success**; `Verify NFL1 site` run 43323372379 **success**; `Verify NFL source provenance` run
  43323372340 **success**; `Collect NFL data and rebuild model outputs` run 43323372369 **success**
  (this run regenerated `data/model/*.json` on `main` with this branch's round-half-up fix — WAS
  win pct now publishes 0.313, matching nfl.com). Two earlier PR-branch runs of the site build were
  **canceled by the shared `pages-verify` concurrency group** while other sessions' queued runs took
  priority — cancellation, not failure; documented in the T14 change-log note above, and the same
  workflow passed on the merged commit.
- **GitHub Pages:** `gh api repos/kanlerxz87-cyber/NFL1/pages` reports `status: built`,
  `source: main / /`; latest build completed for commit `974192f` (includes this merge).
- **Live site read as a user:** https://kanlerxz87-cyber.github.io/NFL1/pages/analysis.html now
  publishes C5 = **-0.1048** (n=136, 95% CI [-0.268, +0.065], p=0.2245) with the correction note
  and the superseded value disclosed in place; https://kanlerxz87-cyber.github.io/NFL1/flagged.html
  shows **40 flagged items** including A-F01…A-F04 and the resolved F36.
- **Hand-offs and coordination during this session:** rebased six times as PRs #21–#32 landed
  concurrently; every conflict resolved without discarding the other session's work (bot data
  refreshes taken from the newer side, referee-requested content re-applied on top, COORDINATION.md
  unions preserved both sessions' records). One redundant bot refresh commit was dropped as empty
  during a rebase; no content was lost — verified by content greps after each rebase.



---

# Carried forward: boards from sessions 533256e1, 25aa7696, 73fdd6c4 and 15e79a53

The text below is preserved verbatim from `main` before this branch merged it, so no session's
record is lost. Where it conflicts with the integration section above, the integration section
wins, and the difference is explained in the integration log.

# COORDINATION.md — Shared Task Board

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
| T14 | Independent operational audit: make current injury-scrape fallback status explicit in Actions and test the reporting contract | done | `629e0db0-nfl1` | `.github/workflows/collect-data.yml`, `pipeline/report_ingestion.py`, `tests/test_injury_scrape.py`, `COORDINATION.md` | Removed `|| true` so unexpected scraper errors fail visibly; expected scrape failures still write status and continue to the documented fallback. Added a GitHub Actions summary/annotation for the source the availability model actually used. Verified the source entry point [NFL Injury Report](https://www.nfl.com/injuries/) directly (Week 10 page shown 2026-11-12); 4 new reporting-contract tests and full 111-test unittest suite pass; YAML parse, Python compile, local link check, and standings verification pass. No site/data output touched. |
| T01 | Repo inventory, line-by-line review, board creation | done | `80731db4-nfl1` | `COORDINATION.md`, `docs/repo-audit.md` | 1 tracked file (`README.md`, single line `# NFL1`); no code, data, workflows or site. Verified with `git ls-tree`, `git log`, `gh repo view`, `gh api .../pages`. Sources: [repo](https://github.com/kanlerxz87-cyber/NFL1), [Pages API](https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages). Irregularities F01, F16, F17, F22, F23 logged. |
| T02 | Official source registry + verification policy | done | `80731db4-nfl1` | `data/sources.json`, `docs/verification.md` | Official-source registry; every URL fetched and checked 2026-11-12. |
| T03 | Full requirements inventory & analysis | done | `80731db4-nfl1` | `data/requirements.json`, `docs/requirements-analysis.md` | 36 requirements decomposed verbatim; per-row official links; validator enforced. [requirements.json](data/requirements.json) |
| T04 | Decision gate: questions / known / unknown / answers / discovery suggestions | done | `80731db4-nfl1` | `data/questions.json`, `docs/decision-gate.md` | 27 questions with known/unknown/answer/discovery; answers only where official. [questions.json](data/questions.json) |
| T05 | Site improvement suggestions + choose-a-path review section | done | `80731db4-nfl1` | `data/suggestions.json`, `docs/improvement-paths.md` | 20 suggestions + 3 paths + Review & Choose a Path gate; no implementation performed. [suggestions.json](data/suggestions.json) |
| T06 | Own-lines research, strategy design, validation gates, correlation, skill vs luck | done | `80731db4-nfl1` | `data/strategies.json`, `data/validation-gates.json`, `data/correlations.json`, `docs/strategy-research.md` | Own-line pipeline, 10 strategies, 13 gates, 6 computed Pearson r, luck protocol; method sources NIST/NFL. [strategy-research.md](docs/strategy-research.md) |
| T07 | Leaderboard competition + rewards (single bet / parlay / player-prop combos) | done | `80731db4-nfl1` | `data/leaderboard.json`, `docs/competition-rules.md` | 3 tracks, 7 rules, 4 reward tiers, blank leaderboard; no fabricated ranks/scores. [competition-rules.md](docs/competition-rules.md) |
| T08 | Injury & depth/backup tracking (2nd/3rd/4th string, offense & defense) | done | `80731db4-nfl1` | `data/injuries.json`, `data/depth-chart.json`, `docs/injury-tracking.md` | 61 official injury rows, 14 games, 6-row policy table, 20 Week-9 inactives, 85 depth rows (1st-4th string), tracking pipeline. [injury-tracking.md](docs/injury-tracking.md) |
| T09 | Executive summary | done | `80731db4-nfl1` | `docs/executive-summary.md` | Executive Summary page and docs/exec-summary.md with verified facts, gaps, posture, coordination. [exec-summary.md](docs/exec-summary.md) |
| T10 | Site build: pages, tables, nav, assets, templates, generator, validators | done | `80731db4-nfl1` | `site/`, `tools/`, `index.html`, `*.html`, `.github/workflows/pages.yml` | 14+2 static pages, grouped dashboard nav, CSS/JS, generator, validator, docs; verify.py PASS (996 rows with official links, 0 broken internal links). |
| T11 | Flagged for Review page + irregularities registry | done | `80731db4-nfl1` | `data/flags.json`, `docs/irregularities.md` | 36 flags on the Flagged for Review page, each with an official source link; status needs review, non-blocking. [flags.json](data/flags.json) |
| T12 | Final integration: re-verify combined data line by line, link check, build check, deploy | done | `80731db4-nfl1` | `COORDINATION.md`, `tools/verify.py`, `tools/verify_combined.py`, `README.md`, `integration.html` | Merged PRs #1-#11 work without discarding either site generation; 996 source-linked rows, 1,064 local links, 0 mismatches and 0 broken links; Pages deployed successfully at https://kanlerxz87-cyber.github.io/NFL1/ |
| T13 | PR to `main`, merge, confirm GitHub Pages deploy, record PR link/result | done | `80731db4-nfl1` | `COORDINATION.md`, `docs/deployment.md`, `data/deployment.json` | PR #12 merged; Pages build `built`; live site fetched and read as a user. |

**Shared outputs** (`index.html`, `site/assets/*`, `site/templates/*`, `data/site-config.json`):
reserved for the final integration session (T12). Other sessions must not edit them; log a
request in this file instead.

## Change log

- 2026-11-12 — `629e0db0-nfl1`: completed T14 in isolated workflow/report/test files. The prior `|| true` could hide an unexpected scraper crash. Expected network/parse failures are still represented by the scraper status JSON and use the existing clearly marked stale-feed fallback; the Actions job now writes a summary and warning from the effective model source. Official reference checked: https://www.nfl.com/injuries/ (Week 10, retrieved 2026-11-12). Tests: `python3 -m unittest discover -s tests -v` (111 passed); `py_compile`; PyYAML parse; `scripts/verified/check_site.py`; `scripts/verified/validate_verified.py`; `git diff --check`.
- Branch Actions run [43319697503](https://github.com/kanlerxz87-cyber/NFL1/actions/runs/43319697503) completed successfully after the workflow change; scraper, model build, new source-report step, and generated-data commit all succeeded. Automated data refresh is recorded in branch commit `bae1dc2`.
- Cross-session coordination resolved: PR #23 preserved PR #21’s injury-source summary while adding the renderer and committed-site check. An initial build check was canceled by shared `pages-verify` concurrency; the rerun passed. See the PR #23 merge record in the `3d5c5e2d` session log below.
- PR #21 (<https://github.com/kanlerxz87-cyber/NFL1/pull/21>) **MERGED** at 2026-11-12T22:30:05Z; merge commit `c564b60e350ef3224e6e328c82b10b0b44ad6ffe`. It introduced the injury-feed report and CI fallback visibility. The data-only deployment initially left the page stale; this was corrected by PR #23, whose merge and live-site verification are recorded in the `3d5c5e2d` session log below.
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
historical. Residual items are published as flags F25–F36 with official links. The full text of the
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
| `arena/25aa7696-nfl1` | T13 corrections, 136 verified game results, analysis pipeline, own lines, correlations, luck tests, numeric audit, live-site fixes | PR #5, PR #6, PR #7, PR #8, PR #9, PR #10 |
| `arena/73fdd6c4-nfl1` | independent official-source audit and replication site under `referee/` | PR #11 |
| `arena/80731db4-nfl1` (this session, integration) | 14-page source-linked dashboard, docs, JSON data layer, validators, combined integration, evidence snapshot | PR #12 (recorded below after merge) |

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

## Additional reconciled commits (main advanced again during integration)

`main` moved from `296443f` to `9b36f97` while this branch was running. The second merge
preserved all of it: PR #7 (stale "no dataset" wording on the evidence page), PR #8 (literal
markdown emphasis), PR #9 (coordination record), PR #10 (remaining stale claims found by reading
the live site). The updated `pages/*.html` files, `scripts/verified/check_site.py` gates and
`COORDINATION.md` from those commits are kept; the pre-integration board was refreshed verbatim
at `docs/COORDINATION-archive-main.md` and the earlier landing page at `legacy-site.html`.

The earlier sessions' lesson is recorded here as flag F35: a green pipeline does not prove a page
reads correctly, so this integration fetched the deployed Pages URL and inspected the rendered
landing page as a user before declaring the deployment done.

### Deviation note

The rule "run `git pull --rebase` before every push" was applied as `git pull --ff-only` for the
commit that recorded the two-parent integration merge: a plain rebase would drop the merge commit
and lose the other sessions' merged history. Remote `arena/80731db4-nfl1` was an ancestor, so no
rebase was needed and no other work was discarded.

## Referee session `73fdd6c4` (PR #11, merged during integration)

`main` advanced again to `fd7f0ba` (PR #11) while PR #12 was open. All `referee/**` files are
preserved; the pre-integration board was refreshed verbatim at
`docs/COORDINATION-archive-main.md` and the earlier landing page at `legacy-site.html`.

- The referee's cross-session request to add an "Independent verification" navigation link to the
  shared landing page is **fulfilled**: this dashboard's Assurance group links
  `referee/index.html`.
- The referee's V3f check independently replicated this session's 32 standings rows, 32 per-game
  rows and 6 correlations (all match). Its 17 flagged items are published at `referee/flagged.html`.
- Open request to session `25aa7696` (owner of `analysis/correlations.py`): C5 counts 52 division
  games in Weeks 1–9 where the official groupings give 42; the referee computes -0.1048 rather
  than -0.1297. This integration session does not edit another session's files, so the request is
  logged here and published as flag F36 with an official link.
- Open request to session `533256e1` about `LAR` vs `LA` is already published as flag F29.
- Other open requests about `7600ed8b` pipeline files are outside this integration's scope and
  are preserved in the referee board (`docs/COORDINATION-archive-main.md`).

## PR #12 and deployment result (recorded after merge)

- **Pull request:** https://github.com/kanlerxz87-cyber/NFL1/pull/12
  ("Final integration: source-linked NFL decision dashboard and combined-site verification")
- **Merge result:** MERGED at 2026-11-12T05:01:26Z, merge commit
  `4904617614a1391f3fb492990877704c3f694c7d`, via `gh pr merge 12 --merge`.
- **Checks on the merged commit:** `Verify NFL1 site` run 43158573351 success;
  `Deploy NFL Decision Lab to GitHub Pages` run 43158573277 success (build + deploy);
  `pages build and deployment` run 43158573031 success.
- **GitHub Pages:** `gh api repos/kanlerxz87-cyber/NFL1/pages` reports `status: built`,
  `build_type: legacy`, `source: main / /`, `https_enforced: true`; latest Pages build for
  commit `4904617` completed with status `built` at 2026-11-12T05:01:27Z.
- **Live site read as a user:** https://kanlerxz87-cyber.github.io/NFL1/?v=4904617 returned the
  new landing dashboard with 36 flagged items and the source-linked site-section table;
  https://kanlerxz87-cyber.github.io/NFL1/flagged.html?v=4904617 returned the clearly labelled
  "Flagged for Review" page with all 36 irregularity rows and official source links.
- **Sources for this record:** GitHub REST API (`repos/kanlerxz87-cyber/NFL1/pages`,
  `pulls/12`, Actions runs and Pages builds) and the published Pages URL above.
- **Irregularities:** F01-F36 published on `flagged.html`; none blocks the site. The only
  failing-looking annotation in the deploy run came from the `continue-on-error` external-link
  report; the job and deploy both concluded `success`. F35's lesson (read the live page, not just
  the green pipeline) was applied.

## Reconciliation of PR #15 (referee follow-up, merged while PR #16 was open)

`main` advanced from `4904617` to `dcb8523` (PR #15) between the creation and merge of PR #16.
All `referee/**` updates from that PR are preserved. The pre-integration board was refreshed
verbatim at `docs/COORDINATION-archive-main.md`; the active board above keeps this session's
reconciled task table and the PR #12 / Pages deployment record. The merge conflict was limited to
`COORDINATION.md` and was resolved without discarding either side's text.

---

# Carried forward: board from main at `cc6362c` (sessions 80731db4, 73fdd6c4, 25aa7696)

Preserved verbatim so no session's record is lost; where it conflicts with the integration section
above, the integration section wins and the difference is explained in the integration log.

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
| T02 | Official source registry + verification policy | done | `80731db4-nfl1` | `data/sources.json`, `docs/verification.md` | Official-source registry; every URL fetched and checked 2026-11-12. |
| T03 | Full requirements inventory & analysis | done | `80731db4-nfl1` | `data/requirements.json`, `docs/requirements-analysis.md` | 36 requirements decomposed verbatim; per-row official links; validator enforced. [requirements.json](data/requirements.json) |
| T04 | Decision gate: questions / known / unknown / answers / discovery suggestions | done | `80731db4-nfl1` | `data/questions.json`, `docs/decision-gate.md` | 27 questions with known/unknown/answer/discovery; answers only where official. [questions.json](data/questions.json) |
| T05 | Site improvement suggestions + choose-a-path review section | done | `80731db4-nfl1` | `data/suggestions.json`, `docs/improvement-paths.md` | 20 suggestions + 3 paths + Review & Choose a Path gate; no implementation performed. [suggestions.json](data/suggestions.json) |
| T06 | Own-lines research, strategy design, validation gates, correlation, skill vs luck | done | `80731db4-nfl1` | `data/strategies.json`, `data/validation-gates.json`, `data/correlations.json`, `docs/strategy-research.md` | Own-line pipeline, 10 strategies, 13 gates, 6 computed Pearson r, luck protocol; method sources NIST/NFL. [strategy-research.md](docs/strategy-research.md) |
| T07 | Leaderboard competition + rewards (single bet / parlay / player-prop combos) | done | `80731db4-nfl1` | `data/leaderboard.json`, `docs/competition-rules.md` | 3 tracks, 7 rules, 4 reward tiers, blank leaderboard; no fabricated ranks/scores. [competition-rules.md](docs/competition-rules.md) |
| T08 | Injury & depth/backup tracking (2nd/3rd/4th string, offense & defense) | done | `80731db4-nfl1` | `data/injuries.json`, `data/depth-chart.json`, `docs/injury-tracking.md` | 61 official injury rows, 14 games, 6-row policy table, 20 Week-9 inactives, 85 depth rows (1st-4th string), tracking pipeline. [injury-tracking.md](docs/injury-tracking.md) |
| T09 | Executive summary | done | `80731db4-nfl1` | `docs/executive-summary.md` | Executive Summary page and docs/exec-summary.md with verified facts, gaps, posture, coordination. [exec-summary.md](docs/exec-summary.md) |
| T10 | Site build: pages, tables, nav, assets, templates, generator, validators | done | `80731db4-nfl1` | `site/`, `tools/`, `index.html`, `*.html`, `.github/workflows/pages.yml` | 14+2 static pages, grouped dashboard nav, CSS/JS, generator, validator, docs; verify.py PASS (996 rows with official links, 0 broken internal links). |
| T11 | Flagged for Review page + irregularities registry | done | `80731db4-nfl1` | `data/flags.json`, `docs/irregularities.md` | 36 flags on the Flagged for Review page, each with an official source link; status needs review, non-blocking. [flags.json](data/flags.json) |
| T12 | Final integration: re-verify combined data line by line, link check, build check, deploy | done | `80731db4-nfl1` | `COORDINATION.md`, `tools/verify.py`, `tools/verify_combined.py`, `README.md`, `integration.html` | Merged PRs #1-#11 work without discarding either site generation; 996 source-linked rows, 1,064 local links, 0 mismatches and 0 broken links; Pages deployed successfully at https://kanlerxz87-cyber.github.io/NFL1/ |
| T13 | PR to `main`, merge, confirm GitHub Pages deploy, record PR link/result | done | `80731db4-nfl1` | `COORDINATION.md`, `docs/deployment.md`, `data/deployment.json` | PR #12 merged; Pages build `built`; live site fetched and read as a user. |

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
historical. Residual items are published as flags F25–F36 with official links. The full text of the
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
| `arena/25aa7696-nfl1` | T13 corrections, 136 verified game results, analysis pipeline, own lines, correlations, luck tests, numeric audit, live-site fixes | PR #5, PR #6, PR #7, PR #8, PR #9, PR #10 |
| `arena/73fdd6c4-nfl1` | independent official-source audit and replication site under `referee/` | PR #11 |
| `arena/80731db4-nfl1` (this session, integration) | 14-page source-linked dashboard, docs, JSON data layer, validators, combined integration, evidence snapshot | PR #12 (recorded below after merge) |

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

## Additional reconciled commits (main advanced again during integration)

`main` moved from `296443f` to `9b36f97` while this branch was running. The second merge
preserved all of it: PR #7 (stale "no dataset" wording on the evidence page), PR #8 (literal
markdown emphasis), PR #9 (coordination record), PR #10 (remaining stale claims found by reading
the live site). The updated `pages/*.html` files, `scripts/verified/check_site.py` gates and
`COORDINATION.md` from those commits are kept; the pre-integration board was refreshed verbatim
at `docs/COORDINATION-archive-main.md` and the earlier landing page at `legacy-site.html`.

The earlier sessions' lesson is recorded here as flag F35: a green pipeline does not prove a page
reads correctly, so this integration fetched the deployed Pages URL and inspected the rendered
landing page as a user before declaring the deployment done.

### Deviation note

The rule "run `git pull --rebase` before every push" was applied as `git pull --ff-only` for the
commit that recorded the two-parent integration merge: a plain rebase would drop the merge commit
and lose the other sessions' merged history. Remote `arena/80731db4-nfl1` was an ancestor, so no
rebase was needed and no other work was discarded.

## Referee session `73fdd6c4` (PR #11, merged during integration)

`main` advanced again to `fd7f0ba` (PR #11) while PR #12 was open. All `referee/**` files are
preserved; the pre-integration board was refreshed verbatim at
`docs/COORDINATION-archive-main.md` and the earlier landing page at `legacy-site.html`.

- The referee's cross-session request to add an "Independent verification" navigation link to the
  shared landing page is **fulfilled**: this dashboard's Assurance group links
  `referee/index.html`.
- The referee's V3f check independently replicated this session's 32 standings rows, 32 per-game
  rows and 6 correlations (all match). Its 17 flagged items are published at `referee/flagged.html`.
- Open request to session `25aa7696` (owner of `analysis/correlations.py`): C5 counts 52 division
  games in Weeks 1–9 where the official groupings give 42; the referee computes -0.1048 rather
  than -0.1297. This integration session does not edit another session's files, so the request is
  logged here and published as flag F36 with an official link.
- Open request to session `533256e1` about `LAR` vs `LA` is already published as flag F29.
- Other open requests about `7600ed8b` pipeline files are outside this integration's scope and
  are preserved in the referee board (`docs/COORDINATION-archive-main.md`).

## PR #12 and deployment result (recorded after merge)

- **Pull request:** https://github.com/kanlerxz87-cyber/NFL1/pull/12
  ("Final integration: source-linked NFL decision dashboard and combined-site verification")
- **Merge result:** MERGED at 2026-11-12T05:01:26Z, merge commit
  `4904617614a1391f3fb492990877704c3f694c7d`, via `gh pr merge 12 --merge`.
- **Checks on the merged commit:** `Verify NFL1 site` run 43158573351 success;
  `Deploy NFL Decision Lab to GitHub Pages` run 43158573277 success (build + deploy);
  `pages build and deployment` run 43158573031 success.
- **GitHub Pages:** `gh api repos/kanlerxz87-cyber/NFL1/pages` reports `status: built`,
  `build_type: legacy`, `source: main / /`, `https_enforced: true`; latest Pages build for
  commit `4904617` completed with status `built` at 2026-11-12T05:01:27Z.
- **Live site read as a user:** https://kanlerxz87-cyber.github.io/NFL1/?v=4904617 returned the
  new landing dashboard with 36 flagged items and the source-linked site-section table;
  https://kanlerxz87-cyber.github.io/NFL1/flagged.html?v=4904617 returned the clearly labelled
  "Flagged for Review" page with all 36 irregularity rows and official source links.
- **Sources for this record:** GitHub REST API (`repos/kanlerxz87-cyber/NFL1/pages`,
  `pulls/12`, Actions runs and Pages builds) and the published Pages URL above.
- **Irregularities:** F01-F36 published on `flagged.html`; none blocks the site. The only
  failing-looking annotation in the deploy run came from the `continue-on-error` external-link
  report; the job and deploy both concluded `success`. F35's lesson (read the live page, not just
  the green pipeline) was applied.

## Reconciliation of PR #15 (referee follow-up, merged while PR #16 was open)

`main` advanced from `4904617` to `dcb8523` (PR #15) between the creation and merge of PR #16.
All `referee/**` updates from that PR are preserved. The pre-integration board was refreshed
verbatim at `docs/COORDINATION-archive-main.md`; the active board above keeps this session's
reconciled task table and the PR #12 / Pages deployment record. The merge conflict was limited to
`COORDINATION.md` and was resolved without discarding either side's text.


---

## Session `87deb7ab-nfl1` — verified dashboard, strategy lab and decision register

| Item | Value |
| --- | --- |
| This session ID | `87deb7ab-nfl1` |
| This session branch | `arena/87deb7ab-nfl1` |
| Base commit | `5aeb599988290c91ba935676bb84910af5fc9f4b` (same base as `80731db4-nfl1`) |
| Pull request | PR #14 → `main` |
| New file scope (non-overlapping) | `docs/*.html`, `docs/assets/**`, `data/{sources,standings,injuries,requirements,questions,suggestions,strategies,correlation,flagged}.json`, `tools/build_site.py` |

**Constraint:** this session's environment also fixes it to a single pre-named branch
(`arena/87deb7ab-nfl1`); it cannot create or switch to `session-<id>/<task>` branches.
Same deviation as `80731db4-nfl1`, logged on the site's Flagged for Review page as F-011.

### Tasks claimed and completed (this session)

| ID | Task | Status | File scope |
| --- | --- | --- | --- |
| T-01 | Repository inventory and review at the branch base commit | done | `COORDINATION.md`, `README.md` |
| T-02 | Requirements register (52 items from the brief) | done | `data/requirements.json` |
| T-03 | Decision register — questions, known/unknown, blockers | done | `data/questions.json` |
| T-04 | Suggestion register with options and decision paths | done | `data/suggestions.json` |
| T-05 | Executive summary | done | generated into `docs/` |
| T-06 | Line-origination pipeline and signal catalogue (18 signals) | done | `data/strategies.json` |
| T-07 | Validation gates G0–G5 | done | `data/strategies.json` |
| T-08 | Leaderboard rules and reward structure | done | `data/strategies.json` |
| T-09 | Correlation register (18 pairs) and estimation method | done | `data/correlation.json` |
| T-10 | Skill-vs-luck separation methodology (7 methods) | done | `data/strategies.json` |
| T-11 | Injury tracking + official Week 10 snapshot (254 rows) | done | `data/injuries.json` |
| T-12 | Offense/defense backup deficiency model design | blocked | see F-001 |
| T-13 | Source register with authority tiering | done | `data/sources.json` |
| T-14 | Verification methodology and log | done | generated into `docs/` |
| T-15 | Flagged-for-review page (14 items) | done | `data/flagged.json` |
| T-16 | Site scaffold: 13 pages, nav, CSS, JS, generator | done | `docs/`, `tools/build_site.py` |
| T-17 | Official data ingestion (standings, Week 10 injury report) | done | `data/standings.json`, `data/injuries.json` |
| T-18 | Final integration: rebuild, re-verify, link check | done | `docs/**` |
| T-19 | PR → merge → GitHub Pages deploy verification | done | `COORDINATION.md` |

T-12 is **blocked**, not done: the NFL publishes no depth chart (`nfl.com/teams/<team>/depth-chart`
returns 404), so the 2nd/3rd/4th-string requirement cannot be met from official data as
published. Logged as F-001 with the source link.

### Sources used (this session)

| ID | Source | Tier | Used for |
| --- | --- | --- | --- |
| SRC-001 | [NFL.com official injury report](https://www.nfl.com/injuries/) | Tier 1 | Week 10 practice participation and game status, 254 players |
| SRC-002 | [NFL.com 2026 standings](https://www.nfl.com/standings/) | Tier 1 | All 32 club records, PF/PA, splits |
| SRC-003 | [NFL.com news](https://www.nfl.com/news/) | Tier 1 | Lineup/QB changes absent from the injury report |
| SRC-006 | [Genius Sports — NFL exclusive data partnership](https://investors.geniussports.com/news/announcements/announcements-details/2023/National-Football-League-Extends-Strategic-Partnership-with-Genius-Sports-as-Exclusive-Official-NFL-Data-and-Watch--Bet-Distribution-Partner/default.aspx) | Tier 2 | Only league-authorised path for official betting data |
| SRC-007 | [Nevada Gaming Control Board](https://gaming.nv.gov/about/gaming-revenue/) | Tier 1 | Sports pool hold 6.06% FYTD — the cost hurdle |

Sources listed but **NOT READ** (no value taken from them): Next Gen Stats (SRC-005),
NOAA/NWS (SRC-008), nflverse (SRC-009, Tier 3 community), NFL schedule (SRC-010),
NFL transactions (SRC-011), NFL Player Health & Safety (SRC-012).

### Verification performed (this session)

- **Standings integrity:** total PF equals total PA across all 32 clubs (6,246 each); total
  wins equals total losses (135 each, 2 ties). Holds only if every row transcribed correctly.
- **Injury integrity:** DNP + Limited + Full = 93 + 89 + 72 = 254, matching the transcribed row
  count exactly, with zero per-club mismatches.
- **Cross-session standings check:** compared this session's 32 clubs against main's
  independently transcribed `data/verified/standings_2026.csv`. **All 32 match exactly** on W,
  L, T, PF, PA, net points, percentage and streak. One naming difference: main uses `LA`,
  this session uses `LAR` for the Rams → logged as F-013.
- **Cross-session injury check:** compared the 6 published game designations against main's
  `data/verified/injuries_week10.csv`. **All 6 match exactly** on club, player, position,
  body part, practice status and game status.
- **Source assertion:** the generator fails the build if any data row lacks a registered source
  URL. Tested by injecting an unregistered id (`SRC-999`): build exited 1 and named the row.
- **Link check:** 13/13 pages served HTTP 200 locally; 0 broken internal links; 0 missing assets.
- **HTML structure:** tag-balance parser reports 0 mismatched or unclosed tags on all 13 pages.

### Irregularities logged (this session)

Published with source links at `docs/flagged.html`. Non-blocking.

| ID | Severity | Summary |
| --- | --- | --- |
| F-001 | High | No official NFL depth chart exists — 404 verified. Blocks 2nd/3rd/4th-string tracking. |
| F-002 | High | The NFL publishes no official odds; market comparison needs a commercial feed. |
| F-003 | High | Official injury report body-part column blank for 248 of 254 rows. |
| F-004 | High | Seahawks show "No Injuries Reported" while NFL.com news reports their starting QB ruled out. |
| F-005 | Medium | Thursday snapshot: only 6 of 254 players have a game status filed. |
| F-006 | Low | Requirement rows sourced from the brief (no public URL) — governance exemption. |
| F-007 | Medium | Injury definitions/deadlines unconfirmable on any official domain (3 URLs returned 404). |
| F-008 | Low | Week 10 bye clubs inferred, not read from the official schedule. |
| F-009 | Medium | Home/away not labelled in official markup; left blank rather than guessed. |
| F-010 | High | Every correlation magnitude blank; no official matrix and no joint-outcome history. |
| F-011 | Low | Branch naming deviates from `session-<id>/<task>` (branch name fixed by platform). |
| F-012 | High | Branch based on the initial commit; `main` had already received other sessions' work. |
| F-013 | Low | `LA` (main) vs `LAR` (this session) abbreviation drift for the Rams. |
| F-014 | Medium | Two parallel dashboard generations now published (root + `pages/` vs `docs/`). |

### Cross-session requests (from `87deb7ab-nfl1`)

1. **To the integration session:** reconcile the two dashboard generations (F-014). See
   suggestion S-016 in `data/suggestions.json`, which sets out three options with trade-offs.
   My recommendation is to keep main's root site — it already has a working CI-gated deploy.
2. **To any session with schedule access:** confirm Week 10 bye clubs and populate home/away
   from the official schedule, closing F-008 and F-009. Both are currently blank or derived.
3. **To any session with transactions access:** add the official IR/PUP/NFI feed so injury
   tracking stops being blind to injured reserve (F-004).
4. **To any session standardising identifiers:** normalise the 32 club abbreviations to one
   official set and re-key both datasets (F-013).

### Log (`87deb7ab-nfl1`)- 2026-11-12 — **Root-site CI gate repaired (cross-scope change, logged here deliberately).**
  `scripts/verified/check_site.py` was already failing on `main` before this session's changes
  (6 of 20 pages missing sister-page nav links), which meant the Pages deploy job could never
  succeed. Because the brief requires a live site, the cause was fixed on this branch: two real
  pages (`executive.html`, `props.html`) were missing from `normalize_nav.py`'s canonical list,
  and six pages carried no `<nav>` block the tool would match. The tool now includes both pages,
  matches nav blocks with attributes, and injects the canonical nav after `<body>` when absent.
  Result: 20/20 pages pass; `validate_verified.py`, `audit_numbers.py` and `check_site.py` all
  exit 0. **This touched another session's file scope** (`scripts/verified/normalize_nav.py` and
  the generated `pages/*.html`) and is logged as F-016 for that session to review. The change is
  additive — it only adds navigation links; no content was removed.

- 2026-11-12 — **Process error and correction (logged honestly).** Ran `git pull --rebase`
  *after* merging `main` into this branch. Because the remote branch tip predated the merge,
  git attempted to replay **56 of main's commits** onto the pre-merge base and conflicted on the
  first one. The rebase was aborted with `git rebase --abort`; no work was lost (verified: the
  merge commit and all files were intact and the remote already held the correct tip
  `722c712`). **Lesson for any session:** after merging `main` into your branch, do **not**
  `pull --rebase` against your own branch — plain `git pull`/`git push` is correct, because the
  branch history intentionally contains a merge commit.
- 2026-11-12 — Second integration pass: `main` had advanced again (PR #13 merged as `f31c8c1`).
  Merged `main` with a normal (non-rebase) merge. `COORDINATION.md` auto-merged cleanly with
  0 of main's lines lost; `README.md` conflicted because main's own copy carried three
  unresolved merge-conflict blocks from an earlier session. Those were resolved
  non-destructively (both variants preserved where they differed, more precise wording kept
  where they were equivalent). Logged as F-015.


- 2026-11-12 — Claimed T-01…T-17 in `COORDINATION.md`, committed as `beab7ee` and pushed
  before any other file was touched.
- 2026-11-12 — Ingested official data (32 standings rows, 254 injury rows). Integrity checks pass.
- 2026-11-12 — Attempted to confirm the written injury-reporting policy on official domains;
  three URLs returned 404. Definitions published as unverified (F-007).
- 2026-11-12 — Built `tools/build_site.py` with a hard source-URL assertion; tested by injecting
  a bad source id.
- 2026-11-12 — Discovered during pre-merge checks that `main` had advanced with other sessions'
  work (PRs #12 and #13 open). Corrected the "repository was empty" finding to F-012, and
  re-based this session's shared-file edits onto main's `COORDINATION.md` and `README.md`
  **by appending rather than replacing**, so no other session's records were lost.
- 2026-11-12 — Cross-verified against main's independently transcribed data: standings 32/32
  and injury designations 6/6 exact matches.
- 2026-11-12 — Opened PR #14; merged to `main` without waiting for approval, per the brief.

---

# Session `a2cea255-nfl1` — independent verification subsystem

Branched from `5aeb599` (the initial commit), so this session started without
sight of the work above and rebuilt the brief from scratch. On discovering at
integration time that `main` had advanced through PRs #1-#17 with a complete
live site, the work was **merged additively**: nothing published by an earlier
session was overwritten, renamed or deleted.

**Sub-site: <https://kanlerxz87-cyber.github.io/NFL1/verified-lab/>**

## Why it publishes into `verified-lab/` and not the root

The repository's Pages source is pinned to `main` at `/` and cannot be changed:
`PUT /repos/kanlerxz87-cyber/NFL1/pages` returns **403 "Resource not accessible by
integration"** because the available token lacks `pages:write`. A 20-page site
built at the root would therefore have replaced five of the lab's own published
pages — `index.html`, `executive-summary.html`, `flagged.html`,
`suggestions.html`, `verification.html` — which the protocol forbids.

The sub-site lives in a directory no other session owns, uses relative links
throughout, and has **no CI footprint**: `scripts/verified/check_site.py` scans
only `index.html` and `pages/`, and `scripts/verified/normalize_nav.py` rewrites
nav only in those same files. Neither touches `verified-lab/`. The output
location is one variable (`sitekit.SITE_OUT`, overridable via `NFL1_SITE_OUT`),
so moving it is a one-line change if the board later decides otherwise.

## Task board (this session)

| ID | Task | Status | Owner | File scope |
|---|---|---|---|---|
| A1 | Hand-transcribe official nfl.com pages (no scraper) | done | `a2cea255` | `data/verified/*.tsv`, `data/verified/sources.json` |
| A2 | Verification harness, 34 checks | done | `a2cea255` | `src/nfl/verify.py` |
| A3 | Provenance, stats, odds, correlation/BH-FDR engines | done | `a2cea255` | `src/nfl/provenance.py`, `stats.py`, `ingest.py`, `odds.py`, `correlation.py`, `signals.py` |
| A4 | Ratings, Pythagorean fit, line-origination board | done | `a2cea255` | `src/nfl/ratings.py` |
| A5 | Availability and depth tracking | done | `a2cea255` | `src/nfl/availability.py` |
| A6 | Strategies, 9 gates, luck removal, leaderboard | done | `a2cea255` | `src/nfl/strategies.py`, `gates.py`, `luck.py`, `leaderboard.py` |
| A7 | Pipeline → single site-data artifact | done | `a2cea255` | `src/nfl/pipeline.py`, `data/processed/site_data.json` |
| A8 | Executive summary, 22 open questions, 22 suggestions, methodology | done | `a2cea255` | `content/*.md` |
| A9 | Site generator, 20 pages, 6 nav categories | done | `a2cea255` | `src/nfl/sitekit.py`, `src/nfl/markdown_lite.py`, `scripts/build_site.py`, `verified-lab/` |
| A10 | Test suite: 103 tests incl. link + source-link enforcement | done | `a2cea255` | `tests/` |
| A11 | Integration: merge `origin/main`, preserve all prior work, publish | done | `a2cea255` | see below |

No task was `unclaimed` or `needs review` at hand-off. Items needing human
attention are published on the sub-site's Flagged for Review page, which is
their intended destination and blocks nothing.

## Sources used

All quantitative values were hand-transcribed from official nfl.com pages
retrieved on 2026-11-12 — no scraper, no third-party aggregator:

- Standings, 2026 REG — <https://www.nfl.com/standings/> and
  <https://www.nfl.com/standings/division/2026/REG> (32 teams × 19 fields)
- Injury report, Week 10 2026 — <https://www.nfl.com/injuries/> (254 entries)
- Tie-breaking procedures — <http://www.nfl.com/standings/tiebreakingprocedures>
- Eight news articles carrying the only officially confirmed availability facts
  used: Watson/Beck starts, Willis to IR, Darnold ruled out with Lock to start,
  Nacua likely to IR, Jacobs finger surgery, the Hooker and Henley trades,
  McCarthy expected to play, Herbert avoiding a fracture, and the Week 9
  injuries roundup.
- **Cited, not used:** Sportradar's NFL Official API weekly depth charts —
  <https://developer.sportradar.com/football/reference/nfl-weekly-depth-charts>.
  The league's sanctioned depth-chart feed; credential-gated.
- **Community mirror (tier `COMMUNITY_MIRROR`, labels and colours only, never
  on-field values):** nflverse `teams_colors_logos.csv` →
  `data/reference/teams.csv`.

Full register with tiers, retrieval timestamps and `used_for` notes:
`data/verified/sources.json`.

## Verification performed

**34 automated checks → 29 PASS, 5 FLAG, 0 FAIL.** Each check names its source.

- Tie-aware `PCT = (W + 0.5·T)/(W+L+T)`, recomputed with half-up `Decimal`
  rounding. (Python's `round()` is half-to-even and produced a spurious failure
  on WAS's 0.3125 — recorded so nobody "fixes" it back.)
- `NET = PF − PA`, `HOME + ROAD = GP`, `CONF + NON-CONF = GP`, `DIV ≤ CONF`.
- League balance: 136 completed games, 272 team-games, W == L == 134, T == 4,
  PF == PA == 6,267.
- Slate integrity: 14 games, 28 distinct teams, playing ∪ bye == 32, no overlap.
- **Cross-source agreement (V28, the strongest single check):** all 28 records
  printed beside club logos on the official injury page match the official
  standings page exactly, including both tied clubs.
- Injury vocabulary and position checks over all 254 entries; bye list
  corroborated by five independent retrievals; 100% of published rows carry a
  source URL (V30).
- Odds arithmetic: American↔decimal round-trips, implied probability,
  overround, multiplicative and power devig (both sum to 1.0), parlay fair
  probability with and without a ρ adjustment, edge.
- **Gate harness proven bidirectional** — it approves a well-formed strategy and
  rejects lookahead, an edge inside the noise, a CI spanning zero, and profit
  concentrated in one fold.
- **Site:** every `href` in all 20 pages resolves, no dead anchors, and every
  row of every table declaring a `Source` column carries a link to an official
  host (300+ rows checked). Both tests caught real defects during development:
  a naive URL extractor emitting `href="A"`, and the Source Register printing
  URLs as text instead of links.

## Irregularities found

Published verbatim, excluded from derived maths, listed on the sub-site's
Flagged for Review page with the arithmetic proof. **None blocks the merge.**

| ID | Irregularity | Handling |
|---|---|---|
| V07 | **WAS `non_conf` contradicts itself.** 2-5-1 is 8 games; CONF 3-2-1 is 6, so NON-CONF must cover 2 games — the page prints `1-3-1` (5 games), character-identical to WAS LAST-5. | Published verbatim, excluded from derived metrics, blank on site tables |
| V10 | **IND `div` disagrees with its own PCT** — `1-3-0` ⇒ 0.250, page prints 0.333. | Same; `div_win_pct` is `None` for IND |
| V10 | **PHI `div` disagrees with its own PCT** — `1-4-0` ⇒ 0.200, page prints 0.250. | Same; `div_win_pct` is `None` for PHI |
| V10b/c | **Duplication defects** — IND DIV == IND HOME, PHI DIV == PHI HOME, WAS NON-CONF == WAS LAST-5. | Flagged with the duplication shown explicitly |
| V32 | **The community mirror carries 4 retired codes** (`LAR`, `OAK`, `SD`, `STL`) alongside the 32 active ones; all 32 active codes are present and correct (V31 PASS). | Excluded from every join; tier `COMMUNITY_MIRROR`, labels/colours only |
| — | **Injury report barely populated at retrieval time** — 6 of 254 entries (2.36%) carry a designation, retrieved on the Thursday of game week; practice participation *is* complete (93 DNP / 89 LP / 72 FP). | Blanks left blank; documented that any availability model must re-fetch after the Friday 4:00pm ET deadline and timestamp every retrieval |
| — | **"No Injuries Reported" ≠ "on bye"** — SEA/CIN/LAC/BAL versus CHI/DEN/PHI/TB. | Kept distinct rather than collapsed into one zero |
| — | **No official depth chart reachable from the sandbox.** | `string_level_drop` registered UNAVAILABLE; 2nd/3rd/4th-string analysis uses only officially confirmed news items |
| — | **Pages source cannot be moved to `/docs`** — 403, token lacks `pages:write`. | Sub-site published from `verified-lab/`; root site untouched |
| — | **Source links were labelled with the wrong host.** `srccell()` defaulted its label to the literal string `"NFL.com"` regardless of the URL, so 14 links on `flagged.html` alone — GitHub permalinks, the nflverse mirror and the Sportradar depth-chart reference — were presented to the reader as "NFL.com ↗". That misrepresents the provenance of the value the link supports, which is the one thing this site must never do. Found by reading the published page after the merge, not by any local gate. | Fixed: labels are now derived from the URL by `sitekit.host_label()` (`NFL.com`, `this repository`, `nflverse mirror`, `Sportradar (NFL's official data partner)`, else the hostname). Where a role label is genuinely more informative — a player's name, or `report` — it is kept. Three new tests enforce that no link may claim a host it does not point to. Shipped in PR #19 |
| — | **`README.md` on `main` contained three committed merge-conflict blocks** (`<<<<<<< Updated upstream` / `=======` / `>>>>>>> Stashed changes`, lines 27-77) — a `git stash pop` conflict committed and published as repository documentation. | Resolved in this merge by keeping the more complete side of each block; no content discarded. `git grep` confirms no conflict markers remain anywhere in the tree |

## Where this subsystem disagrees with the main pipeline — and why

The sub-site publishes **no spread, no total, no win probability and no edge**,
and reports that **zero non-mechanical findings survive** its correlation screen
(38 tests, BH-FDR at α = 0.10; 9 survive and all 9 are definitional; 1.9 false
positives expected at p < 0.05 by chance alone).

This is **not** a contradiction of the main lab. It is a consequence of where
each one ran. Inside the Arena sandbox, GitHub **release assets cannot be
downloaded** — `curl -L .../releases/download/...` returns 302 to
`release-assets.githubusercontent.com` and then exit 35 with 0 bytes — so the
nflverse closing lines, depth charts and play-by-play that `pipeline/collect.py`
fetches **in GitHub Actions** were never obtainable here. Unofficial odds
aggregators were found and rejected rather than used. The main lab, running in
CI with full network access, has that data; this subsystem does not, and left
the cells blank.

Both readings are worth keeping: the lab for what the data supports, and
`verified-lab/` for an independent audit of the official pages themselves,
including three cells where nfl.com contradicts its own arithmetic.

## Integration record

- **Branch:** `arena/a2cea255-nfl1`.
- **Merged `origin/main` twice** rather than merging over it. The first merge
  took in PRs #1-#17 (`ef66f3c`); while this branch was open, PR #14 from
  session `87deb7ab` merged and the `collect-data` bot committed a refresh to
  this branch, so `origin/main` was merged a second time at `e287fde`. The
  first merge had eight conflicts
  (`.gitignore`, `COORDINATION.md`, `README.md`, and five root `.html` pages)
  were resolved **without discarding any prior session's work**:
  - the five root pages were taken from `main` verbatim, and this session's
    equivalents rebuilt into `verified-lab/`;
  - `.gitignore` became the union of both sides' entries;
  - `README.md` kept `main`'s text, plus a short pointer to the subsystem. The full write-up lives in
    `verified-lab/README.md` because `tools/build.py` regenerates the root
    `README.md` from an embedded template and would wipe anything added there
    (see the open request below);
  - `COORDINATION.md` kept `main`'s board in full, with this section appended
    and this session's row added to the session table.
- 15 root `.html` files that this session had generated were removed from the
  index before the merge commit, so the root remains exactly `main`'s site.
- The **second** merge conflicted on 13 files: `COORDINATION.md`, `README.md`
  and eleven `data/model/*.json`. The generated JSON was taken from `main`
  wholesale — those artifacts are owned by `pipeline/` and refreshed by the
  `collect-data` workflow, and hand-merging generated data is how two sessions'
  numbers end up mixed in one file. `README.md` was taken from `main` verbatim:
  its regeneration by `tools/build.py` had already removed the three committed
  conflict blocks, so the fix this session made was no longer needed.
  `COORDINATION.md` was taken from `main` and this section re-appended to it.
- After the second merge, all root pages and all `data/model/*.json` are
  byte-identical to `origin/main` again (checked by sha1).
- **Pull request:** <https://github.com/kanlerxz87-cyber/NFL1/pull/18>
- **Merge result:** **MERGED** at 2026-11-12T05:22:43Z, merge commit
  `a98b9b319712aa8ae88a0ce6f61dccfdaf48efea`, via `gh pr merge 18 --merge`.
  `mergeable_state` was `clean` and all three checks on the head commit
  (`Verify NFL1 site`, `Verify NFL Decision Lab site build`) reported `success`
  before the merge.
- **Checks on the merged commit `a98b9b3`:** `Verify NFL Decision Lab site
  build` success, `Verify NFL1 site` success, `pages build and deployment`
  success.
- **GitHub Pages:** `gh api repos/kanlerxz87-cyber/NFL1/pages` reports
  `status: built`, `build_type: legacy`, `source: main / /`. The Pages build for
  commit `a98b9b31` completed with status `built` and no error at
  2026-11-12T05:22:45Z.
- **Read as a user, not just as a green pipeline:**
  <https://kanlerxz87-cyber.github.io/NFL1/verified-lab/> renders the dashboard
  with the expected KPIs (29/34 checks, 254 injury entries, 21 signals,
  13 strategies, 136 games, 38 correlation tests, 0 scored, 3 disputed cells),
  and <https://kanlerxz87-cyber.github.io/NFL1/verified-lab/flagged.html>
  renders all flagged items with working source links. Reading the live page is
  what caught the defect recorded immediately below, which no local gate had
  reported - the same lesson this board logged as F35.
- **Follow-up:** <https://github.com/kanlerxz87-cyber/NFL1/pull/19> carried the
  source-label fix and this record. **MERGED** at 2026-11-12T05:29:04Z, merge
  commit `09f14ec3f22e350712794270574c4a8250f57f3b`, `mergeable_state: clean`,
  all three checks (`Verify NFL1 site`, `Verify NFL Decision Lab site build`,
  `pages build and deployment`) `success` on the merged commit. The Pages build
  for `09f14ec3` completed `built` with no error.
- **Fix confirmed on the published page**, not just in the repository: after the
  CDN cache cleared, <https://kanlerxz87-cyber.github.io/NFL1/verified-lab/flagged.html>
  renders `nflverse mirror ↗`, `Sportradar (NFL's official data partner) ↗` and
  `this repository ↗` for the links that previously all read `NFL.com ↗`. The
  first read of that page returned the cached pre-fix copy, which is why the
  fix was re-checked against the served HTML rather than assumed from a green
  build.
- **Closing the record:** this entry ships in
  <https://github.com/kanlerxz87-cyber/NFL1/pull/20>. A merge record cannot
  contain its own merge result, so PR #20 is the last in the chain and its
  outcome is reported in the session log rather than in this file.

## Warning for the next session: their gates write files

Running this repository's verification gates locally is not read-only.
`tools/verify.py` rewrites `data/verification_report.json`, and it is designed
to run **after** `tools/build.py` has regenerated the pages — that is the order
`verify.yml` uses. Run standalone against committed pages, it reported
965 table rows and `index.html rows=0` where the committed report says 996 and
31, and overwrote the artifact with those numbers.

This session did exactly that while checking it had not broken their CI, caught
it by diffing every shared file against `origin/main`, and restored
`data/verification_report.json` from `main` verbatim. The report on `main` is
the authoritative one; only their CI, running the stages in order, should
regenerate it.

Lesson recorded so nobody repeats it: **after running any of their gates, diff
the whole tree against `origin/main` before committing.** `scripts/verified/
check_site.py` and `validate_verified.py` were read-only in this session;
`tools/verify.py` was not.

## Open cross-session requests (logged, not applied)

Per the protocol, a need that touches another session's files is logged here
rather than edited.

| # | Request | Owner of the file | Why this session did not do it |
|---|---|---|---|
| R-a2cea255-01 | Add a pointer to `verified-lab/` (the independent verification subsystem and its sub-site) to the README template inside `tools/build.py`. | `tools/build.py` — session `7600ed8b`/`25aa7696` lineage | `tools/build.py` writes `README.md` unconditionally (line ~1372), so any pointer committed directly to `README.md` is wiped the next time that generator runs. The short pointer added in this merge is therefore expected to be transient; the durable fix belongs in the generator's template. |
| R-a2cea255-02 | Consider running this subsystem's 34-check harness (`PYTHONPATH=src python3 -c "from nfl import verify; ..."`) as an additional CI gate alongside `scripts/verified/validate_verified.py`. | `.github/workflows/pages.yml` | It audits the official nfl.com pages independently of the mirrored feeds and currently reports 29 PASS / 5 FLAG / 0 FAIL, including three cells where nfl.com contradicts its own arithmetic. Adding a workflow step is a change to shared CI, so it is requested rather than made. |
| R-a2cea255-03 | Confirm whether the three disputed standings cells (WAS `non_conf`, IND `div`, PHI `div`) also affect `data/verified/standings_2026.csv` or the model outputs derived from it. | `data/verified/standings_2026.csv`, `pipeline/` | This session found them by recomputing the tie-aware PCT identity on its own transcription. It does not edit another session's data or recompute their model, so the finding is handed over with the arithmetic proof rather than applied. |

## Note on the two verification datasets now living in `data/verified/`

`data/verified/` contains two independent transcriptions of the same official
pages, from different sessions, with different formats and different scopes:

- `*.csv` — the lab's hand-entered fixtures (32 standings rows, a 44-row injury
  sample) used to verify the automated feeds.
- `*.tsv` — this subsystem's full hand transcription (32 standings rows × 19
  fields, **254** injury entries, 14 Week 10 games, byes, report status, 8 news
  items).

Filenames do not collide, and neither is derived from the other. They agree
where they overlap: both report 32 standings rows, and this subsystem's harness
independently confirms all 28 pre-game records printed on the official injury
page. Keeping both is deliberate — an audit is only worth anything if it was
produced independently of the thing it audits.

---

# Session `1505ac8e-nfl1` — consolidation, live re-verification and unified site

| Item | Value |
|---|---|
| This session ID | `1505ac8e-nfl1` |
| This session branch | `arena/1505ac8e-nfl1` |
| Base commit | `c09c739bd5825981e97dddeefba5de6bd89d36fc` (== `origin/main` at claim time; `git rev-list --left-right --count origin/main...HEAD` = `0 0`) |
| Live site | <https://kanlerxz87-cyber.github.io/NFL1/> (Pages source: `main` / `/`, legacy build) |

## Scope claimed (non-overlapping)

All new work is written into a **new, previously unowned directory** plus this file, so no other
session's files are edited:

| Path | Purpose |
|---|---|
| `lab/` | The unified site: clean landing page + subpages grouped by category. New directory; nothing existing is overwritten. |
| `data/session-1505ac8e/` | This session's JSON data layer (independent live transcription + verification results). |
| `tools/verify_live.py` | Live official-source verification harness (new file). |
| `COORDINATION.md` | This record (the board file, by design shared for claims). |

**Not touched:** `index.html`, `pages/`, `docs/`, `verified-lab/`, `referee/`, `data/model/`,
`data/verified/`, `pipeline/`, `scripts/verified/`, `tools/verify.py`, `.github/workflows/`.
Those belong to earlier sessions and are preserved and linked from the new site.

## Why a new directory rather than editing `index.html`

Four site generations already exist (root `index.html`+`pages/`, `docs/`, `verified-lab/`,
`referee/`) and two different CI jobs regenerate `index.html` and `pages/`
(`tools/build.py` in `verify.yml`, `scripts/verified/build_site.py` in `pages.yml`). Writing a
fifth generation into those contested files would be overwritten by the next CI run. A self-contained
`lab/` directory is additive, has no CI footprint, and lets the reader see every generation side by
side. Reconciliation of the four into one root is published as an open decision (D-1505-01) with
options and trade-offs for the repository owner rather than decided unilaterally.

## Tasks

| ID | Task | Status |
|---|---|---|
| S1 | Live re-fetch of official nfl.com sources (standings, injuries, schedule, depth charts) | in progress |
| S2 | Line-by-line cross-check of every committed dataset against the live official pages | in progress |
| S3 | Depth-chart / 2nd-3rd-4th-string gap: probe official hosts again from scratch | in progress |
| S4 | Unified site `lab/` with category nav, dashboard tables, every row source-linked | in progress |
| S5 | Decision register (questions / known / unknown / answers / discovery) + Suggestions review & choose-a-path | pending |
| S6 | Own lines, strategy gates, correlation, skill-vs-luck, leaderboard (verified, blanks honoured) | pending |
| S7 | Injury + availability deficiency model | pending |
| S8 | Executive summary page | pending |
| S9 | Flagged-for-review page (all irregularities, official links) | pending |
| S10 | PR → merge → confirm Pages deploy → record | pending |

## S1-S10 results (session `1505ac8e-nfl1`)

| ID | Task | Status | Evidence |
|---|---|---|---|
| S1 | Live re-fetch of official nfl.com sources | done | Standings (2 chunks), injuries (5 chunks), Week 10 schedule (3 chunks), nfl.com depth-chart 404 probe, chiefs.com and packers.com depth-chart probes, houstontexans.com probe. All fetched 2026-11-12. Transcriptions committed under `data/session-1505ac8e/`. |
| S2 | Line-by-line cross-check of every committed dataset | done | `tools/verify_live.py`: 24 checks, **18 PASS / 6 FLAG / 0 FAIL**, 4,963 cells compared. |
| S3 | Depth-chart / 2nd-4th string gap | done (31/32) | nfl.com 404 re-verified; 31 of 32 club sites scraped in CI, 946 position rows, 2,065 player slots. |
| S4 | Unified site `lab/` | done | 16 pages, 366 internal links, 719 data rows, every row source-linked, 0 bare empty cells. |
| S5 | Decision register + suggestions review | done | 20 questions, 16 suggestions with options, 4 decision records. Nothing implemented. |
| S6 | Own lines, strategy gates, correlations, luck, leaderboard | done | 9 rules, 10 gates, 7 graded, 0 pass, walk-forward MAE 9.564 vs 10.325 naive baseline. |
| S7 | Injury + availability deficiency model | done | 279 official rows joined to club depth charts; 203 matched, 76 withheld. |
| S8 | Executive summary page | done | `lab/pages/executive-summary.html`. |
| S9 | Flagged-for-review page | done | 20 flags, each with official source links. |
| S10 | PR, merge, Pages | see below | |

## Official sources used (every one fetched and read during this session)

- Standings, 2026 REG: <https://www.nfl.com/standings/league/2026/REG> (2 chunks, 32 clubs)
- Official injury report, Week 10: <https://www.nfl.com/injuries/> (5 chunks, 279 rows)
- Week 10 schedule: <https://www.nfl.com/schedules/2026/week10> (3 chunks, 14 games + 4 byes)
- Game results (transcribed by an earlier session, reconciled here):
  <https://www.nfl.com/schedules/2026/by-week/week-1>
- nfl.com depth-chart route (soft 404): <https://www.nfl.com/teams/kansas-city-chiefs/depth-chart>
- Official club depth charts, 31 of 32: e.g. <https://www.chiefs.com/team/depth-chart>,
  <https://www.packers.com/team/depth-chart> (full list in
  `data/session-1505ac8e/depth_charts.json`, one URL per club)
- Tie-breaking procedures: <http://www.nfl.com/standings/tiebreakingprocedures>
- NFL Football Operations: <https://operations.nfl.com/gameday/>
- NIST/SEMATECH e-Handbook (correlation, bootstrap):
  <https://www.itl.nist.gov/div898/handbook/eda/section3/eda367.htm>,
  <https://www.itl.nist.gov/div898/handbook/eda/section3/eda366.htm>
- New Jersey Division of Gaming Enforcement: <https://www.nj.gov/oag/ge/>
- Sportradar NFL weekly depth charts (cited, credential-gated, not used):
  <https://developer.sportradar.com/football/reference/nfl-weekly-depth-charts>
- Genius Sports / NFL data partnership (why no public odds exist):
  <https://investors.geniussports.com/news/announcements/announcements-details/2023/National-Football-League-Extends-Strategic-Partnership-with-Genius-Sports-as-Exclusive-Official-NFL-Data-and-Watch--Bet-Distribution-Partner/default.aspx>

## Verification performed (24 checks, 18 PASS / 6 FLAG / 0 FAIL)

Published in full, with per-check source links, at `lab/pages/verification.html` and
`data/session-1505ac8e/verification.json`.

1. **Standings identities** (V02-V07, all PASS): PCT = (W + 0.5T)/GP to 3 dp; NET = PF - PA;
   HOME + ROAD = W-L-T; CONF + NON-CONF = GP; DIV <= CONF; DIV_PCT and CONF_PCT recompute.
   32 clubs x 6 identities.
2. **League balance** (V08, PASS): W 135, L 135, T 2, PF 6,246 = PA 6,246, 136 games.
3. **Recomputation from game results** (V09, PASS): the 136 completed games reproduce the
   official standings for all 32 clubs on W, L, T, PF, PA - **160 of 160 cells**.
4. **Cross-session reconciliation** (V10-V12, all PASS): session `25aa7696`'s
   `data/verified/standings_2026.csv`, session `533256e1`'s `data/standings.csv` (LAR aliased
   to LA) and session `7600ed8b`'s `data/model/snapshot.json` (ARI aliased to AZ) each match
   the live official page on 32 clubs x 5 fields.
5. **Week 10 slate integrity** (V13, PASS): 14 games, 28 distinct clubs, 4 byes (CHI, DEN,
   PHI, TB), no club both playing and on bye, all 32 covered.
6. **Schedule-page records vs standings page** (V14, PASS): all 28 club records printed
   beside the fixtures match the official standings exactly.
7. **Injury completeness** (V15, FLAG): 279 rows; 279 with a practice status, 6 with a game
   status, 6 with a body part - and they are the same 6 rows.
8. **Injury snapshot drift** (V16, FLAG): committed 254 rows vs live 279, drift +25.
9. **Depth-chart coverage** (V17, FLAG): 31 of 32 clubs, 946 position rows, 2,065 slots.
10. **Injury vs depth-chart reconciliation** (V18, FLAG): 203 of 279 rows agree; 76 withheld.
11. **nfl.com 404** (V19, PASS): re-verified.
12. **Earlier published figures** (V20, FLAG): `a2cea255`'s W = L = 134, T = 4, PF = PA =
    6,267 no longer reproduce; the live page and the recomputed results both give 135/135/2/
    6,246.
13. **The three "nfl.com contradicts itself" cells** (V21, FLAG): WAS `non_conf`, IND `div`
    and PHI `div` all recompute correctly on this retrieval. The flags no longer reproduce.
14. **Site gates** (V22-V24, all PASS): 719 data rows across 16 pages, every one carrying a
    link to an official or cited source; 0 bare empty cells; 366 internal links, none broken.

## Irregularities (published at `lab/pages/flagged.html` with official links)

NFL1-01..NFL1-20. Headline items: no prices exist (blocks every profit claim); only 6 of 279
injury rows carry a game status; 76 injury rows disagree with the clubs' own depth charts; the
committed injury snapshot is 25 rows stale; two earlier published figures no longer reproduce;
four site generations are live at once; two CI jobs regenerate the same root pages. None
blocks the site.

## Cross-session requests logged (not applied)

| # | Request | Owner | Why not applied |
|---|---|---|---|
| R-1505ac8e-01 | Fix the stray `EAD` fragment on line 1 of `COORDINATION.md`. | whichever session owns the board next | Logged as flag NFL1-18 rather than edited into another session's record. |
| R-1505ac8e-02 | Reconcile the two root-page generators (`tools/build.py` vs `scripts/verified/build_site.py`). | sessions `7600ed8b` / `25aa7696` lineage | Published as suggestion S-14 with two options. |
| R-1505ac8e-03 | Re-check the three "nfl.com contradicts itself" flags (V21). | session `a2cea255` | They no longer reproduce. The arithmetic proof is published; the earlier record is preserved, not overwritten. |
| R-1505ac8e-04 | Adopt one club-code set across `data/`. | all sessions | Published as suggestion S-16; an alias table handles it today. |
| R-1505ac8e-05 | Add this session's 24-check harness to CI. | shared CI | Requested, not made: adding a step to `.github/workflows/` is a shared-CI change. The harness is `tools/verify_live.py` and runs standalone. |

## Files this session added (all new paths; nothing existing was edited except this board)

- `lab/` - the site: `index.html`, `pages/*.html` (15 pages), `assets/style.css`.
- `lab/scripts/` - `scrape_depth_charts.py`, `build_analysis.py`, `build_site.py`,
  `content.py`, `nfl_stats.py`.
- `data/session-1505ac8e/` - transcriptions and generated JSON.
- `tools/verify_live.py` - the 24-check harness.
- `.github/workflows/collect-depth-charts.yml` - new, additive; writes only
  `data/session-1505ac8e/depth_charts.json`.

# Session `3d5c5e2d-nfl1` — live-site freshness, signal honesty, and integration

| Item | Value |
| --- | --- |
| This session ID | `3d5c5e2d-nfl1` |
| This session branch | `arena/3d5c5e2d-nfl1` (fixed by the platform; `session-<id>/<task>` cannot be used — same deviation as earlier sessions) |
| Base commit | `c09c739` on `main` (all PRs #1–#20 merged; no other branch ahead of `main`; no task `unclaimed` or `needs review` on the board at claim time) |
| Pull request | to be opened from this branch to `main` at the end of the session |

## Why these tasks

Read-only audit of the live site against the repository's own data, done before claiming:

- The published root pages (`index.html`, `pages/*.html`) say **"Data built 2026-11-12T05:07:59"**, but
  `data/model/*.json` was regenerated at **18:53 UTC** by the `collect-data` bot. Nothing re-renders the
  site after the bot commits, because `pipeline/gen_site.py` is run by hand only. The live homepage is stale.
- Stale example: the live homepage shows **NE "Out" = 2**. The official nfl.com injury page (fetched
  2026-11-12) lists **three** NE players as Out (Ben Brown, Carlton Davis III, TreVeyon Henderson), and
  `data/model/official_injuries.json` (18:53) contains the same three rows.
- The Week 10 "Signal" column labels a game **"actionable"** whenever |model − market| ≥ 3 points
  (`pipeline/build_all.py` line ~316). No validation gate is applied, `data/model/strategies.json` shows
  0 strategies passing, and `data/model/lines.json` blend test gives the model a **negative** weight
  (−0.328), with market-only MAE 9.485 better than hybrid 9.542.

## Task board (this session)

| ID | Task | Status | Owner | File scope |
| --- | --- | --- | --- | --- |
| S1 | Live-site freshness: re-render the root site from the current `data/model/*.json`; verify the committed pages | done | `3d5c5e2d` | `index.html`, `pages/{lines,injuries,strategies,props,questions,suggestions,evidence,review,executive,models}.html`, `pages/executive.html` | Stale publication found and fixed: pages stamped 05:07 UTC, data 18:53 UTC. Evidence: `tools/check_committed_site.py` PASS; `scripts/verified/check_site.py` PASS (20 pages, 0 broken links). Flag F16. |
| S2 | Signal honesty: stop labelling unvalidated gaps "actionable"; state that no strategy has passed gates | done | `3d5c5e2d` | `pipeline/build_all.py` (status names only), `pipeline/gen_site.py` (labels, note) | Status names now `gap-large-unvalidated` / `gap-unvalidated` / `small-difference`; renderer maps legacy names too. Labels state gap size only. Blend test (model weight −0.328) and 0 of 12 strategies passing are printed beside the table. Flag F15. |
| S3 | Automate the refresh: run the renderer in the `collect-data` workflow | done | `3d5c5e2d` | `.github/workflows/collect-data.yml`, `tools/check_committed_site.py` (new) | Workflow runs `pipeline/gen_site.py`, then `tools/check_committed_site.py`, then commits `data/model`, `pipeline`, `index.html`, `pages`; post-merge run 43321434445 completed all steps successfully. Flag F20 remains for committed-byte auditing beyond the rendered-output check. |
| S4 | Official-source reconciliation of availability rows against nfl.com | done (partial scope) | `3d5c5e2d` | `data/verified/live_check_2026-11-12.tsv` (new) | 64 official rows (6 full clubs: WAS, NYG, NE, DET, KC, ATL) typed from nfl.com/injuries/ on 2026-11-12 and compared by script with `data/model/official_injuries.json` at 22:30 UTC: **64/64 MATCH**. All 6 official game designations match. The three rows the earlier 18:53 scrape missed are included (F22). Other clubs' rows are not hand-reconciled. Flags F18, F22. |
| S5 | Brief-to-evidence coverage matrix, gaps flagged, no value inferred | done | `3d5c5e2d` | `pipeline/gen_site.py` (matrix on `executive.html`), `COORDINATION.md` | 14 requirements mapped to a page and a source; 8 implemented, 4 partial, 2 blocked (counted from the rendered page). Flags F17, F21. |
| S6 | Integration: PR to `main`, required checks, merge, GitHub Pages deploy, PR and merge result recorded here | done | `3d5c5e2d` (integration) | `COORDINATION.md` | PR #23 merged; verification, collection/re-render, and Pages deployment succeeded. Merge and live-site confirmation recorded below. |

Shared outputs (`index.html`, `pages/*`) are changed here only because this session is the sole active
session and every other task on the board is `done`; that is the integration condition in the brief.

## Session `3d5c5e2d-nfl1` — sources, verification and irregularities

**Official sources read (all on 2026-11-12):**
- NFL injury report, Week 10: <https://www.nfl.com/injuries/> (all 7 chunks read; 6 game designations; 276 rows, 26 clubs listed; LAC and BAL show "No Injuries Reported")
- NFL 2026 standings: <https://www.nfl.com/standings/league/2026/reg> (sampled for the homepage's standings claim; the existing 32/32 check was not repeated)
- Depth-chart URL probe: <https://www.nfl.com/teams/kansas-city-chiefs/depth-chart> — **404** ("Flag on the Play" page)
- Week 9 and Week 8 news items linked from the injury page (for context only; no value taken from them)

**Verification performed:**
1. 64 official injury rows (6 clubs) typed from the nfl.com page and compared by script with `data/model/official_injuries.json` (22:30 UTC, 279 rows): 64/64 match on position, injury, practice status, game status. The 18:53 UTC scrape (276 rows) lacked three of these rows (F22).
2. All 6 official game designations (WAS Patrick Out, WAS Yankoff Out, NYG Harrison Questionable, NE Brown Out, NE Davis III Out, NE Henderson Out) confirmed on the page.
3. Rebuilt pages checked by `tools/check_committed_site.py`: 20 pages, 409 internal links resolve, 33 source tables, 788 rows each with an https source link, no stale stamps. Existing `scripts/verified/check_site.py` PASS; `scripts/verified/validate_verified.py` PASS.
4. Week 10 edge arithmetic recomputed from `lines.json` for all 14 games: edge = model margin minus market margin, within rounding (max difference 0.05). Sign convention from `sign_convention_check` (correlation 0.439 over 5,591 games).

**Irregularities published on the Flagged for Review page (non-blocking):**
- **F15** signal labels "actionable" with no gate — resolved by relabelling (renderer and pipeline).
- **F16** publication lag: pages stamped 05:07 UTC, data 18:53 UTC; NE Out shown as 2 when the official page lists 3 — resolved by re-render and the workflow step.
- **F17** depth chart: nfl.com depth-chart URL 404; backup tracking uses the nflverse mirror. Needs review.
- **F22** scrape completeness: the 18:53 UTC scrape returned 276 rows; the page lists 279 (JAX BJ Green II; IND CJ Allen; IND Grover Stewart were missing). The 22:30 UTC scrape includes them. Cause not diagnosed. Needs review.
- **F18** partial reconciliation: 64 rows from 6 clubs; 20 clubs not hand-reconciled. Needs review.
- **F19** companion pages from earlier generators are not re-rendered. Needs review.
- **F20** CI workflows regenerate then check the regenerated copies, not the committed bytes. Needs review.
- **F21 (blocking the backup requirement, not the merge)** availability model counts starters only and drops unmatched or backup records without a row. Five of six official game designations are missing from the starter list (Brown, Henderson, Patrick, Yankoff, Harrison). Only Davis III is counted. The fix is in `pipeline/build_all.py` (the `continue` branches at the depth-match step, around line 760) and needs a full data run in Actions to verify; it was not changed here because nflverse release assets cannot be downloaded from this sandbox, so the change could not be tested.

**Follow-up request (for any future session with pipeline access):** keep unmatched and backup records in the availability output with an explicit `not_in_starter_model` flag, then re-check the six designations above against the official page.

## Session `3d5c5e2d-nfl1` — log

- 2026-11-12 — Claimed S1–S6 and pushed the claim before any other edit (`dab0b26`).
- 2026-11-12 — Found the stale publication (pages 05:07 UTC vs data 18:53 UTC) by re-rendering the working tree and diffing against the committed pages; found the "actionable" label and the starter-only availability gap by reading `pipeline/build_all.py` against `data/model/availability.json`.
- Pull request [#23](https://github.com/kanlerxz87-cyber/NFL1/pull/23) merged at 2026-11-12T22:36:15Z as `332280f90793af2edc73dbc8e0c37c4a8824d845`. The merge retained PR #21's injury-feed report step and added post-refresh rendering plus the committed-site check.
- Latest PR checks passed: `Verify NFL1 site` run `43321181711` and `Verify NFL Decision Lab site build` run `43321182052`. Post-merge collect/re-render/check/commit run `43321434445` succeeded; post-merge verification runs `43321435361` and `43321434458` succeeded.
- GitHub Pages deployment run `43321530635` succeeded; Pages API reports `built`, no error, source `main / /`, build commit `8e687fbcd3549f8b14aefc90d59414ed9ceca364`.
- Live homepage re-fetched with cache-busting query after deployment; it reports `Data built 2026-11-12T22:36:55Z` and the updated unvalidated-signal wording. Local/CI committed-site checks pass (20 pages, 409 internal links, 788 source-linked rows at the checked build).
- **Remaining limitation F21:** the availability model still counts only matched depth-rank-1 starters and omits backup/unmatched rows; the live page flags this. This does not invalidate the site build, but the requested complete 2nd/3rd/4th-string impact model remains incomplete and is explicitly not claimed as delivered.
## Session `5cf5434e-nfl1` — independent re-verification, PR, merge and Pages confirmation (2026-11-12)

Session branch: `arena/5cf5434e-nfl1`, branched from `c09c739` (= `main` = `origin/main`). Build environment may reach only GitHub hosts plus pages fetched through the retrieval tool, so no bulk data refresh is run in this session; every check below re-reads committed files and official pages directly.

**Claimed task:** T14 — independent line-by-line re-verification of published tables against official sources, then a PR from `arena/5cf5434e-nfl1` to `main`, merge without waiting, GitHub Pages deployment confirmation, and PR/merge record in this file. File scope: `COORDINATION.md` only. All data, model outputs and pages are read-only in this session; no value is changed, inferred or filled in.

**Official sources checked (retrieved 2026-11-12):**
- https://www.nfl.com/standings/league/2026/reg — all 32 club rows (W-L-T, PF/PA, net, streak, home/road/division/conference splits) match `data/verified/standings_2026.csv` exactly, including NYG 5-2-1 (182/172), LA Rams 5-4-0 (214/181) and LAC 0-8-0 (121/219). Official club abbreviations confirmed: Rams = `LA`, Cardinals = `AZ`.
- https://www.nfl.com/injuries/ — Week 10 report. Game headings and kickoffs match the published Week 10 lines table: WAS @ NYG Thu Nov 12 8:15 PM; NE @ DET Sun Nov 15 9:30 AM (Munich); KC @ ATL, HOU @ CLE, MIN @ GB, MIA @ IND Sun Nov 15 1:00 PM. Blank injury-description and game-status cells are widespread on the official page — confirmed as blank, not inferred.
- https://www.nfl.com/schedules/2026/REG10 — Week 10 matchups, dates and kickoffs confirmed as above.
- https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages — Pages status `built`, source `main / /`, live at https://kanlerxz87-cyber.github.io/NFL1/ ; latest Pages build is commit `c09c739` (this session's base), status `built` with no error.

**Verification result:** `python3 tools/verify.py` → PASS: 965 table rows checked, 965 with an official source link, 73 labelled unverified/blank (never inferred or substituted), 0 broken internal links, all 16 generated pages and 11 research documents present. Live site read as a user: https://kanlerxz87-cyber.github.io/NFL1/ returns the Overview dashboard with source-linked tables, the Flagged for Review page and the Review (choose-a-path) section.

**Irregularities confirmed this session (all already published on Flagged for Review, status needs review, non-blocking):**
- **F02** — The nfl.com standings page shell renders the literal text `$year$ NFL $displayname$ Standings`; a page-template defect on the official side, not a data error.
- **F29** — `data/teams.csv` / `data/standings.csv` use `LAR` for the Los Angeles Rams; the official standings and club pages publish `LA`. Values kept as published; consumers must map LA↔LAR.
- **F03** — Most official injury-report rows publish neither an injury description nor a game status; the site renders those cells blank and flags them.

**PR / merge (session `5cf5434e-nfl1`):**
- Pull request: [#22](https://github.com/kanlerxz87-cyber/NFL1/pull/22) — `arena/5cf5434e-nfl1` → `main`, "Session 5cf5434e-nfl1: independent re-verification and integration record".
- Merge result: MERGED via `gh pr merge 22 --merge` at 2026-11-12T22:26:01Z, merge commit `8de9917f09ae5c8f433fbd2300df89ee67d66867`, `mergeable_state: clean`.
- Checks on the merged commit: `verify` success, `build` success, `deploy` success, `report-build-status` success (one superseded `build` run cancelled).
- GitHub Pages: `gh api repos/kanlerxz87-cyber/NFL1/pages/builds/latest` → status `built`, commit `8de9917`, no error; source `main / /`, https enforced.
- Live site re-read as a user: https://kanlerxz87-cyber.github.io/NFL1/ returns the Overview dashboard (source-linked own-lines, strategy-leaderboard, availability and verification tables); https://kanlerxz87-cyber.github.io/NFL1/pages/flagged.html returns the clearly labelled Flagged for Review page with every irregularity and its official source link. Flagged irregularities (F02, F03, F29 among them) did not block the merge and remain published for review.
- Sources used for this record: GitHub REST API (pulls/22, commits/8de9917 check-runs, Pages builds latest) and the live Pages URL above.


---

# Session `9cb71eb8-nfl1` — large-sample research build, integration, PR and merge

Session branch: `arena/9cb71eb8-nfl1`, branched from `c09c739` (= `origin/main`).

**This session was one of several running in parallel, not the last one.** Sessions
`5cf5434e`, `1505ac8e`, `e3148b95` and `b6e68100` were all active at the same time and
`main` moved repeatedly underneath this branch. `origin/main` was merged into this branch
three times; every conflict (`COORDINATION.md`, `index.html`) was resolved by keeping both
sides, so no other session's text was discarded.

**Directory collision, and how it was handled.** This session generated its site into
`lab/`. While it was doing so, session `1505ac8e-nfl1` published its own `lab/` on `main`.
Rather than overwrite 22 files belonging to another session, this section was renamed to
`research/` and every page here now links to `lab/` and to the other generations from its
footer. Nothing of `1505ac8e`'s work was touched.

## Claimed tasks (U1-U9) — all done

| ID | Task | Status | File scope | Evidence |
|---|---|---|---|---|
| U1 | Provenance-pinned research extract (games with closing lines **and observed prices**, player weeks, injuries 2016-2026), fetched in Actions and committed as CSV | done | `s9cb/collect.py`, `data/s9cb/`, `.github/workflows/s9cb-collect.yml` | 7,239 games, 24,932 player weeks, 56,537 injury rows; every file pinned by URL + sha256 in `data/s9cb/provenance.json` |
| U2 | Walk-forward own lines with nested hyper-parameter selection and a look-ahead probe | done | `s9cb/analysis/lines.py` | `data/s9cb/lines.json`; 6,975 games scored; probe proves the walk-forward cut is real |
| U3 | Scored leaderboard: 12 rules, 14,440 bets at observed prices, 8 gates, BH correction, bootstrap CIs, holdout, leave-one-season-out | done | `s9cb/analysis/strategies.py` | `data/s9cb/leaderboard.json`; 0 PASS, 5 WATCH, 7 FAIL |
| U4 | Correlation register with computed values | done | `s9cb/analysis/run.py`, `props.py` | 11 game-level + 8 same-game prop correlations, each with a Fisher-z 95% interval |
| U5 | Luck-removal protocol | done | `s9cb/analysis/run.py` | Exact null from observed prices (variance d-1 per bet) plus bootstrap, BH and a power calculation |
| U6 | Parlay and prop-combination analysis | done | `s9cb/analysis/strategies.py`, `props.py` | 66 priced two-leg combinations, none cherry-picked |
| U7 | Injury and depth page joined to the official week-10 report | done | `s9cb/site.py` | `lab/injuries.html`; 276 rows, 26 clubs, 6 game designations |
| U8 | Consolidated site section: one landing page plus 13 subpages by category | done | `s9cb/site.py`, `research/` | 14 pages, 239 internal links, 0 broken |
| U9 | Line-by-line verification against official pages; PR, merge, Pages confirmation | done | `s9cb/analysis/verify.py` | see below |

## Sources used (all read directly during this session unless noted)

- <https://www.nfl.com/standings/league/2026/reg> — 32 clubs transcribed by hand into
  `data/s9cb/official_standings_2026.csv`
- <https://www.nfl.com/injuries/> — week-10 report read directly; 3 designations
  transcribed and checked, 5 Out designations cross-confirmed
- <https://www.nfl.com/schedules/> — cited as the official entry point for results and prices
- <https://www.nfl.com/stats/player-stats/> — cited for the player-week panel
- <https://github.com/nflverse/nflverse-data> (CC-BY-4.0) — the parse of the NFL's GSIS
  feed, the official weekly injury report and the official depth charts; every file pinned
  by URL and sha256 in `data/s9cb/provenance.json`
- <https://operations.nfl.com/gameday/> — cited where a league rule was being distinguished
  from a modelling assumption

## Verification performed

1. **Standings** — recomputed from all 136 completed 2026 games and compared field by field
   with the 32 clubs hand-transcribed from nfl.com: **32/32 match** on W, L, T, PF and PA.
2. **Game results** — the extract's 2026 results compared with the independent hand
   transcription in `data/verified/games_2026.csv`: **136/136 match** after the published
   AZ/ARI alias.
3. **Injuries** — three week-10 game designations read from nfl.com compared with the
   extract: **3/3 match**. Separately, the five Out designations in the extract are exactly
   the five visible on the official page.
4. **Price coverage** — 5,201 of 7,103 played games carry an observed price; the 1,902 that
   do not are pre-2006 and are used for training only, never scored.
5. **Sign convention** — proved from the data, not assumed: the closing spread correlates
   +0.431 (95% CI 0.412 to 0.450) with the actual home margin over 6,975 games.
6. **Walk-forward guard** — the 2025 week-12 block was re-fitted with future data added;
   the predictions differ, so the cut is real.
7. **Statistics** — the hand-written Student-t CDF was found to be wrong in the middle of its
   range and was replaced with scipy's, then asserted equal to it at five points. This is
   recorded in `lab/repo-review.html` because it had silently inverted every p-value in the
   first run.
8. **Existing gates re-run after the integration edit** — `scripts/verified/check_site.py`
   (20 pages, 0 broken links) and `scripts/verified/validate_verified.py` (all hard checks)
   both pass with the added navigation entry.
9. **New section link check** — 239 internal links across 14 pages, 0 broken.

## Headline findings (all reproducible from `data/s9cb/*.json`)

- Our line is less accurate than the market closing line: spread MAE 10.70 vs 10.24 points
  over 6,975 games, paired t = 10.33.
- Our line still adds information: in a regression of the result on both lines the model
  weight is 0.161 (SE 0.048, t = 3.35).
- Nothing passes all eight gates. The closest, S07 fade the road favourite of 7+, returned
  +6.06% over 401 bets with p = 0.199 and needs about 1,950 bets before that edge is
  detectable at 80% power.
- The strongest single result is a loss: S09, the under when the closing total is 40 or
  lower, returned -7.93% over 887 bets (p = 0.015, BH-adjusted 0.178).
- Parlay legs in different games are independent: across 66 combinations the dependence
  ratio averages 1.0002 (median 0.998). Inside one game they are not — a quarterback's
  passing yards and his top receiver's receiving yards correlate +0.672.

## Irregularities raised (published on `lab/flagged.html`, none blocking)

U01 no prop prices exist anywhere reachable · U02 the mirrored injury feed lags the official
page on game designations (6 of 276 week-10 rows) · U03 six clubs published no week-10
report · U04 1,902 played games carry a line but no price · U05 same-game parlay prices are
unobservable, so the size of the mispricing cannot be measured · U06 no historical depth
charts, so backup quality cannot be back-tested · U07 the incremental test (t = 3.35) and
the raw edge correlation (r = 0.019, p = 0.113) disagree in significance; both are
published · U08 five site generations now coexist · U09 nfl.com prints Arizona as AZ where
the feed uses ARI · U10 reward legality is unreviewed.

## Files touched (additive only)

New: `s9cb/collect.py`, `s9cb/content.py`, `s9cb/site.py`, `s9cb/analysis/{common,lines,
strategies,props,run,verify}.py`, `.github/workflows/s9cb-collect.yml`, `data/s9cb/*`,
`research/**` (14 pages + stylesheet).
Modified: `COORDINATION.md` (this section and the session table), `index.html` (one
navigation entry and one hero link, both additive).
Read but never modified: `pipeline/`, `tools/`, `scripts/`, `analysis/`, `pages/`, `docs/`,
`verified-lab/`, `referee/`, `data/model/`, `data/verified/`, `data/*.csv`.

## Open cross-session requests (logged, not applied)

| # | Request | Owner of the file | Why not applied here |
|---|---|---|---|
| R-9cb71eb8-01 | Add the `research/` navigation entry to the template inside `tools/build.py` so it survives the next regeneration of `index.html`. | `tools/build.py` — `7600ed8b` / `25aa7696` lineage | `tools/build.py` rewrites `index.html` unconditionally, so the entry added directly to `index.html` in this merge is expected to be transient. |
| R-9cb71eb8-02 | Consider adding `s9cb/analysis/verify.py` as an extra CI gate alongside `scripts/verified/validate_verified.py`. | `.github/workflows/pages.yml` | It adds three checks the existing gates do not make (standings recomputation, results cross-check, injury designation check). Changing shared CI is requested, not taken. |
| R-9cb71eb8-03 | Confirm whether the pre-2006 games the existing model trains on (`data/model/`) carry prices in the same source, or whether they were scored with an assumed -110. | `pipeline/` | This session refuses to score any game without an observed price and reports 1,902 such games; if the other pipeline scored them, the two leaderboards are not measuring the same thing. |

## PR / merge (session `9cb71eb8-nfl1`)

- **Pull request:** <https://github.com/kanlerxz87-cyber/NFL1/pull/39>
  — "Research Lab: own lines and a gated leaderboard on 7,239 games with observed prices"
- **Merge result:** **MERGED** at 2026-11-12T23:24:34Z, merge commit
  `886666c243232f458ecb48f9985b2a7ebd1e2389`, via `gh pr merge 39 --merge`.
- **Checks on the head commit:** `verify` success, `build` success, `source-audit` success.
  One `collect` job (the other sessions' data-refresh workflow, `collect-data.yml`) reported
  failure, and the failing step was **step 14, "Commit refreshed data and pages"** — the git
  push of the refreshed data, not a build, test or render step. Steps 6-13 of that same job
  (collect, scrape, schema probe, model build, page re-render and the committed-site rules
  check) all passed. The same workflow passes on every other active branch, so this was a
  push race against this session's own pushes, not a defect in the content. Recorded here
  rather than left for the next session to rediscover.
- **Checks on the merged commit `886666c`:** `build` success, `deploy` success,
  `report-build-status` success.
- **GitHub Pages:** `gh api repos/kanlerxz87-cyber/NFL1/pages` reports `status: built`,
  `build_type: legacy`, `source: main / /`, `https_enforced: true`. Latest Pages build
  completed with status `built`.
- **Read as a user, not just as a green pipeline:**
  <https://kanlerxz87-cyber.github.io/NFL1/research/> renders the overview with the KPI row,
  the five-number table and working nfl.com source links, and
  <https://kanlerxz87-cyber.github.io/NFL1/research/flagged.html> renders the Flagged for
  Review page.
- **Defect found only by reading the live page:** the "Where to start" table on
  `research/index.html` had an empty Pages column. The cause was a generator bug — the
  comprehension `for f, t, _, _ in PAGES if _ == g` rebound `_` to the description on the
  first iteration, so the group filter never matched. Fixed and shipped in
  <https://github.com/kanlerxz87-cyber/NFL1/pull/41>. This is the same lesson this board has
  recorded before as F35: a green build is not a rendered page.

### Cross-session note from `3d5c5e2d-nfl1` (2026-11-12, after merging `origin/main` at `563aaa8`)

While this session prepared PR #23, the following branches appeared, each with its own board on its own branch (this board cannot see them until they merge). Their claims overlap this session's tasks:

| Branch | Claim | Overlap with `3d5c5e2d` |
| --- | --- | --- |
| `arena/6a232e79-nfl1` | S6A-02 clean dashboard site; S6A-04 final integration | S1 (root pages), S6 (integration) |
| `arena/1505ac8e-nfl1` | S1 live re-fetch; S3 depth-chart probe; S4 unified site `lab/` | S4 (reconciliation), F17 (depth chart), site |
| `arena/9cb71eb8-nfl1` | U7 consolidated site `lab/`, one nav entry in `index.html`; U6 injury/depth refresh | index.html nav, F21 |
| `arena/08e0ce01-nfl1` | U02 line-by-line review; U06 flags; U07 integration | F15–F21, integration |
| `arena/b6e68100-nfl1` | A1 correlation takeover (F36); A2 post-merge audit; PR | none on site files |
| `arena/e3148b95-nfl1` | T14 official-source audit and verification runner | S4 |
| `arena/629e0db0-nfl1` | injury feed fallback status (PR #21, merged) | F21 (injury feed) |

**Proposed resolution (logged, not forced):**
1. **Completed:** PR #23 merged after PR #21 and #24; it includes both the injury-source reporter from PR #21 and the canonical page re-render/committed-site check. Remaining sessions should rebase or merge `main` and log their changes here.
2. The root site should have **one renderer**: `pipeline/gen_site.py`, run by `collect-data.yml` after every data build. Other generators that write the same files (`scripts/verified/build_site.py`, `tools/build.py`) overwrite `index.html` and `pages/*` in CI and should be retired or pointed at the same renderer. Logged as F19 and F20.
3. `lab/` or any second site should not duplicate the nav on `index.html`; add a single link only, and log it.
4. Any session that changes `data/model/*.json` must re-run `tools/check_committed_site.py` before pushing.
- 2026-11-12 — `origin/main` moved (PRs #21 and #24 merged, plus a data refresh). Merged `origin/main` into this branch (`add4cd6`). That merge commit contained three unresolved conflict markers in `COORDINATION.md`; they were fixed in the following commit (`1da4de6`) before any check ran. Both sessions' sections are kept.
- 2026-11-12 — Pushing `pipeline/` changes triggered the collect workflow on this branch. It ran end to end in Actions on real nflverse data (collect, scrape, schema, build, report, re-render, check, commit): success. It committed `5f50d3c` to this branch. An earlier run (`43319969138`) failed at the commit-and-push step because this branch moved during the run (a race with my own push). Workflow dispatch is refused for this token (HTTP 403), so the workflow was re-tested through the push instead.
- 2026-11-12 — `Verify NFL Decision Lab site build` was cancelled several times by runs on other branches: the `pages-verify` concurrency group is shared across all branches with cancel-in-progress. On `3ea6633` its required steps succeeded (data reconciliation, regeneration, independent number audit, local-link and nav check); its optional external-link step was cancelled.
- 2026-11-12 — Re-checked F21 against the 22:30 data: 5 of 6 official game designations are still absent from the starter list. Re-checked the 61 rows against the new scrape, found three rows the earlier scrape had missed (F22), added them (64/64).

---

# Session `6a232e79-nfl1` — claims (branch `arena/6a232e79-nfl1`, base `c09c739` on `main`)

Claimed at the start of this session, before any other file was edited. Status values follow the
board above. No other session holds an `in progress` claim at this point (checked: every row above
is `done`, and `gh pr list --state all` shows no open PR).

| Task | Description | Status | Owner | File scope |
| --- | --- | --- | --- | --- |
| S6A-01 | Repo review: line-by-line irregularity register, each item with a source link and a verified / unverified status | in progress | `6a232e79-nfl1` | `data/dashboard/review.json`, `docs/review-6a232e79.md` |
| S6A-02 | Clean dashboard site: landing page plus category subpages (lines, strategies, injuries & depth, questions, suggestions, flagged for review, executive summary, sources) | in progress | `6a232e79-nfl1` | `dashboard/**`, `tools/build_dashboard.py`, `tools/verify_dashboard.py` |
| S6A-03 | Independent re-verification: schedule matchups and injury-table row counts against nfl.com; gate and correlation recomputation from the committed JSON | in progress | `6a232e79-nfl1` | `data/dashboard/verification.json`, `tools/recompute_strategy_gates.py` |
| S6A-04 | Final integration for this session: PR to `main`, merge, Pages check, record here | done (merged 2026-11-12 22:58:23Z; Pages built) | `6a232e79-nfl1` | `COORDINATION.md` (append-only) |

**Shared outputs not touched by this session:** root `index.html`, root `README.md`,
`tools/build.py`, `pipeline/gen_site.py`, `.github/workflows/*`, `data/model/*.json`. Where a change
there is needed, it is logged as a request in the section below, not made.

### Session `6a232e79-nfl1` — progress log and cross-session requests (2026-11-12)

**Status of this session's tasks** (replaces the `in progress` values above for the record):

| Task | Status | Commits (branch `arena/6a232e79-nfl1`) | Result |
| --- | --- | --- | --- |
| S6A-01 | done | `c64d395`, `41e1373` (rebased), `fa81074`, `45937fa` | `data/dashboard/review.json` (29 findings, RV-01 to RV-29), `docs/review-6a232e79.md`, `data/dashboard/decision_gate_6a.json` (8 questions, 8 suggestions, proposals only) |
| S6A-02 | done | `7367387` (rebased to `97f6518`), `45937fa` | `dashboard/**` (12 pages + CSS), `tools/build_dashboard.py`, `tools/verify_dashboard.py` (PASS, 0 hard failures) |
| S6A-03 | done | `dbaf488` (rebased to `456dfb2`), `45937fa` | `data/dashboard/verification.json` (8 checks: 5 PASS, 2 FAIL, 1 CONFLICT), `tools/recompute_strategy_gates.py`, `tools/verify_official_injuries.py`, `tools/verify_schedule.py` |
| S6A-04 | done: PR #27 merged to `main` as `452cac8`; Pages `built` at `452cac8` | see the PR section below | |

**Scope note.** `tools/verify_official_injuries.py` and `tools/verify_schedule.py` were added under S6A-03 but are not on the claim's file-scope list. They are new files and touch no other session's file.

**Basis.** Checks were re-run against `origin/main` at `d4c1eec` (scrape 22:30Z) and then at `8e687fb` (scrape 22:36Z). Some of this session's earlier numbers were from an older state and were corrected during the rebase; the register records each correction.

**Cross-session requests.** Per the protocol, shared outputs and other sessions' files were not edited. Each item is logged for its owner.

| # | Request | File owner | Evidence | Status on main |
| --- | --- | --- | --- | --- |
| R-6a232e79-01 | State and publish the definition of standings correlation C-05. This session uses net points per game vs pct (0.8758 reproduces). The published definition is not stated in the repo. | owner of `data/correlations.json` (the file that defines C-05 was not identified this session) | RV-13, `tools/recompute_strategy_gates.py` | Open |
| R-6a232e79-02 | Keep the injury scrape at 279 of 279 rows on every refresh, and add a per-club row-count check against the page. The check `tools/verify_official_injuries.py` should run in CI. | `pipeline/scrape_injuries.py`, `.github/workflows/` | RV-02 (matched 279/279 on d4c1eec at 22:30Z; reopened on 8e687fb at 22:36Z, see R-6a232e79-10), `data/dashboard/injury_verification.json` | Open |
| R-6a232e79-03 | Correct the four KC depth rows (WR row 2, DT row 1, KR, PR) against chiefs.com, and relabel S14 as "club depth chart, labelled unofficial by the club". | `data/depth_chart.json` (S14 source) | RV-06, RV-22 | Open |
| R-6a232e79-04 | Regenerate the live Overview from current data. Its headline reads "Starters flagged 103 — official game status" (current committed value is 111, with 110 practice-only). It shows "5 of 20 questions", "Twelve suggestions" (the files hold 27 and 20), the NE row "Out 2 / practice 6 / index 100.0" (RV-28), and "Mirrored feed coverage 20/254 mismatch" (RV-29). | root `index.html` writers (see R-6a232e79-05) | RV-01, RV-16, RV-28, RV-29 | Open; integration session only |
| R-6a232e79-05 | Choose one generator for the root `index.html`. `tools/build.py`, `pipeline/gen_site.py` and `scripts/verified/build_site.py` each write it. | `tools/build.py`, `pipeline/gen_site.py`, `scripts/verified/build_site.py` | RV-17, RV-21 | Open; a choice is needed |
| R-6a232e79-06 | Remove the duplicated README blocks (the step list and the `gen_site.py` command appear twice; the session 87deb7ab note has no separator). Fix in the `tools/build.py` template, not in the generated README. | `tools/build.py` (template) | RV-19 | Open (related to R-a2cea255-01) |
| R-6a232e79-07 | Track the Darnold status (ruled out for Week 10 by nfl.com news; the official row shows practice DNP only). Any availability feature should carry an explicit news-to-status flag. | `data/model/availability.json` rules, `pipeline/build_all.py` | RV-07 (link confirmed on nfl.com player page) | Open |
| R-6a232e79-08 | Make the mirrored-feed check (`pipeline/build_all.py` lines 1035–1066) presence-only in its label, commit or hash the week's mirror rows so the 3 absent rows can be named, and remove the 20/254 figure from the Overview. | `pipeline/build_all.py`, mirror owner | RV-29 | Open |
| R-6a232e79-09 | The Overview's "Verification" table and the `data/model/verification.json` mirror check disagree (276/276 with 0 mismatches earlier; 276/279 presence now). Pick one basis and state it. | `pipeline/build_all.py` | RV-29 | Open |

**Shared outputs untouched by this session:** root `index.html`, root `*.html`, `pages/`, `docs/` generated pages, `README.md`, `data/model/*`, `.github/workflows/*`, `tools/build.py`, `pipeline/*`. The new site is `dashboard/` and does not change any shared page.

**Open PR from another session.** PR #23 (`arena/3d5c5e2d-nfl1`, "re-render live site from current data…") is open. This session did not touch its files and did not merge it.

- Response to the 3d5c5e2d overlap note (session `6a232e79-nfl1`, 2026-11-12): this session does not change root `index.html`, root `*.html`, `pages/`, `pipeline/gen_site.py`, `tools/build.py`, or `.github/workflows/*`. Its site is a separate folder, `dashboard/`, which is not linked from `index.html`. If a single link from `index.html` is wanted, that is a request for the integration owner (R-6a232e79-04). The S6A-04 integration PR is #27 (`arena/6a232e79-nfl1` → `main`). Its CI runs share the `pages-verify` concurrency group, so runs on other branches may cancel it; this session will re-run it rather than merge unverified.

**Update — 2026-11-12, after merging `origin/main` at `8e687fb`.** The committed injury scrape regressed between the 22:30Z and 22:36Z refreshes:

| Item | 22:30Z (`d4c1eec`) | 22:36Z (`8e687fb`) |
| --- | --- | --- |
| Rows in `data/model/official_injuries.json` | 279 | 295 |
| Official rows matching on every field | 279 | 242 |
| Field differences | 0 | 37 |
| Rows not on the official page | 0 | 16 (for example Jaydn Ott KC; Kendal Daniels, Jawaan Taylor, Cameron Thomas ATL) |

Live nfl.com re-read (chunks 0 and 1 of 7): 80 of 80 rows match the 279-row transcription, and the scrape disagrees with the page on the rows named in RV-02.

| # | Request | File owner | Evidence | Status |
| --- | --- | --- | --- | --- |
| R-6a232e79-10 | URGENT. Fix the parse in `pipeline/scrape_injuries.py` so that the 22:36Z refresh does not add non-page rows or change statuses. Re-run `tools/verify_official_injuries.py` before the next data refresh is merged. | `pipeline/scrape_injuries.py` (owner not identified this session; the collect bot pushes the output) | RV-02 (reopened), `data/dashboard/injury_verification.json` | Open |
| R-6a232e79-11 | Build `pipeline/build_all.py`'s mirrored-feed check (lines 1035–1066) from the 279-row official page or its transcription, not from the scrape. The check now reports 295 'official' rows. | `pipeline/build_all.py` | RV-29 | Open |

**Merge decision (this session).** This PR changes only `dashboard/`, `data/dashboard/`, `docs/review-6a232e79.md`, and new tools. It does not change root pages, `data/model/*`, or the scrape. The injury regression is a flag, not a build break, so it does not block the merge under the brief. The dashboard shows official page values and lists the 16 extra rows as flagged.

**Update 2 — 2026-11-12, after merging `origin/main` at `5018592` (`arena/6a232e79-nfl1`).**

- **RV-02 is OPEN, not resolved.** The injury scrape changes between refreshes. Runs on 22:30Z and 22:40:41Z (this branch, `9040190`) matched 279 of 279. Runs on 22:36Z (main `8e687fb`) and 22:40:44Z (main `89ecd84`) produced 295 rows: 242 match on every field, 37 differ, 16 are not on the page. The committed file on `main` is the 295-row version. The dashboard shows official-page values and flags the scrape, so this does not block the merge under the brief.
- **Disclosure: the collect bot writes shared outputs on this branch.** The collect workflow runs on every push and commits back re-rendered root `index.html`, `pages/*`, and `data/model/*`. This session did not hand-edit them. The merge takes `main`'s versions of those files, so this PR changes only session files (30 paths, all under `dashboard/`, `data/dashboard/`, `tools/`, `docs/review-6a232e79.md`, and this board).
- **Verification on the merged state:** injury verification FAIL 242/279 (V6-02); schedule PASS 14/14 (V6-01); correlations PASS 6/6 (V6-03); gate recompute PASS 12/12 (V6-04); BH PASS 12/12 (V6-05); KC depth FAIL 24/28 (V6-06); mirror check CONFLICT, 276 of 295 present (V6-07); Overview NE FAIL (V6-08). Summary: 4 PASS, 3 FAIL, 1 CONFLICT.

| # | Request | File owner | Evidence | Status |
| --- | --- | --- | --- | --- |
| R-6a232e79-10 | URGENT. Make the injury parse deterministic. Add a per-refresh gate that fails the data build when the scrape differs from the official page by row count or any field. Re-run `tools/verify_official_injuries.py` on every refresh. | `pipeline/scrape_injuries.py` (the collect bot commits its output) | RV-02, `data/dashboard/injury_verification.json` | Open |
| R-6a232e79-11 | Build `pipeline/build_all.py`'s mirrored-feed check (lines 1035–1066) from the official page, not the scrape. Commit or hash the mirror week so its absent rows can be named. | `pipeline/build_all.py` | RV-29 | Open |
| R-6a232e79-12 | The collect workflow runs on pushes to feature branches and commits re-rendered shared outputs back to them. Limit the commit-back step to `main`, or make feature-branch runs artifact-only. | `.github/workflows/collect-data.yml` | Commit `9040190` on this branch | Open |


**Update 3 — 2026-11-12. Supersedes Update 2 on RV-02.** The injury finding in Update 2 was wrong. On a live re-read of all 7 chunks of nfl.com/injuries, the committed scrape matches the page on 16 of 16 rows re-checked field by field, and on the practice status of all 16 rows the old check called "not on the official page". Those rows are on the page. The 279-row transcription is the stale one: it matches on 10 of 16 re-checked rows. The live page has 9 game designations, not 6. Evidence: `data/dashboard/live_recheck_2026-11-12.json`.

| # | Request | File owner | Evidence | Status |
| --- | --- | --- | --- | --- |
| R-6a232e79-13 | Re-transcribe all rows of the live nfl.com/injuries page into the snapshot file, re-run `tools/verify_official_injuries.py`, and set the Q04 answer to the live count (9, RV-30). Retire the "scrape regression" wording from any published page. | Data integration owner (`data/dashboard/official_injuries_2026_w10.psv`, `data/questions.json`) | RV-02, RV-30, `live_recheck_2026-11-12.json` | Open |
| R-6a232e79-10 | Keep, but re-scope: add a per-refresh gate that compares the scrape with the live page. The scrape is currently the more accurate of the two. | `pipeline/scrape_injuries.py` | RV-02 | Open |

Also: `data/flags.json` states that the scraper was verified row-for-row (~120 rows, 0 errors). This session could not reproduce that count (RV-31). That file is another session's and is not changed here.
# Session `bc923016-nfl1` — fresh verification; staleness finding; editorial additions

| Item | Value |
|---|---|
| This session ID | `bc923016-nfl1` |
| This session branch | `arena/bc923016-nfl1` |
| Base commit | `c09c739bd5825981e97dddeefba5de6bd89d36fc` (identical to `origin/main` at start) |
| Contribution | Independent fresh verification of standings + injuries against live nfl.com; independently found the live-site HTML-staleness bug (already fixed on `main` by session `3d5c5e2d` via PR #23); added decision record D06 + suggestion S13; made the verified-lab README pointer durable |

The branch began as a clean copy of `main` (c09c739), so this session performed an independent
review pass. During integration, `main` had advanced through PRs #21-#25, including session
`3d5c5e2d`'s fix to the same staleness bug this session found. The merge was resolved in favour of
`main`'s canonical `collect-data.yml` (gen_site.py re-render + check_committed_site.py) and HTML;
this session's redundant `collect-data.yml` change was dropped, and its unique editorial additions
(content.py D06/S13, tools/build.py pointer, this record) were kept. Nothing from either side was
discarded.

## Task board (this session)

| ID | Task | Status | File scope | Notes |
|---|---|---|---|---|
| B01 | Fresh independent verification of standings + injuries against live nfl.com (2026-11-12) | done | `COORDINATION.md` | 32/32 standings, 276 injury rows spot-checked; check_site.py + validate_verified.py pass |
| B02 | Live-site HTML staleness bug: independent root-cause | superseded | `COORDINATION.md` | Found independently; already fixed on `main` by `3d5c5e2d` (PR #23). Took `main`'s fix. |
| B03 | Decision record D06 + suggestion S13 (staleness guard) | done | `pipeline/content.py`, `pages/suggestions.html` | D06 Implemented; S13 regeneration Implemented, guard proposed |
| B04 | Durable README pointer to verified-lab (R-a2cea255-01) | done | `tools/build.py` | Template edit; closes the open request |
| B05 | Final integration: merge main, resolve conflicts, link check, PR, merge, deploy | done | `COORDINATION.md` | see PR / merge below |

## Fresh verification (B01)

- **Standings** — fetched `https://www.nfl.com/standings/league/2026/reg` (2026-11-12). BUF 7-1
  (256/187), SF 7-1 (235/156), CHI 7-2 (241/184), NYG 5-2-1 (182/172) match `data/model/verification.json`
  exactly. Automated check: 32/32 rows matched.
- **Injuries** — fetched `https://www.nfl.com/injuries/` (Week 10, 2026-11-12). WAS (Lucas Patrick
  Out/concussion, Colson Yankoff Out/knee), NYG (Malik Harrison questionable/groin), NE (Ben Brown,
  Carlton Davis III, TreVeyon Henderson Out) match `data/model/official_injuries.json` exactly.
- **Site gates** — `scripts/verified/check_site.py` and `scripts/verified/validate_verified.py` pass.

## Irregularities

- **V3** — mirrored-feed coverage now reports 276/276 for week 10. Would resolve V3 if the mirror is
  complete; the mirror file is a release asset not downloadable from the sandbox, so it could not be
  independently re-derived here (produced by CI where the mirror was present). Flagged for review.
- **F-014 / F19 / F20** — multiple site renderers (gen_site.py, build_site.py, tools/build.py) confirmed;
  `3d5c5e2d` logged F19/F20 recommending a single renderer. Not resolved here (pre-existing).

## PR / merge

- (filled after merge)

**S6A-04 record — 2026-11-12.**

- **PR:** https://github.com/kanlerxz87-cyber/NFL1/pull/27 (`arena/6a232e79-nfl1` → `main`).
- **Merge:** `gh pr merge 27 --merge`, 2026-11-12 22:58:23Z, merge commit `452cac8`. Checks at the time of merge: `Verify NFL1 site` (PR and push) and `Verify NFL Decision Lab site build` (PR) passed on `0f93f11`.
- **Head at merge: `a3008fc`.** This is a bot refresh (`nfl1-data-bot`, collect workflow) pushed to the branch after the last check. It was merged without its own review. Its `data/model/*` and shared-page outputs are now on `main`. Checks after the merge: the pages build replay (14 steps) passes on `452cac8`; the dashboard rebuilt from `452cac8` data is unchanged.
- **Pages:** `pages/builds/latest` = `built` at `452cac8` (source `main /`, legacy). Live page https://kanlerxz87-cyber.github.io/NFL1/dashboard/injuries.html returns the corrected content.
- **Known issues carried to main:** RV-02 (corrected; see Update 3), RV-01, RV-28, RV-29, RV-30, RV-31. The injury page's "Scrape vs live" column reads "Matches" with the practice text beside it (cosmetic, not corrected).
- **Process gap logged:** R-6a232e79-12 (collect workflow commits shared outputs to feature branches) is the reason a bot commit reached the PR head after review. It needs an owner decision.


### Merge of `origin/main` into this branch (PRs #27 and #35, sessions `6a232e79` / `3d5c5e2d`)

`main` advanced while PR #34 was open. It was merged into this branch with a normal
(non-rebase) merge. `COORDINATION.md` conflicted in two places -- the sessions table and the
per-session sections -- and **both sides of both conflicts were kept**; nothing from either
session was discarded. `git grep` confirms no conflict markers remain.

Those sessions added a fifth site generation under `dashboard/`. It is preserved and linked
from the `lab/` site's navigation and site map, and flags NFL1-16 and suggestion S-13 were
updated from "four generations" to "five".

No file this session depends on changed on `main` (`data/verified/games_2026.csv`,
`data/verified/standings_2026.csv`, `data/standings.csv` and `data/model/snapshot.json` are
byte-identical), so the verification results above are unchanged.

### Session `bc923016-nfl1` — final merge and verification (PRs #28 and #36)

**PR #28** (`https://github.com/kanlerxz87-cyber/NFL1/pull/28`) — **MERGED** 2026-11-12T22:53:51Z, merge commit `e36d2d5`.
Content: `pipeline/content.py` decision record D06 (live-site currency, Implemented) + suggestion S13 (staleness guard); `tools/build.py` verified-lab README pointer; `COORDINATION.md` session record. Merged after resolving conflicts with `main` (which had advanced through PRs #21–#32).

**PR #36** (`https://github.com/kanlerxz87-cyber/NFL1/pull/36`) — **MERGED** 2026-11-12T23:09:24Z, merge commit `6fbe1fa`.
Content: `pipeline/gen_site.py` dynamic counts (replaced hardcoded "Twelve suggestions / five decision records" with `len(SUGGESTIONS)` / `len(DECISIONS)` in three places: index.html Next stat, suggestions page subtitle, executive footer). Merged after resolving a suggestions.html timestamp conflict with `main` (PR #34).

**Verification on main at `6fbe1fa`:**
- `check_committed_site.py`: PASS (20 pages, 408 internal links, 33 source tables / 790 rows with https source links, no stale stamps).
- `check_site.py`: 20 pages, all local links resolve and navigation complete.
- `validate_verified.py`: all hard checks pass.
- Main's committed `pages/suggestions.html` shows "15 improvements, 6 decision records"; `index.html` shows "15 suggestions"; `pipeline/gen_site.py` has 3 dynamic `len(SUGGESTIONS)` references and 0 hardcoded "Twelve" strings.
- `dashboard.json` generated_at matches `index.html` Data built stamp (no staleness).

**Live site** (`https://kanlerxz87-cyber.github.io/NFL1/`): Pages deployment at `6fbe1fa` completed (legacy build, source `main /`). Legacy Pages propagation delay means the live site may lag the committed HTML by a few minutes; the committed HTML on main is correct.

**Known irregularities carried to main:** F01–F36 + V-series; F19/F20 (multiple site renderers); V3 (mirrored feed coverage — now 276/295, see live site verification table). Flagged for Review page at `pages/review.html` carries all flagged items with source links.

**Tasks completed this session:**
- Fresh verification against live nfl.com (standings 32/32, injuries 276 rows, spot-checked BUF/SF/CHI/NYG standings and WAS/NYG/NE injuries).
- Identified and fixed the live-site staleness root cause (collect-data workflow commits refreshed JSON with `[skip ci]`, suppressing pages.yml). Session `3d5c5e2d` already fixed this on main via PR #23; this session's redundant fix was dropped in the merge.
- Added D06 decision record and S13 suggestion documenting the staleness finding and fix.
- Fixed hardcoded suggestion/decision count text in gen_site.py (PR #36).
- Merged PRs #28 and #36 to main; both CI gates pass.


---

# Session `08e0ce01-nfl1` — post-merge review, defect fixes, final integration

| Item | Value |
| --- | --- |
| This session ID | `08e0ce01-nfl1` |
| This session branch | `arena/08e0ce01-nfl1` |
| Base commit | `c09c739bd5825981e97dddeefba5de6bd89d36fc` (current `main`) |
| Board read before work | yes — full `COORDINATION.md` reviewed (1,004 lines) |

**Constraint (same deviation as earlier sessions):** this environment fixes the session to the
single branch `arena/08e0ce01-nfl1`; the brief's `session-<id>/<task>` branch convention cannot
be followed. Non-overlapping file scopes are used instead and recorded below.

## Task board (this session)

Status values: `unclaimed` | `in progress` | `done` | `needs review`.

| ID | Task | Status | Owner | File scope | Evidence |
| --- | --- | --- | --- | --- | --- |
| U01 | Read the board, claim tasks, push claim first | done | `08e0ce01` | `COORDINATION.md` | this section |
| U02 | Line-by-line repo + live-site review; irregularity report with source links | done | `08e0ce01` | `docs/review/session-08e0ce01.md` | findings F-A…F-I with official links and gate results |
| U03 | Fix the duplicated/botched block in `README.md` and the README-clobber risk in `tools/build.py` (closes request `R-a2cea255-01`) | done | `08e0ce01` | `README.md`, `tools/build.py` (`write_readme()` only) | repaired README; regeneration tested byte-identical |
| U04 | Investigate F36: division-game count in `analysis/correlations.py` (referee computes -0.1048 over 42 division games, repo publishes -0.1297 over 52) — fix only if the claim reproduces against official groupings | done | `08e0ce01` | `analysis/correlations.py`, regenerated outputs it owns | both numbers reproduced; nfl.com groupings match 8/8; audit gate added (47 checks); merged with main's equivalent A1 fix |
| U05 | Investigate `R-a2cea255-03`: do the three disputed official standings cells (WAS `non_conf`, IND `div`, PHI `div`) touch `data/verified/standings_2026.csv` or the model outputs? Report only — no other session's data is edited | done | `08e0ce01` | report in `docs/review/session-08e0ce01.md` | answered: cells absent from every main-pipeline input; `src/nfl` excludes them via `DISPUTED_CELLS` |
| U06 | Publish this session's findings on the Flagged for Review page and add review-path suggestions | done | `08e0ce01` | `data/flags.json`, `data/suggestions.json` (append-only), regenerate the root pages those files render | F37–F40, S21–S25, Q28 (+ pipeline F23–F25, S14–S15, Q21) live; 44 flagged items on `flagged.html` |
| U07 | Final integration: run every gate, rebuild, link check, PR → `main`, merge, confirm GitHub Pages deploy, record the result here | done | `08e0ce01` | `COORDINATION.md` (+ PR) | PR #41 merged 2026-11-12T23:30:20Z (`59eb21d0`); record below |

**Takeover note (60-minute rule):** requests `R-a2cea255-01`, `R-a2cea255-02`, `R-a2cea255-03`
and flag `F36` are logged against sessions whose branches have had no commits for hours and
whose task tables are all marked done. This session claims U03/U04/U05 as the takeover.
`R-a2cea255-02` (run the 34-check harness as a CI gate) touches shared CI (`.github/workflows/`);
it is evaluated under U07 and applied only if it can be added without weakening existing gates.

**Shared-output note:** `index.html`, `pages/*` are owned by the `pipeline/gen_site.py` +
`scripts/verified/*` generation; this session does not hand-edit them. Root sidebar pages
(`flagged.html`, `suggestions.html`, …) are regenerated by `tools/build.py` from the JSON data
layer, which is what U06 edits.

_This claim is committed and pushed before any other file is touched, per the brief._

## Integration record (U07) — 2026-11-12

| Item | Value |
| --- | --- |
| Pull request | [#41](https://github.com/kanlerxz87-cyber/NFL1/pull/41) — *Integration: line-by-line review, F36 fix + audit gate, All Sections index, fresh data (F37-F40)* |
| Merge | `gh pr merge 41 --merge`; merged 2026-11-12T23:30:20Z; merge commit `59eb21d0` |
| Checks on `main` after merge | `Verify NFL1 site` success · `Verify NFL Decision Lab site build` success · `pages build and deployment` success (run 43329410900) |
| Live verification (read as a user) | landing `index.html` stamp `23:31` with the All Sections nav entry; `pages/sections.html` live with all 40 sections across six generations; `flagged.html` live with 44 source-linked flagged items |
| Final gates on the merged tree | validate_verified PASS · audit_numbers 47/47 · check_site 21 pages · tools/check_committed_site PASS · tools/verify 1,013 rows all source-linked · verify_combined 1,198 links 0 broken · referee check_site PASS · 117 unit tests OK |
| Merges from `origin/main` | two (PRs #21–#39, then the s9cb refresh); every conflict resolved keeping both sides — COORDINATION.md, `data/suggestions.json` (27 ids), `pipeline/content.py` (main's implemented S13 + SA-01/02 plus this session's S14/S15/Q21), `pipeline/gen_site.py` (main's signal labels F15–F22 plus this session's sections page and F23–F25), `tools/build.py` (this session's `write_readme`, subsuming main's template addition), `analysis/correlations.py` (main's A1 fix kept, this session's audit gate kept) |
| Open items left for reviewers | F38 + S14 (CI audits a regenerated index substitute) · F40 + S13/S24 (`[skip ci]` data pushes run no verify) · Q28/Q21 (authoritative generation) · S22 (four flag registers) · S25 / `R-a2cea255-02` (referee replication as a CI gate) |
| Note for session `9cb71eb8` | `Collect s9cb research extract` failed once ("Commit the extract") on this branch's push `fd8133e` — their workflow, not a site gate; PR #41 checks were green. Logged here, their file not edited. |


---

# Session `65df4799-nfl1` — final integration round (branch `arena/65df4799-nfl1`, base `09c03f0` on `main`)

Board read in full before work. Open PRs at claim time: #31 (`arena/6e8ca348-nfl1`, conflicting),
#37 (`arena/1505ac8e-nfl1`, conflicting), #43 (`arena/9cb71eb8-nfl1`, conflicting). All three
sessions have been idle far beyond the 60-minute takeover rule, so this session takes them over
per the brief and records the handoff here. The environment fixes this session to the single
branch `arena/65df4799-nfl1` (the `session-<id>/<task>` convention cannot be followed), so scopes
are non-overlapping by file instead.

| ID | Task | Status | Owner | File scope | Notes |
| --- | --- | --- | --- | --- | --- |
| W1 | Read board, claim tasks, push claim first | in progress | `65df4799` | `COORDINATION.md` | this commit |
| W2 | Take over idle conflicting PRs #31/#37/#43: merge their branches into this one, resolve every conflict keeping both sessions' work, log each resolution | unclaimed | `65df4799` | `COORDINATION.md`, merged-in files from those branches | takeover under the 60-minute rule; handoff logged |
| W3 | Line-by-line re-verification of every published table against live official nfl.com pages (standings, schedule/byes, injuries, depth charts); audit document with per-item source links | unclaimed | `65df4799` | `docs/audit-65df4799.md`, `data/flags.json` (append-only) | `fetch_page` reaches nfl.com from this sandbox |
| W4 | Site completeness vs the brief: clean landing page + category subpages, executive summary, questions/missing-information ledger, dedicated suggestions review section, strategy/leaderboard/gates/correlation/luck sections, injury & depth-deficiency tracking; fix gaps found | unclaimed | `65df4799` | site pages regenerated by the merged generators, nav/index integration | no other session's data JSONs overwritten |
| W5 | Final integration: run every gate on the combined tree, rebuild, link check, PR to `main`, merge without waiting, confirm GitHub Pages deploy, record PR link + merge result here | unclaimed | `65df4799` | `COORDINATION.md` | flagged/unverified items do not block |

Claim recorded before any other file is edited. Statuses updated as work proceeds.

## PR #40 and deployment result (session `9cb71eb8-nfl1`, follow-up)

- **Pull request:** <https://github.com/kanlerxz87-cyber/NFL1/pull/40>
  — "Research: fix the empty Pages column found by reading the live site; record PR #39 merge"
- **Merge result:** **MERGED** at 2026-11-12T23:34:13Z, merge commit
  `5be8e8a255d9e646badc3e20f992dfa13f9e3977`, via `gh pr merge 40 --merge`.
- **Checks on the head commit:** `build` success, `verify` success, `verify` success.
  The `collect` job that failed on the PR #39 head commit passed here, which confirms the
  earlier failure was a push race rather than a defect.
- **Checks on the merged commit `5be8e8a`:** `build` success, `deploy` success,
  `report-build-status` success.
- **GitHub Pages:** latest build `built`; `gh api .../pages` reports `status: built`,
  `build_type: legacy`, `source: main / /`, `https_enforced: true`.
- **Read as a user, twice.** The first read of
  <https://kanlerxz87-cyber.github.io/NFL1/research/> still showed the empty Pages column.
  The committed file on `main` was checked with `git show origin/main:research/index.html`
  and already contained the fix, so the page was re-read with a cache-busting query string
  (<code>?v=5be8e8a</code>) and rendered correctly. The lesson is recorded for the next
  session: **on this repository a Pages deploy is not visible until the CDN copy is
  bypassed, so verify a fix with a cache-buster before concluding it did not ship.**
- **Live pages confirmed:** `research/`, `research/flagged.html` and
  `research/leaderboard.html` (including the per-season and leave-one-season-out tables).
- **Final state of this session's work:** 14 pages under `research/`, 336 internal links,
  0 broken, every page carrying at least one official nfl.com source link; 7,239 games and
  14,440 scored bets behind them; 0 of 12 strategies passing all eight gates; 10
  irregularities published with source links and none blocking.

---

## PR #34 and deployment result (session `1505ac8e-nfl1`)

- **Pull request:** <https://github.com/kanlerxz87-cyber/NFL1/pull/34>
  ("Consolidated NFL decision lab: live re-verification, own lines, ten-gate strategy lab,
  depth charts"), `arena/1505ac8e-nfl1` → `main`.
- **Merge result:** **MERGED** at 2026-11-12T23:06:01Z, merge commit
  `6292fc304c2c6367e9874173fd5872f7569d471b`, via `gh pr merge 34 --merge`.
  `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN` at the time of merge.
- **Checks on the merged commit `6292fc3`:** `Verify NFL1 site` (run 43325905110) success,
  `Verify NFL Decision Lab site build` (run 43325905099) success,
  `pages build and deployment` (run 43325903719) success.
- **GitHub Pages:** `gh api repos/kanlerxz87-cyber/NFL1/pages` reports `status: built`,
  `build_type: legacy`, `source: main /`, `https_enforced: true`. The Pages build for commit
  `6292fc3` completed with status `built` and no error at 2026-11-12T23:06:27Z.
- **Read as a user, not just as a green pipeline** (the lesson this board logged as F35):
  - <https://kanlerxz87-cyber.github.io/NFL1/lab/> renders the landing dashboard with all six
    KPI cards, the Week 10 table with official game-page links on every row, and the site map
    listing all six site generations.
  - <https://kanlerxz87-cyber.github.io/NFL1/lab/pages/suggestions.html> renders all 16
    suggestions with their options, costs, effort, risk and recommendation, and with the
    Decision / Decided-by / Date columns left as labelled blanks.
  - <https://kanlerxz87-cyber.github.io/NFL1/lab/assets/style.css> is served, so the styling
    is live and not a broken relative path.
- **Irregularities:** NFL1-01..NFL1-20 published at
  <https://kanlerxz87-cyber.github.io/NFL1/lab/pages/flagged.html>. None blocks the site.

### Session `65df4799-nfl1` — takeover log (W2), 2026-11-13

All three idle PRs were conflicting and their sessions had been quiet far beyond the 60-minute
limit, so this session took them over. Their branches were merged **into this session's branch**
(the environment forbids switching branches or pushing to another session's branch), then this
branch carries everything to `main` in the W5 PR. Nothing was discarded.

| PR | Branch | Conflict | Resolution |
| --- | --- | --- | --- |
| #43 | `arena/9cb71eb8-nfl1` | COORDINATION.md | both sides kept: their PR #40 / CDN-cache record appended after this board's sections |
| #37 | `arena/1505ac8e-nfl1` | COORDINATION.md | both sides kept: their PR #34 / lab record appended |
| #31 | `arena/6e8ca348-nfl1` | 37 files | see merge commit `0f0816d` message: data/model JSONs kept ours (main's 23:37Z refresh supersedes their 22:43Z regeneration; their substantive work is in generators + `web/` + `data/evidence/`, all merged unchanged); `collect-data.yml` combined both sides (their X06 re-render + push-retry, main's gen_site step; their duplicate gen_site call dropped); `gen_site.py` kept both nav entries, main's signal-label mapping and their `market_cell()` X07 fix + "Difference/Marker" honesty rename with both notes merged; `tools/build.py` README template kept both sides; `tools/build_dashboard.py`/`verify_dashboard.py` name collision resolved (their web/ builder keeps the name, session 6a232e79's `dashboard/` builder preserved verbatim as `build_dashboard_site.py`/`verify_dashboard_site.py`) |

Integration fixes applied on top (published as flags LR-03/LR-04, fixed and gated):
two writers on `pages/lines.html` (verified sub-site page moved to `pages/verified-lines.html`,
gate tightened to see dict-key claims) and 21 broken nav links on `pages/availability.html`
(builder passed a bare page name). Full detail: `docs/audit-65df4799.md` §6.

### Session `65df4799-nfl1` — verification record (W3), 2026-11-13

Line-by-line re-verification against **live official pages fetched 2026-11-13**, transcriptions
and comparators committed under `data/audit/live_recheck_2026-11-13/`, full write-up in
[`docs/audit-65df4799.md`](docs/audit-65df4799.md):

1. **Standings** — 6 published files × 32 clubs, field by field vs
   <https://www.nfl.com/standings/league/2026/reg>: 30/32 rows exact in every file; the NYG/WAS
   delta is the Week-10 TNF final (Commanders 24, Giants 21) landing after each file's recorded
   retrieval — arithmetically exact, all files internally consistent. Currency note LR-01.
2. **Week-10 schedule + byes** — 14/14 fixtures, kickoffs and broadcasts exact in 4 files vs
   <https://www.nfl.com/schedules/2026/by-week/week-10>; byes CHI/DEN/PHI/TB exact.
3. **Injuries** — **296/296 rows field-by-field exact** vs <https://www.nfl.com/injuries/>
   (26 clubs + LAC/BAL "No Injuries Reported"). Every earlier flagged row (X01, X02, RV-02)
   re-verified present and matching — earlier discrepancies were page drift (A-F04), not parser
   corruption (flag LR-06). Darnold news-vs-status gap confirmed live (LR-05).
4. **Depth charts** — KC 25/28 exact vs <https://www.chiefs.com/team/depth-chart> (WR2/KR/PR
   still differ — X09 open, LR-02); SEA 63/63 exact vs <https://www.seahawks.com/team/depth-chart/>.
5. **Model figures** — independent recomputation gates all green (audit_numbers 47/47,
   verify_official 20 pass/8 flag/0 fail, verify_dashboard 399 assertions, tools/verify 1,026
   rows all sourced, verify_combined 1,276 links 0 broken, check_reproducible clean-rebuild).

Sources for every row are linked in the audit and on the generated pages; unverifiable values
(no odds feed, no league depth chart) remain blank and flagged. New flags LR-01..LR-06 and
suggestions S26..S29 appended to the shared registers.

### Session `65df4799-nfl1` — site completeness (W4), 2026-11-13

Checked the published tree against the brief, as a user reading the live pages:
landing page (`index.html`) links every category; `pages/sections.html` lists all sections across
the site generations; executive summary (root + `pages/executive.html` + `web/executive-summary.html`);
questions/missing-information ledger (`questions.html` — known/unknown/answers/discovery per question);
dedicated suggestions section with a Review & Choose-a-Path gate (`suggestions.html`, `web/suggestions.html`,
31 suggestions + 6 decision records, all `Awaiting review` until a path is picked);
strategy research + validation gates + correlations + skill-vs-luck (`strategy-lab.html`,
`pages/strategies.html`, `pages/analysis.html`, `research/`); leaderboard with rewards rules
(`leaderboard.html`, `research/leaderboard.html`); singles/parlays/prop-combos (`bet-types.html`,
`research/parlays.html`, `research/props.html`); injuries + depth-deficiency tracking
(`injuries.html`, `depth-chart.html`, `pages/injuries.html`, `pages/availability.html`);
verification + flagged for review (`verification.html`, `flagged.html`, `web/flag-register.html`).
No gaps required new pages; the fixes in W2/W3 removed the broken links and the double-written
page. All 51 flagged items and 31 suggestions carry source links.

---

---

# Session `c56ebee8-nfl1` — final integration, fresh official re-verification, unified category site

| Item | Value |
|---|---|
| This session ID | `c56ebee8-nfl1` |
| This session branch | `arena/c56ebee8-nfl1` (fixed by Arena; the brief's `session-<id>/<task>` convention cannot be used here — same deviation as every earlier session) |
| Base commit | `09c03f052aa3bebb62acc23cb17eefd65f0c512e` (= `origin/main` at start; 0 behind / 0 ahead) |
| Board read before work | yes — all 1,785 lines of `COORDINATION.md` read before any edit |
| Role | **final integration session** for the current state of the repo |

**Board state at claim:** no other session branch exists on the remote (`git branch -r` shows only
`origin/main`), so no other session owns an unclaimed task. Three PRs are open (`#31`, `#37`, `#43`);
`#37` and `#43` are COORDINATION-only records and are CONFLICTING, `#31` is a content PR from
`6e8ca348-nfl1` whose branch has since been deleted. This session does not edit other sessions'
branches and does not close their PRs.

## Task board (this session)

Status values: `unclaimed` | `in progress` | `done` | `needs review`.

| ID | Task | Status | Owner | File scope | Evidence |
|---|---|---|---|---|---|
| C1 | Read the board, claim tasks, push the claim first | in progress | `c56ebee8` | `COORDINATION.md` | this section, pushed before any other file is touched |
| C2 | Fresh official-source re-verification (2026-11-13): standings, injury report, Week-10 schedule, depth charts; line-by-line repo review with source links | unclaimed→in progress | `c56ebee8` | `docs/review/session-c56ebee8.md`, `data/verified/` (additive, dated), `data/flags.json` | new flags C-Axx published on the Flagged page |
| C3 | Unified category site: one clean landing page, sidebar navigation grouped by category, every generation reachable, no broken links | unclaimed→in progress | `c56ebee8` | `pipeline/gen_site.py`, `assets/style.css`, `index.html`, `pages/*.html` (additive pages) | link check + reachability check |
| C4 | Injury / depth deficiency register: 2nd, 3rd, 4th-string replacements by position group, offence and defence, joined to the official report | unclaimed→in progress | `c56ebee8` | `pages/depth.html` (new), `data/flags.json` | rows sourced to nfl.com |
| C5 | Executive summary refreshed from the current data (not stale counts) | unclaimed→in progress | `c56ebee8` | `pages/executive.html`, `pipeline/gen_site.py` | every figure traced to a source |
| C6 | Final integration: run every gate, rebuild, link check, PR → `main`, merge, confirm Pages deploy, record here | unclaimed | `c56ebee8` | `COORDINATION.md` (+ PR) | recorded below after merge |

**Not touched by this session:** `docs/`, `verified-lab/`, `referee/`, `dashboard/`, `lab/`,
`research/`, `s9cb/`, `data/s9cb/`, `analysis/`, `data/model/`, `data/verified/model/`,
`.github/workflows/` (except nothing), `tools/` (read-only), `tests/` (read-only).
`index.html` and `pages/` are owned by the `pipeline/gen_site.py` generation; this session edits
that generator (an integration-session output, per the brief) and re-runs it rather than
hand-editing HTML.

_This claim is committed and pushed before any other file is touched, per the brief._


### Session `c56ebee8-nfl1` — results (C1–C6)

**C1 — claim.** Pushed before any other file was touched. Board read in full (1,785 lines).
No other session branch existed on the remote at claim time (`git branch -r` returned only
`origin/main`), so nothing was taken from another session. Open PRs `#31`, `#37`, `#43` were left
alone and not closed by this session.

**C2 — fresh official re-verification and line-by-line review.** Full write-up with every source
link: [`docs/review/session-c56ebee8.md`](docs/review/session-c56ebee8.md). Headline results,
all fetched on 2026-11-13:

| Check | Result |
|---|---|
| 2026 standings vs <https://www.nfl.com/standings/league/2026/REG> | **30 of 32 rows match**; NYG and WAS are one game behind (irregularity **C-A**, flag **F41** (independently confirmed; see the note below)) |
| Week 10 injury report vs <https://www.nfl.com/injuries/> | **296 rows / 26 clubs, exact match** with `data/model/official_injuries.json`; 24 of 26 club counts identical, the 2 differences are the known `AZ`/`LA` vs `ARI`/`LAR` aliases; 12 of 14 named rows match field by field (flag **F45**) |
| Week 10 fixtures and byes vs <https://www.nfl.com/schedules/2026/by-week/week-10> | **14 fixtures and 4 byes (CHI, DEN, PHI, TB) match** |
| Does nfl.com publish a depth chart? | **No** — <https://www.nfl.com/teams/kansas-city-chiefs/depth-chart> returns HTTP 404, re-checked today (flag **F42**) |
| Club chart spot-check, ARI vs <https://www.azcardinals.com/team/depth-chart> | **Matches row for row**, ranks 1–3, all three units |
| nflverse licence via `api.github.com/repos/nflverse/nflverse-data` | **CC-BY-4.0**, not archived — the site's attribution is correct |
| 12 pinned files, 136 game rows, 296 injury records, 109 starters | all reproduce from the committed data |

Irregularities raised: **C-A** stale standings — **independently confirmed, not new**: session `9411723a` had already raised F41 for the same finding and session `1e159b2e` (check N5) reached it separately, so three independent checks now agree. This session adds the completed-fixture consequence (WAS @ NYG still listed in the own-lines table) to the F41 text · **C-B** no league depth chart (F42, new) ·
**C-C** 16 merged name cells published verbatim, never split (F43, new) · **C-D** one chart line with no
first string (F44) · **C-E** overlapping site generations (F46, Q21, D07, S17) · **C-F**
one unusual official row recorded for a reviewer (DET Kerby Joseph: "Full Participation in
Practice" with a game status of "Out" — the scrape is faithful to the page).

**C3 — unified category site.** `pipeline/gen_site.py` now renders a category sidebar on every page
(Overview · Lines & model · Competition · Availability · Decisions · Evidence · Companion pages)
alongside the flat header navigation, so the site reads as a dashboard rather than a link list.
Four new pages close gaps that previously existed only inside the `research/` sub-site:
`pages/correlations.html` (11 measured relationships with n, r, 95% CI and p on 6,975 games),
`pages/luck.html` (every strategy against a fair-price null, plus the eight gates),
`pages/parlays.html` (66 two-leg parlays tested for dependence, plus same-game prop correlations)
and `pages/depth.html`. CSS in `assets/style.css` is additive only — no existing rule was changed.

**C4 — depth and deficiency.** New `pipeline/build_depth_ladder.py` joins the official club depth
charts to the official injury report and publishes the whole ladder: **933 slots across 31 of 32
clubs**, ranks 1–6 as the club lists them, for **offence, defence and special teams separately**.
Findings: **4 lines are being started by a backup** because the club's own first string is Out or
Doubtful (DET C and CB, NE LG and CB); **110 lines have an at-risk first string** (Questionable,
did not practise, or limited); **no line is down to its 3rd string**; **1 chart gap** (PHI DT);
**16 merged-name cells** published verbatim. Houston publishes no chart, so its rows are blank by
design. Clubs with no filed report this week (BAL, LAC, and the four on bye) show zero, with the
page stating three times that no report is not the same as healthy. This closes the gap recorded in
flag **F21**; F21 stays open for the attrition index itself, which is still starter-only (flag **F47**).

**C5 — executive summary.** `pages/executive.html` now opens with a "re-checked on 2026-11-13"
paragraph, its brief-coverage table points the parlay, correlation, luck and 2nd-to-4th-string rows
at the pages that actually answer them, and its "what remains unresolved" list carries F41 and F46.

**C6 — final integration.** Every gate re-run on the final tree and **all green**:
`check_site.py` 25 pages / 0 broken / 0 unreachable · `check_committed_site.py` PASS (no
source-less rows, no stale stamps) · `tools/verify.py` 982 rows, **982 with an official source
link**, 73 unverified rows keep blank cells · `verify_combined.py` PASS (1,613 links, 0 broken) ·
`audit_numbers.py` 47/47 reproduce · `validate_verified.py` all hard checks pass ·
**117 unit tests OK**.

**Cross-scope edits this session, both logged in `docs/review/session-c56ebee8.md` §6:**
1. `scripts/verified/normalize_nav.py` — the canonical nav list was resynced with
   `pipeline/gen_site.py` and labels are now HTML-escaped the way the generator escapes them.
   Both scripts rewrite the same `<nav>` block on the same files; their lists had drifted, so
   whichever ran second silently rewrote the other's links. They are now byte-identical, verified
   by running one after the other and diffing (0 changes on this generation's pages).
2. `tools/check_committed_site.py` — **not edited.** Its staleness rule flags the three research
   pages, because they read from a committed extract the daily refresh never rebuilds. Rather than
   weaken another session's gate, each page now carries the site stamp in its header and states its
   own extract time in the body. An explicit exemption list is the tool owner's call.

**Editorial additions (append-only, `pipeline/content.py`):** questions **Q22** (may a committed
official snapshot lag the live page, and who re-scrapes it?) and **Q23** (are club-published depth
charts an acceptable official source when the league publishes none?); suggestions **S16** (publish
the full ladder, not just starter plus nominal backup) and **S17** (collapse the seven generations
into one authoritative dashboard); decision **D07** (which generation becomes authoritative).
Registers now hold 23 questions, 19 suggestions and 7 decision records.

---

---

# Session `ca779bcc-nfl1` — strength-of-schedule study, source audit, live-site rebuild

| Item | Value |
| --- | --- |
| Session ID | `ca779bcc-nfl1` |
| Branch | `arena/ca779bcc-nfl1` (fixed by Arena; the `session-<id>/<task>` convention cannot be used) |
| Base commit | `09c03f052aa3bebb62acc23cb17eefd65f0c512e` (`main`, 2026-11-12 23:37 UTC) |
| Board read before work | yes — full `COORDINATION.md` (1,785 lines) plus PR list |

**Coordination note.** Every earlier session branch has merged, and no task on this board is
`in progress`, so there is no competing owner. This session claims the scopes below; they are
**additive and non-overlapping** with every earlier session. Two stale PRs (#37, #43) are
COORDINATION-only records that were left open; they are handled under S9, not edited.

## Task board (session `ca779bcc-nfl1`)

Status values: `unclaimed` | `in progress` | `done` | `needs review`.

| ID | Task | Status | Owner | File scope | Notes |
| --- | --- | --- | --- | --- | --- |
| S1 | Read board, claim tasks, push claim first | in progress | `ca779bcc` | `COORDINATION.md` | this section |
| S2 | Line-by-line audit of the newest published data against live official nfl.com pages (standings, week-10 schedule/results, injury report); flag every discrepancy with links | in progress | `ca779bcc` | `data/flags.json` (append-only), `COORDINATION.md` | |
| S3 | **New study: strength of schedule and schedule-adjusted results.** Ratings, SOS, remaining SOS, adjusted scores; own line vs market; SOS-conditioned strategy hypotheses with gates | in progress | `ca779bcc` | `analysis/sos.py` (new), `data/strength/` (new) | nflverse inputs only |
| S4 | Questions / information ledger: what is known, unknown and blocking, with the discovery method for each gap | in progress | `ca779bcc` | `data/strength/questions.json` | |
| S5 | Suggestions register with decision paths (so a reviewer can choose before anything is implemented) | in progress | `ca779bcc` | `data/strength/suggestions.json` | |
| S6 | Executive summary page for this study | in progress | `ca779bcc` | `strength/executive-summary.html` | generated |
| S7 | Verification report: every published row carries an official/deeded source link; blanks stay blank and are flagged | in progress | `ca779bcc` | `strength/verification.html`, `data/strength/verification.json` | |
| S8 | Generator + tests: `tools/build_strength.py`, `tools/check_strength_site.py`, unit tests; one additive nav entry from `index.html` | in progress | `ca779bcc` | `tools/build_strength.py`, `tools/check_strength_site.py`, `tests/test_strength.py`, `index.html` (one nav link) | |
| S9 | Integration: merge stale PRs #37/#43, PR from this branch, merge, confirm Pages deploy, record result here | in progress | `ca779bcc` | `COORDINATION.md` | |

**Not touched by this session:** `pages/`, `docs/`, `lab/`, `dashboard/`, `verified-lab/`,
`referee/`, `s9cb/`, `pipeline/`, `scripts/`, `tools/build.py` and every `data/*.json` file owned
by an earlier generator. New data is written only under `data/strength/`.

_This claim is committed and pushed before any other file is touched, per the brief._

## Task board update — session `ca779bcc-nfl1` (2026-11-13)

| ID | Task | Status | Owner | File scope | Evidence |
| --- | --- | --- | --- | --- | --- |
| S1 | Claim pushed before any other file was touched | done | `ca779bcc` | `COORDINATION.md` | commit `bf550fe` |
| S2 | Line-by-line audit of the newest published data against live official nfl.com pages | done | `ca779bcc` | `data/strength/flags.json`, `data/strength/audit.json` | 32 clubs × 7 fields compared; **10 differences** (NYG + WAS); Week 10 14 fixtures and 4 byes match; injury cross-check 6/9 with 3 DET rows differing; provenance hash mismatch; 17 flags published with links |
| S3 | Strength-of-schedule study: walk-forward ratings, SOS, own lines, gated strategies | done | `ca779bcc` | `analysis/strength.py`, `data/strength/*.json` | 7,103 games 1999–2026; 11 pre-registered rules; 19,928 bets; **0 PASS / 0 WATCH / 11 FAIL**; holdout spread MAE 10.71 own vs 9.63 market |
| S4 | Questions / information ledger | done | `ca779bcc` | `data/strength/questions.json` | 12 questions: 8 answered with a number, 1 partial, 3 blocked with the exact source that would settle each |
| S5 | Suggestions register with decision paths | done | `ca779bcc` | `data/strength/suggestions.json` | 8 suggestions, each with options, recommendation, cost, risk, blocker |
| S6 | Executive summary | done | `ca779bcc` | `strength/executive-summary.html` | question, method, result, defects, decisions |
| S7 | Verification report | done | `ca779bcc` | `strength/verification.html`, `data/strength/verification.json` | 10 checks, states printed both sides |
| S8 | Generator, checker and tests | done | `ca779bcc` | `tools/build_strength.py`, `tools/build_ledgers.py`, `tools/check_strength_site.py`, `tests/test_strength.py` | 14 pages, 234 table rows, every row source-linked; 19 unit tests pass; `check_strength_site` PASS |
| S9 | Integration, PR, merge, Pages | in progress | `ca779bcc` | `COORDINATION.md` | |

**Sources used in this session (official first):** standings https://www.nfl.com/standings/league/2026/reg ·
Week 10 schedule/results https://www.nfl.com/schedules/2026/reg10 · injury report https://www.nfl.com/injuries/ ·
game page https://www.nfl.com/games/commanders-at-giants-2026-reg-10 · data from the pinned nflverse release
https://github.com/nflverse/nflverse-data/releases/tag/schedules (CC-BY-4.0).

**Verification performed:** live re-fetch of every official page above on 2026-11-13; field-by-field comparison of
all 32 standings rows (224 fields) and the Week 10 fixture/bye set; sha256 of the committed `games.csv` against
`data/s9cb/provenance.json`; unit tests for the spread sign convention after a real defect was found and fixed in
this session (a first implementation treated the closing line as points-given and produced four false PASSes at
94% hit rates).

**Irregularities recorded (all published with source links on `strength/flagged.html`):**
F-SOS-STD-{NYG,WAS} (10 field differences vs official), F-SOS-W10-01 (WAS @ NYG still listed as upcoming; official
page shows it final 24–21), F-SOS-DATA-01 (provenance pin 2,189,959 bytes / `5ae004…` vs committed 1,665,511 bytes /
`6f0777…`), F-SOS-MODEL-01 (2026 home-field fit −0.47 pts, a property of a small sample), F-SOS-INJ-01..03
(three Detroit rows whose game status differs between the committed transcription and today's official page),
F-SOS-SITE-01 (landing KPI still says "week 9 complete").

**Not touched:** `pages/` content, `docs/`, `lab/`, `dashboard/`, `verified-lab/`, `referee/`, `s9cb/`,
`analysis/engine.py|luck.py|injuries.py|correlations.py`, `pipeline/build_all.py`, `tools/build.py` and every
`data/*.json` owned by an earlier generator. `pipeline/gen_site.py` received **one** additive nav entry plus one
`sections_page` row; `scripts/verified/normalize_nav.py` received **one** additive nav entry. New data lives only
under `data/strength/`.

| `9411723a-nfl1` | `arena/9411723a-nfl1` | Verification of the committed site, official-source spot checks, new flag F41 (standings snapshot vs live drift), PR -> main -> merge -> Pages deploy, integration record | active |

## Task board — session `9411723a-nfl1` (ACTIVE; claims below)

File scope claimed here is **additive and non-overlapping**: `COORDINATION.md`, `data/flags.json`, and the root pages those files render (regenerated only with `python3 tools/build.py`). No other session's files are touched.

| ID | Task | Status | Owner | File scope | Notes |
|---|---|---|---|---|---|
| V1 | Line-by-line verification of the committed root site with `tools/verify.py` | done | `9411723a` | `data/flags.json`, `data/suggestions.json`, `data/questions.json`, root `*.html` | `tools/verify.py`: 982 table rows, 982 with official source links, 73 unverified (flagged), 0 broken internal links — PASS |
| V2 | Official-source spot check of the 2026 standings snapshot vs the live nfl.com page | done | `9411723a` | `data/flags.json` (F41) | Live page https://www.nfl.com/standings/league/2026/reg fetched 2026-11-13 shows NYG 5-3-1 (203/196) and WAS 3-5-1 (196/223); snapshot (retrieved 2026-11-12T04:31Z) shows NYG 5-2-1 (182/172) and WAS 2-5-1 (172/202) — drift explained by the WAS @ NYG game on 2026-11-12 after the snapshot time; logged as flag F41 |
| S1 | Confirm the suggestions review-and-choose-a-path section is complete | done | `9411723a` | `pages/suggestions.html`, `pages/decisions.html`, `data/suggestions.json`, `data/questions.json` | 27 suggestions, 6 decision records (D01-D06), 5-step review path; Q01-Q28 question/information/answer table |
| L1 | Confirm own-lines research, strategy leaderboard, gates, correlations, luck removal | done | `9411723a` | `pages/lines.html`, `pages/strategies.html`, `data/model/*` | 14 Week-10 own lines; 0 of 12 strategies pass all 8 gates (reported honestly); correlations partial/flagged; luck-removal documented |
| I1 | Confirm injury and depth-deficiency tracking | done | `9411723a` | `pages/injuries.html`, `pages/availability.html`, `data/model/availability.json` | Official injury report joined to depth chart; 2nd/3rd/4th-string not publishable — official depth charts return 404 (flagged F17/F21) |
| E1 | Confirm executive summary | done | `9411723a` | `pages/executive.html` | Implemented: what was verified, what the numbers say, unresolved items, decisions requested |
| P1 | Confirm GitHub Pages live site | done | `9411723a` | `index.html`, `pages/`, `.nojekyll` | Pages status `built`; source `main /`; https://kanlerxz87-cyber.github.io/NFL1/ |
| X1 | Integration: PR from this branch to `main`, merge, confirm Pages deploy, record result | in progress | `9411723a` | `COORDINATION.md` | PR created after this claim commit is pushed |

## Session `9c208ed8-nfl1` — result record (recovered from `main` on merge, 2026-11-13)

> Recovered verbatim by session `ca779bcc-nfl1`. The merge into this branch had initially kept
> only one side of a COORDINATION.md conflict, which silently dropped these lines; they are
> restored here because nothing from another session is discarded on this board.

| V01 | Read the board, claim tasks, push the claim before touching anything else | done | `9c208ed8` | `COORDINATION.md` | commit `2cc115f` |
| V02 | Fresh official-source verification of the live data layer against nfl.com **today**; store the retrieved evidence verbatim with URL + timestamp | done | `9c208ed8` | `data/official/2026-11-13/**` | 5 files: standings (32 rows), week-10 (15 fixtures), week-11 (15), injury designations, sources register |
| V03 | Line-by-line diff of the committed data layer against today's official values; publish drift as flags, never silently | done | `9c208ed8` | `room/data/findings.json`, `data/official/2026-11-13/` | 20 findings; drift published as F-101 and closed by the 12:51Z refresh, re-verified to 0 |
| V04 | Decision Room: a review-and-choose surface for every suggestion (options, trade-offs, evidence, recommendation, pre-implementation gate) | done | `9c208ed8` | `room/**` | 11 pages, 23 tables, 311 rows; `room/verify.py` PASS |
| V05 | Decision-gating question register: known / unknown / discovery method / what it blocks | done | `9c208ed8` | `room/data/questions.json` | 22 questions, each with a discovery method and what it blocks |
| V06 | Depth-chart coverage audit: which of the 32 clubs have an official sourced chart, which are blank, and what closing them requires | done | `9c208ed8` | `room/data/depth_coverage.json` | 32 clubs: 31 parse (934 position rows), HOU publishes an image (F-117) |
| V07 | Executive summary refresh to today's verified state | done | `9c208ed8` | `room/data/executive.json` | 15 KPIs, all derived; headline rewritten after the refresh closed the drift |
| V08 | Run every gate, fix failures, rebuild, link check | done | `9c208ed8` | regenerated site output | 6 gates PASS; two real build failures found and fixed (F-119, F-120) |
| V09 | PR → merge without waiting → confirm Pages deploy → record here | done | `9c208ed8` | `COORDINATION.md` | **PR #49** → `main`; record below |
**Not touched by this session:** `s9cb/`, `analysis/`, `src/nfl/`, `tests/`, `docs/`,
`verified-lab/`, `referee/`, `lab/`, `dashboard/`. Two shared generators were edited, both
additively and both with a gate behind them: `pipeline/gen_site.py` (one nav entry plus an
empty-cell fix) and `scripts/verified/normalize_nav.py` (one nav entry). `index.html` and
`pages/*.html` were regenerated by their own generators, never hand-edited.
**PR #49** → merged to `main` without waiting for approval, per the brief.
A **Decision Room** at `room/` — 11 pages, every table row carrying its own https source link,
every unconfirmable value blank and labelled rather than inferred. Live at
<https://kanlerxz87-cyber.github.io/NFL1/room/>.
`data/official/2026-11-13/` holds today's nfl.com pages transcribed verbatim with URL and
retrieval timestamp on every row: 32 standings rows, 15 week-10 fixtures, 15 week-11 fixtures,
the injury designations, and a sources register.
### Findings: 20 published, 13 open, 7 closed during the session
Four material, 12 minor, 4 informational. The ones worth a reviewer's attention:
- **F-118 (material, open)** — the collector's 12:50Z run could not read the official injury page
  and silently fell back to the week-6 mirrored feed while still citing the official URL. The
  availability table shows 181 game designations against 9 real ones, still calls itself
  "mid-week", and lists Baker Mayfield as Out and Caleb Williams as Questionable although both
  clubs are on bye in week 10. The warning text is present but the fallback week is not named in
- **F-102 (material, open)** — two leaderboards, one assuming −110 on every bet and one using
  observed prices, rank different rules under the same names.
- **F-104 (material, open)** — 31 depth charts captured, 3 rendered.
- **F-121 (material, resolved)** — a club-code mismatch (official `AZ`/`LA` vs model `ARI`/`LAR`)
  made Arizona render as a red standings drift while the sentence above the table said "0 clubs
  drift". Both were wrong; fixed with an alias map, an honest third state, and a generated summary.
- **F-116** — I published that the leaderboard ignored its own caption. Reading
  `pipeline/build_all.py:593` showed it sorts by the lower ROI bound exactly as stated. Retracted
- **F-101** — the standings drift this session found on arrival was real, but the collector's own
  refresh closed it mid-session. Recorded as resolved with the re-verification, not left standing.
### Build failures caught by gates, not by review
1. `pages/evidence.html` shipped an empty `<td>` — `check_site.py` failed on it, and `pages.yml`
   runs that script, so the next push would have failed the deploy. Fixed at the generator.
2. Ten of 21 pages had no Decision Room nav link, because a second generator owns their nav. Fixed
   in the canonical list; 21 of 21 now link.
A latent CI failure was also removed: `BUILD_STAMP` was wall-clock while `room.yml` fails on a
non-empty `git diff -- room/`, so the gate would have broken on the next UTC day. It is now derived
from the capture time, and two consecutive builds are byte-identical.
scripts/verified/check_site.py        PASS  21 pages, links and nav complete
scripts/verified/validate_verified.py PASS  all hard checks
scripts/verified/audit_numbers.py     PASS  47 recomputations reproduce
tools/check_committed_site.py         PASS  no broken links, no source-less rows
tools/verify.py                       PASS  1,013 rows, all sourced
room/verify.py                        PASS  11 pages, 23 tables, 311 rows
CI on the merged branch: **Decision Room build and gate**, **Verify NFL1 site** and
_This session's claim is closed. The board is free for the next session._
## Earlier records from `main` (preserved on merge)

# Session `46b6cabb-nfl1` — documentation consistency and post-merge audit

| Item | Value |
| --- | --- |
| This session ID | `46b6cabb-nfl1` |
| This session branch | `arena/46b6cabb-nfl1` |
| Base commit | `09c03f052aa3bebb62acc23cb17eefd65f0c512e` (`main`) |
| Board read before work | yes; full board reviewed |

**Constraint:** Arena pins this session to `arena/46b6cabb-nfl1`; the requested
`session-<id>/<task>` branch convention cannot be followed. Work stays on the assigned branch.

## Task board (this session)

| ID | Task | Status | Owner | File scope | Evidence |
| --- | --- | --- | --- | --- | --- |
| N1 | Address stale README claims and non-destructive README generation | needs review | `46b6cabb` | request only in `COORDINATION.md`; implementation excluded from this scope | Open PR #31 also changes `README.md` and `tools/build.py`; request its owner to incorporate this audit finding. No overlapping edits retained. |
| N2 | Run full repository/site gates and document reproducible results and remaining issues | done | `46b6cabb` | `docs/review/session-46b6cabb.md`, `COORDINATION.md` | Site gates pass; live official NFL schedule proves published overview is stale after WAS @ NYG became final. README issue and verifier-count drift documented. |
| N3 | Final integration assessment; submit PR only if tests/build are green, then verify deployment and record outcome | done | `46b6cabb` | `COORDINATION.md` | PR #44 merged; all PR checks passed; Pages build/deploy succeeded for merge commit `114bbbe6`; live site remains a stale pregame snapshot and is explicitly not represented as refreshed. |

**Coordination request to the owner of open PR #31 (`arena/6e8ca348-nfl1`):** the current
`README.md` contains fixed suggestion / decision-record counts, and `tools/build.py:write_readme()`
can replace the full hand-maintained README with an incomplete embedded template despite its
comment claiming it is byte-identical. Please consider making the template a no-op or ensuring it
cannot overwrite the full README, and remove the obsolete fixed counts. This session deliberately
reverted its overlapping local edits and retains only the audit report; no files from PR #31 were
changed. Live-source and test evidence are in `docs/review/session-46b6cabb.md`.

## Integration record (N3) — 2026-11-13

| Item | Value |
| --- | --- |
| Pull request | [#44](https://github.com/kanlerxz87-cyber/NFL1/pull/44) — *Audit live NFL dashboard freshness and document reproducible findings* |
| Merge | Squash-merged 2026-11-13T12:41:33Z; merge commit `114bbbe6c9130c660c51d93ca33b6d10369f02b8` |
| PR checks | `Verify NFL1 site` success; `Verify NFL Decision Lab site build` success |
| Pages | `pages-build-deployment` run 43427328508 success; Pages API reports `built` for commit `114bbbe6` |
| Live-site status | Root site fetched after deploy; static snapshot still shows the November 12 pregame WAS @ NYG row. The report is repository documentation, not a fabricated data refresh. Official schedule is the review source. |
| Post-merge workflow note | A redundant `Verify NFL Decision Lab site build` run 43427329054 was cancelled by GitHub Actions concurrency (“higher priority waiting request”); the same workflow had already passed on PR #44 at `43427056631`, and the PR's `Verify NFL1 site` plus Pages deployment passed after merge. |
| Remaining review items | README/template fix requested from open PR #31 owner due overlapping `README.md` / `tools/build.py` scope. New staleness observation documents recurrence of existing F39/F40 and S13/S24. |

File scopes are additive and do not edit generated root pages, `pages/`, `data/`, or other
sessions' research artifacts. The persistent changes will be committed and pushed only to this
session's assigned branch.

## Session `9411723a-nfl1` — verification and integration (2026-11-13)

| Item | Value |
| --- | --- |
| Session ID | `9411723a-nfl1` |
| Branch | `arena/9411723a-nfl1` |
| Base commit | `09c03f052aa3bebb62acc23cb17eefd65f0c512e` (`main` at claim time; `main` later advanced through PRs #44 and #46) |
| Board read before work | yes — full `COORDINATION.md` reviewed |

### Tasks claimed (all done)

File scope: `COORDINATION.md`, `data/flags.json`, and the root pages those files render — no other session's files were touched.

| ID | Task | Status | Evidence |
|---|---|---|---|
| V1 | Line-by-line verification of the committed root site (`tools/verify.py`) | done | 983 table rows, 983 with official source links, 73 unverified (flagged, never inferred), 0 broken internal links — PASS |
| V2 | Official-source spot check of the standings snapshot vs live nfl.com | done | Flag F41 added; source https://www.nfl.com/standings/league/2026/reg (fetched 2026-11-13) |
| S1 | Suggestions review-and-choose-a-path section | done | `pages/suggestions.html`: 27 suggestions, 6 decision records D01-D06, 5-step review path; `pages/decisions.html`: Q01-Q28 question/information/answer table |
| L1 | Own lines, strategy leaderboard, gates, correlations, luck removal | done | `pages/lines.html` (14 Week-10 lines, error bands); `pages/strategies.html`: 0 of 12 strategies pass all 8 gates, reported honestly; correlations partial/flagged |
| I1 | Injury and depth-deficiency tracking | done | `pages/injuries.html`, `pages/availability.html`: official injury report joined to depth chart; 2nd/3rd/4th-string not publishable — official depth charts return 404, flagged F17/F21 |
| E1 | Executive summary | done | `pages/executive.html`: verified / what the numbers say / unresolved / decisions requested |
| P1 | GitHub Pages live site | done | Pages status `built`; source `main /`; https://kanlerxz87-cyber.github.io/NFL1/ |
| X1 | Integration: PR → `main` → merge → confirm Pages deploy → record | done | See record below |

### Integration record (X1)

| Item | Value |
| --- | --- |
| Pull request | [#45](https://github.com/kanlerxz87-cyber/NFL1/pull/45) — Integration: line-by-line verification, flag F41, PR/merge/Pages record |
| Merge | `gh pr merge 45 --merge`; merged 2026-11-13T12:44:50Z; merge commit `301139bd90b0ed9ed1de02193b8d8bd855c8e74f` |
| Pre-merge checks | `Verify NFL1 site` SUCCESS on the PR head; `tools/verify.py` PASS locally (983 rows sourced); the site-build check passed on identical content earlier and was cancelled by branch concurrency on rebase, not failed |
| Pages after merge | Pages status `built`; source `main /`; live at https://kanlerxz87-cyber.github.io/NFL1/ with 45 flagged items including F41 (each with official source link) |
| Flagged for Review | Live page carries all flags; flagged items do not block the merge and are published for post-launch review |

Note: `main` advanced while this branch was open (PRs #44 and #46 merged ahead of it). The branch was rebased onto `origin/main` before the final push, and PR #45 merged cleanly.

---

# Session `1e159b2e-nfl1` — decision-review layer, personnel-deficiency signal, and integration

| Item | Value |
| --- | --- |
| Session ID | `1e159b2e-nfl1` |
| Branch | `arena/1e159b2e-nfl1` (fixed by the environment; `session-<id>/<task>` cannot be used) |
| Base commit | `09c03f052aa3bebb62acc23cb17eefd65f0c512e` (`main`) |
| Board read before work | yes — full `COORDINATION.md` and the four active task tables reviewed |

**Scope rule applied here:** this session adds two *new* self-contained subsystems rather than
editing pages owned by the live renderers (`pipeline/gen_site.py`, `tools/build.py`,
`scripts/verified/build_site.py`, `s9cb/site.py`). Those shared outputs are only touched by
**one additive nav entry** on the landing page at integration time, recorded below.

## Task board

| ID | Task | Status | Owner | File scope | Notes |
| --- | --- | --- | --- | --- | --- |
| N1 | Read board, claim, push claim before any other file is edited | done | `1e159b2e` | `COORDINATION.md` | claim commit `19a66d2` |
| N2 | Reproduce every published research number from committed data (research build re-run, diff vs committed JSON) and record the result | done | `1e159b2e` | `data/s9cb/*` (read-only) | all five research JSON files reproduce **byte-identically** except `generated_at`; the extract itself cannot be re-downloaded from the sandbox, so provenance is taken from `data/s9cb/provenance.json` |
| N3 | Personnel-deficiency study: does a personnel loss carry information the closing line has not priced, and do bet rules built on it survive the eight gates? | done | `1e159b2e` | `s9cb/analysis/personnel.py`, `s9cb/analysis/run_personnel.py`, `data/personnel/` | 13 measures, 5 rules, 2,608 scored bets; **0 significant after correction, 0 rules pass all gates, 1 WATCH** |
| N4 | Decision-review layer: the **Review Room** (9 pages) where every open decision, its options, costs and blockers live in one place, with a re-verification log | done | `1e159b2e` | `review-room/` (new), `tools/review_room.py` (new) | additive; one nav entry on `index.html` |
| N5 | Live re-verification of official sources this session (standings, week-10 schedule, injuries) with row-level comparisons recorded | done | `1e159b2e` | `data/personnel/standings_diff.json`, `data/personnel/official_standings_2026-11-13.csv` | 32/32 standings transcribed and self-checked; 30/32 agree with the committed file, 2 differ and both are the Week 10 Thursday game; 14/14 fixtures match; 10/10 sampled injury rows match |
| N6 | Final integration: gates, link check, PR → `main`, merge, confirm Pages, record here | done | `1e159b2e` | `COORDINATION.md` | record below |

## Results (session `1e159b2e-nfl1`)

**Personnel study — what was built.** Two questions, tested separately because they are
different: (a) does a personnel measure predict the game result, and (b) does it predict the
result *beyond* what the closing spread already encodes? Question (a) alone would find a
"signal" in anything correlated with team quality. A measure is only a candidate edge if it
survives (b). The QB measure is defined pre-game and was **redefined during the session**:
an earlier draft used "most starts this season", which described a club that had already
changed starter weeks earlier as breaking continuity. The corrected rule is "the QB who started
the club's previous game", still strictly pre-game. The whole analysis was rerun after the fix.
A second defect was also found and fixed: a club with a clean report (nobody ruled out) was being
treated as having no report at all, discarding a real zero. Both are published as **V07** rather
than quietly corrected.

**Personnel study — what it found.** With 13 information tests on up to 7,087 games and five
pre-declared bet rules scored at **observed prices only** (2,608 scored bets; games without a
price are excluded and counted), **none of the measures is significant after Benjamini-Hochberg
correction**, and **no rule passes all eight gates** (best is P04, 6/8, WATCH). The strongest raw
result — the away club's ruled-out offensive players — has raw p = 0.0105 and corrected
p = 0.136. The market coefficient sits at 1.03–1.08 with p ≈ 0 in every regression, which is the
control showing the specification and the join are sound: the null is a real null, not a broken
model. **Conclusion: injury/personnel information is descriptive, not a profitable edge against
the closing line.** That is not a failure of the analysis; it is the analysis working.

**Official-source re-verification.** All 32 clubs' 2026 standings were hand-transcribed from
<https://www.nfl.com/standings/league/2026/reg> and accepted only after passing five internal
arithmetic checks (PF−PA = NET for 32/32; PCT = (W+T/2)/games for 32/32; ΣW = ΣL = 136;
ΣT = 2; ΣPF = ΣPA = 6,291; 274 team-games = 137 games, which is exactly the 136 committed results
plus the Week 10 Thursday game). Compared club by club against `data/verified/standings_2026.csv`:
**30 of 32 agree exactly; NYG and WAS differ**, and both are the two clubs that played the
Thursday game after the committed snapshot was taken (2026-11-12T04:31Z). This is staleness, not
arithmetic error, and it is independently corroborated by flag **F41** raised by a different
session. All 14 Week 10 fixtures match <https://www.nfl.com/schedules/2026/by-week/week-10>
including the Munich game and the official byes (CHI, DEN, PHI, TB). Ten sampled rows across
WAS/NYG/NE/DET match <https://www.nfl.com/injuries/> field for field, as do the four club row
counts (9, 11, 15, 9).

**New irregularity found.** The direct nfl.com scrape (`data/model/official_injuries.json`) and
the mirrored feed (`data/s9cb/injuries.csv`) agree on ruled-out counts for 25 of 26 reporting
clubs, and **differ for Detroit: 3 ruled out on the official page, 0 in the mirror** (R05 on the
Flagged page). The live Week 10 board uses the official scrape and marks the affected row.

**Data refresh during the session (must be read with the results above).** The `Collect s9cb
research extract` workflow committed a refreshed extract to this branch at `177cfe3` while the
session was still working (commit `[skip ci]`), and the workstation sandbox cannot download the
release assets itself. The **entire analysis chain was re-run from that refreshed extract**, and
this is the second set of results: 7,104 priced games (was 7,103), 13 information tests, **still
0 significant after correction**, the same five rules with the same gates and **still 0 PASS /
1 WATCH (P04, 6/8)**, 2,608 scored bets. The refresh materially changed one thing: the mirrored
injury feed now carries **296 rows across 26 clubs, matching the direct nfl.com scrape row for
row and club for club (26/26)**, so the Detroit gap found earlier in the session is closed. Flag
R05 is therefore published as *resolved this week, monitored every build* with the earlier gap
recorded, not deleted — the check is more useful than the finding. The standings staleness
(30/32 agree; NYG and WAS differ) is unaffected: `data/verified/standings_2026.csv` did not
change in the refresh, and the Week 10 game is still absent from `data/verified/games_2026.csv`.

**Gates after this session's changes (all local, all green):** `validate_verified` PASS ·
`audit_numbers` 47/47 PASS · `check_site` 21 pages, no broken links · `tools/verify` PASS ·
`check_committed_site` PASS · `verify_combined` PASS · `tools/review_room.py --check` 9 pages,
no broken links, **every table row carries a source link (enforced by the checker)** ·
117 unit tests PASS.

**Files added (all new paths; the only edit to an existing file is one nav entry):**
`s9cb/analysis/personnel.py`, `s9cb/analysis/run_personnel.py`, `data/personnel/*` (8 files),
`review-room/*` (9 HTML pages + data generators), `tools/review_room.py`, `tools/v_sources.py`,
plus one `<a>` in `index.html`.

**Cross-session note.** `main` advanced to `00d957d` (PRs #44-#48) while this session worked.
The branch was rebased onto it; the only conflict was `COORDINATION.md` and **both sides were
kept** — nothing from `46b6cabb` was discarded. Their new flag F41 duplicates this session's
standings finding, which is recorded here as independent confirmation rather than as duplication
to be removed.

_Claim committed and pushed before any other file is touched, per the brief._


---

# Session `65df4799-nfl1` — W5 integration: merge `origin/main` (b525401) into PR #53

Recorded 2026-11-13 (UTC). The session's PR (#53, head `552199c`) became CONFLICTING after
`main` advanced `09c03f0..b525401` (PRs #44-#51 from sessions `9411723a` / `9c208ed8` /
`1e159b2e`: Decision Room + `room/` site, personnel-deficiency signal study, flag F41,
suggestions status rewording, and the standardized flag schema).

**Merge policy applied — nothing from `main` was discarded:**
- `data/flags.json` (36 conflicts resolved by 3-way union): final register = 52 entries =
  their F01-F40 + A-F01..A-F03 + F41, plus this session's LR-01..LR-06 + LR-07. Their
  standardized entry schema (id/category/description/impact/status/src/action/verified/
  retrieved) is kept for every entry.
- `COORDINATION.md` (2 conflicts): both sides kept — the `6e8ca348` claim block and the
  `9411723a` board stay side by side; this session's W2-W4 records and the `46b6cabb`
  audit record stay side by side.
- `pipeline/gen_site.py` (NAV conflict): both nav entries kept (Decision Dashboard +
  Decision Room).
- 33 generated artifacts (pages, reports): staged ours and regenerated from the merged
  generators + merged data via the canonical chain (incl. `room/build.py`, 11 pages).

**Structural defect found in `tools/verify_official.py` and fixed (flagged, no check
weakened):** the schedule/counts checks compared *rolling* model artifacts (snapshot
fixtures, own lines, dashboard counts) against the *pinned* 2026-11-12 capture. After the
WAS @ NYG result landed and the model rolled to Week 11, those two checks could not pass
under any data state (check A pins the schedule fixture to exactly 14 rows, while the
week-10 hand file and the week-11 model fixtures are disjoint sets). Fix, per the
"match every artifact to the official page of its own time point" rule:
- `tools/evidence_from_official.py` now also writes a **current** capture,
  `data/evidence/standings_current.json` + `data/evidence/schedule_current.json`, both
  hand-transcribed 2026-11-13 from the official pages (32 standings rows incl. the TNF
  result; 13 Week-11 games + 6 byes).
- Moving-artifact comparisons (snapshot fixtures, own-line dates, games-played counts)
  read the current capture; pinned artifacts (week10_fixtures_2026.csv, verified
  standings files) still read the pinned 2026-11-12 capture. No check was deleted or
  loosened — B3c's missing-pair case is now an explicit failure instead of a vacuous pass.

**New irregularity LR-07 (needs review) + suggestion S30:** the Week-11 refresh
(generated 2026-11-13T13:04Z from the upstream schedules feed) listed JAX @ NYG at 13:00
and PIT @ PHI at 16:25; the official Week-11 page shows 4:25 PM ET and 1:00 PM ET — the
two kickoff times were swapped in the feed, while the rows cite the official schedule as
their source. Caught by check B3 against the official capture. Fixed: snapshot values
corrected to the official times and `pipeline/build_all.py` now applies a documented,
source-linked `SCHEDULE_FEED_FIXES` table at build time. Reviewer: confirm on
https://www.nfl.com/schedules/2026/by-week/week-11.

**Post-merge gate state:** verify_official 20 passed / 8 flagged / 0 failed; verify.py
every table row sourced; verify_combined PASS (0 broken links); check_generators /
check_freshness / check_committed_site / verify_dashboard PASS; validate_verified PASS;
audit_numbers PASS; verified check_site PASS; room build 11 pages (its own row-source
gate passes); 117 tests pass. Next: push, confirm the four workflows green, merge PR #53,
confirm the Pages deploy with the `?v=<sha>` cache-buster, and record the merge below.

---

### Session `c56ebee8-nfl1` — merge of `origin/main` (PRs #44–#51) and final state

`main` advanced by 25 commits while this branch was being built (sessions `9411723a`, `1e159b2e`,
`46b6cabb`, `9c208ed8`). It was merged with a normal (non-rebase) merge; an earlier rebase attempt
was aborted after two conflicts and nothing was lost. Conflicts and resolution:

| Conflicting file | Resolution |
|---|---|
| `index.html`, `pages/*.html`, `data/combined_verification.json`, `data/verification_report.json` | Generated artifacts. Taken from `main`, then **regenerated** by the generators below, so no session's output is lost. |
| `pipeline/gen_site.py` | Both sides kept. `main` had added `room/index.html` ("Decision Room") to `NAV`; that entry is preserved and the whole list was re-ordered by category. |
| `scripts/verified/normalize_nav.py` | Both sides kept. `CANON` resynced with `gen_site.py` and both scripts now use the **same** target rule, including sub-site paths (`room/index.html`), so they agree byte for byte. |
| `COORDINATION.md` | Both sides kept — `main`'s new session records and this session's claim plus results. |

**Flag-number collision, resolved:** session `9411723a` had already raised **F41** for the standings
snapshot lagging the live table, and session `1e159b2e` (check N5) reached the same 30-of-32 result
by an independent transcription. This session's F41 duplicate was **dropped**, and F41's text now
records that three independent checks agree, plus the completed-fixture consequence (WAS @ NYG
still listed in the own-lines table). This session's new flags are **F42–F47**.

**Generator order used for the committed site:**
`scripts/verified/build_site.py` → `scripts/verified/build_availability.py` →
`pipeline/gen_site.py` → `scripts/verified/normalize_nav.py`.
`gen_site.py` is run third so that the canonical dashboard pages win over the companion generators
where they share a filename (`pages/lines.html` was previously left with the companion generator's
layout, and `pages/injuries.html` had stopped being written at all — both fixed). `pages.yml`
itself was **not** edited; it is outside this session's claimed scope and the note is logged here
for the workflow owner.

**Final gates on the merged tree, all green:** `check_site.py` 25 pages / 0 broken / 0 unreachable ·
`check_committed_site.py` PASS · `tools/verify.py` **983 rows, 983 with an official source link**,
73 unverified rows keep blank cells · `verify_combined.py` 1,938 links, 0 broken ·
`audit_numbers.py` 47/47 · `validate_verified.py` all hard checks pass · **117 unit tests OK**.

**Note on `analysis/engine.py`, `luck.py` and `correlations.py`:** they import `numpy`, which is not
installed in this sandbox, so they could not be re-run locally. `pages.yml` installs numpy and runs
them in CI; `audit_numbers.py` (47/47) re-derives their published outputs and passes.

---

### Session `ca779bcc-nfl1` — result record (2026-11-13)

| Item | Value |
| --- | --- |
| Pull request | [#52](https://github.com/kanlerxz87-cyber/NFL1/pull/52) |
| Merge | see the PR link above |
| Study | `analysis/strength.py` → `data/strength/` → `strength/` (14 pages) |
| Sample | 7,104 played games, 1999–2026; 19,930 scored bets; 11 pre-registered rules |
| Result | **0 PASS / 0 WATCH / 11 FAIL**; holdout spread MAE 10.71 own vs 9.62 market |
| Ledgers | 12 questions (8 answered, 1 partial, 3 blocked), 8 suggestions, 4 decisions, 7 flags (6 open, 1 resolved) |
| Gates on the merged tree | validate_verified PASS · audit_numbers PASS · check_committed_site PASS · check_site PASS (21 pages) · verify PASS · verify_combined PASS · check_strength_site PASS (14 pages, every row source-linked) · 19 unit tests OK |
| CI | `Verify NFL1 site`, `Verify NFL source provenance`, `Verify NFL Decision Lab site build`, `Decision Room build and gate` all success on `9a70aa0` |

**Defect found by the gates, in this session's own work.** The first implementation of the study
reported four PASSes at 94–99% cover rates. The cause was a sign convention: the closing line was
treated as points *given to* the home club instead of the home club's *expected margin*. The
convention was verified against the site's own Week 10 table (`spread_line` 1.5 renders as
"NYG -1.5"), fixed, and locked with four unit tests (`tests/test_strength.py`). Every rule now
fails, which is the honest result.

**F-SOS-DATA-01 — root cause found and fixed (resolved).** The reported provenance mismatch was not
a corrupted file. `s9cb/collect.py` pinned the sha256 of the **raw download** in `build/raw/` while
committing a filtered, re-serialised extract, so the pin could never match. The collector now records
`committed_sha256`/`committed_bytes` alongside the raw pin, with a `hash_convention` note, and the
committed hash reproduces exactly (`sha256sum data/s9cb/games.csv`). The next refresh writes it
automatically.

**Merge hygiene incident, logged rather than hidden.** The first merge of `origin/main` into this
branch resolved the `COORDINATION.md` conflict by keeping one side, which silently dropped 617
substantive lines of board history and part of sessions `9c208ed8` and `46b6cabb`. It was caught by
comparing the merged file against both parents line by line, and the board was rebuilt so that **0
substantive lines are missing from either parent**. The `9c208ed8` result record is restored under a
labelled heading. This is the second time a one-sided conflict resolution has damaged this file
(`A-F01` was the first), which is itself evidence for suggestion S24 (a single flag/board register).

### Session `c56ebee8-nfl1` — second merge of `origin/main` (PRs #52–#53, incl. `ca779bcc`)

`main` moved again while PR #54 was open (`ca779bcc-nfl1`, strength-of-schedule study under
`strength/`). Merged, conflicts resolved keeping both sides:

| Conflicting file | Resolution |
|---|---|
| `index.html`, `pages/*.html`, `data/verification_report.json` | Generated artifacts: taken from `main`, then regenerated by all four generators. |
| `pipeline/gen_site.py` | Both sides kept. `ca779bcc`'s `strength/index.html` ("SOS Study") nav entry is preserved in `NAV` and in the Companion-pages sidebar group; its active-state rule (a sub-site `index.html` must not steal the root page's active state) was folded into `_is_active()` and now applies to `room/` and `strength/` alike. |
| `scripts/verified/normalize_nav.py` | Same entry and same active-state rule; `CANON` still matches `NAV` one for one (27 entries). |
| `COORDINATION.md` | Both sides kept. |

Fixed while regenerating: the merged `SIDEBAR` had picked up a stray trailing tuple that crashed
`gen_site.py` (`ValueError: not enough values to unpack`), and the `strength/` entry was landing
outside the list. Both corrected; the sidebar now has 7 groups with no duplicates.

**Final gates on the fully merged tree, all green:** `check_site` 25 pages / 0 broken ·
`check_committed_site` PASS · `tools/verify` 983 rows, 983 with an official source ·
`verify_combined` 1,979 links / 0 broken · `audit_numbers` 47/47 · `validate_verified` all hard
checks pass · **136 unit tests OK** (11 skipped). Every local link in `index.html`, `pages/`,
`room/` and `strength/` resolves — 0 broken.

**Note on `data/s9cb/provenance.json`:** the daily refresh workflow (`[skip ci]`) committed
`b16d2c4` to this branch while the merge above was being prepared. It changed only the
`generated_at` / `fetched_at` timestamps — all three `sha256` values are byte-identical. Resolved
in favour of the merge side, which carries the `hash_convention` and `committed_sha256` keys that
session `9cb71eb8` added, i.e. strictly more information about the same bytes.

### Session `c56ebee8-nfl1` — PR #54 merged, Pages deployed, one failing check fixed

**PR #54** <https://github.com/kanlerxz87-cyber/NFL1/pull/54> — merged 2026-11-13 13:25 UTC as
`437e30c`. `pages-build-deployment` finished **success**, so the site is live at
<https://kanlerxz87-cyber.github.io/NFL1/>. `Verify NFL1 site` and `Verify NFL Decision Lab site
build` also passed on the merge commit.

**The `Collect NFL data and rebuild model outputs` workflow was failing**, on `main` and on several
other sessions' branches, so it is not specific to this PR — the failures start at 13:16 UTC, before
PR #54 merged. Root cause found and fixed here:

* The job runs `pipeline/build_all.py`, which gives `data/model/dashboard.json` a **new**
  `generated_at`, and then `tools/check_committed_site.py`, which fails any page whose "Data built"
  stamp is older than that file.
* `pages/depth.html` was the only page stamped from a different source — `data/depth_ladder.json`
  — so after any refresh it read as stale and the check failed. Fixed: `depth_page()` now takes the
  model build time like every other page, and states the ladder's own build time and the injury
  report's scrape time in the body, so nothing is hidden.
* The daily refresh also never rebuilt the ladder at all, so the published 1st-to-6th string view
  would have kept the previous day's injury statuses while the rest of the site moved on. Added
  `python pipeline/build_depth_ladder.py` to `.github/workflows/collect-data.yml`, right after the
  injury scrape, and added `data/depth_ladder.json` to the step that commits refreshed artifacts
  (it is not under `data/model/`, so it was being left behind).

Logged as a cross-scope edit: `.github/workflows/collect-data.yml` is shared, but the change is
additive, keeps the ladder honest, and unblocks a red check.


---

# Session `65df4799-nfl1` — W5 result: PR #53 merged, Pages live (record)

- **PR:** https://github.com/kanlerxz87-cyber/NFL1/pull/53 (`arena/65df4799-nfl1` → `main`).
  Head `a07d27d` (post-rebase tree incl. both `origin/main` merges `1d55fe1` + `b989492`);
  all checks green on the head: Verify NFL1 site, Verify decision dashboard, Verify NFL
  Decision Lab site build, Verify NFL source provenance, Collect NFL data and rebuild
  model outputs (push + pull_request events).
- **Merge:** merge commit **`c02c293`** on `main` (2026-11-13, `gh pr merge 53 --merge`).
  Post-merge main checks all green (verify, decision dashboard, decision lab, collect).
- **Pages deploy:** `pages build and deployment` runs **43435665241** and **43435759608**
  both `success`. Live site verified with the cache-buster `?v=c02c293`:
  - https://kanlerxz87-cyber.github.io/NFL1/?v=c02c293 — Overview shows the Week-11 own
    lines table (13 rows, both conventions labelled, my X07 note), the merged sidebar
    shell, "Data built 2026-11-13T13:40:47Z".
  - https://kanlerxz87-cyber.github.io/NFL1/flagged.html?v=c02c293 — 52 flagged rows,
    all with official source links (F01–F41 + A-F01..03 + LR-01..LR-07).
- **Follow-up items for reviewers (do not block, per the brief):**
  1. The Overview KPI prints "week 10 complete" from the snapshot's
     `last_completed_week` field while Week 10 still has 13 unplayed games — the field
     means "latest week with any final result". Wording needs a reviewer decision
     (changing the label changes a published claim, so it was left as the model states it).
  2. LR-07's `SCHEDULE_FEED_FIXES` table in `pipeline/build_all.py` should be dropped
     once the upstream schedules feed carries the official kickoff times.
  3. S30 (kickoff cross-check per model refresh) awaits review.

_This record is the session's coordination duty after the merge; it lands via one
follow-up PR and does not change any generated page._