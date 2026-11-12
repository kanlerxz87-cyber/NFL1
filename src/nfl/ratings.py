"""Team ratings derived ONLY from verified NFL.com standings cells.

Every output is tagged with a provenance tier. Where a required input does not
exist in verified form the output is None plus an explicit BLOCKED reason -
the module refuses to invent a number.
"""
from __future__ import annotations

from typing import Any

from . import ingest, stats, verify
from .provenance import DERIVED, MODELED, UNAVAILABLE, VERIFIED

#: Cells the verification harness proved internally inconsistent on the official
#: page. They are published verbatim but excluded from every computation.
DISPUTED_CELLS = {("IND", "div"), ("PHI", "div"), ("WAS", "non_conf")}


def _usable(team: str, field: str) -> bool:
    return (team, field) not in DISPUTED_CELLS


def team_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        gp = (r["w"] or 0) + (r["l"] or 0) + (r["t"] or 0)
        rec = {
            "team_abbr": r["team_abbr"], "conference": r["conference"],
            "division": r["division"], "gp": gp,
            "w": r["w"], "l": r["l"], "t": r["t"], "win_pct": r["pct"],
            "pf": r["pf"], "pa": r["pa"], "net_pts": r["net_pts"],
            "home": r["home"], "road": r["road"], "strk": r["strk"],
            "div": r["div"], "conf": r["conf"], "non_conf": r["non_conf"],
            "last5": r["last5"], "conf_pct": r["conf_pct"], "div_pct": r["div_pct"],
            # Cells the harness proved internally inconsistent on the official
            # page are published verbatim but never used and never displayed as
            # though they were sound.
            "div_disputed": not _usable(r["team_abbr"], "div"),
            "non_conf_disputed": not _usable(r["team_abbr"], "non_conf"),
            "source_url": r["source_url"],
        }
        if gp:
            rec.update({
                "ppg": round(r["pf"] / gp, 3),
                "papg": round(r["pa"] / gp, 3),
                "net_pg": round(r["net_pts"] / gp, 3),
                "home_win_pct": (round((r["home_w"] + 0.5 * (r["home_t"] or 0)) /
                                       ((r["home_w"] or 0) + (r["home_l"] or 0) + (r["home_t"] or 0)), 3)
                                 if ((r["home_w"] or 0) + (r["home_l"] or 0) + (r["home_t"] or 0)) else None),
                "road_win_pct": (round((r["road_w"] + 0.5 * (r["road_t"] or 0)) /
                                       ((r["road_w"] or 0) + (r["road_l"] or 0) + (r["road_t"] or 0)), 3)
                                 if ((r["road_w"] or 0) + (r["road_l"] or 0) + (r["road_t"] or 0)) else None),
                "conf_win_pct": r["conf_pct"],
                # DIV is disputed for IND and PHI -> excluded, left blank.
                "div_win_pct": (r["div_pct"] if _usable(r["team_abbr"], "div") else None),
                "last5": r["last5"],
                "streak_signed": _streak(r["strk"]),
            })
        else:
            rec.update({k: None for k in ("ppg", "papg", "net_pg", "home_win_pct",
                                          "road_win_pct", "conf_win_pct",
                                          "div_win_pct", "last5", "streak_signed")})
        out.append(rec)
    return out


def _streak(s: str) -> int | None:
    if not s or len(s) < 2 or s[-1] not in "WL":
        return None
    try:
        n = int(s[:-1])
    except ValueError:
        return None
    return n if s[-1] == "W" else -n


def fit_pythagorean(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Fit the Pythagorean exponent on the 32 verified rows.

    win% ~ pf**k / (pf**k + pa**k).  k is found by golden-section search on the
    sum of squared errors. This is a genuine least-squares fit to official data
    (one free parameter, 32 observations), so it is DERIVED, not assumed.
    """
    xs = [(r["pf"], r["pa"], r["pct"]) for r in rows
          if r["pf"] and r["pa"] and r["pct"] is not None
          and (r["w"] or 0) + (r["l"] or 0) + (r["t"] or 0) > 0]

    def sse(k: float) -> float:
        return sum((p ** k / (p ** k + a ** k) - w) ** 2 for p, a, w in xs)

    if len(xs) < 5:
        return {"status": "NOT_FITTED", "reason": "fewer than 5 usable rows"}
    k, err = stats.golden_section_min(sse, 0.5, 6.0)
    preds = [p ** k / (p ** k + a ** k) for p, a, _ in xs]
    acts = [w for _, _, w in xs]
    _, b, r2 = stats.linfit(preds, acts)
    lo, hi = stats.bootstrap_ci(preds, acts, lambda x, y: 0.0, draws=1) if False else (None, None)
    # bootstrap the exponent itself
    import random
    rng = random.Random(20261112)
    ks = []
    for _ in range(600):
        sample = [xs[rng.randrange(len(xs))] for _ in xs]
        def s2(kk: float, s=sample) -> float:
            return sum((p ** kk / (p ** kk + a ** kk) - w) ** 2 for p, a, w in s)
        ks.append(stats.golden_section_min(s2, 0.5, 6.0, tol=1e-5)[0])
    ks.sort()
    lo = ks[int(0.025 * len(ks))]
    hi = ks[int(0.975 * len(ks))]
    return {
        "status": "FITTED", "exponent": round(k, 4),
        "ci95": [round(lo, 4), round(hi, 4)],
        "n": len(xs), "sse": round(err, 6),
        "mae_win_pct": round(stats.mae(preds, acts), 4),
        "rmse_win_pct": round(stats.rmse(preds, acts), 4),
        "calibration_slope": round(b, 4), "r2": round(r2, 4),
        "tier": DERIVED,
        "source_url": ingest.STANDINGS_URL,
        "note": "Exponent fitted by least squares on the 32 official 2026 rows; "
                "not borrowed from any external study.",
    }


def pythagorean(r: dict[str, Any], k: float) -> float | None:
    if not r.get("pf") or not r.get("pa"):
        return None
    return round(r["pf"] ** k / (r["pf"] ** k + r["pa"] ** k), 4)


def home_advantage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """League home win rate, computed from the official HOME/ROAD cells only."""
    hw = sum(r["home_w"] or 0 for r in rows)
    hl = sum(r["home_l"] or 0 for r in rows)
    ht = sum(r["home_t"] or 0 for r in rows)
    gp = hw + hl + ht
    rw = sum(r["road_w"] or 0 for r in rows)
    if gp == 0:
        return {"status": "UNAVAILABLE"}
    rate = (hw + 0.5 * ht) / gp
    # Wilson score interval - the honest uncertainty on n home games.
    import math
    z = 1.959963985
    denom = 1 + z * z / gp
    centre = (rate + z * z / (2 * gp)) / denom
    half = z * math.sqrt(rate * (1 - rate) / gp + z * z / (4 * gp * gp)) / denom
    return {
        "home_games": gp, "home_wins": hw, "home_losses": hl, "home_ties": ht,
        "road_wins": rw,
        "home_win_rate": round(rate, 4),
        "ci95_wilson": [round(centre - half, 4), round(centre + half, 4)],
        "tier": DERIVED, "source_url": ingest.STANDINGS_URL,
        "note": "Counts each team's official HOME cell as one observation. Games "
                "are not independent observations (every game contributes one "
                "home and one road record), so this interval is indicative only.",
    }


def home_advantage_points(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Home field expressed in POINTS - required to turn ratings into a spread.

    Needs game-level home/away point margins. Not obtainable from the official
    sources reachable in this environment, so it is deliberately left blank.
    """
    return {
        "value": None, "tier": UNAVAILABLE,
        "reason": "Requires game-level final scores with home/away designation "
                  "for a full season or more. NFL.com publishes these only on "
                  "per-week score pages, which were not obtainable within this "
                  "session's budget; the NFL's bulk feed and the nflverse "
                  "release assets are both unreachable from the build "
                  "environment's network allowlist.",
        "resolving_source": "https://www.nfl.com/scores/2026/week-1 .. week-9 "
                            "(official) or https://github.com/nflverse/nflverse-data "
                            "release 'schedules' (games.csv)",
    }


def week_slate(metrics: list[dict[str, Any]],
               schedule: list[dict[str, Any]],
               k: float) -> list[dict[str, Any]]:
    """Origination board for one week.

    rating_gap is DERIVED arithmetic on verified cells and is published.
    spread / total / win_probability are BLOCKED because they need at least one
    input that does not exist in verified form. They are published as blank.
    """
    m = {r["team_abbr"]: r for r in metrics}
    out = []
    for g in schedule:
        a, h = m.get(g["away_abbr"]), m.get(g["home_abbr"])
        row = {
            "week": g["week"], "game_date": g["game_date"], "day": g["day"],
            "kickoff_et": g["kickoff_et"], "broadcast": g["broadcast"],
            "venue_status": g["venue_status"],
            "away_abbr": g["away_abbr"], "home_abbr": g["home_abbr"],
            "source_url": g["source_url"],
            "away_record": f'{a["w"]}-{a["l"]}' + (f'-{a["t"]}' if a["t"] else "") if a else None,
            "home_record": f'{h["w"]}-{h["l"]}' + (f'-{h["t"]}' if h["t"] else "") if h else None,
        }
        if a and h and a.get("net_pg") is not None and h.get("net_pg") is not None:
            row["rating_gap_home_minus_away"] = round(h["net_pg"] - a["net_pg"], 3)
            row["rating_gap_tier"] = DERIVED
            row["pyth_home"] = pythagorean({"pf": h["pf"], "pa": h["pa"]}, k)
            row["pyth_away"] = pythagorean({"pf": a["pf"], "pa": a["pa"]}, k)
            row["pyth_gap"] = round(row["pyth_home"] - row["pyth_away"], 4)
            row["naive_total"] = round(a["ppg"] + h["ppg"], 2)
            row["naive_total_tier"] = DERIVED
            row["naive_total_note"] = ("Arithmetic sum of the two clubs' verified "
                                       "points-per-game. NOT a validated betting total.")
        else:
            for f in ("rating_gap_home_minus_away", "pyth_home", "pyth_away",
                      "pyth_gap", "naive_total"):
                row[f] = None
            row["rating_gap_tier"] = UNAVAILABLE
        row["spread"] = None
        row["spread_tier"] = UNAVAILABLE
        row["spread_blocked_by"] = "home_advantage_points"
        row["win_probability"] = None
        row["win_probability_tier"] = UNAVAILABLE
        row["win_probability_blocked_by"] = ("mapping from rating gap to win "
                                             "probability requires fitted "
                                             "game-level data")
        row["market_line"] = None
        row["market_line_tier"] = UNAVAILABLE
        row["market_line_blocked_by"] = "no licensed odds feed reachable"
        out.append(row)
    return out


def build() -> dict[str, Any]:
    rows = ingest.standings()
    metrics = team_metrics(rows)
    pyth = fit_pythagorean(rows)
    k = pyth["exponent"] if pyth.get("status") == "FITTED" else None
    for r in metrics:
        r["pyth_win_pct"] = pythagorean(r, k) if k else None
        r["pyth_win_pct_tier"] = DERIVED if r.get("pyth_win_pct") is not None else UNAVAILABLE
        r["pyth_delta"] = (round(r["pyth_win_pct"] - r["win_pct"], 4)
                           if r.get("pyth_win_pct") is not None and r.get("win_pct") is not None
                           else None)
        for f in ("ppg", "papg", "net_pg", "home_win_pct", "road_win_pct",
                  "pyth_win_pct", "pyth_delta", "streak_signed"):
            r.setdefault(f + "_tier", DERIVED if r.get(f) is not None else UNAVAILABLE)
        r["win_pct_tier"] = VERIFIED
    return {
        "metrics": metrics, "pythagorean_fit": pyth,
        "home_advantage_win_rate": home_advantage(rows),
        "home_advantage_points": home_advantage_points(rows),
        "week10_board": week_slate(metrics, ingest.schedule(), k) if k else [],
        "verification": verify.run(),
    }
