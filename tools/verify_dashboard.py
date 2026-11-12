#!/usr/bin/env python3
"""Independent checks on dashboard/*.html. Run after tools/build_dashboard.py.

Hard failures (exit 1):
  * a table row in tbody has no link at all
  * a cell marked data-verified="false" contains a value (it must be blank apart from its flag)
  * an internal link points to a file that does not exist under dashboard/
  * a page is missing its title or the shared stylesheet

Reported, not failed (listed so a reviewer can act on them):
  * rows whose only links are repository files or other non-official hosts
  * unverified cells (count per page)

Writes dashboard/verification_report.json (committed) with per-page counts.
"""
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DASH = os.path.join(ROOT, "dashboard")
OFFICIAL = re.compile(r"^https://(www\.)?(nfl\.com|operations\.nfl\.com|nextgenstats\.nfl\.com|chiefs\.com|packers\.com|49ers\.com|static\.www\.nfl\.com|itl\.nist\.gov|nj\.gov|docs\.github\.com)/")
REPO = "https://github.com/kanlerxz87-cyber/NFL1/"


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_tbody = False
        self.rows = []          # each: {"hrefs": [...], "unverified": [...], "text": ""}
        self.row = None
        self.cell = None
        self.hrefs_all = []
        self.has_title = False
        self.has_css = False
        self._in_title = False
        self._title = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "link" and a.get("rel") == "stylesheet" and a.get("href") == "style.css":
            self.has_css = True
        if tag == "tbody":
            self.in_tbody = True
        if tag == "tr" and self.in_tbody:
            self.row = {"hrefs": [], "unverified": [], "text": ""}
        if tag == "td" and self.row is not None:
            self.cell = {"verified": a.get("data-verified"), "text": "", "cls": a.get("class", "")}
        if tag == "a" and "href" in a:
            self.hrefs_all.append(a["href"])
            if self.row is not None:
                self.row["hrefs"].append(a["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "tbody":
            self.in_tbody = False
        if tag == "td" and self.row is not None and self.cell is not None:
            if self.cell["verified"] == "false":
                visible = re.sub(r"⚑\s*[A-Z0-9-]+", "", self.cell["text"]).strip()
                if visible:
                    self.row["unverified"].append(visible)
            self.row["text"] += " " + self.cell["text"]
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self._in_title:
            self._title += data
        if self.cell is not None:
            self.cell["text"] += data

    @property
    def title(self):
        return self._title.strip()


def classify(href):
    if OFFICIAL.match(href):
        return "official"
    if href.startswith(REPO):
        return "internal"
    if href.startswith("http"):
        return "other"
    return "local"


def main():
    errors = []
    report = {"pages": {}, "external_hosts": {}, "errors": []}
    html_files = sorted(f for f in os.listdir(DASH) if f.endswith(".html"))
    for fname in html_files:
        p = Page()
        with open(os.path.join(DASH, fname), encoding="utf-8") as f:
            p.feed(f.read())
        if not p.title:
            errors.append(f"{fname}: missing <title>")
        if not p.has_css:
            errors.append(f"{fname}: missing style.css link")
        rows_no_link = []
        rows_official = rows_internal = rows_other = 0
        unverified_cells = 0
        bad_blank = []
        for i, r in enumerate(p.rows):
            kinds = {classify(h) for h in r["hrefs"]}
            if not r["hrefs"]:
                rows_no_link.append(i)
            elif "official" in kinds:
                rows_official += 1
            elif "internal" in kinds:
                rows_internal += 1
            else:
                rows_other += 1
            if r["unverified"]:
                bad_blank.extend(r["unverified"])
            unverified_cells += r["text"].count("⚑")
        if rows_no_link:
            errors.append(f"{fname}: {len(rows_no_link)} table row(s) with no source link (rows {rows_no_link[:5]})")
        if bad_blank:
            errors.append(f"{fname}: unverified cell(s) contain a value: {bad_blank[:3]}")
        for h in p.hrefs_all:
            k = classify(h)
            if k == "local":
                target = h.split("#")[0]
                if target and not os.path.exists(os.path.join(DASH, target)):
                    errors.append(f"{fname}: broken internal link -> {h}")
            elif k in ("official", "other"):
                host = re.match(r"https?://([^/]+)", h).group(1)
                report["external_hosts"][host] = report["external_hosts"].get(host, 0) + 1
        report["pages"][fname] = {
            "title": p.title,
            "table_rows": len(p.rows),
            "rows_with_official_source": rows_official,
            "rows_with_internal_source_only": rows_internal,
            "rows_with_other_source_only": rows_other,
            "rows_with_no_link": len(rows_no_link),
            "unverified_cells_flagged": unverified_cells,
        }
    report["errors"] = errors
    report["result"] = "FAIL" if errors else "PASS"
    with open(os.path.join(DASH, "verification_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    for k, v in report["pages"].items():
        print(f'{k:18s} rows={v["table_rows"]:4d} official={v["rows_with_official_source"]:4d} internal-only={v["rows_with_internal_source_only"]:3d} other-only={v["rows_with_other_source_only"]:3d} unverified-cells={v["unverified_cells_flagged"]:4d}')
    print("external hosts linked:", json.dumps(report["external_hosts"]))
    if errors:
        print("ERRORS:")
        for e_ in errors:
            print(" -", e_)
        return 1
    print("RESULT: PASS (no hard failures)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
