#!/usr/bin/env python3
"""V3e - Game-level cross-check of the 2026 results.

Three independent routes to the same 2026 scores are compared:
  (1) nflverse/nfldata games.csv (this session's snapshot),
  (2) session 25aa7696's own transcription of official nfl.com schedule pages (data/verified/games_2026.csv, read from a git ref),
  (3) 12 Week 1 finals this session read directly on the official nfl.com Week 1 schedule page.
It also re-computes the correlation values 25aa7696 published that depend only on game scores.

Read-only with respect to other sessions' files.
Run from the repository root:  python3 referee/analysis/replicate_25aa7696.py [git-ref]   (default origin/arena/25aa7696-nfl1)
Output: referee/data/replication_25aa7696.json     (standard library only)
"""
import csv
import io
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
REPO = os.path.join(ROOT, "..")
OUT = os.path.join(ROOT, "data", "replication_25aa7696.json")
CODE = {"AZ": "ARI", "LAR": "LA"}


def norm(c):
    return CODE.get(c, c)


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, check=True).stdout


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/arena/25aa7696-nfl1"
    sha = git("rev-parse", ref).strip()
    theirs = list(csv.DictReader(io.StringIO(git("show", f"{ref}:data/verified/games_2026.csv"))))
    corr = json.loads(git("show", f"{ref}:data/verified/model/correlations.json"))

    ds = {}
    with open(os.path.join(ROOT, "data", "raw", "games.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["season"] == "2026" and r["game_type"] == "REG" and r["home_score"] not in ("", "NA"):
                ds[(int(r["week"]), r["away_team"], r["home_team"])] = r

    # (3) vs (1): officially seen Week 1 finals
    official_rows = []
    with open(os.path.join(ROOT, "data", "official", "nflcom_scores_2026_wk1_partial.csv"), newline="") as fh:
        for o in csv.DictReader(line for line in fh if not line.startswith("#")):
            d = ds.get((int(o["week"]), o["away"], o["home"]))
            ok = d is not None and d["away_score"] == o["away_score"] and d["home_score"] == o["home_score"]
            official_rows.append({"game": f"Week {o['week']}: {o['away']} at {o['home']}", "official": f"{o['away_score']}-{o['home_score']}",
                                  "dataset": None if d is None else f"{d['away_score']}-{d['home_score']}",
                                  "result": "match" if ok else "MISMATCH", "source": "https://www.nfl.com/schedules/2026/by-week/week-1"})

    # (2) vs (1): every game in their file
    game_rows, seen = [], set()
    for t in theirs:
        key = (int(t["week"]), norm(t["away_abbr"]), norm(t["home_abbr"]))
        seen.add(key)
        d = ds.get(key)
        issues = []
        if d is None:
            issues.append("game not found in dataset with this week/away/home")
        else:
            if d["away_score"] != t["away_score"] or d["home_score"] != t["home_score"]:
                issues.append(f"score: theirs {t['away_score']}-{t['home_score']}, dataset {d['away_score']}-{d['home_score']}")
            if d["gameday"] != t["gameday"]:
                issues.append(f"date: theirs {t['gameday']}, dataset {d['gameday']}")
        game_rows.append({"game": f"Week {t['week']}: {key[1]} at {key[2]}", "date": t["gameday"],
                          "transcribed": f"{t['away_score']}-{t['home_score']}",
                          "dataset": None if d is None else f"{d['away_score']}-{d['home_score']}",
                          "result": "match" if not issues else "MISMATCH", "issues": issues, "source": t["source_url"]})
    missing = sorted(f"Week {k[0]}: {k[1]} at {k[2]}" for k in set(ds) - seen)

    # correlations that depend only on scores
    games = sorted(ds.values(), key=lambda r: (int(r["week"]), r["game_id"]))
    margin = [int(r["home_score"]) - int(r["away_score"]) for r in games]
    total = [int(r["home_score"]) + int(r["away_score"]) for r in games]
    div = [1.0 if r["div_game"] == "1" else 0.0 for r in games]
    by_team = {}
    for r in games:
        by_team.setdefault(r["home_team"], {})[int(r["week"])] = int(r["home_score"])
        by_team.setdefault(r["away_team"], {})[int(r["week"])] = int(r["away_score"])
    xs, ys = [], []
    for t, wk in by_team.items():
        for w in sorted(wk):
            if w + 1 in wk:
                xs.append(wk[w])
                ys.append(wk[w + 1])
    pub = {c["id"]: c for c in corr.get("correlations", [])}
    hw = corr.get("home_win", {})
    checks = []

    def add(item, published, ours, tol=0.0, note=""):
        if published is None:
            status = "nothing published"
        else:
            status = "replicated" if abs(published - ours) <= tol + 1e-9 else "NOT replicated"
        checks.append({"item": item, "published": published, "referee": ours, "status": status, "note": note})

    add("Games used", corr.get("n_games"), len(games))
    add("C2 margin vs total, same game: r", pub.get("C2", {}).get("r"), round(pearson(margin, total), 4), 0.00006)
    add("C3 team points in consecutive weeks: pairs", pub.get("C3", {}).get("n"), len(xs),
        note="Referee definition: same team, week t and week t+1 both played.")
    add("C3 team points in consecutive weeks: r", pub.get("C3", {}).get("r"), round(pearson(xs, ys), 4), 0.00006)
    add("C5 division-game flag vs total: r", pub.get("C5", {}).get("r"), round(pearson(div, total), 4), 0.00006,
        note="Division flag taken from the dataset's div_game column.")
    add("C5 number of division games", 52 if "52 of 136" in pub.get("C5", {}).get("note", "") else None, int(sum(div)))
    add("Home wins", hw.get("home_wins"), sum(1 for m in margin if m > 0))
    add("Decided games", hw.get("decided_games"), sum(1 for m in margin if m != 0))
    add("Ties", hw.get("ties"), sum(1 for m in margin if m == 0))

    # Root cause test for C5: the official page groups clubs in fours inside each conference.
    groups = {}
    with open(os.path.join(ROOT, "data", "official", "nflcom_divisions_2026.txt")) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            for club in parts[2:]:
                groups[norm(club)] = (parts[0], parts[1])
    st = list(csv.DictReader(io.StringIO(git("show", f"{ref}:data/verified/standings_2026.csv"))))
    label = {norm(r["abbr"]): r["division"] for r in st}
    conf = {norm(r["abbr"]): r["conference"] for r in st}
    official_div = [1.0 if groups[r["home_team"]] == groups[r["away_team"]] else 0.0 for r in games]
    label_only = [1.0 if label[r["home_team"]] == label[r["away_team"]] else 0.0 for r in games]
    wrongly = [f"Week {r['week']}: {r['away_team']} ({conf[r['away_team']]} {label[r['away_team']]}) at {r['home_team']} ({conf[r['home_team']]} {label[r['home_team']]})"
               for r, a, b in zip(games, official_div, label_only) if b == 1.0 and a == 0.0]
    c5 = {"published_division_games": 52, "official_grouping_division_games": int(sum(official_div)),
          "dataset_flag_division_games": int(sum(div)),
          "games_counted_when_only_the_division_word_is_compared": int(sum(label_only)),
          "r_using_official_grouping": round(pearson(official_div, total), 4),
          "r_using_division_word_only": round(pearson(label_only, total), 4),
          "cross_conference_games_counted_as_division_games": wrongly,
          "cause": "Their standings file stores the division as East/North/South/West without the conference, and analysis/correlations.py "
                   "line 162-163 compares only that word, so an AFC East club playing an NFC East club is counted as a division game.",
          "official_source": "https://www.nfl.com/standings/division/2026/REG"}

    out = {"generated_by": "referee/analysis/replicate_25aa7696.py", "owner_session": "25aa7696", "ref": ref, "commit": sha,
           "c5_root_cause": c5,
           "official_spot_check": {"rows": official_rows, "matching": sum(r["result"] == "match" for r in official_rows)},
           "game_level": {"their_games": len(theirs), "dataset_games": len(ds), "matching": sum(r["result"] == "match" for r in game_rows),
                          "dataset_games_missing_from_their_file": missing, "rows": game_rows},
           "correlation_checks": checks}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print("ref", ref, sha[:10])
    print("official spot check:", out["official_spot_check"]["matching"], "/", len(official_rows))
    print("game level:", out["game_level"]["matching"], "/", len(theirs), "dataset games", len(ds), "missing", missing)
    for r in game_rows:
        if r["issues"]:
            print("  ", r["game"], r["issues"])
    print({k: v for k, v in c5.items() if k not in ("cause",)})
    for c in checks:
        print("  ", c["status"].ljust(16), c["item"], "| published", c["published"], "| referee", c["referee"])


if __name__ == "__main__":
    main()
