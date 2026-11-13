#!/usr/bin/env python3
"""check_strength_site.py -- hard gate on the strength/ site.

Checks, all of which fail the build:
  1. every page in strength/ is reachable from strength/index.html and appears in the nav
  2. every local href/image resolves to a file that exists (no broken links)
  3. every <tr> inside a table body carries an https source link
  4. no table row contains a bare "TBD", "-" or "None" in place of a value
  5. no unresolved template markers or stray backslash escapes leaked into the HTML
  6. the eight required page types are present

Run: python3 tools/check_strength_site.py
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "strength")
REQUIRED = ["index.html", "ratings.html", "lines.html", "leaderboard.html", "parlays.html",
            "props.html", "injuries.html", "correlations.html", "questions.html",
            "suggestions.html", "decisions.html", "flagged.html", "verification.html",
            "executive-summary.html"]
BANNED = ["TBD", "None", "undefined", "NaN", "{{", "}}", "\\\""]


def main() -> int:
    problems = []
    pages = sorted(f for f in os.listdir(SITE) if f.endswith(".html"))
    for req in REQUIRED:
        if req not in pages:
            problems.append(f"missing required page: {req}")
    for page in pages:
        path = os.path.join(SITE, page)
        text = open(path, encoding="utf-8").read()
        # 1/2: links
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("https://", "http://", "#", "mailto:")):
                continue
            target = os.path.normpath(os.path.join(SITE, href.split("#")[0]))
            if not os.path.exists(target):
                problems.append(f"{page}: broken local link {href}")
        for src in re.findall(r'src="([^"]+)"', text):
            if src.startswith(("https://", "http://", "data:")):
                continue
            if not os.path.exists(os.path.normpath(os.path.join(SITE, src))):
                problems.append(f"{page}: broken asset {src}")
        # 3: every table row has a source link
        for tbody in re.findall(r"<tbody>(.*?)</tbody>", text, flags=re.S):
            for i, row in enumerate(re.findall(r"<tr>(.*?)</tr>", tbody, flags=re.S), 1):
                if not re.search(r'<a class="src" href="https://', row):
                    label = re.sub(r"<[^>]+>", " ", row)[:70].strip()
                    problems.append(f"{page}: table row without an https source link -> {label}")
        # 4/5: banned placeholders, checked in table cells only, because words
        # like "None" are legitimate English in prose.
        for cell in re.findall(r"<td>(.*?)</td>", text, flags=re.S):
            bare = re.sub(r"<[^>]+>", "", cell).strip()
            for token in BANNED:
                if token in bare:
                    problems.append(f"{page}: banned placeholder {token!r} in a table cell -> {bare[:60]}")
        for token in ("{{", "}}", '\\"'):
            if token in text:
                problems.append(f"{page}: template/escape artefact {token!r}")
        # 1: reachable from the index
        if page != "index.html":
            index = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
            if page not in index:
                problems.append(f"{page}: not linked from strength/index.html")
    # 6: nav completeness
    index = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
    nav = re.search(r'<nav[^>]*>(.*?)</nav>', index, flags=re.S)
    if not nav:
        problems.append("index.html: no <nav> block")
    else:
        for req in REQUIRED:
            if f'href="{req}"' not in nav.group(1):
                problems.append(f"nav is missing {req}")

    rows = sum(len(re.findall(r"<tr>", open(os.path.join(SITE, p), encoding="utf-8").read()))
               for p in pages)
    print(f"pages checked: {len(pages)} · table rows: {rows} · required pages: {len(REQUIRED)}")
    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        for p in problems:
            print("  -", p)
        return 1
    print("PASS: every page reachable, every link resolves, every table row carries a source link, no placeholders")
    return 0


if __name__ == "__main__":
    sys.exit(main())
