#!/usr/bin/env python3
"""venue/verify.py — gate for the Venues & Weather sub-site (session cc5a9cdd).

Checks, against the published HTML itself:
  1. Every table row carries at least one official https source link.
  2. Every UNVERIFIED/FLAGGED cell links to flagged.html in the same row.
  3. Every local href resolves to a file that exists.
  4. venue/index.html links every other venue page (sub-site reachability).
  5. Every external link uses an allow-listed official host.

Run:  python3 venue/verify.py     (exit 0 = pass)
"""
from __future__ import annotations

import html
import os
import re
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ALLOWED_HOSTS = (
    "https://www.nfl.com/",
    "https://static.www.nfl.com/",
    "https://api.weather.gov/",
    "https://operations.nfl.com/",
    "https://media.nfl.com/",
)

PAGES = ["index.html", "week10.html", "week11.html", "schedule.html", "flagged.html"]


class Doc(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.tables: list[dict] = []
        self._table = None
        self._row = None
        self._cell = None
        self._in_head = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and "href" in d:
            self.hrefs.append(d["href"])
            if self._cell is not None:
                self._cell.append(("link", d["href"]))
        elif tag == "table":
            self._table = {"rows": []}
        elif tag == "thead":
            self._in_head = True
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag == "th" and self._cell is not None and self._in_head:
            self._cell = None
        elif tag == "thead":
            self._in_head = False
        elif tag == "td" and self._cell is not None:
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if not self._in_head:
                self._table["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(("text", data))


def main() -> int:
    errors: list[str] = []
    docs: dict[str, Doc] = {}

    for name in PAGES:
        path = os.path.join(HERE, name)
        if not os.path.isfile(path):
            errors.append(f"missing page: venue/{name}")
            continue
        doc = Doc()
        with open(path, encoding="utf-8") as fh:
            doc.feed(fh.read())
        docs[name] = doc

    for name, doc in docs.items():
        # 1. every table row has an https source link
        for ti, table in enumerate(doc.tables, 1):
            for ri, row in enumerate(table["rows"], 1):
                links: list[str] = []
                texts: list[str] = []
                for cell in row:
                    for kind, value in cell:
                        (links if kind == "link" else texts).append(value)
                if not any(h.startswith("https://") for h in links):
                    errors.append(
                        f"venue/{name} table {ti} row {ri}: no official https source link"
                    )
                text = "".join(texts)
                # flag labels must lead to flagged.html — except on flagged.html itself,
                # which is the destination.
                if name != "flagged.html" and re.search(r"(UNVERIFIED|FLAGGED)", text):
                    if not any(h.endswith("flagged.html") or "flagged.html#" in h
                               for h in links):
                        errors.append(
                            f"venue/{name} table {ti} row {ri}: flag label without "
                            "flagged.html link"
                        )
                # 5. external hosts
                for h in links:
                    if h.startswith("http") and not h.startswith(ALLOWED_HOSTS):
                        errors.append(f"venue/{name}: non-allowlisted host {h}")
        # 3. local hrefs resolve
        for h in doc.hrefs:
            if h.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = os.path.normpath(os.path.join(HERE, h.split("#")[0]))
            if not os.path.exists(target):
                errors.append(f"venue/{name}: broken local link {h}")
        # 4. index links every venue page
        if name == "index.html":
            for other in PAGES:
                if other == "index.html":
                    continue
                if other not in doc.hrefs:
                    errors.append(f"venue/index.html does not link {other}")

    if errors:
        print("VENUE VERIFY FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print(f"RESULT: PASS — {len(docs)} pages, "
          f"{sum(len(d.tables) for d in docs.values())} tables, all rows sourced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
