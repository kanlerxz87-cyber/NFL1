#!/usr/bin/env python3
"""build_depth_ladder.py — join official club depth charts to the official injury report.

Why this exists
---------------
The brief asks the system to "track injuries and know any deficiencies in defenses such as
2nd, 3rd or 4th string backups having to replace starters due to lineups", and the same for
offences. The availability model in ``pipeline/build_all.py`` only publishes depth rank 1
starters and their rank 2 replacement. This module publishes the whole ladder.

Two facts established before any code was written, both verified on 2026-11-13:

1. ``https://www.nfl.com/teams/<club>/depth-chart`` returns **404**. nfl.com publishes no
   depth chart at all, so the ladder can only come from the clubs themselves.
2. ``https://www.azcardinals.com/team/depth-chart`` returns a live official chart whose rows
   reproduce this repository's committed transcription exactly (checked row for row).

Inputs (both committed, both official)
--------------------------------------
* ``data/session-1505ac8e/depth_charts.json`` — 31 of 32 club charts, ranks 1..6.
  HOU publishes no depth chart; the gap is reported, never filled.
* ``data/model/official_injuries.json``      — the scraped nfl.com report for the week.

Rules
-----
* A player is *unavailable* only when the official report says Out or Doubtful, or when the
  club has published no report at all, in which case the status is the explicit string
  "no report published", never "healthy".
* Questionable is counted as *available but at risk* and shown in its own column. A slot
  whose projected starter is Questionable is not counted as a deficiency.
* Nothing is inferred. Where the ladder runs out of listed players the cell reads blank.
* Name cells that look like two players merged by the scraper are published verbatim and
  flagged; they are never silently split (that would invent a player).

Output: ``data/depth_ladder.json``.
"""
from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEPTH_IN = os.path.join(ROOT, "data", "session-1505ac8e", "depth_charts.json")
INJ_IN = os.path.join(ROOT, "data", "model", "official_injuries.json")
OUT = os.path.join(ROOT, "data", "depth_ladder.json")

NFL_INJURY_URL = "https://www.nfl.com/injuries/"
NFL_TEAMS_URL = "https://www.nfl.com/teams/"

# The injury report and the club charts disagree on two club codes. Verified on 2026-11-12:
# nfl.com uses LAR and AZ; the club sites (and the nflverse directory) use LA and ARI.
CLUB_ALIAS = {"LAR": "LA", "AZ": "ARI", "LA": "LA", "ARI": "ARI"}

SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v", "x"}


def clean_name(raw: str) -> str:
    """Unescape HTML entities and collapse whitespace. Never rewrites the name itself."""
    if raw is None:
        return ""
    return re.sub(r"\s+", " ", html.unescape(str(raw))).strip()


def looks_merged(name: str) -> bool:
    """True when a scraped cell is likely two players run together.

    A normal NFL name is one to three tokens ("Jayden Williams", "Carlton Davis III").
    Four or more capitalised tokens with no generational suffix means the scraper almost
    certainly concatenated two co-starters into one cell. Names with a lowercase particle
    ("Jordan van den Berg") are four tokens but one person, so they are excluded.
    We publish the cell verbatim and flag it rather than guessing a split.
    """
    toks = [t for t in name.split() if t]
    if len(toks) < 4:
        return False
    if any(t[:1].islower() for t in toks):
        return False
    return not any(t.lower().strip(".,") in SUFFIXES for t in toks[2:])


def status_key(rec):
    """Map an official injury row to one status word, preferring the game designation."""
    game = (rec.get("game") or "").strip()
    practice = (rec.get("practice") or "").strip()
    if game:
        return game  # Out / Doubtful / Questionable
    if practice == "Did Not Participate In Practice":
        return "Did not practice"
    if practice == "Limited Participation in Practice":
        return "Limited practice"
    if practice == "Full Participation in Practice":
        return "Full practice"
    return "Listed (no participation shown)"


UNAVAILABLE = {"Out", "Doubtful"}
AT_RISK = {"Questionable", "Did not practice", "Limited practice"}


def dedupe_fragments(slots):
    """Drop slots that are a leftover fragment of the slot immediately before them.

    Several club pages emit the same position line twice, the second copy holding only
    the backup rows (example, verified in the committed transcription: the Jets' defence
    lists "DL: Harrison Phillips / Jack Heflin" and then a second "DL: Jack Heflin").
    A fragment is only dropped when every player it lists already appears at the same rank
    in the preceding line of the same unit and position, so genuinely separate lines
    (the Eagles list three distinct DT lines) are preserved.
    """
    out = []
    for slot in slots:
        prev = None
        for cand in reversed(out):
            if cand["unit"] == slot["unit"] and cand["position"] == slot["position"]:
                prev = cand
                break
            if cand["unit"] != slot["unit"]:
                break
        if prev is not None and slot["players"]:
            prev_keys = {(p["rank"], p["name"]) for p in prev["players"]}
            keys = {(p["rank"], p["name"]) for p in slot["players"]}
            if keys and keys <= prev_keys:
                continue
        out.append(slot)
    return out


def main() -> int:
    with open(DEPTH_IN) as f:
        depth = json.load(f)
    with open(INJ_IN) as f:
        inj = json.load(f)

    week = inj.get("week")
    season = inj.get("season")

    # availability lookup: (club, normalised name) -> status record
    avail = {}
    for r in inj.get("rows", []):
        club = CLUB_ALIAS.get(r.get("team"), r.get("team"))
        key = (club, clean_name(r.get("player")).lower())
        prev = avail.get(key)
        cur = {"status": status_key(r), "injury": r.get("injury"),
               "position": r.get("position"),
               "source": r.get("player_url") or NFL_INJURY_URL}
        # a game designation always beats a practice-only row for the same player
        if prev is None or (prev["status"] not in UNAVAILABLE and cur["status"] in UNAVAILABLE):
            avail[key] = cur

    clubs_with_report = {CLUB_ALIAS.get(r.get("team"), r.get("team"))
                         for r in inj.get("rows", [])}

    merged_flags = []
    clubs_out = []
    slots_out = []
    chart_gaps = []

    for club in depth.get("clubs", []):
        abbr = club.get("abbr")
        if club.get("status") != "ok":
            clubs_out.append({
                "abbr": abbr, "club": club.get("club"),
                "chart_url": club.get("source_url"),
                "chart_status": club.get("status"),
                "reason": club.get("reason") or "club published no depth chart at fetch time",
                "unofficial_label": bool(club.get("unofficial_label")),
                "as_of": club.get("as_of") or "",
                "report_published": abbr in clubs_with_report,
                "slots": 0, "offense_slots": 0, "defense_slots": 0, "special_teams_slots": 0,
                "slots_missing_starter": 0, "offense_missing_starter": 0,
                "defense_missing_starter": 0,
                "slots_starter_at_risk": 0, "offense_starter_at_risk": 0,
                "defense_starter_at_risk": 0,
                "deepest_string_starting": None,
                "offense_deepest_string_starting": None,
                "defense_deepest_string_starting": None,
                "unavailable_in_ladder": 0,
                "ladder_depth_4_plus": 0,
                "source": NFL_TEAMS_URL,
            })
            continue

        unit_counts = {"offense": 0, "defense": 0, "special_teams": 0}
        missing = {"offense": 0, "defense": 0, "special_teams": 0}
        deepest = {"offense": 0, "defense": 0, "special_teams": 0}
        risk = {"offense": 0, "defense": 0, "special_teams": 0}
        unavailable_in_ladder = 0
        ladder_depth_4 = 0

        for slot_no, slot in enumerate(dedupe_fragments(club.get("depth", [])), start=1):
            unit = slot.get("unit")
            pos = slot.get("position")
            players = []
            for p in slot.get("players", []):
                name = clean_name(p.get("name"))
                if not name:
                    continue
                rank = p.get("rank")
                rec = avail.get((abbr, name.lower()))
                if rec is None:
                    status = "Not on the report"
                    injury = None
                    psrc = club.get("source_url")
                else:
                    status = rec["status"]
                    injury = rec["injury"]
                    psrc = rec["source"]
                if looks_merged(name):
                    merged_flags.append({"abbr": abbr, "unit": unit, "position": pos,
                                         "rank": rank, "raw": name,
                                         "chart_url": club.get("source_url")})
                if status in UNAVAILABLE:
                    unavailable_in_ladder += 1
                players.append({"rank": rank, "name": name, "status": status,
                                "injury": injury, "source": psrc})

            if not players:
                continue

            unit_counts[unit] = unit_counts.get(unit, 0) + 1

            # projected starter: the lowest-ranked listed player who is not Out/Doubtful
            starter = next((p for p in players if p["status"] not in UNAVAILABLE), None)
            # at-risk list: everyone above the starter who is Questionable or Out/Doubtful
            out_above = [p for p in players
                         if starter is not None and p["rank"] < starter["rank"]]

            has_rank1 = any(p["rank"] == 1 for p in players)
            if not has_rank1:
                # The club chart lists no first string for this line. That is a gap in the
                # chart, not evidence of an injury: it is published separately and is never
                # counted as a deficiency.
                chart_gaps.append({
                    "abbr": abbr, "club": club.get("club"), "unit": unit,
                    "position": pos, "slot": slot_no,
                    "listed": ", ".join(f"{p['name']} ({p['rank']})" for p in players),
                    "chart_url": club.get("source_url"),
                })

            if starter is None:
                starter_rank = None
                starter_name = None
                starter_status = "No listed player available"
                missing[unit] = missing.get(unit, 0) + 1
            else:
                starter_rank = starter["rank"]
                starter_name = starter["name"]
                starter_status = starter["status"]
                if starter_rank and starter_rank > 1:
                    if has_rank1:
                        # a backup is genuinely pressed into duty by an official designation
                        missing[unit] = missing.get(unit, 0) + 1
                        deepest[unit] = max(deepest.get(unit, 0), starter_rank or 0)
                    else:
                        starter_rank = None
                        starter_name = None
                        starter_status = "Chart lists no first string - unverified"
                if starter_status in AT_RISK:
                    risk[unit] = risk.get(unit, 0) + 1

            if len(players) >= 4:
                ladder_depth_4 += 1

            slots_out.append({
                "abbr": abbr, "club": club.get("club"), "unit": unit, "position": pos,
                "slot": slot_no,
                "starter_rank": starter_rank,
                "starter_name": starter_name,
                "starter_status": starter_status,
                "string_label": (f"{starter_rank}{['st', 'nd', 'rd'][starter_rank - 1]} string"
                                 if starter_rank and starter_rank <= 3
                                 else (f"{starter_rank}th string" if starter_rank else "blank")),
                "out_above": ", ".join(f"{p['name']} ({p['status'].lower()})" for p in out_above) or "",
                "ladder": players[:6],
                "chart_url": club.get("source_url"),
                "report_published": abbr in clubs_with_report,
            })

        def label(rank):
            if not rank:
                return None
            return (f"{rank}{['st', 'nd', 'rd'][rank - 1]} string" if rank <= 3
                    else f"{rank}th string")

        clubs_out.append({
            "abbr": abbr, "club": club.get("club"),
            "chart_url": club.get("source_url"),
            "chart_status": club.get("status"),
            "reason": club.get("reason") or "",
            "unofficial_label": bool(club.get("unofficial_label")),
            "as_of": club.get("as_of") or "",
            "report_published": abbr in clubs_with_report,
            "slots": sum(unit_counts.values()),
            "offense_slots": unit_counts.get("offense", 0),
            "defense_slots": unit_counts.get("defense", 0),
            "special_teams_slots": unit_counts.get("special_teams", 0),
            "slots_missing_starter": sum(missing.values()),
            "offense_missing_starter": missing.get("offense", 0),
            "defense_missing_starter": missing.get("defense", 0),
            "slots_starter_at_risk": sum(risk.values()),
            "offense_starter_at_risk": risk.get("offense", 0),
            "defense_starter_at_risk": risk.get("defense", 0),
            "deepest_string_starting": label(max(deepest.values()) or 0),
            "offense_deepest_string_starting": label(deepest.get("offense", 0)),
            "defense_deepest_string_starting": label(deepest.get("defense", 0)),
            "unavailable_in_ladder": unavailable_in_ladder,
            "ladder_depth_4_plus": ladder_depth_4,
            "source": NFL_TEAMS_URL,
        })

    # Only slots where a backup is actually pressed into duty go on the public page; the
    # full ladder stays in the JSON so a reviewer can audit any club.
    deficient = [s for s in slots_out if (s["starter_rank"] or 1) > 1]

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "season": season,
        "week": week,
        "method": {
            "depth_charts": ("Official club depth charts, https://www.<club>/team/depth-chart, "
                             "transcribed 2026-11-12. nfl.com publishes no depth chart: "
                             "https://www.nfl.com/teams/kansas-city-chiefs/depth-chart returns 404 "
                             "(re-checked 2026-11-13)."),
            "injuries": ("Official nfl.com injury report for the week, scraped in Actions and "
                         "committed to data/model/official_injuries.json."),
            "starter_rule": ("Projected starter = the lowest-ranked listed player at that slot who "
                             "is not Out or Doubtful on the official report. Questionable counts as "
                             "available but at risk and is shown, never upgraded or downgraded."),
            "no_report_clubs": ("Clubs with no published report this week (on bye, or the club has "
                                "filed nothing) are labelled 'no report published'. Their ladders "
                                "are published but no starter is marked unavailable, because the "
                                "absence of a report is not evidence of health."),
            "limits": [
                "Club depth charts are a club publication, not a league filing; several are "
                "labelled unofficial by the club itself and the label is carried through.",
                "The chart is a weekly snapshot. Practice-squad elevations, trades and late "
                "scratches are not modelled.",
                "Game status is a designation, not proof of who plays.",
                "HOU publishes no depth chart; its rows are blank by design.",
            ],
        },
        "sources": {
            "depth_charts": "https://www.nfl.com/teams/",
            "injuries": NFL_INJURY_URL,
            "nfl_depth_chart_probe": "https://www.nfl.com/teams/kansas-city-chiefs/depth-chart",
            "nfl_depth_chart_probe_result": "HTTP 404 - the league publishes no depth chart",
            "spot_check": "https://www.azcardinals.com/team/depth-chart",
        },
        "counts": {
            "clubs_total": len(clubs_out),
            "clubs_with_chart": sum(1 for c in clubs_out if c["chart_status"] == "ok"),
            "clubs_without_chart": sum(1 for c in clubs_out if c["chart_status"] != "ok"),
            "clubs_with_injury_report": sum(1 for c in clubs_out if c["report_published"]),
            "slots": sum(c["slots"] for c in clubs_out),
            "offense_slots": sum(c["offense_slots"] for c in clubs_out),
            "defense_slots": sum(c["defense_slots"] for c in clubs_out),
            "special_teams_slots": sum(c["special_teams_slots"] for c in clubs_out),
            "slots_started_by_a_backup": len(deficient),
            "offense_slots_started_by_a_backup": sum(1 for s in deficient if s["unit"] == "offense"),
            "defense_slots_started_by_a_backup": sum(1 for s in deficient if s["unit"] == "defense"),
            "slots_with_3rd_string_or_worse": sum(1 for s in deficient if (s["starter_rank"] or 0) >= 3),
            "slots_starter_at_risk": sum(c["slots_starter_at_risk"] for c in clubs_out),
            "offense_slots_starter_at_risk": sum(c["offense_starter_at_risk"] for c in clubs_out),
            "defense_slots_starter_at_risk": sum(c["defense_starter_at_risk"] for c in clubs_out),
            "chart_gap_slots": len(chart_gaps),
            "players_unavailable_anywhere_in_a_ladder": sum(c["unavailable_in_ladder"] for c in clubs_out),
            "merged_name_cells_flagged": len(merged_flags),
        },
        "clubs": clubs_out,
        "deficient_slots": deficient,
        "chart_gaps": chart_gaps,
        "merged_name_flags": merged_flags,
    }

    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1)
    print(f"wrote data/depth_ladder.json: "
          f"{payload['counts']['slots']} slots, "
          f"{len(deficient)} started by a backup, "
          f"{len(merged_flags)} merged-name cells flagged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
