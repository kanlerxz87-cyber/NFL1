#!/usr/bin/env python3
"""Check the COMMITTED site files (not regenerated copies).

Session 3d5c5e2d-nfl1. Several CI workflows regenerate pages and then check the regenerated
copies, so they never read the bytes that GitHub Pages serves. This script reads the committed
files directly and fails on:

1. a relative link or image that does not resolve to a file in the repository;
2. a table with a "Source" column where a body row has no link to an https host;
3. a page whose "Data built" timestamp is older than data/model/dashboard.json (stale publication).

Pages without a "Data built" stamp are listed as unstamped (not failed): they belong to earlier
generators and are flagged on pages/review.html (F19).

Usage: python3 tools/check_committed_site.py     (exit 0 = pass, 1 = failures)
Read-only: writes nothing.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PAGES = ["index.html"] + sorted(glob.glob(os.path.join(ROOT, "pages", "*.html")))
PAGES = [p if os.path.isabs(p) else os.path.join(ROOT, p) for p in PAGES]


class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs: list[str] = []          # href / src values
        self.tables: list[dict] = []       # {"headers": [...], "rows": [[cell_has_https_link?]]}
        self._in_table = 0
        self._cur = None                   # current table dict
        self._in_thead = False
        self._in_tbody = False
        self._row = None                   # list of per-cell flags while inside a tr
        self._cell = None                  # dict while inside td/th
        self._text: list[str] = []
        self.stamp = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("href", "src"):
            if a.get(key):
                self.refs.append(a[key])
        if tag == "table":
            self._in_table += 1
            if self._in_table == 1:
                self._cur = {"headers": [], "rows": []}
        elif tag == "thead" and self._cur is not None:
            self._in_thead = True
        elif tag == "tbody" and self._cur is not None:
            self._in_tbody = True
        elif tag == "tr" and self._cur is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None or (tag == "th" and self._in_thead):
            self._cell = {"text": [], "https": False}
        elif tag == "a" and self._cell is not None:
            href = a.get("href") or ""
            if urlsplit(href).scheme == "https":
                self._cell["https"] = True

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            text = "".join(self._cell["text"]).strip()
            if self._in_thead and self._cur is not None:
                self._cur["headers"].append(text)
            elif self._row is not None:
                self._row.append(self._cell["https"])
            self._cell = None
        elif tag == "tr" and self._row is not None and self._cur is not None and self._in_tbody:
            self._cur["rows"].append(self._row)
            self._row = None
        elif tag == "thead":
            self._in_thead = False
        elif tag == "tbody":
            self._in_tbody = False
        elif tag == "table" and self._in_table:
            self._in_table -= 1
            if self._in_table == 0 and self._cur is not None:
                self.tables.append(self._cur)
                self._cur = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell["text"].append(data)
        m = re.search(r"Data built (\d{4}-\d{2}-\d{2}T[\d:+]+)", data)
        if m and self.stamp is None:
            self.stamp = m.group(1)


def resolve(page_dir: str, ref: str) -> str | None:
    """Return None for external/anchor-only refs, else the filesystem path it should point to."""
    parts = urlsplit(ref)
    if parts.scheme or ref.startswith("//") or ref.startswith("mailto:") or ref.startswith("#"):
        return None
    if not parts.path:
        return None
    target = os.path.normpath(os.path.join(page_dir, unquote(parts.path)))
    if os.path.isdir(target):
        target = os.path.join(target, "index.html")
    return target


def parse_stamp(s: str) -> datetime:
    return datetime.fromisoformat(s)


def main() -> int:
    failures: list[str] = []
    unstamped: list[str] = []
    tables_checked = rows_checked = 0
    links_checked = 0

    dash_path = os.path.join(ROOT, "data", "model", "dashboard.json")
    data_stamp = None
    if os.path.exists(dash_path):
        with open(dash_path) as f:
            data_stamp = parse_stamp(json.load(f)["generated_at"])

    for page in PAGES:
        rel = os.path.relpath(page, ROOT)
        if not os.path.exists(page):
            failures.append(f"{rel}: page missing")
            continue
        with open(page, encoding="utf-8") as f:
            text = f.read()
        scan = Scan()
        scan.feed(text)

        for ref in scan.refs:
            target = resolve(os.path.dirname(page), ref)
            if target is None:
                continue
            links_checked += 1
            if not os.path.exists(target):
                failures.append(f"{rel}: broken link '{ref}'")

        for t in scan.tables:
            if "Source" not in t["headers"]:
                continue
            tables_checked += 1
            for i, row in enumerate(t["rows"], start=1):
                rows_checked += 1
                if not any(row):
                    failures.append(f"{rel}: table row {i} has no https source link")

        if scan.stamp is None:
            unstamped.append(rel)
        elif data_stamp is not None and parse_stamp(scan.stamp) < data_stamp:
            failures.append(
                f"{rel}: stale — 'Data built {scan.stamp}' is older than data {data_stamp.isoformat()}")

    print(f"pages checked: {len(PAGES)}")
    print(f"internal links resolved: {links_checked}")
    print(f"source tables: {tables_checked}, rows with https source link checked: {rows_checked}")
    if unstamped:
        print(f"unstamped pages (earlier generators, flagged F19): {len(unstamped)}")
        for u in unstamped:
            print(f"  - {u}")
    if failures:
        print(f"FAILED: {len(failures)}")
        for f_ in failures[:200]:
            print(f"  - {f_}")
        return 1
    print("PASS: committed site has no broken links, no source-less rows, and no stale stamps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
