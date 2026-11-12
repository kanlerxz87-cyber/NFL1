# Repo audit — line by line

Reviewed 2026-11-12 (UTC) on branch `arena/80731db4-nfl1` at base commit `5aeb599`.

| Line | What was checked | Result | Official source |
| --- | --- | --- | --- |
| 1 | Tracked files at start | `README.md` only | [repo](https://github.com/kanlerxz87-cyber/NFL1) |
| 2 | README content | One line: `# NFL1` | [repo](https://github.com/kanlerxz87-cyber/NFL1) |
| 3 | Git history | One commit `5aeb599 Initial commit` | [repo](https://github.com/kanlerxz87-cyber/NFL1) |
| 4 | Branches at start | `main`; a second session branch appeared later | [repo](https://github.com/kanlerxz87-cyber/NFL1) |
| 5 | Pages config | `main / /`, legacy, status built | [Pages API](https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages) |
| 6 | Workflows / site / data | None existed before this session | [repo](https://github.com/kanlerxz87-cyber/NFL1) |

No prior implementation was available to verify, so every value on this site was collected from an official
source during this session. Irregularities F01, F16, F17, F22 and F23 are published on the site's
Flagged for Review page.

| ID | Irregularity | Impact | Action | Official source | Verified |
| --- | --- | --- | --- | --- | --- |
| F01 | The repository contained only README.md at the start; no code, data, workflows or site existed. | No prior implementation to review; all site content is new. | Confirm the repo audit line by line. | [S24](https://github.com/kanlerxz87-cyber/NFL1) | yes |
| F02 | The 2026 standings page heading renders the literal text '$year$ NFL $displayname$ Standings'. | Possible partially rendered official page; re-check before relying on the heading. | Re-fetch and compare division/conference standings views. | [S02](https://www.nfl.com/standings/league/2026/REG) | yes |
| F03 | On the Week 10 injury report most rows publish neither an injury description nor a game status. | Availability signals cannot use those blank fields. | Use the final Game Status Report and official inactives instead. | [S01](https://www.nfl.com/injuries/) | yes |
| F04 | The injury page lists 'Seahawks: No Injuries Reported' while an NFL.com news headline on the same page says Sam Darnold was ruled out for Week 10. | Two official surfaces disagree on availability. | Pre-register which official surface is authoritative. | [S01](https://www.nfl.com/injuries/) | yes |
| F05 | The injury report lists Puka Nacua as DNP with blank injury and game status, while an NFL.com news headline on the same page says he is likely to be placed on IR. | Injury severity is under-reported in the tabular report. | Join news and inactives to the tabular report. | [S01](https://www.nfl.com/injuries/) | yes |
| F06 | Chiefs and Packers depth charts are labelled 'Unofficial' by the clubs themselves. | 2nd/3rd/4th-string assignments are not league-certified. | Ask for a league-published depth chart or use official inactives. | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| F07 | The 49ers chart says 'Updated as of 11/10/26' but is not labelled 'Unofficial'; the Chiefs chart has no as-of date. | Inconsistent provenance metadata across clubs. | Record an as-of label for every snapshot. | [S16](https://www.49ers.com/team/depth-chart) | yes |
| F08 | The league injury report publishes no depth-rank column, and only 3 of 32 clubs' depth charts were transcribed. | Backup-deficiency signals cannot be computed league-wide. | Collect all 32 official club depth-chart URLs and snapshot weekly. | [S01](https://www.nfl.com/injuries/) | yes |