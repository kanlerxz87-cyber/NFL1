#!/usr/bin/env python3
"""V3a - Re-check the data tables that other sessions published on `main` against official pages.

Read-only: the files under data/ belong to session 533256e1 and are never modified here.
Each row of each table is compared with this session's own transcription of the official nfl.com page.

Run from the repository root:  python3 referee/analysis/replicate_main_data.py
Output: referee/data/replication_main_data.json     (standard library only)
"""
import csv
import json
import os
import subprocess

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
REPO = os.path.join(ROOT, "..")
OFF = os.path.join(ROOT, "data", "official")
OUT = os.path.join(ROOT, "data", "replication_main_data.json")
CODE = {"AZ": "ARI", "ARI": "ARI", "LAR": "LA", "LA": "LA"}  # map published abbreviations to dataset codes


def norm(code):
    return CODE.get(code, code)


def read_csv_skip_comments(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(line for line in fh if not line.startswith("#")))


def blob_sha(path):
    try:
        return subprocess.run(["git", "-C", REPO, "rev-parse", f"HEAD:{path}"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def main():
    results = []

    # ---- data/standings.csv -------------------------------------------------------------
    official = {}
    src = "https://www.nfl.com/standings/league/2026/REG"
    for line in open(os.path.join(OFF, "nflcom_standings_2026.txt")):
        if line.startswith("#") or not line.strip():
            continue
        t, w, l, tie, pf, pa, _, _ = line.split()
        official[t] = {"w": int(w), "l": int(l), "t": int(tie), "pf": int(pf), "pa": int(pa)}
    path = os.path.join(REPO, "data", "standings.csv")
    rows = []
    if os.path.exists(path):
        for r in csv.DictReader(open(path, newline="")):
            o = official.get(norm(r["abbr"]))
            pub = {k: int(r[k]) for k in ("w", "l", "t", "pf", "pa")}
            issues = []
            if o is None:
                issues.append("team not found in official transcription")
            else:
                issues += [f"{k}: published {pub[k]}, official {o[k]}" for k in pub if pub[k] != o[k]]
                if int(r["net"]) != o["pf"] - o["pa"]:
                    issues.append(f"net: published {r['net']}, official PF-PA {o['pf'] - o['pa']}")
                g = o["w"] + o["l"] + o["t"]
                exp_pct = f"{(o['w'] + 0.5 * o['t']) / g:.3f}"
                # nfl.com shows .313 for 2-5-1 and .688 for 5-2-1 (half-up); allow either rounding of an exact .xxx5
                if abs(float(r["pct"]) - (o["w"] + 0.5 * o["t"]) / g) > 0.00051:
                    issues.append(f"pct: published {r['pct']}, expected {exp_pct}")
            if r["abbr"] != norm(r["abbr"]) and r["abbr"] == "LAR":
                note = "abbreviation LAR is not the nfl.com club code (LA); values unaffected"
            else:
                note = ""
            rows.append({"key": r["team"], "published": f"{r['w']}-{r['l']}-{r['t']}, PF {r['pf']}, PA {r['pa']}, net {r['net']}, pct {r['pct']}",
                         "official": None if o is None else f"{o['w']}-{o['l']}-{o['t']}, PF {o['pf']}, PA {o['pa']}, net {o['pf'] - o['pa']}",
                         "result": "match" if not issues else "MISMATCH", "issues": issues, "note": note, "source": src})
        results.append({"file": "data/standings.csv", "owner": "533256e1", "blob": blob_sha("data/standings.csv"),
                        "what": "2026 league standings snapshot (W, L, T, PCT, PF, PA, NET)", "official_source": src,
                        "rows": rows, "rows_checked": len(rows), "rows_matching": sum(r["result"] == "match" for r in rows),
                        "missing_official_teams": sorted(set(official) - {norm(r2["abbr"]) for r2 in csv.DictReader(open(path, newline=""))})})

    # ---- data/teams.csv -----------------------------------------------------------------
    src = "https://www.nfl.com/standings/division/2026/REG"
    conf, group = {}, {}
    for line in open(os.path.join(OFF, "nflcom_divisions_2026.txt")):
        if line.startswith("#") or not line.strip():
            continue
        c, n, *teams = line.split()
        for t in teams:
            conf[norm(t)] = c
            group[norm(t)] = frozenset(norm(x) for x in teams)
    path = os.path.join(REPO, "data", "teams.csv")
    rows = []
    if os.path.exists(path):
        pub = list(csv.DictReader(open(path, newline="")))
        by_div = {}
        for r in pub:
            by_div.setdefault(r["division"], set()).add(norm(r["abbreviation"]))
        for r in pub:
            code = norm(r["abbreviation"])
            issues = []
            if code not in conf:
                issues.append("team not found in official transcription")
            else:
                if r["conference"] != conf[code]:
                    issues.append(f"conference: published {r['conference']}, official {conf[code]}")
                if by_div[r["division"]] != group[code]:
                    issues.append(f"division grouping differs: published {sorted(by_div[r['division']])}, official {sorted(group[code])}")
                if not r["division"].startswith(conf[code]):
                    issues.append(f"division label {r['division']} does not start with conference {conf[code]}")
            rows.append({"key": r["team"], "published": f"{r['conference']} / {r['division']}",
                         "official": None if code not in conf else f"{conf[code]} / grouped with {', '.join(sorted(group[code] - {code}))}",
                         "result": "match" if not issues else "MISMATCH", "issues": issues,
                         "note": "Conference and four-team grouping confirmed. The division name itself (East/North/South/West) is not in the fetched page text, so the label is not confirmed by this check.",
                         "source": src})
        results.append({"file": "data/teams.csv", "owner": "533256e1", "blob": blob_sha("data/teams.csv"),
                        "what": "32 teams with conference and division", "official_source": src, "rows": rows,
                        "rows_checked": len(rows), "rows_matching": sum(r["result"] == "match" for r in rows),
                        "missing_official_teams": sorted(set(conf) - {norm(r["abbreviation"]) for r in pub})})

    # ---- data/injuries.csv --------------------------------------------------------------
    src = "https://www.nfl.com/injuries/"
    off_rows = read_csv_skip_comments(os.path.join(OFF, "nflcom_injuries_2026_wk10_WAS_NYG.csv"))
    off_by = {(r["team"], r["player"]): r for r in off_rows}
    path = os.path.join(REPO, "data", "injuries.csv")
    rows = []
    if os.path.exists(path):
        pub = list(csv.DictReader(open(path, newline="")))
        for r in pub:
            o = off_by.get((r["team"], r["player"]))
            issues = []
            if o is None:
                issues.append("player not found in official transcription")
            else:
                issues += [f"{k}: published '{r[k]}', official '{o[k]}'" for k in ("position", "injury", "practice_status", "game_status") if r[k] != o[k]]
            show = lambda x: f"{x['position']} | {x['injury'] or '(blank)'} | {x['practice_status']} | {x['game_status'] or '(blank)'}"
            rows.append({"key": f"{r['team']} - {r['player']}", "published": show(r), "official": None if o is None else show(o),
                         "result": "match" if not issues else "MISMATCH", "issues": issues, "note": "", "source": src})
        missing = sorted(f"{t} - {p}" for (t, p) in set(off_by) - {(r["team"], r["player"]) for r in pub})
        results.append({"file": "data/injuries.csv", "owner": "533256e1", "blob": blob_sha("data/injuries.csv"),
                        "what": "2026 Week 10 injury report rows, Commanders at Giants only", "official_source": src, "rows": rows,
                        "rows_checked": len(rows), "rows_matching": sum(r["result"] == "match" for r in rows),
                        "missing_official_teams": missing})

    with open(OUT, "w") as fh:
        json.dump({"generated_by": "referee/analysis/replicate_main_data.py", "tables": results}, fh, indent=1)
    for t in results:
        print(f"{t['file']}: {t['rows_matching']}/{t['rows_checked']} rows match; missing: {t['missing_official_teams']}")
        for r in t["rows"]:
            if r["issues"]:
                print("   ", r["key"], r["issues"])


if __name__ == "__main__":
    main()
