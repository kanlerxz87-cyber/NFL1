#!/usr/bin/env python3
"""Render and validate the official Week 10 Game Book source index.

The register stores links to official NFL Game Center pages and the Game Book PDFs linked
there. It does not download/re-host PDFs or invent starter, inactive, or snap-count rows.
The normal Referee page wrapper and table helpers are injected by build_site.py so this page
uses the same styles and navigation as the rest of the Referee sub-site.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "data" / "gamebooks_week10_2026.json"

EXPECTED_ROWS = 14
PLAYER_FIELDS = ("actual_starters", "official_inactives", "snap_counts")


def load_register() -> dict:
    return json.loads(REGISTER_PATH.read_text(encoding="utf-8"))


def validate_register(register: dict) -> list[str]:
    """Return schema/provenance failures; no network calls are made."""
    problems: list[str] = []
    if register.get("schema_version") != 1:
        problems.append("schema_version must be 1")
    if register.get("observed_on_utc_date") != "2026-11-16":
        problems.append("observed_on_utc_date must reflect the dated source read")
    if register.get("observed_at_utc") is not None:
        problems.append("exact fetch time must remain blank because the tool did not provide it")
    schedule = register.get("schedule_url", "")
    parsed_schedule = urlparse(schedule)
    if (parsed_schedule.scheme != "https" or parsed_schedule.hostname != "www.nfl.com"
            or parsed_schedule.path != "/schedules/2026/by-week/week-10"):
        problems.append("schedule_url must be the official NFL 2026 Week 10 schedule page")

    rows = register.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_ROWS:
        problems.append(f"rows must contain {EXPECTED_ROWS} Week 10 fixtures")
        rows = rows if isinstance(rows, list) else []
    ids = [row.get("game_id") for row in rows]
    if len(set(ids)) != len(ids):
        problems.append("game_id values must be unique")

    final_rows = [row for row in rows if row.get("state_at_observation") == "final"]
    scheduled_rows = [row for row in rows if row.get("state_at_observation") == "scheduled"]
    linked_rows = [row for row in rows if row.get("gamebook_link_state") == "listed_on_official_game_center"]
    parsed_rows = [row for row in rows if row.get("gamebook_content_parsed") is True]
    summary = register.get("summary", {})
    expected_counts = {
        "scheduled_fixtures": len(rows),
        "final_fixtures_at_observation": len(final_rows),
        "official_gamebook_links_observed": len(linked_rows),
        "scheduled_not_final_at_observation": len(scheduled_rows),
        "gamebook_pdfs_parsed": len(parsed_rows),
        "starter_lists_transcribed": sum(row.get("actual_starters") is not None for row in rows),
        "inactive_lists_transcribed": sum(row.get("official_inactives") is not None for row in rows),
        "snap_count_tables_transcribed": sum(row.get("snap_counts") is not None for row in rows),
    }
    for key, expected in expected_counts.items():
        if summary.get(key) != expected:
            problems.append(f"summary.{key} is {summary.get(key)!r}; expected {expected}")

    if len(final_rows) != 13 or len(scheduled_rows) != 1 or len(linked_rows) != 13:
        problems.append("expected 13 completed/link-listed games and one scheduled fixture")

    attempt = register.get("pdf_fetch_attempt")
    if not isinstance(attempt, dict):
        problems.append("pdf_fetch_attempt must record the failed direct fetch")
    else:
        attempted_game = next((row for row in rows if row.get("game_id") == attempt.get("game_id")), None)
        if attempted_game is None:
            problems.append("pdf_fetch_attempt.game_id must identify a registered fixture")
        elif attempt.get("url") != attempted_game.get("gamebook_pdf_url"):
            problems.append("pdf_fetch_attempt.url must match that fixture's observed official PDF link")
        if attempt.get("method") != "direct_fetch_page":
            problems.append("pdf_fetch_attempt.method must preserve the observed retrieval method")
        if attempt.get("result") != "Failed to fetch page":
            problems.append("pdf_fetch_attempt.result must preserve the observed fetch failure")
        if attempt.get("content_parsed") is not False:
            problems.append("a failed fetch must not imply PDF content was parsed")

    seen_matchups: set[tuple[str, str]] = set()
    for index, row in enumerate(rows, start=1):
        prefix = f"row {index} ({row.get('game_id', 'missing id')})"
        if not row.get("away_team") or not row.get("home_team"):
            problems.append(f"{prefix}: both official team names are required")
        matchup = (row.get("away_team"), row.get("home_team"))
        if matchup in seen_matchups:
            problems.append(f"{prefix}: duplicate matchup")
        seen_matchups.add(matchup)
        try:
            date.fromisoformat(row.get("date", ""))
        except (TypeError, ValueError):
            problems.append(f"{prefix}: date must be ISO YYYY-MM-DD")
        if not row.get("venue") or not row.get("location"):
            problems.append(f"{prefix}: venue and location must be populated from the game center")
        game_center = row.get("game_center_url", "")
        parsed_center = urlparse(game_center)
        if (parsed_center.scheme != "https" or parsed_center.hostname != "www.nfl.com"
                or not parsed_center.path.startswith("/games/")):
            problems.append(f"{prefix}: game_center_url must point to an official HTTPS NFL Game Center")

        if row.get("state_at_observation") == "final":
            pdf_url = row.get("gamebook_pdf_url")
            parsed_pdf = urlparse(pdf_url or "")
            if (parsed_pdf.scheme != "https" or parsed_pdf.hostname != "static.www.nfl.com"
                    or not parsed_pdf.path.endswith(".pdf")):
                problems.append(f"{prefix}: completed game needs its observed official HTTPS PDF link")
            if row.get("gamebook_link_state") != "listed_on_official_game_center":
                problems.append(f"{prefix}: completed game must be marked as link-listed")
        elif row.get("state_at_observation") == "scheduled":
            if row.get("gamebook_pdf_url") is not None:
                problems.append(f"{prefix}: scheduled fixture must not have an unobserved PDF URL")
            if row.get("gamebook_link_state") != "not_checked_pending_game":
                problems.append(f"{prefix}: scheduled fixture must be marked pending, not missing")
        else:
            problems.append(f"{prefix}: unknown state_at_observation")

        if row.get("gamebook_content_parsed") is not False:
            problems.append(f"{prefix}: unparsed PDF content must not be reported as parsed")
        for field in PLAYER_FIELDS:
            if field not in row:
                problems.append(f"{prefix}: {field} must be present as a blank unverified value")
            elif row[field] is not None:
                problems.append(f"{prefix}: {field} must stay blank until verified from an official source")

    return problems


def build_gamebooks_page(*, page, table, tiles, e, a, chip, as_of: str) -> None:
    """Render gamebooks.html using the existing Referee page wrapper."""
    register = load_register()
    problems = validate_register(register)
    if problems:
        raise ValueError("Invalid Game Book source register:\n- " + "\n- ".join(problems))

    rows = []
    for row in register["rows"]:
        is_final = row["state_at_observation"] == "final"
        pdf_link = (a(row["gamebook_pdf_url"], "Official Game Book PDF")
                    if row["gamebook_pdf_url"] else chip("", "Pending final game"))
        status = (chip("warn", "Final at observation · PDF not parsed") if is_final
                  else chip("", "Scheduled at observation"))
        source = (a(row["game_center_url"], "NFL Game Center") + " · " +
                  a(register["schedule_url"], "NFL Week 10 schedule"))
        rows.append([
            e(row["date"]),
            f"{e(row['away_team'])} at {e(row['home_team'])}<br><span class=\"small\">{e(row['game_id'])}</span>",
            f"{e(row['venue'])}<br><span class=\"small\">{e(row['location'])}</span>",
            pdf_link,
            "",  # actual starters are intentionally unreported
            "",  # official inactives are intentionally unreported
            "",  # snap counts are intentionally unreported
            status,
            source,
        ])

    summary = register["summary"]
    attempt = register["pdf_fetch_attempt"]
    attempted_game = next(row for row in register["rows"] if row["game_id"] == attempt["game_id"])
    fetch_note = (
        "One direct fetch attempt for " +
        a(attempt["url"], f"{attempted_game['away_team']} at {attempted_game['home_team']} Game Book PDF") +
        " returned “" + e(attempt["result"]) + "”. " +
        "No PDF content was parsed. A link listing is not proof of the PDF contents."
    )
    body = [
        '<p class="eyebrow">Official evidence · point-in-time source index</p>',
        "<h1>Official Game Book source index</h1>",
        '<p class="lede">A source-discovery pilot for the 2026 regular-season Week 10 fixtures. '
        'Every fixture row links to its official NFL Game Center; completed games link to the '
        'Game Book PDF exposed there. Link presence is verified, PDF contents are not.</p>',
        tiles([
            ("warn", f"{summary['official_gamebook_links_observed']} / {summary['scheduled_fixtures']}",
             "completed-game Game Book links observed on NFL Game Center pages"),
            ("idle", str(summary["gamebook_pdfs_parsed"]), "PDF contents parsed in this session"),
            ("idle", str(summary["starter_lists_transcribed"]), "starter lists transcribed"),
            ("idle", str(summary["inactive_lists_transcribed"] + summary["snap_count_tables_transcribed"]),
             "inactive lists or snap-count tables transcribed"),
        ]),
        '<div class="note bad"><p><strong>Not a verified starters/inactives/snap-count dataset.</strong> '
        'All three value columns below are deliberately blank. The official Game Center page exposes '
        'a Game Book link, but this session did not parse any PDF. ' + fetch_note + '</p></div>',
        '<div class="note"><p><strong>Capture limitation.</strong> The source pages were read on '
        f"{e(register['observed_on_utc_date'])}. The fetch tool did not expose a clock time, so the "
        'exact UTC time is left blank in the JSON register. No raw PDF is stored. NFL publication '
        'terms/permission review is still open; see <a href="flagged.html#R-18">Flag R-18</a>.</p></div>',
        '<h2>Week 10 fixtures and evidence</h2>',
        table([
            ("Date", "nw"), ("Matchup", "w"), ("Game Center venue", "w"),
            ("Game Book PDF", "w"), ("Actual starters", "w"), ("Official inactives", "w"),
            ("Snap counts", "w"), ("Status at observation", ""), ("Source", "m"),
        ], rows, "Source: NFL.com Week 10 schedule and the per-game NFL Game Center page linked in each row."),
        '<p class="small">Blank player-data cells do not mean “available”, “no inactives”, or '
        '“zero snaps”. They mean that no such value was verified from the Game Book in this session. '
        'The sole scheduled fixture is marked pending, not missing.</p>',
        '<h2>How this clears the source-discovery gate</h2>',
        '<ul class="plain">'
        '<li><strong>Found:</strong> official Game Center pages expose a “Download Game Book (PDF)” '
        'link for the 13 fixtures already marked final on the official schedule page.</li>'
        '<li><strong>Still blocked:</strong> zero of those PDFs were parsed here; actual starters, '
        'game-day status, and snap counts remain blank. The pending Chargers–Ravens fixture had not '
        'finished at the observation date.</li>'
        '<li><strong>Next gate:</strong> confirm the permitted storage/processing policy, retrieve '
        'a Game Book through an authorized route, and independently match one parsed game against '
        'the official schedule and dated availability evidence before scaling to the full corpus.</li>'
        '</ul>',
        '<p class="small">Machine-readable register: '
        '<a href="data/gamebooks_week10_2026.json">gamebooks_week10_2026.json</a>. '
        'Official schedule: ' + a(register["schedule_url"], "NFL.com Week 10") + ".</p>",
    ]
    page("gamebooks.html", "Official Game Book source index", "\n".join(body), as_of)


if __name__ == "__main__":
    errors = validate_register(load_register())
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: {len(load_register()['rows'])} source-linked fixture rows; no player-level values inferred")
