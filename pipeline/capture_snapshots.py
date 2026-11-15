#!/usr/bin/env python3
"""Immutable, timestamped captures of the official NFL injury report (nfl.com/injuries).

Session 90c2b454-nfl1, task P2.

What it does, once per run:

1. Fetches https://www.nfl.com/injuries/ and records the HTTP status, the byte count and the
   SHA-256 of the raw response body, with the UTC fetch time. Raw bytes are hashed, not stored
   (the page carries advertising and session markup that changes on every request).
2. Parses the report's own tables (Player / Position / Injuries / Practice Status / Game Status).
   The club of each table is read from the club-name heading that precedes it, mapped to the
   official abbreviation through data/reference/teams.csv restricted to the 32 current clubs.
3. Appends one line to the heartbeat log for EVERY run, so the cadence of captures is visible.
4. Writes a new capture file ONLY when the parsed report (canonical rows) differs from the last
   capture. Capture files are created with exclusive-create and are never rewritten.
5. Appends the field-level delta between the previous and the new capture to changes.jsonl
   (designation evolution, e.g. Did Not Participate -> Limited -> Full, Questionable -> Out).
6. Raises conflict flags (never silently drops them) and writes schema/drift alerts to alerts.jsonl.

Failure policy (drift alarm): if the page cannot be fetched, has no recognisable week/season,
has no report tables, has fewer rows than the pinned minimum, or a table lacks the Practice
Status column, the run exits non-zero so the workflow turns red, and no capture is written.

Usage:
    python pipeline/capture_snapshots.py capture          # fetch, parse, store (scheduled job)
    python pipeline/capture_snapshots.py verify           # hash-check every capture, check freshness
    python pipeline/capture_snapshots.py verify --max-age-hours 12
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data" / "snapshots" / "injury_report"
CAPTURES = STORE / "captures"
HEARTBEAT = STORE / "heartbeat.jsonl"
CHANGES = STORE / "changes.jsonl"
ALERTS = STORE / "alerts.jsonl"
MANIFEST = STORE / "manifest.json"
TEAMS_CSV = ROOT / "data" / "reference" / "teams.csv"

URL = "https://www.nfl.com/injuries/"
PARSER_VERSION = "capture_snapshots/1.0"
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Drift pins. A parse below these is a failure, not a publication.
MIN_ROWS = 100
MIN_TABLES = 10
ROW_DROP_ALERT = 0.25          # alert when the row count falls by more than 25% vs last capture
MAX_MISSING_PLAYER_SHARE = 0.02

# Official designation vocabulary as published on the page. Anything else is flagged.
PRACTICE_VOCAB = {
    "Full Participation in Practice",
    "Limited Participation in Practice",
    "Did Not Participate In Practice",
}
GAME_VOCAB = {"Out", "Doubtful", "Questionable"}

# The 32 current clubs. teams.csv also holds OAK, SD, STL and LAR, whose nicknames collide
# with current clubs (Raiders, Chargers, Rams), so they are excluded from the nickname map.
HISTORICAL_ABBRS = {"OAK", "SD", "STL", "LAR"}

FIELDS = ("club", "player", "position", "injury", "practice_status", "game_status")
TRACKED = ("position", "injury", "practice_status", "game_status")


class CaptureError(RuntimeError):
    """Raised for every condition that must fail the run loudly."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha(rows: list[dict]) -> str:
    blob = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(blob.encode("utf-8"))


def load_nicknames() -> dict[str, str]:
    """Nickname (lower case) -> abbreviation, for the 32 current clubs only."""
    out: dict[str, str] = {}
    with TEAMS_CSV.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            abbr = row["team_abbr"].strip()
            if abbr in HISTORICAL_ABBRS:
                continue
            out[row["team_nick"].strip().lower()] = abbr
    if len(set(out.values())) != 32:
        raise CaptureError(f"expected 32 current clubs in {TEAMS_CSV}, found {len(set(out.values()))}")
    return out


def fetch() -> tuple[int, bytes, str]:
    import requests

    try:
        resp = requests.get(URL, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
                            timeout=60)
    except requests.RequestException as exc:  # network failure is a capture failure, not a silent skip
        raise CaptureError(f"fetch failed: {exc}") from exc
    if resp.status_code != 200:
        raise CaptureError(f"fetch returned HTTP {resp.status_code}")
    return resp.status_code, resp.content, resp.url


def parse(html: bytes, nicknames: dict[str, str]) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    head_text = soup.get_text(" ", strip=True)[:8000]
    m = re.search(r"Week\s+(\d+)\s+of the\s+(20\d{2})\s+Season", f"{title} {head_text}", re.I)
    if not m:
        raise CaptureError("schema drift: no 'Week N of the YYYY Season' marker on the page")
    week, season = int(m.group(1)), int(m.group(2))

    current: str | None = None
    tables: list[dict] = []
    for el in soup.find_all(True):
        if el.name in ("a", "span", "p", "div", "h2", "h3", "h4", "strong", "b", "button"):
            own = el.get_text(" ", strip=True)
            if own and len(own) < 40 and own.lower() in nicknames:
                current = nicknames[own.lower()]
        if el.name != "table":
            continue
        trs = el.find_all("tr")
        if not trs:
            continue
        header = [c.get_text(" ", strip=True).lower() for c in trs[0].find_all(["th", "td"])]
        if "player" not in header or "position" not in header:
            continue  # not a report table
        if "practice status" not in header or "game status" not in header or "injuries" not in header:
            raise CaptureError(f"schema drift: report table header changed: {header}")
        tables.append({"club": current, "header": header, "trs": trs[1:]})

    if len(tables) < MIN_TABLES:
        raise CaptureError(f"parse incomplete: {len(tables)} report tables (pinned minimum {MIN_TABLES})")

    rows: list[dict] = []
    flags: list[str] = []
    seen_clubs: dict[str, int] = {}
    missing_player = 0
    total_cells_rows = 0
    for t in tables:
        club = t["club"]
        if club is None:
            flags.append("table with no club heading (rows kept with club=null)")
        else:
            seen_clubs[club] = seen_clubs.get(club, 0) + 1
        h = t["header"]
        ix = {name: h.index(name) for name in ("player", "position", "injuries", "practice status", "game status")}
        for tr in t["trs"]:
            tds = tr.find_all(["td", "th"])
            cells = [c.get_text(" ", strip=True) for c in tds]
            if len(cells) <= ix["player"]:
                continue
            total_cells_rows += 1
            player = cells[ix["player"]].strip()
            if not player:
                missing_player += 1
                continue
            a = tr.find("a", href=True)
            link = None
            if a and "/players/" in a["href"]:
                link = "https://www.nfl.com" + a["href"].split("?")[0]

            def pick(name: str) -> str | None:
                i = ix[name]
                return cells[i] if i < len(cells) and cells[i] else None

            rows.append({
                "club": club,
                "player": player,
                "position": pick("position"),
                "injury": pick("injuries"),
                "practice_status": pick("practice status"),
                "game_status": pick("game status"),
                "player_url": link,
            })

    if total_cells_rows and missing_player / total_cells_rows > MAX_MISSING_PLAYER_SHARE:
        raise CaptureError(f"schema drift: {missing_player} of {total_cells_rows} rows have no player name")
    if len(rows) < MIN_ROWS:
        raise CaptureError(f"parse incomplete: {len(rows)} rows (pinned minimum {MIN_ROWS})")

    for club, n in seen_clubs.items():
        if n > 1:
            flags.append(f"conflict: {club} has {n} report tables")
    unknown_practice = sorted({r["practice_status"] for r in rows if r["practice_status"]} - PRACTICE_VOCAB)
    if unknown_practice:
        flags.append(f"new practice-status wording: {unknown_practice}")
    unknown_game = sorted({r["game_status"] for r in rows if r["game_status"]} - GAME_VOCAB)
    if unknown_game:
        flags.append(f"new game-status wording: {unknown_game}")
    no_practice = sum(1 for r in rows if not r["practice_status"])
    if no_practice:
        flags.append(f"{no_practice} rows with no practice status")

    names_per_club: dict[tuple[str, str], int] = {}
    for r in rows:
        names_per_club[(r["club"], r["player"])] = names_per_club.get((r["club"], r["player"]), 0) + 1
    for (club, player), n in names_per_club.items():
        if n > 1:
            flags.append(f"conflict: {player} listed {n} times for {club}")
    by_player: dict[str, set[str]] = {}
    for r in rows:
        if r["club"]:
            by_player.setdefault(r["player"], set()).add(r["club"])
    for player, clubs in by_player.items():
        if len(clubs) > 1:
            flags.append(f"conflict: {player} listed under {sorted(clubs)}")

    rows.sort(key=lambda r: (r["club"] or "", r["player"], r["position"] or ""))
    return {"week": week, "season": season, "tables": len(tables), "rows": rows, "flags": flags,
            "clubs": sorted({r["club"] for r in rows if r["club"]})}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")


def last_capture() -> dict | None:
    if not MANIFEST.exists():
        return None
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["captures"]
    if not entries:
        return None
    last = entries[-1]
    return json.loads((ROOT / last["file"]).read_text(encoding="utf-8"))


def row_key(r: dict) -> tuple[str, str]:
    return (r["club"] or "", r["player"])


def diff_rows(old: list[dict], new: list[dict]) -> list[dict]:
    """Field-level changes between two canonical row sets, keyed by (club, player)."""
    a = {row_key(r): r for r in old}
    b = {row_key(r): r for r in new}
    out = []
    for k in sorted(set(a) | set(b)):
        club, player = k
        if k not in a:
            out.append({"change": "added", "club": club, "player": player,
                        "position": b[k]["position"], "to": {f: b[k][f] for f in TRACKED}})
        elif k not in b:
            out.append({"change": "removed", "club": club, "player": player,
                        "position": a[k]["position"], "from": {f: a[k][f] for f in TRACKED}})
        else:
            for f in TRACKED:
                if a[k][f] != b[k][f]:
                    out.append({"change": "changed", "club": club, "player": player, "field": f,
                                "from": a[k][f], "to": b[k][f]})
    return out


def write_manifest(entries: list[dict]) -> None:
    STORE.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({"schema": "injury_report_snapshots/1",
                                    "note": "Append-only. Each capture file is written once with "
                                            "exclusive-create and its SHA-256 is recorded here.",
                                    "captures": entries}, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")


def capture() -> int:
    now = utc_now()
    nicknames = load_nicknames()
    heartbeat = {"fetched_at_utc": iso(now), "source_url": URL, "parser": PARSER_VERSION}
    try:
        status, body, final_url = fetch()
        heartbeat.update({"http_status": status, "final_url": final_url,
                          "raw_sha256": sha256_bytes(body), "raw_bytes": len(body)})
        parsed = parse(body, nicknames)
    except CaptureError as exc:
        heartbeat.update({"status": "failed", "error": str(exc), "changed": False, "capture": None})
        append_jsonl(HEARTBEAT, heartbeat)
        append_alert(now, "fetch-or-parse-failed", str(exc))
        print(f"CAPTURE FAILED: {exc}", file=sys.stderr)
        return 1

    canon = canonical_sha(parsed["rows"])
    heartbeat.update({"week": parsed["week"], "season": parsed["season"], "tables": parsed["tables"],
                      "rows": len(parsed["rows"]), "clubs": len(parsed["clubs"]),
                      "canonical_sha256": canon, "flags": parsed["flags"], "status": "ok"})

    previous = last_capture()
    changed = previous is None or previous["canonical_sha256"] != canon
    heartbeat["changed"] = changed
    heartbeat["capture"] = None

    if previous is not None and previous["season"] == parsed["season"] and previous["week"] == parsed["week"]:
        before = len(previous["rows"])
        drop = (before - len(parsed["rows"])) / before if before else 0
        if drop > ROW_DROP_ALERT:
            msg = f"row count fell {drop:.0%} ({before} -> {len(parsed['rows'])}) vs last capture"
            heartbeat["flags"].append(msg)
            append_alert(now, "row-count-drop", msg)
    for f in parsed["flags"]:
        append_alert(now, "conflict-or-schema-flag", f)

    if changed:
        name = f"{stamp(now)}_{canon[:12]}.json"
        path = CAPTURES / name
        CAPTURES.mkdir(parents=True, exist_ok=True)
        capture_obj = {
            "captured_at_utc": iso(now),
            "source_url": URL,
            "parser": PARSER_VERSION,
            "season": parsed["season"],
            "week": parsed["week"],
            "raw_sha256": heartbeat["raw_sha256"],
            "canonical_sha256": canon,
            "tables": parsed["tables"],
            "clubs": parsed["clubs"],
            "row_count": len(parsed["rows"]),
            "flags": heartbeat["flags"],
            "rows": parsed["rows"],
        }
        data = (json.dumps(capture_obj, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
        with path.open("xb") as fh:  # exclusive create: a capture is never overwritten
            fh.write(data)
        rel = path.relative_to(ROOT).as_posix()
        heartbeat["capture"] = rel
        entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["captures"] if MANIFEST.exists() else []
        entries.append({"file": rel, "sha256": sha256_bytes(data), "bytes": len(data),
                        "captured_at_utc": iso(now), "canonical_sha256": canon,
                        "raw_sha256": heartbeat["raw_sha256"], "rows": len(parsed["rows"]),
                        "week": parsed["week"], "season": parsed["season"]})
        write_manifest(entries)
        if previous is not None:
            delta = diff_rows(previous["rows"], parsed["rows"])
            append_jsonl(CHANGES, {"captured_at_utc": iso(now), "from": previous["captured_at_utc"],
                                   "to_capture": rel, "changes": len(delta), "delta": delta})

    append_jsonl(HEARTBEAT, heartbeat)
    print(f"capture: week={parsed['week']} season={parsed['season']} rows={len(parsed['rows'])} "
          f"clubs={len(parsed['clubs'])} changed={changed} "
          f"capture={heartbeat['capture']} flags={len(heartbeat['flags'])}")
    return 0


def append_alert(now: datetime, kind: str, message: str) -> None:
    append_jsonl(ALERTS, {"at_utc": iso(now), "kind": kind, "message": message})


def verify(max_age_hours: float) -> int:
    problems: list[str] = []
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["captures"] if MANIFEST.exists() else []
    for e in entries:
        path = ROOT / e["file"]
        if not path.exists():
            problems.append(f"missing capture file {e['file']}")
            continue
        if sha256_bytes(path.read_bytes()) != e["sha256"]:
            problems.append(f"capture changed after write: {e['file']}")
        obj = json.loads(path.read_text(encoding="utf-8"))
        if canonical_sha(obj["rows"]) != obj["canonical_sha256"]:
            problems.append(f"canonical rows do not match their recorded hash: {e['file']}")
    beats = read_jsonl(HEARTBEAT)
    if not beats:
        problems.append("no heartbeat recorded yet")
    else:
        last = beats[-1]
        last_at = datetime.strptime(last["fetched_at_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age = utc_now() - last_at
        if age > timedelta(hours=max_age_hours):
            problems.append(f"stale: last heartbeat {last['fetched_at_utc']} is {age} old "
                            f"(limit {max_age_hours} h)")
        if last.get("status") != "ok":
            problems.append(f"last run failed: {last.get('error')}")
    print(f"captures verified: {len(entries)} · heartbeats: {len(beats)}")
    for p in problems:
        print(f"PROBLEM: {p}")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("capture")
    v = sub.add_parser("verify")
    v.add_argument("--max-age-hours", type=float, default=12.0)
    args = ap.parse_args(argv)
    if args.cmd == "capture":
        return capture()
    return verify(args.max_age_hours)


if __name__ == "__main__":
    sys.exit(main())
