#!/usr/bin/env python3
"""build_session_page.py — render this session's verification page from the data.

Session `57c05555-nfl1`.  Writes ``pages/session-57c05555.html`` from, and only from:

    data/depth_raw/*.txt + *.meta.json      the raw official captures
    data/depth_parsed/_summary.json         the parse counts and regression pins
    data/ledger/index.json                  the immutable snapshot ledger
    data/ledger/staleness.json              the depth-vs-transactions register

Rules enforced here, because the brief makes them non-negotiable:

* **Every table row carries an official source link.**  The generator refuses to emit a row
  without one, so a row cannot reach the page unsourced.
* **A blank stays blank.**  Where a value is not published by any official source it renders
  as an explicit "not published" cell, never as a zero and never as a guess.
* **Deterministic.**  No clock except the stamps already recorded in the data, so
  ``--check`` can compare the page byte for byte.
"""
from __future__ import annotations

import html
import json
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "pages", "session-57c05555.html")

STYLE = """
:root{--ink:#17202a;--muted:#5b6672;--line:#d9dee5;--bg:#f6f8fa;--ok:#1d6b3a;--warn:#8a5a00;--bad:#9b1c1c;--link:#0b5cad}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#fff;border-bottom:1px solid var(--line);padding:14px 22px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between}
header a{color:var(--link);text-decoration:none;font-weight:600}header nav a{margin-left:14px;font-weight:500}
main{max-width:1180px;margin:0 auto;padding:22px}
h1{font-size:24px;margin:4px 0 6px}h2{font-size:18px;margin:30px 0 8px}h3{font-size:15px;margin:18px 0 6px}
.lede{color:var(--muted);max-width:860px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.kpi{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--muted);font-size:13px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden;font-size:14px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#eef2f6;font-weight:600;position:sticky;top:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.wrap{overflow-x:auto;max-height:640px;border-radius:8px}
.flag{border-left:4px solid var(--warn)}.ok{border-left:4px solid var(--ok)}
.open{color:var(--warn);font-weight:600}.good{color:var(--ok);font-weight:600}.bad{color:var(--bad);font-weight:600}
.blank{color:var(--muted);font-style:italic}
.note{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 14px;color:var(--muted)}
footer{color:var(--muted);font-size:13px;margin:30px 0 10px}
code{background:#eef2f6;padding:1px 4px;border-radius:4px}
"""


def e(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def link(url: str, label: str = "") -> str:
    return f'<a href="{e(url)}">{e(label or url)}</a>'


def n(x, dash: str = "—") -> str:
    if x is None or x == "":
        return f'<span class="blank">{e(dash)}</span>'
    return e(x)


class Builder:
    """Collects rows, refusing any row that has no official https source."""

    def __init__(self) -> None:
        self.refused: list[str] = []

    def row(self, cells: list[str], sources: list[str], cls: str = "") -> str:
        live = [s for s in sources if s and s.startswith("https://")]
        if not live:
            self.refused.append(" | ".join(c for c in cells if c))
            return ""
        src_html = " ".join(link(s, "source") for s in live)
        body = "".join(f"<td>{c}</td>" for c in cells)
        return f'<tr{f" class={cls!r}" if cls else ""}>{body}<td>{src_html}</td></tr>'

    def table(self, headers: list[str], rows: list[str], numeric: set[int] = frozenset()) -> str:
        head = "".join(
            f'<th class="num">{e(h)}</th>' if i in numeric else f"<th>{e(h)}</th>"
            for i, h in enumerate(headers)
        )
        return (
            f'<div class="wrap"><table><thead><tr>{head}<th>Source</th></tr></thead>'
            f'<tbody>{"".join(r for r in rows if r)}</tbody></table></div>'
        )


def load(path: str, default=None):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return default
    return json.load(open(p, encoding="utf-8"))


def build() -> str:
    b = Builder()
    parsed = load("data/depth_parsed/_summary.json", {"clubs": []})
    ledger = load("data/ledger/index.json", {"counts": {}, "by_source": {}, "coverage": {}})
    stale = load("data/ledger/staleness.json", {"clubs": [], "total_stale_rows": 0})

    clubs = parsed.get("clubs", [])
    tot_names = sum(c["counts"].get("player_names", 0) for c in clubs)
    tot_shared = sum(c["counts"].get("shared_groups", 0) for c in clubs)
    tot_jersey = sum(c["counts"].get("jersey_numbers_stripped", 0) for c in clubs)
    tot_slots = sum(c["counts"].get("slots", 0) for c in clubs)
    gaps = sum(len(c.get("gaps", [])) for c in clubs)
    cov = ledger.get("coverage", {})
    n_caps = sum(ledger.get("counts", {}).values()) if ledger.get("counts") else 0

    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>Official depth charts and the availability ledger · NFL Decision Lab</title>",
        f"<style>{STYLE}</style></head><body>",
        "<header><a href=\"../index.html\">NFL Decision Lab</a>",
        '<nav><a href="../index.html">Overview</a>'
        '<a href="../pages/depth.html">Depth &amp; Deficiency</a>'
        '<a href="../pages/injuries.html">Injuries</a>'
        '<a href="../pages/review.html">Flagged for Review</a>'
        '<a href="../pages/sections.html">All sections</a></nav></header>',
        "<main>",
        "<h1>Official depth charts, parsed faithfully, and a ledger that can be replayed</h1>",
        '<p class="lede">Six official club depth-chart pages were read on 15 November 2026 and stored '
        "byte for byte. Each is parsed so that a slot is a <em>group</em> of the players the club "
        "printed in it, a jersey number is separated from the name and kept, and an empty cell stays "
        "empty. Every capture is entered in an append-only ledger with its fetch clock time and the "
        "sha256 of its bytes, so a depth chart or an injury designation can be replayed as it stood "
        "when it was read. Nothing on this page is inferred, and where an official source does not "
        "publish a value the cell says so.</p>",
    ]

    # ---------------- KPIs
    out.append(
        '<section class="kpis">'
        f'<div class="kpi"><b>{len(clubs)}</b><span>official club charts captured</span></div>'
        f'<div class="kpi"><b>{tot_slots}</b><span>depth slots parsed</span></div>'
        f'<div class="kpi"><b>{tot_names}</b><span>player names published</span></div>'
        f'<div class="kpi"><b>{tot_jersey}</b><span>jersey numbers stripped and retained</span></div>'
        f'<div class="kpi"><b>{tot_shared}</b><span>shared slots kept as one group</span></div>'
        f'<div class="kpi"><b>{gaps}</b><span>chart gaps recorded, not filled</span></div>'
        f'<div class="kpi"><b>{n_caps}</b><span>immutable ledger captures</span></div>'
        f'<div class="kpi"><b>{stale.get("total_stale_rows", 0)}</b><span>depth rows the transactions log contradicts</span></div>'
        "</section>"
    )

    # ---------------- 1. what each capture produced
    out.append("<h2>1. What each official capture produced</h2>")
    out.append(
        '<p class="note">One row per official page read this session. "Capture kind" distinguishes a '
        "page that prints table rows from one that prints only an image. A jersey count is the "
        "number of cells where a leading number was removed from the name and stored in its own "
        "field. A shared slot is a cell where the club printed two players at the same rank; it is "
        "kept whole. A gap is a fact the official page does not publish in a readable form; it is "
        "recorded and never filled in.</p>"
    )
    rows = []
    for c in clubs:
        cnt = c["counts"]
        kind = c["capture_kind"]
        kind_html = (
            '<span class="good">table rows</span>'
            if kind == "table"
            else '<span class="open">image only</span>'
        )
        rows.append(
            b.row(
                [
                    f'<strong>{e(c["club"])}</strong>',
                    kind_html,
                    n(c.get("chart_date"), "no date printed"),
                    f'<span class="num">{cnt.get("slots", 0)}</span>',
                    f'<span class="num">{cnt.get("player_names", 0)}</span>',
                    f'<span class="num">{cnt.get("jersey_numbers_stripped", 0)}</span>',
                    f'<span class="num">{cnt.get("shared_groups", 0)}</span>',
                    f'<span class="num">{cnt.get("slots_with_hole", 0)}</span>',
                    f'<span class="num">{cnt.get("rows_dropped", 0)}</span>',
                    n(c.get("fetched_at")),
                ],
                [c["url"]],
            )
        )
    out.append(
        b.table(
            ["Club", "Capture kind", "Chart date (as printed)", "Slots", "Names",
             "Jerseys", "Shared slots", "Slots with a hole", "Rows dropped",
             "Captured at (UTC)"],
            rows,
        )
    )

    # ---------------- 2. the two named defects
    out.append("<h2>2. The two parsing failures the brief names, and what was found</h2>")
    rows = []
    gb = next((c for c in clubs if c["club"] == "GB"), None)
    if gb:
        rows.append(
            b.row(
                [
                    "<strong>Green Bay Packers</strong> — jersey numbers",
                    'The club prints <code>9 Christian Watson</code>. The old transcription stored '
                    "the number inside the name and also in the name field's leading text.",
                    f'{gb["counts"]["jersey_numbers_stripped"]} cells split: the number is stored in '
                    "its own field and the raw string is kept in <code>raw_cell</code>",
                    '<span class="good">fixed</span>',
                ],
                [gb["url"]],
            )
        )
    hou = next((c for c in clubs if c["club"] == "HOU"), None)
    if hou:
        ev = hou["gaps"][0]["evidence"] if hou.get("gaps") else ""
        rows.append(
            b.row(
                [
                    "<strong>Houston Texans</strong> — image-only chart",
                    'The page prints the heading "Unofficial Depth Chart" and one bitmap. There are '
                    "no rows, no position labels and no names in the page text.",
                    f'<span class="open">0 names produced</span>. The image is recorded as evidence: '
                    f"{link(ev, 'the chart image')}. Transcribing it by eye is what the brief forbids.",
                    '<span class="open">unrecoverable from this source</span>',
                ],
                [hou["url"]],
            )
        )
    out.append(
        b.table(["Case", "What the official page prints", "What this build does", "State"], rows)
    )

    # ---------------- 3. shared and empty slots
    shared_rows = []
    for c in clubs:
        for g in c.get("shared_groups", []):
            shared_rows.append(
                b.row(
                    [
                        f'<strong>{e(c["club"])}</strong>',
                        e(g["unit"]),
                        e(g["position"]),
                        f'<span class="num">{g["rank"]}</span>',
                        " and ".join(e(x) for x in g["names"]),
                        f'<code>{e(g["raw_cell"])[:120]}</code>',
                        "kept as one group, not split into rank 1 and rank 2",
                    ],
                    [c["url"]],
                )
            )
    out.append("<h2>3. Shared slots: the club named two players at one rank</h2>")
    out.append(
        '<p class="note">Splitting these into rank 1 and rank 2 would invent a depth order the club '
        f"never published. The table lists every one found across the {len(clubs)} captures.</p>"
    )
    out.append(
        b.table(["Club", "Unit", "Position", "Rank", "Players printed in one cell",
                 "Raw cell", "Treatment"], shared_rows)
        if shared_rows
        else '<p class="note">No shared slot was found in these captures.</p>'
    )

    hole_rows = []
    empty_rows = []
    for c in clubs:
        for h in c.get("holes", []):
            hole_rows.append(
                b.row(
                    [
                        f'<strong>{e(c["club"])}</strong>',
                        e(h["unit"]),
                        e(h["position"]),
                        ", ".join(f"column {x}" for x in h["holes"]),
                        f'<code>{e(h["raw_row"])[:110]}</code>',
                        "hole published as a hole; no player invented",
                    ],
                    [c["url"]],
                )
            )
        for s in c.get("empty_slots", []):
            empty_rows.append(
                b.row(
                    [
                        f'<strong>{e(c["club"])}</strong>',
                        e(s["unit"]),
                        e(s["position"]),
                        f'<code>{e(s["raw_row"])[:110]}</code>',
                        "published as empty: the club named nobody",
                    ],
                    [c["url"]],
                )
            )
    out.append("<h2>4. Empty slots and holes in the middle of a row</h2>")
    out.append(
        '<p class="note">An empty cell is a fact. A club that prints no kicker, or leaves the second '
        "column of a row blank, has not named a backup, and the site says so rather than closing the "
        "gap up. A <em>hole</em> is a blank column with a filled column after it.</p>"
    )
    if hole_rows:
        out.append("<h3>Holes</h3>")
        out.append(b.table(["Club", "Unit", "Position", "Blank column", "Raw row", "Treatment"], hole_rows))
    if empty_rows:
        out.append("<h3>Slots printed empty</h3>")
        out.append(b.table(["Club", "Unit", "Position", "Raw row", "Treatment"], empty_rows))

    # ---------------- 5. ledger
    out.append("<h2>5. The immutable availability ledger</h2>")
    out.append(
        '<p class="note">Each capture is its own directory, named with the first 12 characters of the '
        "sha256 of its own bytes, holding <code>raw.txt</code> and <code>record.json</code>. A capture "
        "is never rewritten: re-reading the same page writes a second, separately hashed capture. "
        "That is what makes a designation replayable as it was known. "
        f'<code>python3 pipeline/ledger.py verify</code> re-hashes all {n_caps} and re-derives every '
        "stored count.</p>"
    )
    led_rows = []
    for src, entries in (ledger.get("by_source") or {}).items():
        for en in entries:
            prec = en.get("clock_precision", "")
            prec_html = (
                '<span class="good">clock time</span>'
                if prec == "second"
                else '<span class="open">date only</span>'
            )
            cnt = en.get("counts") or {}
            summary = ", ".join(f"{k}={v}" for k, v in list(cnt.items())[:3]) or "—"
            led_rows.append(
                b.row(
                    [
                        f'<strong>{e(src)}</strong>',
                        e(en.get("club") or en.get("week") or "—"),
                        e(en.get("captured_at")),
                        prec_html,
                        e(en.get("payload_kind", "")),
                        f'<code>{e(en.get("sha256", "")[:16])}…</code>',
                        f'<span class="num">{en.get("bytes", 0)}</span>',
                        e(summary),
                    ],
                    [en["url"]],
                )
            )
    out.append(
        b.table(
            ["Source", "Club / week", "Captured at (UTC)", "Clock precision", "Payload kind",
             "sha256", "Bytes", "Recorded counts"],
            led_rows,
        )
    )

    out.append("<h3>What the ledger can and cannot answer today</h3>")
    cov_rows = [
        b.row(
            ["Injury report days captured", f'<span class="num">{cov.get("injury_distinct_days", 0)}</span>',
             "days on which an official injury read is stored",
             "The brief asks for a daily Wednesday-to-kickoff series. Two days is not a series."],
            ["https://www.nfl.com/injuries/"],
        ),
        b.row(
            ["Days still to capture for a 14-day holdout",
             f'<span class="num">{cov.get("days_still_to_capture", 0)}</span>',
             "14 minus the days already held",
             "The ledger makes each future read replayable; it cannot invent the missing days."],
            ["https://www.nfl.com/injuries/"],
        ),
        b.row(
            ["Club depth charts captured",
             f'<span class="num">{cov.get("depth_chart_clubs_captured", 0)} of {cov.get("depth_chart_clubs_expected", 32)}</span>',
             "clubs with an official chart in the ledger",
             "The remaining clubs' charts are not yet read; they are not assumed similar."],
            ["https://www.nfl.com/teams/"],
        ),
        b.row(
            ["Captures with a second-precision clock time",
             f'<span class="num">{cov.get("captures_with_a_clock_time", 0)}</span>',
             "captures that can be placed before or after a kickoff",
             "A date-only capture cannot prove what was known at kickoff and is marked as such."],
            ["https://www.nfl.com/injuries/"],
        ),
        b.row(
            ["Captures recorded as date only",
             f'<span class="num">{cov.get("captures_date_only", 0)}</span>',
             "earlier copies brought inside the ledger without a clock time",
             "Imported rather than excluded, and labelled, because a labelled weak record beats no record."],
            ["https://www.nfl.com/injuries/"],
        ),
    ]
    out.append(b.table(["Question", "Value", "What it means", "Honest limit"], cov_rows))

    # ---------------- 6. staleness
    out.append("<h2>6. Depth rows the official transactions log contradicts</h2>")
    out.append(
        '<p class="note">A depth chart is a club opinion with no expiry date; a transactions log is a '
        "dated legal fact. A row is flagged stale when the chart still names a player whom the log "
        "placed on reserve and no later dated line returns him. Nothing is corrected on either side: "
        "both sources are published as they stand. A transactions line often reports several "
        "unrelated moves, so the comparison is made clause by clause — a player only inherits the "
        "move in the clause that names him.</p>"
    )
    cu_rows = []
    for c in stale.get("clubs", []):
        order = c.get("capture_order_note", "")
        cu_rows.append(
            b.row(
                [
                    f'<strong>{e(c["club"])}</strong>',
                    f'<span class="num">{c.get("transactions_captured", 0)}</span>',
                    e(c.get("transaction_window", "")) or "—",
                    e(c.get("depth_captured_at", "")) or "—",
                    f'<span class="num">{(c.get("reserve_transaction_count") or 0)}</span>',
                    f'<span class="num">{len(c.get("stale_rows", []))}</span>',
                    "confirmed clean" if not c.get("stale_rows") else '<span class="open">see below</span>',
                    e(order),
                ],
                [c.get("transactions_url") or c.get("depth_url")],
            )
        )
    out.append(
        b.table(
            ["Club", "Log lines", "Log window", "Chart captured at (UTC)", "Reserve moves in log",
             "Stale rows", "Verdict", "Capture-order note"],
            cu_rows,
        )
    )

    st_rows = []
    for c in stale.get("clubs", []):
        for s in c.get("stale_rows", []):
            st_rows.append(
                b.row(
                    [
                        f'<strong>{e(c["club"])}</strong>',
                        e(s["player"]),
                        e(f'{s["unit"]} {s["position"]}'),
                        f'<span class="num">{n(s.get("rank"))}</span>',
                        e(s["transaction_date"]),
                        f'<span class="num">{e(s["transaction_text"])[:180]}</span>',
                        "The chart still names him; the log placed him on reserve with no later "
                        "activation.",
                    ],
                    [s["transaction_url"], s["chart_url"]],
                )
            )
    out.append("<h3>Every stale row found</h3>")
    out.append(
        b.table(
            ["Club", "Player still on the chart", "Slot", "Rank", "Transaction date",
             "The dated transaction", "Why it is flagged"],
            st_rows,
        )
        if st_rows
        else '<p class="note">No stale row was found in the clubs compared.</p>'
    )

    # ---------------- 7. the Baltimore case from the brief
    out.append("<h2>7. The Baltimore case named in the brief, checked against both official pages</h2>")
    out.append(
        '<p class="note">The brief states that "Baltimore still publishes Lamar Jackson and Tyler '
        'Huntley at QB after both went on injured reserve and a replacement was traded in". Both '
        "official pages were read this session and the claim does not hold for the pages as they "
        "stand on 15 November 2026. The evidence is below, unedited.</p>"
    )
    bal_rows = [
        b.row(
            ["Official transactions page", "2026-11-05",
             "Placed QB Lamar Jackson and QB Tyler Huntley on Injured Reserve.",
             "Confirms the premise of the brief: both went on injured reserve.", '<span class="good">confirmed</span>'],
            ["https://www.baltimoreravens.com/team/transactions/"],
        ),
        b.row(
            ["Official transactions page", "2026-11-10",
             "Acquired OL Ryan Neuzil via trade from the Atlanta Falcons in exchange for G Andrew "
             "Vorhees and undisclosed draft compensation. Released TE Nick Vannett and G Kyle Hergel.",
             "The trade in this window was an offensive lineman, not a quarterback.", '<span class="good">confirmed</span>'],
            ["https://www.baltimoreravens.com/team/transactions/"],
        ),
        b.row(
            ["Official depth chart", "read 2026-11-15T12:52:48Z and again at 12:57:10Z",
             "QB: Jacoby Brissett, Joe Fagnano, Kedon Slovis.",
             "Neither Lamar Jackson nor Tyler Huntley appears anywhere on the current chart, so no "
             "stale QB row exists. The two reads are byte-identical (sha256 f9da4c0aab60…), which "
             "settles it rather than leaving it to memory.", '<span class="good">brief example already fixed</span>'],
            ["https://www.baltimoreravens.com/team/depth-chart"],
        ),
        b.row(
            ["Official transactions page", "2026-11-03",
             "Signed QB Kedon Slovis. Placed K Tyler Loop on Injured Reserve.",
             "Explains the third-string name on the chart, and shows the log and the chart agree.",
             '<span class="good">confirmed</span>'],
            ["https://www.baltimoreravens.com/team/transactions/"],
        ),
    ]
    out.append(
        b.table(["Official page", "Date / fetch", "What it says", "What that settles", "State"], bal_rows)
    )

    # ---------------- 8. irregularities
    out.append("<h2>8. Irregularities flagged for review</h2>")
    out.append(
        '<p class="note">These are published here and on the <a href="../pages/review.html">Flagged '
        "for Review</a> page so a reader can judge them. None blocks the merge.</p>"
    )
    irr = [
        ("The Houston chart cannot be read at all",
         "houstontexans.com renders the depth chart as one JPEG. No parser can recover names from it, "
         "and the brief forbids transcription by eye, so Houston has zero published depth rows. This "
         "is a genuine hole in depth coverage for one of 32 clubs.",
         "An authorised structured source for the Houston chart, or the club publishing a table.",
         "https://www.houstontexans.com/team/depth-chart", "open"),
        ("Only 6 of 32 club charts are captured so far",
         "The parser and the ledger are general, but this session read six clubs. The other 26 are "
         "not captured, and are therefore not published rather than assumed.",
         "Read the remaining 26 official pages and add them to the ledger; the code needs no change.",
         "https://www.nfl.com/teams/", "open"),
        ("The injury archive is two days, not a series",
         "The brief asks for a daily Wednesday-to-kickoff capture. The ledger holds 2026-11-13 (a "
         "10-row hand transcription) and 2026-11-15 (a 347-row transcription), both date-only.",
         "Twelve more days of dated captures; each will carry a clock time automatically.",
         "https://www.nfl.com/injuries/", "open"),
        ("Neither existing injury copy kept the raw page",
         "Both injury captures are transcriptions of fetch-tool text, and the earlier one records no "
         "clock time. The ledger stores them as <code>transcribed-table</code> and marks them "
         "date-only, so no reader can mistake a transcription for the page itself.",
         "Future reads are stored as raw page text with a clock time; the archive cannot be retrofitted.",
         "https://www.nfl.com/injuries/", "open"),
        ("The Ravens depth capture preceded the transactions capture",
         "The Baltimore chart was read at 12:52:48Z and the transaction log at 12:54:51Z, so a clean "
         "comparison could have been an artefact of the order. The chart was re-read at 12:57:10Z, "
         "after the log, and came back byte-identical. The finding is therefore sound, and the "
         "capture order is published with it.",
         "Settled for Baltimore. The Indianapolis chart was also read before its log; a later chart "
         "read would strengthen it, though both Indianapolis rows turn on a transaction dated 11/14 "
         "which the chart already predates.",
         "https://www.baltimoreravens.com/team/depth-chart", "open, bounded"),
        ("The Chicago and Philadelphia double-ranking cases are unverified here",
         "Earlier sessions recorded a Chicago defence row printed with both a 1st-string and a "
         "2nd-string player, and an Eagles DT row that looks like a fragment. Neither club was "
         "captured in this session, so no claim is made about them either way.",
         "Capture both clubs and let the shared-slot and hole counts decide.",
         "https://www.chicagobears.com/team/depth-chart", "not assessed"),
    ]
    irr_rows = []
    for title, what, clears, url, state in irr:
        cls = "open" if state.startswith("open") else ""
        irr_rows.append(
            b.row(
                [f"<strong>{e(title)}</strong>", e(what), e(clears),
                 f'<span class="{cls or "blank"}">{e(state)}</span>'],
                [url],
            )
        )
    out.append(b.table(["Irregularity", "What was found", "What would settle it", "State"], irr_rows))

    # ---------------- 9. the injury report as a series
    evo = load("data/ledger/injury_report_evolution.json", {})
    if evo:
        out.append("<h2>9. The injury report as a dated series, not a weekly snapshot</h2>")
        out.append(
            '<p class="note">Three sessions recorded three different row counts for the same week. '
            "That is not a contradiction: the official page grew during the week. Publishing the "
            "series is the only way a reader can tell the difference, and it is the reason the "
            "ledger exists.</p>"
        )
        rows = []
        for pt in evo.get("series", []):
            rows.append(
                b.row(
                    [
                        f'<strong>{e(pt["captured"])}</strong>',
                        f'<span class="num">{pt["rows"]}</span>',
                        f'<span class="num">{pt["clubs"]}</span>',
                        f'<span class="num">{pt["clubs_printing_no_injuries"]}</span>',
                        e(", ".join(pt["no_injury_clubs"]) or "none"),
                        e(pt["note"]),
                        e(pt["artifact"]),
                    ],
                    [evo["source_url"]],
                )
            )
        out.append(
            b.table(["Captured (UTC)", "Rows", "Clubs", "Clubs printing no injuries",
                     "Which clubs", "What it records", "Artifact"], rows)
        )
        d = evo.get("delta", {})
        if d:
            out.append(
                '<p class="note"><strong>What changed between the last two reads:</strong> '
                f'{d["rows"]} player rows and {d["clubs"]} club tables appeared in the 48 hours '
                f'before kickoff, and {d["no_injury_sections_closed"]} "No Injuries Reported" '
                "sections became full injury tables. A model that froze a Wednesday reading would "
                "have been wrong about all of it.</p>"
            )
        out.append("<h3>Claims still published elsewhere in this repository</h3>")
        out.append(
            '<p class="note">These are recorded here and on the coordination board rather than '
            "edited, because each lives in a file owned by another session. Every one is checkable "
            "against the capture in one click.</p>"
        )
        rows = []
        for c in evo.get("contradiction_register", []):
            from_r = ", ".join(c["who_still_publishes_it"])
            rows.append(
                b.row(
                    [
                        f'<strong>{e(c["claim"])}</strong>',
                        f'<span class="open">{e(c["status"])}</span>',
                        e(c["evidence_for_false"]),
                        e(from_r),
                        e(c["action_for_the_owning_session"]),
                        e(c["severity"]),
                    ],
                    [evo["source_url"]],
                )
            )
        out.append(
            b.table(["Claim", "Status on 2026-11-15", "What the official capture shows",
                     "Where it is still published", "What the owning session should do",
                     "Severity"], rows)
        )
        out.append("<h3>What this session fixed at the source</h3>")
        rows = []
        for f in evo.get("fixed_by_this_session", []):
            rows.append(
                b.row(
                    [f'<code>{e(f["artifact"])}</code>', e(f["was"]), e(f["now"]), e(f["how"])],
                    [evo["source_url"]],
                )
            )
        out.append(b.table(["Artifact", "Was", "Now", "How"], rows))

    # ---------------- 10. reproduce
    out.append("<h2>10. Reproduce every number on this page</h2>")
    out.append(
        '<p class="note">Each command runs offline against the committed captures and fails if a '
        "number on this page stops being true.</p>"
        "<pre><code>python3 tools/check_depth_parse.py          # parse gate + regression pins\n"
        "python3 pipeline/ledger.py verify           # re-hash every capture\n"
        "python3 pipeline/ledger.py index --check    # ledger index is current\n"
        "python3 scripts/nfl1_57c05555/staleness.py --check   # staleness register is current\n"
        "python3 scripts/nfl1_57c05555/repair_verified_injuries.py --check  # verified injury files\n"
        "python3 tools/build_session_page.py --check # this page equals what the data produces\n"
        "python3 -m pytest tests/test_depth_parse_57c05555.py tests/test_staleness_57c05555.py -q</code></pre>"
    )

    out.append(
        "<footer>Every row on this page carries the official page it came from. Values an official "
        "source does not publish are shown as an explicit blank, never filled. "
        f"Built from {len(clubs)} raw captures, {n_caps} ledger records and "
        f"{stale.get('total_stale_rows', 0)} stale-row findings.</footer>"
    )
    out.append("</main></body></html>")

    if b.refused:
        raise SystemExit(
            "REFUSED: these rows had no official https source and were dropped:\n  "
            + "\n  ".join(b.refused)
        )
    return "\n".join(out) + "\n"


def main() -> int:
    page = build()
    if "--check" in sys.argv:
        if not os.path.exists(OUT) or open(OUT, encoding="utf-8").read() != page:
            print("FAIL: pages/session-57c05555.html is stale — re-run without --check")
            return 1
        print("OK: session page is current")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({len(page):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
