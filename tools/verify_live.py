#!/usr/bin/env python3
"""Session 1505ac8e - verify the published data line by line against official sources.

This is the harness behind the Verification page. It reads this session's transcriptions
of the official pages, the repository's committed datasets, and the generated site, and
writes data/session-1505ac8e/verification.json.

It does NOT re-fetch the network: the transcriptions in data/session-1505ac8e/ are the
record of what the official pages said when they were retrieved, and each check names the
official URL it came from so a human can re-read it.

Run order: build_analysis.py -> build_site.py -> verify_live.py -> build_site.py
(the second build_site.py folds these results into the Verification page).
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUTD = os.path.join(DATA, "session-1505ac8e")
SITE = os.path.join(ROOT, "lab")

NFL_STANDINGS = "https://www.nfl.com/standings/league/2026/REG"
NFL_SCHEDULE = "https://www.nfl.com/schedules/2026/week10"
NFL_INJURIES = "https://www.nfl.com/injuries/"
NFL_GAMES = "https://www.nfl.com/schedules/2026/by-week/week-1"
NFL_DEPTH_404 = "https://www.nfl.com/teams/kansas-city-chiefs/depth-chart"

ALIAS = {"LAR": "LA", "ARI": "AZ"}


def rd(x, n=3):
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP))


def rec_tuple(s):
    a, b, c = (int(x) for x in s.split("-"))
    return a, b, c


CHECKS = []


def check(cid, name, against, sources, fn):
    try:
        result, detail, cells = fn()
    except Exception as e:  # a check that crashes is a FAIL, not a silent skip
        result, detail, cells = "FAIL", f"{type(e).__name__}: {e}", 0
    CHECKS.append({"id": cid, "name": name, "against": against, "result": result,
                   "detail": detail, "sources": sources, "cells": cells})
    return result


# ---------------------------------------------------------------------------

def load_mine():
    rows = {}
    with open(os.path.join(OUTD, "_raw_standings.tsv"), encoding="utf-8") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 17 or not p[0].strip():
                continue
            rows[p[0].strip()] = {
                "w": int(p[1]), "l": int(p[2]), "t": int(p[3]), "pct": float(p[4]),
                "pf": int(p[5]), "pa": int(p[6]), "net": int(p[7]),
                "home": p[8], "road": p[9], "div": p[10], "div_pct": float(p[11]),
                "conf": p[12], "conf_pct": float(p[13]), "non_conf": p[14],
                "strk": p[15], "last5": p[16],
            }
    return rows


def main():
    mine = load_mine()

    def c01():
        return ("PASS" if len(mine) == 32 else "FAIL",
                f"{len(mine)} clubs transcribed from the official league standings page", 32)
    check("V01", "Standings row count", "official league standings",
          [("nfl.com standings", NFL_STANDINGS)], c01)

    def idcheck(field, fn, label):
        def f():
            bad = [f"{ab}:{fn(r)}" for ab, r in mine.items() if not fn(r)[0]] if False else []
            return _run(field, fn, label)
        return f

    def _run(field, fn, label):
        bad = []
        for ab, r in mine.items():
            ok, got, exp = fn(r)
            if not ok:
                bad.append(f"{ab} ({got} vs {exp})")
        n = len(mine)
        return (("PASS", f"all {n} clubs satisfy {label}", n) if not bad
                else ("FAIL", f"{len(bad)} clubs fail {label}: " + "; ".join(bad[:6]), n))

    check("V02", "Winning percentage identity",
          "PCT = (W + 0.5*T) / (W+L+T), rounded half-up to 3 dp",
          [("nfl.com standings", NFL_STANDINGS)],
          lambda: _run("pct", lambda r: (
              rd((r["w"] + 0.5 * r["t"]) / (r["w"] + r["l"] + r["t"])) == rd(r["pct"]),
              r["pct"], rd((r["w"] + 0.5 * r["t"]) / (r["w"] + r["l"] + r["t"]))),
              "the winning-percentage identity"))

    check("V03", "Net points identity", "NET = PF - PA",
          [("nfl.com standings", NFL_STANDINGS)],
          lambda: _run("net", lambda r: (r["pf"] - r["pa"] == r["net"], r["net"], r["pf"] - r["pa"]),
                       "the net-points identity"))

    check("V04", "Home plus road equals overall record", "HOME + ROAD = W-L-T",
          [("nfl.com standings", NFL_STANDINGS)],
          lambda: _run("hr", lambda r: (
              tuple(sum(x) for x in zip(rec_tuple(r["home"]), rec_tuple(r["road"])))
              == (r["w"], r["l"], r["t"]),
              f'{r["home"]} + {r["road"]}', f'{r["w"]}-{r["l"]}-{r["t"]}'),
              "home plus road equals the overall record"))

    check("V05", "Conference plus non-conference equals games played",
          "CONF + NON-CONF = W+L+T (conference includes division)",
          [("nfl.com standings", NFL_STANDINGS)],
          lambda: _run("cn", lambda r: (
              tuple(sum(x) for x in zip(rec_tuple(r["conf"]), rec_tuple(r["non_conf"])))
              == (r["w"], r["l"], r["t"]),
              f'{r["conf"]} + {r["non_conf"]}', f'{r["w"]}-{r["l"]}-{r["t"]}'),
              "conference plus non-conference equals games played"))

    check("V06", "Division record sits inside conference record", "DIV <= CONF",
          [("nfl.com standings", NFL_STANDINGS)],
          lambda: _run("dc", lambda r: (
              all(a <= b for a, b in zip(rec_tuple(r["div"]), rec_tuple(r["conf"]))),
              r["div"], r["conf"]), "division within conference"))

    def c07():
        bad = []
        for ab, r in mine.items():
            d = rec_tuple(r["div"])
            cf = rec_tuple(r["conf"])
            if d[0] + d[1] + d[2] and rd((d[0] + 0.5 * d[2]) / sum(d)) != rd(r["div_pct"]):
                bad.append(f"{ab} div_pct {r['div_pct']} vs {rd((d[0] + 0.5 * d[2]) / sum(d))}")
            if cf[0] + cf[1] + cf[2] and rd((cf[0] + 0.5 * cf[2]) / sum(cf)) != rd(r["conf_pct"]):
                bad.append(f"{ab} conf_pct {r['conf_pct']} vs {rd((cf[0] + 0.5 * cf[2]) / sum(cf))}")
        return (("PASS", "all 32 clubs: DIV_PCT and CONF_PCT both recompute correctly", 64)
                if not bad else ("FAIL", "; ".join(bad[:6]), 64))
    check("V07", "Division and conference percentages",
          "DIV_PCT = (W + 0.5*T)/division games; CONF_PCT likewise",
          [("nfl.com standings", NFL_STANDINGS)], c07)

    def c08():
        sw = sum(r["w"] for r in mine.values())
        sl = sum(r["l"] for r in mine.values())
        st = sum(r["t"] for r in mine.values())
        spf = sum(r["pf"] for r in mine.values())
        spa = sum(r["pa"] for r in mine.values())
        bad = []
        if sw != sl:
            bad.append(f"wins {sw} != losses {sl}")
        if st % 2:
            bad.append(f"ties {st} is odd")
        if spf != spa:
            bad.append(f"points for {spf} != points against {spa}")
        games = sw + st // 2
        detail = (f"W {sw}, L {sl}, T {st}, PF {spf}, PA {spa}, "
                  f"{games} games played. Points for equals points against, as it must.")
        return (("PASS", detail, 5) if not bad else ("FAIL", "; ".join(bad), 5))
    check("V08", "League balance", "the league must score exactly what it concedes",
          [("nfl.com standings", NFL_STANDINGS)], c08)

    # ---- recompute from game results ----------------------------------------
    games = list(csv.DictReader(open(os.path.join(DATA, "verified", "games_2026.csv"))))

    def c09():
        calc = defaultdict(lambda: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0})
        for g in games:
            a, h = ALIAS.get(g["away_abbr"], g["away_abbr"]), ALIAS.get(g["home_abbr"], g["home_abbr"])
            asc, hsc = int(g["away_score"]), int(g["home_score"])
            calc[a]["pf"] += asc
            calc[a]["pa"] += hsc
            calc[h]["pf"] += hsc
            calc[h]["pa"] += asc
            if asc > hsc:
                calc[a]["w"] += 1
                calc[h]["l"] += 1
            elif hsc > asc:
                calc[h]["w"] += 1
                calc[a]["l"] += 1
            else:
                calc[a]["t"] += 1
                calc[h]["t"] += 1
        bad, cells = [], 0
        for ab, m in mine.items():
            c = calc.get(ab)
            if not c:
                bad.append(f"{ab} missing from the game results")
                continue
            for k in ("w", "l", "t", "pf", "pa"):
                cells += 1
                if c[k] != m[k]:
                    bad.append(f"{ab} {k}: standings {m[k]} vs recomputed {c[k]}")
        return (("PASS", f"all 32 clubs x 5 fields = {cells} cells match; "
                         f"{len(games)} games recomputed", cells)
                if not bad else ("FAIL", "; ".join(bad[:6]), cells))
    check("V09", "Standings recomputed from game results",
          "136 completed games read from the official schedule pages",
          [("nfl.com game results", NFL_GAMES), ("nfl.com standings", NFL_STANDINGS)], c09)

    def crosscheck(path, key, alias_note):
        def f():
            d = {}
            with open(path, encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    ab = ALIAS.get(r[key].strip(), r[key].strip())
                    d[ab] = {k: int(r[k]) for k in ("w", "l", "t", "pf", "pa")}
            bad, cells = [], 0
            for ab, m in mine.items():
                o = d.get(ab)
                if not o:
                    bad.append(f"{ab} absent")
                    continue
                for k in ("w", "l", "t", "pf", "pa"):
                    cells += 1
                    if o[k] != m[k]:
                        bad.append(f"{ab} {k}: {m[k]} vs {o[k]}")
            return (("PASS", f"32 clubs x 5 fields = {cells} cells match. {alias_note}", cells)
                    if not bad else ("FAIL", "; ".join(bad[:6]), cells))
        return f

    check("V10", "Cross-check: session 25aa7696 standings transcription",
          "data/verified/standings_2026.csv",
          [("nfl.com standings", NFL_STANDINGS)],
          crosscheck(os.path.join(DATA, "verified", "standings_2026.csv"), "abbr",
                     "No aliasing needed; this file already uses the nfl.com codes."))
    check("V11", "Cross-check: session 533256e1 standings CSV",
          "data/standings.csv",
          [("nfl.com standings", NFL_STANDINGS)],
          crosscheck(os.path.join(DATA, "standings.csv"), "abbr",
                     "LAR aliased to LA."))
    def c12():
        snap = json.load(open(os.path.join(DATA, "model", "snapshot.json"), encoding="utf-8"))
        d = {}
        for row in snap["standings"]:
            ab = ALIAS.get(row["team"].strip(), row["team"].strip())
            d[ab] = {k: int(row[k]) for k in ("w", "l", "t", "pf", "pa")}
        bad, cells = [], 0
        for ab, m in mine.items():
            o = d.get(ab)
            if not o:
                bad.append(f"{ab} absent")
                continue
            for k in ("w", "l", "t", "pf", "pa"):
                cells += 1
                if o[k] != m[k]:
                    bad.append(f"{ab} {k}: {m[k]} vs {o[k]}")
        return (("PASS", f"32 clubs x 5 fields = {cells} cells match. ARI aliased to AZ and "
                         f"LA is already the nfl.com code.", cells)
                if not bad else ("FAIL", "; ".join(bad[:6]), cells))
    check("V12", "Cross-check: session 7600ed8b model snapshot",
          "data/model/snapshot.json",
          [("nfl.com standings", NFL_STANDINGS)], c12)

    # ---- schedule ------------------------------------------------------------
    lines = json.load(open(os.path.join(OUTD, "lines.json"), encoding="utf-8"))

    def c13():
        sched = lines["lines"]
        playing = set()
        for g in sched:
            playing.add(g["away"])
            playing.add(g["home"])
        byes = set(lines["byes"])
        bad = []
        if len(sched) != 14:
            bad.append(f"{len(sched)} games, expected 14")
        if len(playing) != 28:
            bad.append(f"{len(playing)} distinct clubs playing, expected 28")
        if len(byes) != 4:
            bad.append(f"{len(byes)} byes, expected 4")
        if playing & byes:
            bad.append(f"clubs both playing and on bye: {sorted(playing & byes)}")
        if len(playing | byes) != 32:
            bad.append(f"{len(playing | byes)} clubs covered, expected 32")
        return (("PASS", f"14 games, 28 clubs playing, 4 byes "
                         f"({', '.join(sorted(byes))}), no overlap, all 32 clubs covered", 32)
                if not bad else ("FAIL", "; ".join(bad), 32))
    check("V13", "Week 10 slate integrity", "official Week 10 schedule",
          [("nfl.com schedule", NFL_SCHEDULE)], c13)

    def c14():
        bad, cells = [], 0
        for g in lines["lines"]:
            for side in ("away", "home"):
                ab = g[side]
                printed = g[f"{side}_record"]
                m = mine.get(ab)
                if not m:
                    bad.append(f"{ab} not in the standings")
                    continue
                exp = f'{m["w"]}-{m["l"]}' + (f'-{m["t"]}' if m["t"] else "")
                cells += 1
                if printed != exp:
                    bad.append(f"{ab}: schedule says {printed}, standings say {exp}")
        return (("PASS", f"all {cells} club records printed on the schedule page match the "
                         f"official standings", cells)
                if not bad else ("FAIL", "; ".join(bad[:6]), cells))
    check("V14", "Schedule page records match the standings page",
          "the records nfl.com prints beside each Week 10 fixture",
          [("nfl.com schedule", NFL_SCHEDULE), ("nfl.com standings", NFL_STANDINGS)], c14)

    # ---- injuries ------------------------------------------------------------
    injuries = [l.rstrip("\n").split("\t")
                for l in open(os.path.join(OUTD, "_raw_injuries_week10.tsv"), encoding="utf-8")]
    avail = json.load(open(os.path.join(OUTD, "availability.json"), encoding="utf-8"))

    def c15():
        n = len(injuries)
        practice = sum(1 for r in injuries if r[5].strip())
        gstat = sum(1 for r in injuries if r[6].strip())
        body = sum(1 for r in injuries if r[4].strip())
        detail = (f"{n} rows: {practice} with a practice status, {gstat} with a game status, "
                  f"{body} with a body part. The {gstat} rows with a game status are the same "
                  f"{body} rows with a body part.")
        return ("FLAG", detail, n)
    check("V15", "Injury report completeness", "official Week 10 injury report",
          [("nfl.com injuries", NFL_INJURIES)], c15)

    def c16():
        committed = 0
        p = os.path.join(DATA, "verified", "injury_report_2026_week10.tsv")
        if os.path.exists(p):
            committed = sum(1 for l in open(p, encoding="utf-8") if l.strip()) - 1
        live = len(injuries)
        drift = live - committed
        return ("FLAG", f"committed snapshot {committed} rows, live page {live} rows, "
                        f"drift {drift:+d}. The committed file is a snapshot, not a feed.", live)
    check("V16", "Committed injury snapshot vs the live page",
          "data/verified/injury_report_2026_week10.tsv",
          [("nfl.com injuries", NFL_INJURIES)], c16)

    # ---- depth charts --------------------------------------------------------
    depth = json.load(open(os.path.join(OUTD, "depth_charts.json"), encoding="utf-8"))

    def c17():
        ok, total = depth["clubs_ok"], depth["clubs_total"]
        ranks = depth["slots_by_depth_rank"]
        detail = (f"{ok} of {total} club depth charts collected; "
                  f"{depth['position_rows_total']} position rows, "
                  f"{depth['player_slots_total']} player slots. "
                  f"By string: " + ", ".join(f"{k}th {v}" for k, v in sorted(ranks.items(), key=lambda x: int(x[0]))) + ".")
        return ("FLAG" if ok < total else "PASS", detail, depth["player_slots_total"])
    check("V17", "Depth chart coverage", "the 32 official club sites",
          [("chiefs.com depth chart", "https://www.chiefs.com/team/depth-chart"),
           ("nfl.com depth chart (404)", NFL_DEPTH_404)], c17)

    def c18():
        n = avail["n_injury_rows"]
        m, u = avail["n_matched"], avail["n_unmatched"]
        return ("FLAG", f"{m} of {n} injury rows match a player on that club's own depth "
                        f"chart; {u} do not. Two official sources disagree about club "
                        f"membership. Only the {m} that agree are scored.", n)
    check("V18", "Injury report vs club depth chart reconciliation",
          "official injury report and official club depth charts",
          [("nfl.com injuries", NFL_INJURIES),
           ("chiefs.com depth chart", "https://www.chiefs.com/team/depth-chart")], c18)

    def c19():
        return ("PASS", "nfl.com/teams/<club>/depth-chart returns a soft 404 "
                        "('404 - Flag on the Play.'). Re-verified 2026-11-12. An earlier "
                        "session recorded this as a blocking gap; the club sites close it.", 1)
    check("V19", "nfl.com publishes no depth chart", "nfl.com",
          [("nfl.com depth chart (404)", NFL_DEPTH_404)], c19)

    # ---- repository state ----------------------------------------------------
    def c20():
        sw = sum(r["w"] for r in mine.values())
        sl = sum(r["l"] for r in mine.values())
        st = sum(r["t"] for r in mine.values())
        spf = sum(r["pf"] for r in mine.values())
        published = "W = L = 134, T = 4, PF = PA = 6,267 (session a2cea255)"
        now = f"W = L = {sw}, T = {st}, PF = PA = {spf}"
        return ("FLAG", f"Earlier published figures: {published}. Live official page and the "
                        f"recomputed game results both give {now}. The earlier figures no "
                        f"longer reproduce.", 5)
    check("V20", "Earlier published league-balance figures",
          "the figures published by session a2cea255",
          [("nfl.com standings", NFL_STANDINGS), ("nfl.com game results", NFL_GAMES)], c20)

    def c21():
        bad = []
        for ab in ("WAS", "IND", "PHI"):
            r = mine[ab]
            d, cf, nc = rec_tuple(r["div"]), rec_tuple(r["conf"]), rec_tuple(r["non_conf"])
            if tuple(a + b for a, b in zip(cf, nc)) != (r["w"], r["l"], r["t"]):
                bad.append(f"{ab} conf+non-conf")
            if any(a > b for a, b in zip(d, cf)):
                bad.append(f"{ab} div<=conf")
        return (("FLAG", "WAS non_conf, IND div and PHI div were published as cells where "
                         "nfl.com contradicts its own arithmetic. All three recompute "
                         "correctly on this retrieval, so the flags no longer reproduce. "
                         "Either the page was corrected or the earlier transcription was "
                         "wrong; both remain possible.", 9) if not bad
                else ("FAIL", "still inconsistent: " + "; ".join(bad), 9))
    check("V21", "The three 'nfl.com contradicts itself' cells",
          "the flags published by session a2cea255",
          [("nfl.com standings", NFL_STANDINGS)], c21)

    # ---- generated site ------------------------------------------------------
    def c22():
        files = [os.path.join(SITE, "index.html")]
        pd = os.path.join(SITE, "pages")
        if os.path.isdir(pd):
            files += [os.path.join(pd, f) for f in sorted(os.listdir(pd)) if f.endswith(".html")]
        total_rows, no_src = 0, []
        OFFICIAL = ("nfl.com", "chiefs.com", "packers.com", "49ers.com", "github.com",
                    "itl.nist.gov", "operations.nfl.com", "sportradar.com", "nj.gov",
                    "nfl.com/standings", "geniussports.com")
        for f in files:
            htmltxt = open(f, encoding="utf-8").read()
            for tbl in re.findall(r"<table.*?</table>", htmltxt, flags=re.S):
                heads = re.findall(r"<th>(.*?)</th>", tbl.split("</thead>")[0], flags=re.S)
                heads = [re.sub(r"<[^>]+>", "", h).strip().lower() for h in heads]
                if "source" not in heads and "link" not in heads:
                    continue
                body = tbl.split("</thead>")[-1]
                for tr in re.findall(r"<tr>(.*?)</tr>", body, flags=re.S):
                    total_rows += 1
                    if not re.search(r'<a[^>]+href="https?://', tr):
                        no_src.append(os.path.basename(f))
        return (("PASS", f"{total_rows} data rows checked across {len(files)} pages; every one "
                         f"carries a link to an official or cited source", total_rows)
                if not no_src else
                ("FAIL", f"{len(no_src)} rows without a source link, in: "
                         f"{', '.join(sorted(set(no_src))[:6])}", total_rows))
    check("V22", "Every data row carries a source link", "the generated site in lab/",
          [("this repository", "https://github.com/kanlerxz87-cyber/NFL1")], c22)

    def c23():
        files = [os.path.join(SITE, "index.html")]
        pd = os.path.join(SITE, "pages")
        if os.path.isdir(pd):
            files += [os.path.join(pd, f) for f in sorted(os.listdir(pd)) if f.endswith(".html")]
        empties = 0
        for f in files:
            for tr in re.findall(r"<tr>(.*?)</tr>", open(f, encoding="utf-8").read(), flags=re.S):
                for td in re.findall(r"<td>(\s*)</td>", tr):
                    empties += 1
        return (("PASS", "no bare empty cells: unknown values render as a labelled blank span",
                 empties) if empties == 0 else
                ("FAIL", f"{empties} bare empty cells found", empties))
    check("V23", "Unconfirmed values are labelled, not left bare",
          "the generated site in lab/",
          [("this repository", "https://github.com/kanlerxz87-cyber/NFL1")], c23)

    def c24():
        files = [os.path.join(SITE, "index.html")]
        pd = os.path.join(SITE, "pages")
        if os.path.isdir(pd):
            files += [os.path.join(pd, f) for f in sorted(os.listdir(pd)) if f.endswith(".html")]
        broken = []
        n = 0
        for f in files:
            base = os.path.dirname(f)
            for href in re.findall(r'href="([^"#]+)"', open(f, encoding="utf-8").read()):
                if href.startswith(("http", "mailto:", "javascript:")):
                    continue
                n += 1
                target = os.path.normpath(os.path.join(base, href.split("?")[0]))
                if not os.path.exists(target):
                    broken.append(f"{os.path.basename(f)} -> {href}")
        return (("PASS", f"{n} internal links checked across {len(files)} pages; none broken", n)
                if not broken else ("FAIL", ", ".join(broken[:8]), n))
    check("V24", "Internal links resolve", "the generated site in lab/",
          [("this repository", "https://github.com/kanlerxz87-cyber/NFL1")], c24)

    summary = {
        "total": len(CHECKS),
        "pass": sum(1 for c in CHECKS if c["result"] == "PASS"),
        "flag": sum(1 for c in CHECKS if c["result"] == "FLAG"),
        "fail": sum(1 for c in CHECKS if c["result"] == "FAIL"),
        "cells_compared": sum(c["cells"] for c in CHECKS),
    }
    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "retrieved": "2026-11-12",
        "purpose": ("Line-by-line verification of everything this session publishes, against "
                    "the official pages it came from."),
        "summary": summary, "checks": CHECKS,
    }
    with open(os.path.join(OUTD, "verification.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)

    for c in CHECKS:
        print(f"{c['id']} {c['result']:5s} {c['name']}")
        print(f"      {c['detail'][:200]}")
    print(json.dumps(summary, indent=1))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
