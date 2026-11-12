#!/usr/bin/env python3
"""check_reachability.py — whole-site navigation and source-link gate.

Session 4c043747 (final integration).  Run from the repository root:

    python3 tools/check_reachability.py

Three rules, all of them about the published site rather than the repository:

1. Reachability — every published HTML page (the landing page, pages/, the governance
   registers at the root, and the three independent sub-sites in docs/, verified-lab/ and
   referee/) must be reachable from index.html by following local links.  A published page
   that nothing links to is invisible to a reader, so this is a hard failure.
2. Links — every local href must resolve to a file that exists.
3. Source links — every row of every table that declares a "Source" column must carry a
   link in that row (in the source cell itself, or in a neighbouring cell when the table
   prints the URL separately).  A row with neither a link nor an explicit "no public
   source" marker is a row nobody can check, and it fails the gate.  Rows whose source cell
   has no link of its own are counted separately and reported for review.

Exit code 0 when all three rules hold, 1 otherwise.
"""
from __future__ import annotations

import html
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", ".github", "__pycache__", "node_modules", "site", ".venv", ".pytest_cache"}
SKIP_FILES = {"site/templates/base.html"}


class Page(HTMLParser):
    """Collects hrefs, ids, and the cells of every table."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs = []
        self.ids = set()
        self.tables = []          # list of (headers, [row cells])
        self._table = None
        self._headers = []
        self._row = None
        self._cell = None
        self._in_head = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and "href" in d:
            self.hrefs.append(d["href"])
        if "id" in d:
            self.ids.add(d["id"])
        if tag == "table":
            self._table = {"headers": [], "rows": []}
        elif tag == "thead" and self._table is not None:
            self._in_head = True
        elif tag == "th" and self._table is not None:
            self._cell = []
        elif tag == "tr" and self._table is not None and not self._in_head:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag == "a" and self._cell is not None:
            self._cell.append("link")

    def handle_endtag(self, tag):
        if tag == "th" and self._cell is not None and self._in_head:
            self._table["headers"].append("".join(self._cell))
            self._cell = None
        elif tag == "thead":
            self._in_head = False
        elif tag == "td" and self._cell is not None:
            self._row.append("".join(self._cell))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self._table["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def published_pages():
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in sorted(filenames):
            if not f.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), ROOT).replace(os.sep, "/")
            if rel in SKIP_FILES:
                continue
            out.append(rel)
    return sorted(out)


def parse(path):
    p = Page()
    with open(path, encoding="utf-8", errors="replace") as fh:
        p.feed(fh.read())
    return p


def local_target(page_rel, href):
    href = html.unescape(href.split("#")[0])
    if not href or href.startswith(("http://", "https://", "mailto:", "javascript:", "data:", "#")):
        return None
    target = os.path.normpath(os.path.join(os.path.dirname(page_rel), href))
    if os.path.isdir(os.path.join(ROOT, target)):
        target = os.path.join(target, "index.html")
    return target.replace(os.sep, "/")


NO_SOURCE = re.compile(r"^(internal|none|n/?a|\u2014|-|blank|unverified|no public url|"
                        r"not applicable|not available|internal source)?$", re.I)


def main() -> int:
    pages = published_pages()
    problems = []
    weak_source_cells = []
    no_source_rows = []
    graph = {}

    for rel in pages:
        p = parse(os.path.join(ROOT, rel))
        edges = set()
        for href in p.hrefs:
            t = local_target(rel, href)
            if t is None:
                continue
            if not os.path.isfile(os.path.join(ROOT, t)):
                problems.append(f"broken link: {rel} -> {href}")
            else:
                edges.add(t)
        graph[rel] = edges

        # rule 3: every row of a table with a Source column carries a link
        for t in p.tables:
            headers = [h.strip().lower() for h in t["headers"]]
            if "source" not in headers:
                continue
            idx = headers.index("source")
            for row in t["rows"]:
                if len(row) <= idx:
                    continue
                row_has_link = any("link" in c for c in row)
                cell_has_link = "link" in row[idx]
                if cell_has_link:
                    continue
                text = " ".join(row[idx].replace("link", "").split())
                if row_has_link:
                    weak_source_cells.append(f"{rel}: {text[:50]}")
                    continue
                if NO_SOURCE.match(text):
                    no_source_rows.append(f"{rel}: {text[:50] or '(blank)'}")
                    continue
                snippet = re.sub(r"<[^>]+>", " ", " | ".join(row))[:70]
                problems.append(f"row without a source link: {rel} ({snippet.strip()})")

    # rule 1: reachability from the landing page
    seen, stack = set(), ["index.html"]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, ()))
    orphans = [rel for rel in pages if rel not in seen]
    for o in orphans:
        problems.append(f"unreachable from index.html: {o}")

    reachable = [p for p in pages if p in seen]
    print(f"published pages: {len(pages)}   reachable from index.html: {len(reachable)}")
    print(f"rows whose source cell has no link of its own (link is in a neighbouring cell): "
          f"{len(weak_source_cells)}")
    print(f"rows with an explicit 'no public source' marker: {len(no_source_rows)}")
    print(f"problems: {len(problems)}")
    for x in problems:
        print(" -", x)
    if weak_source_cells:
        print("\nsource cell without its own link (for review):")
        for x in weak_source_cells[:40]:
            print("   ~", x)
        if len(weak_source_cells) > 40:
            print(f"   ... and {len(weak_source_cells) - 40} more")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
