# Pre-registration: shadow-v1 (singles-only team-strength baseline)

Session `55dc53f4-nfl1`, 2026-11-15 (UTC). This file and `shadow-v1.json` are the rule text.
The **commit that adds them is the registration**; its hash is recorded on `COORDINATION.md`.
Everything below was fixed before any Week 11 result existed.

## What it is

A shadow forecast, not a betting strategy. It forecasts **win probability for each Week 11 game**
(singles only). It has no price, no stake, no parlay and no prop. Its record cannot promote anything.

## Inputs (frozen by hash)

| Input | File | sha256 (at registration) |
|---|---|---|
| 2026 finals, weeks 1-10 (137 games) | `data/shadow/corpus_v1.csv` | in `shadow-v1.json` |
| Week 11 fixtures and official venues (13 games) | `data/shadow/week11_venues.csv` | in `shadow-v1.json` |
| Forecast code | `tools/shadow_forecast.py` | in `shadow-v1.json` |

The tool **refuses to run** if any hash differs. No market line, price or third-party odds is an input.

## Model

- `margin_home = b * h + (r_home - r_away)`
- `h = 1` unless the game is neutral. Neutral = the official game-centre location is outside the
  United States (Week 11: only MIN at SF, Estadio Banorte, Mexico City). Training neutral games are
  those whose official week-page note says "International" (7 games).
- Ratings `r` (32 clubs) and `b` minimise squared margin error plus `lambda * sum(r^2)`, with
  **lambda = 4, fixed a priori, not tuned**. `b` is unpenalised.
- `sigma = sqrt(SSE / n)`, in-sample residual SD over the 137 games.
- `P(home win) = Phi(margin_home / sigma)`. Ties are not modelled.

## Recorded per game (for later scoring)

Probability, predicted margin, both ratings, `b`, `sigma`, `lambda`, `h`, the official venue, the
three benchmark picks, and the corpus, fixture and code hashes. **Fixture context** (rest days from
the official schedule dates, short week, division game) is recorded but **not used** by shadow-v1.

## Benchmarks (scored later against the same games)

1. **Coin**: P(home win) = 0.5.
2. **Random pick**: seeded (seed 20261115), one side per game.
3. **Favourite by record**: the side with the higher win percentage in the corpus at registration
   (ties count 0.5; a tie between the sides goes to the home side).

## Scoring after results (not yet applied)

Brier score per game. Skill = 1 - Brier(model) / Brier(benchmark). Uncertainty = game-cluster
bootstrap by week, 1000 resamples, seed 20261115, 95% interval. **No claim is made below 40 graded
games.**

## Gates

- **G-SH1 record integrity.** Each forecast is committed before that game's kickoff. Week 11 must
  be committed before Thu 19 Nov 2026 20:15 ET (2026-11-20 01:15 UTC). Later records are marked
  `late` and are never scored as forecasts.
- **G-SH2 reproducibility.** `python3 tools/shadow_forecast.py --check` reproduces the record byte
  for byte.
- **G-SH3 input integrity.** Recorded hashes equal the registered ones.
- **G-SH4 benchmark-relative skill.** After >= 40 graded games, the lower 95% bound of skill against
  the coin **and** against the favourite-by-record benchmark is above 0.

## Demotion gate (PR-07)

Applies to any strategy that moves from paper to stakes. None exists today, and shadow-v1 cannot
stake. A strategy goes back to paper if **any** of these holds:

1. After >= 40 graded games, the lower 95% bound of skill against the coin is below 0.
2. A registered input is missing, edited or hash-mismatched for any scored game.
3. Two consecutive scoring weeks have negative point-estimate skill against the favourite-by-record benchmark.
4. A forecast committed after kickoff is found in the scored set (G-SH1).

These thresholds are **proposed values**, fixed by this commit. Changing one needs a new commit,
logged on `COORDINATION.md`.

## What would change our mind (two-sided)

- **Keep shadow-v1 as the benchmark** if, after 40 graded games, the lower 95% bound of skill is above
  0 against both the coin and the favourite-by-record benchmark, and calibration slope is between 0.8
  and 1.2 (proposed).
- **Retire shadow-v1** if the lower 95% bound of skill against the favourite-by-record benchmark is
  below 0 after 40 graded games, or calibration slope is below 0.5 or above 1.5 (proposed), or any
  G-SH1 or G-SH3 failure occurs.

## Known limits, stated before any result

- One season (137 games, about 8.5 per club). Ratings are noisy. This is a baseline, not a model
  that is expected to beat a market.
- The home-field term is estimated at about 0.16 points. That is what the rule gives; it is not a
  claim about home advantage.
- Week 10 has 13 games still unplayed at registration. They are excluded from the training corpus
  here. A later, separately labelled record will include them.
