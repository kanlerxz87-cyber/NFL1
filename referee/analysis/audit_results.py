#!/usr/bin/env python3
"""V1 - Audit the scores in nflverse/nfldata games.csv against official nfl.com standings.

For every team-season that has an official transcription in referee/data/official/, the script
re-derives W, L, T, PF, PA, home record and road record from the game-by-game scores in games.csv
and compares each of the seven fields with the value shown on nfl.com.

It also runs internal consistency checks on every season in the file (no official source involved).

Run from the repository root:  python3 referee/analysis/audit_results.py
Output: referee/data/audit_results.json     (standard library only)
"""
import collections
import csv
import glob
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
GAMES = os.path.join(ROOT, "data", "raw", "games.csv")
OFFICIAL_GLOB = os.path.join(ROOT, "data", "official", "nflcom_standings_*.txt")
OUT = os.path.join(ROOT, "data", "audit_results.json")
FIELDS = ["W", "L", "T", "PF", "PA", "HOME", "ROAD"]


def played(r):
    return r["home_score"] not in ("", "NA") and r["away_score"] not in ("", "NA")


def aggregate(rows):
    """season -> team -> record derived from regular-season scores."""
    out = collections.defaultdict(lambda: collections.defaultdict(
        lambda: {"W": 0, "L": 0, "T": 0, "PF": 0, "PA": 0, "H": [0, 0, 0], "R": [0, 0, 0], "G": 0}))
    for r in rows:
        if r["game_type"] != "REG" or not played(r):
            continue
        hs, aw = int(r["home_score"]), int(r["away_score"])
        for team, pf, pa, key in ((r["home_team"], hs, aw, "H"), (r["away_team"], aw, hs, "R")):
            x = out[int(r["season"])][team]
            x["PF"] += pf
            x["PA"] += pa
            x["G"] += 1
            i = 0 if pf > pa else 1 if pf < pa else 2
            x["WLT"[i]] += 1
            x[key][i] += 1
    return out


def load_official(path):
    meta = {"source": None, "retrieved": None, "note": None}
    teams = {}
    with open(path) as fh:
        lines = fh.read().splitlines()
    meta["note"] = lines[0].lstrip("# ").strip()
    for line in lines:
        if line.startswith("# Source:"):
            meta["source"] = line.split(":", 1)[1].strip()
        elif line.startswith("# Retrieved:"):
            meta["retrieved"] = line.split(":", 1)[1].strip()
        elif line and not line.startswith("#"):
            t, w, l, tie, pf, pa, home, road = line.split()
            teams[t] = {"W": int(w), "L": int(l), "T": int(tie), "PF": int(pf), "PA": int(pa), "HOME": home, "ROAD": road}
    return meta, teams


def main():
    with open(GAMES, newline="") as fh:
        rows = list(csv.DictReader(fh))
    agg = aggregate(rows)

    # ---- official comparison -------------------------------------------------------------
    audit_rows, season_summaries, audited = [], [], set()
    for path in sorted(glob.glob(OFFICIAL_GLOB), reverse=True):
        season = int(re.search(r"(\d{4})\.txt$", path).group(1))
        meta, official = load_official(path)
        audited.add(season)
        n_fields = n_match = n_team_ok = 0
        for team in sorted(official):
            off = official[team]
            d = agg[season].get(team)
            ds = None
            if d:
                ds = {"W": d["W"], "L": d["L"], "T": d["T"], "PF": d["PF"], "PA": d["PA"],
                      "HOME": "-".join(map(str, d["H"])), "ROAD": "-".join(map(str, d["R"]))}
            diffs = [f for f in FIELDS if ds is None or ds[f] != off[f]]
            n_fields += len(FIELDS)
            n_match += len(FIELDS) - len(diffs)
            n_team_ok += 0 if diffs else 1
            audit_rows.append({"season": season, "team": team, "official": off, "dataset": ds,
                               "match": not diffs, "mismatched_fields": diffs, "source": meta["source"]})
        missing = sorted(set(agg[season]) - set(official))
        season_summaries.append({
            "season": season, "status": "audited", "source": meta["source"], "retrieved": meta["retrieved"],
            "note": meta["note"], "teams_official": len(official), "teams_matching": n_team_ok,
            "fields_checked": n_fields, "fields_matching": n_match,
            "dataset_teams_not_on_official_page": missing,
            "reg_games_in_dataset": sum(v["G"] for v in agg[season].values()) // 2,
        })

    # ---- internal consistency, every season ----------------------------------------------
    internal = []
    ids = collections.Counter(r["game_id"] for r in rows)
    dup_ids = sorted(k for k, v in ids.items() if v > 1)
    by_season = collections.defaultdict(list)
    for r in rows:
        by_season[int(r["season"])].append(r)
    for season in sorted(by_season, reverse=True):
        rs = by_season[season]
        pl = [r for r in rs if played(r)]
        bad_result = [r["game_id"] for r in pl if int(r["result"]) != int(r["home_score"]) - int(r["away_score"])]
        bad_total = [r["game_id"] for r in pl if int(r["total"]) != int(r["home_score"]) + int(r["away_score"])]
        ties = [r["game_id"] for r in pl if r["home_score"] == r["away_score"]]
        ties_not_ot = [g for g in ties if next(r for r in pl if r["game_id"] == g)["overtime"] != "1"]
        post_ties = [r["game_id"] for r in pl if r["game_type"] != "REG" and r["home_score"] == r["away_score"]]
        games_per_team = collections.Counter(v["G"] for v in agg[season].values())
        internal.append({
            "season": season, "rows": len(rs), "played": len(pl), "unplayed": len(rs) - len(pl),
            "reg_played": sum(1 for r in pl if r["game_type"] == "REG"),
            "post_played": sum(1 for r in pl if r["game_type"] != "REG"),
            "teams": len(agg[season]),
            "reg_games_per_team": {str(k): v for k, v in sorted(games_per_team.items())},
            "result_field_errors": bad_result, "total_field_errors": bad_total,
            "ties": ties, "ties_not_flagged_overtime": ties_not_ot, "postseason_ties": post_ties,
            "official_audit": "audited" if season in audited else "not audited",
        })
        if season not in audited:
            season_summaries.append({"season": season, "status": "not audited", "source": None, "retrieved": None,
                                     "note": "No official transcription made in this session", "teams_official": None,
                                     "teams_matching": None, "fields_checked": None, "fields_matching": None,
                                     "dataset_teams_not_on_official_page": [],
                                     "reg_games_in_dataset": sum(v["G"] for v in agg[season].values()) // 2})
    season_summaries.sort(key=lambda s: -s["season"])

    out = {
        "generated_by": "referee/analysis/audit_results.py",
        "dataset": {"file": "referee/data/raw/games.csv", "rows": len(rows), "duplicate_game_ids": dup_ids,
                    "first_season": min(by_season), "last_season": max(by_season)},
        "fields": FIELDS,
        "totals": {
            "seasons_audited": len(audited),
            "team_seasons_audited": len(audit_rows),
            "team_seasons_matching": sum(1 for r in audit_rows if r["match"]),
            "fields_checked": len(audit_rows) * len(FIELDS),
            "fields_matching": sum(len(FIELDS) - len(r["mismatched_fields"]) for r in audit_rows),
            "reg_games_covered": sum(s["reg_games_in_dataset"] for s in season_summaries if s["status"] == "audited"),
            "seasons_not_audited": sorted(set(by_season) - audited),
        },
        "season_summaries": season_summaries,
        "rows": audit_rows,
        "internal_checks": internal,
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    t = out["totals"]
    print(f"audited seasons: {sorted(audited)}")
    print(f"team-seasons matching: {t['team_seasons_matching']}/{t['team_seasons_audited']}; "
          f"fields matching: {t['fields_matching']}/{t['fields_checked']}; regular-season games covered: {t['reg_games_covered']}")
    for s in internal:
        flags = []
        if s["result_field_errors"]: flags.append(f"result errors {len(s['result_field_errors'])}")
        if s["total_field_errors"]: flags.append(f"total errors {len(s['total_field_errors'])}")
        if s["ties_not_flagged_overtime"]: flags.append(f"ties w/o OT flag {s['ties_not_flagged_overtime']}")
        if s["postseason_ties"]: flags.append(f"postseason ties {s['postseason_ties']}")
        print(s["season"], "rows", s["rows"], "played", s["played"], "teams", s["teams"], "G/team", s["reg_games_per_team"], "; ".join(flags))
    print("duplicate game_ids:", dup_ids)


if __name__ == "__main__":
    main()
