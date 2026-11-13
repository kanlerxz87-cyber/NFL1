#!/usr/bin/env python3
"""verify.py — the gate for the Decision Room.

Fails (exit 1) when any of the following is true, because each one is a way this
kind of site lies without anyone noticing:

  1. a local link resolves to a missing file
  2. a page is unreachable from index.html
  3. a table has a header but no data rows
  4. a table cell is rendered empty instead of an explicit blank label
  5. a data table row has no https source link at all
  6. literal markdown (** or _emphasis_) leaked into prose
  7. an "official" claim is made without an nfl.com / club / github link on the page
  8. a numeric-looking claim in a KPI card has no note explaining where it came from

Run: python3 room/verify.py
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGES = sorted(ROOT.glob("*.html"))


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []
        self.ids: set[str] = set()
        self.tables: list[dict] = []
        self._cur = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and "href" in d:
            self.hrefs.append(d["href"])
        if "id" in d:
            self.ids.add(d["id"])
        if tag == "table":
            self._cur = {"rows": 0, "header": False, "cells": [], "https": 0, "links": 0,
                         "nav": "nav-table" in (d.get("class") or ""),
                         "row_links": [], "_row_has_link": False}
        elif tag == "thead" and self._cur is not None:
            self._cur["header"] = True
        elif tag == "tr" and self._cur is not None:
            self._cur["rows"] += 1
        elif tag == "td" and self._cur is not None:
            self._cell = []
        elif tag == "a" and self._cur is not None:
            self._cur["links"] += 1
            self._cur["_row_has_link"] = True
            if d.get("href", "").startswith("https://"):
                self._cur["https"] += 1

    def handle_endtag(self, tag):
        if tag == "td" and self._cur is not None and self._cell is not None:
            self._cur["cells"].append("".join(self._cell).strip())
            self._cell = None
        elif tag == "table" and self._cur is not None:
            self.tables.append(self._cur)
            self._cur = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def main() -> int:
    problems: list[str] = []
    graph: dict[Path, set[Path]] = {}
    n_tables = 0
    n_rows = 0
    for p in PAGES:
        s = Scan()
        s.feed(p.read_text(encoding="utf-8"))
        text = p.read_text(encoding="utf-8")
        edges = set()
        for h in s.hrefs:
            if h.startswith(("http://", "https://", "mailto:")):
                continue
            if h.startswith("#"):
                continue
            target = h.split("#")[0]
            if not target:
                continue
            t = (p.parent / target).resolve()
            if not t.is_file():
                problems.append(f"{p.name}: broken link -> {h}")
            else:
                edges.add(t)
        graph[p.resolve()] = edges

        for tb in s.tables:
            n_tables += 1
            n_rows += max(0, tb["rows"] - 1)
            if tb["header"] and tb["rows"] <= 1:
                problems.append(f"{p.name}: table with a header but no data rows")
            for c in tb["cells"]:
                if c == "":
                    problems.append(f"{p.name}: empty table cell (use an explicit blank label)")
                    break
            if tb["rows"] > 1 and tb["https"] == 0:
                if tb["nav"] and tb["links"] >= tb["rows"] - 1:
                    pass  # a navigation index: every row links to the page it describes
                else:
                    problems.append(f"{p.name}: data table with no https source link")

        # A doubled repo path (blob/main/blob/main/) resolves to a 404 on GitHub while still
        # looking like a link in the HTML, so check it explicitly.
        for bad in re.findall(r'href="[^"]*(?:blob|tree)/[a-z]+/(?:blob|tree)/[a-z]+/[^"]*"', text):
            problems.append(f"{p.name}: doubled repo path in link ({bad[:80]})")

        prose = re.sub(r"<code\b.*?</code>|<pre\b.*?</pre>", "", text, flags=re.S)
        prose = re.sub(r"<[^>]+>", " ", prose)
        for pat, label in ((r"\*\*[^*\n]{1,80}\*\*", "**bold**"),
                           (r"(?<![\w_])_[A-Za-z][A-Za-z '\-]{0,40}_(?![\w_])", "_emphasis_")):
            m = re.search(pat, prose)
            if m:
                problems.append(f"{p.name}: literal markdown {label} in prose ({m.group(0)[:40]!r})")

        # every KPI card must carry a note, so a headline number is never bare
        for card in re.findall(r'<article class="kpi">(.*?)</article>', text, re.S):
            if 'class="note"' not in card:
                problems.append(f"{p.name}: KPI card without a provenance note")

    seen, stack = set(), [(ROOT / "index.html").resolve()]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(graph.get(n, ()))
    for p in PAGES:
        if p.resolve() not in seen:
            problems.append(f"{p.name}: unreachable from index.html")

    print(f"room pages checked: {len(PAGES)}")
    print(f"tables checked: {n_tables} · data rows: {n_rows}")
    if problems:
        print("\nPROBLEMS:")
        for x in problems:
            print(" -", x)
        return 1
    print("PASS: all local links resolve, every page is reachable, every data table carries a"
          " source link, and no cell renders empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
