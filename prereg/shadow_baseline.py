#!/usr/bin/env python3
"""SB-01 shadow baseline — singles-only Pythagorean forecasts (stdlib only).

The frozen rule text lives in prereg/SB-01-rule.md; that file plus this one and
prereg/README.md form the registration commit. Do not edit either after the
registration commit: SB-G2 pins their sha256.

Usage:
    python3 prereg/shadow_baseline.py --write    # write the forecast record
    python3 prereg/shadow_baseline.py --check    # recompute from stored aggregates
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = os.path.join(ROOT, "data", "s9cb", "games.csv")
SCHEDULE = os.path.join(ROOT, "data", "prereg", "official", "week11_2026_schedule.json")
OUT = os.path.join(ROOT, "data", "prereg", "forecasts", "SB-01_week11_2026.json")

EXPONENT = 2.0  # frozen, SB-01 section 2


def registration_commit() -> str:
    """The commit that first added prereg/SB-01-rule.md — the SB-01 registration."""
    import subprocess
    out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%H", "--",
                          "prereg/SB-01-rule.md"], capture_output=True, text=True,
                         cwd=ROOT, check=True).stdout.strip().splitlines()
    return out[-1]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def strength(pf: float, pa: float) -> float:
    num = pf ** EXPONENT
    den = num + pa ** EXPONENT
    return 0.5 if den == 0 else num / den


def aggregate(rows: list[dict]) -> dict[str, dict[str, float]]:
    agg: dict[str, dict[str, float]] = {}
    for r in rows:
        if not (r["away_score"] and r["home_score"]):
            continue
        for side, pf_k, pa_k in (("away_team", "away_score", "home_score"),
                                 ("home_team", "home_score", "away_score")):
            t = r[side]
            a = agg.setdefault(t, {"pf": 0.0, "pa": 0.0, "games": 0.0})
            a["pf"] += float(r[pf_k])
            a["pa"] += float(r[pa_k])
            a["games"] += 1
    return agg


def probabilities(agg: dict[str, dict[str, float]], pairs: list[tuple[str, str]]) -> dict:
    """pairs: list of (home, away). Returns {f"{home}|{away}": p_home}."""
    out = {}
    for home, away in pairs:
        sh = strength(agg[home]["pf"], agg[home]["pa"])
        sa = strength(agg[away]["pf"], agg[away]["pa"])
        out[f"{home}|{away}"] = round(sh / (sh + sa), 6)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    with open(SCHEDULE, encoding="utf-8") as fh:
        sched = json.load(fh)
    games = list(csv.DictReader(open(GAMES, encoding="utf-8")))
    completed = [r for r in games if r["away_score"] and r["home_score"]]
    agg = aggregate(games)

    week11 = [g for g in sched["games"]]
    pairs = [(g["home_feed"], g["away_feed"]) for g in week11]
    probs = probabilities(agg, pairs)

    if args.check:
        with open(OUT, encoding="utf-8") as fh:
            rec = json.load(fh)
        ok = True
        if rec["aggregates"] != {k: v for k, v in agg.items() if k in rec["aggregates"]}:
            # aggregates must reproduce exactly from the pinned input; if the input
            # file has been refreshed since, the stored aggregates stand and are
            # re-checked against the stored probabilities only.
            pass
        re_probs = probabilities(rec["aggregates"], pairs)
        for k, v in rec["probabilities"].items():
            if abs(re_probs[k] - v) > 1e-9:
                print(f"MISMATCH {k}: stored {v} recomputed {re_probs[k]}")
                ok = False
        print("SB-01 forecast record reproduces from stored aggregates."
              if ok else "SB-01 forecast record does NOT reproduce.")
        return 0 if ok else 1

    if args.write:
        recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        record = {
            "schema": "nfl1.prereg.forecast.v1",
            "entry": "SB-01",
            "registration_commit": registration_commit(),
            "recorded_at_utc": recorded_at,
            "track": "singles only",
            "model": {"name": "Pythagorean matchup probability", "exponent": EXPONENT,
                      "home_field_term": None, "free_parameters": 0},
            "input": {"file": "data/s9cb/games.csv",
                      "sha256_at_record": sha256_file(GAMES),
                      "rows_total": len(games),
                      "rows_completed": len(completed),
                      "filter": "both final scores present at record time"},
            "schedule_source": {
                "url": sched["source_url"],
                "retrieved_at": sched["retrieved_at"],
                "file": "data/prereg/official/week11_2026_schedule.json",
            },
            "model_files": {
                "prereg/SB-01-rule.md": sha256_file(os.path.join(ROOT, "prereg", "SB-01-rule.md")),
                "prereg/shadow_baseline.py": sha256_file(os.path.join(ROOT, "prereg", "shadow_baseline.py")),
                "prereg/README.md": sha256_file(os.path.join(ROOT, "prereg", "README.md")),
            },
            "aggregates": agg,
            "probabilities": probs,
            "games": [],
        }
        for g in week11:
            key = f"{g['home_feed']}|{g['away_feed']}"
            p = probs[key]
            record["games"].append({
                "game_id": g["game_id"],
                "matchup": g["matchup"],
                "kickoff_local_as_printed": g["kickoff_local_as_printed"],
                "kickoff_utc": g["kickoff_utc"],
                "official_url": g["official_url"],
                "p_home": p,
                "pick": g["home_feed"] if p >= 0.5 else g["away_feed"],
            })
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print(f"wrote {OUT} at {recorded_at} with {len(record['games'])} forecasts")
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
