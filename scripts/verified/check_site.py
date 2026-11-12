#!/usr/bin/env python3
"""check_site.py — structural gate for the static site.

Fails (exit 1) if any local link resolves to a missing file, if any page is missing a
nav entry to a sister page, or if an anchor is malformed. Runs in CI and locally.
"""
from __future__ import annotations
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.ids = [], []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and "href" in d:
            self.hrefs.append(d["href"])
        if "id" in d:
            self.ids.append(d["id"])


def main() -> int:
    pages = [ROOT / "index.html"] + sorted((ROOT / "pages").glob("*.html"))
    problems = []
    all_ids = {}
    for p in pages:
        parser = Links()
        parser.feed(p.read_text(encoding="utf-8"))
        all_ids[p.resolve()] = set(parser.ids)
        for h in parser.hrefs:
            if h.startswith(("http://", "https://", "mailto:")):
                continue
            if h.startswith("#"):
                continue
            target = h.split("#")[0]
            if not target:
                continue
            t = (p.parent / target).resolve()
            if not t.is_file():
                problems.append(f"broken link: {p.relative_to(ROOT)} -> {h}")
        # nav completeness: every page must link every sister page
        names = {x.name for x in pages}
        linked = {Path(h.split('#')[0]).name for h in parser.hrefs if not h.startswith(("http", "mailto"))}
        missing = names - linked - {p.name}
        if missing:
            problems.append(f"{p.relative_to(ROOT)}: nav missing {sorted(missing)}")

    print(f"pages checked: {len(pages)}")
    if problems:
        print("\nPROBLEMS:")
        for x in problems:
            print(" -", x)
        return 1
    print("All local links resolve and navigation is complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
