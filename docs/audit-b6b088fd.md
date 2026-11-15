# Current-session repository and evidence audit

**Audit date:** 2026-11-15 (UTC)  
**Branch:** `arena/b6b088fd-nfl1`  
**Scope:** read-only review of the published repository, official-source snapshots, and reproducible verification gates. No model/data/site output was edited. The only file change outside this report is the coordination-board claim/result.

## Executive summary

The repository already contains the requested static GitHub Pages dashboard, executive summary, requirements inventory, strategy/leaderboard research, injury/depth views, decision questions, suggestions workflow, and a Flagged for Review page. The live public URL recorded in the repo is [NFL Decision Lab](https://kanlerxz87-cyber.github.io/NFL1/).

Local build and consistency checks passed. In particular, the source-link check found **2,024 table rows with official source links, 73 unverified values left blank/flagged, and no broken internal links**. All 136 unit tests passed, with 11 optional strength/statistics tests skipped because NumPy/Pandas are not installed in this environment. The offline official-data audit reported **20 PASS, 8 FLAG, 0 FAIL**; its flags are not equivalent to an all-clear.

The material risk is **freshness and snapshot lineage**, not a broken site build. The current official NFL injury report page (fetched during this audit) still identifies itself as Week 10 and includes Sunday, November 15 games. The committed injury source registry is dated November 12, and older report transcriptions in the repository differ from later official captures. An official-source audit also reports a difference between the 136-game verification corpus and current standings-implied 137 games. Existing verification results therefore establish reproducibility for specific captured snapshots; they do not certify that every displayed injury or depth value is current at kickoff.

No strategy currently qualifies for real staking based on the current dashboard's own published gate counts (0 strategies passing all gates). The sound next step is to keep the system in shadow/paper mode, refresh official availability evidence with exact timestamps and hashes, and rerun the same registered rules only after the result and price datasets are synchronized.

## Verification performed

| Check | Result | What it establishes | Reproduce |
|---|---:|---|---|
| Unit tests | 136 passed; 11 skipped | Current Python test suite passes; 11 tests were skipped because NumPy/Pandas are absent | `python3 -m unittest discover -v` |
| Source-link audit | 2,024 rows; 2,024 with official links; 73 unverified; 0 broken | Rows in the audited root and `pages/` tables have official links; unverified values remain identified | `python3 tools/verify.py` |
| Combined data/site verification | 32 standings, 20 injury rows, 32 team-directory rows, 136 game rows; 0 mismatches; 2,418 links; 0 broken | Cross-file arithmetic and internal links match the checked-in evidence corpus | `python3 tools/verify_combined.py` |
| Committed-site check | 27 pages, 1,510 internal links, 1,118 sourced rows | Generated committed pages have no broken links or source-less rows; 11 older pages are explicitly reported as unstamped | `python3 tools/check_committed_site.py` |
| Independent numeric recomputation | 47/47 | Published figures reproduce from checked-in inputs | `python3 scripts/verified/audit_numbers.py` |
| Verified dataset hard checks | PASS | 136 captured games; all 32 teams reconcile; arithmetic and dataset checks pass | `python3 scripts/verified/validate_verified.py` |
| Site links/navigation | PASS; 27 pages | Local links resolve and navigation is complete for the checked site | `python3 scripts/verified/check_site.py` |
| Official evidence comparison | 20 PASS, 8 FLAG, 0 FAIL | Standings/arithmetic and some schedule checks pass; injury/depth mismatches are flagged rather than silently changed | `python3 tools/verify_official.py` |
| Official audit arithmetic | 905 checks; 0 failed; 65 flags | The checked-in official retrievals are internally reproducible for selected columns; some official page columns differ between retrievals or contradict themselves | `python3 tools/audit_official.py` |
| Freshness | 23 assertions pass | Generated pages match the freshness metadata available to the checker, not the live freshness of every external source | `python3 tools/check_freshness.py` |
| Generator ownership | PASS | Each enumerated generated path has one writer | `python3 tools/check_generators.py` |
| Reachability | 166/166 pages reachable | Local pages are reachable from the published landing page; 90 table rows have their source link in a neighbouring cell rather than the source cell | `python3 tools/check_reachability.py` |
| Strategy research subsite | 14 pages, 221 rows, PASS | Every table row is sourced and links/placeholders pass the subsite gate | `python3 tools/check_strength_site.py` |
| Decision Room | 11 pages, 23 tables, 312 data rows, PASS | Every Room table has source links, no blank rendered cells, and local links resolve | `python3 room/verify.py` |

**Interpretation limits:** `verify_official.py` compares the repo with hand-transcribed files in `data/evidence/`; it is a reproducible comparison, not a fresh network fetch each time it is run. `audit_official.py` compares archived retrievals and the repo; its passing checks do not erase its flags. A `PASS` on a snapshot only says that the cited snapshot or computation is consistent, not that the source has not changed since capture.

## Confirmed findings and irregularities

| Finding | Evidence / impact | Source and next action |
|---|---|---|
| Injury-report snapshots are time-sensitive and some committed transcriptions are stale relative to later captures. | The repo's official injury source entry says it was retrieved 2026-11-12. `verify_official.py` flags injury-row differences and missing/extra rows against its checked-in Week 10 evidence. The board already records an earlier same-day official report change as `A-F04`; do not treat an old capture as current availability. | [NFL official injury report](https://www.nfl.com/injuries/); [source registry](../data/sources.json); [existing A-F04 record](../data/flags.json). Capture Wed-to-kickoff versions, hashes, timestamps and conflict flags; compare each dataset to the exact capture it claims to represent. |
| Current official standings imply a different game count than one validated corpus. | `verify_combined.py` reconciles **136** official game rows; the official audit's latest checked standings imply **137** played games. This is a one-game lineage/version mismatch until the precise season cutoff and completed game are reconciled; do not merge the counts or silently add a row. | [NFL 2026 standings](https://www.nfl.com/standings/league/2026/REG); [NFL 2026 schedule](https://www.nfl.com/schedules); [verification output](../data/combined_verification.json); [archived audit output](../data/audit/official_verification.json). Reconcile the exact missing/extra game ID, official game book/result, and cutoff before extending the backtest corpus. |
| Some depth-chart rows differ from the official club pages. | The official comparison flags KC/SEA rows absent or assigned different ranks in the repo. The existing audit explicitly treats club charts as their own published ordering and avoids inventing a league-certified depth list. Depth rank must not be inferred from jersey order, roster order, or salary. | [Kansas City Chiefs official depth chart](https://www.chiefs.com/team/depth-chart); [Seattle Seahawks official depth chart](https://www.seahawks.com/team/depth-chart); [per-row evidence register](../data/evidence/depth_charts.json); [comparison output](../data/audit/official_verification.json). Re-transcribe only from dated official club pages and preserve shared/empty slots and raw source text. |
| Official standings page contains columns that drift between retrievals or contradict the clubs' own W-L-T arithmetic. | The archived audit reports 65 flags; it separately states which columns reproduce and which are excluded. Do not use disputed divisions/conference splits as model input. | [NFL standings](https://www.nfl.com/standings/league/2026/REG); [audit implementation](../tools/audit_official.py); [archived audit](../data/audit/4c043747/official_audit.json). Keep the exclusions and source timestamps visible. |
| The standings-derived 137-game count and 136-game verified game corpus need a common as-of cutoff. | Backtests require exact results and a pre-kickoff origin record for each fixture. A count-only fix would risk lookahead or a duplicated result. | [NFL Game Center schedule/results](https://www.nfl.com/schedules); [verified game corpus](../data/verified/games_2026.csv); [current verified corpus checks](../data/combined_verification.json). Match unique game IDs, final scores, venue and timestamps to official Game Books/results before scoring. |
| Current line/strategy outcomes must remain separate from official evidence and market-price evidence. | Repository documentation identifies NFL.com as the official source for schedule, game results, status and roster facts; it does not publish wagering prices. Market line/odds comparison must be governed by a separately declared data policy and provenance. | [NFL official schedule](https://www.nfl.com/schedules); [official player statistics](https://www.nfl.com/stats/player-stats/); [repo price/source policy](../data/terms.json); [price-history provenance](../data/s9cb/provenance.json). Identify whether a feed is licensed/usable, define open/close timestamps and market/line conventions, then publish the policy and hashes before new backtests. |
| Some generated pages are explicitly unstamped, even though the checker passes its stale-stamp gate. | The committed-site checker lists 11 earlier-generator pages as unstamped. They are flagged as legacy/old-generation material in the repo, but a passing freshness command cannot prove their external data are current. | [unstamped page list](../tools/check_committed_site.py); [generator ownership map](../tools/check_generators.py); [published landing page](https://kanlerxz87-cyber.github.io/NFL1/). Keep historical pages visibly dated or retire them through the final integration owner; do not call them freshly verified. |

## Questions that must be answered before a defensible decision

| Question | Information present | Missing evidence / discovery step | Gate before decision |
|---|---|---|---|
| Which exact game results belong in the backtest window? | A 136-game corpus and a current official standings view that implies 137 games are both present. | Reconcile game IDs, dates, scores and the snapshot cutoff against NFL Game Center and official Game Books. | No rescore / no promotion until corpus game IDs and source snapshots match. |
| What injury report did the model know at its prediction timestamp? | Dated official Week 10 transcriptions, an automated scrape, and later reports of intraday status changes. | Immutable scheduled captures with UTC fetch time, raw hash, report date, parser version, source row count and conflict status; retain every Wednesday-through-kickoff revision. | No injury-feature evaluation until point-in-time joins are replayable without lookahead. |
| Did an unavailable starter actually leave a replacement on the field, and how much? | Dated club depth information and availability labels for part of the season. | Official inactive lists, actual starters from Game Books, and official snap counts; compare actual playing time, not jersey/depth order alone. | No replacement-impact feature until the chain is confirmed from official evidence. |
| Does the model add prospective skill beyond market and controls? | Registered strategy definitions, historical scoring, baselines and rejection gates exist; no strategy currently passes all gates in the primary dashboard. | Immutable forecast-before-kickoff records, settled official results, synchronized prices, chronological holdouts and full uncertainty/multiplicity reporting. | Remain shadow/paper; do not rank by win rate or short-run ROI. |
| Can a parlay or prop combo be scored fairly? | Marginal probabilities and correlation research exist, with blank/unavailable values in places. | Directly validated joint-probability data, sample sizes, official settlement/push/void rules and the applicable market terms. | No combo leaderboard entry unless joint evidence and settlement contract both pass. |
| Can live strategy be demoted safely? | Governance and validation pages describe gates. | A monitor that checks rolling prospective calibration/CLV with uncertainty and records the automatic paper-mode transition. | Keep staking disabled until demotion is implemented and exercised by a failing fixture/test. |

## Recommended next actions (ordered)

1. **Freeze the evidence boundary.** Preserve the current outputs and hashes; identify the exact date/time/as-of labels each snapshot describes. Do not edit historic data in place.
2. **Reconcile game results.** Compare all 136 game IDs with the official schedule/Game Center and Game Books; identify the standings-implied 137th result and decide whether it falls inside the registered window.
3. **Refresh availability immutably.** Capture the NFL injury report and club depth pages on a schedule through kickoff; retain raw content hashes and parsed row-count/schema checks. Capture official inactives, starters and snap counts separately.
4. **Keep model readiness conservative.** Existing checks report no all-gate-passing strategy; keep singles shadow-only and keep parlays/prop combos blocked until joint probabilities, price policy and settlement rules are proven.
5. **Publish the current audit flags in the site register.** The new findings above are documented in this report and in the coordination log as a cross-scope integration request; the generated shared `data/flags.json` and Flagged page were intentionally not edited in this audit scope. The final integration owner should assign a non-colliding flag ID, add official links, rebuild the page and rerun all gates.

## Primary official sources

- [NFL Official Injury Report](https://www.nfl.com/injuries/)
- [NFL 2026 league standings](https://www.nfl.com/standings/league/2026/REG)
- [NFL 2026 schedule and game results](https://www.nfl.com/schedules)
- [NFL player statistics](https://www.nfl.com/stats/player-stats/)
- [Kansas City Chiefs official team depth chart](https://www.chiefs.com/team/depth-chart)
- [Seattle Seahawks official team depth chart](https://www.seahawks.com/team/depth-chart)
- [NFL 2026 Washington Commanders at New York Giants Game Center](https://www.nfl.com/games/commanders-at-giants-2026-reg-10)

All local data references above link to repository files for audit reproducibility. They are not substituted for the linked official source. This report does not claim that every historical or current row was freshly re-transcribed by hand; it separates reproducible local gates from time-sensitive source verification.
