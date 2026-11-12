#!/usr/bin/env python3
"""audit_numbers.py — independent recomputation of every published figure.

Deliberately re-implements the arithmetic from the raw CSVs rather than importing the
analysis modules, so a bug in the pipeline cannot hide behind itself. Exits non-zero if any
published number disagrees with an independent recomputation.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "data/verified/model"
KEY = {"model (opponent-adjusted, ridge)": "pred_model", "B1 home field only": "pred_b1_hfa",
       "B2 season-to-date differential": "pred_b2_diff", "B3 last-5 differential": "pred_b3_recent"}


def j(name): return json.loads((M / name).read_text())


def main() -> int:
    problems, checks = [], 0
    rows, bt, lk, co, ln = (j("predictions_log.json"), j("backtest.json"), j("luck.json"),
                            j("correlations.json"), j("lines_week10.json"))
    rat = {r["abbr"]: r for r in j("ratings.json")["ratings"]}
    hfa = j("ratings.json")["meta"]["hfa_points"]

    for r in bt["leaderboard"]:
        k = KEY[r["strategy"]]
        mae = sum(abs(x["actual"] - x[k]) for x in rows) / len(rows)
        checks += 1
        if abs(mae - r["mae_margin"]) > 0.01:
            problems.append(f"MAE {r['strategy']}: recomputed {mae:.3f} vs published {r['mae_margin']}")

    for v in lk["leaderboard"]:
        k = KEY[v["strategy"]]
        c = sum(1 for x in rows if x["actual"] != 0 and (x[k] > 0) == (x["actual"] > 0))
        n = sum(1 for x in rows if x["actual"] != 0)
        checks += 2
        if c != v["correct"]: problems.append(f"hits {v['strategy']}: {c} vs {v['correct']}")
        if n != v["n_decided"]: problems.append(f"decided {v['strategy']}: {n} vs {v['n_decided']}")

    for g in ln["games"]:
        exp = rat[g["home"]]["power"] - rat[g["away"]]["power"] + hfa
        checks += 2
        if abs(exp - g["model_margin_home"]) > 0.15:
            problems.append(f"line {g['game_id']}: {exp:.2f} vs {g['model_margin_home']}")
        if g["market_line"] is not None:
            problems.append(f"market line must stay blank: {g['game_id']}")

    games = list(csv.DictReader(open(ROOT / "data/verified/games_2026.csv")))
    marg = [int(g["home_score"]) - int(g["away_score"]) for g in games]
    tot = [int(g["home_score"]) + int(g["away_score"]) for g in games]
    mean = lambda a: sum(a) / len(a)
    mx, my = mean(marg), mean(tot)
    r_c2 = (sum((a - mx) * (b - my) for a, b in zip(marg, tot)) /
            (sum((a - mx) ** 2 for a in marg) * sum((b - my) ** 2 for b in tot)) ** 0.5)
    published_c2 = next(c for c in co["correlations"] if c["id"] == "C2")["r"]
    checks += 2
    if abs(r_c2 - published_c2) > 0.001:
        problems.append(f"C2: {r_c2:.4f} vs {published_c2}")
    hw = sum(1 for x in marg if x > 0) / sum(1 for x in marg if x != 0)
    if abs(hw - co["home_win"]["rate"]) > 0.001:
        problems.append(f"home win rate: {hw:.4f} vs {co['home_win']['rate']}")

    # C5 (flag F36): division-game flag must use conference + division together,
    # checked against the official groupings published at
    # https://www.nfl.com/standings/division/2026/REG (retrieved 2026-11-12).
    OFFICIAL_GROUPS = {
        ("AFC", "East"): {"BUF", "NE", "NYJ", "MIA"},
        ("AFC", "North"): {"PIT", "CIN", "CLE", "BAL"},
        ("AFC", "South"): {"JAX", "HOU", "IND", "TEN"},
        ("AFC", "West"): {"DEN", "KC", "LV", "LAC"},
        ("NFC", "East"): {"NYG", "DAL", "WAS", "PHI"},
        ("NFC", "North"): {"CHI", "DET", "MIN", "GB"},
        ("NFC", "South"): {"CAR", "NO", "TB", "ATL"},
        ("NFC", "West"): {"SF", "SEA", "LA", "AZ"},
    }
    st_rows = list(csv.DictReader(open(ROOT / "data/verified/standings_2026.csv")))
    csv_groups: dict[tuple[str, str], set[str]] = {}
    for r in st_rows:
        csv_groups.setdefault((r["conference"], r["division"]), set()).add(r["abbr"])
    checks += 1
    if csv_groups != OFFICIAL_GROUPS:
        problems.append("standings_2026.csv groupings no longer match the official nfl.com divisions")
    grp = {r["abbr"]: (r["conference"], r["division"]) for r in st_rows}
    dflag = [1 if grp[g["home_abbr"]] == grp[g["away_abbr"]] else 0 for g in games]
    df_mean, t_mean = mean(dflag), mean(tot)
    r_c5 = (sum((a - df_mean) * (b - t_mean) for a, b in zip(dflag, tot)) /
            (sum((a - df_mean) ** 2 for a in dflag) * sum((b - t_mean) ** 2 for b in tot)) ** 0.5)
    pub_c5 = next(c for c in co["correlations"] if c["id"] == "C5")
    checks += 2
    if abs(r_c5 - pub_c5["r"]) > 0.001:
        problems.append(f"C5: {r_c5:.4f} vs {pub_c5['r']}")
    if sum(dflag) != int(pub_c5["note"].split()[0]):
        problems.append(f"C5 division-game count: {sum(dflag)} vs note '{pub_c5['note']}'")

    inj = list(csv.DictReader(open(ROOT / "data/verified/injuries_week10.csv")))
    av = j("availability.json")
    checks += 1
    if sum(1 for r in inj if r["game_status"] == "Out") != av["totals"]["verified_out"]:
        problems.append("injury Out count mismatch")

    checks += 1
    if j("validation.json")["failures"]:
        problems.append("data validation gate reports failures")

    print(f"independent recomputations: {checks}")
    if problems:
        print("\nDISCREPANCIES:")
        for p in problems:
            print(" -", p)
        return 1
    print("All published figures reproduce from the source data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
