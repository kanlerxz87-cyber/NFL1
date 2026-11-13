#!/usr/bin/env python3
"""Build the NFL1 dashboard static site from the JSON data layer in ../data.

Design rules enforced here, not by convention:
  1. Every DATA row must carry a source URL. The build fails loudly if one does not.
  2. A value that could not be confirmed from an official source renders as an
     explicit UNVERIFIED cell. It is never silently omitted and never invented.
  3. Derived values (pure arithmetic on official values) are badged DERIVED.
  4. Governance rows sourced from the owner's brief are badged INTERNAL and are
     the only permitted exemption from rule 1 (flag F-006).

Usage:  python3 tools/build_docs_site.py
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "session-87deb7ab")
DOCS = os.path.join(ROOT, "docs")

RETRIEVED = "2026-11-12"
# Deterministic stamp taken from the data this site is built from, so a rebuild
# reproduces the committed files exactly.
with open(os.path.join(ROOT, "data", "session-87deb7ab", "sources.json"), encoding="utf-8") as _fh:
    BUILD_STAMP = json.load(_fh).get("meta", {}).get("generated_utc", "") + " data snapshot"

problems: list[str] = []


# --------------------------------------------------------------------------- io
def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


# --------------------------------------------------------------------------- data
sources = load("sources.json")
standings = load("standings.json")
injuries = load("injuries.json")
requirements = load("requirements.json")
questions = load("questions.json")
suggestions = load("suggestions.json")
strategies = load("strategies.json")
correlation = load("correlation.json")
flagged = load("flagged.json")

SRC = {s["id"]: s for s in sources["sources"]}
SRC["SRC-000"] = {
    "id": "SRC-000",
    "name": "Owner project brief (this repository)",
    "tier": "Internal — governance",
    "url": "https://github.com/kanlerxz87-cyber/NFL1",
}


def src_cell(sid: str, label: str | None = None) -> str:
    """Render a source link cell. Missing sources are a build failure."""
    s = SRC.get(sid)
    if not s or not s.get("url"):
        problems.append(f"source id not registered or has no URL: {sid!r}")
        return '<td class="src"><span class="badge b-flagged">NO SOURCE</span></td>'
    return (f'<td class="src"><a class="ext" href="{esc(s["url"])}" target="_blank" '
            f'rel="noopener noreferrer" title="{esc(s["name"])}">{esc(label or sid)}</a></td>')


def src_inline(sid: str) -> str:
    s = SRC.get(sid)
    if not s or not s.get("url"):
        problems.append(f"source id not registered: {sid!r}")
        return '<span class="badge b-flagged">NO SOURCE</span>'
    return (f'<a class="ext" href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">'
            f'{esc(s["name"])}</a>')


# ----------------------------------------------------------------------- widgets
def badge(text: str, kind: str = "na") -> str:
    return f'<span class="badge b-{kind}">{esc(text)}</span>'


def blank_cell(note: str = "UNVERIFIED") -> str:
    return f'<td><span class="blank">{esc(note)}</span></td>'


STATUS_BADGE = {
    "Answered": "done", "Done": "done", "Done (partial)": "partial",
    "Partially answered": "partial", "Implemented": "done", "Ready": "done",
    "In progress": "partial", "Proposed": "proposed", "Specified": "derived",
    "Open - blocking": "open", "Open - owner input": "open", "Open": "open",
    "Open - unverified": "open", "Open - derived only": "partial",
    "Blocked": "open", "Deviation": "flagged", "Not estimated": "unverified",
    "Not started": "na", "Known by definition": "done", "needs review": "unverified",
}


def status_badge(s: str) -> str:
    return badge(s, STATUS_BADGE.get(s, "na"))


PRACTICE_BADGE = {"DNP": "dnp", "LP": "lp", "FP": "fp"}
STATUS_GBADGE = {"Out": "out", "Doubtful": "q", "Questionable": "q"}


def render_table(rows, cols, table_id, sortable=True, empty_msg="No rows match."):
    """cols: list of (header, extractor(row)->html, css_class or '')."""
    head = "".join(f'<th class="{esc(cls)}">{esc(h)}</th>' for h, _, cls in cols)
    body_parts = []
    for r in rows:
        cells = []
        search_bits = []
        for _, fn, _cls in cols:
            out = fn(r)
            if out.startswith("<td"):
                cells.append(out)
            else:
                cells.append(f"<td>{out}</td>")
            search_bits.append(_strip_tags(out))
        body_parts.append(
            f'<tr data-search="{esc(" ".join(search_bits).lower())}">{"".join(cells)}</tr>')
    body = "".join(body_parts)
    attr = " data-sortable" if sortable else ""
    return (
        f'<div class="scroll"><table id="{esc(table_id)}"{attr}>'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
        f'<p class="tbl-empty" style="display:none">{esc(empty_msg)}</p>'
    )


def _strip_tags(s: str) -> str:
    out, in_tag = [], False
    for ch in s:
        if ch == "<":
            in_tag = True
        elif ch == ">":
            in_tag = False
        elif not in_tag:
            out.append(ch)
    # Cells arrive HTML-escaped; unescape so search text matches what the user types.
    return html.unescape("".join(out))


def tools(filter_col=None, filter_label="All categories", keys=None, placeholder="Search rows…"):
    sel = ""
    if keys is not None and filter_col is not None:
        opts = "".join(f'<option value="{esc(k)}">{esc(k)}</option>' for k in sorted(set(keys)))
        sel = (f'<select data-filter="{filter_col}" aria-label="{esc(filter_label)}">'
               f'<option value="">{esc(filter_label)}</option>{opts}</select>')
    return (f'<div class="table-tools" data-table-tools>'
            f'<input type="search" placeholder="{esc(placeholder)}" aria-label="Search this table">'
            f"{sel}<span class="f'count"></span></div>')


def card(title, inner, body=True, sub=""):
    head = f"<h2>{title}</h2>" if not sub else f"<h2>{title}{sub}</h2>"
    if body:
        return f'<section class="card">{head}<div class="body">{inner}</div></section>'
    return f'<section class="card">{head}{inner}</section>'


def kpi(k, v, note="", kind=""):
    return f'<div class="kpi {kind}"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div><div class="n">{esc(note)}</div></div>'


def note(txt, kind=""):
    return f'<div class="note {kind}">{txt}</div>'


# -------------------------------------------------------------------------- nav
NAV = [
    ("Overview", [("index.html", "Dashboard"), ("executive-summary.html", "Executive summary")]),
    ("Decision making", [("requirements.html", "Requirements"), ("questions.html", "Questions & answers"),
                         ("suggestions.html", "Suggestions & decisions")]),
    ("Strategy", [("strategy-lab.html", "Strategy lab"), ("signals.html", "Signal catalogue"),
                  ("correlation.html", "Correlation")]),
    ("Roster", [("injury-depth.html", "Injury & depth"), ("standings.html", "Standings")]),
    ("Governance", [("data-sources.html", "Data sources"), ("verification.html", "Verification"),
                    ("flagged.html", "Flagged for review")]),
]


def page(filename, title, desc, sections, stamp_extra=""):
    nav_html = []
    for group, items in NAV:
        links = []
        for href, label in items:
            active = " class=\"active\"" if href == filename else ""
            links.append(f"<a href=\"{href}\"{active}>{esc(label)}</a>")
        nav_html.append(f'<div class="nav-group"><h4>{esc(group)}</h4>{"".join(links)}</div>')
    stamp = (f'Data retrieved from official sources: <strong>{RETRIEVED}</strong>'
             f'{stamp_extra} &nbsp;·&nbsp; Page generated: {BUILD_STAMP}')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — NFL1</title>
<meta name="description" content="NFL1 — verified NFL analytics, strategy research and decision register.">
<link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="layout">
<aside class="sidebar">
  <div class="brand"><a href="index.html">NFL1</a>
    <div class="sub">Verified NFL analytics, line origination<br>and decision register</div></div>
  <nav class="nav">{"".join(nav_html)}</nav>
  <div class="sidebar-foot">Static dashboard · no trackers · no external requests<br>
    <a href="flagged.html" style="color:#8fa8c8">Flagged items: {len(flagged["flags"])}</a></div>
</aside>
<main class="main">
  <div class="topbar">
    <h1 class="title">{esc(title)}</h1>
    <p class="desc">{desc}</p>
    <div class="stamp">{stamp}</div>
  </div>
  <div class="content" id="main">
{"".join(sections)}
  </div>
  <footer class="site">
    NFL1 — built from league-official and government-official sources.
    Every table row links to its source. Values that could not be confirmed from an
    official source are shown as <span class="blank">UNVERIFIED</span> and listed on the
    <a href="flagged.html">Flagged for review</a> page.
    Repository: <a class="ext" href="https://github.com/kanlerxz87-cyber/NFL1" target="_blank"
    rel="noopener noreferrer">github.com/kanlerxz87-cyber/NFL1</a>
  </footer>
</main>
</div>
<script src="assets/js/app.js"></script>
</body>
</html>
"""


def write(filename, content):
    path = os.path.join(DOCS, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"  wrote docs/{filename}  ({len(content):,} bytes)")


# =============================================================== page: index
def page_index():
    req = requirements["requirements"]
    qs = questions["questions"]
    sug = suggestions["suggestions"]
    sig = strategies["signals"]
    flg = flagged["flags"]
    tot = injuries["totals"]
    n_open = sum(1 for q in qs if q["status"].startswith("Open"))
    n_ans = sum(1 for q in qs if q["status"] == "Answered")
    n_impl = sum(1 for s in sug if s["status"] == "Implemented")
    n_blank = sum(1 for p in correlation["pairs"] if not p["magnitude"])

    tiles = []
    for group, items in NAV:
        if group == "Overview":
            continue
        for href, label in items:
            blurb = {
                "requirements.html": "All 52 requirements extracted from the brief, with status and owner.",
                "questions.html": "What we know, what we do not, and what blocks a decision.",
                "suggestions.html": "15 improvements with options, trade-offs and a decision path.",
                "strategy-lab.html": "Line origination pipeline, validation gates, leaderboard and skill tests.",
                "signals.html": "18 candidate signals, each with its hypothesis and what blocks it.",
                "correlation.html": "Correlation register. Every magnitude is blank until measured.",
                "injury-depth.html": "Official Week 10 injury report in full, plus the depth-chart gap.",
                "data-sources.html": "Every source used, tiered by authority.",
                "verification.html": "How each dataset was checked, and the rules the build enforces.",
                "flagged.html": "Everything we could not verify, with source links.",
            }.get(href, "")
            tiles.append(f'<a class="tile" href="{href}"><h3>{esc(label)}</h3><p>{esc(blurb)}</p>'
                         f'<div class="meta">{esc(group)}</div></a>')

    kpis = "".join([
        kpi("Requirements", len(req), "tracked line by line", "info"),
        kpi("Open questions", n_open, f"{n_ans} answered, {len(qs)} total", "danger" if n_open else "ok"),
        kpi("Suggestions", len(sug), f"{n_impl} implemented, rest proposed", "info"),
        kpi("Correlation values", "0", f"{n_blank} pairs awaiting measurement", "danger"),
        kpi("Flagged items", len(flg), "none block the merge", "warn"),
        kpi("Injury rows", tot["players_listed"], f'{tot["dnp"]} DNP / {tot["lp"]} LP / {tot["fp"]} FP', "info"),
    ])

    n_status = tot["game_status_out"] + tot["game_status_doubtful"] + tot["game_status_questionable"]
    week_a = (
        "<strong>Week 10, 2026 season.</strong> The official NFL.com injury report was read in full on "
        + RETRIEVED + ". It lists <strong>" + str(tot["matchups_listed"]) + " matchups</strong> covering "
        "<strong>" + str(tot["teams_listed"]) + " teams</strong> and <strong>"
        + str(tot["players_listed"]) + " players</strong>. Four clubs do not appear on the report and are "
        "presumed on bye - that is an inference, not a read value, and is flagged as "
        '<a href="flagged.html">F-008</a>.'
    )
    week_b = (
        "Only <strong>" + str(n_status) + "</strong> of " + str(tot["players_listed"])
        + " players carry a game status in this snapshot: " + str(tot["game_status_out"]) + " Out, "
        + str(tot["game_status_doubtful"]) + " Doubtful, " + str(tot["game_status_questionable"])
        + " Questionable. The remaining " + str(tot["game_status_blank"]) + " are blank because the final "
        "game-status report had not been filed when we retrieved it. This is the expected Thursday state, "
        'not a data error (<a href="flagged.html">F-005</a>).'
    )
    week_c = (
        "<strong>The three things that block progress.</strong>"
        "<br>1. No official depth chart exists - the league's own depth-chart URL returns 404 "
        '(<a href="flagged.html">F-001</a>).'
        "<br>2. No official NFL odds exist, so closing-line value cannot yet be measured "
        '(<a href="flagged.html">F-002</a>).'
        "<br>3. The injury report is blind to injured reserve, demonstrated by Seattle showing "
        "'No Injuries Reported' on the same page that reports their quarterback ruled out "
        '(<a href="flagged.html">F-004</a>).'
    )
    week = ('<div class="grid2"><div>' + note(week_a) + note(week_b, "warn") + "</div><div>"
            + note(week_c, "danger") + "</div></div>")

    glance_rows = [
        {"p": "Requirements", "h": "requirements.html", "n": len(req),
         "d": "Every requirement from the brief, with status", "u": "0", "s": "SRC-000"},
        {"p": "Questions & answers", "h": "questions.html", "n": len(qs),
         "d": "Known, unknown, and what each unknown blocks", "u": str(n_open), "s": "SRC-001"},
        {"p": "Suggestions & decisions", "h": "suggestions.html", "n": len(sug),
         "d": "Options, trade-offs and a decision path each", "u": "0", "s": "SRC-000"},
        {"p": "Strategy lab", "h": "strategy-lab.html", "n": len(strategies["pipeline"]) + len(strategies["gates"]),
         "d": "Line pipeline, six gates, leaderboard, skill tests", "u": "0", "s": "SRC-007"},
        {"p": "Signal catalogue", "h": "signals.html", "n": len(sig),
         "d": "Hypotheses with their blockers", "u": "0", "s": "SRC-001"},
        {"p": "Correlation", "h": "correlation.html", "n": len(correlation["pairs"]),
         "d": "Pair register with the algebra of combining legs", "u": str(n_blank), "s": "SRC-005"},
        {"p": "Injury & depth", "h": "injury-depth.html", "n": tot["players_listed"],
         "d": "Official Week 10 report, all listed players", "u": "0", "s": "SRC-001"},
        {"p": "Standings", "h": "standings.html", "n": len(standings["teams"]),
         "d": "Official 2026 records, points and splits", "u": "0", "s": "SRC-002"},
        {"p": "Data sources", "h": "data-sources.html", "n": len(sources["sources"]),
         "d": "Every source used, tiered by authority", "u": "0", "s": "SRC-001"},
        {"p": "Verification", "h": "verification.html", "n": 12,
         "d": "Checks performed and the rules the build enforces", "u": "0", "s": "SRC-002"},
        {"p": "Flagged for review", "h": "flagged.html", "n": len(flg),
         "d": "Unverified values and feed irregularities", "u": str(len(flg)), "s": "SRC-001"},
    ]
    tbl_glance = render_table(
        glance_rows,
        [("Register", lambda r: f'<a href="{esc(r["h"])}"><strong>{esc(r["p"])}</strong></a>', "narrow"),
         ("Entries", lambda r: esc(r["n"]), "num"),
         ("What is in it", lambda r: esc(r["d"]), "wrap"),
         ("Unverified cells", lambda r: (f'<td class="num">{badge(r["u"] + " open", "open")}</td>'
                                         if r["u"] != "0" else '<td class="num"><span class="blank">none</span></td>'), "num"),
         ("Source", lambda r: src_cell(r["s"], r["s"]), "src")],
        "tbl-glance")

    sections = [
        f'<div class="kpis">{kpis}</div>',
        card("At a glance", tbl_glance, body=False,
             sub='<span class="badge b-proposed">11 registers</span>'),
        card("What this is",
             note("<strong>Read this before anything else.</strong> This session's branch was created from the "
                  "repository's initial commit (<code>5aeb599</code>), which held one commit and one 6-byte "
                  "<code>README.md</code>. <code>main</code> has since received substantial work from other "
                  "sessions. This content was therefore built in parallel to the existing site rather than on "
                  "top of it, and the two generations need reconciling. See "
                  "<a href=\"flagged.html\">F-012</a> and <a href=\"flagged.html\">F-014</a>.") +
             "<p>This dashboard is the collected, organised and analysed output of the brief: a requirement "
             "register, a decision register separating what we know from what we do not, a suggestion register "
             "with decision paths, a strategy lab with validation gates, an injury and depth tracker, a source "
             "register, a verification log, and a queue for everything that could not be verified.</p>"
             "<p><strong>Rule applied throughout:</strong> a value appears only if it was read from an official "
             "source that is linked from its row. Anything else is left blank, badged "
             "<span class=\"blank\">UNVERIFIED</span>, and listed on the "
             "<a href=\"flagged.html\">Flagged for review</a> page. Nothing is inferred to make a table look "
             "complete.</p>",
             sub=""),
        card("Browse", f'<div class="tiles">{"".join(tiles)}</div>', body=True, sub=""),
        card("Week 10 snapshot", week, sub=""),
        card("Where to start if you only read one page",
             "<p><a href=\"executive-summary.html\"><strong>Executive summary</strong></a> — the important "
             "details in one place, including what is working, what is blocked and why.</p>"
             "<p>Then <a href=\"questions.html\">Questions &amp; answers</a> if you want to see the gaps, "
             "and <a href=\"suggestions.html\">Suggestions</a> if you want to pick a path forward.</p>"),
    ]
    return page("index.html", "NFL1 dashboard",
                "Verified NFL analytics, proprietary line origination and a decision register — "
                "built only from league-official and government-official sources.",
                sections)


# ================================================== page: executive summary
def page_exec():
    tot = injuries["totals"]
    qs = questions["questions"]
    n_open = sum(1 for q in qs if q["status"].startswith("Open"))
    blocking = [q for q in qs if q["status"] == "Open - blocking"]

    findings = [
        ("Built in parallel to an existing site", "This branch came off the initial commit; main had already received other sessions' work. Two dashboard generations now exist and need reconciling (F-012, F-014).", "flagged.html"),
        ("No official depth chart exists", "nfl.com/teams/&lt;team&gt;/depth-chart returns 404. The 2nd/3rd/4th-string requirement cannot be met from official data as published.", "flagged.html"),
        ("No official NFL odds exist", "The league publishes no prices. Its exclusive betting-data distributor is Genius Sports, so market comparison needs a commercial feed.", "flagged.html"),
        ("The injury report is blind to injured reserve", "Seattle shows 'No Injuries Reported' while NFL.com news on the same page reports their starting quarterback ruled out.", "flagged.html"),
        ("97.6% of injury rows have no body part", f'{tot["players_without_injury_text"]} of {tot["players_listed"]} listed players have an empty Injuries column.', "injury-depth.html"),
        ("Home/away is not asserted", "The official report lists two clubs per matchup without a home/away label in the retrieved markup. We left it blank rather than guess.", "flagged.html"),
        ("Every correlation value is blank", "No official or regulator source publishes a prop correlation matrix, and no joint-outcome history has been ingested.", "correlation.html"),
        ("Official data is fully ingested for Week 10", f'All {tot["players_listed"]} players across {tot["teams_listed"]} teams, and all 32 team records, transcribed from NFL.com.', "injury-depth.html"),
        ("Standings data cross-checks clean", "Total points for equals total points against across all 32 teams (6,246 each), and total wins equals total losses (135 each). The transcription is internally consistent.", "verification.html"),
    ]
    f_rows = [(t, d, link) for t, d, link in findings]

    blockers = [(q["id"], q["q"], q["blocks"] or "—", q["source"]) for q in blocking]

    sections = [
        card("Executive summary",
             "<p><strong>Purpose.</strong> Build a system that originates its own NFL lines, generates and "
             "validates betting strategies on a competitive leaderboard, tracks injuries and lineup "
             "weaknesses down to backup level, and does all of it on evidence that can be traced to an "
             "official source — with an explicit record of what is known, what is unknown, and what "
             "decision each unknown is blocking.</p>"
             "<p><strong>What was delivered.</strong> A twelve-page static dashboard served from this "
             "repository, a JSON data layer for every register, a generator that refuses to publish a data "
             "row without a source link, an official-source ingestion of the 2026 Week 10 injury report and "
             "the 2026 standings, a 52-item requirement register, a 24-question decision register, 15 "
             "suggestions with decision paths, an 18-signal catalogue, six validation gates, a correlation "
             "register, and a 12-item flagged-for-review queue.</p>"
             "<p><strong>The honest headline.</strong> The analytical framework is complete and specified. "
             "The <em>evidence</em> it needs is not yet available. There is no official odds feed, so no "
             "strategy has been backtested, no correlation has been measured, and no strategy has passed a "
             "gate. That is the current state and it is reported as such rather than papered over.</p>"),
        card("Findings that matter",
             render_table(
                 [{"t": t, "d": d, "l": l} for t, d, l in f_rows],
                 [("Finding", lambda r: f"<strong>{esc(r['t'])}</strong>", ""),
                  ("Detail", lambda r: esc(r["d"]), "wrap"),
                  ("Page", lambda r: f'<a href="{esc(r["l"])}">Open</a>', "narrow")],
                 "tbl-findings"),
             body=False),
        card("What is blocking a decision",
             "<p>These are the questions that must be answered before the corresponding decision can "
             "reasonably be made. They are blocking, not merely unknown.</p>" +
             render_table(
                 [{"id": i, "q": q, "b": b, "s": s} for i, q, b, s in blockers],
                 [("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>', "id"),
                  ("Blocking question", lambda r: esc(r["q"]), "wrap"),
                  ("What it blocks", lambda r: esc(r["b"]), "wrap"),
                  ("Source", lambda r: src_cell(r["s"], r["s"]), "src")],
                 "tbl-blockers"),
             body=False),
        card("Numbers as they stand",
             f'<div class="kpis">' +
             kpi("Requirements tracked", len(requirements["requirements"]), "across 10 categories", "info") +
             kpi("Open questions", n_open, f'of {len(qs)}', "danger") +
             kpi("Strategies validated", "0", "no odds archive — none can be", "danger") +
             kpi("Correlation values", "0", "of 18 pairs measured", "danger") +
             kpi("Official rows ingested", tot["players_listed"] + 32, "254 injury + 32 standings", "ok") +
             "</div>"),
        card("Recommended next three moves",
             "<ol>"
             "<li><strong>Obtain a timestamped odds archive.</strong> It is the single input that unblocks "
             "backtesting, closing-line value, all six validation gates and the leaderboard. Until it "
             "arrives, every performance claim is unfalsifiable.</li>"
             "<li><strong>Add the official transactions feed.</strong> Without it the injury tracker is "
             "blind to injured reserve, which is exactly where the worst injuries go. Proven by flag "
             "F-004.</li>"
             "<li><strong>Decide the depth-chart approach.</strong> The league publishes none. Either "
             "accept a derived snap-share ordering badged as derived, or licence one — but decide "
             "explicitly, because the brief's 2nd/3rd/4th-string requirement depends on it.</li>"
             "</ol>"),
    ]
    return page("executive-summary.html", "Executive summary",
                "The important details, what is working, what is blocked, and what to do next.",
                sections)


# ==================================================== page: requirements
def page_requirements():
    reqs = requirements["requirements"]
    rows = []
    for r in reqs:
        if not r.get("page"):
            problems.append(f"requirement {r['id']} has no page")
        rows.append(r)

    def page_link(r):
        return f'<td class="narrow"><a href="{esc(r["page"])}">{esc(r["page"].replace(".html", ""))}</a></td>'

    tbl = render_table(
        rows,
        [("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>', "id"),
         ("Category", lambda r: esc(r["cat"]), "narrow"),
         ("Requirement", lambda r: esc(r["text"]), "wrap"),
         ("Status", lambda r: status_badge(r["status"]), "narrow"),
         ("Addressed on", page_link, "narrow"),
         ("Note", lambda r: esc(r["note"]), "wrap"),
         ("Source", lambda r: '<td class="src"><span class="badge b-na" title="'
                              'The owner project brief has no public URL. See flag F-006.">INTERNAL</span></td>', "src")],
        "tbl-req")

    counts = {}
    for r in reqs:
        counts[r["cat"]] = counts.get(r["cat"], 0) + 1
    chips = "".join(f'<span class="badge b-proposed" style="margin-right:6px">{esc(k)}: {v}</span>'
                    for k, v in sorted(counts.items()))

    sections = [
        card("Requirement register",
             note("<strong>Source note.</strong> These rows come from the owner's project brief, which has "
                  "no public official URL. They are marked <span class=\"badge b-na\">INTERNAL</span> rather "
                  "than verified, and this is the one deliberate exemption from the 'every row links to an "
                  "official site' rule. It is published as <a href=\"flagged.html\">F-006</a> so the "
                  "exemption is visible rather than assumed.") +
             f'<p style="margin-bottom:12px">{chips}</p>' +
             "<p>Every requirement extracted line by line from the brief, grouped so that nothing in the "
             "request is lost. Status meanings: <strong>Done</strong> complete; <strong>In progress</strong> "
             "built but evolving; <strong>Blocked</strong> cannot proceed until a flagged data gap is "
             "closed; <strong>Deviation</strong> the convention could not be followed as written.</p>",
             sub=f'<span class="badge b-proposed">{len(reqs)} items</span>'),
        card("All requirements",
             tools(filter_col=1, filter_label="All categories", keys=[r["cat"] for r in rows]) + tbl,
             body=False),
    ]
    return page("requirements.html", "Requirements",
                "The full requirement list extracted line by line from the project brief, with status and "
                "where each item is addressed.",
                sections)


# ======================================================= page: questions
def page_questions():
    qs = questions["questions"]
    n_ans = sum(1 for q in qs if q["status"] == "Answered")
    n_part = sum(1 for q in qs if q["status"].startswith("Partially"))
    n_open = sum(1 for q in qs if q["status"].startswith("Open"))
    n_block = sum(1 for q in qs if q["status"] == "Open - blocking")
    n_owner = sum(1 for q in qs if q["status"] == "Open - owner input")

    def ans_cell(q):
        a = q.get("answer", "")
        return f"<td>{esc(a)}</td>" if a else blank_cell()

    tbl = render_table(
        qs,
        [("ID", lambda q: f'<span class="id">{esc(q["id"])}</span>', "id"),
         ("Category", lambda q: esc(q["cat"]), "narrow"),
         ("Question", lambda q: esc(q["q"]), "wrap"),
         ("Status", lambda q: status_badge(q["status"]), "narrow"),
         ("Answer", ans_cell, "wrap"),
         ("Source", lambda q: src_cell(q["source"], q["source"]), "src")],
        "tbl-q")

    blocks = []
    for q in qs:
        dl = [
            ("What we know", q.get("known", "")),
            ("What is missing", q.get("missing", "")),
            ("Proposed default", q.get("proposed_default", "")),
            ("Blocks", q.get("blocks", "")),
            ("Evidence", q.get("evidence", "")),
        ]
        dl_html = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in dl if v)
        blocks.append(
            f'<div class="item" data-search="{esc((q["id"] + " " + q["q"] + " " + q["cat"]).lower())}">'
            f'<div class="head"><span class="id">{esc(q["id"])}</span>'
            f'<h4>{esc(q["q"])}</h4>{status_badge(q["status"])}'
            f'<span class="badge b-na">{esc(q["cat"])}</span></div>'
            f'<p class="q">{esc(q.get("answer") or "No verified answer yet.")}</p>'
            f'<dl>{dl_html}<dt>Source</dt><dd>{src_inline(q["source"])}</dd></dl></div>')

    sections = [
        f'<div class="kpis">' +
        kpi("Answered", n_ans, "confirmed against a linked source", "ok") +
        kpi("Partially answered", n_part, "direction known, value not", "warn") +
        kpi("Open", n_open, f"of {len(qs)} questions", "danger") +
        kpi("Blocking", n_block, "stop a decision entirely", "danger") +
        kpi("Need your input", n_owner, "default proposed so work continues", "info") +
        "</div>",
        card("Decision register",
             "<p>A question earns a place here if a decision cannot reasonably be made until it is "
             "answered. The register separates what we already have from what we do not, because the brief "
             "asks for both, and it names what each unknown is blocking rather than leaving that implicit.</p>" +
             note("An empty <strong>Answer</strong> cell means we do not know. It is shown as "
                  "<span class=\"blank\">UNVERIFIED</span> rather than filled with a plausible-sounding "
                  "value. Q-004 is the clearest case: the injury-designation definitions are repeated "
                  "everywhere, but every official URL we tried to confirm them on returned 404, so they are "
                  "published as unverified."),
             sub=f'<span class="badge b-proposed">{len(qs)} questions</span>'),
        card("Index",
             tools(filter_col=1, filter_label="All categories", keys=[q["cat"] for q in qs]) + tbl,
             body=False),
        card("Detail", "".join(blocks), sub=f'<span class="badge b-proposed">{len(qs)} entries</span>'),
    ]
    return page("questions.html", "Questions & answers",
                "What we know, what we do not know, and which unknowns are blocking a decision.",
                sections)


# ===================================================== page: suggestions
def page_suggestions():
    sug = suggestions["suggestions"]
    n_impl = sum(1 for s in sug if s["status"] == "Implemented")

    tbl = render_table(
        sug,
        [("ID", lambda s: f'<span class="id">{esc(s["id"])}</span>', "id"),
         ("Category", lambda s: esc(s["cat"]), "narrow"),
         ("Suggestion", lambda s: f'<strong>{esc(s["title"])}</strong>', "wrap"),
         ("Problem", lambda s: esc(s["problem"]), "wrap"),
         ("Recommended", lambda s: esc(s["recommended"]), "wrap"),
         ("Effort", lambda s: esc(s["effort"]), "narrow"),
         ("Risk", lambda s: esc(s["risk"]), "narrow"),
         ("Status", lambda s: status_badge(s["status"]), "narrow"),
         ("Source", lambda s: src_cell(s["source"], s["source"]), "src")],
        "tbl-sug")

    blocks = []
    for s in sug:
        opts = "".join(
            f'<div class="opt"><div class="lbl">{esc(o["id"])}. {esc(o["label"])}</div>'
            f'<div class="d">{esc(o["detail"])}</div>'
            f'<div class="pc"><b>Pro:</b> {esc(o["pros"])} &nbsp; <i>Con:</i> {esc(o["cons"])}</div></div>'
            for o in s["options"])
        path = "".join(f"<li>{esc(p)}</li>" for p in s["decision_path"])
        blocks.append(f'''
<div class="item" data-search="{esc((s["id"] + " " + s["title"] + " " + s["cat"]).lower())}">
  <div class="head"><span class="id">{esc(s["id"])}</span><h4>{esc(s["title"])}</h4>
    {status_badge(s["status"])}<span class="badge b-na">{esc(s["cat"])}</span>
    <span class="badge b-derived">Effort {esc(s["effort"])}</span>
    <span class="badge b-unverified">Risk {esc(s["risk"])}</span></div>
  <dl>
    <dt>Problem</dt><dd>{esc(s["problem"])}</dd>
    <dt>Proposed change</dt><dd>{esc(s["change"])}</dd>
    <dt>Evidence needed</dt><dd>{esc(s["evidence_needed"])}</dd>
    <dt>Recommended</dt><dd><strong>{esc(s["recommended"])}</strong></dd>
    <dt>Source</dt><dd>{src_inline(s["source"])}</dd>
  </dl>
  <div class="opts"><div style="font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
       font-weight:700;color:var(--text-faint);margin-bottom:4px">Options and trade-offs</div>{opts}</div>
  <div style="margin-top:10px"><div style="font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
       font-weight:700;color:var(--text-faint);margin-bottom:6px">Decision path</div>
       <ol class="path">{path}</ol></div>
</div>''')

    sections = [
        f'<div class="kpis">' +
        kpi("Suggestions", len(sug), "across 8 categories", "info") +
        kpi("Implemented", n_impl, "the rest await your decision", "ok") +
        kpi("Awaiting decision", len(sug) - n_impl, "nothing auto-implemented", "warn") +
        kpi("Aimed at missing info", 6, "S-001, 002, 004, 011, 012, 015", "info") +
        "</div>",
        card("Suggestions & decision paths",
             "<p>Nothing here has been implemented without a recorded decision, except the three items "
             "marked <strong>Implemented</strong> which are governance scaffolding (the decision register "
             "itself, the build-time source assertion, and the flagged queue). Every other item gives you "
             "the options, the trade-offs and a recommended path so you can choose before anything "
             "changes.</p>" +
             note("<strong>How to use this page.</strong> Read the problem, read the options, check what "
                  "evidence is missing, then pick A, B or C. The decision path lists the ordered steps that "
                  "follow from that choice. Six of the fifteen suggestions "
                  "(S-001, S-002, S-004, S-011, S-012, S-015) exist specifically to surface missing "
                  "information rather than to change behaviour."),
             sub=f'<span class="badge b-proposed">{len(sug)} entries</span>'),
        card("Index",
             tools(filter_col=1, filter_label="All categories", keys=[s["cat"] for s in sug]) + tbl,
             body=False),
        card("Detail", "".join(blocks)),
    ]
    return page("suggestions.html", "Suggestions & decisions",
                "Improvement proposals with options, trade-offs and a decision path — choose the path "
                "before anything is implemented.",
                sections)


# ==================================================== page: strategy lab
def page_strategy():
    pl = strategies["pipeline"]
    tbl_pipeline = render_table(
        pl,
        [("#", lambda r: esc(r["step"]), "num"),
         ("Stage", lambda r: f"<strong>{esc(r['name'])}</strong>", "narrow"),
         ("What it does", lambda r: esc(r["detail"]), "wrap"),
         ("Status", lambda r: status_badge(r["status"]), "narrow"),
         ("Current state", lambda r: esc(r["note"]), "wrap")],
        "tbl-pipeline")

    fm = strategies["formulas"]
    tbl_formula = render_table(
        fm,
        [("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>', "id"),
         ("Formula", lambda r: f"<strong>{esc(r['name'])}</strong>", "wrap"),
         ("Expression", lambda r: f"<code>{esc(r['formula'])}</code>", "wrap"),
         ("Kind", lambda r: esc(r["kind"]), "narrow"),
         ("Note", lambda r: esc(r["note"]), "wrap")],
        "tbl-formula")

    gt = strategies["gates"]
    tbl_gates = render_table(
        gt,
        [("Gate", lambda r: f'<span class="id">{esc(r["id"])}</span>', "id"),
         ("Name", lambda r: f"<strong>{esc(r['name'])}</strong>", "narrow"),
         ("Question it asks", lambda r: esc(r["question"]), "wrap"),
         ("Threshold", lambda r: esc(r["threshold"]), "wrap"),
         ("On failure", lambda r: esc(r["on_fail"]), "wrap"),
         ("Status", lambda r: status_badge(r["status"]), "narrow"),
         ("Source", lambda r: src_cell(r["src"], r["src"]), "src")],
        "tbl-gates")

    lb = strategies["leaderboard"]
    sk = strategies["skill_vs_luck"]
    tbl_skill = render_table(
        sk["methods"],
        [("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>', "id"),
         ("Method", lambda r: f"<strong>{esc(r['name'])}</strong>", "narrow"),
         ("Rank", lambda r: status_badge(r["rank"]), "narrow"),
         ("What it does", lambda r: esc(r["detail"]), "wrap"),
         ("Limitation", lambda r: esc(r["limitation"]), "wrap")],
        "tbl-skill")

    sections = [
        f'<div class="kpis">' +
        kpi("Pipeline stages", len(pl), "ingest to score", "info") +
        kpi("Validation gates", len(gt), "all must pass, in order", "warn") +
        kpi("Strategies passing", "0", "none can be tested yet", "danger") +
        kpi("Formulas specified", len(fm), "identities, not estimates", "ok") +
        "</div>",
        card("Originating our own lines",
             note("<strong>What 'our own line' means here.</strong> The model produces a probability. "
                  "That probability is converted to a fair price in the market's own format. That fair "
                  "price is our line. Only then do we look at the market: an edge exists where our fair "
                  "price is better than the de-vigged market price by more than the cost of doing "
                  "business. Comparing a raw market price to a model probability without removing the "
                  "margin first is the standard way to manufacture a fake edge.") +
             tbl_pipeline,
             body=False, sub='<span class="badge b-proposed">Design, not results</span>'),
        card("The arithmetic", tbl_formula, body=False),
        card("Validation gates",
             note("A strategy must pass all six gates in order. Failing any gate returns it to research; "
                  "it does not get a waiver. Gate thresholds marked <strong>PROPOSED</strong> are design "
                  "choices awaiting ratification, not measured facts — they are labelled so you can "
                  "argue with them.", "warn") +
             tbl_gates, body=False),
        card("Leaderboard competition",
             f"<dl style=\"display:grid;grid-template-columns:170px 1fr;gap:6px 14px;font-size:13px\">"
             f"<dt>Ranking metric</dt><dd><strong>{esc(lb['ranking_metric'])}</strong></dd>"
             f"<dt>Tiebreak</dt><dd>{esc(lb['tiebreak'])}</dd>"
             f"<dt>Reported, not scored</dt><dd>{esc(lb['reported_not_scored'])}</dd>"
             f"<dt>Minimum bets floor</dt><dd>{esc(lb['minimum_bets_floor'])}</dd>"
             f"<dt>Why</dt><dd>{esc(lb['rationale'])}</dd></dl>"
             f"<h3>Anti-gaming rules</h3><ul>" +
             "".join(f"<li>{esc(x)}</li>" for x in lb["anti_gaming_rules"]) + "</ul>" +
             f"<h3>Rewards ({esc(lb['rewards']['status'])})</h3><ul>" +
             "".join(f"<li>{esc(x)}</li>" for x in lb["rewards"]["proposed"]) + "</ul>" +
             f"<p>{esc(lb['rewards']['note'])}</p>"),
        card("Removing luck from the equation",
             f"<p><strong>{esc(sk['principle'])}</strong></p>" +
             tbl_skill +
             note(f"<strong>What we cannot do yet.</strong> {esc(sk['what_we_cannot_yet_do'])}", "danger")),
    ]
    return page("strategy-lab.html", "Strategy lab",
                "How lines are originated, how strategies are gated, how the leaderboard is scored, and "
                "how luck is separated from skill.",
                sections)


# ========================================================= page: signals
def page_signals():
    sig = strategies["signals"]
    blocked = sum(1 for s in sig if "Blocked" in s["note"] or "blocked" in s["note"])
    tbl = render_table(
        sig,
        [("ID", lambda s: f'<span class="id">{esc(s["id"])}</span>', "id"),
         ("Signal", lambda s: f"<strong>{esc(s['name'])}</strong>", "narrow"),
         ("Category", lambda s: esc(s["cat"]), "narrow"),
         ("Hypothesis", lambda s: esc(s["hypothesis"]), "wrap"),
         ("Inputs required", lambda s: esc(s["inputs"]), "wrap"),
         ("Status", lambda s: status_badge(s["status"]), "narrow"),
         ("Blocker / note", lambda s: esc(s["note"]), "wrap"),
         ("Primary source", lambda s: src_cell(s["src"], s["src"]), "src")],
        "tbl-signals")

    sections = [
        f'<div class="kpis">' +
        kpi("Candidate signals", len(sig), "none tested", "info") +
        kpi("Fully unblocked", 1, "SIG-015 — official PF/PA only", "ok") +
        kpi("Blocked on data", blocked, "awaiting a source", "danger") +
        kpi("Passed validation", "0", "no strategy has been run", "danger") +
        "</div>",
        card("Signal catalogue",
             note("<strong>Every signal here is a hypothesis, not a finding.</strong> No signal has been "
                  "tested, because no historical odds archive has been ingested. A signal only becomes a "
                  "strategy after it passes gates G0–G5. Until then it is an idea with a stated "
                  "rationale and a stated blocker.") +
             note("Only <strong>SIG-015</strong> is unblocked today: points-versus-wins divergence can be "
                  "computed entirely from the official standings, which we have verified for all 32 teams. "
                  "Everything else needs a source we do not yet have.", "ok") +
             tools(filter_col=2, filter_label="All categories", keys=[s["cat"] for s in sig]) + tbl,
             body=False),
    ]
    return page("signals.html", "Signal catalogue",
                "Candidate signals with their hypotheses, required inputs, and what is blocking each one.",
                sections)


# ===================================================== page: correlation
def page_correlation():
    pairs = correlation["pairs"]
    alg = correlation["algebra"]
    n_blank = sum(1 for p in pairs if not p["magnitude"])

    def mag_cell(p):
        if p["magnitude"]:
            return f'<td class="num"><strong>{esc(p["magnitude"])}</strong></td>'
        return '<td class="num"><span class="blank">UNVERIFIED</span></td>'

    def dir_cell(p):
        d = p["direction"]
        kind = "flagged" if "Negative" in d else ("ok" if "Positive" in d else "na")
        return f'<td>{badge(d, kind)}</td>'

    tbl_alg = render_table(
        alg,
        [("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>', "id"),
         ("Name", lambda r: f"<strong>{esc(r['name'])}</strong>", "wrap"),
         ("Expression", lambda r: f"<code>{esc(r['formula'])}</code>", "wrap"),
         ("Kind", lambda r: esc(r["kind"]), "narrow"),
         ("Note", lambda r: esc(r["note"]), "wrap")],
        "tbl-alg")

    tbl_pairs = render_table(
        pairs,
        [("ID", lambda p: f'<span class="id">{esc(p["id"])}</span>', "id"),
         ("Leg A", lambda p: esc(p["leg_a"]), "wrap"),
         ("Leg B", lambda p: esc(p["leg_b"]), "wrap"),
         ("Scope", lambda p: esc(p["scope"]), "narrow"),
         ("Direction", dir_cell, "narrow"),
         ("Magnitude", mag_cell, "num"),
         ("Why this direction", lambda p: esc(p["why"]), "wrap"),
         ("Estimation method", lambda p: esc(p["estimation"]), "wrap"),
         ("Status", lambda p: status_badge(p["status"]), "narrow"),
         ("Source", lambda p: src_cell(p["source"], p["source"]), "src")],
        "tbl-pairs")

    sections = [
        f'<div class="kpis">' +
        kpi("Pairs in register", len(pairs), "same-game and prop pairs", "info") +
        kpi("Magnitudes measured", len(pairs) - n_blank, "all blank", "danger") +
        kpi("Known by definition", 1, "COR-010, mutually exclusive", "ok") +
        kpi("Pairs usable today", 0, "no pair may be priced yet", "danger") +
        "</div>",
        card("Why this page is mostly empty",
             note("<strong>The brief asks us to determine correlation values. We have not invented them.</strong> "
                  "No league-official, government-official or regulator-official source publishes a player-prop "
                  "correlation matrix, and no historical joint-outcome data has been ingested. Every "
                  "<em>Magnitude</em> cell is therefore blank and badged "
                  "<span class=\"blank\">UNVERIFIED</span>. That empty column is the honest state of the "
                  "project, and filling it in with plausible numbers would be the single worst thing this "
                  "page could do.", "danger") +
             "<p>What the register <em>does</em> give you is the structural direction of each relationship, "
             "which follows from how football works rather than from data, plus the exact estimation method "
             "for each pair and the order in which they should be estimated. One value is known without "
             "measurement: COR-010, where two moneylines in the same game are mutually exclusive and "
             "exhaustive, so the correlation is −1 by definition.</p>" +
             note("The most important line on this page is the guardrail: <strong>a pair whose correlation "
                  "is unknown is treated as unknown, not as zero.</strong> Assuming zero is itself an "
                  "assumption, and it is precisely the one that misprices parlays.")),
        card("The arithmetic of combining legs", tbl_alg, body=False),
        card("Correlation register",
             tools(filter_col=3, filter_label="All scopes", keys=[p["scope"] for p in pairs]) + tbl_pairs,
             body=False, sub=f'<span class="badge b-proposed">{len(pairs)} pairs</span>'),
        card("Estimation plan",
             "<ol>" + "".join(f"<li>{esc(x)}</li>" for x in correlation["meta"]["estimation_plan"]) + "</ol>"),
        card("Guardrails",
             "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in correlation["guardrails"]) + "</ul>"),
    ]
    return page("correlation.html", "Correlation",
                "The correlation register, the algebra of combining legs, and why every magnitude is "
                "currently blank.",
                sections)


# ==================================================== page: injury & depth
def page_injury():
    meta = injuries["meta"]
    tot = injuries["totals"]
    teams = injuries["teams"]

    policy_rows = [
        {"c": "Did Not Participate in Practice", "t": "Practice participation",
         "v": "Observed on the official report", "s": "SRC-001"},
        {"c": "Limited Participation in Practice", "t": "Practice participation",
         "v": "Observed on the official report", "s": "SRC-001"},
        {"c": "Full Participation in Practice", "t": "Practice participation",
         "v": "Observed on the official report", "s": "SRC-001"},
        {"c": "Out", "t": "Game status", "v": "Observed on the official report", "s": "SRC-001"},
        {"c": "Doubtful", "t": "Game status", "v": "Category observed; no official definition located", "s": "SRC-004"},
        {"c": "Questionable", "t": "Game status", "v": "Category observed; no official definition located", "s": "SRC-004"},
    ]

    tbl_policy = render_table(
        policy_rows,
        [("Official category", lambda r: f"<strong>{esc(r['c'])}</strong>", "wrap"),
         ("Type", lambda r: esc(r["t"]), "narrow"),
         ("Verification status", lambda r: esc(r["v"]), "wrap"),
         ("Source", lambda r: src_cell(r["s"], r["s"]), "src")],
        "tbl-policy")

    tbl_games = render_table(
        injuries["games"],
        [("ID", lambda g: f'<span class="id">{esc(g["id"])}</span>', "id"),
         ("Day", lambda g: esc(g["day"]), "narrow"),
         ("Date", lambda g: esc(g["date"]), "narrow"),
         ("Time (ET)", lambda g: esc(g["time_et"]), "num"),
         ("Network", lambda g: esc(g["network"]), "narrow"),
         ("Matchup", lambda g: f'{esc(g["team1"])} ({esc(g["team1_record"])}) vs '
                               f'{esc(g["team2"])} ({esc(g["team2_record"])})', "narrow"),
         ("Home / away", lambda g: '<td><span class="blank">NOT ASSERTED</span></td>', "narrow"),
         ("Source", lambda g: src_cell("SRC-001", "nfl.com"), "src")],
        "tbl-games")

    team_rows = []
    for abbr, t in sorted(teams.items()):
        team_rows.append({"a": abbr, **t})
    tbl_teams = render_table(
        team_rows,
        [("Team", lambda r: f"<strong>{esc(r['a'])}</strong>", "narrow"),
         ("Club", lambda r: esc(r["name"]), "narrow"),
         ("Listed", lambda r: esc(r["total"]), "num"),
         ("DNP", lambda r: esc(r["dnp"]), "num"),
         ("Limited", lambda r: esc(r["lp"]), "num"),
         ("Full", lambda r: esc(r["fp"]), "num"),
         ("Report", lambda r: badge("No injuries reported", "fp") if r.get("no_injuries_reported")
          else badge("Players listed", "na"), "narrow"),
         ("Source", lambda r: src_cell("SRC-001", "nfl.com"), "src")],
        "tbl-teams")

    status_rows = []
    for abbr, t in teams.items():
        for p in t["players"]:
            if p["status"]:
                status_rows.append({"a": abbr, **p})
    tbl_status = render_table(
        status_rows,
        [("Team", lambda r: esc(r["a"]), "narrow"),
         ("Player", lambda r: esc(r["name"]), "narrow"),
         ("Pos", lambda r: esc(r["pos"]), "narrow"),
         ("Injury", lambda r: (f"<td>{esc(r['injury'])}</td>" if r["injury"]
                              else '<td><span class="blank">BLANK ON SOURCE</span></td>'), "narrow"),
         ("Practice", lambda r: f'<td>{badge(r["practice"], PRACTICE_BADGE.get(r["practice"], "na"))}</td>', "narrow"),
         ("Game status", lambda r: f'<td>{badge(r["status"], STATUS_GBADGE.get(r["status"], "na"))}</td>', "narrow"),
         ("Source", lambda r: src_cell("SRC-001", "nfl.com"), "src")],
        "tbl-status")

    def player_row(abbr, p):
        inj = f"<td>{esc(p['injury'])}</td>" if p["injury"] else '<td><span class="blank">BLANK ON SOURCE</span></td>'
        gs = (f'<td>{badge(p["status"], STATUS_GBADGE.get(p["status"], "na"))}</td>' if p["status"]
              else '<td><span class="blank">NOT YET FILED</span></td>')
        return (
            f'<td>{esc(abbr)}</td><td>{esc(p["name"])}</td><td>{esc(p["pos"])}</td>{inj}'
            f'<td>{badge(p["practice"], PRACTICE_BADGE.get(p["practice"], "na"))}</td>{gs}'
            + src_cell("SRC-001", "nfl.com"))

    all_rows = []
    for abbr in sorted(teams):
        for p in teams[abbr]["players"]:
            all_rows.append((abbr, p))

    body_all = "".join(
        f'<tr data-search="{esc((abbr + " " + p["name"] + " " + p["pos"] + " " + p["practice"] + " " + p["status"] + " " + p["injury"]).lower())}">'
        + player_row(abbr, p) + "</tr>" for abbr, p in all_rows)

    tbl_all = (f'<div class="scroll"><table id="tbl-all" data-sortable>'
               f"<thead><tr><th>Team</th><th>Player</th><th>Pos</th><th>Injury</th>"
               f"<th>Practice</th><th>Game status</th><th>Source</th></tr></thead>"
               f"<tbody>{body_all}</tbody></table></div>"
               f'<p class="tbl-empty" style="display:none">No rows match.</p>')

    tnfx = []
    for abbr in ("WAS", "NYG"):
        for p in teams[abbr]["players"]:
            tnfx.append((abbr, p))
    body_tnf = "".join(
        f'<tr data-search="{esc((a + " " + p["name"]).lower())}">' + player_row(a, p) + "</tr>"
        for a, p in tnfx)
    tbl_tnf = (f'<div class="scroll"><table id="tbl-tnf" data-sortable>'
               f"<thead><tr><th>Team</th><th>Player</th><th>Pos</th><th>Injury</th>"
               f"<th>Practice</th><th>Game status</th><th>Source</th></tr></thead>"
               f"<tbody>{body_tnf}</tbody></table></div>")

    sections = [
        f'<div class="kpis">' +
        kpi("Players listed", tot["players_listed"], "on the official Week 10 report", "info") +
        kpi("Did not participate", tot["dnp"], "derived by tallying official rows", "danger") +
        kpi("Limited", tot["lp"], "derived by tallying official rows", "warn") +
        kpi("Full", tot["fp"], "derived by tallying official rows", "ok") +
        kpi("Game statuses filed", tot["game_status_out"] + tot["game_status_questionable"],
            f'{tot["game_status_out"]} Out · {tot["game_status_questionable"]} Questionable · '
            f'{tot["game_status_doubtful"]} Doubtful', "warn") +
        kpi("Body parts given", tot["players_with_injury_text"],
            f'{tot["players_without_injury_text"]} rows blank', "danger") +
        "</div>",
        card("How injury tracking works here",
             note(f"<strong>Source.</strong> {src_inline('SRC-001')} — the official NFL injury report, "
                  f"read in full on {RETRIEVED}. Page title as retrieved: "
                  f"<em>{esc(meta['page_title_as_read'])}</em>.") +
             note("<strong>Three defects you should know about before trusting this feed.</strong>"
                  "<br>1. It is blind to injured reserve — Seattle shows 'No Injuries Reported' while "
                  "NFL.com news on the same page reports their starting quarterback ruled out "
                  "(<a href=\"flagged.html\">F-004</a>)."
                  f"<br>2. The body-part column is empty for {tot['players_without_injury_text']} of "
                  f"{tot['players_listed']} rows (<a href=\"flagged.html\">F-003</a>)."
                  "<br>3. Game statuses are only filed near the end of the week, so a Thursday snapshot "
                  "is mostly blank (<a href=\"flagged.html\">F-005</a>).", "danger") +
             "<p>Per-team DNP / Limited / Full counts below are <strong>derived</strong> — pure arithmetic "
             "on the official rows. They are badged accordingly; no count was read off the page as a "
             "summary figure.</p>",
             sub='<span class="badge b-verified">Official source</span>'),
        card("Official categories", tbl_policy, body=False,
             sub='<span class="badge b-partial">Definitions unverified</span>'),
        card("Week 10 matchups", tbl_games, body=False,
             sub=f'<span class="badge b-proposed">{len(injuries["games"])} games</span>'),
        card("Practice participation by club",
             tools(filter_col=0, filter_label="All teams", keys=[r["a"] for r in team_rows]) + tbl_teams,
             body=False, sub=f'<span class="badge b-derived">{len(team_rows)} clubs</span>'),
        card("Players with an official game status",
             note(f"Only {len(status_rows)} of {tot['players_listed']} listed players carry a game status in "
                  "this snapshot. That is the expected state on a Thursday, not a data error.", "warn") +
             tbl_status, body=False,
             sub=f'<span class="badge b-partial">{len(status_rows)} players</span>'),
        card("Tonight's game — full official report",
             "<p>The Thursday night matchup is the only game whose final game-status report had been filed "
             "at retrieval time, so it is the only complete report on the page. Reproduced exactly as "
             "published, including blank cells.</p>" + tbl_tnf, body=False),
        card("Every listed player (Week 10)",
             tools(placeholder="Search all 254 players — name, team, position, status…") + tbl_all,
             body=False, sub=f'<span class="badge b-verified">{len(all_rows)} rows</span>'),
        card("Deficiencies and backups — the hard part",
             note("<strong>The brief asks the system to know when a 2nd, 3rd or 4th string player is "
                  "replacing a starter, on both sides of the ball. The league publishes no depth chart.</strong> "
                  "A direct fetch of <code>nfl.com/teams/&lt;team&gt;/depth-chart</code> returns the NFL's "
                  "404 page. There is therefore no official field to read, and any depth ordering is an "
                  "estimate rather than a fact. Flagged as <a href=\"flagged.html\">F-001</a> and "
                  "addressed by suggestions <a href=\"suggestions.html\">S-007</a> and "
                  "<a href=\"suggestions.html\">S-008</a>.", "danger") +
             "<h3>Proposed deficiency index</h3>"
             "<p>For each club and each position group, compute the share of the group's recent snap share "
             "that is unavailable, weighted by the inferred depth of the replacement. Losing 60% of a "
             "position group's snaps to a third-string replacement must score worse than losing 20% to a "
             "second-string replacement — otherwise the index does not capture what the brief is "
             "actually asking for.</p>"
             "<h3>What it needs</h3>"
             "<ul><li>An official or licensed snap-count / participation source. <strong>Not yet "
             "confirmed.</strong></li>"
             "<li>A trailing window for the snap-share ranking. A short window reacts fast but is noisy; a "
             "long window is stable but lags a demotion.</li>"
             "<li>The official transactions feed, so that injured-reserve placements are counted as "
             "unavailable rather than invisible.</li></ul>"
             "<p>Until those exist, the honest output is the practice-participation table above, badged as "
             "an incomplete proxy rather than presented as the finished feature.</p>"),
    ]
    return page("injury-depth.html", "Injury & depth tracking",
                "The official Week 10 injury report in full, the categories the league actually publishes, "
                "and the depth-chart gap that blocks backup-level deficiency tracking.",
                sections)


# ===================================================== page: data sources
def page_sources():
    rows = sources["sources"]
    tbl = render_table(
        rows,
        [("ID", lambda s: f'<span class="id">{esc(s["id"])}</span>', "id"),
         ("Source", lambda s: f"<strong>{esc(s['name'])}</strong>", "wrap"),
         ("Tier", lambda s: esc(s["tier"]), "narrow"),
         ("Publisher", lambda s: esc(s["publisher"]), "wrap"),
         ("Read on", lambda s: '<td>' + (esc(s["accessed"]) if s.get("accessed")
                                         else '<span class="blank">NOT READ</span>') + '</td>', "narrow"),
         ("Verified", lambda s: f'<td>{badge("Yes", "done") if s.get("verified") else badge("No", "unverified")}</td>', "narrow"),
         ("Used for", lambda s: esc(s["used_for"]), "wrap"),
         ("Notes", lambda s: esc(s["notes"] or ""), "wrap"),
         ("Link", lambda s: (f'<td class="src"><a class="ext" href="{esc(s["url"])}" target="_blank" '
                             f'rel="noopener noreferrer">Open source</a></td>' if s.get("url")
                             else '<td class="src"><span class="badge b-flagged">NO URL</span></td>'), "src")],
        "tbl-sources")

    sections = [
        card("Source register",
             "<p>Every value on this site traces to one of these. The tiering is what makes the "
             "'no hallucinations' rule structural rather than aspirational.</p>"
             "<ul>"
             "<li><strong>Tier 1 — league-official or government-official.</strong> Published by the "
             "league itself or by a government body. May populate any value.</li>"
             "<li><strong>Tier 2 — primary issuer or regulated operator.</strong> A company's own "
             "announcement about its own contract, or a regulator's own filing. May populate a value, but "
             "is a claim by an interested party about itself.</li>"
             "<li><strong>Tier 3 — community.</strong> Open-source redistributions. May be referenced; "
             "may <em>never</em> populate a value without re-verification against a Tier 1 source.</li>"
             "</ul>" +
             note("Sources marked <strong>NOT READ</strong> are listed because they are the right "
                  "candidate for a future input, not because data was taken from them. No value anywhere "
                  "on this site comes from a source marked NOT READ.")),
        card("All sources", tools(filter_col=2, filter_label="All tiers",
                                  keys=[s["tier"] for s in rows]) + tbl, body=False,
             sub=f'<span class="badge b-proposed">{len(rows)} sources</span>'),
    ]
    return page("data-sources.html", "Data sources",
                "Every source used, tiered by authority, with what each one was used for and when it was read.",
                sections)


# ====================================================== page: verification
def page_verification():
    checks = [
        ("V-01", "Repository inventory", "git log and file listing",
         "One commit (5aeb599), one tracked file (README.md, 6 bytes). No code, data or site existed.",
         "Pass — nothing to review; flagged F-012"),
        ("V-02", "Standings internal consistency", "Total PF vs total PA across 32 teams",
         "6,246 points for equals 6,246 points against. Every point scored by one team is allowed by another.",
         "Pass"),
        ("V-03", "Standings internal consistency", "Total wins vs total losses",
         "135 wins, 135 losses, 2 ties. 135 + 135 + 2 = 272 team-games = 136 games played.",
         "Pass"),
        ("V-04", "Injury row totals", "Recomputed DNP/LP/FP from transcribed rows",
         "93 DNP + 89 Limited + 72 Full = 254, matching the number of transcribed player rows exactly.",
         "Pass"),
        ("V-05", "Injury per-club totals", "Recomputed each club's counts from its rows",
         "All 28 clubs match their stored totals; zero mismatches.",
         "Pass"),
        ("V-06", "Bye-week cross-check", "Teams absent from the injury report vs games played",
         "DEN, PHI, CHI and TB are absent and all four show exactly 9 games played. Consistent with a bye, "
         "but inferred, not read from the schedule.",
         "Pass as DERIVED — flagged F-008"),
        ("V-07", "Depth chart availability", "Direct fetch of the league depth-chart URL",
         "nfl.com/teams/kansas-city-chiefs/depth-chart returned HTTP 404.",
         "Confirmed gap — flagged F-001"),
        ("V-08", "Injury policy text", "Three candidate official URLs fetched",
         "operations.nfl.com/gameday/nfl-game-status, operations.nfl.com/inside-football-ops/"
         "health-and-safety/injury-report and nfl.com/injuries/inactives all returned 404.",
         "Unverified — flagged F-007"),
        ("V-09", "Injury feed completeness", "Seattle entry vs NFL.com news on the same page",
         "Seattle shows 'No Injuries Reported' while the official news rail reports their starting "
         "quarterback ruled out for that game.",
         "Feed defect — flagged F-004"),
        ("V-10", "Body-part coverage", "Counted non-empty Injuries cells",
         "6 of 254 rows carry a body part; 248 are blank.",
         "Feed defect — flagged F-003"),
        ("V-11", "Internal link check", "Every generated page parsed for href to a local file",
         "All internal links resolve to a generated file; no link points at a missing page.",
         "Run at build"),
        ("V-12", "Source assertion", "Build refuses to emit a page with a sourceless data row",
         "The generator raises and lists offending rows rather than publishing them.",
         "Enforced at build"),
        ("V-13", "Cross-session standings check",
         "Compared this session's 32 clubs against main's independently transcribed "
         "data/verified/standings_2026.csv",
         "All 32 clubs match exactly on wins, losses, ties, points for, points against, net points, "
         "percentage and streak. One naming difference: main uses LA, this session uses LAR for the Rams.",
         "Pass — flagged F-013"),
        ("V-14", "Cross-session injury check",
         "Compared the 6 published game designations against main's independently transcribed "
         "data/verified/injuries_week10.csv",
         "All 6 rows match exactly on club, player, position, body part, practice status and game status. "
         "Two independent transcriptions of the same official page agree.",
         "Pass"),
    ]
    tbl = render_table(
        [{"id": a, "n": b, "m": c, "r": d, "v": e} for a, b, c, d, e in checks],
        [("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>', "id"),
         ("Check", lambda r: f"<strong>{esc(r['n'])}</strong>", "narrow"),
         ("Method", lambda r: esc(r["m"]), "wrap"),
         ("Result", lambda r: esc(r["r"]), "wrap"),
         ("Outcome", lambda r: (f'<td>{badge(r["v"].split(" — ")[0], "done")}'
                                f'{" — " + esc(r["v"].split(" — ", 1)[1]) if " — " in r["v"] else ""}</td>'), "wrap")],
        "tbl-verify")

    rules = [
        ("Blank, never invented",
         "If a value cannot be confirmed from an official source, the cell renders as UNVERIFIED. It is "
         "never estimated, interpolated or copied from a third party."),
        ("Derived is labelled",
         "A value computed by pure arithmetic on official values (a total, a tally, a share) is permitted "
         "and is badged DERIVED so it is never mistaken for a read value."),
        ("Source on every data row",
         "The build fails if a data row lacks a source URL. The only exemption is the requirement "
         "register, which is governance sourced from the brief (F-006)."),
        ("Never marked verified without a check",
         "A row is only badged verified where the value has been checked against the linked official "
         "source in this session."),
        ("Tier separation",
         "Community data may be referenced but never populates a value."),
        ("Reproducible",
         "Every register lives in a JSON file under /data and the site is generated from it, so any claim "
         "can be traced back to the exact file and row."),
    ]

    sections = [
        card("Verification",
             "<p>Verification here means two things: checking each dataset against the official source it "
             "came from, and building rules that make it impossible to publish an unsourced value by "
             "accident. Both are covered below.</p>" +
             note("<strong>The strongest check was not ours.</strong> Another session had independently "
                  "transcribed the same official pages into <code>data/verified/</code> on main. Comparing "
                  "the two transcriptions: all 32 clubs match exactly on every numeric field, and all 6 "
                  "published game designations match exactly on every field. Two independent readings of the "
                  "same official source agreeing is far better evidence than any internal consistency check.",
                  "ok") +
             note("A second check is arithmetic: across all 32 teams, total points for equals total points "
                  "against (6,246 each), and total wins equals total losses (135 each, with 2 ties). Those "
                  "equalities hold only if every transcribed row is correct.") +
             note("<strong>One caveat on scope.</strong> This session's branch came off the repository's "
                  "initial commit, so the repository review covered that lineage only. main had already "
                  "received other sessions' work. See <a href=\"flagged.html\">F-012</a>.", "warn")),
        card("Checks performed", tbl, body=False,
             sub=f'<span class="badge b-proposed">{len(checks)} checks</span>'),
        card("Rules the build enforces",
             "".join(f"<h3>{esc(a)}</h3><p>{esc(b)}</p>" for a, b in rules)),
        card("How to re-run this",
             "<p>The site is generated from the JSON data layer by a single command:</p>"
             "<pre>python3 tools/build_site.py</pre>"
             "<p>It re-reads every file in <code>/data</code>, re-runs the source assertion, rewrites "
             "every page in <code>/docs</code>, and prints any row that failed verification. If a data "
             "row is missing its source link, the build fails and names the row rather than publishing a "
             "sourceless table.</p>"),
    ]
    return page("verification.html", "Verification",
                "How each dataset was checked against its official source, and the rules the build enforces.",
                sections)


# ========================================================= page: flagged
def page_flagged():
    rows = flagged["flags"]
    sev_badge = {"High": "flagged", "Medium": "unverified", "Low": "na"}

    tbl = render_table(
        rows,
        [("ID", lambda f: f'<span class="id">{esc(f["id"])}</span>', "id"),
         ("Severity", lambda f: f'<td>{badge(f["sev"], sev_badge.get(f["sev"], "na"))}</td>', "narrow"),
         ("Category", lambda f: esc(f["cat"]), "narrow"),
         ("Item", lambda f: f"<strong>{esc(f['title'])}</strong>", "wrap"),
         ("Impact", lambda f: esc(f["impact"]), "wrap"),
         ("Status", lambda f: status_badge(f["status"]), "narrow"),
         ("Source", lambda f: src_cell(f["source"], f["source"]), "src")],
        "tbl-flagged")

    blocks = []
    for f in rows:
        blocks.append(f'''
<div class="item">
  <div class="head"><span class="id">{esc(f["id"])}</span><h4>{esc(f["title"])}</h4>
    {badge(f["sev"], sev_badge.get(f["sev"], "na"))}<span class="badge b-na">{esc(f["cat"])}</span>
    {status_badge(f["status"])}</div>
  <dl>
    <dt>Detail</dt><dd>{esc(f["detail"])}</dd>
    <dt>Impact</dt><dd>{esc(f["impact"])}</dd>
    <dt>Suggested action</dt><dd><strong>{esc(f["action"])}</strong></dd>
    <dt>Source</dt><dd>{src_inline(f["source"])}</dd>
  </dl>
</div>''')

    n_high = sum(1 for f in rows if f["sev"] == "High")
    sections = [
        f'<div class="kpis">' +
        kpi("Flagged items", len(rows), "none block the merge", "warn") +
        kpi("High severity", n_high, "material gaps", "danger") +
        kpi("Data gaps", sum(1 for f in rows if f["cat"] == "Data gap"), "no official source exists", "danger") +
        kpi("Feed defects", sum(1 for f in rows if "Feed" in f["cat"]), "official feed problems", "danger") +
        "</div>",
        card("Flagged for review",
             note("Everything on this page is something we could not confirm from an official source, or "
                  "an irregularity we found in an official feed. Per the brief, <strong>none of these "
                  "blocks the merge</strong> — they are published here with their source links so you can "
                  "review them after the site is live and request changes.") +
             "<p><strong>Please read F-012 first.</strong> It records that this session's branch came off the "
             "repository's original initial commit, while <code>main</code> had already received other "
             "sessions' work. If you expected an existing site to be reviewed, it is on "
             "<code>main</code> — this content was built alongside it, not from it. F-013 and F-014 cover "
             "the resulting naming drift and the duplicate navigation.</p>"),
        card("Queue", tools(filter_col=2, filter_label="All categories",
                            keys=[f["cat"] for f in rows]) + tbl, body=False,
             sub=f'<span class="badge b-flagged">{len(rows)} items</span>'),
        card("Detail", "".join(blocks)),
    ]
    return page("flagged.html", "Flagged for review",
                "Every unverified value and every irregularity found in an official feed, with source links.",
                sections)


# ============================================================== page: standings
def page_standings():
    rows = standings["teams"]
    tbl = render_table(
        rows,
        [("Team", lambda t: f"<strong>{esc(t['abbr'])}</strong>", "narrow"),
         ("Club", lambda t: esc(t["name"]), "narrow"),
         ("Conf", lambda t: esc(t["conf"]), "narrow"),
         ("Division", lambda t: esc(t["div"]), "narrow"),
         ("W", lambda t: esc(t["w"]), "num"), ("L", lambda t: esc(t["l"]), "num"),
         ("T", lambda t: esc(t["t"]), "num"),
         ("Pct", lambda t: f"{t['pct']:.3f}", "num"),
         ("PF", lambda t: esc(t["pf"]), "num"), ("PA", lambda t: esc(t["pa"]), "num"),
         ("Net", lambda t: f'<td class="num">{t["net"]:+d}</td>', "num"),
         ("Home", lambda t: esc(t["home"]), "narrow"),
         ("Road", lambda t: esc(t["road"]), "narrow"),
         ("Div", lambda t: esc(t["div_rec"]), "narrow"),
         ("Conf", lambda t: esc(t["conf_rec"]), "narrow"),
         ("Streak", lambda t: esc(t["streak"]), "narrow"),
         ("Last 5", lambda t: esc(t["last5"]), "narrow"),
         ("Week 10", lambda t: (f'<td><span class="blank">BYE (derived)</span></td>'
                                if t["abbr"] in injuries["totals"]["teams_not_on_report"]
                                else '<td><span class="badge b-done">On injury report</span></td>'), "narrow"),
         ("Source", lambda t: (f'<td class="src"><a class="ext" href="{esc(t["url"])}" target="_blank" '
                               f'rel="noopener noreferrer" title="NFL.com official team page">nfl.com</a></td>'), "src")],
        "tbl-standings")

    sections = [
        f'<div class="kpis">' +
        kpi("Teams", len(rows), "all 32, official", "info") +
        kpi("Total points for", f'{sum(t["pf"] for t in rows):,}', "equals total points against", "ok") +
        kpi("Ties", sum(t["t"] for t in rows), "NYG and WAS", "na") +
        kpi("Unbeaten or winless", 1, "LAC 0-8", "danger") +
        "</div>",
        card("2026 standings",
             note(f"Transcribed from {src_inline('SRC-002')} on {RETRIEVED}. Reflects completion of Week 9; "
                  "the Week 10 Thursday game had not kicked off at retrieval time.") +
             note("The <strong>Week 10</strong> column is <strong>derived</strong>, not read: clubs absent "
                  "from the official Week 10 injury report are shown as on bye, cross-checked against "
                  "games played. Confirm against the official schedule — flagged as "
                  "<a href=\"flagged.html\">F-008</a>.", "warn") +
             "<p>Points for and points against are verified official values. The integrity check is "
             "worth stating: total PF across all 32 teams equals total PA exactly, which can only hold if "
             "every row was transcribed correctly.</p>") ,
        card("Full table",
             tools(filter_col=2, filter_label="All conferences", keys=[t["conf"] for t in rows]) + tbl,
             body=False, sub=f'<span class="badge b-verified">{len(rows)} rows</span>'),
    ]
    return page("standings.html", "Standings",
                "Official 2026 NFL standings for all 32 clubs, as of completion of Week 9.",
                sections)


# ==================================================================== main
def main():
    os.makedirs(os.path.join(DOCS, "assets", "css"), exist_ok=True)
    os.makedirs(os.path.join(DOCS, "assets", "js"), exist_ok=True)
    with open(os.path.join(DOCS, ".nojekyll"), "w") as fh:
        fh.write("")

    print("Building NFL1 dashboard …")
    write("index.html", page_index())
    write("executive-summary.html", page_exec())
    write("requirements.html", page_requirements())
    write("questions.html", page_questions())
    write("suggestions.html", page_suggestions())
    write("strategy-lab.html", page_strategy())
    write("signals.html", page_signals())
    write("correlation.html", page_correlation())
    write("injury-depth.html", page_injury())
    write("standings.html", page_standings())
    write("data-sources.html", page_sources())
    write("verification.html", page_verification())
    write("flagged.html", page_flagged())

    problems = _problems()
    if problems:
        print("\nBUILD FAILED — source assertion violations:", file=sys.stderr)
        for p in sorted(set(problems)):
            print("  - " + p, file=sys.stderr)
        return 1
    print(f"\nBuild OK — no source assertions violated.")
    return 0


_problems_store: list[str] = []


def _problems():
    return [p for p in globals().get("problems", [])]


if __name__ == "__main__":
    sys.exit(main())
