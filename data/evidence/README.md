# data/evidence — hand-transcribed official NFL pages

These files are the **ground truth** the rest of the repository is checked against.
They are transcribed by hand, line by line, from official NFL pages, and every row keeps
the URL it was read from. Nothing in this directory is computed, inferred or copied from
another dataset.

| File | Source | Rows | Read |
|---|---|---|---|
| `standings_2026.json` | <https://www.nfl.com/standings/league/2026/reg> | 32 clubs (W L T PF PA) | 2026-11-12 |
| `injuries_week10.json` | <https://www.nfl.com/injuries/> | 279 player rows across 26 club sections | 2026-11-12 |
| `schedule_week10.json` | <https://www.nfl.com/schedules/2026/REG10> | 14 games + 4 byes | 2026-11-12 |
| `depth_charts.json` | `https://www.chiefs.com/team/depth-chart`, `https://www.seahawks.com/team/depth-chart/` | 123 slots × player | 2026-11-12 |

Regenerate with `python3 tools/evidence_from_official.py`; check everything against it with
`python3 tools/verify_official.py`.

Known limits, stated rather than hidden:

* The league site returns **404** for `/teams/<club>/depth-chart` (checked on two clubs and
  recorded in `data/verified/depth_chart_probe.csv`). Club sites do publish depth charts, in
  string order, so `depth_charts.json` covers the two clubs read in this session only.
  Other clubs' depth charts are *not* in this file, and nothing is substituted for them.
* The injury page prints "No Injuries Reported" for LAC and BAL. That is recorded as a
  league statement, not as "0 injuries".
* Practice status is transcribed exactly as printed. A blank practice cell is left blank.
