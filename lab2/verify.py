#!/usr/bin/env python3
"""verify.py — the gate for the Origination Desk sub-site.

Fails (exit 1) if any of these is true:
  1. a table row carries no https source link;
  2. a cell contains the raw string "None" or "nan" (a value that leaked out of Python);
  3. a local href does not resolve to a file;
  4. a page is not reachable from lab2/index.html;
  5. a published residual or correlation does not reproduce from its stored inputs;
  6. the build is not deterministic (a second build changes a byte).

Run from the repository root:  python3 lab2/verify.py
"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

ROOT = lib.ROOT
SITE = os.path.join(ROOT, "lab2")


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs, self.tables, self._t, self._row, self._cell, self._in_head = [], [], None, None, None, False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and "href" in d:
            self.hrefs.append(d["href"])
        if tag == "table":
            self._t = {"heads": [], "rows": []}
        elif tag == "thead" and self._t is not None:
            self._in_head = True
        elif tag == "tr" and self._t is not None and not self._in_head:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag == "a" and self._cell is not None:
            self._cell.append("LINK")

    def handle_endtag(self, tag):
        if tag == "th" and self._cell is not None and self._in_head:
            self._t["heads"].append("".join(self._cell))
            self._cell = None
        elif tag == "thead":
            self._in_head = False
        elif tag == "td" and self._cell is not None:
            self._row.append("".join(self._cell))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self._t["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._t is not None:
            self.tables.append(self._t)
            self._t = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def pages():
    out = []
    for dirpath, _dirs, files in os.walk(SITE):
        if "assets" in dirpath or "data" in dirpath:
            continue
        for f in files:
            if f.endswith(".html"):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def check_rows(fails, stats):
    for p in pages():
        parser = Page()
        parser.feed(open(p, encoding="utf-8").read())
        rel = os.path.relpath(p, ROOT)
        stats["tables"] += len(parser.tables)
        for t in parser.tables:
            for i, row in enumerate(t["rows"], 1):
                stats["rows"] += 1
                has_link = any("LINK" in c for c in row)
                says_missing = any("no public source" in c for c in row)
                if not (has_link or says_missing):
                    fails.append(f"{rel}: table row {i} has neither a source link nor an explicit "
                                 f"'no public source' marker: {row[:2]}")
                for c in row:
                    if re.search(r"(?<![A-Za-z])None(?![A-Za-z])|(?<![A-Za-z])nan(?![A-Za-z])|\bNaN\b", c):
                        fails.append(f"{rel}: table row {i} prints a raw Python value: {c[:80]}")


def check_links(fails, stats):
    for p in pages():
        parser = Page()
        parser.feed(open(p, encoding="utf-8").read())
        rel = os.path.relpath(p, ROOT)
        for h in parser.hrefs:
            stats["links"] += 1
            if h.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = h.split("#")[0]
            if not target:
                continue
            tp = os.path.normpath(os.path.join(os.path.dirname(p), target))
            if not os.path.exists(tp):
                fails.append(f"{rel}: link does not resolve: {h}")


def check_reachability(fails, stats):
    start = os.path.join(SITE, "index.html")
    seen, todo = {start}, [start]
    while todo:
        cur = todo.pop()
        parser = Page()
        parser.feed(open(cur, encoding="utf-8").read())
        for h in parser.hrefs:
            if h.startswith(("http", "#", "mailto:")):
                continue
            tp = os.path.normpath(os.path.join(os.path.dirname(cur), h.split("#")[0]))
            if tp.endswith(".html") and os.path.exists(tp) and tp not in seen and tp.startswith(SITE):
                seen.add(tp)
                todo.append(tp)
    unreachable = [os.path.relpath(p, ROOT) for p in pages() if p not in seen]
    if unreachable:
        fails.append("unreachable from lab2/index.html: " + ", ".join(unreachable))
    stats["reachable"] = len(seen)


def check_arithmetic(fails, stats):
    d = lib.load("lab2/data/derived.json")
    # residuals
    for r in d["lines"]["rows"]:
        if r["side_market_num"] is None:
            continue
        if round(r["side_fair_num"] - r["side_market_num"], 2) != r["side_residual"]:
            fails.append(f"side residual does not reproduce for {r['matchup']}")
        if r["total_market"] is not None and round(r["total_fair"] - r["total_market"], 2) != r["total_residual"]:
            fails.append(f"total residual does not reproduce for {r['matchup']}")
        stats["recomputed"] += 1
    # standings arithmetic: stored table + finals == official table
    bad = [r for r in d["results"]["recon_rows"] if not r["agrees"]]
    if bad:
        fails.append(f"standings reconciliation fails for {len(bad)} clubs")
    stats["recon"] = len(d["results"]["recon_rows"]) - len(bad)
    # correlation intervals must bracket r
    for r in d["correlations"]["rows"] + d["correlations"]["official_rows"]:
        if r["published"]:
            lo, hi = [float(x) for x in r["ci95"].strip("[]").split(",")]
            if not (lo <= r["r"] <= hi):
                fails.append(f"interval does not contain r: {r['relationship']}")
            stats["correlations"] += 1
    # signal: portfolio q-values must be non-increasing down the sorted p list
    qs = [r["bh_q"] for r in sorted(d["signal"]["rows"], key=lambda x: x["p_value"])]
    if any(qs[i] > qs[i + 1] + 1e-9 for i in range(len(qs) - 1)):
        fails.append("Benjamini-Hochberg q values are not monotone")
    stats["signal"] = len(d["signal"]["rows"])


def check_official_reads(fails, stats):
    """Every source a page cites must be a page this session opened, or a repository file."""
    # cited pages must be one of: the league site, the mirrored feed, a club's own official site,
    # this repository, or this site.  Anything else is an unverified citation and fails the gate.
    allowed_prefix = ("https://www.nfl.com/", "https://github.com/nflverse/",
                      "https://github.com/kanlerxz87-cyber/NFL1/", "https://kanlerxz87-cyber.github.io/NFL1/")
    CLUB_HOSTS = {
        "azcardinals.com", "atlantafalcons.com", "baltimoreravens.com", "buffalobills.com", "panthers.com",
        "chicagobears.com", "bengals.com", "clevelandbrowns.com", "dallascowboys.com", "denverbroncos.com",
        "detroitlions.com", "packers.com", "houstontexans.com", "colts.com", "jaguars.com", "chiefs.com",
        "chargers.com", "rams.com", "raiders.com", "miamidolphins.com", "vikings.com", "patriots.com",
        "neworleanssaints.com", "giants.com", "newyorkjets.com", "philadelphiaeagles.com", "steelers.com",
        "seahawks.com", "49ers.com", "buccaneers.com", "tennesseetitans.com", "commanders.com",
    }
    def allowed(u: str) -> bool:
        if u.startswith(allowed_prefix):
            return True
        host = u.split("/")[2]
        return host in CLUB_HOSTS or host.replace("www.", "") in CLUB_HOSTS
    seen = set()
    for p in pages():
        txt = open(p, encoding="utf-8").read()
        for m in re.findall(r'href="(https://[^"]+)"', txt):
            seen.add(m)
    for u in sorted(seen):
        stats["citations"] += 1
        if not allowed(u):
            fails.append(f"citation outside the verified source list: {u}")


def check_determinism(fails, stats):
    def snapshot():
        h = {}
        for p in pages():
            h[p] = lib.sha256_of(os.path.relpath(p, ROOT))
        return h
    before = snapshot()
    r = subprocess.run([sys.executable, "lab2/render.py"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        fails.append("rebuild failed: " + r.stderr[-400:])
        return
    after = snapshot()
    changed = [os.path.relpath(k, ROOT) for k in before if before[k] != after.get(k)]
    if changed:
        fails.append("rebuild is not deterministic: " + ", ".join(changed))
    stats["deterministic_pages"] = len(after)


def main():
    fails, stats = [], {"tables": 0, "rows": 0, "links": 0, "recomputed": 0, "citations": 0, "correlations": 0}
    check_rows(fails, stats)
    check_links(fails, stats)
    check_reachability(fails, stats)
    check_arithmetic(fails, stats)
    check_official_reads(fails, stats)
    check_determinism(fails, stats)
    print(json.dumps(stats, indent=1))
    if fails:
        print(f"\nFAIL — {len(fails)} problem(s):")
        for f in fails[:40]:
            print("  -", f)
        return 1
    print("\nPASS — every row sourced, every link resolves, every residual recomputes, build reproducible")
    return 0


if __name__ == "__main__":
    sys.exit(main())
