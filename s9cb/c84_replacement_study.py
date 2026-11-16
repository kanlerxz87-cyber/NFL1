#!/usr/bin/env python3
"""c84_replacement_study.py — confirmed replacements, not inferred depth order.

The brief asks for three things this file can answer WITHOUT inferring anything:

  * "Track the depth of the replacement, not just the fact of a replacement"
  * "Do not model depth from jersey order; model it from playing time"
  * "Add an announced-starter evidence field (not an inferred replacement)"

A club depth chart is an opinion and, in this repository, a one-time transcription with two
known parse failures. Who actually TOOK THE FIRST SNAP at quarterback is a fact carried by the
game feed itself (`home_qb_id` / `away_qb_id`, the GSIS starting-QB id on every game row).
This study therefore uses only confirmed starters, and measures how deep the replacement was by
counting that replacement's OWN PRIOR STARTS inside the walk-forward window.

Nothing here reads a depth chart, a jersey number, a salary or a draft slot.

Output: data/session-c84a41a4/qb_replacement.json
Run:   python3 s9cb/c84_replacement_study.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "session-c84a41a4")
SEASONS = list(range(2006, 2027))
SEED = 20261115
OFFICIAL = "https://www.nfl.com/schedules/"


def american_to_decimal(a):
    return 1.0 + (a / 100.0 if a > 0 else 100.0 / abs(a))


def cluster_ci(rows, n_boot=2000, seed=SEED):
    cl = defaultdict(list)
    for r in rows:
        cl[r["game_id"]].append(r["profit"])
    keys = list(cl)
    if len(keys) < 3:
        return None
    sums = {k: sum(v) for k, v in cl.items()}
    rng = random.Random(seed)
    out = []
    for _ in range(n_boot):
        pick = [keys[rng.randrange(len(keys))] for _ in keys]
        num = sum(sums[k] for k in pick)
        out.append(num / len(pick))
    out.sort()
    return [round(out[int(0.025 * (len(out) - 1))], 5), round(out[int(0.975 * (len(out) - 1))], 5)]


def main():
    path = os.path.join(ROOT, "data/s9cb/games.csv")
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    games = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if int(r["season"]) not in SEASONS:
                continue
            hs, as_ = r["home_score"].strip(), r["away_score"].strip()
            games.append({
                "game_id": r["game_id"], "season": int(r["season"]), "week": int(r["week"]),
                "home": r["home_team"], "away": r["away_team"],
                "home_qb": (r["home_qb_name"] or "").strip(),
                "away_qb": (r["away_qb_name"] or "").strip(),
                "home_qb_id": (r["home_qb_id"] or "").strip(),
                "away_qb_id": (r["away_qb_id"] or "").strip(),
                "played": bool(hs and as_),
                "margin": (float(hs) - float(as_)) if (hs and as_) else None,
                "spread": float(r["spread_line"]) if r["spread_line"].strip() else None,
                "home_price": float(r["home_spread_odds"]) if r["home_spread_odds"].strip() else None,
                "away_price": float(r["away_spread_odds"]) if r["away_spread_odds"].strip() else None,
                "home_ml": float(r["home_moneyline"]) if r["home_moneyline"].strip() else None,
                "away_ml": float(r["away_moneyline"]) if r["away_moneyline"].strip() else None,
            })

    games.sort(key=lambda g: (g["season"], g["week"]))
    # who started, by club, walk-forward
    prior_starts = defaultdict(int)         # (club_id_key) -> starts seen so far
    nominal = {}                            # club-season -> current plurality starter id
    counts = defaultdict(lambda: defaultdict(int))
    rows = []
    for g in games:
        if not g["played"]:
            # a game that has not been played still consumes the club's slot for the week,
            # but it cannot inform a starter, so nothing is recorded for it.
            continue
        for side in ("home", "away"):
            club = g[side]
            qb_id = g[f"{side}_qb_id"]
            qb_name = g[f"{side}_qb"]
            if not qb_id:
                continue
            key = (club, g["season"])
            # the club's nominal starter is whoever has started most often for it so far
            # THIS SEASON, which is a walk-forward fact and not an opinion.
            cs = counts[key]
            nom_id = max(cs, key=lambda k: cs[k]) if cs else None
            is_replacement = bool(nom_id) and qb_id != nom_id
            depth = prior_starts[(club, qb_id)]
            if nom_id:
                rows.append({
                    "game_id": g["game_id"], "season": g["season"], "week": g["week"],
                    "club": club, "side": side, "opponent": g["away" if side == "home" else "home"],
                    "confirmed_starter": qb_name, "confirmed_starter_id": qb_id,
                    "nominal_starter_id": nom_id, "replacement": is_replacement,
                    "replacement_prior_starts_this_club": depth,
                    "replacement_depth_label": (
                        "first change (no prior start)" if is_replacement and depth == 0 else
                        "later change (has started before)" if is_replacement else "incumbent"),
                    "spread": g["spread"], "result": g["margin"],
                    "price_home": g["home_price"], "price_away": g["away_price"],
                    "home_ml": g["home_ml"], "away_ml": g["away_ml"],
                    "home": g["home"], "away": g["away"],
                })
            prior_starts[(club, qb_id)] += 1
            cs[qb_id] += 1

    # ---------------------------------------------------------------- summary
    total_starts = len(rows)
    repl = [r for r in rows if r["replacement"]]
    first_change = [r for r in repl if r["replacement_prior_starts_this_club"] == 0]
    later_change = [r for r in repl if r["replacement_prior_starts_this_club"] > 0]

    # --------------------------------------------- does the market price a replacement?
    # Test: back the CLUB that starts a replacement, at its own spread price.
    def ats(club_row, back_club=True):
        """Profit of backing `club_row['club']` at its own spread."""
        r = club_row
        if r["spread"] is None:
            return None
        if r["side"] == "home":
            price = r["price_home"]
        else:
            price = r["price_away"]
        if price is None:
            return None
        margin = r["result"] if r["side"] == "home" else -r["result"]
        line = r["spread"] if r["side"] == "home" else -r["spread"]
        if abs(margin - line) < 1e-9:
            return 0.0
        won = margin > line
        dec = american_to_decimal(price)
        if not back_club:
            won = not won
        return (dec - 1.0) if won else -1.0

    bets = []
    for r in rows:
        p = ats(r)
        if p is None:
            continue
        bets.append({"game_id": r["game_id"], "group": r["replacement_depth_label"],
                     "season": r["season"], "profit": p})
    groups = defaultdict(list)
    for b in bets:
        groups[b["group"]].append(b)

    by_group = {}
    for label, grp in groups.items():
        n = len(grp)
        roi = sum(x["profit"] for x in grp) / n
        by_group[label] = {"n": n, "roi_pct": round(100 * roi, 3),
                           "roi_ci95_game_cluster": cluster_ci(grp)}

    diff = []
    a = {b["game_id"]: b["profit"] for b in groups.get("first change (no prior start)", [])}
    for b in groups.get("incumbent", []):
        if b["game_id"] in a:
            diff.append({"game_id": b["game_id"], "profit": a[b["game_id"]] - b["profit"]})
    diff_ci = cluster_ci(diff)

    # ------------------------------------------------- per-club replacement counts
    per_club = defaultdict(lambda: {"confirmed_starts": 0, "replacements": 0,
                                    "first_change": 0, "later_change": 0})
    for r in rows:
        d = per_club[r["club"]]
        d["confirmed_starts"] += 1
        if r["replacement"]:
            d["replacements"] += 1
            if r["replacement_prior_starts_this_club"] == 0:
                d["first_change"] += 1
            else:
                d["later_change"] += 1

    # ------------------------------------------------------------- example rows
    examples = []
    seen = set()
    for r in rows:
        if not r["replacement"]:
            continue
        k = (r["club"], r["season"], r["confirmed_starter"])
        if k in seen:
            continue
        seen.add(k)
        examples.append({**{x: r[x] for x in
                            ("season", "week", "club", "opponent", "confirmed_starter",
                             "replacement_depth_label", "replacement_prior_starts_this_club",
                             "game_id")},
                         "source": OFFICIAL})
        if len(examples) >= 60:
            break

    out = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "input": {"path": "data/s9cb/games.csv", "sha256": h,
                  "columns_used": ["home_qb_id", "away_qb_id", "home_qb_name", "away_qb_name",
                                   "spread_line", "home_spread_odds", "away_spread_odds",
                                   "home_score", "away_score"]},
        "official_source": OFFICIAL,
        "what_is_confirmed": (
            "The starting quarterback on each game row is the quarterback who took the first snap, "
            "carried in the game feed by GSIS player id. It is a record of playing time, not a "
            "depth-chart opinion, so a replacement identified here is a CONFIRMED replacement."),
        "what_is_not_used": [
            "club depth charts (a weekly opinion, and a one-time transcription in this repo)",
            "jersey numbers, roster order, salary, draft position or experience",
            "any snap count (no official snap-count source is committed here)",
        ],
        "method": {
            "nominal_starter": ("the club's most frequent confirmed starter so far THIS SEASON, "
                                "computed only from games before the one being judged"),
            "replacement": "this week's confirmed starter is not the club's nominal starter",
            "depth_of_replacement": ("the replacement's OWN prior confirmed starts for the same club "
                                     "in the sample. 0 = he had never started for the club, i.e. the "
                                     "replacement went one level deeper than a backup who has played."),
            "walk_forward": True,
        },
        "counts": {
            "confirmed_starts": total_starts,
            "replacements": len(repl),
            "replacement_rate_pct": round(100 * len(repl) / total_starts, 2) if total_starts else None,
            "first_change_no_prior_start": len(first_change),
            "later_change_has_started": len(later_change),
        },
        "market_test": {
            "question": "Does backing a club that starts a confirmed replacement beat its own price?",
            "by_group": by_group,
            "first_change_minus_incumbent": {
                "n_paired": len(diff),
                "mean_difference_units": round(sum(x["profit"] for x in diff) / len(diff), 5) if diff else None,
                "ci95_game_cluster": diff_ci,
                "reading": ("A negative difference means starting a replacement went worse than "
                            "starting the incumbent, relative to the price. An interval containing "
                            "zero means the sample cannot separate the two."),
            },
            "note": ("This is a diagnostic, not a promoted strategy: it is ONE rule, it was not in "
                     "the pre-registered family, and it is published as an observation for the review "
                     "page rather than as a bet recommendation."),
        },
        "per_club": [{"club": k, **v} for k, v in sorted(per_club.items())],
        "examples": examples,
        "limits": [
            "The feed records the starter, not the reasons: an injury, a benching and a rest week all "
            "appear as the same event.",
            "Only the quarterback. Offensive line and secondary replacements cannot be confirmed from "
            "any committed source, because no official snap count and no confirmed-starter feed for "
            "those positions exists in this repository.",
            "A club with two co-starters will look like it changes starter often; the plurality rule "
            "makes the label unstable in that case, and it is labelled as a change rather than smoothed.",
        ],
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "qb_replacement.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out["counts"], indent=1))
    print(json.dumps(by_group, indent=1))
    print("paired diff:", out["market_test"]["first_change_minus_incumbent"])


if __name__ == "__main__":
    main()
