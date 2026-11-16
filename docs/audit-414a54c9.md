# Audit — session `414a54c9-nfl1` (2026-11-16, UTC)

Branch `arena/414a54c9-nfl1`, base `32a8fffe` (= `main` at session start). Claim and scope:
`COORDINATION.md`, session block Z1–Z5. This document is the line-by-line record the brief
asks for: what was checked, against which official source, what was found, and what is
flagged rather than fixed.

## 1. Takeover integration of seven stale PRs (Z2)

All seven open PRs were hours-to-days old with no new commits and were `CONFLICTING` with
`main`, so under the board's 60-minute stale-claim rule this session took them over. Nothing
was deleted: each PR's content is on the branch, and each PR is closed with a pointer.

| PR | Session | Content taken | Resolution |
|---|---|---|---|
| [#59](https://github.com/kanlerxz87-cyber/NFL1/pull/59) | `edbb28da` | `docs/audit-edbb28da.md`, board record | added verbatim |
| [#57](https://github.com/kanlerxz87-cyber/NFL1/pull/57) | `65df4799` | PR #53 merge record | union-appended to COORDINATION.md |
| [#79](https://github.com/kanlerxz87-cyber/NFL1/pull/79) | `48ab654c` | `policy/official-injury-data-publication-policy-48ab654c.md` (the F51 terms audit), heartbeat line, board record | policy kept; the request to link NFL Terms in F51's source cell is applied (F51 now carries `data_src: S35`) |
| [#47](https://github.com/kanlerxz87-cyber/NFL1/pull/47) | `cf97db19` | official-roster **Backup Register**: `tools/scrape_rosters.py`, `tools/build_backup_register.py`, `data/backup-register/`, `pages/backup-register.html`, workflow | page reachable via nav; its four page-flags moved into the global register (F70–F73, request R-cf97db19-03) |
| [#80](https://github.com/kanlerxz87-cyber/NFL1/pull/80) | `c84a41a4` | pre-registered origination study + **Origination Ledger** sub-site (`ledger/`, `data/session-c84a41a4/`, `s9cb/c84_*.py`) | `ledger/verify.py` PASS; `ledger/check_registration.py` OK (registration C84-PREREG-1 unchanged) |
| [#77](https://github.com/kanlerxz87-cyber/NFL1/pull/77) | `57c05555` | faithful depth parsing (`pipeline/depth_parse.py`, `data/depth_raw/`, `data/depth_parsed/`), immutable availability ledger (`data/ledger/`, `pipeline/ledger.py`), rebuilt Week-10 injury filings (`data/verified/injury_report_2026_week10.tsv`, 347 rows) | `tools/check_depth_parse.py` PASS (6 captures, 289 names, 2 shared groups, 55 numbers stripped, 1 gap recorded); `tools/build_site_all.py` steps unioned with `55dc53f4`'s shadow steps (both kept) |
| [#81](https://github.com/kanlerxz87-cyber/NFL1/pull/81) | `55dc53f4` | generated-page rebuild repair | superseded: `main` already passed `build_site_all.py --check` at session start; closed with that evidence |

Conflict-resolution rules used throughout: `COORDINATION.md` union (no session record
discarded); generated pages and dated evidence taken from `main`'s fresher copies and
rebuilt from source; append-only logs (`heartbeat.jsonl`) unioned with de-duplication;
code conflicts merged semantically (`tools/build_site_all.py` kept **both** sessions' build
steps). The parallel session `bf0e6e5f` merged PRs [#89](https://github.com/kanlerxz87-cyber/NFL1/pull/89) /
[#90](https://github.com/kanlerxz87-cyber/NFL1/pull/90) into `main` during this session;
`origin/main` was merged in, and their `verify_dashboard` blank-market fix was kept over
this session's equivalent draft (theirs is stricter; no work discarded).

## 2. Defects fixed (integration fixes, logged)

1. **`tools/build_dashboard.py` — "Model (away)" column printed the market away.**
   The row builder passed `-mk` (negated *market* home) into the column labelled
   *Model (away)*; e.g. IND @ HOU showed −10.0 where the model's away view is −5.7. Fixed to
   `-my`. The TB @ DET row (market not yet published) now shows model away −2.4 with the
   market cells blank. This is a data-fidelity fix: a market number was mislabelled as model
   output.
2. **`tools/verify_dashboard.py` vs unpublished markets.** The numeric parser rejected the
   correctly-blank TB @ DET row. `bf0e6e5f` fixed the same failure on `main` (kept); the gate
   now requires blank market cells exactly when the data has no market line and never accepts
   a number where the data has none.
3. **Nav/generator registration for integrated sub-sites.** `Backup Register` and
   `Origination Ledger` added to `pipeline/gen_site.py` NAV and mirrored in
   `scripts/verified/normalize_nav.py` CANON (PRs #47/#80 each touched only one list);
   `tools/check_generators.py` now records ownership for `pages/backup-register.html`
   (`tools/build_backup_register.py`) and `ledger/*.html` (`ledger/build.py`).
4. **F51 source traceability** (request of `48ab654c`): the F51 source cell now links S35
   (NFL.com Terms) directly via the renderer's `data_src` field, keeping S01 for the scrape
   context.

## 3. Fresh official-source re-verification (Z3, 2026-11-16)

Method and rows: `data/session-414a54c9/README.md`. Every checked row carries its official
URL and read time; values not printed by the official page stay blank.

| Check | Rows | Result |
|---|---|---|
| Standings vs <https://www.nfl.com/standings/league/2026/REG> | 32 | 32/32 read; arithmetic self-checks pass (ΣPF=ΣPA, net=PF−PA, pct consistent); 24 teams' records changed since the repo's dated snapshot — published as a delta (F68) |
| Week-10 results vs <https://www.nfl.com/schedules/2026/REG10> | 14 | 13 FINAL + LAC @ BAL scheduled (MNF tonight); the frozen corpus carries blank scores by policy (F69); results recorded as the separately labelled record |
| Week-11 schedule vs <https://www.nfl.com/schedules/2026/by-week/week-11> | 13 | 13/13 fixtures match `data/prereg/official/week11_2026_schedule.json`; MIN @ SF confirmed Mexico City |
| Injury report spot-check vs <https://www.nfl.com/injuries/league/2026/reg10> (chunk 0/8) | 13 | 13/13 game-status cells match the committed 347-row capture; CAP-04 re-confirmed (Joseph/Mays/Reed **Out**); Ben Brown C-vs-G re-confirmed (F71) |

## 4. Gate results on the integrated tree (all green)

`tools/build_site_all.py --check` · `tools/verify.py` (2,111 rows, all source-linked) ·
`tools/verify_combined.py` (3,105 links, 0 broken) · `tools/check_reproducible.py` ·
`tools/check_committed_site.py` · `tools/check_freshness.py` (23 assertions) ·
`tools/verify_dashboard.py` (450 assertions) · `tools/verify_official.py` ·
`scripts/verified/audit_numbers.py` (47/47) · `scripts/verified/check_site.py` ·
`scripts/verified/validate_verified.py` · `scripts/verified/check_source_audit.py` ·
`tools/check_generators.py` · `tools/check_reachability.py` (0 problems) ·
`tools/check_preregistration.py` · `tools/check_preregistration_d4027.py` ·
`tools/check_scraper_pins.py` · `tools/check_scrape_drift.py` · `tools/check_depth_register.py` ·
`tools/check_capture.py` · `tools/check_strength_site.py` · `room/verify.py` ·
`prereg/verify.py` · `ledger/verify.py` · `strat/verify.py` · `pytest tests/` (255 passed).
Non-blocking: `tools/audit_official.py` reports the known 23 official-page
self-contradiction rows (carried over from earlier sessions).

## 5. Irregularities flagged (published, none blocking)

F68 (dated standings drift), F69 (corpus blank scores by policy), F70 (depth-source gap),
F71 (Ben Brown C vs G), F72 (Kerby Joseph Out vs PUP), F73 (three clubs' roster rows not
re-read) — appended to `data/flags.json`, published on the Flagged for Review page.

## 6. Manual-review links

- Official standings: <https://www.nfl.com/standings/league/2026/REG>
- Official Week 10 results: <https://www.nfl.com/schedules/2026/REG10>
- Official Week 11 schedule: <https://www.nfl.com/schedules/2026/by-week/week-11>
- Official Week 10 injury report: <https://www.nfl.com/injuries/league/2026/reg10>
- NFL.com Terms (F51): <https://www.nfl.com/legal/terms/>
- Session artifacts: `data/session-414a54c9/` (README + three TSVs + recheck JSON)
- Terms audit taken over from PR #79: `policy/official-injury-data-publication-policy-48ab654c.md`
