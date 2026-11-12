## The rule that governs everything here

A number is either transcribed from an official source, computed from such a number, openly
labelled as an assumption, or blank. There is no fourth category, and in particular there is
no category for "a reasonable value somebody would expect".

Four provenance tiers enforce this. They are printed next to every value on every page.

| Tier | Meaning |
| --- | --- |
| VERIFIED | Transcribed character-for-character from an official source. A clickable official URL is attached. No transformation applied. |
| DERIVED | Deterministic arithmetic on VERIFIED values only - ratios, sums, differences, correlations, least-squares fits. Fully reproducible from the cited source with no external assumption. |
| MODELED | Depends on at least one analyst prior or un-fitted coefficient. Must never be staked on until it passes the validation gates. |
| UNAVAILABLE | Not obtainable from an official source in this environment. Left blank on purpose and listed on the Flagged for Review page with the exact source that would resolve it. |

## Rating construction

With no game-level data reachable, the only rating inputs available are the official
standings cells. The rating is therefore net points per game:

```
net_pg = (PF - PA) / (W + L + T)
```

This is DERIVED. It is a coarse instrument and its limitations are stated rather than
hidden: it weights a Week 1 blowout identically to a Week 9 win, it says nothing about
opponent quality, and it does not adjust for who was on the field.

The Pythagorean expectation uses an exponent fitted on the 32 official rows by golden-section
search on the sum of squared errors:

```
pyth_win_pct = PF**k / (PF**k + PA**k)
```

Fitted result: **k = 3.5073**, 95% bootstrap CI **2.7498 to 4.3113**, n = 32,
R² = 0.7715, calibration slope 0.9991, MAE 0.0929, RMSE 0.1141. The exponent is fitted here
rather than imported from published literature, so the number belongs to this dataset. It is
high and its interval is wide because it is fitted on roughly 8.5 games per team; a
full-season fit would be expected to produce a lower, tighter estimate.

The luck measure is the residual:

```
pyth_delta = pyth_win_pct - published_win_pct
games_of_luck = pyth_delta x games_played
```

Positive means the club has won fewer games than its scoring justifies.

## Home advantage

Only the win-rate form is computable, from the official HOME and ROAD cells:

```
home_win_rate = (home_wins + 0.5 x home_ties) / home_games
```

Result: **49.63%**, Wilson 95% CI **41.36% to 57.93%**, n = 136 home games. The interval
includes 50%, so the data does not establish that home advantage has vanished; it establishes
that the conventional ~2.5-point assumption cannot be asserted from it. The observations are
also not independent - every game contributes one home record and one road record - so the
interval is indicative only.

The **point** form of home advantage is not computable and is left blank. It requires
game-level final scores with home/away designation. Because a spread cannot be produced
without it, the origination engine publishes rating gaps and refuses to publish spreads.

## Availability index

```
availability_pressure = sum over report entries of (severity_weight x position_weight)
                      + sum over officially confirmed QB / marquee news items
                        of (news_severity x position_weight)
```

Both weight tables are analyst priors. They are published here in full precisely because they
are not verified, and every output that uses them is labelled MODELED.

Severity weights, keyed to the NFL's own report vocabulary:

| Report state | Weight |
| --- | --- |
| Game Status = Out | 1.00 |
| Game Status = Doubtful | 0.80 |
| Game Status = Questionable | 0.50 |
| Did Not Participate, no game status yet | 0.45 |
| Limited Participation | 0.25 |
| Full Participation | 0.05 |

Position weights:

| Position | Weight | Position | Weight |
| --- | --- | --- | --- |
| QB | 1.00 | DT | 0.45 |
| CB | 0.55 | LB | 0.45 |
| DE / EDGE | 0.55 | RB | 0.45 |
| T | 0.55 | WR | 0.45 |
| C | 0.50 | G | 0.40 |
| OL / DB | 0.45-0.50 | TE | 0.40 |
| K | 0.25 | P | 0.20 |
| LS | 0.15 | FB | 0.10 |

The index carries no string-level weighting, because official depth charts are unavailable.
A third-string absence and a first-string absence therefore contribute identically, which is
a serious deficiency and the reason the index is described as a ranking aid rather than an
estimate. Left tackle and right tackle cannot be distinguished either: the official report
publishes only `T`.

## Correlation screening

Twenty-one signals are screened against two targets - published win percentage and the
Pythagorean residual - on the 32-club cross-section. Availability signals exist for only 28
clubs, because the four teams on bye publish no report and are excluded rather than treated
as zero. Sample size is printed for every single pair.

Reporting Pearson r alone would be misleading, so each cell also carries Spearman rho, a
t-statistic, a raw p-value and a seeded percentile bootstrap interval (4,000 draws, seed
20261112, so published intervals are reproducible).

Thirty-eight tests are run. At p<0.05 alone, **1.9 false positives would be expected purely
by chance.** All results therefore pass Benjamini-Hochberg false-discovery-rate control at
α=0.10, and nothing is called a finding unless its q-value clears that threshold.

Surviving FDR control is necessary but not sufficient, so every surviving correlation is
then classified:

| Class | Meaning | Treatment |
| --- | --- | --- |
| MECHANICAL | Both variables are computed from the same game outcomes, so the association is definitional. | Reported for completeness. Excluded from findings. |
| REDUNDANT | Absolute r at or above 0.80. The two signals are one signal wearing two hats. | Excluded from findings. Never permitted as separate legs of the same multi-leg bet (gate G8). |
| CANDIDATE | One side is an availability or news signal and the other is an outcome, so the association is not definitional. | Reported as a research lead, never as a validated edge. |

Nine of the thirty-eight tests survive FDR control. All nine are MECHANICAL or REDUNDANT.
**Zero non-mechanical findings survive.** That is the correct answer for this dataset, and
the classification step exists so that "teams that outscore their opponents win more games"
is never presented as a discovery.

## Removing luck

Four instruments, in increasing order of strength.

1. **Pythagorean residual** - team level. Runs today on verified official data. Separates a
   club's scoring from its results, which is the part of a record attributable to variance.
2. **Percentile bootstrap** - strategy level. Seeded, 5,000 draws, on per-wager returns.
   Produces a confidence interval on ROI and a t-statistic. Requires settled wagers.
3. **Sign-flip permutation placebo** - strategy level. Under the null of no skill each
   wager's return is equally likely positive or negative, so flipping signs destroys any real
   edge while preserving the return distribution. The share of permutations beating the
   observed statistic is an honest p-value. Requires settled wagers.
4. **Closing-line value** - the gold standard. A model that consistently beats the closing
   number has demonstrated skill long before its ROI has accumulated enough sample to be
   statistically meaningful. Requires a closing-odds feed.

Instruments 2 to 4 are implemented and unit-tested. All three return NOT_RUN today, with the
reason recorded, because their inputs do not exist.

## Validation gates

Nine gates stand between a strategy and a stake. A gate whose evidence does not exist returns
BLOCKED, and BLOCKED is fatal - it is never treated as a pass.

| Gate | Requirement |
| --- | --- |
| G1 Data provenance | Every input is VERIFIED or DERIVED from an official source. A MODELED input may not drive a stake without recorded human sign-off. |
| G2 Sample size | At least 300 settled wagers for a single or total, 200 for a player prop, 150 for a parlay or prop combo. |
| G3 No lookahead | Every feature timestamped strictly before kickoff, and the walk-forward split documented. Injury data must be the version that was public when the bet would have been made, not the final Friday report. |
| G4 Out-of-sample | ROI measured on held-out games, with degradation versus in-sample no worse than 40%. |
| G5 Luck removed | t ≥ 3.0 on no-vig ROI, the 95% bootstrap CI excludes zero, and the permutation placebo p ≤ 0.05. |
| G6 Vig-adjusted | The edge must survive at posted prices, not only at de-vigged fair prices. |
| G7 Stability | The sign of the edge retained in at least 70% of leave-one-out folds, and no single fold contributing more than 35% of total profit. |
| G8 Correlation control | For multi-leg bets every leg pair's correlation must be measured and priced. Independent-product pricing is forbidden above absolute rho of 0.15. |
| G9 Execution | Average closing-line value at least +0.20 points, and posted limits must absorb the model stake. |

The gate engine is exercised in the test suite against a deliberately well-formed
hypothetical strategy, so it is demonstrably capable of returning APPROVED. It also rejects a
strategy with lookahead, one whose edge is within noise, and one whose profit is concentrated
in a single fold. A gate that can only ever say no would be worthless as evidence.

## Leaderboard scoring

```
score = t_statistic(no_vig_roi) x stability_multiplier x capacity_factor
```

Ranking on a t-statistic rather than raw ROI is deliberate. Raw ROI ranks noise: a strategy
returning 80% on eleven wagers outranks one returning 9% on nine hundred, which is exactly
backwards. The t-statistic forces a strategy to be both good and proven, and sample size
enters the score directly. The stability multiplier is the share of leave-one-out folds that
retain the sign of the edge, clipped to [0,1]. The capacity factor is the ratio of average
posted limit to model stake, capped at 1.

A score is published only when gates G1 to G7 pass. Otherwise the score is blank, never zero,
so that "not yet measured" can never be mistaken for "measured and worthless".

## Odds arithmetic

American and decimal conversion, overround, multiplicative de-vig, Shin/power de-vig, parlay
fair probability and edge at posted prices are implemented exactly and unit-tested. For a
-110/-110 book both de-vig methods return exactly 0.500/0.500, and the edge of a 55% model
probability at -110 is exactly +5.00%.

Parlay pricing applies a first-order correlation adjustment when measured pairwise
correlations are supplied:

```
P(A and B) = P(A) P(B) + rho x sd(A) x sd(B)
```

This is a first-order correction only. It is better than the independent product the
sportsbooks themselves use to price parlays, and it is not a substitute for measuring the
joint distribution directly.

## Reproducing all of it

```
python3 -m venv .venv                 # optional: the core is standard library only
PYTHONPATH=src python3 -m nfl.pipeline   # rebuilds data/processed/site_data.json
PYTHONPATH=src python3 scripts/build_site.py   # regenerates docs/
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The pipeline is deterministic: identical verified inputs produce byte-identical JSON, because
every random routine is seeded.
