# Reward Rule — NFL1 Strategy Competition (pre-registered)

**Registration:** this file is the frozen rule. It is committed **before** any strategy is
graded against it for a badge. The commit that first added this file is the registration; the
SHA-256 of this file at that commit is the registration fingerprint. `rewards/verify.py`
re-derives both from `git log --diff-filter=A` and the file's content and fails on any drift.

**Status of this rule:** a **pre-registered proposal (policy)**, not an official NFL fact. The
thresholds below are taken from this repository's own published proper-score method
(`data/strat/proper_score.json`); they are not invented and not sourced from any league
document, because the league publishes no reward programme. Rewards are **non-monetary
badges** only. No cash value is attached to any badge.

**Why this rule exists.** The brief asks for a leaderboard competition that "provides rewards
for top performing strategies", that separates signal from staking, that ranks by
benchmark-relative skill with a game-cluster lower bound and a multiplicity adjustment, and
that forbids backtest numbers from appearing on the leaderboard. This rule turns those
requirements into a frozen, two-stage qualification with concrete numeric thresholds, so a
badge can only be earned prospectively by a strategy that has already been shown to carry
calibrated skill.

---

## Stage 1 — Proper-Score Qualification (the "Verified Signal" badge)

A strategy collection in a track earns the **Verified Signal** badge when, over a **frozen
walk-forward out-of-sample window** that was registered before grading, all three hold:

1. **Skill lower bound > 0.** Its benchmark-relative Brier skill score (BSS) has a
   **game-cluster 95% bootstrap lower bound strictly greater than zero**. The published
   number is the lower bound, never the point estimate.
2. **Multiplicity charge cleared.** Its Benjamini-Hochberg-adjusted p-value over the frozen
   family of model-market tests is **< 0.05**, **and** it also clears the Bonferroni
   threshold **0.05 / N_tests**, where **N_tests** is the number of tests in the frozen
   multiplicity family recorded in `data/strat/proper_score.json` (6 as of registration).
3. **Sample floor met.** Its **decided-bet sample is ≥ 200** (the repository's `min_sample`),
   with pushes excluded from the count.

**Value of the Verified Signal badge:** 1 qualification point, and the strategy becomes
**Stage-2 eligible** in its track. A strategy that fails any of the three is **not** eligible
and earns no badge.

## Stage 2 — Prospective CLV / ROI Escrow (the track badges)

Only Stage-1-qualified strategies enter Stage 2. Stage 2 is evaluated over a **registered
multi-week prospective escrow window** of settled bets, with each prediction recorded before
the corresponding official kickoff.

4. **Ranking.** Within a track, rank eligible strategies by the **prospective Closing Line
   Value (CLV) lower bound** (game-cluster), then by the **prospective ROI lower bound**.
5. **Award.** The **Top {Track}** badge is awarded to the rank-1 eligible strategy whose
   **prospective ROI lower bound remains > 0** after the multiplicity charge. The three
   track badges are **Top Single Bet**, **Top Parlay**, **Top Player Prop Combo**.
6. **No fabrication.** If no strategy qualifies at Stage 1, or none clears the Stage-2 ROI
   lower bound, **no badge is awarded**. The cell is published blank with the reason; a
   winner is never invented.

**Value of a track badge:** the track badge plus rank 1 in that track for the escrow window.
Non-monetary.

## Demotion and re-promotion (frozen with the rule)

A badged strategy **returns to paper** — its badge is withdrawn — if it trips any of the
repository's existing demotion rules (`data/strat/demotion_rules.json`):

- **D1** skill interval collapses (90% interval lower bound < 0);
- **D2** stop-loss (realised return < −10%);
- **D3** hit rate below break-even (hit rate < break-even − 2 standard errors);
- **D4** losing streak (12 consecutive settled losses);
- **D5** definition drift (rule text or inputs differ from the registration commit).

**Re-promotion** requires a **fresh prospective sample of 200 settled bets** that clears
D1–D3 in the opposite direction. The same sample that demoted a strategy cannot also promote
it.

## What may never appear on this board

- **Backtest performance numbers.** No ROI, win rate, hit rate, profit or rank derived from
  a backtest is printed on the reward board. Stage 1 publishes the **rule, the thresholds and
  a qualification status** (qualified / not qualified) — never a backtest ROI figure. The
  underlying proper-score result lives on the Strategy Competition sub-site and is linked,
  not re-published here.
- **A badge without a cleared Stage-1 gate.** No exceptions.
- **A monetary value.** Badges are non-monetary by rule.

## Two-sided "what would change our mind"

- **Upside (a strategy earns a badge):** its BSS lower bound is > 0, its BH-adjusted
  p-value is < 0.05 (and it clears Bonferroni 0.05 / N_tests), and its decided-bet sample is
  ≥ 200, on a frozen walk-forward window; and, for a track badge, its prospective ROI lower
  bound is > 0 over the registered escrow window.
- **Downside (a badge is withdrawn):** its BSS lower bound falls to ≤ 0, or its BH-adjusted
  p-value rises to ≥ 0.05, or its sample falls below the track floor, or it trips any
  demotion rule D1–D5.

## Frozen thresholds (numeric, for the verifier)

| Threshold | Value | Where it comes from |
|---|---|---|
| Skill lower bound | `> 0` | `data/strat/proper_score.json` eligibility rule |
| BH-adjusted p-value | `< 0.05` | standard false-discovery control |
| Bonferroni alpha | `0.05 / N_tests`, N_tests = 6 | `data/strat/proper_score.json` multiplicity family |
| Decided-bet sample floor | `≥ 200` | `data/strat/proper_score.json` `min_sample` |
| Stage-2 prospective ROI lower bound | `> 0` | this rule (prospective escrow) |
| Re-promotion sample | `200 settled bets` | `data/strat/demotion_rules.json` repromotion |

These numbers are recorded verbatim in `data/rewards/thresholds.json`. If any of them is
changed, the rule file changes, the registration fingerprint changes, and the verifier fails
until the change is itself a new, explicitly re-registered rule.

## Current status (as of registration)

The repository's own proper-score result is `any_eligible = false`: **no market or rule
clears all three Stage-1 conditions today** (`data/strat/proper_score.json`). Therefore
**no badge is awarded and no track badge is active**. This is the honest starting state, not
a result: the rule is frozen and waiting for a strategy that clears it.
