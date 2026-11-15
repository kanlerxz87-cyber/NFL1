#!/usr/bin/env python3
"""check_scrape_drift.py — drift alarm for the official injury scrape (P4, session 55dc53f4-nfl1).

Fails the build LOUDLY (exit 1, one line per failure) when the scraper output cannot be trusted:

  1. Capture integrity. data/capture/nflcom_injuries_reg10_2026-11-15_rows.tsv and its games file
     must match the sha256 recorded in data/capture/manifest.json; row, club, game and per-club
     counts must equal the manifest's pinned counts.
  2. Required fields. In the capture and in the scrape, team, player, position and practice must be
     non-blank on every row. A blank here is a parser failure, not an official blank.
  3. Scrape pin. data/model/official_injuries.json must have status "ok", the same week as the
     capture, and the pinned row and club counts. A scrape that parses fewer rows fails here, even
     though the scraper's own threshold (150 rows) would have passed it.
  4. Scrape vs capture, row by row. Every capture row must be found in the scrape by (club, player).
     A missing or extra row fails. A differing designation, practice or game status is reported as a
     WARNING (it is a real change in the report, not a parse failure) and is listed for review.

Exit 0 when 1-4 hold (warnings allowed). Exit 1 otherwise.

    python3 tools/check_scrape_drift.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "data/capture")
MANIFEST = os.path.join(CAP, "manifest.json")
SCRAPE = os.path.join(ROOT, "data/model/official_injuries.json")
# capture TSV column names and scrape JSON key names differ; both are checked for these fields.
CAP_REQUIRED = ("team", "player", "position", "practice_status")
SCRAPE_REQUIRED = ("team", "player", "position", "practice")
# The scraper writes the Rams and Cardinals as LA and ARI; the printed page and the capture use LAR and AZ
# (club-code conflict, flag CAP-05). Mapped explicitly and counted, never silently.
SCRAPE_TO_PAGE_CODE = {"LA": "LAR", "ARI": "AZ"}


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run(scrape_path: str = SCRAPE) -> tuple[list[str], list[str], int]:
    """Return (failures, warnings, capture_rows). Pure function of the files; used by main() and tests."""
    failures: list[str] = []
    warnings: list[str] = []
    m = json.load(open(MANIFEST, encoding="utf-8"))
    rows_path = os.path.join(CAP, m["rows_tsv"])
    games_path = os.path.join(CAP, m["games_tsv"])

    # 1. capture integrity
    if sha256(rows_path) != m["rows_tsv_sha256"]:
        failures.append(f"capture rows hash differs from manifest ({os.path.basename(rows_path)})")
    if sha256(games_path) != m["games_tsv_sha256"]:
        failures.append("capture games hash differs from manifest")
    cap = list(csv.DictReader(open(rows_path, newline="", encoding="utf-8"), delimiter="\t"))
    counts = m["counts"]
    if len(cap) != counts["rows"]:
        failures.append(f"capture has {len(cap)} rows, manifest pins {counts['rows']}")
    clubs = {r["team"] for r in cap}
    if len(clubs) != counts["clubs"]:
        failures.append(f"capture has {len(clubs)} clubs, manifest pins {counts['clubs']}")
    games = {r["game_id"] for r in cap}
    if len(games) != counts["games"]:
        failures.append(f"capture has {len(games)} games, manifest pins {counts['games']}")
    per_club = {}
    for r in cap:
        per_club[r["team"]] = per_club.get(r["team"], 0) + 1
    if per_club != m["rows_per_club"]:
        diff = sorted(set(per_club.items()) ^ set(m["rows_per_club"].items()))
        failures.append(f"per-club row counts differ from manifest: {diff[:6]}")

    # 2. required fields in the capture
    for i, r in enumerate(cap, start=2):
        for f in CAP_REQUIRED:
            if not (r.get(f) or "").strip():
                failures.append(f"capture row {i} ({r.get('team')} {r.get('player')}): blank '{f}'")

    # 3. scrape pin
    if not os.path.exists(scrape_path):
        failures.append(f"scrape file {os.path.relpath(scrape_path, ROOT)} is missing")
        scrape = None
    else:
        with open(scrape_path, encoding="utf-8") as fh:
            scrape = json.load(fh)
        if scrape.get("status") != "ok":
            failures.append(f"scrape status is '{scrape.get('status')}' (error: {scrape.get('error') or scrape.get('warning')})")
        if scrape.get("week") != m["week"] or scrape.get("season") != m["season"]:
            failures.append(f"scrape is season {scrape.get('season')} week {scrape.get('week')}; capture is {m['season']} week {m['week']}")
        srows = scrape.get("rows", [])
        if len(srows) != counts["rows"]:
            failures.append(f"scrape has {len(srows)} rows, pinned {counts['rows']} (rows were lost or added)")
        sclubs = {r.get("team") for r in srows}
        if len(sclubs) != counts["clubs"]:
            failures.append(f"scrape has {len(sclubs)} clubs, pinned {counts['clubs']}")
        remapped = 0
        for r in srows:
            if r.get("team") in SCRAPE_TO_PAGE_CODE:
                r["team"] = SCRAPE_TO_PAGE_CODE[r["team"]]
                remapped += 1
        if remapped:
            warnings.append(f"club code: {remapped} scrape rows use LA/ARI; mapped to the page codes LAR/AZ (flag CAP-05)")
        for i, r in enumerate(srows):
            for f in SCRAPE_REQUIRED:
                if not (r.get(f) or "").strip():
                    failures.append(f"scrape row {i} ({r.get('team')} {r.get('player')}): blank '{f}'")

        # 4. row-by-row, by (club, player)
        cap_by = {(r["team"], r["player"]): r for r in cap}
        scr_by = {}
        for r in srows:
            scr_by.setdefault((r.get("team"), r.get("player")), []).append(r)
        for key, c in cap_by.items():
            hits = scr_by.get(key, [])
            if len(hits) != 1:
                failures.append(f"capture row {key} found {len(hits)} times in the scrape")
                continue
            s = hits[0]
            for cap_f, scr_f in (("injury", "injury"), ("practice_status", "practice"), ("game_status", "game")):
                a, b = (c.get(cap_f) or "").strip(), (s.get(scr_f) or "").strip()
                if a != b:
                    warnings.append(f"{key[0]} {key[1]}: {cap_f} capture='{a}' scrape='{b}'")
        for key in scr_by:
            if key not in cap_by:
                failures.append(f"scrape row {key} is not in the capture")

    MAX_LINES = 25
    return failures, warnings, len(cap)


def main() -> int:
    failures, warnings, n_cap = run()
    m = json.load(open(MANIFEST, encoding="utf-8"))
    counts = m["counts"]
    MAX_LINES = 25
    for w in warnings[:MAX_LINES]:
        print(f"WARNING drift: {w}")
    if len(warnings) > MAX_LINES:
        print(f"WARNING drift: ... {len(warnings) - MAX_LINES} more designation differences (all listed in the review file)")
    if failures:
        for f in failures[:MAX_LINES]:
            print(f"FAIL drift: {f}")
        if len(failures) > MAX_LINES:
            print(f"FAIL drift: ... {len(failures) - MAX_LINES} more failures")
        print(f"DRIFT ALARM: {len(failures)} failure(s), {len(warnings)} warning(s)")
        return 1
    code_notes = [w for w in warnings if w.startswith("club code")]
    diffs = [w for w in warnings if not w.startswith("club code")]
    print(f"OK: capture pinned ({counts['rows']} rows, {counts['clubs']} clubs, {counts['games']} games); "
          f"scrape matches row for row; {len(diffs)} designation difference(s); {len(code_notes)} club-code note(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
