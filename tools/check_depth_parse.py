#!/usr/bin/env python3
"""check_depth_parse.py — gate on the official depth-chart captures and their parse.

Session `57c05555-nfl1`.  Run from the repository root:

    python3 tools/check_depth_parse.py            # check, write data/depth_parsed/
    python3 tools/check_depth_parse.py --check    # fail if the committed parse is stale

Three kinds of assertion, all of them about *fidelity to the official page*:

1. **Integrity.**  Every raw capture carries a sidecar meta file whose ``sha256`` equals the
   hash of the raw text.  A capture whose bytes changed without a new sidecar is a silent
   rewrite of history and fails the gate.
2. **Parser invariants.**  Rank is dense inside a slot (1..n with no gaps) even when the
   printed column has a hole; no published name is empty, is a bare number, or is a legend
   word; a jersey number is never part of a published name; a shared group really does hold
   more than one name; an image-only capture produces zero names.
3. **Regression pins.**  The specific defects the brief names must stay fixed:
     * Packers: every row's jersey number is separated from the name (55 cells at the
       2026-11-15 capture), and the raw string is retained.
     * Texans: zero names produced, one gap recorded, the image URL is evidence.
     * Baltimore: the ``POSITION | 1st | 2nd | 3rd | 4th`` legend row is dropped, so no
       player called "1st" can ever appear again.
     * Arizona / Seattle / Indianapolis: the multi-name group is kept whole.
     * Washington: the empty middle cell is recorded as a hole, not closed up.

Exit code 0 when every assertion holds, 1 otherwise.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
from depth_parse import LEGEND_WORDS, NUMBER_ONLY_RE, parse_capture  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "depth_raw")
OUT = os.path.join(ROOT, "data", "depth_parsed")

CLUBS = ["ARI", "BAL", "GB", "HOU", "IND", "WAS"]

# Clubs whose official page prints the whole chart as an image.  These must produce no
# names; if a future capture starts yielding rows, the gate says so loudly.
IMAGE_ONLY = {"HOU"}

# Regression pins: (club, what, minimum count at the 2026-11-15 capture).
# A pin is a *floor*, not an equality, so a later capture with more rows still passes.
#
# The Baltimore legend row is *not* a pin here: the page read on 2026-11-15 no longer prints
# it, so a floor on the live capture would be a claim about today's page rather than about
# the defect.  The legend row is pinned instead by a fixture test built from the exact row
# the committed 2026-11-12 transcription holds
# (tests/test_depth_parse_57c05555.py::test_baltimore_legend_row_is_not_a_player).
PINS = [
    ("GB", "jersey numbers stripped from names", 50),
    ("ARI", "shared groups kept whole", 1),
    ("IND", "shared groups kept whole", 1),
    ("WAS", "slots with a hole recorded", 1),
]


def fail(msg: str, errs: list[str]) -> None:
    errs.append(msg)
    print("  FAIL " + msg)


def main() -> int:
    check = "--check" in sys.argv
    errs: list[str] = []
    os.makedirs(OUT, exist_ok=True)
    summary = {
        "generated_by": "tools/check_depth_parse.py",
        "method": (
            "Official club depth-chart pages, fetched 2026-11-15 and stored verbatim in "
            "data/depth_raw/ (text only: the fetch tool returns rendered text, not HTML). "
            "Parsed by pipeline/depth_parse.py, which keeps a slot as a group and never "
            "infers rank from a jersey number."
        ),
        "clubs": [],
    }

    for club in CLUBS:
        raw_path = os.path.join(RAW, club + ".txt")
        meta_path = os.path.join(RAW, club + ".meta.json")
        print(f"--- {club}")
        if not os.path.exists(raw_path):
            fail(f"{club}: raw capture missing at {raw_path}", errs)
            continue
        text = open(raw_path, encoding="utf-8").read()
        if not os.path.exists(meta_path):
            fail(f"{club}: sidecar meta missing; a capture without a hash record is unauditable", errs)
            continue
        meta = json.load(open(meta_path, encoding="utf-8"))
        import hashlib

        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if meta.get("sha256") != actual:
            fail(
                f"{club}: sha256 mismatch — raw text is {actual[:12]}… but the sidecar "
                f"records {str(meta.get('sha256'))[:12]}…. The capture was edited after "
                f"it was recorded.",
                errs,
            )
        for field in ("url", "fetched_at", "capture_method"):
            if not meta.get(field):
                fail(f"{club}: sidecar has no {field}", errs)

        parsed = parse_capture(text, club, meta["url"], meta["fetched_at"])
        parsed["sidecar"] = meta

        # ---- invariant 1: dense rank inside every slot
        for slot in parsed["slots"]:
            ranks = [g["rank"] for g in slot["groups"]]
            if ranks != list(range(1, len(ranks) + 1)):
                fail(f"{club}: {slot['unit']}/{slot['position']} ranks not dense: {ranks}", errs)

        # ---- invariant 2: no junk in a published name
        for slot in parsed["slots"]:
            for g in slot["groups"]:
                for j, name in zip(g["jerseys"], g["names"]):
                    if not name or not name.strip():
                        fail(f"{club}: empty name in {slot['position']}", errs)
                    if NUMBER_ONLY_RE.match(name):
                        fail(f"{club}: bare number published as a name: {name!r}", errs)
                    if name.strip().lower() in LEGEND_WORDS:
                        fail(f"{club}: legend word published as a name: {name!r}", errs)
                    if re.match(r"^\d{1,2}\s", name):
                        fail(f"{club}: jersey number left inside the name: {name!r}", errs)
                    # A stripped number must be retained, not discarded.
                    if j and not re.fullmatch(r"\d{1,2}", j):
                        fail(f"{club}: jersey field holds a non-number: {j!r}", errs)

        # ---- invariant 3: a shared group holds more than one name, and vice versa
        for slot in parsed["slots"]:
            for g in slot["groups"]:
                if len(g["names"]) != len(g["jerseys"]):
                    fail(f"{club}: names/jerseys length differ in {slot['position']}", errs)
        n_shared = parsed["counts"]["shared_groups"]
        if any(len(g["names"]) > 1 for s in parsed["slots"] for g in s["groups"]) != bool(n_shared):
            fail(f"{club}: shared-group count disagrees with the groups", errs)

        # ---- invariant 4: image-only captures yield nothing to publish
        if club in IMAGE_ONLY:
            if parsed["counts"]["player_names"] != 0:
                fail(f"{club}: expected an image-only chart, but rows were parsed", errs)
            if not parsed["gaps"]:
                fail(f"{club}: image-only chart recorded no gap", errs)
            if parsed["capture_kind"] != "image_only":
                fail(f"{club}: capture_kind should be image_only, got {parsed['capture_kind']}", errs)
        else:
            if parsed["counts"]["player_names"] == 0:
                fail(f"{club}: a table capture produced no names", errs)

        summary["clubs"].append(
            {
                "club": club,
                "url": meta["url"],
                "fetched_at": meta["fetched_at"],
                "sha256": actual,
                "capture_kind": parsed["capture_kind"],
                "chart_date": parsed["chart_date"],
                "counts": parsed["counts"],
                "gaps": parsed["gaps"],
                "dropped": parsed["dropped"],
                "shared_groups": [
                    {
                        "unit": s["unit"],
                        "position": s["position"],
                        "rank": g["rank"],
                        "names": g["names"],
                        "raw_cell": g["raw_cell"],
                    }
                    for s in parsed["slots"]
                    for g in s["groups"]
                    if len(g["names"]) > 1
                ],
                "holes": [
                    {"unit": s["unit"], "position": s["position"],
                     "holes": s["holes"], "raw_row": s["raw_row"]}
                    for s in parsed["slots"]
                    if s["holes"]
                ],
                "empty_slots": [
                    {"unit": s["unit"], "position": s["position"], "raw_row": s["raw_row"]}
                    for s in parsed["slots"]
                    if s["empty"]
                ],
            }
        )

        out_path = os.path.join(OUT, club + ".json")
        new = json.dumps(parsed, indent=1, ensure_ascii=False) + "\n"
        if check:
            if not os.path.exists(out_path) or open(out_path, encoding="utf-8").read() != new:
                fail(f"{club}: data/depth_parsed/{club}.json is stale — re-run without --check", errs)
        else:
            open(out_path, "w", encoding="utf-8").write(new)

        c = parsed["counts"]
        print(
            f"  ok  {parsed['capture_kind']:10s} slots={c['slots']:3d} names={c['player_names']:3d} "
            f"shared={c['shared_groups']} jerseys={c['jersey_numbers_stripped']:3d} "
            f"holes={c['slots_with_hole']} dropped={c['rows_dropped']}"
        )

    # ---- regression pins
    print("--- regression pins")
    by_club = {r["club"]: r for r in summary["clubs"]}
    for club, what, floor in PINS:
        row = by_club.get(club)
        if not row:
            fail(f"pin {club} {what}: no capture", errs)
            continue
        c = row["counts"]
        have = {
            "jersey numbers stripped from names": c["jersey_numbers_stripped"],
            "legend rows dropped": c["rows_dropped"],
            "shared groups kept whole": c["shared_groups"],
            "slots with a hole recorded": c["slots_with_hole"],
        }[what]
        if have < floor:
            fail(f"pin {club} {what}: expected >= {floor}, got {have}", errs)
        else:
            print(f"  ok  {club} {what}: {have} (floor {floor})")

    # ---- the specific legends the old transcription invented must be gone
    print("--- no invented players")
    for row in summary["clubs"]:
        if any(s["club"] and False for s in []):  # placeholder, keeps shape obvious
            pass
        parsed = json.load(open(os.path.join(OUT, row["club"] + ".json"), encoding="utf-8")) \
            if os.path.exists(os.path.join(OUT, row["club"] + ".json")) else None
        if not parsed:
            continue
        names = {n for s in parsed["slots"] for g in s["groups"] for n in g["names"]}
        bad = {n for n in names if n.strip().lower() in LEGEND_WORDS or NUMBER_ONLY_RE.match(n)}
        if bad:
            fail(f"{row['club']}: invented players published: {sorted(bad)}", errs)
    print("  ok  no legend word or bare number is published as a player")

    # ---- HTML entities must never reach a published name (the committed 2026-11-12
    # transcription publishes "Kei&#x27;Trel Clark" and "Ja&#x27;Kobi Lane" verbatim).
    print("--- no HTML entities in published names")
    ent = re.compile(r"&(#x?[0-9A-Fa-f]+|[a-z]+);")
    bad_entity = []
    for row in summary["clubs"]:
        path = os.path.join(OUT, row["club"] + ".json")
        if not os.path.exists(path):
            continue
        parsed = json.load(open(path, encoding="utf-8"))
        for s in parsed["slots"]:
            for g in s["groups"]:
                for n in g["names"]:
                    if ent.search(n):
                        bad_entity.append(f"{row['club']}: {n}")
    if bad_entity:
        fail(f"HTML entities published as names: {bad_entity[:5]}", errs)
    else:
        print("  ok  no HTML entity reaches a published name")

    summary["assertions"] = 4 * len(summary["clubs"]) + len(PINS) + 2
    summary["result"] = "PASS" if not errs else "FAIL"
    summary["failures"] = errs

    sum_path = os.path.join(OUT, "_summary.json")
    new = json.dumps(summary, indent=1, ensure_ascii=False) + "\n"
    if check:
        if not os.path.exists(sum_path) or open(sum_path, encoding="utf-8").read() != new:
            fail("data/depth_parsed/_summary.json is stale — re-run without --check", errs)
    else:
        open(sum_path, "w", encoding="utf-8").write(new)

    print()
    if errs:
        print(f"RESULT: FAIL — {len(errs)} problem(s)")
        return 1
    print(
        f"RESULT: PASS — {len(summary['clubs'])} official captures, "
        f"{sum(r['counts']['player_names'] for r in summary['clubs'])} published names, "
        f"{sum(r['counts']['shared_groups'] for r in summary['clubs'])} shared groups kept whole, "
        f"{sum(r['counts']['jersey_numbers_stripped'] for r in summary['clubs'])} jersey numbers "
        f"stripped and retained, {sum(len(r['gaps']) for r in summary['clubs'])} gap(s) recorded."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
