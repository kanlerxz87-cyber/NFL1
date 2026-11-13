#!/usr/bin/env python3
"""build_site_all.py — build every published page, in one order, deterministically.

Session 4c043747 (final integration).  Run from the repository root:

    python3 tools/build_site_all.py            # build
    python3 tools/build_site_all.py --check    # build, then fail if anything changed

Why one script
--------------
Before this existed, four different generators wrote into the same directories and two of
them wrote the *same* file (index.html, pages/lines.html).  Whichever ran last won, so the
published site could not be reproduced from the repository and the committed pages could
drift away from the data they claim to show.

The order below is the contract:

  1. scripts/verified/build_site.py        -> pages/{data,verified-lines,analysis,decisions,verified}.html
  2. scripts/verified/build_availability.py -> pages/availability.html
  3. tools/build.py                         -> the governance registers at the repository root,
                                              dashboard.html and README.md
  4. pipeline/gen_site.py                   -> index.html and the Decision Lab pages
                                              (last, so the landing page's site map lists every
                                              page that the earlier steps produced)
  5. scripts/verified/normalize_nav.py      -> one canonical navigation on index.html and pages/
  6. tools/build_docs_site.py               -> the docs/ sub-site
  7. PYTHONPATH=src scripts/build_site.py   -> the verified-lab/ sub-site
  8. referee/tools/build_site.py            -> the referee/ sub-site

Every step is deterministic: the pages are a function of the data files, so running the
script twice produces the same bytes and `--check` can be used as a CI gate.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STEPS = [
    ("verified pages", [sys.executable, "scripts/verified/build_site.py"], ROOT),
    ("availability page", [sys.executable, "scripts/verified/build_availability.py"], ROOT),
    ("governance registers", [sys.executable, "tools/build.py"], ROOT),
    ("landing page and decision lab", [sys.executable, "gen_site.py"], os.path.join(ROOT, "pipeline")),
    ("canonical navigation", [sys.executable, "scripts/verified/normalize_nav.py"], ROOT),
    ("docs sub-site", [sys.executable, "tools/build_docs_site.py"], ROOT),
    ("verified-lab sub-site", [sys.executable, "scripts/build_site.py"], ROOT),
    ("referee sub-site", [sys.executable, "referee/tools/build_site.py"], ROOT),
]


def main() -> int:
    check = "--check" in sys.argv
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(ROOT, "src") + os.pathsep + env.get("PYTHONPATH", "")

    for label, cmd, cwd in STEPS:
        print(f"--- {label}: {' '.join(cmd)}", flush=True)
        r = subprocess.run(cmd, cwd=cwd, env=env)
        if r.returncode != 0:
            print(f"FAILED: {label} (exit {r.returncode})")
            return r.returncode

    if check:
        print("--- checking that the committed pages equal the generated pages")
        r = subprocess.run(["git", "diff", "--exit-code", "--", "*.html", "README.md", "docs/", "verified-lab/", "referee/"],
                           cwd=ROOT)
        if r.returncode != 0:
            print("FAILED: the committed pages differ from the generated pages "
                  "(run tools/build_site_all.py and commit the result)")
            return 1
        print("OK: the committed pages are exactly what the generators produce")
    return 0


if __name__ == "__main__":
    sys.exit(main())
