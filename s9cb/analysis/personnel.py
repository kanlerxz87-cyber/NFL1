#!/usr/bin/env python3
"""Personnel-deficiency signals: do lineup losses predict results against the price?

What this module answers, and how:

  1. "tracking injuries and know any deficiencies in defenses such as 2nd, 3rd or 4th
     string backups having to replace starters" -> a per-club, per-week **defensive
     deficiency register** built from the official weekly report: ruled-Out/Doubtful
     defenders split into front seven and secondary, with the Questionable count beside
     them. The committed extract carries no defensive player statistics, so the register
     is count-based and says so rather than inventing a yards measure.
  2. "same can be said for offenses using starters or backups" -> two independent offence
     measures: QB continuity (is the club's incumbent starter actually starting?) and a
     production-loss share (what fraction of the club's recent offensive yardage belongs
     to players ruled Out/Doubtful this week?).
  3. "research and develop strategies for generating useful signals" -> each measure is
     first tested for *information* against the closing line (does it move the result
     beyond what the price already knows?). Only then is a bet rule written.
  4. "remove luck from the equation" -> the candidate rules are scored with the same eight
     gates as the strategy lab, and their p-values enter the SAME Benjamini-Hochberg
     correction as the twelve existing rules (family = 16, not 4). A rule that only looks
     good because it is the best of sixteen does not pass G5.

Honesty rules, enforced in code rather than promised in prose:
  * Every input is pre-game. The incumbent QB for a game is the QB with the most starts
    for that club in that season *strictly before* that game; week 1 falls back to the
    previous season's most frequent starter; if neither exists the value is NaN (unknown),
    never silently "starter".
  * The production window for a game in week W is the club's own previous games only.
  * A club with no rows in the official report for that week gets NaN, is excluded from
    the rule that needs it, and is counted in the exclusion totals.
  * No price is assumed anywhere: a bet is scored only when the source carries an
    observed price for that side.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies import GATES, MIN_BETS, HOLDOUT_SEASONS, STABILITY_FRACTION, \
    STABILITY_SEASON_MIN_BETS, score_group, season_table, leave_one_season_out

OFF_POSITIONS = {"QB", "RB", "FB", "WR", "TE", "T", "G", "C", "OT", "OG", "OL"}
OL_POSITIONS = {"T", "G", "C", "OT", "OG", "OL"}
FRONT7 = {"DE", "DT", "NT", "EDGE", "LB", "ILB", "OLB", "MLB", "IDL"}
SECONDARY = {"CB", "S", "DB", "FS", "SS", "SAF"}
SKILL = {"RB", "FB", "WR", "TE"}

LOOKBACK_WEEKS = 4        # production window: the club's own previous 4 games
MIN_PRIOR_GAMES = 2       # refuse to compute a share off a single game
PROD_GAP_POINTS = 15.0    # declared rule threshold, percentage points of production share
DEF_OUT_GAP = 3           # declared rule threshold, count of ruled-out defenders


# ------------------------------------------------------------------ team games
def team_games(g: pd.DataFrame) -> pd.DataFrame:
    """One row per team-game. Sorted so only earlier games can ever be read."""
    base = ["game_id", "season", "week", "gameday", "spread_line", "total_line", "total",
            "result", "div_game"]
    h = g[base + ["home_team", "away_team", "home_score", "away_score", "home_qb_id",
                  "home_qb_name", "home_spread_odds", "away_spread_odds",
                  "over_odds", "under_odds"]].copy()
    h["side"] = "home"
    h = h.rename(columns={"home_team": "team", "away_team": "opp", "home_score": "pf",
                          "away_score": "pa", "home_qb_id": "qb_id", "home_qb_name": "qb_name"})
    a = g[base + ["away_team", "home_team", "away_score", "home_score", "away_qb_id",
                  "away_qb_name", "away_spread_odds", "home_spread_odds",
                  "over_odds", "under_odds"]].copy()
    a["side"] = "away"
    a = a.rename(columns={"away_team": "team", "home_team": "opp", "away_score": "pf",
                          "home_score": "pa", "away_qb_id": "qb_id", "away_qb_name": "qb_name"})
    L = pd.concat([h, a], ignore_index=True)
    return L.sort_values(["season", "week", "gameday", "game_id", "side"]).reset_index(drop=True)


# ------------------------------------------------------- 1. QB continuity
def quarterback_continuity(L: pd.DataFrame) -> pd.DataFrame:
    """Did the club start the QB that started its previous game?

    Definition, fixed before any result was looked at:
      * incumbent(team, game) = the QB who started the club's most recent previous game,
        regardless of season boundary;
      * if the club has no previous game inside the sample, continuity is UNKNOWN (NaN),
        never "starter";
      * a start is a start: the QB of record in the source's game row, not a depth-chart
        guess and not a snap-share threshold.

    An earlier draft of this function used "most starts this season" and was wrong: a club
    that had moved on from a benched QB for two weeks was still scored as breaking
    continuity in week 3. The most-recent-starter rule matches what a reader means by
    "the starter", and it is still strictly pre-game, because the previous game is over.
    """
    L = L.copy()
    L["incumbent_qb"] = pd.Series(index=L.index, dtype="object")
    L["incumbent_qb_name"] = pd.Series(index=L.index, dtype="object")
    L["backup_qb_start"] = pd.Series(index=L.index, dtype="float64")
    L["qb_continuity_unknown"] = pd.Series(index=L.index, dtype="float64")

    last: dict[str, tuple[str, str]] = {}          # team -> (qb_id, qb_name) of last game
    for idx, r in L.sort_values(["season", "week", "gameday", "game_id", "side"]).iterrows():
        prev = last.get(r["team"])
        if prev is None:
            L.at[idx, "qb_continuity_unknown"] = 1.0
        else:
            qb_id, qb_name = prev
            L.at[idx, "incumbent_qb"] = qb_id
            L.at[idx, "incumbent_qb_name"] = qb_name
            L.at[idx, "backup_qb_start"] = float(r["qb_id"] != qb_id)
        # the current game's starter becomes the incumbent for this club's next game
        if isinstance(r["qb_id"], str) and r["qb_id"]:
            last[r["team"]] = (r["qb_id"], r.get("qb_name"))
    return L


# --------------------------------------------- 2. production-loss share
def production_loss(L: pd.DataFrame, pw: pd.DataFrame, inj: pd.DataFrame) -> pd.DataFrame:
    """Share of a club's recent offensive output ruled Out/Doubtful this week.

    Construction, stated plainly because the arithmetic matters:
      * a player's output in a game = passing_yards + rushing_yards + receiving_yards, i.e.
        everything he personally produced. Summed over players this necessarily counts a
        completed pass twice (once to the passer, once to the receiver); numerator and
        denominator use the identical construction, so the *share* is well defined even
        though the level is not team yardage. `team_yards_per_game` is published beside it
        so the reader can see the level rather than infer it.
      * the window is the club's own previous LOOKBACK_WEEKS games in the same season;
      * the ruled-out list is that week's official report, matched on GSIS player id;
      * fewer than MIN_PRIOR_GAMES in the window, or a club with no report row that week,
        gives NaN and is counted as excluded.
    """
    off = pw[(pw["season_type"].fillna("REG") == "REG")
             & pw["position"].isin(OFF_POSITIONS)].copy()
    for c in ("passing_yards", "rushing_yards", "receiving_yards"):
        off[c] = pd.to_numeric(off[c], errors="coerce").fillna(0.0)
    per = (off.groupby(["player_id", "team", "season", "week"], as_index=False)
              .agg(pass_yds=("passing_yards", "sum"), rush_yds=("rushing_yards", "sum"),
                   rec_yds=("receiving_yards", "sum")))
    per["yards"] = per["pass_yds"] + per["rush_yds"] + per["rec_yds"]

    reg = inj[inj["game_type"].fillna("REG") == "REG"].copy()
    # A club "has a report" if the official report lists ANY player for it that week -- not
    # only a ruled-out one. A club with a clean report has a real, publishable value: nobody
    # ruled out, so the share is 0.0. Treating it as missing would throw away the zero.
    reported = set(zip(reg["season"].astype(int), reg["week"].astype(int), reg["team"]))
    ruled = reg[reg["report_status"].isin(["Out", "Doubtful"])]

    rows = []
    for (season, team), grp in L.groupby(["season", "team"], sort=True):
        hist = per[per["team"] == team]
        for idx, r in grp.iterrows():
            prior = hist[(hist["season"] == season) & (hist["week"] < r["week"])]
            weeks = sorted(prior["week"].unique())[-LOOKBACK_WEEKS:]
            win = prior[prior["week"].isin(weeks)]
            if win["week"].nunique() < MIN_PRIOR_GAMES:
                rows.append((idx, np.nan, np.nan, np.nan, 0, 0, "window too short"))
                continue
            if (int(season), int(r["week"]), team) not in reported:
                rows.append((idx, np.nan, np.nan, np.nan, 0, int(win["week"].nunique()),
                             "no official report row for this club-week"))
                continue
            total = float(win["yards"].sum())
            if total <= 0:
                rows.append((idx, np.nan, np.nan, np.nan, 0, int(win["week"].nunique()),
                             "no recorded output in window"))
                continue
            out_ids = set(ruled[(ruled["season"] == season) & (ruled["week"] == r["week"])
                                & (ruled["team"] == team)]["gsis_id"].dropna())
            by_player = win.groupby("player_id")["yards"].sum()
            hit = by_player[by_player.index.isin(out_ids)]
            share = float(hit.sum()) / total
            rows.append((idx, share, total, float(total / win["week"].nunique()),
                         int(len(hit)), int(win["week"].nunique()), ""))
    S = pd.DataFrame(rows, columns=["idx", "production_loss_share", "window_yards",
                                    "team_yards_per_game", "ruled_out_producers",
                                    "window_games", "production_loss_note"]).set_index("idx")
    return L.join(S)


# ------------------------------------------- 3. official out register
def out_register(inj: pd.DataFrame) -> pd.DataFrame:
    """Per club-week ruled-out counts by unit, from the official weekly report."""
    d = inj[inj["game_type"].fillna("REG") == "REG"].copy()
    d["pos"] = d["position"].fillna("").str.upper()
    d["is_out"] = d["report_status"].isin(["Out", "Doubtful"])
    d["is_q"] = d["report_status"].eq("Questionable")

    def unit(p: str) -> str:
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

    d["unit"] = d["pos"].map(unit)
    g = d.groupby(["season", "week", "team"])
    reg = pd.DataFrame({
        "n_report": g.size(),
        "n_out": g["is_out"].sum(),
        "n_questionable": g["is_q"].sum(),
        "out_qb": g.apply(lambda x: int((x["is_out"] & x["unit"].eq("qb")).any()), include_groups=False),
        "out_skill": g.apply(lambda x: int((x["is_out"] & x["unit"].eq("skill")).sum()), include_groups=False),
        "out_off_line": g.apply(lambda x: int((x["is_out"] & x["unit"].eq("off_line")).sum()), include_groups=False),
        "out_front7": g.apply(lambda x: int((x["is_out"] & x["unit"].eq("front7")).sum()), include_groups=False),
        "out_secondary": g.apply(lambda x: int((x["is_out"] & x["unit"].eq("secondary")).sum()), include_groups=False),
    }).reset_index()
    reg["out_defense"] = reg["out_front7"] + reg["out_secondary"]
    reg["out_offense"] = reg["out_qb"] + reg["out_skill"] + reg["out_off_line"]
    return reg


def join_register(L: pd.DataFrame, reg: pd.DataFrame) -> pd.DataFrame:
    """Attach the club's own register row and its opponent's, both keyed on the same week."""
    own = reg.add_prefix("own_").rename(columns={"own_season": "season", "own_week": "week",
                                                "own_team": "team"})
    L = L.merge(own, on=["season", "week", "team"], how="left")
    opp = reg.add_prefix("opp_").rename(columns={"opp_season": "season", "opp_week": "week",
                                                "opp_team": "opp"})
    L = L.merge(opp, on=["season", "week", "opp"], how="left")
    return L


def opponent_features(L: pd.DataFrame) -> pd.DataFrame:
    """For each team-game, the opponent's continuity and production-loss values."""
    key = ["game_id", "season", "week"]
    mine = L[key + ["team", "backup_qb_start", "production_loss_share",
                    "team_yards_per_game", "ruled_out_producers", "qb_continuity_unknown"]]
    other = mine.rename(columns={
        "team": "opp", "backup_qb_start": "opp_backup_qb_start",
        "production_loss_share": "opp_production_loss_share",
        "team_yards_per_game": "opp_team_yards_per_game",
        "ruled_out_producers": "opp_ruled_out_producers",
        "qb_continuity_unknown": "opp_qb_continuity_unknown"})
    return L.merge(other, on=key + ["opp"], how="left")


# ============================================================== information tests
def _ols(y: np.ndarray, X: np.ndarray):
    """OLS with intercept already in X. Returns beta, se, t, p (two-sided, t dist)."""
    from common import _student_t_cdf
    n, k = X.shape
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = n - k
    if dof <= 0:
        return beta, np.full(k, np.nan), np.full(k, np.nan), np.full(k, np.nan)
    sigma2 = float(resid @ resid) / dof
    try:
        cov = sigma2 * np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return beta, np.full(k, np.nan), np.full(k, np.nan), np.full(k, np.nan)
    se = np.sqrt(np.diag(cov))
    t = beta / se
    p = np.array([2 * (1 - _student_t_cdf(abs(tt), dof)) for tt in t])
    return beta, se, t, p


def game_level(L: pd.DataFrame) -> pd.DataFrame:
    """Collapse the team-game rows to one row per game, with home-minus-away differences.

    This matters: the outcome is a home-perspective margin, so pooling the two team-game
    rows would make "own" and "opponent" features mirror images of each other and every
    regression would return the same coefficient twice. One row per game, with the
    differential as the regressor, is the only honest way to ask the question.
    """
    key = ["season", "week", "gameday", "spread_line", "total_line", "total",
           "result", "div_game"]
    h = L[L["side"] == "home"].set_index("game_id")
    a = L[L["side"] == "away"].set_index("game_id")
    cols = ["backup_qb_start", "production_loss_share", "own_out_defense", "own_out_offense",
            "own_out_front7", "own_out_secondary", "own_n_out", "own_out_qb", "own_out_skill",
            "team_yards_per_game"]
    out = h[key + cols].copy()
    for c in cols:
        out[f"away_{c}"] = a[c]
        out[f"{c}_diff_home_minus_away"] = h[c] - a[c]
    out["home_team"] = h["team"]
    out["away_team"] = a["team"]
    return out.reset_index()


FEATURE_LABELS = {
    "backup_qb_start_diff_home_minus_away":
        "home club is starting a backup QB minus away club is (+1 = home is the disrupted side)",
    "production_loss_share_diff_home_minus_away":
        "home ruled-out share of recent offensive output minus away",
    "own_out_defense_diff_home_minus_away":
        "home ruled-out defenders minus away ruled-out defenders",
    "own_out_offense_diff_home_minus_away":
        "home ruled-out offensive players minus away",
    "own_n_out_diff_home_minus_away": "home total ruled Out/Doubtful minus away",
    "backup_qb_start": "home club starts a backup QB (0/1)",
    "away_backup_qb_start": "away club starts a backup QB (0/1)",
    "production_loss_share": "home ruled-out share of recent offensive output",
    "away_production_loss_share": "away ruled-out share of recent offensive output",
    "own_out_defense": "home ruled-out defenders (front seven + secondary)",
    "away_own_out_defense": "away ruled-out defenders (front seven + secondary)",
    "own_out_offense": "home ruled-out offensive players",
    "away_own_out_offense": "away ruled-out offensive players",
}


def incremental_information(G: pd.DataFrame, features: list[str]) -> tuple[list[dict], dict]:
    """Does the measure move the result beyond what the closing line already knows?

        M0: result = a + b1 * spread_line
        M1: result = a + b1 * spread_line + b2 * feature

    b2 with its t statistic and two-sided p is the *incremental* information. The closing
    line is the market's best pre-game estimate; a feature that adds nothing to it is not a
    new signal. The market coefficient is printed alongside as a sanity check on the sample
    (it must stay near 1.0 and highly significant, or the join is wrong).
    """
    out = []
    base = G[G["spread_line"].notna() & G["result"].notna()].copy()
    for f in features:
        d = base[base[f].notna()].copy()
        if len(d) < 300:
            out.append({"feature": f, "what_it_measures": FEATURE_LABELS.get(f, ""),
                        "n": int(len(d)), "note": "too few complete rows to test"})
            continue
        y = d["result"].to_numpy(float)
        X0 = np.column_stack([np.ones(len(d)), d["spread_line"].to_numpy(float)])
        X1 = np.column_stack([X0, d[f].to_numpy(float)])
        b0, _, _, _ = _ols(y, X0)
        b1, se1, t1, p1 = _ols(y, X1)
        r0, r1 = y - X0 @ b0, y - X1 @ b1
        sst = float(((y - y.mean()) ** 2).sum())
        r2_0, r2_1 = 1 - float(r0 @ r0) / sst, 1 - float(r1 @ r1) / sst
        out.append({
            "feature": f,
            "what_it_measures": FEATURE_LABELS.get(f, ""),
            "n": int(len(d)),
            "market_coef_on_result": round(float(b1[1]), 5),
            "market_p": round(float(p1[1]), 8) if np.isfinite(p1[1]) else None,
            "feature_coef": round(float(b1[2]), 5),
            "feature_se": round(float(se1[2]), 5) if np.isfinite(se1[2]) else None,
            "feature_t": round(float(t1[2]), 4) if np.isfinite(t1[2]) else None,
            "feature_p_two_sided": round(float(p1[2]), 6) if np.isfinite(p1[2]) else None,
            "r2_market_only": round(r2_0, 6),
            "r2_with_feature": round(r2_1, 6),
            "incremental_r2_points": round(100 * (r2_1 - r2_0), 5),
            "interpretation": (
                "adds information beyond the closing line at the 5% level"
                if np.isfinite(p1[2]) and p1[2] < 0.05
                else "no information beyond the closing line at the 5% level"),
        })
    from common import benjamini_hochberg
    pv = [r.get("feature_p_two_sided") for r in out]
    adj = benjamini_hochberg([np.nan if v is None else v for v in pv])
    tested = sum(1 for v in pv if v is not None)
    for r, a in zip(out, adj):
        r["feature_p_bh_adjusted"] = round(float(a), 6) if np.isfinite(a) else None
        r["significant_after_correction"] = bool(np.isfinite(a) and a < 0.05)
    out_meta = {"tests_run": tested,
                "correction": ("Benjamini-Hochberg over all %d information tests in this "
                               "file; a raw p below 0.05 is expected roughly once per twenty "
                               "tests, so the corrected column is the one to read" % tested)}
    return out, out_meta


def _verdict(net: float, best: np.ndarray) -> str:
    """One sentence a reviewer can act on, derived only from the bet log."""
    if net <= 0:
        return ("no positive return to explain: there is nothing here for luck to have "
                "caused, and the rule loses money in this sample")
    share = float(best.sum()) / net
    if share >= 1.0:
        return ("the entire return sits in the best few bets: remove them and the rule is "
                "negative, which is what luck looks like")
    if share >= 0.5:
        return "most of the return sits in a handful of bets, the signature of luck"
    return "the return is spread across many bets rather than a few"


# ============================================================ luck decomposition
def luck_decomposition(g: pd.DataFrame) -> dict:
    """How much of the return is concentrated in a handful of bets?

    Three cheap, hard-to-fake diagnostics, computed on the bet log itself:

      * profit concentration: share of the net profit contributed by the best 5% of bets,
        and by the single best bet. A rule whose whole return is one Sunday is luck.
      * longest losing streak, and the streak length that would be expected by chance at
        the rule's own observed hit rate (expected longest run in n Bernoulli trials is
        about log_{1/p}(n * (1-p))). A streak far longer than that is not an edge.
      * the break-even gap: the rule's hit rate minus the average implied break-even rate
        of the prices it actually took. That gap, not the ROI, is the skill statement.
    """
    d = g.copy()
    n = len(d)
    if n == 0:
        return {}
    profits = d["profit"].to_numpy(float)
    order = np.argsort(-profits)
    top5 = max(1, int(round(0.05 * n)))
    net = float(profits.sum())
    decided = d[~d["push"]]
    hit = float(decided["won"].mean()) if len(decided) else float("nan")
    be = float(d["implied_prob"].mean())

    # longest losing run over the chronological sequence
    seq = d.sort_values(["season", "week", "game_id"])["won"].to_numpy()
    longest = cur = 0
    for won in seq:
        cur = 0 if won else cur + 1
        longest = max(longest, cur)
    p = hit if np.isfinite(hit) and 0 < hit < 1 else 0.5
    n_dec = max(1, len(decided))
    expected_longest = (np.log(n_dec * (1 - p)) / np.log(1.0 / (1 - p))) if 0 < p < 1 else np.nan

    equity = np.cumsum(profits)
    peak = np.maximum.accumulate(np.concatenate([[0.0], equity]))[1:]
    drawdown = float((equity - peak).min())

    return {
        "n_bets": int(n),
        "net_profit_units": round(net, 3),
        "profit_share_from_best_5pct_of_bets": (round(float(profits[order[:top5]].sum()) / net, 4)
                                                if net else None),
        "profit_share_from_best_single_bet": (round(float(profits.max()) / net, 4)
                                              if net else None),
        "longest_losing_streak": int(longest),
        "expected_longest_losing_streak_at_observed_hit_rate":
            round(float(expected_longest), 2) if np.isfinite(expected_longest) else None,
        "max_drawdown_units": round(drawdown, 3),
        "skill_gap_hit_minus_breakeven": round(hit - be, 4) if np.isfinite(hit) else None,
        "verdict": _verdict(net, profits[order[:top5]]),
    }


# ================================================================== bet rules
def _bet(r: pd.Series, kind: str, side: str) -> dict | None:
    """Price a bet from the observed quote only. No price, no bet."""
    if kind == "spread":
        line = r.get("spread_line", np.nan)
        price = r.get("home_spread_odds" if side == "home" else "away_spread_odds", np.nan)
        margin = r.get("result", np.nan)
        if not np.isfinite(line) or not np.isfinite(price) or not np.isfinite(margin):
            return None
        push = abs(margin - line) < 1e-9
        won = margin > line if side == "home" else margin < line
        return {"market": f"{side} spread", "price": float(price), "won": bool(won),
                "push": bool(push), "line": float(line)}
    line = r.get("total_line", np.nan)
    price = r.get("over_odds" if side == "over" else "under_odds", np.nan)
    tot = r.get("total", np.nan)
    if not np.isfinite(line) or not np.isfinite(price) or not np.isfinite(tot):
        return None
    push = abs(tot - line) < 1e-9
    won = tot > line if side == "over" else tot < line
    return {"market": f"{side} total", "price": float(price), "won": bool(won),
            "push": bool(push), "line": float(line)}


RULES = [
    ("P01 Back the opponent when the club starts a backup QB", "qb_continuity",
     "Opponent's club starts a QB who is not its incumbent starter. Side is the OTHER club, "
     "so the rule bets on the information advantage, not on the disrupted club."),
    ("P02 Fade the club that starts a backup QB", "qb_continuity",
     "Same flag as P01, bet the opposite way. Published as a control: if P01 only worked "
     "because the market had not moved, its mirror image would lose by a similar amount."),
    ("P03 Under when combined ruled-out production share is high", "production",
     "Both clubs' ruled-out share of recent offensive output sums above the declared "
     "threshold. Lost producers mean fewer available yards, so the total is the market."),
    ("P04 Fade the side missing 3+ more defenders", "defense",
     "One club has at least DEF_OUT_GAP more ruled-out defenders (front seven plus "
     "secondary) than its opponent; bet the side with the healthier defence."),
    ("P05 Over when both defences are missing 3+", "defense",
     "Both clubs are missing DEF_OUT_GAP or more ruled-out defenders: replacement "
     "defenders on both sides, so the total is the market."),
]


def generate_bets(L: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Build the bet log plus the exclusion accounting for every rule."""
    played = L[L["pf"].notna() & L["pa"].notna()].copy()
    bets, excluded = [], {r[0]: {"games_meeting_condition": 0, "no_observed_price": 0,
                                 "feature_unknown": 0} for r in RULES}

    for _, r in played.iterrows():
        # P01 / P02 -----------------------------------------------------------------
        b_own, b_opp = r.get("backup_qb_start"), r.get("opp_backup_qb_start")
        if np.isfinite(b_own) and np.isfinite(b_opp):
            if b_own == 1.0 and b_opp == 0.0:
                excluded[RULES[0][0]]["games_meeting_condition"] += 1
                excluded[RULES[1][0]]["games_meeting_condition"] += 1
                side = "home" if r["side"] == "away" else "away"
                for name, s in ((RULES[0][0], side), (RULES[1][0], r["side"])):
                    bet = _bet(r, "spread", s)
                    if bet:
                        bets.append(_row(r, name, bet))
                    else:
                        excluded[name]["no_observed_price"] += 1
            # The mirror case (this club's opponent is the one starting a backup) is the
            # same game seen from the other team-game row. It is deliberately NOT scored
            # again, so each game enters P01/P02 exactly once.
        else:
            excluded[RULES[0][0]]["feature_unknown"] += 1
            excluded[RULES[1][0]]["feature_unknown"] += 1

        # P03 -----------------------------------------------------------------------
        so, sp = r.get("production_loss_share"), r.get("opp_production_loss_share")
        if np.isfinite(so) and np.isfinite(sp):
            if r["side"] == "home" and (100 * (so + sp)) >= PROD_GAP_POINTS:
                excluded[RULES[2][0]]["games_meeting_condition"] += 1
                bet = _bet(r, "total", "under")
                if bet:
                    bets.append(_row(r, RULES[2][0], bet))
                else:
                    excluded[RULES[2][0]]["no_observed_price"] += 1
        else:
            excluded[RULES[2][0]]["feature_unknown"] += 1

        # P04 / P05 -----------------------------------------------------------------
        if r["side"] == "home" and np.isfinite(r.get("own_out_defense", np.nan)) \
                and np.isfinite(r.get("opp_out_defense", np.nan)):
            gap = r["own_out_defense"] - r["opp_out_defense"]
            if abs(gap) >= DEF_OUT_GAP:
                excluded[RULES[3][0]]["games_meeting_condition"] += 1
                side = "away" if gap > 0 else "home"     # bet against the more depleted side
                bet = _bet(r, "spread", side)
                if bet:
                    bets.append(_row(r, RULES[3][0], bet))
                else:
                    excluded[RULES[3][0]]["no_observed_price"] += 1
            if r["own_out_defense"] >= DEF_OUT_GAP and r["opp_out_defense"] >= DEF_OUT_GAP:
                excluded[RULES[4][0]]["games_meeting_condition"] += 1
                bet = _bet(r, "total", "over")
                if bet:
                    bets.append(_row(r, RULES[4][0], bet))
                else:
                    excluded[RULES[4][0]]["no_observed_price"] += 1
        else:
            excluded[RULES[3][0]]["feature_unknown"] += 1
            excluded[RULES[4][0]]["feature_unknown"] += 1

    if not bets:
        return pd.DataFrame(), excluded
    from common import american_to_decimal
    B = pd.DataFrame(bets)
    B["decimal"] = [american_to_decimal(p) for p in B["price"]]
    B["profit"] = [0.0 if p else (d - 1.0 if w else -1.0)
                   for p, w, d in zip(B["push"], B["won"], B["decimal"])]
    B["implied_prob"] = 1.0 / B["decimal"]
    return B, excluded


def _row(r: pd.Series, strategy: str, bet: dict) -> dict:
    return {"strategy": strategy, "season": int(r["season"]), "week": int(r["week"]),
            "gameday": r.get("gameday"), "game_id": r["game_id"], "team": r["team"],
            "opp": r["opp"], "side": r["side"], "pf": float(r["pf"]), "pa": float(r["pa"]),
            **bet}


def evaluate(B: pd.DataFrame, prior_rule_pvalues: list[float], n_prior_rules: int) -> dict:
    """Score every rule with the lab's eight gates, correcting over the WHOLE family."""
    from common import benjamini_hochberg
    rows = []
    for strat, g in B.groupby("strategy"):
        sc = score_group(g)
        if not sc:
            continue
        seasons = season_table(g)
        hold = score_group(g[g["season"].isin(HOLDOUT_SEASONS)])
        big = [s for s in seasons if s["n_bets"] >= STABILITY_SEASON_MIN_BETS]
        pos = sum(1 for s in big if s["roi_pct"] > 0)
        loso = leave_one_season_out(g)
        rows.append({
            "strategy": strat, **sc,
            "luck": luck_decomposition(g),
            "seasons": seasons,
            "seasons_positive": pos, "seasons_evaluated": len(big),
            "leave_one_season_out": loso,
            "worst_case_roi_pct_after_dropping_a_season":
                min((v["roi_pct"] for v in loso.values()), default=None),
            "holdout_2024_2025": ({"n_bets": hold["n_bets"], "roi_pct": hold["roi_pct"],
                                   "hit_rate": hold["hit_rate"]} if hold else None),
            "gates": {
                "G1": True,
                "G2": bool(g["price"].notna().all()),
                "G3": sc["n_bets"] >= MIN_BETS,
                "G4": sc["hit_rate"] > sc["break_even_hit_rate"],
                "G5": None,
                "G6": bool(hold) and hold["roi_pct"] > 0,
                "G7": (len(big) > 0) and (pos / len(big)) >= STABILITY_FRACTION,
                "G8": bool(sc["roi_ci95"]) and sc["roi_ci95"][0] > 0,
            },
        })
    # ---- one correction over every rule ever tested, old and new ----------------
    allp = [float(p) for p in prior_rule_pvalues if p is not None and np.isfinite(p)]
    allp += [r["p_value"] for r in rows if r["p_value"] is not None]
    adj = benjamini_hochberg(allp)
    offset = len([p for p in prior_rule_pvalues if p is not None and np.isfinite(p)])
    for r, a in zip(rows, adj[offset:offset + len(rows)]):
        r["p_value_bh_adjusted_whole_family"] = round(float(a), 6) if np.isfinite(a) else None
        r["gates"]["G5"] = bool(np.isfinite(a) and a < 0.05)

    for r in rows:
        passed = [k for k, v in r["gates"].items() if v]
        r["gates_passed"] = passed
        r["n_gates_passed"] = len(passed)
        r["status"] = ("PASS" if len(passed) == 8 else
                       "WATCH" if all(r["gates"][k] for k in ("G1", "G2", "G3", "G4"))
                       else "FAIL")
    rows.sort(key=lambda r: r["p_value"] if r["p_value"] is not None else 1.0)
    for i, r in enumerate(rows, 1):
        r["rank_by_p_value"] = i
    return {
        "n_new_strategies": len(rows),
        "n_prior_strategies_in_family": n_prior_rules,
        "family_size_for_multiple_testing": n_prior_rules + len(rows),
        "leaderboard": rows,
        "gate_definitions": [{"id": i, "name": n, "why": w} for i, n, w in GATES],
    }
