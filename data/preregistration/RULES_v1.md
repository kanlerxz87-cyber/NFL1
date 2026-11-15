# Pre-registered rules, version 1

Registered by session `d4027f66-nfl1` on 2026-11-15, before any prospective evaluation window
has opened. The registration is the git commit that first adds this file (see `registry.json`).
Any later change creates a new version (`RULES_v2.md`) with its own registration; this file is
never edited after registration.

**Status of every number below.** Each threshold is a *design parameter chosen by the analysis
session*, not an official NFL figure, and it is not derived from any source. They are published so
that a reviewer can object before the window opens. Changing one after registration voids it.

## R1. What is registered
A strategy is registered by a rule text that fixes: its inputs, its market (single, game parlay,
same-game parlay or prop combo), its stake rule, and its evaluation window. A strategy with no
registration is shown as `NOT REGISTERED` and carries no rank, score, sample size or reward.

## R2. Prospective window
A window opens at the first game whose official kickoff (nfl.com schedule) is after the
committer timestamp of the registration commit. Games before that are *historical* and cannot
enter any leaderboard column (R3).

## R3. Leaderboard ban on historical numbers (BAN-1)
Rank, score, sample size, reward and ROI columns show prospective results from registered windows
only. Backtest, in-sample, or pre-registration holdout numbers may appear only on a research page,
labelled `backtest — not eligible`. `tools/check_preregistration.py` fails the build when a
leaderboard row carries a rank, score, sample size or reward without a registration.

## R4. Score: benchmark-relative Brier skill
For singles, `BSS = 1 − Brier(strategy) / Brier(benchmark)`, where the benchmark is the
favourites-only control and the random-pick control, both recorded on every run (control baseline).
Brier is computed on the implied probability each strategy published before kickoff.

## R5. Uncertainty
Game-cluster bootstrap (cluster = one game; 10,000 resamples; seed `20261115`). Report the
one-sided 95% lower bound of BSS. Multiplicity: Holm step-down over the K registered strategies in
the same window (α = 0.05).

## R6. Stage 1 qualification (singles)
A registered single qualifies when all hold in its window: (a) at least 100 settled games;
(b) the Holm-adjusted lower bound of BSS is above 0; (c) every probability was recorded before
kickoff in the point-in-time ledger. Parlays and prop combos cannot qualify under R6; see R9.

## R7. Demotion gate (live strategy → paper)
A strategy that is live is returned to paper if **any** of these is true at any evaluation after a
settled week:
1. **Signal:** after at least 50 settled games since promotion, the one-sided 95% lower bound of
   BSS is below 0.
2. **Price:** after at least 100 priced bets since promotion, the mean closing-line value is
   negative with the 95% interval entirely below 0. Not evaluable until a price source is approved
   (open item PR-01 / PR-10); until then no strategy can be live.
3. **Integrity:** any data gate fails for that strategy's inputs (missing snapshot, unverified
   value used, leaderboard ban violated).
Staking results never keep a strategy live (R8). Demoted strategies return only through a new
registration.

## R8. Separation of signal and staking
Signal is judged by R4–R7 alone. Staking, bankroll and ROI are reported in a separate column that
cannot change a signal's status. A positive ROI does not offset a failed R7 test.

## R9. Joint-evidence gate (parlays and prop combos)
A combo is rankable only when both (a) a directly validated joint probability and (b) the
operator's void/push rules are recorded. Multiplying marginal probabilities is not accepted. If
either is missing the combo shows `NOT RANKABLE — joint evidence missing`.

## R10. Two stages
Stage 1 is R6. Stage 2 (prospective closing-line and ROI escrow) requires a closing-price source
under the price-data policy; it is not defined to run yet. A strategy cannot be live until both
stages pass.

## R11. Frozen parameters
`alpha = 0.05`; bootstrap resamples = 10,000; seed = 20261115; minimum settled games = 100
(Stage 1) and 50 (demotion check 1); minimum priced bets = 100 (demotion check 2).
