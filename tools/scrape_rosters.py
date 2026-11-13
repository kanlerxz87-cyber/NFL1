#!/usr/bin/env python3
"""Scrape the official nfl.com club roster pages into data/backup-register/rosters_2026.json.

Why this exists: nfl.com does not publish a depth chart page (the team depth-chart URL returns 404),
but every club has an official roster page that lists each player's number, position, roster status,
height, weight, years of experience and college. The backup register uses that official roster to show
which same-position players are active when an official designation (Out / Doubtful / Questionable) lands.

Runs in GitHub Actions because the Arena sandbox cannot reach nfl.com. Per club it records the page
URL, HTTP status and SHA-256 of the exact bytes parsed. A club that cannot be parsed is written with an
explicit warning and no players, never filled in from another source.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT_DIR = os.path.join(ROOT, "data", "backup-register")
OUT = os.path.join(OUT_DIR, "rosters_2026.json")
TEAMS_INDEX = "https://www.nfl.com/teams/"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}
SEASON = 2026
EXPECTED_CLUBS = 32
# Column order observed on the official roster table after the name cell.
COLUMNS = ["number", "position", "status", "height", "weight", "experience", "college"]
POS_RE = re.compile(r"^[A-Z]{1,4}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url: str) -> requests.Response:
    last = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except requests.RequestException as exc:  # noqa: PERF203 - retry loop
            last = str(exc)
        time.sleep(2 + attempt * 2)
    raise RuntimeError(f"GET {url} failed: {last}")


def club_slugs() -> list[str]:
    """Club slugs from the official NFL team directory (one profile link per club)."""
    soup = BeautifulSoup(get(TEAMS_INDEX).text, "lxml")
    slugs: list[str] = []
    for a in soup.find_all("a", href=True):
        m = re.match(r"^https://www\.nfl\.com/teams/([a-z0-9-]+)/?$", a["href"])
        if m and m.group(1) not in slugs:
            slugs.append(m.group(1))
    return slugs


def club_abbr(soup: BeautifulSoup) -> str | None:
    """Club abbreviation from the club logo on the roster page (clubs/logos/XXX)."""
    for img in soup.find_all("img", src=True):
        m = re.search(r"clubs/logos/([A-Z]{2,3})(?:[/?\"]|$)", img["src"])
        if m:
            return m.group(1)
    return None


def parse_roster(html: str) -> tuple[str | None, list[dict], list[str]]:
    soup = BeautifulSoup(html, "lxml")
    abbr = club_abbr(soup)
    warnings: list[str] = []
    players: list[dict] = []
    for tr in soup.find_all("tr"):
        link = tr.find("a", href=re.compile(r"/players/"))
        if link is None:
            continue
        cells = tr.find_all(["td", "th"])
        texts = [c.get_text(" ", strip=True) for c in cells]
        # The name cell is the one that holds the player link; the rest are data cells.
        name_idx = next((i for i, c in enumerate(cells) if c.find("a", href=re.compile(r"/players/"))), 0)
        name = link.get_text(" ", strip=True)
        data = [t for i, t in enumerate(texts) if i != name_idx]
        rec = {"name": name, "player_url": link["href"], "raw_cells": texts}
        if len(data) < len(COLUMNS):
            warnings.append(f"row has {len(data)} data cells, expected {len(COLUMNS)}: {name}")
            data = data + [""] * (len(COLUMNS) - len(data))
        for key, val in zip(COLUMNS, data[: len(COLUMNS)]):
            rec[key] = val or None
        if not (rec.get("position") and POS_RE.match(rec["position"])):
            warnings.append(f"unexpected position value {rec.get('position')!r}: {name}")
        players.append(rec)
    return abbr, players, warnings


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    started = now_iso()
    clubs: list[dict] = []
    status = "ok"
    try:
        slugs = club_slugs()
    except Exception as exc:  # noqa: BLE001 - recorded, never silently ignored
        slugs = []
        status = "failed"
        clubs.append({"slug": None, "error": f"team directory failed: {exc}", "players": []})

    if slugs and len(slugs) != EXPECTED_CLUBS:
        status = "partial"

    for slug in slugs:
        url = f"https://www.nfl.com/teams/{slug}/roster"
        rec = {"slug": slug, "url": url, "fetched_at": now_iso()}
        try:
            r = get(url)
            rec["http_status"] = r.status_code
            rec["sha256"] = hashlib.sha256(r.content).hexdigest()
            abbr, players, warnings = parse_roster(r.text)
            rec.update({"abbr": abbr, "player_count": len(players), "warnings": warnings,
                        "players": players})
            if not abbr or len(players) < 40:
                rec["warnings"].append(f"only {len(players)} player rows parsed; club marked partial")
                status = "partial"
        except Exception as exc:  # noqa: BLE001
            rec.update({"abbr": None, "player_count": 0, "error": str(exc), "players": []})
            status = "partial"
        clubs.append(rec)
        time.sleep(1)

    parsed = [c for c in clubs if c.get("players")]
    payload = {
        "season": SEASON,
        "status": status,
        "generated_at": now_iso(),
        "started_at": started,
        "source_index": TEAMS_INDEX,
        "method": ("Each row is one player on the club's official nfl.com roster page. Values are copied "
                   "from the page's own table cells; none are inferred. Depth order is not on this page."),
        "counts": {
            "clubs_expected": EXPECTED_CLUBS,
            "clubs_found": len(slugs),
            "clubs_parsed": len(parsed),
            "players": sum(c.get("player_count", 0) for c in clubs),
            "row_warnings": sum(len(c.get("warnings", [])) for c in clubs),
        },
        "clubs": clubs,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(payload["counts"]), "status:", status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
