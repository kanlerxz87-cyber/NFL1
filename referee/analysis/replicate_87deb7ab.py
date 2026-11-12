#!/usr/bin/env python3
"""V3g - Replication of the standings table published by session 87deb7ab (data/standings.json).

Per team: W, L, T, PCT, PF, PA, net, home and road records are compared with this session's own
transcription of the official NFL.com league standings; conference and four-team grouping with the
official division standings page. Division, conference and non-conference records are rebuilt from
the audited game rows using the official groupings (this session did not transcribe those columns
from the official page, so that part is a replication, not an official-source match).
Read-only with respect to their files.

Run from the repository root:  python3 referee/analysis/replicate_87deb7ab.py [git-ref]   (default origin/arena/87deb7ab-nfl1)
Output: referee/data/replication_87deb7ab.json     (standard library only)
"""
import csv
import json
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
REPO = os.path.join(ROOT, "..")
OUT = os.path.join(ROOT, "data", "replication_87deb7ab.json")
SRC = "https://www.nfl.com/standings/league/2026/REG"
CODE = {"AZ": "ARI", "LAR": "LA"}


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, check=True).stdout


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/arena/87deb7ab-nfl1"
    sha = git("rev-parse", ref).strip()
    official = {}
    with open(os.path.join(ROOT, "data", "official", "nflcom_standings_2026.txt")) as fh:
        for line in fh:
            p = line.split()
            if line.startswith("#") or len(p) < 8:
                continue
            w, l, t, pf, pa = map(int, p[1:6])
            official[p[0]] = {"w": w, "l": l, "t": t, "pf": pf, "pa": pa, "net": pf - pa, "pct": (w + t / 2) / (w + l + t), "home": p[6], "road": p[7]}
    group = {}
    with open(os.path.join(ROOT, "data", "official", "nflcom_divisions_2026.txt")) as fh:
        for line in fh:
            p = line.split()
            if line.startswith("#") or len(p) != 6:
                continue
            for c in p[2:]:
                group[CODE.get(c, c)] = (p[0], p[1])
    rec = {t: {"div": [0, 0, 0], "conf": [0, 0, 0], "non": [0, 0, 0]} for t in official}
    with open(os.path.join(ROOT, "data", "raw", "games.csv"), newline="") as fh:
        for g in csv.DictReader(fh):
            if g["season"] != "2026" or g["game_type"] != "REG" or g["home_score"] in ("", "NA"):
                continue
            h, a, m = g["home_team"], g["away_team"], int(g["home_score"]) - int(g["away_score"])
            kind = "div" if group[h] == group[a] else None
            for team, mm in ((h, m), (a, -m)):
                i = 0 if mm > 0 else 1 if mm < 0 else 2
                if kind:
                    rec[team]["div"][i] += 1
                rec[team]["conf" if group[h][0] == group[a][0] else "non"][i] += 1

    def fmt(x):
        return f"{x[0]}-{x[1]}-{x[2]}"

    data = json.loads(git("show", f"{ref}:data/standings.json"))
    members = {}
    for r in data["teams"]:
        members.setdefault(r["div"], set()).add(CODE.get(r["abbr"], r["abbr"]))
    rows, drows = [], []
    for r in data["teams"]:
        code = CODE.get(r["abbr"], r["abbr"])
        o = official.get(code)
        issues = []
        if o is None:
            issues.append("club not found on the official page")
        else:
            for k in ("w", "l", "t", "pf", "pa", "net"):
                if int(r[k]) != o[k]:
                    issues.append(f"{k}: published {r[k]}, official {o[k]}")
            if abs(float(r["pct"]) - o["pct"]) > 0.00051:
                issues.append(f"pct: published {r['pct']}, official {o['pct']:.3f}")
            for k in ("home", "road"):
                if r[k] != o[k]:
                    issues.append(f"{k}: published {r[k]}, official {o[k]}")
            if r["conf"] != group[code][0]:
                issues.append(f"conference: published {r['conf']}, official {group[code][0]}")
            if members[r["div"]] != {c for c, gk in group.items() if gk == group[code]}:
                issues.append("four-team grouping differs from the official page")
        rows.append({"key": r["name"], "published": f"{r['w']}-{r['l']}-{r['t']}, PF {r['pf']}, PA {r['pa']}, net {r['net']}, pct {r['pct']}, home {r['home']}, road {r['road']}, {r['conf']}",
                     "official": None if o is None else f"{o['w']}-{o['l']}-{o['t']}, PF {o['pf']}, PA {o['pa']}, net {o['net']}, pct {o['pct']:.3f}, home {o['home']}, road {o['road']}, {group[code][0]}",
                     "result": "match" if not issues else "MISMATCH", "issues": issues, "source": SRC})
        if o is not None:
            d = rec[code]
            di = [f"{lab}: published {r[k]}, rebuilt {fmt(d[q])}" for lab, k, q in (("division", "div_rec", "div"), ("conference", "conf_rec", "conf"), ("non-conference", "nonconf", "non")) if r[k] != fmt(d[q])]
            drows.append({"key": r["name"], "published": f"division {r['div_rec']}, conference {r['conf_rec']}, non-conference {r['nonconf']}",
                          "referee": f"division {fmt(d['div'])}, conference {fmt(d['conf'])}, non-conference {fmt(d['non'])}",
                          "status": "replicated" if not di else "NOT replicated", "issues": di, "source": "https://www.nfl.com/standings/division/2026/REG"})
    out = {"generated_by": "referee/analysis/replicate_87deb7ab.py", "owner_session": "87deb7ab", "ref": ref, "commit": sha,
           "standings": {"file": "data/standings.json", "rows_checked": len(rows), "rows_matching": sum(r["result"] == "match" for r in rows),
                         "missing_official_teams": sorted(set(official) - {CODE.get(r["abbr"], r["abbr"]) for r in data["teams"]}), "rows": rows},
           "split_records": {"rows_checked": len(drows), "rows_replicated": sum(r["status"] == "replicated" for r in drows), "rows": drows,
                             "not_checked": "streak and last-5 columns were not transcribed or rebuilt by this session"}}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print("ref", sha[:10], "standings", out["standings"]["rows_matching"], "/", len(rows), "| split records", out["split_records"]["rows_replicated"], "/", len(drows))
    for r in rows + drows:
        if r["issues"]:
            print("  ", r["key"], r["issues"])


if __name__ == "__main__":
    main()
