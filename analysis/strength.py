#!/usr/bin/env python3
"""strength.py -- strength of schedule, schedule-adjusted team strength and own lines.

Question this study answers
---------------------------
*Does knowing how hard a club's schedule has been change the price of its next
game?*  To answer it honestly the module needs a team-strength estimate that is
opponent adjusted, built only from information available before kick-off, and
validated against the closing line with real observed prices.

Method (frozen before evaluation; the parameter block and the rule list are
hashed into data/strength/meta.json)
------------------------------------------------------------------------------
Ratings are a ridge-regularised least-squares fit of

    margin_home = rating_home - rating_away + hfa          (spread model)
    points      = base + off_team - def_opponent + hfa_pts (scoring model)

on every game completed *before* the game being predicted.  The fit is redone
week by week, so week 9 only ever sees weeks 1-8.  Ratings carry over between
consecutive seasons at 60% of the final value -- a documented choice, not a
fitted parameter.

Strength of schedule (SOS) is the mean pre-game rating of the opponents a club
faced.  It is therefore itself a walk-forward number: no future information
leaks into it.  "Remaining SOS" uses today's ratings and is labelled a snapshot.

Nothing is inferred.  A game without an observed price is never scored.  A
player prop has no price in this repository's sources, so prop combos are
published as correlations only and never as profit.

Run: python3 analysis/strength.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from itertools import combinations

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "strength")
GAMES = os.path.join(DATA, "s9cb", "games.csv")
PROVENANCE = os.path.join(DATA, "s9cb", "provenance.json")
PLAYER_WEEK = os.path.join(DATA, "s9cb", "player_week.csv")
OFFICIAL = os.path.join(OUT, "official_week10.json")

# ---------------------------------------------------------------- frozen knobs
RIDGE_RATING = 5.0        # penalty on team ratings in the margin model
RIDGE_HFA = 5.0           # penalty on home-field advantage
RIDGE_SCORE = 8.0         # penalty on offence/defence ratings in the scoring model
CARRYOVER = 0.60          # share of last season's final rating kept at week 1
HOLDOUT_SEASONS = (2024, 2025, 2026)
MIN_BETS = 200
BOOTSTRAP = 10000
SEED = 20261113
SOS_MIN_GAMES = 3         # below this a club's SOS is blank
# nfl.com prints the Arizona club as "AZ"; the nflverse files print "ARI".
ALIASES = {"AZ": "ARI"}
RECENT_WINDOW = 5         # games in the recent-form rating
PYTHAGOREAN_EXPONENT = 2.37   # NFL-wide value used for the Pythagorean expectation

OFFICIAL_STANDINGS_URL = "https://www.nfl.com/standings/league/2026/reg"
OFFICIAL_SCHEDULE_W10_URL = "https://www.nfl.com/schedules/2026/reg10"
OFFICIAL_INJURIES_URL = "https://www.nfl.com/injuries/"
NV_SCHEDULES = "https://github.com/nflverse/nflverse-data/releases/tag/schedules"


# ---------------------------------------------------------------- small stats
def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _two_sided_normal_p(z: float) -> float:
    return 2.0 * (1.0 - _phi(abs(z)))


def american_to_decimal(ml: float) -> float | None:
    """American moneyline -> decimal odds.  Blank in, blank out; never a default."""
    if ml is None or not np.isfinite(ml) or ml == 0:
        return None
    return 1.0 + (ml / 100.0 if ml > 0 else 100.0 / abs(ml))


def decimal_to_american(dec: float) -> float:
    if dec >= 2.0:
        return round((dec - 1.0) * 100.0)
    return round(-100.0 / (dec - 1.0))


def pearson(x, y) -> dict | None:
    """Pearson r with a Fisher-z 95% interval and a two-sided t test."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = int(x.size)
    if n < 4 or x.std() == 0 or y.std() == 0:
        return None
    r = float(np.corrcoef(x, y)[0, 1])
    r_c = max(min(r, 0.999999), -0.999999)
    z = 0.5 * math.log((1 + r_c) / (1 - r_c))
    se = 1.0 / math.sqrt(n - 3)
    lo, hi = math.tanh(z - 1.959964 * se), math.tanh(z + 1.959964 * se)
    t = r * math.sqrt((n - 2) / max(1e-12, 1 - r * r))
    return {"n": n, "r": round(r, 4), "ci95": [round(lo, 4), round(hi, 4)],
            "p_value": round(_two_sided_normal_p(t), 6),
            "method": "Pearson r, Fisher-z 95% CI, two-sided t test (normal approximation for p)"}


def bootstrap_ci(values, reps: int = BOOTSTRAP, seed: int = SEED) -> dict | None:
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size < 30:
        return None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, v.size, size=(reps, v.size))
    draws = v[idx].mean(axis=1)
    return {"reps": reps, "ci95": [round(float(np.percentile(draws, 2.5)), 4),
                                   round(float(np.percentile(draws, 97.5)), 4)]}


def benjamini_hochberg(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank, i in enumerate(reversed(order), start=1):
        val = min(prev, pvals[i] * m / (m - rank + 1))
        q[i] = val
        prev = val
    return q


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- data loading
def load_games() -> tuple[pd.DataFrame, dict]:
    """Load the nflverse extract and re-check its sha256 against provenance.

    The check is reported, not enforced: if the committed file no longer matches
    the pinned hash the study still runs, but the mismatch is published as a
    flag on the verification page so the reader knows the provenance pin is
    stale.  Silently trusting either side would be worse.
    """
    prov = json.load(open(PROVENANCE, encoding="utf-8"))
    entry = next((f for f in prov["files"] if f["local"] == "games.csv"), None)
    actual = _sha256(GAMES)
    integrity = {
        "file": "data/s9cb/games.csv",
        "sha256_now": actual,
        "bytes_now": os.path.getsize(GAMES),
        "sha256_recorded": (entry or {}).get("sha256"),
        "bytes_recorded": (entry or {}).get("bytes"),
        "matches_provenance": bool(entry) and entry.get("sha256") == actual,
        "url": (entry or {}).get("url"),
        "official_upstream": (entry or {}).get("official_upstream"),
        "provenance_generated_at": prov.get("generated_at"),
    }
    df = pd.read_csv(GAMES, low_memory=False)
    integrity["rows_in_file"] = int(len(df))
    df = df[df["home_score"].notna() & df["away_score"].notna()].copy()
    df["margin"] = df["home_score"] - df["away_score"]
    bad = df[(df["result"].notna()) & (df["result"] != df["margin"])]
    integrity["result_sign_check"] = {"rows": int(len(df)), "mismatches": int(len(bad)),
                                      "rule": "result == home_score - away_score"}
    df["gameday"] = pd.to_datetime(df["gameday"], errors="coerce")
    df = df.sort_values(["season", "week", "gameday", "game_id"]).reset_index(drop=True)
    integrity["played_games_used"] = int(len(df))
    return df, integrity


# ---------------------------------------------------------------- the model
def _solve_ratings(games: pd.DataFrame, teams: list[str], prior: dict | None) -> tuple[dict, float]:
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams) + 1
    A = np.zeros((n, n))
    b = np.zeros(n)
    h = games.home_team.values
    a = games.away_team.values
    m = games.margin.values.astype(float)
    valid = np.array([(x in idx) and (y in idx) for x, y in zip(h, a)])
    for x, y, mm in zip(h[valid], a[valid], m[valid]):
        row = np.zeros(n)
        row[idx[x]] += 1.0
        row[idx[y]] -= 1.0
        row[-1] = 1.0
        A += np.outer(row, row)
        b += row * mm
    lam = np.full(n, RIDGE_RATING)
    lam[-1] = RIDGE_HFA
    target = np.zeros(n)
    if prior:
        for t, v in prior.items():
            if t in idx:
                target[idx[t]] = CARRYOVER * v
    beta = np.linalg.solve(A + np.diag(lam), b + lam * target)
    return {t: float(beta[i]) for t, i in idx.items()}, float(beta[-1])


def _solve_scoring(games: pd.DataFrame, teams: list[str], prior: dict | None) -> dict:
    idx = {t: i for i, t in enumerate(teams)}
    k = len(teams)
    n = 2 * k + 2
    A = np.zeros((n, n))
    b = np.zeros(n)
    for r in games.itertuples(index=False):
        if r.home_team not in idx or r.away_team not in idx:
            continue
        for team, opp, pts, home in ((r.home_team, r.away_team, r.home_score, True),
                                     (r.away_team, r.home_team, r.away_score, False)):
            x = np.zeros(n)
            x[idx[team]] += 1.0
            x[k + idx[opp]] -= 1.0
            x[-2] = 1.0
            if home:
                x[-1] = 1.0
            A += np.outer(x, x)
            b += x * pts
    lam = np.full(n, RIDGE_SCORE)
    lam[-1] = RIDGE_HFA
    lam[-2] = 1.0
    target = np.zeros(n)
    target[-2] = 21.0
    if prior:
        for t, v in prior.items():
            if t in idx:
                target[idx[t]] = CARRYOVER * v.get("off", 0.0)
                target[k + idx[t]] = CARRYOVER * v.get("def", 0.0)
    beta = np.linalg.solve(A + np.diag(lam), b + lam * target)
    return {"base": float(beta[-2]), "hfa_pts": float(beta[-1]),
            "off": {t: float(beta[i]) for t, i in idx.items()},
            "def": {t: float(beta[k + i]) for t, i in idx.items()}}


def build_walk_forward(df: pd.DataFrame) -> pd.DataFrame:
    """Attach pre-game ratings, own lines and pre-game SOS to every played game."""
    teams = sorted(set(df.home_team) | set(df.away_team))
    hist_parts = []
    out = []
    prior_r = prior_s = None
    prev_season = None
    for season, sdf in df.groupby("season", sort=True):
        if prev_season is not None and season != prev_season + 1:
            prior_r = prior_s = None
        r_prior, s_prior = prior_r, prior_s
        for week, wdf in sdf.groupby("week", sort=True):
            fit = pd.concat([*hist_parts, sdf[sdf.week < week]]) if hist_parts or len(sdf[sdf.week < week]) else None
            if fit is not None and len(fit) >= 40:
                ratings, hfa = _solve_ratings(fit, teams, r_prior)
                scoring = _solve_scoring(fit, teams, s_prior)
                have_fit = True
            else:
                ratings = {t: 0.0 for t in teams}
                hfa = 1.6
                scoring = {"base": 21.5, "hfa_pts": 0.9, "off": {t: 0.0 for t in teams},
                           "def": {t: 0.0 for t in teams}}
                have_fit = False
            for row in wdf.itertuples(index=False):
                ph = (scoring["base"] + scoring["off"].get(row.home_team, 0.0)
                      - scoring["def"].get(row.away_team, 0.0) + scoring["hfa_pts"])
                pa = (scoring["base"] + scoring["off"].get(row.away_team, 0.0)
                      - scoring["def"].get(row.home_team, 0.0))
                out.append({
                    "game_id": row.game_id, "season": int(season), "week": int(week),
                    "gameday": row.gameday.strftime("%Y-%m-%d") if pd.notna(row.gameday) else "",
                    "home": row.home_team, "away": row.away_team,
                    "home_score": float(row.home_score), "away_score": float(row.away_score),
                    "margin": float(row.margin), "total": float(row.home_score + row.away_score),
                    "spread_line": float(row.spread_line) if np.isfinite(row.spread_line) else None,
                    "total_line": float(row.total_line) if np.isfinite(row.total_line) else None,
                    "home_spread_odds": float(row.home_spread_odds) if np.isfinite(row.home_spread_odds) else None,
                    "away_spread_odds": float(row.away_spread_odds) if np.isfinite(row.away_spread_odds) else None,
                    "over_odds": float(row.over_odds) if np.isfinite(row.over_odds) else None,
                    "under_odds": float(row.under_odds) if np.isfinite(row.under_odds) else None,
                    "div_game": bool(row.div_game) if np.isfinite(row.div_game) else False,
                    "rest_home": float(row.home_rest) if np.isfinite(row.home_rest) else None,
                    "rest_away": float(row.away_rest) if np.isfinite(row.away_rest) else None,
                    "own_margin": float(ratings.get(row.home_team, 0.0) - ratings.get(row.away_team, 0.0) + hfa),
                    "own_total": float(ph + pa), "own_home_pts": float(ph), "own_away_pts": float(pa),
                    "rating_home": float(ratings.get(row.home_team, 0.0)),
                    "rating_away": float(ratings.get(row.away_team, 0.0)),
                    "hfa": float(hfa), "model_fitted": have_fit,
                })
        hist_parts.append(sdf)
        sfit = df[df.season == season]
        if len(sfit) >= 40:
            prior_r, _ = _solve_ratings(sfit, teams, r_prior)
            prior_s = _solve_scoring(sfit, teams, s_prior)
        prev_season = season
    panels = pd.DataFrame(out)

    # Pre-game SOS and recent form, both strictly walk-forward.  Games are in
    # chronological order, so a club's record at the moment of kick-off is
    # exactly the list accumulated from the games already processed.  (An
    # earlier version extended a list forward into later weeks and double
    # counted early games; that is why this is a plain accumulator.)
    sos_h, sos_a, form_h, form_a = [], [], [], []
    seen: dict[str, list] = {}
    for row in panels.itertuples(index=False):
        key_h = f"{row.season}|{row.home}"
        key_a = f"{row.season}|{row.away}"
        sh = seen.get(key_h, [])
        sa = seen.get(key_a, [])
        sos_h.append(float(np.mean([x[0] for x in sh])) if len(sh) >= SOS_MIN_GAMES else None)
        sos_a.append(float(np.mean([x[0] for x in sa])) if len(sa) >= SOS_MIN_GAMES else None)
        form_h.append(recent_window(sh))
        form_a.append(recent_window(sa))
        sign = 1.0 if row.margin > 0 else (-1.0 if row.margin < 0 else 0.0)
        seen.setdefault(key_h, []).append((row.rating_away, sign))
        seen.setdefault(key_a, []).append((row.rating_home, -sign))
    panels["sos_home"] = sos_h
    panels["sos_away"] = sos_a
    panels["form_home"] = form_h
    panels["form_away"] = form_a
    return panels


def recent_window(entries: list) -> float | None:
    if len(entries) < SOS_MIN_GAMES:
        return None
    return float(np.mean([s for _, s in entries[-RECENT_WINDOW:]]))


def current_state(df: pd.DataFrame, panels: pd.DataFrame) -> dict:
    """Today's ratings, SOS to date, luck and remaining-strength picture."""
    season = int(df.season.max())
    teams = sorted(set(df[df.season == season].home_team) | set(df[df.season == season].away_team))
    sfit = df[df.season == season]
    prev = df[df.season == season - 1]
    prior_r = prior_s = None
    if len(prev) >= 40:
        prior_r, _ = _solve_ratings(prev, teams, None)
        prior_s = _solve_scoring(prev, teams, None)
    ratings, hfa = _solve_ratings(sfit, teams, prior_r)
    scoring = _solve_scoring(sfit, teams, prior_s)
    latest = panels[panels.season == season]

    rows = []
    for team in teams:
        g = latest[(latest.home == team) | (latest.away == team)].sort_values(["week", "gameday"])
        if g.empty:
            continue
        opp = g.rating_away.where(g.home == team, g.rating_home)
        sos = float(opp.mean()) if len(opp) >= SOS_MIN_GAMES else None
        pf = float(np.where(g.home == team, g.home_score, g.away_score).sum())
        pa = float(np.where(g.home == team, g.away_score, g.home_score).sum())
        wins = int(sum(1 for r in g.itertuples(index=False)
                       if (r.home_score - r.away_score) * (1 if r.home == team else -1) > 0))
        close = [(r.home_score - r.away_score) * (1 if r.home == team else -1)
                 for r in g.itertuples(index=False) if abs(r.home_score - r.away_score) <= 3]
        pyth = pf ** PYTHAGOREAN_EXPONENT / (pf ** PYTHAGOREAN_EXPONENT + pa ** PYTHAGOREAN_EXPONENT) \
            if pf + pa > 0 else None
        row = {
            "team": team, "games": int(len(g)), "wins": wins, "losses": int(len(g) - wins),
            "points_for": round(pf, 1), "points_against": round(pa, 1), "diff": round(pf - pa, 1),
            "rating": round(ratings.get(team, 0.0), 3),
            "off": round(scoring["off"].get(team, 0.0), 3),
            "def": round(scoring["def"].get(team, 0.0), 3),
            "sos_to_date": round(sos, 3) if sos is not None else None,
            "sos_games": int(len(opp)),
            "close_games": len(close), "close_wins": int(sum(1 for c in close if c > 0)),
            "close_win_pct": round(sum(1 for c in close if c > 0) / len(close), 3) if close else None,
            "pyth_wins": round(pyth * len(g), 2) if pyth is not None else None,
            "luck_wins": round(wins - pyth * len(g), 2) if pyth is not None else None,
        }
        rows.append(row)
    for i, r in enumerate(sorted(rows, key=lambda x: -x["rating"]), 1):
        r["rating_rank"] = i
    # remaining opponents come from the official Week 10 snapshot only
    official = json.load(open(OFFICIAL, encoding="utf-8"))
    remaining = {}
    for game in official["week10"]["games"]:
        if game.get("result"):
            continue
        remaining.setdefault(game["home"], []).append(game["away"])
        remaining.setdefault(game["away"], []).append(game["home"])
    rating = {r["team"]: r["rating"] for r in rows}
    # The official page uses the club-logo codes; the nflverse files use their own.
    # Only "AZ" differs (nfl.com AZ, nflverse ARI); everything else matches.
    for r in rows:
        opps = [ALIASES.get(o, o) for o in remaining.get(r["team"], [])]
        vals = [rating.get(o) for o in opps if o in rating]
        r["next_opponents"] = opps
        r["next_opponent_rating"] = round(float(np.mean(vals)), 3) if vals else None
    return {"season": season, "hfa": round(hfa, 3), "base_points": round(scoring["base"], 3),
            "hfa_points": round(scoring["hfa_pts"], 3), "teams": rows}


# ---------------------------------------------------------------- evaluation
def validate(panels: pd.DataFrame) -> dict:
    df = panels[panels.spread_line.notna()].copy()
    df["err_own"] = df.own_margin - df.margin
    df["err_mkt"] = df.spread_line - df.margin
    df = df[df.total_line.notna()].copy()
    df["err_own_tot"] = df.own_total - df.total
    df["err_mkt_tot"] = df.total_line - df.total

    def block(d: pd.DataFrame) -> dict:
        if not len(d):
            return {"games": 0}
        return {
            "games": int(len(d)),
            "spread_mae_own": round(float(d.err_own.abs().mean()), 3),
            "spread_mae_market": round(float(d.err_mkt.abs().mean()), 3),
            "spread_rmse_own": round(float(np.sqrt((d.err_own ** 2).mean())), 3),
            "spread_rmse_market": round(float(np.sqrt((d.err_mkt ** 2).mean())), 3),
            "total_mae_own": round(float(d.err_own_tot.abs().mean()), 3),
            "total_mae_market": round(float(d.err_mkt_tot.abs().mean()), 3),
            "bias_spread_own": round(float(d.err_own.mean()), 3),
            "bias_total_own": round(float(d.err_own_tot.mean()), 3),
        }

    out = {
        "all_seasons": block(df),
        "holdout": block(df[df.season.isin(HOLDOUT_SEASONS)]),
        "holdout_seasons": list(HOLDOUT_SEASONS),
        "by_season": [],
        "calibration": [],
        "correlation_model_market": pearson(df.own_margin, df.spread_line),
        "rule": "Own line is produced walk-forward. Market MAE/RMSE is the closing line's own error on the same games, so the comparison is like-for-like.",
    }
    for season, sdf in df.groupby("season"):
        row = block(sdf)
        row["season"] = int(season)
        out["by_season"].append(row)
    for lo, hi in [(-30, -7), (-7, -3), (-3, 0), (0, 3), (3, 7), (7, 30)]:
        b = df[(df.own_margin >= lo) & (df.own_margin < hi)]
        out["calibration"].append({
            "bucket": f"[{lo},{hi})", "games": int(len(b)),
            "mean_own_margin": round(float(b.own_margin.mean()), 2) if len(b) else None,
            "mean_actual_margin": round(float(b.margin.mean()), 2) if len(b) else None,
        })
    return out


# ---------------------------------------------------------------- strategies
def _price_dec(american: float | None) -> float | None:
    if american is None or not np.isfinite(american) or american == 0:
        return None
    return 1.0 + (american / 100.0 if american > 0 else 100.0 / abs(american))


def _resolve(row: dict, side: str, market: str):
    """(decimal, won, push) or None when the price is not observed."""
    if market == "spread":
        price = row["home_spread_odds"] if side == "home" else row["away_spread_odds"]
        line = row["spread_line"]
    else:
        price = row["over_odds"] if side == "over" else row["under_odds"]
        line = row["total_line"]
    dec = _price_dec(price)
    if dec is None or line is None:
        return None
    if market == "spread":
        # Verified convention: nflverse spread_line is the home club's expected
        # margin, positive when the home club is favoured (the site's Week 10
        # table prints spread_line 1.5 for WAS @ NYG as "NYG -1.5").  Therefore
        # the home club covers when margin > spread_line.
        adj = row["margin"] - line
        if side == "away":
            adj = -adj
    else:
        adj = (row["total"] - line) * (1 if side == "over" else -1)
    if abs(adj) < 1e-9:
        return (dec, None, True)
    return (dec, adj > 0, False)


# Rules are frozen here, before any scoring. Each returns [(side, market), ...].
def _r(edge_thresh, market="spread"):
    def f(row):
        if market == "spread":
            edge = row["own_margin"] - row["spread_line"]
        else:
            edge = row["own_total"] - row["total_line"]
        if edge is None or abs(edge) < edge_thresh:
            return []
        if market == "spread":
            return [("home" if edge > 0 else "away", "spread")]
        return [("over" if edge > 0 else "under", "total")]
    return f


def _fade_lucky(row):
    if row["home_fav"] and row["luck_home"] is not None and row["luck_home"] >= 1.5:
        return [("away", "spread")]
    if row["away_fav"] and row["luck_away"] is not None and row["luck_away"] >= 1.5:
        return [("home", "spread")]
    return []


def _back_unlucky(row):
    if (not row["home_fav"]) and row["luck_home"] is not None and row["luck_home"] <= -1.5:
        return [("home", "spread")]
    if (not row["away_fav"]) and row["luck_away"] is not None and row["luck_away"] <= -1.5:
        return [("away", "spread")]
    return []


def _sos_both_tough(row):
    if row["sos_home"] is not None and row["sos_away"] is not None \
            and row["sos_home"] > 0 and row["sos_away"] > 0:
        return [("under", "total")]
    return []


def _sos_both_weak(row):
    if row["sos_home"] is not None and row["sos_away"] is not None \
            and row["sos_home"] < 0 and row["sos_away"] < 0:
        return [("over", "total")]
    return []


def _div_dog_positive_edge(row):
    if row["div_game"] and row["spread_line"] is not None and row["spread_line"] <= -6.5 \
            and (row["rating_away"] - row["rating_home"]) > 0:
        return [("away", "spread")]
    return []


def _form_contrarian(row):
    if row["form_home"] is None or row["form_away"] is None or row["spread_line"] is None:
        return []
    gap = row["form_home"] - row["form_away"]
    if gap <= -0.60:
        return [("home", "spread")]
    if gap >= 0.60:
        return [("away", "spread")]
    return []


RULES = [
    ("X01 Own spread edge >= 1.5 pts", _r(1.5)),
    ("X02 Own spread edge >= 3.0 pts", _r(3.0)),
    ("X03 Own total edge >= 3.0 pts", _r(3.0, "total")),
    ("X04 Own total edge >= 5.0 pts", _r(5.0, "total")),
    ("X05 Fade a club with a lucky record (luck >= +1.5 wins) when it is favoured", _fade_lucky),
    ("X06 Back a club with an unlucky record (luck <= -1.5 wins) when it is an underdog", _back_unlucky),
    ("X07 Own rating edge vs market >= 2.0 pts", _r(2.0)),
    ("X08 Under when both clubs' SOS to date is above league average", _sos_both_tough),
    ("X09 Over when both clubs' SOS to date is below league average", _sos_both_weak),
    ("X10 Divisional underdog of 6.5+ with a positive own-rating edge", _div_dog_positive_edge),
    ("X11 Recency: back the club with the better last-5 form when it is an underdog", _form_contrarian),
]


def descriptor_frame(panels: pd.DataFrame) -> pd.DataFrame:
    """Point-in-time luck (wins minus Pythagorean wins) before each kick-off."""
    df = panels.sort_values(["season", "week", "gameday", "game_id"])
    teams = sorted(set(df.home) | set(df.away))
    rows = []
    for season, sdf in df.groupby("season"):
        weeks = sorted(sdf.week.unique())
        for week in weeks:
            done = sdf[sdf.week < week]
            if done.empty:
                continue
            for team in teams:
                g = done[(done.home == team) | (done.away == team)]
                if g.empty:
                    continue
                wins = 0
                pf = pa = 0.0
                for r in g.itertuples(index=False):
                    home = r.home == team
                    pf += r.home_score if home else r.away_score
                    pa += r.away_score if home else r.home_score
                    if (r.home_score - r.away_score) * (1 if home else -1) > 0:
                        wins += 1
                pyth = pf ** PYTHAGOREAN_EXPONENT / (pf ** PYTHAGOREAN_EXPONENT + pa ** PYTHAGOREAN_EXPONENT)
                rows.append({"season": int(season), "week": int(week), "team": team,
                             "wins_to_date": wins, "pyth_to_date": round(pyth * len(g), 4),
                             "luck_to_date": round(wins - pyth * len(g), 4)})
    return pd.DataFrame(rows)


def score_rules(panels: pd.DataFrame, desc: pd.DataFrame) -> tuple[dict, dict]:
    """Score every frozen rule once. Prices must be observed or no bet is scored."""
    luck = {(int(r.season), int(r.week), r.team): r.luck_to_date for r in desc.itertuples(index=False)}
    all_bets = {}
    results = []
    games_considered = 0
    for name, decide in RULES:
        bets = []
        for r in panels.itertuples(index=False):
            if r.spread_line is None or not np.isfinite(r.spread_line):
                continue
            row = {
                "season": r.season, "week": r.week, "game_id": r.game_id,
                "spread_line": r.spread_line, "total_line": r.total_line,
                "own_margin": r.own_margin, "own_total": r.own_total,
                "margin": r.margin, "total": r.total,
                "home_spread_odds": r.home_spread_odds, "away_spread_odds": r.away_spread_odds,
                "over_odds": r.over_odds, "under_odds": r.under_odds,
                "home_fav": r.spread_line < 0, "away_fav": r.spread_line > 0,
                "luck_home": luck.get((r.season, r.week, r.home)),
                "luck_away": luck.get((r.season, r.week, r.away)),
                "sos_home": r.sos_home if np.isfinite(r.sos_home) else None,
                "sos_away": r.sos_away if np.isfinite(r.sos_away) else None,
                "rating_home": r.rating_home, "rating_away": r.rating_away,
                "form_home": r.form_home if np.isfinite(r.form_home) else None,
                "form_away": r.form_away if np.isfinite(r.form_away) else None,
                "div_game": r.div_game,
            }
            for side, market in decide(row):
                res = _resolve(row, side, market)
                if res is None:
                    continue
                dec, won, push = res
                if push:
                    continue
                bets.append({"game_id": r.game_id, "season": int(r.season), "week": int(r.week),
                             "side": side, "market": market, "decimal": dec,
                             "won": bool(won), "profit": (dec - 1.0) if won else -1.0})
        games_considered = len(panels)
        b = pd.DataFrame(bets)
        all_bets[name] = b
        if b.empty:
            results.append({"strategy": name, "n_bets": 0, "status": "FAIL", "gates_passed": 0,
                            "note": "the rule never fired on a game with an observed price",
                            "p_value": 1.0, "holdout_roi_pct": None, "roi_ci95": None,
                            "seasons_positive": 0, "seasons_played": 0, "hit_rate": None,
                            "break_even_hit_rate": None})
            continue
        n = len(b)
        wins = int(b.won.sum())
        roi = float(b.profit.mean())
        be = float((1.0 / b.decimal).mean())
        sd = float(b.profit.std(ddof=1)) if n > 1 else float("nan")
        t = roi / (sd / math.sqrt(n)) if n > 1 and sd > 0 else float("nan")
        p = _two_sided_normal_p(t) if np.isfinite(t) else 1.0
        hold = b[b.season.isin(HOLDOUT_SEASONS)]
        seasons = [{"season": int(s), "n_bets": int(len(g)),
                    "hit_rate": round(float(g.won.mean()), 4),
                    "roi_pct": round(float(g.profit.mean()) * 100, 3)}
                   for s, g in b.groupby("season")]
        results.append({
            "strategy": name, "n_bets": n, "considered_games": games_considered,
            "wins": wins, "losses": n - wins,
            "hit_rate": round(wins / n, 4),
            "break_even_hit_rate": round(be, 4),
            "profit_units": round(float(b.profit.sum()), 3),
            "roi_pct": round(roi * 100, 3),
            "avg_decimal": round(float(b.decimal.mean()), 4),
            "t_stat": round(float(t), 4) if np.isfinite(t) else None,
            "p_value": round(float(p), 6),
            "roi_ci95": (bootstrap_ci(b.profit.values) or {}).get("ci95"),
            "holdout_n": int(len(hold)),
            "holdout_roi_pct": round(float(hold.profit.mean()) * 100, 3) if len(hold) else None,
            "seasons": seasons,
            "seasons_positive": sum(1 for s in seasons if s["roi_pct"] > 0),
            "seasons_played": len(seasons),
        })
    qs = benjamini_hochberg([r.get("p_value") if r.get("p_value") is not None else 1.0 for r in results])
    for r, q in zip(results, qs):
        r["bh_q"] = round(q, 6)
        g = {"G1": True, "G2": r["n_bets"] > 0, "G3": r["n_bets"] >= MIN_BETS,
             "G4": (r.get("hit_rate") or 0) > (r.get("break_even_hit_rate") or 1),
             "G5": q < 0.05, "G6": (r.get("holdout_roi_pct") or -1) > 0,
             "G7": (r.get("seasons_positive", 0) / max(1, r.get("seasons_played", 1))) >= 0.60,
             "G8": bool(r.get("roi_ci95") and r["roi_ci95"][0] > 0)}
        r["gates"] = g
        r["gates_passed"] = sum(1 for v in g.values() if v)
        r["status"] = ("PASS" if r["gates_passed"] == 8
                       else "WATCH" if all(g[k] for k in ("G1", "G2", "G3", "G8"))
                       else "FAIL")
    results.sort(key=lambda r: (-(r.get("roi_ci95") or [0, 0])[0], -r["gates_passed"], -r["n_bets"]))
    payload = {
        "gate_definitions": [
            {"id": "G1", "name": "walk-forward", "rule": "inputs known before kick-off; the fit uses earlier games only"},
            {"id": "G2", "name": "observed prices", "rule": "every scored bet carries a price taken from the source file; no -110 default"},
            {"id": "G3", "name": "minimum sample", "rule": f"at least {MIN_BETS} scored bets"},
            {"id": "G4", "name": "beats break-even", "rule": "hit rate above the break-even implied by the prices actually taken"},
            {"id": "G5", "name": "multiple testing", "rule": f"Benjamini-Hochberg q < 0.05 across the {len(RULES)} rules tested"},
            {"id": "G6", "name": "holdout", "rule": f"positive ROI in untouched seasons {list(HOLDOUT_SEASONS)}"},
            {"id": "G7", "name": "season stability", "rule": "positive in at least 60% of the seasons played"},
            {"id": "G8", "name": "confidence", "rule": "95% bootstrap interval on ROI excludes zero"},
        ],
        "n_rules_tested": len(RULES),
        "min_bets": MIN_BETS,
        "strategies": results,
        "totals": {"bets_scored": int(sum(r["n_bets"] for r in results)),
                   "rules": len(results),
                   "pass": sum(1 for r in results if r["status"] == "PASS"),
                   "watch": sum(1 for r in results if r["status"] == "WATCH"),
                   "fail": sum(1 for r in results if r["status"] == "FAIL"),
                   "games_in_sample": int(len(panels)),
                   "seasons": [int(panels.season.min()), int(panels.season.max())]},
    }
    return payload, all_bets


def parlay_register(panels: pd.DataFrame, all_bets: dict) -> dict:
    """Two-leg combos of any two rules that fired on the same game.

    Combo price = product of the two observed leg prices.  That is a constructed
    price and is labelled as such: a book's parlay price includes its own margin
    and may be priced differently.  Correlations are therefore the useful output
    here; the constructed ROI is reported for completeness only.
    """
    pairs = []
    for a, b in combinations(all_bets.keys(), 2):
        da, db = all_bets[a], all_bets[b]
        if da is None or db is None or da.empty or db.empty:
            continue
        m = da.merge(db, on="game_id", suffixes=("_a", "_b"))
        if len(m) < 50:
            continue
        dec = m.decimal_a * m.decimal_b
        won_both = m.won_a & m.won_b
        profit = np.where(won_both, dec - 1.0, -1.0)
        indep = float(m.won_a.mean() * m.won_b.mean())
        pairs.append({
            "legs": [a, b], "n_parlays": int(len(m)),
            "hit_rate": round(float(won_both.mean()), 4),
            "hit_rate_if_independent": round(indep, 4),
            "correlation_ratio": round(float(won_both.mean()) / indep, 4) if indep else None,
            "avg_decimal": round(float(dec.mean()), 4),
            "constructed_roi_pct": round(float(profit.mean()) * 100, 3),
            "phi": pearson(m.won_a.astype(float), m.won_b.astype(float)),
        })
    pairs.sort(key=lambda p: -(p["phi"]["r"] if p["phi"] else 0))
    return {
        "method": "Two-leg parlay combos from every pair of frozen rules that fired on the same game. "
                  "Price = product of the two observed leg prices (constructed, not a sportsbook quote).",
        "pairs_scored": len(pairs),
        "pairs_with_positive_phi": sum(1 for p in pairs if p["phi"] and p["phi"]["r"] > 0
                                       and p["phi"]["ci95"][0] > 0),
        "pairs": pairs,
    }


def correlation_register(panels: pd.DataFrame) -> dict:
    df = panels[panels.spread_line.notna()].copy()
    df["ats_home"] = df.margin + df.spread_line
    pairs = [
        ("C-SOS-01", "Own rating difference vs closing spread", df.rating_home - df.rating_away, df.spread_line),
        ("C-SOS-02", "Own rating difference vs actual margin", df.rating_home - df.rating_away, df.margin),
        ("C-SOS-03", "Own total vs closing total", df.own_total, df.total_line),
        ("C-SOS-04", "Own total vs actual total", df.own_total, df.total),
        ("C-SOS-05", "Home rest days vs margin", df.rest_home, df.margin),
        ("C-SOS-06", "Rest differential vs margin", df.rest_home - df.rest_away, df.margin),
        ("C-SOS-07", "This is deliberately blank: a pre-game rating difference cannot be correlated with an ATS result, because the rating difference is what the own line is made of -- the two series are the same number and the correlation would be a tautology",
         None, None),
        ("C-SOS-08", "Sum of own predicted points vs actual total", df.own_home_pts + df.own_away_pts, df.total),
    ]
    reg = []
    for cid, label, x, y in pairs:
        r = pearson(x, y)
        reg.append({"id": cid, "relationship": label, "value": r,
                    "reading": "published" if r else "blank: fewer than 4 paired observations or no variance"})
    return {"method": "Pearson r, Fisher-z 95% CI, n reported. Values publish only when n >= 4 and both series vary.",
            "register": reg}


def prop_correlations() -> dict:
    """Same-game correlations a prop-combo strategy would need (no price, no scoring)."""
    if not os.path.exists(PLAYER_WEEK):
        return {"status": "blank: the player-week file is not present"}
    p = pd.read_csv(PLAYER_WEEK, low_memory=False)
    p = p[p.season_type == "REG"]
    qb = p[p.position == "QB"].groupby(["game_id", "team"])["passing_yards"].sum().rename("pass")
    rec = p[p.position.isin(["WR", "TE"])].groupby(["game_id", "team"])["receiving_yards"].sum().rename("rec")
    rush = p[p.position == "RB"].groupby(["game_id", "team"])["rushing_yards"].sum().rename("rush")
    same = pd.concat([qb, rec, rush], axis=1).dropna()
    r1 = pearson(same["pass"], same["rec"])
    r2 = pearson(same["rec"], same["rush"])
    # opponent rushing vs this club's receiving
    opp = p[["game_id", "team", "opponent_team"]].drop_duplicates()
    m = rec.reset_index().merge(opp, on=["game_id", "team"])
    m = m.merge(rush.reset_index().rename(columns={"team": "opponent_team", "rush": "opp_rush"}),
                on=["game_id", "opponent_team"])
    r3 = pearson(m["rec"], m["opp_rush"])
    return {
        "source": "data/s9cb/player_week.csv (nflverse weekly player stats)",
        "price_status": "BLANK: no official or book price exists in this repository's sources for any player prop, "
                        "so no prop combo is scored and no profit is claimed.",
        "register": [
            {"id": "P-01", "relationship": "Club passing yards vs same-club receiver yards (same game)", "value": r1},
            {"id": "P-02", "relationship": "Club receiver yards vs same-club rushing yards (same game)", "value": r2},
            {"id": "P-03", "relationship": "Club receiver yards vs opponent rushing yards (same game)", "value": r3},
        ],
    }


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    df, integrity = load_games()
    panels = build_walk_forward(df)
    state = current_state(df, panels)
    desc = descriptor_frame(panels)
    validation = validate(panels)
    strategies, all_bets = score_rules(panels, desc)
    parlays = parlay_register(panels, all_bets)
    corr = correlation_register(panels)
    props = prop_correlations()

    params = {"ridge_rating": RIDGE_RATING, "ridge_hfa": RIDGE_HFA, "ridge_score": RIDGE_SCORE,
              "carryover": CARRYOVER, "holdout_seasons": list(HOLDOUT_SEASONS),
              "min_bets": MIN_BETS, "bootstrap": BOOTSTRAP, "seed": SEED,
              "sos_min_games": SOS_MIN_GAMES, "recent_window": RECENT_WINDOW,
              "pythagorean_exponent": PYTHAGOREAN_EXPONENT}
    rules_blob = json.dumps([{"name": n, "function": f.__name__} for n, f in RULES]
                            + [{"thresholds": [1.5, 3.0, 5.0, 2.0]}, params], sort_keys=True)
    meta = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session": "ca779bcc-nfl1",
        "inputs": integrity,
        "frozen_parameters": params,
        "rules_tested": len(RULES),
        "preregistration_sha256": hashlib.sha256(rules_blob.encode()).hexdigest(),
        "preregistration_note": "Hash of the rule names and frozen parameters. Changing a threshold or adding a rule changes this hash, which is how a reader can tell the rules were fixed before scoring.",
        "code_sha256": _sha256(os.path.abspath(__file__)),
        "official_sources": {"standings": OFFICIAL_STANDINGS_URL,
                             "week10_schedule": OFFICIAL_SCHEDULE_W10_URL,
                             "injuries": OFFICIAL_INJURIES_URL,
                             "nflverse_release": NV_SCHEDULES},
        "limitations": [
            "The nflverse closing line is a consensus number, not a book quote; no official league odds exist.",
            "Prop markets have no price in these sources, so prop combos cannot be scored.",
            "Remaining opponents come from the official Week 10 snapshot only; the source file carries no future fixtures.",
            "Ratings are linear; injuries, weather and quarterback changes enter only through the score.",
        ],
    }
    payloads = {
        "meta.json": meta,
        "current_state.json": state,
        "validation.json": validation,
        "strategies.json": strategies,
        "parlays.json": parlays,
        "correlations.json": corr,
        "props.json": props,
        "panels.json": {"rows": int(len(panels)), "seasons": [int(panels.season.min()), int(panels.season.max())],
                        "note": "Last 60 rows only; the full panel is regenerated by analysis/strength.py.",
                        "sample": json.loads(panels.tail(60).to_json(orient="records"))},
    }
    for name, payload in payloads.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1)
            f.write("\n")
    print(f"wrote {len(payloads)} files to data/strength/")
    print("provenance hash match:", integrity["matches_provenance"],
          "| rows in file:", integrity["rows_in_file"], "| played:", integrity["played_games_used"])
    print("validation all:", json.dumps(validation["all_seasons"]))
    print("validation holdout:", json.dumps(validation["holdout"]))
    print("strategies:", json.dumps(strategies["totals"]))
    print("parlays:", parlays["pairs_scored"], "pairs;", parlays["pairs_with_positive_phi"], "with CI above 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
