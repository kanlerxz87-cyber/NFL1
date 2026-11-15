# Dated official-source audit — session `3738d9f0-nfl1`

**Audit recorded:** `2026-11-15T12:49:11Z` · **Outcome:** **PASS**

**Verifier:** [`tools/verify_audit_3738d9f0.py`](../tools/verify_audit_3738d9f0.py) · [Machine-readable result](../data/official/2026-11-15/official_audit_3738d9f0.json)

The standings, Week 11 schedule, and complete Week 10 injury transcription all match the read-only model snapshot. The audit records zero review flags and did not modify either model file.

## Official sources and capture boundary

- [2026 NFL league standings](https://www.nfl.com/standings/league/2026/reg) — both page chunks read; 32 team rows transcribed.
- [2026 Week 11 schedule](https://www.nfl.com/schedules/2026/by-week/week-11) — all three page chunks read; 13 fixtures captured in [`week11_schedule_2026-11-15.tsv`](../data/official/2026-11-15/week11_schedule_2026-11-15.tsv).
- [Official NFL injury report](https://www.nfl.com/injuries/) — page title identifies **Week 10 of the 2026 season**; all eight chunks were re-read on 2026-11-15. A complete same-day 347-row transcription is preserved in [`live_read_2026-11-15_week10.psv`](../data/brief_07810d9f/live_read_2026-11-15_week10.psv). Its accompanying [source delta metadata](../data/brief_07810d9f/injury_delta_2026-11-15.json) records the full read at `2026-11-15T12:18Z`.

The model targets are read-only: [`snapshot.json`](../data/model/snapshot.json) and [`official_injuries.json`](../data/model/official_injuries.json). The injury snapshot was refreshed at `2026-11-15T12:38:01+00:00` and contains 347 rows across 28 clubs. This audit compares the full same-day live transcription against that refreshed snapshot. The fetch tool exposes neither raw response bodies nor exact per-response timestamps; the row transcription and source metadata are saved, but raw HTML is not archived. Capture boundaries and timestamp details are also recorded in [`sources_audit_2026-11-15.json`](../data/official/2026-11-15/sources_audit_2026-11-15.json).

## Comparison results

| Dataset | Official rows transcribed | Read-only target | Result | Official source |
| --- | ---: | --- | --- | --- |
| Standings: W/L/T/PCT/PF/PA/NET | 32 | `data/model/snapshot.json` | **32/32 match; zero field mismatches** | [NFL league standings](https://www.nfl.com/standings/league/2026/reg) |
| Week 11 schedule: matchup/date/kickoff ET/network | 13 | `data/model/snapshot.json` fixtures | **13/13 match; zero field mismatches** | [NFL Week 11 schedule](https://www.nfl.com/schedules/2026/by-week/week-11) |
| Week 10 injury report: player/position/injury/practice/game status | 347 | `data/model/official_injuries.json` | **347/347 team-player keys and all four fields match; zero key or field mismatches** | [NFL injury report](https://www.nfl.com/injuries/) |

The row totals are independently derived from the saved official transcriptions, not assumed from model metadata. The complete injury row-level comparison found no live-only or model-only keys and no mismatches in position, injury, practice status, or game status. The existing [`12-row source-linked spot check`](../data/official/2026-11-15/injury_spotchecks_2026-11-15.tsv) is retained as a smaller supplemental capture; all twelve rows are also covered by the full comparison.

The standings league totals balance at W=136, L=136, T=2, PF=6291, PA=6291. The official standings/schedule capture uses `AZ` for Arizona while the model uses `ARI`; the injury capture uses `AZ` for Arizona and `LAR` for the Rams while the model uses `ARI` and `LA`. These aliases are applied only to comparison keys; original source codes remain unchanged in their captures.

## Verification and no-mutation boundary

Run:

```text
python3 tools/verify_audit_3738d9f0.py
```

The offline verifier reports **PASS** for 32/32 standings, 13/13 schedule rows, and 347/347 complete injury rows, with zero review flags. It checks capture provenance, row-key coverage, all compared fields, the selected spot-check links, and input hashes. It does not fetch NFL pages. Neither existing model file was edited; no shared site pages, tables, generators, or navigation were changed.
