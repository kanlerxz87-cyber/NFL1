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


# Club slugs as they appear in the official nfl.com team directory (https://www.nfl.com/teams/).
# Used only when the directory links cannot be parsed; every slug is then checked by fetching its roster.
FALLBACK_SLUGS = [
    "arizona-cardinals", "atlanta-falcons", "baltimore-ravens", "buffalo-bills", "carolina-panthers",
    "chicago-bears", "cincinnati-bengals", "cleveland-browns", "dallas-cowboys", "denver-broncos",
    "detroit-lions", "green-bay-packers", "houston-texans", "indianapolis-colts", "jacksonville-jaguars",
    "kansas-city-chiefs", "las-vegas-raiders", "los-angeles-chargers", "los-angeles-rams", "miami-dolphins",
    "minnesota-vikings", "new-england-patriots", "new-orleans-saints", "new-york-giants", "new-york-jets",
    "philadelphia-eagles", "pittsburgh-steelers", "san-francisco-49ers", "seattle-seahawks",
    "tampa-bay-buccaneers", "tennessee-titans", "washington-commanders",
]
# nfl.com logo codes that differ from the abbreviations used in the official injury report.
ABBR_ALIAS = {"AZ": "ARI", "LAR": "LA", "WSH": "WAS", "JAC": "JAX"}


def club_slugs() -> tuple[list[str], str]:
    """Club slugs from the official NFL team directory; falls back to the documented list."""
    slugs: list[str] = []
    try:
        soup = BeautifulSoup(get(TEAMS_INDEX).text, "lxml")
        for a in soup.find_all("a", href=True):
            m = re.match(r"^(?:https://www\.nfl\.com)?/teams/([a-z0-9-]+)/?$", a["href"].strip())
            if m and m.group(1) not in slugs:
                slugs.append(m.group(1))
    except Exception:  # noqa: BLE001 - recorded in the output below
        slugs = []
    if len(slugs) == EXPECTED_CLUBS:
        return slugs, "team directory links"
    return list(FALLBACK_SLUGS), f"documented list (directory parse found {len(slugs)} links)"


def club_abbr(soup: BeautifulSoup) -> str | None:
    """Club abbreviation from the club logo on the roster page (clubs/logos/XXX)."""
    for img in soup.find_all("img", src=True):
        m = re.search(r"clubs/logos/([A-Z]{2,3})(?:[/?\"]|$)", img["src"])
        if m:
            return ABBR_ALIAS.get(m.group(1), m.group(1))
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
    slugs, slug_source = club_slugs()

    for slug in slugs:
        url = f"https://www.nfl.com/teams/{slug}/roster"
        rec = {"slug": slug, "url": url, "fetched_at": now_iso()}
        try:
            r = get(url)
            rec["http_status"] = r.status_code
            rec["sha256"] = hashlib.sha256(r.content).hexdigest()
            soup_title = BeautifulSoup(r.text, "lxml")
            rec["page_title"] = soup_title.title.get_text(" ", strip=True) if soup_title.title else None
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

    parsed = [c for c in clubs if c.get("players") and c.get("abbr")]
    if len(parsed) != EXPECTED_CLUBS:
        status = "partial"
    payload = {
        "season": SEASON,
        "status": status,
        "generated_at": now_iso(),
        "started_at": started,
        "source_index": TEAMS_INDEX,
        "slug_source": slug_source,
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
