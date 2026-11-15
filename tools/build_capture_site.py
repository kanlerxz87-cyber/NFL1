#!/usr/bin/env python3
"""build_capture_site.py: render capture/index.html from the immutable capture files.

Session 543676f8-nfl1 (task X1/X3). Run from the repository root:

    python3 tools/build_capture_site.py

Inputs (all committed, none fetched here):
    data/capture/nflcom_injuries_reg10_2026-11-15_rows.tsv
    data/capture/nflcom_injuries_reg10_2026-11-15_games.tsv
    data/capture/manifest.json
    data/capture/comparison.json      (written by tools/check_capture.py)

The page is a pure function of those files. The build first runs the structural gate in
tools/check_capture.py and stops if it fails, so a page is never rendered from a capture that
does not validate. Every table row links to the official page the row was transcribed from.
"""
from __future__ import annotations

import csv
import html
import json
import os
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_capture  # noqa: E402  (structural gate, same file the CI runs)

CAP = os.path.join(ROOT, "data", "capture")
OUT = os.path.join(ROOT, "capture", "index.html")


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def read_tsv(name: str) -> list[dict]:
    with open(os.path.join(CAP, name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def load_json(name: str) -> dict:
    with open(os.path.join(CAP, name), encoding="utf-8") as fh:
        return json.load(fh)


CSS = """
:root{--ink:#17202a;--muted:#5b6672;--line:#d9dee5;--bg:#f6f8fa;--ok:#1d6b3a;--warn:#8a5a00;--bad:#9b1c1c;--link:#0b5cad}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#fff;border-bottom:1px solid var(--line);padding:14px 22px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between}
header a{color:var(--link);text-decoration:none;font-weight:600}header nav a{margin-left:14px;font-weight:500}
main{max-width:1180px;margin:0 auto;padding:22px}
h1{font-size:24px;margin:4px 0 6px}h2{font-size:18px;margin:28px 0 8px}
.lede{color:var(--muted);max-width:820px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.kpi{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--muted);font-size:13px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden;font-size:14px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#eef2f6;font-weight:600;position:sticky;top:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.wrap{overflow-x:auto;max-height:620px;border-radius:8px}
.flag{border-left:4px solid var(--warn)}.open{color:var(--warn);font-weight:600}
.blank{color:var(--muted);font-style:italic}
.note{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 14px;color:var(--muted)}
footer{color:var(--muted);font-size:13px;margin:30px 0 10px}
code{background:#eef2f6;padding:1px 4px;border-radius:4px}
"""


def page(body: str, stamp: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Official Week 10 injury report: capture · NFL Decision Lab</title>
<style>{CSS}</style></head>
<body>
<header>
  <a href="../index.html">NFL Decision Lab</a>
  <nav><a href="../index.html">Overview</a><a href="../pages/review.html">Flagged for Review</a>
  <a href="../pages/injuries.html">Injuries</a><a href="../pages/sections.html">All sections</a></nav>
</header>
<main>{body}
<footer>Built {esc(stamp)} by <code>tools/build_capture_site.py</code> from <code>data/capture/</code>.
Every row links to the official nfl.com page it was transcribed from. A blank cell means the official
page printed nothing in that column; it is not an inferred value.</footer>
</main></body></html>
"""


def main() -> int:
    print("build_capture_site: running the structural gate first")
    if check_capture.main() != 0:
        print("build_capture_site: capture failed its gate; no page written", file=sys.stderr)
        return 1
    man = load_json("manifest.json")
    comp = load_json("comparison.json")
    rows = read_tsv("nflcom_injuries_reg10_2026-11-15_rows.tsv")
    games = read_tsv("nflcom_injuries_reg10_2026-11-15_games.tsv")
    src = man["source_url"]
    game_by_club = {}
    for g in games:
        for c in g["listed_clubs"].split():
            game_by_club[c] = g["game_id"]
    gs = Counter(r["game_status"] or "" for r in rows)
    pr = Counter(r["practice_status"] for r in rows)
    scrape_by_club = {x["club"]: x["scrape"] for x in comp["club_counts_vs_scrape"]}
    hand_by_club = {x["club"]: x["hand_copy"] for x in comp["club_counts_vs_hand_copy"]}

    kpis = "".join(f'<div class="kpi"><b>{esc(v)}</b><span>{esc(k)}</span></div>' for k, v in [
        ("rows on the official page", len(rows)),
        ("clubs", man["counts"]["clubs"]),
        ("games (Week 10)", man["counts"]["games"]),
        ("Out", gs.get("Out", 0)),
        ("Doubtful", gs.get("Doubtful", 0)),
        ("Questionable", gs.get("Questionable", 0)),
        ("no game designation printed", gs.get("", 0)),
        ("open flags", sum(1 for f in comp["flags"] if f["state"] == "open")),
    ])

    club_rows = []
    for club in sorted(man["rows_per_club"]):
        lst = [r for r in rows if r["team"] == club]
        c = Counter(r["game_status"] for r in lst)
        dnp = sum(1 for r in lst if r["practice_status"] == "Did Not Participate In Practice")
        hand = hand_by_club.get(club, "")
        hand_cell = (f'<span class="blank">{esc(hand)}</span>' if isinstance(hand, str) and hand and not hand.isdigit()
                     else esc(hand))
        scrape = scrape_by_club.get(club)
        scrape_cell = esc(scrape) if scrape is not None else '<span class="blank">absent</span>'
        club_rows.append(
            f"<tr><td><strong>{esc(club)}</strong></td><td>{esc(game_by_club.get(club, ''))}</td>"
            f'<td class="num">{len(lst)}</td><td class="num">{c.get("Out", 0)}</td>'
            f'<td class="num">{c.get("Doubtful", 0)}</td><td class="num">{c.get("Questionable", 0)}</td>'
            f'<td class="num">{dnp}</td><td class="num">{scrape_cell}</td><td class="num">{hand_cell}</td>'
            f'<td><a href="{esc(src)}">nfl.com injury report</a></td></tr>')
    club_table = (
        '<div class="wrap"><table><thead><tr><th>Club</th><th>Game</th><th class="num">Rows</th>'
        '<th class="num">Out</th><th class="num">Doubtful</th><th class="num">Questionable</th>'
        '<th class="num">Did not practise</th><th class="num">Scrape 14 Nov</th>'
        '<th class="num">Hand copy 12 Nov</th><th>Source</th></tr></thead><tbody>'
        + "".join(club_rows) + "</tbody></table></div>")

    player_rows = []
    for r in rows:
        gcell = (f'<span class="blank">blank</span>' if not r["game_status"]
                 else f'<strong>{esc(r["game_status"])}</strong>')
        icell = (f'<span class="blank">blank</span>' if not r["injury"] else esc(r["injury"]))
        player_rows.append(
            f"<tr><td>{esc(r['game_id'])}</td><td>{esc(r['team'])}</td><td>{esc(r['player'])}</td>"
            f"<td>{esc(r['position'])}</td><td>{icell}</td><td>{esc(r['practice_status'])}</td>"
            f"<td>{gcell}</td><td><a href=\"{esc(src)}\">nfl.com</a></td></tr>")
    player_table = (
        '<div class="wrap"><table><thead><tr><th>Game</th><th>Club</th><th>Player</th><th>Pos</th>'
        '<th>Injury as printed</th><th>Practice status</th><th>Game status</th><th>Source</th>'
        '</tr></thead><tbody>' + "".join(player_rows) + "</tbody></table></div>")

    flag_rows = []
    for f in comp["flags"]:
        flag_rows.append(
            f'<tr class="flag"><td><strong>{esc(f["id"])}</strong></td><td>{esc(f["area"])}</td>'
            f'<td>{esc(f["issue"])}</td><td><span class="open">{esc(f["state"])}</span></td>'
            f'<td>{esc(f["what_settles_it"])}</td><td><a href="{esc(f["source"])}">official page</a></td></tr>')
    flag_table = (
        '<div class="wrap"><table><thead><tr><th>ID</th><th>Area</th><th>What is flagged</th>'
        '<th>State</th><th>What settles it</th><th>Source</th></tr></thead><tbody>'
        + "".join(flag_rows) + "</tbody></table></div>")

    body = f"""
<h1>Official Week 10 injury report, captured 15 November 2026</h1>
<p class="lede">Every player row on the nfl.com Week 10 injury report, transcribed from the page and
checked against the page's own club and game structure. Nothing here is inferred. Where the other
copies in this repository disagree, the difference is listed as a flag rather than resolved by
editing the capture.</p>
<p><a href="{esc(src)}">Official source: NFL Injury Report, Week 10 of the 2026 season</a></p>

<section class="kpis">{kpis}</section>

<h2>Club by club</h2>
<p class="note">Counts are the rows on the official page. The last two columns are the counts the
other copies in this repository hold for the same club: the automated scrape of 14 November and the
hand copy of 12 November. "absent" or "No Injuries Reported" means that copy does not list the club
with rows.</p>
{club_table}

<h2>Every row</h2>
<p class="note">Blank injury: the page printed no injury. Blank game status: the page printed no
designation. Practice status is copied as printed.</p>
{player_table}

<h2>Flags raised by this capture</h2>
<p class="note">Each flag is an open question for review. None of them blocks the publication of the capture
itself; each names the official page that settles it.</p>
{flag_table}

<h2>Files and method</h2>
<table><tbody>
<tr><td>Rows (TSV)</td><td><a href="../data/capture/nflcom_injuries_reg10_2026-11-15_rows.tsv">data/capture/nflcom_injuries_reg10_2026-11-15_rows.tsv</a></td><td><code>{esc(man['rows_tsv_sha256'])}</code></td></tr>
<tr><td>Games (TSV)</td><td><a href="../data/capture/nflcom_injuries_reg10_2026-11-15_games.tsv">data/capture/nflcom_injuries_reg10_2026-11-15_games.tsv</a></td><td><code>{esc(man['games_tsv_sha256'])}</code></td></tr>
<tr><td>Manifest</td><td><a href="../data/capture/manifest.json">data/capture/manifest.json</a></td><td>counts, method, cross-references</td></tr>
<tr><td>Comparison</td><td><a href="../data/capture/comparison.json">data/capture/comparison.json</a></td><td>every difference against the other copies</td></tr>
<tr><td>Method</td><td colspan="2">{esc(man['capture_method'])}</td></tr>
<tr><td>Captured</td><td colspan="2">{esc(man['captured'])}</td></tr>
</tbody></table>
<p class="note">Practice status counts on the page: {esc(dict(pr))}.</p>
"""
    stamp = man["captured"]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page(body, stamp))
    print(f"build_capture_site: wrote {os.path.relpath(OUT, ROOT)} ({len(rows)} rows, {len(comp['flags'])} flags)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
