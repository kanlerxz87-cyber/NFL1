# Own lines, signals, validation gates, correlations, skill vs luck

All strategies are research designs. No strategy has passed validation; no performance value is published.

## Own-line pipeline

| ID | Step | Action | Detail | Official source | Verified |
| --- | --- | --- | --- | --- | --- |
| OL-01 | 1 | Snapshot official inputs at a fixed timestamp | Standings PF/PA/W/L/T, schedule, injury report, club depth charts, player stats, Next Gen Stats | [S02](https://www.nfl.com/standings/league/2026/REG) | yes |
| OL-02 | 2 | Normalise totals to per-game values | PF / (W+L+T), PA / (W+L+T), NET PTS / (W+L+T) — reproducible in tools/compute_correlations.py | [S02](https://www.nfl.com/standings/league/2026/REG) | yes |
| OL-03 | 3 | Estimate team strength from published values only | strength = f(net points per game, points for, points against); all coefficients blank until validated | [S19](https://www.itl.nist.gov/div898/handbook/ppc/section1/ppc136.htm) | yes |
| OL-04 | 4 | Apply an availability adjustment | Join official injury designations and official club depth rank; effect size blank until out-of-sample validation | [S01](https://www.nfl.com/injuries/) | yes |
| OL-05 | 5 | Originate the own line | own spread / own total = symbolic function of the two teams' strength and availability; no numeric line published | [S20](https://www.nj.gov/oag/ge/docs/Regulations/CHAPTER69N.pdf) | yes |
| OL-06 | 6 | Benchmark | Compare the own line with a reference market line — reference line blank, no official odds source found | [S20](https://www.nj.gov/oag/ge/docs/Regulations/CHAPTER69N.pdf) | NO — flagged |
| OL-07 | 7 | Generate a signal only above a frozen threshold | signal = own line minus reference line; threshold blank until pre-registered | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | NO — flagged |
| OL-08 | 8 | Validate before publication | G01–G13 must all pass; no strategy currently passes | [S18](https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm) | yes |

## Strategies

| ID | Strategy | Track | Hypothesis | Formula | Gates | Official source | Verified |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ST-01 | Net-points strength differential | Single bet | Teams with a higher net points per game cover a derived point spread more often | spread_own = f(NPG_home - NPG_away); f is symbolic, coefficient blank | G01,G02,G03,G04,G05,G06,G07,G12 | [S02](https://www.nfl.com/standings/league/2026/REG) | yes |
| ST-02 | Points-allowed total | Single bet | Points-allowed per game informs a derived game total | total_own = f(PA_pg_home + PA_pg_away); coefficients blank | G01,G02,G03,G04,G05,G06,G07,G12 | [S02](https://www.nfl.com/standings/league/2026/REG) | yes |
| ST-03 | Defensive backup-depth deficiency | Single bet | When a defense starts a 2nd/3rd/4th-string CB, S or EDGE, points allowed rises | delta_rank = depth_rank(starter) - depth_rank(actual); effect size blank | G01,G02,G03,G05,G06,G08,G09,G12 | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| ST-04 | Offensive backup-depth deficiency | Single bet | When an offense starts a backup QB or skill player, points scored falls | delta_rank = depth_rank(starter) - depth_rank(actual); effect size blank | G01,G02,G03,G05,G06,G08,G09,G12 | [S15](https://www.packers.com/team/depth-chart) | yes |
| ST-05 | Practice-status trend | Single bet | A DNP -> Limited -> Full trend predicts availability and performance | trend = ordinal(Full) - ordinal(first report); coefficient blank | G01,G02,G04,G05,G06,G12 | [S04](https://www.nfl.com/news/2026-27-national-football-league-important-dates) | yes |
| ST-06 | Designation-gated availability | Single bet | An official Out/Doubtful/Questionable designation changes the expected lineup | indicator = 1 if designation published; effect size blank | G01,G02,G05,G06,G12 | [S01](https://www.nfl.com/injuries/) | yes |
| ST-07 | Two-leg parlay with correlation guard | Parlay | Two independently validated single-bet signals can be combined | P(parlay) = P(A) x P(B) only if corr(A,B) is measured; corr blank | G01,G02,G05,G06,G09,G10,G12 | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| ST-08 | Same-game player-prop combo | Player prop combo | QB and receiver props in one game are jointly predictable from official player stats | joint model requires corr(prop_A, prop_B); corr blank | G01,G02,G04,G05,G06,G09,G12 | [S03](https://www.nfl.com/stats/player-stats/) | yes |
| ST-09 | Prop availability gate | Player prop combo | Props must be suppressed for officially Out / IR / inactive players | rule = block if status in published Out/IR/inactive set | G01,G02,G12 | [S05](https://www.nfl.com/news/nfl-week-9-inactives-players-ruled-out-sunday-2026-season) | yes |
| ST-10 | Backup-exposure index | All tracks | A composite of published depth rank and injury designations ranks teams by exposure | index = weighted sum; weights blank until validated | G01,G02,G03,G04,G05,G06,G08,G09,G12 | [S14](https://www.chiefs.com/team/depth-chart) | yes |

## Validation gates

| ID | Gate | Criterion | Threshold | Official source | Verified |
| --- | --- | --- | --- | --- | --- |
| G01 | Provenance | Every input value has an official source link and retrieval timestamp |   | [S02](https://www.nfl.com/standings/league/2026/REG) | yes |
| G02 | Point-in-time | Only data published before the decision timestamp is used; official filing times are respected |   | [S04](https://www.nfl.com/news/2026-27-national-football-league-important-dates) | yes |
| G03 | Pre-registration | Strategy formula, thresholds and evaluation window are frozen before scoring |   | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| G04 | Minimum sample | NIST generic advice: 20 observations for a correlation, 32 per group for an average difference, 50 for a standard deviation | 20 / 32 / 50 (generic, not NFL-specific) | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| G05 | Out-of-sample | Model is fit on one partition and assessed on data not used to build it |   | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| G06 | Significance | Two-sample t-test for equal means with pre-registered alpha and critical region | alpha blank (no official value) | [S18](https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm) | yes |
| G07 | Multiple comparisons | Every tested strategy is logged so the number of tests is known before scoring | correction threshold blank | [S18](https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm) | yes |
| G08 | Correlation is not causality | No strategy is described as causal without designed-experiment evidence |   | [S19](https://www.itl.nist.gov/div898/handbook/ppc/section1/ppc136.htm) | yes |
| G09 | Parlay/prop correlation guard | Leg correlations must be measured before combining legs | corr blank | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| G10 | Stability | Signal must persist across consecutive seasons/weeks | window blank | [S13](https://operations.nfl.com/rules-officiating/enforcement/accountability) | yes |
| G11 | Skill over luck | Performance must exceed a pre-registered skill threshold after all other gates pass | threshold blank | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| G12 | Reproducibility | A script and data snapshot reproduce every published number |   | [S24](https://github.com/kanlerxz87-cyber/NFL1) | yes |
| G13 | Deploy integrity | Every table row has an official source link; no broken internal links; Pages build succeeds |   | [S23](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site) | yes |

## Computed correlations (from official standings)

| ID | Pair | x | y | n | Pearson r | Method | Caveat | Official source | Verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-01 | Points For (PF) vs Wins (W) | pf | w | 32 | 0.6676 | Pearson correlation coefficient | Correlation does not imply causality (NIST, S19). | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| C-02 | Points Against (PA) vs Losses (L) | pa | l | 32 | 0.6812 | Pearson correlation coefficient | Correlation does not imply causality (NIST, S19). | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| C-03 | Net Points (NET) vs Winning Percentage (PCT) | net | pct | 32 | 0.869 | Pearson correlation coefficient | Correlation does not imply causality (NIST, S19). | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| C-04 | Points For (PF) vs Points Against (PA) | pf | pa | 32 | -0.0816 | Pearson correlation coefficient | Correlation does not imply causality (NIST, S19). | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| C-05 | Net Points per Game vs Winning Percentage (PCT) | net_pg | pct | 32 | 0.8758 | Pearson correlation coefficient | Correlation does not imply causality (NIST, S19). | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| C-06 | Games Played vs Net Points (NET) | games | net | 32 | -0.2408 | Pearson correlation coefficient | Correlation does not imply causality (NIST, S19). | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |

## Requested correlations still blank

| ID | Pair | Blocker | Value | Official source | Verified |
| --- | --- | --- | --- | --- | --- |
| CR-01 | Injury designation count vs points allowed | A timestamped panel dataset is not published by an official source |  | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | NO — flagged |
| CR-02 | Backup depth rank vs points allowed | Depth rank is not published league-wide |  | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | NO — flagged |
| CR-03 | Backup depth rank vs points scored | Same as CR-02, offense side |  | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | NO — flagged |
| CR-04 | QB passing yards vs WR receiving yards (same game) | No official leg-level correlation dataset |  | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | NO — flagged |
| CR-05 | Two parlay legs (same game) | No official leg-level correlation dataset |  | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | NO — flagged |
| CR-06 | Practice-status trend vs game-day inactive | Joined historical series not available from an official page |  | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | NO — flagged |
| CR-07 | Own line error vs realized margin | No official odds source to define the benchmark |  | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | NO — flagged |
| CR-08 | Net points per game vs win percentage | Computed from official standings — see C-05 in the computed correlations table. | 0.8758 | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |

## Luck-control protocol

| ID | Control | Mechanism | Official source | Verified |
| --- | --- | --- | --- | --- |
| LK-01 | Point-in-time inputs | Use only information published before the decision timestamp; respect the official injury-report filing times | [S04](https://www.nfl.com/news/2026-27-national-football-league-important-dates) | yes |
| LK-02 | Cross-validation | Fit on one partition, assess on data not used to build the model | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| LK-03 | Significance test | Two-sample t-test for equal means with a pre-registered alpha and critical region | [S18](https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm) | yes |
| LK-04 | Pre-registration | Freeze formula, thresholds and window before scoring; log every tested variant | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| LK-05 | Correlation control | Measure leg correlations; reject correlated parlay legs; never equate correlation with causality | [S19](https://www.itl.nist.gov/div898/handbook/ppc/section1/ppc136.htm) | yes |
| LK-06 | Minimum sample | NIST generic advice: 20 for a correlation, 32 per group for an average difference, 50 for a standard deviation | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | yes |
| LK-07 | Skill threshold | Numeric threshold blank and flagged until pre-registered; no strategy is labelled skill-based yet | [S17](https://www.itl.nist.gov/div898/handbook/glossary.htm) | NO — flagged |
