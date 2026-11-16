# Session `414a54c9-nfl1` — official-source re-check artifacts (2026-11-16)

Every file in `official_2026-11-16/` is a verbatim transcription of what the official page
printed when it was read this session (2026-11-16, UTC). Nothing is inferred, rounded or
filled in. Where the repo's published copies are older, the difference is published as a
dated delta in `recheck_2026-11-16.json`, not overwritten.

| File | Rows | Official source | Read |
|---|---|---|---|
| `official_2026-11-16/standings.tsv` | 32 | <https://www.nfl.com/standings/league/2026/REG> (2 chunks) | 2026-11-16T14:35–14:40Z |
| `official_2026-11-16/week10_results.tsv` | 14 (13 FINAL, 1 scheduled) | <https://www.nfl.com/schedules/2026/REG10> (2 chunks) | 2026-11-16T14:36–14:40Z |
| `official_2026-11-16/week11_schedule.tsv` | 13 | <https://www.nfl.com/schedules/2026/by-week/week-11> (chunks 0–1 of 3) | 2026-11-16T14:38–14:40Z |
| `recheck_2026-11-16.json` | 32 + 14 + 13 + 13 rows compared | comparisons vs the repo's committed files | 2026-11-16 |

## Arithmetic self-checks (all passed at write time)

- sum of `pf` equals sum of `pa` across the 32 standings rows;
- `net_pts` = `pf` − `pa` on every row;
- printed `pct` equals (W + 0.5·T) / games to ±0.001 on every row;
- Week-10 finals reconcile with the repo snapshot deltas (12 Sunday games × 2 teams = the 24
  changed rows in `what_changed_week9_to_week10`; WAS@NYG was already in the snapshot because
  it was played Thursday 2026-11-12).

## What the re-check found

1. **Standings (32/32 rows read).** The repo's two dated copies
   (`data/model/snapshot.json`, generated 2026-11-15T17:42Z, and
   `data/verified/standings_2026.csv`, retrieved 2026-11-12T04:31Z) agree with each other on
   every team and both predate the 13 Week-10 finals. 24 teams' records changed between the
   repo snapshot and the official page today. Published as a dated delta
   (`what_changed_week9_to_week10`), matching the brief's "publish the delta, never the level"
   rule. Flag F68.
2. **Week-10 results (14 rows).** 13 games FINAL on the official page. The frozen backtest
   corpus (`data/s9cb/games.csv`, sha-pinned by `data/prereg/corpus.json`) carries blank scores
   for those 13 by design — results were unpublished at registration and the corpus may not be
   edited. The results are recorded here as the separately labelled record the pre-registration
   plan calls for. Flag F69. LAC @ BAL (MNF, 2026-11-16 8:15 PM ET) was not played at read
   time and is recorded as SCHEDULED with blank scores.
3. **Week-11 schedule (13 rows).** 13/13 fixtures match
   `data/prereg/official/week11_2026_schedule.json` (team pairs and game URLs). MIN @ SF is
   confirmed as the Mexico City international game.
4. **Injury report spot-check (13 rows).** Read chunk 0 of 8 of
   <https://www.nfl.com/injuries/league/2026/reg10> and compared row by row against the
   committed 347-row capture: 13/13 game-status cells match. Re-confirms the CAP-04 finding
   (Kerby Joseph, Cade Mays, D.J. Reed are officially **Out**) and the X-POS note (Ben Brown
   is listed at **C** on the report).

## Method boundary

Transcriptions come from the `fetch_page` text rendering of the official pages. Rows keep the
exact printed values. Any value not printed by the official page is left blank in these files.
