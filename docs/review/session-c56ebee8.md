# Line-by-line review and fresh official re-verification — session `c56ebee8-nfl1`

Date of review: **2026-11-13** (UTC). Branch `arena/c56ebee8-nfl1`, base `09c03f05` (= `origin/main`
at start, 0 behind / 0 ahead).

Board read before work: yes, all 1,785 lines of `COORDINATION.md`. No other session branch existed on
the remote at claim time, so no other session held a live task. Three pull requests were open
(`#31`, `#37`, `#43`); none was touched, none was closed by this session.

---

## 1. Method

Every claim below was checked against the official page it cites, on 2026-11-13, by fetching the
page and comparing values field by field. Nothing in this document is inferred. Where a value could
not be confirmed it is recorded as unverified and linked to the page that would settle it.

The word *official* is used narrowly: **nfl.com**, **a club's own site on the `*.nfl.com` /
club-domain family**, and the NFL's own operations site. `nflverse` is treated as a community mirror
of the league's GSIS feed — useful, licensed CC-BY-4.0, and **not** official.

---

## 2. Sources fetched and read during this review

| Source | URL | Used to check |
|---|---|---|
| NFL league standings | <https://www.nfl.com/standings/league/2026/REG> | the 32-row standings snapshot |
| NFL Week 10 schedule | <https://www.nfl.com/schedules/2026/by-week/week-10> | 14 fixtures, kickoff times, 4 byes |
| NFL injury report (Week 10) | <https://www.nfl.com/injuries/> | the 296-row scraped snapshot |
| NFL depth-chart probe | <https://www.nfl.com/teams/kansas-city-chiefs/depth-chart> | whether the league publishes a depth chart |
| Arizona Cardinals depth chart | <https://www.azcardinals.com/team/depth-chart> | spot-check of the committed club-chart transcription |
| nflverse licence (GitHub API) | <https://api.github.com/repos/nflverse/nflverse-data> | the CC-BY-4.0 licence claim |

---

## 3. What was checked, and the result

| # | Check | Compared against | Result |
|---|---|---|---|
| R1 | 2026 standings, 32 clubs (W / L / T / PCT / PF / PA / NET) | nfl.com league standings, 2026-11-13 | **30 of 32 match.** See irregularity **C-A** |
| R2 | Week 10 injury report row counts | nfl.com injury page, 2026-11-13 | **296 rows, 26 clubs — exact match** with `data/model/official_injuries.json` |
| R3 | Week 10 injury report, per-club counts | same | **24 of 26 club counts identical.** The 2 that differ are club-code aliases (nfl.com `AZ`/`LA` vs this repo's `ARI`/`LAR`), not missing rows |
| R4 | Week 10 injury report, 14 named rows field by field | same | **12 of 14 match exactly**; the 2 "missing" are the same `LAR` alias |
| R5 | Week 10 fixtures and byes | nfl.com Week 10 schedule, 2026-11-13 | **14 fixtures and 4 byes (CHI, DEN, PHI, TB) match** |
| R6 | Does nfl.com publish a depth chart? | nfl.com depth-chart probe | **No. HTTP 404**, "Flag on the Play". Same result as the 2026-11-12 check |
| R7 | Club depth-chart transcription (ARI) | azcardinals.com, 2026-11-13 | **Matches row for row**, including ranks 1–3 and all three units |
| R8 | nflverse licence | GitHub API | **CC-BY-4.0**, repo not archived — the site's attribution footer is correct |
| R9 | Pinned source files | `data/model/provenance.json` | **12 files, every one with URL + byte count + sha256** |
| R10 | 2026 game rows | `data/verified/games_2026.csv` | **136 rows**, matching the "136 games" figure published on the site |
| R11 | Availability counts | `data/model/availability.json` | **296 injury records, 109 starters** — matches the dashboard counts |
| R12 | Internal links, all 25 pages | `scripts/verified/check_site.py` | **PASS**, 0 broken, 0 unreachable |
| R13 | Committed-site rules | `tools/check_committed_site.py` | **PASS**, no source-less rows, no stale stamps |
| R14 | Row-level source links | `tools/verify.py` | **982 rows, 982 with an official source link, 73 unverified rows keep blank cells** |
| R15 | Independent recomputation of published figures | `scripts/verified/audit_numbers.py` | **47 / 47 reproduce** |
| R16 | Hard data-integrity checks | `scripts/verified/validate_verified.py` | **All pass** |
| R17 | Unit tests | `python3 -m unittest discover -s tests` | **117 pass** |

---

## 4. Irregularities found

### C-A — Two of 32 standings rows are one game behind the live official table

**Severity: high (visible on the published dashboard). Independently confirmed, not new:**
flag F41 for this finding was already raised by session `9411723a` (PR #45) and session
`1e159b2e` reached the same 30-of-32 result by a separate transcription (its check N5). Three
independent checks now agree, which is worth more than any one of them.

The committed standings snapshot was taken before the Week 10 Thursday game. That game has since
finished (Commanders 24, Giants 21, final, per
[nfl.com](https://www.nfl.com/schedules/2026/by-week/week-10)). Two rows are therefore stale:

| Club | Field | Committed | Official, 2026-11-13 |
|---|---|---|---|
| NYG | W-L-T | 5-2-1 | **5-3-1** |
| NYG | PCT | 0.688 | **0.611** |
| NYG | PF / PA / NET | 182 / 172 / +10 | **203 / 196 / +7** |
| WAS | W-L-T | 2-5-1 | **3-5-1** |
| WAS | PCT | 0.313 | **0.389** |
| WAS | PF / PA / NET | 172 / 202 / −30 | **196 / 223 / −27** |

Every one of the other 30 clubs matches exactly, including the two clubs whose records look unusual
(LAC 0-8, MIA 1-7).

Affected files: `data/verified/standings_2026.csv` and `data/standings.csv`.

**Not silently corrected.** Both files are dated evidence records; editing them by hand would
destroy the thing that makes them evidence. The daily `collect-data` workflow re-scrapes. Published as flag **F41**, with the completed-fixture consequence added to its text.

**Consequence also visible on the dashboard:** the Week 10 own-lines table still lists WAS @ NYG,
which has now been played. Those lines were built before kick-off, so they are a legitimate
pre-game prediction, but the page now says so explicitly.

To settle it: re-run the collector and compare again.
Source: <https://www.nfl.com/standings/league/2026/REG>

### C-B — nfl.com publishes no depth chart at all

**Severity: medium (it bounds what the 2nd/3rd/4th-string requirement can ever be).**

<https://www.nfl.com/teams/kansas-city-chiefs/depth-chart> returns HTTP 404. The league does not
publish depth charts, so the 1st-to-4th string ladder can only come from the 31 clubs that publish
their own. Houston publishes none. Several clubs label their chart *unofficial*; the label is
carried through to the page. Published as flag **F42**.

### C-C — 16 depth-chart cells hold two players run together

**Severity: low, but they must not be guessed at.**

The club-chart transcription contains cells such as `Zaven Collins Baron Browning` (ARI, OLB, rank 1)
and `Cooper Kupp Rashid Shaheed` (SEA, WR, rank 1). These are almost certainly two co-starters whose
cells the scraper concatenated. They are **published verbatim and flagged**, never split, because
splitting them would invent a player. Names containing a lowercase particle (`Jordan van den Berg`)
are correctly excluded from this flag — that is one person. Published as flag **F43**.

### C-D — One line lists a backup and no starter

**Severity: low.**

PHI, defence, DT: the chart lists `Ty Robinson (2)` and no rank 1. That is a gap in the club's chart,
not an injury, so it is excluded from every deficiency count and published on its own.
Published as flag **F44**.

### C-E — Seven overlapping site generations

**Severity: high (reader confusion).**

The repository now publishes seven independently built site generations: the root dashboard, the
root section pages, `docs/`, `dashboard/`, `lab/`, `research/`, and the `referee/` and
`verified-lab/` sub-sites. They overlap and in places disagree. Only one (the root dashboard) is
rebuilt by the daily data workflow, so the other six can silently go stale. Published as flag
**F46**, question **Q21**, decision **D07**, suggestion **S17**.

### C-F — Prior findings confirmed, not re-opened

* The injury snapshot is **sound**. 296 rows, 26 clubs, 24/26 club counts identical with only the
  known `AZ`/`LA` vs `ARI`/`LAR` aliases differing, and 12/14 named rows matching field by field
  including position, injury, practice status and game status. The official page has not drifted
  materially since the 2026-11-12T23:37Z scrape. Published as flag **F45**.
* One row deserves a second look from a reviewer even though it matches the page: **DET Kerby Joseph
  is listed as "Full Participation in Practice" with a game status of "Out"**. That is what nfl.com
  publishes and the scrape is faithful; it is recorded here because "full practice but out" is
  unusual and a reviewer may want to see the original row.
  Source: <https://www.nfl.com/injuries/>

---

## 5. What this session changed

| File | Change |
|---|---|
| `pipeline/build_depth_ladder.py` | **New.** Joins official club depth charts to the official injury report and publishes the 1st-to-4th string ladder per club, per unit, per position |
| `data/depth_ladder.json` | **New.** 933 slots across 31 clubs; 4 lines started by a backup; 110 with an at-risk starter; 1 chart gap; 16 flagged cells |
| `pipeline/gen_site.py` | Category sidebar on every page; four new pages; overview refreshed; seven new flags; brief-coverage table corrected |
| `pages/depth.html`, `pages/correlations.html`, `pages/luck.html`, `pages/parlays.html` | **New pages** |
| `assets/style.css` | Additive sidebar / shell styles only; no existing rule touched |
| `pipeline/content.py` | Appended questions Q22–Q23, suggestions S16–S17, decision D07 (append-only) |
| `scripts/verified/normalize_nav.py` | **Cross-scope edit, logged here:** the canonical nav list was resynced with `pipeline/gen_site.py` so the two generators agree byte for byte, and labels are now HTML-escaped as the generator escapes them. Without this, whichever ran second silently rewrote the other's links |
| `COORDINATION.md` | Claim, results and hand-off notes |

## 6. Cross-scope changes another session owns — logged, not applied

1. **`tools/check_committed_site.py`** compares every page's "Data built" stamp with
   `data/model/dashboard.json`. The three research pages read from a committed extract that the
   daily refresh never rebuilds, so they will always look stale under that rule. This session did
   **not** weaken the gate; instead each of those pages now states its own extract time in the page
   body and carries the site stamp in its header. A cleaner fix would be an explicit exemption list,
   which is that tool owner's call.
2. **`normalize_nav.py`** was edited (see above) because the two generators write the same `<nav>`
   block on the same files and their lists had drifted apart. Recorded here so a reviewer can see
   exactly what changed and why.

## 7. Reproduction

```bash
python3 pipeline/build_depth_ladder.py     # rebuild data/depth_ladder.json
python3 pipeline/gen_site.py               # render index.html and pages/*.html
python3 scripts/verified/normalize_nav.py  # no-op on this generation's pages
python3 scripts/verified/check_site.py
python3 tools/check_committed_site.py
python3 tools/verify.py
python3 scripts/verified/audit_numbers.py
python3 scripts/verified/validate_verified.py
python3 -m unittest discover -s tests
```
