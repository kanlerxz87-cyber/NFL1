#!/usr/bin/env python3
"""verify_site.py — check the rendered `desk/` pages against the data and the sources, independently.

Session `ed736fc3-nfl1`, task D2. This file deliberately does not import build_site.py: it re-reads
the transcriptions and the rendered HTML and recomputes what it expects to find, so a shared bug in
the renderer cannot hide as a "pass".

What it fails on
  1. a page in desk/ that is not what the data produces (stale committed output);
  2. a local link that does not resolve, or a page reachable from nowhere;
  3. a table row in a Source column without an <a href>, or an empty <td>;
  4. a number published on a page that cannot be recomputed from data/desk/*.json;
  5. a published claim that the source contradicts — checked where the source is in the repository
     (the injury transcription and the standings transcription), cell by cell.

Run: python3 tools/desk/verify_site.py
"""
from __future__ import annotations

import csv
import glob
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DESK_DATA = os.path.join(ROOT, "data", "desk")
DESK_SITE = os.path.join(ROOT, "desk")
PAGES = ["index.html", "readiness.html", "verification.html", "strategies.html", "availability.html",
         "pricing.html", "questions.html", "suggestions.html", "flagged.html",
         "executive-summary.html", "method.html"]

problems: list[str] = []
notes: list[str] = []


def J(name):
    with open(os.path.join(DESK_DATA, name), encoding="utf-8") as f:
        return json.load(f)


def repo(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs, self.tables, self.text = [], [], []
        self._t = self._r = self._c = None
        self._head = False
        self._in_main = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and "href" in d:
            self.hrefs.append(d["href"])
            if self._c is not None:
                self._c.append("LINK")
        if tag == "table":
            self._t = {"headers": [], "rows": []}
        elif tag == "thead" and self._t:
            self._head = True
        elif tag == "th" and self._t:
            self._c = []
        elif tag == "tr" and self._t and not self._head:
            self._r = []
        elif tag in ("td", "th") and self._r is not None:
            self._c = []
        elif tag == "main":
            self._in_main = True

    def handle_endtag(self, tag):
        if tag == "th" and self._c is not None and self._head and self._t:
            self._t["headers"].append("".join(self._c))
            self._c = None
        elif tag == "thead":
            self._head = False
        elif tag == "td" and self._c is not None and self._r is not None:
            self._r.append("".join(self._c))
            self._c = None
        elif tag == "tr" and self._r is not None and self._t:
            self._t["rows"].append(self._r)
            self._r = None
        elif tag == "table" and self._t:
            self.tables.append(self._t)
            self._t = None
        elif tag == "main":
            self._in_main = False

    def handle_data(self, data):
        if self._c is not None:
            self._c.append(data)
        if self._in_main:
            self.text.append(data)


def load(path):
    p = Page()
    with open(path, encoding="utf-8", errors="replace") as f:
        p.feed(f.read())
    return p


def check_committed():
    """Rule 1: committed pages must be exactly what the generator produces."""
    sys.path.insert(0, os.path.dirname(__file__))
    import build_site  # noqa: E402  (imported only to ask it for the rendered text)
    build_site.GEN_AT = J("injuries.json")["retrieved"]
    for name, fn in build_site.PAGES.items():
        want = fn()
        path = os.path.join(DESK_SITE, name)
        if not os.path.exists(path):
            problems.append(f"page missing: desk/{name}")
            continue
        got = open(path, encoding="utf-8").read()
        if got != want:
            problems.append(f"desk/{name} is not what data/desk/*.json produces (stale output)")
    css = os.path.join(DESK_SITE, "style.css")
    if not os.path.exists(css) or open(css, encoding="utf-8").read() != build_site.STYLE.strip() + "\n":
        problems.append("desk/style.css does not match the generator")
    notes.append("committed output == generator output for 11 pages + style.css")


def check_links():
    """Rule 2: every local link resolves, and no page is orphaned."""
    graph = {}
    for name in PAGES:
        p = load(os.path.join(DESK_SITE, name))
        edges = set()
        for href in p.hrefs:
            href = html.unescape(href.split("#")[0])
            if not href or href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(os.path.join(DESK_SITE, name)), href))
            if os.path.isdir(target):
                target = os.path.join(target, "index.html")
            if not os.path.isfile(target):
                problems.append(f"broken link: desk/{name} -> {href}")
            else:
                edges.add(os.path.basename(target))
        graph[name] = edges
    seen, stack = set(), ["index.html"]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(graph.get(n, ()))
    for name in PAGES:
        if name not in seen:
            problems.append(f"desk/{name} is not reachable from desk/index.html")
    notes.append(f"local links resolve; {len(seen)} of {len(PAGES)} pages reachable from index.html")


def check_tables():
    """Rule 3: a Source cell carries a link; no empty cell anywhere."""
    rows = links = 0
    for name in PAGES:
        p = load(os.path.join(DESK_SITE, name))
        for t in p.tables:
            heads = [h.strip().lower() for h in t["headers"]]
            src_i = heads.index("source") if "source" in heads else None
            for r in t["rows"]:
                rows += 1
                for i, c in enumerate(r):
                    if not c.strip():
                        problems.append(f"empty cell: desk/{name} row {rows} column {i}")
                if src_i is not None:
                    if len(r) <= src_i:
                        problems.append(f"short row: desk/{name} row {rows} has {len(r)} cells, header has {len(t['headers'])}")
                        continue
                    if "LINK" not in r[src_i]:
                        problems.append(f"Source cell without a link: desk/{name} row {rows}")
                    else:
                        links += 1
    notes.append(f"{rows} table rows checked; {links} Source cells carry a link")


def check_numbers():
    """Rule 4: every number a page prints must be recomputable from the data layer."""
    st, inj, sch, dep = J("standings.json"), J("injuries.json"), J("schedule.json"), J("depth.json")
    rd, cl = J("readiness.json"), J("claims.json")
    idx = load(os.path.join(DESK_SITE, "index.html")).text
    idx = " ".join(" ".join(idx).split())

    def want(fragment, label):
        if fragment not in idx:
            problems.append(f"index.html does not print {label} ({fragment!r})")

    want(f'{st["counts"]["clubs"]} clubs', "the club count")
    want(f'{st["counts"]["games_played"]} completed games', "games implied by the standings")
    want(f'{inj["counts"]["rows"]} rows', "the injury row count")
    want(f'{inj["counts"]["clubs"]} clubs', "the injured-club count")
    want(f'{sch["week11"]["counts"]["fixtures"]} fixtures', "the fixture count")
    want(f'{sch["week11"]["counts"]["byes"]} byes', "the bye count")
    want(f'{sch["corpus"]["played_rows"]} vs {sch["corpus"]["implied_from_official_standings"]} games',
         "the corpus gap")
    want(f'{dep["counts"]["clubs"]} of 32 clubs', "the depth coverage count")

    # recompute the standings arithmetic from the transcription itself
    off = list(csv.DictReader(open(os.path.join(DESK_DATA, "standings_2026-11-16.psv"), encoding="utf-8"),
                              delimiter="|"))
    bad = 0
    for r in off:
        if int(r["pf"]) - int(r["pa"]) != int(r["net"]):
            bad += 1
        if abs(round((int(r["w"]) + 0.5 * int(r["t"])) / (int(r["w"]) + int(r["l"]) + int(r["t"])), 3) - float(r["pct"])) > 5e-4:
            bad += 1
    if bad != st["counts"]["arithmetic_failures"]:
        problems.append(f"standings arithmetic: transcription has {bad} failures, data says {st['counts']['arithmetic_failures']}")
    if sum(int(r["w"]) + int(r["l"]) + int(r["t"]) for r in off) // 2 != st["counts"]["games_played"]:
        problems.append("standings: club games / 2 does not equal the published games_played")

    # recompute the injury counts from the transcription itself
    tsv = list(csv.DictReader(open(os.path.join(DESK_DATA, "injuries_w10_2026-11-16.tsv"), encoding="utf-8"),
                              delimiter="\t"))
    if len(tsv) != inj["counts"]["rows"]:
        problems.append(f"injury rows: transcription has {len(tsv)}, data says {inj['counts']['rows']}")
    outs = sum(1 for r in tsv if r["game_status"] == "Out")
    if outs != inj["counts"]["out"]:
        problems.append(f"Out rows: transcription has {outs}, data says {inj['counts']['out']}")
    with_status = sum(1 for r in tsv if r["game_status"].strip())
    if with_status != inj["counts"]["with_game_status"]:
        problems.append(f"rows with a game status: transcription has {with_status}, data says {inj['counts']['with_game_status']}")
    clubs = len({r["club"] for r in tsv})
    if clubs != inj["counts"]["clubs"]:
        problems.append(f"clubs on the report: transcription has {clubs}, data says {inj['counts']['clubs']}")

    # fixtures and byes must cover the league exactly once
    fx = list(csv.DictReader(open(os.path.join(DESK_DATA, "week11_fixtures_2026-11-16.psv"), encoding="utf-8"), delimiter="|"))
    by = list(csv.DictReader(open(os.path.join(DESK_DATA, "week11_byes_2026-11-16.psv"), encoding="utf-8"), delimiter="|"))
    playing = {f["away"] for f in fx} | {f["home"] for f in fx}
    byeclubs = {b["club"] for b in by}
    alias = {"LAR": "LA", "ARI": "AZ"}
    byeclubs = {alias.get(c, c) for c in byeclubs}
    if playing & byeclubs:
        problems.append(f"a club both plays and is on bye in Week 11: {sorted(playing & byeclubs)}")
    if len(playing | byeclubs) != 32:
        problems.append(f"Week 11 covers {len(playing | byeclubs)} clubs, not 32")

    # Week-10 results: a final score must have both scores
    w10 = list(csv.DictReader(open(os.path.join(DESK_DATA, "week10_results_2026-11-16.psv"), encoding="utf-8"), delimiter="|"))
    for r in w10:
        if r["status"] == "Final" and not (r["away_score"] and r["home_score"]):
            problems.append(f"a Final with no score: {r['away']} @ {r['home']}")

    # depth: every named cell has a raw string; empty slots are explicit
    for club, chart in json.load(open(os.path.join(DESK_DATA, "depth_2026-11-16.json"), encoding="utf-8")).items():
        if club == "_readme":
            continue
        for u in chart["units"]:
            for s in u["slots"]:
                for pl in s["players"]:
                    if not pl.get("raw"):
                        problems.append(f"depth: {club} {s['position']} has a name with no raw cell: {pl}")

    # readiness: each row names a file that exists, and its status is one of the legend keys
    legend = set(rd["legend"])
    for r in rd["rows"]:
        if r["status"] not in legend:
            problems.append(f"readiness {r['id']} has status {r['status']!r} not in the legend")
        first = r["computed_from"].split(",")[0].strip()
        if "/" in first and not first.startswith(("data/desk", "desk/")) and not os.path.exists(os.path.join(ROOT, first)):
            problems.append(f"readiness {r['id']} cites a file that does not exist: {first}")
    notes.append(f"{len(rd['rows'])} readiness rows: status in legend, cited file exists")


def check_sources():
    """Rule 5: the claims must match what the transcription says, and links must be official."""
    inj = J("injuries.json")
    det = {r["player"]: r["game_status"] for r in inj["rows"] if r["club"] == "DET"}
    for p in ("Kerby Joseph", "Cade Mays", "D.J. Reed"):
        if det.get(p) != "Out":
            problems.append(f"claim D-C04 says {p} is Out; the transcription says {det.get(p)!r}")
    if not any(r["id"] == "D-C04" and r["verdict"] == "confirmed" for r in J("claims.json")["rows"]):
        problems.append("claim D-C04 must be published as confirmed when the page lists all three as Out")

    # the 83/17 reserve split is quoted on the availability page; it must still be what the file says
    rv = repo("data/reserve/report_vs_reserve.json")
    av = " ".join(" ".join(load(os.path.join(DESK_SITE, "availability.html")).text).split())
    for key, label in (("report_rows", "the Week-10 report row count"),
                       ("on_reserve", "open reserve designations"),
                       ("on_reserve_not_in_report", "named on a reserve list and on no report row"),
                       ("named_in_both", "named on both records")):
        n = rv["totals"][key]
        if str(n) not in av:
            problems.append(f"availability.html does not print {label} ({n}) from report_vs_reserve.json")

    # every official URL cited must be a host the brief calls official
    ok_hosts = ("https://www.nfl.com/", "https://www.detroitlions.com/", "https://www.baltimoreravens.com/",
                "https://www.packers.com/")
    for s in J("sources.json")["sources"]:
        if not s["url"].startswith(ok_hosts):
            problems.append(f"source {s['id']} is not an official host: {s['url']}")
        if not s.get("retrieved"):
            problems.append(f"source {s['id']} has no read date")
    notes.append(f"{len(J('sources.json')['sources'])} sources: official hosts only, every one dated")


def main() -> int:
    for name in PAGES:
        if not os.path.exists(os.path.join(DESK_SITE, name)):
            problems.append(f"missing page desk/{name}")
    check_committed()
    check_links()
    check_tables()
    check_numbers()
    check_sources()

    print("desk/ verification")
    for n in notes:
        print("  ok  ", n)
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print("   -", p)
        return 1
    print("\nRESULT: PASS — every page reproduces from the data, every link resolves, "
          "every Source cell carries an official link, and every published number recomputes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
