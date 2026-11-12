#!/usr/bin/env python3
"""Dump the real schema of every collected file so column names are never guessed.

Output: data/model/schema.json  (columns, dtypes, row counts, first rows for dates).
Also validates that each expected column family exists and records gaps, which is how
the site knows what it must leave blank.
"""
from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone

import pandas as pd

RAW = os.path.join(os.path.dirname(__file__), "..", "build", "raw")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "model")

EXPECT = {
    "games.csv": ["season", "week", "game_type", "gameday", "away_team", "home_team",
                  "away_score", "home_score", "spread_line", "total_line", "result"],
    "injuries_2026.csv": ["season", "week", "team", "position", "full_name",
                          "report_status", "practice_status"],
    "depth_charts_2026.parquet": ["team", "player_name", "pos_abb", "depth_team", "dt"],
    "roster_weekly_2026.parquet": ["team", "position", "status", "week"],
    "snap_counts_2026.parquet": ["team", "player", "week", "offense_snaps", "defense_snaps"],
    "stats_player_week_2026.parquet": ["player_id", "week", "passing_yards"],
    "pbp_2026.parquet": ["game_id", "posteam", "defteam", "epa", "play_type", "week"],
    "players.csv": ["gsis_id", "display_name", "position", "debut_year", "latest_team"],
    "teams.csv": ["team_abbr", "team_name", "team_conf", "team_division"],
}


def read(path: str, nrows: int | None = None) -> pd.DataFrame:
    if path.endswith(".parquet"):
        df = pd.read_parquet(path)
        return df.head(nrows) if nrows else df
    return pd.read_csv(path, nrows=nrows, low_memory=False)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    report: dict = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "files": {}, "missing_expectations": []}
    for path in sorted(glob.glob(os.path.join(RAW, "*"))):
        name = os.path.basename(path)
        try:
            df = read(path)
            entry = {
                "rows": int(len(df)),
                "columns": list(df.columns),
                "dtypes": {c: str(t) for c, t in df.dtypes.items()},
                "head": json.loads(df.head(2).to_json(orient="records", date_format="iso")),
            }
            missing = [c for c in EXPECT.get(name, []) if c not in df.columns]
            entry["missing_expected_columns"] = missing
            if missing:
                report["missing_expectations"].append({"file": name, "missing": missing})
            report["files"][name] = entry
            print(f"{name}: {len(df)} rows, {len(df.columns)} cols, missing={missing}")
        except Exception as exc:  # noqa: BLE001
            report["files"][name] = {"error": str(exc)}
            print(f"{name}: ERROR {exc}")
    with open(os.path.join(OUT, "schema.json"), "w") as f:
        json.dump(report, f, indent=1)
    print("wrote data/model/schema.json")


if __name__ == "__main__":
    main()
