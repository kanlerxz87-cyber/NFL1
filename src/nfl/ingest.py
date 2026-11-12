"""Load the verified TSV snapshots into typed records.

Nothing here derives, defaults or fills a value. A missing cell stays missing
and is reported as such by verify.py.
"""
from __future__ import annotations

import csv
import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERIFIED_DIR = ROOT / "data" / "verified"
PROCESSED_DIR = ROOT / "data" / "processed"
REFERENCE_DIR = ROOT / "data" / "reference"

PRACTICE_LABELS = {
    "FP": "Full Participation in Practice",
    "LP": "Limited Participation in Practice",
    "DNP": "Did Not Participate In Practice",
}

PLAYER_URL_PREFIX = "https://www.nfl.com/players/"
INJURY_REPORT_URL = "https://www.nfl.com/injuries/"
STANDINGS_URL = "https://www.nfl.com/standings/"
#: Community mirror (nflverse). Labels and colours only - never on-field values.
TEAM_REF_URL = "https://github.com/nflverse/nflverse-pbp/blob/master/teams_colors_logos.csv"


def _read_tsv(name: str) -> list[dict[str, str]]:
    with (VERIFIED_DIR / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _int(raw: str) -> int | None:
    raw = (raw or "").strip()
    return int(raw) if raw not in ("", "-") else None


def _float(raw: str) -> float | None:
    raw = (raw or "").strip()
    return float(raw) if raw not in ("", "-") else None


def _wl(raw: str) -> tuple[int | None, int | None, int | None]:
    raw = (raw or "").strip()
    if not raw:
        return (None, None, None)
    parts = raw.split("-")
    if len(parts) != 3:
        return (None, None, None)
    return (_int(parts[0]), _int(parts[1]), _int(parts[2]))


def sources() -> dict[str, Any]:
    with (VERIFIED_DIR / "sources.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def standings() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in _read_tsv("standings_2026_reg.tsv"):
        hw, hl, ht = _wl(r["home"])
        rw, rl, rt = _wl(r["road"])
        dw, dl, dt = _wl(r["div"])
        cw, cl, ct = _wl(r["conf"])
        nw, nl, nt = _wl(r["non_conf"])
        rows.append({
            "team_abbr": r["team_abbr"], "conference": r["conference"],
            "division": r["division"],
            "w": _int(r["w"]), "l": _int(r["l"]), "t": _int(r["t"]),
            "pct": _float(r["pct"]), "pf": _int(r["pf"]), "pa": _int(r["pa"]),
            "net_pts": _int(r["net_pts"]),
            "home": r["home"], "road": r["road"],
            "home_w": hw, "home_l": hl, "home_t": ht,
            "road_w": rw, "road_l": rl, "road_t": rt,
            "div": r["div"], "div_pct": _float(r["div_pct"]),
            "div_w": dw, "div_l": dl, "div_t": dt,
            "conf": r["conf"], "conf_pct": _float(r["conf_pct"]),
            "conf_w": cw, "conf_l": cl, "conf_t": ct,
            "non_conf": r["non_conf"],
            "non_conf_w": nw, "non_conf_l": nl, "non_conf_t": nt,
            "strk": r["strk"], "last5": r["last5"],
            "source_url": STANDINGS_URL,
        })
    return rows


def schedule() -> list[dict[str, Any]]:
    return [{**r, "week": _int(r["week"]), "source_url": INJURY_REPORT_URL}
            for r in _read_tsv("schedule_2026_week10.tsv")]


def byes() -> list[dict[str, Any]]:
    return [{**r, "week": _int(r["week"]), "source_url": INJURY_REPORT_URL}
            for r in _read_tsv("bye_week10.tsv")]


def team_report_status() -> list[dict[str, Any]]:
    return [{**r, "week": _int(r["week"]), "source_url": INJURY_REPORT_URL}
            for r in _read_tsv("team_report_status_week10.tsv")]


def injuries() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in _read_tsv("injury_report_2026_week10.tsv"):
        code = (r["practice"] or "").strip()
        rows.append({
            "team_abbr": r["team_abbr"], "player": r["player"],
            "position": r["position"],
            # Blank means blank: NFL.com published no designation for this row
            # at retrieval time. A body part is never inferred.
            "injury": (r["injury"] or "").strip() or None,
            "practice_code": code or None,
            "practice_label": PRACTICE_LABELS.get(code),
            "game_status": (r["game_status"] or "").strip() or None,
            "player_url": PLAYER_URL_PREFIX + r["player_slug"] + "/",
            "source_url": INJURY_REPORT_URL,
        })
    return rows


def news() -> list[dict[str, Any]]:
    return [{**r, "tier": "VERIFIED"} for r in _read_tsv("nfl_news_2026_week10.tsv")]


def teams_reference() -> list[dict[str, Any]]:
    """Community-mirror team metadata - labels and colours only, never stats."""
    path = REFERENCE_DIR / "teams.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [{"tier": "COMMUNITY_MIRROR", "source_url": TEAM_REF_URL, **r}
                for r in csv.DictReader(fh)]
