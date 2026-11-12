"""Pipeline orchestrator.

    PYTHONPATH=src python3 -m nfl.pipeline

Reads only data/verified/*.tsv, runs every module, and writes
data/processed/site_data.json which is the single input to the site generator.
Deterministic and reproducible: same inputs, byte-identical outputs.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

from . import (availability, correlation, gates, ingest, leaderboard, luck,
               odds, ratings, signals, strategies, verify)
from .provenance import TIER_DEFINITIONS

OUT = ingest.PROCESSED_DIR / "site_data.json"


def _json_default(o: object):
    """Sets appear in verification checks; serialise them deterministically."""
    if isinstance(o, (set, frozenset)):
        return sorted(str(x) for x in o)
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serialisable")


def _gate_definitions() -> list[dict[str, str]]:
    """Pull the live requirement text straight out of the gate functions."""
    probe = gates.Evaluation(market_type="parlay")
    return [{"gate_id": r.gate_id, "name": r.name, "requirement": r.requirement}
            for r in [fn(probe) for fn in gates.ALL_GATES]]


def build_all() -> dict[str, Any]:
    src = ingest.sources()
    rat = ratings.build()
    av = availability.build()
    sig = signals.build(rat, av)
    corr_screen = correlation.screen(sig["matrix"], sig["teams"], signals.TARGETS,
                                    [s for s in sig["signal_ids"]
                                     if s not in signals.TARGETS])
    corr_pair = correlation.pairwise_matrix(sig["matrix"], sig["teams"],
                                            sig["signal_ids"])
    corr_pair["leg_pairs"] = [c["pearson_r"] for c in corr_pair["cells"]
                              if c["pearson_r"] is not None]
    corr = correlation.annotate(corr_screen, corr_pair)
    strat = strategies.build()
    lb = leaderboard.build(strat["strategies"])
    luck_table = luck.pythagorean_luck_table(rat["metrics"])

    return {
        "meta": {
            "generated_by": "src/nfl/pipeline.py",
            "season": 2026, "week": 10,
            "source_retrieved_at_utc": src.get("retrieved_at_utc"),
            "retrieved_by": src.get("retrieved_by"),
            "standings_as_of": "games completed through Week 9 of the 2026 regular "
                               "season (136 games; Week 10 not yet played at "
                               "retrieval time)",
            "tier_definitions": TIER_DEFINITIONS,
            "sources": src["sources"],
            "unreachable_sources": src["sources_attempted_but_unreachable_from_build_environment"],
            "odds_contract": odds.MARKET_DATA_CONTRACT,
        },
        "verification": rat["verification"],
        "standings": {"metrics": rat["metrics"],
                      "pythagorean_fit": rat["pythagorean_fit"],
                      "home_advantage_win_rate": rat["home_advantage_win_rate"],
                      "home_advantage_points": rat["home_advantage_points"]},
        "schedule": {"games": ingest.schedule(), "byes": ingest.byes(),
                     "origination_board": rat["week10_board"]},
        "availability": av,
        "signals": {"specs": sig["specs"], "active": sig["active"],
                    "blocked": sig["blocked"], "matrix": sig["matrix"],
                    "teams": sig["teams"]},
        "correlation": corr,
        "luck": {"table": luck_table,
                 "team_luck_instrument_status": "RUN on verified official data",
                 "strategy_instruments": [
                     {"instrument": "bootstrap_roi", "status": "NOT_RUN",
                      "reason": "no settled wagers exist"},
                     {"instrument": "permutation_placebo", "status": "NOT_RUN",
                      "reason": "no settled wagers exist"},
                     {"instrument": "skill_vs_luck_variance", "status": "NOT_RUN",
                      "reason": "no settled wagers exist"},
                     {"instrument": "closing_line_value", "status": "NOT_RUN",
                      "reason": odds.MARKET_DATA_CONTRACT["reason"]},
                 ]},
        "strategies": strat,
        "leaderboard": lb,
        "gates": {"definitions": _gate_definitions(),
            "min_samples": gates.MIN_SAMPLES, "min_t": gates.MIN_T,
            "min_clv_points": gates.MIN_CLV_POINTS,
            "max_single_fold_profit_share": gates.MAX_SINGLE_FOLD_PROFIT_SHARE,
            "min_fold_sign_stability": gates.MIN_FOLD_SIGN_STABILITY,
            "correlation_pricing_threshold": gates.CORRELATION_PRICING_THRESHOLD,
            "max_oos_degradation": gates.MAX_OOS_DEGRADATION},
    }


def main() -> None:
    data = build_all()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=False, ensure_ascii=False,
                  default=_json_default)
    v = data["verification"]
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    print(f"verification: {v['total']} checks -> PASS {v['PASS']} / FLAG {v['FLAG']} / FAIL {v['FAIL']}")
    print(f"disputed official cells flagged: {len(v['flags'])}")
    print(f"injury report entries: {v['injury_rows']} across {v['teams_reporting']} teams")
    print(f"signals: {len(data['signals']['active'])} active, {len(data['signals']['blocked'])} blocked")
    print(f"correlation screen: {data['correlation']['screen']['tests_run']} tests, "
          f"{len(data['correlation']['screen']['survivors'])} survive BH-FDR "
          f"at alpha={correlation.FDR_ALPHA}")
    print(f"strategies: {data['strategies']['counts']}")
    print(f"leaderboard: {data['leaderboard']['scored_count']} scored, "
          f"{data['leaderboard']['withheld_count']} withheld")


if __name__ == "__main__":
    main()
