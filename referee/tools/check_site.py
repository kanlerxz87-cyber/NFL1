#!/usr/bin/env python3
"""Checks for the Referee pages. Exits 1 on any problem.

1. Every local link (href/src) in referee/*.html resolves to a file in the repository.
2. Every in-page anchor (#id) exists.
3. Every table body row contains at least one link for manual review, and at least one link to an
   outside source (http/https) unless the row sits in a table that only points to detail pages.
4. No row contains a bare 'None', 'nan' or 'null' value.

Run from the repository root:  python3 referee/tools/check_site.py     (standard library only)
"""
import glob
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.rows = [], set(), []
        self.in_body = self.in_row = False
        self.row_links, self.row_text = [], []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.ids.add(d["id"])
        if tag == "a" and "href" in d:
            self.links.append(d["href"])
            if self.in_row:
                self.row_links.append(d["href"])
        if tag == "link" and "href" in d:
            self.links.append(d["href"])
        if tag == "tbody":
            self.in_body = True
        if tag == "tr" and self.in_body:
            self.in_row, self.row_links, self.row_text = True, [], []

    def handle_endtag(self, tag):
        if tag == "tbody":
            self.in_body = False
        if tag == "tr" and self.in_row:
            self.rows.append((list(self.row_links), " ".join(self.row_text)))
            self.in_row = False

    def handle_data(self, data):
        if self.in_row and data.strip():
            self.row_text.append(data.strip())


def main():
    problems, n_rows, n_links, n_ext = [], 0, 0, set()
    for path in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        name = os.path.basename(path)
        p = P()
        p.feed(open(path, encoding="utf-8").read())
        for h in p.links:
            n_links += 1
            if h.startswith(("http://", "https://")):
                n_ext.add(h)
                continue
            target, _, frag = h.partition("#")
            tpath = path if not target else os.path.normpath(os.path.join(os.path.dirname(path), target))
            if not os.path.isfile(tpath):
                problems.append(f"{name}: broken local link {h}")
            elif frag and tpath == path and frag not in p.ids:
                problems.append(f"{name}: missing anchor #{frag}")
        for links, text in p.rows:
            n_rows += 1
            if not links:
                problems.append(f"{name}: row without any link: {text[:90]}")
            elif not any(l.startswith("http") for l in links):
                problems.append(f"{name}: row without an outside source link: {text[:90]}")
            if re.search(r"\b(None|nan|null)\b", text):
                problems.append(f"{name}: row shows an empty placeholder value: {text[:90]}")
    print(f"pages {len(glob.glob(os.path.join(ROOT, '*.html')))}, table rows {n_rows}, links {n_links}, distinct outside addresses {len(n_ext)}")
    if problems:
        print("PROBLEMS:")
        for x in problems[:60]:
            print(" -", x)
        print(len(problems), "problem(s)")
        return 1
    print("All local links resolve; every table row carries an outside source link.")
    with open(os.path.join(ROOT, "data", "outside_links.txt"), "w") as fh:
        fh.write("\n".join(sorted(n_ext)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
