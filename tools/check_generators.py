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
    # Session 0c5215c1-nfl1: the pre-registration sub-site. write() takes bare filenames;
    # the generator writes them under prereg/ (prefix added in claims()).
    "prereg/build.py": [r'write\(\s*"([^"/]+\.html)"'],
    # Session 1d824ec2-nfl1: the transactions/reserve sub-site. Bare filenames under reserve/.
    "tools/build_reserve_site.py": [r'OUT_DIR / "([^"/]+\.html)"'],
    # Session cc5a9cdd-nfl1: the Venues & Weather sub-site. write() takes bare
    # filenames; the generator writes them under venue/ (prefix added in claims()).
    "venue/build.py": [r'write\(\s*"([^"/]+\.html)"'],
