#!/usr/bin/env python3
"""Session 1505ac8e - build the decision lab's numbers from verified official data.

Inputs (every one verified against an official page; see verification.json):
  data/verified/games_2026.csv                 136 completed 2026 games (official schedule)
  data/verified/standings_2026.csv             official standings transcription
  data/session-1505ac8e/_raw_standings.tsv     this session's live official transcription
  data/session-1505ac8e/_raw_schedule_week10.tsv
  data/session-1505ac8e/_raw_injuries_week10.tsv
  data/session-1505ac8e/depth_charts.json      official club depth charts (31/32 clubs)

Outputs, all under data/session-1505ac8e/:
  lines.json  strategies.json  correlations.json  luck.json
  availability.json  summary.json

HONESTY RULES
  * Ratings for week W use only games with week < W. No look-ahead, ever.
  * Every strategy rule is written to this file before any outcome is computed, and the
    file's SHA-256 is published with the results so the ordering can be checked.
  * Where a required input does not exist (book prices, multi-season history, official
    travel data), the gate that needs it reports BLOCKED and the strategy is NOT
    certified. Nothing is filled in to make a gate pass.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nfl_stats as st  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "session-1505ac8e")
SEASON = 2026
TARGET_WEEK = 10
RULE_FILE_SHA256 = hashlib.sha256(
    open(os.path.abspath(__file__), "rb").read()).hexdigest()

SRC_STANDINGS = "https://www.nfl.com/standings/league/2026/REG"
SRC_SCHEDULE = "https://www.nfl.com/schedules/2026/week10"
SRC_INJURIES = "https://www.nfl.com/injuries/"
SRC_GAMES = "https://www.nfl.com/schedules/2026/by-week/week-"

# Official nfl.com club codes. Two other sessions' files use LAR / ARI for the Rams and
# Cardinals; that alias is handled here and published as an irregularity rather than
# silently rewritten.
ALIAS = {"LAR": "LA", "ARI": "AZ"}


def norm_abbr(a):
    a = (a or "").strip().upper()
    return ALIAS.get(a, a)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_games():
    rows = []
    with open(os.path.join(DATA, "verified", "games_2026.csv")) as fh:
        for r in csv.DictReader(fh):
            gd = datetime.strptime(r["gameday"], "%Y-%m-%d").date()
            rows.append({
                "game_id": r["game_id"], "week": int(r["week"]), "gameday": gd,
                "away": norm_abbr(r["away_abbr"]), "home": norm_abbr(r["home_abbr"]),
                "away_score": int(r["away_score"]), "home_score": int(r["home_score"]),
                "margin": int(r["home_score"]) - int(r["away_score"]),
                "total": int(r["home_score"]) + int(r["away_score"]),
                "source": r["source_url"],
            })
    rows.sort(key=lambda g: (g["week"], g["gameday"], g["game_id"]))
    return rows


def load_official_standings():
    out = {}
    path = os.path.join(OUT, "_raw_standings.tsv")
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 17 or not p[0].strip():
                continue
            out[p[0].strip()] = {
                "w": int(p[1]), "l": int(p[2]), "t": int(p[3]), "pct": float(p[4]),
                "pf": int(p[5]), "pa": int(p[6]), "net": int(p[7]),
                "home": p[8], "road": p[9], "div": p[10], "div_pct": float(p[11]),
                "conf": p[12], "conf_pct": float(p[13]), "non_conf": p[14],
                "strk": p[15], "last5": p[16], "source": SRC_STANDINGS,
            }
    return out


def load_divisions():
    out = {}
    with open(os.path.join(DATA, "verified", "standings_2026.csv")) as fh:
        for r in csv.DictReader(fh):
            ab = norm_abbr(r["abbr"])
            out[ab] = {"conference": r["conference"], "division": r["division"]}
    return out


def load_week10():
    sched, byes = [], []
    with open(os.path.join(OUT, "_raw_schedule_week10.tsv")) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 8:
                continue
            sched.append({
                "away": p[0], "home": p[1], "gameday": p[2], "kickoff_et": p[3],
                "network": p[4], "away_record": p[5], "home_record": p[6],
                "source": p[7],
                "game_id": f"2026_{TARGET_WEEK}_{p[0]}_{p[1]}",
            })
    with open(os.path.join(OUT, "_raw_byes_week10.tsv")) as fh:
        byes = [l.strip() for l in fh if l.strip()]
    return sched, byes


def load_injuries():
    out = []
    with open(os.path.join(OUT, "_raw_injuries_week10.tsv")) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 7:
                continue
            out.append({
                "game": p[0], "club": p[1], "player": p[2], "pos": p[3],
                "injury": p[4], "practice": p[5], "game_status": p[6],
                "source": SRC_INJURIES,
            })
    return out


def load_depth():
    with open(os.path.join(OUT, "depth_charts.json")) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Ratings: Simple Rating System with a home-field term
# ---------------------------------------------------------------------------

def fit_srs(games, teams, ridge=1e-6):
    """margin = rating_home - rating_away + HFA, solved by least squares.

    Reference: the standard Simple Rating System formulation
    (Sports-Reference, "How are the SRS ratings calculated?").
    A zero-sum constraint row keeps the 32 ratings identified.
    """
    idx = {t: i for i, t in enumerate(teams)}
    p = len(teams) + 1
    X, y = [], []
    for g in games:
        row = [0.0] * p
        row[idx[g["home"]]] += 1.0
        row[idx[g["away"]]] -= 1.0
        row[-1] = 1.0  # home-field advantage
        X.append(row)
        y.append(float(g["margin"]))
    for t in teams:  # sum of ratings = 0
        row = [0.0] * p
        row[idx[t]] = 1.0
        X.append(row)
        y.append(0.0)
    beta = st.ols(X, y, ridge=ridge)
    ratings = {t: beta[idx[t]] for t in teams}
    return ratings, beta[-1]


def fit_total_model(games, ratings, hfa):
    """total = a + b * (rating_home + rating_away), fitted on prior games."""
    X, y = [], []
    for g in games:
        X.append([1.0, ratings[g["home"]] + ratings[g["away"]]])
        y.append(float(g["total"]))
    a, b = st.ols(X, y)
    resid = [y[i] - (a + b * X[i][1]) for i in range(len(y))]
    return {"intercept": a, "slope": b, "resid_sd": st.sd(resid) if len(resid) > 2 else float("nan")}


def margin_resid_sd(games, ratings, hfa):
    resid = [g["margin"] - (ratings[g["home"]] - ratings[g["away"]] + hfa) for g in games]
    return st.sd(resid) if len(resid) > 2 else float("nan")


# ---------------------------------------------------------------------------
# Derived, pre-game team state (computed only from games with week < W)
# ---------------------------------------------------------------------------

def team_state_before(games, week, teams):
    """Everything a rule is allowed to know before week W kicks off."""
    prior = [g for g in games if g["week"] < week]
    pf = defaultdict(int)
    pa = defaultdict(int)
    w = defaultdict(int)
    l = defaultdict(int)
    t = defaultdict(int)
    last_game = {}
    results = defaultdict(list)
    for g in prior:
        for side, opp in (("home", "away"), ("away", "home")):
            tm = g[side]
            pf[tm] += g[f"{side}_score"]
            pa[tm] += g[f"{opp}_score"]
            if g[f"{side}_score"] > g[f"{opp}_score"]:
                w[tm] += 1
                results[tm].append(1)
            elif g[f"{side}_score"] < g[f"{opp}_score"]:
                l[tm] += 1
                results[tm].append(-1)
            else:
                t[tm] += 1
                results[tm].append(0)
            last_game[tm] = max(last_game.get(tm, date(2000, 1, 1)), g["gameday"])
    state = {}
    for tm in teams:
        gp = w[tm] + l[tm] + t[tm]
        pyth = 0.0
        if pf[tm] + pa[tm] > 0:
            pyth = (pf[tm] ** 2.337) / (pf[tm] ** 2.337 + pa[tm] ** 2.337)
        pyth_wins = pyth * gp if gp else 0.0
        act_wins = w[tm] + 0.5 * t[tm]
        streak = 0
        for r in reversed(results[tm]):
            if streak == 0:
                streak = r
            elif (r > 0) == (streak > 0) and r != 0:
                streak += r
            else:
                break
        state[tm] = {
            "gp": gp, "w": w[tm], "l": l[tm], "t": t[tm], "pf": pf[tm], "pa": pa[tm],
            "net_pts": pf[tm] - pa[tm],
            "ppg": (pf[tm] / gp) if gp else 0.0,
            "papg": (pa[tm] / gp) if gp else 0.0,
            "net_pg": ((pf[tm] - pa[tm]) / gp) if gp else 0.0,
            "pyth": pyth, "pyth_wins": pyth_wins,
            "pyth_resid": (pyth_wins - act_wins) if gp else 0.0,
            "streak": streak,
            "last_gameday": last_game.get(tm),
        }
    return state


def rest_days(gameday, last_gameday):
    if not last_gameday:
        return None
    return (gameday - last_gameday).days


# ---------------------------------------------------------------------------
# Strategy rules - FIXED HERE, BEFORE ANY OUTCOME IS COMPUTED
# ---------------------------------------------------------------------------

RULES = [
    {
        "id": "S1", "name": "Rest edge",
        "track": "single",
        "text": ("Bet the side with at least 3 more days of rest than its opponent. "
                 "Rest = days since that club's previous game."),
        "selector": "rest differential (official game dates)",
        "uses_model_prediction": False,
        "needs_market_price": False,
        "backtestable": True,
    },
    {
        "id": "S2", "name": "Home team off a bye",
        "track": "single",
        "text": ("Bet the home side when it has had 13+ days since its last game and the "
                 "visitor has not."),
        "selector": "rest, home/away (official schedule)",
        "uses_model_prediction": False,
        "needs_market_price": False,
        "backtestable": True,
    },
    {
        "id": "S3", "name": "Division dog",
        "track": "single",
        "text": ("In division games, bet the club with the worse net points per game "
                 "(points for minus points against, from completed games only)."),
        "selector": "official net points per game + division (official standings)",
        "uses_model_prediction": False,
        "needs_market_price": False,
        "backtestable": True,
    },
    {
        "id": "S4", "name": "Fade the hot streak",
        "track": "single",
        "text": "Bet against any club that enters the week on a win streak of 3 or more.",
        "selector": "win/loss streak built from completed official results",
        "uses_model_prediction": False,
        "needs_market_price": False,
        "backtestable": True,
    },
    {
        "id": "S5", "name": "Pythagorean bounce-back",
        "track": "single",
        "text": ("Bet the club whose Pythagorean expected wins exceed its actual wins by "
                 "at least 1.0. Exponent 2.337."),
        "selector": "points for/against from completed official results",
        "uses_model_prediction": False,
        "needs_market_price": False,
        "backtestable": True,
    },
    {
        "id": "S6", "name": "Road dog with the better defence",
        "track": "single",
        "text": ("Bet the road club when it allows fewer points per game than its host "
                 "and enters with the worse record."),
        "selector": "official points allowed per game and win-loss record",
        "uses_model_prediction": False,
        "needs_market_price": False,
        "backtestable": True,
    },
    {
        "id": "S7", "name": "Model-vs-market disagreement",
        "track": "single",
        "text": ("Bet the side my model favours when it differs from the consensus closing "
                 "line by 3 points or more."),
        "selector": "my line vs the consensus closing line",
        "uses_model_prediction": True,
        "needs_market_price": True,
        "backtestable": False,
        "blocked_reason": ("No official NFL odds exist and no licensed book feed is "
                           "connected. Historical closing lines are unavailable, so this "
                           "rule cannot be scored and is published as a signal only."),
    },
    {
        "id": "S8", "name": "Bet the model's biggest edge",
        "track": "single",
        "text": ("Bet the side my model favours by 4 points or more. INCLUDED ON PURPOSE: "
                 "the selector is the same number the outcome is measured against, so it "
                 "is a self-referential test and gate G10 exists to catch it."),
        "selector": "my own predicted margin (self-referential by design)",
        "uses_model_prediction": True,
        "needs_market_price": False,
        "backtestable": True,
        "self_referential": True,
    },
    {
        "id": "S9", "name": "Fade the injury-hit starter",
        "track": "single",
        "text": ("Bet against a club with two or more starters (first string on its own "
                 "depth chart) ruled Out or Questionable."),
        "selector": "official injury report joined to official club depth charts",
        "uses_model_prediction": False,
        "needs_market_price": False,
        "backtestable": False,
        "blocked_reason": ("The official injury report and club depth charts are only "
                           "retained for the current week, so there is no history to "
                           "backtest. Published as a live signal for Week 10 with no "
                           "grade."),
    },
]

PARLAY_TRACK = {
    "id": "P1", "name": "Two-leg correlated parlay",
    "text": ("Combine the two least-correlated graded rules. Legs are only worth "
             "combining if their outcomes are genuinely independent; the measured "
             "correlation decides that, not intuition."),
}

PROP_TRACK = {
    "id": "R1", "name": "Player-prop combos",
    "text": ("Same-game player-prop combinations. No official or book prop prices exist, "
             "so no line, price or edge can be produced. Track is defined and empty."),
}


def generate_bets(games, weeks, teams, divs, lines_by_week):
    """Return {rule_id: [bet, ...]}. A bet selects a side; the outcome is scored later."""
    bets = defaultdict(list)
    for week in weeks:
        state = team_state_before(games, week, teams)
        wk_games = [g for g in games if g["week"] == week]
        preds = lines_by_week.get(week, {}).get("pred", {})
        for g in wk_games:
            h, a = g["home"], g["away"]
            gd = g["gameday"]
            rh = rest_days(gd, state[h]["last_gameday"])
            ra = rest_days(gd, state[a]["last_gameday"])
            ctx = {"rh": rh, "ra": ra, "state": state, "div": divs}
            same_div = (divs.get(h, {}).get("division") == divs.get(a, {}).get("division")
                        and divs.get(h, {}).get("conference") == divs.get(a, {}).get("conference"))
            pred = preds.get(g["game_id"])
            pred_margin = pred["pred_margin"] if pred else None

            def add(rid, side, why):
                bets[rid].append({
                    "week": week, "game_id": g["game_id"], "gameday": gd.isoformat(),
                    "home": h, "away": a, "side": side, "why": why,
                    "rest_home": rh, "rest_away": ra,
                })

            # S1 rest edge
            if rh is not None and ra is not None:
                if rh - ra >= 3:
                    add("S1", h, f"rest {rh}d vs {ra}d")
                elif ra - rh >= 3:
                    add("S1", a, f"rest {ra}d vs {rh}d")
            # S2 home off bye
            if rh is not None and ra is not None and rh >= 13 and ra < 13:
                add("S2", h, f"home off bye ({rh}d)")
            # S3 division dog
            if same_div:
                add("S3", h if state[h]["net_pg"] < state[a]["net_pg"] else a,
                    "division game, worse net points per game")
            # S4 fade streak
            if state[h]["streak"] >= 3:
                add("S4", a, f"fading {h} on a {state[h]['streak']}-game win streak")
            if state[a]["streak"] >= 3:
                add("S4", h, f"fading {a} on a {state[a]['streak']}-game win streak")
            # S5 pythagorean bounce-back
            if state[h]["pyth_resid"] >= 1.0:
                add("S5", h, f"pythag +{state[h]['pyth_resid']:.2f} wins")
            if state[a]["pyth_resid"] >= 1.0:
                add("S5", a, f"pythag +{state[a]['pyth_resid']:.2f} wins")
            # S6 road dog with better defence
            if (state[a]["papg"] < state[h]["papg"]
                    and state[a]["w"] < state[h]["w"]):
                add("S6", a, f"road {a} allows {state[a]['papg']:.1f} vs {state[h]['papg']:.1f}")
            # S8 self-referential: biggest model edge
            if pred_margin is not None and abs(pred_margin) >= 4.0:
                add("S8", h if pred_margin > 0 else a,
                    f"model edge {abs(pred_margin):.1f}")
    return bets


# ---------------------------------------------------------------------------
# Availability model: official injury report x official club depth chart
# ---------------------------------------------------------------------------

SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def norm_name(n):
    n = re.sub(r"[.'`]", "", (n or "").lower())
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    parts = [p for p in n.split() if p and p not in SUFFIXES]
    return " ".join(parts)


POS_ALIAS = {
    # Injury-report position -> the position labels official club depth charts use.
    # The league and the clubs do not share a vocabulary (nfl.com says DT, Washington's
    # own chart says DL), so both sides are listed. Nothing is guessed: a player is only
    # matched when their name appears in one of these rows.
    "T": {"LT", "RT", "T", "OL"}, "G": {"LG", "RG", "G", "OL"}, "C": {"C", "OL"},
    "OL": {"OL", "LT", "RT", "LG", "RG", "C", "T", "G"},
    "QB": {"QB"}, "RB": {"RB", "FB"}, "FB": {"FB", "RB"}, "WR": {"WR"},
    "TE": {"TE"}, "DE": {"DE", "EDGE", "DL", "OLB"}, "EDGE": {"EDGE", "DE", "LB"},
    "DT": {"DT", "NT", "DL"}, "NT": {"NT", "DT", "DL"}, "DL": {"DL", "DT", "DE", "NT"},
    "LB": {"LB", "ILB", "OLB", "MLB", "EDGE"}, "ILB": {"ILB", "LB", "MLB"},
    "OLB": {"OLB", "LB", "EDGE"}, "MLB": {"MLB", "LB"},
    "CB": {"CB", "DB", "NB"}, "S": {"S", "FS", "SS", "DB", "NB"},
    "FS": {"FS", "S", "DB"}, "SS": {"SS", "S", "DB"}, "NB": {"NB", "CB", "DB"},
    "DB": {"DB", "CB", "S"},
    "K": {"K"}, "P": {"P"}, "LS": {"LS"}, "H": {"H"},
    "KR": {"KR", "WR", "RB"}, "PR": {"PR", "WR", "RB"},
}

# Column-header rows that some clubs' charts emit as if they were positions.
HEADER_POSITIONS = {"POSITION", "POS", "PLAYER"}


def build_availability(injuries, depth):
    """Join the official injury report to the official club depth charts."""
    charts = {}
    for c in depth["clubs"]:
        if c["status"] != "ok":
            continue
        pos_index = defaultdict(list)
        for row in c["depth"]:
            if row["position"].upper() in HEADER_POSITIONS:
                continue
            pos_index[row["position"].upper()].append(row)
        charts[norm_abbr(c["abbr"])] = {
            "rows": c["depth"], "pos_index": dict(pos_index),
            "source": c["source_url"], "as_of": c["as_of"],
        }

    status_weight = {"Out": 1.0, "Doubtful": 0.75, "Questionable": 0.5}
    # Practice weights are a modelling assumption, not an NFL rule. They exist because the
    # official game status column is empty for almost everyone until the clubs file it.
    practice_weight = {"Did Not Participate": 0.5, "Limited": 0.2, "Full": 0.0, "": 0.0}
    rank_weight = {1: 1.0, 2: 0.5, 3: 0.25, 4: 0.125}
    rows, unmatched = [], []
    club_pressure = defaultdict(lambda: {
        "offense": 0.0, "defense": 0.0, "special_teams": 0.0,
        "practice_offense": 0.0, "practice_defense": 0.0, "practice_special": 0.0,
        "starters_out": 0, "starters_questionable": 0, "starters_dnp": 0,
        "starters_limited": 0, "list_size": 0, "starters_affected": [],
        "backups_affected": [],
    })

    for inj in injuries:
        ab = inj["club"]
        chart = charts.get(ab)
        rec = dict(inj)
        rec.update({"depth_rank": None, "unit": None, "matched_position": None,
                    "next_man_up": "", "pressure": 0.0, "match": "no-chart"})
        if chart:
            want = POS_ALIAS.get(inj["pos"].upper(), {inj["pos"].upper()})
            want = {w.upper() for w in want}
            best = None
            for pos, lst in chart["pos_index"].items():
                if pos.upper() not in want:
                    continue
                for row in lst:
                    for pl in row["players"]:
                        if norm_name(pl["name"]) == norm_name(inj["player"]):
                            if best is None or pl["rank"] < best[1]["rank"]:
                                best = (row, pl)
            if best:
                row, pl = best
                rec.update({
                    "depth_rank": pl["rank"], "unit": row["unit"],
                    "matched_position": row["position"],
                    "match": "matched",
                })
                # next man up = the next listed player at that position who is not Out
                out_names = {norm_name(i["player"]) for i in injuries
                             if i["club"] == ab and i["game_status"] == "Out"}
                for cand in row["players"]:
                    if cand["rank"] > pl["rank"] and norm_name(cand["name"]) not in out_names:
                        rec["next_man_up"] = f"{cand['name']} (string {cand['rank']})"
                        break
                if not rec["next_man_up"] and pl["rank"] >= 2:
                    rec["next_man_up"] = "no deeper replacement listed"
            else:
                rec["match"] = "not-on-depth-chart"
                unmatched.append(rec)
        else:
            rec["match"] = "no-depth-chart-for-club"
            unmatched.append(rec)

        pw = practice_weight.get(inj["practice"], 0.0)
        if rec["depth_rank"]:
            rw = rank_weight.get(rec["depth_rank"], 0.05)
            rec["practice_pressure"] = round(pw * rw, 4)
            cp = club_pressure[ab]
            key = {"offense": "practice_offense", "defense": "practice_defense",
                   "special_teams": "practice_special"}.get(rec["unit"])
            if key:
                cp[key] = round(cp[key] + rec["practice_pressure"], 4)
            if rec["depth_rank"] == 1:
                if inj["practice"] == "Did Not Participate":
                    cp["starters_dnp"] += 1
                elif inj["practice"] == "Limited":
                    cp["starters_limited"] += 1
                cp["starters_affected"].append(
                    f"{inj['player']} ({inj['pos']}, {inj['practice'].lower()})")
            elif rec["depth_rank"] and rec["depth_rank"] <= 4:
                cp["backups_affected"].append(
                    f"{inj['player']} ({inj['pos']}, string {rec['depth_rank']})")

        w = status_weight.get(inj["game_status"], 0.0)
        if w and rec["depth_rank"]:
            rw = rank_weight.get(rec["depth_rank"], 0.05)
            rec["pressure"] = round(w * rw, 4)
            cp = club_pressure[ab]
            cp[rec["unit"]] = round(cp[rec["unit"]] + rec["pressure"], 4)
            if rec["depth_rank"] == 1:
                if inj["game_status"] == "Out":
                    cp["starters_out"] += 1
                elif inj["game_status"] == "Questionable":
                    cp["starters_questionable"] += 1
                cp["starters_affected"].append(
                    f"{inj['player']} ({inj['pos']}, {inj['game_status']})")
        club_pressure[ab]["list_size"] += 1
        rows.append(rec)

    clubs = []
    for ab, p in sorted(club_pressure.items()):
        clubs.append({
            "abbr": ab,
            "players_listed": p["list_size"],
            "starters_out": p["starters_out"],
            "starters_questionable": p["starters_questionable"],
            "offense_pressure": round(p["offense"], 3),
            "defense_pressure": round(p["defense"], 3),
            "special_teams_pressure": round(p["special_teams"], 3),
            "game_status_pressure": round(p["offense"] + p["defense"] + p["special_teams"], 3),
            "practice_offense_pressure": round(p["practice_offense"], 3),
            "practice_defense_pressure": round(p["practice_defense"], 3),
            "practice_total_pressure": round(
                p["practice_offense"] + p["practice_defense"] + p["practice_special"], 3),
            "total_pressure": round(
                p["offense"] + p["defense"] + p["special_teams"]
                + p["practice_offense"] + p["practice_defense"] + p["practice_special"], 3),
            "starters_dnp": p["starters_dnp"], "starters_limited": p["starters_limited"],
            "starters_affected": p["starters_affected"],
            "backups_affected": p["backups_affected"][:6],
            "depth_chart_source": charts.get(ab, {}).get("source", ""),
            "injury_source": SRC_INJURIES,
        })
    clubs.sort(key=lambda c: (-c["game_status_pressure"], -c["practice_total_pressure"]))
    return {
        "rows": rows, "clubs": clubs, "unmatched": unmatched,
        "n_injury_rows": len(injuries), "n_matched": sum(1 for r in rows if r["match"] == "matched"),
        "n_unmatched": len(unmatched),
        "counts": {
            "rows_with_game_status": sum(1 for r in rows if r["game_status"]),
            "rows_with_body_part": sum(1 for r in rows if r["injury"].strip()),
            "rows_with_practice_status": sum(1 for r in rows if r["practice"]),
        },
        "weights": {
            "status": status_weight, "practice": practice_weight, "depth_rank": rank_weight,
            "note": ("Weights are this project's modelling choice, not an NFL rule. "
                     "They are published so a reviewer can change them."),
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    games = load_games()
    standings = load_official_standings()
    divs = load_divisions()
    sched10, byes10 = load_week10()
    injuries = load_injuries()
    depth = load_depth()

    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    weeks = sorted({g["week"] for g in games})

    # ---- walk-forward lines and backtest -------------------------------------
    eval_weeks = [w for w in weeks if w >= 4]
    lines_by_week, fold_metrics = {}, []
    for w in eval_weeks + [TARGET_WEEK]:
        train = [g for g in games if g["week"] < w]
        test = [g for g in games if g["week"] == w]
        if len(train) < 32:
            continue
        ratings, hfa = fit_srs(train, teams)
        tmod = fit_total_model(train, ratings, hfa)
        sigma = margin_resid_sd(train, ratings, hfa)
        preds = {}
        for g in test:
            pm = ratings[g["home"]] - ratings[g["away"]] + hfa
            pt = tmod["intercept"] + tmod["slope"] * (ratings[g["home"]] + ratings[g["away"]])
            preds[g["game_id"]] = {
                "pred_margin": pm, "pred_total": pt,
                "home_win_prob": st.norm_cdf(pm / sigma) if sigma else float("nan"),
            }
        lines_by_week[w] = {"ratings": ratings, "hfa": hfa, "total_model": tmod,
                            "sigma": sigma, "pred": preds, "n_train": len(train)}
        if test:
            errs = [g["margin"] - preds[g["game_id"]]["pred_margin"] for g in test]
            terr = [g["total"] - preds[g["game_id"]]["pred_total"] for g in test]
            base_hfa = [g["margin"] - hfa for g in test]
            base_zero = [g["margin"] for g in test]
            fold_metrics.append({
                "week": w, "n": len(test), "n_train": len(train),
                "hfa": round(hfa, 3), "sigma": round(sigma, 3),
                "spread_mae": round(sum(abs(e) for e in errs) / len(errs), 3),
                "spread_rmse": round(math.sqrt(sum(e * e for e in errs) / len(errs)), 3),
                "total_mae": round(sum(abs(e) for e in terr) / len(terr), 3),
                "baseline_hfa_only_mae": round(sum(abs(e) for e in base_hfa) / len(base_hfa), 3),
                "baseline_zero_mae": round(sum(abs(e) for e in base_zero) / len(base_zero), 3),
            })

    all_mae = [f["spread_mae"] for f in fold_metrics]
    all_n = [f["n"] for f in fold_metrics]
    pooled_mae = (sum(m * n for m, n in zip(all_mae, all_n)) / sum(all_n)) if all_n else float("nan")
    pooled_hfa_mae = (sum(f["baseline_hfa_only_mae"] * f["n"] for f in fold_metrics)
                      / sum(all_n)) if all_n else float("nan")
    pooled_zero_mae = (sum(f["baseline_zero_mae"] * f["n"] for f in fold_metrics)
                       / sum(all_n)) if all_n else float("nan")

    # ---- week 10 published lines ---------------------------------------------
    wk10 = lines_by_week[TARGET_WEEK]
    published = []
    for s in sched10:
        h, a = s["home"], s["away"]
        pm = wk10["ratings"][h] - wk10["ratings"][a] + wk10["hfa"]
        pt = (wk10["total_model"]["intercept"]
              + wk10["total_model"]["slope"] * (wk10["ratings"][h] + wk10["ratings"][a]))
        sigma = wk10["sigma"]
        published.append({
            "game_id": s["game_id"], "week": TARGET_WEEK, "gameday": s["gameday"],
            "kickoff_et": s["kickoff_et"], "network": s["network"],
            "away_record": s["away_record"], "home_record": s["home_record"],
            "away": a, "home": h,
            "my_home_line": round(pm, 1),
            "my_line_display": (f"{h} -{abs(pm):.1f}" if pm > 0 else f"{h} +{abs(pm):.1f}"),
            "my_total": round(pt, 1),
            "my_home_win_prob": round(st.norm_cdf(pm / sigma), 3),
            "spread_band95": [round(pm - 1.96 * sigma, 1), round(pm + 1.96 * sigma, 1)],
            "total_band95": [round(pt - 1.96 * wk10["total_model"]["resid_sd"], 1),
                             round(pt + 1.96 * wk10["total_model"]["resid_sd"], 1)],
            "market_home_line": None, "market_total": None, "edge": None,
            "source_game": s["source"], "source_results": SRC_GAMES + "1",
        })

    lines_doc = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "season": SEASON, "week": TARGET_WEEK,
        "method": {
            "ratings": ("Simple Rating System: margin = rating_home - rating_away + HFA, "
                        "solved by least squares with a zero-sum constraint. Reference: "
                        "Sports-Reference SRS definition."),
            "totals": "total = a + b*(rating_home + rating_away), OLS on prior games.",
            "win_prob": "P(home win) = Phi(predicted margin / residual SD).",
            "walk_forward": ("Ratings for week W use only games with week < W, so no game "
                             "is predicted using information from itself or from a later week."),
            "season_coverage": ("Only the 2026 season is used, because that is the only "
                                "season whose game results have been transcribed and "
                                "verified against official nfl.com pages in this repo."),
        },
        "rule_file_sha256": RULE_FILE_SHA256,
        "n_training_games": wk10["n_train"],
        "hfa": round(wk10["hfa"], 3),
        "home_field_crosscheck": {
            "raw_mean_home_margin": round(sum(g["margin"] for g in games) / len(games), 3),
            "home_wins": sum(1 for g in games if g["margin"] > 0),
            "away_wins": sum(1 for g in games if g["margin"] < 0),
            "ties": sum(1 for g in games if g["margin"] == 0),
            "n": len(games),
            "note": ("Raw, unadjusted home margin over every completed game. The fitted term "
                     "differs from it because the fitted term is adjusted for the strength of "
                     "the teams involved."),
        },
        "residual_sd_margin": round(wk10["sigma"], 3),
        "total_model": {k: (round(v, 4) if isinstance(v, float) else v)
                        for k, v in wk10["total_model"].items()},
        "ratings": [{"abbr": t, "rating": round(wk10["ratings"][t], 3)} for t in teams],
        "backtest": {
            "folds": fold_metrics,
            "pooled_spread_mae": round(pooled_mae, 3),
            "baseline_hfa_only_mae": round(pooled_hfa_mae, 3),
            "baseline_zero_mae": round(pooled_zero_mae, 3),
            "beats_hfa_baseline": bool(pooled_mae < pooled_hfa_mae),
            "beats_zero_baseline": bool(pooled_mae < pooled_zero_mae),
        },
        "lines": published,
        "byes": byes10,
        "sources": {"results": SRC_GAMES + "1", "schedule": SRC_SCHEDULE,
                    "standings": SRC_STANDINGS},
    }

    # ---- strategies -----------------------------------------------------------
    grade_weeks = [w for w in eval_weeks if w < TARGET_WEEK and w in lines_by_week]
    bets = generate_bets(games, grade_weeks, teams, divs, lines_by_week)
    game_by_id = {g["game_id"]: g for g in games}

    # Outcome measured as the model residual from the bet side's point of view.
    pool_by_week = defaultdict(list)
    for w in grade_weeks:
        for g in games:
            if g["week"] != w:
                continue
            pred = lines_by_week[w]["pred"].get(g["game_id"])
            if not pred:
                continue
            pool_by_week[w].append(g["margin"] - pred["pred_margin"])

    # Live, ungraded signals for the upcoming slate: the same rules applied to week 10
    # with no outcome, because the games have not been played.
    week10_games = [{
        "game_id": g["game_id"], "week": TARGET_WEEK,
        "gameday": datetime.strptime(g["gameday"], "%Y-%m-%d").date(),
        "home": g["home"], "away": g["away"], "margin": None, "total": None,
    } for g in sched10]
    wk10_bets = generate_bets(games + week10_games, [TARGET_WEEK], teams, divs, lines_by_week)
    live_signals = []
    for rule in RULES:
        rid = rule["id"]
        for b in wk10_bets.get(rid, []):
            live_signals.append({
                "rule": rid, "rule_name": rule["name"], "game_id": b["game_id"],
                "home": b["home"], "away": b["away"], "side": b["side"], "why": b["why"],
                "status": "not graded - game not played",
            })

    graded = {}
    for rule in RULES:
        rid = rule["id"]
        rec = dict(rule)
        bl = bets.get(rid, [])
        scored = []
        for b in bl:
            g = game_by_id[b["game_id"]]
            pred = lines_by_week[b["week"]]["pred"].get(b["game_id"])
            if not pred:
                continue
            resid = g["margin"] - pred["pred_margin"]
            edge = resid if b["side"] == b["home"] else -resid
            scored.append({
                "week": b["week"], "game_id": b["game_id"], "side": b["side"],
                "why": b["why"], "edge": round(edge, 3), "win": edge > 0,
                "actual_margin_home": g["margin"],
            })
        rec["n_bets"] = len(scored)
        rec["graded"] = bool(scored)
        if not rule.get("backtestable", True):
            rec["status"] = "NOT GRADED"
            rec["status_reason"] = rule.get("blocked_reason", "")
            rec["gates"] = {g: "BLOCKED" for g in
                            ("G1", "G3", "G4", "G5", "G6", "G8", "G9")}
            rec["gates"]["G2"] = "PASS"
            rec["gates"]["G0"] = "PASS"
            rec["gates"]["G10"] = "BLOCKED"
            rec["stats"] = {}
            graded[rid] = rec
            continue

        edges = [s["edge"] for s in scored]
        wins = sum(1 for s in scored if s["win"])
        n = len(edges)
        ci_lo, ci_hi = st.bootstrap_mean_ci(edges)
        tstat = (st.mean(edges) / (st.sd(edges) / math.sqrt(n))) if n > 1 and st.sd(edges) else float("nan")
        p_t = st.t_two_sided_p(tstat, n - 1) if n > 1 else float("nan")
        p_bin = st.binomial_two_sided_p(wins, n)
        pool = [v for w in grade_weeks for v in pool_by_week[w]]
        p_perm, obs = st.permutation_p(edges, pool)
        by_week = defaultdict(float)
        for s in scored:
            by_week[s["week"]] += s["edge"]
        total_edge = sum(edges)
        max_week_share = (max((abs(v) for v in by_week.values()), default=0.0)
                          / abs(total_edge)) if total_edge else float("nan")
        halves = {}
        for s in scored:
            halves.setdefault("early" if s["week"] <= (min(grade_weeks) + 1) else "late", []).append(s["edge"])
        if len(halves) == 2 and all(len(v) > 2 for v in halves.values()):
            r_half, _ = st.pearson(halves["early"], halves["late"])
        else:
            r_half = float("nan")

        rec["stats"] = {
            "n": n, "wins": wins, "losses": n - wins,
            "win_rate": round(wins / n, 4) if n else float("nan"),
            "mean_edge_pts": round(st.mean(edges), 3) if n else float("nan"),
            "sd_edge": round(st.sd(edges), 3) if n > 1 else float("nan"),
            "ci95_mean_edge": [round(ci_lo, 3), round(ci_hi, 3)],
            "t_stat": round(tstat, 3), "p_t": p_t,
            "p_binomial": p_bin,
            "permutation_p": p_perm,
            "max_single_week_share": round(max_week_share, 3),
            "split_half_correlation": r_half,
            "edge_by_week": {str(k): round(v, 2) for k, v in sorted(by_week.items())},
        }
        rec["bets"] = scored
        graded[rid] = rec

    # Benjamini-Hochberg across the graded rules that produced bets
    graded_ids = [r for r in graded if graded[r]["graded"]]
    pvals = [graded[r]["stats"]["p_t"] for r in graded_ids]
    adj, rej = st.benjamini_hochberg(pvals, alpha=0.10)
    for i, rid in enumerate(graded_ids):
        graded[rid]["stats"]["p_t_bh"] = adj[i]
        graded[rid]["stats"]["p_t_bh_reject"] = bool(rej[i])

    # Gates
    GATE_DEFS = [
        ("G0", "Rule written down before any outcome was computed",
         "The rule file is committed and its SHA-256 is published with the results."),
        ("G1", "At least 30 graded bets", "Sample size floor."),
        ("G2", "Walk-forward: no look-ahead information",
         "Ratings and form use only games with week < W."),
        ("G3", "Bootstrap 95% CI for mean edge has a lower bound above 0",
         "Percentile bootstrap, 10,000 resamples, fixed seed."),
        ("G4", "Beats the break-even vig of a real sportsbook",
         "Needs book prices. BLOCKED: no official odds and no licensed feed."),
        ("G5", "No single week supplies more than 40% of the total edge",
         "Concentration check."),
        ("G6", "Holds up in a second season",
         "BLOCKED: only 2026 results are transcribed and verified in this repo."),
        ("G7", "Correlation below 0.70 with every other passing rule",
         "Parlay diversification check. Evaluated once two rules pass."),
        ("G8", "p-value survives Benjamini-Hochberg at FDR 0.10",
         "Multiple-testing correction across all graded rules."),
        ("G9", "Beats a random-bet null (permutation p <= 0.05)",
         "10,000 same-size random draws from the same weeks. This is the luck test."),
        ("G10", "Selector is independent of the number the outcome is measured against",
         "Catches self-referential rules such as 'bet my biggest edge'."),
    ]
    for rid, rec in graded.items():
        if not rec["graded"]:
            continue
        s = rec["stats"]
        g = {}
        g["G0"] = "PASS"
        g["G1"] = "PASS" if s["n"] >= 30 else "FAIL"
        g["G2"] = "PASS"
        g["G3"] = "PASS" if s["ci95_mean_edge"][0] > 0 else "FAIL"
        g["G4"] = "BLOCKED"
        g["G5"] = "PASS" if s["max_single_week_share"] < 0.40 else "FAIL"
        g["G6"] = "BLOCKED"
        g["G7"] = "NOT EVALUATED"
        g["G8"] = "PASS" if s.get("p_t_bh_reject") else "FAIL"
        g["G9"] = "PASS" if (s["permutation_p"] or 1.0) <= 0.05 else "FAIL"
        g["G10"] = "FAIL" if rec.get("uses_model_prediction") else "PASS"
        rec["gates"] = g
        failed = [k for k, v in g.items() if v == "FAIL"]
        blocked = [k for k, v in g.items() if v in ("BLOCKED", "NOT EVALUATED")]
        if failed:
            rec["status"] = "FAIL"
            rec["status_reason"] = "fails " + ", ".join(failed)
        elif blocked:
            rec["status"] = "CANNOT CERTIFY"
            rec["status_reason"] = ("passes every gate it can be tested on, but "
                                    + ", ".join(blocked)
                                    + " cannot be evaluated with the data that exists")
        else:
            rec["status"] = "PASS"
            rec["status_reason"] = ""

    # ---- correlations ---------------------------------------------------------
    series = {}
    for rid, rec in graded.items():
        if not rec["graded"]:
            continue
        series[rid] = {b["game_id"]: b["edge"] for b in rec["bets"]}
    ids = sorted(series)
    pairs = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            common = sorted(set(series[a]) & set(series[b]))
            if len(common) < 5:
                pairs.append({"a": a, "b": b, "n": len(common), "r": None,
                              "p": None, "ci95": None,
                              "note": "fewer than 5 shared games; not estimated"})
                continue
            r, n = st.pearson([series[a][g] for g in common], [series[b][g] for g in common])
            degenerate = abs(r) >= 0.999
            pairs.append({
                "a": a, "b": b, "n": n, "r": round(r, 4),
                "p": None if degenerate else st.pearson_p(r, n),
                "ci95": ([round(x, 4) for x in st.fisher_ci(r, n)]
                         if not degenerate else None),
                "note": ("the two rules picked the same side on every shared game, so the "
                         "correlation is degenerate at this sample size and no p-value is "
                         "meaningful" if degenerate else ""),
            })
    # phi (binary) correlation for the parlay maths
    def phi(a, b):
        common = sorted(set(series[a]) & set(series[b]))
        if len(common) < 5:
            return None, len(common)
        xa = [1.0 if series[a][g] > 0 else 0.0 for g in common]
        xb = [1.0 if series[b][g] > 0 else 0.0 for g in common]
        r, n = st.pearson(xa, xb)
        return (round(r, 4) if r == r else None), n

    best = None
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            r, n = phi(ids[i], ids[j])
            if r is None:
                continue
            if best is None or r < best["phi"]:
                best = {"a": ids[i], "b": ids[j], "phi": r, "n": n}

    parlay = {"note": PARLAY_TRACK["text"], "best_pair": None}
    if best:
        pa = sum(1 for v in series[best["a"]].values() if v > 0) / len(series[best["a"]])
        pb = sum(1 for v in series[best["b"]].values() if v > 0) / len(series[best["b"]])
        rho = best["phi"]
        indep = pa * pb
        adj_p = indep + rho * math.sqrt(pa * (1 - pa) * pb * (1 - pb))
        parlay["best_pair"] = {
            "legs": [best["a"], best["b"]], "n_shared_games": best["n"],
            "p_leg_a": round(pa, 4), "p_leg_b": round(pb, 4),
            "phi": rho, "p_both_independent": round(indep, 4),
            "p_both_with_correlation": round(adj_p, 4),
            "formula": "p(A and B) = p(A)p(B) + rho*sqrt(p(A)(1-p(A))p(B)(1-p(B)))",
            "caveat": ("Win probabilities are measured against MY line, not against a book "
                       "price, so this is a correlation exercise, not a payout."),
        }

    corr_doc = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "definition": ("Pearson r between two rules' per-game edge series. Edge = actual "
                       "home margin minus my predicted home margin, signed to the side the "
                       "rule bet. Only games both rules bet on are used."),
        "method_sources": [
            {"name": "NIST/SEMATECH e-Handbook, correlation",
             "url": "https://www.itl.nist.gov/div898/handbook/eda/section3/eda367.htm"},
            {"name": "Benjamini & Hochberg (1995) FDR",
             "url": "https://doi.org/10.1111/j.2517-6161.1995.tb02031.x"},
        ],
        "n_rules": len(ids), "pairs": pairs, "parlay": parlay,
    }

    # ---- luck -----------------------------------------------------------------
    luck_doc = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "definition": ("Luck is removed by asking how a rule would have done had it bet "
                       "the same number of games chosen at random from the same weeks. "
                       "10,000 random draws, fixed seed. A rule is only interesting if it "
                       "sits in the top 5% of that null distribution."),
        "rules": [{"id": rid, "n": graded[rid]["stats"]["n"],
                   "mean_edge_pts": graded[rid]["stats"]["mean_edge_pts"],
                   "permutation_p": graded[rid]["stats"]["permutation_p"],
                   "ci95_mean_edge": graded[rid]["stats"]["ci95_mean_edge"],
                   "split_half_correlation": graded[rid]["stats"]["split_half_correlation"],
                   "verdict": ("beats the random-bet null"
                               if (graded[rid]["stats"]["permutation_p"] or 1) <= 0.05
                               else "indistinguishable from random bet selection")}
                  for rid in graded_ids],
        "pool_size": sum(len(v) for v in pool_by_week.values()),
        "note": ("This measures whether the SELECTION has information. It does not measure "
                 "profit, because no book prices exist."),
    }

    # ---- availability ---------------------------------------------------------
    avail = build_availability(injuries, depth)

    # ---- leaderboard ----------------------------------------------------------
    board = []
    for rid in sorted(graded):
        rec = graded[rid]
        s = rec.get("stats", {})
        board.append({
            "id": rid, "name": rec["name"], "track": rec["track"],
            "status": rec["status"], "status_reason": rec.get("status_reason", ""),
            "n": s.get("n"), "win_rate": s.get("win_rate"),
            "mean_edge_pts": s.get("mean_edge_pts"),
            "ci95": s.get("ci95_mean_edge"),
            "permutation_p": s.get("permutation_p"),
            "gates": rec.get("gates", {}),
            "points": (round(3 * s["wins"] + (25 if rec["status"] == "PASS" else 0), 1)
                       if s.get("n") else 0.0),
        })
    board.sort(key=lambda r: (-(r["points"] or 0), r["id"]))

    strat_doc = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "rule_file_sha256": RULE_FILE_SHA256,
        "gate_definitions": [{"id": i, "name": n, "detail": d} for i, n, d in GATE_DEFS],
        "window": {"season": SEASON, "weeks": grade_weeks,
                   "note": (f"Weeks {min(grade_weeks)}-{max(grade_weeks)} of 2026; "
                            f"weeks 1-{min(grade_weeks) - 1} are used only to train the "
                            "ratings and the form measures.")},
        "live_signals": live_signals,
        "rules": [graded[r] for r in sorted(graded)],
        "leaderboard": board,
        "tracks": {"single": "One bet per game.",
                   "parlay": PARLAY_TRACK, "props": PROP_TRACK},
        "rewards": {
            "currency": "paper points only",
            "scoring": "3 points per graded win against my line; +25 for a rule that passes every gate.",
            "tiers": [{"tier": "Bronze", "points": "0-49"}, {"tier": "Silver", "points": "50-99"},
                      {"tier": "Gold", "points": "100-199"}, {"tier": "Platinum", "points": "200+"}],
            "legal_note": ("No money, prize or thing of value is awarded. Any reward with "
                           "monetary value needs legal review before it is offered; that "
                           "review has not happened, so the board is paper only."),
        },
    }

    # ---- summary --------------------------------------------------------------
    summary = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "season": SEASON, "week": TARGET_WEEK,
        "n_completed_games": len(games),
        "n_week10_games": len(sched10), "week10_byes": byes10,
        "pooled_spread_mae": lines_doc["backtest"]["pooled_spread_mae"],
        "baseline_hfa_only_mae": lines_doc["backtest"]["baseline_hfa_only_mae"],
        "baseline_zero_mae": lines_doc["backtest"]["baseline_zero_mae"],
        "n_rules": len(RULES),
        "n_rules_graded": len(graded_ids),
        "n_rules_pass": sum(1 for r in board if r["status"] == "PASS"),
        "n_rules_fail": sum(1 for r in board if r["status"] == "FAIL"),
        "n_rules_blocked": sum(1 for r in board if r["status"] in ("CANNOT CERTIFY", "NOT GRADED")),
        "n_injury_rows": len(injuries),
        "n_depth_clubs": depth["clubs_ok"],
        "n_depth_slots": depth["player_slots_total"],
    }

    os.makedirs(OUT, exist_ok=True)
    for name, doc in (("lines", lines_doc), ("strategies", strat_doc),
                      ("correlations", corr_doc), ("luck", luck_doc),
                      ("availability", avail), ("summary", summary)):
        with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
        print(f"wrote {name}.json")

    print(json.dumps(summary, indent=1))
    for r in board:
        print(f"{r['id']} {r['status']:16s} n={r['n']} wr={r['win_rate']} "
              f"edge={r['mean_edge_pts']} perm_p={r['permutation_p']} :: {r['status_reason']}")


if __name__ == "__main__":
    main()
