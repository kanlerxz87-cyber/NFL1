#!/usr/bin/env python3
"""ledger/verify.py — the gate for the ledger site.

Fails the build on any of:

  1. a local href or src that does not resolve to a real file;
  2. a table ROW that carries no https link to an official source and is not explicitly
     marked blank/unverified;
  3. a placeholder token left in published text (TODO, FIXME, XXX, lorem, {placeholder});
  4. a page in ledger/ that is not linked from ledger/index.html;
  5. a page whose navigation lists a page that does not exist.

It deliberately does NOT check anything outside ledger/. Other sessions own the rest of the site
and this session must not fail their build.

Run: python3 ledger/verify.py
"""
from __future__ import annotations

import html
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE = os.path.join(ROOT, "ledger")
PLACEHOLDERS = re.compile(r"\b(TODO|FIXME|XXX|lorem ipsum|\{\{|\bTBD\b)", re.I)
BLANK_OK = re.compile(r"blank|unverified|no public source|no price|not verifiable|"
                      r"not in any committed|internal|policy choice|no external source", re.I)


class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs, self.ids, self.tables, self.text = [], set(), [], []
        self._t = None
        self._row = None
        self._cell = None
        self._cell_links = []      # hrefs seen inside the current cell
        self._tables_links = None  # parallel structure of links per table row
        self._nav = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        if tag in ("img", "script", "link") and a.get("src"):
            self.hrefs.append(a["src"])
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "table":
            self._t = []
            self._nav = a.get("data-nav") == "1"
            self._tables_links = []
        elif tag == "tr" and self._t is not None:
            self._row = []
            self._row_links = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
            self._cell_links = []
        if tag == "a" and a.get("href") and self._cell is not None:
            self._cell_links.append(a["href"])

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._row_links.append(list(self._cell_links))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self._t.append((self._row, self._row_links))
            self._row = None
        elif tag == "table" and self._t is not None:
            self.tables.append((self._t, self._nav))
            self._t = None

    def handle_data(self, data):
        self.text.append(data)
        if self._cell is not None:
            self._cell.append(data)


def main() -> int:
    if not os.path.isdir(SITE):
        print("ledger/ does not exist")
        return 1
    pages = sorted(f for f in os.listdir(SITE) if f.endswith(".html"))
    problems, soft = [], []
    total_rows = sourced = 0
    parsed = {}
    for f in pages:
        p = Scan()
        with open(os.path.join(SITE, f), encoding="utf-8") as fh:
            p.feed(fh.read())
        parsed[f] = p
        # rule 1: local links resolve
        for h in p.hrefs:
            if h.startswith(("http://", "https://", "mailto:", "#", "data:", "javascript:")):
                continue
            target = os.path.normpath(os.path.join(SITE, h.split("#")[0]))
            if not os.path.exists(target):
                problems.append(f"{f}: broken local link -> {h}")
        # rule 3: placeholders
        txt = " ".join(p.text)
        for m in PLACEHOLDERS.finditer(txt):
            problems.append(f"{f}: placeholder token {m.group(0)!r}")
        # rule 2: every data row carries an official source link
        for t, is_nav in p.tables:
            if not t or len(t) < 2:
                continue
            header = [c.lower() for c in t[0][0]]
            declares_source = any("source" in h or "settle" in h or "verif" in h for h in header)
            if is_nav:
                continue
            if not declares_source:
                # a non-navigation table WITHOUT a source column is a data table hiding
                # its evidence; that is a failure, not a skip.
                problems.append(f"{f}: data table with no Source column -> "
                                f"headers {t[0][0]}")
                continue
            for row, links in t[1:]:
                if len(row) < 2:
                    continue
                total_rows += 1
                flat = [h for cell in links for h in cell]
                has_official = any(h.startswith("https://") for h in flat)
                joined = " ".join(row) + " " + " ".join(flat)
                if has_official:
                    sourced += 1
                elif BLANK_OK.search(joined):
                    soft.append(f"{f}: row keeps a labelled blank ({row[0][:40]!r})")
                else:
                    problems.append(f"{f}: row with no official https link and no blank marker -> {row[0][:60]!r}")

    # rule 4: reachability from index
    reach = {"index.html"}
    stack = ["index.html"]
    while stack:
        cur = stack.pop()
        for h in parsed.get(cur, Scan()).hrefs:
            if h.startswith(("http", "mailto", "#")):
                continue
            t = os.path.normpath(h.split("#")[0])
            if t in parsed and t not in reach:
                reach.add(t)
                stack.append(t)
    for f in pages:
        if f not in reach:
            problems.append(f"{f}: not reachable from index.html")

    print(f"pages {len(pages)} · table rows {total_rows} · rows with an official https source {sourced}")
    for s in soft[:12]:
        print("  note:", s)
    if problems:
        print(f"\nFAIL — {len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1
    print("\nPASS — every local link resolves, every data row carries an official source link or a "
          "labelled blank, no placeholder text, every page reachable from index.html.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
