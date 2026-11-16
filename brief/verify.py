#!/usr/bin/env python3
"""brief/verify.py — the gate on the eight brief pages.

What it refuses
---------------
  E1  a page listed in brief/build.py PAGES is missing from disk;
  E2  a table cell renders empty (`<td></td>`) — a blank fact must say why it is blank;
  E3  a table row inside <tbody> has no https source link and no explicit "not published" label;
  E4  a placeholder appears (TBD, TODO, lorem, XXX, N/A, nan, None);
  E5  a local href/src does not resolve on disk;
  E6  a page is not reachable from index.html;
  E7  the committed HTML differs from what brief/build.py produces now (hand-edit or stale build);
  E8  a page is missing the eight-link nav or the active marker;
  E9  a page is missing its <h1> or its timestamp;
  E10 a data file under data/session-2b927826/ changed after the pages were built.

Run:
    python3 brief/build.py && python3 brief/verify.py

Exit 0 only when every check passes. It prints one line per check and a row count per page.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HERE = os.path.join(ROOT, "brief")
DATA = os.path.join(ROOT, "data", "session-2b927826")

sys.path.insert(0, HERE)
import build  # noqa: E402  (the generator, imported so E7 can rebuild in memory)

ROW_SOURCE = re.compile(r"https?://")
BLANK_OK = ("not published", "unverified", "not captured", "no date on chart",
            "no official source applies", "no note recorded", "analytic, no sample",
            "lower bound below zero", "differs from the feed", "nobody pressed")
# Deliberately narrow: "none" is a legitimate English word and appears in prose
# ("none of the twelve rules clears the gates"). What matters is a *rendered* empty
# value -- a Python repr or a stand-in token inside a cell -- so those are the patterns.
PLACEHOLDER = re.compile(r"\b(TBD|TODO|lorem|ipsum|XXX|N/?A)\b|>\s*(None|nan|NaN|undefined)\s*<", re.I)
EMPTY_TD = re.compile(r"<td[^>]*>\s*</td>")
EMPTY_TH = re.compile(r"<th[^>]*>\s*</th>")
TBODY = re.compile(r"<tbody>(.*?)</tbody>", re.S)
ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
HREF = re.compile(r'(?:href|src)="([^"]+)"')
TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def main() -> int:
    problems: list[str] = []
    pages = [name for name, _ in build.PAGES]

    # E1 — existence
    missing = [p for p in pages if not os.path.isfile(os.path.join(HERE, p))]
    if missing:
        problems.append(f"E1 pages not built: {missing}")

    html = {}
    for p in pages:
        path = os.path.join(HERE, p)
        if os.path.isfile(path):
            html[p] = open(path, encoding="utf-8").read()

    # E7 — the committed file must equal a fresh build
    for name, fn in build.BUILDERS.items():
        fresh = fn()
        if name in html and html[name] != fresh:
            problems.append(f"E7 brief/{name} is stale or hand-edited "
                            f"(committed {len(html[name]):,} bytes, fresh {len(fresh):,} bytes) — run brief/build.py")

    index = html.get("index.html", "")
    total_rows = 0
    for name, body in html.items():
        # E2 — no empty cell
        if EMPTY_TD.search(body):
            problems.append(f"E2 {name}: a <td> renders empty")
        if EMPTY_TH.search(body):
            problems.append(f"E2 {name}: a <th> renders empty")

        # E3 — every data row names a source or says why it cannot
        for tbody in TBODY.findall(body):
            for row in ROW.findall(tbody):
                cells = TD.findall(row)
                if not cells:
                    continue
                total_rows += 1
                text = strip_tags(row)
                if not ROW_SOURCE.search(row) and not any(k in text for k in BLANK_OK):
                    problems.append(f"E3 {name}: row without a source link or a stated reason: "
                                    f"{text.strip()[:90]!r}")

        # E4 — placeholders
        for m in PLACEHOLDER.finditer(strip_tags(body)):
            problems.append(f"E4 {name}: placeholder {m.group(0)!r}")

        # E5 — local links resolve
        for href in HREF.findall(body):
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = os.path.normpath(os.path.join(HERE, href.split("#")[0]))
            if not target.startswith(ROOT):
                problems.append(f"E5 {name}: link escapes the repository: {href}")
            elif not os.path.exists(target):
                problems.append(f"E5 {name}: broken local link: {href}")

        # E6 — reachable from the index
        if name != "index.html" and f'href="{name}"' not in index:
            problems.append(f"E6 {name} is not linked from index.html")

        # E8 — nav present with every page and one active marker
        nav = re.search(r'<nav aria-label="Categories">(.*?)</nav>', body, re.S)
        if not nav:
            problems.append(f"E8 {name}: no category nav")
        else:
            links = re.findall(r'<a href="([^"]+)"( class="active")?>', nav.group(1))
            if len(links) != len(pages):
                problems.append(f"E8 {name}: nav has {len(links)} links, expected {len(pages)}")
            if sum(1 for _, a in links if a) != 1:
                problems.append(f"E8 {name}: nav must mark exactly one active page")
            if not any(h == name and a for h, a in links):
                problems.append(f"E8 {name}: the nav does not mark itself active")

        # E9 — heading and timestamp
        if "<h1>" not in body:
            problems.append(f"E9 {name}: no <h1>")
        if 'class="timestamp"' not in body:
            problems.append(f"E9 {name}: no build timestamp")

    # E10 — data freshness: every input JSON must be older than the pages
    newest_page = max(os.path.getmtime(os.path.join(HERE, p)) for p in html) if html else 0
    for f in sorted(os.listdir(DATA)):
        if f.endswith(".json"):
            mp = os.path.getmtime(os.path.join(DATA, f))
            if mp > newest_page + 1:
                problems.append(f"E10 data/session-2b927826/{f} is newer than the built pages — rebuild")

    # Report
    print("brief/verify.py")
    print(f"  pages           {len(html)} of {len(pages)}")
    print(f"  data rows       {total_rows}")
    print(f"  https links     {sum(b.count('https://') for b in html.values())}")
    for p in pages:
        if p in html:
            print(f"  {p:22} {len(html[p]):>7,} bytes  {html[p].count('<tr>'):>4} rows")

    if problems:
        print(f"\nFAIL ({len(problems)}):")
        for p in problems:
            print("  -", p)
        return 1
    print("\nRESULT: PASS — 8 pages, every row sourced or explicitly blank, no placeholders, "
          "no broken links, no stale build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
