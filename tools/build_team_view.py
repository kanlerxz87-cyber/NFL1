#!/usr/bin/env python3
"""build_team_view.py — per-team injury view and a two-read delta, 13 Nov vs 15 Nov (P5, session 55dc53f4-nfl1).

Inputs (all in the repository):
  data/capture/nflcom_injuries_reg10_2026-11-15_rows.tsv  15 Nov full read of the nfl.com Week 10 injury page
  data/capture/manifest.json                              source URL and pinned counts for that read
  data/official/2026-11-13/injury_report_counts_2026-11-13.py  13 Nov per-club COUNT audit (not a transcript)
  data/official/2026-11-13/injury_designations_2026-11-13.tsv  13 Nov: 9 player designations

Outputs:
  data/shadow/team_view.json     per club, from the 15 Nov read only: listed players, game-status and
                                 practice-status counts; every player row carries its source URL.
                                 'starters_out' and 'replacements' are left blank with a flag: no
                                 official starter or depth-chart source exists for them.
  data/shadow/whats_changed.json the DELTA only (differences), never the levels:
                                 club row-count differences where both reads are complete, practice-status
                                 differences, and the 9 designation comparisons. Clubs where the 13 Nov read
                                 is partial are not compared and are listed as such.

Not claimed: a player-level delta. The 13 Nov read has no full transcript, only counts and 9 designations.

    python3 tools/build_team_view.py
"""
from __future__ import annotations

import collections
import csv
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP_ROWS = os.path.join(ROOT, "data/capture/nflcom_injuries_reg10_2026-11-15_rows.tsv")
MANIFEST = os.path.join(ROOT, "data/capture/manifest.json")
COUNTS_13 = os.path.join(ROOT, "data/official/2026-11-13/injury_report_counts_2026-11-13.py")
DESIG_13 = os.path.join(ROOT, "data/official/2026-11-13/injury_designations_2026-11-13.tsv")
OUT_VIEW = os.path.join(ROOT, "data/shadow/team_view.json")
OUT_DELTA = os.path.join(ROOT, "data/shadow/whats_changed.json")

SRC_15 = "https://www.nfl.com/injuries/league/2026/reg10"
SRC_13 = "https://www.nfl.com/injuries/"
DNP, LIM, FULL = "Did Not Participate In Practice", "Limited Participation in Practice", "Full Participation in Practice"
# The 13 Nov count audit uses LA for the Rams; the 15 Nov capture uses LAR (nfl.com page code). Mapped, and listed.
CODE_13_TO_15 = {"LA": "LAR"}
FLAG_STARTERS = "blank: no official starter or depth-chart source (nfl.com has no depth-chart page; 404 checked in data/official/2026-11-13/sources.json, S-NFL404)"
FLAG_REPL = "blank: no official replacement source; not inferred"


def load_counts_13() -> list[tuple]:
    spec = importlib.util.spec_from_file_location("counts13", COUNTS_13)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CLUBS


def main() -> int:
    m = json.load(open(MANIFEST, encoding="utf-8"))
    cap = list(csv.DictReader(open(CAP_ROWS, newline="", encoding="utf-8"), delimiter="\t"))
    by_club: dict[str, list[dict]] = collections.defaultdict(list)
    for r in cap:
        by_club[r["team"]].append(r)

    # ---- team view (15 Nov level, per club) ----
    clubs = []
    for club in sorted(by_club):
        rows = by_club[club]
        gs = collections.Counter((r["game_status"] or "(none)") for r in rows)
        ps = collections.Counter(r["practice_status"] for r in rows)
        clubs.append({
            "club": club,
            "source_url": SRC_15,
            "listed_players": len(rows),
            "game_status_counts": {k: gs.get(k, 0) for k in ("Out", "Doubtful", "Questionable", "(none)")},
            "practice_status_counts": {"Did Not Participate In Practice": ps.get(DNP, 0),
                                       "Limited Participation in Practice": ps.get(LIM, 0),
                                       "Full Participation in Practice": ps.get(FULL, 0)},
            "starters_out": None,
            "starters_out_flag": FLAG_STARTERS,
            "replacements": None,
            "replacements_flag": FLAG_REPL,
            "players": [{"player": r["player"], "position": r["position"], "injury": r["injury"],
                         "practice_status": r["practice_status"], "game_status": r["game_status"],
                         "source_url": SRC_15} for r in rows],
        })
    view = {
        "what": "Per-team injury view from the 15 Nov full read of the official nfl.com Week 10 injury page. Level, not delta.",
        "read": {"source_url": SRC_15, "captured": m["captured"], "rows": m["counts"]["rows"],
                 "clubs": m["counts"]["clubs"], "manifest_rows_tsv_sha256": m["rows_tsv_sha256"]},
        "not_in_this_view": "starters_out and replacements: no official source in the repository; left blank, not inferred.",
        "club_code_note": "The page uses LAR (Rams) and AZ (Cardinals). Flag CAP-05 on the AZ/ARI code conflict.",
        "clubs": clubs,
    }

    # ---- delta: 13 Nov vs 15 Nov (differences only) ----
    counts13 = load_counts_13()
    rows_15 = {c: len(by_club.get(c, [])) for c in by_club}
    gs_dnp_15 = {c: sum(1 for r in by_club.get(c, []) if r["practice_status"] == DNP) for c in by_club}
    gs_lim_15 = {c: sum(1 for r in by_club.get(c, []) if r["practice_status"] == LIM) for c in by_club}
    gs_full_15 = {c: sum(1 for r in by_club.get(c, []) if r["practice_status"] == FULL) for c in by_club}
    per_club = []
    not_comparable = []
    conflicts = []
    for (club13, n13, dnp13, lim13, full13, _gd, status13, note13) in counts13:
        club = CODE_13_TO_15.get(club13, club13)
        if status13 != "complete":
            not_comparable.append({"club": club, "reason": f"13 Nov read is {status13}: {note13}"})
            continue
        if n13 == 0 and club in by_club and rows_15.get(club, 0) > 0:
            conflicts.append({"club": club, "conflict": "13 Nov read: 'No Injuries Reported' (0 rows); 15 Nov read lists "
                              f"{rows_15[club]} rows. Either the report changed between the reads or one read is wrong. "
                              "Not resolved from the record.",
                              "sources": [SRC_13, SRC_15]})
        entry = {"club": club, "sources": [SRC_13, SRC_15],
                 "rows_difference": rows_15.get(club, 0) - n13,
                 "did_not_participate_difference": gs_dnp_15.get(club, 0) - dnp13,
                 "limited_difference": gs_lim_15.get(club, 0) - lim13,
                 "full_difference": gs_full_15.get(club, 0) - full13}
        per_club.append(entry)
    desig = []
    cap_idx = {(r["team"], r["player"]): r for r in cap}
    with open(DESIG_13, encoding="utf-8") as fh:
        for d in csv.DictReader(fh, delimiter="\t"):
            club = CODE_13_TO_15.get(d["club"], d["club"])
            c = cap_idx.get((club, d["player"]))
            if c is None:
                desig.append({"club": club, "player": d["player"], "result": "not on the 15 Nov read", "sources": [SRC_13, SRC_15]})
                continue
            diffs = {}
            for k13, k15 in (("injury", "injury"), ("practice_status", "practice_status"), ("game_status", "game_status")):
                a, b = d[k13].strip(), c[k15].strip()
                if a != b:
                    diffs[k13] = {"13_nov": a, "15_nov": b}
            desig.append({"club": club, "player": d["player"],
                          "result": "changed" if diffs else "unchanged",
                          "differences": diffs, "sources": [SRC_13, SRC_15]})
    conflict_clubs = {c["club"] for c in conflicts}
    for e in per_club:
        if e["club"] in conflict_clubs:
            e["conflict_flag"] = "13 Nov 'No Injuries Reported' vs 15 Nov listed rows; see conflicts_unresolved"
    changed_desig = [x for x in desig if x.get("result") == "changed"]
    delta = {
        "what": "Differences between the 13 Nov and 15 Nov official nfl.com reads. Differences only; the levels are in team_view.json.",
        "reads": {"13_nov": {"source_url": SRC_13, "retrieved": "2026-11-13T12:20Z", "type": "per-club row counts (26 complete clubs) and 9 designations"},
                  "15_nov": {"source_url": SRC_15, "captured": m["captured"], "type": "full transcript, 347 rows"}},
        "not_claimed": "A player-by-player delta. The 13 Nov read has no full transcript; only the 9 designations above can be compared player by player. Players listed on 15 Nov but not on 13 Nov cannot be told apart from players the 13 Nov read did not record.",
        "club_code_map": {"LA (13 Nov)": "LAR (15 Nov)"},
        "per_club_differences": per_club,
        "clubs_not_comparable": not_comparable,
        "conflicts_unresolved": conflicts,
        "designations": {"compared": len(desig), "changed": len(changed_desig), "rows": desig},
    }

    os.makedirs(os.path.dirname(OUT_VIEW), exist_ok=True)
    with open(OUT_VIEW, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(view, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    with open(OUT_DELTA, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(delta, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    changed_rows = sum(1 for e in per_club if e["rows_difference"] != 0)
    print(f"team_view: {len(clubs)} clubs, {sum(len(c['players']) for c in clubs)} player rows, every row source-linked")
    print(f"delta: {len(per_club)} clubs compared, {changed_rows} with a row-count difference; "
          f"{len(not_comparable)} not comparable; {len(conflicts)} unresolved conflict(s); "
          f"designations {len(changed_desig)}/{len(desig)} changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
