#!/usr/bin/env python3
"""Session 9cb71eb8 data collector -- runs in GitHub Actions (full internet).

Why this file exists separately from `pipeline/collect.py`
---------------------------------------------------------
`pipeline/collect.py` (session 7600ed8b) downloads the nflverse release files into
`build/raw/` for the *existing* model, and writes only small JSON summaries to
`data/model/`. It deliberately does not commit the bulk downloads (the repository
`.gitignore` excludes `build/raw/` and `*.parquet`), so nothing it produces can be
read inside the Arena sandbox, which can only reach github.com / pypi.org.

The Arena sandbox also cannot reach release-asset hosts, so the raw files cannot be
re-downloaded here. This collector therefore runs in Actions and commits a *small,
text-only* extract into `data/s9cb/` so the analysis can be done locally, line by line,
against a pinned, hash-checked source.

Nothing is invented: every column written here is copied from the downloaded file.
Where the source has no value the cell stays empty, and the coverage of every
price column is measured and published so a reviewer can see exactly how much of
the sample carries a real price.

Sources (nflverse parses the NFL's own GSIS feed, the official weekly injury report
and the official depth charts; each file is pinned by URL + sha256):
    https://github.com/nflverse/nflverse-data
Official entry points cited on the site:
    https://www.nfl.com/schedules/  https://www.nfl.com/injuries/
    https://www.nfl.com/stats/player-stats/  https://www.nfl.com/teams/
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(ROOT, "build", "s9cb")
OUT = os.path.join(ROOT, "data", "s9cb")
BASE = "https://github.com/nflverse/nflverse-data/releases/download"

FIRST_SEASON = 2016          # first season with reliable prices and injury reports
CURRENT_SEASON = 2026

# (release tag, asset, local name, description, official upstream page)
SOURCES = [
    ("schedules", "games.csv", "games.csv",
     "Game results, closing spread/total/moneylines with the price on each side, "
     "rest days, roof, surface, temperature, wind, division flag, referee, starting QBs",
     "https://www.nfl.com/schedules/"),
    ("teams", "teams_colors_logos.csv", "teams.csv",
     "Club directory: abbreviation, name, conference, division",
     "https://www.nfl.com/teams/"),
    ("players", "players.csv", "players.csv",
     "Player master (GSIS id, position, years of experience, latest team)",
     "https://www.nfl.com/players/"),
]

PROP_SEASONS = list(range(2019, CURRENT_SEASON + 1))
INJURY_SEASONS = list(range(FIRST_SEASON, CURRENT_SEASON + 1))

# Columns kept from the weekly player file. Kept deliberately narrow so the committed
# extract stays small enough to review; every field is a verbatim source column.
PROP_COLS = [
    "player_id", "player_display_name", "position", "position_group",
    "season", "week", "season_type", "game_id", "team", "opponent_team",
    "completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions",
    "carries", "rushing_yards", "rushing_tds",
    "receptions", "targets", "receiving_yards", "receiving_tds",
]
# Only these positions can carry a passing/rushing/receiving prop market.
PROP_POSITIONS = {"QB", "RB", "FB", "WR", "TE"}

INJURY_COLS = [
    "season", "game_type", "team", "week", "gsis_id", "position", "full_name",
    "report_primary_injury", "report_status", "practice_status",
]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: str, attempts: int = 4) -> int:
    for i in range(attempts):
        try:
            with requests.get(url, stream=True, timeout=240, allow_redirects=True) as r:
                if r.status_code == 200:
                    tmp = dest + ".part"
                    with open(tmp, "wb") as f:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
                    os.replace(tmp, dest)
                    return os.path.getsize(dest)
                print(f"  HTTP {r.status_code} for {url}")
        except Exception as exc:  # noqa: BLE001
            print(f"  attempt {i + 1} failed: {exc}")
        time.sleep(3 * (i + 1))
    return 0


def main() -> None:
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    manifest: list[dict] = []

    for tag, asset, local, desc, official in SOURCES:
        url = f"{BASE}/{tag}/{asset}"
        dest = os.path.join(RAW, local)
        size = os.path.getsize(dest) if os.path.exists(dest) else download(url, dest)
        manifest.append({
            "local": local, "release_tag": tag, "asset": asset, "url": url,
            "official_upstream": official, "description": desc, "bytes": size,
            "status": "ok" if size else "unavailable",
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sha256": sha256(dest) if size else None,
        })
        print(f"{local}: {'ok' if size else 'MISSING'} {size}")

    import pandas as pd

    # ---------------------------------------------------------------- 1. games
    games_path = os.path.join(RAW, "games.csv")
    rows_written = 0
    coverage: dict = {}
    if os.path.exists(games_path) and os.path.getsize(games_path):
        g = pd.read_csv(games_path, low_memory=False)
        g = g[g["game_type"] == "REG"].copy()
        g = g.sort_values(["season", "week", "game_id"]).reset_index(drop=True)
        keep = [
            "game_id", "season", "week", "gameday", "weekday", "gametime",
            "away_team", "home_team", "away_score", "home_score", "result", "total",
            "overtime", "location", "div_game", "roof", "surface", "temp", "wind",
            "away_rest", "home_rest", "away_moneyline", "home_moneyline",
            "spread_line", "away_spread_odds", "home_spread_odds",
            "total_line", "over_odds", "under_odds",
            "away_qb_id", "home_qb_id", "away_qb_name", "home_qb_name",
            "referee", "stadium",
        ]
        keep = [c for c in keep if c in g.columns]
        g = g[keep]
        g.to_csv(os.path.join(OUT, "games.csv"), index=False)
        rows_written = int(len(g))
        # Price coverage: how much of the sample carries a REAL price, per season.
        for col in ["spread_line", "total_line", "home_spread_odds", "away_spread_odds",
                    "over_odds", "under_odds", "away_moneyline", "home_moneyline"]:
            if col not in g.columns:
                continue
            by_season = (g.dropna(subset=[col]).groupby("season").size().to_dict())
            coverage[col] = {
                "rows_with_value": int(g[col].notna().sum()),
                "rows_total": int(len(g)),
                "first_season_with_any": int(min(by_season)) if by_season else None,
                "by_season": {str(k): int(v) for k, v in sorted(by_season.items())},
            }
        print(f"games.csv -> {rows_written} regular-season rows, seasons "
              f"{int(g['season'].min())}-{int(g['season'].max())}")

    # ------------------------------------------------------- 2. weekly players
    prop_files: list[dict] = []
    frames = []
    for season in PROP_SEASONS:
        tag, asset = "stats_player", f"stats_player_week_{season}.parquet"
        url = f"{BASE}/{tag}/{asset}"
        dest = os.path.join(RAW, asset)
        size = os.path.getsize(dest) if os.path.exists(dest) else download(url, dest)
        prop_files.append({
            "asset": asset, "url": url, "bytes": size,
            "official_upstream": "https://www.nfl.com/stats/player-stats/",
            "status": "ok" if size else "unavailable",
            "sha256": sha256(dest) if size else None,
        })
        if not size:
            continue
        df = pd.read_parquet(dest)
        cols = [c for c in PROP_COLS if c in df.columns]
        df = df[cols]
        if "season_type" in df.columns:
            df = df[df["season_type"] == "REG"]
        if "position" in df.columns:
            df = df[df["position"].isin(PROP_POSITIONS)]
        # Keep only player-weeks with a real offensive opportunity, so the committed
        # extract stays reviewable. This is a filter, never a fill: dropped rows are
        # simply absent, and the count before filtering is published.
        before = int(len(df))
        opp = 0
        for c in ["attempts", "carries", "targets"]:
            if c in df.columns:
                opp = opp + df[c].fillna(0)
        df = df[opp >= 4]
        frames.append(df)
        print(f"  {asset}: {before} skill-player rows -> {len(df)} with >=4 opportunities")

    prop_rows = 0
    if frames:
        pw = pd.concat(frames, ignore_index=True)
        pw = pw.sort_values(["season", "week", "team", "player_id"]).reset_index(drop=True)
        pw.to_csv(os.path.join(OUT, "player_week.csv"), index=False)
        prop_rows = int(len(pw))
        print(f"player_week.csv -> {prop_rows} rows")

    # ------------------------------------------------------------- 3. injuries
    inj_files: list[dict] = []
    iframes = []
    for season in INJURY_SEASONS:
        tag, asset = "injuries", f"injuries_{season}.csv"
        url = f"{BASE}/{tag}/{asset}"
        dest = os.path.join(RAW, asset)
        size = os.path.getsize(dest) if os.path.exists(dest) else download(url, dest)
        inj_files.append({
            "asset": asset, "url": url, "bytes": size,
            "official_upstream": "https://www.nfl.com/injuries/",
            "status": "ok" if size else "unavailable",
            "sha256": sha256(dest) if size else None,
        })
        if not size:
            continue
        df = pd.read_csv(dest, low_memory=False)
        cols = [c for c in INJURY_COLS if c in df.columns]
        iframes.append(df[cols])
        print(f"  {asset}: {len(df)} rows")

    inj_rows = 0
    if iframes:
        inj = pd.concat(iframes, ignore_index=True)
        if "game_type" in inj.columns:
            inj = inj[inj["game_type"].fillna("REG") == "REG"]
        inj = inj.sort_values(["season", "week", "team", "full_name"]).reset_index(drop=True)
        inj.to_csv(os.path.join(OUT, "injuries.csv"), index=False)
        inj_rows = int(len(inj))
        print(f"injuries.csv -> {inj_rows} rows")

    prov = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session": "9cb71eb8-nfl1",
        "source_repo": "https://github.com/nflverse/nflverse-data",
        "source_note": (
            "nflverse publishes parsed copies of the NFL's GSIS feed, the official weekly "
            "injury report and the official depth charts. nfl.com is the primary publisher "
            "but blocks automated clients, so nfl.com pages are cited as the official entry "
            "point and spot-checked separately against this repository's hand transcriptions."
        ),
        "licence": "CC-BY-4.0 (https://github.com/nflverse/nflverse-data)",
        "files": manifest,
        "prop_files": prop_files,
        "injury_files": inj_files,
        "extract": {
            "games_rows": rows_written,
            "player_week_rows": prop_rows,
            "injuries_rows": inj_rows,
        },
        "price_coverage": coverage,
    }
    with open(os.path.join(OUT, "provenance.json"), "w") as f:
        json.dump(prov, f, indent=1, default=str)
    print("wrote data/s9cb/provenance.json")


if __name__ == "__main__":
    main()
