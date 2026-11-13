#!/usr/bin/env python3
"""Compare the 2026-11-13 live nfl.com league standings transcription against every
standings-bearing file in the repo. Field-by-field; no inference; blanks stay blank."""
import csv, json, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HERE = os.path.dirname(__file__)

live = {}
with open(os.path.join(HERE, "live_standings.tsv"), newline="") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        live[r["club"]] = {k: r[k] for k in ("w", "l", "t", "pct", "pf", "pa", "net")}

report = {"checked_against": "https://www.nfl.com/standings/league/2026/reg (fetched 2026-11-13)",
          "clubs": len(live), "files": {}}

def cmp_rows(name, rows, colmap):
    """rows: iterable of dict; colmap: live-field -> row-key"""
    ok, bad = 0, []
    seen = set()
    for r in rows:
        club = r[colmap["club"]]
        seen.add(club)
        if club not in live:
            bad.append({"club": club, "issue": "not on live page"})
            continue
        diffs = {}
        for f in ("w", "l", "t", "pct", "pf", "pa", "net"):
            k = colmap.get(f)
            if not k:
                continue
            v = str(r.get(k, "")).strip()
            if v == "":
                diffs[f] = {"repo": "", "live": live[club][f], "note": "blank in repo"}
                continue
            if f == "pct":
                if abs(float(v) - float(live[club][f])) > 0.0006:
                    diffs[f] = {"repo": v, "live": live[club][f]}
            elif int(float(v)) != int(live[club][f]):
                diffs[f] = {"repo": v, "live": live[club][f]}
        if diffs:
            bad.append({"club": club, "diffs": diffs})
        else:
            ok += 1
    missing = sorted(set(live) - seen)
    report["files"][name] = {"rows": len(list(rows)) if not hasattr(rows, "__len__") else len(rows),
                             "rows_matching_live": ok, "mismatches": bad,
                             "clubs_missing_from_file": missing}

# 1. data/verified/standings_2026.csv
with open(os.path.join(ROOT, "data/verified/standings_2026.csv"), newline="") as fh:
    rows = list(csv.DictReader(fh))
cmp_rows("data/verified/standings_2026.csv", rows,
         {"club": "abbr", "w": "w", "l": "l", "t": "t", "pct": "pct", "pf": "pf", "pa": "pa", "net": "net_pts"})

# 2. data/verified/standings_2026_reg.tsv
with open(os.path.join(ROOT, "data/verified/standings_2026_reg.tsv"), newline="") as fh:
    rows = list(csv.DictReader(fh, delimiter="\t"))
cmp_rows("data/verified/standings_2026_reg.tsv", rows,
         {"club": "team_abbr", "w": "w", "l": "l", "t": "t", "pct": "pct", "pf": "pf", "pa": "pa", "net": "net_pts"})

# 3. data/verified/official_standings_2026.json (only team,w,l,t,pf,pa are transcribed;
#    pct/net are not columns in this file, and it writes ARI where the page logo code is AZ)
d = json.load(open(os.path.join(ROOT, "data/verified/official_standings_2026.json")))
rows = [dict(r, team={"ARI": "AZ"}.get(r["team"], r["team"])) for r in d["rows"]]
cmp_rows("data/verified/official_standings_2026.json", rows,
         {"club": "team", "w": "w", "l": "l", "t": "t", "pf": "pf", "pa": "pa"})

# 4. data/s9cb/official_standings_2026.csv
with open(os.path.join(ROOT, "data/s9cb/official_standings_2026.csv"), newline="") as fh:
    rows = list(csv.DictReader(fh))
cmp_rows("data/s9cb/official_standings_2026.csv", rows,
         {"club": "team_abbr", "w": "w", "l": "l", "t": "t", "pct": "pct", "pf": "pf", "pa": "pa", "net": "net_pts"})

# 5. data/derived_standings.json — derived per-game values: recompute from live totals
deriv = json.load(open(os.path.join(ROOT, "data/derived_standings.json")))
bad = []
ok = 0
for r in deriv:
    club = r["code"]
    lw, ll, lt = int(live[club]["w"]), int(live[club]["l"]), int(live[club]["t"])
    g = lw + ll + lt
    exp = {"games": g,
           "pf_pg": round(int(live[club]["pf"]) / g, 3),
           "pa_pg": round(int(live[club]["pa"]) / g, 3),
           "net_pg": round(int(live[club]["net"]) / g, 3)}
    diffs = {}
    for k, v in exp.items():
        got = r.get(k)
        if k == "games":
            if got != v:
                diffs[k] = {"repo": got, "live_recomputed": v}
        else:
            if got is None or abs(float(got) - v) > 0.006:
                diffs[k] = {"repo": got, "live_recomputed": v}
    if diffs:
        bad.append({"club": club, "diffs": diffs})
    else:
        ok += 1
report["files"]["data/derived_standings.json"] = {
    "rows": len(deriv), "rows_matching_live": ok, "mismatches": bad,
    "note": "compared after recomputing per-game values from live totals (no repo row copied)"}

# 6. data/model/snapshot.json standings (w,l,t,pct only)
snap = json.load(open(os.path.join(ROOT, "data/model/snapshot.json")))
rows = [dict(r, team={"ARI": "AZ", "LAR": "LA"}.get(r["team"], r["team"])) for r in snap["standings"]]
cmp_rows("data/model/snapshot.json (standings)", rows,
         {"club": "team", "w": "w", "l": "l", "t": "t", "pct": "pct"})

out = os.path.join(HERE, "standings_diff.json")
json.dump(report, open(out, "w"), indent=1)
print("clubs live:", len(live))
for f, r in report["files"].items():
    print(f"{f}: {r['rows_matching_live']}/{r['rows']} match, {len(r['mismatches'])} mismatching rows, missing: {r.get('clubs_missing_from_file')}")
for f, r in report["files"].items():
    for m in r["mismatches"][:5]:
        print(" ", f, m)
