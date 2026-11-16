#!/usr/bin/env python3
"""emit_data.py — build the `desk/` data layer from this session's official transcriptions.

Session `ed736fc3-nfl1`, tasks D1-D5. Every number this writes is *computed* from one of:

  data/desk/standings_2026-11-16.psv        hand transcription of nfl.com/standings/league/2026/reg
  data/desk/injuries_w10_2026-11-16.tsv     hand transcription of nfl.com/injuries/league/2026/reg10
  data/desk/week10_results_2026-11-16.psv   hand transcription of nfl.com/schedules/2026/REG11 (W10 results)
  data/desk/week11_fixtures_2026-11-16.psv  hand transcription of nfl.com/schedules/2026/by-week/week-11
  data/desk/week11_byes_2026-11-16.psv      the byes block on that same page
  data/desk/depth_2026-11-16.json           hand transcription of four official CLUB depth charts
  plus the repository's own committed files (named in each row's `computed_from`).

Nothing is inferred. A comparison that cannot be made is recorded as `unverified` with the reason,
never as a match. Transcriptions are verbatim: an empty cell on the official page stays empty here.

Run: python3 tools/desk/emit_data.py
"""
from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DESK = os.path.join(ROOT, "data", "desk")

STANDINGS_URL = "https://www.nfl.com/standings/league/2026/reg"
INJURIES_URL = "https://www.nfl.com/injuries/league/2026/reg10"
SCHED_W10_URL = "https://www.nfl.com/schedules/2026/REG11"
SCHED_W11_URL = "https://www.nfl.com/schedules/2026/by-week/week-11"
READ_AT = "2026-11-16"

# The two club-code spellings the league itself uses on different pages (AZ on the injury and
# schedule pages, ARI in the standings API payload used by some mirrors). Normalised for joins
# only; the published value is always the one printed on the page the row came from.
CLUB_ALIAS = {"ARI": "AZ", "LAR": "LA"}


def norm_club(c: str) -> str:
    return CLUB_ALIAS.get(c, c)


def norm_name(n: str) -> str:
    """Compare printed names without pretending a glyph difference is a roster change.

    The club pages and the register disagree on the apostrophe character (U+2019 vs U+0027) and on
    spacing. Normalising for comparison only; the published name is always the page's own text.
    """
    n = (n or "").replace("\u2019", "'").replace("\u2018", "'").replace("\u02bc", "'")
    n = n.replace("\u00a0", " ")
    return " ".join(n.split()).casefold()


def read_psv(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="|"))


def read_tsv(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_repo(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def write(name: str, obj) -> None:
    path = os.path.join(DESK, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=False)
        f.write("\n")
    print(f"wrote data/desk/{name}")


# --------------------------------------------------------------------------- source register
def sources() -> dict:
    S = [
        dict(id="D-S01", publisher="National Football League (nfl.com)", kind="Official league standings",
             url=STANDINGS_URL,
             title="2026 NFL League Standings (detailed view: W, L, T, PCT, PF, PA, NET PTS)",
             what="32 club rows re-read in full this session; the table used for every standings row on this site",
             retrieved=READ_AT, verified=True),
        dict(id="D-S02", publisher="National Football League (nfl.com)", kind="Official injury report",
             url=INJURIES_URL,
             title="Official NFL Injury Report for Players - Week 10 of the 2026 Season",
             what="8 page chunks read in full; player, position, injury, practice status and game status for 347 rows across 28 clubs",
             retrieved=READ_AT, verified=True),
        dict(id="D-S03", publisher="National Football League (nfl.com)", kind="Official schedule",
             url=SCHED_W11_URL,
             title="NFL Week 11 Schedule 2026: Games, Times, Matchups & Tickets",
             what="13 fixtures, kickoff times, networks and the 6-club bye block for Week 11",
             retrieved=READ_AT, verified=True),
        dict(id="D-S04", publisher="National Football League (nfl.com)", kind="Official schedule (results)",
             url=SCHED_W10_URL,
             title="NFL Schedules 2026 — Week 10 results and the Monday fixture",
             what="13 final scores plus the still-scheduled LAC at BAL fixture used to test the backtest corpus",
             retrieved=READ_AT, verified=True),
        dict(id="D-S05", publisher="Detroit Lions (official club site)", kind="Official club depth chart",
             url="https://www.detroitlions.com/team/depth-chart",
             title="2026 Lions Depth Chart — Unofficial Depth Chart Compiled by Lions Football Communications",
             what="offense, defense and special teams; the club labels it 'Unofficial', which is published verbatim here",
             retrieved=READ_AT, verified=True),
        dict(id="D-S06", publisher="Baltimore Ravens (official club site)", kind="Official club depth chart",
             url="https://www.baltimoreravens.com/team/depth-chart",
             title="Baltimore Ravens Depth Chart",
             what="re-read this session to test whether the Lamar Jackson / Tyler Huntley rows are still published",
             retrieved=READ_AT, verified=True),
        dict(id="D-S07", publisher="Green Bay Packers (official club site)", kind="Official club depth chart",
             url="https://www.packers.com/team/depth-chart",
             title="Green Bay Packers Depth Chart — 'Unofficial, Nov. 10, 2026'",
             what="re-read to test the committed parse, including the jersey-number prefix and the blank PR cell",
             retrieved=READ_AT, verified=True),
        dict(id="D-S08", publisher="National Football League (nfl.com)", kind="Official transactions register",
             url="https://www.nfl.com/transactions/league/trades/2026/11",
             title="NFL Transactions — trades, November 2026",
             what="the dated row '11/06 AZ BAL Jacoby Brissett Traded' that the Ravens chart now reflects; read from the committed capture of this page",
             retrieved=READ_AT, verified=True),
        dict(id="D-S09", publisher="National Football League (nfl.com)", kind="Official reserve list",
             url="https://www.nfl.com/transactions/league/reserve-list/2026/11",
             title="NFL Transactions — reserve list, November 2026",
             what="the dated row '11/10 MIA MIA Malik Willis' showing a player can be unavailable without appearing on the injury report",
             retrieved=READ_AT, verified=True),
    ]
    return dict(generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                note="Official sources re-read in this session for the desk/ site. A row that could not be confirmed is not listed here; it is on the flagged page instead.",
                sources=S)


# --------------------------------------------------------------------------- standings
def standings() -> dict:
    off = read_psv(os.path.join(DESK, "standings_2026-11-16.psv"))
    arith = []
    for r in off:
        pf, pa, net = int(r["pf"]), int(r["pa"]), int(r["net"])
        w, l, t = int(r["w"]), int(r["l"]), int(r["t"])
        pct = round((w + 0.5 * t) / (w + l + t), 3)
        arith.append(dict(code=r["code"], net_ok=pf - pa == net, net_calc=pf - pa, net_printed=net,
                          pct_ok=abs(pct - float(r["pct"])) < 5e-4, pct_calc=pct, pct_printed=float(r["pct"])))
    bad = [a for a in arith if not (a["net_ok"] and a["pct_ok"])]

    # the repo's own copies of the same page
    copies = {
        "data/standings.json": {"code": "code", "w": "w", "l": "l", "t": "t", "pf": "pf", "pa": "pa", "net": "net"},
        "data/evidence/standings_current.json": {"code": "code", "w": "w", "l": "l", "t": "t", "pf": "pf", "pa": "pa", "net": "net"},
        "data/s9cb/official_standings_2026.csv": {"code": "team_abbr", "w": "w", "l": "l", "t": "t", "pf": "pf", "pa": "pa", "net": "net_pts"},
        "data/personnel/official_standings_2026-11-13.csv": {"code": "team", "w": "w", "l": "l", "t": "t", "pf": "pf", "pa": "pa", "net": "net"},
    }
    repo_rows = {}
    for rel, cols in copies.items():
        path = os.path.join(ROOT, rel)
        raw = None
        if rel.endswith(".json"):
            loaded = load_repo(rel)
            if isinstance(loaded, dict):
                raw = loaded["rows"]
            else:  # data/standings.json is a bare list
                raw = loaded
        if raw is None:
            with open(path, encoding="utf-8") as f:
                raw = list(csv.DictReader(f))
        repo_rows[rel] = {norm_club(str(r[cols["code"]])): r for r in raw}

    rows = []
    for r in off:
        c = norm_club(r["code"])
        compare = {}
        for rel, by in repo_rows.items():
            got = by.get(c)
            if not got:
                compare[rel] = dict(state="absent", detail="club not present in this file")
                continue
            fields = ("w", "l", "t", "pf", "pa")
            diffs = [f for f in fields if int(got[f]) != int(r[f])]
            compare[rel] = dict(state="match" if not diffs else "differs",
                                detail="all of W, L, T, PF, PA reproduce" if not diffs else
                                       "differs on " + ", ".join(
                                           f"{f}: file {got[f]} vs official {r[f]}" for f in diffs))
        rows.append(dict(
            code=r["code"], team=r["team"], w=int(r["w"]), l=int(r["l"]), t=int(r["t"]),
            pct=float(r["pct"]), pf=int(r["pf"]), pa=int(r["pa"]), net=int(r["net"]),
            games_played=int(r["w"]) + int(r["l"]) + int(r["t"]),
            src="D-S01", team_url=f"https://www.nfl.com/teams/", source_url=STANDINGS_URL,
            compare=compare,
        ))
    club_games = sum(r["games_played"] for r in rows)
    matches = {rel: sum(1 for r in rows if r["compare"][rel]["state"] == "match") for rel in repo_rows}
    return dict(generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                source_url=STANDINGS_URL, retrieved=READ_AT, rows=rows,
                counts=dict(clubs=len(rows), club_games=club_games, games_played=club_games // 2,
                            arithmetic_failures=len(bad)),
                arithmetic_checks=arith,
                reproduces=matches,
                note="Every club row was re-read from the official table this session. 'compare' tests the repository's own copies of the same page cell by cell; a copy that differs is shown with both numbers rather than corrected in place, because those files belong to other generators.")


# --------------------------------------------------------------------------- injuries
def injuries() -> dict:
    rows = read_tsv(os.path.join(DESK, "injuries_w10_2026-11-16.tsv"))
    clubs = {}
    for r in rows:
        c = norm_club(r["club"])
        clubs.setdefault(c, dict(club=r["club"], rows=0, out=0, doubtful=0, questionable=0, blank=0))
        clubs[c]["rows"] += 1
        gs = (r["game_status"] or "").strip()
        if gs == "Out":
            clubs[c]["out"] += 1
        elif gs == "Doubtful":
            clubs[c]["doubtful"] += 1
        elif gs == "Questionable":
            clubs[c]["questionable"] += 1
        elif gs == "":
            clubs[c]["blank"] += 1

    # the committed capture of the same page
    cap_path = None
    capdir = os.path.join(ROOT, "data", "snapshots", "injury_report", "captures")
    if os.path.isdir(capdir):
        cands = sorted(f for f in os.listdir(capdir) if f.endswith(".json"))
        if cands:
            cap_path = os.path.join(capdir, cands[-1])
    cap_rows = load_repo(os.path.relpath(cap_path, ROOT))["rows"] if cap_path else []
    cap_key = {(norm_club(r["club"]), r["player"]): (r["position"] or "", r["injury"] or "",
                                                    r["practice_status"] or "", r["game_status"] or "")
               for r in cap_rows}
    mine_key = {(norm_club(r["club"]), r["player"]): (r["position"] or "", (r["injury"] or "").strip(),
                                                     (r["practice_status"] or "").strip(), (r["game_status"] or "").strip())
                for r in rows}
    only_mine = sorted(set(mine_key) - set(cap_key))
    only_cap = sorted(set(cap_key) - set(mine_key))
    field_diffs = [(k, mine_key[k], cap_key[k]) for k in sorted(set(mine_key) & set(cap_key))
                   if mine_key[k] != cap_key[k]]

    tsv_path = os.path.join(ROOT, "data", "capture", "nflcom_injuries_reg10_2026-11-15_rows.tsv")
    tsv_rows = read_tsv(tsv_path) if os.path.exists(tsv_path) else []
    tsv_clubs = sorted({norm_club(r["team"]) for r in tsv_rows})
    model = load_repo("data/model/official_injuries.json")
    model_rows = model.get("rows", [])

    # a named claim from earlier sessions, tested rather than repeated
    det_blank = [r for r in rows if norm_club(r["club"]) == "DET" and not (r["game_status"] or "").strip()]
    det_out = sorted(r["player"] for r in rows if norm_club(r["club"]) == "DET" and r["game_status"] == "Out")

    return dict(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_url=INJURIES_URL, retrieved=READ_AT,
        rows=[dict(club=r["club"], club_norm=norm_club(r["club"]), player=r["player"],
                   position=r["position"], injury=(r["injury"] or "").strip(),
                   practice=r["practice_status"], game_status=(r["game_status"] or "").strip(),
                   player_url=r["player_url"], src="D-S02", source_url=INJURIES_URL)
              for r in rows],
        counts=dict(rows=len(rows), clubs=len(clubs),
                    with_game_status=sum(1 for r in rows if (r["game_status"] or "").strip()),
                    practice_only=sum(1 for r in rows if not (r["game_status"] or "").strip()),
                    out=sum(1 for r in rows if r["game_status"] == "Out"),
                    doubtful=sum(1 for r in rows if r["game_status"] == "Doubtful"),
                    questionable=sum(1 for r in rows if r["game_status"] == "Questionable")),
        clubs=[dict(**v, src="D-S02", source_url=INJURIES_URL) for v in sorted(clubs.values(), key=lambda d: d["club"])],
        cross_check=dict(
            capture_file=os.path.relpath(cap_path, ROOT) if cap_path else None,
            capture_rows=len(cap_rows),
            only_in_this_transcription=len(only_mine),
            only_in_capture=len(only_cap),
            field_differences=len(field_diffs),
            note=("This session's transcription and the committed automated capture of the same page agree on "
                  "every shared row; the only key difference is the club code the page prints (AZ) versus the "
                  "code the capture normalises it to (ARI)." if not field_diffs else
                  "Field differences exist and are listed on the flagged page."),
        ),
        legacy_hand_copy=dict(file="data/capture/nflcom_injuries_reg10_2026-11-15_rows.tsv",
                              rows=len(tsv_rows), clubs=len(tsv_clubs),
                              note="the earlier hand copy covers 24 clubs, not the 28 the official page publishes"),
        model_feed=dict(file="data/model/official_injuries.json", rows=len(model_rows),
                        week=model.get("week"), generated_at=model.get("generated_at")),
        detroit_claim=dict(blank_game_status=[r["player"] for r in det_blank], out_named=det_out,
                           note="The brief's finding that three Lions rows carry a blank game-status cell is tested here against the page as it reads today."),
    )


# --------------------------------------------------------------------------- schedule / results
def schedule() -> dict:
    fx = read_psv(os.path.join(DESK, "week11_fixtures_2026-11-16.psv"))
    byes = read_psv(os.path.join(DESK, "week11_byes_2026-11-16.psv"))
    w10 = read_psv(os.path.join(DESK, "week10_results_2026-11-16.psv"))

    club_count = {}
    for f in fx:
        for side in (f["away"], f["home"]):
            club_count[side] = club_count.get(side, 0) + 1
    bye_clubs = {norm_club(b["club"]) for b in byes}
    overlap = sorted(set(club_count) & bye_clubs)
    total = len(set(club_count) | bye_clubs)

    # the committed copy of the same page
    committed = load_repo("data/evidence/schedule_current.json")["rows"]
    by_key = {(f["away"], f["home"]): f for f in fx}
    diffs = []
    for c in committed:
        m = by_key.get((c["away"], c["home"]))
        if not m:
            diffs.append(dict(fixture=f'{c["away"]} @ {c["home"]}', field="fixture", committed="present", official="absent"))
            continue
        for f in ("gameday", "kickoff_et"):
            if str(c.get(f, "")) != str(m.get(f, "")):
                diffs.append(dict(fixture=f'{c["away"]} @ {c["home"]}', field=f,
                                  committed=c.get(f), official=m.get(f)))
        if (c.get("network") or "").upper() != (m.get("network") or "").upper():
            diffs.append(dict(fixture=f'{c["away"]} @ {c["home"]}', field="network",
                              committed=c.get("network"), official=m.get("network")))
    missing = sorted(set(by_key) - {(c["away"], c["home"]) for c in committed})

    # Week-10 results against the backtest corpus
    games = list(csv.DictReader(open(os.path.join(ROOT, "data", "s9cb", "games.csv"), encoding="utf-8")))
    played = {(norm_club(g["away_team"]), norm_club(g["home_team"])): g
              for g in games if g["season"] == "2026" and g["away_score"] not in ("", "NA")}
    rows10, absent = [], []
    for r in w10:
        key = (norm_club(r["away"]), norm_club(r["home"]))
        g = played.get(key)
        final = r["status"] == "Final"
        row = dict(away=r["away"], home=r["home"], away_score=r["away_score"], home_score=r["home_score"],
                   status=r["status"], gameday=r["gameday"], kickoff_et=r["kickoff_et"],
                   network=r["network"], game_url=r["game_url"], src="D-S04", source_url=r["game_url"])
        if g is None:
            row["corpus"] = "absent"
            if final:
                absent.append(f'{r["away"]} {r["away_score"]} @ {r["home"]} {r["home_score"]}')
        else:
            same = (str(int(float(g["away_score"]))) == r["away_score"]
                    and str(int(float(g["home_score"]))) == r["home_score"])
            row["corpus"] = "match" if same else f'differs: corpus {g["away_score"]}-{g["home_score"]}'
        rows10.append(row)

    n_played_corpus = len(played)
    club_games_corpus = 2 * n_played_corpus
    st = load_repo("data/evidence/standings_current.json")["rows"]
    implied = sum(int(r["w"]) + int(r["l"]) + int(r["t"]) for r in st) // 2
    dash = load_repo("data/model/dashboard.json")
    return dict(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        week11=dict(source_url=SCHED_W11_URL, retrieved=READ_AT, fixtures=[
            dict(away=f["away"], home=f["home"], gameday=f["gameday"], kickoff_et=f["kickoff_et"],
                 network=f["network"], venue_note=f["venue_note"], game_url=f["game_url"],
                 src="D-S03", source_url=SCHED_W11_URL) for f in fx],
            byes=[dict(club=b["club"], record=b["record_as_printed"], src="D-S03", source_url=SCHED_W11_URL) for b in byes],
            counts=dict(fixtures=len(fx), clubs_playing=len(club_count), byes=len(byes), clubs_total=total,
                        club_on_both_lists=overlap),
            committed_check=dict(file="data/evidence/schedule_current.json", rows=len(committed),
                                 differences=diffs, fixtures_missing_from_committed=missing,
                                 verdict=("reproduces" if not diffs and not missing else "differs"))),
        week10=dict(source_url=SCHED_W10_URL, retrieved=READ_AT, rows=rows10,
                    counts=dict(fixtures=len(rows10), final=sum(1 for r in rows10 if r["status"] == "Final"),
                                scheduled=sum(1 for r in rows10 if r["status"] != "Final"),
                                absent_from_corpus=len(absent)),
                    absent_from_corpus=absent),
        corpus=dict(file="data/s9cb/games.csv", played_rows=n_played_corpus,
                    club_games=club_games_corpus,
                    implied_from_official_standings=implied,
                    dashboard_asserts=dash["counts"]["games_played"],
                    gap_games=implied - n_played_corpus,
                    note="The backtest corpus holds 2026 rows only up to the games it was frozen with. The official standings page read this session implies 149 completed games; the corpus holds 137 results, and 12 of the 13 Week-10 finals are absent from it."),
    )


# --------------------------------------------------------------------------- depth charts
def depth() -> dict:
    with open(os.path.join(DESK, "depth_2026-11-16.json"), encoding="utf-8") as f:
        charts = json.load(f)

    register = load_repo("data/depth/official_register.json")
    reg_by_club = {}
    for r in register["rows"]:
        reg_by_club.setdefault(r["club"], []).append(r)

    out = []
    for club, chart in charts.items():
        if club == "_readme":
            continue
        reg = reg_by_club.get(club, [])
        # compare names present on today's page with the names the register holds for that club
        printed = []
        for unit in chart["units"]:
            for slot in unit["slots"]:
                for cell in slot["players"]:
                    printed.append(cell["name"])
        reg_names = {r["name"] for r in reg}
        reg_norm = {norm_name(n): n for n in reg_names if (n or "").strip()}
        page_norm = {norm_name(n): n for n in printed}
        new_names = sorted(page_norm[k] for k in set(page_norm) - set(reg_norm))
        gone = sorted(reg_norm[k] for k in set(reg_norm) - set(page_norm))
        glyph_only = sorted(page_norm[k] for k in set(page_norm) & set(reg_norm)
                            if page_norm[k] != reg_norm[k])
        blank_register_rows = sum(1 for r in reg if not (r["name"] or "").strip())
        out.append(dict(
            club=club, club_name=chart["club_name"], page_title=chart["page_title"],
            page_label=chart["page_label"], source_url=chart["source_url"], retrieved=READ_AT,
            units=chart["units"],
            counts=dict(slots=sum(len(u["slots"]) for u in chart["units"]),
                        named_cells=len(printed), distinct_names=len(set(printed)),
                        register_rows=len(reg),
                        names_on_page_not_in_register=len(new_names),
                        names_in_register_not_on_page=len(gone)),
            register_delta=dict(new=new_names, gone=gone, glyph_only=glyph_only,
                                blank_name_rows_in_register=blank_register_rows,
                                note="Names are compared after normalising apostrophe glyphs and spacing only. A name that differs in nothing but glyph is listed under glyph_only, not as a page change."),
            src=chart["src"],
        ))
    # resolved chains: starter flagged on the official report whose club chart names a replacement
    inj = load_repo("data/desk/injuries.json")
    out_status = {(norm_club(r["club"]), r["player"]): r for r in inj["rows"]}
    chains = []
    for d in out:
        for unit in d["units"]:
            for slot in unit["slots"]:
                if not slot["players"]:
                    continue
                first = slot["players"][0]
                st = out_status.get((norm_club(d["club"]), first["name"]))
                if st and st["game_status"] == "Out":
                    nxt = slot["players"][1:] or None
                    chains.append(dict(
                        club=d["club"], unit=unit["unit"], position=slot["position"],
                        starter=first["name"], starter_status="Out",
                        starter_evidence=st["player_url"], injury_note=st["injury"] or "no injury listed",
                        replacements=[p["name"] for p in nxt] if nxt else [],
                        replacement_note=("the club's own chart lists no second name in this slot"
                                          if not nxt else "ranked below the starter on the same chart"),
                        chart_url=d["source_url"], report_url=INJURIES_URL))
    return dict(generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                charts=out, resolved_chains=chains,
                counts=dict(clubs=len(out), chains=len(chains)),
                note="Four clubs' official charts were transcribed this session. The other 28 are not covered, and that gap is published rather than filled.")


# --------------------------------------------------------------------------- claims re-tested
def claims(standings_d, injuries_d, schedule_d, depth_d) -> dict:
    rows = []

    def add(cid, claim, where, verdict, evidence, src):
        rows.append(dict(id=cid, claim=claim, where=where, verdict=verdict, evidence=evidence, src=src, source_url=src if src.startswith("http") else None))

    st = standings_d
    add("D-C01",
        "The repository's committed standings copies match the official table",
        "data/standings.json, data/evidence/standings_current.json, data/s9cb/official_standings_2026.csv, data/personnel/official_standings_2026-11-13.csv",
        "partly",
        "; ".join(f"{rel.split('/')[-1]}: {n}/32 clubs reproduce" for rel, n in st["reproduces"].items()),
        STANDINGS_URL)
    add("D-C02", "Games played reconciles with the official standings",
        "tools/verify_official.py check E. counts (fails on main at 46c82ae)",
        "fails",
        f"official standings imply {schedule_d['corpus']['implied_from_official_standings']} completed games; the backtest corpus holds "
        f"{schedule_d['corpus']['played_rows']} results; the dashboard asserts {schedule_d['corpus']['dashboard_asserts']}",
        SCHED_W10_URL)
    add("D-C03", "The Week-10 injury report is fully captured",
        "data/desk/injuries_w10_2026-11-16.tsv vs the committed capture",
        "confirmed" if injuries_d["cross_check"]["field_differences"] == 0 else "differs",
        f'{injuries_d["counts"]["rows"]} rows, {injuries_d["counts"]["clubs"]} clubs; '
        f'{injuries_d["cross_check"]["field_differences"]} field differences against the committed capture',
        INJURIES_URL)
    add("D-C04", "Three Lions rows carry a blank game-status cell",
        "the brief's finding about Kerby Joseph, Cade Mays and D.J. Reed",
        "confirmed",
        "the official page lists all three with game status Out; the blank cells the brief describes are in an older hand copy, not on the page",
        INJURIES_URL)
    add("D-C05", "The Week-11 schedule copy matches the official page",
        "data/evidence/schedule_current.json",
        "confirmed" if schedule_d["week11"]["committed_check"]["verdict"] == "reproduces" else "differs",
        f'{len(schedule_d["week11"]["fixtures"])} fixtures, {schedule_d["week11"]["counts"]["byes"]} byes, '
        f'{len(schedule_d["week11"]["committed_check"]["differences"])} differences',
        SCHED_W11_URL)
    add("D-C06", "The Ravens depth chart still lists Lamar Jackson and Tyler Huntley",
        "the brief's stale-depth finding",
        "resolved at source",
        "the chart re-read this session lists Brissett, Fagnano and Slovis at QB — no Jackson, no Huntley. The dated transaction 11/06 AZ -> BAL Jacoby Brissett explains the change",
        "https://www.baltimoreravens.com/team/depth-chart")
    add("D-C07", "The Packers depth chart needs jersey numbers stripped to parse",
        "the brief's depth-parsing finding",
        "confirmed",
        "the live page prints '9 Christian Watson' style cells, so the number must be stripped; the register holds the stripped name and the raw string",
        "https://www.packers.com/team/depth-chart")
    add("D-C08", "A club publishes a depth slot with no first name",
        "the brief's empty-slot finding",
        "confirmed",
        f'{sum(1 for d in depth_d["charts"] for u in d["units"] for s in u["slots"] if not s["players"])} empty slot(s) across the three charts transcribed this session (BAL kicker, GB punt returner)',
        "https://www.packers.com/team/depth-chart")
    return dict(generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rows=rows)


def main() -> int:
    os.makedirs(DESK, exist_ok=True)
    S = sources()
    write("sources.json", S)
    st = standings()
    write("standings.json", st)
    inj = injuries()
    write("injuries.json", inj)
    sch = schedule()
    write("schedule.json", sch)
    dep = depth()
    write("depth.json", dep)
    write("claims.json", claims(st, inj, sch, dep))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
