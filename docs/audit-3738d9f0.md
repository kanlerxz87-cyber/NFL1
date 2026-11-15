# Dated official-source audit — session `3738d9f0-nfl1`

**Audit recorded:** `2026-11-15T12:36:03Z` · **Verifier:** [`tools/verify_audit_3738d9f0.py`](../tools/verify_audit_3738d9f0.py)

**Outcome:** **PASS WITH REVIEW** — the standings and Week 11 schedule comparisons pass; the Week 10 injury audit remains deliberately partial and is not reported as a full 345-row match.

## Official sources

- [2026 NFL league standings](https://www.nfl.com/standings/league/2026/reg) — both page chunks read; 32 team rows transcribed.
- [2026 Week 11 schedule](https://www.nfl.com/schedules/2026/by-week/week-11) — all three page chunks read; 13 fixtures captured in [`week11_schedule_2026-11-15.tsv`](../data/official/2026-11-15/week11_schedule_2026-11-15.tsv).
- [Official NFL injury report](https://www.nfl.com/injuries/) — all eight page chunks read; page title identifies **Week 10 of the 2026 season**. Twelve individual rows were transcribed for the spot check below. The raw page body was not retained, and the remaining rows were not fully transcribed.

The exact response time and raw HTML were not exposed by the page-fetch tool. The timestamp above is the audit-record timestamp, not a claimed HTTP response instant. Per-row source links are preserved in each TSV. The dated source metadata and collection boundary are in [`sources_audit_2026-11-15.json`](../data/official/2026-11-15/sources_audit_2026-11-15.json).

## Comparison result

| Dataset | Source rows captured | Read-only target | Result | Official source |
| --- | ---: | --- | --- | --- |
| Standings: W/L/T/PCT/PF/PA/NET | 32 | `data/model/snapshot.json` | **32/32 match; zero field mismatches** | [NFL league standings](https://www.nfl.com/standings/league/2026/reg) |
| Week 11 schedule: matchup/date/kickoff ET/network | 13 | `data/model/snapshot.json` fixtures | **13/13 match; zero field mismatches** | [NFL Week 11 schedule](https://www.nfl.com/schedules/2026/by-week/week-11) |
| Week 10 injury rows | 12 selected rows | `data/model/official_injuries.json` (generated `2026-11-14T17:02:31+00:00`, 345 rows) | **12/12 match; 333 model rows not independently checked against the live page** | [NFL injury report](https://www.nfl.com/injuries/) |

The injury line above is intentionally a **spot check**, not a complete live-report audit. Although all eight page chunks were read, the tool did not expose a persistent raw capture and I did not independently transcribe every live row. The model file's 345 rows are a property of that saved model snapshot, **not** a separately recounted total for the live page on 2026-11-15. The 333 unverified model rows remain flagged for review; no values are filled in or assumed from them.

## Injury spot-check rows

Each row below was read from the official Week 10 report and compared field by field with the corresponding saved model row. The player link and report link are both official NFL sources.

| Club | Player | Position | Injury label | Practice status | Game status | Official row sources |
| --- | --- | --- | --- | --- | --- | --- |
| WAS | Lucas Patrick | C | Concussion | Did Not Participate In Practice | Out | [Player](https://www.nfl.com/players/lucas-patrick/) · [Report](https://www.nfl.com/injuries/) |
| WAS | Colson Yankoff | TE | Knee | Did Not Participate In Practice | Out | [Player](https://www.nfl.com/players/colson-yankoff/) · [Report](https://www.nfl.com/injuries/) |
| NYG | Malik Harrison | LB | Groin | Limited Participation in Practice | Questionable | [Player](https://www.nfl.com/players/malik-harrison/) · [Report](https://www.nfl.com/injuries/) |
| NE | Ben Brown | C | Knee | Did Not Participate In Practice | Out | [Player](https://www.nfl.com/players/ben-brown-2/) · [Report](https://www.nfl.com/injuries/) |
| NE | Carlton Davis III | CB | Knee | Did Not Participate In Practice | Out | [Player](https://www.nfl.com/players/carlton-davis/) · [Report](https://www.nfl.com/injuries/) |
| NE | TreVeyon Henderson | RB | Illness | Did Not Participate In Practice | Out | [Player](https://www.nfl.com/players/treveyon-henderson/) · [Report](https://www.nfl.com/injuries/) |
| DET | Kerby Joseph | S | Knee | Did Not Participate In Practice | Out | [Player](https://www.nfl.com/players/kerby-joseph/) · [Report](https://www.nfl.com/injuries/) |
| DET | Cade Mays | C | Ankle | Did Not Participate In Practice | Out | [Player](https://www.nfl.com/players/cade-mays/) · [Report](https://www.nfl.com/injuries/) |
| DET | D.J. Reed | CB | Hip | Did Not Participate In Practice | Out | [Player](https://www.nfl.com/players/d-j-reed/) · [Report](https://www.nfl.com/injuries/) |
| SEA | Sam Darnold | QB | Ribs, Quadricep | Did Not Participate In Practice | Out | [Player](https://www.nfl.com/players/sam-darnold/) · [Report](https://www.nfl.com/injuries/) |
| NE | A.J. Brown | WR | Ankle, Knee | Limited Participation in Practice | Questionable | [Player](https://www.nfl.com/players/a-j-brown/) · [Report](https://www.nfl.com/injuries/) |
| NE | Kevin Byard | S | Chest | Full Participation in Practice | Questionable | [Player](https://www.nfl.com/players/kevin-byard/) · [Report](https://www.nfl.com/injuries/) |

The 12-row machine-readable capture is [`injury_spotchecks_2026-11-15.tsv`](../data/official/2026-11-15/injury_spotchecks_2026-11-15.tsv). Blank injury-report cells elsewhere remain blank; no designation was inferred from practice status or news.

## Code conventions and no-mutation boundary

The NFL standings/schedule capture uses `AZ` for Arizona, while the repository model uses `ARI`. The source file preserves `AZ`; the offline verifier applies the explicit `AZ` → `ARI` mapping only when joining rows. The NFL bye list prints `LAR` while its adjacent Rams logo asset uses `LA`; the captured note preserves that source distinction. Neither existing model file was modified.

Run:

```text
python3 tools/verify_audit_3738d9f0.py
```

The saved result is [`official_audit_3738d9f0.json`](../data/official/2026-11-15/official_audit_3738d9f0.json), including per-check results, mismatch lists, input hashes, and the non-blocking injury coverage flag. This verifier is offline: it validates the saved row captures and comparisons; it does not fetch NFL pages. The two full comparisons pass. The incomplete live injury row coverage remains a published review item, not a silent PASS.
