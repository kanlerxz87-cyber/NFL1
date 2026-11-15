#!/usr/bin/env python3
"""shadow_forecast.py — produce the frozen shadow-v1 forecast record (P2, session 55dc53f4-nfl1).

Rule text: prereg/shadow-v1.md. Parameters and input hashes: prereg/shadow-v1.json.
This tool REFUSES to run if the corpus, the fixture table or this file differ from the hashes
recorded in the registration. It uses only the Python standard library (no numpy).

    python3 tools/shadow_forecast.py          # writes data/shadow/forecasts_week11_v1.json
    python3 tools/shadow_forecast.py --check  # recompute and fail if the record on disk differs

Model (shadow-v1, singles only):
    margin_home = b * h + (r_home - r_away)
    h = 1 unless the game is at a neutral site (official rule, see prereg)
    ratings r (32 clubs) and intercept b minimise  sum (y - b h - dr)^2 + lambda * sum r^2
    sigma = sqrt(SSE / n) on the training corpus (in-sample residual standard deviation)
    P(home win) = Phi(margin_home / sigma)
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREREG = os.path.join(ROOT, "prereg/shadow-v1.json")
OUT = os.path.join(ROOT, "data/shadow/forecasts_week11_v1.json")
CODE_FILE = os.path.abspath(__file__)


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_prereg() -> dict:
    with open(PREREG, encoding="utf-8") as fh:
        return json.load(fh)


def verify_inputs(p: dict) -> None:
    checks = [
        ("corpus", os.path.join(ROOT, p["corpus"]["file"]), p["corpus"]["sha256"]),
        ("fixtures", os.path.join(ROOT, p["fixtures"]["file"]), p["fixtures"]["sha256"]),
        ("code", CODE_FILE, p["code_sha256"]),
    ]
    for name, path, want in checks:
        got = sha256_file(path)
        if got != want:
            raise SystemExit(f"REFUSED: {name} hash differs from the registration\n  file {path}\n  registered {want}\n  found      {got}")


def solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Gauss-Jordan elimination with partial pivoting (small dense systems only)."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[piv] = m[piv], m[c]
        pv = m[c][c]
        if abs(pv) < 1e-12:
            raise SystemExit("singular system")
        m[c] = [v / pv for v in m[c]]
        for r in range(n):
            if r != c and m[r][c] != 0.0:
                f = m[r][c]
                m[r] = [vr - f * vc for vr, vc in zip(m[r], m[c])]
    return [m[i][n] for i in range(n)]


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def load_corpus(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["away_score"] = int(r["away_score"])
        r["home_score"] = int(r["home_score"])
        r["neutral"] = "International" in (r.get("note") or "")
    return rows


def load_fixtures(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fit(corpus: list[dict], teams: list[str], lam: float) -> tuple[float, dict, float]:
    idx = {t: i for i, t in enumerate(teams)}
    k = len(teams) + 1  # column 0 = home-field term b, then one rating per club
    xtx = [[0.0] * k for _ in range(k)]
    xty = [0.0] * k
    rows = []
    for g in corpus:
        h = 0.0 if g["neutral"] else 1.0
        y = float(g["home_score"] - g["away_score"])
        x = [0.0] * k
        x[0] = h
        x[1 + idx[g["home_abbr"]]] += 1.0
        x[1 + idx[g["away_abbr"]]] -= 1.0
        rows.append((x, y))
        for i in range(k):
            if x[i] == 0.0:
                continue
            xty[i] += x[i] * y
            for j in range(k):
                xtx[i][j] += x[i] * x[j]
    for i in range(1, k):
        xtx[i][i] += lam  # ridge on ratings only; b is unpenalised
    beta = solve(xtx, xty)
    sse = 0.0
    for x, y in rows:
        pred = sum(xi * bi for xi, bi in zip(x, beta))
        sse += (y - pred) ** 2
    sigma = math.sqrt(sse / len(rows))
    ratings = {t: beta[1 + idx[t]] for t in teams}
    return beta[0], ratings, sigma


US_LOCATION = ("NY", "NJ", "CA", "CO", "MI", "MD", "MO", "IL", "NC", "TX", "PA")


def is_united_states(location: str) -> bool:
    """A location printed as 'CITY, ST' with a US state code is inside the United States."""
    tail = location.strip().upper().split(",")[-1].strip()
    return tail in US_LOCATION


def record_wins(corpus: list[dict]) -> dict:
    w = {}
    for g in corpus:
        hs, aws = g["home_score"], g["away_score"]
        for team, own, opp in ((g["home_abbr"], hs, aws), (g["away_abbr"], aws, hs)):
            d = w.setdefault(team, {"w": 0, "l": 0, "t": 0})
            if own > opp:
                d["w"] += 1
            elif own < opp:
                d["l"] += 1
            else:
                d["t"] += 1
    return w


def pct(d: dict) -> float:
    n = d["w"] + d["l"] + d["t"]
    return (d["w"] + 0.5 * d["t"]) / n if n else 0.5


def build() -> dict:
    p = load_prereg()
    verify_inputs(p)
    corpus = load_corpus(os.path.join(ROOT, p["corpus"]["file"]))
    fixtures = load_fixtures(os.path.join(ROOT, p["fixtures"]["file"]))
    teams = sorted({g["home_abbr"] for g in corpus} | {g["away_abbr"] for g in corpus})
    for f in fixtures:
        for t in (f["home"], f["away"]):
            if t not in teams:
                raise SystemExit(f"fixture team {t} has no ratings (not in corpus)")
    lam = float(p["model"]["penalty_lambda"])
    b, ratings, sigma = fit(corpus, teams, lam)
    wins = record_wins(corpus)
    rng = random.Random(int(p["benchmarks"]["control_random"]["seed"]))

    games = []
    for f in sorted(fixtures, key=lambda r: (r["gameday"], r["game_id"])):
        # neutral-site rule (registered): the official game-centre location is outside the United States.
        neutral = not is_united_states(f["location_as_printed"])
        h = 0.0 if neutral else 1.0
        dr = ratings[f["home"]] - ratings[f["away"]]
        margin = b * h + dr
        p_home = norm_cdf(margin / sigma)
        coin = "home" if rng.random() < 0.5 else "away"
        ph, pa = pct(wins.get(f["home"], {"w": 0, "l": 0, "t": 0})), pct(wins.get(f["away"], {"w": 0, "l": 0, "t": 0}))
        fav = "home" if ph >= pa else "away"
        games.append({
            "game_id": f["game_id"],
            "gameday": f["gameday"],
            "weekday": f["weekday"],
            "kickoff_et_as_printed": f["kickoff_et_as_printed"],
            "away": f["away"],
            "home": f["home"],
            "venue": {"stadium_as_printed": f["stadium_as_printed"], "location_as_printed": f["location_as_printed"],
                      "game_centre_url": f["game_centre_url"]},
            "neutral_site": neutral,
            "h": h,
            "inputs": {"r_home": round(ratings[f["home"]], 4), "r_away": round(ratings[f["away"]], 4),
                       "home_field_term_b": round(b, 4), "sigma": round(sigma, 4), "lambda": lam},
            "predicted_margin_home": round(margin, 3),
            "p_home_win": round(p_home, 4),
            "benchmarks": {
                "coin_p_home_win": 0.5,
                "control_random_pick": coin,
                "control_favourite_record_pick": fav,
                "favourite_record_pct": {"home": round(ph, 4), "away": round(pa, 4)},
            },
        })

    out = {
        "model": p["id"],
        "record_type": "pre-kickoff shadow forecast (singles only). Not a bet, not a staking recommendation.",
        "first_kickoff_utc": p["kickoff_cutoff_utc"],
        "corpus": {"file": p["corpus"]["file"], "sha256": p["corpus"]["sha256"], "n_games": len(corpus)},
        "fixtures": {"file": p["fixtures"]["file"], "sha256": p["fixtures"]["sha256"], "n_games": len(fixtures)},
        "code_sha256": p["code_sha256"],
        "parameters": {"penalty_lambda": lam, "home_field_term_b": round(b, 4), "sigma": round(sigma, 4),
                       "clubs": len(teams), "training_games": len(corpus),
                       "training_neutral_games": sum(1 for g in corpus if g["neutral"])},
        "ratings": {t: round(ratings[t], 4) for t in sorted(ratings)},
        "games": games,
    }
    return out


def main() -> int:
    out = build()
    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        if not os.path.exists(OUT) or open(OUT, encoding="utf-8").read() != text:
            print("FAIL: forecast record on disk differs from a recomputation")
            return 1
        print("OK: forecast record reproduces byte for byte")
        return 0
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(out['games'])} forecasts, "
          f"b={out['parameters']['home_field_term_b']}, sigma={out['parameters']['sigma']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
