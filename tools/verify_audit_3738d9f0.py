#!/usr/bin/env python3
"""Offline verifier for session 3738d9f0's dated NFL source captures.

Run from any directory:

    python3 tools/verify_audit_3738d9f0.py

This is an offline comparator. It checks the saved 2026-11-15 standings transcription
against the read-only model snapshot, the saved Week 11 schedule against model fixtures,
and a complete, same-day 347-row Week 10 injury transcription against the refreshed,
read-only injury snapshot. It also validates the earlier twelve-row spot-check capture.
It does not fetch live NFL pages.
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
LIVE_INJURY_CAPTURE_PATH = (
    ROOT / "data" / "brief_07810d9f" / "live_read_2026-11-15_week10.psv"
)
LIVE_INJURY_DELTA_PATH = (
    ROOT / "data" / "brief_07810d9f" / "injury_delta_2026-11-15.json"
)
RESULT_PATH = CAPTURE / "official_audit_3738d9f0.json"

STANDINGS_URL = "https://www.nfl.com/standings/league/2026/reg"
SCHEDULE_URL = "https://www.nfl.com/schedules/2026/by-week/week-11"
INJURY_URL = "https://www.nfl.com/injuries/"
# The official standings/schedule pages use AZ for Arizona; the model uses ARI.
# Preserve source values in each capture and normalize only comparison keys.
OFFICIAL_TO_MODEL_CODE = {"AZ": "ARI"}
# The injury report uses AZ and LAR while the model uses ARI and LA.
INJURY_TO_MODEL_CODE = {"AZ": "ARI", "LAR": "LA"}
LIVE_INJURY_FIELDS = ["team", "player", "position", "injury", "practice", "game"]
LIVE_PRACTICE_LABELS = {
    "FULL": "Full Participation in Practice",
    "LIM": "Limited Participation in Practice",
    "DNP": "Did Not Participate In Practice",
    "": None,
}
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


def read_live_injury_capture(path: Path) -> list[dict[str, str]]:
    """Read the full hand-transcribed NFL report, whose column names are in comments."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not any("Source: https://www.nfl.com/injuries/" in line for line in lines):
        raise ValueError(f"{path.relative_to(ROOT)} is missing its official source URL")
    if not any("Columns: team|player|position|injury|practice|game" in line for line in lines):
        raise ValueError(f"{path.relative_to(ROOT)} is missing its documented columns")
    data_lines = [line for line in lines if line.strip() and not line.startswith("#")]
    reader = csv.DictReader(data_lines, fieldnames=LIVE_INJURY_FIELDS, delimiter="|", strict=True)
    rows = list(reader)
    for line_no, row in enumerate(rows, start=1):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"{path.relative_to(ROOT)} data row {line_no} is malformed")
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
    standings_captured_at = metadata["standings_capture_recorded_at_utc"]
    schedule_captured_at = metadata["schedule_capture_recorded_at_utc"]
    injury_spotchecks_captured_at = metadata["injury_spotcheck_recorded_at_utc"]
    standings = read_tsv(STANDINGS_PATH, STANDINGS_FIELDS)
    schedule = read_tsv(SCHEDULE_PATH, SCHEDULE_FIELDS)
    injury_samples = read_tsv(INJURIES_PATH, INJURY_FIELDS)
    live_injuries = read_live_injury_capture(LIVE_INJURY_CAPTURE_PATH)
    live_injury_delta = json.loads(LIVE_INJURY_DELTA_PATH.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    injury_model = json.loads(INJURY_MODEL_PATH.read_text(encoding="utf-8"))
    checks: list[dict[str, str]] = []
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str) -> None:
        status = "PASS" if ok else "FAIL"
        checks.append({"check": name, "result": status, "detail": detail})
        if not ok:
            failures.append(f"{name}: {detail}")

    audit_at = metadata["audit_recorded_at_utc"]
    check("audit timestamp", audit_at.endswith("Z"), audit_at)
    fresh_page_reread = metadata.get("fresh_page_reread", {})
    check("fresh Week 10 page reread provenance",
          fresh_page_reread.get("source_url") == INJURY_URL
          and fresh_page_reread.get("retrieved_on_utc_date") == "2026-11-15"
          and fresh_page_reread.get("chunks_read") == "8/8",
          f"date={fresh_page_reread.get('retrieved_on_utc_date')} "
          f"chunks={fresh_page_reread.get('chunks_read')}")
    recorded_aliases = metadata.get("comparison_code_aliases", {})
    check("comparison-only team aliases documented",
          recorded_aliases.get("standings_schedule_official_to_model") == OFFICIAL_TO_MODEL_CODE
          and recorded_aliases.get("injury_report_official_to_model") == INJURY_TO_MODEL_CODE,
          f"standings_schedule={recorded_aliases.get('standings_schedule_official_to_model')} "
          f"injury={recorded_aliases.get('injury_report_official_to_model')}")
    check(
        "standings source links and timestamps",
        all(row["source_url"] == STANDINGS_URL
            and is_official_url(row["source_url"], "/standings/")
            and row["audit_recorded_at_utc"] == standings_captured_at for row in standings),
        f"valid={sum(row['source_url'] == STANDINGS_URL and row['audit_recorded_at_utc'] == standings_captured_at for row in standings)}/{len(standings)}",
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
        and row["audit_recorded_at_utc"] == schedule_captured_at
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

    live_read = live_injury_delta.get("live_read", {})
    live_summary = live_injury_delta.get("summary", {})
    expected_live_path = LIVE_INJURY_CAPTURE_PATH.relative_to(ROOT).as_posix()
    full_capture_provenance_ok = (
        live_read.get("source_url") == INJURY_URL
        and live_read.get("file") == expected_live_path
        and "chunks 0-7 of 8" in live_read.get("method", "")
        and live_read.get("read_on_utc", "").startswith("2026-11-15T")
    )
    check("full injury transcript provenance", full_capture_provenance_ok,
          f"source={live_read.get('source_url')} read_at={live_read.get('read_on_utc')} "
          f"capture={live_read.get('file')}")
    check("full Week 10 injury transcription row count",
          len(live_injuries) == live_summary.get("live_rows") == 347,
          f"transcribed={len(live_injuries)} source_delta={live_summary.get('live_rows')}")

    raw_live_keys = [(row["team"], row["player"]) for row in live_injuries]
    check("unique full live injury keys", len(raw_live_keys) == len(set(raw_live_keys)),
          f"unique={len(set(raw_live_keys))}/{len(raw_live_keys)}")
    live_injuries_by_key = {
        (INJURY_TO_MODEL_CODE.get(row["team"], row["team"]), row["player"]): row
        for row in live_injuries
    }
    model_rows = injury_model.get("rows", [])
    model_injuries = {(row["team"], row["player"]): row for row in model_rows}
    model_counts = injury_model.get("counts", {})
    check("model injury snapshot count metadata",
          model_counts.get("rows") == len(model_rows)
          and model_counts.get("teams") == len({row["team"] for row in model_rows}),
          f"rows={model_counts.get('rows')} actual={len(model_rows)} "
          f"teams={model_counts.get('teams')} actual={len({row['team'] for row in model_rows})}")
    live_keys = set(live_injuries_by_key)
    model_keys = set(model_injuries)
    live_only_keys = sorted(live_keys - model_keys)
    model_only_keys = sorted(model_keys - live_keys)
    check("unique injury model keys", len(model_keys) == len(model_rows),
          f"unique={len(model_keys)}/{len(model_rows)}")
    check("unique full live keys after team aliases", len(live_keys) == len(live_injuries),
          f"unique={len(live_keys)}/{len(live_injuries)}")
    check("full live injury key coverage", not live_only_keys and not model_only_keys,
          f"live={len(live_keys)} model={len(model_keys)} "
          f"live-only={live_only_keys} model-only={model_only_keys}")

    injury_mismatches: list[dict[str, object]] = []
    invalid_practice_labels = sorted({
        row["practice"] for row in live_injuries
        if row["practice"] not in LIVE_PRACTICE_LABELS
    })
    for key in sorted(live_keys & model_keys):
        source = live_injuries_by_key[key]
        model = model_injuries[key]
        observed_fields = {
            "position": source["position"] or None,
            "injury": source["injury"] or None,
            "practice": LIVE_PRACTICE_LABELS.get(source["practice"], source["practice"]),
            "game": source["game"] or None,
        }
        for field, observed in observed_fields.items():
            if observed != model.get(field):
                injury_mismatches.append({
                    "team": key[0], "source_team_code": source["team"],
                    "player": key[1], "field": field,
                    "official_transcription": observed, "model": model.get(field),
                })
    check("supported live practice labels", not invalid_practice_labels,
          f"unsupported={invalid_practice_labels}")
    check("full injury row-by-row field comparison", not injury_mismatches,
          f"matched_keys={len(live_keys & model_keys)} field_mismatches={len(injury_mismatches)}")

    check("12 injury spot-check rows", len(injury_samples) == 12,
          f"rows={len(injury_samples)}")
    injury_sample_keys = [(row["team"], row["player"]) for row in injury_samples]
    check("unique injury spot-check keys",
          len(injury_sample_keys) == len(set(injury_sample_keys)),
          f"unique={len(set(injury_sample_keys))}")
    injury_sample_mismatches: list[dict[str, object]] = []
    injury_sample_source_ok = True
    for row in injury_samples:
        key = (INJURY_TO_MODEL_CODE.get(row["team"], row["team"]), row["player"])
        source = live_injuries_by_key.get(key)
        model = model_injuries.get(key)
        if source is None or model is None:
            injury_sample_mismatches.append({
                "team": key[0], "player": key[1], "field": "row",
                "detail": "missing from full transcript or model snapshot",
            })
            continue
        for source_field, sample_field, model_field in (
            ("position", "position", "position"),
            ("injury", "injury", "injury"),
            ("practice", "practice_status", "practice"),
            ("game", "game_status", "game"),
        ):
            source_value = source[source_field]
            if source_field == "practice":
                source_value = LIVE_PRACTICE_LABELS.get(source_value, source_value)
            observed = source_value or None
            sample_value = row[sample_field] or None
            model_value = model.get(model_field)
            if observed != sample_value or observed != model_value:
                injury_sample_mismatches.append({
                    "team": key[0], "player": key[1], "field": sample_field,
                    "full_transcription": observed, "spot_check": sample_value,
                    "model": model_value,
                })
        if (row["player_url"] or None) != model.get("player_url"):
            injury_sample_mismatches.append({
                "team": key[0], "player": key[1], "field": "player_url",
                "spot_check": row["player_url"], "model": model.get("player_url"),
            })
        injury_sample_source_ok &= (
            row["report_url"] == INJURY_URL
            and is_official_url(row["report_url"], "/injuries/")
            and is_official_url(row["player_url"], "/players/")
            and row["audit_recorded_at_utc"] == injury_spotchecks_captured_at
        )
    check("injury spot-check source links and timestamps",
          injury_sample_source_ok,
          f"valid={sum(row['report_url'] == INJURY_URL and row['audit_recorded_at_utc'] == injury_spotchecks_captured_at for row in injury_samples)}/{len(injury_samples)}")
    check("injury spot-check rows agree with full capture and model",
          not injury_sample_mismatches,
          f"mismatches={len(injury_sample_mismatches)}")

    model_injury_rows = len(model_rows)
    injury_boundary = metadata["injury_capture_boundary"]
    remaining_unmatched_rows = len(model_keys - live_keys)
    injury_boundary_ok = (
        injury_boundary.get("status") == "complete"
        and injury_boundary.get("live_rows_transcribed") == len(live_injuries)
        and injury_boundary.get("live_rows_compared_to_model") == len(live_keys & model_keys)
        and injury_boundary.get("model_snapshot_rows") == model_injury_rows
        and injury_boundary.get("model_rows_without_live_match") == remaining_unmatched_rows
        and injury_boundary.get("field_mismatches") == len(injury_mismatches)
        and injury_boundary.get("live_page_total_row_count_independently_recounted") is True
        and injury_boundary.get("full_capture_path") == expected_live_path
    )
    check("complete injury capture boundary recorded",
          injury_boundary_ok,
          f"transcribed={len(live_injuries)} model={model_injury_rows} "
          f"model_rows_without_live_match={remaining_unmatched_rows}")

    review_flags: list[dict[str, str]] = []
    hard_failures = [item for item in checks if item["result"] == "FAIL"]
    result = {
        "audit_id": metadata["audit_id"],
        "audit_recorded_at_utc": audit_at,
        "result": "FAIL" if hard_failures else "PASS_WITH_REVIEW" if review_flags else "PASS",
        "summary": {
            "standings_rows": len(standings),
            "standings_matches": len(standings) if not standing_mismatches and not missing_standing_codes else len(standings) - len(standing_mismatches),
            "schedule_rows": len(schedule),
            "schedule_matches": len(schedule) if schedule_coverage and not schedule_mismatches else len(schedule) - len(schedule_mismatches),
            "injury_live_rows_transcribed": len(live_injuries),
            "injury_model_snapshot_rows": model_injury_rows,
            "injury_rows_matched_by_team_and_player": len(live_keys & model_keys),
            "injury_live_rows_only": len(live_only_keys),
            "injury_model_rows_only": len(model_only_keys),
            "injury_field_mismatches": len(injury_mismatches),
            "injury_model_rows_not_independently_checked": remaining_unmatched_rows,
            "injury_rows_spot_checked": len(injury_samples),
            "review_flags": review_flags,
        },
        "live_injury_transcription": {
            "path": expected_live_path,
            "source_url": INJURY_URL,
            "read_at_utc": live_read.get("read_on_utc"),
            "chunks_read": "8/8",
            "rows": len(live_injuries),
        },
        "comparison_code_aliases": {
            "standings_schedule_official_to_model": OFFICIAL_TO_MODEL_CODE,
            "injury_report_official_to_model": INJURY_TO_MODEL_CODE,
            "note": "Official values remain unchanged in the captures; aliases are applied only to comparison keys.",
        },
        "checks": checks,
        "mismatches": {
            "standings": standing_mismatches,
            "schedule": schedule_mismatches,
            "injury_live_only_keys": live_only_keys,
            "injury_model_only_keys": model_only_keys,
            "injury_full_capture_fields": injury_mismatches,
            "injury_spot_checks": injury_sample_mismatches,
        },
        "league_totals": {"w": league_w, "l": league_l, "t": league_t, "pf": league_pf, "pa": league_pa},
        "input_sha256": {
            STANDINGS_PATH.name: sha256(STANDINGS_PATH),
            SCHEDULE_PATH.name: sha256(SCHEDULE_PATH),
            INJURIES_PATH.name: sha256(INJURIES_PATH),
            LIVE_INJURY_CAPTURE_PATH.relative_to(ROOT).as_posix(): sha256(LIVE_INJURY_CAPTURE_PATH),
            LIVE_INJURY_DELTA_PATH.relative_to(ROOT).as_posix(): sha256(LIVE_INJURY_DELTA_PATH),
            METADATA_PATH.name: sha256(METADATA_PATH),
            SNAPSHOT_PATH.name: sha256(SNAPSHOT_PATH),
            INJURY_MODEL_PATH.name: sha256(INJURY_MODEL_PATH),
        },
        "limitations": [
            "Offline verifier only; it does not fetch NFL pages. The official Week 10 injury page was re-read via fetch_page in all 8/8 chunks on 2026-11-15.",
            "The full 347-row hand transcription was captured earlier the same day at the timestamp recorded in the source delta and is checked against the refreshed 2026-11-15T12:38:01Z model snapshot; the model files were read-only.",
            "The page-fetch tool did not provide raw page bodies or exact per-response timestamps; the full row transcription and source-delta metadata are preserved, but raw HTML is not archived.",
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
