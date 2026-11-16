# Session `c84a41a4-nfl1` — repo audit

Read-only audit of the data layer, the writers and the gates that existed before this session.
Nothing in this document changed another session's files; defects are recorded and published on
`ledger/flagged.html` instead.

## 1. What was re-run, and what it said

| Gate | Result |
|---|---|
| `tools/build_site_all.py --check` | byte-identical after rebuild |
| `tools/check_reachability.py` | 177 pages, 177 reachable, 0 problems |
| `tools/check_generators.py` | every generated path has exactly one owner |
| `tools/verify.py` | 2,062 table rows, all with an official source link |
| `tools/verify_combined.py` | 2,533 local links, 0 broken |
| `tools/check_freshness.py` | 23 assertions |
| `tools/audit_official.py` | 905 checks, 0 failed, 65 flags |
| `room/verify.py` | pass |
| `scripts/verified/*` | check_site, audit_numbers, validate_verified all pass |
| `tools/check_committed_site.py` | pass |
| `tools/check_strength_site.py` | pass |
| `tools/check_reproducible.py` | pass |
| `tools/check_capture.py` | pass |
| `tests/` | 136 tests OK |

The repository was in good shape before this session. The audit found no broken gate.

## 2. Defects found in committed artifacts

### A. The depth-chart JSON cannot represent a shared slot  (`C84-F02`)

`data/session-1505ac8e/depth_charts.json` holds 934 slots and **zero** slots with more than one
rank-1 player:

```
slots=934  slots with >1 rank-1 player=0  slots with no rank-1=2  rank gaps=5
```

The live official charts do publish shared slots — Seattle's page renders
`Cooper Kupp` and `Rashid Shaheed` inside a single rank-1 cell, and the committed JSON stores that
as the single string `"Cooper Kupp Rashid Shaheed"` (verified this session against
<https://www.seahawks.com/team/depth-chart/>).

The brief states "149 club/unit/position slots list more than one rank-1 player". That number is
reproducible from neither the committed file (0) nor the parser's own merged-name counter
(16). What is true is that the brief's *concern* is real and the *count* is not, and that a parser
which merges the cell destroys exactly the information the brief asks for.

Two other structural gaps survive in the same file:

* Washington publishes a slot with no rank 2 (`Frankie Luvu` rank 1, `Kain Medrano` rank 3). The
  committed JSON reproduces the gap faithfully rather than closing it — confirmed against
  <https://www.commanders.com/team/depth-chart>.
* Philadelphia's DT slot begins at rank 2 (`Ty Robinson`). Also reproduced faithfully.

### B. 31 of 32 charts are undated  (`C84-F04`)

Only Green Bay ("Nov. 10, 2026") carries a club-published `as_of`. The rest have a blank. The brief
requires depth, availability and lineup evidence to be versioned against the last official roster
event; a chart with no club date cannot be versioned against anything but this repository's own
capture time.

### C. The brief's Baltimore claim no longer holds  (`C84-F01`)

The brief asserts Baltimore "still publishes Lamar Jackson and Tyler Huntley at QB after both went
on injured reserve". The live chart this session read lists:

```
QB  Jacoby Brissett | Joe Fagnano | Kedon Slovis
```

That is <https://www.baltimoreravens.com/team/depth-chart>. The stale-chart complaint is not
reproducible today. Any feature built on it would be built on a false premise, so it is flagged
rather than implemented.

### D. Two incompatible gate schemes  (`C84-F07`)

`data/s9cb/leaderboard.json` declares 8 gates (G1–G8, 200-bet floor, BH at 0.05).
This session registered 10 gates (C84-G1–G10, 300-bet floor, adds control-beating and
delete-the-best-season). Both are published; neither is declared canonical. A reviewer comparing
"gates passed" across pages is comparing different tests.

### E. The 136-game log is not the corpus  (`C84-F08`)

`data/verified/model/predictions_log.json` holds 136 rows for the 2026 season.
`data/s9cb/games.csv` holds 5,336 decided games for 2006–2026. Both are real; they are not the same
thing, and a result from one must never be quoted as if it came from the other.

### F. Stale injury rows still render elsewhere  (`C84-F05`, `C84-F06`)

The committed capture holds 347 rows, 28 clubs, 171 rows with a game designation. The brief's
"254 rows and 4 no-injury sections" and "6 of 254 rows carry a designation" are stale. Seattle
(15 rows) and Cincinnati (9 rows) both publish full sections, so any page still printing
"No Injuries Reported" for them is reading an older file. Those pages are outside this session's
scope and are listed for the owner.

## 3. Errors this session made, and how they were caught

Recorded as `C84-F09` because a verification page that lists only other people's mistakes is not a
verification page.

| # | Error | How it surfaced | Fix |
|---|---|---|---|
| 1 | The pre-registration text described the repository's S7 rule as "fade the road favourite" while also pointing at the repo's S07, which bets the **home** side. The sign convention was stated backwards. | Re-reading the raw numbers: home covers 222 of 401 when `spread_line <= -7`. | Registration left **unedited**; correction published as a flag. The rule was registered as its own rule (C84-S8) and is published with its real result (−11.66%). |
| 2 | The first implementation computed the moneyline probability as `Φ(−line/sd)` instead of the registered `Φ(line/sd)`, inverting every M3 probability. Brier came out 0.3141. | The Brier was absurdly bad next to the repo's independent run; investigating the sign found it. | Fixed to the registered formula; Brier 0.2255. |
| 3 | The first design matrix had `2n+3` columns indexed up to `4n`, so the fit raised `IndexError`. | The fit crashed on the first run. | Rewritten as the simple one-number-per-club strength model the brief asks for. |
| 4 | A flag said Cincinnati had 4 injury rows. | Recounting the committed capture: 9. | Corrected in place, with the correction noted in the flag text itself. |

## 4. What this session did not do

* Did not edit any other session's data file, generator output or page content, except two
  additive lines in `pipeline/gen_site.py` (one nav entry, one All Sections row) required by the
  repo-wide reachability gate, and the README template.
* Did not capture new snapshots over time: that is a scheduled Actions job, not a session action,
  and one capture cannot support backtesting.
* Did not build a prop price, an opening line, or a snap-count feed; none exists in any source
  reachable from here, and each is published as blocked with the action that would clear it.
* Did not claim any row is verified that was not read against an official page this session. The 12
  live re-checks are listed on `ledger/verification.html`.
