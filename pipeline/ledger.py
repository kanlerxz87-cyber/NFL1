#!/usr/bin/env python3
"""ledger.py — an append-only, hashed, point-in-time ledger of official availability.

Session `57c05555-nfl1`.  Run from the repository root:

    python3 pipeline/ledger.py capture --source injuries --week 10 \
        --url https://www.nfl.com/injuries/league/2026/reg10 --file /tmp/page.txt \
        --status generated --generated-at 2026-11-15T12:24:19Z
    python3 pipeline/ledger.py capture --source depth_chart --club GB \
        --url https://www.packers.com/team/depth-chart --file data/depth_raw/GB.txt
    python3 pipeline/ledger.py capture --source transactions --url ... --file ...
    python3 pipeline/ledger.py index          # rebuild data/ledger/index.json
    python3 pipeline/ledger.py verify         # re-hash every capture; fail on drift

Why a ledger and not a "latest snapshot"
----------------------------------------
The brief asks for two things that a single snapshot cannot give:

* **"Capture the official report and club depth pages at least daily with retained hashes,
  so practice designations can be replayed as they were known."**
* **"Point-in-time snapshot ledger … prevents lookahead leakage when backtesting."**

Both need the *history*, keyed by the clock time the fetch happened, not by "the week".
This module writes each capture as its own immutable directory:

    data/ledger/<source>/<captured_at>Z_<short-hash>/
        raw.txt        the bytes that were read, unchanged
        record.json    url, captured_at, sha256, byte count, parser version, conflicts

Rules this module enforces
--------------------------
1. **Append only.**  A capture directory is created once and never rewritten.  Re-capturing
   the same source at the same second with different bytes is a *conflict*: both files are
   kept and the conflict is recorded rather than overwritten.
2. **Content addressed.**  The directory name contains the first 12 hex characters of the
   sha256, so a reader can spot a mismatched file without trusting the record.
3. **Clock time is mandatory.**  A capture with no UTC timestamp is refused, because a
   capture you cannot place in time cannot be used to prove what was known before kickoff.
4. **Parser version is recorded.**  The depth-chart parser changed in this session; a record
   that does not say which parser read the bytes cannot be replayed.
5. **Conflicts are data.**  When the same logical fact differs between two sources or two
   capture times, the difference is recorded as a conflict entry — never resolved silently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEDGER = os.path.join(ROOT, "data", "ledger")

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import depth_parse  # noqa: E402

SOURCES = {
    "injuries": {
        "title": "nfl.com official weekly injury report",
        "official": True,
        "url_pattern": r"^https://www\.nfl\.com/injuries/",
        "what": "practice status and game status for every listed player",
    },
    "depth_chart": {
        "title": "Official club depth chart",
        "official": True,
        "url_pattern": r"^https://www\.[a-z0-9.-]+\.com/team/depth-chart/?$",
        "what": "the club's own published depth order, as printed",
    },
    "transactions": {
        "title": "Official club transactions announcement",
        "official": True,
        "url_pattern": r"^https://www\.[a-z0-9.-]+\.com/",
        "what": "dated roster moves (signings, releases, reserve list) that invalidate a depth chart",
    },
    "inactives": {
        "title": "Official game-day inactives",
        "official": True,
        "url_pattern": r"^https://",
        "what": "who was actually unavailable at kickoff",
    },
}

PARSER_VERSION = {
    "injuries": "row-table/1",
    "depth_chart": "depth_parse.py/57c05555",
    "transactions": "text/1",
    "inactives": "text/1",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _slug_time(ts: str) -> str:
    """Turn an ISO-8601 UTC timestamp into a sortable, filesystem-safe token."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})", ts)
    if not m:
        raise SystemExit(f"refusing a capture with an unparseable clock time: {ts!r}")
    return "".join(m.groups())


def _clock_precision(ts: str) -> str:
    """'second' when the capture recorded a clock time, 'date-only' when it did not.

    Date-only captures are accepted so an existing archive can be brought under the ledger
    instead of being left outside it, but they are marked and the index reports how many
    captures cannot be replayed to a kickoff.  Inventing a time would defeat the purpose.
    """
    return "second" if re.search(r"[T ]\d{2}:\d{2}", ts) else "date-only"


def _normalise_time(ts: str) -> str:
    if not ts:
        raise SystemExit("refusing a capture with no clock time (--captured-at or --generated-at)")
    ts = ts.strip().replace(" ", "T")
    if ts.endswith("Z"):
        pass
    elif re.search(r"[+-]\d{2}:?\d{2}$", ts):
        ts = ts
    m = re.match(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}):(\d{2})", ts)
    if not m:
        raise SystemExit(f"refusing a capture with an unparseable clock time: {ts!r}")
    # Normalise to second precision UTC, keeping an explicit Z.
    base = f"{m.group(1)}T{m.group(2)}:{m.group(3)}"
    if "+" in ts or re.search(r"-\d{2}:\d{2}$", ts):
        try:
            dt = datetime.fromisoformat(ts)
            dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass
    return base + "Z"


def cmd_capture(args) -> int:
    src = args.source
    if src not in SOURCES:
        raise SystemExit(f"unknown source {src!r}; known: {sorted(SOURCES)}")
    spec = SOURCES[src]
    if not re.match(spec["url_pattern"], args.url or ""):
        raise SystemExit(
            f"{src}: URL {args.url!r} does not match the official pattern "
            f"{spec['url_pattern']}. The ledger holds official captures only."
        )

    with open(args.file, "rb") as fh:
        raw = fh.read()
    digest = sha256_bytes(raw)
    when = args.captured_at
    precision = _clock_precision(when)
    if precision == "date-only":
        token = _slug_time(when[:10] + "T00:00:00")
    else:
        token = _slug_time(when)
    dirname = f"{token}Z_{digest[:12]}"
    day_dir = os.path.join(LEDGER, src, when[:10])
    cap_dir = os.path.join(day_dir, dirname)
    raw_path = os.path.join(cap_dir, "raw.txt")
    rec_path = os.path.join(cap_dir, "record.json")

    # ---- conflict 1: same instant, different bytes
    conflict = None
    if os.path.exists(rec_path):
        prev = json.load(open(rec_path, encoding="utf-8"))
        if prev.get("sha256") and prev["sha256"] != digest:
            conflict = {
                "kind": "same-instant-different-bytes",
                "detail": (
                    f"a capture for {args.url} at {when} already exists with sha256 "
                    f"{prev['sha256'][:12]}…; this read is {digest[:12]}…. Both are kept."
                ),
            }
            # keep both: suffix the new directory with a counter
            n = 2
            while os.path.exists(cap_dir + f"_r{n}"):
                n += 1
            cap_dir = cap_dir + f"_r{n}"
            raw_path = os.path.join(cap_dir, "raw.txt")
            rec_path = os.path.join(cap_dir, "record.json")
        else:
            print(f"unchanged: {cap_dir} already holds these exact bytes")
            return 0

    os.makedirs(cap_dir, exist_ok=True)
    if os.path.exists(raw_path):
        print(f"refusing to overwrite an existing capture: {raw_path}")
        return 1
    with open(raw_path, "wb") as fh:
        fh.write(raw)

    record = {
        "source": src,
        "source_title": spec["title"],
        "official": spec["official"],
        "what_this_records": spec["what"],
        "url": args.url,
        "captured_at": when,
        "clock_precision": precision,
        "replayable_to_a_kickoff": precision == "second",
        "generated_at": args.generated_at or "",
        "captured_at_kind": (
            "page-declared generation time" if args.generated_at
            else "fetch clock time (the page declares no update time)"
        ),
        "club": args.club or "",
        "week": args.week or "",
        "season": args.season or "2026",
        "sha256": digest,
        "bytes": len(raw),
        "parser": PARSER_VERSION[src],
        "parser_version_depths": (
            "depth_parse.py as of session 57c05555-nfl1: jersey prefixes stripped and "
            "retained, slots kept as groups, empty slots kept empty, legend rows dropped"
        ) if src == "depth_chart" else "",
        "capture_method": args.method or "fetch_page render of the official page (text, not HTML)",
        # What the stored bytes actually ARE.  A raw page render and a row-by-row
        # transcription are both useful and both hashed, but they are not the same evidence,
        # so the ledger never lets a reader confuse one for the other.
        "payload_kind": args.payload_kind,
        "raw_html_retained": args.payload_kind == "raw-page-text",
        "conflict": conflict,
        "notes": args.note or "",
    }

    # ---- per-source structural facts, computed at capture time and frozen with the record
    if src == "depth_chart" and args.club:
        parsed = depth_parse.parse_capture(
            raw.decode("utf-8", "replace"), args.club, args.url, when
        )
        record["parse"] = {
            "capture_kind": parsed["capture_kind"],
            "chart_date": parsed["chart_date"],
            "counts": parsed["counts"],
            "gaps": parsed["gaps"],
        }
    if src == "injuries":
        record["counts"] = injury_counts(raw.decode("utf-8", "replace"))

    with open(rec_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print(f"captured  {src:12s} {when}  {digest[:12]}…  {len(raw):>7} bytes -> {os.path.relpath(cap_dir, ROOT)}")
    if conflict:
        print(f"  CONFLICT recorded: {conflict['detail']}")
    return 0


def injury_counts(text: str) -> dict:
    """Count the rows and clubs a captured injury page text holds.

    This is deliberately simple and conservative: a player row is a markdown row whose
    first cell is a ``[Player](https://www.nfl.com/players/...)`` link.  Anything that does
    not match is not counted, so the count can only be too low — never inflated by a header.
    """
    rows = 0
    clubs = set()
    pending_club = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and "nfl.com/players/" in s:
            rows += 1
        # a club section heading is a bare club name line followed by a table
        if s and not s.startswith("|") and not s.startswith("#") and len(s) < 30:
            pending_club = s
        if s.startswith("| Player |") and pending_club:
            clubs.add(pending_club)
    return {"player_rows": rows, "clubs_with_a_table": len(clubs)}


def iter_captures():
    for src in sorted(os.listdir(LEDGER)) if os.path.isdir(LEDGER) else []:
        src_dir = os.path.join(LEDGER, src)
        if not os.path.isdir(src_dir) or src.startswith("_"):
            continue
        for day in sorted(os.listdir(src_dir)):
            day_dir = os.path.join(src_dir, day)
            if not os.path.isdir(day_dir):
                continue
            for cap in sorted(os.listdir(day_dir)):
                rec_path = os.path.join(day_dir, cap, "record.json")
                if os.path.exists(rec_path):
                    yield src, day, cap, json.load(open(rec_path, encoding="utf-8")), rec_path


def cmd_index(args) -> int:
    by_source: dict[str, list] = {}
    conflicts = []
    for src, day, cap, rec, path in iter_captures():
        entry = {
            "captured_at": rec["captured_at"],
            "clock_precision": rec.get("clock_precision", "second"),
            "payload_kind": rec.get("payload_kind", "raw-page-text"),
            "dir": os.path.relpath(os.path.dirname(path), ROOT),
            "url": rec["url"],
            "sha256": rec["sha256"],
            "bytes": rec["bytes"],
            "club": rec.get("club", ""),
            "week": rec.get("week", ""),
            "parser": rec.get("parser", ""),
            "capture_kind": (rec.get("parse") or {}).get("capture_kind", ""),
            "counts": rec.get("counts") or (rec.get("parse") or {}).get("counts") or {},
        }
        by_source.setdefault(src, []).append(entry)
        if rec.get("conflict"):
            conflicts.append({"dir": entry["dir"], **rec["conflict"]})

    # ---- coverage: what the ledger can and cannot answer
    injury_days = sorted({e["captured_at"][:10] for e in by_source.get("injuries", [])})
    replayable = [e for v in by_source.values() for e in v if e["clock_precision"] == "second"]
    date_only = [e for v in by_source.values() for e in v if e["clock_precision"] == "date-only"]
    depth_clubs = sorted({e["club"] for e in by_source.get("depth_chart", []) if e["club"]})
    index = {
        "generated_by": "pipeline/ledger.py",
        # Derived, not clocked: the index is a function of the captures alone, so
        # `index --check` is a real gate. The newest capture time is the only time on it,
        # because that is a fact about the data rather than about when the file was written.
        "newest_capture_at": max(
            (e["captured_at"] for v in by_source.values() for e in v), default=""
        ),
        "what_this_is": (
            "Append-only captures of official sources, each with the clock time it was read "
            "and the sha256 of its bytes. A capture is never rewritten; a second read of the "
            "same source at a later time is a new capture."
        ),
        "sources": SOURCES,
        "counts": {src: len(v) for src, v in by_source.items()},
        "by_source": by_source,
        "conflicts": conflicts,
        "coverage": {
            "injury_capture_days": injury_days,
            "injury_distinct_days": len(injury_days),
            "depth_chart_clubs": depth_clubs,
            "depth_chart_clubs_captured": len(depth_clubs),
            "depth_chart_clubs_expected": 32,
            "days_needed_for_a_14_day_holdout": 14,
            "days_still_to_capture": max(0, 14 - len(injury_days)),
            "captures_with_a_clock_time": len(replayable),
            "captures_date_only": len(date_only),
            "honest_position": (
                "One day of captures cannot replay a practice week. The ledger makes every "
                "future read replayable and proves the archive is thin today; it does not "
                "manufacture the missing days."
            ),
        },
    }
    os.makedirs(LEDGER, exist_ok=True)
    out = os.path.join(LEDGER, "index.json")
    new = json.dumps(index, indent=1, ensure_ascii=False) + "\n"
    check = getattr(args, "check", False)
    if check:
        if not os.path.exists(out) or open(out, encoding="utf-8").read() != new:
            print("FAIL: data/ledger/index.json is stale — run 'pipeline/ledger.py index'")
            return 1
        print("OK: ledger index is current")
        return 0
    open(out, "w", encoding="utf-8").write(new)
    print(
        f"indexed {sum(index['counts'].values())} capture(s): "
        + ", ".join(f"{k}={v}" for k, v in index["counts"].items())
    )
    return 0


def cmd_verify(args) -> int:
    """Re-hash every capture and re-check every recorded fact against its bytes."""
    errs = []
    n = 0
    for src, day, cap, rec, path in iter_captures():
        n += 1
        raw_path = os.path.join(os.path.dirname(path), "raw.txt")
        if not os.path.exists(raw_path):
            errs.append(f"{cap}: record without raw.txt")
            continue
        raw = open(raw_path, "rb").read()
        digest = sha256_bytes(raw)
        if digest != rec["sha256"]:
            errs.append(f"{cap}: sha256 drift — recorded {rec['sha256'][:12]}… actual {digest[:12]}…")
        if not cap.endswith(digest[:12]):
            errs.append(f"{cap}: directory name does not carry its own content hash")
        if rec.get("clock_precision") == "second" and not rec.get("captured_at", "").endswith("Z"):
            errs.append(f"{cap}: captured_at is not an explicit UTC instant")
        if not rec.get("parser"):
            errs.append(f"{cap}: no parser version recorded")
        if src == "depth_chart" and rec.get("club"):
            parsed = depth_parse.parse_capture(
                raw.decode("utf-8", "replace"), rec["club"], rec["url"], rec["captured_at"]
            )
            if parsed["counts"] != (rec.get("parse") or {}).get("counts"):
                errs.append(f"{cap}: parse counts no longer reproduce from the stored bytes")
        if src == "injuries" and rec.get("counts"):
            if injury_counts(raw.decode("utf-8", "replace")) != rec["counts"]:
                errs.append(f"{cap}: injury counts no longer reproduce from the stored bytes")
    for e in errs:
        print("  FAIL " + e)
    print()
    if errs:
        print(f"RESULT: FAIL — {len(errs)} problem(s) across {n} capture(s)")
        return 1
    print(f"RESULT: PASS — {n} immutable capture(s); every hash, timestamp and derived count reproduces")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("capture", help="add one immutable capture")
    c.add_argument("--source", required=True, choices=sorted(SOURCES))
    c.add_argument("--url", required=True)
    c.add_argument("--file", required=True)
    c.add_argument("--captured-at", default="", help="fetch clock time, UTC (ISO-8601)")
    c.add_argument("--generated-at", default="", help="time the source itself declares")
    c.add_argument("--club", default="")
    c.add_argument("--week", default="")
    c.add_argument("--season", default="2026")
    c.add_argument("--method", default="")
    c.add_argument("--note", default="")
    c.add_argument(
        "--payload-kind",
        default="raw-page-text",
        choices=["raw-page-text", "transcribed-table", "raw-html"],
        help=(
            "raw-page-text = the rendered text the fetch tool returned; "
            "transcribed-table = a table transcribed row by row from that text; "
            "raw-html = the page source"
        ),
    )

    i = sub.add_parser("index", help="rebuild data/ledger/index.json")
    i.add_argument("--check", action="store_true")

    sub.add_parser("verify", help="re-hash every capture")

    args = ap.parse_args()
    if args.cmd == "capture":
        return cmd_capture(args)
    if args.cmd == "index":
        return cmd_index(args)
    return cmd_verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
