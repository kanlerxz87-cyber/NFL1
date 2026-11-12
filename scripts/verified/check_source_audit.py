#!/usr/bin/env python3
"""Read-only provenance gate for the independently transcribed NFL snapshots.

Run from the repository root with:
    PYTHONPATH=src python3 scripts/verified/check_source_audit.py

A source inconsistency is a visible FLAG, not a build failure. A FAIL, missing
or unregistered row source, incorrect source tier, or unpublished flag blocks
CI. This keeps known official-page irregularities reviewable without silently
turning them into values.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from nfl import ingest, verify  # noqa: E402


def _https_url(url: object) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.hostname)


def _row_name(row: dict) -> str:
    return str(row.get("team_abbr") or row.get("player") or row.get("headline") or "?")


def audit() -> tuple[list[str], dict]:
    problems: list[str] = []
    source_doc = ingest.sources()
    sources = source_doc.get("sources", [])
    source_by_url = {s.get("url"): s for s in sources if isinstance(s, dict)}
    registered_urls = set(source_by_url)

    # The source register is itself held to its declared authority tier.
    for source in sources:
        url = source.get("url")
        tier = source.get("tier")
        if not _https_url(url):
            problems.append(f"source register: {source.get('id', '?')} has no HTTPS URL")
            continue
        host = (urlparse(url).hostname or "").lower()
        if tier == "OFFICIAL" and host not in {"nfl.com", "www.nfl.com"}:
            problems.append(f"source register: {source.get('id', '?')} is marked OFFICIAL but host is {host}")
        elif tier == "OFFICIAL_PARTNER_CREDENTIAL_GATED" and host != "developer.sportradar.com":
            problems.append(f"source register: {source.get('id', '?')} has an unexpected official-partner host {host}")
        elif tier == "COMMUNITY_MIRROR" and host != "github.com":
            problems.append(f"source register: {source.get('id', '?')} has an unexpected community-mirror host {host}")

    # Each snapshot row must point to a registered source, with the mirror
    # allowed only for its explicitly non-on-field team-label/reference data.
    datasets = (
        ("standings", ingest.standings(), "source_url", "OFFICIAL"),
        ("schedule fixtures", ingest.schedule(), "source_url", "OFFICIAL"),
        ("bye list", ingest.byes(), "source_url", "OFFICIAL"),
        ("team report status", ingest.team_report_status(), "source_url", "OFFICIAL"),
        ("injury report", ingest.injuries(), "source_url", "OFFICIAL"),
        ("official news", ingest.news(), "url", "OFFICIAL"),
        ("team reference", ingest.teams_reference(), "source_url", "COMMUNITY_MIRROR"),
    )
    for dataset, rows, url_field, expected_tier in datasets:
        for row in rows:
            row_urls = row.get("source_urls") or [row.get(url_field)]
            for url in row_urls:
                label = f"{dataset} row {_row_name(row)}"
                if not _https_url(url):
                    problems.append(f"{label}: missing or non-HTTPS source URL")
                    continue
                source = source_by_url.get(url)
                if source is None:
                    problems.append(f"{label}: source URL is absent from data/verified/sources.json: {url}")
                elif source.get("tier") != expected_tier:
                    problems.append(f"{label}: expected source tier {expected_tier}, found {source.get('tier')}")
                if dataset == "bye list" and url != ingest.WEEK10_SCHEDULE_URL:
                    problems.append(f"{label}: byes must cite the official NFL Week 10 schedule, not {url}")
            if dataset == "schedule fixtures":
                required_sources = {ingest.WEEK10_SCHEDULE_URL, ingest.INJURY_REPORT_URL}
                if row.get("source_url") != ingest.WEEK10_SCHEDULE_URL:
                    problems.append(f"{dataset} row {_row_name(row)}: primary source must be the official schedule")
                if not required_sources <= set(row_urls):
                    problems.append(f"{dataset} row {_row_name(row)}: missing schedule or broadcast metadata source")
            if (dataset == "team report status"
                    and row.get("report_status") == "on bye (no report)"
                    and ingest.WEEK10_SCHEDULE_URL not in row_urls):
                problems.append(f"{dataset} row {_row_name(row)}: bye status lacks the official schedule source")

    report = verify.run()
    counts = Counter(c.get("result") for c in report.get("checks", []))
    if report.get("total") != len(report.get("checks", [])):
        problems.append("verification report total does not match the number of check rows")
    for result in ("PASS", "FLAG", "FAIL"):
        if report.get(result) != counts.get(result, 0):
            problems.append(f"verification report {result} count does not match the check rows")

    allowed_results = {"PASS", "FLAG", "FAIL"}
    for check in report.get("checks", []):
        label = f"verification check {check.get('check_id', '?')}"
        if check.get("result") not in allowed_results:
            problems.append(f"{label} has an unknown result {check.get('result')!r}")
        row_urls = check.get("source_urls") or [check.get("source_url")]
        for url in row_urls:
            if not _https_url(url):
                problems.append(f"{label}: missing or non-HTTPS source URL")
            elif url not in registered_urls:
                problems.append(f"{label}: source URL is absent from the source register: {url}")
        if check.get("result") == "FAIL":
            problems.append(f"{label} failed: {check.get('scope')}")

    # Fixture and bye checks must cite the official NFL schedule directly.
    schedule_check_ids = {"V14", "V15", "V16", "V17", "V18", "V29", "V33"}
    checks_by_id = {c.get("check_id"): c for c in report.get("checks", [])}
    for check_id in sorted(schedule_check_ids):
        check = checks_by_id.get(check_id)
        if check is None:
            problems.append(f"verification report is missing {check_id} (official schedule check)")
        elif check.get("source_url") != ingest.WEEK10_SCHEDULE_URL:
            problems.append(f"{check_id} does not link to the official NFL Week 10 schedule")

    for flag in report.get("flags", []):
        url = flag.get("source_url")
        if not _https_url(url) or url not in registered_urls:
            problems.append(f"flag {flag.get('team_abbr', '?')}:{flag.get('field', '?')} lacks a registered HTTPS source")

    # Known source-level flags are non-blocking only if the published review
    # page exposes their identities and source links.
    flagged_path = ingest.ROOT / "verified-lab" / "flagged.html"
    if not flagged_path.is_file():
        problems.append("verified-lab/flagged.html is missing")
    else:
        page = flagged_path.read_text(encoding="utf-8")
        for flag in report.get("flags", []):
            for token in (flag.get("team_abbr"), flag.get("field"), flag.get("source_url")):
                if token and token not in page:
                    problems.append(f"flagged page does not publish {flag.get('team_abbr')}:{flag.get('field')} token {token}")
        for check in report.get("checks", []):
            if check.get("result") == "FLAG" and check.get("check_id") not in page:
                problems.append(f"flagged page does not list verification flag {check.get('check_id')}")

    return problems, report


def main() -> int:
    problems, report = audit()
    print("Independent official-source snapshot audit")
    print(f"{report['total']} checks: {report['PASS']} PASS / {report['FLAG']} FLAG / {report['FAIL']} FAIL")
    for check in report["checks"]:
        urls = check.get("source_urls") or [check["source_url"]]
        print(f"  [{check['result']}] {check['check_id']} {check['scope']} — {'; '.join(urls)}")
    print(f"Source rows checked: standings, schedule fixtures, byes, team report status, "
          f"injuries, official news and the explicitly-labelled team reference.")
    if problems:
        print("\nPROBLEMS:")
        for problem in problems:
            print(f" - {problem}")
        return 1
    print("No FAILs; all published source rows and non-blocking flags have registered provenance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
