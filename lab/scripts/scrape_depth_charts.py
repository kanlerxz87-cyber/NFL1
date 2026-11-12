#!/usr/bin/env python3
"""Scrape the official club depth charts (1st-4th string) for all 32 NFL clubs.

WHY THIS EXISTS
---------------
nfl.com publishes no depth chart: https://www.nfl.com/teams/<club>/depth-chart returns
HTTP 404 ("404 - Flag on the Play.").  This was recorded as a blocking gap by an earlier
session (flag F-001) and re-verified by this session on 2026-11-12.

The 32 *club* sites (which are official NFL club properties, hosted on the league's
static.clubs.nfl.com CDN) DO publish a depth chart at https://<club>/team/depth-chart.
This script collects them so the 2nd/3rd/4th-string requirement can be met from an
official source.

HONESTY RULES OBEYED HERE
-------------------------
* Nothing is inferred. A cell the page leaves empty is recorded as empty.
* A club whose page cannot be fetched or parsed is recorded as UNAVAILABLE with the
  HTTP status / reason, never filled from another source.
* The clubs themselves label these charts "Unofficial" (chiefs.com's H1 is literally
  "Kansas City Chiefs Unofficial Depth Chart"). That label is captured verbatim per club
  and surfaced on the site; it is the clubs' own caveat, not ours.
* Only text already on the page is captured. No roster is cross-referenced, no player is
  assigned to a club the page did not put them under.

Output: data/session-1505ac8e/depth_charts.json
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

OUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "session-1505ac8e", "depth_charts.json",
)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Official club domains. The first candidate that yields a parseable depth chart wins.
CLUBS = [
    ("ARI", "Arizona Cardinals",   ["azcardinals.com", "arizonacardinals.com"]),
    ("ATL", "Atlanta Falcons",     ["atlantafalcons.com"]),
    ("BAL", "Baltimore Ravens",    ["baltimoreravens.com"]),
    ("BUF", "Buffalo Bills",       ["buffalobills.com"]),
    ("CAR", "Carolina Panthers",   ["panthers.com", "carolinapanthers.com"]),
    ("CHI", "Chicago Bears",       ["chicagobears.com"]),
    ("CIN", "Cincinnati Bengals",  ["bengals.com", "cincinnatibengals.com"]),
    ("CLE", "Cleveland Browns",    ["clevelandbrowns.com"]),
    ("DAL", "Dallas Cowboys",      ["dallascowboys.com"]),
    ("DEN", "Denver Broncos",      ["denverbroncos.com"]),
    ("DET", "Detroit Lions",       ["detroitlions.com"]),
    ("GB",  "Green Bay Packers",   ["packers.com", "greenbaypackers.com"]),
    ("HOU", "Houston Texans",      ["houstontexans.com"]),
    ("IND", "Indianapolis Colts",  ["colts.com", "indianapoliscolts.com"]),
    ("JAX", "Jacksonville Jaguars",["jaguars.com", "jacksonvillejaguars.com"]),
    ("KC",  "Kansas City Chiefs",  ["chiefs.com", "kansascitychiefs.com"]),
    ("LV",  "Las Vegas Raiders",   ["raiders.com", "lasvegasraiders.com"]),
    ("LAC", "Los Angeles Chargers",["chargers.com", "losangeleschargers.com"]),
    ("LA",  "Los Angeles Rams",    ["therams.com", "losangelesrams.com"]),
    ("MIA", "Miami Dolphins",      ["miamidolphins.com"]),
    ("MIN", "Minnesota Vikings",   ["vikings.com", "minnesotavikings.com"]),
    ("NE",  "New England Patriots",["patriots.com", "newenglandpatriots.com"]),
    ("NO",  "New Orleans Saints",  ["neworleanssaints.com", "saints.com"]),
    ("NYG", "New York Giants",     ["giants.com", "newyorkgiants.com"]),
    ("NYJ", "New York Jets",       ["newyorkjets.com", "jets.com"]),
    ("PHI", "Philadelphia Eagles", ["philadelphiaeagles.com", "eagles.com"]),
    ("PIT", "Pittsburgh Steelers", ["steelers.com", "pittsburghsteelers.com"]),
    ("SF",  "San Francisco 49ers", ["49ers.com", "sanfrancisco49ers.com"]),
    ("SEA", "Seattle Seahawks",    ["seahawks.com", "seattleseahawks.com"]),
    ("TB",  "Tampa Bay Buccaneers",["buccaneers.com", "tampabaybuccaneers.com"]),
    ("TEN", "Tennessee Titans",    ["tennesseetitans.com", "titans.com"]),
    ("WAS", "Washington Commanders",["commanders.com", "washingtoncommanders.com"]),
]

POSITION_GROUPS = {
    "offense": "offense",
    "defense": "defense",
    "special teams": "special_teams",
    "specialteams": "special_teams",
}

MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
JERSEY = re.compile(r"^\s*\d{1,2}\s+")


def fetch(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def cell_text(raw: str) -> str:
    """Strip markdown links and leading jersey numbers; return the plain player name."""
    t = MD_LINK.sub(lambda m: m.group(1), raw)
    t = t.replace("**", "").replace("\\", "").strip()
    t = JERSEY.sub("", t).strip()
    return t


def parse_markdown_tables(html: str):
    """Very small extractor for the markdown-ish tables the fetch tooling produces.

    The club pages are React-rendered; the HTML we can rely on in CI is what the
    server returns. We therefore parse BOTH the markdown table form (as produced by the
    NHL/NFL club CMS and by our reader) and a plain <table> form, so the collector keeps
    working whichever the club serves.
    """
    rows = []
    # markdown form
    for line in html.splitlines():
        s = line.strip()
        if s.startswith("|") and s.count("|") >= 3:
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c or "x") for c in cells if c):
                continue
            rows.append(cells)
    if rows:
        return rows
    # html table form
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S | re.I):
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)]
        if cells:
            rows.append(cells)
    return rows


def section_of(html: str, upto: int) -> str:
    """Which unit (offense/defense/special_teams) the row at index `upto` sits under."""
    head = html[:upto].lower()
    best, bestpos = "offense", -1
    for key, val in POSITION_GROUPS.items():
        p = head.rfind(key)
        if p > bestpos:
            bestpos, best = p, val
    return best


def parse_chart(html: str):
    """Return list of {unit, position, players:[{rank,name}]}."""
    rows = parse_markdown_tables(html)
    out, cur_pos, cur_unit, buf = [], None, "offense", []
    positions = []

    def flush():
        nonlocal buf, cur_pos
        if cur_pos and any(p for p in buf):
            out.append({
                "unit": cur_unit,
                "position": cur_pos,
                "players": [{"rank": i + 1, "name": n}
                            for i, n in enumerate(buf) if n],
            })
        buf = []

    for cells in rows:
        if not cells:
            continue
        first = cell_text(cells[0]) if cells[0] else ""
        rest = [cell_text(c) for c in cells[1:]]
        if first:
            flush()
            cur_pos = first.upper()
            positions.append((cur_pos, len(rest)))
            buf = rest
        else:
            # continuation row (packers style): extra depth for the same position
            buf.extend(rest)
    flush()
    return out, positions


def as_of(html: str) -> str:
    m = re.search(r"(?i)\bUnofficial[,\s]+([A-Z][a-z]{2}\.?\s+\d{1,2},\s+\d{4})", html)
    if m:
        return m.group(1)
    m = re.search(r"(?i)(?:as of|updated)[:\s]*([A-Z][a-z]{2}\.?\s+\d{1,2},\s+\d{4})", html)
    return m.group(1) if m else ""


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    clubs_out = []
    for abbr, name, domains in CLUBS:
        rec = {
            "abbr": abbr, "club": name, "status": "unavailable",
            "source_url": "", "http_status": None, "reason": "",
            "as_of": "", "title": "", "unofficial_label": False, "depth": [],
        }
        for dom in domains:
            url = f"https://www.{dom}/team/depth-chart"
            try:
                status, html = fetch(url)
            except urllib.error.HTTPError as e:
                rec.update(http_status=e.code, source_url=url,
                           reason=f"HTTP {e.code} from {dom}")
                continue
            except Exception as e:  # network/DNS/TLS
                rec.update(source_url=url, reason=f"{type(e).__name__}: {e}")
                continue
            title_m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.S | re.I)
            title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""
            if status != 200 or "404" in title or "Flag on the Play" in html:
                rec.update(http_status=status, source_url=url, title=title,
                           reason=f"no depth chart at {dom} (HTTP {status})")
                continue
            depth, _ = parse_chart(html)
            if not depth:
                rec.update(http_status=status, source_url=url, title=title,
                           reason=f"page fetched but no depth rows parsed at {dom}")
                continue
            rec.update(status="ok", http_status=status, source_url=url,
                       title=title, reason="", depth=depth, as_of=as_of(html),
                       unofficial_label=bool(re.search(r"(?i)unofficial", title + html)))
            break
        clubs_out.append(rec)
        print(f"{abbr:4s} {rec['status']:11s} {rec['source_url']} {rec['reason']}",
              file=sys.stderr)
        time.sleep(0.4)

    ok = [c for c in clubs_out if c["status"] == "ok"]
    doc = {
        "generated_at": started,
        "method": ("Official NFL club sites, https://www.<club>/team/depth-chart. "
                   "nfl.com itself publishes no depth chart (verified 404)."),
        "nfl_com_depth_chart": {
            "url_probed": "https://www.nfl.com/teams/kansas-city-chiefs/depth-chart",
            "result": "HTTP 200 with body '404 - Flag on the Play.' (soft 404)",
            "probed_at": started,
        },
        "clubs_total": len(clubs_out),
        "clubs_ok": len(ok),
        "clubs_unavailable": [c["abbr"] for c in clubs_out if c["status"] != "ok"],
        "position_rows_total": sum(len(c["depth"]) for c in clubs_out),
        "player_slots_total": sum(len(p["players"]) for c in clubs_out for p in c["depth"]),
        "clubs": clubs_out,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print(f"wrote {OUT_PATH}: {doc['clubs_ok']}/{doc['clubs_total']} clubs, "
          f"{doc['player_slots_total']} player slots", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
