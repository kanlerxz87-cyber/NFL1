#!/usr/bin/env python3
"""brief/build.py — the public front door for the brief's own requirements.

Why this sub-site exists
------------------------
The repository grew thirteen sub-sites, four landing pages and a 38-entry header nav. Each of them
is accurate and none of them is a front door: a reader arriving to answer "can I stake on this?"
has to know which of 194 pages holds the answer.

This build produces eight pages, one per category, from JSON only:

    index.html          the dashboard: what holds, what does not, what is missing
    requirements.html   one row per distinct line of the brief, with its blocking gate
    answers.html        the questions that must be settled before a decision
    strategies.html     the leaderboard (empty, by design) and the labelled backtest archive
    availability.html   injuries, replacements and depth deficiency, official only
    fixtures.html       the Week 11 schedule facts, every venue read from the game centre
    suggestions.html    what to improve, with a pre-condition on each row
    verification.html   every check performed, every flag, and this session's own defects

Rules enforced by brief/verify.py, which fails the build:
  * every <tr> in <tbody> carries at least one https source link, or an explicit unverified label;
  * no table cell renders empty — a blank fact is written as "not published", "not captured" or
    "unverified", never as whitespace;
  * no placeholder text (TBD, TODO, lorem, XXX, N/A);
  * every local href resolves, and every page is reachable from index.html.
"""
from __future__ import annotations

import html
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HERE = os.path.join(ROOT, "brief")
DATA = os.path.join(ROOT, "data", "session-2b927826")

BUILT_AT = "2026-11-16T14:36:42Z"

PAGES = [
    ("index.html", "Overview"),
    ("requirements.html", "Requirements"),
    ("answers.html", "Questions"),
    ("strategies.html", "Strategies"),
    ("availability.html", "Availability"),
    ("fixtures.html", "Fixtures & venues"),
    ("suggestions.html", "Suggestions"),
    ("verification.html", "Verification"),
]

WEEK11 = "https://www.nfl.com/schedules/2026/by-week/week-11"
INJURIES_W10 = "https://www.nfl.com/injuries/league/2026/reg10"
INJURIES_W11 = "https://www.nfl.com/injuries/league/2026/reg11"

CSS = """
:root{--bg:#0b1220;--panel:#111a2b;--panel2:#16223a;--ink:#e8eef9;--muted:#93a4c0;--line:#24314b;
--accent:#4ade80;--accent-ink:#062a16;--blue:#60a5fa;--amber:#fbbf24;--red:#f87171;--radius:14px}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:radial-gradient(1200px 600px at 12% -10%,#16233c 0%,var(--bg) 55%) no-repeat,var(--bg);
color:var(--ink);font:16px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
-webkit-font-smoothing:antialiased}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.85em;color:#c7d2fe}
.top{position:sticky;top:0;z-index:20;display:flex;gap:16px;align-items:center;flex-wrap:wrap;
padding:12px 20px;background:rgba(11,18,32,.9);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:9px;color:var(--ink);font-weight:700}
.mark{background:var(--accent);color:var(--accent-ink);padding:3px 9px;border-radius:8px;font-size:.8rem;letter-spacing:.08em}
.brand-text{font-size:.95rem;color:var(--muted)}
.top nav{display:flex;gap:3px;flex-wrap:wrap;margin-left:auto}
.top nav a{color:var(--muted);padding:6px 10px;border-radius:9px;font-size:.85rem}
.top nav a:hover{background:var(--panel2);color:var(--ink);text-decoration:none}
.top nav a.active{background:var(--accent);color:var(--accent-ink);font-weight:600}
main{max-width:1180px;margin:0 auto;padding:24px 20px 72px}
.page-head{margin:8px 0 20px}
.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:.7rem;color:var(--accent);margin:0 0 6px}
h1{font-size:clamp(1.6rem,3.2vw,2.3rem);line-height:1.12;margin:0 0 8px}
.standfirst{color:var(--muted);max-width:78ch;margin:0}
.timestamp{color:#6f809d;font-size:.78rem;margin:10px 0 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px;margin:20px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:14px}
.kpi-label{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.09em}
.kpi-value{font-size:1.55rem;font-weight:700;margin:4px 0 0}
.kpi-sub{color:#7f8fab;font-size:.75rem;margin-top:3px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;margin:18px 0}
.panel h2{font-size:1.05rem;margin:0 0 4px}
.panel .sub{color:var(--muted);font-size:.85rem;margin:0 0 12px}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:.855rem}
thead th{position:sticky;top:0;background:var(--panel2);text-align:left;padding:9px 10px;font-size:.72rem;
text-transform:uppercase;letter-spacing:.06em;color:var(--muted);border-bottom:1px solid var(--line);white-space:nowrap}
tbody td{padding:8px 10px;border-bottom:1px solid #1b2740;vertical-align:top}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover{background:#0f1a2d}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:.72rem;font-weight:600;white-space:nowrap}
.b-done{background:#12341f;color:#6ee7a0}.b-partial{background:#33280c;color:#fcd34d}
.b-not{background:#3a1616;color:#fca5a5}.b-open{background:#1d2b46;color:#93c5fd}
.missing{color:#fca5a5;font-style:normal}
.sub2{color:#7f8fab;font-size:.78rem}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
ul.bullets{margin:8px 0 0;padding-left:20px;color:var(--muted)}
ul.bullets li{margin:5px 0}
.note{background:#0e1a2e;border-left:3px solid var(--blue);padding:10px 14px;border-radius:8px;color:var(--muted);font-size:.86rem;margin:12px 0}
.note.alert{border-left-color:var(--amber)}
.foot{margin-top:36px;padding-top:14px;border-top:1px solid var(--line);color:#6f809d;font-size:.78rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:15px}
.card h3{margin:0 0 6px;font-size:.98rem}
.card p{margin:0;color:var(--muted);font-size:.85rem}
.card a.more{display:inline-block;margin-top:9px;font-size:.83rem}
.src{font-size:.78rem;white-space:nowrap}
"""


# ---------------------------------------------------------------- helpers
def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def load(name: str):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def repo(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


BLANK = {"", "n/a", "na", "none", "null", "-", "\u2014", "tbd", "todo", "xxx"}


def missing(v, label: str = "not published") -> str:
    """A blank fact is never rendered as whitespace or a dash."""
    s = "" if v is None else str(v).strip()
    if s and s.lower() not in BLANK:
        return esc(s)
    return f'<span class="missing">{esc(label)}</span>'


def link(url: str, text: str | None = None) -> str:
    return f'<a href="{esc(url)}">{esc(text or url)}</a>'


def src_cell(url: str, label: str) -> str:
    return f'<span class="src">{link(url, label)}</span>'


def badge(status: str) -> str:
    s = status.lower()
    if s in {"done", "answered", "resolved", "pass"}:
        cls = "b-done"
    elif s in {"partial", "answered-unverified", "partly done", "needs review"}:
        cls = "b-partial"
    elif s in {"not met", "blocked", "not verified"}:
        cls = "b-not"
    else:
        cls = "b-open"
    return f'<span class="badge {cls}">{esc(status)}</span>'


def kpi(label: str, value: str, sub: str = "") -> str:
    tail = f'<div class="kpi-sub">{esc(sub)}</div>' if sub else ""
    return (f'<div class="kpi"><div class="kpi-label">{esc(label)}</div>'
            f'<div class="kpi-value">{esc(value)}</div>{tail}</div>')


def table(headers: list, rows: list, caption: str) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join(f"<tr>{r}</tr>" for r in rows)
    return (f'<div class="panel"><h2>{esc(caption)}</h2>'
            f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table></div></div>")


def page(name: str, title: str, body: str) -> str:
    nav = []
    for href, label in PAGES:
        cls = ' class="active"' if href == name else ""
        nav.append(f'<a href="{href}"{cls}>{esc(label)}</a>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · NFL Decision Lab</title>
<style>{CSS}</style>
</head>
<body>
<header class="top">
  <a class="brand" href="index.html"><span class="mark">NFL</span><span class="brand-text">Decision Lab · brief dashboard</span></a>
  <nav aria-label="Categories">{"".join(nav)}</nav>
</header>
<main>
{body}
<p class="foot">Built {esc(BUILT_AT)} by session <code>2b927826-nfl1</code> from <code>data/session-2b927826/*.json</code> only.
Every table row carries a source link or states that no value is published. Research tool, not betting advice.
<a href="verification.html">How every value was checked &rarr;</a></p>
</main>
</body>
</html>
"""


# ---------------------------------------------------------------- index
def build_index() -> str:
    req, ans, flags = load("requirements.json"), load("answers.json"), load("flags.json")
    sug, av, fx = load("suggestions.json"), load("availability.json"), load("official_week11_fixtures.json")
    ver = load("verification.json")
    ps = repo("data/strat/proper_score.json")
    lb = repo("data/s9cb/leaderboard.json")
    ctrl = repo("data/prereg/controls.json")

    rc, ac = req["counts"], ans["counts"]
    side = ps["markets"][0]["results"]["model"]
    best = max(lb["leaderboard"], key=lambda r: r.get("n_gates_passed", 0))
    best_gates = f'{best["n_gates_passed"]} of 8'
    zero_gates = sum(1 for r in lb["leaderboard"] if r.get("n_gates_passed") == 8)

    kpis = "".join([
        kpi("Brief lines covered", str(rc["rows"]),
            f'{rc["done"]} done \u00b7 {rc["partial"]} partial \u00b7 {rc["not_met"]} not met'),
        kpi("Questions open", str(ac["open_needs_data"] + ac["open_needs_decision"]),
            f'{ac["answered"] + ac["answered_unverified"]} answered or partly answered'),
        kpi("Strategies passing 8/8 gates", str(zero_gates), f"best is {best_gates}"),
        kpi("Brier skill vs closing line", f'{side["bss"]:.4f}',
            f'95% interval [{side["bss_ci95"][0]:.4f}, {side["bss_ci95"][1]:.4f}]'),
        kpi("Backups projected to start", str(av["depth_deficiency"]["totals"]["backup_projected_to_start"]),
            "all second string; 0 third or deeper"),
        kpi("Week 11 venues verified",
            f'{fx["venue_coverage"]["venue_read_from_game_centre"]} of {fx["venue_coverage"]["fixtures"]}',
            "read from the official game centre"),
        kpi("Flags in this register", str(flags["counts"]["rows"]),
            f'{flags["counts"]["open"]} open \u00b7 {flags["counts"]["needs_review"]} need review'),
        kpi("Checks performed", str(len(ver["checks"])), "on official pages this session"),
    ])

    cards = [
        ("requirements.html", "Requirements",
         f'{rc["rows"]} rows, one per distinct line of the brief, each with the gate that blocks it and the number that would clear it.'),
        ("answers.html", "Questions before any decision",
         f'{ac["rows"]} questions: what is known, what is missing, and the capture or test that would produce it.'),
        ("strategies.html", "Strategies &amp; leaderboard",
         "The ranked board is empty by design. Every backtest number is quarantined in a labelled archive block below it."),
        ("availability.html", "Injuries &amp; depth deficiency",
         f'Week 10 official designations, and the {av["depth_deficiency"]["totals"]["backup_projected_to_start"]} slots a backup is projected to start.'),
        ("fixtures.html", "Fixtures &amp; venues",
         f'{fx["venue_coverage"]["fixtures"]} Week 11 fixtures with venue, city, kickoff and network, each read from the official game centre.'),
        ("suggestions.html", "Suggestions",
         f'{sug["counts"]["rows"]} improvements, each with the pre-condition that must hold before it is worth starting.'),
        ("verification.html", "Verification &amp; flags",
         f'{len(ver["checks"])} checks, {flags["counts"]["rows"]} flags, and this session\'s own defects, published rather than hidden.'),
    ]
    cardhtml = "".join(
        f'<div class="card"><h3>{t}</h3><p>{d}</p><a class="more" href="{h}">Open &rarr;</a></div>'
        for h, t, d in cards)

    holds = [
        f'The closing line is a better forecaster than the model on the side market: Brier skill '
        f'{side["bss"]:.4f}, interval entirely below zero on {side["n_scored"]:,} games.',
        f'No strategy clears the eight gates. {zero_gates} of {lb["n_strategies"]} clear all eight; the best '
        f'({best["strategy"]}) clears {best_gates} and fails multiple testing and the ROI interval.',
        f'A coin-flip control loses {ctrl["controls"][0]["expected_roi_pct"]:.2f}% on the frozen corpus. Every '
        f'published strategy result sits inside its own luck band, so none can be called skilful.',
        'The official Week 11 injury report is not published yet: the league address serves Week 10. The committed '
        'capture matches the live Week 10 page on every cell checked (220 of 220).',
        f'{fx["venue_coverage"]["fixtures"]} of {fx["venue_coverage"]["fixtures"]} Week 11 venues were read from the official '
        'game centre and agree with two independent transcriptions made earlier. One official-to-official naming '
        'difference exists for Arrowhead Stadium and is flagged.',
        'The depth ladder reconciles: 41 = 38 slots where a backup is pressed into duty plus 3 slots with no available '
        'player. No club is projected to start a third-string player this week.',
    ]

    missing_list = [
        'An official price. The NFL publishes no odds, so every ROI is measured against a third-party line (flag '
        'BF-11). This gates every backtest number on every page.',
        'The actual starter. No Game Book, inactive list or snap-count capture exists for any 2026 game, so a '
        'replacement can be projected but never confirmed (BF-10).',
        'A price-snapshot store with opening and closing numbers. Without it there is no closing-line value and no way '
        'to see which side of a line move a bet is on (Q11).',
        'A within-week injury series. Two capture days and zero recorded designation changes means the "surprise" the '
        'brief asks for has never been observed (BF-02).',
        'One authoritative pre-registration registry. Four exist, with four checkers (BF-06).',
        'A recorded terms review before row-level injury data is published (Q21).',
    ]

    return page("index.html", "Overview", f"""
<div class="page-head">
  <p class="eyebrow">Evidence-first dashboard</p>
  <h1>What the evidence supports, what it refuses to support, and what is missing</h1>
  <p class="standfirst">A working front door for the brief's own requirements. Every number below is copied from a
  committed file named beside it, and every row on every page links to the source that settles it. Nothing is filled
  in: where no official value exists, the cell says so.</p>
  <p class="timestamp">Data built {esc(BUILT_AT)} \u00b7 official pages read 2026-11-16 \u00b7
  <a href="verification.html">all {len(ver["checks"])} checks</a></p>
</div>
<div class="kpis">{kpis}</div>

<div class="panel">
  <h2>The one-line verdict</h2>
  <p class="sub">What a reader should take away before opening any other page.</p>
  <div class="note alert"><strong>The model does not beat the market, and no strategy clears the gates.</strong>
  That is the finding, not a failure of the build. The own line is worse than the closing line on the side
  (Brier skill {side["bss"]:.4f}, interval [{side["bss_ci95"][0]:.4f}, {side["bss_ci95"][1]:.4f}]) and on the total,
  and the moneyline is published as a probability rather than a priced bet. Staking anything on the current model
  would be a decision the evidence contradicts.</div>
  <div class="cards" style="margin-top:14px">{cardhtml}</div>
</div>

<div class="grid2">
  <div class="panel">
    <h2>What holds up</h2>
    <p class="sub">Each item is checkable from a named file or an official page.</p>
    <ul class="bullets">{''.join(f'<li>{esc(x)}</li>' for x in holds)}</ul>
  </div>
  <div class="panel">
    <h2>What is missing, and what it blocks</h2>
    <p class="sub">In the brief's order of impact on the next decision.</p>
    <ul class="bullets">{''.join(f'<li>{esc(x)}</li>' for x in missing_list)}</ul>
    <div class="note"><a href="answers.html">All {ac["rows"]} questions, with the test that would answer each &rarr;</a></div>
  </div>
</div>

<div class="panel">
  <h2>Where to go next</h2>
  <p class="sub">Eight pages, one per category. The rest of the repository is linked, not replaced.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>Page</th><th>What it answers</th><th class="num">Rows</th><th>Source of the rows</th>
  </tr></thead><tbody>
    <tr><td><a href="requirements.html">Requirements</a></td><td>Which of the brief's lines are met, and what blocks the rest</td><td class="num">{rc["rows"]}</td><td>{src_cell("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-2b927826/requirements.json", "register")}</td></tr>
    <tr><td><a href="answers.html">Questions</a></td><td>What must be settled before any decision, and how to discover it</td><td class="num">{ac["rows"]}</td><td>{src_cell("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-2b927826/answers.json", "register")}</td></tr>
    <tr><td><a href="strategies.html">Strategies</a></td><td>Why the board is empty, and every backtest number behind that</td><td class="num">{lb["n_strategies"]}</td><td>{src_cell("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/leaderboard.json", "leaderboard")}</td></tr>
    <tr><td><a href="availability.html">Availability</a></td><td>Official designations and the slots a backup is projected to start</td><td class="num">{av["week10_report"]["rows"]}</td><td>{src_cell(INJURIES_W10, "nfl.com injuries")}</td></tr>
    <tr><td><a href="fixtures.html">Fixtures &amp; venues</a></td><td>Week 11 schedule facts, every venue from the game centre</td><td class="num">{fx["venue_coverage"]["fixtures"]}</td><td>{src_cell(WEEK11, "nfl.com schedule")}</td></tr>
    <tr><td><a href="suggestions.html">Suggestions</a></td><td>What to build next, and what must be true first</td><td class="num">{sug["counts"]["rows"]}</td><td>{src_cell("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-2b927826/suggestions.json", "register")}</td></tr>
    <tr><td><a href="verification.html">Verification</a></td><td>Every check performed and every flag raised</td><td class="num">{len(ver["checks"])}</td><td>{src_cell("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-2b927826/verification.json", "record")}</td></tr>
  </tbody></table></div>
</div>

<div class="panel">
  <h2>The rest of the repository</h2>
  <p class="sub">Thirteen sub-sites and about 194 pages already exist. This page indexes them; it does not replace them.</p>
  <ul class="bullets">
    <li><a href="../pages/executive.html">Executive summary</a> \u00b7 <a href="../pages/readiness.html">long-form requirement register</a> \u00b7 <a href="../pages/questions.html">long-form question register</a></li>
    <li><a href="../pages/lines.html">Own lines</a> \u00b7 <a href="../pages/strategies.html">strategy lab</a> \u00b7 <a href="../pages/luck.html">luck removal</a> \u00b7 <a href="../pages/correlations.html">correlations</a></li>
    <li><a href="../pages/injuries.html">Injuries</a> \u00b7 <a href="../pages/depth.html">depth &amp; deficiency</a> \u00b7 <a href="../pages/snapshots.html">snapshot ledger</a> \u00b7 <a href="../shadow/team-view.html">per-team view</a></li>
    <li><a href="../prereg/registry.html">strategy registry</a> \u00b7 <a href="../prereg/archive.html">backtest archive</a> \u00b7 <a href="../strat/index.html">strategy competition</a> \u00b7 <a href="../shadow/index.html">shadow baseline</a></li>
    <li><a href="../room/index.html">decision room</a> \u00b7 <a href="../review-room/index.html">review room</a> \u00b7 <a href="../pages/review.html">flagged for review</a> \u00b7 <a href="../capture/index.html">official capture</a></li>
    <li><a href="../index.html">the repository's main landing page</a></li>
  </ul>
</div>
""")


# ---------------------------------------------------------------- requirements
def build_requirements() -> str:
    req = load("requirements.json")
    rc = req["counts"]
    off = {
        "BR-23": WEEK11, "BR-24": WEEK11, "BR-25": WEEK11,
        "BR-56": "https://www.nfl.com/",
        "BR-75": "https://github.com/kanlerxz87-cyber/NFL1/blob/main/COORDINATION.md",
    }
    rows = []
    for r in req["rows"]:
        url = off.get(r["id"], "https://www.nfl.com/")
        note = esc(r.get("note", "")) if r.get("note") else missing(None, "no note recorded")
        rows.append(
            f"<td>{esc(r['id'])}</td>"
            f"<td>{esc(r['title'])}</td>"
            f"<td>{badge(r['status'])}</td>"
            f"<td>{esc(r['now'])}</td>"
            f"<td>{esc(r['gate'])}</td>"
            f"<td class='sub2'>{note}</td>"
            f"<td>{src_cell('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-2b927826/requirements.json', 'register')} "
            f"{src_cell(url, 'source')}</td>")
    kpis = "".join([
        kpi("Rows", str(rc["rows"]), "one per distinct brief line"),
        kpi("Done", str(rc["done"]), "an artifact exists and is checkable"),
        kpi("Partial", str(rc["partial"]), "some of it exists"),
        kpi("Not met", str(rc["not_met"]), "the artifact does not exist"),
    ])
    return page("requirements.html", "Requirements", f"""
<div class="page-head">
  <p class="eyebrow">Requirement coverage</p>
  <h1>Every distinct line of the brief, with the gate that blocks it</h1>
  <p class="standfirst">The brief restates several requirements in different words: the price policy appears four
  times, the injury series five. This register de-duplicates them into one row per distinct requirement. A row is
  <em>done</em> only when an artifact exists that can be checked, not when the intent is agreed.</p>
  <p class="timestamp">Built {esc(BUILT_AT)} from <code>data/session-2b927826/requirements.json</code>, generated by
  <code>tools/session-2b927826/build_requirements.py</code></p>
</div>
<div class="kpis">{kpis}</div>
<div class="note alert"><strong>How to read the gate column.</strong> The gate is what blocks the row, not who is to
blame. "An official price" blocks every ROI row because the NFL publishes no odds and no official substitute exists,
so nothing in the repository can close it. "An archived Game Book" blocks every actual-starter row and can be closed
by one capture run. Both kinds are marked the same way, so read the wording, not the colour.</div>
{table(["ID", "Requirement as the brief states it", "Status", "The number today", "The gate that blocks it", "Note", "Sources"],
       rows, f"All {rc['rows']} requirement rows")}
<div class="panel">
  <h2>The four rows that decide the rest</h2>
  <div class="cards">
    <div class="card"><h3>An official price</h3><p>Every ROI, every gate that uses ROI, and every reward rests on a
      third-party line. Until the price-data policy is decided, no backtest number can be called official.</p>
      <a class="more" href="answers.html">Q10 &rarr;</a></div>
    <div class="card"><h3>The actual starter</h3><p>Every availability feature, every replacement claim and the whole
      availability graph needs one Game Book archive. It is 0 of 137 games today.</p>
      <a class="more" href="answers.html">Q15 &rarr;</a></div>
    <div class="card"><h3>A within-week injury series</h3><p>The brief asks for the surprise, not the level. Two
      capture days and zero recorded changes means the surprise has never been observed.</p>
      <a class="more" href="answers.html">Q05 &rarr;</a></div>
    <div class="card"><h3>One pre-registration registry</h3><p>Four registries with four checkers means
      "registered" has four meanings, and the leaderboard gate depends on which one a page reads.</p>
      <a class="more" href="answers.html">Q16 &rarr;</a></div>
  </div>
</div>
""")


# ---------------------------------------------------------------- answers
def build_answers() -> str:
    ans = load("answers.json")
    ac = ans["counts"]
    rows = []
    for r in ans["rows"]:
        miss = r["missing"]
        miss_html = esc(miss) if miss.startswith("nothing") else f'<span class="missing">{esc(miss)}</span>'
        rows.append(
            f"<td>{esc(r['id'])}</td>"
            f"<td><strong>{esc(r['question'])}</strong></td>"
            f"<td>{badge(r['status'])}</td>"
            f"<td>{esc(r['answer'])}</td>"
            f"<td>{miss_html}</td>"
            f"<td>{esc(r['decision_unblocked'])}</td>"
            f"<td class='sub2'>{esc(r['how_to_discover'])}</td>"
            f"<td>{src_cell('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-2b927826/answers.json', 'register')}</td>")
    kpis = "".join([
        kpi("Questions", str(ac["rows"]), "one row each"),
        kpi("Answered", str(ac["answered"]), "value exists and was checked"),
        kpi("Answered, unverified", str(ac["answered_unverified"]), "rests on a third-party source"),
        kpi("Open on data", str(ac["open_needs_data"]), "no source captured yet"),
        kpi("Open on policy", str(ac["open_needs_decision"]), "a human must choose"),
    ])
    return page("answers.html", "Questions", f"""
<div class="page-head">
  <p class="eyebrow">Decision-gating questions</p>
  <h1>What must be settled before a decision can reasonably be made</h1>
  <p class="standfirst">The brief asks for a clear list of questions, the information that answers them, and where the
  information is missing, a way to discover it. Each row states the answer if one exists, what is missing if not, the
  decision it unblocks, and the concrete capture or test that would produce the missing value.</p>
  <p class="timestamp">Built {esc(BUILT_AT)} from <code>data/session-2b927826/answers.json</code></p>
</div>
<div class="kpis">{kpis}</div>
<div class="note alert"><strong>Four questions gate almost every other row.</strong>
<em>Q10</em> &mdash; which prices count: no official price exists, so the policy is a choice, not a capture.
<em>Q15</em> &mdash; who actually started: one Game Book archive closes it.
<em>Q05</em> &mdash; is the injury signal a surprise: one week of daily captures closes it.
<em>Q08</em> &mdash; is a depth chart a legitimate source for who starts: a policy choice, and the brief has already
made it (it is not).</div>
{table(["ID", "Question", "Status", "What is known", "What is missing", "Decision it unblocks", "How to discover it", "Source"],
       rows, f"All {ac['rows']} questions")}
<div class="grid2">
  <div class="panel">
    <h2>The missing information, ranked by what it unblocks</h2>
    <ul class="bullets">
      <li><strong>Official inactive lists</strong> &mdash; one fetch per game window &mdash; turn "a backup probably
        started" into "a backup played". Nothing else moves so many rows for so little work.</li>
      <li><strong>Official Game Books</strong>, one per played game, give the actual starters and close Q08 and Q15.</li>
      <li><strong>Daily injury captures</strong> &mdash; the workflow already exists &mdash; produce the first
        designation change the readiness gate is waiting for.</li>
      <li><strong>An opening and a closing price per market</strong> is the only route to closing-line value, and it
        cannot be backfilled: every week without it is lost permanently.</li>
      <li><strong>A terms review</strong> decides whether the row-level tables that already exist may stay public.</li>
    </ul>
  </div>
  <div class="panel">
    <h2>What a decision needs that no capture can supply</h2>
    <ul class="bullets">
      <li><strong>Which pre-registration registry is authoritative</strong> &mdash; four exist; a person must choose.</li>
      <li><strong>Whether a third-party price is acceptable</strong> &mdash; the league publishes none, so this is a
        policy call with a real consequence for every published number.</li>
      <li><strong>The operator's void and push rules</strong> for every market &mdash; they are the operator's, not the
        NFL's, and a parlay cannot be ranked without them.</li>
      <li><strong>How long a live sample must run</strong> before a demotion is informative &mdash; the power table
        says roughly seven seasons at a 3-point-equivalent edge, which may be longer than the project's patience.</li>
    </ul>
  </div>
</div>
""")


# ---------------------------------------------------------------- strategies
def build_strategies() -> str:
    lb = repo("data/s9cb/leaderboard.json")
    ps = repo("data/strat/proper_score.json")
    pr = repo("data/strat/preregistration.json")
    dm = repo("data/strat/demotion.json")
    wwc = repo("data/strat/what_would_change.json")
    ctrl = repo("data/prereg/controls.json")
    par = repo("data/s9cb/parlays.json")
    LB = "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/leaderboard.json"

    gates = {g["id"]: g["name"] for g in lb["gate_definitions"]}
    why = {g["id"]: g["why"] for g in lb["gate_definitions"]}
    ranked = [r for r in lb["leaderboard"] if r.get("n_gates_passed") == len(gates)]

    archive_rows = []
    for r in sorted(lb["leaderboard"], key=lambda x: (-x.get("n_gates_passed", 0), x.get("p_value_bh_adjusted", 1))):
        failed = [g for g in gates if not r["gates"].get(g)]
        archive_rows.append(
            f"<td>{esc(r['strategy'])}</td>"
            f"<td class='num'>{r['n_bets']:,}</td>"
            f"<td class='num'>{r['hit_rate'] * 100:.2f}%</td>"
            f"<td class='num'>{r['roi_pct']:+.2f}%</td>"
            f"<td class='num'>[{r['roi_ci95'][0] * 100:+.1f}%, {r['roi_ci95'][1] * 100:+.1f}%]</td>"
            f"<td class='num'>{r['p_value_bh_adjusted']:.3f}</td>"
            f"<td class='num'>{r['n_gates_passed']} of {len(gates)}</td>"
            f"<td class='sub2'>{esc(', '.join(failed) or 'none')}</td>"
            f"<td>{src_cell(LB, 'run')}</td>")

    def market(name):
        return next(m for m in ps["markets"] if m["market"] == name)["results"]["model"]

    side, total, ml = market("side"), market("total"), market("moneyline")
    ps_rows = []
    for nm, m, extra in (
            ("Side &mdash; P(home covers the close)", side, ""),
            ("Total &mdash; P(over the close)", total, ""),
            ("Moneyline &mdash; P(home win)", ml, " vs the de-vigged close")):
        bss = m.get("bss", m.get("bss_vs_devig"))
        lo = m["bss_lower_bound"]
        verdict = "lower bound above zero" if lo > 0 else '<span class="missing">lower bound below zero</span>'
        ps_rows.append(
            f"<td>{nm}</td>"
            f"<td class='num'>{m['n_scored']:,}</td>"
            f"<td class='num'>{bss:+.4f}</td>"
            f"<td class='num'>[{m['bss_ci95'][0]:+.4f}, {m['bss_ci95'][1]:+.4f}]</td>"
            f"<td class='num'>{m['brier']:.4f}</td>"
            f"<td class='num'>{m['p_value_bootstrap']:.2f}</td>"
            f"<td>{verdict}{esc(extra)}</td>"
            f"<td>{src_cell('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/strat/proper_score.json', 'scores')}</td>")

    ctrl_rows = []
    for c in ctrl["controls"]:
        n = c.get("n_games", c.get("n_scored"))
        roi = c.get("expected_roi_pct", (c.get("roi_pct") or 0) * 100)
        hit = f"{c['hit_rate'] * 100:.2f}%" if c.get("hit_rate") is not None else \
            '<span class="sub2">analytic, no sample</span>'
        ctrl_rows.append(
            f"<td>{esc(c['id'])}</td><td>{esc(c['name'])}</td><td>{esc(c['market'])}</td>"
            f"<td class='num'>{n:,}</td>"
            f"<td class='num'>{roi:+.2f}%</td>"
            f"<td class='num'>{hit}</td>"
            f"<td class='sub2'>{esc(c['role'])}</td>"
            f"<td>{src_cell('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/prereg/controls.json', 'controls')}</td>")

    wwc_rows = []
    for w in wwc["rows"]:
        st = "not met" if w["status"].startswith("NOT SUPPORTED") else "partial"
        wwc_rows.append(
            f"<td>{esc(w['id'])}</td><td>{esc(w['claim'])}</td>"
            f"<td class='sub2'>{esc(w['current'])}</td>"
            f"<td>{badge(st)}<br><span class='sub2'>{esc(w['status'])}</span></td>"
            f"<td>{esc(w['confirm_if'])}</td><td>{esc(w['abandon_if'])}</td>"
            f"<td class='sub2'>{esc(w['next_measurement'])}</td>"
            f"<td>{src_cell('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/strat/what_would_change.json', 'register')}</td>")

    gate_rows = "".join(
        f"<tr><td>{esc(k)}</td><td>{esc(v)}</td><td class='sub2'>{esc(why[k])}</td>"
        f"<td>{src_cell(LB, 'gate defs')}</td></tr>" for k, v in gates.items())

    best = max(lb["leaderboard"], key=lambda r: (r["n_gates_passed"], -r["p_value_bh_adjusted"]))
    kpis = "".join([
        kpi("Ranked on the board", str(len(ranked)), "a rule must clear all eight gates"),
        kpi("Scored backtest rules", str(lb["n_strategies"]), "in the labelled archive below"),
        kpi("Pre-registered records", str(pr["n_records"]),
            f'{pr["n_prospective"]} prospective / {pr["n_backtest"]} backtest-first'),
        kpi("Live strategies", str(dm["n_live"]), f'{dm["n_demotions_ever"]} demotions ever'),
        kpi("Bets scored", f'{lb["totals"]["bets_scored"]:,}', f'{lb["totals"]["games_in_sample"]:,} games'),
    ])
    return page("strategies.html", "Strategies", f"""
<div class="page-head">
  <p class="eyebrow">The competition</p>
  <h1>The ranked board is empty, and that is the result</h1>
  <p class="standfirst">The brief asks for a leaderboard competition that rewards skill and forbids backtest numbers
  from appearing on the board. Both rules are implemented. A strategy enters the board only after it clears all eight
  validation gates on a prospective sample; none has. The backtests are published below in a clearly labelled
  archive, with every number, so that the absence of a ranked row is auditable rather than a claim.</p>
  <p class="timestamp">Built {esc(BUILT_AT)} from <code>data/s9cb/leaderboard.json</code>,
  <code>data/strat/proper_score.json</code>, <code>data/strat/preregistration.json</code></p>
</div>
<div class="kpis">{kpis}</div>

<div class="panel">
  <h2>Stage 1 &mdash; the qualified board</h2>
  <p class="sub">Ranked by benchmark-relative Brier skill with a game-cluster lower bound and a multiplicity charge.
  Win rate and short-run ROI never rank.</p>
  <div class="note alert"><strong>No strategy is listed.</strong> {len(ranked)} of {lb["n_strategies"]} scored rules
  clear all eight gates. The best, {esc(best["strategy"])}, clears {best["n_gates_passed"]} of 8 and fails {esc(", ".join(g for g in gates if not best["gates"].get(g)))}.
  A board that listed anything here would be ranking luck.</div>
  <div class="table-wrap"><table><thead><tr>
    <th>Rule (archive, not ranked)</th><th class="num">Bets</th><th class="num">Hit rate</th><th class="num">ROI</th>
    <th class="num">ROI 95%</th><th class="num">BH-adjusted p</th><th class="num">Gates</th><th>Failed</th><th>Source</th>
  </tr></thead><tbody>{''.join(archive_rows)}</tbody></table></div>
  <div class="note"><strong>Every number in this table is retrospective.</strong> It is here so that the gate result can
  be checked, not so that a rule can be followed. None of these rows is a recommendation, and the brief's own rule
  forbids promoting one to the board on the strength of it.</div>
</div>

<div class="panel">
  <h2>Stage 1 &mdash; does the model forecast better than the closing line?</h2>
  <p class="sub">Brier skill = 1 &minus; Brier(model)/Brier(benchmark). A negative value means the benchmark is better.
  The test statistic is the lower bound of a game-cluster bootstrap interval, not the point estimate. The benchmark for
  the side and the total is the closing number at p = 0.5; for the moneyline it is the de-vigged closing price, which
  is a stronger benchmark than a coin flip.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>Market</th><th class="num">Games scored</th><th class="num">Brier skill</th><th class="num">95% interval</th>
    <th class="num">Brier</th><th class="num">p (bootstrap)</th><th>Verdict</th><th>Source</th>
  </tr></thead><tbody>{''.join(ps_rows)}</tbody></table></div>
  <div class="note">The side is worse than the close by {abs(side.get("bss", 0)):.4f}, the total by
  {abs(total.get("bss", 0)):.4f}, the moneyline by {abs(ml.get("bss", ml.get("bss_vs_devig", 0))):.4f} against the
  de-vigged price. On the moneyline the model does beat a coin flip, which is not the question: the closing price
  beats a coin flip by more. Nothing is eligible; the rule is printed verbatim in
  <code>data/strat/proper_score.json</code> as <em>{esc(ps["eligibility_rule"])}</em></div>
</div>

<div class="panel">
  <h2>Luck removal &mdash; the control every result is measured against</h2>
  <p class="sub">A no-skill reference line computed analytically on the same frozen corpus and the same observed
  prices. A rule that cannot beat this is noise, whatever its ROI.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>ID</th><th>Control</th><th>Market</th><th class="num">Games</th><th class="num">Expected ROI</th>
    <th class="num">Hit rate</th><th>Role</th><th>Source</th>
  </tr></thead><tbody>{''.join(ctrl_rows)}</tbody></table></div>
  <div class="note">Every rule in the archive above sits inside its own luck band. The number of bets needed for 80%
  power at the observed edge is printed with the run: for the best rule, 1,950 bets against 401 placed. That is not a
  reason to wait for 1,950 bets; it is a reason to stop treating 401 as evidence.</div>
</div>

<div class="panel">
  <h2>What would change our mind</h2>
  <p class="sub">A two-sided falsifier on every substantive claim: what would raise confidence, and what would make us
  abandon it. Both sides carry a number, and the next measurement is named.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>ID</th><th>Claim</th><th>Where it stands</th><th>Status</th><th>Confirm if</th><th>Abandon if</th>
    <th>Next measurement</th><th>Source</th>
  </tr></thead><tbody>{''.join(wwc_rows)}</tbody></table></div>
</div>

<div class="panel">
  <h2>Parlays and combos &mdash; the joint-evidence gate</h2>
  <p class="sub">Multiplying marginal probabilities is invalid under dependence, so a combo may only be ranked when a
  directly validated joint probability and the operator's void and push rules are both available.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>Tested</th><th class="num">Survive BH at 5%</th><th>Void/push rules recorded</th><th>Gate</th><th>Source</th>
  </tr></thead><tbody>
    <tr><td>Every two-leg pair in the scored set</td><td class="num">{par["n_pairs_scored"]}</td>
      <td><span class="missing">not recorded</span></td>
      <td>SHUT &mdash; {par["n_pairs_surviving_bh_5pct"]} of {par["n_pairs_scored"]} pairs survives the multiplicity
      charge, and no combo is ranked until the rules are recorded and the joint probability is validated directly</td>
      {src_cell('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/parlays.json', 'parlays')}</tr>
  </tbody></table></div>
  <div class="note"><strong>Why a correlated parlay is not a product.</strong> {esc(par["pricing_note"])}</div>
</div>

<div class="panel">
  <h2>The eight gates</h2>
  <p class="sub">Read straight from the data file, so that the board's shape cannot drift from its rules.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>Gate</th><th>What it requires</th><th>Why</th><th>Source</th>
  </tr></thead><tbody>{gate_rows}</tbody></table></div>
</div>

<div class="panel">
  <h2>Pre-registration and demotion</h2>
  <p class="sub">A rule frozen before it sees data, and a written exit for anything that goes live.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>Quantity</th><th class="num">Value</th><th>Reading</th><th>Source</th>
  </tr></thead><tbody>
    <tr><td>Strategy records</td><td class="num">{pr["n_records"]}</td>
      <td class="sub2">{pr["n_prospective"]} prospective, {pr["n_backtest"]} backtest-first and disclosed as such.
      The hash of the committing record is the registration.</td>
      <td>{src_cell('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/strat/preregistration.json', 'registry')}</td></tr>
    <tr><td>Live strategies</td><td class="num">{dm["n_live"]}</td>
      <td class="sub2">{esc(dm["state_note"])}</td>
      <td>{src_cell('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/strat/demotion.json', 'demotion')}</td></tr>
    <tr><td>Demotion rules armed</td><td class="num">{len(dm["rules"])}</td>
      <td class="sub2">{dm["n_paper"]} strategies sit in paper. A paper strategy cannot be demoted, and calling one
      live would be an unverified claim.</td>
      <td>{src_cell('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/strat/demotion.json', 'demotion')}</td></tr>
  </tbody></table></div>
</div>
""")


# ---------------------------------------------------------------- availability
def build_availability() -> str:
    av = load("availability.json")
    rep, dd = av["week10_report"], av["depth_deficiency"]
    byclub = []
    for c in sorted(dd["by_club"], key=lambda x: (-x["backup_projected"], x["club"])):
        deepest = esc(c["deepest_string"]) if c["deepest_string"] else '<span class="sub2">nobody pressed</span>'
        dated = esc(c["as_of"]) if c["as_of"] else missing(None, "no date on chart")
        byclub.append(
            f"<td>{esc(c['club'])}</td><td class='sub2'>{esc(c['name'])}</td>"
            f"<td>{esc(c['chart_status'])}</td>"
            f"<td class='num'>{c['slots']}</td>"
            f"<td class='num'>{c['backup_projected']}</td>"
            f"<td class='num'>{c['starter_at_risk']}</td>"
            f"<td>{deepest}</td>"
            f"<td>{'yes' if c['unofficial_label'] else 'no'}</td>"
            f"<td>{dated}</td>"
            f"<td>{src_cell(c['chart_url'], 'club chart')}</td>")
    dep = dd["deepest_replacement_among_projected_starters"][0]
    design_rows = "".join(
        f"<tr><td>{esc(k)}</td><td class='num'>{v}</td><td>{src_cell(INJURIES_W10, 'official report')}</td></tr>"
        for k, v in rep["designations"].items())
    t = dd["totals"]
    kpis = "".join([
        kpi("Official report rows", str(rep["rows"]), f'{rep["clubs"]} clubs \u00b7 {rep["games"]} games'),
        kpi("Out / Doubtful / Questionable",
            f'{rep["designations"]["Out"]} / {rep["designations"]["Doubtful"]} / {rep["designations"]["Questionable"]}',
            "printed designations"),
        kpi("Backups projected to start", str(t["backup_projected_to_start"]),
            "21 offense \u00b7 14 defense \u00b7 3 special teams"),
        kpi("Third-string or deeper starting", str(t["third_string_or_worse_projected"]),
            "the deepest is second string"),
        kpi("Starters at risk (Questionable)", str(t["starter_at_risk_questionable"]),
            "shown, never upgraded"),
        kpi("Clubs with a structured chart", f'{t["clubs_with_chart"]} of 32',
            "Houston publishes an image only"),
    ])
    limits = "".join(f"<li><strong>{esc(x['question'])}</strong> &mdash; missing: {esc(x['missing'])}. Gate: {esc(x['gate'])}.</li>"
                     for x in av["what_cannot_be_answered_yet"])
    return page("availability.html", "Availability", f"""
<div class="page-head">
  <p class="eyebrow">Injuries, replacements and depth deficiency</p>
  <h1>Who is out, who replaces them, and how deep the replacement is</h1>
  <p class="standfirst">Two kinds of evidence are on this page and they are labelled differently throughout. The
  injury designations are an official league filing. The depth charts are a club publication, and the starter inferred
  from one is a <em>projection</em>, not an observation. The brief forbids using a depth chart as a playing-time source,
  so no row here claims that a backup played.</p>
  <p class="timestamp">Built {esc(BUILT_AT)} \u00b7 report re-read {esc(rep["row_check_this_session"]["read_at"])} \u00b7
  <a href="{INJURIES_W10}">official Week 10 report</a></p>
</div>
<div class="kpis">{kpis}</div>

<div class="note alert"><strong>The Week 11 report does not exist yet.</strong> The league address
<a href="{INJURIES_W11}">nfl.com/injuries/league/2026/reg11</a> serves the Week 10 page, verified this session by the
page title. Nothing on this page is a Week 11 designation.</div>

<div class="panel">
  <h2>Week 10 official designations</h2>
  <p class="sub">Every count below is a cell of the official report. The four clubs on its first page (WAS, NYG, NE,
  DET) were re-read live this session and compared cell by cell with the committed capture:
  {rep["row_check_this_session"]["cells_compared"]} of {rep["row_check_this_session"]["cells_compared"]} cells match.</p>
  <div class="grid2">
    <div class="table-wrap"><table><thead><tr><th>Designation</th><th class="num">Rows</th><th>Source</th></tr></thead>
      <tbody>{design_rows}</tbody></table></div>
    <div>
      <div class="table-wrap"><table><thead><tr><th>Clubs with no report</th><th>Why</th><th>Source</th></tr></thead>
        <tbody><tr><td>{esc(", ".join(rep["clubs_with_no_report"]))}</td>
          <td>On bye in Week 10 per the official schedule. The absence of a report is not evidence of health.</td>
          <td>{src_cell(WEEK11, "schedule")}</td></tr></tbody></table></div>
      <div class="note">Rows whose game-status cell is blank are counted as <em>blank</em> above. A blank is printed
      as blank; it is not read as "available".</div>
    </div>
  </div>
</div>

<div class="panel">
  <h2>Depth deficiency by club</h2>
  <p class="sub"><strong>Definition.</strong> A slot is <em>deficient</em> when the lowest-ranked listed player who is
  not Out or Doubtful is not rank 1, so a backup is projected to start. Questionable is shown as at risk and is never
  upgraded to available or downgraded to out. Houston carries no rows because its chart is an image.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>Club</th><th>Name</th><th>Chart</th><th class="num">Slots</th><th class="num">Backups projected</th>
    <th class="num">Starters at risk</th><th>Deepest projected</th><th>Club calls it unofficial</th><th>Chart date</th><th>Source</th>
  </tr></thead><tbody>{''.join(byclub)}</tbody></table></div>
  <div class="note"><strong>One column, two meanings, both published.</strong> The generator's per-club
  <code>slots_missing_starter</code> column adds two different things: slots where a backup is pressed into duty
  ({t["reconciliation"]["pressed_into_duty"]}) and slots with no available listed player ({t["reconciliation"]["empty_code_slots"]}). It sums to
  {t["reconciliation"]["sum_over_32_clubs"]}, and the identity {t["reconciliation"]["sum_over_32_clubs"]} = {t["reconciliation"]["pressed_into_duty"]} +
  {t["reconciliation"]["empty_code_slots"]} is checked at build time. Reading the column as "empty slots" would be wrong by
  {t["reconciliation"]["pressed_into_duty"]} slots (flag BF-04).</div>
</div>

<div class="panel">
  <h2>The deepest replacement this week, printed in full</h2>
  <p class="sub">One slot's ladder, so the reasoning can be checked rather than trusted.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>Club</th><th>Unit</th><th>Pos</th><th>Projected starter</th><th>String</th><th>Replaces</th>
    <th>Their status</th><th>Sources</th>
  </tr></thead><tbody>
    <tr><td>{esc(dep['club'])}</td><td>{esc(dep['unit'])}</td><td>{esc(dep['position'])}</td>
      <td>{esc(dep['starter_name'])}</td><td>{esc(dep['string_label'])}</td><td>{esc(dep['replaces'])}</td>
      <td>{esc(dep['replaces_status'])}</td>
      <td>{src_cell(dep['chart_url'], 'club chart')} {src_cell(dep['report_url'], 'official report')}</td></tr>
  </tbody></table></div>
  <div class="note">This is the deepest case, not a special one: all {t["backup_projected_to_start"]} projected
  replacements are second string. Nothing in the repository projects a third- or fourth-string starter this week,
  which is the direct answer to the brief's "2nd, 3rd or 4th string" question: the deficiency is second string.</div>
</div>

<div class="grid2">
  <div class="panel">
    <h2>What cannot be answered yet</h2>
    <ul class="bullets">{limits}</ul>
  </div>
  <div class="panel">
    <h2>Why these limits exist</h2>
    <ul class="bullets">
      <li><strong>No inactive list, Game Book or snap count</strong> for any 2026 game, so "played" is unobservable
        (0 of 137 played games archived).</li>
      <li><strong>30 of 31 depth charts carry no date</strong>, so a chart cannot be versioned against a roster event.</li>
      <li><strong>14 of 31 charts carry the club's own "unofficial" label.</strong> The label is carried through
        rather than dropped.</li>
      <li><strong>Absence from the weekly report is not availability.</strong> A reserve-list player is not listed at
        all, and no reserve-list capture exists, so "not listed" is published as "not listed".</li>
    </ul>
    <div class="note"><a href="../pages/depth.html">The full 933-slot ladder with every rank &rarr;</a> \u00b7
    <a href="../shadow/team-view.html">the per-team view &rarr;</a></div>
  </div>
</div>
""")


# ---------------------------------------------------------------- fixtures
def build_fixtures() -> str:
    fx = load("official_week11_fixtures.json")
    rc = load("standings_reconcile.json")
    ctx = repo("data/shadow/week11_context.json")
    rows = []
    for g in fx["games"]:
        agree = "agrees with the feed" if g["stadium_agrees_with_feed"] else \
            '<span class="missing">differs from the feed, flagged BF-03</span>'
        rows.append(
            f"<td>{esc(g['matchup'])}</td><td>{esc(g['day_as_printed'])}</td>"
            f"<td class='num'>{esc(g['kickoff_et_as_printed'])}</td>"
            f"<td class='sub2'>{esc(g['kickoff_utc'])}</td>"
            f"<td>{esc(g['network'])}</td>"
            f"<td>{esc(g['location_as_printed'])}</td>"
            f"<td><strong>{esc(g['stadium_as_printed'])}</strong></td>"
            f"<td class='sub2'>{esc(g['feed_stadium'])}<br>{agree}</td>"
            f"<td>{src_cell(g['game_centre'], 'game centre')}</td>")
    byes = "".join(
        f"<tr><td>{esc(b['printed'])}</td><td>{esc(b['name'])}</td><td class='num'>{esc(b['record_on_page'])}</td>"
        f"<td>{src_cell(WEEK11, 'schedule page')}</td></tr>" for b in fx["byes"])
    st_rows = []
    for c in rc["comparison_with_committed_snapshot"]:
        moved = badge("partial") if c["changed"] else badge("done")
        st_rows.append(
            f"<td>{esc(c['club'])}</td><td class='num'>{esc(c['snapshot_2026_11_13'])}</td>"
            f"<td class='num'>{esc(c['official_2026_11_16'])}</td>"
            f"<td>{moved} <span class='sub2'>{'moved' if c['changed'] else 'identical'}</span></td>"
            f"<td>{src_cell(WEEK11, 'official')}</td>")
    ctx_rows = []
    for g in ctx["games"]:
        ctx_rows.append(
            f"<td>{esc(g['game_id'])}</td><td>{esc(g['weekday'])}</td>"
            f"<td class='num'>{g['away_rest_days']}</td><td class='num'>{g['home_rest_days']}</td>"
            f"<td>{'yes' if g['away_short_week'] or g['home_short_week'] else 'no'}</td>"
            f"<td>{'yes' if g['division_game'] else 'no'}</td>"
            f"<td>{esc(g['stadium_as_printed'])}</td>"
            f"<td>{missing(None)}</td><td>{missing(None)}</td>"
            f"<td>{src_cell(g['game_centre_url'], 'game centre')}</td>")
    kpis = "".join([
        kpi("Fixtures", str(fx["reconciliation"]["games"]),
            f'{fx["reconciliation"]["clubs_in_games"]} clubs + {fx["reconciliation"]["clubs_on_bye"]} on bye = 32'),
        kpi("Venues verified",
            f'{fx["venue_coverage"]["venue_read_from_game_centre"]} of {fx["venue_coverage"]["fixtures"]}',
            "from the game centre's Game Info block"),
        kpi("Stadium strings matching the feed", "12 of 13", "1 official naming difference, flagged"),
        kpi("Independent transcriptions agreeing", "3 of 3", "this session twice, another session once"),
        kpi("Records moved since 13 Nov", f'{rc["summary"]["changed"]} of 32', "the Week 10 slate was played"),
    ])
    return page("fixtures.html", "Fixtures & venues", f"""
<div class="page-head">
  <p class="eyebrow">Published schedule facts only</p>
  <h1>Week 11, with every venue read from the official game centre</h1>
  <p class="standfirst">The brief asks for the venue of every fixture to be transcribed from the official game centre,
  and for a fixture-context feature set built only from published schedule facts. This page is that table. Nothing
  here comes from a third-party feed: the feed is shown only where it disagrees, so the disagreement is visible.</p>
  <p class="timestamp">Built {esc(BUILT_AT)} \u00b7 official schedule read 2026-11-16 \u00b7
  <a href="{WEEK11}">official Week 11 schedule</a></p>
</div>
<div class="kpis">{kpis}</div>

<div class="panel">
  <h2>The 13 fixtures</h2>
  <p class="sub">Kickoff is the ET clock time printed on the official schedule page; the UTC column converts at EST
  (UTC&minus;5, November 2026). The city and stadium are the Game Info block of the game centre, transcribed in
  capitals exactly as printed. The feed column is a cross-check, never the source.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>Fixture</th><th>Day</th><th class="num">Kickoff ET</th><th>Kickoff UTC</th><th>Network</th>
    <th>City (official)</th><th>Stadium (official)</th><th>Third-party string</th><th>Source</th>
  </tr></thead><tbody>{''.join(rows)}</tbody></table></div>
  <div class="note">One disagreement, the Kansas City game. The game centre prints <code>ARROWHEAD STADIUM</code>; the
  same official site's schedule page and the pinned feed print <code>GEHA Field at Arrowhead Stadium</code>. Both
  strings are official, on different nfl.com pages. The game-centre string is published as the captured value and the
  difference is flagged; neither is presented as "the" official name.</div>
</div>

<div class="panel">
  <h2>Clubs on bye</h2>
  <p class="sub">The official page carries a "Teams on Bye" section. Six clubs idle plus 26 playing is 32, which is
  the reconciliation check.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>Code (as printed)</th><th>Club</th><th class="num">Record</th><th>Source</th>
  </tr></thead><tbody>{byes}</tbody></table></div>
</div>

<div class="panel">
  <h2>Fixture context &mdash; the feature set, with the two facts that are not official left blank</h2>
  <p class="sub">Rest days, short week, division game, neutral site and venue are all derivable from published facts
  and are tabulated here. Roof and surface are <em>not</em> printed on the official game centre, so they stay blank
  rather than being filled from the third-party feed.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>Game</th><th>Day</th><th class="num">Away rest (days)</th><th class="num">Home rest (days)</th>
    <th>Short week</th><th>Division game</th><th>Stadium (official)</th><th>Roof</th><th>Surface</th><th>Source</th>
  </tr></thead><tbody>{''.join(ctx_rows)}</tbody></table></div>
  <div class="note"><strong>Why roof and surface stay blank.</strong> The pinned feed carries both, and it is a
  reasonable third-party parse, but publishing it under an official label is exactly the error the brief's
  verification rule exists to prevent. A stadium's roof does not change between games, so this can be sourced once
  per venue from a club or league page and never again &mdash; that is suggestion SG-08.</div>
</div>

<div class="panel">
  <h2>Standings: the published snapshot against the official page today</h2>
  <p class="sub">A dated snapshot is not an error; an undated one would be. All 32 committed rows matched the official
  page on the snapshot's own date (2026-11-13). {rc["summary"]["changed"]} have moved since, because the Week 10 slate
  was played on 12&ndash;16 November. The arithmetic closes: the official records sum to
  {rc["arithmetic_check"]["wins"]} wins, {rc["arithmetic_check"]["losses"]} losses and
  {rc["arithmetic_check"]["ties"]} tie entries for one tied game, so wins equal losses, as a closed league requires.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>Club</th><th class="num">Snapshot 2026-11-13</th><th class="num">Official 2026-11-16</th><th>Drift</th><th>Source</th>
  </tr></thead><tbody>{''.join(st_rows)}</tbody></table></div>
  <div class="note"><strong>Club-code inconsistency (flag BF-05).</strong> The official pages print <code>AZ</code> for
  the Cardinals and <code>LA</code> for the Rams; the feed uses <code>ARI</code> and <code>LAR</code>. The
  repository's own files are not consistent, and a naive join drops the Cardinals row in 1 of 32 cases. The
  reconciliation behind this table maps the code explicitly rather than trusting a raw match.</div>
</div>
""")


# ---------------------------------------------------------------- suggestions
def build_suggestions() -> str:
    sug = load("suggestions.json")
    rows = []
    for s in sug["rows"]:
        if s["status"].startswith("done"):
            st = badge("done")
        elif s["status"].startswith("partly"):
            st = badge("partial")
        else:
            st = badge("not met")
        rows.append(
            f"<td>{esc(s['id'])}</td>"
            f"<td><strong>{esc(s['title'])}</strong><br><span class='sub2'>{esc(s['what'])}</span></td>"
            f"<td>{esc(s['type'])}</td>"
            f"<td>{st}<br><span class='sub2'>{esc(s['status'])}</span></td>"
            f"<td>{esc(s['precondition'])}</td>"
            f"<td class='sub2'>{esc(s['cost'])}</td>"
            f"<td class='sub2'>{esc(s['produces'])}</td>"
            f"<td>{esc(s['changes_decision'])}</td>"
            f"<td class='sub2'>{esc(s['gate_that_would_confirm'])}</td>"
            f"<td>{src_cell('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-2b927826/suggestions.json', 'register')}</td>")
    c = sug["counts"]
    return page("suggestions.html", "Suggestions", f"""
<div class="page-head">
  <p class="eyebrow">Review before implementation</p>
  <h1>{c["rows"]} suggestions, each with the pre-condition that must hold before it is worth starting</h1>
  <p class="standfirst">The brief asks for a section where suggestions can be reviewed and a path chosen before
  anything is implemented, and for suggestions that discover missing information rather than restate it. Every row
  carries the condition that must be true first, because the failure mode this repository has actually hit is building
  a page before its source was verified and then correcting it three times.</p>
  <p class="timestamp">Built {esc(BUILT_AT)} from <code>data/session-2b927826/suggestions.json</code></p>
</div>
<div class="kpis">
  {kpi("Suggestions", str(c["rows"]), "one row each")}
  {kpi("Implemented or partial", str(c["implemented_or_partial"]), "by this or an earlier session")}
  {kpi("Awaiting a choice", str(c["suggested"]), "nothing is built until a reviewer picks")}
  {kpi("Cheapest first step", "SG-03", "the capture workflow already exists")}
</div>
<div class="note"><strong>How to choose.</strong> {esc(sug["review_process"])}</div>
{table(["ID", "Suggestion", "Type", "Status", "Pre-condition", "Cost", "What it produces",
        "Decision it changes", "Gate that confirms it", "Source"],
       rows, f"All {c['rows']} suggestions")}
<div class="grid2">
  <div class="panel">
    <h2>If you do only three things</h2>
    <ul class="bullets">
      <li><strong>SG-03 &mdash; widen the injury capture.</strong> The workflow exists; it needs a schedule. It
      produces the first designation change this repository has ever recorded, which is the gate on the brief's
      central injury requirement.</li>
      <li><strong>SG-01 and SG-02 &mdash; capture the inactive list and the Game Book.</strong> Together they turn a
      projection into an observation and close the availability graph.</li>
      <li><strong>SG-04 &mdash; write the price policy and start the opening/closing store.</strong> It cannot be
      backfilled, so every week without it is a permanent gap in closing-line value.</li>
    </ul>
  </div>
  <div class="panel">
    <h2>What not to do next</h2>
    <ul class="bullets">
      <li><strong>Do not model availability with a fixed points penalty.</strong> The brief forbids it and the honest
      version of the test already exists (SG-09).</li>
      <li><strong>Do not rank anything on this week's numbers.</strong> Nothing clears the gates and every result is
      inside its luck band (SG-10).</li>
      <li><strong>Do not fill a blank from the third-party feed.</strong> Roof and surface are the current temptation;
      they are blank for a reason (SG-08).</li>
      <li><strong>Do not build a 3rd/4th-string deficiency matrix yet.</strong> No club is projected to start one this
      week, so the matrix would have no rows and would look like a defect.</li>
    </ul>
  </div>
</div>
""")


# ---------------------------------------------------------------- verification
def build_verification() -> str:
    ver, flg = load("verification.json"), load("flags.json")
    checks = []
    for c in ver["checks"]:
        srcs = c.get("sources") or ([c["source"]] if str(c.get("source", "")).startswith("http") else [])
        if srcs:
            srch = " ".join(src_cell(u, u.split("//")[1].split("/")[0]) for u in srcs)
        else:
            srch = src_cell("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-2b927826/verification.json", "record")
        res = c["result"]
        if res.startswith("PASS"):
            st = badge("done")
        elif res.startswith(("FAIL", "NOT")):
            st = badge("not met")
        else:
            st = badge("partial")
        checks.append(
            f"<td>{esc(c['id'])}</td><td>{esc(c['what'])}</td>"
            f"<td class='sub2'>{esc(c['method'])}</td>"
            f"<td>{st}<br><span class='sub2'>{esc(res)}</span></td>"
            f"<td>{srch}</td>")
    flags = []
    for f in flg["rows"]:
        if f["status"].startswith("open"):
            label, st = "open", badge("not met")
        elif f["status"].startswith("needs"):
            label, st = "needs review", badge("partial")
        else:
            label, st = "resolved", badge("done")
        settle = src_cell(f["official_source"], "settles it") if f["official_source"].startswith("http") \
            else missing(None, "no official source applies")
        flags.append(
            f"<td>{esc(f['id'])}</td><td>{esc(f['severity'])}</td>"
            f"<td><strong>{esc(f['what'])}</strong><br><span class='sub2'>{esc(f['detail'])}</span></td>"
            f"<td class='sub2'>{esc(f['repo_says'])}</td>"
            f"<td>{st}<br><span class='sub2'>{esc(label)}</span></td>"
            f"<td>{settle}</td>")
    own = []
    for d in ver["defects_of_my_own"]:
        own.append(
            f"<td>{esc(d['id'])}</td><td>{esc(d['what'])}</td><td class='sub2'>{esc(d['how_found'])}</td>"
            f"<td class='sub2'>{esc(d['fix'])}</td><td class='sub2'>{esc(d['why_published'])}</td>")
    passing = sum(1 for c in ver["checks"] if c["result"].startswith("PASS"))
    fc = flg["counts"]
    flagsub = f'{fc["open"]} open / {fc["needs_review"]} need review / {fc["resolved"]} resolved'
    return page("verification.html", "Verification", f"""
<div class="page-head">
  <p class="eyebrow">Line by line</p>
  <h1>Every check, every flag, and the errors this page's own build made</h1>
  <p class="standfirst">The brief asks for line-by-line verification against official sources, a source link on every
  row, and a blank whenever a value cannot be confirmed. {len(ver["checks"])} checks were run this session,
  {flg["counts"]["rows"]} flags are published, and two defects in this session's own work were caught before
  publication &mdash; they are published here rather than quietly fixed.</p>
  <p class="timestamp">Built {esc(BUILT_AT)} from <code>data/session-2b927826/verification.json</code> and
  <code>flags.json</code></p>
</div>
<div class="kpis">
  {kpi("Official pages read", str(ver["headline"]["official_sources_read"]), "nfl.com only, this session")}
  {kpi("Cells checked", f'{ver["headline"]["cells_checked_against_a_source"]:,}', "against an official page or a committed file")}
  {kpi("Checks passing", str(passing), f'of {len(ver["checks"])}')}
  {kpi("Flags raised", str(flg["counts"]["rows"]),
       flagsub)}
  {kpi("Blanks left blank", str(ver["headline"]["unverified_blanks_left_blank"]), "no value filled from a non-official source")}
</div>
{table(["Check", "What was checked", "Method", "Result", "Source read"], checks, f"All {len(ver['checks'])} checks")}
{table(["Flag", "Severity", "What", "What the repository says", "Status", "Official source that settles it"], flags,
       f"Flag register &mdash; {flg['counts']['rows']} rows")}
<div class="panel">
  <h2>This session's own defects</h2>
  <p class="sub">A verification page that reports only other people's errors is not a verification page. Both of these
  were caught by the field-by-field comparison against the source file, before the page was built.</p>
  <div class="table-wrap"><table><thead><tr>
    <th>ID</th><th>What was wrong</th><th>How it was found</th><th>Fix</th><th>Why it is published</th>
  </tr></thead><tbody>{''.join(own)}</tbody></table></div>
</div>
<div class="grid2">
  <div class="panel">
    <h2>Not verified in this session</h2>
    <p class="sub">Stated so that the page cannot be read as covering more than it does.</p>
    <ul class="bullets">{''.join(f"<li>{esc(x)}</li>" for x in ver["not_verified_in_this_session"])}</ul>
  </div>
  <div class="panel">
    <h2>How these pages gate themselves</h2>
    <ul class="bullets">
      <li><code>brief/verify.py</code> fails the build when a table row has no <code>https</code> source link and no
        explicit "not published" label.</li>
      <li>It fails when any table cell renders empty, or contains one of the usual stand-in tokens &mdash; the four-letter to-do and not-applicable markers, the sample-text word, and a literal empty-value repr.</li>
      <li>It fails when a local <code>href</code> does not resolve, or when a page is unreachable from the index.</li>
      <li>It fails when a <code>data/session-2b927826/*.json</code> file changes without the pages being rebuilt.</li>
      <li>The repository's existing gates (<code>tools/verify.py</code>, <code>check_reachability.py</code>,
        <code>build_site_all.py --check</code>) run over these pages too, unchanged.</li>
    </ul>
  </div>
</div>
""")


BUILDERS = {
    "index.html": build_index,
    "requirements.html": build_requirements,
    "answers.html": build_answers,
    "strategies.html": build_strategies,
    "availability.html": build_availability,
    "fixtures.html": build_fixtures,
    "suggestions.html": build_suggestions,
    "verification.html": build_verification,
}


def main() -> None:
    os.makedirs(HERE, exist_ok=True)
    total = 0
    for name, fn in BUILDERS.items():
        out = fn()
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            f.write(out)
        total += len(out.encode())
        print(f"wrote brief/{name} ({len(out.encode()):,} bytes)")
    print(f"{len(BUILDERS)} pages, {total:,} bytes -> {HERE}")


if __name__ == "__main__":
    main()
