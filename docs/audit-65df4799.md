# Live re-verification audit — session `65df4799-nfl1` (2026-11-13)

Every published table was re-checked **line by line against the live official pages on
2026-11-13 (UTC)**, using the page-fetch tool against nfl.com and the two club sites.
Nothing was inferred or filled in: where a value could not be confirmed it stays blank and
is flagged. Machine-readable results live in [`data/audit/live_recheck_2026-11-13/`](../data/audit/live_recheck_2026-11-13/)
(transcriptions + comparison scripts + JSON diffs), so every number below can be reproduced.

**Sources read live in this audit**

| Source | URL | Used for |
| --- | --- | --- |
| League standings | <https://www.nfl.com/standings/league/2026/reg> | 32 clubs W/L/T/PCT/PF/PA/NET |
| Week 10 schedule | <https://www.nfl.com/schedules/2026/by-week/week-10> | 14 fixtures, kickoff times, byes |
| Week 11 schedule | <https://www.nfl.com/schedules/2026/by-week/week-11> | confirms no games Nov 13–18 |
| Official injury report | <https://www.nfl.com/injuries/> | Week 10, 296 player rows, 26 clubs + 2 "No Injuries Reported" |
| Chiefs depth chart | <https://www.chiefs.com/team/depth-chart> | "Unofficial Depth Chart" (club's own label) |
| Seahawks depth chart | <https://www.seahawks.com/team/depth-chart/> | 1st–4th string, all three units |
| TNF game page (for the delta) | <https://www.nfl.com/games/commanders-at-giants-2026-reg-10> | Commanders 24, Giants 21, FINAL |

## 1. Standings — 6 published files × 32 clubs

Compared club-by-club, field-by-field (W, L, T, PCT, PF, PA, NET where present) against the
live league standings page. Comparator: [`compare_standings.py`](../data/audit/live_recheck_2026-11-13/compare_standings.py);
results: [`standings_diff.json`](../data/audit/live_recheck_2026-11-13/standings_diff.json).

| File | Rows matching live | Mismatching rows | Note |
| --- | --- | --- | --- |
| `data/verified/standings_2026.csv` | 30/32 | NYG, WAS | see delta below |
| `data/verified/standings_2026_reg.tsv` | 30/32 | NYG, WAS | same delta |
| `data/verified/official_standings_2026.json` | 30/32 | NYG, WAS | transcribes 6 of 7 columns (no PCT/NET by design) |
| `data/s9cb/official_standings_2026.csv` | 30/32 | NYG, WAS | same delta |
| `data/derived_standings.json` | 30/32 | NYG, WAS | per-game values re-derived from live totals |
| `data/model/snapshot.json` (standings) | 30/32 | NYG, WAS | same delta |

**The two-row delta is fully explained and is not a data error.** Every repo file carries a
retrieval stamp of 2026-11-12 (04:31Z–23:37Z). The Week-10 Thursday-night game
**Commanders 24, Giants 21 (FINAL, Thursday Nov 12, 8:15 PM ET)** kicked off after those
retrievals and finished after them; the live page (fetched 2026-11-13) includes it, the
snapshots correctly do not. The delta is arithmetically exact — NYG +21 PF / +24 PA, WAS
+24 PF / +21 PA, one extra game each — and all six files agree with each other on the
pre-game values. The daily collect refresh folds results in automatically.
Status: **verified with a documented currency note** (flag LR-01).

## 2. Week-10 schedule and byes — 14 games, 4 byes

Transcribed live ([`live_week10_schedule.tsv`](../data/audit/live_recheck_2026-11-13/live_week10_schedule.tsv)) and compared
matchups, dates, kickoff times and broadcasts ([`compare_schedule.py`](../data/audit/live_recheck_2026-11-13/compare_schedule.py),
[`schedule_diff.json`](../data/audit/live_recheck_2026-11-13/schedule_diff.json)).

| File | Matchups | Dates/kickoffs |
| --- | --- | --- |
| `data/verified/week10_fixtures_2026.csv` | 14/14 | 14/14 |
| `data/verified/schedule_2026_week10.tsv` | 14/14 | 14/14 |
| `data/dashboard/schedule_2026_w10.json` | 14/14 | 14/14 |
| `data/model/snapshot.json` (fixtures) | 14/14 | 14/14 |

Byes **CHI, DEN, PHI, TB** — live page matches `data/verified/bye_week10.tsv` exactly.
Note: `data/dashboard/schedule_2026_w10.json` writes the Rams as `LAR` where nfl.com's logo
code is `LA`; the comparator maps `LAR→LA` / `ARI→AZ` (the known X10 code-convention issue,
kept visible rather than silently normalised in source files).

## 3. Official injury report — 296/296 rows verified field-by-field

The live page (Week 10) was read chunk-by-chunk and **every row compared with
`data/model/official_injuries.json`** on player, position, injury, practice status and game
status: **296 of 296 rows match exactly**, across all 26 club sections, plus LAC and BAL
printing "No Injuries Reported" (the file holds zero rows for those two clubs, correctly).

Spot results for the rows earlier sessions had flagged:

| Earlier flag | Live finding (2026-11-13) | Status |
| --- | --- | --- |
| X01 — IND practice cells (A.J. Haulcy, Jonathan Taylor, Jerry Tillery, Charvarius Ward) wrong in both scrape and transcription | live: Haulcy Full, Taylor Full, Tillery DNP, Ward Full — file matches live exactly | resolved (page drift, not corruption) |
| X02 — scrape dropped BJ Green II (JAX), CJ Allen (IND), Grover Stewart (IND) | all three on live page and in the file with matching statuses | resolved |
| RV-02 / X-rows "not on the page" (Jaydn Ott KC; Kendal Daniels, Jawaan Taylor, Cameron Thomas ATL) | all four on live page now and in the file, matching | resolved (page drift at differing scrape times, cf. A-F04) |
| R-6a232e79-07 — Sam Darnold news-vs-status | live page row: DNP practice, game status blank; official news: "Sam Darnold ruled out for Seahawks' Week 10 game" — both true at once | open feature gap (LR-05): availability model needs a news-to-status flag |

The official page drifts within hours (already recorded as A-F04); the committed file's
`generated_at` is `2026-11-12T23:37:48Z` and matched the page exactly at recheck time.

## 4. Depth charts — club pages, row-by-row

The league publishes **no** depth chart (X08 stands: `/teams/<club>/depth-chart` is a 404);
club sites label their charts "Unofficial". Verified against the two transcribed clubs.

**Kansas City (28 rows, `data/depth_chart.json`, vs <https://www.chiefs.com/team/depth-chart>):**
25/28 rows exact. Three rows still differ from the club page (flag LR-02, X09 stays open):

| Row | Club page (live 2026-11-13) | Repo | Verdict |
| --- | --- | --- | --- |
| Offense WR (2) | 1st Xavier Worthy, 2nd Cyrus Allen, 3rd Josh Downs | s1 Worthy, s2 blank, s3 Cyrus Allen | differs — 2nd-string slot empty and Josh Downs missing |
| KR | 1st Emmett Johnson, 2nd Cyrus Allen | s1 blank, s2 Emmett Johnson | differs |
| PR | 1st Emmett Johnson, 2nd Cyrus Allen | s1 blank, s2 Emmett Johnson | differs |
| DT (1) | Chris Jones, Peter Woods | same | now matches (was part of X09) |

The rows are marked `verified: true` in `data/depth_chart.json`; under the no-silent-correction
rule the file is left untouched and the discrepancy is published for review.
Evidence: [`data/audit/live_recheck_2026-11-13/`](../data/audit/live_recheck_2026-11-13/), club URL above.

**Seattle (63 rows, `data/evidence/depth_charts.json`, vs
<https://www.seahawks.com/team/depth-chart/>):** 63/63 exact — every unit, 1st–4th string.
(The club's WR1 cell lists Cooper Kupp and Rashid Shaheed together; the transcription ranks
them 1st/2nd in row order, which preserves the cell content.)

## 5. Model/strategy figures — internal recomputation

These have no official published counterpart (no league odds feed exists — F02/F04), so
verification is by independent recomputation from committed inputs, all rerun on the merged
tree this session and all green:

| Gate | Result |
| --- | --- |
| `tools/verify_official.py` (repo vs hand-transcribed official pages) | 20 pass / 8 flag / 0 fail |
| `tools/verify_dashboard.py` (web/ figures independently reproduced) | 399 assertions, PASS |
| `scripts/verified/audit_numbers.py` (published figures recomputed) | 47/47 reproduce |
| `tools/verify.py` (every table row sourced) | 1,015 rows, 1,015 with official source link |
| `tools/verify_combined.py` (combined link + data check) | 1,276 links, 0 broken, PASS |
| `tools/check_committed_site.py` | PASS — no broken links, no source-less rows, no stale stamps |
| `tools/check_generators.py` | PASS — one writer per generated path (after the fix below) |
| `tools/check_reproducible.py` | PASS — clean rebuild changes nothing |
| `tools/check_freshness.py` | 23 assertions, PASS |
| referee replication (C5 division correlation) | −0.1048 reproduced independently (F36 resolved) |
| model spread MAE vs market | 9.98 vs 9.485 out of sample — market at least as good (CI [−0.054, 1.033]) |
| strategies passing all 8 gates | 0 of 12 — nothing promotable |

## 6. Repo review — defects found and fixed in this integration

| ID | Finding | Fix | Gate |
| --- | --- | --- | --- |
| LR-03 | `pages/lines.html` had **two writers** (`pipeline/gen_site.py` "My Lines" and `scripts/verified/build_site.py` "Own Lines"); whichever generator ran last silently replaced the page. The ownership gate could not see it (its regex missed the builder's page dict). | the verified sub-site's page moved to `pages/verified-lines.html`; both pages now coexist; `tools/check_generators.py` now detects dict-key claims and the ownership map records both | `tools/check_generators.py` |
| LR-04 | `scripts/verified/build_availability.py` passed a bare page name to the renderer, emitting 21 root-style nav links (`pages/x.html` from inside `pages/`) — every nav link on `pages/availability.html` was broken. | pass the `pages/`-qualified name so the renderer emits sibling-relative links | `tools/check_committed_site.py`, `scripts/verified/check_site.py` |
| — | Merge of idle PR #31 kept both sessions' work in `collect-data.yml`, `gen_site.py`, `tools/build.py`, `COORDINATION.md`, `README.md`; two different tools shared the names `tools/build_dashboard.py` / `tools/verify_dashboard.py` | web/ builder keeps the name (its workflow and gates pin it); the `dashboard/` builder preserved verbatim as `tools/build_dashboard_site.py` / `tools/verify_dashboard_site.py` | documented, both tools run green |

## 7. What remains flagged (published on the Flagged for Review page)

- **LR-01** — standings snapshot predates the Week-10 TNF final (currency note, auto-refreshed).
- **LR-02** — KC depth rows WR2 / KR / PR differ from the club's self-labelled "Unofficial"
  depth chart (X09 open). Club chart has no date stamp; weekly re-transcription advised (S27).
- **LR-05** — news-to-status gap (Darnold): official news rules a player out while the official
  report row still shows practice-only; the availability model has no news column (S28).
- **F02/F04** — no official odds feed exists; market columns are consensus mirror numbers,
  prop prices blank by design. Unverifiable against any official source — left blank.
- **X08/X10** — the league publishes no depth chart; club-code conventions (AZ/ARI, LA/LAR)
  differ between pages and files. Joins must normalise; files keep their own conventions.
- **F05** — monetary rewards need legal review; the leaderboard is paper points only.

No finding blocks publication; each is listed with its source links so a reviewer can decide.
