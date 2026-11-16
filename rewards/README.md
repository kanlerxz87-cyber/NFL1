# Reward Board (`rewards/`)

A self-contained, static site that publishes the **pre-registered reward rule** for the NFL1
strategy competition: a two-stage qualification (proper-score → prospective CLV/ROI escrow)
that decides which strategies earn a **non-monetary badge**. It is built from the committed
JSON in `data/rewards/` and published under
<https://kanlerxz87-cyber.github.io/NFL1/rewards/>. It is linked from the main landing page
navigation ("Rewards").

**This is a pre-registered proposal (policy), not an official NFL fact.** The league publishes
no reward programme. The thresholds are taken from this repository's own proper-score method
(`data/strat/proper_score.json`); they are not invented and not sourced from any league
document. Rewards are non-monetary badges only — no cash value is attached to any badge.

## The rule in one paragraph

A strategy earns the **Verified Signal** badge (Stage 1) when, on a frozen walk-forward
out-of-sample window, its Brier skill *lower bound* is > 0, its BH-adjusted p-value is < 0.05
(and it clears Bonferroni 0.05 / N_tests), and its decided-bet sample is ≥ 200. Only
Stage-1-qualified strategies enter Stage 2, a registered multi-week prospective escrow, where
the **Top Single Bet / Top Parlay / Top Player Prop Combo** badge goes to the rank-1 eligible
strategy whose prospective ROI lower bound is > 0. If no strategy qualifies, **no badge is
awarded** — the cell is blank, never fabricated. A badged strategy returns to paper if it
trips demotion rule D1–D5.

The full frozen text is in [`REWARDS-RULE.md`](REWARDS-RULE.md). The registration commit that
first added it is the registration; its SHA-256 is the registration fingerprint.

## Build and gate

```bash
python3 rewards/build.py     # rewrite rewards/index.html from data/rewards/*.json
python3 rewards/verify.py    # fail on: broken link, unreachable page, table with no rows,
                             # empty cell, row with no https source, literal markdown,
                             # KPI without a note, rule drift, blank threshold, or a
                             # backtest metric used as a table column
```

`build.py` refuses to render a row whose source link is not `https://`. The build stamp is
derived from the registration commit and the rule fingerprint, never the wall clock, so a
rebuild is byte-identical. `verify.py` is run in `.github/workflows/verify.yml` (additive
step) together with a staleness check.

## Data

| File | Contents | Source |
|---|---|---|
| `data/rewards/rewards.json` | the frozen rule summary, registration commit + rule sha256, per-track status, mind-changers, sources | rule file + proper-score result |
| `data/rewards/thresholds.json` | the concrete numeric thresholds, each with its source | `data/strat/proper_score.json`, `data/strat/demotion_rules.json` |

## What this directory does not do

- It does not edit `index.html`, `pages/`, `strat/`, `room/`, `data/strat/**` or any other
  session's generator or data. The only shared files touched are the additive navigation
  entries and the one-step build registration (logged in `COORDINATION.md`).
- It does not publish a backtest performance number (ROI, win rate, hit rate, profit, rank).
  The board publishes the rule, the thresholds and a qualification status.
- It does not award a badge to a strategy that did not clear the Stage-1 gate. Today
  `any_eligible = false`, so no badge is awarded and the status is published blank.
- It does not attach a monetary value to any badge.
