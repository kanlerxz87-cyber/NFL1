# Improvement suggestions and choose-a-path

All suggestions are awaiting review. A reviewer must choose a path before anything is implemented; the site's Suggestions page provides the selection control and a prefilled decision-record issue.

## Paths

| ID | Path | Summary | Blocked by | Official source | Verified |
| --- | --- | --- | --- | --- | --- |
| P-A | Path A — Data first | Close the open data questions (odds source, depth charts for all clubs, game-level panel, inactives deadline), then build signals. | Q05, Q06, Q09, Q10, Q11, Q12, F08, F09, F10 | [S02](https://www.nfl.com/standings/league/2026/REG) | yes |
| P-B | Path B — Strategy first | Prototype the 10 candidate strategies and the leaderboard immediately, with all performance values blank until gates pass. | Q11, Q12, Q13, F09, F10, F11 | [S19](https://www.itl.nist.gov/div898/handbook/ppc/section1/ppc136.htm) | yes |
| P-C | Path C — Review only / hold | Implement nothing beyond documentation and the review gate until a reviewer explicitly chooses a path. | Q27, F16, F22 | [S24](https://github.com/kanlerxz87-cyber/NFL1) | yes |

## Suggestions

| ID | Area | Suggestion | Decision impact | Effort | Official source | Verified |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | Provenance | Add a source link and retrieval date to every table row | Makes any decision auditable line by line |  | [S02](https://www.nfl.com/standings/league/2026/REG) | yes |
| S02 | Provenance | Keep blank cells blank and flag them instead of substituting estimates | Prevents fabricated values entering a decision |  | [S02](https://www.nfl.com/standings/league/2026/REG) | yes |
| S03 | Decision readiness | Add a decision-readiness panel that counts open questions and flagged values | Shows at a glance whether a decision is defensible |  | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| S04 | Freshness | Show an as-of timestamp and the next official filing deadline on every data page | Prevents stale injury data being used in a decision |  | [S04](https://www.nfl.com/news/2026-27-national-football-league-important-dates) | yes |
| S05 | CI | Run the row-source validator and internal link checker on every push | A broken link or unsourced row is caught before publishing |  | [S22](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) | yes |
| S06 | Availability | Add an injury x depth-chart join that shows which string would take the snaps | Directly addresses the 2nd/3rd/4th-string deficiency requirement |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| S07 | Availability | Add a conflict detector for 'No Injuries Reported' vs official news headlines | Removes contradictory inputs before they reach a model |  | [S01](https://www.nfl.com/injuries/) | yes |
| S08 | Availability | Add the official weekly inactives list as the availability authority | Inactives are closer to game time than practice reports |  | [S05](https://www.nfl.com/news/nfl-week-9-inactives-players-ruled-out-sunday-2026-season) | yes |
| S09 | Signals | Add a correlation matrix view with method, n and confidence information | Makes 'determine correlation values' reviewable |  | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| S10 | Signals | Add a validation-gate pass/fail badge to every strategy | Prevents unvalidated strategies from being used |  | [S18](https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm) | yes |
| S11 | Signals | Add a pre-registration hash field for each strategy | Frees the evaluation from post-hoc tuning |  | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| S12 | Signals | Add a frozen out-of-sample evaluation window on the leaderboard | Separates in-sample fit from genuine predictive skill |  | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| S13 | Parlays | Add a leg-correlation guard before any parlay or prop combo is eligible | Correlated legs change parlay risk materially |  | [S19](https://www.itl.nist.gov/div898/handbook/ppc/section1/ppc136.htm) | yes |
| S14 | Risk | Add a bet-type risk panel using official loss percentages | Gives reviewers a common risk baseline |  | [S21](https://nj.gov/oag/ge/2024news/2020sportswagerreportrevised121523.pdf) | yes |
| S15 | Data access | Add JSON/CSV downloads for every table | Allows independent line-by-line review outside the browser |  | [S24](https://github.com/kanlerxz87-cyber/NFL1) | yes |
| S16 | Navigation | Group pages by category with a persistent dashboard sidebar | Reduces time to find the evidence behind a decision |  | [S23](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site) | yes |
| S17 | Review workflow | Add an explicit decision log recording the chosen path and reviewer | Makes the 'choose before implementing' gate enforceable |  | [S24](https://github.com/kanlerxz87-cyber/NFL1) | yes |
| S18 | Review workflow | Add triage fields (owner, due date, disposition) to Flagged for Review | Turns flags into resolvable work items |  | [S24](https://github.com/kanlerxz87-cyber/NFL1) | yes |
| S19 | Glossary | Add a verbatim glossary of official designations and bet types | Prevents inconsistent interpretation of official labels |  | [S20](https://www.nj.gov/oag/ge/docs/Regulations/CHAPTER69N.pdf) | yes |
| S20 | Accessibility | Add table sorting/filtering and responsive table wrappers | Makes large verified tables readable on any screen |  | [S23](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site) | yes |
| SA-01 | Site architecture | Guard shared output paths across the four site generators | Prevents a routine rebuild from silently replacing the canonical landing page (this audit had to restore index.html and README.md after tools/build.py regenerated them from another generation). | Small | [S23](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site) | yes |
| SA-02 | Data freshness | Add a pre-slate injury-report refresh before kickoffs | Keeps game-day reads aligned with the official report | Small (one extra cron in collect-data.yml) | [S02](https://www.nfl.com/standings/league/2026/REG) | yes |
