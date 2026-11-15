# SB-01 — singles-only shadow baseline (frozen rule text)

Registration kind: **prospective**. This file, `prereg/README.md` and
`prereg/shadow_baseline.py` together form the registration commit. It contains no
results, no forecasts and no outcomes. The commit hash of this commit is the
registration for SB-01.

## 1. Rule (what is forecast, and where it is used)

For every game of the registered week, produce a **win probability for the home club**
and a single pick (the side with the higher probability). Track: **singles only** — no
parlays, no prop combos, no staking curve; any later score is flat 1-unit paper stakes.
This baseline exists to be beaten, not to be optimised: it is the control a new signal
must clear before anyone calls the new signal skill.

## 2. Model (frozen; zero free parameters)

Pythagorean matchup probability with exponent exactly **2.0**:

1. From the input set (section 3) compute for every club `t`:
   `PF_t` = points scored by `t`, `PA_t` = points allowed by `t`.
2. Strength `s_t = PF_t^2 / (PF_t^2 + PA_t^2)`; if `PF_t^2 + PA_t^2 == 0`, `s_t = 0.5`.
3. `p_home = s_home / (s_home + s_away)`.
4. Pick = home if `p_home >= 0.5`, else away.

No home-field term, no rest term, no injury term, no tuning knob. If a later session
wants a different exponent or a home-field constant, that is a **new** registration
(SB-02+), not an amendment to this one.

## 3. Input

All rows of `data/s9cb/games.csv` (nflverse `schedules` release, CC-BY-4.0, pinned by
sha256 in the forecast record) that carry **both final scores** at the time the forecast
record is written. The record also stores `PF`/`PA` per club so every probability is
reproducible without the original file.

Provenance tier: the file is a third-party parse of the NFL's schedule feed; its 2026
results were checked against the official schedule pages by earlier sessions
(136-row transcription `data/verified/games_2026.csv` plus the official WAS 24–21 NYG
final, flag F49). Pre-2026 results in the file are **not** officially verified; that is
recorded on the corpus, not hidden.

## 4. Sample window

The registered forecast window for this registration is **2026 Week 11** (13 games,
kickoffs 2026-11-19 to 2026-11-23, transcribed from
<https://www.nfl.com/schedules/2026/by-week/week-11> into
`data/prereg/official/week11_2026_schedule.json`). One week is a **pipeline test**, not
a skill sample.

## 5. Gates (pre-declared)

| gate | rule |
|---|---|
| SB-G1 | every forecast in the record has `recorded_at` strictly earlier than that game's official kickoff |
| SB-G2 | the model file's sha256 at settlement equals the sha256 recorded at forecast time (no post-hoc edits) |
| SB-G3 | probabilities recompute exactly from the stored `PF`/`PA` aggregates |
| SB-G4 | skill claim gate: a claim of skill requires Brier skill vs the 0.5 base rate with a 95% interval above zero over **≥ 200 settled forecasts**; Week 11 (n=13) can never satisfy this gate and is reported as a pipeline test only |

## 6. Two-sided "what would change our mind"

* **upside** — across ≥200 settled prospective forecasts the Brier skill vs the 0.5 base
  rate has a 95% interval strictly above zero *and* the record was written before every
  kickoff (SB-G1 holds for all of them); only then does the baseline graduate from
  control to benchmark.
* **downside** — any single forecast whose `recorded_at` is not earlier than its kickoff,
  or any post-kickoff edit to a settled record (SB-G1/SB-G2 broken), voids the whole
  prospective claim regardless of how well it scored, and the entry is demoted to the
  retrospective archive.

## 7. Scoring (after the window closes)

Each settled game is scored with the Brier score `(p_home − outcome)^2` (outcome = 1 if
the home club won, 0 if it lost; ties count 0.5). Scores are published only after every
game in the window is final on the official schedule page, and only together with the
same two controls registered for every board run: a random-side control and a
favourites-only control (`data/prereg/controls.json`).
