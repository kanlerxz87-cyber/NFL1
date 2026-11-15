#!/usr/bin/env python3
"""Offline verifier for session 3738d9f0's dated NFL source captures.

Run from any directory:

    python3 tools/verify_audit_3738d9f0.py

This is an offline comparator. It checks the saved 2026-11-15 standings transcription
against the read-only model snapshot, the saved Week 11 schedule against model fixtures,
and twelve explicitly transcribed Week 10 injury-report rows against the read-only injury
snapshot. It does not fetch live NFL pages. It reports the injury audit as partial rather
than claiming that the remaining rows were verified.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "data" / "official" / "2026-11-15"
STANDINGS_PATH = CAPTURE / "standings_2026-11-15.tsv"
SCHEDULE_PATH = CAPTURE / "week11_schedule_2026-11-15.tsv"
INJURIES_PATH = CAPTURE / "injury_spotchecks_2026-11-15.tsv"
METADATA_PATH = CAPTURE / "sources_audit_2026-11-15.json"
SNAPSHOT_PATH = ROOT / "data" / "model" / "snapshot.json"
INJURY_MODEL_PATH = ROOT / "data" / "model" / "official_injuries.json"
RESULT_PATH = CAPTURE / "official_audit_3738d9f0.json"

STANDINGS_URL = "https://www.nfl.com/standings/league/2026/reg"
SCHEDULE_URL = "https://www.nfl.com/schedules/2026/by-week/week-11"
INJURY_URL = "https://www.nfl.com/injuries/"
# The official NFL pages use AZ for Arizona; this repository's model uses ARI.
# Preserve the official value in the capture and normalize only the comparison key.
OFFICIAL_TO_MODEL_CODE = {"AZ": "ARI"}
STANDINGS_FIELDS = [
    "team", "team_name_as_displayed", "w", "l", "t", "pct", "pf", "pa",
    "net", "source_url", "audit_recorded_at_utc",
]
SCHEDULE_FIELDS = [
    "week", "game", "away", "home", "gameday_display", "kickoff_et_display",
    "network", "game_center_url", "schedule_url", "audit_recorded_at_utc",
]
INJURY_FIELDS = [
    "team", "player", "position", "injury", "practice_status", "game_status",
    "player_url", "report_url", "audit_recorded_at_utc",
]


def read_tsv(path: Path, expected_fields: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if reader.fieldnames != expected_fields:
            raise ValueError(
                f"{path.relative_to(ROOT)} header mismatch: {reader.fieldnames!r}; "
                f"expected {expected_fields!r}"
            )
        rows = list(reader)
    for line_no, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"{path.relative_to(ROOT)} line {line_no} is malformed")
    return rows


def is_official_url(value: str, path_prefix: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "www.nfl.com"
        and parsed.path.startswith(path_prefix)
        and not parsed.username
        and not parsed.password
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_schedule_date(value: str) -> tuple[str, str]:
    match = re.fullmatch(r"([A-Za-z]+), ([A-Za-z]+) (\d{1,2})(?:st|nd|rd|th)", value.strip())
    if not match:
        raise ValueError(f"unrecognized schedule date display: {value!r}")
    weekday, month, day = match.groups()
    date = datetime.strptime(f"2026 {month} {day}", "%Y %B %d").date()
    if date.strftime("%A") != weekday:
        raise ValueError(f"weekday/date disagreement in {value!r}")
    return date.isoformat(), weekday


def run() -> dict:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    captured_at = metadata["audit_recorded_at_utc"]
    standings = read_tsv(STANDINGS_PATH, STANDINGS_FIELDS)
    schedule = read_tsv(SCHEDULE_PATH, SCHEDULE_FIELDS)
    injury_samples = read_tsv(INJURIES_PATH, INJURY_FIELDS)
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    injury_model = json.loads(INJURY_MODEL_PATH.read_text(encoding="utf-8"))
    checks: list[dict[str, str]] = []
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str) -> None:
        status = "PASS" if ok else "FAIL"
        checks.append({"check": name, "result": status, "detail": detail})
        if not ok:
            failures.append(f"{name}: {detail}")

    check("audit timestamp", captured_at.endswith("Z"), captured_at)
    check(
        "standings source links and timestamps",
        all(row["source_url"] == STANDINGS_URL
            and is_official_url(row["source_url"], "/standings/")
            and row["audit_recorded_at_utc"] == captured_at for row in standings),
        f"valid={sum(row['source_url'] == STANDINGS_URL and row['audit_recorded_at_utc'] == captured_at for row in standings)}/{len(standings)}",
    )
    check("32 standings rows", len(standings) == 32, f"rows={len(standings)}")
    standing_codes = [row["team"] for row in standings]
    check("unique standings team codes", len(standing_codes) == len(set(standing_codes)),
          f"unique={len(set(standing_codes))}")

    snapshot_standings = {row["team"]: row for row in snapshot.get("standings", [])}
    transcribed_standings = {
        OFFICIAL_TO_MODEL_CODE.get(row["team"], row["team"]): row for row in standings
    }
    missing_standing_codes = sorted(set(snapshot_standings) ^ set(transcribed_standings))
    standing_mismatches: list[dict[str, object]] = []
    for model_team in sorted(set(snapshot_standings) & set(transcribed_standings)):
        official = transcribed_standings[model_team]
        model = snapshot_standings[model_team]
        source_team = official["team"]
        fields = ("w", "l", "t", "pf", "pa")
        for field in fields:
            if int(official[field]) != int(model[field]):
                standing_mismatches.append({"team": model_team, "source_team_code": source_team,
                                            "field": field, "official": official[field],
                                            "model": model[field]})
        if Decimal(official["pct"]) != Decimal(str(model["pct"])):
            standing_mismatches.append({"team": model_team, "source_team_code": source_team,
                                        "field": "pct", "official": official["pct"],
                                        "model": model["pct"]})
        if int(official["net"]) != int(model["diff"]):
            standing_mismatches.append({"team": model_team, "source_team_code": source_team,
                                        "field": "net", "official": official["net"],
                                        "model": model["diff"]})
    check("standings team coverage", not missing_standing_codes,
          f"symmetric difference after documented AZ→ARI comparison alias={missing_standing_codes}")
    check("standings row-by-row comparison", not standing_mismatches,
          f"field mismatches={len(standing_mismatches)}")

    league_w = sum(int(row["w"]) for row in standings)
    league_l = sum(int(row["l"]) for row in standings)
    league_t = sum(int(row["t"]) for row in standings)
    league_pf = sum(int(row["pf"]) for row in standings)
    league_pa = sum(int(row["pa"]) for row in standings)
    check("standings league totals balance", league_w == league_l and league_pf == league_pa,
          f"W={league_w} L={league_l} T={league_t} PF={league_pf} PA={league_pa}")

    check("13 schedule rows", len(schedule) == 13, f"rows={len(schedule)}")
    schedule_games = [row["game"] for row in schedule]
    check("unique schedule matchup keys", len(schedule_games) == len(set(schedule_games)),
          f"unique={len(set(schedule_games))}")
    schedule_source_ok = all(
        row["week"] == "11"
        and row["game"] == f"{row['away']}@{row['home']}"
        and row["schedule_url"] == SCHEDULE_URL
        and is_official_url(row["schedule_url"], "/schedules/")
        and is_official_url(row["game_center_url"], "/games/")
        and "2026-reg-11" in urlparse(row["game_center_url"]).path
        and row["audit_recorded_at_utc"] != ""
        for row in schedule
    )
    check("schedule row provenance and keys", schedule_source_ok,
          "each Week 11 row has official schedule and direct Game Center links")

    fixture_rows = [row for row in snapshot.get("fixtures", []) if int(row.get("week", -1)) == 11]
    fixture_by_game = {(row["away"], row["home"]): row for row in fixture_rows}
    schedule_by_game = {
        (OFFICIAL_TO_MODEL_CODE.get(row["away"], row["away"]),
         OFFICIAL_TO_MODEL_CODE.get(row["home"], row["home"])): row
        for row in schedule
    }
    schedule_coverage = set(fixture_by_game) == set(schedule_by_game)
    schedule_mismatches: list[dict[str, object]] = []
    for pair in sorted(set(fixture_by_game) & set(schedule_by_game)):
        model = fixture_by_game[pair]
        source = schedule_by_game[pair]
        try:
            date, weekday = parse_schedule_date(source["gameday_display"])
            kickoff = datetime.strptime(source["kickoff_et_display"], "%I:%M %p").strftime("%H:%M")
        except ValueError as exc:
            schedule_mismatches.append({"game": source["game"], "field": "parse", "detail": str(exc)})
            continue
        for field, observed, expected in (
            ("gameday", date, model["gameday"]),
            ("weekday", weekday, model["weekday"]),
            ("gametime", kickoff, model["gametime"]),
        ):
            if observed != expected:
                schedule_mismatches.append({"game": source["game"], "field": field,
                                            "official": observed, "model": expected})
    check("schedule fixture coverage", schedule_coverage,
          f"source={len(schedule_by_game)} model={len(fixture_by_game)} after documented "
          f"AZ→ARI comparison alias; source-only={sorted(set(schedule_by_game) - set(fixture_by_game))}; "
          f"model-only={sorted(set(fixture_by_game) - set(schedule_by_game))}")
    check("schedule date/time row-by-row comparison", not schedule_mismatches,
          f"field mismatches={len(schedule_mismatches)}")

    check("12 injury spot-check rows", len(injury_samples) == 12,
          f"rows={len(injury_samples)}")
    injury_keys = [(row["team"], row["player"]) for row in injury_samples]
    check("unique injury spot-check keys", len(injury_keys) == len(set(injury_keys)),
          f"unique={len(set(injury_keys))}")
    model_injuries = {(row["team"], row["player"]): row for row in injury_model.get("rows", [])}
    injury_mismatches: list[dict[str, object]] = []
    injury_sources_ok = True
    injury_timestamp_ok = True
    for row in injury_samples:
        key = (row["team"], row["player"])
        model = model_injuries.get(key)
        if model is None:
            injury_mismatches.append({"team": key[0], "player": key[1], "field": "row", "detail": "missing from model snapshot"})
            continue
        for capture_field, model_field in (
            ("position", "position"), ("injury", "injury"),
            ("practice_status", "practice"), ("game_status", "game"),
            ("player_url", "player_url"),
        ):
            observed = row[capture_field] or None
            expected = model.get(model_field)
            if observed != expected:
                injury_mismatches.append({"team": key[0], "player": key[1],
                                          "field": capture_field, "official": observed,
                                          "model": expected})
        injury_sources_ok &= (
            row["report_url"] == INJURY_URL
            and is_official_url(row["report_url"], "/injuries")
            and is_official_url(row["player_url"], "/players/")
        )
        injury_timestamp_ok &= row["audit_recorded_at_utc"] == captured_at
    check("injury spot-check source links and timestamps", injury_sources_ok and injury_timestamp_ok,
          f"valid={sum(row['report_url'] == INJURY_URL and row['audit_recorded_at_utc'] == captured_at for row in injury_samples)}/{len(injury_samples)}")
    check("injury spot-check comparison", not injury_mismatches,
          f"field mismatches={len(injury_mismatches)}")

    model_injury_rows = len(injury_model.get("rows", []))
    unreviewed_model_rows = max(0, model_injury_rows - len(injury_samples))
    check("injury incompleteness is explicitly recorded",
          metadata["injury_capture_boundary"].get("status", "").startswith("partial")
          and metadata["injury_capture_boundary"].get("live_rows_transcribed_and_compared") == len(injury_samples)
          and metadata["injury_capture_boundary"].get("remaining_model_rows_not_independently_transcribed_from_the_2026-11-15_live_page") == unreviewed_model_rows,
          f"spot_checked={len(injury_samples)} model_rows={model_injury_rows} not independently checked={unreviewed_model_rows}")

    review_flags = [{
        "id": "INJURY-LIVE-ROW-COVERAGE",
        "status": "needs review",
        "detail": f"Only {len(injury_samples)}/{model_injury_rows} model injury rows were independently transcribed and compared with the current live report; {unreviewed_model_rows} remain unverified. The model total is not claimed as the official live-page row count.",
        "source_url": INJURY_URL,
    }]
    hard_failures = [item for item in checks if item["result"] == "FAIL"]
    result = {
        "audit_id": metadata["audit_id"],
        "audit_recorded_at_utc": captured_at,
        "result": "FAIL" if hard_failures else "PASS_WITH_REVIEW",
        "summary": {
            "standings_rows": len(standings),
            "standings_matches": len(standings) if not standing_mismatches and not missing_standing_codes else len(standings) - len(standing_mismatches),
            "schedule_rows": len(schedule),
            "schedule_matches": len(schedule) if schedule_coverage and not schedule_mismatches else len(schedule) - len(schedule_mismatches),
            "injury_rows_spot_checked": len(injury_samples),
            "injury_model_snapshot_rows": model_injury_rows,
            "injury_model_rows_not_independently_checked": unreviewed_model_rows,
            "review_flags": review_flags,
        },
        "comparison_code_aliases": {
            "official_to_model": OFFICIAL_TO_MODEL_CODE,
            "note": "Official values remain unchanged in the TSV; AZ→ARI is applied only to the comparison key.",
        },
        "checks": checks,
        "mismatches": {
            "standings": standing_mismatches,
            "schedule": schedule_mismatches,
            "injury_spot_checks": injury_mismatches,
        },
        "league_totals": {"w": league_w, "l": league_l, "t": league_t, "pf": league_pf, "pa": league_pa},
        "input_sha256": {
            STANDINGS_PATH.name: sha256(STANDINGS_PATH),
            SCHEDULE_PATH.name: sha256(SCHEDULE_PATH),
            INJURIES_PATH.name: sha256(INJURIES_PATH),
            METADATA_PATH.name: sha256(METADATA_PATH),
            SNAPSHOT_PATH.name: sha256(SNAPSHOT_PATH),
            INJURY_MODEL_PATH.name: sha256(INJURY_MODEL_PATH),
        },
        "limitations": [
            "Offline verifier only; it does not fetch NFL pages.",
            "Standings and Week 11 fixtures are fully transcribed and compared; the Week 10 injury report has only the twelve listed rows checked against the live page.",
            "The remaining live injury rows were not independently transcribed from the 2026-11-15 responses. No full live-page injury row-count or full row-match claim is made.",
            "The page-fetch tool did not provide raw page bodies or exact response timestamps; audit timestamps identify the recorded transcript, not an HTTP response instant.",
        ],
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    try:
        result = run()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["result"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
