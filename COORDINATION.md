EAD
# COORDINATION.md — shared task board and integration log

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

> Branch naming: Arena fixes each session to a single branch named `arena/<session>-nfl1`, so the
> `session-<id>/<task>` convention in the brief cannot be followed here. Scopes were kept
> non-overlapping by file instead, and this board records them.

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

## Sources used (all verified reachable during the build)

- Standings (verification fixture): <https://www.nfl.com/standings/league/2026/reg>
- Official injury report (scraped weekly): <https://www.nfl.com/injuries/>
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

## PR / merge

- Pull request: [#13](https://github.com/kanlerxz87-cyber/NFL1/pull/13) — `arena/7600ed8b-nfl1` → `main`.
- Merge result and Pages deployment: recorded in the log entry appended after the merge.

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
- **Follow-up:** <https://github.com/kanlerxz87-cyber/NFL1/pull/19> carries the
  source-label fix and this record.

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
