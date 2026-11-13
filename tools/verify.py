#!/usr/bin/env python3
"""Validate the generated NFL1 site.

Checks, line by line:
  1. every row of every data table has at least one link to an allow-listed official domain;
  2. every row marked unverified links to flagged.html and keeps all value cells blank;
  3. every blank cell really is blank;
  4. every internal href/src (including navigation and fragment anchors) resolves;
  5. every registered source URL points to an allow-listed official domain;
  6. every generated page and research document exists.

Writes data/verification_report.json. Exit status 1 on any failure.
Run: python3 tools/verify.py
"""
import html
import json
import os
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

OFFICIAL_DOMAINS = {
    "nfl.com", "operations.nfl.com", "nextgenstats.nfl.com",
    "chiefs.com", "packers.com", "49ers.com",
    "itl.nist.gov", "nj.gov", "docs.github.com", "github.com", "api.github.com",
    "static.www.nfl.com", "static.clubs.nfl.com", "charts-cdn-a.nextgenstats.nfl.com",
}

PAGES = [
    "index.html", "governance.html", "executive-summary.html", "requirements.html", "questions.html",
    "suggestions.html", "strategy-lab.html", "leaderboard.html", "bet-types.html",
    "injuries.html", "depth-chart.html", "data-tables.html", "verification.html",
    "flagged.html", "deployment.html", "integration.html",
]
DOCS = [
    "repo-audit.md", "verification.md", "requirements-analysis.md", "decision-gate.md",
    "improvement-paths.md", "strategy-research.md", "competition-rules.md",
    "injury-tracking.md", "exec-summary.md", "deployment.md",
]


def is_official(url):
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)


class Checker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_data_table = False
        self.in_thead = False
        self.table_depth = 0
        self.rows = []
        self.row = None
        self.td = None
        self.links = []
        self.ids = set()
        self.errors = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for key in ("href", "src"):
            if a.get(key):
                self.links.append((tag, key, a[key]))
        if tag == "thead" and self.in_data_table:
            self.in_thead = True
        if tag == "table" and "data-table" in (a.get("class") or "").split():
            self.in_data_table = True
            self.table_depth = 1
        elif self.in_data_table and tag == "table":
            self.table_depth += 1
        if tag == "tr" and self.in_data_table and not self.in_thead:
            self.row = dict(verified=True, links=[], cells=[], id=a.get("id"))
            if a.get("data-verified") == "false":
                self.row["verified"] = False
        if tag == "a" and self.row is not None:
            href = a.get("href") or ""
            self.row["links"].append(href)
            if self.td is not None:
                self.td["links"].append(href)
        if tag == "td" and self.row is not None:
            classes = (a.get("class") or "").split()
            self.td = dict(blank="blank" in classes, value="data-value" in a,
                           text=[], links=[])
            self.row["cells"].append(self.td)

    def handle_data(self, data):
        if self.td is not None:
            self.td["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "td":
            self.td = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == "thead" and self.in_data_table:
            self.in_thead = False
        if tag == "table" and self.in_data_table:
            self.table_depth -= 1
            if self.table_depth == 0:
                self.in_data_table = False


def check():
    errors = []
    report_rows = []
    total_rows = 0
    total_official = 0
    total_unverified = 0

    sources = json.load(open(os.path.join(DATA, "sources.json"), encoding="utf-8"))
    for s in sources:
        if not is_official(s["url"]):
            errors.append("source %s has a non-official URL: %s" % (s["id"], s["url"]))
    print("source registry: %d URLs checked against official-domain allow-list" % len(sources))

    for page in PAGES:
        path = os.path.join(ROOT, page)
        if not os.path.isfile(path):
            errors.append("missing page: " + page)
            continue
        text = open(path, encoding="utf-8").read()
        c = Checker()
        c.feed(text)
        c.close()
        page_rows = len(c.rows)
        total_rows += page_rows
        official_rows = 0
        unverified_rows = 0

        for i, row in enumerate(c.rows, 1):
            label = "%s row %d%s" % (page, i, " (#%s)" % row["id"] if row["id"] else "")
            hrefs = [h for h in row["links"] if h]
            if not any(is_official(h) for h in hrefs):
                errors.append("%s has no link to an official site" % label)
            else:
                official_rows += 1
            if not row["verified"]:
                unverified_rows += 1
                total_unverified += 1
                if not any(h.startswith("flagged.html") for h in hrefs):
                    errors.append("%s is unverified but has no flagged.html link" % label)
                for j, td in enumerate(row["cells"], 1):
                    if td["value"] and "".join(td["text"]).strip():
                        errors.append("%s column %d is unverified but contains a value" % (label, j))
            for j, td in enumerate(row["cells"], 1):
                if td["blank"] and "".join(td["text"]).strip():
                    errors.append("%s column %d is marked blank but contains text" % (label, j))

        # Internal links (navigation, footer, assets, fragment anchors).
        broken = []
        for tag, key, href in c.links:
            h = href.strip()
            if not h or h == "#":
                continue
            if h.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            if h.startswith("#"):
                if h[1:] not in c.ids:
                    broken.append("%s=%s (missing anchor id %s)" % (key, h, h[1:]))
                continue
            clean = h.split("#", 1)[0].split("?", 1)[0]
            if not clean:
                continue
            target = os.path.normpath(os.path.join(ROOT, clean))
            if not os.path.isfile(target):
                broken.append("%s=%s" % (key, h))
            elif "#" in h:
                frag = h.split("#", 1)[1]
                if frag:
                    other = open(target, encoding="utf-8", errors="ignore").read()
                    if ('id="%s"' % frag) not in other:
                        broken.append("%s=%s (missing anchor id in target)" % (key, h))
        for b in broken:
            errors.append("%s broken internal link: %s" % (page, b))

        total_official += official_rows
        report_rows.append(dict(page=page, rows=page_rows,
                                rows_with_official_source=official_rows,
                                unverified_rows=unverified_rows,
                                broken_internal_links=len(broken)))
        print("  %-26s rows=%-4d official=%-4d unverified=%-3d broken_links=%d" %
              (page, page_rows, official_rows, unverified_rows, len(broken)))

    for doc in DOCS:
        if not os.path.isfile(os.path.join(ROOT, "docs", doc)):
            errors.append("missing research document: docs/" + doc)
    for asset in ("site/assets/style.css", "site/assets/app.js", "site/templates/base.html", ".nojekyll"):
        if not os.path.isfile(os.path.join(ROOT, asset)):
            errors.append("missing asset: " + asset)

    # Every source id referenced by a data row must be registered.
    for name in sorted(f for f in os.listdir(DATA) if f.endswith(".json")):
        obj = json.load(open(os.path.join(DATA, name), encoding="utf-8"))
        if isinstance(obj, list):
            for r in obj:
                if isinstance(r, dict) and r.get("src") and r["src"] not in {s["id"] for s in sources}:
                    errors.append("%s references unknown source id %s" % (name, r["src"]))

    report = dict(
        pages_checked=len(PAGES), research_documents_checked=len(DOCS),
        sources_checked=len(sources), table_rows=total_rows,
        rows_with_official_source=total_official,
        unverified_rows=total_unverified,
        errors=errors,
        pages=report_rows,
        result="PASS" if not errors else "FAIL",
    )
    with open(os.path.join(DATA, "verification_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print("\ntable rows checked: %d | with official source: %d | unverified: %d" %
          (total_rows, total_official, total_unverified))
    if errors:
        print("\nFAILED (%d problems):" % len(errors))
        for e in errors[:60]:
            print(" -", e)
        return 1
    print("RESULT: PASS — every table row has an official source link; no broken internal links.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
