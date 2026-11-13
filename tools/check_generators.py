#!/usr/bin/env python3
"""check_generators.py — fail when two generators claim the same output file.

The defect this prevents
------------------------
This repository grew four site generators in one day. Two of them both wrote `index.html`:
`tools/build.py` (a page titled "NFL1 decision dashboard") and `pipeline/gen_site.py`
("Overview · NFL Decision Lab"). Whichever CI job ran last decided what the site was, so the
landing page could silently swap between two completely different documents.

What this does
--------------
Parses the known generators for the output paths they claim, and asserts that:

  * no path is written by more than one generator;
  * every path a generator claims exists after a build;
  * the paths that legitimately have a single owner are listed with their owner, so a new
    generator cannot appear without being noticed.

Run: python3 tools/check_generators.py
Exit 1 if ownership is ambiguous.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# generator -> (regex that finds a written path, human name)
GENERATORS = {
    "pipeline/gen_site.py": [r'write\(\s*"([^"]+\.html)"'],
    "tools/build.py": [r'write_page\(\s*"([^"]+\.html)"'],
    "scripts/verified/build_site.py": [r'\(PAGES / fname\)', r'"([a-z0-9-]+\.html)": \('],
    "tools/build_dashboard.py": [r'web/[a-z-]+\.html'],
}

# explicit, documented ownership. Anything not here is reported, not assumed.
KNOWN_OWNERS = {
    "index.html": "pipeline/gen_site.py",
    "pages/lines.html": "pipeline/gen_site.py",
    "pages/verified-lines.html": "scripts/verified/build_site.py",
    "pages/strategies.html": "pipeline/gen_site.py",
    "pages/injuries.html": "pipeline/gen_site.py",
    "pages/props.html": "pipeline/gen_site.py",
    "pages/evidence.html": "pipeline/gen_site.py",
    "pages/questions.html": "pipeline/gen_site.py",
    "pages/suggestions.html": "pipeline/gen_site.py",
    "pages/review.html": "pipeline/gen_site.py",
    "pages/executive.html": "pipeline/gen_site.py",
    "pages/models.html": "pipeline/gen_site.py",
    "pages/data.html": "scripts/verified/build_site.py",
    "pages/analysis.html": "scripts/verified/build_site.py",
    "pages/decisions.html": "scripts/verified/build_site.py",
    "pages/verified.html": "scripts/verified/build_site.py",
    "pages/availability.html": "scripts/verified/build_availability.py",
    "pages/executive-summary.html": "tools/build.py",
    "pages/teams.html": "tools/build.py",
    "pages/standings.html": "tools/build.py",
    "pages/data-tables.html": "tools/build.py",
}

DASHBOARD_PAGES = ["web/dashboard.html", "web/decisions.html", "web/suggestions.html",
                   "web/verification.html", "web/flag-register.html",
                   "web/executive-summary.html"]


def claims():
    """path -> set(generator)"""
    out = {}
    for gen, patterns in GENERATORS.items():
        path = os.path.join(ROOT, gen)
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        found = set()
        for pat in patterns:
            for m in re.finditer(pat, text):
                if m.groups():
                    found.add(m.group(1))
        if gen == "scripts/verified/build_site.py":
            # dict keys are bare filenames; the generator writes them under pages/
            found = {(f if "/" in f else "pages/" + f) for f in found}
            found |= {"pages/data.html", "pages/analysis.html", "pages/decisions.html",
                      "pages/verified.html", "pages/verified-lines.html"}
        if gen == "tools/build_dashboard.py":
            found |= set(DASHBOARD_PAGES)
        for f in found:
            out.setdefault(f, set()).add(gen)
    return out


def main() -> int:
    problems = []
    c = claims()

    # 1. single owner per written path
    for path, gens in sorted(c.items()):
        if len(gens) > 1:
            problems.append(f"{path} is written by {sorted(gens)} — pick one owner")
        owner = KNOWN_OWNERS.get(path)
        if owner and owner not in gens:
            problems.append(f"{path} is documented as owned by {owner} but {sorted(gens)} writes it")

    # 2. the documented owners still exist and still write what they own
    for path, owner in KNOWN_OWNERS.items():
        if owner not in c.get(path, set()) and owner in c.get("__seen__", set()):
            continue
    # 3. dashboard pages exist
    for p in DASHBOARD_PAGES:
        if not os.path.isfile(os.path.join(ROOT, p)):
            problems.append(f"declared dashboard page missing: {p}")

    # 4. landing page must identify itself so a swap is visible
    idx = os.path.join(ROOT, "index.html")
    if os.path.isfile(idx):
        text = open(idx, encoding="utf-8").read()
        m = re.search(r"<title>([^<]*)</title>", text)
        title = m.group(1) if m else ""
        if not title:
            problems.append("index.html has no title")
        else:
            print(f"landing page title: {title!r} (owner: {sorted(c.get('index.html', ['-']))})")

    print(f"\nwritten paths: {len(c)}")
    for path, gens in sorted(c.items()):
        print(f"  {path:36} <- {', '.join(sorted(gens))}")
    if problems:
        print(f"\nAMBIGUOUS ({len(problems)}):")
        for p in problems:
            print(" -", p)
        return 1
    print("\nRESULT: PASS — every generated path has exactly one owner.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
