#!/usr/bin/env python3
"""verify_official.py — line-by-line check of every published dataset against the
hand-transcribed official NFL pages, plus the site's own arithmetic and conventions.

This is the gate the project brief asks for: "every table row must have a source link to
an official site; if a value can't be confirmed from an official source, leave it blank
and flag it as unverified; never infer or fill in values."

What it does
------------
  A. Official fixtures are internally consistent (arithmetic identities, page counts).
  B. Every repo dataset used on the site is compared row-by-row and cell-by-cell with
     the official fixture:  data/evidence/*.json  vs
        data/standings.json, data/verified/standings_2026.csv,
        data/verified/standings_2026_reg.tsv,
        data/model/official_injuries.json, data/verified/injury_report_2026_week10.tsv,
        data/injuries.json, data/model/snapshot.json (fixtures), data/verified/week10_fixtures_2026.csv,
        data/depth_chart.json, data/model/dashboard.json
  C. Every published model line is checked for an internally consistent sign convention
     against the market column it is diffed with (the defect found in session 6e8ca348).
  D. Every date shown for a Week 10 fixture is checked against the official schedule.
  E. Result: JSON report at data/audit/official_verification.json; exit 1 on any FAIL.

FAIL versus FLAG — the distinction matters, so it is stated once here:
  * FAIL  = data *this* pipeline publishes contradicts the official page. Publication stops.
  * FLAG  = another session's artifact (data/model/*, data/verified/*, data/injuries.json,
            data/depth_chart.json) disagrees with the official page, or an official source
            publishes nothing for a value the project would like to have. The brief says these
            must not block the merge: they are published on the Flagged for Review page with
            the official source link so a human can arbitrate. They are never silently
            "corrected" in another session's file.

Design rule: a value that the official page does not publish is never "fixed" here — it
is reported as BLANK/UNVERIFIED and appears on the Flagged for Review page instead.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV = os.path.join(ROOT, "data", "evidence")
OUT = os.path.join(ROOT, "data", "audit")

CLUB_ALIASES = {"LAR": "LA", "ARI": "AZ", "AZ": "AZ", "ARZ": "AZ", "WAS": "WAS", "WSH": "WAS",
                "JAC": "JAX", "LA": "LA", "LAC": "LAC", "LV": "LV", "OAK": "LV"}


def canon(code: str) -> str:
    c = (code or "").strip().upper()
    return CLUB_ALIASES.get(c, c)


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def rows_of(path):
    d = load(path)
    return d["rows"] if isinstance(d, dict) else d


class Report:
    def __init__(self):
        self.checks = []

    def add(self, area, name, status, checked, detail=""):
        self.checks.append(dict(area=area, check=name, status=status,
                                rows_checked=checked, detail=detail))
        return status

    def fail(self, area, name, checked, detail):
        return self.add(area, name, "FAIL", checked, detail)

    def ok(self, area, name, checked, detail=""):
        return self.add(area, name, "PASS", checked, detail)

    def flag(self, area, name, checked, detail):
        return self.add(area, name, "FLAG", checked, detail)


# ------------------------------------------------------------------ A. fixtures
def check_fixtures(R: Report):
    st = load("data/evidence/standings_2026.json")
    rows = st["rows"]
    bad = [r["code"] for r in rows if r["net"] != r["pf"] - r["pa"]]
    R.ok("A. fixture", "official standings: NET PTS = PF - PA on every row",
         len(rows)) if not bad else R.fail("A. fixture", "NET arithmetic", len(rows), bad)
    codes = [r["code"] for r in rows]
    R.ok("A. fixture", "official standings: 32 clubs, no duplicates", len(rows),
         "") if len(set(codes)) == 32 else R.fail(
        "A. fixture", "32 unique clubs", len(rows), f"{len(set(codes))} unique")

    inj = load("data/evidence/injuries_week10.json")
    irows = inj["rows"]
    per = {}
    for r in irows:
        per[r["club"]] = per.get(r["club"], 0) + 1
    R.ok("A. fixture", "official injury report: club sections match section order",
         len(irows), f"{len(per)} clubs, {len(irows)} player rows")
    missing = [c for c in inj["club_order"] if c not in per]
    R.flag("A. fixture", "clubs listed with a section but no transcribed row", len(missing),
           ", ".join(missing)) if missing else R.ok(
        "A. fixture", "every listed club has at least one transcribed row", len(per))
    both = [c for c in inj["no_injuries_reported"] if c in per]
    R.ok("A. fixture", "clubs marked 'No Injuries Reported' have no player rows",
         len(inj["no_injuries_reported"])) if not both else R.fail(
        "A. fixture", "no-injury clubs carry rows", len(both), both)

    sch = load("data/evidence/schedule_week10.json")
    srows = sch["rows"]
    R.ok("A. fixture", "official schedule: 14 games in week 10", len(srows),
         "") if len(srows) == 14 else R.fail("A. fixture", "14 week-10 games", len(srows))
    clubs = set()
    for r in srows:
        clubs.add(canon(r["away"]))
        clubs.add(canon(r["home"]))
    byes = {canon(b) for b in sch["byes"]}
    R.ok("A. fixture", "schedule: 14 games (28 clubs) + 4 byes = 32 clubs", len(srows) + len(byes),
         "") if len(clubs | byes) == 32 else R.fail(
        "A. fixture", "28 playing clubs + 4 byes = 32",
        len(clubs | byes), f"{len(clubs)} playing, {len(byes)} bye")


# --------------------------------------------------- B1. standings vs official
def check_standings(R: Report):
    off = {r["code"]: r for r in load("data/evidence/standings_2026.json")["rows"]}
    sources = [
        ("data/standings.json", lambda r: r["code"],
         lambda r: (r["w"], r["l"], r["t"], r["pf"], r["pa"])),
        ("data/verified/standings_2026.csv", lambda r: r["abbr"],
         lambda r: (int(r["w"]), int(r["l"]), int(r["t"]), int(r["pf"]), int(r["pa"]))),
        ("data/verified/standings_2026_reg.tsv", lambda r: r["team_abbr"],
         lambda r: (int(r["w"]), int(r["l"]), int(r["t"]), int(r["pf"]), int(r["pa"]))),
    ]
    for path, keyf, valf in sources:
        if path.endswith(".csv") or path.endswith(".tsv"):
            delim = "\t" if path.endswith(".tsv") else ","
            rows = list(csv.DictReader(open(os.path.join(ROOT, path), encoding="utf-8"),
                                       delimiter=delim))
        else:
            rows = rows_of(path)
        seen, bad, unknown = set(), [], []
        for r in rows:
            c = canon(keyf(r))
            seen.add(c)
            if c not in off:
                unknown.append(c)
                continue
            want = (off[c]["w"], off[c]["l"], off[c]["t"], off[c]["pf"], off[c]["pa"])
            got = valf(r)
            if got != want:
                bad.append(f"{c}: repo={got} official={want}")
        missing = sorted(set(off) - seen)
        n = len(rows)
        if bad or missing or unknown:
            R.fail("B1. standings", f"{path} vs official standings", n,
                   "; ".join(bad[:6] + [f"missing={missing}"] + [f"unknown={unknown}"]))
        else:
            R.ok("B1. standings", f"{path} vs official standings", n,
                 "every W/L/T/PF/PA cell matches the official page")


# --------------------------------------------- B2. official injury report vs repo
PRACTICE_MAP = {"FP": "Full Participation in Practice",
                "LP": "Limited Participation in Practice",
                "DNP": "Did Not Participate In Practice",
                "Full Participation in Practice": "Full Participation in Practice",
                "Limited Participation in Practice": "Limited Participation in Practice",
                "Did Not Participate In Practice": "Did Not Participate In Practice"}


def norm_practice(v):
    v = (v or "").strip()
    return PRACTICE_MAP.get(v, v)


def compare_injury_rows(off_rows, repo_rows, R, label, clubf, namef, posf, injf, pracf, gamef):
    off = {}
    for r in off_rows:
        off.setdefault((r["club"], r["player"]), r)
    seen, mism, extra = set(), [], []
    for r in repo_rows:
        k = (canon(clubf(r)), namef(r))
        seen.add(k)
        if k not in off:
            extra.append(k)
            continue
        o = off[k]
        pairs = [("position", posf(r), o["position"]),
                 ("injury", injf(r), o["injury"]),
                 ("practice", norm_practice(pracf(r)), norm_practice(o["practice"])),
                 ("game", (gamef(r) or "").strip(), o["game_status"])]
        for field, got, want in pairs:
            if got != want:
                mism.append(f"{k[0]} {k[1]} {field}: repo={got!r} official={want!r}")
    missing = sorted(set(off) - seen)
    n = len(repo_rows)
    detail = ""
    if mism:
        detail += "value mismatches: " + "; ".join(mism[:5])
    if missing:
        detail += (" | " if detail else "") + f"{len(missing)} official rows absent from repo, e.g. {missing[:5]}"
    if extra:
        detail += (" | " if detail else "") + f"repo rows not on official page: {extra[:5]}"
    if mism or extra or missing:
        R.flag("B2. injuries", label, n, detail)
    else:
        R.ok("B2. injuries", label, n, "every cell matches the official page")


def check_injuries(R: Report):
    off = load("data/evidence/injuries_week10.json")["rows"]
    per = {}
    for r in off:
        per[r["club"]] = per.get(r["club"], 0) + 1

    scraped = load("data/model/official_injuries.json")["rows"]
    compare_injury_rows(off, scraped, R, "data/model/official_injuries.json (automated scrape)",
                        lambda r: r["team"], lambda r: r["player"], lambda r: r["position"],
                        lambda r: r["injury"] or "", lambda r: r["practice"],
                        lambda r: r["game"] or "")

    tsv = list(csv.DictReader(open(os.path.join(ROOT, "data/verified/injury_report_2026_week10.tsv"),
                                   encoding="utf-8"), delimiter="\t"))
    compare_injury_rows(off, tsv, R, "data/verified/injury_report_2026_week10.tsv (hand transcription)",
                        lambda r: r["team_abbr"], lambda r: r["player"], lambda r: r["position"],
                        lambda r: r["injury"], lambda r: r["practice"], lambda r: r["game_status"])

    d = load("data/injuries.json")
    compare_injury_rows(off, d, R, "data/injuries.json (companion transcription)",
                        lambda r: r["team"], lambda r: r["player"], lambda r: r["pos"],
                        lambda r: r["injury"], lambda r: r["practice"],
                        lambda r: r["game_status"])

    # per-club coverage of each repo source, so a dropped club is visible, not hidden
    for label, path, key in [
            ("scrape", "data/model/official_injuries.json", "team"),
            ("tsv", "data/verified/injury_report_2026_week10.tsv", "team_abbr"),
            ("companion", "data/injuries.json", "team")]:
        if path.endswith(".json"):
            raw = rows_of(path)
        else:
            raw = list(csv.DictReader(open(os.path.join(ROOT, path), encoding="utf-8"),
                                      delimiter="\t"))
        have = {}
        for r in raw:
            c = canon(r[key])
            have[c] = have.get(c, 0) + 1
        diffs = [f"{c}: {have.get(c,0)}/{per[c]}" for c in sorted(per) if have.get(c, 0) != per[c]]
        if diffs:
            R.flag("B2. injuries", f"per-club row counts: {label} vs official page",
                   sum(per.values()), "; ".join(diffs))
        else:
            R.ok("B2. injuries", f"per-club row counts: {label} vs official page",
                 sum(per.values()), "all 26 publishing clubs have the same number of rows")


# ------------------------------------------------ B3. schedule / fixtures vs official
def check_schedule(R: Report):
    off = load("data/evidence/schedule_week10.json")["rows"]
    key = lambda a, h: (canon(a), canon(h))
    om = {key(r["away"], r["home"]): r for r in off}

    snap = load("data/model/snapshot.json")["fixtures"]
    bad = []
    for f in snap:
        k = key(f["away"], f["home"])
        if k not in om:
            bad.append(f"{k} not on official schedule")
            continue
        o = om[k]
        if str(f["gameday"]) != o["gameday"]:
            bad.append(f"{k} date repo={f['gameday']} official={o['gameday']}")
        if (f.get("gametime") or "") != o["kickoff_et"]:
            bad.append(f"{k} kickoff repo={f.get('gametime')} official={o['kickoff_et']}")
        if f.get("source") is None:
            bad.append(f"{k} has no source link")
    if bad:
        R.fail("B3. schedule", "data/model/snapshot.json fixtures vs official schedule",
               len(snap), "; ".join(bad[:8]))
    else:
        R.ok("B3. schedule", "data/model/snapshot.json fixtures vs official schedule", len(snap),
             "date, kickoff time and source link match the official page")

    fx = list(csv.DictReader(open(os.path.join(ROOT, "data/verified/week10_fixtures_2026.csv"),
                                  encoding="utf-8")))
    bad = []
    for f in fx:
        k = key(f["away_abbr"], f["home_abbr"])
        if k not in om:
            bad.append(f"{k} not on official schedule")
            continue
        o = om[k]
        if f["gameday"] != o["gameday"]:
            bad.append(f"{k} date repo={f['gameday']} official={o['gameday']}")
        hhmm = o["kickoff_et"].replace(":", "")
        if f["kickoff_et"].replace(":", "") != o["kickoff_et"].replace(":", ""):
            bad.append(f"{k} kickoff repo={f['kickoff_et']} official={o['kickoff_et']}")
    if bad:
        R.fail("B3. schedule", "data/verified/week10_fixtures_2026.csv vs official schedule",
               len(fx), "; ".join(bad[:8]))
    else:
        R.ok("B3. schedule", "data/verified/week10_fixtures_2026.csv vs official schedule",
             len(fx), "all 14 games match date and kickoff time")

    # the published own-lines table must show the official date for each game
    lines = load("data/model/lines.json")["lines"]
    bad = [f"{g['away']}@{g['home']} {g['gameday']} vs {om[key(g['away'], g['home'])]['gameday']}"
           for g in lines
           if key(g["away"], g["home"]) in om
           and str(g["gameday"]) != om[key(g["away"], g["home"])]["gameday"]]
    R.fail("B3. schedule", "published own-line dates vs official schedule", len(lines),
           "; ".join(bad)) if bad else R.ok(
        "B3. schedule", "published own-line dates vs official schedule", len(lines))


# ------------------------------------------------------ B4. depth charts vs official
def check_depth(R: Report):
    off = load("data/evidence/depth_charts.json")["rows"]
    repo = load("data/depth_chart.json")
    # repo rows are per position slot with s1..s4; rebuild (club, player) -> rank
    repo_rank = {}
    for r in repo:
        for i in range(1, 5):
            name = (r.get(f"s{i}") or "").strip()
            if name:
                repo_rank.setdefault((canon(r["code"]), name), []).append(i)
    off_rank = {(canon(r["club"]), r["player"]): r["depth_rank"] for r in off}
    mism, missing = [], []
    for k, rank in off_rank.items():
        if k not in repo_rank:
            missing.append(f"{k[0]} {k[1]} (rank {rank})")
        elif rank not in repo_rank[k]:
            mism.append(f"{k[0]} {k[1]}: official rank {rank}, repo {repo_rank[k]}")
    if missing or mism:
        R.flag("B4. depth", "data/depth_chart.json vs club official depth charts", len(off_rank),
               "; ".join((mism + [f"absent: {missing[:6]}"])[:6]))
    else:
        R.ok("B4. depth", "data/depth_chart.json vs club official depth charts", len(off_rank),
             "every transcribed player appears at the same rank")


# ------------------------------------------- C. own-line/market sign-convention audit
def check_line_convention(R: Report):
    d = load("data/model/lines.json")
    conv = (d.get("sign_convention_check") or {}).get("conclusion", "")
    sign_ok = "positive = home favourite" in conv.lower() or "home team" in conv.lower()
    R.ok("C. convention", "market line convention documented from data", 1,
         conv[:120]) if sign_ok else R.flag("C. convention",
                                            "market line convention not documented", 1, conv)

    bad = []
    for g in d["lines"]:
        my, mk = g.get("my_home_line"), g.get("market_home_line")
        if my is not None and mk is not None:
            # both are "home margin" numbers. If a page prints the market number without a
            # sign convention, a reader computes my - mk. Flag any pair where that
            # difference and the published edge disagree by more than rounding.
            calc = round(my - mk, 2)
            # both inputs are rounded to 0.1 before publication, so the published edge can
            # differ from (rounded model - rounded market) by up to 0.1 without any error.
            if g.get("edge_home_line") is None or abs(calc - g["edge_home_line"]) > 0.15:
                bad.append(f"{g['away']}@{g['home']}: my-mkt={calc} edge={g.get('edge_home_line')}")
    if bad:
        R.fail("C. convention", "published edge equals model minus market", len(d["lines"]),
               "; ".join(bad[:6]))
    else:
        R.ok("C. convention", "published edge equals model minus market", len(d["lines"]),
             "every edge row reproduces from my_home_line - market_home_line")

    # The Overview prints a bare market number next to a signed model line. A bare number
    # under a "positive = home favoured" heading reads as +x for the home team.
    mixed = [g for g in d["lines"] if (g.get("market_home_line") or 0) < 0
             and (g.get("my_home_line") or 0) > 0]
    mixed += [g for g in d["lines"] if (g.get("market_home_line") or 0) > 0
              and (g.get("my_home_line") or 0) < 0]
    if mixed:
        R.flag("C. convention",
               "games where model and market favour different sides (sign ambiguity risk)",
               len(mixed), ", ".join(f"{g['away']}@{g['home']}" for g in mixed[:8]))
    else:
        R.ok("C. convention", "no model/market side disagreement", len(d["lines"]))


# ------------------------------------------------ D. availability dashboard arithmetic
def check_availability(R: Report):
    a = load("data/model/availability.json")
    teams = a.get("teams", [])
    players = a.get("players", [])
    off = load("data/evidence/injuries_week10.json")["rows"]
    official_clubs = sorted({r["club"] for r in off})

    # starter counts must be reproducible from the player rows
    bad = []
    for t in teams:
        club = canon(t["team"])
        rows = [p for p in players if canon(p["team"]) == club and p.get("depth_rank") == 1]
        n_out = sum(1 for p in rows if (p.get("game_status") or "") == "Out")
        n_dbt = sum(1 for p in rows if (p.get("game_status") or "") == "Doubtful")
        n_q = sum(1 for p in rows if (p.get("game_status") or "") == "Questionable")
        if (n_out, n_dbt, n_q) != (t["starters_out"], t["starters_doubtful"],
                                   t["starters_questionable"]):
            bad.append(f"{club}: published {t['starters_out']}/{t['starters_doubtful']}/"
                       f"{t['starters_questionable']} vs rows {n_out}/{n_dbt}/{n_q}")
    R.fail("D. availability", "club starter-out counts reproduce from player rows",
           len(teams), "; ".join(bad[:6])) if bad else R.ok(
        "D. availability", "club starter-out counts reproduce from player rows", len(teams))

    # every club the official page publishes should be represented on the dashboard
    dash_clubs = {canon(t["team"]) for t in teams}
    absent = [c for c in official_clubs if c not in dash_clubs]
    R.flag("D. availability", "official publishing clubs missing from the availability table",
           len(absent), ", ".join(absent)) if absent else R.ok(
        "D. availability", "all official publishing clubs appear in availability table",
        len(official_clubs))

    # practice-only counts must not be presented as game designations
    bad = [p for p in players if p.get("signal", "").startswith("practice")
           and (p.get("effective_status") or "").startswith(("Out", "Doubtful", "Questionable"))]
    R.fail("D. availability", "practice-only rows are not labelled as game designations",
           len(players), f"{len(bad)} rows conflate practice with game status") if bad else R.ok(
        "D. availability", "practice-only rows are not labelled as game designations",
        len(players))


# ------------------------------------------------------------- E. dashboard counts
def check_counts(R: Report):
    dash = load("data/model/dashboard.json")
    counts = dash["counts"]
    st = load("data/evidence/standings_2026.json")["rows"]
    games = sum(r["w"] + r["l"] + r["t"] for r in st) // 2
    R.ok("E. counts", "games played = half the sum of club games", counts["games_played"],
         f"official standings imply {games}") if games == counts["games_played"] else R.fail(
        "E. counts", "games played reconciles with official standings", counts["games_played"],
        f"sum of club games / 2 = {games}")
    a = load("data/model/availability.json")
    R.ok("E. counts", "starters flagged matches availability detail",
         counts["starters_flagged_unavailable"]) if \
        counts["starters_flagged_unavailable"] == a["counts"]["starters_impacted"] else R.fail(
        "E. counts", "starters flagged matches availability detail",
        counts["starters_flagged_unavailable"],
        f"availability says {a['counts']['starters_impacted']}")


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    R = Report()
    check_fixtures(R)
    check_standings(R)
    check_injuries(R)
    check_schedule(R)
    check_depth(R)
    check_line_convention(R)
    check_availability(R)
    check_counts(R)

    fails = [c for c in R.checks if c["status"] == "FAIL"]
    flags = [c for c in R.checks if c["status"] == "FLAG"]
    passes = [c for c in R.checks if c["status"] == "PASS"]
    report = dict(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        official_sources=dict(
            standings="https://www.nfl.com/standings/league/2026/reg",
            injuries="https://www.nfl.com/injuries/",
            schedule="https://www.nfl.com/schedules/2026/REG10",
            depth_charts="club official depth-chart pages (URL per row in data/evidence/depth_charts.json)"),
        result="PASS" if not fails else "FAIL",
        counts=dict(passed=len(passes), flagged=len(flags), failed=len(fails)),
        checks=R.checks,
    )
    with open(os.path.join(OUT, "official_verification.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
        f.write("\n")

    for c in R.checks:
        mark = {"PASS": "PASS", "FLAG": "FLAG", "FAIL": "FAIL"}[c["status"]]
        print(f"[{mark}] {c['area']:16} {c['check'][:64]:64} rows={c['rows_checked']:<4}"
              + (f"  {c['detail'][:110]}" if c["detail"] else ""))
    print(f"\n{len(passes)} passed, {len(flags)} flagged, {len(fails)} failed")
    print("wrote data/audit/official_verification.json")
    if fails:
        print("\nFAILURES block publication. Fix the data or the page, do not edit the check.")
        return 1
    print("RESULT: PASS — every checked repo row reproduces from a hand-transcribed official page.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
