#!/usr/bin/env python3
"""Check the 14 Week 10 games in data/model/lines.json against the nfl.com schedule transcription.

Output: data/dashboard/schedule_check.json. A game matches when away, home and date are identical.
Club codes: nfl.com uses LAR and AZ; the pipeline uses LA and ARI (mapped here, nothing else).
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE = {"LAR": "LA", "AZ": "ARI"}


def main():
    official = json.load(open(os.path.join(ROOT, "data/dashboard/schedule_2026_w10.json"), encoding="utf-8"))
    lines = json.load(open(os.path.join(ROOT, "data/model/lines.json"), encoding="utf-8"))["lines"]
    off = {(CODE.get(g["away"], g["away"]), CODE.get(g["home"], g["home"]), g["date"]) for g in official["games"]}
    mod = {(g["away"], g["home"], g["gameday"]) for g in lines}
    result = {
        "checked_on": "2026-11-12",
        "official_games": len(off),
        "model_games": len(mod),
        "matched": len(off & mod),
        "official_not_in_model": sorted(off - mod),
        "model_not_in_official": sorted(mod - off),
        "bye_teams_official": official["byes_week_10"],
        "result": "PASS" if off == mod else "FAIL",
    }
    with open(os.path.join(ROOT, "data/dashboard/schedule_check.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
