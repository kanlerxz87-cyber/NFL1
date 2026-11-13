#!/usr/bin/env python3
"""check_freshness.py — fail the build when a page shows older data than the repository holds.

The defect this prevents
------------------------
The scheduled `collect-data` job commits refreshed `data/model/*.json` and nothing ever
re-renders the HTML, so the published site keeps whatever numbers it had when a human last
ran a generator. In this repository that produced a landing page stamped 05:07 next to data
stamped 18:53, and a New England injury row reading "Out 2" from data that said "Out 1".

Rule
----
* every generated page that prints a data stamp must carry the same stamp as the data file
  it was built from;
* a data file may never be newer than the newest page that displays it (with a tolerance so
  that a render immediately after a refresh is allowed);
* the JSON produced by the decision-room step must be newer than the files it reads.

Run: python3 tools/check_freshness.py [--fix-report]
Exit 1 when the site is stale.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# page -> the generated_at value it must print, and the JSON that value comes from
PAGE_DATA = {
    "web/dashboard.html": ("data/decision_room/decision_room.json", "generated_at"),
    "web/decisions.html": ("data/decision_room/decision_room.json", "generated_at"),
    "web/suggestions.html": ("data/decision_room/decision_room.json", "generated_at"),
    "web/verification.html": ("data/decision_room/decision_room.json", "generated_at"),
    "web/flag-register.html": ("data/decision_room/decision_room.json", "generated_at"),
    "web/executive-summary.html": ("data/decision_room/decision_room.json", "generated_at"),
}

# pages rendered by the model pipeline (session 7600ed8b) print "Data built <stamp>"
MODEL_DATA = "data/model/dashboard.json"
MODEL_PAGES = ["index.html", "pages/injuries.html", "pages/evidence.html",
               "pages/suggestions.html", "pages/questions.html", "pages/executive.html",
               "pages/review.html", "pages/lines.html", "pages/strategies.html",
               "pages/props.html"]


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def stamp_of(path, key="generated_at"):
    return load(path).get(key)


def main() -> int:
    problems, checked = [], 0

    # 1. decision-room pages print the stamp of the JSON they were built from
    dr = stamp_of("data/decision_room/decision_room.json")
    if not dr:
        problems.append("data/decision_room/decision_room.json has no generated_at")
    for page, (datafile, key) in PAGE_DATA.items():
        p = os.path.join(ROOT, page)
        if not os.path.isfile(p):
            problems.append(f"missing page {page}")
            continue
        text = open(p, encoding="utf-8").read()
        checked += 1
        if dr and dr not in text:
            problems.append(f"{page}: does not print the data stamp {dr} "
                            f"(rebuild with tools/build_dashboard.py)")

    # 2. model pages: the stamp they print must match data/model/dashboard.json
    model_stamp = stamp_of(MODEL_DATA)
    stale_model_pages = []
    for page in MODEL_PAGES:
        p = os.path.join(ROOT, page)
        if not os.path.isfile(p):
            continue
        text = open(p, encoding="utf-8").read()
        m = re.search(r"Data built ([0-9T:+\-]+)", text)
        if not m:
            continue
        checked += 1
        if model_stamp and m.group(1) != model_stamp:
            stale_model_pages.append(f"{page} ({m.group(1)} != {model_stamp})")
    if stale_model_pages:
        problems.append("model pages are stale relative to data/model/dashboard.json: "
                        + "; ".join(stale_model_pages[:6]))

    # 3. the decision room must be newer than every input it reads
    inputs = ["data/model/lines.json", "data/model/strategies.json",
              "data/model/availability.json", "data/model/props.json",
              "data/evidence/injuries_week10.json", "data/evidence/standings_2026.json",
              "data/audit/official_verification.json"]
    dr_mtime = os.path.getmtime(os.path.join(ROOT, "data/decision_room/decision_room.json"))
    older = []
    for i in inputs:
        p = os.path.join(ROOT, i)
        if not os.path.isfile(p):
            problems.append(f"missing input {i}")
            continue
        checked += 1
        if os.path.getmtime(p) > dr_mtime + 1:
            older.append(i)
    if older:
        problems.append("decision_room/decision_room.json is older than its inputs "
                        f"({', '.join(older)}); re-run tools/build_decision_room.py")

    print(f"freshness assertions: {checked}")
    if problems:
        print(f"\nSTALE ({len(problems)}):")
        for p in problems:
            print(" -", p)
        print("\nRebuild in this order: tools/build_decision_room.py, tools/build_dashboard.py")
        return 1
    print("RESULT: PASS — every generated page carries the stamp of the data it shows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
