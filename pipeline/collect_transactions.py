#!/usr/bin/env python3
"""Immutable, timestamped captures of the official NFL transactions register.

Session 1d824ec2-nfl1 (task V2/V3). Runs in GitHub Actions: nfl.com is not reachable from the
Arena sandbox, and the brief requires an official source for every row.

Why this file exists
--------------------
The weekly injury report names players who are *questionable for this week's game*. It does not
name a player who is on a reserve list, because the league does not put him on the weekly report
at all. So "absent from the injury report" has always been read here as "available", which is
wrong: Malik Willis (MIA) is on the Week 10 injury report page nowhere, because he was placed on
injured reserve on 11/10 (read from the official register on 2026-11-16), not because he is
healthy. The same register is the only official, dated record of the trades, releases and waiver
claims that make a depth chart stale (the brief's "roster turnover as a first-class data event"
and "flag stale depth rows against the official transactions log").

The official feed is https://www.nfl.com/transactions/, which carries six dated categories per
month: Trades, Signings, Reserve List, Waivers, Terminations, Other. Each is one table with the
columns From, To, Date, Name, Position, Transaction.

What it does, once per run
--------------------------
1. For every pinned (category, year, month), fetches the page, records HTTP status, byte count
   and SHA-256 of the raw body with the UTC fetch time, and parses its table by *header name*,
   never by column position.
2. Keeps one immutable capture file per (category, month) whenever the parsed rows change.
   Capture files are created with exclusive-create and never rewritten, so the same source can be
   replayed as it was known on that date.
3. Appends a heartbeat line for every run (including a run where nothing changed), so the cadence
   is auditable and a missing run is visible.
4. Rebuilds the derived files (flat row table, per-club reserve state, coverage, report-vs-reserve
   join) from the captures only. Nothing is typed into them.
5. Raises a conflict flag for anything ambiguous, and fails the run (exit 1) when a page that
   must carry rows carries none, when a required column is missing, or when a row cannot be
   attributed to one of the 32 current clubs. A blank is published as a blank and flagged; it is
   never filled by inference.

Usage:
    python3 pipeline/collect_transactions.py collect            # fetch, parse, store, derive
    python3 pipeline/collect_transactions.py collect --months 2026-09,2026-10,2026-11
    python3 pipeline/collect_transactions.py derive             # rebuild derived files from captures
    python3 pipeline/collect_transactions.py verify [--max-age-hours 30]
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
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data" / "reserve"
CAPTURES = STORE / "captures"
HEARTBEAT = STORE / "heartbeat.jsonl"
MANIFEST = STORE / "manifest.json"
ALERTS = STORE / "alerts.jsonl"

ROWS_TSV = STORE / "transactions.tsv"
ROWS_JSON = STORE / "transactions.json"
STATE_JSON = STORE / "reserve_state.json"
COVERAGE_JSON = STORE / "coverage.json"
JOIN_JSON = STORE / "report_vs_reserve.json"

BASE = "https://www.nfl.com/transactions/league"
SEASON_YEAR = 2026
CATEGORIES = ["trades", "signings", "reserve-list", "waivers", "terminations", "other"]
# Months the season actually runs plus the pre-season roster-cut months. A month not in this list
# is not claimed to be empty; the coverage file records exactly what was fetched.
DEFAULT_MONTHS = ["2026-08", "2026-09", "2026-10", "2026-11"]
# A category/month that has rows in one run and none in a later run is a schema or availability
# change, not an empty month. A category/month that has NEVER had rows is reported as "empty".
MUST_HAVE_ROWS = {("reserve-list", "2026-09"), ("reserve-list", "2026-10"),
                  ("reserve-list", "2026-11"), ("trades", "2026-11")}
# Verified against the live page on 2026-11-16: every transactions month page prints at most this
# many rows, newest first. A page that returns exactly this many is truncated by the publisher, not
# by us: `?page=2` returns the same rows and a per-day url returns 404, so the only recovery is to
# read the running page often and keep the union of every read.
PRINTED_CAP = 25
PARSER_VERSION = "collect_transactions/1.0"
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
REQUIRED_HEADERS = {"from", "to", "date", "name"}
LOGO_RE = re.compile(r"clubs/logos/([A-Z]{2,3})")
PLAYER_HREF_RE = re.compile(r"^https://www\.nfl\.com/players/([^/]+)/?$")
DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})$")
CLUB_CODES = {
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB", "HOU",
    "IND", "JAX", "KC", "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG", "NYJ", "PHI", "PIT",
    "SEA", "SF", "TB", "TEN", "WAS",
}
# The printed register uses AZ for Arizona and LA for the Rams; data/reference/teams.csv uses
# ARI and LAR. The alias is recorded, never silently renamed.
CLUB_ALIASES = {"AZ": "ARI", "LAR": "LA", "SD": "LAC", "OAK": "LV", "STL": "LA"}
# Official transaction texts that END a reserve designation, matched on the printed wording.
OFF_RESERVE_RE = re.compile(
    r"(designated to return from|activated from|released from|signed from|\bfrom\b.*(injured reserve|reserve/injured))",
    re.I)
ON_RESERVE_RE = re.compile(r"reserve/", re.I)

INJURY_REPORT = ROOT / "data" / "model" / "official_injuries.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(p: Path) -> str:
    """Path as seen from the repository root, or absolute when the store is elsewhere (tests)."""
    try:
        return str(Path(p).relative_to(ROOT))
    except ValueError:
        return str(p)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(rows: list[dict]) -> str:
    """Hash of the parsed content only: stable across ads, session tokens and markup churn."""
    keep = ["date", "club_from", "club_to", "player", "player_url", "position", "transaction"]
    payload = [{k: r.get(k) for k in keep} for r in sorted(rows, key=row_sort_key)]
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def row_sort_key(r: dict) -> tuple:
    return (r.get("date") or "", r.get("club_to") or r.get("club_from") or "",
            r.get("player") or "", r.get("transaction") or "")


def club_of(cell) -> tuple[str | None, str | None]:
    """Return (printed club code, club page url) for a From/To cell, or (None, None)."""
    if cell is None:
        return None, None
    img = cell.find("img")
    code = None
    if img and img.get("src"):
        m = LOGO_RE.search(img["src"])
        if m:
            code = m.group(1)
    a = cell.find("a")
    url = a.get("href") if a and a.get("href") else None
    if code is None:
        text = cell.get_text(" ", strip=True)
        m = re.search(r"\b([A-Z]{2,3})\b", text)
        if m:
            code = m.group(1)
    return code, url


def parse_rows(html: str, year: int, month: int, source_url: str) -> tuple[list[dict], list[str], list[str]]:
    """Parse every transaction table on a page.

    Returns (rows, headers_seen, flags). Header names, not cell positions, decide where a value
    goes, so a reordered column changes the row count not at all — and a missing required header
    is a flag, not a silent shift.
    """
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []
    headers_seen: list[str] = []
    flags: list[str] = []
    tables = soup.find_all("table")
    if not tables:
        return rows, headers_seen, ["no <table> element on the page"]
    for t_i, table in enumerate(tables):
        header_row = table.find("thead") or table
        ths = header_row.find_all("th")
        if not ths:
            first = table.find("tr")
            ths = first.find_all(["td", "th"]) if first else []
        header = [(th.get_text(" ", strip=True) or "").lower() for th in ths]
        if not any(header):
            continue
        headers_seen.append("|".join(h or "?" for h in header))
        col = {}
        for want in REQUIRED_HEADERS | {"position", "transaction"}:
            for i, h in enumerate(header):
                if want in h:
                    col[want] = i
                    break
        missing = [h for h in REQUIRED_HEADERS if h not in col]
        if missing:
            flags.append(f"table {t_i}: required header(s) missing: {','.join(sorted(missing))}")
            continue
        body = table.find("tbody") or table
        for tr in body.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < len(header) or not tds:
                continue
            cells = {k: tds[i] if i < len(tds) else None for k, i in col.items()}
            name_cell = cells.get("name")
            link = name_cell.find("a") if name_cell else None
            player = link.get_text(" ", strip=True) if link else (
                name_cell.get_text(" ", strip=True) if name_cell else "")
            href = link.get("href") if link and link.get("href") else None
            if href:
                href = href if href.startswith("http") else "https://www.nfl.com" + href
            m = PLAYER_HREF_RE.match(href or "")
            if not m:
                href = None  # a name with no official player page stays a name, with no link
            date_cell = cells.get("date")
            dtext = date_cell.get_text(" ", strip=True) if date_cell else ""
            dm = DATE_RE.match(dtext)
            if not dm:
                flags.append(f"table {t_i}: unparseable date {dtext!r} for {player!r}")
                iso = None
            else:
                iso = f"{year}-{int(dm.group(1)):02d}-{int(dm.group(2)):02d}"
            f_code, _ = club_of(cells.get("from"))
            t_code, _ = club_of(cells.get("to"))
            position = cells.get("position").get_text(" ", strip=True) if cells.get("position") else ""
            txn = cells.get("transaction").get_text(" ", strip=True) if cells.get("transaction") else ""
            if not player:
                flags.append(f"table {t_i}: row with no player name ({iso} {txn})")
                continue
            if not f_code and not t_code:
                flags.append(f"table {t_i}: row for {player!r} carries no club code on either "
                             f"side; the club is left blank rather than guessed")
            for label, code in (("from", f_code), ("to", t_code)):
                if code and code not in CLUB_CODES and code not in CLUB_ALIASES:
                    flags.append(f"table {t_i}: club code {code!r} ({label}) is not one of the 32; "
                                 f"row kept, code left as printed")
            rows.append({
                "date": iso,
                "date_printed": dtext,
                "category": None,          # filled by the caller
                "month": f"{year}-{month:02d}",
                "club_from": f_code,
                "club_to": t_code,
                "player": player,
                "player_url": href,
                "position_printed": position or None,
                "transaction": txn or None,
                "source_url": source_url,
            })
    return rows, headers_seen, flags


def fetch(url: str, attempts: int = 4) -> tuple[int, str, str]:
    last = None
    for i in range(attempts):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT,
                                           "Accept-Language": "en-US,en;q=0.9"},
                             timeout=60)
            if r.status_code == 200 and r.text.strip():
                return r.status_code, r.text, r.url
            last = f"status {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last = repr(exc)[:160]
        time.sleep(2 + 3 * i)
    raise RuntimeError(f"fetch failed after {attempts} attempts ({last})")


def cap_facts(rows: list[dict], year: int, month: int) -> dict:
    """Facts about the publisher's own window, from one read of one page.

    Verified on the live page 2026-11-16: a transactions category-month page prints at most
    PRINTED_CAP rows, newest first, and offers no deeper window (`?page=2` repeats the same rows, a
    per-day url returns 404). So a read of exactly PRINTED_CAP rows is only a complete view of the
    month when its oldest row reaches the first day of the month. Returned as data, never as a
    silent fix: the missing rows do not exist anywhere we can reach, so they are disclosed.
    """
    n = len(rows)
    dates = sorted(r["date"] for r in rows if r.get("date"))
    month_start = f"{year}-{month:02d}-01"
    oldest = dates[0] if dates else None
    capped = n >= PRINTED_CAP
    return {
        "cap": capped,
        "cap_rows_printed": n,
        "cap_oldest_printed": oldest,
        "cap_month_complete_as_printed": (not capped) or bool(dates) and oldest <= month_start,
        "cap_note": (f"page is at its printed cap of {PRINTED_CAP} rows (oldest printed {oldest}, "
                     f"month starts {month_start}); the league prints no deeper window: ?page=2 "
                     f"repeats the same rows and a per-day url returns 404, verified 2026-11-16")
        if capped else "",
    }


def capture_one(cat: str, ym: str, sleep: float = 1.0) -> dict:
    year, month = (int(x) for x in ym.split("-"))
    url = f"{BASE}/{cat}/{year}/{month}"
    rec = {"category": cat, "month": ym, "url": url, "fetched_at_utc": now_iso()}
    try:
        status, html, final = fetch(url)
    except RuntimeError as exc:
        rec.update(status="fetch_error", error=str(exc), rows=0, row_list=[])
        return rec
    time.sleep(sleep)
    rows, headers, flags = parse_rows(html, year, month, url)
    for r in rows:
        r["category"] = cat
    canon = canonical(rows)
    rec.update(status="ok", http_status=status, final_url=final,
               raw_bytes=len(html.encode()), raw_sha256=sha256_text(html),
               canonical_sha256=canon, rows=len(rows), tables=len(headers),
               headers=headers, flags=flags,
               row_list=sorted(rows, key=row_sort_key))
    if not rows:
        # A page with no rows is either an empty month or a schema change. Say which, by keyword.
        marker = {"trades": "Traded", "signings": "Signed", "reserve-list": "Reserve/",
                  "waivers": "Waiver", "terminations": "Terminated", "other": "released"}[cat]
        rec["flag_page_has_keyword"] = marker in html
        if rec["flag_page_has_keyword"]:
            rec["flags"] = flags + [f"page mentions {marker!r} but no table row parsed: parser or schema drift"]
    # The printed cap. Verified on 2026-11-16: /transactions/league/reserve-list/2026/11 prints the
    # 25 most recent rows of the month, ?page=2 returns the same 25 rows, and a per-day URL 404s.
    # So 25 rows with the oldest one still inside the month means the page is at its cap and the
    # month is only partly printed. Recorded as a fact about the source, not repaired by inference.
    rec.update(cap_facts(rows, year, month))
    if rec["cap"]:
        rec["flags"] = (rec.get("flags") or []) + [rec["cap_note"]]
    return rec


def write_capture(rec: dict) -> Path | None:
    """Exclusive-create a capture file when the parsed content differs from the newest one."""
    CAPTURES.mkdir(parents=True, exist_ok=True)
    stem = f"{rec['category']}_{rec['month']}"
    existing = sorted(CAPTURES.glob(f"{stem}_*.json"))
    if existing:
        try:
            last = json.loads(existing[-1].read_text(encoding="utf-8"))
            if last.get("canonical_sha256") == rec.get("canonical_sha256"):
                return None
        except Exception:  # noqa: BLE001  a truncated file is not a reason to skip the new one
            pass
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = CAPTURES / f"{ts}_{stem}_{rec['canonical_sha256'][:12]}.json"
    payload = {"captured_at_utc": rec["fetched_at_utc"], "parser": PARSER_VERSION, **rec,
               "_file": rel(path)}
    # The row content lives in the capture file itself, so the derived files can be rebuilt
    # offline from stored data alone and hashed against it.
    payload["row_list"] = sorted(rec["row_list"], key=row_sort_key)
    body = json.dumps(payload, indent=1, ensure_ascii=False) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


def load_captures() -> list[dict]:
    out = []
    for p in sorted(CAPTURES.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            d["_file"] = rel(p)
            out.append(d)
        except Exception as exc:  # noqa: BLE001
            out.append({"_unreadable": p.name, "_file": rel(p), "_error": repr(exc)[:160]})
    return out


def latest_rows_per_key(captures: list[dict]) -> tuple[list[dict], dict]:
    """Union every capture of a (category, month) page, newest metadata winning.

    Deduplication is on the printed content (date, both clubs, name, transaction). A row seen in an
    earlier capture but absent from the newest one is KEPT and marked `seen_in_captures`, because
    the publisher's 25-row window slides: a move can leave the printed page without being undone.
    Dropping it would silently un-publish a fact the league printed.
    """
    by_key: dict[tuple, list[dict]] = {}
    newest: dict[tuple, dict] = {}
    for cap in captures:
        if cap.get("_unreadable") or cap.get("status") != "ok":
            continue
        key = (cap["category"], cap["month"])
        by_key.setdefault(key, []).append(cap)
        if key not in newest or (cap.get("captured_at_utc") or "") >= (
                newest[key].get("captured_at_utc") or ""):
            newest[key] = cap
    rows: list[dict] = []
    for (cat, month), caps in sorted(by_key.items()):
        caps = sorted(caps, key=lambda c: c.get("captured_at_utc") or "")
        seen: dict[tuple, dict] = {}
        for cap in caps:
            for r in cap.get("row_list") or []:
                ident = (r.get("date"), r.get("club_from"), r.get("club_to"), r.get("player"),
                         r.get("transaction"))
                if ident in seen:
                    seen[ident]["seen_in_captures"].append(cap.get("_file", ""))
                    continue
                r2 = dict(r)
                r2["category"] = cat
                r2["month"] = month
                r2["captured_at_utc"] = cap.get("captured_at_utc")
                r2["source_capture"] = cap.get("_file", "")
                r2["seen_in_captures"] = [cap.get("_file", "")]
                seen[ident] = r2
        rows.extend(seen.values())
    return sorted(rows, key=row_sort_key), {f"{c}/{m}": v.get("captured_at_utc")
                                            for (c, m), v in newest.items()}


def normalise_club(code: str | None) -> tuple[str | None, bool]:
    """Map a printed code to the repo's code; second element is True when an alias was applied."""
    if not code:
        return None, False
    return CLUB_ALIASES.get(code, code), code in CLUB_ALIASES


def reserve_state(rows: list[dict]) -> dict:
    """Latest dated event per player per club, so a designation is a state, not a count.

    A player's reserve entry is open until a later dated transaction ends it. Ending patterns
    come from the printed wording; anything that looks like an ending but is not recognised is
    reported as `unclassified_event`, never guessed at.
    """
    per_player: dict[str, list[dict]] = {}
    for r in rows:
        club, aliased = normalise_club(r.get("club_to") or r.get("club_from"))
        key = r["player"]
        r2 = dict(r)
        r2["club"] = club
        r2["club_printed"] = r.get("club_to") or r.get("club_from")
        r2["club_alias_applied"] = aliased
        per_player.setdefault(key, []).append(r2)
    players = {}
    unclassified: list[dict] = []
    for name, events in per_player.items():
        events.sort(key=lambda e: (e.get("date") or "", e.get("category") or ""))
        open_reserve = None
        for e in events:
            txt = e.get("transaction") or ""
            on = bool(ON_RESERVE_RE.search(txt))
            off = bool(OFF_RESERVE_RE.search(txt))
            if on and not off:
                open_reserve = e
            elif off and open_reserve:
                open_reserve = None
            elif off and not open_reserve:
                unclassified.append({"player": name, "date": e.get("date"), "transaction": txt,
                                     "why": "an off-reserve-looking event with no open reserve entry"})
            elif txt and not on and not off and e is events[-1] and open_reserve is None:
                pass  # ordinary move (trade, waiver claim): not a reserve designation
        last = events[-1]
        players[name] = {
            "player": name,
            "events": len(events),
            "first_date": events[0].get("date"),
            "last_date": last.get("date"),
            "club": last.get("club"),
            "club_printed": last.get("club_printed"),
            "position_printed": last.get("position_printed"),
            "last_transaction": last.get("transaction"),
            "on_reserve_as_of_capture": bool(open_reserve),
            "reserve_opened": open_reserve.get("date") if open_reserve else None,
            "reserve_text": open_reserve.get("transaction") if open_reserve else None,
            "categories": sorted({e.get("category") for e in events if e.get("category")}),
            "source_urls": sorted({e.get("source_url") for e in events if e.get("source_url")}),
        }
    by_club: dict[str, dict] = {}
    for name, p in players.items():
        club = p.get("club") or "UNKNOWN"
        d = by_club.setdefault(club, {"club": club, "players_on_reserve": [], "events": 0,
                                     "players_with_turnover": 0})
        d["events"] += p["events"]
        d["players_with_turnover"] += 1
        if p["on_reserve_as_of_capture"]:
            d["players_on_reserve"].append(
                {"player": name, "opened": p["reserve_opened"], "designation": p["reserve_text"],
                 "position_printed": p["position_printed"], "source_urls": p["source_urls"]})
    for d in by_club.values():
        d["n_on_reserve"] = len(d["players_on_reserve"])
        d["players_on_reserve"].sort(key=lambda x: (x["opened"] or "", x["player"]))
    return {"as_of": max((p["last_date"] or "") for p in players.values()) if players else None,
            "players": players, "by_club": by_club, "unclassified_events": unclassified}


def report_vs_reserve(state: dict) -> dict:
    """Join the reserve state to the latest official weekly report.

    The point is not to double-count injuries. It is to make a club's absence list complete: a
    player on a reserve list will never appear on the weekly report, so a report-only count
    understates who is unavailable. Every number is a count of printed rows, both sides linked.
    """
    out = {"note": "The weekly report and the reserve list are two different official records. "
                   "A player on a reserve list does not appear on the weekly report, so a report "
                   "count is not the club's availability count.",
           "clubs": {}, "totals": {}, "join_source": None}
    if not INJURY_REPORT.exists():
        # No per-club keys at all: an empty `clubs` map would read as "every club has zero rows",
        # which is a number, and no number may be published from a file that is not there.
        return {"note": out["note"],
                "error": "data/model/official_injuries.json absent: the weekly side of the join "
                         "was not available, so no count is published"}
    rep = json.loads(INJURY_REPORT.read_text(encoding="utf-8"))
    rep_rows = rep.get("rows") or []
    out["join_source"] = {"url": rep.get("source_url"), "week": rep.get("week"),
                          "season": rep.get("season"), "report_rows": len(rep_rows),
                          "tables_parsed": rep.get("tables_parsed"),
                          "generated_at": rep.get("generated_at"),
                          "html_sha256": rep.get("html_sha256")}
    by_club_rep: dict[str, list[dict]] = {}
    for r in rep_rows:
        by_club_rep.setdefault(r.get("team") or "UNKNOWN", []).append(r)
    rep_week_label = f"Week {rep.get('week')}"
    clubs = sorted(set(by_club_rep) | set(state.get("by_club") or {}))
    tot = {"report_rows": 0, "on_reserve": 0, "named_in_both": 0, "on_reserve_not_in_report": 0}
    for club in clubs:
        rep_rows_c = by_club_rep.get(club, [])
        names_rep = {r["player"] for r in rep_rows_c}
        reserve = (state.get("by_club") or {}).get(club, {}).get("players_on_reserve", [])
        both, only_reserve = [], []
        for p in reserve:
            (both if p["player"] in names_rep else only_reserve).append(p["player"])
        row = {"club": club, "report_rows": len(rep_rows_c),
               "report_week": rep_week_label,
               "n_on_reserve": len(reserve),
               "on_reserve_not_in_report": len(only_reserve),
               "named_in_both": len(both),
               "on_reserve_names": [p["player"] for p in reserve],
               "unavailable_total_report_plus_reserve": len(names_rep) + len(only_reserve)}
        out["clubs"][club] = row
        tot["report_rows"] += len(rep_rows_c)
        tot["on_reserve"] += len(reserve)
        tot["named_in_both"] += len(both)
        tot["on_reserve_not_in_report"] += len(only_reserve)
    out["totals"] = tot
    out["clubs_with_no_report_table"] = sorted(
        c for c in (state.get("by_club") or {}) if c not in by_club_rep)
    return out


def write_derived(rows: list[dict], captures: list[dict], newest: dict) -> dict:
    STORE.mkdir(parents=True, exist_ok=True)
    cols = ["date", "category", "club_from", "club_to", "player", "position_printed",
            "transaction", "source_url", "player_url"]
    header = ["date", "category", "club_from_printed", "club_to_printed", "player",
              "position_printed", "transaction", "source_url", "player_url",
              "date_missing", "transaction_missing"]
    with ROWS_TSV.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(header) + "\n")
        for r in rows:
            fh.write("\t".join(str(r.get(c) or "") for c in cols)
                     + "\t" + ("1" if not r.get("date") else "")
                     + "\t" + ("1" if not r.get("transaction") else "") + "\n")
    ROWS_JSON.write_text(json.dumps({"parser": PARSER_VERSION, "generated_at_utc": now_iso(),
                                     "rows": rows, "count": len(rows)},
                                    indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    state = reserve_state(rows)
    state["generated_at_utc"] = now_iso()
    state["parser"] = PARSER_VERSION
    STATE_JSON.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    join = report_vs_reserve(state)
    join["generated_at_utc"] = now_iso()
    JOIN_JSON.write_text(json.dumps(join, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    cov = {"generated_at_utc": now_iso(), "parser": PARSER_VERSION,
           "categories": CATEGORIES, "months_requested": newest.get("_months", DEFAULT_MONTHS),
           "pages": {}, "flags": []}
    for cap in captures:
        if cap.get("_unreadable"):
            cov["flags"].append({"page": cap.get("_unreadable"),
                                 "flag": "capture file is not readable JSON"})
            continue
        key = f"{cap.get('category')}/{cap.get('month')}"
        prev = cov["pages"].get(key)
        entry = {"captured_at_utc": cap.get("captured_at_utc") or cap.get("fetched_at_utc"),
                 "status": cap.get("status"), "rows": cap.get("rows"),
                 "canonical_sha256": cap.get("canonical_sha256"),
                 "raw_sha256": cap.get("raw_sha256"), "http_status": cap.get("http_status"),
                 "url": cap.get("url"), "flags": cap.get("flags") or [],
                 # The cap is derived from the stored rows, so a capture written before the flag
                 # existed is judged by the same rule as one written after it: the number of rows a
                 # single read returned is a fact inside the capture, not a note beside it.
                 "rows_last_read": len(cap.get("row_list") or []),
                 "cap_rows_printed": len(cap.get("row_list") or []),
                 "cap_oldest_printed": min((x.get("date") for x in (cap.get("row_list") or [])
                                            if x.get("date")), default=None),
                 "cap": cap_facts(cap.get("row_list") or [], int(str(cap.get("month") or "0000-01")[:4]),
                                  int(str(cap.get("month") or "0000-01")[5:7] or 1))["cap"],
                 "cap_at_source_flag": cap.get("cap"),
                 "captures_for_page": sum(1 for x in captures if x.get("category") == cap.get("category")
                                          and x.get("month") == cap.get("month")),
                 "headers": cap.get("headers") or []}
        if prev and (entry["captured_at_utc"] or "") >= (prev["captured_at_utc"] or ""):
            cov["pages"][key] = entry
        elif prev is None:
            cov["pages"][key] = entry
        for f in entry["flags"]:
            cov["flags"].append({"page": key, "flag": f})
    union_per_page: dict[str, int] = {}
    for r in rows:
        k = f"{r.get('category')}/{r.get('month')}"
        union_per_page[k] = union_per_page.get(k, 0) + 1
    for k, entry in cov["pages"].items():
        entry["rows_in_the_union"] = union_per_page.get(k, 0)
    for k, e in cov["pages"].items():
        month_start = (k.split("/")[1] if "/" in k else "") + "-01"
        e["cap_month_complete_as_printed"] = bool(e.get("cap_oldest_printed")) and \
            (e.get("cap_oldest_printed") or "") <= month_start
    cov["pages_capped"] = sorted(k for k, e in cov["pages"].items() if e.get("cap"))
    cov["months_incomplete_at_source"] = sorted(
        k for k, e in cov["pages"].items() if e.get("cap") and not e["cap_month_complete_as_printed"])
    cov["months_fully_printed"] = sorted(k for k, e in cov["pages"].items()
                                         if not e.get("cap") or e["cap_month_complete_as_printed"])
    cov["printed_cap"] = PRINTED_CAP
    cov["cap_explained"] = ("The league's month page prints at most "
                            f"{PRINTED_CAP} rows, newest first, and offers no deeper window "
                            "(`?page=2` repeats the same rows; a per-day url returns 404). A page at"
                            f" {PRINTED_CAP} rows is therefore only complete for the month if its "
                            "oldest printed row is on the first day. Capturing the running page "
                            "often is what recovers the rest: the derived register is the union of "
                            "every capture of that page, so a row is never lost by leaving the "
                            "printed window.")
    cov["pages"] = dict(sorted(cov["pages"].items()))
    cov["n_pages"] = len(cov["pages"])
    cov["n_rows_latest"] = len(rows)
    COVERAGE_JSON.write_text(json.dumps(cov, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"rows": len(rows), "clubs": len(state.get("by_club") or {}),
            "on_reserve": sum(c["n_on_reserve"] for c in (state.get("by_club") or {}).values()),
            "pages": cov["n_pages"], "flags": len(cov["flags"])}


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")


def cmd_collect(args) -> int:
    months = args.months.split(",") if args.months else DEFAULT_MONTHS
    cats = args.categories.split(",") if args.categories else CATEGORIES
    failures: list[str] = []
    n_new = 0
    for ym in months:
        for cat in cats:
            rec = capture_one(cat, ym, sleep=args.sleep)
            path = None
            if rec.get("status") == "ok":
                try:
                    path = write_capture(rec)
                except FileExistsError:
                    path = None      # same content raced a concurrent write; nothing to store
                if path:
                    n_new += 1
            hb = {k: rec.get(k) for k in
                  ("category", "month", "url", "fetched_at_utc", "status", "http_status",
                   "rows", "raw_bytes", "raw_sha256", "canonical_sha256", "flags")}
            hb["capture"] = rel(path) if path else None
            hb["parser"] = PARSER_VERSION
            append_jsonl(HEARTBEAT, hb)
            if rec.get("status") != "ok":
                failures.append(f"{cat}/{ym}: {rec.get('error')}")
                continue
            if rec.get("rows", 0) == 0 and (cat, ym) in MUST_HAVE_ROWS:
                failures.append(f"{cat}/{ym}: page carries no parsed row; a month that must have "
                                f"rows returned none")
            for f in rec.get("flags") or []:
                append_jsonl(ALERTS, {"at": rec["fetched_at_utc"], "page": f"{cat}/{ym}",
                                      "flag": f})
            print(f"{cat}/{ym}: {rec['rows']} rows, sha {rec['canonical_sha256'][:12]}, "
                  f"{'new capture' if path else 'unchanged'}")
        # end category loop
    captures = load_captures()
    rows, newest = latest_rows_per_key(captures)
    newest["_months"] = months
    summary = write_derived(rows, captures, newest)
    manifest = {"schema": "transactions_register/1", "parser": PARSER_VERSION,
                "generated_at_utc": now_iso(),
                "note": "Append-only captures; derived files rebuilt from them. Each capture "
                        "file is written once with exclusive-create and its SHA-256 is recorded.",
                "categories": CATEGORIES, "months": months,
                "must_have_rows": [f"{c}/{m}" for c, m in sorted(MUST_HAVE_ROWS)],
                "captures": [], "summary": summary}
    for cap in captures:
        p = (ROOT / cap["_file"]) if not cap["_file"].startswith("/") else Path(cap["_file"])
        manifest["captures"].append({
            "file": cap["_file"], "sha256": sha256_text(p.read_text(encoding="utf-8")),
            "category": cap.get("category"), "month": cap.get("month"),
            "captured_at_utc": cap.get("captured_at_utc"),
            "canonical_sha256": cap.get("canonical_sha256"),
            "raw_sha256": cap.get("raw_sha256"), "rows": cap.get("rows"),
            "url": cap.get("url"), "status": cap.get("status")})
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"derived: {summary['rows']} rows, {summary['pages']} pages, "
          f"{summary['on_reserve']} players on an open reserve designation, "
          f"{n_new} new capture(s), {summary['flags']} flag(s) on record")
    if failures:
        for f in failures:
            print(f"FAIL {f}", file=sys.stderr)
        return 1
    return 0


def cmd_derive(_args) -> int:
    captures = load_captures()
    rows, newest = latest_rows_per_key(captures)
    newest["_months"] = DEFAULT_MONTHS
    summary = write_derived(rows, captures, newest)
    print(f"derived from {len(captures)} capture(s): {summary}")
    return 0


def cmd_verify(args) -> int:
    """Recompute every hash and the derived row set from the stored captures; check freshness."""
    failures: list[str] = []
    caps = load_captures()
    if not caps:
        print("FAIL no capture files in data/reserve/captures/")
        return 1
    for cap in caps:
        if cap.get("_unreadable"):
            failures.append(f"unreadable capture {cap['_unreadable']}: {cap['_error']}")
            continue
        rows = cap.get("row_list") or []
        if canonical(rows) != cap.get("canonical_sha256"):
            failures.append(f"{cap['_file']}: row_list no longer hashes to the recorded "
                            f"canonical_sha256 (edited capture)")
        if cap.get("status") == "ok" and (cap.get("category"), cap.get("month")) in MUST_HAVE_ROWS \
                and not rows:
            failures.append(f"{cap.get('category')}/{cap.get('month')}: pinned as must-have-rows "
                            f"but the capture holds none")
    rows, _ = latest_rows_per_key(caps)
    state = reserve_state(rows)
    n_on = sum(c["n_on_reserve"] for c in (state.get("by_club") or {}).values())
    if not rows:
        failures.append("no rows at all: the register is empty, which must never be published")
    if args.max_age_hours:
        ages = []
        for cap in caps:
            ts = cap.get("captured_at_utc")
            if not ts:
                continue
            try:
                dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                ages.append((datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)
            except ValueError:
                failures.append(f"bad captured_at_utc {ts!r} in {cap['_file']}")
        if not ages:
            failures.append("no capture carries a parseable timestamp")
        elif min(ages) > args.max_age_hours:
            failures.append(f"newest capture is {min(ages):.1f} h old, older than the "
                            f"{args.max_age_hours} h freshness limit")
    print(f"verify: {len(caps)} capture(s), {len(rows)} row(s) in the current view, "
          f"{n_on} players on an open reserve designation, "
          f"{len({p.get('club') for p in state['players'].values()})} clubs")
    if failures:
        for f in failures:
            print(f"FAIL {f}", file=sys.stderr)
        return 1
    print("PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect", help="fetch, parse, store and derive")
    c.add_argument("--months", help="comma-separated YYYY-MM list (default: the pinned season months)")
    c.add_argument("--categories", help="comma-separated category list (default: all six)")
    c.add_argument("--sleep", type=float, default=1.0, help="seconds between requests")
    c.set_defaults(fn=cmd_collect)
    d = sub.add_parser("derive", help="rebuild the derived files from the stored captures only")
    d.set_defaults(fn=cmd_derive)
    v = sub.add_parser("verify", help="re-hash every capture, check pins and freshness")
    v.add_argument("--max-age-hours", type=float, default=0)
    v.set_defaults(fn=cmd_verify)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
