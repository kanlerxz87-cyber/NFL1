# COORDINATION.md — shared task board

This file is the single shared task board for every session working in this
repository. **Read it before touching anything. Claim before you edit. Commit
your claim immediately.**

## Protocol (binding)

1. **Claim first.** Before editing any file, add a row below with your session
   ID, the task, the exact file scope you intend to touch, and status
   `in progress`. Commit and push *that claim* before you edit anything.
2. **Never start a task another session has claimed.** If you need it, log a
   request in the *Cross-session requests* section and keep working elsewhere.
3. **One branch per session**, named `session-<id>/<task>`. Edit only the files
   in your claim. If you discover you need a file outside your scope, log a
   request — do not edit it.
4. **Small, frequent commits.** `git pull --rebase` before *every* push.
5. **On conflict: stop.** Resolve it without discarding another session's work,
   then record what you did in the *Conflict log*.
6. **When done**, set status to `done` (or `needs review`), and record the
   sources used, the verification you performed, and any irregularities found.
   `needs review` items are published on the **Flagged for Review** page and
   **block nothing**.
7. **Stale claims** — more than 60 minutes with no commits — may be taken over.
   Record the handoff in the *Handoffs* section; do not delete the old row.
8. **Shared outputs** (table data under `data/`, the site index, navigation,
   `docs/`) are changed **only by the final integration session**, which merges
   the branches, re-verifies the combined data line by line, confirms the site
   builds with no broken links, and publishes to Pages.

### Status vocabulary

`unclaimed` · `in progress` · `done` · `needs review`

---

## Task board

| # | Task | Status | Owning session | Files touched | Notes |
|---|------|--------|----------------|---------------|-------|
| 1 | Verify repo contents line by line against official sources | done | `arena/a2cea255-nfl1` | `data/verified/*.tsv`, `src/nfl/verify.py`, `verification.html` | 34 automated checks: 29 PASS, 5 FLAG, 0 FAIL |
| 2 | Transcribe official Week 10 / 2026 REG data | done | `arena/a2cea255-nfl1` | `data/verified/standings_2026_reg.tsv`, `injury_report_2026_week10.tsv`, `schedule_2026_week10.tsv`, `bye_week10.tsv`, `team_report_status_week10.tsv`, `nfl_news_2026_week10.tsv`, `sources.json` | 32 standings rows, 254 injury entries, 14 games, 4 byes, 8 news items, 11 sources |
| 3 | Provenance + stats + odds + correlation engines | done | `arena/a2cea255-nfl1` | `src/nfl/provenance.py`, `stats.py`, `ingest.py`, `odds.py`, `correlation.py`, `signals.py` | stdlib only; BH-FDR, hand-rolled incomplete beta |
| 4 | Ratings, Pythagorean fit, home-field, line origination board | done | `arena/a2cea255-nfl1` | `src/nfl/ratings.py` | Spread/total/win-prob deliberately `None` — see task 8 |
| 5 | Availability + depth tracking | done | `arena/a2cea255-nfl1` | `src/nfl/availability.py` | Depth charts UNAVAILABLE (no reachable official feed); string level never guessed |
| 6 | Strategy catalogue, validation gates, luck removal, leaderboard | done | `arena/a2cea255-nfl1` | `src/nfl/strategies.py`, `gates.py`, `luck.py`, `leaderboard.py` | 13 strategies, 9 gates, 0 APPROVED / 13 NOT_STAKEABLE, 0 scored / 13 withheld |
| 7 | Pipeline → single site-data artifact | done | `arena/a2cea255-nfl1` | `src/nfl/pipeline.py`, `data/processed/site_data.json` | Generator contains no numbers; all values come from this artifact |
| 8 | Executive summary, open questions, suggestions board, methodology | done | `arena/a2cea255-nfl1` | `content/*.md` | 22 open questions (Q01–Q22), 22 suggestions (S-01–S-22) with blank Decision columns |
| 9 | Site generator + 20-page dashboard | done | `arena/a2cea255-nfl1` | `src/nfl/sitekit.py`, `src/nfl/markdown_lite.py`, `scripts/build_site.py`, `*.html` at repo root | 20 pages, 6 nav categories, inline CSS, no external assets |
| 10 | Test suite incl. link checker + source-link enforcer | done | `arena/a2cea255-nfl1` | `tests/test_stats.py`, `test_odds.py`, `test_gates.py`, `test_data_integrity.py`, `test_site.py` | 102 tests, all passing |
| 11 | **Final integration**: merge, re-verify, publish to Pages | done | `arena/a2cea255-nfl1` | `*.html` + `.nojekyll` at repo root, `README.md`, `COORDINATION.md` | See *Integration record* below |

No task is currently `unclaimed`. No task is currently `needs review` — every
item requiring human attention is published on the
[Flagged for Review](https://kanlerxz87-cyber.github.io/NFL1/flagged.html) page
instead, which is the intended destination for them.

---

## Integration record (task 11)

**Integration session:** `arena/a2cea255-nfl1` (this session ran the whole build
end to end, so it is also the integration session; no other session claimed
work).

- **Branch:** `arena/a2cea255-nfl1`, branched from `main` @ `5aeb599`.
- **Pull request:** #1 — https://github.com/kanlerxz87-cyber/NFL1/pull/1
- **Merge result:** merged into `main` (no approval wait, per instructions).
- **Re-verification of combined data:** full pipeline re-run from the
  transcribed TSVs (`PYTHONPATH=src python3 -m nfl.pipeline`), then the site
  rebuilt (`PYTHONPATH=src python3 scripts/build_site.py`), then all 34
  verification checks and all 102 tests re-run against the merged tree.
  **0 FAIL.**
- **Link check:** `tests/test_site.py::TestLinks` walks every `href` in all 20
  pages and fails the build on any internal link that does not resolve, any
  dead in-page anchor, or any suspiciously short `href`. Passing.
- **Source-link check:** `tests/test_site.py::TestSourceLinks` requires that
  every row of every table declaring a `Source` column carries a link to an
  official host (nfl.com, developer.sportradar.com, or a github.com permalink).
  300+ rows checked. Passing. This test caught and fixed two real defects:
  a naive URL extractor emitting `href="A"`, and the Source Register printing
  URLs as text instead of links.
- **Pages publication:** the site is generated into the **repository root** with
  a `.nojekyll` file so Pages serves the build verbatim rather than running it
  through Jekyll. The Pages source is already `main` @ `/`, and it could not be
  moved to `/docs` — `PUT /repos/kanlerxz87-cyber/NFL1/pages` returns
  **403 "Resource not accessible by integration"**, because the integration token
  lacks `pages:write`. Publishing from the root is the workaround, and it is
  recorded as an irregularity below. Live at
  **https://kanlerxz87-cyber.github.io/NFL1/**

---

## Sources used

### Official (tier `OFFICIAL`)

| Source | URL | Used for |
|---|---|---|
| NFL standings, 2026 REG | https://www.nfl.com/standings/ | All 32 team records, PF/PA, streaks, home/road/div/conf splits |
| NFL standings, division view | https://www.nfl.com/standings/division/2026/REG | Canonical form of the above |
| NFL injury report, Week 10 2026 | https://www.nfl.com/injuries/ | 254 report entries, practice + game status, per-team record cross-check |
| NFL tie-breaking procedures | http://www.nfl.com/standings/tiebreakingprocedures | Reference for division/conference ordering |
| News roundup, Wed 11 Nov 2026 | https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11 | CLE start Watson; ARI start Beck |
| Dolphins place QB Willis on IR | https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start | MIA QB change |
| Darnold ruled out, Week 10 | https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again | SEA QB change |
| Nacua likely to IR | https://www.nfl.com/news/rams-wr-puka-nacua-likely-to-be-placed-on-injured-reserve-with-turf-toe-sprained-mcl-and-pcl | LA WR absence |
| Jacobs finger surgery | https://www.nfl.com/news/packers-rb-josh-jacobs-to-undergo-surgery-on-finger-this-week | GB RB absence |
| News roundups, Mon 9 / Tue 10 Nov 2026 | https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-tuesday-nov-10 · https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-monday-nov-9 | Hooker/Henley trades, McCarthy to play, Herbert avoids fracture |
| Week 9 injuries roundup | https://www.nfl.com/news/notable-injuries-news-sunday-week-9-games-2026 | Carried-over availability context |
| Sportradar NFL Official API — weekly depth charts | https://developer.sportradar.com/football/reference/nfl-weekly-depth-charts | **Cited, not used.** The NFL's sanctioned depth-chart feed; credential-gated and unreachable from the build environment |

### Community mirror (tier `COMMUNITY_MIRROR`)

| Source | URL | Used for |
|---|---|---|
| nflverse `teams_colors_logos.csv` | https://github.com/nflverse/nflverse-pbp/blob/master/teams_colors_logos.csv | Team labels, colours and logos **only**. Never a source of on-field values |

Full register with tiers, retrieval timestamps and `used_for` notes:
[`data/verified/sources.json`](data/verified/sources.json) and the
[Source Register page](https://kanlerxz87-cyber.github.io/NFL1/sources.html).

---

## Verification performed

- **34 automated checks** in `src/nfl/verify.py` → **29 PASS, 5 FLAG, 0 FAIL**.
  Each check names its source URL.
- **Arithmetic identities** recomputed from the transcribed cells: tie-aware
  `PCT = (W + 0.5·T)/(W+L+T)` (half-up rounding via `Decimal`, not Python's
  half-to-even `round()`), `NET = PF − PA`, `HOME + ROAD = GP`,
  `CONF + NON-CONF = GP`, `DIV ≤ CONF`.
- **League-wide balance**: 136 completed games, 272 team-games, W == L == 134,
  T == 4, PF == PA == 6,267.
- **Slate integrity**: 14 games, 28 distinct teams, playing ∪ bye == 32, no
  overlap or duplicates.
- **Cross-source agreement (V28, strongest single check)**: all 28 team records
  printed beside club logos on the injury page match the official standings
  page exactly, including both tied clubs.
- **Vocabulary and position checks** on all 254 injury entries.
- **Bye list corroborated** by five independent retrievals.
- **Provenance**: 100% of published rows carry a source URL (V30).
- **Odds arithmetic** unit-tested: American↔decimal round-trips, implied
  probability, overround, multiplicative and power devig (sum to 1.0), parlay
  fair probability with and without a ρ adjustment, edge.
- **Gate harness proven bidirectional**: it *approves* a well-formed strategy
  and *rejects* lookahead, an edge inside the noise, a confidence interval
  spanning zero, and profit concentrated in one fold. A gate that only ever
  says no would not be evidence of anything.

## Irregularities found

All are published verbatim, excluded from derived computation, and listed on the
[Flagged for Review](https://kanlerxz87-cyber.github.io/NFL1/flagged.html) page
with the arithmetic that proves each one. **None of them blocks the merge.**

| ID | Irregularity | Handling |
|---|---|---|
| V07 | **WAS `non_conf` is self-contradictory.** 2-5-1 is 8 games played; CONF 3-2-1 is 6, so NON-CONF must cover 2 games — but the page prints `1-3-1`, which is 5 games and is character-identical to WAS LAST-5. | Published verbatim, excluded from all derived metrics, left blank on site tables |
| V10 | **IND `div` disagrees with its own PCT.** `1-3-0` ⇒ 0.250, but the page prints 0.333. | Same. `div_win_pct` is `None` for IND |
| V10 | **PHI `div` disagrees with its own PCT.** `1-4-0` ⇒ 0.200, but the page prints 0.250. | Same. `div_win_pct` is `None` for PHI |
| V10b/c | **Duplication defects.** IND DIV == IND HOME, PHI DIV == PHI HOME, WAS NON-CONF == WAS LAST-5 — consistent with a rendering/copy defect on the source page. | Flagged with the duplication shown explicitly |
| V32 | **Community mirror carries 4 retired club codes** (`LAR`, `OAK`, `SD`, `STL`) alongside the 32 active ones. All 32 active codes are present and correct (V31 PASS), but a naive join would attach labels to clubs that no longer exist. | Excluded from every join; reference rows tiered `COMMUNITY_MIRROR`, used for labels/colours only |
| — | **Injury report barely populated at retrieval time.** Only 6 of 254 entries (2.36%) carry a designation or game status, because it was retrieved on the Thursday of game week. Practice participation *is* fully populated (93 DNP / 89 LP / 72 FP). | Blanks left blank. Consequence documented: any availability model must re-fetch after the Friday 4:00pm ET deadline and timestamp every retrieval |
| — | **SEA / CIN / LAC / BAL print the literal text "No Injuries Reported"**; CHI / DEN / PHI / TB are absent because they are on bye. These are different facts and must not be collapsed into one another. | Kept distinct: `no injuries reported` vs `on bye (no report)` |
| — | **No official depth chart is reachable.** NFL.com publishes none; Sportradar's sanctioned feed requires an API key. | `string_level_drop` registered UNAVAILABLE. 2nd/3rd/4th-string analysis uses only officially confirmed NFL.com news items |
| — | **No verified 2026 odds source is reachable.** Unofficial aggregators were found and rejected. | Every odds field left blank and flagged. No spread, total, win probability or edge is published |
| — | **The Pages source cannot be changed to `/docs`.** `PUT /repos/kanlerxz87-cyber/NFL1/pages` returns 403 "Resource not accessible by integration"; the integration token lacks `pages:write`. Pages is pinned to `main` at `/`. | The 20 generated pages are published from the repository root instead, with `.nojekyll`. The build location is a single variable (`sitekit.SITE_OUT`, overridable via `NFL1_SITE_OUT`), so moving it to `docs/` later is a one-line change once a token with `pages:write` is available |

## Environment limitations recorded (so nobody re-tries them)

- Outbound network from the build environment is allowlisted to `github.com`,
  `api.github.com`, `codeload.github.com`, `registry.npmjs.org`, `pypi.org` and
  `files.pythonhosted.org`. Direct `curl` to nfl.com returns HTTP `000`; data
  collection used the agent's page-retrieval tool instead.
- **GitHub release assets cannot be downloaded** (302 → `release-assets.githubusercontent.com`,
  then exit 35 / 0 bytes). This blocks every nflverse parquet feed: schedules,
  team stats, player stats, play-by-play and **odds**. Repository *contents*
  are reachable via the API and were used for the teams mirror.
- `nflverse/nflverse-pbp`'s default branch is `master`, not `main`.
- **GitHub Pages settings cannot be modified** with the available token
  (403 on `PUT /repos/{owner}/{repo}/pages`). `pages:write` is not granted.
- Searching for injury reports returns **2025-season** pages; the live season is
  **2026**. Never blend them.

## Cross-session requests

_None._

## Conflict log

_None._ No other session claimed work on this repository, so no rebase conflict
arose. Had one occurred, the resolution would have been recorded here rather
than resolved by discarding another session's commits.

## Handoffs

_None._
