"""Injury, availability and depth-chart impact tracking.

Two hard rules:
1. Everything transcribed from nfl.com/injuries is VERIFIED and stays verbatim.
2. String level (1st/2nd/3rd/4th on the depth chart) is NOT published by NFL.com.
   The NFL's sanctioned weekly depth-chart feed is Sportradar's official NFL API
   and it is credential-gated. String level is therefore reported as UNAVAILABLE
   and never guessed, and any index that would need it is labelled accordingly.
"""
from __future__ import annotations

from typing import Any

from . import ingest
from .provenance import DERIVED, MODELED, UNAVAILABLE, VERIFIED

OFFENSE = {"QB", "RB", "WR", "TE", "FB", "T", "G", "C", "OL"}
DEFENSE = {"DE", "DT", "LB", "CB", "S", "DB", "DL", "NT", "EDGE"}
SPECIAL = {"K", "P", "LS"}

#: Analyst priors. NOT fitted, NOT verified. Published openly for review and
#: listed in Open Questions as a calibration task.
SEVERITY_WEIGHTS = {
    "Out": 1.00, "Doubtful": 0.80, "Questionable": 0.50,
    "DNP_no_status": 0.45, "LP": 0.25, "FP": 0.05,
}
POSITION_WEIGHTS = {
    "QB": 1.00, "CB": 0.55, "DE": 0.55, "EDGE": 0.55, "T": 0.55,
    "C": 0.50, "DT": 0.45, "LB": 0.45, "RB": 0.45, "WR": 0.45,
    "G": 0.40, "TE": 0.40, "S": 0.40, "K": 0.25, "P": 0.20,
    "LS": 0.15, "FB": 0.10, "OL": 0.45, "DB": 0.50, "DL": 0.45, "NT": 0.45,
}
#: Positions whose absence moves a betting line the most.
KEY_POSITIONS = {"QB", "T", "C", "DE", "EDGE", "CB", "WR", "RB"}

DEPTH_CHART_STATUS = {
    "value": None, "tier": UNAVAILABLE,
    "reason": "NFL.com does not publish a public weekly depth chart. The league's "
              "official weekly depth-chart feed is Sportradar's NFL Official API "
              "(Sportradar is the NFL's official data partner) and it requires an "
              "API key that this environment does not hold. Individual club sites "
              "publish charts in inconsistent, unversioned formats.",
    "resolving_source": "https://developer.sportradar.com/football/reference/nfl-weekly-depth-charts",
    "consequence": "String level (1st/2nd/3rd/4th) cannot be attached to any "
                   "player row. The availability index below is therefore "
                   "computed WITHOUT string weighting and is labelled MODELED.",
}

#: Starting-quarterback and marquee-absence facts confirmed by official NFL.com
#: news items listed on the official injury report page. Transcribed verbatim.
QB_AND_KEY_AVAILABILITY = [
    {"team_abbr": "CLE", "position": "QB", "fact": "Browns to start QB Deshaun Watson vs. Texans",
     "kind": "starter change", "week": 10, "tier": VERIFIED,
     "url": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11"},
    {"team_abbr": "AZ", "position": "QB", "fact": "Cardinals' Carson Beck to start vs. Rams",
     "kind": "starter change", "week": 10, "tier": VERIFIED,
     "url": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11"},
    {"team_abbr": "MIA", "position": "QB",
     "fact": "Dolphins place QB Malik Willis (groin) on injured reserve; Kyle McCord in line for first start",
     "kind": "starter change (IR placement)", "week": 10, "tier": VERIFIED,
     "url": "https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start"},
    {"team_abbr": "SEA", "position": "QB",
     "fact": "Sam Darnold ruled out for Seahawks' Week 10 game vs. Raiders; Drew Lock expected to start again",
     "kind": "starter ruled out", "week": 10, "tier": VERIFIED,
     "url": "https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again"},
    {"team_abbr": "NYG", "position": "QB",
     "fact": "J.J. McCarthy expected to play Week 10",
     "kind": "starter expected to play", "week": 10, "tier": VERIFIED,
     "url": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-monday-nov-9"},
    {"team_abbr": "LAC", "position": "QB",
     "fact": "Justin Herbert avoids finger fracture",
     "kind": "starter cleared of fracture", "week": 10, "tier": VERIFIED,
     "url": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-monday-nov-9"},
    {"team_abbr": "LA", "position": "WR",
     "fact": "Rams WR Puka Nacua likely to be placed on injured reserve with turf toe, sprained MCL and PCL",
     "kind": "marquee absence (IR likely)", "week": 10, "tier": VERIFIED,
     "url": "https://www.nfl.com/news/rams-wr-puka-nacua-likely-to-be-placed-on-injured-reserve-with-turf-toe-sprained-mcl-and-pcl"},
    {"team_abbr": "GB", "position": "RB",
     "fact": "Packers RB Josh Jacobs to undergo surgery on finger this week; timeline to return TBD",
     "kind": "marquee absence (surgery)", "week": 10, "tier": VERIFIED,
     "url": "https://www.nfl.com/news/packers-rb-josh-jacobs-to-undergo-surgery-on-finger-this-week"},
    {"team_abbr": "BUF", "position": "S", "fact": "Bills acquire S Amani Hooker",
     "kind": "transaction", "week": 10, "tier": VERIFIED,
     "url": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-tuesday-nov-10"},
    {"team_abbr": "DEN", "position": "LB", "fact": "Broncos trade for Chargers' Daiyan Henley",
     "kind": "transaction", "week": 10, "tier": VERIFIED,
     "url": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-tuesday-nov-10"},
]

#: Severity implied by an official NFL.com news headline, keyed to the row above.
NEWS_DISRUPTION = {("CLE", "QB"): 1.00, ("AZ", "QB"): 1.00, ("MIA", "QB"): 1.00,
                   ("SEA", "QB"): 1.00, ("NYG", "QB"): 0.15, ("LAC", "QB"): 0.10,
                   ("LA", "WR"): 0.90, ("GB", "RB"): 0.90}


def unit(position: str) -> str:
    if position in OFFENSE:
        return "OFF"
    if position in DEFENSE:
        return "DEF"
    if position in SPECIAL:
        return "ST"
    return "UNKNOWN"


def _severity(row: dict[str, Any]) -> float:
    gs = row.get("game_status")
    if gs in ("Out", "Doubtful", "Questionable"):
        return SEVERITY_WEIGHTS[gs]
    code = row.get("practice_code")
    if code == "DNP":
        return SEVERITY_WEIGHTS["DNP_no_status"]
    if code == "LP":
        return SEVERITY_WEIGHTS["LP"]
    if code == "FP":
        return SEVERITY_WEIGHTS["FP"]
    return 0.0


def team_availability(injuries: list[dict[str, Any]],
                      status_rows: list[dict[str, Any]],
                      schedule: list[dict[str, Any]],
                      byes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    playing = {g["away_abbr"] for g in schedule} | {g["home_abbr"] for g in schedule}
    bye = {b["team_abbr"] for b in byes}
    smap = {r["team_abbr"]: r for r in status_rows}
    out = []
    for team in sorted(playing | bye):
        rows = [r for r in injuries if r["team_abbr"] == team]
        st = smap.get(team, {})
        rec: dict[str, Any] = {
            "team_abbr": team, "week": 10,
            "report_status": st.get("report_status"),
            "evidence": st.get("evidence"), "source_url": ingest.INJURY_REPORT_URL,
            "entries": len(rows),
            "counts": {"FP": 0, "LP": 0, "DNP": 0},
            "game_status": {"Out": 0, "Doubtful": 0, "Questionable": 0},
            "by_unit": {"OFF": 0, "DEF": 0, "ST": 0},
            "dnp_by_unit": {"OFF": 0, "DEF": 0, "ST": 0},
            "out_by_unit": {"OFF": 0, "DEF": 0, "ST": 0},
            "key_position_entries": 0,
            "qb_entries": 0,
            "injury_designation_present": 0,
            "injury_designation_blank": 0,
        }
        for r in rows:
            u = unit(r["position"])
            if r["practice_code"] in rec["counts"]:
                rec["counts"][r["practice_code"]] += 1
            if r["game_status"] in rec["game_status"]:
                rec["game_status"][r["game_status"]] += 1
            if u in rec["by_unit"]:
                rec["by_unit"][u] += 1
                if r["practice_code"] == "DNP":
                    rec["dnp_by_unit"][u] += 1
                if r["game_status"] == "Out":
                    rec["out_by_unit"][u] += 1
            if r["position"] in KEY_POSITIONS:
                rec["key_position_entries"] += 1
            if r["position"] == "QB":
                rec["qb_entries"] += 1
            if r["injury"]:
                rec["injury_designation_present"] += 1
            else:
                rec["injury_designation_blank"] += 1

        # Unstringed availability pressure: sum(severity * position weight).
        pressure = sum(_severity(r) * POSITION_WEIGHTS.get(r["position"], 0.30)
                       for r in rows)
        for (t, pos), sev in NEWS_DISRUPTION.items():
            if t == team:
                pressure += sev * POSITION_WEIGHTS.get(pos, 0.30)
        rec["availability_pressure_unstringed"] = round(pressure, 4)
        rec["availability_pressure_tier"] = MODELED
        rec["availability_pressure_note"] = (
            "Sum over entries of severity_weight x position_weight. Both weight "
            "tables are analyst priors (see Methodology) - NOT fitted and NOT "
            "verified - and no string-level weighting is applied because official "
            "depth charts are unavailable. Treat as a ranking aid only.")
        rec["qb_disruption"] = [f for f in QB_AND_KEY_AVAILABILITY
                                if f["team_abbr"] == team and f["position"] == "QB"]
        rec["marquee_absences"] = [f for f in QB_AND_KEY_AVAILABILITY
                                   if f["team_abbr"] == team and f["position"] != "QB"
                                   and f["kind"].startswith("marquee")]
        rec["string_levels"] = DEPTH_CHART_STATUS
        out.append(rec)
    return out


def league_availability_summary(team_rows: list[dict[str, Any]],
                                injuries: list[dict[str, Any]]) -> dict[str, Any]:
    playing = [r for r in team_rows if r["report_status"] != "on bye (no report)"]
    tot = len(injuries)
    return {
        "total_report_entries": tot,
        "teams_with_entries": sum(1 for r in playing if r["entries"] > 0),
        "teams_printing_no_injuries_reported": sum(
            1 for r in playing if r["report_status"] == "no injuries reported"),
        "teams_on_bye": sum(1 for r in team_rows
                            if r["report_status"] == "on bye (no report)"),
        "entries_with_out_designation": sum(r["game_status"]["Out"] for r in team_rows),
        "entries_with_questionable": sum(r["game_status"]["Questionable"] for r in team_rows),
        "entries_with_doubtful": sum(r["game_status"]["Doubtful"] for r in team_rows),
        "entries_dnp": sum(r["counts"]["DNP"] for r in team_rows),
        "entries_lp": sum(r["counts"]["LP"] for r in team_rows),
        "entries_fp": sum(r["counts"]["FP"] for r in team_rows),
        "off_entries": sum(r["by_unit"]["OFF"] for r in team_rows),
        "def_entries": sum(r["by_unit"]["DEF"] for r in team_rows),
        "st_entries": sum(r["by_unit"]["ST"] for r in team_rows),
        "qb_entries": sum(r["qb_entries"] for r in team_rows),
        "key_position_entries": sum(r["key_position_entries"] for r in team_rows),
        "injury_designation_present": sum(r["injury_designation_present"] for r in team_rows),
        "injury_designation_blank": sum(r["injury_designation_blank"] for r in team_rows),
        "designation_coverage_pct": round(
            100.0 * sum(r["injury_designation_present"] for r in team_rows) / tot, 2) if tot else None,
        "designation_coverage_tier": DERIVED,
        "source_url": ingest.INJURY_REPORT_URL,
    }


def build() -> dict[str, Any]:
    inj = ingest.injuries()
    teams = team_availability(inj, ingest.team_report_status(),
                              ingest.schedule(), ingest.byes())
    return {
        "teams": teams,
        "league": league_availability_summary(teams, inj),
        "entries": inj,
        "qb_and_key_availability": QB_AND_KEY_AVAILABILITY,
        "depth_chart_status": DEPTH_CHART_STATUS,
        "severity_weights": SEVERITY_WEIGHTS,
        "position_weights": POSITION_WEIGHTS,
        "news": ingest.news(),
    }
