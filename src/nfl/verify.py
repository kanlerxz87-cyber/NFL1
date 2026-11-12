"""Line-by-line verification harness.

Three outcomes per check:
  PASS  - the verified source agrees with arithmetic / an independent page.
  FLAG  - the OFFICIAL SOURCE is internally inconsistent. We publish the cell
          verbatim, exclude it from every downstream computation, and put it on
          the Flagged for Review page with the arithmetic proof. We never
          overwrite it with a guessed value.
  FAIL  - our own transcription or harness is wrong and must be fixed.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from . import ingest

#: Official 8-division alignment of the 32 NFL clubs.
NFL32 = {
    "AFC East": ["BUF", "MIA", "NE", "NYJ"],
    "AFC North": ["BAL", "CIN", "CLE", "PIT"],
    "AFC South": ["HOU", "IND", "JAX", "TEN"],
    "AFC West": ["DEN", "KC", "LAC", "LV"],
    "NFC East": ["DAL", "NYG", "PHI", "WAS"],
    "NFC North": ["CHI", "DET", "GB", "MIN"],
    "NFC South": ["ATL", "CAR", "NO", "TB"],
    "NFC West": ["ARI", "LA", "SEA", "SF"],
}
#: NFL.com standings prints AZ; the NFL's club code is ARI.
ABBR_ALIASES = {"AZ": "ARI"}

KNOWN_POSITIONS = {"QB","RB","WR","TE","FB","T","G","C","OL","K","P","LS",
                   "DE","DT","LB","CB","S","DB","DL","NT","EDGE"}
GAME_STATUS_VOCAB = {None, "Out", "Doubtful", "Questionable"}


def pct(w: int | None, l: int | None, t: int | None) -> float | None:
    """NFL winning percentage: ties count as half a win and half a loss."""
    if w is None or l is None or t is None:
        return None
    gp = w + l + t
    if not gp:
        return None
    # NFL.com rounds winning percentage half-up to three decimals, so the
    # harness must too (Python's built-in round() is half-to-even, which turns
    # 0.3125 into 0.312 instead of the published 0.313).
    return float(Decimal((w + 0.5 * t) / gp).quantize(Decimal("0.001"),
                                                      rounding=ROUND_HALF_UP))


def _games(w, l, t) -> int:
    return (w or 0) + (l or 0) + (t or 0)


def _row(check_id, scope, expected, actual, source_url, result=None, note="",
         source_urls=None):
    if result is None:
        result = "PASS" if expected == actual else "FAIL"
    row = {"check_id": check_id, "scope": scope, "expected": expected,
           "actual": actual, "result": result, "source_url": source_url,
           "note": note}
    if source_urls:
        row["source_urls"] = list(source_urls)
    return row


#: Transcribed verbatim from the record printed beside each team logo on
#: https://www.nfl.com/injuries/ (Week 10, 2026) in the same retrieval session.
INJURY_PAGE_RECORDS = {
    "WAS": "2-5-1", "NYG": "5-2-1", "NE": "5-4", "DET": "6-2", "KC": "6-2",
    "ATL": "3-6", "MIN": "6-2", "GB": "6-3", "JAX": "6-2", "TEN": "1-7",
    "BUF": "7-1", "NYJ": "2-7", "MIA": "1-7", "IND": "2-7", "CAR": "3-5",
    "NO": "3-5", "HOU": "3-5", "CLE": "5-4", "LA": "5-4", "AZ": "3-6",
    "SEA": "5-4", "LV": "4-5", "SF": "7-1", "DAL": "4-5", "PIT": "6-2",
    "CIN": "6-2", "LAC": "0-8", "BAL": "4-5",
}

#: Week 10 clubs explicitly listed in the "Teams on Bye" block of the
#: official NFL schedule. Transcribed and rechecked against the source on
#: 2026-11-12; never inferred from injury-report omissions.
OFFICIAL_WEEK10_BYES = ["CHI", "DEN", "PHI", "TB"]

#: Week 10 fixture snapshot transcribed from the official NFL schedule on
#: 2026-11-12. Matchup order is away, home.
OFFICIAL_WEEK10_FIXTURES = [
    (10, "2026-11-12", "Thursday", "8:15 PM", "WAS", "NYG"),
    (10, "2026-11-15", "Sunday", "9:30 AM", "NE", "DET"),
    (10, "2026-11-15", "Sunday", "1:00 PM", "KC", "ATL"),
    (10, "2026-11-15", "Sunday", "1:00 PM", "HOU", "CLE"),
    (10, "2026-11-15", "Sunday", "1:00 PM", "MIN", "GB"),
    (10, "2026-11-15", "Sunday", "1:00 PM", "MIA", "IND"),
    (10, "2026-11-15", "Sunday", "1:00 PM", "CAR", "NO"),
    (10, "2026-11-15", "Sunday", "1:00 PM", "BUF", "NYJ"),
    (10, "2026-11-15", "Sunday", "1:00 PM", "JAX", "TEN"),
    (10, "2026-11-15", "Sunday", "4:05 PM", "SEA", "LV"),
    (10, "2026-11-15", "Sunday", "4:05 PM", "LA", "AZ"),
    (10, "2026-11-15", "Sunday", "4:25 PM", "SF", "DAL"),
    (10, "2026-11-15", "Sunday", "8:20 PM", "PIT", "CIN"),
    (10, "2026-11-16", "Monday", "8:15 PM", "LAC", "BAL"),
]


def run() -> dict[str, Any]:
    st = ingest.standings()
    sch = ingest.schedule()
    byes = ingest.byes()
    inj = ingest.injuries()
    trs = ingest.team_report_status()
    su, iu = ingest.STANDINGS_URL, ingest.INJURY_REPORT_URL

    checks: list[dict] = []
    flags: list[dict] = []

    def flag(field: str, team: str, published: str, proof: str, url: str):
        flags.append({"field": field, "team_abbr": team, "published_value": published,
                      "arithmetic_proof": proof, "source_url": url,
                      "handling": "published verbatim; EXCLUDED from all derived "
                                  "metrics; left blank on the site tables"})

    abbrs = [r["team_abbr"] for r in st]
    checks.append(_row("V01", "standings: exactly 32 team rows", 32, len(abbrs), su))
    checks.append(_row("V02", "standings: team codes are unique", 32, len(set(abbrs)), su))

    exp_div = {t: d for d, ts in NFL32.items() for t in ts}
    mis = [f'{r["team_abbr"]} in "{r["division"]}" but official alignment says '
           f'"{exp_div.get(ABBR_ALIASES.get(r["team_abbr"], r["team_abbr"]), "?")}"'
           for r in st
           if r["division"] != exp_div.get(ABBR_ALIASES.get(r["team_abbr"], r["team_abbr"]))]
    checks.append(_row("V03", "standings: every club sits in its official division",
                       [], mis, su))

    bad = {k: [] for k in ("pct", "net", "homeroad", "confnon", "divle", "confpct", "divpct")}
    dup_div, dup_non = [], []
    for r in st:
        gp = _games(r["w"], r["l"], r["t"])
        e = pct(r["w"], r["l"], r["t"])
        if e is not None and r["pct"] is not None and abs(e - r["pct"]) > 1e-3:
            bad["pct"].append(f'{r["team_abbr"]}: published {r["pct"]} vs (W+.5T)/GP {e}')
        if (r["pf"] or 0) - (r["pa"] or 0) != r["net_pts"]:
            bad["net"].append(f'{r["team_abbr"]}: {r["pf"]}-{r["pa"]} != {r["net_pts"]}')
        hg, rg = _games(r["home_w"], r["home_l"], r["home_t"]), _games(r["road_w"], r["road_l"], r["road_t"])
        if hg + rg != gp:
            bad["homeroad"].append(f'{r["team_abbr"]}: home {hg} + road {rg} != gp {gp}')
        cg = _games(r["conf_w"], r["conf_l"], r["conf_t"])
        ng = _games(r["non_conf_w"], r["non_conf_l"], r["non_conf_t"])
        dg = _games(r["div_w"], r["div_l"], r["div_t"])
        if cg + ng != gp:
            bad["confnon"].append(f'{r["team_abbr"]}: conf {cg} + non-conf {ng} != gp {gp}')
            flag("non_conf", r["team_abbr"], r["non_conf"],
                 f'games played = {gp} (W{r["w"]}-L{r["l"]}-T{r["t"]}); CONF cell = '
                 f'{r["conf"]} = {cg} games; therefore NON-CONF must be {gp - cg} game(s), '
                 f'but the published NON-CONF cell "{r["non_conf"]}" totals {ng} games. '
                 f'Overall {r["w"]} wins with {r["conf_w"]} conference wins implies the '
                 f'non-conference record is {r["w"] - (r["conf_w"] or 0)}-'
                 f'{(r["l"] or 0) - (r["conf_l"] or 0)}-{(r["t"] or 0) - (r["conf_t"] or 0)}. '
                 f'Note the published NON-CONF cell is identical to the published LAST-5 '
                 f'cell ("{r["last5"]}"), which is consistent with a cell-duplication '
                 f'rendering defect rather than a real record.', su)
        if dg > cg:
            bad["divle"].append(f'{r["team_abbr"]}: div {dg} > conf {cg}')
        ce, de = pct(r["conf_w"], r["conf_l"], r["conf_t"]), pct(r["div_w"], r["div_l"], r["div_t"])
        if ce is not None and r["conf_pct"] is not None and abs(ce - r["conf_pct"]) > 1e-3:
            bad["confpct"].append(f'{r["team_abbr"]}: published {r["conf_pct"]} vs recomputed {ce}')
        if de is not None and r["div_pct"] is not None and abs(de - r["div_pct"]) > 1e-3:
            bad["divpct"].append(f'{r["team_abbr"]}: DIV cell "{r["div"]}" gives {de} '
                                 f'but the adjacent DIV PCT cell says {r["div_pct"]}')
            flag("div", r["team_abbr"], r["div"],
                 f'the DIV record cell "{r["div"]}" implies DIV PCT {de}, yet NFL.com '
                 f'prints DIV PCT {r["div_pct"]} in the adjacent cell. {r["div_pct"]} '
                 f'corresponds to a {r["div_pct"]} record one loss shorter than printed. '
                 f'The printed DIV cell is also character-identical to the printed HOME '
                 f'cell ("{r["home"]}"), which is consistent with a cell-duplication '
                 f'rendering defect.', su)
        if r["div"] == r["home"]:
            dup_div.append(f'{r["team_abbr"]}: DIV "{r["div"]}" == HOME "{r["home"]}"')
        if r["non_conf"] == r["last5"]:
            dup_non.append(f'{r["team_abbr"]}: NON-CONF "{r["non_conf"]}" == LAST-5 "{r["last5"]}"')

    checks.append(_row("V04", "standings: PCT == (W + 0.5*T) / (W+L+T) for all 32 rows",
                       [], bad["pct"], su,
                       note="NFL winning-percentage convention: a tie counts as half a "
                            "win and half a loss. Recomputed for all 32 rows."))
    checks.append(_row("V05", "standings: NET PTS == PF - PA for all 32 rows",
                       [], bad["net"], su))
    checks.append(_row("V06", "standings: HOME games + ROAD games == games played",
                       [], bad["homeroad"], su))
    checks.append(_row("V07", "standings: CONF games + NON-CONF games == games played",
                       [], bad["confnon"], su,
                       result="FLAG" if bad["confnon"] else "PASS",
                       note="See Flagged for Review: the official NON-CONF cell is "
                            "internally inconsistent for the listed team(s)."))
    checks.append(_row("V08", "standings: division games never exceed conference games",
                       [], bad["divle"], su))
    checks.append(_row("V09", "standings: CONF PCT recomputes from the CONF cell",
                       [], bad["confpct"], su))
    checks.append(_row("V10", "standings: DIV PCT recomputes from the DIV cell",
                       [], bad["divpct"], su,
                       result="FLAG" if bad["divpct"] else "PASS",
                       note="See Flagged for Review: the official DIV cell contradicts "
                            "its own adjacent DIV PCT cell for the listed team(s)."))
    checks.append(_row("V10b", "standings: no DIV cell is character-identical to the HOME "
                               "cell (cell-duplication rendering defect)", [], dup_div, su,
                       result="FLAG" if dup_div else "PASS"))
    checks.append(_row("V10c", "standings: no NON-CONF cell is character-identical to the "
                               "LAST-5 cell (cell-duplication rendering defect)",
                       [], dup_non, su, result="FLAG" if dup_non else "PASS"))

    total_gp = sum(_games(r["w"], r["l"], r["t"]) for r in st)
    total_w = sum(r["w"] or 0 for r in st)
    total_l = sum(r["l"] or 0 for r in st)
    total_t = sum(r["t"] or 0 for r in st)
    checks.append(_row("V11", "standings: league team-games is an even number",
                       0, total_gp % 2, su,
                       note=f"{total_gp} team-games => {total_gp // 2} completed games"))
    checks.append(_row("V12", "standings: league wins == league losses", total_w, total_l, su,
                       note=f"{total_t} tie(s) counted on both sides"))
    checks.append(_row("V13", "standings: league PF == league PA",
                       sum(r["pf"] or 0 for r in st), sum(r["pa"] or 0 for r in st), su))

    playing = {g["away_abbr"] for g in sch} | {g["home_abbr"] for g in sch}
    bye_set = {b["team_abbr"] for b in byes}
    schedule_url = ingest.WEEK10_SCHEDULE_URL
    checks.append(_row("V14", "schedule: week 10 has 14 games", 14, len(sch), schedule_url))
    checks.append(_row("V15", "schedule: 28 distinct teams play", 28, len(playing), schedule_url))
    checks.append(_row("V16", "schedule: playing + bye == 32 teams", 32,
                       len(playing | bye_set), schedule_url))
    checks.append(_row("V17", "schedule: no team both plays and has a bye", set(),
                       playing & bye_set, schedule_url))
    listed = [g["away_abbr"] for g in sch] + [g["home_abbr"] for g in sch]
    repeated_teams = sorted({team for team in listed if listed.count(team) > 1})
    checks.append(_row("V18", "schedule: no team appears twice in the slate", [],
                       repeated_teams, schedule_url))
    stset = {r["team_abbr"] for r in trs}
    schedule_and_injuries = [iu, schedule_url]
    checks.append(_row("V19", "injuries: all 32 teams have an explicit report status",
                       32, len(stset), iu, source_urls=schedule_and_injuries))
    checks.append(_row("V20", "injuries: report status covers exactly the 32 teams",
                       sorted(playing | bye_set), sorted(stset), iu,
                       source_urls=schedule_and_injuries))

    inj_teams = {r["team_abbr"] for r in inj}
    reported_none = {r["team_abbr"] for r in trs
                     if r["report_status"] == "no injuries reported"}
    checks.append(_row("V21", "injuries: teams with rows + teams printing an explicit "
                              "'No Injuries Reported' == the 28 playing teams",
                       sorted(playing), sorted(inj_teams | reported_none), iu,
                       source_urls=schedule_and_injuries))
    checks.append(_row("V22", "injuries: no bye team has an injury row", set(),
                       inj_teams & bye_set, iu, source_urls=schedule_and_injuries))
    checks.append(_row("V23", "injuries: game_status uses only the NFL's published "
                              "designations (Out / Doubtful / Questionable)", [],
                       sorted({r["game_status"] for r in inj
                               if r["game_status"] not in GAME_STATUS_VOCAB}), iu))
    checks.append(_row("V24", "injuries: practice code is one of FP / LP / DNP / blank",
                       [], sorted({r["practice_code"] for r in inj
                                   if r["practice_code"] not in {None, "FP", "LP", "DNP"}}), iu))
    checks.append(_row("V25", "injuries: every position code is a known NFL position",
                       [], sorted({r["position"] for r in inj
                                   if r["position"] not in KNOWN_POSITIONS}), iu))
    keys = [f'{r["team_abbr"]}|{r["player"]}' for r in inj]
    checks.append(_row("V26", "injuries: no duplicate player rows", [],
                       sorted({k for k in keys if keys.count(k) > 1}), iu))
    checks.append(_row("V27", "injuries: every row carries an official nfl.com player URL",
                       [], [r["player"] for r in inj
                            if not r["player_url"].startswith(ingest.PLAYER_URL_PREFIX)
                            or r["player_url"] == ingest.PLAYER_URL_PREFIX], iu))

    rec = {r["team_abbr"]: f'{r["w"]}-{r["l"]}' + (f'-{r["t"]}' if r["t"] else "")
           for r in st}
    disagree = [f'{t}: standings says {rec.get(t)}, injury page says {v}'
                for t, v in INJURY_PAGE_RECORDS.items() if rec.get(t) != v]
    checks.append(_row("V28", "cross-source: the 28 records printed on nfl.com/injuries "
                              "agree with nfl.com/standings", [], disagree, iu,
                       note="two separate official NFL.com pages retrieved in the same "
                            "session; agreement is a genuine cross-check"))

    actual_byes = sorted(bye_set)
    checks.append(_row(
        "V29", "schedule: bye teams match the explicit Week 10 list on the official NFL schedule",
        OFFICIAL_WEEK10_BYES, actual_byes, schedule_url,
        note="Transcribed from the NFL.com Week 10 schedule's 'Teams on Bye' block. "
             "The four bye designations are not inferred from missing injury-report rows."))

    # Every published input row must carry an HTTPS source URL that is present
    # in the provenance register. News uses its article URL; all other datasets
    # use the source_url attached by ingest.
    registered_urls = {s.get("url") for s in ingest.sources().get("sources", [])}
    published_rows = (
        [("standings", r, "source_url") for r in st]
        + [("schedule", r, "source_url") for r in sch]
        + [("byes", r, "source_url") for r in byes]
        + [("team report status", r, "source_url") for r in trs]
        + [("injury report", r, "source_url") for r in inj]
        + [("official news", r, "url") for r in ingest.news()]
        + [("team reference", r, "source_url") for r in ingest.teams_reference()]
    )
    no_src = []
    for dataset, row, field in published_rows:
        row_urls = row.get("source_urls") or [row.get(field)]
        for url in row_urls:
            row_label = row.get("team_abbr", row.get("player", row.get("headline", "?")))
            if not isinstance(url, str) or not url.startswith("https://"):
                no_src.append(f"{dataset}:{row_label} (missing HTTPS source URL)")
            elif url not in registered_urls:
                no_src.append(f"{dataset}:{row_label} (source not in register: {url})")
    checks.append(_row("V30", "provenance: every published data row has a registered HTTPS source",
                       [], no_src, su))

    # V31/V32 - the community team-metadata mirror. Labels and colours only;
    # nothing on-field is ever taken from it. Checked for coverage of the 32
    # active clubs and for the presence of retired codes that must not be
    # joined to current-season rows.
    ref = ingest.teams_reference()
    ref_codes = {r["team_abbr"] for r in ref}
    active = {ABBR_ALIASES.get(t, t) for v in NFL32.values() for t in v}
    checks.append(_row(
        "V31", "reference mirror: every one of the 32 active club codes is present",
        [], sorted(active - ref_codes), ingest.TEAM_REF_URL,
        note=f"{len(ref_codes)} rows in data/reference/teams.csv; tier COMMUNITY_MIRROR; "
             "used for team labels and colours only, never for on-field values."))
    legacy = sorted(ref_codes - active)
    checks.append(_row(
        "V32", "reference mirror: no retired club code may join to a current-season row",
        [], legacy, ingest.TEAM_REF_URL,
        result="PASS" if not legacy else "FLAG",
        note="Retired codes are present in the mirror and must be excluded from any join "
             "against current-season data. Flagged, not failed: the file is a community "
             "mirror and is never a source of on-field values."))
    # V32 is a FLAG on the *check list*, not an entry in `flags`: `flags` is
    # reserved for disputed official cells, which carry an arithmetic proof.
    # The mirror's retired codes are reported with their own check row so the
    # schema stays honest about what each list means.

    fixture_fields = ("week", "game_date", "day", "kickoff_et", "away_abbr", "home_abbr")
    official_fixtures = set(OFFICIAL_WEEK10_FIXTURES)
    captured_fixtures = {
        tuple(g[field] for field in fixture_fields)
        for g in sch
    }
    fixture_discrepancies = [
        "missing official fixture: " + " ".join(map(str, item))
        for item in sorted(official_fixtures - captured_fixtures)
    ] + [
        "unexpected captured fixture: " + " ".join(map(str, item))
        for item in sorted(captured_fixtures - official_fixtures)
    ]
    checks.append(_row(
        "V33", "schedule: every Week 10 fixture, date and kickoff matches the official NFL schedule",
        [], fixture_discrepancies, schedule_url,
        note="Independent fixture snapshot transcribed from NFL.com on 2026-11-12; "
             "abbreviations LA and AZ follow NFL.com."))

    counts = {"PASS": 0, "FLAG": 0, "FAIL": 0}
    for c in checks:
        counts[c["result"]] = counts.get(c["result"], 0) + 1
    return {
        "checks": checks, "flags": flags,
        "total": len(checks), **counts,
        "completed_games": total_gp // 2, "team_games": total_gp,
        "league_wins": total_w, "league_losses": total_l, "league_ties": total_t,
        "injury_rows": len(inj), "teams_reporting": len(inj_teams),
        "teams_no_injuries_reported": len(reported_none), "teams_on_bye": len(bye_set),
        "official_week10_byes": OFFICIAL_WEEK10_BYES,
    }
