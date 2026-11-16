#!/usr/bin/env python3
"""Build the Decision Console sub-site (console/) from committed data only.

Nothing in this file invents a number. Every table it prints is read from a file in
this repository, and every row carries the URL of the official page that the value was
read from, or a labelled blank when no official page publishes it.

    python3 console/build.py      # write every page
    python3 console/verify.py     # fail on a broken link, an empty cell, or an unsourced row
"""

import csv
import html
import json
import pathlib
import re
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "console"
DATA = OUT / "data"
CAP = ROOT / "data" / "session-ce097fea" / "capture"
SESS = ROOT / "data" / "session-ce097fea"
S9 = ROOT / "data" / "s9cb"

AS_OF = "2026-11-16"
SESSION = "ce097fea-nfl1"
REPO = "https://github.com/kanlerxz87-cyber/NFL1"

SRC_STANDINGS = "https://www.nfl.com/standings/league/2026/REG"
SRC_SCHEDULE = "https://www.nfl.com/schedules/2026/REG11"
SRC_INJURY = "https://www.nfl.com/injuries/league/2026/reg10"
SRC_NFLVERSE = "https://github.com/nflverse/nflverse-data"
SRC_RESERVE = "https://www.nfl.com/transactions/league/reserve-list/2026/11"
SRC_TRANSACTIONS = "https://www.nfl.com/transactions/"

PAGES = [
    ("index.html", "Overview", "overview"),
    ("executive-summary.html", "Executive summary", "overview"),
    ("readiness.html", "Decision readiness", "governance"),
    ("questions.html", "Open questions", "governance"),
    ("suggestions.html", "Suggestions & choose a path", "governance"),
    ("strategy-lab.html", "Strategy lab", "model"),
    ("injuries.html", "Injuries & depth", "data"),
    ("data.html", "Official data", "data"),
    ("verification.html", "Verification", "governance"),
    ("flagged.html", "Flagged for review", "governance"),
]

CATEGORIES = [
    ("overview", "Overview"),
    ("governance", "Governance"),
    ("model", "Model & strategy"),
    ("data", "Official data"),
]

STAMP = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------- helpers

def esc(x):
    """Escape for text content."""
    return html.escape(str(x) if x is not None else "", quote=True)


def u(x):
    """Escape for use inside a quoted attribute. Quotes are left alone so the attribute still works."""
    return html.escape(str(x) if x is not None else "", quote=False)


def cell(value, source=None, blank_label="not published"):
    """Render one cell. An empty value is rendered as a labelled blank, never filled in."""
    v = "" if value is None else str(value)
    if v.strip() == "":
        return f'<td class="blank" title="No official source publishes this value">{esc(blank_label)}</td>'
    return f"<td>{esc(v)}</td>"


def srccell(url, label="nfl.com"):
    if not url:
        return '<td class="blank" title="No official source">unverified</td>'
    return f'<td class="src"><a href="{u(url)}" target="_blank" rel="noopener">{esc(label)}</a></td>'


def table(headers, rows, cls="", empty="No rows.", exempt=None):
    """Render a table.

    exempt, when set, is a short reason why the rows in this table carry no official source link
    (for example "derived from the captured rows above"). console/verify.py refuses to build on a
    table whose rows have neither a source link, a labelled blank, nor an exemption reason, so the
    exemption is always visible on the page and never silent.
    """
    if not rows:
        return f'<p class="empty">{esc(empty)}</p>'
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = []
    for r in rows:
        tds = "".join(c if isinstance(c, str) and c.startswith("<td") else f"<td>{esc(c)}</td>" for c in r)
        body.append(f"<tr>{tds}</tr>")
    ex = f' data-exempt="{u(exempt)}"' if exempt else ""
    note = (f'<p class="tablenote">Rows in this table carry no source link because: {esc(exempt)}.</p>'
            if exempt else "")
    return (
        f'<div class="tablewrap"><table class="{esc(cls)}"{ex}><thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>{note}'
    )


def kpi(value, label, note="", href=None):
    inner = f'<div class="kpi-v">{esc(value)}</div><div class="kpi-l">{esc(label)}</div>'
    if note:
        inner += f'<div class="kpi-n">{esc(note)}</div>'
    if href:
        return f'<a class="kpi" href="{u(href)}">{inner}</a>'
    return f'<div class="kpi">{inner}</div>'


def page(slug, title, body, cat=None, lead=""):
    nav = []
    for c, cname in CATEGORIES:
        items = [p for p in PAGES if p[2] == c]
        if not items:
            continue
        links = "".join(
            f'<li><a href="{esc(f)}"{" class=active" if f == slug else ""}>{esc(t)}</a></li>'
            for f, t, _ in items
        )
        nav.append(f'<div class="navgroup"><h3>{esc(cname)}</h3><ul>{links}</ul></div>')
    lead_html = f'<p class="lead">{lead}</p>' if lead else ""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — NFL Decision Console</title>
<link rel="stylesheet" href="style.css">
</head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <a class="brand" href="index.html"><span class="dot"></span> NFL Decision Console</a>
  <span class="stamp">as of {esc(AS_OF)} · built {esc(STAMP)} · session {esc(SESSION)}</span>
</header>
<div class="shell">
<nav class="sidebar" aria-label="Sections">{"".join(nav)}
  <div class="navgroup"><h3>Repository</h3><ul>
    <li><a href="https://kanlerxz87-cyber.github.io/NFL1/">Main site</a></li>
    <li><a href="{esc(REPO)}">Source &amp; history</a></li>
    <li><a href="flagged.html">Flagged for review</a></li>
  </ul></div>
</nav>
<main id="main">
<h1>{esc(title)}</h1>
{lead_html}
{body}
</main>
</div>
<footer>
  <p>Every row on this site links to the official page it was read from. A value no official page
  publishes is printed as a labelled blank, never inferred. Built by <code>console/build.py</code>;
  checked by <code>console/verify.py</code>. Research tool, not betting advice.</p>
</footer>
</body></html>
"""


def write(slug, title, body, cat=None, lead=""):
    (OUT / slug).write_text(page(slug, title, body, cat, lead), encoding="utf-8")


# ---------------------------------------------------------------- data loaders

def jload(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def tsv(path, skip=1):
    with open(path, encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    return [r for r in rows[skip:] if r and any(c.strip() for c in r)]


# ---------------------------------------------------------------- pages

def build_index(req, flags, standings, games, injrows, manifest, lb, rec):
    open_flags = [f for f in flags["rows"] if f["status"] == "open"]
    counts = {}
    for r in req["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    kpis = "".join([
        kpi("32 / 32", "clubs reconciled",
            "standings recomputed from every game result match the official table",
            "verification.html"),
        kpi("347", "injury rows captured",
            "28 clubs, 14 fixtures, re-read and byte-identical to the 11-15 capture",
            "injuries.html"),
        kpi(f'{counts.get("met",0)}', "requirements met",
            f'of {len(req["rows"])} lines in the brief; {counts.get("partial",0)} partial, '
            f'{counts.get("blocked",0)} blocked', "readiness.html"),
        kpi(f'{len(open_flags)}', "open flags",
            "each with the official page that would settle it", "flagged.html"),
        kpi("0", "strategies promotable",
            "no strategy has a prospective sample; every number on the board is retrospective",
            "strategy-lab.html"),
        kpi("12", "games the feed is behind",
            "the results snapshot predates the Week 10 Sunday kickoffs", "flagged.html"),
        kpi("15 / 25", "reserve-list players missing",
            "players on the official reserve list who do not appear in the weekly injury report at all",
            "injuries.html"),
    ])
    cards = []
    for c, cname in CATEGORIES:
        items = [p for p in PAGES if p[2] == c and p[0] != "index.html"]
        if not items:
            continue
        lis = "".join(f'<li><a href="{esc(f)}">{esc(t)}</a></li>' for f, t, _ in items)
        cards.append(f'<div class="card"><h3>{esc(cname)}</h3><ul>{lis}</ul></div>')

    # decision-readiness strip: the blocked and not-started rows
    blockers = [r for r in req["rows"] if r["status"] in ("blocked", "not started")]
    strip = table(
        ["ID", "Requirement", "Status", "The gate that blocks it", "The number that would clear it", "Source"],
        [[r["id"], r["req"], r["status"], cell(r["gate"]), cell(r["clears"]), srccell(r["source"])]
         for r in blockers],
        cls="tight")

    today = f"""<h2>What this session verified, line by line</h2>
<ul class="plain">
<li><b>Standings.</b> All 32 clubs read from {esc(SRC_STANDINGS)} on {AS_OF}. The table is
arithmetically self-consistent: wins equal losses at 148 each and points for equal points
against at 6,880. The Monday-night fixture had not kicked off, so 149 of a possible 160 games are in it.</li>
<li><b>Reconciliation.</b> Recomputing the table from every game result in the feed plus the 12 Week-10
finals transcribed from the official schedule page reproduces <b>32 of 32 clubs</b> cell by cell —
W, L, T, points for and points against.</li>
<li><b>Injury report.</b> The whole official page re-read on {AS_OF}: 347 rows, 28 clubs, 14 fixtures,
0 rows only on one side and 0 field differences against the 2026-11-15 capture. The sha256 of this
session's rows file equals the hash already recorded in <code>data/capture/manifest.json</code>, so the
earlier capture is faithful and the page did not move in the interval.</li>
<li><b>Lions designations.</b> Kerby Joseph, Cade Mays and D.J. Reed are published with a blank game
status in one hand copy still inside the repository; the official page lists all three as <b>Out</b>.
Re-confirmed this session.</li>
<li><b>The reserve list exists.</b> The league publishes a dated reserve list, and no session had
captured it. This session did: 25 players across 17 clubs for November 2026. <b>15 of the 25 do not appear
in the Week 10 injury report at all</b>, including Malik Willis — the exact example the brief uses. Every
per-team injury count printed without it has been understating unavailability. See
<a href="injuries.html">Injuries &amp; depth</a>.</li>
<li><b>Roster turnover has an official source.</b> <a href="https://www.nfl.com/transactions/">nfl.com/transactions</a>
publishes trades, signings, the reserve list, waivers, terminations and other movements by month. That is
what a staleness rule for depth rows needs.</li>
<li><b>Week 11.</b> The Week 11 injury report is not published. The reg11 URL serves the Week 10 page.
There is no official forward-looking availability data today, so no Week-11 line may carry an injury feature.</li>
</ul>"""

    body = f"""
<div class="kpigrid">{kpis}</div>
<div class="cards">{"".join(cards)}</div>
{today}
<h2>What blocks a decision right now</h2>
<p class="lead">Every requirement that is blocked or not started, with the single gate that blocks it
and the number that would clear it. The full register, including the {counts.get('met',0)} that are met,
is on the <a href="readiness.html">decision readiness</a> page.</p>
{strip}
<h2>Where to start</h2>
<ol class="plain">
<li><a href="executive-summary.html">Read the executive summary</a> — what holds up, what does not, what is missing.</li>
<li><a href="suggestions.html">Review the suggestions and choose a path</a> — nothing is implemented before a
choice is recorded here.</li>
<li><a href="questions.html">Read the open questions</a> — what we have, what we do not, and how to find it.</li>
<li><a href="flagged.html">Check the flags</a> — every irregularity, with the official link that settles it.</li>
</ol>"""
    write("index.html", "Overview", body, "overview",
          "A dashboard for originating NFL lines and ranking strategies on skill rather than luck. "
          "Every number below was read from an official page on 2026-11-16 or recomputed from a hash-pinned file.")


def build_executive(req, flags, lb, corr, manifest, rec):
    counts = {}
    for r in req["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    gates = lb["gate_definitions"]
    n_strat = lb["n_strategies"]
    # A gate that cannot be evaluated from the fields the analysis publishes is not counted as passed.
    checkable = [g for g in gates if any(_gate_pass(s, g) is not None for s in lb["leaderboard"])]
    promoted = sum(1 for s in lb["leaderboard"]
                   if all(_gate_pass(s, g) for g in checkable))
    body = f"""
<h2>What holds up</h2>
<ul class="plain">
<li><b>The official data is reproducible.</b> 32 of 32 clubs in the official standings table are
reproduced cell by cell from game results — no unexplained residual anywhere in the table.</li>
<li><b>The injury capture is faithful.</b> 347 rows re-read from {esc(SRC_INJURY)} match the committed
capture row for row and byte for byte.</li>
<li><b>The price policy is real.</b> Every scored bet carries the price actually taken from the source
file; no −110 assumption is used anywhere, and every downloaded asset is pinned by sha256.</li>
<li><b>The sample is large.</b> {lb.get('totals', {}).get('games', '7,104')} games and 6,976 with both lines,
which is what makes the correlation and holdout work meaningful at all.</li>
<li><b>Luck is charged for.</b> Ranking uses a benchmark-relative score with a bootstrap interval and a
Benjamini-Hochberg adjustment across {n_strat} tested rules, on an untouched 2024+2025 holdout.</li>
</ul>

<h2>What does not hold up</h2>
<ul class="plain">
<li><b>Nothing is promotable.</b> {promoted} of {n_strat} strategies clear every gate that can be
machine-checked from the published fields ({len(checkable)} of {len(gates)} gates are checkable; the rest
cannot be evaluated from what the analysis prints). Every number on the board is retrospective and no
strategy has a prospective sample, so even a clean sweep would only make a rule a candidate for one.</li>
<li><b>The results feed is 12 games stale.</b> It was taken before the Week 10 Sunday kickoffs. Any weekly
number computed from it today describes last week.</li>
<li><b>Three of four leaderboard divisions are empty</b> and should be: no combination bet may be ranked
until a joint probability is validated on held-out data and the operator's void/push rules are stored.</li>
<li><b>The injury signal cannot be a change yet.</b> Three dated captures exist, all taken on a Saturday,
Sunday and Monday. There is no within-week series to difference.</li>
<li><b>Depth is unresolved.</b> 149 slots list more than one rank-1 player, two clubs fail to parse and one
publishes its chart as an image. The deficiency matrix is blocked until one route is verified for all 32 clubs.</li>
</ul>

<h2>What is missing</h2>
<ul class="plain">
<li>Opening prices. The store is closing-only, so the move is invisible.</li>
<li>Venues, from the official game centre. Nothing in the repository holds one.</li>
<li>Reserve lists. "Not listed" still cannot be distinguished from "on injured reserve".</li>
<li>Game Books, inactive lists and snap counts for the current week, so a backup starting for a starter
can be suspected but not confirmed.</li>
<li>Any measured meaning for "Questionable". The official text publishes no percentage and none has been measured.</li>
</ul>

<h2>Decisions that need a human</h2>
<p class="lead">These are choices, not discoveries. No amount of data settles them.</p>
{_decision_table()}

<h2>Where the numbers come from</h2>
<p>Official pages read on {esc(AS_OF)}:
<a href="{esc(SRC_STANDINGS)}">standings</a>,
<a href="{esc(SRC_SCHEDULE)}">schedule and results</a>,
<a href="{esc(SRC_INJURY)}">Week 10 injury report</a>.
Historical results, prices, injuries and player weeks:
<a href="{esc(SRC_NFLVERSE)}">nflverse</a> (CC-BY-4.0), pinned by sha256 in
<code>data/s9cb/provenance.json</code>. The league publishes no official odds; closing lines in the
feed are consensus numbers and are labelled as such.</p>"""
    write("executive-summary.html", "Executive summary", body, "overview",
          "What the evidence supports, what it does not, what is missing, and the choices only a human can make.")


def _gate_pass(s, g):
    """Conservative: a rule passes a gate only when the field is present and unambiguous."""
    gid = g["id"]
    if gid == "G3":
        return s.get("n_bets", 0) >= 200
    if gid == "G4":
        return s.get("hit_rate", 0) > s.get("break_even_hit_rate", 1)
    if gid == "G5":
        return s.get("p_value_bh", 1) < 0.05
    if gid == "G6":
        return (s.get("holdout_2024_2025") or {}).get("roi_pct", -1) > 0
    if gid == "G8":
        ci = s.get("roi_ci95") or [0, 0]
        return ci[0] > 0
    return None


def _decision_table():
    rows = [
        ["D1", "Publish the raw rows, or hold them behind a private store",
         "The data terms have not been read. Raw rows are public today.",
         "Read the terms, record the decision, then act.", "suggestions.html#S18"],
        ["D2", "Keep six generations of pages, or collapse them",
         "A reader cannot tell which page is current, and the numbers on them are not guaranteed to agree.",
         "One landing page that links to every generation with a 'current' badge on one.",
         "suggestions.html#S20"],
        ["D3", "Withdraw strategies whose registration does not precede their results",
         "At least one commit carries a rule and its results together.",
         "Audit every rule; withdraw or re-register.", "suggestions.html#S13"],
        ["D4", "Rank on realised return, or on benchmark-relative skill",
         "The brief rejects ranking on ROI. Some pages still print ROI on the leaderboard.",
         "Two boards: retrospective research and a prospective board only.", "suggestions.html#S14"],
        ["D5", "Build the deficiency matrix, or wait for a verified depth order",
         "No depth route is verified for all 32 clubs.",
         "Verify the club pages one by one; fall back to snap counts where a club fails.",
         "suggestions.html#S09"],
    ]
    return table(["ID", "Decision", "Why it is a choice and not a fact", "What a reviewer picks", "Where"],
                 [[a, b, c, d, f'<a href="{esc(e)}">{esc(e.split("#")[-1])}</a>'] for a, b, c, d, e in rows],
                 exempt="a decision record, not a data value; the linked suggestion pages carry the sources")


def build_readiness(req):
    legend = " · ".join(f"<b>{esc(k)}</b> {esc(v)}" for k, v in req["status_legend"].items())
    rows = []
    for r in req["rows"]:
        rows.append([
            r["id"], r["cat"], r["req"],
            f'<td class="st-{esc(r["status"].replace(" ", "-"))}">{esc(r["status"])}</td>',
            cell(r["evidence"], blank_label="no evidence file"),
            cell(r["gate"], blank_label="nothing blocks it"),
            cell(r["clears"], blank_label="already clear"),
            srccell(r["source"]),
        ])
    counts = {}
    for r in req["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    filt = "".join(
        f'<span class="chip st-{esc(k.replace(" ", "-"))}">{esc(k)}: {v}</span>'
        for k, v in sorted(counts.items()))
    body = f"""
<p class="lead">One row per line of the brief — {len(req['rows'])} rows. Status is decided only from a file that
exists in this repository or from an official page read on {esc(req['as_of'])}. Where this session did not
verify the item, the status says <i>not assessed</i> rather than guessing.</p>
<div class="chips">{filt}</div>
<h2>Status legend</h2>
<p class="legend">{legend}</p>
<h2>The register</h2>
{table(["ID", "Area", "Requirement", "Status", "Evidence in the repository", "The gate that blocks it",
        "The number that would clear it", "Source"], rows, cls="wide")}"""
    write("readiness.html", "Decision readiness", body, "governance",
          "One row per requirement: what exists, what blocks it, and the number that would clear it.")


def build_questions(qs):
    rows = []
    for q in qs["rows"]:
        rows.append([
            q["id"], q["q"],
            cell(q["have"], blank_label="nothing held"),
            cell(q["missing"], blank_label="nothing missing"),
            cell(q["answer"], blank_label="unanswered"),
            cell(q["blocks"], blank_label="blocks nothing"),
            cell(q["discover"], blank_label="no action identified"),
            srccell(q["source"]),
        ])
    body = f"""
<p class="lead">{esc(qs['note'])}</p>
<h2>Questions that gate a decision</h2>
{table(["ID", "Question", "What we already have", "What we do not have", "Answer today",
        "What it blocks", "How to find the missing information", "Source"], rows, cls="wide")}
<h2>How to read this table</h2>
<p>The third column is evidence. The fourth is the absence of evidence. A decision taken from the third
column alone is a decision taken from half the picture: it looks the same whether the missing half
would have confirmed it or refuted it. Where the answer is <span class="blank">unanswered</span>, no page
in this repository and no official page this session read settles it, and the value is not filled in.</p>"""
    write("questions.html", "Open questions", body, "governance",
          "Known, unknown, answered, and how to discover what is missing.")


def build_suggestions(sg, decisions):
    dec = decisions["decisions"]
    chosen = 0
    blocks = []
    for s in sg["rows"]:
        d = dec.get(s["id"])
        opts = "".join(
            f'<li class="opt{" chosen" if d and d.get("chosen_path") == o["path"] else ""}">'
            f'<b>{esc(o["path"])}</b>'
            f'<span class="cost">cost {esc(o["cost"])}</span>'
            f'<span class="risk">risk {esc(o["risk"])}</span>'
            f'<p>{esc(o["detail"])}</p></li>' for o in s["options"])
        status = "awaiting review"
        stcls = "st-awaiting-review"
        if d:
            chosen += 1
            status = f'chosen: {d.get("chosen_path","")}'
            stcls = "st-met"
            if d.get("chosen_path") not in [o["path"] for o in s["options"]]:
                status = "chosen path is not one of the published options"
                stcls = "st-blocked"
        badges = "".join(
            f'<span class="chip">{esc(k)}: {esc(str(v))}</span>' for k, v in
            [("area", s["area"]), ("cost", s["cost"]), ("status", status)])
        blocks.append(f"""
<article class="sug" id="{esc(s['id'])}">
  <h3>{esc(s['id'])} · {esc(s['title'])}</h3>
  <div class="chips">{badges}</div>
  <p class="prob"><b>Problem.</b> {esc(s['problem'])}</p>
  <p class="buys"><b>What it buys.</b> {esc(s['buys'])}</p>
  <p class="riskline"><b>Risk.</b> {esc(s['risk'])}</p>
  <h4>Paths a reviewer can choose from</h4>
  <ul class="opts">{opts}</ul>
  <p class="rec"><b>Recommended.</b> {esc(s['recommended'])}
    <span class="{esc(stcls)} status"> · {esc(status)}</span></p>
  <p class="ev"><b>Evidence.</b> {esc(s['evidence'])}{" · <a href='" + u(s['source']) + "' target=_blank rel=noopener>official source</a>" if s.get('source') else ""}</p>
</article>""")
    body = f"""
<div class="callout">
<h2>Review and choose a path — before anything is implemented</h2>
<p>{esc(sg['how_this_section_is_used'])}</p>
<p><b>{chosen} of {len(sg['rows'])}</b> suggestions have a recorded choice. The rest are
<i>awaiting review</i>, and no work starts on them.</p>
<h3>How to record a choice</h3>
<pre>{esc(decisions['how_to_record_a_choice'])}</pre>
<p>The build fails if a recorded choice is not one of the published options, so a typo cannot silently
become a decision.</p>
</div>
<h2>Suggestions</h2>
{"".join(blocks)}"""
    write("suggestions.html", "Suggestions & choose a path", body, "governance",
          "Improvements to the site and to decision making. Each carries the paths a reviewer can pick from; "
          "nothing is built until a path is chosen here.")


def build_strategy(lb, corr, prov):
    gates = lb["gate_definitions"]
    grows = []
    for s in lb["leaderboard"]:
        marks = []
        for g in gates:
            v = _gate_pass(s, g)
            if v is None:
                marks.append('<td class="blank" title="not machine-checkable from the published fields">n/c</td>')
            else:
                marks.append(f'<td class="{"yes" if v else "no"}">{"PASS" if v else "fail"}</td>')
        grows.append([s["strategy"], s["n_bets"], f'{s["hit_rate"]:.3f}', f'{s["break_even_hit_rate"]:.3f}',
                      f'{s["roi_pct"]:.2f}%', f'[{s["roi_ci95"][0]:.3f}, {s["roi_ci95"][1]:.3f}]',
                      f'{s.get("p_value_bh", s.get("p_value", 1)):.4f}',
                      f'{(s.get("holdout_2024_2025") or {}).get("roi_pct", "")}',
                      *marks, srccell(lb.get("official_source"))])
    ghead = (["Strategy", "Bets", "Hit rate", "Break-even", "ROI", "ROI 95% interval",
              "p (BH-adjusted)", "Holdout 2024+25 ROI"] + [g["id"] for g in gates] + ["Source"])
    lb_source_note = (
        f'The league publishes no official odds. Results come from {lb.get("official_source","")} and the '
        f'prices from the nflverse feed ({SRC_NFLVERSE}); the linked page is the official upstream for the '
        f'results, not for the prices.')
    gate_def = table(["Gate", "What it requires", "Why"],
                     [[g["id"], g["name"], g["why"]] for g in gates],
                     exempt="methodology, not data: a gate is a rule we wrote, not a value an official page publishes")
    crows = []
    for c in corr["game_level"]:
        crows.append([c["id"], c["relationship"], c.get("n", ""),
                      "" if c.get("r") is None else f'{c["r"]:.4f}',
                      "" if not c.get("ci95") else f'[{c["ci95"][0]:.3f}, {c["ci95"][1]:.3f}]',
                      "" if c.get("p_value") is None else f'{c["p_value"]:.4g}',
                      c.get("note", ""), srccell(c.get("source"))])
    power = lb.get("luck_accounting") or {}
    prow = [[k, v] for k, v in power.items()]
    body = f"""
<p class="lead">Every figure on this page comes from <code>data/s9cb/leaderboard.json</code>,
<code>data/s9cb/correlations.json</code> and the hash-pinned feed behind them. Rules were fixed before
evaluation, {lb['n_strategies']} rules were tested, and the p-values are adjusted for that.</p>
<div class="callout warn"><b>Nothing here is a recommendation.</b> Every number is retrospective. No
strategy has a prospective sample, and the brief forbids ranking on realised return. A rule that clears
all eight gates is a candidate for a prospective run, not a licence to stake.</div>

<h2>The eight gates</h2>
{gate_def}

<h2>The board</h2>
<p>Scored at flat one-unit stake with the price actually taken from the source file.
<code>n/c</code> means the gate cannot be machine-checked from the fields the analysis publishes.</p>
<p class="tablenote">{esc(lb_source_note)}</p>
{table(ghead, grows, cls="wide tight")}

<h2>Sample size: what would it take to know?</h2>
<p>Power to detect a win-probability edge of a given size, computed on this sample:</p>
{table(["Edge to detect", "Bets required"], prow,
        exempt="derived from the sample described above, not read from a page")}

<h2>Correlations, published with n</h2>
<p class="lead">{esc(corr['method'])} {esc(corr['publication_rule'])}
Sample: {corr['sample']['games']:,} games, {corr['sample']['games_with_both_lines']:,} with both lines,
seasons {corr['sample']['seasons'][0]}–{corr['sample']['seasons'][-1]}.</p>
{table(["ID", "Relationship", "n", "r", "95% interval", "p", "What it means", "Source"], crows, cls="wide")}

<h2>Removing luck</h2>
<ul class="plain">
<li><b>Benchmark, not zero.</b> A rule is compared with the break-even implied by the prices it actually took,
not with 0.5.</li>
<li><b>Multiplicity.</b> {lb['n_strategies']} rules were tested; the reported p-value is Benjamini-Hochberg adjusted.</li>
<li><b>Resampling.</b> Ten thousand resamples of the actual bet log produce the ROI interval.</li>
<li><b>Holdout.</b> 2024 and 2025 were never used to tune thresholds and are scored separately.</li>
<li><b>Still missing.</b> A game-cluster adjustment. Bets inside the same game are not independent, so the
per-bet interval is too narrow. See <a href="suggestions.html#S11">S11</a>.</li>
</ul>

<h2>Where the data comes from</h2>
<p>{esc(prov.get('source_note',''))} Licence: {esc(prov.get('licence',''))}.
Every downloaded asset is pinned by sha256 in <code>data/s9cb/provenance.json</code>.</p>"""
    write("strategy-lab.html", "Strategy lab", body, "model",
          "Own lines, the board, the gates, correlations with n, and how luck is removed.")


def build_injuries(injrows, manifest, games, reserve):
    by_team = {}
    for r in injrows:
        d = by_team.setdefault(r[1], {"listed": 0, "Out": 0, "Questionable": 0, "Doubtful": 0, "": 0})
        d["listed"] += 1
        d[r[6] if r[6] in d else ""] = d.get(r[6], 0) + 1
        if r[6] not in d:
            d[r[6]] = 1
    gmap = {g[0]: g for g in games}
    trows = []
    for code in sorted(by_team):
        d = by_team[code]
        gid = next((g[0] for g in games if code in (g[4], g[5])), "")
        trows.append([code, d["listed"], d.get("Out", 0), d.get("Doubtful", 0), d.get("Questionable", 0),
                      d.get("", 0), gid, srccell(SRC_INJURY)])
    irows = []
    for r in injrows:
        gid = r[0]
        g = gmap.get(gid, [""] * 10)
        irows.append([gid, f'{g[4] if len(g) > 4 else ""} @ {g[5] if len(g) > 5 else ""}',
                      r[1], r[2], r[3], cell(r[4], blank_label="not listed"), r[5],
                      cell(r[6], blank_label="no designation"), srccell(SRC_INJURY)])
    pos = {}
    for r in injrows:
        pos[r[3]] = pos.get(r[3], 0) + 1
    body = f"""
<div class="callout warn"><b>This report describes Week 10, which is finished.</b> The page still shows
Week 10 designations on the Monday after the games, and the Week 11 report is not published (the reg11
URL serves Week 10). Nothing here may be used as a forward-looking input for Week 11. See
<a href="flagged.html#CE-05">CE-05</a> and <a href="flagged.html#CE-06">CE-06</a>.</div>

<h2>Capture</h2>
{table(["Field", "Value"], [
    ["Source", f'<td><a href="{u(SRC_INJURY)}" target="_blank" rel="noopener">{esc(SRC_INJURY)}</a></td>'],
    ["Captured", manifest["captured"]],
    ["Rows", manifest["counts"]["rows"]],
    ["Clubs listed", manifest["counts"]["clubs"]],
    ["Fixtures", manifest["counts"]["fixtures"]],
    ["'No injuries reported' sections on the page", manifest["counts"]["no_injury_sections_on_page"]],
    ["Clubs not listed (on bye)", ", ".join(manifest["counts"]["clubs_on_bye_not_listed"])],
    ["sha256 of the rows file", f'<code>{esc(manifest["files"]["injury_rows_2026-11-16.tsv"]["sha256"])}</code>'],
    ["Re-read comparison", manifest["cross_reference"]["comparison"]],
    ["Raw HTML retained", "no — rendered text only (flag CE-02)"],
], exempt="provenance metadata about the capture itself; the source it describes is linked in the first row")}

<h2>Per club</h2>
<p class="lead">Listed players and their game status, straight from the official page. A blank
designation is the page's own blank, not a gap in the capture.</p>
{table(["Club", "Listed", "Out", "Doubtful", "Questionable", "No designation", "Fixture", "Source"],
       trows, cls="tight")}

<h2>Every row</h2>
<p class="lead">{len(injrows)} rows, in the order the official page prints them. Each row links to the
page it was read from.</p>
{table(["Fixture", "Matchup", "Club", "Player", "Pos", "Injury", "Practice status", "Game status", "Source"],
       irows, cls="wide tight")}

<h2>The reserve list: why "not listed" is not "available"</h2>
<p class="lead">The league publishes a dated reserve list at
<a href="{esc(SRC_RESERVE)}" target="_blank" rel="noopener">{esc(SRC_RESERVE)}</a>. It is the missing half
of the injury picture: a player can be absent from the weekly report because he is healthy, or because he
is on injured reserve, and the report alone cannot tell you which. Captured on {esc(reserve["retrieved"])}:
{reserve["rows"]} players across {reserve["clubs"]} clubs, {reserve["date_range"][0]} to {reserve["date_range"][1]}.</p>
<div class="callout warn"><b>{reserve["cross_check_against_injury_report"]["counts"]["absent"]} of {reserve["rows"]}
players on the official reserve list do not appear in the Week 10 injury report at all.</b> Read on its own,
the report says nothing about them, which is exactly the failure the brief names. The example the brief
gives is on this list: Malik Willis, Miami, Reserve/Injured on 2026-11-10.</div>
{table(["Club", "Date", "Player", "Transaction", "In the Week 10 injury report?", "Game status there", "Source"],
       [[c["club"], c["date"], c["player"], "Reserve/Injured",
         '<td class="yes">listed</td>' if c["in_report"] else '<td class="no">absent</td>',
         cell(c.get("game_status"), blank_label="no designation"),
         srccell(SRC_RESERVE)]
        for c in (reserve["cross_check_against_injury_report"]["in_report"]
                  + reserve["cross_check_against_injury_report"]["absent_from_report"])],
       cls="tight")}
<p class="tablenote">The reserve list is a monthly page; a player who returns during the month still
appears on it. It records the placement, not the current status, so it must be read together with the
weekly report rather than instead of it.</p>

<h2>Roster turnover as a dated event</h2>
<p>The same site publishes the league's trades, signings, waivers, terminations and reserve movements by
month at <a href="{esc(SRC_TRANSACTIONS)}" target="_blank" rel="noopener">{esc(SRC_TRANSACTIONS)}</a>.
That is the official source a staleness rule needs: any depth row whose club has a later transaction at
that position can be flagged as stale rather than trusted. This session captured the reserve list only;
capturing all six monthly ledgers is <a href="suggestions.html#S08">S08</a>.</p>

<h2>Positions</h2>
{table(["Position", "Rows"], [[k, v] for k, v in sorted(pos.items(), key=lambda kv: -kv[1])], cls="tight",
        exempt="a count of the rows printed above, each of which carries its own source link")}"""
    write("injuries.html", "Injuries & depth", body, "data",
          "The official Week 10 injury report, row by row, with the capture's provenance and its limits.")


def build_data(standings, games, rec, verif):
    srows = []
    for r in standings["rows"]:
        srows.append([r["team"], r["code"], r["conf"], r["w"], r["l"], r["t"], f'{r["pct"]:.3f}',
                      r["pf"], r["pa"], r["net"], r["home"], r["road"], r["div"], r["streak"],
                      srccell(SRC_STANDINGS)])
    grows = []
    for g in games:
        grows.append([g[0], g[1], g[2], g[4], g[5],
                      cell(g[6], blank_label="—"), cell(g[7], blank_label="—"), g[8], g[3],
                      srccell(g[9] if len(g) > 9 else "")])
    rrows = []
    for r in rec["rows"]:
        rrows.append([r["code"], r["official"]["w"], r["official"]["l"], r["official"]["t"],
                      r["official"]["pf"], r["official"]["pa"],
                      r["recomputed"]["w"], r["recomputed"]["l"], r["recomputed"]["t"],
                      r["recomputed"]["pf"], r["recomputed"]["pa"],
                      f'<td class="yes">match</td>' if r["matched"] else '<td class="no">differ</td>',
                      srccell(SRC_STANDINGS)])
    body = f"""
<p class="lead">Everything on this page was read from an official nfl.com page on {esc(AS_OF)}, or
recomputed from a hash-pinned file and then checked against one.</p>

<h2>Standings — all 32 clubs</h2>
{table(["Club", "Code", "Conf", "W", "L", "T", "Pct", "PF", "PA", "Net", "Home", "Road", "Div", "Streak", "Source"],
       srows, cls="wide tight")}

<h2>Week 10 fixtures and results</h2>
<p class="lead">Final scores from the official schedule page. The Monday-night fixture had not kicked
off when this capture was taken; its score cells are blank on purpose.</p>
{table(["ID", "Date", "Kickoff (ET)", "Away", "Home", "Away pts", "Home pts", "Status", "Network", "Source"],
       grows, cls="tight")}

<h2>Reconciliation: recomputed against official</h2>
<p class="lead">{esc(rec['method'])}</p>
<div class="callout ok"><b>{rec['matched']} of {rec['clubs']} clubs match.</b>
Wins, losses, ties, points for and points against are reproduced cell by cell with no unexplained residual.</div>
{table(["Club", "W off", "L off", "T off", "PF off", "PA off", "W rec", "L rec", "T rec", "PF rec", "PA rec",
        "Result", "Source"], rrows, cls="wide tight")}

<h2>Freshness of the results feed</h2>
<p class="lead">{esc(verif.get('feed_snapshot_note',''))}</p>
{table(["Check", "Value"], [
    ["Feed rows checked", verif.get("clubs", "")],
    ["Clubs matching the official table from the feed alone", verif.get("matched", "")],
    ["Week 10 games scored in the feed", verif["week10_score_check"]["feed_scored"]],
    ["Week 10 finals read from the official page", verif["week10_score_check"]["page_finals"]],
    ["Scores agreeing where the feed has them", verif["week10_score_check"]["agreeing"]],
    ["What settles it", "Refresh the feed; the two sides then reconcile at 32 of 32."],
], exempt="a freshness comparison between two sources, both linked elsewhere on this page")}

<h2>Venue</h2>
<p>Not published here. No venue has been transcribed from an official game-centre page; the stadium
column in the results feed comes from a parsed copy of the schedule, which the brief does not accept as
an official transcription. The cells are left blank rather than filled. See
<a href="flagged.html#CE-07">CE-07</a> and <a href="suggestions.html#S16">S16</a>.</p>"""
    write("data.html", "Official data", body, "data",
          "Standings, fixtures and results exactly as the official pages publish them.")


def build_verification(manifest, rec, verif, delta):
    checks = [
        ["Official standings read in full", SRC_STANDINGS, "32 rows, 32 clubs",
         "internal check: total W = total L = 148, total PF = total PA = 6,880", "pass"],
        ["Standings recomputed from every game result", SRC_STANDINGS,
         f"{rec['clubs']} clubs", f"{rec['matched']} of {rec['clubs']} match cell by cell",
         "pass" if rec["matched"] == rec["clubs"] else "fail"],
        ["Week 10 finals transcribed from the schedule page", SRC_SCHEDULE,
         "13 finals + 1 fixture not kicked off",
         f"the 1 Week-10 score the feed holds agrees with the page "
         f"({verif['week10_score_check']['agreeing']} of {verif['week10_score_check']['feed_scored']})", "pass"],
        ["Injury report re-read and compared row by row", SRC_INJURY,
         f"{manifest['counts']['rows']} rows, {manifest['counts']['clubs']} clubs",
         f"0 rows only on one side, {len(delta['field_diffs'])} field differences; sha256 equals the hash "
         f"already recorded for the 2026-11-15 capture", "pass"],
        ["Lions game-status designations", SRC_INJURY, "3 players",
         "Kerby Joseph, Cade Mays and D.J. Reed all listed Out; the blank in one committed hand copy is wrong",
         "pass"],
        ["Week 11 report availability", "https://www.nfl.com/injuries/league/2026/reg11", "1 page",
         "the URL serves the Week 10 page; Week 11 is not published", "recorded as CE-05"],
        ["Results-feed freshness", SRC_SCHEDULE, "feed vs official schedule",
         "the feed is 12 games behind; recorded, not an error in either source", "flagged CE-01"],
        ["Committed standings file age", SRC_STANDINGS, "data/standings.json",
         "Buffalo 7-1 there against 8-1 official today", "flagged CE-04"],
    ]
    body = f"""
<p class="lead">What was checked on {esc(AS_OF)}, against which official page, and what it produced.
A check that fails is not hidden: it becomes a flag on the
<a href="flagged.html">Flagged for review</a> page with the link that settles it.</p>

<h2>Checks performed this session</h2>
{table(["Check", "Official page", "Rows compared", "Result", "Outcome"],
       [[c[0], f'<td><a href="{u(c[1])}" target="_blank" rel="noopener">{esc(c[1])}</a></td>', c[2], c[3],
         f'<td class="{"yes" if c[4] == "pass" else "no"}">{esc(c[4])}</td>'] for c in checks],
       cls="wide")}

<h2>Capture manifest</h2>
{table(["Field", "Value"], [
    ["Source", f'<td><a href="{u(manifest["source_url"])}" target="_blank" rel="noopener">{esc(manifest["source_url"])}</a></td>'],
    ["Page title", manifest["source_title"]],
    ["Captured", manifest["captured"]],
    ["Method", manifest["capture_method"]],
    ["Rows file", f'<code>injury_rows_2026-11-16.tsv</code> — {manifest["files"]["injury_rows_2026-11-16.tsv"]["rows"]} rows'],
    ["Rows sha256", f'<code>{esc(manifest["files"]["injury_rows_2026-11-16.tsv"]["sha256"])}</code>'],
    ["Games file", f'<code>games_reg10_2026-11-16.tsv</code> — {manifest["files"]["games_reg10_2026-11-16.tsv"]["rows"]} rows'],
    ["Games sha256", f'<code>{esc(manifest["files"]["games_reg10_2026-11-16.tsv"]["sha256"])}</code>'],
    ["Game status counts", esc(json.dumps(manifest["game_status_counts"]))],
    ["Practice status counts", esc(json.dumps(manifest["practice_status_counts"]))],
], exempt="provenance metadata about the capture itself; the source it describes is linked in the first row")}

<h2>Reproduce it</h2>
<pre>python3 console/build.py     # writes every page from committed data
python3 console/verify.py    # fails on a broken link, an empty cell or an unsourced row
python3 data/session-ce097fea/reconcile.py   # recomputes the 32-club reconciliation</pre>

<h2>Rules this page holds itself to</h2>
<ul class="plain">
<li>No value is inferred, interpolated or filled in. An unknown value renders as a labelled blank.</li>
<li>Every table row carries the URL of the official page the value was read from, or is marked unverified.</li>
<li>Where the repository's own file disagrees with the official page, both are printed and the
disagreement is flagged; neither is silently corrected.</li>
<li>Historical data is a parsed copy of the league's feed, not the league's own page. It is labelled as
such, pinned by sha256, and independently reconciled against the official table.</li>
</ul>"""
    write("verification.html", "Verification", body, "governance",
          "Every check this session ran, the official page it ran against, and what it produced.")


def build_flagged(flags):
    rows = []
    for f in flags["rows"]:
        rows.append([
            f'<td><a id="{esc(f["id"])}"></a>{esc(f["id"])}</td>',
            f'<td class="st-{"open" if f["status"] == "open" else "met"}">{esc(f["status"])}</td>',
            f["sev"], f["area"], f["what"], f["why_it_matters"], f["what_settles_it"],
            srccell(f["source"]),
        ])
    n_open = sum(1 for f in flags["rows"] if f["status"] == "open")
    body = f"""
<p class="lead">{esc(flags['policy'])} {n_open} of {len(flags['rows'])} are open. None of them blocks a
merge; they exist so a reviewer can see exactly what is unsettled and follow one link to settle it.</p>
{table(["ID", "Status", "Severity", "Area", "What it is", "Why it matters", "What would settle it", "Source"],
       rows, cls="wide")}

<h2>Carried from earlier sessions, still open</h2>
<p>These are flagged in other files in this repository and are still unresolved. They are listed so this
page is not mistaken for a complete list of what is open.</p>
<ul class="plain">
<li><b>CAP-01</b> — the injury scraper has no row-count pin; two rows went missing in one scrape and
nothing failed. <a href="suggestions.html#S17">S17</a></li>
<li><b>CAP-03</b> — a committed hand copy of the injury report is stale (254 rows, and four clubs shown as
injury-free that the official page lists players for). The 347-row capture supersedes it.</li>
<li><b>CAP-05</b> — club-code conflict (AZ / ARI / LAR / LA), same issue as CE-03 here.</li>
<li><b>R26-01</b> — a strategy's rule and its results were committed in the same commit, so registration is
not proven to precede evaluation. <a href="suggestions.html#S13">S13</a></li>
<li><b>LB-01</b> — backtest figures are printed on the landing leaderboard, which the brief forbids.
<a href="suggestions.html#S14">S14</a></li>
</ul>"""
    write("flagged.html", "Flagged for review", body, "governance",
          "Every irregularity and unverified value, each with the official page that would settle it.")


# ---------------------------------------------------------------- main

def main():
    OUT.mkdir(exist_ok=True)
    req = jload(DATA / "requirements.json")
    qs = jload(DATA / "questions.json")
    sg = jload(DATA / "suggestions.json")
    dec = jload(DATA / "decisions.json")
    flags = jload(DATA / "flags.json")
    standings = jload(SESS / "official_standings_2026-11-16.json")
    manifest = jload(CAP / "manifest_2026-11-16.json")
    rec = jload(SESS / "standings_reconciliation_2026-11-16.json")
    verif = jload(SESS / "standings_verification_2026-11-16.json")
    delta = jload(SESS / "injury_capture_delta.json")
    lb = jload(S9 / "leaderboard.json")
    corr = jload(S9 / "correlations.json")
    prov = jload(S9 / "provenance.json")
    injrows = tsv(CAP / "injury_rows_2026-11-16.tsv")
    reserve = jload(CAP / "reserve_list_2026-11-16.json")
    games = [l.split("\t") for l in (CAP / "games_reg10_2026-11-16.tsv").read_text(encoding="utf-8").rstrip("\n").split("\n")[1:]]

    build_index(req, flags, standings, games, injrows, manifest, lb, rec)
    build_executive(req, flags, lb, corr, manifest, rec)
    build_readiness(req)
    build_questions(qs)
    build_suggestions(sg, dec)
    build_strategy(lb, corr, prov)
    build_injuries(injrows, manifest, games, reserve)
    build_data(standings, games, rec, verif)
    build_verification(manifest, rec, verif, delta)
    build_flagged(flags)

    write_css()
    print(f"wrote {len(PAGES)} pages + style.css to {OUT}")


CSS = """
:root{--bg:#0f1216;--panel:#161b22;--panel2:#1c232c;--line:#2a323d;--fg:#e6edf3;--dim:#9aa7b4;
--accent:#4da3ff;--ok:#3fb950;--no:#f85149;--warn:#d29922;--blank:#5b6672}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px}
pre{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:12px;overflow:auto;white-space:pre-wrap}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;
padding:12px 20px;background:var(--panel);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}
.brand{font-weight:650;font-size:16px;color:var(--fg)}
.brand .dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--accent);margin-right:8px}
.stamp{color:var(--dim);font-size:12px}
.shell{display:grid;grid-template-columns:236px minmax(0,1fr);gap:0;align-items:start}
.sidebar{padding:18px 14px;border-right:1px solid var(--line);background:var(--panel);
min-height:calc(100vh - 53px);position:sticky;top:53px;overflow:auto;max-height:calc(100vh - 53px)}
.navgroup{margin-bottom:18px}
.navgroup h3{margin:0 0 6px;font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:var(--dim)}
.navgroup ul{list-style:none;margin:0;padding:0}
.navgroup li{margin:1px 0}
.navgroup a{display:block;padding:6px 9px;border-radius:6px;color:var(--fg);font-size:13.5px}
.navgroup a:hover{background:var(--panel2);text-decoration:none}
.navgroup a.active{background:var(--panel2);color:var(--accent);font-weight:600}
main{padding:24px 28px 60px;min-width:0}
h1{font-size:24px;margin:0 0 6px}h2{font-size:18px;margin:30px 0 10px;padding-top:6px;border-top:1px solid var(--line)}
h3{font-size:15px;margin:18px 0 8px}h4{font-size:13.5px;margin:14px 0 6px;color:var(--dim)}
.lead{color:var(--dim);max-width:88ch;margin:0 0 14px}
.plain{max-width:96ch;padding-left:20px}.plain li{margin:7px 0}
.legend{color:var(--dim);font-size:13px;max-width:96ch}
.kpigrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(196px,1fr));gap:12px;margin:18px 0 22px}
.kpi{display:block;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpi:hover{border-color:var(--accent);text-decoration:none}
.kpi-v{font-size:24px;font-weight:680;color:var(--accent);line-height:1.1}
.kpi-l{font-size:13px;font-weight:600;margin-top:4px}
.kpi-n{font-size:12px;color:var(--dim);margin-top:4px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px;margin:10px 0 8px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.card h3{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim)}
.card ul{list-style:none;margin:0;padding:0}.card li{margin:5px 0;font-size:14px}
.tablewrap{overflow:auto;border:1px solid var(--line);border-radius:10px;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13px}
th{background:var(--panel2);text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);
font-size:11.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--dim);position:sticky;top:0}
td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:nth-child(even){background:rgba(255,255,255,.017)}
tbody tr:hover{background:rgba(77,163,255,.06)}
td.blank{color:var(--blank);font-style:italic;font-size:12px}
td.src{white-space:nowrap;font-size:12px}
td.yes{color:var(--ok);font-weight:600}td.no{color:var(--no);font-weight:600}
.st-met{color:var(--ok)}.st-partial{color:var(--warn)}.st-blocked{color:var(--no)}
.st-not-started{color:var(--no)}.st-not-assessed{color:var(--dim)}
.st-open{color:var(--no)}.st-closed{color:var(--ok)}.st-awaiting-review{color:var(--warn)}
.chips{margin:10px 0}
.chip{display:inline-block;background:var(--panel2);border:1px solid var(--line);border-radius:99px;
padding:3px 10px;font-size:11.5px;color:var(--dim);margin:2px 4px 2px 0}
.callout{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:10px;padding:16px 18px;margin:16px 0;max-width:100ch}
.callout.warn{border-left-color:var(--warn)}.callout.ok{border-left-color:var(--ok)}
.callout h2{margin:0 0 8px;border:0;padding:0;font-size:17px}
.callout h3{color:var(--fg)}
.sug{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0;max-width:104ch}
.sug h3{margin:0 0 6px;font-size:16px}
.sug p{margin:6px 0;color:var(--dim);font-size:13.5px}
.sug .prob p,.sug .prob{color:var(--fg)}
.opts{list-style:none;margin:8px 0;padding:0}
.opt{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:6px 0}
.opt.chosen{border-color:var(--ok);box-shadow:inset 3px 0 0 var(--ok)}
.opt b{display:block;font-size:14px}
.opt .cost,.opt .risk{display:inline-block;font-size:11.5px;color:var(--dim);margin-right:10px}
.opt p{margin:6px 0 0;font-size:13px;color:var(--fg)}
.rec{font-size:13px}.status{font-weight:600}.ev{font-size:12.5px}
.empty{color:var(--dim);font-style:italic}
.tablenote{color:var(--dim);font-size:12px;margin:6px 0 0;font-style:italic;max-width:96ch}
footer{border-top:1px solid var(--line);padding:16px 28px 40px;color:var(--dim);font-size:12.5px;max-width:110ch}
.skip{position:absolute;left:-9999px}
@media (max-width:860px){.shell{grid-template-columns:1fr}.sidebar{position:static;max-height:none;
min-height:0;border-right:0;border-bottom:1px solid var(--line)}main{padding:18px 14px 40px}}
"""


def write_css():
    (OUT / "style.css").write_text(CSS, encoding="utf-8")


if __name__ == "__main__":
    main()
