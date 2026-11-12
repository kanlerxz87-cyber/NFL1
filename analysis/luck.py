#!/usr/bin/env python3
"""
luck.py — separate skill from luck for every strategy in the forward test.

Reads  data/verified/model/predictions_log.json (produced by analysis/engine.py).
Writes data/verified/model/luck.json.

Why each test exists
  1. Exact binomial test vs 50%          — is the directional hit rate distinguishable from coin flips?
  2. Bootstrap CI on accuracy            — how wide is our uncertainty with only 8-9 weeks?
  3. Holm-Bonferroni adjustment          — we tested several strategies; unadjusted p-values overclaim.
  4. Brier score + log loss + calibration— accuracy can look good while probabilities are wrong.
  5. Split-half stability (early vs late) — a real edge persists; luck decays.
  6. Flat-stake P/L at an ASSUMED -110   — converts accuracy into the currency of the leaderboard,
                                            clearly labelled as an assumption, never as a market quote.

Nothing here is a claim of profitability: with no observed market price, P/L at -110 is a
sensitivity scenario, not a realised return.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "verified" / "model"
SEED = 20261112
PRICE = -110.0          # assumed standard price (ASSUMPTION, not observed)
N_BOOT = 20000

STRATS = {
    "model (opponent-adjusted, ridge)": "pred_model",
    "B1 home field only": "pred_b1_hfa",
    "B2 season-to-date differential": "pred_b2_diff",
    "B3 last-5 differential": "pred_b3_recent",
}


def exact_binom_two_sided(k: int, n: int, p: float = 0.5) -> float:
    """Two-sided exact binomial p-value (sum of outcomes no more likely than observed)."""
    pmf = [math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(n + 1)]
    obs = pmf[k]
    return float(min(1.0, sum(v for v in pmf if v <= obs + 1e-12)))


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def analyse(rows: list[dict]) -> dict:
    rng = np.random.default_rng(SEED)
    res = {}
    actual = np.array([r["actual"] for r in rows])
    home_win = (actual > 0).astype(float)
    ties = int((actual == 0).sum())

    # residual scale of the primary model, used to convert margins into probabilities
    model_err = actual - np.array([r["pred_model"] for r in rows])
    sd_model = float(np.std(model_err))

    for name, key in STRATS.items():
        pred = np.array([r[key] for r in rows])
        pick = np.sign(pred)
        correct = (pick == np.sign(actual)) & (actual != 0)
        n = int((actual != 0).sum())
        k = int(correct.sum())
        acc = k / n if n else float("nan")

        # bootstrap accuracy CI
        boots = np.empty(N_BOOT)
        idx_ok = np.where(actual != 0)[0]
        for i in range(N_BOOT):
            s = rng.choice(idx_ok, len(idx_ok), replace=True)
            boots[i] = np.mean(pick[s] == np.sign(actual[s]))
        ci = (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)))

        # probabilities for Brier / log loss, using each strategy's own residual scale
        sd_s = float(np.std(actual - pred)) or sd_model
        probs = np.array([norm_cdf(m / sd_s) if m != 0 else 0.5 for m in pred])
        probs = np.clip(probs, 1e-6, 1 - 1e-6)
        brier = float(np.mean((probs - home_win) ** 2))
        logloss = float(-np.mean(home_win * np.log(probs) + (1 - home_win) * np.log(1 - probs)))
        brier_base = float(np.mean((0.5 - home_win) ** 2))

        # calibration by decile of predicted probability
        order = np.argsort(probs)
        chunks = np.array_split(order, 5)
        calib = [{"bucket": i + 1,
                  "n": int(len(c)),
                  "mean_pred": round(float(probs[c].mean()), 3),
                  "observed": round(float(home_win[c].mean()), 3)} for i, c in enumerate(chunks)]

        # split-half stability
        weeks = np.array([r["week"] for r in rows])
        early = weeks <= 5
        late = weeks > 5

        def acc_of(mask):
            ok = (actual[mask] != 0)
            if ok.sum() == 0:
                return None
            return float(np.mean(pick[mask][ok] == np.sign(actual[mask][ok])))

        # flat stake P/L at assumed price
        win_pay = 100.0 / abs(PRICE) * 100.0
        units = k * win_pay - (n - k)
        res[name] = {
            "n_decided": n, "ties_excluded": ties,
            "correct": k, "accuracy": round(acc, 4),
            "acc_ci95": [round(ci[0], 4), round(ci[1], 4)],
            "p_value_vs_coinflip": round(exact_binom_two_sided(k, n), 5),
            "brier": round(brier, 4), "brier_coinflip": round(brier_base, 4),
            "brier_skill_score": round(1 - brier / brier_base, 4) if brier_base else None,
            "log_loss": round(logloss, 4),
            "accuracy_weeks_1_5": None if acc_of(early) is None else round(acc_of(early), 4),
            "accuracy_weeks_6_9": None if acc_of(late) is None else round(acc_of(late), 4),
            "calibration": calib,
            "assumed_price": PRICE,
            "units_at_assumed_price": round(units, 2),
            "units_per_bet": round(units / n, 4) if n else None,
            "roi_at_assumed_price": round(units / (n * 100.0), 4) if n else None,
        }

    # Holm-Bonferroni across the four strategies
    order = sorted(res.items(), key=lambda kv: kv[1]["p_value_vs_coinflip"])
    m = len(order)
    holm, prev = {}, 0.0
    for i, (name, v) in enumerate(order):
        adj = min(1.0, max(prev, (m - i) * v["p_value_vs_coinflip"]))
        prev = adj
        holm[name] = round(adj, 5)
    for name, v in res.items():
        v["p_value_holm_adjusted"] = holm[name]
        v["survives_multiple_testing_5pct"] = holm[name] < 0.05

    # leaderboard ordered by the decision-relevant metric (accuracy, then Brier)
    board = sorted(res.items(), key=lambda kv: (-kv[1]["accuracy"], kv[1]["brier"]))
    for rank, (name, v) in enumerate(board, 1):
        v["rank"] = rank

    metric_note = {
        "metric": "straight-up winner accuracy (which team wins the game)",
        "not_measured": "against-the-spread (ATS) accuracy",
        "why_ats_missing": "ATS requires an observed closing line for every game. No official "
                           "NFL odds/closing-line source is reachable from this environment and "
                           "none is stored in the repo, so spread-beating accuracy and realised "
                           "betting P/L are UNVERIFIED and left blank.",
        "interpretation_warning": "Picking winners is materially easier than covering a spread. "
                                  "A ~60% straight-up hit rate is fully consistent with an "
                                  "average-accuracy forecaster and says nothing about beating a price.",
    }

    return {
        "metric_definition": metric_note,
        "assumptions": {
            "price_model": f"{PRICE:.0f} standard juice applied flat to every pick",
            "price_is_observed_market": False,
            "note": "No official NFL odds source is reachable from this environment and none is "
                    "stored in the repo. P/L figures are a sensitivity scenario, not realised "
                    "returns, and cannot be used to claim profitability.",
            "ties": "ties excluded from accuracy (NFL regular season can tie; 1 tie in sample)",
        },
        "leaderboard": [{"strategy": n, **res[n]} for n, _ in board],
        "gate_summary": {
            "any_strategy_significant_after_multiple_testing":
                any(v["survives_multiple_testing_5pct"] for v in res.values()),
            "any_strategy_positive_brier_skill":
                any((v["brier_skill_score"] or 0) > 0 for v in res.values()),
            "required_before_any_real_use":
                ["observed market closing lines with timestamps (unavailable)",
                 "at least one full season of forward-test predictions",
                 "pre-registered hypotheses to avoid multiple-testing bias",
                 "independent replication of the signal"],
        },
        "input_rows": len(rows),
    }


def main() -> int:
    rows = json.loads((OUT / "predictions_log.json").read_text())
    out = analyse(rows)
    (OUT / "luck.json").write_text(json.dumps(out, indent=2))
    print(f"{'strategy':<34}{'acc':>7}{'95% CI':>16}{'p':>9}{'p_holm':>9}{'brier':>8}{'early':>8}{'late':>8}")
    for v in out["leaderboard"]:
        ci = f"[{v['acc_ci95'][0]:.2f},{v['acc_ci95'][1]:.2f}]"
        print(f"{v['strategy']:<34}{v['accuracy']:>7.3f}{ci:>16}{v['p_value_vs_coinflip']:>9.4f}"
              f"{v['p_value_holm_adjusted']:>9.4f}{v['brier']:>8.3f}"
              f"{(v['accuracy_weeks_1_5'] or 0):>8.3f}{(v['accuracy_weeks_6_9'] or 0):>8.3f}")
    print("\nany significant after Holm:", out["gate_summary"]["any_strategy_significant_after_multiple_testing"])
    print("any positive Brier skill:", out["gate_summary"]["any_strategy_positive_brier_skill"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
