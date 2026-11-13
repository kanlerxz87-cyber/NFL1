#!/usr/bin/env python3
"""Compare the live 2026-11-13 Week-10 schedule transcription with the repo's fixtures."""
import csv, json, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HERE = os.path.dirname(__file__)

live = {}
with open(os.path.join(HERE, "live_week10_schedule.tsv"), newline="") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        live[(r["away"], r["home"])] = r

report = {"checked_against": "https://www.nfl.com/schedules/2026/by-week/week-10 (fetched 2026-11-13)",
          "live_games": len(live), "files": {}}

def cmp_games(name, rows):
    ok, bad, seen = 0, [], set()
    NORM = {"LAR": "LA", "ARI": "AZ"}
    for r in rows:
        key = (NORM.get(r["away"], r["away"]), NORM.get(r["home"], r["home"]))
        seen.add(key)
        if key not in live:
            bad.append({"game": f"{key[0]}@{key[1]}", "issue": "not on live Week-10 page"})
            continue
        diffs = {}
        for f in ("date", "kickoff", "tv"):
            if r.get(f) and live[key].get(r.get(f + "_live", f) if False else f) and r[f] != live[key][f]:
                diffs[f] = {"repo": r[f], "live": live[key][f]}
        if diffs:
            bad.append({"game": f"{key[0]}@{key[1]}", "diffs": diffs})
        else:
            ok += 1
    missing = [f"{a}@{h}" for (a, h) in live if (a, h) not in seen]
    report["files"][name] = {"rows": len(rows), "matchups_matching_live": ok,
                             "mismatches": bad, "games_missing_from_file": missing}

# week10_fixtures_2026.csv — compare matchup + date + kickoff (hh:mm vs "8:15 PM")
rows = []
with open(os.path.join(ROOT, "data/verified/week10_fixtures_2026.csv"), newline="") as fh:
    for r in csv.DictReader(fh):
        rows.append({"away": r["away_abbr"], "home": r["home_abbr"], "date": r["gameday"],
                     "kickoff": r["kickoff_et"]})
cmp_games("data/verified/week10_fixtures_2026.csv", rows)

# schedule_2026_week10.tsv — matchup + date + kickoff string + broadcast
rows = []
with open(os.path.join(ROOT, "data/verified/schedule_2026_week10.tsv"), newline="") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        rows.append({"away": r["away_abbr"], "home": r["home_abbr"], "date": r["game_date"],
                     "kickoff": r["kickoff_et"], "tv": r["broadcast"].split(",")[0]})
cmp_games("data/verified/schedule_2026_week10.tsv", rows)

# data/dashboard/schedule_2026_w10.json
d = json.load(open(os.path.join(ROOT, "data/dashboard/schedule_2026_w10.json")))
games = d["games"] if isinstance(d, dict) and "games" in d else d
rows = [{"away": g.get("away") or g.get("away_abbr"), "home": g.get("home") or g.get("home_abbr"),
         "date": g.get("gameday") or g.get("date"), "kickoff": g.get("kickoff_et") or g.get("kickoff")}
        for g in games]
cmp_games("data/dashboard/schedule_2026_w10.json", rows)

# model snapshot fixtures — all 14 week-10 matchups with kickoff (gametime)
snap = json.load(open(os.path.join(ROOT, "data/model/snapshot.json")))
rows = [{"away": g["away"], "home": g["home"], "date": g.get("gameday"),
         "kickoff": g.get("gametime")} for g in snap.get("fixtures", [])]
cmp_games("data/model/snapshot.json (fixtures)", rows)

# byes
byes_repo = []
with open(os.path.join(ROOT, "data/verified/bye_week10.tsv"), newline="") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        byes_repo.append(r["team_abbr"])
live_byes = open(os.path.join(HERE, "live_week10_byes.txt")).read().split()
report["byes"] = {"live": live_byes, "repo_data/verified/bye_week10.tsv": sorted(byes_repo),
                  "match": sorted(byes_repo) == sorted(live_byes)}

json.dump(report, open(os.path.join(HERE, "schedule_diff.json"), "w"), indent=1)
for f, r in report["files"].items():
    print(f, "->", {k: v for k, v in r.items() if k != "note"})
print("byes match:", report["byes"]["match"])
