#!/usr/bin/env python3
"""Assemble the pre-registration data layer (session 0c5215c1-nfl1).

Writes, from committed sources only (read-only inputs elsewhere in the repo):
  data/prereg/corpus.json          frozen backtest corpus + splits   (readiness PR-09)
  data/prereg/controls.json        random-side + favourites controls (readiness PR-17)
  data/prereg/registrations.json   every strategy entry, registration hash,
                                   two-sided what-would-change-our-mind (PR-15, PR-24)

Run: python3 prereg/build_data.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = os.path.join(ROOT, "data", "s9cb", "games.csv")
OUTDIR = os.path.join(ROOT, "data", "prereg")
def registration_commit() -> str:
    """The commit that first added prereg/SB-01-rule.md — the SB-01 registration."""
    out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%H", "--",
                          "prereg/SB-01-rule.md"], capture_output=True, text=True,
                         cwd=ROOT, check=True).stdout.strip().splitlines()
    return out[-1]


def jload(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def jdump(rel: str, obj) -> None:
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write("\n")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def first_add(rel: str) -> tuple[str, str]:
    out = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H %ci", "--", rel],
        capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip().splitlines()
    sha, date = out[-1].split()[0], out[-1].split()[1]
    return sha, date


def blob(url_path: str, sha: str) -> str:
    return f"https://github.com/kanlerxz87-cyber/NFL1/blob/{sha}/{url_path}"


# ---------------------------------------------------------------- corpus (PR-09)
def build_corpus(games: list[dict], sha: str, nbytes: int) -> dict:
    done = [r for r in games if r["away_score"] and r["home_score"]]
    frozen = [r for r in done if r["gameday"] <= "2026-11-12"]
    train = [r for r in frozen if int(r["season"]) <= 2022]
    val = [r for r in frozen if int(r["season"]) in (2023, 2024)]
    hold = [r for r in frozen if int(r["season"]) >= 2025]
    priced_s = [r for r in frozen if r["spread_line"] and r["away_spread_odds"] and r["home_spread_odds"]]
    priced_t = [r for r in frozen if r["total_line"] and r["over_odds"] and r["under_odds"]]
    return {
        "schema": "nfl1.prereg.corpus.v1",
        "corpus_id": "NFL1-CORPUS-2026-11-15-v1",
        "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "frozen_by": "session 0c5215c1-nfl1",
        "requirement": "brief: turn the 136-game log into the pre-registered backtest corpus (readiness PR-09)",
        "file": "data/s9cb/games.csv",
        "sha256_at_freeze": sha,
        "bytes_at_freeze": nbytes,
        "rows_at_freeze": len(games),
        "membership_rule": "rows with both final scores present AND gameday <= 2026-11-12",
        "membership_counts": {
            "completed_total": len(frozen),
            "train_1999_2022": len(train),
            "validation_2023_2024": len(val),
            "holdout_2025_2026": len(hold),
            "priced_spread": len(priced_s),
            "priced_total": len(priced_t),
        },
        "splits": {
            "train": {"seasons": "1999-2022", "n_games": len(train),
                      "use": "any fitting, threshold choice, rating estimation"},
            "validation": {"seasons": "2023-2024", "n_games": len(val),
                           "use": "model selection only; never reported as final"},
            "holdout": {"seasons": "2025-2026", "n_games": len(hold),
                        "use": "may not be reported on until opened",
                        "holdout_opened": None,
                        "holdout_opened_note": "add a dated record here (reason + decision link) in a later commit before any holdout number is published anywhere"},
        },
        "price_policy": {
            "state": "open decision",
            "note": "observed prices only for scoring; the -110 assumption used by data/model/strategies.json is retired for future runs pending decision PR-10",
            "decision_ref": "room/data/decisions.json",
        },
        "official_verification": {
            "verified_subset": "2026 games: 136 rows in data/verified/games_2026.csv (each row carries its official nfl.com week-page URL) + the official WAS 24-21 NYG final of 2026-11-12 absent from that file (flag F49)",
            "official_schedule_index": "https://www.nfl.com/schedules/",
            "unverified_subset": "1999-2025 games are nflverse (third-party, CC-BY-4.0) parses of the NFL schedule feed; they are NOT matched to official pages (readiness PR-02)",
            "tier_label": "2026 = official-verified; 1999-2025 = community mirror",
        },
        "supersedes": None,
        "amendment_rule": "membership may only be extended by a new corpus_id in a later commit; the frozen counts above are never edited",
    }


# --------------------------------------------------------------- controls (PR-17)
def american_to_decimal(a: float) -> float:
    return a / 100.0 + 1 if a > 0 else 1 + 100.0 / (-a)


def build_controls(games: list[dict], sha: str) -> dict:
    done = [r for r in games if r["away_score"] and r["home_score"]]
    frozen = [r for r in done if r["gameday"] <= "2026-11-12"]
    priced_s = [r for r in frozen if r["spread_line"] and r["away_spread_odds"] and r["home_spread_odds"]]
    priced_t = [r for r in frozen if r["total_line"] and r["over_odds"] and r["under_odds"]]

    # CTRL-01 random side, analytic expectation at observed prices.
    rand_s = [0.25 * (american_to_decimal(float(r["away_spread_odds"])) +
                      american_to_decimal(float(r["home_spread_odds"]))) - 1 for r in priced_s]
    rand_t = [0.25 * (american_to_decimal(float(r["over_odds"])) +
                      american_to_decimal(float(r["under_odds"]))) - 1 for r in priced_t]

    # CTRL-02 favourites only (spreads). spread_line = home expected margin
    # (verified: corr(spread_line, home margin) > 0 and the s9cb scorer), so the
    # home club is the favourite iff spread_line > 0. Home covers iff result > line;
    # away covers iff result < line; equal is a push (s9cb/analysis/strategies.py).
    profs, wins, losses, pushes, pickem = [], 0, 0, 0, 0
    for r in priced_s:
        line, margin = float(r["spread_line"]), float(r["result"])
        if line > 0:
            side, odds = "home", float(r["home_spread_odds"])
        elif line < 0:
            side, odds = "away", float(r["away_spread_odds"])
        else:
            side, odds = "home", float(r["home_spread_odds"])
            pickem += 1
        if margin == line:
            pushes += 1
            continue
        covered = (margin > line) if side == "home" else (margin < line)
        wins += covered
        losses += not covered
        profs.append(american_to_decimal(odds) - 1 if covered else -1.0)
    n = len(profs)
    mean = statistics.fmean(profs)
    sd = statistics.stdev(profs)
    ci = [round(mean - 1.96 * sd / math.sqrt(n), 6), round(mean + 1.96 * sd / math.sqrt(n), 6)]

    official = "https://www.nfl.com/schedules/"
    return {
        "schema": "nfl1.prereg.controls.v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requirement": "brief: add a control baseline (random picks; favourites only) to every leaderboard run (readiness PR-17)",
        "corpus": "NFL1-CORPUS-2026-11-15-v1",
        "input_sha256": sha,
        "price_rule": "observed prices only (American odds -> decimal); no -110 fill",
        "controls": [
            {
                "id": "CTRL-01",
                "name": "random side (analytic)",
                "market": "spread",
                "method": "for each priced game the expected profit of a uniformly random side is 0.25*(dec_away + dec_home) - 1; the reported value is the mean over the frozen corpus (no RNG, fully deterministic)",
                "n_games": len(priced_s),
                "expected_roi": round(statistics.fmean(rand_s), 6),
                "expected_roi_pct": round(100 * statistics.fmean(rand_s), 4),
                "role": "no-skill reference line for every board run",
                "source": {"t": "results + prices: nfl.com schedules index (official) via the pinned feed", "u": official},
            },
            {
                "id": "CTRL-01T",
                "name": "random side over/under (analytic)",
                "market": "total",
                "method": "same as CTRL-01 on over/under prices",
                "n_games": len(priced_t),
                "expected_roi": round(statistics.fmean(rand_t), 6),
                "expected_roi_pct": round(100 * statistics.fmean(rand_t), 4),
                "role": "no-skill reference for totals tracks",
                "source": {"t": "results + prices: nfl.com schedules index (official) via the pinned feed", "u": official},
            },
            {
                "id": "CTRL-02",
                "name": "favourites only",
                "market": "spread",
                "method": "bet the favourite every priced frozen game at its observed spread price; side = home iff spread_line > 0; push excluded from ROI",
                "n_considered": len(priced_s),
                "n_scored": n,
                "wins": wins,
                "losses": losses,
                "pushes": pushes,
                "pickem_line_zero": pickem,
                "hit_rate": round(wins / n, 4),
                "roi": round(mean, 6),
                "roi_pct": round(100 * mean, 4),
                "roi_ci95_normal": ci,
                "role": "the market's own default bet; a strategy must beat this before it beats anything",
                "source": {"t": "results + prices: nfl.com schedules index (official) via the pinned feed", "u": official},
            },
        ],
        "prospective_rule": "every future board run must publish CTRL-01/CTRL-02 computed on the same settled set as the strategies it ranks; a strategy whose interval overlaps the control interval is not distinguishable from no skill",
        "note": "the favourites-only control loses at observed prices in this corpus; that is the vig the strategy must first overcome, and it is why raw win rate cannot rank strategies",
    }


# ------------------------------------------------------------ registrations (PR-15, PR-24)
# Two-sided what-would-change-our-mind fields. Every entry carries an upside and a
# downside trigger; they are authored against each rule's own threshold and each
# collection's own gates (the gates are read from the source files at build time).
MIND: dict[str, tuple[str, str]] = {}


def mind(cid: str, sid: str, up: str, dn: str) -> None:
    MIND[f"{cid}/{sid}"] = (up, dn)


# --- s9cb-12 (retrospective; gates G1-G8; holdout 2024-2025; min 200 bets; BH over 12)
STD_UP_S9 = ("Graduates to the prospective board only on: >=200 further scored bets at the "
             "frozen threshold, BH q<0.05 across the 12-rule family, bootstrap ROI 95% CI "
             "above zero, positive 2024-25 holdout, >=60% of seasons positive.")
STD_DN_S9 = ("Demoted to paper and closed if a G1/G2 audit finds look-ahead or an unobserved "
             "price, or the next 200 scored bets leave the ROI CI spanning zero.")
mind("s9cb", "S01", "The 1.5-point edge keeps q<0.05 and CI>0 over the next 500 priced games "
     "with the walk-forward fit re-run frozen (G1), 2024-25 holdout positive. " + STD_UP_S9,
     "The edge lives in one walk-forward fold or disappears when the frozen code is re-run. " + STD_DN_S9)
mind("s9cb", "S02", "A 3-point edge is rarer: reaches n>=200 with CI>0 and hit rate above the "
     "price-implied break-even (G4) on new seasons. " + STD_UP_S9,
     "n stays below 200 for two more full seasons (G3 never clears) - archived as underpowered "
     "at this threshold, never re-tuned under this id. " + STD_DN_S9)
mind("s9cb", "S03", "Total edge >=2.5 keeps CI>0 over >=200 new scored totals bets with the "
     "model total fit frozen. " + STD_UP_S9,
     "Re-running the frozen model flips the sign of >10% of picks (input instability) - void, "
     "re-register as a new rule. " + STD_DN_S9)
mind("s9cb", "S04", "Total edge >=4.0 reaches n>=200 with q<0.05 and CI>0. " + STD_UP_S9,
     "The threshold is so rare the sample never reaches 200 in two seasons - archived as "
     "untestable at this threshold; lowering it requires a new id. " + STD_DN_S9)
mind("s9cb", "S05", "Rest days audit clean for every scored game (G1) and CI>0 at n>=200. " + STD_UP_S9,
     "Missing rest values correlate with the chosen side (selection bias) - void pending a "
     "rebuild of the rest feature. " + STD_DN_S9)
mind("s9cb", "S06", "Positive at n>=200 with the division flag taken from the official "
     "standings and a residual edge after conditioning on the closing line. " + STD_UP_S9,
     "Outcome regression on the closing line leaves no residual for the rule - archived as "
     "already priced. " + STD_DN_S9)
mind("s9cb", "S07", "Currently the closest rule (p=0.199): about 1,950 scored bets at 80% "
     "power would make the existing +6.1% distinguishable; BH q<0.05 with CI>0 and a positive "
     "holdout graduates it. " + STD_UP_S9,
     "The next 400 scored bets pull the ROI CI across zero while q stays >=0.05 - stays on "
     "WATCH only as long as the interval keeps its sign; otherwise paper. " + STD_DN_S9)
mind("s9cb", "S08", "Rest>=13 days verified for every scored game and CI>0 at n>=200. " + STD_UP_S9,
     "Audit finds a mis-coded bye/rest week for any club in the pick set - void and re-register "
     "after the fix. " + STD_DN_S9)
mind("s9cb", "S09", "The strongest raw result is a LOSS (-7.9%, BH q=0.178): it flips to "
     "candidate only if a prospective re-test at the frozen threshold is positive with CI>0 "
     "and q<0.05. " + STD_UP_S9,
     "Stays archived as evidence the low-total market prices efficiently; any threshold change "
     "is a new id, not a rescue. " + STD_DN_S9)
mind("s9cb", "S10", "Over at total>=50 turns positive with CI>0 over >=200 new bets at observed "
     "prices. " + STD_UP_S9,
     "Stays negative or CI spans zero at n>=200 - closed as priced efficiently. " + STD_DN_S9)
mind("s9cb", "S11", "Every scored game's QB designation comes from the official weekly report "
     "(G1) and CI>0 at n>=200 with q<0.05. " + STD_UP_S9,
     "Designation coverage gaps (mirror lag vs nfl.com, flag U02) touch >2% of picks - void "
     "until the official scrape is the only input. " + STD_DN_S9)
mind("s9cb", "S12", "Out-counts reconciled row-for-row against the official report every week "
     "and CI>0 at n>=200. " + STD_UP_S9,
     "Report row-count drift between scrape and official page affects >2% of picks - void "
     "(flags CAP-01/02 pattern). " + STD_DN_S9)

# --- model-12 (retrospective; gates G1-G8; window 2005-2026; -110 price assumption)
STD_UP_M = ("Re-scored at OBSERVED prices (the -110 assumption is retired under PR-10) with "
            ">=200 bets, BH q<0.05, CI>0 and a positive holdout before any graduate claim.")
STD_DN_M = ("If the edge exists only under the -110 fill, it is an artefact of the price "
            "policy, not a signal: archive and re-register after PR-10 is decided.")
mind("model", "S01", "Own-line edge >=2.0 survives observed-price re-scoring with q<0.05. " + STD_UP_M,
     "Sign flips or CI spans zero once real prices replace -110. " + STD_DN_M)
mind("model", "S02", "Own-line edge >=3.0 keeps CI>0 at observed prices over >=200 bets. " + STD_UP_M,
     "Threshold so rare n<100 at observed prices after a full season - archived. " + STD_DN_M)
mind("model", "S03", "Own-total edge >=3 keeps CI>0 at observed prices. " + STD_UP_M,
     "Model-total fit changes sign of the pick on re-run - void. " + STD_DN_M)
mind("model", "S04", "Divisional dog +6.5 shows a residual after conditioning on the closing "
     "line, positive at observed prices. " + STD_UP_M,
     "The line already prices the divisional dog (no residual) - archived. " + STD_DN_M)
mind("model", "S05", "Short-rest <=4 days positive at observed prices with rest data audited. " + STD_UP_M,
     "Rest missingness correlates with pick side - void. " + STD_DN_M)
mind("model", "S06", "Fade divisional road favourite 6.5+ positive across >=2 seasons at "
     "observed prices. " + STD_UP_M,
     "Positive only in one season (G6 <60%) - paper. " + STD_DN_M)
mind("model", "S07", "Home 3+ rest edge positive at observed prices with G1 walk-forward "
     "re-audit clean. " + STD_UP_M,
     "Walk-forward re-audit fails - void. " + STD_DN_M)
mind("model", "S08", "Home vs opponent off bye positive at observed prices. " + STD_UP_M,
     "Bye/rest source error found in audit - void pending fix. " + STD_DN_M)
mind("model", "S09", "Home favourite 10+ positive at observed prices with holdout positive. " + STD_UP_M,
     "Holdout negative after PR-10 re-scoring - close. " + STD_DN_M)
mind("model", "S10", "Over at closing total <=41 positive at observed prices. " + STD_UP_M,
     "Below break-even at observed prices at n>=200 - close. " + STD_DN_M)
mind("model", "S11", "Best current model rule (WATCH, 6/8): passes all eight at observed "
     "prices with BH q<0.05 and a positive holdout. " + STD_UP_M,
     "Loses WATCH when -110 is removed - archived as an artefact of the price policy. " + STD_DN_M)
mind("model", "S12", "Backup-QB join covers >=95% of scored games from the official report "
     "(club-key flag F48 resolved) and is positive at observed prices. " + STD_UP_M,
     "Join gaps bias the sample (F48 open) - void until club keys resolve. " + STD_DN_M)

# --- strength-11 (retrospective; gates G1-G8 (their own set); 1999-2026; holdout 2024-26)
STD_UP_X = ("BH q<0.05 across the 11-rule family on new seasons, ROI 95% CI>0 at the frozen "
            "threshold, and positive once the corpus holdout is opened - re-thresholding "
            "requires a new id (R26-01 discipline).")
STD_DN_X = ("Remains FAIL: any positive number published before the holdout opens is a policy "
            "violation, and re-running with a new threshold does not revive this id.")
for sid, name in [("X01", "own spread edge >=1.5"), ("X02", "own spread edge >=3.0"),
                  ("X03", "own total edge >=3.0"), ("X04", "own total edge >=5.0"),
                  ("X07", "own rating edge vs market >=2.0")]:
    mind("strength", sid, f"Positive with CI>0 at the frozen {name} threshold on post-2024 "
         "walk-forward data. " + STD_UP_X, STD_DN_X)
mind("strength", "X05", "Fade-the-lucky-favourite shows CI>0 after the luck metric itself is "
     "split-half reliable (>=0.5 correlation between halves). " + STD_UP_X,
     "Luck metric unstable across halves - void: the fade would be betting on noise. " + STD_DN_X)
mind("strength", "X06", "Back-the-unlucky-dog shows CI>0 with a reliable luck metric. " + STD_UP_X,
     "Luck metric unstable across halves - void. " + STD_DN_X)
mind("strength", "X08", "Under when both clubs' SOS above average is positive at the frozen "
     "threshold with SOS computed only from games before kickoff. " + STD_UP_X,
     "SOS uses any post-kickoff game (look-ahead) - void. " + STD_DN_X)
mind("strength", "X09", "Over when both SOS below average positive with pre-kickoff-only SOS. " + STD_UP_X,
     "SOS look-ahead found - void. " + STD_DN_X)
mind("strength", "X10", "Divisional dog 6.5+ with positive own-rating edge positive after "
     "conditioning on the closing line. " + STD_UP_X,
     "No residual beyond the closing line - archived as priced. " + STD_DN_X)
mind("strength", "X11", "Last-5 form underdog positive with form computed strictly pre-kickoff. " + STD_UP_X,
     "Form window overlaps the game being predicted - void. " + STD_DN_X)

# --- personnel-5 (retrospective; family of 17; observed prices; 2019-2026)
STD_UP_P = ("BH q<0.05 within the 17-strategy family on >=200 further scored bets at observed "
            "prices with CI>0; the official availability join must be complete for every "
            "scored game.")
STD_DN_P = ("Current result is 'descriptive, not an edge' (0 of 13 significant after "
            "correction): if the next 200 scored bets keep q>=0.05 the entry is closed as "
            "evidence of market efficiency, not re-tuned.")
mind("personnel", "P01", "Backup-QB opponent back positive with the official news join "
     "(VR-24/25 starter evidence) complete. " + STD_UP_P, STD_DN_P)
mind("personnel", "P02", "Fade the club starting a backup QB positive with the same join. " + STD_UP_P,
     STD_DN_P)
mind("personnel", "P03", "Currently -10.0% (raw p=0.058): flips positive with q<0.05 at "
     "observed prices. " + STD_UP_P, STD_DN_P)
mind("personnel", "P04", "Fade the side missing 3+ defenders positive with verified inactives "
     "as the source (IN-04 gate). " + STD_UP_P, STD_DN_P)
mind("personnel", "P05", "Over when both defences missing 3+ positive with verified inactives. " + STD_UP_P,
     STD_DN_P)

# --- foundation-10 (never evaluated -> prospective-eligible; definition commit 232a3b0)
STD_UP_F = ("First evaluation, run on NFL1-CORPUS-2026-11-15-v1 at observed prices, reaches "
            "n>=200 with BH q<0.05 across the 10-rule family and CI>0 - and cites this "
            "registration in the run.")
STD_DN_F = ("Fails G3 (n<100) or is negative at first look: closed under this id; any tuning "
            "creates a new id and must register again before re-evaluating.")
mind("foundation", "ST-01", "Net-points strength differential clears G01-G07 on first "
     "evaluation. " + STD_UP_F, STD_DN_F)
mind("foundation", "ST-02", "Points-allowed total clears the gates on first evaluation. " + STD_UP_F,
     "Negative at first look - closed. " + STD_DN_F)
mind("foundation", "ST-03", "Cannot be evaluated until the depth-source route is verified for "
     "all 32 clubs (readiness IN-08/IN-11); if it ever clears the eight gates with verified "
     "depth it graduates. " + STD_UP_F,
     "If no authorized depth source exists for all clubs, stays untested forever - no "
     "jersey-order or salary proxy may substitute (brief rejection). " + STD_DN_F)
mind("foundation", "ST-04", "Same depth gate as ST-03, offensive side. " + STD_UP_F,
     "Depth-source gate unmet - untested, no proxy substitution. " + STD_DN_F)
mind("foundation", "ST-05", "Requires timestamped Wed/Thu/Fri official reports (readiness "
     "IN-16) before the trend feature can be scored at all. " + STD_UP_F,
     "Without a dated report series the feature is untestable - stays untested, never "
     "level-substituted. " + STD_DN_F)
mind("foundation", "ST-06", "Requires play-rate-per-designation calibration with confidence "
     "intervals first (readiness IN-15). " + STD_UP_F,
     "Calibration never run - stays untested. " + STD_DN_F)
mind("foundation", "ST-07", "Two-leg parlay only ranks after a directly validated joint "
     "probability and the operator's void/push rules are on file (brief's joint-evidence "
     "gate). " + STD_UP_F,
     "Multiplying marginal probabilities without a validated joint model - permanently "
     "ineligible for the board. " + STD_DN_F)
mind("foundation", "ST-08", "Same-game combo only with a validated joint probability. " + STD_UP_F,
     "Joint-evidence gate unmet - ineligible. " + STD_DN_F)
mind("foundation", "ST-09", "Prop availability gate needs observed prop prices (flag F04/U01) "
     "before any evaluation. " + STD_UP_F,
     "No reachable official prop price - stays untested. " + STD_DN_F)
mind("foundation", "ST-10", "Backup-exposure index evaluated only with verified availability "
     "snapshots (IN-02). " + STD_UP_F,
     "Snapshot ledger absent - untested. " + STD_DN_F)

# --- signals-18 (proposed, never evaluated -> prospective-eligible; commit 0d1621f)
SIG_UP = ("First evaluation on the frozen corpus at observed prices cites registration "
          "0d1621f, reaches n>=200 with BH q<0.05 across the 18-signal family and CI>0.")
SIG_DN = ("Negative or underpowered at first look: closed under this id; a changed "
          "definition is a new signal id and a new registration.")
SIG_MIND = {
    "SIG-001": ("Practice-participation delta positive across three dated official reports "
                "per week (DNP->LP->FP trajectory).", "Without the dated report series the "
                "trajectory cannot be reconstructed - untested, never level-substituted."),
    "SIG-002": ("OL not-participation count predicts offensive output beyond the closing "
                "total.", "Official participation counts unavailable per club - untested."),
    "SIG-003": ("Secondary depletion predicts explosive passes beyond standings priors.",
                "Inactives not captured officially (IN-04) - untested."),
    "SIG-004": ("Edge availability shifts pressure rate and QB efficiency measurably.",
                "Snap counts absent (IN-11) - untested."),
    "SIG-005": ("Confirmed QB change (official news) is the largest repricing event and is "
                "captured before the line moves.", "News-to-line lag not measurable without "
                "intraday prices - untested until price snapshots exist (PR-01)."),
    "SIG-006": ("Top-two RB both limited -> pass-heavy shift, over hits at frozen threshold.",
                "Official RB designations incomplete - untested."),
    "SIG-007": ("Bye/rest differential positive with rest computed from the official "
                "schedule only.", "Rest look-ahead or schedule error - void."),
    "SIG-008": ("West-coast teams travelling east for early kickoffs underperform baseline.",
                "Travel feature unverifiable from official sources alone - untested."),
    "SIG-009": ("Faster-than-implied pace lifts total plays and overs.", "Play-level pace "
                "data not officially sourced - untested."),
    "SIG-010": ("Red-zone TD rate mean-reverts; fade hot converters.", "Multi-season "
                "red-zone data official match incomplete - untested."),
    "SIG-011": ("Takeaway rate regresses; fade extreme takeaway teams.", "Same data gate as "
                "SIG-010 - untested."),
    "SIG-012": ("Wind/precipitation thresholds depress totals (NWS overlay, readiness "
                "IN-29).", "NWS hourly overlay not built - untested; no level proxy."),
    "SIG-013": ("Divisional games lower scoring than the market's implied total.",
                "Negative at first look - closed."),
    "SIG-014": ("Lookahead/sandwich spots underperform.", "Schedule-context feature not "
                "built from published schedule facts only - untested."),
    "SIG-015": ("Wins outrunning scoring margin => overpriced; reverse underpriced.",
                "Divergence metric unstable in small samples - if split-half unreliable, void."),
    "SIG-016": ("Public over-reacts to primetime blowouts; next week's line biased.",
                "Requires closing-line history snapshots (PR-01) - untested until they exist."),
    "SIG-017": ("Target share above prop implied value => underpriced receiver over.",
                "No observed prop prices anywhere reachable (U01) - permanently untested "
                "until a source exists."),
    "SIG-018": ("Correlated SGP legs underpriced vs naive multiplication - only with a "
                "validated joint probability (brief's joint-evidence gate).",
                "Marginal multiplication without joint validation - permanently ineligible."),
}
for sid, (name, _hyp) in [(s["id"], (s["name"], s.get("hypothesis", ""))) for s in
                          jload("data/session-87deb7ab/strategies.json")["signals"]]:
    up, dn = SIG_MIND[sid]
    mind("signals", sid, up, dn)

# --- lab-9 (retrospective; gates G0-G10; 2026 weeks 4-9)
LAB_MIND = {
    "S1": ("Rest edge: BH-adjusted p=0.008 exists BUT split-half correlation is -0.04 - it "
           "graduates only if the split-half correlation turns positive with a larger "
           "sample while CI>0.", "If split-half stays ~0, the p-value is selection, not "
           "signal: close and do not re-run weeks 10-18 under this id."),
    "S2": ("Home off bye positive on >=200 games (its n is currently 26, G1-blocked).",
           "n stays tiny or G1 (pre-game info) fails - paper."),
    "S3": ("Division dog positive after conditioning on the closing line.",
           "No residual vs closing line - archived as priced."),
    "S4": ("Fade 3+ win streaks positive with the streak defined pre-kickoff.",
           "Streak definition uses post-game knowledge - void."),
    "S5": ("Pythagorean bounce-back positive at the frozen threshold.",
           "Pythagorean gap unreliable (split-half) - void."),
    "S6": ("Road dog with better defence positive at the frozen threshold.",
           "Defence metric not officially sourced - untested."),
    "S7": ("Model-vs-market disagreement positive with the model walk-forward clean.",
           "Model weight negative (as the root pipeline found) - archived."),
    "S8": ("Bet-the-biggest-edge positive with the pick list frozen before kickoff.",
           "Pick list chosen after seeing results - void immediately."),
    "S9": ("Fade injury-hit starter positive with official designations only.",
           "Designation source incomplete - untested."),
}
for sid, (up, dn) in LAB_MIND.items():
    mind("lab", sid, up, dn)

# --- verifiedlab-13 (graded not-stakeable -> retrospective; gates G0-G9 style)
VL_MIND = {
    "S1": ("Pythagorean regression: graduates only if, scored at observed prices on >=200 "
           "bets, CI>0 and BH q<0.05 in the 13-strategy family.",
           "Currently not_stakeable: if first stakeable run is negative - closed."),
    "S2": ("Confirmed QB disruption positive with the official news item dated before the "
           "line moved.", "News timestamp not verifiable pre-line - untested."),
    "S3": ("Defensive absence cluster positive with official DNP sources.",
           "DNP counts not officially captured - untested."),
    "S4": ("Streak fade positive pre-kickoff.", "Streak uses post-game data - void."),
    "S5": ("Home-advantage mispricing positive after the 2026 home-win rate is confirmed on "
           "a larger window (current CI 41.4-57.9% spans 50%).",
           "CI keeps spanning 50% - never stakeable as written."),
    "S6": ("Divisional rematch under positive on 3rd/4th meetings only.",
           "Meeting-count data not officially verified - untested."),
    "P1": ("Favourite+under script positive only with a validated joint probability.",
           "Marginal multiplication - permanently ineligible (joint-evidence gate)."),
    "P2": ("QB-change stack positive with validated joint probability.",
           "Joint gate unmet - ineligible."),
    "P3": ("Low-correlation diversifier positive with measured near-independence.",
           "Measured correlation not significantly below zero - ineligible."),
    "X1": ("Opportunity transfer positive when the replacement is officially named "
           "(announced-starter evidence, VR-24/25).", "Inferred replacements may not be "
           "used - untested until announced evidence exists."),
    "X2": ("Pass-volume stack vs missing CB positive with the CB's Out status official.",
           "Opposing-CB status not official - untested."),
    "X3": ("Rush-attempt transfer positive with the lead back officially Out.",
           "Official designation incomplete - untested."),
    "X4": ("Negative-correlation guard stays a veto: any combo failing it is never ranked.",
           "If used to rank rather than veto - policy violation, close the entry."),
}
for sid, (up, dn) in VL_MIND.items():
    mind("verifiedlab", sid, up, dn)

# SB-01 (prospective; registration commit A)
MIND["SB-01"] = (
    "Brier skill vs the 0.5 base rate with a 95% interval strictly above zero over >=200 "
    "settled prospective forecasts, every one recorded before its kickoff (SB-G1) - only "
    "then does the baseline graduate from control to benchmark.",
    "Any recorded_at not earlier than its kickoff, or any post-kickoff edit to a settled "
    "record (SB-G1/SB-G2 broken), voids the prospective claim no matter how well it "
    "scored; the entry moves to the retrospective archive and a fresh registration is "
    "required before forecasting again.")


def collection_rows() -> list[dict]:
    """Per-collection registration metadata, computed from committed sources."""
    s9cb_lb = jload("data/s9cb/leaderboard.json")
    model_lb = jload("data/model/strategies.json")
    strength = jload("data/strength/strategies.json")
    foundation = jload("data/strategies.json")
    signals = jload("data/session-87deb7ab/strategies.json")
    personnel = jload("data/personnel/leaderboard.json")
    lab = jload("data/session-1505ac8e/strategies.json")
    vl = jload("data/processed/site_data.json")

    c = {}

    def add(cid, title, source_file, rule_file, kind, window, gates, note,
            strategies, sid_key, name_key, rule_key=None):
        dc, dd = first_add(source_file)
        rc = dc
        if rule_file and rule_file != source_file:
            rc, _ = first_add(rule_file)
        if sid_key is None:
            strat_out = []
        else:
            strat_out = [(s[sid_key], s.get(name_key) or s.get("strategy"),
                          (s.get(rule_key) if rule_key else None)) for s in strategies]
        c[cid] = {
            "id": cid, "title": title, "kind": kind,
            "definition_commit": dc, "definition_commit_date": dd,
            "rules_commit": rc,
            "results_commit": dc,
            "sample_window": window,
            "gates": gates,
            "source_file": source_file,
            "source_url": blob(source_file, dc),
            "note": note,
            "strategies": strat_out,
        }

    def prefixed(items, name_field="strategy"):
        """Collections whose files carry the rule id as the first token of the name."""
        out = []
        for s in items:
            name = s[name_field]
            out.append((name.split()[0], name, None))
        return out

    add("s9cb-12", "s9cb scored leaderboard: 12 rules at observed prices",
        "data/s9cb/leaderboard.json", "s9cb/analysis/strategies.py", "retrospective",
        "2006-2026, priced games only (5,202 priced spreads in the frozen corpus); holdout 2024-2025",
        s9cb_lb.get("gate_definitions", []),
        "rules and results first appear in the same commit (f15c018): not pre-registered; "
        "registered here for disclosure only (R26-01 pattern).",
        s9cb_lb["leaderboard"], None, None)
    c["s9cb-12"]["strategies"] = prefixed(s9cb_lb["leaderboard"])

    add("model-12", "root model leaderboard: 12 strategies (G1-G8)",
        "data/model/strategies.json", "pipeline/build_all.py", "retrospective",
        "2005-2026; price assumption -110 on every bet (retired pending decision PR-10)",
        model_lb.get("gate_definitions", []),
        "rule code (ef9bc8b) and first results (8158948) landed in the same session on "
        "2026-11-12; no results-free registration exists - retrospective.",
        model_lb["leaderboard"], None, None)
    c["model-12"]["strategies"] = prefixed(model_lb["leaderboard"])

    add("strength-11", "strength-of-schedule study: 11 rules through 8 gates",
        "data/strength/strategies.json", "analysis/strength.py", "retrospective",
        "1999-2026 walk-forward; holdout 2024-2026 per its G6",
        strength.get("gate_definitions", []),
        "rule file and results committed together at 2d9ebfe (flag R26-01 documents the "
        "earlier 5a769b3 instance, observed from a shallow clone); retrospective.",
        strength["strategies"], None, None)
    c["strength-11"]["strategies"] = prefixed(strength["strategies"])

    add("personnel-5", "personnel-deficiency study: 5 rules, family of 17",
        "data/personnel/leaderboard.json", "s9cb/analysis/personnel.py", "retrospective",
        "2019-2026, observed prices only; multiple-testing family = 17",
        [], "rules and results together at 00873cd (2026-11-13); retrospective. "
        "0 of 13 information tests significant after correction (published conclusion).",
        personnel["leaderboard"], None, None)
    c["personnel-5"]["strategies"] = prefixed(personnel["leaderboard"])

    add("foundation-10", "foundation design register: 10 strategies, never evaluated",
        "data/strategies.json", None, "prospective-eligible",
        "design only - no evaluation window has opened",
        [], "performance fields are null everywhere in the file: registration now precedes "
        "the first evaluation; the first evaluation must cite this entry's commit.",
        foundation, "id", "name", "formula")

    add("signals-18", "87deb7ab signal catalogue: 18 proposed signals, never evaluated",
        "data/session-87deb7ab/strategies.json", None, "prospective-eligible",
        "design only - status 'Proposed' on every signal",
        signals.get("gates", []), "never scored anywhere; first evaluation must cite this "
        "entry's commit (0d1621f).",
        signals["signals"], "id", "name", "hypothesis")

    add("lab-9", "lab unified study: 9 rules, gates G0-G10",
        "data/session-1505ac8e/strategies.json", "lab/scripts/build_analysis.py",
        "retrospective", lab.get("window", {}),
        lab.get("gate_definitions", []),
        "rules and results together at 7186f70; the collection did publish a rule-file "
        "sha256 (G0) but the hash and the results still landed in one commit - retrospective.",
        lab["rules"], "id", "name", "text")

    add("verifiedlab-13", "verified-lab independent study: 13 strategies (all not_stakeable)",
        "data/processed/site_data.json", "src/nfl/strategies.py", "retrospective",
        "2026 season; every entry currently graded not_stakeable (no prices)",
        [], "rules and results together at b7653d3; retrospective.",
        vl["strategies"]["strategies"], "id", "name", "hypothesis")

    return c


def build_registrations() -> dict:
    cols = collection_rows()
    entries = []

    # collection rows
    for cid, c in cols.items():
        up = ("Collection graduates only when its own worst-performing gate set is cleared "
              "prospectively: >=200 scored bets at observed prices, BH q<0.05 across the "
              "family, ROI 95% CI above zero, and a positive holdout after it is opened.")
        dn = ("If any gate audit (G1 look-ahead, G2 observed prices) fails, or the family's "
              "holdout is negative once opened, the collection is archived and may only be "
              "re-registered under new ids.")
        entries.append({
            "id": f"COLL/{cid}",
            "entry_type": "collection",
            "collection": cid,
            "strategy": c["title"],
            "track": "n/a (collection)",
            "rule_summary": c["note"],
            "sample_window": c["sample_window"],
            "gates": c["gates"],
            "registration": {
                "kind": c["kind"],
                "commit": c["definition_commit"],
                "commit_date": c["definition_commit_date"],
                "rules_commit": c["rules_commit"],
                "results_commit": c["results_commit"],
                "note": c["note"],
            },
            "would_change_our_mind": {"upside": up, "downside": dn},
            "source": {"t": c["source_file"], "u": c["source_url"]},
        })
        for sid, name, rule in c["strategies"]:
            key = f"{cid.split('-')[0]}/{sid}"
            if cid == "verifiedlab-13":
                key = f"verifiedlab/{sid}"
            elif cid == "signals-18":
                key = f"signals/{sid}"
            elif cid == "foundation-10":
                key = f"foundation/{sid}"
            elif cid == "lab-9":
                key = f"lab/{sid}"
            elif cid == "strength-11":
                key = f"strength/{sid}"
            elif cid == "personnel-5":
                key = f"personnel/{sid}"
            elif cid == "model-12":
                key = f"model/{sid}"
            elif cid == "s9cb-12":
                key = f"s9cb/{sid}"
            up, dn = MIND.get(key, (None, None))
            if up is None:
                raise SystemExit(f"missing mind-changer for {key}")
            entries.append({
                "id": key,
                "entry_type": "strategy",
                "collection": cid,
                "strategy": name,
                "track": "single" if cid != "foundation-10" or sid not in (
                    "ST-07", "ST-08") else "combo",
                "rule_summary": (rule or name),
                "sample_window": c["sample_window"],
                "gates_ref": cid,
                "registration": {
                    "kind": c["kind"],
                    "commit": c["definition_commit"],
                    "commit_date": c["definition_commit_date"],
                    "rules_commit": c["rules_commit"],
                    "results_commit": c["results_commit"],
                    "note": c["note"],
                },
                "would_change_our_mind": {"upside": up, "downside": dn},
                "source": {"t": c["source_file"], "u": c["source_url"]},
            })

    # SB-01 prospective entry
    sb_up, sb_dn = MIND["SB-01"]
    entries.append({
        "id": "SB-01",
        "entry_type": "strategy",
        "collection": "shadow-baseline",
        "strategy": "SB-01 singles-only shadow baseline (Pythagorean, exponent 2.0)",
        "track": "single",
        "rule_summary": "Pythagorean matchup probability, exponent 2.0, zero free parameters; "
        "singles only; full frozen rule text in prereg/SB-01-rule.md",
        "sample_window": "2026 Week 11 (13 games) as pipeline test; skill claims require >=200 "
        "settled forecasts (SB-G4)",
        "gates": [
            {"id": "SB-G1", "rule": "recorded_at earlier than every kickoff covered"},
            {"id": "SB-G2", "rule": "model file sha256 unchanged between registration and settlement"},
            {"id": "SB-G3", "rule": "probabilities reproduce from stored PF/PA aggregates"},
            {"id": "SB-G4", "rule": "skill claims need Brier skill CI>0 over >=200 settled forecasts"},
        ],
        "registration": {
            "kind": "prospective",
            "commit": registration_commit(),
            "commit_date": "2026-11-15",
            "rules_commit": registration_commit(),
            "results_commit": None,
            "note": "registration commit contains rule text, policy and model code and NO "
            "results; forecast record written afterwards in a later commit",
        },
        "forecast_record": "data/prereg/forecasts/SB-01_week11_2026.json",
        "would_change_our_mind": {"upside": sb_up, "downside": sb_dn},
        "source": {"t": "prereg/SB-01-rule.md", "u": blob("prereg/SB-01-rule.md", registration_commit())},
    })

    kinds = {}
    for e in entries:
        kinds[e["registration"]["kind"]] = kinds.get(e["registration"]["kind"], 0) + 1
    return {
        "schema": "nfl1.prereg.registry.v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requirement": "brief: pre-register every strategy; two-sided what-would-change-our-mind "
        "on every entry (readiness PR-15, PR-24); flag R26-01 context",
        "policy": "prereg/README.md",
        "counts": {"entries": len(entries), "by_kind": kinds,
                   "collections": len(cols) + 1},
        "entries": entries,
    }


def main() -> int:
    raw = open(GAMES, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    games = list(csv.DictReader(open(GAMES, encoding="utf-8")))

    corpus = build_corpus(games, sha, len(raw))
    jdump("data/prereg/corpus.json", corpus)

    controls = build_controls(games, sha)
    jdump("data/prereg/controls.json", controls)

    regs = build_registrations()
    jdump("data/prereg/registrations.json", regs)

    print(f"corpus: {corpus['membership_counts']}")
    print(f"controls: {[(c['id'], c.get('expected_roi', c.get('roi'))) for c in controls['controls']]}")
    print(f"registrations: {regs['counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
