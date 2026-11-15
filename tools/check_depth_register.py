#!/usr/bin/env python3
"""Drift alarm for the official depth register (session d4027f66-nfl1).

FAILS the build (exit 1) when:
  * the set of clubs captured changes from the pinned set,
  * a capture's host is not the club's own domain,
  * a capture's printed-name count differs from its pin (the raw file was edited or the page
    changed: re-capture, then update the pin in this file on purpose),
  * a metadata field, required section or fetch date is missing (schema drift),
  * the committed register or comparison no longer reproduces from the captures.
REPORTS (does not fail) value anomalies, so a blank or odd cell is shown, not hidden:
  shared slots, empty gaps, continuation rows, players printed in more than one slot,
  and repo-vs-official differences.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_depth_register as bdr  # noqa: E402

# Pinned expectations. A change here is a deliberate, reviewed edit.
PINS = {
    "GB": {"domain": "packers.com", "printed_names": 55},
    "KC": {"domain": "chiefs.com", "printed_names": 60},
    "SF": {"domain": "49ers.com", "printed_names": 58},
    "SEA": {"domain": "seahawks.com", "printed_names": 63},
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main() -> int:
    failures: list[str] = []
    flags: list[str] = []
    try:
        js, tsv, cmp_js = bdr.build()
    except ValueError as exc:  # schema drift in a raw capture
        print(f"FAIL schema drift: {exc}")
        return 1
    import json
    doc = json.loads(js)
    summary = doc["summary"]["clubs"]
    rows = doc["rows"]

    if set(summary) != set(PINS):
        failures.append(f"club set {sorted(summary)} != pinned {sorted(PINS)}")
    for club, pin in PINS.items():
        if club not in summary:
            continue
        meta_url = summary[club]["source_url"]
        host = re.sub(r"^https://(www\.)?", "", meta_url).split("/")[0]
        if not host.endswith(pin["domain"]):
            failures.append(f"{club}: host {host} is not {pin['domain']}")
        if not DATE_RE.match(summary[club]["fetched"]):
            failures.append(f"{club}: fetched date {summary[club]['fetched']!r} is not YYYY-MM-DD")
        n = summary[club]["printed_names"]
        if n != pin["printed_names"]:
            failures.append(f"{club}: {n} printed names, pinned {pin['printed_names']} "
                            "(re-capture and update the pin deliberately)")
        if summary[club]["shared_slots"]:
            flags.append(f"{club}: {summary[club]['shared_slots']} shared slot(s) (two players, one printed cell)")
        if summary[club]["empty_gaps"]:
            flags.append(f"{club}: {summary[club]['empty_gaps']} empty gap(s) before a filled cell")
        if summary[club]["continuation_rows"]:
            flags.append(f"{club}: {summary[club]['continuation_rows']} continuation row(s) with no printed position label")
        for name, where in summary[club]["players_in_more_than_one_slot"].items():
            flags.append(f"{club}: {name} printed in more than one slot: {', '.join(sorted(set(where)))}")
    for r in rows:
        if not r["source_url"] or not r["fetched"]:
            failures.append(f"row without source or fetch date: {r['club']} {r['position']}")
            break

    for path, text in ((bdr.OUT_JSON, js), (bdr.OUT_TSV, tsv), (bdr.OUT_CMP, cmp_js)):
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            failures.append(f"{path.relative_to(ROOT)} is stale: run tools/build_depth_register.py")

    cmp = json.loads(cmp_js)
    for src, block in cmp.items():
        for d in block["differences"]:
            flags.append(f"repo vs official [{src}]: {d['club']} {d['position']} col {d.get('column', d.get('depth_rank'))}: "
                         f"{d.get('repo_value', d.get('player'))} -> {d['difference']}")
        for d in block.get("official_players_missing_from_repo", []):
            flags.append(f"repo omits official player [{src}]: {d['club']} {d['position']} col {d['column']}: "
                         f"{d['official_value']}")

    for f in flags:
        print(f"FLAG  {f}")
    for f in failures:
        print(f"FAIL  {f}")
    t = doc["summary"]["totals"]
    print(f"depth register: {t['clubs']} clubs, {t['printed_names']} printed names, "
          f"{t['slot_groups']} slot groups, {t['groups_with_more_than_one_rank1']} groups with >1 rank-1, "
          f"{t['cells_with_jersey_prefix_stripped']} jersey prefixes stripped")
    if failures:
        print("RESULT: FAIL")
        return 1
    print(f"RESULT: PASS ({len(flags)} flagged for review, none blocking)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
