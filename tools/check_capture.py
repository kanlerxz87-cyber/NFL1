#!/usr/bin/env python3
"""check_capture.py: validate the official nfl.com injury-report capture and compare it with
the other copies in this repository.

Session 543676f8-nfl1 (task X1). Run from the repository root:

    python3 tools/check_capture.py

What it does
------------
1. Structural gate (exit 1 on any failure):
   * the row and game files parse with the expected header;
   * every row names a game, a club listed in that game, a player, a position;
   * game_status is one of the official designations (Out, Doubtful, Questionable) or blank;
   * practice_status is one of the three official phrases;
   * no player appears twice for one club;
   * per-club row counts, the row total, the game count and the club count equal the manifest;
   * the SHA-256 of both TSV files equals the value recorded in the manifest.
2. Comparison (never fails the build; every difference becomes a published flag):
   * against the automated scrape in data/model/official_injuries.json;
   * against the hand copy in data/verified/injury_report_2026_week10.tsv and the
     no-injury list in data/verified/no_injuries_week10.csv.
   The result is written to data/capture/comparison.json for the capture page.

Nothing here infers a value. A player missing from one copy is reported as missing from that
copy; the capture itself is never edited to agree with another source.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAP = os.path.join(ROOT, "data", "capture")
ROWS = os.path.join(CAP, "nflcom_injuries_reg10_2026-11-15_rows.tsv")
GAMES = os.path.join(CAP, "nflcom_injuries_reg10_2026-11-15_games.tsv")
MANIFEST = os.path.join(CAP, "manifest.json")
COMPARISON = os.path.join(CAP, "comparison.json")
SCRAPE = os.path.join(ROOT, "data", "model", "official_injuries.json")
VERIFIED = os.path.join(ROOT, "data", "verified", "injury_report_2026_week10.tsv")
VERIFIED_NONE = os.path.join(ROOT, "data", "verified", "no_injuries_week10.csv")

GAME_STATUS = {"", "Out", "Doubtful", "Questionable"}
PRACTICE_STATUS = {
    "Full Participation in Practice",
    "Limited Participation in Practice",
    "Did Not Participate In Practice",
}
# Club codes: the capture uses the codes printed on nfl.com (AZ, LAR). The other copies use
# their own codes; this table maps capture code -> code in that copy. Both sides are recorded
# as published, and the mismatch is itself a flag.
SCRAPE_CODE = {"AZ": "ARI", "LAR": "LA"}
VERIFIED_CODE = {"LAR": "LA"}

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  [FAIL] {msg}")


def ok(msg: str) -> None:
    print(f"  [PASS] {msg}")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def read_tsv(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def main() -> int:
    print("check_capture: nfl.com Week 10 injury report capture (session 543676f8-nfl1)")
    with open(MANIFEST, encoding="utf-8") as fh:
        man = json.load(fh)
    rows = read_tsv(ROWS)
    games = read_tsv(GAMES)

    # ---- 1. structure -------------------------------------------------------------------
    print("\n1. Structure")
    with open(ROWS, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
    if header == ["game_id", "team", "player", "position", "injury", "practice_status", "game_status"]:
        ok("row file header matches the schema")
    else:
        fail(f"row file header is {header}")
    with open(GAMES, encoding="utf-8") as fh:
        ghead = fh.readline().rstrip("\n").split("\t")
    if ghead == ["game_id", "listed_clubs", "day_and_kickoff_as_printed", "networks_as_printed"]:
        ok("game file header matches the schema")
    else:
        fail(f"game file header is {ghead}")

    game_clubs = {g["game_id"]: g["listed_clubs"].split() for g in games}
    if len(games) == man["counts"]["games"]:
        ok(f"{len(games)} games, as the manifest states")
    else:
        fail(f"{len(games)} games, manifest says {man['counts']['games']}")
    slots = [c for clubs in game_clubs.values() for c in clubs]
    if len(slots) == len(set(slots)) == man["counts"]["clubs"]:
        ok(f"{len(set(slots))} clubs, each in exactly one game")
    else:
        fail("clubs are not each in exactly one game")

    bad_game = [r for r in rows if r["team"] not in game_clubs.get(r["game_id"], [])]
    if bad_game:
        fail(f"{len(bad_game)} rows name a club that is not listed in their game")
    else:
        ok("every row's club is listed in its game")
    for r in rows:
        if not r["player"].strip() or not r["position"].strip():
            fail(f"row with blank player or position: {r}")
            break
    else:
        ok("no row has a blank player or position")
    bad_gs = sorted({r["game_status"] for r in rows} - GAME_STATUS)
    bad_ps = sorted({r["practice_status"] for r in rows} - PRACTICE_STATUS)
    (fail(f"unknown game_status values {bad_gs}") if bad_gs else ok("game_status values are official"))
    (fail(f"unknown practice_status values {bad_ps}") if bad_ps else ok("practice_status values are official"))

    seen = Counter((r["team"], norm_name(r["player"])) for r in rows)
    dups = [k for k, v in seen.items() if v > 1]
    (fail(f"duplicate player rows {dups}") if dups else ok("no player listed twice for one club"))

    if len(rows) == man["counts"]["rows"]:
        ok(f"{len(rows)} rows, as the manifest states")
    else:
        fail(f"{len(rows)} rows, manifest says {man['counts']['rows']}")
    per_club = Counter(r["team"] for r in rows)
    expected = man["rows_per_club"]
    mismatch = {c: (per_club.get(c, 0), n) for c, n in expected.items() if per_club.get(c, 0) != n}
    extra = sorted(set(per_club) - set(expected))
    if not mismatch and not extra:
        ok("per-club row counts equal the manifest for all 28 clubs")
    else:
        fail(f"per-club count differences {mismatch} extra {extra}")

    for path, key in ((ROWS, "rows_tsv_sha256"), (GAMES, "games_tsv_sha256")):
        digest = sha256(path)
        if digest == man[key]:
            ok(f"{os.path.basename(path)} sha256 equals the manifest")
        else:
            fail(f"{os.path.basename(path)} sha256 {digest} != manifest {man[key]}")

    # ---- 2. comparison --------------------------------------------------------------------
    print("\n2. Comparison with the other copies in this repository (flags, never failures)")
    flags: list[dict] = []
    cap_by_club: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        cap_by_club[r["team"]].append(r)

    # 2a. automated scrape
    with open(SCRAPE, encoding="utf-8") as fh:
        scrape = json.load(fh)
    srows = scrape["rows"]
    s_by_club: dict[str, list[dict]] = defaultdict(list)
    for r in srows:
        s_by_club[r["team"]].append(r)
    scrape_missing, scrape_extra, scrape_status_diff = [], [], []
    for club, lst in cap_by_club.items():
        sc = SCRAPE_CODE.get(club, club)
        s_names = {norm_name(x["player"]): x for x in s_by_club.get(sc, [])}
        for r in lst:
            key = norm_name(r["player"])
            if key not in s_names:
                scrape_missing.append({"club": club, "player": r["player"], "position": r["position"],
                                       "injury": r["injury"], "game_status": r["game_status"]})
            else:
                s = s_names[key]
                cg = r["game_status"] or ""
                sg = s.get("game") or ""
                if cg != sg:
                    scrape_status_diff.append({"club": club, "player": r["player"],
                                               "capture": cg, "scrape": sg})
        cap_names = {norm_name(r["player"]) for r in lst}
        for key, s in s_names.items():
            if key not in cap_names:
                scrape_extra.append({"club": sc, "player": s["player"]})
    scrape_counts = {c: len(v) for c, v in s_by_club.items()}
    club_rows = []
    for club in sorted(expected):
        sc = SCRAPE_CODE.get(club, club)
        club_rows.append({"club": club, "capture": per_club[club], "scrape": scrape_counts.get(sc)})
    print(f"  scrape ({scrape['generated_at']}): {len(srows)} rows, {len(s_by_club)} clubs")
    cause = ("The scrape and this capture are different days (scrape 2026-11-14 17:02 UTC; capture 2026-11-15). "
             "The differences cluster on the Monday LAC-BAL game and the Ravens rows, which fits a page "
             "update between the two captures, but the saved data cannot prove it: the scrape kept only a hash "
             "of the page, not the page itself, so it cannot be re-parsed. The scrape raised no error.")
    if scrape_missing:
        print(f"  flag: scrape lacks {len(scrape_missing)} row(s) that the capture has: "
              + ", ".join(f"{m['club']} {m['player']}" for m in scrape_missing))
        flags.append({
            "id": "CAP-01", "area": "automated injury scrape",
            "issue": (f"The scrape has {len(srows)} rows; the capture of the same official page has {len(rows)}. "
                      "Rows in the capture and absent from the scrape: "
                      + "; ".join(f"{m['club']} {m['player']} ({m['position']}, game status "
                                  f"'{m['game_status'] or 'blank'}')" for m in scrape_missing)
                      + ". " + cause),
            "state": "open",
            "source": "https://www.nfl.com/injuries/league/2026/reg10",
            "what_settles_it": "Store the raw page with each scheduled capture (sha256 + fetch time) so the two "
                               "versions can be compared row by row, then pin per-club row counts in the scraper.",
        })
    if scrape_status_diff:
        flags.append({"id": "CAP-02", "area": "automated injury scrape",
                      "issue": (f"Game designation differs for {len(scrape_status_diff)} players between the scrape "
                                "and the capture: " + "; ".join(
                                    f"{d['club']} {d['player']} (capture '{d['capture'] or 'blank'}', "
                                    f"scrape '{d['scrape'] or 'blank'}')" for d in scrape_status_diff)
                                + ". " + cause),
                      "state": "open", "source": "https://www.nfl.com/injuries/league/2026/reg10",
                      "what_settles_it": "Re-capture on a schedule with raw storage; the official page is the arbiter."})
    if scrape_extra:
        flags.append({"id": "CAP-03", "area": "automated injury scrape",
                      "issue": "Scrape has rows the capture does not: "
                               + "; ".join(f"{d['club']} {d['player']}" for d in scrape_extra),
                      "state": "open", "source": "https://www.nfl.com/injuries/league/2026/reg10",
                      "what_settles_it": "Re-capture the official page."})

    # 2b. hand copy (stale)
    vrows = read_tsv(VERIFIED)
    v_by_club: dict[str, list[dict]] = defaultdict(list)
    for r in vrows:
        v_by_club[r["team_abbr"]].append(r)
    with open(VERIFIED_NONE, encoding="utf-8") as fh:
        none_rows = list(csv.DictReader(fh))
    none_clubs = sorted({r["team_abbr"] for r in none_rows})
    v_clubs_all = set(v_by_club) | set(none_clubs)
    cap_clubs = set(per_club)
    v_row_total = len(vrows)
    cap_names_all = {(VERIFIED_CODE.get(r["team"], r["team"]), norm_name(r["player"])) for r in rows}
    v_extra = [(r["team_abbr"], r["player"]) for r in vrows
               if (r["team_abbr"], norm_name(r["player"])) not in cap_names_all]
    print(f"  hand copy (data/verified): {v_row_total} rows, {len(v_by_club)} clubs with rows, "
          f"{len(none_clubs)} listed as 'No Injuries Reported'")
    # Players present in the capture but missing from the hand copy
    v_missing = []
    for club, lst in cap_by_club.items():
        vc = VERIFIED_CODE.get(club, club)
        names = {norm_name(x["player"]) for x in v_by_club.get(vc, [])}
        for r in lst:
            if norm_name(r["player"]) not in names:
                v_missing.append((club, r["player"]))
    v_none_conflict = [c for c in none_clubs if VERIFIED_CODE.get(c, c) in cap_clubs or c in cap_clubs]
    lions = []
    for r in vrows:
        if r["team_abbr"] == "DET" and r["player"] in ("Kerby Joseph", "Cade Mays", "D.J. Reed"):
            cap = next(x for x in rows if x["team"] == "DET" and x["player"] == r["player"])
            lions.append({"player": r["player"], "hand_copy_game_status": r["game_status"] or "blank",
                          "capture_game_status": cap["game_status"] or "blank"})
    club_rows_v = []
    for club in sorted(expected):
        vc = VERIFIED_CODE.get(club, club)
        club_rows_v.append({"club": club, "capture": per_club[club],
                            "hand_copy": len(v_by_club.get(vc, [])) if vc in v_by_club else
                            ("No Injuries Reported" if vc in none_clubs else "absent")})
    if v_missing or v_none_conflict:
        flags.append({
            "id": "CAP-03", "area": "hand-copied injury table (data/verified)",
            "issue": (f"The hand copy holds {v_row_total} rows against {len(rows)} on the official page "
                      f"captured 2026-11-15. {len(v_extra)} of its rows are not on the capture; {len(v_missing)} "
                      f"rows of the capture are not in the hand copy, "
                      f"and lists as 'No Injuries Reported' the clubs "
                      + ", ".join(v_none_conflict) + ", which the official page lists with rows. "
                      "Its retrieval stamp is 2026-11-12T05:30Z, so it predates the Sunday games."),
            "state": "open", "source": "https://www.nfl.com/injuries/league/2026/reg10",
            "what_settles_it": "Superseded by data/capture/. Leave the old file in place, labelled, until a "
                               "reviewer confirms the replacement."})
    if lions:
        flags.append({"id": "CAP-04", "area": "hand-copied injury table (data/verified)",
                      "issue": "Blank game-status cells in the hand copy for: "
                               + "; ".join(f"{x['player']} (hand copy '{x['hand_copy_game_status']}', "
                                           f"official '{x['capture_game_status']}')" for x in lions),
                      "state": "open", "source": "https://www.nfl.com/injuries/league/2026/reg10",
                      "what_settles_it": "The official page lists each as Out; the capture carries that value."})
    club_code_flag = sorted(set(SCRAPE_CODE) | set(VERIFIED_CODE))
    flags.append({"id": "CAP-05", "area": "club codes",
                  "issue": ("The official page prints Arizona as AZ and the Rams as LAR; the automated scrape "
                            "uses ARI and LA and the hand copy uses AZ and LA. The capture keeps the printed "
                            "codes and maps them in tools/check_capture.py."),
                  "state": "open", "source": "https://www.nfl.com/injuries/league/2026/reg10",
                  "what_settles_it": "One club-code table shared by every generator."})
    flags.append({"id": "CAP-06", "area": "capture method",
                  "issue": ("The capture is the text the fetch tool returned for the official page (8 chunks), "
                            "transcribed row by row. No raw HTML was retained, so the hash in the manifest covers "
                            "the transcription, not the page bytes. The time of capture was not logged; only the "
                            "date (2026-11-15) is recorded."),
                  "state": "open", "source": "https://www.nfl.com/injuries/league/2026/reg10",
                  "what_settles_it": "Scheduled capture in GitHub Actions that stores the raw page and its sha256 "
                                     "(pipeline/scrape_injuries.py already runs there)."})

    comparison = {
        "generated_by": "tools/check_capture.py",
        "capture": {"source": man["source_url"], "captured": man["captured"], "rows": len(rows),
                    "clubs": len(per_club), "games": len(games)},
        "scrape": {"generated_at": scrape["generated_at"], "html_sha256": scrape.get("html_sha256"),
                   "rows": len(srows), "clubs": len(s_by_club), "status": scrape.get("status")},
        "hand_copy": {"path": "data/verified/injury_report_2026_week10.tsv", "rows": v_row_total,
                      "rows_not_on_capture": [{"club": c, "player": p} for c, p in v_extra],
                      "clubs_with_rows": len(v_by_club), "no_injury_clubs": none_clubs},
        "club_counts_vs_scrape": club_rows,
        "club_counts_vs_hand_copy": club_rows_v,
        "scrape_missing_from_scrape": scrape_missing,
        "scrape_status_differences": scrape_status_diff,
        "hand_copy_missing_players": [{"club": c, "player": p} for c, p in v_missing],
        "hand_copy_lions_designations": lions,
        "flags": flags,
    }
    with open(COMPARISON, "w", encoding="utf-8") as fh:
        json.dump(comparison, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"  wrote {os.path.relpath(COMPARISON, ROOT)} with {len(flags)} flags")
    for f in flags:
        print(f"  flag {f['id']}: {f['issue'][:150]}...")

    print()
    if failures:
        print(f"RESULT: FAIL — {len(failures)} structural failure(s)")
        return 1
    print("RESULT: PASS — capture structure valid; comparison written; differences are flags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
