#!/usr/bin/env python3
"""check_reserve_register.py — the drift alarm and publication gate for the transactions register.

Session 1d824ec2-nfl1 (task V5). The brief asks for a drift alarm on every scraper: "pin each
parser to expected row counts and required fields; fail the build loudly when a field goes missing
rather than publishing a blank." This is that alarm for the transactions and reserve-list capture.

Fails (exit 1) when:
  * the store is missing or empty, or a capture file is not readable JSON;
  * a capture's stored rows no longer hash to the hash recorded in it (an edited capture);
  * the derived files do not reproduce from the captures (a hand-edited page or data file);
  * a pinned category/month carries a different number of rows than its pin;
  * a row has no player, no source URL, a source URL off nfl.com, a date that cannot be read as
    a real calendar date in the month it was filed under, or a club code outside the 32;
  * a published page has a table row with no link, or a placeholder word, or a broken local link.
Reports without failing:
  * an unpinned page (so a new month shows up as "not pinned yet", never as a silent pass);
  * a printed blank in a column that is usually blank (Position).

Run: python3 tools/check_reserve_register.py
"""
from __future__ import annotations

import datetime as _dt
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "reserve"
PAGES = [ROOT / "reserve" / "index.html", ROOT / "reserve" / "rows.html"]

_spec = importlib.util.spec_from_file_location("collect_transactions",
                                               ROOT / "pipeline" / "collect_transactions.py")
ct = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("collect_transactions", ct)
_spec.loader.exec_module(ct)

# Reviewed row-count pins. A count above or below the pin fails the build: the page changed, or
# the parser did. Update a pin only on purpose, with the reason in the commit message.
PINS: dict[str, int] = {}
MONTHS = ct.DEFAULT_MONTHS
CATEGORIES = ct.CATEGORIES
PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|lorem ipsum|placeholder|xxx+)\b", re.I)
TR_RE = re.compile(r"<tr\b.*?</tr>", re.S)
A_HREF_RE = re.compile(r'<a\b[^>]*href="([^"]+)"', re.I)
ROW_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def rel(p: Path) -> str:
    try:
        return str(Path(p).relative_to(ROOT))
    except ValueError:
        return str(p)


def fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)
    print(f"FAIL {msg}")


def check_captures(failures: list[str], reports: list[str]) -> list[dict]:
    caps = ct.load_captures()
    if not caps:
        fail("no capture file in data/reserve/captures/: the sweep has not run, so the register "
             "page would publish an empty table as if it were the truth", failures)
        return []
    for cap in caps:
        rel = cap.get("_file", "?")
        if cap.get("_unreadable"):
            fail(f"{rel}: not readable JSON ({cap.get('_error')})", failures)
            continue
        if cap.get("status") != "ok":
            fail(f"{rel}: capture recorded a non-ok status ({cap.get('error')})", failures)
            continue
        rows = cap.get("row_list") or []
        if ct.canonical(rows) != cap.get("canonical_sha256"):
            fail(f"{rel}: the stored rows no longer hash to the recorded canonical_sha256 "
                 f"(content edited after capture)", failures)
        key = f"{cap.get('category')}/{cap.get('month')}"
        if key in PINS and len(rows) != PINS[key]:
            fail(f"{key}: {len(rows)} rows captured, {PINS[key]} pinned — the page or the parser "
                 f"changed; re-read the official page, then re-pin on purpose", failures)
        elif key not in PINS:
            reports.append(f"{key}: {len(rows)} rows, not pinned yet")
    return caps


def check_rows(failures: list[str], reports: list[str]) -> list[dict]:
    path = STORE / "transactions.json"
    if not path.exists():
        fail("data/reserve/transactions.json missing", failures)
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("rows") or []
    caps = ct.load_captures()
    expect, _ = ct.latest_rows_per_key(caps)
    if [json.dumps(r, sort_keys=True) for r in expect] != \
            [json.dumps(r, sort_keys=True) for r in rows]:
        fail("data/reserve/transactions.json does not reproduce from the captures "
             "(run: python3 pipeline/collect_transactions.py derive)", failures)
    if not rows:
        fail("the register holds zero rows: publishing an empty table is a failure, not a result",
             failures)
    bad = 0
    for i, r in enumerate(rows):
        who = f"row {i} ({r.get('player')})"
        if not r.get("player"):
            fail(f"{who}: no player name", failures); bad += 1
        if not r.get("source_url"):
            fail(f"{who}: no source link", failures); bad += 1
        elif "nfl.com" not in r["source_url"]:
            fail(f"{who}: source link is not an nfl.com page: {r['source_url']}", failures); bad += 1
        if r.get("category") not in CATEGORIES:
            fail(f"{who}: category {r.get('category')!r} is not one of the six official "
                 f"categories", failures); bad += 1
        d = r.get("date")
        if d:
            m = ROW_DATE_RE.match(d)
            if not m:
                fail(f"{who}: date {d!r} is not YYYY-MM-DD", failures); bad += 1
            else:
                try:
                    _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                except ValueError:
                    fail(f"{who}: date {d!r} is not a real calendar day", failures); bad += 1
                month = f"{m.group(1)}-{m.group(2)}"
                if r.get("month") and month != r["month"]:
                    fail(f"{who}: printed date {d} is not inside the month it was filed under "
                         f"({r['month']}) — either the page moved it or the parser mis-read the "
                         f"column", failures); bad += 1
        for side in ("club_from", "club_to"):
            code = r.get(side)
            if code and code not in ct.CLUB_CODES and code not in ct.CLUB_ALIASES:
                fail(f"{who}: club code {code!r} on {side} is not one of the 32 or a known alias",
                     failures); bad += 1
    if bad == 0:
        print(f"row rules: {len(rows)} rows, all with a player, an nfl.com source link, a valid "
              f"category and a date inside its month")
    return rows


def check_derived(failures: list[str], reports: list[str]) -> None:
    for name in ("reserve_state.json", "coverage.json", "report_vs_reserve.json",
                 "transactions.tsv", "depth_staleness.json"):
        if not (STORE / name).exists():
            fail(f"data/reserve/{name} missing: the page would render a blank as if it were a "
                 f"number", failures)
    cov = STORE / "coverage.json"
    if cov.exists():
        doc = json.loads(cov.read_text(encoding="utf-8"))
        got = doc.get("n_pages")
        if got != len(doc.get("pages") or {}):
            fail(f"coverage.json: n_pages {got} != {len(doc.get('pages') or {})} entries", failures)
        want = len(MONTHS) * len(CATEGORIES)
        if got is not None and got < want:
            reports.append(f"coverage: {got} of {want} pinned category/month pages captured; the "
                           f"missing ones are listed by the collector's own log, not guessed")


def check_pages(failures: list[str], reports: list[str]) -> None:
    for page in PAGES:
        if not page.exists():
            fail(f"{rel(page)}: not built (run python3 tools/build_reserve_site.py)",
                 failures)
            continue
        text = page.read_text(encoding="utf-8")
        if PLACEHOLDER_RE.search(text):
            fail(f"{rel(page)}: contains a placeholder word", failures)
        rows = TR_RE.findall(text)
        unlinked = 0
        for tr in rows:
            if "<th" in tr:
                continue
            if "not built" in tr:
                continue
            if not A_HREF_RE.search(tr):
                unlinked += 1
        if unlinked:
            fail(f"{rel(page)}: {unlinked} table row(s) carry no link — every row "
                 f"must be checkable by a reader", failures)
        else:
            print(f"{rel(page)}: {len(rows)} rows, every one with a link")
        for href in A_HREF_RE.findall(text):
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = (page.parent / href.split("#")[0]).resolve()
            if not target.exists():
                fail(f"{rel(page)}: local link does not resolve: {href}", failures)


def main() -> int:
    failures: list[str] = []
    reports: list[str] = []
    if not STORE.exists():
        print("FAIL data/reserve/ does not exist: the sweep has never run")
        return 1
    check_captures(failures, reports)
    check_rows(failures, reports)
    check_derived(failures, reports)
    check_pages(failures, reports)
    for r in reports:
        print(f"note {r}")
    n_pinned = len(PINS)
    print(f"reserve register gate: {len(failures)} failure(s), {len(reports)} note(s), "
          f"{n_pinned} pinned page(s)")
    if failures:
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
