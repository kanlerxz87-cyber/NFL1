#!/usr/bin/env python3
"""Offline structural verifier for the 2026 NFL Week 11 venue capture.

Run from any working directory:

    python3 tools/verify_week11_venues_3738d9f0.py

The official NFL pages were read with Arena's page-fetch tool and transcribed row by row.
This tool does NOT fetch the live web pages. It validates the saved transcriptions, checks
that every current Week 11 schedule row has exactly one matching Game Center venue row,
checks all row-level provenance links and timestamps, and records hashes of its inputs.
A PASS means those offline checks pass; it is not a claim that this script independently
re-read the live pages. Venue naming differences recorded in the data are review flags,
not silently normalized values.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "data" / "official" / "2026-11-15"
SCHEDULE_PATH = CAPTURE / "week11_schedule_2026-11-15.tsv"
VENUES_PATH = CAPTURE / "week11_game_centres.tsv"
SOURCES_PATH = CAPTURE / "sources_venues_2026-11-15.json"
RESULT_PATH = CAPTURE / "week11_venue_verification_3738d9f0.json"
SCHEDULE_URL = "https://www.nfl.com/schedules/2026/by-week/week-11"

SCHEDULE_FIELDS = [
    "week", "game", "away", "home", "gameday_display", "kickoff_et_display",
    "network", "game_center_url", "schedule_url", "audit_recorded_at_utc",
]
VENUE_FIELDS = [
    "week", "game", "away", "home", "location_as_displayed",
    "stadium_as_displayed", "venue_name_review", "game_center_url",
    "schedule_url", "audit_recorded_at_utc",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
            raise ValueError(f"{path.relative_to(ROOT)} line {line_no} has a malformed row")
    return rows


def official_nfl_url(value: str, path_prefix: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "www.nfl.com"
        and parsed.path.startswith(path_prefix)
        and not parsed.username
        and not parsed.password
    )


def run() -> dict:
    checks: list[dict[str, str]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "result": "PASS" if passed else "FAIL", "detail": detail})

    metadata = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    schedule = read_tsv(SCHEDULE_PATH, SCHEDULE_FIELDS)
    venues = read_tsv(VENUES_PATH, VENUE_FIELDS)
    audit_at = metadata["audit_recorded_at_utc"]

    check("metadata audit timestamp", bool(audit_at) and audit_at.endswith("Z"), audit_at)
    check(
        "schedule capture timestamp consistency",
        all(row["audit_recorded_at_utc"] == audit_at for row in schedule),
        f"{sum(row['audit_recorded_at_utc'] == audit_at for row in schedule)}/{len(schedule)} rows",
    )
    check(
        "venue capture timestamp consistency",
        all(row["audit_recorded_at_utc"] == audit_at for row in venues),
        f"{sum(row['audit_recorded_at_utc'] == audit_at for row in venues)}/{len(venues)} rows",
    )
    check("13 official schedule rows", len(schedule) == 13, f"rows={len(schedule)}")
    check("13 Game Center venue rows", len(venues) == 13, f"rows={len(venues)}")

    schedule_games = [row["game"] for row in schedule]
    venue_games = [row["game"] for row in venues]
    check("unique schedule game keys", len(schedule_games) == len(set(schedule_games)),
          f"unique={len(set(schedule_games))} rows={len(schedule_games)}")
    check("unique venue game keys", len(venue_games) == len(set(venue_games)),
          f"unique={len(set(venue_games))} rows={len(venue_games)}")
    check("schedule/venue matchup coverage", set(schedule_games) == set(venue_games),
          f"schedule-only={sorted(set(schedule_games) - set(venue_games))}; "
          f"venue-only={sorted(set(venue_games) - set(schedule_games))}")

    schedule_by_game = {row["game"]: row for row in schedule}
    venue_by_game = {row["game"]: row for row in venues}
    pairing_mismatches: list[str] = []
    source_mismatches: list[str] = []
    missing_schedule_values: list[str] = []
    missing_venue_values: list[str] = []
    bad_timestamps: list[str] = []
    teams: list[str] = []

    for game, row in schedule_by_game.items():
        if row["week"] != "11" or row["game"] != f"{row['away']}@{row['home']}":
            pairing_mismatches.append(f"schedule {game}: week={row['week']} away={row['away']} home={row['home']}")
        if row["schedule_url"] != SCHEDULE_URL or not official_nfl_url(row["schedule_url"], "/schedules/"):
            source_mismatches.append(f"schedule {game}: invalid schedule URL")
        if not official_nfl_url(row["game_center_url"], "/games/") or "2026-reg-11" not in urlparse(row["game_center_url"]).path:
            source_mismatches.append(f"schedule {game}: invalid Game Center URL")
        if not row["gameday_display"] or not row["kickoff_et_display"] or not row["network"]:
            missing_schedule_values.append(game)
        teams.extend((row["away"], row["home"]))

    for game, row in venue_by_game.items():
        if row["week"] != "11" or row["game"] != f"{row['away']}@{row['home']}":
            pairing_mismatches.append(f"venue {game}: week={row['week']} away={row['away']} home={row['home']}")
        scheduled = schedule_by_game.get(game)
        if scheduled and (row["away"], row["home"]) != (scheduled["away"], scheduled["home"]):
            pairing_mismatches.append(f"venue {game}: away/home differ from schedule capture")
        if row["schedule_url"] != SCHEDULE_URL or not official_nfl_url(row["schedule_url"], "/schedules/"):
            source_mismatches.append(f"venue {game}: invalid schedule URL")
        if not official_nfl_url(row["game_center_url"], "/games/") or "2026-reg-11" not in urlparse(row["game_center_url"]).path:
            source_mismatches.append(f"venue {game}: invalid Game Center URL")
        if scheduled and row["game_center_url"] != scheduled["game_center_url"]:
            source_mismatches.append(f"venue {game}: Game Center URL differs from schedule capture")
        if not row["location_as_displayed"] or not row["stadium_as_displayed"]:
            # An unresolved value can stay blank, but only when the row carries a review note.
            if not row["venue_name_review"]:
                missing_venue_values.append(game)
        if not row["audit_recorded_at_utc"].endswith("Z"):
            bad_timestamps.append(game)

    check("schedule game/week keys", not pairing_mismatches, "; ".join(pairing_mismatches) or "all rows are Week 11 away@home records")
    check("26 unique scheduled clubs", len(set(teams)) == 26, f"unique clubs={len(set(teams))}")
    check("official row provenance links", not source_mismatches, "; ".join(source_mismatches) or "all schedule and Game Center URLs use official nfl.com pages")
    check("schedule date/time/network populated", not missing_schedule_values,
          f"missing={sorted(missing_schedule_values)}")
    check("venue fields present or explicitly review-flagged", not missing_venue_values,
          f"unflagged blank venue fields={sorted(missing_venue_values)}")
    check("UTC audit timestamps", not bad_timestamps, f"invalid rows={sorted(bad_timestamps)}")

    review_rows = {
        game: row for game, row in venue_by_game.items() if row["venue_name_review"].strip()
    }
    metadata_reviews = {row["game"]: row for row in metadata.get("venue_name_review_rows", [])}
    review_consistent = set(review_rows) == set(metadata_reviews)
    review_details: list[str] = []
    for game, review in metadata_reviews.items():
        row = venue_by_game.get(game)
        if not row:
            review_consistent = False
            review_details.append(f"{game}: metadata review has no venue row")
            continue
        if review["game_center_label"] != row["stadium_as_displayed"]:
            review_consistent = False
            review_details.append(f"{game}: Game Center label differs")
        if review["schedule_page_hotel_link_destination"] not in row["venue_name_review"]:
            review_consistent = False
            review_details.append(f"{game}: schedule-page discrepancy missing from row")
        if review.get("status") != "needs review":
            review_consistent = False
            review_details.append(f"{game}: metadata status is not needs review")
    check("venue-name review flags are preserved", review_consistent,
          f"flagged={sorted(review_rows)}; " + ("; ".join(review_details) or "row and metadata notes agree"))

    result = {
        "audit_id": metadata["audit_id"],
        "audit_recorded_at_utc": audit_at,
        "result": "PASS" if all(item["result"] == "PASS" for item in checks) else "FAIL",
        "summary": {
            "schedule_rows": len(schedule),
            "venue_rows": len(venues),
            "matched_games": len(set(schedule_games) & set(venue_games)),
            "unique_clubs": len(set(teams)),
            "venue_name_review_flags": sorted(review_rows),
        },
        "checks": checks,
        "input_sha256": {
            SCHEDULE_PATH.name: sha256(SCHEDULE_PATH),
            VENUES_PATH.name: sha256(VENUES_PATH),
            SOURCES_PATH.name: sha256(SOURCES_PATH),
        },
        "limitations": [
            "Offline structural check only; live NFL pages are not fetched by this script.",
            "Official page text was manually transcribed via Arena fetch_page; response-specific timestamps and raw page bodies were not available for archival.",
            "Venue-name flags preserve differing labels from the official Game Center and the official schedule page's hotel-search link; no canonical name was inferred.",
        ],
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    try:
        result = run()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
