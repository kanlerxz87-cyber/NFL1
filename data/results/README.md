# 2026 official results: re-verification (session 9a1c5fa6-nfl1, read 2026-11-16 UTC)

**What is here**

| File | What it is |
|---|---|
| `official_read_2026-11-16.tsv` | One row per game as printed on the official nfl.com week pages, Weeks 1-10. Column 7 is the exact header text each score was read from; column 8 is the game page. |
| `official_records_week10_2026-11-16.tsv` | The season record printed beside each club on the Week 10 page. |
| `official_results_2026.csv` | The comparison: each official final game, whether it matches `data/verified/games_2026.csv`, and the official link. |
| `RESULTS_2026_VERIFIED.md` | The same table, readable on GitHub, with a link on every game row. |
| `verification_2026-11-16.json` | Counts, every check, every gap, the record check. |
| `flags_R1.json` | Four items for review (F-R1-01 to F-R1-04). |

**How to re-run:** `python3 tools/check_results_official.py` (the test `tests/test_results_official.py` runs it too).

**Result on 2026-11-16:** 149 official final games read (Weeks 1-10, with one Week 10 game still scheduled).
136 of 136 rows in `games_2026.csv` match the official pages exactly (score and date). 13 official Week 10 finals are
not yet in that file (flag F-R1-01). All 32 clubs' printed records equal the wins, losses and ties computed from the
official scores. Three Week 10 margins were also checked against each game's official Game Center page.

**What this does not cover:** seasons before 2026, not yet tested (F-R1-03); the Monday Week 10 game (F-R1-02); the terms question (F-R1-04).

**Method, stated plainly:** the official pages were read with the page-reading tool and the values were typed into
the TSV. The script does not fetch anything. Every value is then checked by the programmatic checks listed in the
script's docstring (header vs. columns, URL vs. clubs, date vs. header, the records check, and the comparison). The
comparison is the independent check, because `games_2026.csv` was built earlier from a different transcription.
