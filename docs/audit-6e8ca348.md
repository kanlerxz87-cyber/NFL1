# Repository audit — session `6e8ca348-nfl1`

Read at commit `c09c739` (2026-11-12), against the official NFL pages read the same day.
Every finding below names the file that shows it and the official source that settles it.
Where a value could not be confirmed from an official source it is marked **blank** and
published on the Flagged for Review page rather than filled in.

## What the repository contained when this session started

One driver session had produced most of it, and four generations of the same site coexisted:

| Generation | Entry | Owner recorded on the board | Data it reads |
|---|---|---|---|
| Model site (root) | `index.html`, `pages/*.html` | session `7600ed8b` | `data/model/*.json` |
| Governance site (root) | `governance.html` (was `index.html`) | session `80731db4` | `data/*.json` |
| Companion dashboard | `docs/index.html` | session `87deb7ab` | `data/session-87deb7ab/*.json` |
| Referee audit | `referee/index.html` | session `73fdd6c4` | its own transcriptions |
| Verified lab | `verified-lab/index.html` | session `a2cea255` | hand transcription |

Nothing was deleted. This session adds one entry dashboard (`web/`) and a verification layer,
and fixes the defects below in the files that cause them.

## Method

1. Read every generator, every data file and the live site.
2. Re-read the four official pages the project depends on and transcribe them row by row into
   `data/evidence/` — 32 standings rows, 279 injury rows, 14 games plus 4 byes, and 123
   depth-chart slots from two club sites.
3. Compare every repo dataset with those transcriptions **cell by cell**
   (`tools/verify_official.py`, 28 checks).
4. Rebuild the site from a clean checkout and diff it against what was committed
   (`tools/check_freshness.py`, `tools/check_generators.py`).

## Findings

### Verified correct

| What | How | Result |
|---|---|---|
| 2026 standings, W/L/T/PF/PA, 32 clubs | `data/standings.json`, `data/verified/standings_2026.csv`, `data/verified/standings_2026_reg.tsv` vs <https://www.nfl.com/standings/league/2026/reg> | **32/32 rows, all five fields exact, in all three files** |
| NET PTS arithmetic | every row, `PF − PA = NET` | 32/32 |
| Week 10 schedule, 14 games | `data/model/snapshot.json`, `data/verified/week10_fixtures_2026.csv` vs <https://www.nfl.com/schedules/2026/REG10> | 14/14 dates and kickoff times match |
| Week 10 byes | CHI, DEN, PHI, TB | match the official page |
| Injury report, per-club row counts | `data/model/official_injuries.json` vs <https://www.nfl.com/injuries/> | 24 of 26 clubs exact |
| Own-line/market convention | `data/model/lines.json` `sign_convention_check` | correlation 0.439 over 5,591 games; the documented convention is right |
| Games played | half the sum of club games in the official table | 136 = published 136 |
| Availability starter counts | recomputed from the player rows | all 32 clubs reproduce |

### Defects found and fixed in this session

| # | Defect | Evidence | Fix | Gate |
|---|---|---|---|---|
| X05 | Two generators both wrote `index.html`; whichever job ran last decided the landing page | `tools/build.py` `page_home()` and `pipeline/gen_site.py` `main()` | `tools/build.py` now writes `governance.html`; `index.html` has one owner | `tools/check_generators.py` |
| X06 | The data refresh committed JSON but never re-rendered HTML, so pages went stale | live `index.html` stamped `05:07:59` beside `data/model/dashboard.json` stamped `18:53`; NE row read Out 2 / practice 6 from data saying Out 1 / 7 | `collect-data.yml` re-renders and commits pages, with a push retry | `tools/check_freshness.py` |
| X07 | The landing page printed a bare market number beside a signed home line, making LA @ ARI look like a 14.7-point difference when it is 4.27 | `index.html` row LA @ ARI: `ARI +5.2` next to `-9.5` | market rendered signed for both teams; difference derived from printed numbers | `tools/verify_dashboard.py` (383 assertions) |
| — | "actionable" printed on LA @ ARI while the blend test puts a **negative** weight (−0.328) on the model | `data/model/lines.json` `blend_test` | relabelled "largest difference"; `Edge` renamed `Difference` wherever no price exists | same |
| — | The dashboard's `web/` pages initially linked assets with the wrong relative prefix | first run of `tools/verify_dashboard.py` failed on 10 links | prefix corrected and tested | same |

### Defects found and **not** fixed here (published for review)

Another session's file is never silently corrected; each row is on the Flagged for Review page
with both links.

| # | Finding | Official source | Repo file |
|---|---|---|---|
| X01 | Four Colts practice cells are wrong in **both** the automated scrape and the hand transcription: A.J. Haulcy, Jonathan Taylor, Jerry Tillery, Charvarius Ward | <https://www.nfl.com/injuries/> | `data/model/official_injuries.json`, `data/verified/injury_report_2026_week10.tsv` |
| X02 | The scrape drops three players the page lists: BJ Green II (JAX), CJ Allen (IND), Grover Stewart (IND) — 276 captured vs 279 printed | same | `data/model/official_injuries.json` |
| X03 | The hand transcription is missing 25 rows: the whole SEA section (15), the whole CIN section (4), 2 SF, 1 AZ, and the 3 above | same | `data/verified/injury_report_2026_week10.tsv` |
| X04 | `data/injuries.json` holds 61 of 279 rows and is rendered beside full-coverage tables | same | `data/injuries.json` |
| X08 | The league publishes **no** depth chart: `/teams/seattle-seahawks/depth-chart` returns the 404 "Flag on the Play" page | <https://www.nfl.com/teams/seattle-seahawks/depth-chart> | `data/verified/depth_chart_probe.csv` |
| X09 | The repo's KC depth chart disagrees with the club page: Emmett Johnson is 1st (repo: 2nd), Kenneth Walker 3rd (repo: 1st), Cyrus Allen 2nd (repo: 3rd) | <https://www.chiefs.com/team/depth-chart> | `data/depth_chart.json` |
| X10 | Club codes are inconsistent (AZ/ARI, LA/LAR) and a join silently drops rows — this audit's own first run hit it | <https://www.nfl.com/standings/league/2026/reg> | several |

### Values that cannot be verified at all

| Item | Why | Handling |
|---|---|---|
| Any betting price | The NFL publishes no odds and no licensed feed is connected | market columns are consensus closing numbers from the mirror, labelled; prop prices blank |
| Player prop market lines | same | 343 model-only lines, market blank |
| Who physically starts | no league depth chart; 2 of 26 clubs transcribed | "starter" is a stated assumption, flagged |
| Live inactive lists | not ingested | blank, flagged |
| Weather for unplayed games | not published before kickoff | totals ignore it, flagged |

## What the numbers say (recomputed, not quoted)

- Out-of-sample 2026: model spread MAE **9.98** vs market **9.485**; 95% CI on the difference
  `[−0.054, 1.033]`, i.e. the market is at least as good and probably better.
- Blend fitted on 2025, tested on 2026: weight **1.336** market, **−0.328** model; hybrid MAE
  **9.542** vs market-only **9.485**. The model adds nothing in the test window.
- Leaderboard: **0 of 12** strategies pass all 8 gates; best lower-bound ROI **−3.85%**;
  smallest BH q-value **0.9889**.
- Sample needed to separate a real edge from luck at 80% power: **17,689** bets for a 1%
  edge, **708** for 5% — 65 and 2.6 seasons respectively.

## Sources read for this audit

- <https://www.nfl.com/standings/league/2026/reg> — 32 clubs, W/L/T/PCT/PF/PA/NET
- <https://www.nfl.com/injuries/> — Week 10, 279 player rows across 26 club sections, LAC and BAL "No Injuries Reported"
- <https://www.nfl.com/schedules/2026/REG10> — 14 games, 4 byes, kickoff times
- <https://www.nfl.com/teams/seattle-seahawks/depth-chart> — 404
- <https://www.seahawks.com/team/depth-chart/> — 1st–4th string, all three units
- <https://www.chiefs.com/team/depth-chart> — "Unofficial Depth Chart", all three units
- <https://www.nfl.com/teams/seattle-seahawks/roster> — roster only, no depth order
- <https://www.nfl.com/teams/> — club directory
- <https://github.com/nflverse/nflverse-data> — mirrored feeds (CC-BY-4.0)
