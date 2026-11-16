#!/usr/bin/env python3
"""venue/build.py — "Venues & Weather" sub-site (session cc5a9cdd).

Design rules enforced, not aspirational:
  1. Every table row carries at least one official https source link; the build fails
     loudly otherwise (data rows are never published unlinked).
  2. A value that could not be confirmed renders as an explicit UNVERIFIED / FLAGGED
     cell that links venue/flagged.html. It is never silently omitted, never invented,
     and never replaced by a guess from a third-party dataset.
  3. Deterministic: the page stamp is derived from the data files' own read_at values,
     so rebuilding reproduces the committed bytes exactly.

Data (all under data/session-cc5a9cdd/):
  venue_week10.json          Week-10 venue transcription (official nfl.com game centres)
  venue_week11.json          Week-11 venue transcription (official nfl.com game centres)
  venue_conditions_w11.json  roof/surface register (official NFL Game Books)
  nws_hourly_w11.json        NWS hourly overlay (api.weather.gov)
  schedule_announcement.json dated 2026 schedule announcement (nfl.com)

Run:  python3 venue/build.py
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "session-cc5a9cdd")

NAV = [
    ("index.html", "Overview"),
    ("week10.html", "Week 10 venues"),
    ("week11.html", "Week 11 venues &amp; conditions"),
    ("schedule.html", "Schedule announcement"),
    ("flagged.html", "Flagged for review"),
]

problems: list[str] = []


# --------------------------------------------------------------------- helpers
def load(name: str) -> dict:
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def link(url: str, text: str | None = None) -> str:
    if not url:
        return ""
    return f'<a href="{esc(url)}">{esc(text or url)}</a>'


def dash(v) -> str:
    """Render a printed-but-absent value as an em dash (a placeholder, not a claim)."""
    return esc(v) if v not in (None, "") else "&mdash;"


def flag_cell(reason: str) -> str:
    return f'<span class="flag">FLAGGED: {esc(reason)}</span>'


def unverified_cell(reason: str) -> str:
    return f'<span class="flag">UNVERIFIED: {esc(reason)}</span>'


def table(headers, rows, caption, source_required=True):
    """rows: list of (label, [cell html...]). Every row must contain an https link."""
    out = [f"<table>\n<caption>{esc(caption)}</caption>\n<thead><tr>"]
    out += [f"<th>{h}</th>" for h in headers]
    out.append("</tr></thead><tbody>")
    for label, cells in rows:
        joined = " ".join(cells)
        if source_required and 'href="https://' not in joined:
            problems.append(f"{caption}: row {label!r} has no official https source link")
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def page(title: str, body: str, active: str) -> str:
    def _anchor(href: str, label: str) -> str:
        cls = ' class="active"' if href == active else ""
        return f'<a href="{esc(href)}"{cls}>{label}</a>'

    nav_items = "".join(_anchor(href, label) for href, label in NAV)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · Venues &amp; Weather · NFL1</title>
<style>
 body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 0; color: #1a1a1a; }}
 header {{ background: #0b2545; color: #fff; padding: 1rem 1.5rem; }}
 header h1 {{ margin: 0.2rem 0; font-size: 1.4rem; }}
 nav {{ display: flex; flex-wrap: wrap; gap: 0.75rem; padding: 0.6rem 1.5rem; background: #13315c; }}
 nav a {{ color: #cfe0ff; text-decoration: none; font-size: 0.92rem; }}
 nav a.active {{ color: #fff; font-weight: 700; text-decoration: underline; }}
 main {{ padding: 1rem 1.5rem 3rem; max-width: 1180px; }}
 table {{ border-collapse: collapse; width: 100%; margin: 0.8rem 0 1.4rem; font-size: 0.88rem; }}
 caption {{ text-align: left; font-weight: 700; padding: 0.4rem 0; }}
 th, td {{ border: 1px solid #ccd; padding: 0.35rem 0.5rem; vertical-align: top; }}
 th {{ background: #eef2f8; text-align: left; }}
 .flag {{ color: #a01818; font-weight: 700; }}
 .box {{ border: 1px solid #ccd; background: #f6f9ff; padding: 0.8rem 1rem; margin: 0.8rem 0; }}
 .stamp {{ color: #556; font-size: 0.85rem; }}
 a {{ color: #0b4f9e; }}
</style>
</head>
<body>
<header><div style="font-size:.85rem">NFL1 · sub-site</div><h1>{esc(title)}</h1></header>
<nav aria-label="Venue pages">{nav_items}</nav>
<main>
{body}
<p class="stamp"><a href="../index.html">← NFL1 main site</a></p>
</main>
</body>
</html>
"""


def write(name: str, content: str) -> None:
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as fh:
        fh.write(content)


# ------------------------------------------------------------------------ data
w10 = load("venue_week10.json")
w11 = load("venue_week11.json")
cond = load("venue_conditions_w11.json")
nws = load("nws_hourly_w11.json")
ann = load("schedule_announcement.json")

stamp_reads = [w10.get("read_at", ""), w11.get("read_at", ""),
               cond.get("read_at", ""), nws.get("fetched_at_utc", ""),
               ann["announcement"].get("read_at", "")]
STAMP = max(s for s in stamp_reads if s)

cond_by_game = {r["game_id"]: r for r in cond["rows"]}
nws_by_game = {r["game_id"]: r for r in nws["rows"]}
w11_by_game = {r["game_id"]: r for r in w11["rows"]}


def kickoff_period(nrow: dict):
    """The hourly period covering kickoff, or None when unavailable."""
    hourly = nrow.get("hourly") or {}
    periods = hourly.get("periods") or []
    if not periods or not nrow.get("kickoff_utc"):
        return None
    ko = datetime.fromisoformat(nrow["kickoff_utc"])
    for p in periods:
        start = datetime.fromisoformat(p["start_time"])
        if start <= ko < start + timedelta(hours=1):
            return p
    return min(periods, key=lambda p: abs(
        (datetime.fromisoformat(p["start_time"]) - ko).total_seconds()))


# ------------------------------------------------------------------- index page
a = ann["announcement"]
verified_cond = sum(1 for r in cond["rows"] if r["verified"])
hourly_ok = sum(1 for r in nws["rows"]
                if (r.get("hourly") or {}).get("status") == 200
                and "kickoff_outside_hourly_horizon" not in r["flags"]
                and "outside_nws_coverage" not in r["flags"])
index_body = f"""
<p>This sub-site publishes the venue evidence for the NFL1 project: stadium
transcription for Weeks 10 and 11, roof/surface registers read from official NFL Game
Books, an official NOAA/NWS hourly forecast overlay around each Week-11 kickoff, and the
dated 2026 schedule announcement shown beside the live schedule.</p>

<div class="box"><strong>2026 schedule announcement.</strong>
The league announced the 2026 NFL Schedule powered by AWS would be released
<strong>{esc(a['release_day'])}, {esc(a['release_date'])} at {esc(a['release_time_printed'])}</strong>
&mdash; source: {link(a['source_url'], a['source_title'])}.
<a href="schedule.html">Full announcement beside the live schedule &rarr;</a></div>

<h2>Executive summary</h2>
<ul>
 <li><strong>{w10['row_count']}</strong> Week-10 and <strong>{w11['row_count']}</strong>
     Week-11 venues transcribed from official nfl.com game-centre pages, each row linked
     to its page: <a href="week10.html">Week 10</a> · <a href="week11.html">Week 11</a>.</li>
 <li><strong>{verified_cond} of {cond['count']}</strong> Week-11 venues have roof and
     surface transcribed verbatim from official NFL Game Books;
     <strong>{cond['count'] - verified_cond}</strong> is blank and
     <a href="flagged.html">flagged</a> (Estadio Banorte — no completed Game Book exists
     yet).</li>
 <li><strong>{hourly_ok} of {nws['count']}</strong> Week-11 venues have official NWS
     hourly wind/temperature/precipitation values for the kickoff window;
     <strong>{nws['count'] - hourly_ok}</strong> flagged (outside NWS coverage; kickoff
     beyond the NWS hourly horizon at read time).</li>
 <li>Every published value links the official source it was read from. Unconfirmable
     values stay blank and are labelled UNVERIFIED/FLAGGED —
     see <a href="flagged.html">Flagged for review</a>.</li>
</ul>

<h2>Method</h2>
<ol>
 <li>Venues: printed <em>Location</em> and <em>Stadium</em> fields from the official NFL
     game-centre pages (read_at per row in the data files).</li>
 <li>Roof/surface/weather: page 1 of the official Game Book (PDF) of each club's most
     recent completed home game at that venue; conditions copied verbatim.</li>
 <li>NWS overlay: stadium coordinates resolved via OpenStreetMap Nominatim (query input
     only), then NOAA <code>api.weather.gov</code> <code>/points</code> and
     <code>forecast/hourly</code> — all published weather values are NWS values with the
     gridpoint URL on each row.</li>
 <li>Schedule announcement: dated nfl.com article, quoted verbatim on
     <a href="schedule.html">schedule.html</a>.</li>
</ol>
<p class="stamp">Data snapshot: {esc(STAMP)} · builder: venue/build.py</p>
"""
write("index.html", page("Venues & Weather", index_body, "index.html"))

# ---------------------------------------------------------------- week 10 page
rows10 = []
for r in w10["rows"]:
    src = " · ".join(x for x in (link(r["game_centre_url"], "game centre"),
                                 link(r.get("game_book_url", ""), "Game Book")) if x)
    rows10.append((r["game_id"], [
        esc(f"{r['away']}@{r['home']}"),
        esc(f"{r['weekday']} {r['gameday']}"),
        esc(r["kickoff_et"]),
        esc(r["location_as_printed"]),
        esc(r["stadium_as_printed"]),
        src,
    ]))
week10_body = f"""
<p>Week-10 fixtures (2026 regular season) with the venue exactly as printed on the
official NFL game centre. Every row links its official page.</p>
{table(["Game", "Date (printed)", "Kickoff (ET)", "Location (printed)", "Stadium (printed)", "Official source"],
       rows10, "Week 10 venues — source: official nfl.com game centres")}
<p class="stamp">Source pages: {w10['row_count']} game centres · read_at per row in
data/session-cc5a9cdd/venue_week10.json · snapshot {esc(STAMP)}</p>
"""
write("week10.html", page("Week 10 venues", week10_body, "week10.html"))

# ---------------------------------------------------------------- week 11 page
rows_a, rows_b = [], []
for r in w11["rows"]:
    gid = r["game_id"]
    c = cond_by_game[gid]
    n = nws_by_game[gid]
    if c["verified"]:
        roof = esc(c["roof_status"])
        surf = esc(c["surface"])
        wx_bits = [c["game_weather_printed"],
                   (c["temp_f_printed"] + "°F") if c["temp_f_printed"] else "",
                   c["humidity_printed"], c["wind_printed"],
                   (c["wind_chill_printed"] and "chill " + c["wind_chill_printed"] + "°F") or ""]
        wx = esc(", ".join(b for b in wx_bits if b))
        src_a = link(c["source_game_book"], "Game Book (PDF)")
    else:
        roof = unverified_cell("no Game Book yet")
        surf = unverified_cell("no Game Book yet")
        wx = unverified_cell("no Game Book yet")
        src_a = (link(r["game_centre_url"], "game centre") + " · "
                 '<a href="flagged.html">flagged</a>')
    rows_a.append((gid, [
        esc(f"{r['away']}@{r['home']}"),
        esc(r["gameday"]),
        esc(r["kickoff_et"]),
        esc(r["location_as_printed"]),
        esc(r["stadium_as_printed"]),
        roof, surf, wx, src_a,
    ]))

    flags = n.get("flags") or []
    np_ = n.get("nws_points") or {}
    hr = n.get("hourly") or {}
    if "outside_nws_coverage" in flags:
        grid = unverified_cell("NWS 404 outside coverage")
        temp = wind = pop = gen = unverified_cell("outside NWS coverage")
        src_b = (link(r["game_centre_url"], "game centre") + " · "
                 '<a href="flagged.html">flagged</a>')
    elif "kickoff_outside_hourly_horizon" in flags:
        grid = esc(f"{np_.get('grid_id')} {np_.get('grid_x')},{np_.get('grid_y')}")
        temp = wind = pop = unverified_cell("kickoff beyond NWS hourly horizon at read time")
        gen = esc(hr.get("generated_at", ""))
        src_b = link(np_.get("forecast_hourly_url", ""), "NWS hourly") + ' · <a href="flagged.html">flagged</a>'
    elif hr.get("status") == 200 and kickoff_period(n):
        p = kickoff_period(n)
        grid = esc(f"{np_.get('grid_id')} {np_.get('grid_x')},{np_.get('grid_y')}")
        temp = esc(f"{p['temperature_f']}°F")
        wind = esc(f"{p.get('wind_direction') or ''} {p.get('wind_speed') or ''}".strip())
        pop = "—" if p.get("pop_pct") is None else esc(str(p["pop_pct"]) + "%")
        gen = esc(hr.get("generated_at", ""))
        src_b = link(np_.get("forecast_hourly_url", ""), "NWS hourly forecast")
    else:
        grid = temp = wind = pop = gen = unverified_cell("NWS data unavailable")
        src_b = link(r["game_centre_url"], "game centre") + ' · <a href="flagged.html">flagged</a>'
    rows_b.append((gid, [
        esc(f"{r['away']}@{r['home']}"),
        esc(r["kickoff_et"]),
        grid, temp, wind, pop, gen, src_b,
    ]))

week11_body = f"""
<p>Week-11 venues (2026 regular season). Table 1: venue as printed plus roof, surface and
game-day weather copied verbatim from the official NFL Game Book of each venue's most
recent completed home game. Table 2: official NOAA/NWS hourly forecast values for the
kickoff window (kickoff &plusmn; 2 h), read from the gridpoint linked on each row.</p>
{table(["Game", "Date", "Kickoff (ET)", "Location (printed)", "Stadium (printed)",
        "Roof (printed)", "Surface (printed)", "Game weather (printed)", "Official source"],
       rows_a, "Table 1 — Week 11 venues, roof/surface from official NFL Game Books")}
{table(["Game", "Kickoff (ET)", "NWS gridpoint", "Temp", "Wind", "PoP",
        "Forecast generated (UTC)", "Official source"],
       rows_b, "Table 2 — NWS hourly overlay at kickoff (api.weather.gov)")}
<p class="stamp">Roof/surface read {esc(cond['read_at'])} · NWS read
{esc(nws['fetched_at_utc'])} · values are forecasts, not observations · blanks are
labelled, never filled from third-party datasets.</p>
"""
write("week11.html", page("Week 11 venues & conditions", week11_body, "week11.html"))

# ------------------------------------------------------------ schedule page
sched_rows = []
for r in w11["rows"]:
    sched_rows.append((r["game_id"], [
        esc(f"{r['away']}@{r['home']}"),
        esc(r["weekday"]),
        esc(r["gameday"]),
        esc(r["kickoff_et"]),
        esc(r["network"]),
        esc(r["stadium_as_printed"]),
        link(r["game_centre_url"], "game centre"),
    ]))
schedule_body = f"""
<div class="box"><strong>Dated announcement (IN-31).</strong>
<p>{esc(a['statement_printed'])}</p>
<p>Announcement / release date: <strong>{esc(a['release_day'])},
{esc(a['release_date'])}</strong> · Source: {link(a['source_url'], a['source_title'])}
({esc(a['source_publisher'])}) · Schedule hub: {link(a['schedule_hub_url'], 'nfl.com schedule release')}
 · article published {esc(a['article_published'])} <em>(date per Wikipedia citation of
the article; not printed in the fetched article render — secondary)</em>.</p>
<p>Also printed in the same article: international games announced Wednesday,
2026-05-13, 9 a.m. ET; the Mexico City game venue printed as &ldquo;Estadio Banorte&rdquo;,
matching the Week-11 game centre.</p></div>

<h2>Live schedule beside the announcement — Week 11</h2>
{table(["Game", "Day", "Date", "Kickoff (ET)", "Network", "Stadium (printed)", "Official source"],
       sched_rows, "2026 Week 11 live schedule — every row links its official game centre")}
<p class="stamp">Schedule rows transcribed from official nfl.com game centres
(read_at {esc(w11['read_at'])}) · announcement read {esc(a['read_at'])}.</p>
"""
write("schedule.html", page("Schedule announcement", schedule_body, "schedule.html"))

# ------------------------------------------------------------- flagged page
flag_rows = [
    ("banorte-roof", [
        "Estadio Banorte roof &amp; surface (Week 11)",
        unverified_cell("roof/surface blank"),
        "Venue first appears in 2026 Week 11; no prior game in the corpus, so no completed "
        "official Game Book exists to transcribe.",
        "Official Game Book after the 2026-11-22 game (MIN@SF).",
        link(w11_by_game["2026_11_MIN_SF"]["game_centre_url"], "game centre"),
    ]),
    ("banorte-nws", [
        "Estadio Banorte NWS hourly overlay",
        unverified_cell("NWS values blank"),
        "NOAA <code>api.weather.gov/points</code> returns 404 at the venue coordinates — "
        "outside NWS coverage (Mexico City).",
        "No NWS source will exist; remains flagged.",
        link(w11_by_game["2026_11_MIN_SF"]["game_centre_url"], "game centre"),
    ]),
    ("was-horizon", [
        "CIN@WAS kickoff-hour NWS values",
        unverified_cell("kickoff window blank"),
        "Monday 2026-11-23 8:15 PM ET kickoff lies beyond the NWS hourly horizon at read "
        "time (snapshot " + esc(nws["fetched_at_utc"]) + ").",
        "Re-run venue/nws_snapshot.py after 2026-11-20 so the hourly product reaches the "
        "kickoff.",
        link((nws_by_game["2026_11_CIN_WAS"].get("nws_points") or {}).get("forecast_hourly_url", ""),
             "NWS hourly product"),
    ]),
    ("kc-weather-desc", [
        "ARROWHEAD STADIUM game-weather description",
        unverified_cell("description blank"),
        "Official Game Book prints &ldquo;Game Weather:&rdquo; with no description text; "
        "temperature/humidity/wind printed and published.",
        "Not clearable — source prints no description; blank kept.",
        link(cond_by_game["2026_11_ARI_KC"]["source_game_book"], "Game Book (PDF)"),
    ]),
    ("was-weather-desc", [
        "NORTHWEST STADIUM game-weather description",
        unverified_cell("description blank"),
        "Official Game Book conditions row carries temp/wind but no &ldquo;Game "
        "Weather:&rdquo; description; values printed and published.",
        "Not clearable — source prints no description; blank kept.",
        link(cond_by_game["2026_11_CIN_WAS"]["source_game_book"], "Game Book (PDF)"),
    ]),
]
flagged_body = f"""
<p>Non-blocking flags: values that could not be confirmed from an official source stay
blank and are labelled here. None of these block publication.</p>
{table(["Item", "What is blank", "Why", "What would clear it", "Official source"],
       flag_rows, "Flagged for review — venue &amp; weather scope (session cc5a9cdd)")}
<p class="stamp">Snapshot {esc(STAMP)} · cross-scope: the main-site
<a href="../flagged.html">flagged.html</a> aggregates flags repository-wide; this page
carries the venue/weather detail.</p>
"""
write("flagged.html", page("Flagged for review", flagged_body, "flagged.html"))

# ---------------------------------------------------------------------- gate
if problems:
    print("BUILD FAILED:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print(f"venue site built: 5 pages (stamp: {STAMP})")
