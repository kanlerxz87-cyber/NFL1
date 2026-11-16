#!/usr/bin/env python3
"""lab2/lib.py — shared helpers for the Origination Desk sub-site (session a35ddf45-nfl1).

House rules, enforced here rather than by convention:

* No invented values.  Every table cell is either read from a committed file, read from an
  official page recorded in `lab2/data/official_reads.json`, or the explicit string
  "Unverified".  There is no third option, and `lab2/verify.py` fails the build if one appears.
* Every row carries `source` (an https URL) and `retrieved` (the date the cited page was read).
* Derived arithmetic is computed in `build_data.py` from stored inputs and never typed in, so
  a printed difference always equals the difference of the printed numbers it cites.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "lab2", "data")

UNVERIFIED = "Unverified"

# Official pages read during this session, with the exact URL.  Anything a page cites must
# appear here so the verification step can check that the link is one this session opened.
OFFICIAL = {
    "standings": "https://www.nfl.com/standings/league/2026/reg",
    "injuries_w10": "https://www.nfl.com/injuries/league/2026/reg10",
    "schedule_w11": "https://www.nfl.com/schedules/2026/by-week/week-11",
    "schedule_results": "https://www.nfl.com/schedules/2026/REG11",
}

NFL_TEAMS = ["ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET",
             "GB", "HOU", "IND", "JAX", "KC", "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO",
             "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"]

# nfl.com prints AZ and LA where the mirrored feed prints ARI and LAR.  The mapping is
# directional and only used for joins; the row keeps the code the source printed.
NFLCOM_TO_FEED = {"AZ": "ARI", "LA": "LAR"}


def load(rel: str, default=None):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_tsv(rel: str):
    import csv
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def sha256_of(rel: str) -> str:
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(name: str, obj) -> str:
    path = os.path.join(DATA, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write("\n")
    return path


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def r2(x):
    """Round once, to two decimals, or return None (never 0 for a missing value)."""
    return None if x is None else round(float(x) + 0.0, 2)
