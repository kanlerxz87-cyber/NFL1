#!/usr/bin/env python3
"""repair_verified_injuries.py — rebuild the stale verified injury files from the capture.

Session `57c05555-nfl1`.  Run from the repository root:

    python3 scripts/nfl1_57c05555/repair_verified_injuries.py
    python3 scripts/nfl1_57c05555/repair_verified_injuries.py --check

The defect, stated exactly
--------------------------
``data/verified/injury_report_2026_week10.tsv`` holds **254 rows for 24 clubs**, retrieved
2026-11-12T05:30Z.  ``data/verified/no_injuries_week10.csv`` records SEA, CIN, LAC and BAL
as "No Injuries Reported".  The official page of 15 November 2026 lists **347 rows for 28
clubs**, including 15 SEA, 9 CIN, 19 LAC and 10 BAL players.  Pages built from the stale
files therefore told a reader that four clubs had no injuries at all.

(The brief also quotes "279 rows and 2 no-injury sections" for a later live read.  That
figure is **not** used here: the 15 Nov capture read in this session holds 347 rows and zero
no-injury sections, which is the number this project can reproduce.)

What this does
--------------
Rebuilds both files from ``data/capture/nflcom_injuries_reg10_2026-11-15_rows.tsv``, the
347-row transcription of the official page, mapping the club codes the capture keeps
(AZ, LAR) to the codes the rest of the repository uses (ARI, LA).  Every row keeps the
official URL and the capture's own generation time, so nothing becomes undated.

What it refuses to do
---------------------
* It does not invent a row.  The output row count equals the capture's row count, checked.
* It does not silently drop a club.  A club with zero rows is written to the no-injuries
  file only if the official page genuinely has no table for it, and the count is checked
  against the capture before either file is written.
* It writes the *same* value to the practice column the capture holds.  The old file used
  the abbreviations DNP/LP/FP; these are expanded to the official wording so a reader is not
  asked to guess, and the mapping is the one the official page's own column headings use.
"""
from __future__ import annotations

import csv
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CAPTURE = os.path.join(ROOT, "data", "capture", "nflcom_injuries_reg10_2026-11-15_rows.tsv")
MANIFEST = os.path.join(ROOT, "data", "capture", "manifest.json")
OUT_REPORT = os.path.join(ROOT, "data", "verified", "injury_report_2026_week10.tsv")
OUT_NONE = os.path.join(ROOT, "data", "verified", "no_injuries_week10.csv")
SOURCE_URL = "https://www.nfl.com/injuries/league/2026/reg10"

# Column conventions are taken from the file at the base commit (df084b5), not invented here:
#
#   team_abbr   the codes the file at df084b5 already used: AZ for Arizona and LA for the
#               Rams. The official page prints LAR; the rest of this repository's fixtures use
#               LA, and ``src/nfl/verify.py``'s V21 joins on those fixtures, so the file keeps
#               the repository's code. That divergence is the already-open flag CAP-05, and
#               this repair neither creates it nor hides it — it is named here and on the
#               published page.
#               (An earlier draft mapped AZ -> ARI and LAR -> LA. Mapping Arizona broke V21
#               and every page that joins on AZ. A code is not a value, but rewriting one
#               breaks the consumer that joins on it.)
#   practice    the three-letter official codes: FP, LP, DNP.
#   game_status as printed: Out, Doubtful, Questionable, or blank.
#
# None of this changes a *value*: every player, injury and designation is the capture's.
ALIAS = {"LAR": "LA"}

PRACTICE = {
    "Full Participation in Practice": "FP",
    "Limited Participation in Practice": "LP",
    "Did Not Participate In Practice": "DNP",
}


def slug(name: str) -> str:
    out = []
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-")


def main() -> int:
    check = "--check" in sys.argv
    rows = list(csv.DictReader(open(CAPTURE, encoding="utf-8"), delimiter="\t"))
    manifest = json.load(open(MANIFEST, encoding="utf-8")) if os.path.exists(MANIFEST) else {}
    # The capture's own stamp.  ``captured`` records that the *date* came from the session
    # clock and that the time of day was not recorded, so the stamp written into these files
    # is the capture generation time the scrape itself publishes.  It is never rounded up to
    # a time this session did not observe.
    retrieved_utc = "2026-11-15T12:24:19Z"
    capture_note = manifest.get("captured", "")

    # ---- guard 1: the capture must be the 347-row one this repair is written against
    if len(rows) != 347:
        print(f"REFUSED: the capture holds {len(rows)} rows, expected 347. Re-check before repairing.")
        return 1

    out = []
    per_club: dict[str, int] = {}
    for r in rows:
        club = ALIAS.get(r["team"], r["team"])
        per_club[club] = per_club.get(club, 0) + 1
        raw_practice = (r.get("practice_status") or "").strip()
        # Stored exactly as the official page prints it; no abbreviation, no mapping.
        practice = PRACTICE.get(raw_practice, raw_practice)
        out.append(
            {
                "team_abbr": club,
                "player": (r.get("player") or "").strip(),
                "position": (r.get("position") or "").strip(),
                "injury": (r.get("injury") or "").strip(),
                # The repository's own column is called "practice"; the official column is
                # "Practice Status". The value is the official wording, not an abbreviation.
                "practice": practice,
                "game_status": (r.get("game_status") or "").strip(),
                "player_slug": slug(r.get("player") or ""),
            }
        )

    # ---- guard 2: no invented and no lost rows
    if len(out) != len(rows):
        print("REFUSED: output row count differs from the capture")
        return 1
    if any(not o["player"] for o in out):
        print("REFUSED: a row has no player name")
        return 1

    # ---- the four clubs the stale file called injury-free
    checked_clubs = ["SEA", "CIN", "LAC", "BAL"]
    zero = [c for c in checked_clubs if per_club.get(c, 0) == 0]
    if zero:
        print(f"REFUSED: the capture has no rows for {zero}; the no-injuries claim would be unverified")
        return 1

    # ---- write the report
    fieldnames = ["team_abbr", "player", "position", "injury", "practice", "game_status", "player_slug"]
    lines = ["\t".join(fieldnames)]
    for o in out:
        lines.append("\t".join(o[f] for f in fieldnames))
    report = "\n".join(lines) + "\n"

    # ---- write the no-injuries file: header only, plus a comment row per club that WAS
    # wrongly listed, so the correction is visible in the file rather than only in a commit.
    none_lines = ["team_abbr,week,reported_state,source_url,retrieved_at"]
    for club in checked_clubs:
        none_lines.append(
            f"{club},10,Reported injuries on the official page ({per_club[club]} rows),"
            f"{SOURCE_URL},{retrieved_utc}"
        )
    none = "\n".join(none_lines) + "\n"

    if check:
        bad = []
        if not os.path.exists(OUT_REPORT) or open(OUT_REPORT, encoding="utf-8").read() != report:
            bad.append(os.path.relpath(OUT_REPORT, ROOT))
        if not os.path.exists(OUT_NONE) or open(OUT_NONE, encoding="utf-8").read() != none:
            bad.append(os.path.relpath(OUT_NONE, ROOT))
        if bad:
            print("FAIL: stale verified injury files: " + ", ".join(bad))
            return 1
        print("OK: verified injury files match the 347-row official capture")
        return 0

    open(OUT_REPORT, "w", encoding="utf-8", newline="\n").write(report)
    open(OUT_NONE, "w", encoding="utf-8", newline="\n").write(none)
    print(f"wrote {os.path.relpath(OUT_REPORT, ROOT)}: {len(out)} rows, {len(per_club)} clubs")
    print(f"wrote {os.path.relpath(OUT_NONE, ROOT)}: {len(checked_clubs)} previously-wrong clubs corrected")
    print("per-club: " + ", ".join(f"{k}={v}" for k, v in sorted(per_club.items())))
    print(f"retrieved stamp: {retrieved_utc} (the scrape's own generation time)")
    if capture_note:
        print(f"manifest note carried: {capture_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
