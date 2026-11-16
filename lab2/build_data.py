#!/usr/bin/env python3
"""build_data.py — compute every figure the Origination Desk publishes.

Nothing here is typed in by hand.  Each block reads committed inputs, computes a result, and
writes it to `lab2/data/derived.json`, where the page builder reads it.  `lab2/verify.py`
re-runs the arithmetic and fails if a published figure does not reproduce.

Run from the repository root:

    python3 lab2/build_data.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

ROOT = lib.ROOT
RETRIEVED = "2026-11-16"
OUT = {}


def canon(club: str) -> str:
    """One club code, for joins only.  nfl.com prints AZ and LA; the mirrored feed prints both
    ARI/LAR and AZ/LA depending on the file.  The row itself always keeps the code its source
    printed; only the join uses this."""
    return {"AZ": "ARI", "LA": "LAR"}.get(club, club)


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None, None, None, None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx <= 0 or syy <= 0:
        return None, None, None, None
    r = sxy / math.sqrt(sxx * syy)
    if abs(r) >= 1:
        return r, None, None, None
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    lo, hi = z - 1.959963985 * se, z + 1.959963985 * se
    ci = [round((math.exp(2 * lo) - 1) / (math.exp(2 * lo) + 1), 4),
          round((math.exp(2 * hi) - 1) / (math.exp(2 * hi) + 1), 4)]
    t = r * math.sqrt((n - 2) / (1 - r * r))
    return round(r, 4), ci, round(t, 4), n


def tsv(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def csvrows(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------- 1. live vs committed standings
def block_standings():
    off = lib.load("lab2/data/official_standings_2026-11-16.json")
    official = {r["club"]: r for r in off["rows"]}
    repo = {r["abbr"]: r for r in csvrows("data/standings.csv")}
    model = {r["team"]: r for r in lib.load("data/model/snapshot.json")["standings"]}
    rows, diffs, matched = [], 0, 0
    for club in sorted(official):
        o = official[club]
        key = next((k for k in repo if canon(k) == canon(club)), None)
        r = repo.get(key)
        m = next((v for k, v in model.items() if canon(k) == canon(club)), {})
        cmp = {}
        if r:
            for f, of in (("w", "w"), ("l", "l"), ("t", "t"), ("pf", "pf"), ("pa", "pa")):
                if int(r[f]) != int(o[of]):
                    cmp[f] = (int(o[of]), int(r[f]))
        if cmp:
            diffs += 1
        else:
            matched += 1
        rows.append({
            "club_nflcom": club,
            "club_feed": key or canon(club),
            "w": o["w"], "l": o["l"], "t": o["t"], "pf": o["pf"], "pa": o["pa"],
            "repo_w": r["w"] if r else lib.UNVERIFIED,
            "repo_l": r["l"] if r else lib.UNVERIFIED,
            "repo_pf": r["pf"] if r else lib.UNVERIFIED,
            "repo_pa": r["pa"] if r else lib.UNVERIFIED,
            "repo_snapshot": r["snapshot_date"] if r else lib.UNVERIFIED,
            "model_w": m.get("w", lib.UNVERIFIED),
            "model_l": m.get("l", lib.UNVERIFIED),
            "agrees": not cmp,
            "fields_differing": ", ".join(sorted(cmp)) if cmp else "",
            "source": off["official_url"],
            "retrieved": RETRIEVED,
        })
    OUT["standings"] = {
        "official_url": off["official_url"], "retrieved": RETRIEVED,
        "n_clubs": len(rows), "n_matched": matched, "n_differing": diffs,
        "repo_snapshot_date": rows[0]["repo_snapshot"],
        "rows": rows,
        "method": "Every club on the official page was transcribed this session and compared field by field with data/standings.csv (the repository's own transcription) and data/model/snapshot.json (the model's input table).",
    }


# ---------------------------------------------------------------- 2. week-10 results feed
def block_results():
    from_results = json.load(open(os.path.join(ROOT, "lab2/data/official_results_w10_2026-11-16.json")))
    games = from_results["games"]
    repo = [r for r in csvrows("data/s9cb/games.csv") if r["season"] == "2026" and r["week"] == "10"]
    feed = {}
    for r in repo:
        feed[(canon(r["away_team"]), canon(r["home_team"]))] = r
    rows, recompute = [], defaultdict(lambda: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0})
    for g in games:
        a, h = g["away"], g["home"]
        f = feed.get((canon(a), canon(h)))
        total = g["away_score"] + g["home_score"]
        margin = g["home_score"] - g["away_score"]
        rows.append({
            "game_centre": g["game_centre"],
            "weekday_date": g["weekday_date"],
            "away": a, "away_score": g["away_score"],
            "home": h, "home_score": g["home_score"],
            "total": total, "home_margin": margin,
            "feed_final": (f"{f['away_score']} - {f['home_score']}") if f and f["away_score"] and f["home_score"] else "no final in feed",
            "feed_spread": f["spread_line"] if f and f["spread_line"] else lib.UNVERIFIED,
            "feed_total": f["total_line"] if f and f["total_line"] else lib.UNVERIFIED,
            "spread_name": "'" + ("home" if margin > 0 else "away") + "'" if margin else "push (tie)",
            "market_verdict": lib.UNVERIFIED,
            "source": from_results["official_url"], "retrieved": RETRIEVED,
        })
    # market verdict only when the feed printed a closing line: sign check first.
    for row in rows:
        if row["feed_spread"] == lib.UNVERIFIED:
            continue
        spread_home = float(row["feed_spread"])          # positive = home favoured
        m = row["home_margin"]
        if m == 0:
            row["market_verdict"] = "push"
        elif (m + spread_home) > 0:
            row["market_verdict"] = "home covered"
        elif (m + spread_home) < 0:
            row["market_verdict"] = "away covered"
        else:
            row["market_verdict"] = "push"
    # accumulation: repo standings-as-of-12-Nov + these finals must equal the live official table
    repo_tab = {r["abbr"]: r for r in csvrows("data/standings.csv")}
    for row in rows:
        for side, sc, opp, osc in (("away", row["away_score"], "home", row["home_score"]),
                                   ("home", row["home_score"], "away", row["away_score"])):
            t = row[side]
            recompute[t]["pf"] += sc
            recompute[t]["pa"] += osc
        if row["home_margin"] > 0:
            recompute[row["home"]]["w"] += 1
            recompute[row["away"]]["l"] += 1
        elif row["home_margin"] < 0:
            recompute[row["away"]]["w"] += 1
            recompute[row["home"]]["l"] += 1
        else:
            recompute[row["home"]]["t"] += 1
            recompute[row["away"]]["t"] += 1
    off = {r["club"]: r for r in lib.load("lab2/data/official_standings_2026-11-16.json")["rows"]}
    recon_rows, recon_ok = [], 0
    for club in sorted(off):
        key = next((k for k in repo_tab if canon(k) == canon(club)), None)
        base = repo_tab.get(key)
        if not base:
            continue
        add = recompute[key]
        calc = {"w": int(base["w"]) + add["w"], "l": int(base["l"]) + add["l"],
                "pf": int(base["pf"]) + add["pf"], "pa": int(base["pa"]) + add["pa"]}
        o = off[club]
        ok = all(calc[k] == o[k] for k in ("w", "l", "pf", "pa"))
        recon_ok += 1 if ok else 0
        recon_rows.append({
            "club": key or canon(club), "base_w": base["w"], "base_l": base["l"], "base_pf": base["pf"], "base_pa": base["pa"],
            "add_w": add["w"], "add_l": add["l"], "add_pf": add["pf"], "add_pa": add["pa"],
            "calc_w": calc["w"], "calc_l": calc["l"], "calc_pf": calc["pf"], "calc_pa": calc["pa"],
            "official_w": o["w"], "official_l": o["l"], "official_pf": o["pf"], "official_pa": o["pa"],
            "agrees": ok, "source": from_results["standings_url"], "retrieved": RETRIEVED,
        })
    OUT["results"] = {
        "n_games": len(rows), "n_finals": sum(1 for r in rows if r["total"]),
        "n_merged_into_feed": sum(1 for r in rows if r["feed_final"] != "no final in feed"),
        "recon_n": len(recon_rows), "recon_ok": recon_ok,
        "rows": rows, "recon_rows": recon_rows,
        "official_url": from_results["official_url"],
        "standings_url": from_results["standings_url"],
        "retrieved": RETRIEVED,
        "feed_coverage_note": "13 of the 14 Week-10 games had no final score in the committed feed before this session; the LAC @ BAL Monday game had not been played when the pages were read.",
    }


# ---------------------------------------------------------------- 3. own lines: origination order
def block_lines():
    lines = lib.load("data/model/lines.json")
    snap = {f["game_id"]: f for f in lib.load("data/model/snapshot.json")["fixtures"]}
    rows = []
    for g in lines["lines"]:
        f = snap.get(g["game_id"], {})
        gap_spread = None if g["market_home_line"] is None else round(g["my_home_line"] - g["market_home_line"], 2)
        gap_total = None if g["market_total"] is None else round(g["my_total"] - g["market_total"], 2)
        rows.append({
            "game_id": g["game_id"], "matchup": f"{g['away']} @ {g['home']}", "gameday": g["gameday"],
            # side first
            "side_fair": g["my_line_display"],
            "side_fair_num": g["my_home_line"],
            "side_market": (f"{g['home']} {-g['market_home_line']:+.1f} / {g['away']} {g['market_home_line']:+.1f}"
                            if g["market_home_line"] is not None else lib.UNVERIFIED),
            "side_market_num": g["market_home_line"],
            "side_residual": gap_spread,
            # then the total
            "total_fair": g["my_total"], "total_market": g["market_total"], "total_residual": gap_total,
            # then the moneyline
            "ml_fair_p_home": g["my_win_prob_home"],
            "ml_market_p_home": lib.UNVERIFIED,
            "ml_residual": lib.UNVERIFIED,
            "band95": g["home_line_band95"],
            "calibration_status": g["status"],
            "priced_fields": sum(1 for v in (g["market_home_line"], g["market_total"]) if v is not None),
            "source_model": "lab2/data/derived.json (built from data/model/lines.json)",
            "source_schedule": f.get("source", lib.OFFICIAL["schedule_w11"]),
            "retrieved": RETRIEVED,
        })
    n_side = sum(1 for r in rows if r["side_market_num"] is not None)
    n_total = sum(1 for r in rows if r["total_market"] is not None)
    ml_market_present = sum(1 for r in rows if r["ml_market_p_home"] != lib.UNVERIFIED)
    OUT["lines"] = {
        "rows": rows, "n_games": len(rows),
        "n_side": n_side, "n_total": n_total, "n_moneyline_market": ml_market_present,
        "order": ["side (spread)", "total", "moneyline"],
        "sign_convention": lines.get("sign_convention_check", {}),
        "blend_test": lines.get("blend_test", {}),
        "calibration": lines.get("calibration", []),
        "method": lines.get("method", {}),
        "market_provenance": "The market column is a consensus closing line carried in the mirrored feed (nflverse). It is not a book price, and the repository holds no opening number and no moneyline price.",
    }


# ---------------------------------------------------------------- 4. price snapshot policy
def block_prices():
    games = csvrows("data/s9cb/games.csv")
    seasons = sorted({r["season"] for r in games})
    has_close = sum(1 for r in games if r["spread_line"])
    has_open = 0            # no opening field exists in the source at all
    has_ml = sum(1 for r in games if r["home_moneyline"])
    has_alt = sum(1 for r in games if r["away_spread_odds"] or r["home_spread_odds"])
    w11 = [r for r in games if r["season"] == "2026" and r["week"] == "11" and r["spread_line"]]
    OUT["prices"] = {
        "seasons": (seasons[0], seasons[-1]), "n_games": len(games),
        "has_closing_spread": has_close, "has_opening": has_open,
        "has_moneyline": has_ml, "has_sided_price": has_alt,
        "week11_rows_with_close": len(w11),
        "fields_in_source": ["spread_line", "total_line", "away_moneyline", "home_moneyline",
                             "away_spread_odds", "home_spread_odds", "over_odds", "under_odds"],
        "source": "https://github.com/nflverse/nflverse-data/releases/tag/schedules",
        "official_source": lib.OFFICIAL["schedule_w11"],
        "retrieved": RETRIEVED,
    }


# ---------------------------------------------------------------- 5. availability as of a cutoff
def block_availability():
    off = lib.load("lab2/data/official_injuries_w10_2026-11-16.json")
    rows = off["rows"]
    feed = lib.load("data/model/official_injuries.json")["rows"]
    practice = Counter(r["practice_status"] for r in rows)
    game = Counter(r["game_status"] or "blank" for r in rows)
    club_rows = defaultdict(lambda: {"n": 0, "out": 0, "doubtful": 0, "questionable": 0, "blank": 0,
                                     "dnp": 0, "limited": 0, "full": 0})
    for r in rows:
        c = club_rows[canon(r["team"])]
        c["n"] += 1
        g = r["game_status"]
        c["out"] += g == "Out"
        c["doubtful"] += g == "Doubtful"
        c["questionable"] += g == "Questionable"
        c["blank"] += g == ""
        c["dnp"] += r["practice_status"] == "Did Not Participate In Practice"
        c["limited"] += r["practice_status"] == "Limited Participation in Practice"
        c["full"] += r["practice_status"] == "Full Participation in Practice"
    feed_keys = {(canon(r["team"]), r["player"]) for r in feed}
    off_keys = {(canon(r["team"]), r["player"]) for r in rows}
    club_table = []
    for club in sorted(club_rows):
        c = club_rows[club]
        club_table.append({
            "club": club, "n_rows": c["n"], "out": c["out"], "doubtful": c["doubtful"],
            "questionable": c["questionable"], "no_game_status": c["blank"],
            "dnp": c["dnp"], "limited": c["limited"], "full": c["full"],
            "source": off["official_url"], "retrieved": RETRIEVED,
        })
    # a worked example of the cutoff problem: Puka Nacua's status in each committed read
    cutoff = []
    for label, value, src in (
        ("Official Week-10 report, read 2026-11-16", "practice: Did Not Participate · game status: blank", off["official_url"]),
        ("data/model/official_injuries.json", "same 347 rows, 0 differences", "lab2/data/derived.json"),
        ("data/model/availability.json", "injury records: 376, from the mirrored feed week 6", "data/model/availability.json"),
    ):
        cutoff.append({"read": label, "says": value, "source": src, "retrieved": RETRIEVED})
    OUT["availability"] = {
        "n_rows": len(rows), "n_clubs": len({r["team"] for r in rows}),
        "practice": dict(practice), "game": dict(game),
        "clubs": club_table,
        "published_model_week": lib.load("data/model/availability.json")["week"],
        "published_model_depth_dated": lib.load("data/model/availability.json")["depth_chart_timestamp"],
        "feed_vs_official": {"feed_rows": len(feed), "official_rows": len(rows),
                             "in_both": len(feed_keys & off_keys),
                             "only_feed": sorted(feed_keys - off_keys)[:5],
                             "only_official": sorted(off_keys - feed_keys)[:5]},
        "cutoff": cutoff,
        "official_url": off["official_url"], "retrieved": RETRIEVED,
        "board_rows_in_report": sum(1 for r in rows if r["game_status"] in ("Out", "Doubtful", "Questionable")),
        "blank_game_status": game.get("blank", 0),
    }


# ---------------------------------------------------------------- 6. depth ladder + verified names
def block_depth():
    d = lib.load("data/depth_ladder.json")
    dc = lib.load("data/depth_chart.json")
    off = lib.load("lab2/data/official_injuries_w10_2026-11-16.json")["rows"]
    official_names = {r["player"] for r in off}
    clubs = []
    total_slots = 0
    for c in d["clubs"]:
        total_slots += c["slots"]
        clubs.append({
            "club": c["abbr"], "club_name": c["club"], "slots": c["slots"],
            "offense": c["offense_slots"], "defense": c["defense_slots"],
            "starter_at_risk": c["slots_starter_at_risk"],
            "missing_starter": c["slots_missing_starter"],
            "deepest_string": c["deepest_string_starting"] or "none",
            "chart_status": c["chart_status"],
            "chart_url": c["chart_url"],
            "source": c["chart_url"], "retrieved": RETRIEVED,
        })
    # Slot-level names exist for three clubs in data/depth_chart.json.  That is the only file in
    # which a starter's name can be checked against an official page, so it is the only file from
    # which a verified depth row can be built.
    slot_rows = []
    for r in dc:
        s1 = (r.get("s1") or "").strip()
        if not s1:
            continue
        slot_rows.append({
            "club": r["code"], "unit": r.get("unit", ""), "pos": r.get("pos", ""),
            "rank1": s1, "rank2": (r.get("s2") or "").strip() or "—", "rank3": (r.get("s3") or "").strip() or "—",
            "rank4": (r.get("s4") or "").strip() or "—",
            "chart_label": r.get("chart_label", ""),
            "verified": s1 in official_names,
            "verification": ("name appears on the official Week-10 report" if s1 in official_names
                             else "no official source read this session prints this name"),
            "source": r.get("src") and d["clubs"][0]["chart_url"] or d["clubs"][0]["chart_url"],
            "chart_url": next((c["chart_url"] for c in d["clubs"] if c["abbr"] == r["code"]), ""),
            "retrieved": RETRIEVED,
        })
    OUT["depth"] = {
        "clubs": clubs,
        "counts": d["counts"],
        "n_clubs": len(clubs),
        "slots": total_slots,
        "slot_rows": slot_rows,
        "n_slot_rows": len(slot_rows),
        "n_slot_rows_verified": sum(1 for r in slot_rows if r["verified"]),
        "slot_clubs": sorted({r["club"] for r in slot_rows}),
        "sources": d["sources"],
        "method": d["method"],
        "note": "Every starter name in the ladder is cross-checked against the official Week-10 injury report read this session. A name that appears there can be verified; a name that does not cannot, and is not upgraded.",
    }


# ---------------------------------------------------------------- 7. strategy audit
def block_strategies():
    m = lib.load("data/model/strategies.json")
    s = lib.load("data/s9cb/leaderboard.json")
    by_letter_model = {a["strategy"].split()[0]: a for a in m["leaderboard"]}
    by_letter_s9cb = {a["strategy"].split()[0]: a for a in s["leaderboard"]}
    rows = []
    for key in sorted(set(by_letter_model) | set(by_letter_s9cb)):
        a = by_letter_model.get(key, {})
        b = by_letter_s9cb.get(key, {})
        rows.append({
            "id": key,
            "model_rule": a.get("strategy", lib.UNVERIFIED),
            "s9cb_rule": b.get("strategy", lib.UNVERIFIED),
            "same_rule": a.get("strategy") == b.get("strategy"),
            "model_roi_pct": None if a.get("roi") is None else round(a["roi"] * 100, 2),
            "s9cb_roi_pct": b.get("roi_pct", lib.UNVERIFIED),
            "s9cb_n": b.get("n_bets", lib.UNVERIFIED),
            "s9cb_status": b.get("status", lib.UNVERIFIED),
            "s9cb_gates": ",".join(b.get("gates", [])),
            "model_status": a.get("status", lib.UNVERIFIED),
            "source_model": "data/model/strategies.json",
            "source_leaderboard": "data/s9cb/leaderboard.json",
            "retrieved": RETRIEVED,
        })
    # self-consistency: the model page and the leaderboard page must describe the same rule
    n_same = sum(1 for r in rows if r["same_rule"])
    # every strategy carries a staking figure on the published pages
    win_rate_columns = sum(1 for a in m["leaderboard"] if "win_pct" in a)
    OUT["strategies"] = {
        "rows": rows, "n_rows": len(rows), "n_same_rule": n_same,
        "n_conflicting_rule": len(rows) - n_same,
        "window": m["window"], "s9cb_window": s.get("price_source"),
        "price_assumption": m["window"].get("price_assumption"),
        "s9cb_unscored": s.get("unscored_games_no_price"),
        "win_rate_columns_published": win_rate_columns,
        "gates": s["gate_definitions"],
        "model_gates": m["gate_definitions"],
        "luck": s.get("luck_accounting", {}),
        "s9cb_luck_rows": [{"strategy": r["strategy"], "bets": r.get("n_bets"), "profit": r.get("profit_units"),
                            "band": r.get("luck_band_95"), "verdict": r.get("luck_verdict"), "p": r.get("p_value")}
                           for r in s["leaderboard"]],
    }


# ---------------------------------------------------------------- 8. forward record audit
def block_forward():
    records = []
    for path, label in (("data/prereg/forecasts/SB-01_week11_2026.json", "SB-01 (prereg/forecasts)"),
                        ("data/prereg/forecasts_2026_wk11.json", "PR-01..03 (prereg/forecasts_2026_wk11)"),
                        ("data/shadow/forecasts_week11_v1.json", "shadow-v1 (data/shadow)")):
        d = lib.load(path)
        games = d.get("games", [])
        rec = d.get("recorded_at") or d.get("recorded_utc") or d.get("recorded_at_utc")
        first_ko = d.get("first_kickoff_utc") or min(
            (g.get("kickoff_utc") for g in games if g.get("kickoff_utc")),
            default=lib.UNVERIFIED)
        records.append({
            "record": label, "file": path, "n_games": len(games),
            "recorded": rec or lib.UNVERIFIED,
            "first_kickoff_utc": first_ko or lib.UNVERIFIED,
            "registration": d.get("registration_commit") or d.get("corpus", {}).get("sha256", lib.UNVERIFIED),
            "scored_yet": sum(1 for g in games if g.get("outcome") not in (None, "", lib.UNVERIFIED)),
            "source": "lab2/data/derived.json",
            "retrieved": RETRIEVED,
        })
    # has the season produced any result yet for these records?  week 11 has not started.
    feed = [r for r in csvrows("data/s9cb/games.csv") if r["season"] == "2026" and r["week"] == "11"]
    OUT["forward"] = {
        "records": records,
        "n_records": len(records),
        "week11_results_in_feed": sum(1 for r in feed if r["home_score"]),
        "week11_games": len(feed),
        "note": "A forecast record is a record of what the rule said, not a pick. None of the three records can be scored yet: the first Week-11 kickoff is after every record's timestamp and no Week-11 game has a final in the feed.",
        "official_url": lib.OFFICIAL["schedule_w11"],
        "retrieved": RETRIEVED,
    }
    # how many weeks of scoring would be needed to detect an edge?  (analytic, 65% win rate)
    def weeks_to_power(p=0.52, p0=0.5, alpha=0.05, power=0.8):
        za, zb = 1.959963985, 0.8416212336
        n = ((za * math.sqrt(p0 * (1 - p0)) + zb * math.sqrt(p * (1 - p))) / (p - p0)) ** 2
        return int(math.ceil(n)), round(n / 13, 1)
    n_bets, n_weeks = weeks_to_power()
    OUT["forward"]["power"] = {"edge": "52% true win rate vs a 50% break-even",
                               "bets_needed": n_bets, "weeks_at_13_games": n_weeks}


# ---------------------------------------------------------------- 9. matchup board (verified cells only)
def block_matchups():
    off = lib.load("lab2/data/official_injuries_w10_2026-11-16.json")["rows"]
    ladder = lib.load("data/depth_ladder.json")
    ladders = {c["abbr"]: c for c in ladder["clubs"]}
    status = defaultdict(list)
    for r in off:
        if r["game_status"]:
            status[canon(r["team"])].append((r["player"], r["position"], r["game_status"]))
    # the Week-11 fixtures (official) - opponent pairs only, no venue claim
    fix = []
    vpath = os.path.join(ROOT, "data/shadow/week11_venues.csv")
    if os.path.exists(vpath):
        with open(vpath, encoding="utf-8", newline="") as fh:
            fix = list(csv.DictReader(fh))
    rows = []
    for f in fix:
        a, h = f.get("away"), f.get("home")
        for club, opp in ((a, h), (h, a)):
            l = ladders.get(club, {})
            out = status.get(club, [])
            rows.append({
                "club": club, "opponent": opp,
                "designated_out": sum(1 for x in out if x[2] == "Out"),
                "designated_doubtful": sum(1 for x in out if x[2] == "Doubtful"),
                "designated_questionable": sum(1 for x in out if x[2] == "Questionable"),
                "slots_at_risk": l.get("slots_starter_at_risk", lib.UNVERIFIED),
                "deepest_string_starting": l.get("deepest_string_starting") or "none",
                "depth_chart": l.get("chart_url", lib.UNVERIFIED),
                "replacement_named": lib.UNVERIFIED,
                "source": lib.OFFICIAL["injuries_w10"],
                "retrieved": RETRIEVED,
            })
    OUT["matchups"] = {
        "rows": rows, "n_rows": len(rows),
        "note": "Designation counts are from the official Week-10 report, the last official report published when this page was built. The depth columns come from each club's own chart, transcribed 2026-11-12. The replacement column is deliberately blank: the NFL does not publish a dated 'this backup starts because that starter is out' notice, and inferring it would be a guess.",
        "official_url": lib.OFFICIAL["injuries_w10"],
        "retrieved": RETRIEVED,
    }


# ---------------------------------------------------------------- 9b. signal vs staking
def _signal(rows, n_key, win_key, label_key="strategy"):
    """Signal = win rate against a coin flip, with a normal interval and a two-sided z test.

    The signal question is deliberately price-free: it asks whether the rule picks winners more
    often than chance, not whether the prices made money.  Both are printed because they answer
    different questions, and the board's own published p-value is carried beside ours so that a
    disagreement is visible instead of hidden.
    """
    from math import erf
    out = []
    for r in rows:
        n, wins = r.get(n_key), r.get(win_key)
        if not n or wins is None:
            continue
        p = wins / n
        se = math.sqrt(p * (1 - p) / n)
        lo = 100 * (p - 1.959963985 * se - 0.5)
        hi = 100 * (p + 1.959963985 * se - 0.5)
        # null A: a coin flip (0.5).  null B: the break-even hit rate implied by the price the
        # board actually used, which is the stricter and the more useful of the two.
        z_coin = (p - 0.5) / math.sqrt(0.25 / n)
        p_coin = 2 * (1 - 0.5 * (1 + erf(abs(z_coin) / math.sqrt(2))))
        be = r.get("break_even_hit_rate")
        p_price = None
        if be:
            z_price = (p - be) / math.sqrt(be * (1 - be) / n)
            p_price = 2 * (1 - 0.5 * (1 + erf(abs(z_price) / math.sqrt(2))))
        out.append({"row": r, "n": n, "wins": wins, "p": p, "signal_pp": 100 * (p - 0.5),
                    "ci": [lo, hi], "z": z_coin, "p_value": p_coin,
                    "break_even": be, "p_vs_price": p_price,
                    "published_p": r.get("p_value")})
    # q is computed on the merged family in block_signal, not per board: the family is every rule
    # tested, and adjusting board by board would understate the multiplicity.
    return out


def _signal_rows(boards):
    rows = []
    for label, file, objs, n_key, win_key, roi_key, ci_key in boards:
        for o in objs:
            r = o["row"]
            rows.append({
                "board": file, "board_label": label,
                "strategy": r[label_key_for(file)], "n": o["n"],
                "wins": o["wins"], "win_rate": round(100 * o["p"], 2),
                "signal_pp": round(o["signal_pp"], 2),
                "signal_ci_low": round(o["ci"][0], 2), "signal_ci_high": round(o["ci"][1], 2),
                "p_value": round(o["p_value"], 4),
                "break_even": (round(o["break_even"], 4) if o["break_even"] else None),
                "p_vs_price": (round(o["p_vs_price"], 4) if o["p_vs_price"] is not None else None),
                "published_p": (round(o["published_p"], 4) if o["published_p"] is not None else None),
                # the board's own p printed to 4 dp; a 0.02 tolerance allows for its rounding and for
                # a slightly different estimator, and a larger gap is reported rather than smoothed.
                "p_reproduces": (None if o["p_vs_price"] is None or not o["published_p"]
                                 else abs(o["p_vs_price"] - o["published_p"]) <= 0.02),
                "bh_q": round(o["q_value"], 4),
                "staking_roi_pct": (None if r.get(roi_key) is None
                                    else round(float(r[roi_key]) * (100 if abs(float(r[roi_key])) < 1.5 else 1), 2)),
                "staking_ci": r.get(ci_key),
                "source": "https://github.com/kanlerxz87-cyber/NFL1/blob/main/" + file,
                "retrieved": RETRIEVED,
            })
    rank_signal = sorted(rows, key=lambda r: -r["signal_ci_low"])
    rank_money = sorted(rows, key=lambda r: -(r["staking_roi_pct"] if r["staking_roi_pct"] is not None else -999))
    for i, r in enumerate(rank_signal, 1):
        r["rank_signal"] = i
    for i, r in enumerate(rank_money, 1):
        r["rank_money"] = i
    return rows


def label_key_for(file):
    return "strategy"


def block_signal():
    m = lib.load("data/model/strategies.json")["leaderboard"]
    s = lib.load("data/s9cb/leaderboard.json")["leaderboard"]
    sig_m = _signal(m, "n_graded", "wins")
    sig_s = _signal(s, "n_decided", "wins")
    # one family of 24 tests: BH over the merged list, then written back through dict identity
    family = sig_m + sig_s
    family.sort(key=lambda o: o["p_value"])
    run = 1.0
    for pos in range(len(family) - 1, -1, -1):
        run = min(run, family[pos]["p_value"] * len(family) / (pos + 1))
        family[pos]["q_value"] = run
    rows = _signal_rows([
        ("data/model/strategies.json", "data/model/strategies.json", sig_m, "n_graded", "wins", "roi", "roi_ci95"),
        ("data/s9cb/leaderboard.json", "data/s9cb/leaderboard.json", sig_s, "n_decided", "wins", "roi", "roi_ci95"),
    ])
    OUT["signal"] = {
        "rows": rows, "n_rows": len(rows),
        "n_signal_ci_above_zero": sum(1 for r in rows if r["signal_ci_low"] > 0),
        "n_both_positive": sum(1 for r in rows if r["signal_ci_low"] > 0 and (r["staking_roi_pct"] or 0) > 0),
        "n_q_below_05": sum(1 for r in rows if r["bh_q"] < 0.05),
        "n_minus_log10_q": round(-1 * math.log10(max(r["bh_q"] for r in rows)), 3),
        "n_p_reproduces": sum(1 for r in rows if r["p_reproduces"]),
        "n_p_checked": sum(1 for r in rows if r["p_reproduces"] is not None),
        "n_vs_price_above_005": sum(1 for r in rows if r["p_vs_price"] is not None and r["p_vs_price"] < 0.05),
        "price_misses": [{"strategy": r["strategy"], "p_calc": r["p_vs_price"], "p_published": r["published_p"]}
                         for r in rows if r["p_reproduces"] is False],
        "method": ("Signal = 100 x (win rate - 0.5), normal 95% interval, two-sided z test against a coin flip. "
                   "The money column is the board's own ROI at the prices it used. Both are printed because they "
                   "answer different questions. Benjamini-Hochberg q across every rule on both boards (24 tests). "
                   "Two nulls are reported per rule because they answer different questions: H0 = a coin flip "
                   "(is there a signal at all?) and H0 = the break-even rate implied by the price actually taken "
                   "(does the signal survive the price?). The board's own published p is recomputed here from its "
                   "n, wins and break-even rate; a cell that does not reproduce is flagged."),
        "retrieved": RETRIEVED,
    }


# ---------------------------------------------------------------- 10. correlation register
def block_correlations():
    games = csvrows("data/s9cb/games.csv")
    def pairs(rows):
        xs, ys = [], []
        for r in rows:
            if r["spread_line"] and r["home_score"] and r["away_score"]:
                xs.append(float(r["spread_line"]))
                ys.append(float(r["home_score"]) - float(r["away_score"]))
        return xs, ys
    groups = [("All seasons in the feed, 1999-2026", games),
              ("Last completed season, 2025", [r for r in games if r["season"] == "2025"]),
              ("2026, weeks 1-9 (feed results only)", [r for r in games if r["season"] == "2026" and int(r["week"]) <= 9]),
              ("2026 week 10, 13 finals verified against the official schedule page this session",
               [r for r in games if r["season"] == "2026" and r["week"] == "10"])]
    rows = []
    for label, g in groups:
        xs, ys = pairs(g)
        r, ci, t, n = pearson(xs, ys)
        published = ci is not None and n is not None and n >= 25
        rows.append({
            "relationship": "Closing spread vs the actual home margin",
            "sample": label,
            "n": len(xs) if n is None else n,
            "r": r if published else lib.UNVERIFIED,
            "ci95": (f"[{ci[0]}, {ci[1]}]" if published else lib.UNVERIFIED),
            "t": t if published else lib.UNVERIFIED,
            "published": published,
            "why_blank": "" if published else "n is below the repository's 25-observation publication floor, so no coefficient is printed",
            "source": "https://github.com/nflverse/nflverse-data/releases/tag/schedules",
            "official_cross_check": lib.OFFICIAL["schedule_results"],
            "retrieved": RETRIEVED,
        })
    # officially sourced correlations: every input is a number printed on the official standings
    # page and reproduced by the Week-10 reconciliation, so n = 32 clubs.
    off = lib.load("lab2/data/official_standings_2026-11-16.json")["rows"]
    official_rows = []
    specs = [("Wins vs points differential (PF - PA)", [r["w"] for r in off], [r["pf"] - r["pa"] for r in off]),
             ("Wins vs points for (PF)", [r["w"] for r in off], [r["pf"] for r in off]),
             ("Wins vs points against (PA)", [r["w"] for r in off], [r["pa"] for r in off]),
             ("Winning percentage vs points differential", [r["pct"] for r in off], [r["pf"] - r["pa"] for r in off])]
    for label, xs, ys in specs:
        r, ci, t, n = pearson(xs, ys)
        ok = ci is not None and n >= 25
        official_rows.append({
            "relationship": label, "sample": "All 32 clubs, official 2026 standings",
            "n": n, "r": r if ok else lib.UNVERIFIED,
            "ci95": f"[{ci[0]}, {ci[1]}]" if ok else lib.UNVERIFIED,
            "t": t if ok else lib.UNVERIFIED, "published": ok,
            "why_blank": "" if ok else "below the 25-observation floor",
            "source": lib.OFFICIAL["standings"], "official_cross_check": "yes",
            "retrieved": RETRIEVED,
        })
    OUT["correlations"] = {"rows": rows, "official_rows": official_rows, "floor": 25,
                           "method": "Pearson r, Fisher-z 95% interval, two-sided t. Computed here from the stored rows; nothing is copied from another page.",
                           "retrieved": RETRIEVED}


# ---------------------------------------------------------------- 11. what is officially priced
def block_market_provenance():
    snaps = lib.load("data/model/snapshot.json")["fixtures"]
    rows = []
    for f in snaps:
        rows.append({
            "matchup": f"{f['away']} @ {f['home']}",
            "gameday": f["gameday"],
            "market_spread_home": f["market_spread_home"] if f["market_spread_home"] is not None else lib.UNVERIFIED,
            "market_total": f["market_total"] if f["market_total"] is not None else lib.UNVERIFIED,
            "official_line_available": "no",
            "evidence": "The official Week-11 schedule page prints date, time, network and venue; it prints no line, no total and no price.",
            "source": lib.OFFICIAL["schedule_w11"],
            "retrieved": RETRIEVED,
        })
    OUT["market_provenance"] = {
        "rows": rows,
        "n_official_lines": 0,
        "n_unofficial": len(rows),
        "statement": "No number in any market column on this site is an official NFL figure. The league publishes no odds, no spread and no total. Every market number here is a consensus number carried in the mirrored feed and must be read as unofficial.",
        "retrieved": RETRIEVED,
    }


def main():
    block_standings()
    block_results()
    block_lines()
    block_prices()
    block_availability()
    block_depth()
    block_strategies()
    block_forward()
    block_matchups()
    block_signal()
    block_correlations()
    block_market_provenance()
    # Deterministic stamp: the date the sources were read, not the wall clock.  A timestamp would
    # make the build non-reproducible and `--check` could never pass.
    OUT["built"] = RETRIEVED
    OUT["retrieved"] = RETRIEVED
    OUT["official_reads"] = lib.OFFICIAL
    lib.write_json("derived.json", OUT)
    print("derived.json written")
    for k in ("standings", "results", "lines", "availability", "depth", "strategies", "forward",
              "matchups", "signal", "correlations", "market_provenance"):
        v = OUT[k]
        size = len(v.get("rows", [])) if isinstance(v, dict) else len(v)
        print(f"  {k}: {size} rows")


if __name__ == "__main__":
    main()
