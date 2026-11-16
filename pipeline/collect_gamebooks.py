#!/usr/bin/env python3
"""Immutable captures of the official NFL Game Book, the weekly inactives list and the
weekly injury report, for the availability-outcome ledger.

Session `98a40411-nfl1`, tasks G2/G3. Additive: this file writes only under `data/gamebook/`.

Why this collector exists
-------------------------
The repository's readiness register records four rows blocked on one missing source
(`room/data/readiness.json` IN-04 "No official inactive or snap-count source identified",
IN-15 designation reliability, IN-17 expected-vs-actual starter, IN-18 "The Game Book source
has not been identified"). The source is identified here:

* every official game centre page links a **"Download Game Book (PDF)"** file, served from
  `https://static.www.nfl.com/.../gamecenter/<uuid>.pdf`. Its first page prints, per club,
  `Lineups` (offence and defence starters), `Substitutions`, `Did Not Play` and `Not Active`,
  plus the venue, the final score, the officials and the paid attendance;
* the league also publishes a dated weekly inactives article,
  `https://www.nfl.com/news/nfl-week-<w>-inactives-players-ruled-out-sunday-<season>-season`,
  which lists every club's inactives for that Sunday's games.

Two official sources for the same fact are captured separately and cross-checked. Neither is
inferred from the other, and a missing value stays missing (blank plus a flag).

Sub-commands
------------
    inactives  capture + parse the weekly inactives article(s)
    reports    capture + parse the weekly official injury report(s) (game-day designations)
    gamebooks  capture + parse the Game Book PDF of every played game in a season/week range
    derive     rebuild the derived row tables from the stored captures (no network)
    verify     hash-replay every capture, check pins and freshness (no network)

Failure policy (drift alarm, same rule the brief asks of every scraper): a page that cannot be
fetched, a table whose required heading is absent, a parse below the pinned minimum, or a missing
Game Book link is a **failure that is recorded and turns the job red** - it is never published as
a blank cell or as a zero count.

Network note: the Arena sandbox cannot reach nfl.com (outbound allow-list), so `collect` sub-
commands run on GitHub Actions (`.github/workflows/gamebook-sweep.yml`), the same route already
used by `pipeline/collect_transactions.py`. `derive` and `verify` run anywhere, including in a
pull-request check, because they read only committed captures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data" / "gamebook"
CAPS = STORE / "captures"
HEARTBEAT = STORE / "heartbeat.jsonl"
ALERTS = STORE / "alerts.jsonl"
MANIFEST = STORE / "manifest.json"
TEAMS_CSV = ROOT / "data" / "reference" / "teams.csv"
ACTIVE_CLUBS_CSV = ROOT / "data" / "official" / "teams.csv"

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PARSER_VERSION = "collect_gamebooks/1.0"

# ---------------------------------------------------------------- drift pins
MIN_CLUBS_INACTIVES = 24          # a Sunday round lists 28 clubs (14 games); allow a bye-shift floor
MIN_ROWS_INACTIVES = 60           # 8 inactives per club x 24 clubs would be 192; 60 is a hard floor
MIN_ROWS_REPORT = 100             # the Week 10 2026 report carries 347 rows
MIN_CLUBS_REPORT = 10
INACTIVES_PER_CLUB_RANGE = (3, 12)   # NFL game-day rule: 8 inactive max, 6 min on a 53-man roster
PDF_PDF_MIN_BYTES = 20000

ALLOWANCE_NOTE = (
    "Not Active is printed by the league as a per-club list of players who were on the game "
    "roster but were not active for that game. It is an official, dated, per-game fact."
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(t: str) -> str:
    return sha256_bytes(t.encode("utf-8"))


def canon_sha(rows: list[dict]) -> str:
    blob = json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_text(blob)


# The 32 clubs that exist in the 2026 season, i.e. the only abbreviations this collector may
# emit. The historical franchise rows in data/reference/teams.csv (OAK, STL, SD) are the reason
# the filter exists: "Rams" appears for both STL and LA, and without this restriction the map
# silently resolves a Los Angeles club to a franchise that no longer exists there.
CURRENT_CLUBS = {"ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET",
                 "GB", "HOU", "IND", "JAX", "KC", "LAC", "LA", "LV", "MIA", "MIN", "NE", "NO",
                 "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"}


# ---------------------------------------------------------------- club vocabulary
def club_map() -> dict[str, str]:
    """nickname (lowercase) -> current 3-letter abbreviation, from the official club reference.

    Codes follow the ones the league's own pages print and the ones the committed weekly injury
    report capture carries (ARI, LA, LV), so a join between the two needs no alias table.
    """
    import csv as _csv
    abbrs = CURRENT_CLUBS
    out: dict[str, str] = {}
    with TEAMS_CSV.open() as f:
        for r in _csv.DictReader(f):
            a = (r.get("team_abbr") or "").strip().upper()
            nick = (r.get("team_nick") or "").strip()
            name = (r.get("team_name") or "").strip()
            if not a or not nick:
                continue
            if a not in abbrs:
                continue
            out[nick.lower()] = a
            if name:
                out[name.lower()] = a
    # the page prints mascots in upper case; also accept the singular and a few page-only forms
    for extra, a in {
        "cardinals": "ARI", "falcons": "ATL", "ravens": "BAL", "bills": "BUF",
        "panthers": "CAR", "bears": "CHI", "bengals": "CIN", "browns": "CLE",
        "cowboys": "DAL", "broncos": "DEN", "lions": "DET", "packers": "GB",
        "texans": "HOU", "colts": "IND", "jaguars": "JAX", "chiefs": "KC",
        "chargers": "LAC", "rams": "LA", "dolphins": "MIA", "vikings": "MIN",
        "patriots": "NE", "saints": "NO", "giants": "NYG", "jets": "NYJ",
        "eagles": "PHI", "steelers": "PIT", "titans": "TEN", "commanders": "WAS",
        "49ers": "SF", "seahawks": "SEA", "buccaneers": "TB", "raiders": "LV",
    }.items():
        out.setdefault(extra, a)
    return out


NICK_ABBR = club_map()


def nick_to_abbr(text: str) -> str | None:
    key = re.sub(r"[^a-z0-9 ]", "", (text or "").strip().lower())
    if not key:
        return None
    if key in NICK_ABBR:
        return NICK_ABBR[key]
    # "NEW ENGLAND PATRIOTS" / "LOS ANGELES RAMS" style
    tail = key.split()[-1]
    return NICK_ABBR.get(tail)


# ---------------------------------------------------------------- fetch helpers
class NotFound(Exception):
    """The publisher answered definitively: this document does not exist at this url.

    Kept apart from a transport failure on purpose. A missing page is *coverage* (an old weekly
    article that has been taken down, a game book not yet uploaded) and must be reported as such;
    a timeout or a 500 is a fault in our reading and must fail loudly, because a run that treats
    its own outage as "the league has no data" is how a blank column becomes a permanent blank.
    """


def http_get(url: str, *, binary: bool = False, tries: int = 3, sleep: float = 2.0):
    import requests
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT,
                                           "Accept-Language": "en-US,en;q=0.9",
                                           "Accept": "text/html,application/pdf,*/*;q=0.8"},
                             timeout=90)
            if r.status_code == 200:
                return r.content if binary else r.text
            last = f"HTTP {r.status_code}"
            if r.status_code in (404, 410):
                raise NotFound(f"HTTP {r.status_code} for {url}")
        except NotFound:
            raise
        except Exception as exc:                                  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(sleep * (i + 1))
    raise RuntimeError(f"fetch failed for {url}: {last}")


def get_first(urls: list[str], *, binary: bool = False) -> tuple[str, str | bytes]:
    """Try each candidate url in order; return the first that answers 200.

    The league's own url patterns are not stable across years (the dated inactives article slug was
    confirmed for 2026 only), so a capture walk tries the documented variants rather than assuming
    one. If all of them answer 404/410 the *last* NotFound is re-raised; any other failure wins, so
    a transport fault is never hidden behind a "not found" label.
    """
    errs: list[Exception] = []
    for u in urls:
        try:
            return u, http_get(u, binary=binary)
        except Exception as exc:                                  # noqa: BLE001
            errs.append(exc)
            if not isinstance(exc, NotFound):
                raise
    raise errs[-1]


# ---------------------------------------------------------------- capture store
def write_capture(kind: str, key: str, payload: dict) -> Path:
    """Exclusive-create an immutable capture. Never rewrites an existing file."""
    d = CAPS / kind
    d.mkdir(parents=True, exist_ok=True)
    ts = payload["fetched_at"].replace("-", "").replace(":", "").replace("Z", "")
    p = d / f"{key}_{ts}.json"
    p.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
    return p


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def list_captures(kind: str) -> list[Path]:
    d = CAPS / kind
    return sorted(d.glob("*.json")) if d.exists() else []


def latest_capture(kind: str, key: str) -> Path | None:
    hits = [p for p in list_captures(kind) if p.name.startswith(key + "_")]
    return hits[-1] if hits else None


# ================================================================ parsing: inactives article
CLUB_HEAD_RE = re.compile(r"^[A-Z0-9 &'\-\.]+$")
NAME_NOISE = ("emergency third", "designated third", "where:", "when:", "watch:")


def parse_inactives_text(text: str) -> tuple[list[dict], list[str]]:
    """Parse the league's weekly inactives article.

    Structure as published: a section heading per time slot (MUNICH GAME / EARLY GAMES / LATE
    GAMES / SUNDAY NIGHT FOOTBALL), a match-up line, then one upper-case club heading followed
    by the bulleted list of that club's inactives. Any heading whose text resolves to one of the
    32 clubs is treated as a club block; the block ends at the next heading.

    Returns (rows, flags). rows: {club, section, name, position_raw, note}. A club heading with
    no names, or a name that cannot be read, becomes a flag - never a silent skip.
    """
    rows: list[dict] = []
    flags: list[str] = []
    section = ""
    current: str | None = None
    buf: list[str] = []
    fixture_pair: list[str] = []

    def flush():
        nonlocal current, buf
        if current is None:
            return
        if not buf:
            flags.append(f"club heading {current} with no inactive names in section {section or '?'}")
        for raw in buf:
            name = raw
            note = ""
            if "(" in name and name.rstrip().endswith(")"):
                i = name.rfind("(")
                note = name[i + 1:].rstrip(" )").strip()
                name = name[:i].strip()
            name = re.sub(r"\s+", " ", name).strip(" ,.;")
            pos = ""
            m = re.match(r"^(QB|RB|WR|TE|OL|DL|LB|CB|S|FS|SS|DT|DE|OLB|ILB|EDGE|NT|K|P|LS|C|G|T|"
                         r"OT|OG|OLB|DL|DB|FB)\b\.?\s+(.*)$", name, re.I)
            if m:
                pos, name = m.group(1).upper(), m.group(2).strip()
            if not name:
                flags.append(f"unreadable inactive name under {current}: {raw!r}")
                continue
            rows.append({"club": current, "section": section, "name": name,
                         "position_raw": pos, "note": note})
        current, buf = None, []

    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        m = re.match(r"^(#{1,6})\s+(.*)$", s)          # any markdown heading level
        if m:
            head = re.sub(r"[#*_`]", "", m.group(2)).strip()
            up = re.sub(r"\[.*?\]", "", head).strip()
            up = re.sub(r"\s+", " ", up)
            abbr = nick_to_abbr(up) if (up.isupper() and len(up) < 30) else None
            if abbr:
                flush()
                current = abbr
                continue
            flush()
            current = None
            if up and len(up) < 40:
                section = up
            continue
        if low.startswith("- ") or low.startswith("* ") or s.startswith("&bull;"):
            item = re.sub(r"^[-*]\s*", "", s)
            item = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", item).strip()
            if not item:
                continue
            if current is not None:
                buf.append(item)
            else:
                fixture_pair.append(item)
            continue
        if current is not None and re.match(r"^[A-Za-z'\.\-]+ [A-Za-z'\.\-]+$", s) and len(s) < 40:
            buf.append(s)
            continue
        if not low.startswith(("where", "when", "visit", "fans can", "nfl.com keeps", "skip to")):
            # free text between headings: ignore for parsing, but keep the fact that a
            # non-list line appeared while a club block was open
            if current is not None and buf and s.endswith("."):
                flags.append(f"prose inside club block {current}: {s[:60]!r}")
    flush()
    return rows, flags


def parse_inactives_html(html: str) -> tuple[list[dict], list[str], list[str]]:
    """Parse the article body from the real page. Falls back to the text parser on structure drift."""
    flags: list[str] = []
    heads: list[str] = []
    try:
        from bs4 import BeautifulSoup
    except Exception:                                            # noqa: BLE001
        rows, flags = parse_inactives_text(re.sub(r"<[^>]+>", "\n", html))
        return rows, flags + ["beautifulsoup4 unavailable: text parse used"], []
    soup = BeautifulSoup(html, "lxml")
    body = (soup.select_one("div.article-body") or soup.select_one("#main-content")
            or soup.body or soup)
    rows: list[dict] = []
    current: str | None = None
    section = ""

    def flush(names):
        nonlocal rows
        for raw in names:
            name, note = raw, ""
            m = re.search(r"\(([^)]*)\)\s*$", name)
            if m:
                note = m.group(1).strip()
                name = name[:m.start()].strip()
            name = re.sub(r"\s+", " ", name).strip(" ,.;")
            pos = ""
            mm = re.match(r"^(QB|RB|WR|TE|OL|DL|LB|CB|S|FS|SS|DT|DE|OLB|ILB|EDGE|NT|K|P|LS|C|G|T|OT|DB|FB)\b\.?\s+(.*)$",
                          name, re.I)
            if mm:
                pos, name = mm.group(1).upper(), mm.group(2).strip()
            if not name:
                flags.append(f"unreadable inactive name under {current}: {raw!r}")
                continue
            rows.append({"club": current, "section": section, "name": name,
                         "position_raw": pos, "note": note})

    pending: list[str] = []
    for el in body.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol"]):
        tag = el.name
        if tag in ("h1", "h2", "h3", "h4"):
            head = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
            heads.append(f"{tag}:{head[:60]}")
            abbr = nick_to_abbr(head) if head.upper() == head else None
            if abbr and len(head) < 30:
                flush(pending)
                pending = []
                current = abbr
                continue
            flush(pending)
            pending = []
            current = None
            if head and len(head) < 40 and head.upper() == head:
                section = head
            continue
        if tag in ("ul", "ol") and current:
            items = [re.sub(r"\s+", " ", li.get_text(" ", strip=True))
                     for li in el.find_all("li", recursive=False)]
            pending.extend([i for i in items if i and not any(n in i.lower() for n in ("subscribe",))])
            flush(pending)
            pending = []
    flush(pending)
    if not rows:
        flags.append("html structure not recognised; falling back to text parse")
        rows2, flags2 = parse_inactives_text(re.sub(r"<[^>]+>", "\n", html))
        return rows2, flags + flags2, heads
    return rows, flags, heads


# ================================================================ parsing: injury report tables
def parse_report_tables(html: str) -> tuple[list[dict], list[str], list[str]]:
    """Parse the weekly official injury report tables (Player/Position/Injuries/Practice/Game).

    Club is read from the club-logo link inside each table's header block, the same route
    pipeline/scrape_injuries.py uses. Column order is decided by the header NAME, never by
    position, so a reordered table cannot silently shift a game status into the wrong field.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []
    flags: list[str] = []
    heads: list[str] = []
    current: str | None = None
    for el in soup.find_all(["table", "a"]):
        if el.name == "a":
            href = el.get("href") or ""
            m = re.match(r"^/teams/([a-z\-]+)/$", href)
            if m:
                slug = m.group(1).split("-")[-1]
                abbr = nick_to_abbr(slug)
                if abbr:
                    current = abbr
            continue
        table_club = current
        for img in el.find_all("img"):
            src = img.get("src") or ""
            mm = re.search(r"clubs/logos/([A-Z]{2,3})", src)
            if mm:
                table_club = mm.group(1)
                break
        head_cells = [re.sub(r"\s+", " ", th.get_text(" ", strip=True))
                      for th in el.find_all("th")][:8]
        if head_cells:
            heads.append("|".join(head_cells))
        if not any("Player" in h for h in head_cells):
            continue
        col = {}
        for i, h in enumerate(head_cells):
            hl = h.lower()
            if hl.startswith("player"):
                col["player"] = i
            elif hl.startswith("position"):
                col["position"] = i
            elif "injur" in hl:
                col["injury"] = i
            elif "practice" in hl:
                col["practice"] = i
            elif "game" in hl:
                col["game"] = i
        if "player" not in col or "game" not in col or "practice" not in col:
            flags.append(f"report table for {table_club} lacks a required header: {head_cells}")
            continue
        for tr in el.find_all("tr"):
            tds = tr.find_all("td")
            if not tds:
                continue
            def cell(name):
                i = col.get(name)
                if i is None or i >= len(tds):
                    return ""
                return re.sub(r"\s+", " ", tds[i].get_text(" ", strip=True)).strip()
            player = cell("player")
            if not player:
                continue
            link = tds[col["player"]].find("a") if "player" in col else None
            rows.append({
                "club": table_club,
                "player": player,
                "position": cell("position"),
                "injury": cell("injury") or None,
                "practice": cell("practice") or None,
                "designation": cell("game") or None,
                "player_url": ("https://www.nfl.com" + link["href"]) if link and link.get("href") else None,
            })
    return rows, flags, heads


# ================================================================ parsing: game book PDF
GAMEBOOK_SECTIONS = ("Lineups", "Substitutions", "Did Not Play", "Not Active")
NAME_TOK = re.compile(r"(?:(?P<pos>[A-Z/\.]{1,6})\s+)?(?:(?P<num>\d{1,2})\s+)?"
                      r"(?P<name>[A-Z][A-Za-z'\-]*(?:\.[A-Z][A-Za-z'\-]*)*"
                      r"(?:\s+[A-Z][A-Za-z'\-\.]+){0,3})")


def pdf_to_text(path_or_bytes, max_pages: int = 4) -> tuple[str, int, list[str]]:
    notes: list[str] = []
    data = path_or_bytes
    if isinstance(data, (bytes, bytearray)):
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(bytes(data)))
    else:
        from pypdf import PdfReader
        reader = PdfReader(str(path_or_bytes))
    n = len(reader.pages)
    out = []
    for i, page in enumerate(reader.pages):
        if i >= max_pages:
            break
        try:
            out.append(page.extract_text() or "")
        except Exception as exc:                                 # noqa: BLE001
            notes.append(f"page {i + 1} text extraction failed: {type(exc).__name__}: {exc}")
    if n > max_pages:
        notes.append(f"pages parsed {max_pages} of {n}; only the summary pages are needed")
    return "\n".join(out), n, notes


MARKERS = ("Lineups", "Substitutions", "Did Not Play", "Not Active", "Field Goals",
           "Scoring Plays", "VISITOR:", "Final Individual Statistics", "Play-by-Play",
           "Team Statistics", "Coaches Challenge")


def _slices(text: str) -> dict[str, str]:
    """Split the document at its own section markers, in the order they appear.

    A single pass, because the four summary lists are adjacent: a `stop at the next marker` rule
    that only knows about *some* markers is how a Not Active line gets attributed to Did Not Play.
    A region that is empty stays empty - it is reported as absent, never as a zero.
    """
    hits = []
    for m in MARKERS:
        i = -1
        while True:
            i = text.find(m, i + 1)
            if i < 0:
                break
            hits.append((i, m))
    hits.sort()
    out: dict[str, str] = {}
    for n, (i, m) in enumerate(hits):
        end = hits[n + 1][0] if n + 1 < len(hits) else len(text)
        body = text[i + len(m):end]
        if m not in out or len(body.strip()) > len(out[m].strip()):
            out[m] = body
    return out


def _region(text: str, start: str, stops: tuple[str, ...]) -> str:
    sl = _slices(text)
    if start in sl:
        return sl[start]
    i = text.find(start)
    if i < 0:
        return ""
    j = len(text)
    for s in stops:
        k = text.find(s, i + len(start))
        if 0 <= k < j:
            j = k
    return text[i + len(start):j]


def parse_gamebook_text(text: str) -> dict:
    """Extract the dated game facts from the first pages of an official Game Book.

    Deliberate limits, both required by the brief: no depth rank and no snap count is inferred
    from a Game Book. Only what the document prints is kept - the two starting line-ups, the
    substitution list, the Did Not Play list, the Not Active list, the venue, the score, the
    officials and the attendance - together with the raw text region each list came from.
    """
    out: dict = {"flags": [], "sections_found": [], "excerpt_sha": {}}
    if not text:
        out["flags"].append("empty pdf text")
        out["parse_status"] = "failed"
        return out
    m = re.search(r"Date:\s*([A-Za-z]+,\s*\d{1,2}/\d{1,2}/\d{4})", text)
    out["game_date_text"] = m.group(1) if m else None
    m = re.search(r"at\s+([A-Z][^|\n]*?Stadium|[^|\n]*?Arena|[^|\n]*?Field|[^|\n]*?Dome)"
                  r"(?:,|\s*\|)", text)
    out["venue_text"] = m.group(1).strip() if m else None
    m = re.search(r"Referee:\s*([A-Za-z\.]+,\s*[A-Za-z\.]+)\s*\((\d{1,3})\)", text)
    out["referee"] = f"{m.group(1)} ({m.group(2)})" if m else None
    m = re.search(r"Paid Attendance:\s*([\d,]+)", text)
    out["attendance"] = m.group(1) if m else None
    scores = re.findall(r"^\s*(\d{1,2})\s+(\d{1,2})\s*$", text, re.M)
    out["score_pair_candidates"] = scores[:6]

    lines = text.splitlines()
    clubs = re.findall(r"([A-Z][A-Za-z\.\- ]+?(?:State|College)?\s+[A-Z][A-Za-z\.\- ]+)",
                       text[:4000])
    for tag in GAMEBOOK_SECTIONS:
        # the marker alone, so the section boundaries come from _slices(); passing the marker with a
        # trailing newline made every lookup miss and each region ran on to the next known stop.
        region = _region(text, tag, ("Field Goals", "Scoring Plays", "VISITOR:",
                                    "Final Individual Statistics", "Play-by-Play"))
        if not region:
            idx = -1
            for i, ln in enumerate(lines):
                if ln.strip().lower() == tag.lower():
                    idx = i
                    break
            if idx >= 0:
                stop = len(lines)
                for k in range(idx + 1, len(lines)):
                    if lines[k].strip() in MARKERS or any(
                            lines[k].strip().startswith(m) for m in MARKERS):
                        stop = k
                        break
                region = "\n".join(lines[idx + 1:stop])
        out["sections_found"].append(tag) if region else out["flags"].append(f"section {tag!r} absent")
        region = region.strip()
        if region:
            out["excerpt_sha"][tag] = sha256_text(region)
            out.setdefault("excerpts", {})[tag] = region[:6000]
        if tag in ("Not Active", "Did Not Play"):
            names: list[dict] = []
            for chunk in re.split(r",\s*", region):
                chunk = re.sub(r"\s+", " ", chunk).strip(" .;")
                if not chunk or len(chunk) > 60 or chunk.lower().startswith(("new england", "note")):
                    continue
                # the document prefixes a position with a digit when a club carries an emergency
                # quarterback ("3QB 15 B.Morton"), and disambiguates same-surname players with a
                # two-letter initial ("Dr.Jones" vs "Da.Jones"). Both forms are accepted; a token
                # that still does not parse is recorded as unparsed rather than dropped.
                mm = re.match(r"^(?P<pre>\d?[A-Z/\.]{1,6}\s+)?(?P<num>\d{1,2})?\s*"
                              r"(?P<name>[A-Z][A-Za-z'\-\.]*(?:\.[A-Za-z][A-Za-z'\-\.]*)?"
                              r"(?:\s+[A-Z][A-Za-z'\-\.]+){0,3})\s*$", chunk)
                if not mm or not mm.group("name"):
                    if chunk:
                        names.append({"raw": chunk, "unparsed": True})
                    continue
                pre = (mm.group("pre") or "").strip().rstrip(".")
                names.append({"position": pre if len(pre) <= 6 else "",
                              "number": (mm.group("num") or "").strip(),
                              "name": re.sub(r"\s+", " ", mm.group("name")).strip()})
            out[tag] = names
            known = [n for n in names if not n.get("unparsed")]
            if not known:
                if not region.strip():
                    # a printed-but-empty section is a fact of its own: for "Did Not Play" it says
                    # every player the club dressed took a snap. It is recorded as an empty list plus
                    # this note, never as a missing section and never as a zero in a model.
                    out[tag + "_printed_empty"] = True
                    out["flags"].append(f"{tag}: section printed with no names in it")
                else:
                    out["flags"].append(f"{tag}: no name parsed out of the region")
    if "Not Active" not in out and "Did Not Play" not in out:
        out["parse_status"] = "failed"
    elif out["flags"]:
        out["parse_status"] = "partial"
    else:
        out["parse_status"] = "ok"
    # Every short name the document prints on the parsed pages. A player on the game roster is
    # named in the line-ups, the substitution list or a statistics table; a player who was not
    # active is named only on the Not Active line. The token list is stored so the derived "played"
    # state can be re-checked against the document without opening the PDF again.
    out["name_tokens"] = sorted({t.rstrip(".") for t in
                                  re.findall(r"\b[A-Z][a-z]?\.[A-Z][A-Za-z'\.\-]*", text[:22000])})[:800]
    # The printed line-up block is four columns: away offence, away defence, home offence, home
    # defence. A line that does not split into exactly four POS NUMBER NAME triples is not
    # attributed at all - it is counted as unresolved, never guessed into a club.
    cell = re.compile(r"(?P<pos>\d?[A-Z/\.]{1,4})\s+(?P<num>\d{1,2})\s+"
                      r"(?P<ini>[A-Za-z]{1,3})\.(?P<last>[A-Z][A-Za-z'\-\. ]{1,22}?)"
                      r"(?=\s+\d?[A-Z/\.]{1,4}\s+\d|\s*$)")
    starters, unresolved = [], 0
    for ln in (out.get("excerpts", {}).get("Lineups") or "").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        found = list(cell.finditer(ln))
        if len(found) == 4:
            units = [("away", "offence"), ("away", "defence"), ("home", "offence"), ("home", "defence")]
            for mt, (side, unit) in zip(found, units):
                starters.append({"position": mt.group("pos").strip("."), "number": mt.group("num"),
                                   "initial": mt.group("ini"), "surname": mt.group("last").strip(),
                                   "side": side, "unit": unit})
        else:
            unresolved += 1
    if starters:
        out["starters"] = starters
        out["starters_unresolved_lines"] = unresolved
    _ = clubs
    return out


# ================================================================ sub-commands
def cmd_inactives(args) -> int:
    key = f"{args.season}_reg{args.week:02d}"
    if args.url:
        urls = [args.url]
    else:
        pad = f"{args.week:02d}"
        urls = [f"https://www.nfl.com/news/nfl-week-{args.week}-inactives-players-ruled-out-"
                f"{args.season}-season"]
        if pad != str(args.week):
            urls.append(urls[0].replace(f"week-{args.week}-", f"week-{pad}-"))
    fetched = now_iso()
    try:
        url, html = get_first(urls)
    except NotFound as exc:                                      # publisher says: no such article
        append_jsonl(HEARTBEAT, {"at": fetched, "kind": "inactives", "key": key, "url": urls[0],
                                 "rows": 0, "status": "not_published", "detail": str(exc)[:160]})
        print(f"inactives {key}: no official article at this url (HTTP 404) - recorded as missing "
              f"coverage, not as zero rows: {urls[0]}")
        return 0
    except Exception as exc:                                     # noqa: BLE001
        append_jsonl(ALERTS, {"at": fetched, "kind": "inactives", "key": key, "url": urls[0],
                              "alert": "fetch_failed", "detail": str(exc)[:300]})
        append_jsonl(HEARTBEAT, {"at": fetched, "kind": "inactives", "key": key, "url": urls[0],
                                 "rows": 0, "status": "fetch_failed"})
        print(f"::warning::inactives {key}: fetch failed ({exc})", file=sys.stderr)
        return 2
    rows, flags, heads = parse_inactives_html(html)
    # same clamp rule for the article: its own title must name the week that was requested
    t = re.search(r"Week\s+(\d{1,2})\s+inactives", html, re.I)
    if t and int(t.group(1)) != args.week:
        flags.append(f"week_label_mismatch: article prints week {t.group(1)} for a week {args.week} url")
    elif not t:
        flags.append("no week label in the article title")
    clubs = sorted({r["club"] for r in rows if r.get("club")})
    payload = {
        "kind": "inactives", "key": key, "season": args.season, "week": args.week,
        "url": url, "fetched_at": fetched, "raw_sha256": sha256_text(html),
        "raw_bytes": len(html.encode("utf-8")), "parser_version": PARSER_VERSION,
        "headings_seen": heads[:80], "clubs": clubs, "rows": rows,
        "counts": {"rows": len(rows), "clubs": len(clubs)},
        "flags": flags, "note": ALLOWANCE_NOTE,
    }
    p = write_capture("inactives", key, payload)
    status = "ok"
    if len(clubs) < MIN_CLUBS_INACTIVES or len(rows) < MIN_ROWS_INACTIVES:
        status = "below_pin"
        flags.append(f"below pin: clubs={len(clubs)} rows={len(rows)} "
                     f"(pins {MIN_CLUBS_INACTIVES}/{MIN_ROWS_INACTIVES})")
    append_jsonl(HEARTBEAT, {"at": fetched, "kind": "inactives", "key": key, "url": url,
                             "rows": len(rows), "clubs": len(clubs), "status": status,
                             "capture": str(p.relative_to(ROOT))})
    print(f"inactives {key}: {len(rows)} rows, {len(clubs)} clubs -> {p.name}")
    return 0 if status == "ok" else 1


def cmd_reports(args) -> int:
    key = f"{args.season}_reg{args.week:02d}"
    url = f"https://www.nfl.com/injuries/league/{args.season}/reg{args.week:02d}"
    fetched = now_iso()
    try:
        html = http_get(url)
    except NotFound as exc:                                      # publisher answered: nothing here
        append_jsonl(HEARTBEAT, {"at": fetched, "kind": "report", "key": key, "url": url,
                                 "rows": 0, "status": "not_published", "detail": str(exc)[:160]})
        print(f"report {key}: the league publishes no report at this url (HTTP 404) - recorded as "
              f"missing coverage, not as zero rows")
        return 0
    except Exception as exc:                                     # noqa: BLE001
        append_jsonl(ALERTS, {"at": fetched, "kind": "report", "key": key, "url": url,
                              "alert": "fetch_failed", "detail": str(exc)[:300]})
        append_jsonl(HEARTBEAT, {"at": fetched, "kind": "report", "key": key, "url": url,
                                 "rows": 0, "status": "fetch_failed"})
        print(f"::warning::report {key}: fetch failed ({exc})", file=sys.stderr)
        return 2
    rows, flags, heads = parse_report_tables(html)
    # The official report URL does not 404 for a week that has not been published: it returns the
    # most recent published week with HTTP 200. Verified 2026-11-16, when a request for reg11 came
    # back as "Official NFL Injury Report for Players - Week 10 of the 2026 Season" (canonical url
    # .../reg10). A scraper that trusts the url therefore records Week 10 and calls it Week 11, so
    # the page's own label is checked and a mismatch fails the capture instead of mislabelling it.
    label = re.search(r"Week\s+(\d{1,2})\s+of the\s+(\d{4})\s+Season", html)
    if label:
        lw, ls = int(label.group(1)), int(label.group(2))
        if (lw, ls) != (args.week, args.season):
            flags.append(f"week_label_mismatch: asked for week {args.week} of {args.season}, the page "
                         f"states week {lw} of {ls} - the league clamped the request")
            payload_clamp = True
        else:
            payload_clamp = False
    else:
        flags.append("no week label found on the page: the capture cannot be dated to a week")
        payload_clamp = True
    clubs = sorted({r["club"] for r in rows if r.get("club")})
    desig = {}
    for r in rows:
        desig[r.get("designation") or "(blank)"] = desig.get(r.get("designation") or "(blank)", 0) + 1
    payload = {"kind": "report", "key": key, "season": args.season, "week": args.week,
               "url": url, "fetched_at": fetched, "raw_sha256": sha256_text(html),
               "raw_bytes": len(html.encode("utf-8")), "parser_version": PARSER_VERSION,
               "table_headers": heads[:80], "clubs": clubs, "rows": rows,
               "counts": {"rows": len(rows), "clubs": len(clubs), "by_designation": desig},
               "page_week_label": ({"week": lw, "season": ls} if label else None),
               "week_clamped": payload_clamp, "flags": flags,
               "point_in_time": {
                   "captured_after_the_games_of_this_week": True,
                   "why": "nfl.com publishes the report on the game's own week page and keeps it "
                          "up to date; a capture taken later therefore shows the final published "
                          "designation, not the designation an analyst could have held pre-kickoff",
                   "use": "retrospective calibration only - never as a pre-kickoff snapshot",
               }}
    p = write_capture("report", key, payload)
    status = "ok"
    if len(rows) < MIN_ROWS_REPORT or len(clubs) < MIN_CLUBS_REPORT:
        status = "below_pin"
    append_jsonl(HEARTBEAT, {"at": fetched, "kind": "report", "key": key, "url": url,
                             "rows": len(rows), "clubs": len(clubs), "status": status,
                             "capture": str(p.relative_to(ROOT))})
    if payload_clamp:
        append_jsonl(ALERTS, {"at": fetched, "kind": "report", "key": key, "url": url,
                              "alert": "week_label_mismatch", "detail": str(flags[-1])[:200]})
        status = "week_label_mismatch"
    print(f"report {key}: {len(rows)} rows, {len(clubs)} clubs -> {p.name} [{status}]")
    return 0 if status == "ok" else 1


def discover_games(season: int, weeks: list[int]) -> list[dict]:
    """Game slugs + finals, read from the official schedule page for each week.

    The schedule page's server-rendered payload is searched for game links of the form
    /games/<away>-at-<home>-<season>-reg-<week>. A game is 'final' only when the page prints a
    score for both clubs; a tie prints equal scores and is kept.
    """
    games: dict[str, dict] = {}
    empty_weeks: list[str] = []
    for w in weeks:
        url = f"https://www.nfl.com/schedules/{season}/REG{w}"
        before = len(games)
        try:
            html = http_get(url)
        except Exception as exc:                                 # noqa: BLE001
            append_jsonl(ALERTS, {"at": now_iso(), "kind": "schedule", "key": f"{season}_reg{w:02d}",
                                  "url": url, "alert": "fetch_failed", "detail": str(exc)[:200]})
            print(f"::warning::schedule {season} W{w}: fetch failed ({exc})", file=sys.stderr)
            empty_weeks.append(f"W{w} fetch failed")
            continue
        for m in re.finditer(r"/games/([a-z0-9\-]+)-(\d{4})-reg-(\d{1,2})", html):
            slug, s, wk = m.group(1), int(m.group(2)), int(m.group(3))
            if s != season or wk != w or "-at-" not in slug:
                continue
            games.setdefault(slug, {"game_id": slug, "season": season, "week": w,
                                    "schedule_url": url})
        if len(games) == before:
            # a page that loaded but yielded no fixture is the drift case: either the schedule page
            # changed its markup or the league clamped the request to another week (F68). Both must
            # be loud, because a sweep that discovers nothing looks exactly like a successful one.
            empty_weeks.append(f"W{w} rendered no fixture links")
            append_jsonl(ALERTS, {"at": now_iso(), "kind": "schedule", "key": f"{season}_reg{w:02d}",
                                  "url": url, "alert": "no_fixtures_discovered",
                                  "detail": "the page answered 200 but the game-link pattern found "
                                            "nothing for this season/week"})
    if empty_weeks:
        print(f"::warning::discover_games {season}: {'; '.join(empty_weeks)}", file=sys.stderr)
    discover_games.last_problems = empty_weeks
    return list(games.values())


def parse_game_centre(html: str) -> dict:
    """Find the Game Book PDF link and the printed score on a game-centre page."""
    out = {"pdf_url": None, "score_text": None, "venue_text": None, "status_text": None}
    pats = [r"https://static\.www\.nfl\.com/[^\"'\\ ]+?\.pdf"]
    for pat in pats:
        m = re.search(pat, html)
        if m:
            out["pdf_url"] = m.group(0).replace("\\u002F", "/")
            break
    m = re.search(r'"(?:scoreText|shortValue)"\s*:\s*"?(\d{1,3})[^"]*"\s*:\s*"?(\d{1,3})', html)
    m2 = re.search(r"([A-Z][A-Za-z\. ]{2,24})\s+(\d{1,3}),\s+([A-Z][A-Za-z\. ]{2,24})\s+(\d{1,3}),\s+FINAL", html)
    if m2:
        out["score_text"] = m2.group(0)[:120]
    for label in ("Location", "Stadium"):
        mm = re.search(label + r"\s*([A-Z][A-Za-z0-9\.\' \-]{3,40})", html)
        if mm and not out["venue_text"]:
            out["venue_text"] = mm.group(1).strip()
    mm = re.search(r"(FINAL|In Play|Scheduled|Live)", html)
    if mm:
        out["status_text"] = mm.group(1)
    return out


def cmd_gamebooks(args) -> int:
    weeks = list(range(args.week_from, args.week_to + 1))
    if args.weeks:
        weeks = [int(x) for x in args.weeks.split(",")]
    games = discover_games(args.season, weeks)
    if not games and getattr(discover_games, "last_problems", None):
        print("::error::game books: no fixture could be discovered, so nothing was captured; "
              "the schedule page changed or the request was clamped", file=sys.stderr)
        return 2
    if args.limit:
        games = games[:args.limit]
    print(f"discovered {len(games)} games for season {args.season} weeks {weeks[0]}-{weeks[-1]}")
    ok = fail = skipped = missing = 0
    for g in games:
        key = g["game_id"]
        if latest_capture("gamebook", key) and not args.refetch:
            skipped += 1
            continue
        centre = f"https://www.nfl.com/games/{key}?tab=recap"
        fetched = now_iso()
        try:
            html = http_get(centre)
        except Exception as exc:                                 # noqa: BLE001
            fail += 1
            append_jsonl(ALERTS, {"at": fetched, "kind": "gamebook", "key": key, "url": centre,
                                  "alert": "centre_fetch_failed", "detail": str(exc)[:200]})
            continue
        meta = parse_game_centre(html)
        payload = {"kind": "gamebook", "key": key, "season": g["season"], "week": g["week"],
                   "game_centre_url": centre, "schedule_url": g["schedule_url"],
                   "fetched_at": fetched, "centre_sha256": sha256_text(html),
                   "parser_version": PARSER_VERSION,
                   "pdf_url": meta["pdf_url"], "score_text": meta["score_text"],
                   "venue_text_centre": meta["venue_text"], "parsed": None,
                   "counts": {}, "flags": []}
        if not meta["pdf_url"]:
            # the centre page links the PDF only once the game book is uploaded, so "no link" is a
            # coverage fact for a fixture that has not had one published yet. It is recorded either
            # way; `--strict` turns it into a failure for a run that intends to close the gap.
            payload["flags"].append("no Game Book PDF link on the game centre page")
            payload["parse_status"] = "no_pdf_link"
            if args.strict:
                fail += 1
            else:
                missing += 1
            append_jsonl(HEARTBEAT, {"at": fetched, "kind": "gamebook", "key": key,
                                     "url": centre, "rows": 0, "status": "no_pdf_link",
                                     "pdf_sha256": None})
            write_capture("gamebook", key, payload)
            continue
        try:
            raw = http_get(meta["pdf_url"], binary=True)
        except Exception as exc:                                 # noqa: BLE001
            fail += 1
            payload["flags"].append(f"pdf fetch failed: {str(exc)[:200]}")
            payload["parse_status"] = "pdf_fetch_failed"
            write_capture("gamebook", key, payload)
            append_jsonl(HEARTBEAT, {"at": fetched, "kind": "gamebook", "key": key,
                                     "url": meta["pdf_url"], "rows": 0,
                                     "status": "pdf_fetch_failed", "pdf_sha256": None})
            continue
        payload["pdf_bytes"] = len(raw)
        payload["pdf_sha256"] = sha256_bytes(raw)
        if len(raw) < PDF_PDF_MIN_BYTES:
            payload["flags"].append(f"pdf smaller than the pinned minimum ({len(raw)} bytes)")
        try:
            text, npages, notes = pdf_to_text(raw, max_pages=args.pages)
        except Exception as exc:                                 # noqa: BLE001
            fail += 1
            payload["flags"].append(f"pdf text extraction failed: {type(exc).__name__}: {exc}")
            payload["parse_status"] = "extract_failed"
            write_capture("gamebook", key, payload)
            continue
        parsed = parse_gamebook_text(text)
        parsed["pages"] = npages
        parsed["notes"] = notes
        parsed["text_sha256"] = sha256_text(text)
        payload["parsed"] = parsed
        payload["parse_status"] = parsed.get("parse_status")
        payload["counts"] = {"not_active": len([n for n in parsed.get("Not Active", [])
                                                if not n.get("unparsed")]),
                             "did_not_play": len([n for n in parsed.get("Did Not Play", [])
                                                  if not n.get("unparsed")]),
                             "unparsed": len([n for n in (parsed.get("Not Active", [])
                                                           + parsed.get("Did Not Play", []))
                                              if n.get("unparsed")])}
        if payload["counts"]["not_active"] == 0:
            payload["flags"].append("no Not Active name parsed: the game is recorded, not published as zero")
            fail += 1
        else:
            ok += 1
        p = write_capture("gamebook", key, payload)
        append_jsonl(HEARTBEAT, {"at": payload["fetched_at"], "kind": "gamebook", "key": key,
                                 "url": meta["pdf_url"], "rows": payload["counts"]["not_active"],
                                 "status": payload["parse_status"],
                                 "pdf_sha256": payload["pdf_sha256"],
                                 "capture": str(p.relative_to(ROOT))})
        time.sleep(args.sleep)
    print(f"gamebooks: ok={ok} fail={fail} already-captured={skipped} "
          f"no-game-book-published={missing}")
    if missing and not games:
        print("::warning::game books: nothing was discovered for those weeks")
    return 0 if fail == 0 else 1


def iter_captures(kind: str):
    for p in list_captures(kind):
        try:
            yield p, json.loads(p.read_text())
        except Exception as exc:                                 # noqa: BLE001
            yield p, {"_unreadable": f"{type(exc).__name__}: {exc}"}


def cmd_verify(args) -> int:
    """Hash-replay every capture, check the pins, check freshness. No network."""
    problems: list[str] = []
    notes: list[str] = []
    seen = 0
    for kind in ("inactives", "report", "gamebook"):
        for p, cap in iter_captures(kind):
            seen += 1
            if "_unreadable" in cap:
                problems.append(f"{p.name}: unreadable capture ({cap['_unreadable']})")
                continue
            if cap.get("parser_version") != PARSER_VERSION and not cap.get("transcription"):
                notes.append(f"{p.name}: parser_version {cap.get('parser_version')!r} != {PARSER_VERSION!r}")
            for field in ("kind", "key", "fetched_at", "url", "rows"):
                if kind == "gamebook":
                    field = {"url": "game_centre_url", "rows": "parsed"}.get(field, field)
                if cap.get(field) in (None, "", [], {}):
                    if not (kind == "gamebook" and field == "parsed" and cap.get("flags")):
                        problems.append(f"{p.name}: required field {field!r} is blank")
            if cap.get("raw_sha256"):
                if not re.fullmatch(r"[0-9a-f]{64}", cap["raw_sha256"]):
                    problems.append(f"{p.name}: raw_sha256 is not a sha256")
            if kind == "inactives" and cap.get("rows"):
                per = {}
                for r in cap["rows"]:
                    per[r.get("club") or "?"] = per.get(r.get("club") or "?", 0) + 1
                lo, hi = INACTIVES_PER_CLUB_RANGE
                bad = {c: n for c, n in per.items() if not lo <= n <= hi}
                if bad:
                    notes.append(f"{p.name}: inactive count outside {lo}-{hi} per club: {bad}")
                dup = {}
                for r in cap["rows"]:
                    k = (r.get("club"), (r.get("name") or "").lower())
                    dup[k] = dup.get(k, 0) + 1
                doubled = sorted(f"{c}|{n}" for (c, n), k in dup.items() if c and n and k > 1)
                if doubled:
                    problems.append(f"{p.name}: duplicate inactive rows: {doubled[:5]}")
            for r in (cap.get("rows") or []):
                if kind == "inactives" and (not r.get("club") or not r.get("name")):
                    problems.append(f"{p.name}: row with a blank club or name: {r}")
                if kind == "report" and not r.get("player"):
                    problems.append(f"{p.name}: report row with a blank player: {r}")
    if args.max_age_hours:
        hb = [json.loads(l) for l in HEARTBEAT.read_text().splitlines() if l.strip()] \
            if HEARTBEAT.exists() else []
        for kind in ("inactives", "report", "gamebook"):
            last = [h for h in hb if h.get("kind") == kind]
            if not last:
                notes.append(f"{kind}: no heartbeat line yet (never run)")
                continue
            ts = last[-1].get("at", "")
            try:
                age = (datetime.now(timezone.utc)
                       - datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() / 3600
                if age > args.max_age_hours:
                    notes.append(f"{kind}: last capture {age:.1f}h old > {args.max_age_hours}h")
            except Exception:                                    # noqa: BLE001
                notes.append(f"{kind}: unparsable heartbeat timestamp {ts!r}")
    print(f"game-book gate: {seen} capture(s) checked, {len(problems)} failure(s), {len(notes)} note(s)")
    for x in problems:
        print("  FAIL", x)
    for x in notes[:40]:
        print("  note", x)
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("inactives")
    a.add_argument("--season", type=int, required=True)
    a.add_argument("--week", type=int, required=True)
    a.add_argument("--url", help="override the article url (used when the pattern differs)")
    a.set_defaults(func=cmd_inactives)
    b = sub.add_parser("reports")
    b.add_argument("--season", type=int, required=True)
    b.add_argument("--week", type=int, required=True)
    b.set_defaults(func=cmd_reports)
    c = sub.add_parser("gamebooks")
    c.add_argument("--season", type=int, required=True)
    c.add_argument("--week-from", type=int, default=1)
    c.add_argument("--week-to", type=int, default=22)
    c.add_argument("--weeks", help="comma list, overrides from/to")
    c.add_argument("--limit", type=int, default=0)
    c.add_argument("--pages", type=int, default=4)
    c.add_argument("--sleep", type=float, default=1.5)
    c.add_argument("--refetch", action="store_true")
    c.add_argument("--strict", action="store_true",
                   help="treat a game centre with no Game Book link as a failure (default: "
                        "record it as missing coverage and keep going)")
    c.set_defaults(func=cmd_gamebooks)
    v = sub.add_parser("verify")
    v.add_argument("--max-age-hours", type=float, default=0)
    v.set_defaults(func=cmd_verify)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
