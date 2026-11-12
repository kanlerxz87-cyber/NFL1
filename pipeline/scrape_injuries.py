#!/usr/bin/env python3
"""Scrape the official NFL injury report (nfl.com/injuries) for the current week.

Why this exists: the mirrored feed (nflverse) lags the league by a week or more in-season,
and the brief requires current injury tracking. nfl.com blocks the Arena sandbox but is
reachable from GitHub Actions, so this runs there. It parses the page's own tables, keeps a
per-player nfl.com link, and records the page hash. If parsing fails nothing is written and
the build falls back to the mirrored feed with a published warning.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone

import pandas as pd
import requests
from bs4 import BeautifulSoup

RAW = os.path.join(os.path.dirname(__file__), "..", "build", "raw")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "model")
URL = "https://www.nfl.com/injuries/"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch() -> str:
    r = requests.get(URL, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.text


def nicknames() -> dict[str, str]:
    """Map club nickname -> CURRENT abbreviation.

    teams.csv contains historical franchise rows (OAK, STL, SD), so only clubs that appear in
    the 2026 schedule are allowed to register a nickname.
    """
    teams = pd.read_csv(os.path.join(RAW, "teams.csv"))
    active = set()
    try:
        g = pd.read_csv(os.path.join(RAW, "games.csv"))
        g = g[g["season"] == g["season"].max()]
        active = set(g["home_team"]) | set(g["away_team"])
    except Exception:  # noqa: BLE001
        active = set(teams["team_abbr"])
    teams = teams[teams["team_abbr"].isin(active)].drop_duplicates("team_abbr")
    out = {}
    for _, t in teams.iterrows():
        for key in (t.get("team_nick"), t.get("team_name")):
            if isinstance(key, str) and key.strip():
                out[key.strip().lower()] = t["team_abbr"]
    return out


def parse(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    m = re.search(r"WEEK\s*(\d+)", text[:6000], re.I)
    week = int(m.group(1)) if m else None
    season_match = re.search(r"(20\d{2})\s*NFL\s*Injury Report", text[:6000], re.I)

    nicks = nicknames()
    marker = {k: v for k, v in nicks.items() if len(k) > 3}

    def club_from_ancestors(table) -> str | None:
        node = table
        for _ in range(6):
            node = node.parent
            if node is None or node.name is None:
                break
            found = None
            for img in node.find_all("img", src=True):
                m = re.search(r"clubs/logos/([A-Z]{2,3})", img["src"])
                if m:
                    found = m.group(1)
            if found:
                return found
        return None

    def club_from_sibling_text(table) -> str | None:
        prev = table
        for _ in range(40):
            prev = prev.find_previous(True)
            if prev is None:
                return None
            own = prev.get_text(" ", strip=True)
            if own and len(own) < 40 and own.lower() in marker:
                return marker[own.lower()]
        return None

    current = None
    rows = []
    tables = 0
    for el in soup.find_all(True):
        if el.name in ("span", "a", "h2", "h3", "h4", "div", "p", "button"):
            own = el.get_text(" ", strip=True)
            if own and len(own) < 40 and own.lower() in marker:
                current = marker[own.lower()]
        if el.name != "table":
            continue
        trs = el.find_all("tr")
        if not trs:
            continue
        header = [c.get_text(" ", strip=True).lower() for c in trs[0].find_all(["th", "td"])]
        if not any("player" in h for h in header) or not any("status" in h for h in header):
            continue
        tables += 1
        table_club = club_from_ancestors(el) or club_from_sibling_text(el) or current

        def col(name):
            for i, h in enumerate(header):
                if h.replace(" ", "") == name:
                    return i
            return None

        i_player, i_pos = col("player"), col("position")
        i_injury, i_practice, i_game = col("injuries"), col("practicestatus"), col("gamestatus")
        for tr in trs[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if i_player is None or len(cells) <= i_player:
                continue
            player = cells[i_player]
            if not player:
                continue
            link = None
            a = tr.find("a", href=True)
            if a and "/players/" in a["href"]:
                link = "https://www.nfl.com" + a["href"].split("?")[0]
            def pick(i):
                return cells[i] if i is not None and i < len(cells) and cells[i] else None
            rows.append({
                "team": table_club,
                "player": player,
                "position": pick(i_pos),
                "injury": pick(i_injury),
                "practice": pick(i_practice),
                "game": pick(i_game),
                "player_url": link,
            })
    return {
        "week": week,
        "season": int(season_match.group(1)) if season_match else None,
        "tables_parsed": tables,
        "rows": rows,
    }


def resolve_missing_clubs(rows: list[dict]) -> tuple[int, int]:
    """Attribute rows whose club could not be read from the page, using the weekly roster.

    Only names that appear on exactly one 2026 roster are used, so this cannot silently move a
    player to the wrong club. Returns (resolved, still_unknown).
    """
    try:
        roster = pd.read_parquet(os.path.join(RAW, "roster_weekly_2026.parquet"))
    except Exception:  # noqa: BLE001
        return 0, sum(1 for r in rows if not r.get("team"))
    roster = roster[roster["week"] == roster["week"].max()]
    counts = roster.groupby("full_name")["team"].nunique()
    unique = set(counts[counts == 1].index)
    owner = roster.drop_duplicates("full_name").set_index("full_name")["team"].to_dict()
    resolved = 0
    for r in rows:
        if r.get("team"):
            continue
        name = (r.get("player") or "").strip()
        if name in unique and name in owner:
            r["team"] = owner[name]
            r["team_source"] = "weekly roster (unique name)"
            resolved += 1
    return resolved, sum(1 for r in rows if not r.get("team"))


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    html = fetch()
    digest = hashlib.sha256(html.encode()).hexdigest()
    parsed = parse(html)
    rows = parsed["rows"]
    resolved, unresolved = resolve_missing_clubs(rows)
    teams = {r["team"] for r in rows if r["team"]}
    ok = len(rows) >= 150 and len(teams) >= 24
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_url": URL,
        "html_sha256": digest,
        "week": parsed["week"],
        "season": parsed["season"],
        "tables_parsed": parsed["tables_parsed"],
        "counts": {"rows": len(rows), "teams": len(teams),
                   "clubs_resolved_from_roster": resolved, "rows_without_club": unresolved},
        "status": "ok" if ok else "parse-incomplete",
        "warning": (None if ok else
                    "Parsed fewer rows or clubs than expected; build will fall back to the "
                    "mirrored feed and flag the mismatch."),
        "rows": rows,
    }
    with open(os.path.join(OUT, "official_injuries.json"), "w") as f:
        json.dump(payload, f, indent=1)
    print(f"official injuries: status={payload['status']} week={payload['week']} "
          f"rows={len(rows)} teams={len(teams)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"official injury scrape failed: {exc}")
        with open(os.path.join(OUT, "official_injuries.json"), "w") as f:
            json.dump({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "source_url": URL, "status": "failed", "error": str(exc),
                       "rows": []}, f, indent=1)
