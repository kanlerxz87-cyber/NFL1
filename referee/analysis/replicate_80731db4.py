#!/usr/bin/env python3
"""V3f - Replication of the numeric tables published by session 80731db4.

Their standings rows are compared with this session's own transcription of the official NFL.com
league standings; their per-game values and standings-based correlations are recomputed from the
official values. Read-only with respect to their files.

Run from the repository root:  python3 referee/analysis/replicate_80731db4.py [git-ref]   (default origin/arena/80731db4-nfl1)
Output: referee/data/replication_80731db4.json     (standard library only)
"""
import json
import math
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
REPO = os.path.join(ROOT, "..")
OUT = os.path.join(ROOT, "data", "replication_80731db4.json")
SRC = "https://www.nfl.com/standings/league/2026/REG"
CODE = {"AZ": "ARI", "LAR": "LA"}


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, check=True).stdout


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/arena/80731db4-nfl1"
    sha = git("rev-parse", ref).strip()
    official = {}
    with open(os.path.join(ROOT, "data", "official", "nflcom_standings_2026.txt")) as fh:
        for line in fh:
            p = line.split()
            if line.startswith("#") or len(p) < 6:
                continue
            w, l, t, pf, pa = map(int, p[1:6])
            g = w + l + t
            official[p[0]] = {"w": w, "l": l, "t": t, "pf": pf, "pa": pa, "net": pf - pa, "games": g, "pct": (w + t / 2) / g,
                              "pf_pg": pf / g, "pa_pg": pa / g, "net_pg": (pf - pa) / g}

    st = json.loads(git("show", f"{ref}:data/standings.json"))
    rows = []
    for r in st:
        code = CODE.get(r["code"], r["code"])
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
        rows.append({"key": r["team"], "published": f"{r['w']}-{r['l']}-{r['t']}, PF {r['pf']}, PA {r['pa']}, net {r['net']}, pct {r['pct']}",
                     "official": None if o is None else f"{o['w']}-{o['l']}-{o['t']}, PF {o['pf']}, PA {o['pa']}, net {o['net']}, pct {o['pct']:.3f}",
                     "result": "match" if not issues else "MISMATCH", "issues": issues, "source": SRC})
    missing = sorted(set(official) - {CODE.get(r["code"], r["code"]) for r in st})

    dv = json.loads(git("show", f"{ref}:data/derived_standings.json"))
    drows = []
    for r in dv:
        o = official.get(CODE.get(r["code"], r["code"]))
        issues = []
        if o is None:
            issues.append("club not found on the official page")
        else:
            if int(r["games"]) != o["games"]:
                issues.append(f"games: published {r['games']}, official {o['games']}")
            for k in ("pf_pg", "pa_pg", "net_pg"):
                if abs(float(r[k]) - o[k]) > 0.00051:
                    issues.append(f"{k}: published {r[k]}, recomputed {o[k]:.3f}")
        drows.append({"key": r["team"], "published": f"{r['games']} games, PF/g {r['pf_pg']}, PA/g {r['pa_pg']}, net/g {r['net_pg']}",
                      "recomputed": None if o is None else f"{o['games']} games, PF/g {o['pf_pg']:.3f}, PA/g {o['pa_pg']:.3f}, net/g {o['net_pg']:.3f}",
                      "result": "match" if not issues else "MISMATCH", "issues": issues, "source": SRC})

    co = json.loads(git("show", f"{ref}:data/correlations.json"))
    teams = sorted(official)
    crows = []
    for c in co:
        x, y = c.get("x"), c.get("y")
        if x in official[teams[0]] and y in official[teams[0]] and isinstance(c.get("r"), (int, float)):
            ours = round(pearson([official[t][x] for t in teams], [official[t][y] for t in teams]), 4)
            status = "replicated" if abs(ours - c["r"]) <= 0.00011 and c.get("n") == len(teams) else "NOT replicated"
        else:
            ours, status = None, "not replicable here"
        crows.append({"id": c.get("id"), "item": c.get("pair"), "n_published": c.get("n"), "published": c.get("r"), "referee": ours, "status": status, "source": SRC})

    out = {"generated_by": "referee/analysis/replicate_80731db4.py", "owner_session": "80731db4", "ref": ref, "commit": sha,
           "standings": {"file": "data/standings.json", "rows_checked": len(rows), "rows_matching": sum(r["result"] == "match" for r in rows),
                         "missing_official_teams": missing, "rows": rows},
           "per_game": {"file": "data/derived_standings.json", "rows_checked": len(drows), "rows_matching": sum(r["result"] == "match" for r in drows), "rows": drows},
           "correlations": {"file": "data/correlations.json", "rows": crows}}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print("ref", sha[:10], "standings", out["standings"]["rows_matching"], "/", len(rows), "missing", missing,
          "| per-game", out["per_game"]["rows_matching"], "/", len(drows))
    for r in rows + drows:
        if r["issues"]:
            print("  ", r["key"], r["issues"])
    for c in crows:
        print("  ", c["status"].ljust(18), c["id"], c["item"], "| published", c["published"], "n", c["n_published"], "| referee", c["referee"])


if __name__ == "__main__":
    main()
