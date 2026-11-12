# Line-by-line post-merge review — session `08e0ce01-nfl1`

**Reviewed:** 2026-11-12 (UTC)
**Branch:** `arena/08e0ce01-nfl1`, base commit `c09c739bd5825981e97dddeefba5de6bd89d36fc`
**Scope:** the whole repository as published on `main`, and the live GitHub Pages site, read as a
user. Every gate below was run in a throwaway copy first (`/tmp/nfl1-review`) because
`tools/verify.py`, `tools/verify_combined.py` and `scripts/verified/validate_verified.py` write
files — the hazard session `a2cea255` recorded in `COORDINATION.md`. Nothing outside this
session's claimed file scope was edited; cross-session requests were taken over under the
60-minute rule and are logged in `COORDINATION.md`.

## 1. Gates run and results

| Gate | Command | Result |
| --- | --- | --- |
| Official-data reconciliation | `scripts/verified/validate_verified.py` | PASS — 15 hard checks, 136 games, 32 teams |
| Independent number audit | `scripts/verified/audit_numbers.py` | PASS — 47 recomputations (44 existing + 3 new C5 checks) |
| Structural site gate | `scripts/verified/check_site.py` | PASS — 21 pages, 0 broken links, 0 orphan pages |
| Source-link gate | `tools/verify.py` (CI order: build → verify) | PASS — 1,006 table rows, 1,006 with official source, 73 labelled unverified, 0 broken internal links |
| Combined-site verification | `tools/verify_combined.py` | PASS — 32 standings rows, 136 game rows, 6 injury rows, 0 mismatches; 1,159 local links, 0 broken |
| Referee replication gate | `referee/tools/check_site.py` | PASS — 7 pages, 938 rows, 1,084 links, every row carries an outside source link |
| Unit tests | `python3 -m unittest discover -s tests` | PASS — 107 tests |
| Live site read | fetched `https://kanlerxz87-cyber.github.io/NFL1/` | Renders the landing dashboard; all 14 own-line rows, leaderboard and verification table present |

`scripts/verified/check_external_links.py` was not run locally: the Arena sandbox cannot reach
nfl.com over `curl` (host allow-list), and CI runs that step with `continue-on-error`. External
official sources were instead fetched through the full-internet page reader and are cited below.

## 2. Findings, in the order they were found

### F-A — `README.md` contained a duplicated, unclosed code block (fixed)

`README.md` lines 30–53 opened a fenced block, repeated a second variant of the same paragraph
inside it, never closed the first fence, and printed the `pipeline/gen_site.py` line twice. Line 67
ran straight into `## Honesty rules` with no blank line. This is the first file a reviewer reads.
**Fixed** in this session's U03: one clean code fence, one render command, blank line restored.
Source: [repository README](https://github.com/kanlerxz87-cyber/NFL1/blob/main/README.md).

### F-B — `tools/build.py` silently replaced the whole README (fixed, closes `R-a2cea255-01`)

`write_readme()` embedded an obsolete template (`# NFL1 — NFL decision-intelligence dashboard`)
and rewrote `README.md` unconditionally, so the next local run of `tools/build.py` — the command
the repository's own docs tell you to run — would have deleted the verified-lab pointer and the
companion-session sections. **Fixed:** the template is now byte-identical to the published
README; a regeneration was tested and produced a zero-byte diff.

### F-C — flag F36 (C5 division-game count) independently reproduced, then fixed

The referee's open request was re-derived from the raw files rather than trusted:

| Definition | Division games | Pearson r with total points |
| --- | --- | --- |
| Division word only (`East`/`West`/…) — the published code | 52 | **−0.1297** (exactly what was published) |
| Conference + division — official groupings | 42 | **−0.1048** (exactly what the referee computed) |

The 10 spurious games are all AFC West vs NFC West (week 1 `AZ @ LAC`, week 3 `LA @ DEN`, week 4
`LAC @ SEA`, `DEN @ SF`, week 6 `SEA @ DEN`, week 7 `DEN @ AZ`, `LA @ LV`, `KC @ SEA`, week 8
`LAC @ LA`, week 9 `LV @ SF`). All eight official groupings were read from
[NFL.com division standings 2026](https://www.nfl.com/standings/division/2026/REG) and match
`data/verified/standings_2026.csv` exactly (8/8 groups, 32/32 clubs).

**Fixed:** `analysis/correlations.py` now keys the flag on `(conference, division)`;
`data/verified/model/correlations.json` and `pages/analysis.html` regenerated (C5 r = −0.1048,
p = 0.2245, n = 136, note "42 of 136"); `scripts/verified/audit_numbers.py` gained three
independent checks (groupings vs the official page, C5 r, C5 count) so the gate now fails if the
flag regresses. No strategy consumes this flag — the strategy engine uses nflverse's own
`div_game` column (`pipeline/build_all.py` lines 443–460), which was not affected.

### F-D — `R-a2cea255-03` answered: the three disputed standings cells touch nothing

| Artifact | Carries DIV/CONF/NON-CONF split cells? | Affected by WAS `non_conf`, IND `div`, PHI `div`? |
| --- | --- | --- |
| `data/verified/standings_2026.csv` | No — columns are totals only (`w,l,t,pct,pf,pa,net_pts,streak`) | **No** (the cells are not present) |
| `data/standings.csv`, `data/standings.json`, `data/derived_standings.json` | No split fields | **No** |
| `data/verified/model/ratings.json` (main model) | Inputs are `games_2026.csv` + totals; row keys `w,l,t,gp,pf,pa,net` | **No** |
| `pipeline/build_all.py` (main pipeline) | Computes standings from game results; strategies use `div_game` from the schedules feed | **No** |
| `src/nfl/*` (verified-lab) | Yes — ingested from its own TSV | **Yes, by design:** `DISPUTED_CELLS = {("IND","div"),("PHI","div"),("WAS","non_conf")}` publishes them verbatim, sets `div_win_pct = None` for IND/PHI, flags WAS `non_conf`, and excludes them from every computation and from the findings list (definitional family) |

Conclusion: no change required; the verified-lab exclusion is the correct handling and the main
pipeline never saw the cells.

### F-E — flag F37: 15 root pages and both sub-sites were unreachable from the landing page (fixed)

A crawl of every `href` in `index.html` and `pages/*.html` found **zero** inbound links to
`requirements.html`, `strategy-lab.html`, `leaderboard.html`, `bet-types.html`,
`depth-chart.html`, `data-tables.html`, `verification.html`, `integration.html`,
`deployment.html`, `executive-summary.html`, `questions.html`, `suggestions.html`,
`injuries.html`, `flagged.html`, `legacy-site.html`, to `referee/`, `verified-lab/`,
`dashboard/` or `lab/` — including the full requirements inventory the brief asks for.
`check_site.py` stayed green because its reachability rule covers only `index.html` + `pages/*`.

**Fixed:** new `pages/sections.html` publishes a categorized index of all 40 published sections
(six generations plus both sub-sites), linked from the landing navigation through both nav
authorities (`pipeline/gen_site.py` NAV and `scripts/verified/normalize_nav.py` CANON). The flat
header nav was not otherwise disturbed. Flag F37 / suggestion S21.

### F-F — flag F38: CI audits a regenerated index, not the published one (flagged, needs review)

`tools/build.py` rewrites `index.html` from `site/templates/base.html` (sidebar layout) while the
published landing page comes from `pipeline/gen_site.py` (header layout). `verify.yml` runs
build → verify in that order, so `tools/verify.py`'s `index.html rows=31` describes a page that is
never published. Reproduced locally: running `tools/verify.py` against the committed landing page
reports `rows=0` (its tables are not `class="data-table"`), which is exactly the blind spot.
Published as **flag F38 + suggestion S14** for a reviewer to choose a path; not changed unilaterally
because it touches shared workflows and two generators' ownership.

### F-G — flag F39: published pages lagged the data bot, and the lag was material (fixed)

The data bot committed a refresh at 18:53 UTC (`c09c739`) that changed the official injury
report, but the published pages were still the 05:07 build:

| Value | Published before | Current data | Verified against live nfl.com |
| --- | --- | --- | --- |
| Official Week 10 injury rows | 254 | 276 | Spot-checked across page chunks: WAS/NYG rows match row-for-row; CIN and SEA now publish reports; LAC and BAL read "No Injuries Reported" ([Week 10 injury report](https://www.nfl.com/injuries/)) |
| Starters flagged | 103 | 113 | Consistent with the additional reports |
| Clubs without a published report | 4 (BAL, CIN, LAC, SEA) | 2 (BAL, LAC) | Confirmed: the Monday LAC@BAL game shows "No Injuries Reported" for both clubs |
| Mirrored-feed coverage row | 20/254 (mismatch) | 276/276 (matched) | Computed by the pipeline's own verification stage from the refreshed feeds |
| `data/combined_verification.json` link audit | 1,064 | 1,159 | Re-run locally: 1,159 checked, 0 broken |

**Fixed** by regenerating every committed artifact in CI order (verify_combined → build →
gen_site → build_site → build_availability → normalize_nav → verify). Suggestion **S23/S24**
propose a commit-back or staleness gate so this cannot recur. The full 276-row transcription was
not repeated by hand; row-level spot checks plus the club-report statuses above are the evidence,
and the scrape itself reads the official page directly.

### F-H — flag F40: data-bot pushes skip the verification gates (flagged, needs review)

`collect-data.yml` bot commits carry `[skip ci]`, so `verify.yml` and `pages.yml` do not run on
them. Check-runs on `c09c739` are only `report-build-status`, `deploy` and `build` (Pages) — no
`Verify NFL1 site` run exists for that commit. Refreshed data therefore reaches `main` ungated
until the next human push; F-G is the visible consequence. Published as **flag F40 + suggestion
S13** (gated refresh) rather than changed here, because the skip is also what prevents the bot
from looping on its own commits — the fix needs a reviewer's choice of mechanism.

### F-I — minor observations (recorded, not changed)

- `tools/seed_data.py` regenerates `data/*.json` from its embedded transcripts; running it would
  drop this session's appended F37–F40 / S21–S25 / Q28 rows. It is not run by any workflow.
  Noted here so the next session does not run it casually.
- Four flag registers remain live with colliding IDs (root F01–F40, pipeline F01–F19, referee
  R-xx, verified-lab V-xx). Suggestion S22 proposes consolidating them; until then each register
  names its generation in the page text.
- The three open cross-session requests from `a2cea255` are resolved as follows: R-01 fixed
  (§F-B), R-03 answered (§F-D), R-02 (34-check harness as CI gate) left as suggestion S25 for a
  reviewer because it edits shared CI.

## 3. Official sources consulted in this review (for manual checking)

| What was checked | Official source |
| --- | --- |
| Division groupings for the C5 fix (8 groups, 32 clubs) | <https://www.nfl.com/standings/division/2026/REG> |
| Week 10 injury report — row spot checks, club report status | <https://www.nfl.com/injuries/> |
| Standings (re-check of prior sessions' 32/32 match) | <https://www.nfl.com/standings/league/2026/reg> |
| Schedules / week 10 slate | <https://www.nfl.com/schedules/> |
| Live published site | <https://kanlerxz87-cyber.github.io/NFL1/> |
| Pages configuration and check-runs | <https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages> and the repository's check-runs API |

Every number in this report was recomputed from committed files or read from the official pages
on 2026-11-12; nothing is inferred. Values that could not be confirmed are left out rather than
estimated.

## 4. What still needs a reviewer (non-blocking, published on Flagged for Review)

1. **F38 / S14** — verify the published generation instead of a regenerated substitute.
2. **F40 / S13** — gate the data refresh so `[skip ci]` pushes cannot land ungated.
3. **Q28 / Q21** — decide which of the four site generations is authoritative.
4. **S22** — consolidate the four flag registers.
5. **S25 / R-a2cea255-02** — run the referee replication (and optionally the 34-check harness) in CI.
6. Pre-existing blockers unchanged by this review: no official odds feed (F02), no prop prices
   (F04), monetary rewards need legal review (F05), weather/travel/inactives not ingested
   (F06/F09/F10).
