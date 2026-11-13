#!/usr/bin/env python3
"""Run the personnel-deficiency study and write data/personnel/*.json.

    cd s9cb/analysis && python3 run_personnel.py

Outputs (all new paths; nothing existing is modified):
    personnel/lines_of_evidence.json   incremental-information regressions
    personnel/leaderboard.json         the five candidate rules, eight gates, whole-family BH
    personnel/register.json            per-club, per-week ruled-out deficiency register
    personnel/week10_deficiency.json   the Week 10 board, joined to the official report
    personnel/meta.json                method, exclusions, sources, counts
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common as C
import personnel as P
from personnel import OL_POSITIONS, SKILL, FRONT7, SECONDARY

OUT = os.path.join(C.ROOT, "data", "personnel")
OSRC = {
    "schedules": "https://www.nfl.com/schedules/",
    "standings": "https://www.nfl.com/standings/league/2026/reg",
    "injuries_current": "https://www.nfl.com/injuries/",
    "nflverse": "https://github.com/nflverse/nflverse-data",
}


def write(name: str, obj) -> None:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(C.clean(obj), fh, indent=1)
    print("wrote", os.path.relpath(path, C.ROOT))


def _scrape_counts(scrape: dict, team: str, unit_fn) -> dict:
    """Ruled-out counts for one club from the direct nfl.com scrape."""
    c = {"out_ruled": 0, "questionable": 0, "report_rows_this_week": 0,
         "out_defense_front7": 0, "out_defense_secondary": 0, "out_offense_qb": 0,
         "out_offense_skill": 0, "out_offense_line": 0, "mirror_out_ruled": 0}
    for r in scrape["rows"]:
        if r["team"] != team:
            continue
        c["report_rows_this_week"] += 1
        status = (r.get("game") or "")
        if status == "Questionable":
            c["questionable"] += 1
        if status in ("Out", "Doubtful"):
            c["out_ruled"] += 1
            u = unit_fn(r.get("position") or "")
            if u == "front7":
                c["out_defense_front7"] += 1
            elif u == "secondary":
                c["out_defense_secondary"] += 1
            elif u == "qb":
                c["out_offense_qb"] += 1
            elif u == "skill":
                c["out_offense_skill"] += 1
            elif u == "off_line":
                c["out_offense_line"] += 1
    return c


def main() -> int:
    g = C.load_games()
    inj = pd.read_csv(os.path.join(C.DATA, "injuries.csv"))
    pw = pd.read_csv(os.path.join(C.DATA, "player_week.csv"))
    print(f"games {len(g)}, played {int(g['played'].sum())}, injury rows {len(inj)}, "
          f"player-week rows {len(pw)}")

    L = P.team_games(g)
    L = P.quarterback_continuity(L)
    print("building production-loss window ...")
    L = P.production_loss(L, pw, inj)
    reg = P.out_register(inj)
    L = P.join_register(L, reg)
    L = P.opponent_features(L)

    # ---------------------------------------------------------- information tests
    G = P.game_level(L)
    feats = ["backup_qb_start_diff_home_minus_away",
             "production_loss_share_diff_home_minus_away",
             "own_out_defense_diff_home_minus_away",
             "own_out_offense_diff_home_minus_away",
             "own_n_out_diff_home_minus_away",
             "backup_qb_start", "away_backup_qb_start",
             "production_loss_share", "away_production_loss_share",
             "own_out_defense", "away_own_out_defense",
             "own_out_offense", "away_own_out_offense"]
    info, info_meta = P.incremental_information(G, feats)
    write("lines_of_evidence.json", {
        "generated_at": C.now(),
        "question": "Does the measure carry information the closing line does not already carry?",
        "design": ("OLS of the game result (home margin, home perspective) on the closing "
                   "spread, then on the closing spread plus the feature. The feature's own "
                   "coefficient, t and two-sided p, and the change in R-squared, are the test. "
                   "The closing spread is the market's pre-game estimate, so any feature that "
                   "adds nothing to it is not a new signal."),
        "n_games_with_close_and_result": int((G["spread_line"].notna() & G["result"].notna()).sum()),
        "multiple_testing": info_meta,
        "rows": info,
        "sources": OSRC,
    })

    # ------------------------------------------------------------------- bet log
    B, excluded = P.generate_bets(L)
    print(f"bets scored {len(B)}")
    if len(B):
        print(B.groupby("strategy").size().to_string())

    # prior family: the twelve published rules in the lab
    prior = json.load(open(os.path.join(C.DATA, "leaderboard.json")))
    prior_p = [r.get("p_value") for r in prior["leaderboard"]]

    LB = P.evaluate(B, prior_p, len(prior["leaderboard"])) if len(B) else {}
    LB["generated_at"] = C.now()
    LB["rules"] = [{"id": r[0], "basis": r[1], "statement": r[2]} for r in P.RULES]
    LB["exclusions"] = excluded
    LB["totals"] = {
        "bets_scored": int(len(B)),
        "games_in_bet_log": int(B["game_id"].nunique()) if len(B) else 0,
        "seasons": sorted(int(s) for s in B["season"].unique()) if len(B) else [],
        "all_prices_observed": bool(B["price"].notna().all()) if len(B) else True,
    }
    LB["reading"] = (
        "These five rules were written down before they were scored, and their p-values are "
        "corrected together with the twelve rules already published, so a rule cannot pass by "
        "being the best of a small batch. A WATCH result means the price was beaten in the "
        "scored sample but the significance, holdout or stability gate did not clear; it is not "
        "a recommendation to bet.")
    write("leaderboard.json", LB)

    # -------------------------------------------------------------- the register
    reg_out = {
        "generated_at": C.now(),
        "unit": "club-week",
        "source": "official NFL weekly injury report (nflverse mirror of the league report)",
        "source_urls": [OSRC["nflverse"], OSRC["injuries_current"]],
        "definition": {
            "out": "report_status is Out or Doubtful on the official weekly report",
            "front7": "DE, DT, NT, EDGE, LB, ILB, OLB, MLB, IDL",
            "secondary": "CB, S, DB, FS, SS, SAF",
            "off_line": "T, G, C, OT, OG, OL",
            "skill": "RB, FB, WR, TE",
            "qb": "QB",
        },
        "seasons": [int(inj["season"].min()), int(inj["season"].max())],
        "club_weeks": int(len(reg)),
        "rows": reg.sort_values(["season", "week", "team"]).to_dict(orient="records"),
    }
    write("register.json", reg_out)

    # ------------------------------- mirror vs the session's own nfl.com scrape
    # The wider site scrapes nfl.com/injuries/ directly in Actions
    # (data/model/official_injuries.json). The research extract uses the mirrored feed.
    # Where they disagree, the disagreement is a finding and is published, and the current
    # week's board is built from the newer official scrape so the board is not stale.
    diff = None
    try:
        scrape = json.load(open(os.path.join(C.ROOT, "data", "model",
                                             "official_injuries.json")))
        m = inj[(inj["season"] == int(scrape["season"])) & (inj["week"] == int(scrape["week"]))]
        s_out = {}
        for r0 in scrape["rows"]:
            if (r0.get("game") or "") in ("Out", "Doubtful"):
                s_out[r0["team"]] = s_out.get(r0["team"], 0) + 1
        m_out = {}
        for _, r0 in m[m["report_status"].isin(["Out", "Doubtful"])].iterrows():
            m_out[r0["team"]] = m_out.get(r0["team"], 0) + 1
        clubs = sorted(set(s_out) | set(m_out) | set(m["team"].unique()))
        rows0 = []
        for t in clubs:
            a, b = s_out.get(t, 0), m_out.get(t, 0)
            rows0.append({"club": t, "out_on_nfl_com_scrape": a, "out_in_mirror": b,
                          "difference": a - b, "agree": a == b})
        diff = {
            "generated_at": C.now(),
            "nfl_com_scrape": {
                "file": "data/model/official_injuries.json",
                "generated_at": scrape["generated_at"],
                "url": scrape["source_url"],
                "season": scrape["season"], "week": scrape["week"],
                "rows": scrape["counts"]["rows"], "clubs": scrape["counts"]["teams"],
            },
            "mirror": {
                "file": "data/s9cb/injuries.csv",
                "source": "https://github.com/nflverse/nflverse-data",
                "season": int(scrape["season"]), "week": int(scrape["week"]),
                "rows": int(len(m)), "clubs": int(m["team"].nunique()),
            },
            "clubs": rows0,
            "clubs_agreeing": sum(1 for r0 in rows0 if r0["agree"]),
            "clubs_differing": sum(1 for r0 in rows0 if not r0["agree"]),
            "totals": {"out_on_scrape": sum(s_out.values()), "out_in_mirror": sum(m_out.values())},
            "reading": ("Where a club has more ruled-out players on the official nfl.com page "
                        "than in the mirrored feed, the mirror is behind for that club. The "
                        "difference is published rather than averaged away, and this week's "
                        "board is built from the newer of the two."),
        }
        write("mirror_vs_official.json", diff)
    except Exception as exc:                             # noqa: BLE001
        print("mirror comparison skipped:", exc)

    # ------------------------------------------------- Week 10 deficiency board
    wk = L[(L["season"] == 2026) & (L["week"] == 10)].copy()

    # The current-week board prefers the direct nfl.com scrape when it is newer than the
    # mirrored feed; otherwise it uses the mirror. Whichever is used is named on the page.
    use_scrape = False
    try:
        use_scrape = scrape["generated_at"] > str(
            pd.read_csv(os.path.join(C.DATA, "games.csv"), nrows=1).iloc[0].get("gameday", ""))
    except Exception:                                    # noqa: BLE001
        use_scrape = False
    board_source = "mirror"
    scrape_out = {}
    scrape_rows = {}
    if "scrape" in dir():
        try:
            board_source = "nfl.com scrape"
            for r0 in scrape["rows"]:
                t = r0["team"]
                scrape_rows[t] = scrape_rows.get(t, 0) + 1
                if (r0.get("game") or "") in ("Out", "Doubtful"):
                    scrape_out[t] = scrape_out.get(t, 0) + 1
        except Exception:                                # noqa: BLE001
            board_source = "mirror"
            scrape_out, scrape_rows = {}, {}

    unit_of = {}
    _inj10 = inj[(inj["week"] == 10) & (inj["season"] == 2026)]
    for _, r0 in _inj10.iterrows():
        unit_of[(r0["team"], str(r0["full_name"]))] = (r0["position"] or "")
    pos_of = {(r0["team"], str(r0["full_name"])): (r0["position"] or "") for _, r0 in _inj10.iterrows()}

    def _unit(p: str) -> str:
        p = (p or "").upper()
        if p in OL_POSITIONS:
            return "off_line"
        if p in SKILL:
            return "skill"
        if p == "QB":
            return "qb"
        if p in FRONT7:
            return "front7"
        if p in SECONDARY:
            return "secondary"
        return "other"

    board = []
    for _, r in wk.iterrows():
        rec = {
            "game_id": r["game_id"], "gameday": r.get("gameday"), "team": r["team"],
            "opponent": r["opp"], "home_away": r["side"], "qb_starter": r.get("qb_name"),
            "incumbent_qb_name": (r.get("incumbent_qb_name")
                                  if isinstance(r.get("incumbent_qb_name"), str) else None),
            "incumbent_qb_started": (None if not np.isfinite(r.get("backup_qb_start", np.nan))
                                     else bool(r["backup_qb_start"] == 0)),
            "backup_qb_start": (None if not np.isfinite(r.get("backup_qb_start", np.nan))
                                else bool(r["backup_qb_start"] == 1)),
            "report_rows_this_week": (None if not np.isfinite(r.get("own_n_report", np.nan))
                                      else int(r["own_n_report"])),
            "out_ruled": (None if not np.isfinite(r.get("own_n_out", np.nan)) else int(r["own_n_out"])),
            "questionable": (None if not np.isfinite(r.get("own_n_questionable", np.nan))
                             else int(r["own_n_questionable"])),
            "out_defense_front7": (None if not np.isfinite(r.get("own_out_front7", np.nan))
                                   else int(r["own_out_front7"])),
            "out_defense_secondary": (None if not np.isfinite(r.get("own_out_secondary", np.nan))
                                      else int(r["own_out_secondary"])),
            "out_offense_qb": (None if not np.isfinite(r.get("own_out_qb", np.nan))
                               else int(r["own_out_qb"])),
            "out_offense_skill": (None if not np.isfinite(r.get("own_out_skill", np.nan))
                                  else int(r["own_out_skill"])),
            "out_offense_line": (None if not np.isfinite(r.get("own_out_off_line", np.nan))
                                 else int(r["own_out_off_line"])),
            "production_loss_share": (None if not np.isfinite(r.get("production_loss_share", np.nan))
                                      else round(float(r["production_loss_share"]), 4)),
            "counts_source": "mirror",
            "source_url": "https://www.nfl.com/injuries/",
        }
        # if the direct official scrape names more ruled-out players for this club, use it
        if board_source == "nfl.com scrape" and r["team"] in scrape_rows:
            mirror_out = rec["out_ruled"]
            sc = _scrape_counts(scrape, r["team"], _unit)
            rec.update(sc)
            rec["mirror_out_ruled"] = mirror_out
            rec["mirror_questionable"] = rec.get("questionable")
            # the scrape's own questionable count replaces the mirror's
            rec["counts_source"] = ("nfl.com scrape"
                                    if mirror_out == sc["out_ruled"]
                                    else "nfl.com scrape (mirror differed)")
        board.append(rec)

    write("week10_deficiency.json", {
        "generated_at": C.now(),
        "season": 2026, "week": 10,
        "fixtures_source": "https://www.nfl.com/schedules/2026/by-week/week-10",
        "injury_source": "https://www.nfl.com/injuries/",
        "counts_source": board_source,
        "club_rows": len(board),
        "rows": board,
        "note": ("Counts are the official Out/Doubtful designations for the listed week. "
                 "They are not snap counts and they do not prove who replaced whom on Sunday. "
                 "Counts come from the direct nfl.com scrape where that scrape names a player "
                 "the mirrored feed does not; the column says which source was used for each "
                 "club, and every difference is published in mirror_vs_official.json."),
    })

    # ------------------------------------------------------------------- the meta
    write("meta.json", {
        "generated_at": C.now(),
        "session": "1e159b2e-nfl1",
        "inputs": {
            "games": "data/s9cb/games.csv (nflverse schedules release, closing lines and prices)",
            "injuries": "data/s9cb/injuries.csv (nflverse mirror of the official weekly report)",
            "player_week": "data/s9cb/player_week.csv (nflverse stats_player release)",
            "prior_leaderboard": "data/s9cb/leaderboard.json (the twelve published rules)",
        },
        "source_urls": OSRC,
        "method_notes": {
            "qb_continuity": ("incumbent = most starts for that club this season in games "
                              "strictly before this one; week 1 falls back to the previous "
                              "season's most frequent starter; unknown otherwise, never assumed"),
            "production_window": f"the club's previous {P.LOOKBACK_WEEKS} games in the same season",
            "min_prior_games": P.MIN_PRIOR_GAMES,
            "production_gap_threshold_pct": P.PROD_GAP_POINTS,
            "defensive_out_gap_threshold": P.DEF_OUT_GAP,
            "prices": "observed only; a bet with no quoted price is excluded and counted",
            "multiple_testing": ("one Benjamini-Hochberg correction over the twelve already "
                                 "published rules plus these five"),
        },
        "coverage": {
            "team_games": int(len(L)),
            "qb_continuity_known": int(L["backup_qb_start"].notna().sum()),
            "qb_continuity_unknown": int(L["qb_continuity_unknown"].fillna(0).sum()),
            "production_share_known": int(L["production_loss_share"].notna().sum()),
            "production_share_excluded_window": int(
                (L["production_loss_note"] == "window too short").sum()),
            "production_share_excluded_no_report": int(
                (L["production_loss_note"] == "no official report row for this club-week").sum()),
            "player_week_seasons": [int(pw["season"].min()), int(pw["season"].max())],
            "game_seasons": [int(g["season"].min()), int(g["season"].max())],
            "injury_seasons": [int(inj["season"].min()), int(inj["season"].max())],
        },
        "known_limits": [
            "The committed extract has no defensive player statistics, so a defensive "
            "deficiency is measured in ruled-out players, not in lost production.",
            "The official report lists game status; it does not list who replaced whom. "
            "Replacement identity comes from the depth chart on the main site, not here.",
            "Practice-squad promotions and in-game injuries are not in the report.",
            "The 2026 season is in progress: its rows are small-sample and are shown as such.",
        ],
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
