#!/usr/bin/env python3
"""V3c - Two sensitivity tests on the eight games-file strategies published by session 7600ed8b.

Test 1 (price): they grade every bet at an assumed -110. games.csv carries actual closing prices
for most games from 2006 (home_spread_odds, away_spread_odds, over_odds, under_odds). This test
re-grades the same bets at those prices where present.

Test 2 (line source): the same repository ships a second closing-line file (closing_lines.csv,
2006-2018). For games present in both files, each rule is re-selected and re-graded with the
other file's spread/total, and the two records are compared.

Both tests use unverified line data (no official source exists). They measure how much a record
depends on data choices rather than on the rule.

Run from the repository root:  python3 referee/analysis/replicate_sensitivity.py
Output: referee/data/replication_sensitivity.json     (standard library only)
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import replicate_7600ed8b as R  # noqa: E402  (this session's own re-implementation of the rules)

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "replication_sensitivity.json")
NAMES = {"S04": "Divisional underdog +6.5 or more", "S05": "Underdog on short rest (<=4 days)",
         "S06": "Fade divisional road favourite of 6.5+", "S07": "Home team with 3+ rest-day edge",
         "S08": "Home team facing opponent off a bye", "S09": "Home favourite of 10 or more",
         "S10": "Over when closing total is 41 or lower", "S11": "Under in divisional games with total 47+"}


def dec(american):
    a = float(american)
    return a / 100.0 if a > 0 else 100.0 / -a


def record(results):
    w = sum(v == "win" for v in results)
    l = sum(v == "loss" for v in results)
    p = sum(v == "push" for v in results)
    return w, l, p


def main():
    games = R.load_games()
    raw = {}
    with open(R.GAMES, newline="") as fh:
        for r in csv.DictReader(fh):
            raw[r["game_id"]] = r
    hist = [g for g in games if g["season"] >= 2005 and g["spread"] is not None]

    # ---- Test 1: actual prices ---------------------------------------------------------------
    price_rows = []
    for key, rule in R.RULES.items():
        n = wins = 0
        ret_actual = ret_flat = 0.0
        prices = []
        for g in hist:
            pick = rule(g)
            if not pick:
                continue
            kind, side = pick
            col = {"home": "home_spread_odds", "away": "away_spread_odds", "over": "over_odds", "under": "under_odds"}[side]
            price = raw[g["id"]][col]
            if price in ("", "NA"):
                continue
            res = R.grade(g, kind, side)
            if res == "push":
                continue
            n += 1
            prices.append(float(price))
            if res == "win":
                wins += 1
                ret_actual += dec(price)
                ret_flat += R.PAYOUT
            else:
                ret_actual -= 1.0
                ret_flat -= 1.0
        price_rows.append({"strategy": f"{key} {NAMES[key]}", "graded_bets_with_a_price": n, "wins": wins,
                           "win_pct": round(100.0 * wins / n, 2), "roi_at_assumed_minus_110_pct": round(100.0 * ret_flat / n, 2),
                           "roi_at_actual_price_pct": round(100.0 * ret_actual / n, 2),
                           "difference_pct_points": round(100.0 * (ret_actual - ret_flat) / n, 2),
                           "median_price": sorted(prices)[len(prices) // 2]})

    # ---- Test 2: alternative closing-line file ------------------------------------------------
    alt_spread, alt_total = {}, {}
    with open(os.path.join(ROOT, "data", "raw", "closing_lines.csv"), newline="") as fh:
        for c in csv.DictReader(fh):
            g = raw.get(c["alt_game_id"])
            if not g or c["line"] in ("", "NA"):
                continue
            if c["type"] == "SPREAD" and c["side"] == g["home_team"]:
                alt_spread[c["alt_game_id"]] = -float(c["line"])
            elif c["type"] == "TOTAL" and c["side"] == "Over":
                alt_total[c["alt_game_id"]] = float(c["line"])
    both = [g for g in hist if g["id"] in alt_spread and g["id"] in alt_total]
    alt = [{**g, "spread": alt_spread[g["id"]], "total_line": alt_total[g["id"]]} for g in both]
    source_rows = []
    for key, rule in R.RULES.items():
        a = {g["id"]: R.grade(g, *rule(g)) for g in both if rule(g)}
        b = {g["id"]: R.grade(g, *rule(g)) for g in alt if rule(g)}
        wa, la, pa = record(a.values())
        wb, lb, pb = record(b.values())
        same_pick = set(a) & set(b)
        flipped = sum(1 for k in same_pick if a[k] != b[k])
        source_rows.append({"strategy": f"{key} {NAMES[key]}",
                            "record_games_csv": f"{wa}-{la}-{pa}", "win_pct_games_csv": round(100.0 * wa / (wa + la), 2),
                            "record_closing_lines_csv": f"{wb}-{lb}-{pb}", "win_pct_closing_lines_csv": round(100.0 * wb / (wb + lb), 2),
                            "win_pct_change_points": round(100.0 * wb / (wb + lb) - 100.0 * wa / (wa + la), 2),
                            "bets_only_in_games_csv": len(set(a) - set(b)), "bets_only_in_closing_lines_csv": len(set(b) - set(a)),
                            "same_bet_different_result": flipped})

    out = {"generated_by": "referee/analysis/replicate_sensitivity.py",
           "status": "UNVERIFIED INPUT - no official source exists for betting lines or prices",
           "price_test": {"note": "Bets graded only where games.csv has a closing price for the side bet (mostly 2006 onward).", "rows": price_rows},
           "line_source_test": {"games_in_both_files": len(both), "seasons": sorted({g["season"] for g in both}), "rows": source_rows}}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    for r in price_rows:
        print(r)
    print("games in both files", len(both), sorted({g["season"] for g in both})[0], sorted({g["season"] for g in both})[-1])
    for r in source_rows:
        print(r)


if __name__ == "__main__":
    main()
