# Post-merge audit — session `b6e68100-nfl1` (2026-11-12)

Independent line-by-line review of the repository as found at `c09c739` (plus everything merged
to `main` through `5768d16` during the audit). Every claim below was checked against an official
source on 2026-11-12 unless it is a repo-internal check, and every check that produced a number
is reproducible from the named tool.

## 1. What was audited

| Area | Method | Result |
|---|---|---|
| Analysis layer (`analysis/*.py`) | Re-ran all four scripts; compared every regenerated artifact with the committed one | Byte-identical except the intended C5 fix (see §2). The verified model layer is reproducible. |
| Verified-data gate | `scripts/verified/validate_verified.py` | PASS (all hard checks, including "captured games never contradict official standings") |
| Published numbers | `scripts/verified/audit_numbers.py` | 44 independent recomputations reproduce every published figure |
| Site links & nav | `scripts/verified/check_site.py` | 20 pages, all local links resolve, navigation complete |
| Root dashboard rows | `tools/verify.py` | 965 table rows, 965 with an official source link, 73 deliberately blank/unverified, 0 broken links |
| Combined data | `tools/verify_combined.py` | 32+32 standings, 20 injury rows, 32 team rows, 136 games recomputed, 1,187 links — PASS |
| Test suite | `python3 -m pytest tests/` / `unittest discover` | 107 tests pass (111 after PR #21's additions on the rebased base) |
| Referee findings | Re-verified the referee's C5 claim against official standings and data | Confirmed and fixed (§2) |

## 2. Fixed during this audit (verified against official sources before changing anything)

### A1 — C5 correlation used the bare division name (referee request, hand-off from `25aa7696`)

`analysis/correlations.py` built its division map from the `division` column alone. AFC East and
NFC East both publish as "East", so games like AZ @ LAC were counted as intra-division. Weeks 1–9
therefore showed **52 division games; the official groupings give 42**.

- Fix: key the map on `(conference, division)`.
- **Official verification before recomputing:** all 32 club-division assignments were compared
  line by line against <https://www.nfl.com/standings/division/2026/REG> (fetched 2026-11-12):
  32/32 match, 0 mismatches.
- Recomputed C5: **r = -0.1048** (n=136, 95% CI [-0.268, +0.065], p=0.2245) — matches the referee
  session's independent value exactly.
- Propagated to `data/verified/model/correlations.json` and `pages/analysis.html`; referee flag
  **F36 marked resolved** in `data/flags.json`.

### A2 — Winning-percentage rounding convention

The pipeline computed winning percentage with float `.round(3)`, which is banker's rounding:
WAS (2-5-1) = 0.3125 → **0.312**, while the official page publishes **0.313**
(<https://www.nfl.com/standings/league/2026/reg>, and the hand-transcribed
`data/verified/standings_2026.csv` correctly shows 0.313). Fixed in `pipeline/build_all.py` with
exact integer arithmetic (round-half-up); the refreshed `data/model/snapshot.json` lands via the
`collect-data` workflow, which runs automatically on a push touching `pipeline/`.
The stale 0.312 never rendered on any live page (`pages/standings.html` and the verified-data
pages read the hand-transcribed 0.313), so this was a latent pipeline defect, not a published error.

### A-F01 — `COORDINATION.md` line-1 artifact

The board file began with the stray text `EAD` — a leftover conflict-resolution artifact from an
earlier merge. Removed in the claim commit.

### A-F03 — Week-10 injury-report club coverage is now fully explained (supersedes the uncertainty in F11)

The Week-10 official report has 26 club tables. This audit explains every absent club from the
official source itself:

| Absent club | Why (official source) |
|---|---|
| CHI, DEN, PHI, TB | On bye in Week 10 — <https://www.nfl.com/schedules/2026/by-week/week-10> (transcribed in `data/verified/byes_2026.csv`) |
| LAC, BAL | Monday game; the official page prints "No Injuries Reported" for both clubs — <https://www.nfl.com/injuries/> |

So absence-of-rows no longer conflates "on bye", "no injuries reported" and "scrape failure".
F11 remains accurate for its own scrape moment; A-F03 records the current, fully explained state.

### A-F04 — The official injury page drifts within hours; the site is a dated snapshot

Comparing the 18:53 UTC scrape (`html_sha256 54558c9f…`, 276 rows) with the 22:30 UTC scrape on
`main` (279 rows) and with the live page fetched during this audit:

- IND: statuses changed for Haulcy, Taylor, Tillery, Ward and two rows were added (CJ Allen,
  Grover Stewart).
- JAX: one row added (BJ Green II, DE, full participation).

The scraper is faithful — 20+ club tables were compared row-for-row against the live page during
the audit (~120 rows across WAS, NYG, NE, DET, KC, LV, SF, DAL, PIT, CIN, ATL, MIN, GB, TEN, CAR,
MIA, NYJ, NO and partials), 0 scrape errors found. The drift is the official page updating during
the day. Consequence for decision-making: pre-slate reads should re-scrape shortly before kickoff;
the daily 11:17 UTC refresh alone is not enough on game day.

### Verified non-issue (checked so it never gets falsely flagged)

The official Week-10 injury page lists Myles Garrett (LB) and Trent McDuffie (CB) under the Rams,
and several players under clubs they are not traditionally associated with. Before treating this
as an official-page defect, the audit checked the player's own official page:
<https://www.nfl.com/players/myles-garrett/> states **Los Angeles Rams**, and NFL.com news
confirms the trade and his activation from IR. The injury page is internally consistent; no flag.

## 3. Structural observation for reviewers (no action taken)

The repo intentionally carries four site generations (root dashboard from `pipeline/gen_site.py`,
verified-data pages from `scripts/verified/build_site.py`, `docs/` from `tools/build_docs_site.py`,
`verified-lab/` and `referee/` sub-sites). Two generators write shared paths:

- `pipeline/gen_site.py` and `scripts/verified/build_site.py` both write `pages/lines.html`
  (build_site wins in the CI order, and that is the committed state).
- `tools/build.py` also writes a root `index.html` and `README.md` belonging to a different
  generation. Running it verbatim clobbers the canonical `index.html` ("NFL Decision Lab") and the
  session-documented `README.md`. This audit regenerated the root companion pages with
  `tools/build.py` and then restored `index.html` and `README.md` from the canonical generation.
  Recommendation (logged on the Suggestions page as SA-01): split `tools/build.py`'s output paths
  or add a guard so the two generations cannot overwrite each other.

## 4. Official sources used by this audit (all fetched 2026-11-12)

| Source | Used for |
|---|---|
| <https://www.nfl.com/standings/division/2026/REG> | Division groupings for all 32 clubs (A1 verification) |
| <https://www.nfl.com/standings/league/2026/reg> | 32 club rows (W-L-T, PF, PA) compared with `data/model/snapshot.json` — 32/32 match; WAS pct rounding difference found |
| <https://www.nfl.com/injuries/> | Week-10 report, ~120 rows compared row-for-row; club-coverage explanation; drift detection |
| <https://www.nfl.com/players/myles-garrett/> | Confirmed Rams roster membership (non-issue) |
| <https://www.nfl.com/schedules/2026/by-week/week-10> | Bye clubs CHI, DEN, PHI, TB (via committed transcription) |
| <https://github.com/nflverse/nflverse-data> | Mirrored feeds (pinned by URL + sha256 in `data/model/provenance.json`) |

## 5. Status

- A1 (C5 hand-off): **done** — fixed, verified, propagated, F36 resolved.
- A2 (post-merge audit): **done** — this document, flags A-F01…A-F04, all gates green.
- A3 (PR, merge, Pages confirmation): recorded in `COORDINATION.md` after the merge.
