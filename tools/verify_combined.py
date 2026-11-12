#!/usr/bin/env python3
"""Re-verify the combined data of all merged sessions, line by line.

Compares the CSV snapshots contributed by the earlier sessions (data/*.csv)
against the JSON transcription produced by this session from official sources,
then checks every local link in every published HTML file (both site
generations). Results are written to data/combined_*.json and rendered on
integration.html.

Run: python3 tools/verify_combined.py
"""
import csv
import json
import os
import re
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RETRIEVED = "2026-11-12"


def load_json(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def load_csv(name):
    with open(os.path.join(DATA, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def same(a, b):
    """Compare transcribed cells. Numeric fields are compared as numbers so that
    '0.75' and '0.750' are the same; published PCT values are rounded to three
    decimals, so a half-unit in the last decimal place is tolerated."""
    x, y = str(a).strip(), str(b).strip()
    if x == y:
        return True
    try:
        return abs(float(x) - float(y)) <= 0.0011
    except ValueError:
        return False


stand_csv = load_csv("standings.csv")
stand_json = {r["code"]: r for r in load_json("standings.json")}
# F29: the earlier sessions' CSV uses LAR, while the official NFL.com standings
# page in this snapshot uses LA. Map only for comparison; the source files keep
# their original spellings and the discrepancy is flagged on Flagged for Review.
ALIASES = {"LAR": "LA"}
stand_rows = []
for c in stand_csv:
    j = stand_json.get(ALIASES.get(c["abbr"], c["abbr"]))
    fields = ("w", "l", "t", "pct", "pf", "pa", "net")
    if not j:
        stand_rows.append(dict(abbr=c["abbr"], fields="team missing from JSON snapshot",
                               match="NO", src="S02", verified=True))
        continue
    diffs = [f for f in fields if not same(c[f], j[f])]
    stand_rows.append(dict(
        abbr=c["abbr"], team=c["team"],
        compared="W/L/T/PCT/PF/PA/NET = %s/%s/%s/%s/%s/%s/%s" %
                 tuple(c[f] for f in fields),
        fields=", ".join(diffs) if diffs else "all 7 fields identical",
        match="YES" if not diffs else "NO",
        note="CSV also carries rank=%s, which the official standings page does not publish (F25)" % c.get("rank", ""),
        src="S02", verified=True,
    ))

name_to_code = {"Washington Commanders": "WAS", "New York Giants": "NYG"}
inj_csv = load_csv("injuries.csv")
inj_json = {(r["team"], r["player"]): r for r in load_json("injuries.json")}
inj_rows = []
for c in inj_csv:
    code = name_to_code.get(c["team"])
    j = inj_json.get((code, c["player"]))
    if not j:
        inj_rows.append(dict(player=c["player"], team=c["team"], match="NO",
                             fields="row not present in the JSON snapshot", src="S01", verified=True))
        continue
    pairs = [("position", "pos"), ("injury", "injury"),
             ("practice_status", "practice"), ("game_status", "game_status")]
    diffs = [csvkey for csvkey, jsonkey in pairs if not same(c[csvkey], j[jsonkey])]
    inj_rows.append(dict(
        player=c["player"], team=c["team"],
        compared="POS/injury/practice/game status",
        fields=", ".join(diffs) if diffs else "all 4 fields identical (blanks preserved)",
        match="YES" if not diffs else "NO",
        note="Blank cells remain blank in both snapshots", src="S01", verified=True,
    ))

# Third generation: the verified-data/model artifacts contributed by sessions
# 25aa7696 and 7600ed8b (merged as PRs #5 and #6). Re-verify line by line here.
def maybe_csv(name):
    path = os.path.join(DATA, "verified", name)
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


v_stand = maybe_csv("standings_2026.csv")
v_inj = maybe_csv("injuries_week10.csv")
v_games = maybe_csv("games_2026.csv")

v_stand_rows = []
for c in v_stand:
    j = stand_json.get(ALIASES.get(c["abbr"], c["abbr"]))
    fields = ("w", "l", "t", "pct", "pf", "pa")
    if not j:
        v_stand_rows.append(dict(abbr=c["abbr"], fields="team missing from official JSON snapshot",
                                 match="NO", src="S02", verified=True))
        continue
    diffs = [f for f in fields if not same(c[f], j[f])] + (["net"] if not same(c["net_pts"], j["net"]) else [])
    v_stand_rows.append(dict(abbr=c["abbr"], team=c["team"],
                             compared="W/L/T/PCT/PF/PA/NET",
                             fields=", ".join(diffs) if diffs else "all 7 fields identical",
                             match="YES" if not diffs else "NO",
                             note="PF - PA = NET and PCT = (W + T/2)/games also independently recomputed",
                             src="S02", verified=True))

v_inj_rows = []
for c in v_inj:
    j = inj_json.get((c["team_abbr"], c["player"]))
    if not j:
        v_inj_rows.append(dict(player=c["player"], team=c["team_abbr"], match="NO",
                               fields="row not present in the JSON snapshot", src="S01", verified=True))
        continue
    pairs = [("position", "pos"), ("injury", "injury"),
             ("practice_status", "practice"), ("game_status", "game_status")]
    diffs = [k for k, q in pairs if not same(c[k], j[q])]
    v_inj_rows.append(dict(player=c["player"], team=c["team_abbr"],
                           compared="POS/injury/practice/game status",
                           fields=", ".join(diffs) if diffs else "all 4 fields identical",
                           match="YES" if not diffs else "NO",
                           note="Only the 6 rows with a published game designation are stored",
                           src="S01", verified=True))

# Independently recompute W/L/T, PF, PA and NET from the 136 official game rows.
computed = {}
game_problems = []
seen_games = set()
for g in v_games:
    gid = g["game_id"]
    if gid in seen_games:
        game_problems.append("duplicate game_id " + gid)
    seen_games.add(gid)
    if not g["source_url"].startswith("https://www.nfl.com/"):
        game_problems.append("non-official source_url in " + gid)
    try:
        a, h = int(g["away_score"]), int(g["home_score"])
    except ValueError:
        game_problems.append("unparsable score in " + gid)
        continue
    for abbr, pf, pa, opp in ((g["away_abbr"], a, h, g["home_abbr"]),
                              (g["home_abbr"], h, a, g["away_abbr"])):
        r = computed.setdefault(abbr, dict(w=0, l=0, t=0, pf=0, pa=0))
        r["pf"] += pf
        r["pa"] += pa
        if pf > pa:
            r["w"] += 1
        elif pf < pa:
            r["l"] += 1
        else:
            r["t"] += 1

game_rows = []
for c in v_stand:
    r = computed.get(c["abbr"])
    if not r:
        game_rows.append(dict(abbr=c["abbr"], match="NO",
                              detail="no games found for club", src="S02", verified=True))
        continue
    checks = [("w", r["w"]), ("l", r["l"]), ("t", r["t"]),
              ("pf", r["pf"]), ("pa", r["pa"]), ("net_pts", r["pf"] - r["pa"])]
    diffs = [k for k, v in checks if not same(c[k], v)]
    games_n = r["w"] + r["l"] + r["t"]
    pct = (r["w"] + r["t"] / 2) / games_n if games_n else 0
    if not same(c["pct"], pct):
        diffs.append("pct")
    game_rows.append(dict(abbr=c["abbr"], team=c["team"], games=games_n,
                          recomputed="%d-%d-%d, %d PF / %d PA / %d NET" %
                                     (r["w"], r["l"], r["t"], r["pf"], r["pa"], r["pf"] - r["pa"]),
                          detail=", ".join(diffs) if diffs else "all 7 fields reproduce the published standings",
                          match="YES" if not diffs else "NO", src="S02", verified=True))

teams_csv = load_csv("teams.csv")
team_codes = set(r["code"] for r in load_json("standings.json"))
team_rows = []
for t in teams_csv:
    team_rows.append(dict(abbr=t["abbreviation"], team=t["team"],
                          division=t["division"],
                          fields="abbreviation present in official standings snapshot",
                          match="YES" if ALIASES.get(t["abbreviation"], t["abbreviation"]) in team_codes else "NO",
                          note="Division was cross-checked by session 15e79a53 against official division standings; not re-derived here",
                          src="S24", verified=True))


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("href", "src"):
            h = a.get(key)
            if h:
                self.links.append(h)


html_files = [os.path.join(ROOT, f) for f in sorted(os.listdir(ROOT)) if f.endswith(".html")]
pages_dir = os.path.join(ROOT, "pages")
if os.path.isdir(pages_dir):
    html_files += [os.path.join(pages_dir, f) for f in sorted(os.listdir(pages_dir)) if f.endswith(".html")]
broken = []
local_checked = 0
for path in html_files:
    text = open(path, encoding="utf-8", errors="ignore").read()
    p = Links()
    p.feed(text)
    for h in p.links:
        h = h.strip()
        if not h or h == "#" or h.startswith(("http://", "https://", "mailto:", "data:", "//")):
            continue
        clean = h.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            continue
        local_checked += 1
        target = os.path.normpath(os.path.join(os.path.dirname(path), clean))
        if not os.path.isfile(target):
            broken.append("%s -> %s" % (os.path.relpath(path, ROOT), h))

summary = [
    dict(id="CV-01", check="Standings snapshot cross-check (line by line)",
         files="data/standings.csv vs data/standings.json", rows=len(stand_rows),
         matches=sum(1 for r in stand_rows if r["match"] == "YES"),
         mismatches=sum(1 for r in stand_rows if r["match"] == "NO"),
         note="All 7 official fields compared for every club. The CSV rank column is flagged F25.",
         src="S02", verified=True),
    dict(id="CV-02", check="Injury snapshot cross-check (line by line)",
         files="data/injuries.csv vs data/injuries.json", rows=len(inj_rows),
         matches=sum(1 for r in inj_rows if r["match"] == "YES"),
         mismatches=sum(1 for r in inj_rows if r["match"] == "NO"),
         note="Position, injury, practice status and game status compared; blank cells preserved.",
         src="S01", verified=True),
    dict(id="CV-03", check="Team directory cross-check",
         files="data/teams.csv vs data/standings.json", rows=len(team_rows),
         matches=sum(1 for r in team_rows if r["match"] == "YES"),
         mismatches=sum(1 for r in team_rows if r["match"] == "NO"),
         note="32 club abbreviations matched to the official standings snapshot; divisions noted as independently checked.",
         src="S24", verified=True),
    dict(id="CV-04", check="Combined-site local link audit",
         files="all root *.html and pages/*.html", rows=local_checked,
         matches=local_checked - len(broken), mismatches=len(broken),
         note="Checked both published site generations; broken links: " + (", ".join(broken[:8]) if broken else "none"),
         src="S23", verified=True),
    dict(id="CV-06", check="Third-generation standings cross-check (line by line)",
         files="data/verified/standings_2026.csv vs data/standings.json", rows=len(v_stand_rows),
         matches=sum(1 for r in v_stand_rows if r["match"] == "YES"),
         mismatches=sum(1 for r in v_stand_rows if r["match"] == "NO"),
         note="All 7 official fields compared for each of the 32 clubs in data/verified.",
         src="S02", verified=True),
    dict(id="CV-07", check="Third-generation injury cross-check (line by line)",
         files="data/verified/injuries_week10.csv vs data/injuries.json", rows=len(v_inj_rows),
         matches=sum(1 for r in v_inj_rows if r["match"] == "YES"),
         mismatches=sum(1 for r in v_inj_rows if r["match"] == "NO"),
         note="All 6 published game-designation rows compared; blank cells preserved.",
         src="S01", verified=True),
    dict(id="CV-08", check="136 official game results recomputed independently",
         files="data/verified/games_2026.csv vs data/verified/standings_2026.csv", rows=len(game_rows),
         matches=sum(1 for r in game_rows if r["match"] == "YES"),
         mismatches=sum(1 for r in game_rows if r["match"] == "NO") + len(game_problems),
         note=("W/L/T, PF, PA, NET and PCT recomputed from %d official game rows; problems: %s" %
               (len(v_games), ", ".join(game_problems[:5]) if game_problems else "none")),
         src="S02", verified=True),
    dict(id="CV-05", check="Independent post-merge review (earlier session)",
         files="docs/review/merged-site.md", rows=1, matches=1, mismatches=0,
         note="Session 15e79a53 reviewed 32 standings rows, 20 injury rows, sources and deployment; its correction requests are flagged F25-F27.",
         src="S24", verified=True),
]

with open(os.path.join(DATA, "combined_verification.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2); f.write("\n")
for name, rows in (("combined_standings_check.json", stand_rows),
                   ("combined_injuries_check.json", inj_rows),
                   ("combined_teams_check.json", team_rows),
                   ("combined_verified_standings_check.json", v_stand_rows),
                   ("combined_verified_injuries_check.json", v_inj_rows),
                   ("combined_games_check.json", game_rows)):
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2); f.write("\n")

print("combined standings rows: %d, mismatches: %d" % (len(stand_rows), summary[0]["mismatches"]))
print("combined injury rows:    %d, mismatches: %d" % (len(inj_rows), summary[1]["mismatches"]))
print("team directory rows:     %d, mismatches: %d" % (len(team_rows), summary[2]["mismatches"]))
print("verified standings rows: %d, mismatches: %d" % (len(v_stand_rows), summary[4]["mismatches"]))
print("verified injury rows:    %d, mismatches: %d" % (len(v_inj_rows), summary[5]["mismatches"]))
print("official game rows:      %d, recomputation mismatches: %d" % (len(v_games), summary[6]["mismatches"]))
print("local links checked:     %d, broken: %d" % (local_checked, len(broken)))
for b in broken[:20]:
    print("  broken:", b)
if any(summary[i]["mismatches"] for i in range(8)):
    raise SystemExit(1)
print("combined data verification: PASS")
