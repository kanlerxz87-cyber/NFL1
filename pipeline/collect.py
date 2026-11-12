#!/usr/bin/env python3
"""Collect NFL data from official-derived public releases (nflverse) with full provenance.

Why nflverse: nfl.com (the NFL's own site) does not publish machine-readable bulk
play-by-play, injury-report history or depth-chart history, and nfl.com blocks
non-browser clients. nflverse (https://github.com/nflverse/nflverse-data) publishes
parsed copies of the NFL's Game Statistics & Information System (GSIS) feed plus the
official weekly injury reports and depth charts. Every file's download URL, size,
sha256 and fetch time is recorded so each number on the site can be traced.

This script runs inside GitHub Actions (full internet). It never invents values:
if a file is missing it is skipped and recorded as missing.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone

import requests

RAW = os.path.join(os.path.dirname(__file__), "..", "build", "raw")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "model")
BASE = "https://github.com/nflverse/nflverse-data/releases/download"

# (release tag, asset, local name, what it is, official upstream link)
SOURCES = [
    ("schedules", "games.csv", "games.csv",
     "Game results, closing spread/total/moneylines, rest days, roof, surface, officials",
     "https://www.nfl.com/schedules/"),
    ("teams", "teams_colors_logos.csv", "teams.csv",
     "Club directory: abbreviation, full name, conference, division, colors, logo",
     "https://www.nfl.com/teams/"),
    ("players", "players.csv", "players.csv",
     "Player master (GSIS id, position, debut year, draft, latest team)",
     "https://www.nfl.com/players/"),
    ("injuries", "injuries_2026.csv", "injuries_2026.csv",
     "Official weekly injury report, 2026 season (game status + practice status)",
     "https://www.nfl.com/injuries/"),
    ("injuries", "injuries_2025.csv", "injuries_2025.csv",
     "Official weekly injury report, 2025 season",
     "https://www.nfl.com/injuries/"),
    ("depth_charts", "depth_charts_2026.parquet", "depth_charts_2026.parquet",
     "Weekly depth charts, 2026 (starter=1, backup=2, ...)",
     "https://www.nfl.com/teams/"),
    ("weekly_rosters", "roster_weekly_2026.parquet", "roster_weekly_2026.parquet",
     "Weekly roster status (Active / Injured Reserve / Practice Squad) 2026",
     "https://www.nfl.com/players/"),
    ("snap_counts", "snap_counts_2026.parquet", "snap_counts_2026.parquet",
     "Offensive/defensive snap counts by player and week, 2026",
     "https://www.nfl.com/stats/player-stats/"),
    ("stats_player", "stats_player_week_2026.parquet", "stats_player_week_2026.parquet",
     "Player weekly stat lines, 2026 (passing/rushing/receiving)",
     "https://www.nfl.com/stats/player-stats/"),
    ("pbp", "play_by_play_2026.parquet", "pbp_2026.parquet",
     "Play-by-play with EPA/success, 2026 season to date",
     "https://www.nfl.com/stats/"),
    ("pbp", "play_by_play_2025.parquet", "pbp_2025.parquet",
     "Play-by-play with EPA/success, 2025 season (model training/validation)",
     "https://www.nfl.com/stats/"),
    ("pbp", "play_by_play_2024.parquet", "pbp_2024.parquet",
     "Play-by-play with EPA/success, 2024 season (model training/validation)",
     "https://www.nfl.com/stats/"),
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
            with requests.get(url, stream=True, timeout=180, allow_redirects=True) as r:
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
    files = []
    for tag, asset, local, desc, official in SOURCES:
        url = f"{BASE}/{tag}/{asset}"
        dest = os.path.join(RAW, local)
        print(f"fetching {tag}/{asset} -> {local}")
        size = download(url, dest) if not os.path.exists(dest) else os.path.getsize(dest)
        rec = {
            "local": local,
            "release_tag": tag,
            "asset": asset,
            "url": url,
            "official_upstream": official,
            "description": desc,
            "bytes": size,
            "status": "ok" if size else "unavailable",
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sha256": sha256(dest) if size else None,
        }
        files.append(rec)
        print(f"  {'ok' if size else 'MISSING'} {size}")

    prov = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_repo": "https://github.com/nflverse/nflverse-data",
        "source_note": (
            "nflverse parses the NFL's GSIS feed, the official weekly injury report and the "
            "official depth charts. Files are pinned by URL + sha256 below. nfl.com is the "
            "primary publisher but blocks automated clients, so nfl.com pages are cited as "
            "the official entry point and spot-checked separately (see verification.json)."
        ),
        "files": files,
    }
    with open(os.path.join(OUT, "provenance.json"), "w") as f:
        json.dump(prov, f, indent=1)
    print("wrote data/model/provenance.json")


if __name__ == "__main__":
    main()
