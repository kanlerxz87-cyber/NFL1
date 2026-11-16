#!/usr/bin/env python3
"""Gate for the dated schedule announcement page (task IN-31).

Fails (exit 1) when any of these is true:
  * a row has no https link to an official NFL domain (nfl.com or media.nfl.com);
  * the fixture count is not 13 or the bye count is not 6 (13 x 2 + 6 = 32 clubs);
  * a day-of-week printed on the page does not match the calendar date;
  * the derived UTC time for the release is not 8 p.m. EDT converted to UTC;
  * the live fixtures disagree with data/prereg/official/week11_2026_schedule.json;
  * the committed index.html differs from what the builder produces from the JSON;
  * an empty table cell exists in the page.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "schedule_announcement" / "schedule_announcement.json"
PREREG = ROOT / "data" / "prereg" / "official" / "week11_2026_schedule.json"
PAGE = ROOT / "schedule_announcement" / "index.html"
OFFICIAL_HOSTS = {"www.nfl.com", "nfl.com", "media.nfl.com"}
MONTHS = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6, "July": 7,
          "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def is_official(url):
    p = urlparse(url)
    return p.scheme == "https" and p.netloc in OFFICIAL_HOSTS


def check_links(d, problems):
    a = d["announcement"]
    for key in ("official_url", "mirror_url", "release_page_url"):
        if not is_official(a[key]):
            problems.append(f"announcement.{key} is not an official https link: {a[key]}")
    for r in a["rows"]:
        if not is_official(r["source_url"]):
            problems.append(f"row {r['id']} has no official https link")
    for f in d["live_schedule"]["fixtures"]:
        if not is_official(f["official_url"]):
            problems.append(f"fixture {f['matchup']} has no official https link")
    if not is_official(d["live_schedule"]["official_url"]):
        problems.append("live schedule URL is not official")


def parse_day(text):
    """'Thursday, November 19th' -> date(2026, 11, 19)."""
    m = re.match(r"(\w+), (\w+) (\d+)(st|nd|rd|th)$", text)
    if not m:
        return None, None
    return m.group(1), dt.date(2026, MONTHS[m.group(2)], int(m.group(3)))


def check_calendar(d, problems):
    for f in d["live_schedule"]["fixtures"]:
        wd, date = parse_day(f["day"])
        if date is None:
            problems.append(f"unparseable day '{f['day']}' for {f['matchup']}")
            continue
        if WEEKDAYS[date.weekday()] != wd:
            problems.append(f"{f['matchup']}: '{f['day']}' is a {WEEKDAYS[date.weekday()]}")
    # Release arithmetic: Thu 14 May 2026 8 p.m. EDT (UTC-4) -> 00:00 UTC on 15 May.
    edt = dt.timezone(dt.timedelta(hours=-4))
    release = dt.datetime(2026, 5, 14, 20, 0, tzinfo=edt)
    if release.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") != "2026-05-15T00:00:00Z":
        problems.append("release time UTC conversion is wrong")
    if WEEKDAYS[dt.date(2026, 5, 14).weekday()] != "Thursday":
        problems.append("14 May 2026 is not a Thursday")
    if d["announcement"]["rows"][0].get("derived_utc") != "2026-05-15T00:00:00Z":
        problems.append("row A1 derived_utc does not match the arithmetic")


def check_against_prereg(d, problems):
    """Compare the live read with the earlier transcription (independent file, same official URL)."""
    if not PREREG.exists():
        problems.append("prereg transcription missing; cannot cross-check")
        return
    p = json.loads(PREREG.read_text(encoding="utf-8"))
    live = {(f["matchup"], f["day"], f["kickoff_et"], f["network"]) for f in d["live_schedule"]["fixtures"]}
    prior = set()
    for g in p["games"]:
        matchup = g["matchup"].replace(" (Mexico City)", "")
        prior.add((matchup, g["day"], g["kickoff_local_as_printed"], g["network"]))
    if live != prior:
        problems.append(f"live fixtures differ from prereg transcription: "
                        f"only live {sorted(live - prior)}, only prereg {sorted(prior - live)}")
    live_byes = {b.replace("LAR", "LA") for b in d["live_schedule"]["teams_on_bye"]}
    prior_byes = {b["feed"] for b in p["byes"]}
    if live_byes != prior_byes:
        problems.append(f"byes differ: live {sorted(live_byes)} vs prereg {sorted(prior_byes)}")


def check_counts(d, problems):
    n = len(d["live_schedule"]["fixtures"])
    b = len(d["live_schedule"]["teams_on_bye"])
    if n != 13:
        problems.append(f"expected 13 Week 11 fixtures, found {n}")
    if b != 6:
        problems.append(f"expected 6 teams on bye, found {b}")
    if 2 * n + b != 32:
        problems.append("13 x 2 + 6 != 32 clubs")


def check_page(d, problems):
    sys.path.insert(0, str(ROOT / "schedule_announcement"))
    import build  # noqa: E402  (local module, no side effects on import)
    expected = build.build_html(d)
    if not PAGE.exists():
        problems.append("schedule_announcement/index.html missing")
        return
    if PAGE.read_text(encoding="utf-8") != expected:
        problems.append("schedule_announcement/index.html differs from the builder output; run build.py")
    if re.search(r"<td>\s*</td>", expected):
        problems.append("empty table cell in page")


def run():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    problems = []
    check_links(d, problems)
    check_counts(d, problems)
    check_calendar(d, problems)
    check_against_prereg(d, problems)
    check_page(d, problems)
    return d, problems


def main():
    d, problems = run()
    if problems:
        print(f"schedule announcement gate: {len(problems)} problem(s)")
        for p in problems:
            print("  -", p)
        return 1
    rows = len(d["announcement"]["rows"]) + len(d["live_schedule"]["fixtures"]) + len(d["live_schedule"]["teams_on_bye"])
    print(f"schedule announcement gate: PASS ({len(d['announcement']['rows'])} announcement rows, "
          f"{len(d['live_schedule']['fixtures'])} fixtures, {len(d['live_schedule']['teams_on_bye'])} byes, {rows} cells checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
