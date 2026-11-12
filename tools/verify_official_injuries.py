#!/usr/bin/env python3
"""Compare the scraped nfl.com injury JSON with the hand transcription of the official page.

Inputs
  data/dashboard/official_injuries_2026_w10.psv   transcription of https://www.nfl.com/injuries/ (read 2026-11-12)
  data/model/official_injuries.json                scrape committed by the pipeline

Output
  data/dashboard/injury_verification.json          row-level result (matched / missing / extra / field diffs)

Nothing is inferred: a scraped row is 'matched' only when team, player, position, injury,
practice status and game status are identical to the transcription.
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PSV = os.path.join(ROOT, "data/dashboard/official_injuries_2026_w10.psv")
SCRAPE = os.path.join(ROOT, "data/model/official_injuries.json")
OUT = os.path.join(ROOT, "data/dashboard/injury_verification.json")

PRACTICE = {
    "FULL": "Full Participation in Practice",
    "LIM": "Limited Participation in Practice",
    "DNP": "Did Not Participate In Practice",
}
# nfl.com club codes are AZ and LAR; the pipeline uses ARI and LA.
CODE_MAP = {"AZ": "ARI", "LAR": "LA"}


def norm_name(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def read_official():
    rows = []
    with open(PSV, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) != 6:
                raise SystemExit(f"{PSV}:{lineno}: expected 6 fields, got {len(parts)}")
            team, player, pos, injury, practice, game = parts
            rows.append({
                "line": lineno,
                "team": team,
                "player": player,
                "position": pos,
                "injury": injury or None,
                "practice": PRACTICE[practice],
                "game": game or None,
            })
    return rows


def main():
    official = read_official()
    scrape = json.load(open(SCRAPE, encoding="utf-8"))["rows"]

    scraped = []
    for r in scrape:
        team = CODE_MAP.get(r["team"], r["team"])
        scraped.append({
            "team": team,
            "player": r["player"],
            "position": r["position"],
            "injury": r.get("injury"),
            "practice": r.get("practice"),
            "game": r.get("game"),
            "player_url": r.get("player_url"),
        })

    off_index = {}
    for r in official:
        off_index.setdefault((r["team"], norm_name(r["player"])), []).append(r)
    scr_index = {}
    for r in scraped:
        scr_index.setdefault((r["team"], norm_name(r["player"])), []).append(r)

    matched, field_diffs, missing, extra = [], [], [], []
    for key, offs in off_index.items():
        scrs = scr_index.get(key, [])
        if not scrs:
            missing.extend(offs)
            continue
        o, s = offs[0], scrs[0]
        diffs = {}
        for f in ("position", "injury", "practice", "game"):
            if (o[f] or "") != (s[f] or ""):
                diffs[f] = {"official": o[f], "scraped": s[f]}
        if diffs:
            field_diffs.append({"team": key[0], "player": o["player"], "diffs": diffs, "official_line": o["line"]})
        else:
            matched.append({"team": key[0], "player": o["player"], "official_line": o["line"]})
    for key, scrs in scr_index.items():
        if key not in off_index:
            extra.extend(scrs)

    # Row-count comparison per club
    off_counts, scr_counts = {}, {}
    for r in official:
        off_counts[r["team"]] = off_counts.get(r["team"], 0) + 1
    for r in scraped:
        scr_counts[r["team"]] = scr_counts.get(r["team"], 0) + 1
    club_counts = []
    for t in sorted(set(off_counts) | set(scr_counts)):
        club_counts.append({
            "team": t,
            "official_rows": off_counts.get(t, 0),
            "scraped_rows": scr_counts.get(t, 0),
            "match": off_counts.get(t, 0) == scr_counts.get(t, 0),
        })

    result = {
        "checked_on": "2026-11-12",
        "official_source": "https://www.nfl.com/injuries/",
        "method": "Hand transcription of all 7 fetched chunks of the official page (data/dashboard/official_injuries_2026_w10.psv), compared field by field with data/model/official_injuries.json. Club codes AZ->ARI and LAR->LA mapped as in the pipeline.",
        "counts": {
            "official_rows": len(official),
            "scraped_rows": len(scraped),
            "matched_all_fields": len(matched),
            "field_differences": len(field_diffs),
            "missing_from_scrape": len(missing),
            "extra_in_scrape": len(extra),
            "clubs_on_official_page": len(set(r["team"] for r in official)),
            "clubs_in_scrape": len(set(r["team"] for r in scraped)),
        },
        "missing_from_scrape": [{"team": r["team"], "player": r["player"], "position": r["position"], "practice": r["practice"], "game": r["game"], "official_line": r["line"]} for r in missing],
        "extra_in_scrape": [{"team": r["team"], "player": r["player"]} for r in extra],
        "field_differences": field_diffs,
        "club_counts": club_counts,
        "matched_rows": matched,
        "official_game_status_rows": [
            {"team": r["team"], "player": r["player"], "position": r["position"], "injury": r["injury"], "practice": r["practice"], "game": r["game"], "official_line": r["line"]}
            for r in official if r["game"] or r["injury"]
        ],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    c = result["counts"]
    print(json.dumps(c, indent=1))
    for m in result["missing_from_scrape"]:
        print("MISSING", m)
    for d in field_diffs:
        print("DIFF", d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
