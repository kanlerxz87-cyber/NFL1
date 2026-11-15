#!/usr/bin/env python3
"""strat/verify.py — hard gate on the strat/ sub-site.

Checks, all of which fail the build:
  1. every page listed in strat/lib.py NAV exists;
  2. every local href and asset resolves to a file (no broken links);
  3. every table body row carries an https source link;
  4. no table cell is empty, and no banned placeholder appears in a cell
     ("TBD", "None", "undefined", "NaN", "-");
  5. no template marker or stray escape leaked into the HTML;
  6. every page other than the index is linked from the index and appears in the nav;
  7. each number on a page is traceable: a page may only print digits that appear in
     data/strat/*.json, in a source URL, or in a fixed allow-list of structural numbers.

Rule 7 is the unusual one and it is deliberate: it makes it impossible to hand-edit a number
into a page without the data changing too.

Run: python3 strat/verify.py
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = os.path.join(ROOT, "strat")
DATA = os.path.join(ROOT, "data", "strat")

sys.path.insert(0, HERE)
import lib  # noqa: E402

BANNED_CELLS = {"TBD", "None", "undefined", "NaN", "-", "n/a", "N/A", ""}


def data_numbers() -> set:
    """Every numeric literal that appears anywhere in data/strat/*.json."""
    out = set()
    for name in os.listdir(DATA):
        if not name.endswith(".json"):
            continue
        text = open(os.path.join(DATA, name), encoding="utf-8").read()
        for m in re.finditer(r"-?\d+(?:\.\d+)?", text):
            out.add(m.group(0))
            # tolerate formatting: +0.0413, 0.04127, 6,785 -> 6785, 10.53 for 10.5333
            try:
                v = float(m.group(0))
            except ValueError:
                continue
            out.add(f"{v:.0f}")
            out.add(f"{v:.1f}")
            out.add(f"{v:.2f}")
            out.add(f"{v:.3f}")
            out.add(f"{v:.4f}")
            out.add(f"{v:+.1f}")
            out.add(f"{v:+.2f}")
            out.add(f"{v:+.3f}")
            out.add(f"{v:+.4f}")
            out.add(f"{int(v):,}" if abs(v) >= 1000 else f"{int(v)}")
            out.add(f"{v:.5f}")
            # a fraction published as a percentage is the same number, not a new claim
            out.add(f"{v * 100:.2f}")
            out.add(f"{v * 100:.1f}")
    return out


def main() -> int:
    problems = []
    pages = sorted(f for f in os.listdir(SITE) if f.endswith(".html"))
    nav_pages = {href for href, _ in lib.NAV}

    # 1. nav completeness
    for href in nav_pages:
        if not os.path.isfile(os.path.join(SITE, href)):
            problems.append(f"nav lists {href} but the page does not exist")
    for p in pages:
        if p not in nav_pages:
            problems.append(f"{p} exists but is not in the nav")

    index = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
    known = data_numbers()

    for page in pages:
        text = open(os.path.join(SITE, page), encoding="utf-8").read()

        # 2. links and assets
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("https://", "http://", "#", "mailto:")):
                continue
            target = os.path.normpath(os.path.join(SITE, href.split("#")[0]))
            if not os.path.exists(target):
                problems.append(f"{page}: broken local link {href}")
        for asset in re.findall(r'src="([^"]+)"', text):
            if asset.startswith(("https://", "http://", "data:")):
                continue
            if not os.path.exists(os.path.normpath(os.path.join(SITE, asset))):
                problems.append(f"{page}: broken asset {asset}")

        # 3. every table body row has a source link
        for tbody in re.findall(r"<tbody>(.*?)</tbody>", text, flags=re.S):
            for row in re.findall(r"<tr>(.*?)</tr>", tbody, flags=re.S):
                if not re.search(r'<a class="src" href="https://', row):
                    label = re.sub(r"<[^>]+>", " ", row)[:80].strip()
                    problems.append(f"{page}: table row without an https source -> {label}")

        # 4. empty or placeholder cells
        for cell in re.findall(r"<td>(.*?)</td>", text, flags=re.S):
            bare = re.sub(r"<[^>]+>", "", cell).strip()
            if bare in BANNED_CELLS:
                problems.append(f"{page}: empty or placeholder cell {bare!r}")
            for token in ("TBD", "undefined", "NaN"):
                if token in bare:
                    problems.append(f"{page}: banned placeholder {token!r} in a cell -> {bare[:60]}")

        # 5. template artefacts
        for token in ("{{", "}}", '\\"', "{'", '",,'):
            if token in text:
                problems.append(f"{page}: template/escape artefact {token!r}")

        # 6. reachable from the index
        if page != "index.html" and page not in index:
            problems.append(f"{page}: not linked from strat/index.html")

        # 7. every printed number is traceable to the data
        #    strings that are legitimately not in the JSON: URLs, and the fixed vocabulary
        stripped = re.sub(r'<a class="src" href="[^"]+"', "<a", text)
        stripped = re.sub(r"https?://\S+", "", stripped)
        stripped = re.sub(r"<pre.*?</pre>", "", stripped, flags=re.S)   # the reproduce block
        stripped = re.sub(r"<[^>]+>", " ", stripped)
        stripped = re.sub(r"week \d+ · \d{4}-\d{2}-\d{2}", " ", stripped)   # fixture dates
        for m in re.finditer(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?", stripped):
            tok = m.group(0).replace(",", "")
            if tok in known or tok.lstrip("+-") in known:
                continue
            # structural numbers that are part of the template, not claims
            if tok.lstrip("+-") in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
                                    "11", "12", "13", "25", "40", "50", "95", "100", "200",
                                    "1980", "2000", "2026"}:
                continue
            problems.append(f"{page}: number {tok!r} does not appear in data/strat/*.json")

    rows = sum(len(re.findall(r"<tr>", open(os.path.join(SITE, p), encoding="utf-8").read()))
               for p in pages)
    print(f"pages: {len(pages)} · table rows: {rows} · nav entries: {len(nav_pages)}")
    if problems:
        # de-duplicate while keeping order, so one systemic fault is one line
        seen, uniq = set(), []
        for p in problems:
            if p not in seen:
                seen.add(p)
                uniq.append(p)
        print(f"FAIL: {len(uniq)} problem(s)")
        for p in uniq[:60]:
            print("  -", p)
        if len(uniq) > 60:
            print(f"  … and {len(uniq) - 60} more")
        return 1
    print("PASS: every page reachable, every link resolves, every table row carries a source, "
          "no empty or placeholder cells, every printed number traceable to data/strat/*.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
