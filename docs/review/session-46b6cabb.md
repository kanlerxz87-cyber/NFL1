# Post-merge audit — session `46b6cabb-nfl1`

**Date:** 2026-11-13 (UTC)  
**Branch/base:** `arena/46b6cabb-nfl1`, branched from `09c03f052aa3bebb62acc23cb17eefd65f0c512e`  
**Scope:** repository README generation safety, committed-site integrity checks, live-page currency spot-check. This report distinguishes static-site/link checks from fresh source-value verification; it does not claim every historical value was freshly re-transcribed today.

## Executive result

The main static site is reachable and its committed build passes local structure, source-link, internal-link, data reconciliation, and unit-test checks. This audit found two actionable documentation/operations issues:

1. **The published overview is stale after the Week 10 Thursday game.** Its build stamp is `2026-11-12T23:37:56+00:00`; it still lists WAS @ NYG as a future matchup with pregame lines. The official NFL schedule now says **Commanders 24, Giants 21, FINAL**. The overview is therefore not safe to use as a current slate without checking the NFL schedule. The current site already carries freshness flags/suggestions (F39/F40, S13/S24, and the pre-slate refresh suggestion); this observation is evidence that the risk recurred, not a newly verified NFL injury or betting fact.
2. **The README generator is unsafe and the README inventory claims are stale.** `tools/build.py`'s `write_readme()` replaces the whole hand-maintained README with a shorter embedded template. That template says the same stale counts and ends by calling the verified-lab pointer transient. The function docstring incorrectly claims the template is byte-identical to the current README. A separate open PR #31 also changes `README.md` and `tools/build.py`; to avoid editing another active session's scope, this session records the issue and requests that owner to include the safe-template fix. No code change to these files is retained here.

Unverified values remain unfilled. No betting strategy is promoted: the live page itself reports **0 of 12 strategies passing all eight gates**.

## Official-source live check

- [Official NFL Week 10 schedule](https://www.nfl.com/schedules/2026/by-week/week-10) — fetched during this audit. The page identifies the Thursday, November 12 game as “Commanders 24, Giants 21, FINAL.”
- [Official 2026 NFL league standings](https://www.nfl.com/standings/league/2026/reg) — fetched during this audit. The page reflects the postgame records (NYG 5-3-1 and WAS 3-5-1). The published dashboard snapshot, generated before kickoff at 23:37 UTC on November 12, shows the prior 5-2-1 and 2-5-1 records and lists the game among 14 upcoming matchups.
- [Published site overview](https://kanlerxz87-cyber.github.io/NFL1/) — fetched during this audit. It retains the November 12 23:37 UTC build stamp, a future WAS @ NYG line row, the 136-game pregame sample, and the previous standings state. These observations establish page staleness against the official schedule; they do not validate the model lines or any price.

**Disposition:** flag for review as a freshness incident and preserve the existing official-source links. The static build stamp and official final result make the finding reproducible. A source refresh is required before replacing the snapshot; this audit does not invent postgame odds, injury statuses, or new values. The root shared flag/data/render artifacts were not edited because this session's scope did not own those shared outputs. See existing flags **F39/F40** and suggestions **S13/S24** in the site's [Flagged for Review](https://kanlerxz87-cyber.github.io/NFL1/flagged.html) and [Suggestions](https://kanlerxz87-cyber.github.io/NFL1/suggestions.html) pages.

## Automated checks run

Commands were run from the repository root on the base tree before this session's README-only changes:

| Check | Result | What it establishes |
|---|---:|---|
| `python3 tools/check_committed_site.py` | PASS — 21 pages, 482 internal links, 33 source tables / 791 rows with HTTPS source links | Committed-site link/table-source structure. Ten pages lack current build stamps and are reported as earlier-generator pages (F19); the check permits these. |
| `python3 tools/verify_combined.py` | PASS — 32/32 standings, 20/20 companion injury rows, 32/32 teams, 32/32 verified standings, 6/6 verified injuries, 136 official game rows recomputed with zero mismatches; 1,174 local links, zero broken | Local snapshot reconciliation, not a fresh transcription of every historical NFL value. |
| `python3 tools/verify.py` | PASS — 982 rows checked, 982 with allow-listed official links, 73 explicitly unverified, zero broken internal links | Explicit data tables on the verifier's declared 15-page subset. It writes `data/verification_report.json`; the generated counts differed from the previously committed report (1,013 rows). |
| `python3 -m unittest discover -s tests -v` | PASS — 117 tests | Existing regression suite on the base tree. |

`verify.py` and `verify_combined.py` update their JSON reports when run. Their outputs were restored after the check so this audit does not silently rewrite shared verification data. `check_committed_site.py` reports **791** source-linked rows in its scope while `verify.py` reports **982** across its `data-table` scope; these are different scopes, not interchangeable totals. The persisted report count differences should be reconciled by the owning integration/generator task.

## Changes in this session

- Added this source-linked post-merge audit report.
- Logged the README/template issue for the owner of open PR #31 rather than retaining overlapping edits.
- No NFL values, injuries, odds, model outputs, README content, or shared generated pages were changed.

## Remaining follow-up

1. Add a staleness gate tied to the last completed game / current official schedule, not only a static build timestamp; prevent already-completed games from remaining in the upcoming slate.
2. Reconcile the persisted verification report counts against the declared page/table scopes and regenerate only through the owning data/render pipeline.
3. Re-run the official injury-report audit on the refresh that consumes the postgame schedule. Keep unavailable or unmatched entries blank and flagged.
