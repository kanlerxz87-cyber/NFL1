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
    "index.html", "governance.html", "dashboard.html", "executive-summary.html", "requirements.html",
    "questions.html", "suggestions.html", "strategy-lab.html", "leaderboard.html",
    "bet-types.html", "injuries.html", "depth-chart.html", "data-tables.html",
    "verification.html", "flagged.html", "deployment.html", "integration.html",
    "legacy-site.html",
    "pages/lines.html", "pages/strategies.html", "pages/injuries.html",
    "pages/props.html", "pages/audit.html", "pages/evidence.html",
    "pages/questions.html", "pages/suggestions.html", "pages/review.html",
    "pages/executive.html", "pages/analysis.html", "pages/decisions.html",
    "pages/data.html", "pages/verified.html", "pages/verified-lines.html",
    "pages/availability.html", "pages/teams.html", "pages/standings.html",
    "pages/flagged.html", "pages/executive-summary.html",
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
    """Collects data-table rows, page links and anchors.

    A table counts as a data table when it is marked ``class="data-table"`` (the
    governance registers) or when its header row declares a "Source" column (the
    Decision Lab pages).  Both conventions put a source link on every data row, and
    both are therefore held to the same rule.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.ids = set()
        self.rows = []
        self._table = None
        self._row = None
        self._td = None
        self._in_thead = False
        self._headers = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for key in ("href", "src"):
            if a.get(key):
                self.links.append((tag, key, a[key]))
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                classes = (a.get("class") or "").split()
                self._table = {"data": "data-table" in classes, "headers": [], "rows": []}
        elif tag == "thead" and self._table is not None:
            self._in_thead = True
            self._headers = []
        elif tag == "th" and self._table is not None and self._in_thead:
            self._td = dict(blank=False, value=False, text=[], links=[])
        elif tag == "tr":
            if self._in_thead:
                self._headers = []
            elif self._table is not None and self._table["data"]:
                self._row = dict(verified=True, links=[], cells=[], id=a.get("id"))
                if a.get("data-verified") == "false":
                    self._row["verified"] = False
        elif tag == "td" and self._row is not None:
            classes = (a.get("class") or "").split()
            self._td = dict(blank="blank" in classes, value="data-value" in classes,
                            text=[], links=[])
            self._row["cells"].append(self._td)
        elif tag == "a":
            href = a.get("href") or ""
            if self._row is not None:
                self._row["links"].append(href)
            if self._td is not None:
                self._td["links"].append(href)

    def handle_data(self, data):
        if self._td is not None:
            self._td["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "th" and self._td is not None and self._in_thead:
            self._headers.append("".join(self._td["text"]).strip().lower())
            self._td = None
        elif tag == "thead":
            self._in_thead = False
            if self._table is not None and "source" in self._headers:
                self._table["data"] = True
        elif tag == "td" and self._td is not None:
            self._td = None
        elif tag == "tr" and self._row is not None:
            self._table["rows"].append(self._row)
            self._row = None
        elif tag == "table":
            self._depth = max(0, self._depth - 1)
            if self._depth == 0 and self._table is not None:
                self.rows.extend(self._table["rows"])
                self._table = None


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
            target = os.path.normpath(os.path.join(os.path.dirname(path), clean))
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
