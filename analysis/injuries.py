#!/usr/bin/env python3
"""
injuries.py — availability / deficiency snapshot from VERIFIED official rows only.

Output: data/verified/model/availability.json

What this can honestly say
  * which named players the official Week 10 report marks Out or Questionable, by unit
  * how many verified absences each team has, split offence / defence / specialists
  * which teams the official report lists as reporting no injuries at all
  * officially stated quarterback changes (headline-level, with links)

What it deliberately does NOT say
  * who the 2nd/3rd/4th string is — the NFL does not publish depth charts
    (nfl.com/teams/<club>/depth-chart returns 404, checked 2026-11-12), so any
    "3rd-string" ordering would be invented. Those cells stay blank and flagged.
  * how much an absence costs in points — that needs per-player value estimates and
    participation data, neither of which is in the verified set.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "verified"
OUT = DATA / "model"

OFFENCE = {"QB", "RB", "FB", "WR", "TE", "T", "OT", "G", "OG", "C", "OL", "LS"}
DEFENCE = {"DE", "DT", "NT", "LB", "ILB", "OLB", "MLB", "CB", "S", "SS", "FS", "DB"}
SPECIAL = {"K", "P"}


def unit(pos: str) -> str:
    p = pos.upper()
    if p in {"K", "P"}:          # long snapper grouped with specialists here
        return "specialists"
    if p == "LS":
        return "specialists"
    if p in OFFENCE:
        return "offence"
    if p in DEFENCE:
        return "defence"
    return "unclassified"


def rows(name):
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    inj = rows("injuries_week10.csv")
    clean = rows("no_injuries_week10.csv")
    qb = rows("qb_changes_2026.csv")
    st = rows("standings_2026.csv")

    per_team = {}
    for r in inj:
        t = r["team_abbr"]
        e = per_team.setdefault(t, {"out": 0, "questionable": 0, "by_unit": {}, "players": []})
        u = unit(r["position"])
        e["by_unit"][u] = e["by_unit"].get(u, 0) + 1
        if r["game_status"].lower() == "out":
            e["out"] += 1
        else:
            e["questionable"] += 1
        e["players"].append({"player": r["player"], "pos": r["position"], "injury": r["injury"],
                             "status": r["game_status"], "unit": u, "source_url": r["source_url"]})

    table = []
    for r in st:
        t = r["abbr"]
        e = per_team.get(t, {"out": 0, "questionable": 0, "by_unit": {}, "players": []})
        table.append({
            "team": r["team"], "abbr": t,
            "verified_out": e["out"], "verified_questionable": e["questionable"],
            "offence": e["by_unit"].get("offence", 0),
            "defence": e["by_unit"].get("defence", 0),
            "specialists": e["by_unit"].get("specialists", 0),
            "reported_clean": any(c["team_abbr"] == t for c in clean),
            "depth_order_known": False,
            "players": e["players"],
        })
    table.sort(key=lambda x: (-(x["verified_out"] * 2 + x["verified_questionable"]), x["abbr"]))

    out = {
        "week": 10,
        "generated_at": "2026-11-12",
        "sources": {
            "injury_report": "https://www.nfl.com/injuries/",
            "depth_chart_attempt": "https://www.nfl.com/teams/washington-commanders/depth-chart (404)",
        },
        "coverage_note": (
            "Only rows where the official report states a game status are counted. Players listed "
            "with a practice status but no game status are NOT counted as out or available, because "
            "the source does not assert either."
        ),
        "limitation": (
            "Depth order (starter / 2nd / 3rd / 4th string) is not published by the NFL and is "
            "therefore unknown for every team. Absence counts below are verified; replacement "
            "seniority is not."
        ),
        "teams": table,
        "reported_no_injuries": [{"team_abbr": c["team_abbr"], "source_url": c["source_url"]} for c in clean],
        "official_qb_changes": [{
            "team": r["team_abbr"], "change": r["player_change"], "status": r["status_as_stated"],
            "replacement_stated": r["replacement_stated"], "article_url": r["article_url"],
            "listing_source_url": r["listing_source_url"],
            "verification_level": r["verification_level"],
        } for r in qb],
        "totals": {
            "verified_out": sum(x["verified_out"] for x in table),
            "verified_questionable": sum(x["verified_questionable"] for x in table),
            "teams_with_clean_report": len(clean),
            "teams_with_verified_absence": sum(1 for x in table if x["verified_out"] + x["verified_questionable"] > 0),
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "availability.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("verified absences:", out["totals"])
    for t in table[:6]:
        print(f"  {t['abbr']}: out {t['verified_out']} q {t['verified_questionable']} "
              f"(off {t['offence']} / def {t['defence']} / st {t['specialists']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
