#!/usr/bin/env python3
"""Compare the committed nfl.com injury scrape with a dated live read, row by row.

Session 07810d9f-nfl1, 2026-11-15. Publishes the DELTA between two reads of the same
official page (the brief asks for deltas, not levels). Inputs:
  data/model/official_injuries.json                         committed scrape (generated_at 2026-11-14T17:02Z)
  data/brief_07810d9f/live_read_2026-11-15_week10.psv       hand transcription of all 8 fetch_page chunks
Output: data/brief_07810d9f/injury_delta_2026-11-15.json
"""
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRAPE = os.path.join(ROOT, "data/model/official_injuries.json")
LIVE = os.path.join(ROOT, "data/brief_07810d9f/live_read_2026-11-15_week10.psv")
OUT = os.path.join(ROOT, "data/brief_07810d9f/injury_delta_2026-11-15.json")

PRACTICE = {"FULL": "Full Participation in Practice",
            "LIM": "Limited Participation in Practice",
            "DNP": "Did Not Participate In Practice"}
SCRAPE_CLUB = {"LA": "LAR", "ARI": "AZ"}  # the scrape uses LA / ARI; the page prints LAR / AZ


def norm(v):
    return (v or "").strip()


def load_live():
    rows = []
    for line in open(LIVE, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        team, player, pos, injury, practice, game = line.rstrip("\n").split("|")
        rows.append({"team": team, "player": player, "position": pos, "injury": injury,
                     "practice": PRACTICE[practice], "game": game})
    return rows


def load_scrape():
    d = json.load(open(SCRAPE, encoding="utf-8"))
    rows = []
    for r in d["rows"]:
        rows.append({"team": SCRAPE_CLUB.get(r["team"], r["team"]), "player": r["player"],
                     "position": r["position"], "injury": norm(r["injury"]),
                     "practice": norm(r["practice"]), "game": norm(r["game"])})
    return d, rows


def main():
    live = load_live()
    meta, scrape = load_scrape()
    lk = {(r["team"], r["player"]): r for r in live}
    sk = {(r["team"], r["player"]): r for r in scrape}
    assert len(lk) == len(live), "duplicate live key"
    assert len(sk) == len(scrape), "duplicate scrape key"

    live_clubs = Counter(r["team"] for r in live)
    scrape_clubs = Counter(r["team"] for r in scrape)
    clubs = sorted(set(live_clubs) | set(scrape_clubs))
    per_club = {c: {"live_rows": live_clubs.get(c, 0), "scrape_rows": scrape_clubs.get(c, 0)} for c in clubs}

    only_live = [lk[k] for k in sorted(set(lk) - set(sk))]
    only_scrape = [sk[k] for k in sorted(set(sk) - set(lk))]

    field_mismatch = []
    by_field = Counter()
    blank_in_scrape_only = defaultdict(int)
    for k in sorted(set(lk) & set(sk)):
        a, b = lk[k], sk[k]
        for f in ("position", "injury", "practice", "game"):
            if norm(a[f]) != norm(b[f]):
                by_field[f] += 1
                field_mismatch.append({"team": k[0], "player": k[1], "field": f,
                                       "live": a[f], "scrape": b[f]})
                if norm(b[f]) == "" and norm(a[f]) != "":
                    blank_in_scrape_only[k[0]] += 1

    # Rows the scrape reports as having an injury or game status while the live read does not
    scrape_blank_status_clubs = {}
    for c in clubs:
        live_c = [r for r in live if r["team"] == c and (r["injury"] or r["game"])]
        scrape_c = [r for r in scrape if r["team"] == c and (r["injury"] or r["game"])]
        scrape_blank_status_clubs[c] = {
            "live_rows_with_injury_or_game_status": len(live_c),
            "scrape_rows_with_injury_or_game_status": len(scrape_c),
        }

    summary = {
        "live_rows": len(live),
        "scrape_rows": len(scrape),
        "live_clubs_with_rows": len(live_clubs),
        "scrape_clubs_with_rows": len(scrape_clubs),
        "rows_matched_by_team_and_player": len(set(lk) & set(sk)),
        "rows_only_on_live_page": len(only_live),
        "rows_only_in_scrape": len(only_scrape),
        "field_mismatches_on_matched_rows": dict(by_field),
        "clubs_with_scrape_blank_where_live_has_status": {c: n for c, n in blank_in_scrape_only.items()},
        "scrape_generated_at": meta.get("generated_at"),
        "scrape_html_sha256": meta.get("html_sha256"),
        "scrape_rows_claimed": meta.get("counts", {}).get("rows"),
    }
    out = {
        "what": "Delta between the committed nfl.com injury scrape and a dated live read of the same page. Published as differences only.",
        "live_read": {"source_url": "https://www.nfl.com/injuries/", "read_on_utc": "2026-11-15T12:18Z",
                      "method": "fetch_page, chunks 0-7 of 8, each club section's rows transcribed by hand to data/brief_07810d9f/live_read_2026-11-15_week10.psv",
                      "file": "data/brief_07810d9f/live_read_2026-11-15_week10.psv"},
        "committed_scrape": {"file": "data/model/official_injuries.json", "generated_at": meta.get("generated_at"),
                             "source_url": meta.get("source_url")},
        "summary": summary,
        "per_club": per_club,
        "scrape_blank_status_check": scrape_blank_status_clubs,
        "rows_only_on_live_page": only_live,
        "rows_only_in_scrape": only_scrape,
        "field_mismatches": field_mismatch,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
