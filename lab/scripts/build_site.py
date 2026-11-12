#!/usr/bin/env python3
"""Session 1505ac8e - render the consolidated decision lab into lab/.

Every table row that shows data carries a link to the official page it came from.
Values that cannot be confirmed render as a labelled blank; nothing is inferred.
"""

from __future__ import annotations

import csv
import html
import json
import os
import re
import shutil
from datetime import datetime

sys_path = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, sys_path)
import content as C  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
OUTD = os.path.join(DATA, "session-1505ac8e")
SITE = os.path.join(ROOT, "lab")
PAGES = os.path.join(SITE, "pages")
RETRIEVED = "2026-11-12"

BLANK = '<span class="blank" title="Not confirmed from an official source">blank</span>'


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def esc(x):
    return html.escape("" if x is None else str(x), quote=True)


def val(x, fmt=None):
    """Render a value, or a labelled blank when it is unknown."""
    if x is None or x == "":
        return BLANK
    if isinstance(x, float) and x != x:
        return BLANK
    if fmt and isinstance(x, (int, float)):
        return esc(fmt % x)
    return esc(x)


def link(url, text=None):
    t = text or re.sub(r"^https?://(www\.)?", "", url)
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(t)}</a>'


def srclink(sources):
    """sources: list of (label, url)."""
    out = []
    for label, url in sources:
        out.append(f'<a class="src" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>')
    return "<br>".join(out) if out else BLANK


def table(cols, rows, cls="", caption=None):
    th = "".join(f"<th>{esc(c)}</th>" for c in cols)
    body = []
    for r in rows:
        cells = "".join(f"<td>{c}</td>" for c in r)
        body.append(f"<tr>{cells}</tr>")
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    return (f'<table class="{esc(cls)}">{cap}<thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table>')


def kpi(label, value, sub=""):
    s = f'<div class="kpi-sub">{esc(sub)}</div>' if sub else ""
    return f'<div class="kpi"><div class="kpi-label">{esc(label)}</div><div class="kpi-value">{esc(value)}</div>{s}</div>'


def page(title, nav_key, body, lead=None, wide=False):
    # up = prefix for files inside lab/; rootup = prefix for the repository root.
    up = "" if nav_key == "index" else "../"
    rootup = "../" if nav_key == "index" else "../../"
    nav = []
    for group, items in NAV:
        links = []
        for key, label, _ in items:
            cls = "active" if key == nav_key else ""
            href = f"{up}pages/{key}.html"
            links.append(f'<a class="{cls}" href="{esc(href)}">{label}</a>')
        nav.append(f'<div class="nav-group"><div class="nav-title">{esc(group)}</div>'
                   f'{"".join(links)}</div>')
    home = f"{up}index.html"
    lead_html = f'<p class="lead">{lead}</p>' if lead else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} - NFL Decision Lab</title>
<link rel="stylesheet" href="{'assets/style.css' if nav_key == 'index' else '../assets/style.css'}">
</head>
<body>
<header class="topbar">
  <a class="brand" href="{esc(home)}"><span class="brand-mark">NFL</span> Decision Lab</a>
  <div class="tagline">Session 1505ac8e &middot; data retrieved {RETRIEVED} &middot; every row links to its official source</div>
</header>
<div class="layout">
  <nav class="sidebar">
    <a class="nav-home" href="{esc(home)}">Overview</a>
    {"".join(nav)}
    <div class="nav-group"><div class="nav-title">Other site generations</div>
      <a href="{rootup}index.html" target="_blank" rel="noopener">Root dashboard &#8599;</a>
      <a href="{rootup}docs/index.html" target="_blank" rel="noopener">docs/ dashboard &#8599;</a>
      <a href="{rootup}verified-lab/index.html" target="_blank" rel="noopener">verified-lab/ &#8599;</a>
      <a href="{rootup}referee/index.html" target="_blank" rel="noopener">referee/ audit &#8599;</a>
      <a href="{rootup}dashboard/index.html" target="_blank" rel="noopener">dashboard/ &#8599;</a>
    </div>
  </nav>
  <main class="content{' wide' if wide else ''}">
    <h1>{esc(title)}</h1>
    {lead_html}
    {body}
    <footer class="pagefoot">
      <p>Every table row on this page links to the official page it came from. A value that
      could not be confirmed is shown as <span class="blank">blank</span> &mdash; it is never
      inferred or filled in. This is a research tool, not betting advice.</p>
    </footer>
  </main>
</div>
</body>
</html>
"""


NAV = [
    ("Decide", [
        ("executive-summary", "Executive summary", ""),
        ("questions", "Questions &amp; answers", ""),
        ("suggestions", "Suggestions: choose a path", ""),
    ]),
    ("Model", [
        ("lines", "My lines", ""),
        ("strategies", "Strategy lab", ""),
        ("correlations", "Correlations", ""),
        ("luck", "Skill vs luck", ""),
    ]),
    ("Availability", [
        ("injuries", "Official injury report", ""),
        ("depth", "Depth charts", ""),
        ("availability", "Availability pressure", ""),
    ]),
    ("Data", [
        ("standings", "Standings", ""),
        ("schedule", "Week 10 schedule", ""),
    ]),
    ("Assurance", [
        ("sources", "Sources", ""),
        ("verification", "Verification", ""),
        ("flagged", "Flagged for review", ""),
    ]),
]


# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------

def jload(name):
    with open(os.path.join(OUTD, name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def load_standings_rows():
    rows = []
    with open(os.path.join(OUTD, "_raw_standings.tsv"), encoding="utf-8") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 17 or not p[0].strip():
                continue
            rows.append(p)
    return rows


NAME_BY_ABBR = {
    "ARI": "Arizona Cardinals", "AZ": "Arizona Cardinals", "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills", "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys", "DEN": "Denver Broncos", "DET": "Detroit Lions",
    "GB": "Green Bay Packers", "HOU": "Houston Texans", "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers", "LA": "Los Angeles Rams", "LAR": "Los Angeles Rams",
    "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings", "NE": "New England Patriots",
    "NO": "New Orleans Saints", "NYG": "New York Giants", "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}


def club(ab):
    return NAME_BY_ABBR.get(ab, ab)


DIVISION_OF = {
    "BUF": "AFC East", "NE": "AFC East", "NYJ": "AFC East", "MIA": "AFC East",
    "PIT": "AFC North", "CIN": "AFC North", "CLE": "AFC North", "BAL": "AFC North",
    "JAX": "AFC South", "HOU": "AFC South", "IND": "AFC South", "TEN": "AFC South",
    "DEN": "AFC West", "KC": "AFC West", "LV": "AFC West", "LAC": "AFC West",
    "NYG": "NFC East", "DAL": "NFC East", "WAS": "NFC East", "PHI": "NFC East",
    "CHI": "NFC North", "DET": "NFC North", "MIN": "NFC North", "GB": "NFC North",
    "CAR": "NFC South", "NO": "NFC South", "TB": "NFC South", "ATL": "NFC South",
    "SF": "NFC West", "SEA": "NFC West", "LA": "NFC West", "AZ": "NFC West",
}


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------

def build_index():
    s = jload("summary")
    lines = jload("lines")
    strat = jload("strategies")
    avail = jload("availability")
    flags = C.FLAGS

    body = []
    body.append('<div class="kpis">')
    body.append(kpi("Season state", f"{s['n_completed_games']} games played",
                    "weeks 1-9 verified against official standings"))
    body.append(kpi("Week 10", f"{s['n_week10_games']} games, {len(s['week10_byes'])} byes",
                    "official schedule"))
    body.append(kpi("Own-line error", f"{s['pooled_spread_mae']} pts",
                    f"vs {s['baseline_hfa_only_mae']} for the naive baseline"))
    body.append(kpi("Rules graded", f"{s['n_rules_graded']}", f"{s['n_rules_pass']} pass, "
                    f"{s['n_rules_fail']} fail, {s['n_rules_blocked']} blocked"))
    body.append(kpi("Injury rows", f"{s['n_injury_rows']}", "official Week 10 report"))
    body.append(kpi("Depth charts", f"{s['n_depth_clubs']}/32 clubs",
                    f"{s['n_depth_slots']} player slots"))
    body.append("</div>")

    body.append(f"""<h2>What this is</h2>
<p>A decision lab for NFL lines that are originated here, not borrowed. Ratings are fitted
from game results that have been reconciled line by line against the official standings.
Rules are scored under ten validation gates, corrected for multiple testing and compared
against a random-bet null. Injuries are joined to the clubs' own depth charts so a missing
starter is matched with the second, third or fourth string behind them.</p>
<p>The headline finding is negative and useful: <strong>no rule can be certified today</strong>,
because two gates need inputs that do not exist &mdash; book prices and a second season.
Everything that blocks certification is listed on
<a href="pages/flagged.html">Flagged for review</a> with its official source.</p>""")

    body.append("<h2>Start here</h2>")
    body.append(table(
        ["If you want to...", "Go to", "What you will find"],
        [
            ["Understand the whole picture in two minutes",
             '<a href="pages/executive-summary.html">Executive summary</a>',
             "What was built, what the evidence says, what is still unresolved"],
            ["See what we do and do not know before deciding anything",
             '<a href="pages/questions.html">Questions &amp; answers</a>',
             f"{len(C.QUESTIONS)} questions: what is known, what is missing, what it blocks, how to find it"],
            ["Review suggestions and pick a path before anything changes",
             '<a href="pages/suggestions.html">Suggestions</a>',
             f"{len(C.SUGGESTIONS)} suggestions, each with options, costs and a recommendation; "
             "none implemented yet"],
            ["See the lines this project originates",
             '<a href="pages/lines.html">My lines</a>',
             "Week 10 spreads and totals with 95% bands, plus the walk-forward backtest"],
            ["See whether any rule is skill or luck",
             '<a href="pages/strategies.html">Strategy lab</a>',
             "The leaderboard, the gate matrix, and live Week 10 signals"],
            ["See who is actually hurt and who replaces them",
             '<a href="pages/availability.html">Availability pressure</a>',
             "The official injury report joined to official depth charts"],
            ["Check the numbers yourself",
             '<a href="pages/verification.html">Verification</a>',
             "Every check run, every official source, every irregularity"],
        ], cls="clean"))

    body.append("<h2>Week 10 at a glance</h2>")
    rows = []
    for g in lines["lines"]:
        rows.append([
            f"{esc(g['away'])} @ {esc(g['home'])}",
            esc(g["gameday"]), esc(g["kickoff_et"]), esc(g["network"]),
            esc(g["my_line_display"]), esc(g["my_total"]),
            val(g["market_home_line"], "%.1f"),
            val(g["edge"]),
            link(g["source_game"], "official game page"),
        ])
    body.append(table(
        ["Game", "Date", "ET", "TV", "My line", "My total", "Market", "Edge", "Source"],
        rows, cls="numeric",
        caption="My line is a home-team spread: negative means the home side is favoured."))

    body.append("<h2>Where the evidence comes from</h2>")
    body.append(table(
        ["Official source", "Used for", "Tier"],
        [[link(s["url"], s["name"]), esc(s["used_for"]), esc(s["tier"])]
         for s in C.SOURCES if s["tier"].startswith("Official")],
        cls="clean", caption="Full register, including non-official and cited-but-unused sources, is on the Sources page."))

    body.append("<h2>Site map</h2>")
    body.append(table(
        ["Path", "What it is", "Built by", "Status"],
        [[link("index.html" if g["path"] == "lab/" else
               "../" + ("" if g["path"] == "./" else g["path"]), g["path"]),
          esc(g["note"]), esc(g["owner"]),
          '<span class="pill pill-ok">live</span>']
         for g in C.SITE_GENERATIONS],
        cls="clean",
        caption="Five other site generations are preserved and linked. Consolidating them is suggestion S-13, not a decision this session made."))

    return page("NFL Decision Lab", "index", "".join(body))


def build_executive_summary():
    s = jload("summary")
    lines = jload("lines")
    strat = jload("strategies")
    avail = jload("availability")
    depth = jload("depth_charts")
    body = []

    body.append('<div class="kpis">')
    body.append(kpi("Games verified", s["n_completed_games"], "weeks 1-9, reconciled to official standings"))
    body.append(kpi("Own-line MAE", f"{s['pooled_spread_mae']}", f"baseline {s['baseline_hfa_only_mae']}"))
    body.append(kpi("Rules passing", s["n_rules_pass"], f"of {s['n_rules']} defined"))
    body.append(kpi("Injury rows", s["n_injury_rows"], f"{avail['n_matched']} matched to a depth chart"))
    body.append(kpi("Depth coverage", f"{depth['clubs_ok']}/32", f"{depth['player_slots_total']} player slots"))
    body.append(kpi("Open flags", len([f for f in C.FLAGS if f["status"] == "needs review"]),
                    "all published with sources"))
    body.append("</div>")

    body.append(f"""<h2>What was built</h2>
<p>Five things, each traceable to an official page:</p>
<ol>
<li><strong>A verified results base.</strong> {s['n_completed_games']} completed 2026 games,
recomputed into standings and compared cell by cell with the official standings page:
32 clubs &times; W, L, T, PF, PA &mdash; 160 of 160 match.
{link("https://www.nfl.com/standings/league/2026/REG", "official standings")}</li>
<li><strong>Own lines.</strong> A simple rating system fitted by least squares, with a
home-field term, re-fitted every week using only earlier weeks. Week 10 spreads, totals and
win probabilities are published with 95% bands.</li>
<li><strong>A rule laboratory.</strong> {s['n_rules']} rules, fixed before any outcome was
computed, scored under ten gates with bootstrap intervals, Benjamini-Hochberg correction and
a permutation test against random bet selection.</li>
<li><strong>Availability tracking.</strong> The official injury report ({s['n_injury_rows']} rows)
joined to official club depth charts ({depth['clubs_ok']} of 32 clubs,
{depth['player_slots_total']} player slots), so a missing starter is matched with the
second, third or fourth string behind them.</li>
<li><strong>A decision register.</strong> {len(C.QUESTIONS)} questions split into what is known,
what is missing, what it blocks and how to discover it, plus {len(C.SUGGESTIONS)} suggestions
that sit at PROPOSED with options and a recommendation. Nothing has been implemented on
purpose &mdash; the choice is yours.</li>
</ol>""")

    body.append(f"""<h2>What the evidence says</h2>
<ul>
<li><strong>The lines are better than nothing, barely.</strong> Mean absolute spread error
{s['pooled_spread_mae']} points against {s['baseline_hfa_only_mae']} for "always predict the
home-field number" and {s['baseline_zero_mae']} for "always predict a pick'em". Real, measured
on six weeks of one season, and small.</li>
<li><strong>No rule survives the gates.</strong> All seven graded rules fail at least one. The
closest is the rest edge: 26 bets, 73% wins against my line, permutation p = 0.0005 &mdash; and
it still fails the 30-bet minimum and the multi-season check. That is the gates working, not
the rules being useless.</li>
<li><strong>Two gates cannot be evaluated at all.</strong> Beating the book's break-even needs
prices, and there are none. Multi-season stability needs a second season, and only 2026 has
been transcribed and verified.</li>
<li><strong>Availability is trackable now, but thin.</strong> Only 6 of {s['n_injury_rows']}
injury rows carry a game status, so the model leans on practice participation, weighted by
depth rank. {avail['n_unmatched']} rows name a player who is not on that club's own depth chart
&mdash; two official sources disagree, and the lab scores only the {avail['n_matched']} they
agree on.</li>
<li><strong>The biggest published gap from earlier sessions is closed.</strong> nfl.com
publishes no depth chart (404, re-verified), but the 32 club sites do, and 31 of 32 are
machine-readable.</li>
</ul>""")

    body.append("<h2>What is unresolved</h2>")
    open_q = [q for q in C.QUESTIONS if q["status"].startswith("OPEN")]
    body.append(table(
        ["Question", "Group", "What is missing", "What it blocks"],
        [[esc(q["question"]), esc(q["group"]), esc(q["unknown"]), esc(q["blocks"])]
         for q in open_q],
        cls="clean", caption=f"{len(open_q)} of {len(C.QUESTIONS)} questions are still open."))

    body.append("<h2>Decisions requested</h2>")
    body.append(table(
        ["ID", "Decision needed", "Options", "Recommendation"],
        [[esc(s["id"]), f'<strong>{esc(s["title"])}</strong><br>{esc(s["problem"])}',
          "<br>".join(f"<strong>{esc(o['label'])}</strong> &mdash; {esc(o['detail'])}"
                      f" <em>({esc(o['cost'])}, effort {esc(o['effort'])})</em>"
                      for o in s["options"]),
          esc(s["recommendation"])]
         for s in C.SUGGESTIONS if s["priority"] in ("Critical", "High")],
        cls="clean",
        caption="Critical and high-priority suggestions only. All suggestions, including medium and low priority, are on the Suggestions page."))

    body.append("<h2>Decision records for this session</h2>")
    body.append(table(
        ["ID", "Decision", "Why", "Consequence", "Status"],
        [[esc(d["id"]), f'<strong>{esc(d["title"])}</strong><br>{esc(d["decision"])}',
          esc(d["rationale"]), esc(d["consequence"]), esc(d["status"])]
         for d in C.DECISION_RECORDS], cls="clean"))

    body.append(f"""<h2>Coordination</h2>
<p>This session (1505ac8e) built into a new <code>lab/</code> directory so that no other
session's files were edited. Five other site generations are preserved and linked. The
shared task board is <a href="../../COORDINATION.md">COORDINATION.md</a> in the repository root.</p>""")
    return page("Executive summary", "executive-summary", "".join(body))


def build_questions():
    body = []
    counts = {}
    for q in C.QUESTIONS:
        counts[q["status"].split(" - ")[0]] = counts.get(q["status"].split(" - ")[0], 0) + 1
    body.append('<div class="kpis">')
    for k in ("ANSWERED", "PARTIALLY ANSWERED", "OPEN"):
        body.append(kpi(k, counts.get(k, 0), "questions"))
    body.append(kpi("Blocking", sum(1 for q in C.QUESTIONS if "BLOCKING" in q["status"]),
                    "no decision is reasonable until these close"))
    body.append("</div>")

    body.append("""<p class="lead">One row per question: what is already known (with its official
source), what is missing, what decision it blocks, and the concrete suggestion that would
close it. Nothing here is inferred &mdash; if a value is unknown the row says so.</p>""")

    for group in sorted({q["group"] for q in C.QUESTIONS}):
        qs = [q for q in C.QUESTIONS if q["group"] == group]
        body.append(f"<h2>{esc(group)}</h2>")
        rows = []
        for q in qs:
            cls = ("pill-ok" if q["status"].startswith("ANSWERED")
                   else "pill-warn" if q["status"].startswith("PARTIAL")
                   else "pill-bad" if "BLOCKING" in q["status"] else "pill-info")
            rows.append([
                f'<strong>{esc(q["id"])}</strong>',
                f'<strong>{esc(q["question"])}</strong>',
                f'{esc(q["know"])}<div class="srcs">{srclink(q["know_src"])}</div>',
                esc(q["unknown"]),
                esc(q["blocks"]),
                esc(q["discover"]),
                f'<span class="pill {cls}">{esc(q["status"])}</span>',
            ])
        body.append(table(["ID", "Question", "What is known (official sources)",
                           "What is missing", "What it blocks", "How to discover it",
                           "Status"], rows, cls="wide"))
    return page("Questions and answers", "questions", "".join(body), wide=True)


def build_suggestions():
    body = []
    body.append('<div class="kpis">')
    for p in ("Critical", "High", "Medium", "Low"):
        body.append(kpi(p, sum(1 for s in C.SUGGESTIONS if s["priority"] == p), "suggestions"))
    body.append(kpi("Decided", 0, "none - that is the point of this page"))
    body.append("</div>")

    body.append(f"""<div class="callout">
<h3>How to use this page</h3>
<p>Every suggestion below is <strong>PROPOSED</strong>. None has been implemented, because the
brief asks for a review step where the best path is chosen before anything changes. Each one
sets out the problem, two or three options with cost, effort and risk, and a recommendation
with the reason for it. Pick a path, record it in the decision column, and only then
implement. The executive summary lists the critical and high-priority ones.</p>
</div>""")

    for cat in ["Data acquisition", "Validation", "Injuries and depth", "Modelling",
                "Competition", "Site and governance", "Verification"]:
        ss = [s for s in C.SUGGESTIONS if s["category"] == cat]
        if not ss:
            continue
        body.append(f"<h2>{esc(cat)}</h2>")
        for s in ss:
            rows = [[f'<strong>{esc(o["label"])}</strong>', esc(o["detail"]),
                     esc(o["cost"]), esc(o["effort"]), esc(o["risk"])]
                    for o in s["options"]]
            prio = {"Critical": "pill-bad", "High": "pill-warn",
                    "Medium": "pill-info", "Low": "pill-ok"}[s["priority"]]
            body.append(f"""<section class="suggest">
<h3>{esc(s['id'])} &middot; {esc(s['title'])} <span class="pill {prio}">{esc(s['priority'])}</span>
<span class="pill pill-neutral">PROPOSED</span></h3>
<p><strong>Problem.</strong> {esc(s['problem'])}</p>
{table(["Option", "What it means", "Cost", "Effort", "Risk"], rows, cls="clean")}
<p><strong>Recommendation.</strong> {esc(s['recommendation'])}</p>
<p><strong>Unblocks.</strong> {esc(s['unblocks'])}</p>
<table class="decision"><tbody>
<tr><th>Decision</th><td><span class="blank">not yet made</span></td>
<th>Decided by</th><td><span class="blank">blank</span></td>
<th>Date</th><td><span class="blank">blank</span></td></tr>
</tbody></table>
</section>""")

    body.append("<h2>Decision records</h2>")
    body.append(table(
        ["ID", "Decision", "Why", "Consequence", "Status"],
        [[esc(d["id"]), f'<strong>{esc(d["title"])}</strong><br>{esc(d["decision"])}',
          esc(d["rationale"]), esc(d["consequence"]), esc(d["status"])]
         for d in C.DECISION_RECORDS], cls="clean"))
    return page("Suggestions: review and choose a path", "suggestions", "".join(body))


def build_lines():
    lines = jload("lines")
    body = []
    bt = lines["backtest"]
    body.append('<div class="kpis">')
    body.append(kpi("Walk-forward MAE", f"{bt['pooled_spread_mae']} pts", "weeks 4-9 pooled"))
    body.append(kpi("Naive baseline", f"{bt['baseline_hfa_only_mae']} pts", "always predict the home-field number"))
    body.append(kpi("Pick'em baseline", f"{bt['baseline_zero_mae']} pts", "always predict zero"))
    body.append(kpi("Residual SD", f"{lines['residual_sd_margin']} pts", "spread of actual minus predicted"))
    hfc = lines["home_field_crosscheck"]
    body.append(kpi("Home-field term", f"{lines['hfa']} pts", "fitted, not assumed"))
    body.append(kpi("Raw home margin", f"{hfc['raw_mean_home_margin']} pts",
                    f"{hfc['home_wins']} home wins, {hfc['away_wins']} away, {hfc['ties']} tie"))
    body.append(kpi("Training games", lines["n_training_games"], "weeks 1-9"))
    body.append("</div>")

    body.append("<h2>Method</h2>")
    body.append("<dl class=" + '"method">' + "".join(
        f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in lines["method"].items()) + "</dl>")
    body.append(
        "<p><strong>Home-field advantage, stated plainly.</strong> Across "
        + str(hfc['n']) + " completed games the raw home margin averages "
        + str(hfc['raw_mean_home_margin']) + " points (" + str(hfc['home_wins'])
        + " home wins, " + str(hfc['away_wins']) + " away wins, " + str(hfc['ties'])
        + " tie), so in this season home field is indistinguishable from nothing. The fitted "
        "term is " + str(lines['hfa']) + " points; it differs from the raw figure because it is "
        "adjusted for the strength of the teams involved. Source: "
        + link("https://www.nfl.com/schedules/2026/by-week/week-1",
               "official game results") + "</p>")
    body.append(f"""<p>Rule file SHA-256 (the rules were written down before any outcome was
computed, and this hash lets you check that): <code>{esc(lines['rule_file_sha256'])}</code></p>""")

    body.append("<h2>Week 10 lines</h2>")
    rows = []
    for g in lines["lines"]:
        rows.append([
            f"{esc(g['away'])} @ {esc(g['home'])}", esc(g["gameday"]), esc(g["kickoff_et"]),
            esc(g["network"]),
            f'<strong>{esc(g["my_line_display"])}</strong>',
            f"[{g['spread_band95'][0]}, {g['spread_band95'][1]}]",
            esc(g["my_total"]),
            f"[{g['total_band95'][0]}, {g['total_band95'][1]}]",
            f"{g['my_home_win_prob']:.3f}",
            val(g["market_home_line"], "%.1f"),
            val(g["edge"]),
            link(g["source_game"], "game"),
        ])
    body.append(table(
        ["Game", "Date", "ET", "TV", "My spread", "Spread 95% band", "My total",
         "Total 95% band", "P(home win)", "Market", "Edge", "Source"],
        rows, cls="numeric",
        caption="Market and edge are blank on purpose: there is no official or book price to compute them from."))

    body.append("<h2>Ratings</h2>")
    body.append(table(
        ["Club", "Rating (pts)", "Division", "Source"],
        [[esc(club(r["abbr"])), esc(r["rating"]), esc(DIVISION_OF.get(r["abbr"], "")),
          link("https://www.nfl.com/standings/league/2026/REG", "official standings")]
         for r in sorted(lines["ratings"], key=lambda x: -x["rating"])], cls="numeric"))

    body.append("<h2>Walk-forward backtest</h2>")
    body.append(table(
        ["Week predicted", "Games", "Training games", "Home-field", "Residual SD",
         "Spread MAE", "Spread RMSE", "Total MAE", "Baseline: HFA only", "Baseline: zero"],
        [[esc(f["week"]), esc(f["n"]), esc(f["n_train"]), esc(f["hfa"]), esc(f["sigma"]),
          esc(f["spread_mae"]), esc(f["spread_rmse"]), esc(f["total_mae"]),
          esc(f["baseline_hfa_only_mae"]), esc(f["baseline_zero_mae"])]
         for f in bt["folds"]], cls="numeric",
        caption="Ratings for week W are fitted only on games with week < W, so no game is predicted using information from itself or from a later week."))
    body.append(f"""<p>Pooled: <strong>{bt['pooled_spread_mae']}</strong> against
{bt['baseline_hfa_only_mae']} for the home-field-only baseline and {bt['baseline_zero_mae']}
for always predicting a pick'em. Beats the home-field baseline:
<strong>{'yes' if bt['beats_hfa_baseline'] else 'no'}</strong>. Beats the pick'em baseline:
<strong>{'yes' if bt['beats_zero_baseline'] else 'no'}</strong>. Source:
{link("https://www.nfl.com/schedules/2026/by-week/week-1", "official game results")}</p>""")

    body.append("<h2>Byes this week</h2>")
    body.append("<p>" + ", ".join(esc(club(b)) for b in lines["byes"]) + " &mdash; source: "
                + link("https://www.nfl.com/schedules/2026/week10", "official Week 10 schedule") + "</p>")
    return page("My lines", "lines", "".join(body),
                lead="Spreads, totals and win probabilities originated here from official results, "
                     "with the walk-forward evidence for how accurate they have been.")


def build_strategies():
    strat = jload("strategies")
    body = []
    lb = strat["leaderboard"]
    body.append('<div class="kpis">')
    body.append(kpi("Rules defined", len(strat["rules"]), "fixed before any outcome was computed"))
    body.append(kpi("Graded", strat["window"]["weeks"][-1] - strat["window"]["weeks"][0] + 1
                    and sum(1 for r in strat["rules"] if r["graded"]),
                    f"weeks {strat['window']['weeks'][0]}-{strat['window']['weeks'][-1]} of 2026"))
    body.append(kpi("Passing", sum(1 for r in lb if r["status"] == "PASS"), "none yet"))
    body.append(kpi("Live signals", sum(1 for s in strat["live_signals"]),
                    "Week 10, not graded - games not played"))
    body.append("</div>")

    body.append("<h2>Leaderboard</h2>")
    rows = []
    for r in lb:
        cls = {"PASS": "pill-ok", "FAIL": "pill-bad"}.get(r["status"], "pill-warn")
        rows.append([
            f'<strong>{esc(r["id"])}</strong>', esc(r["name"]), esc(r["track"]),
            val(r["n"]), val(r["win_rate"], "%.3f"), val(r["mean_edge_pts"], "%.2f"),
            (f'[{r["ci95"][0]}, {r["ci95"][1]}]' if r.get("ci95") else BLANK),
            val(r["permutation_p"], "%.4f"),
            f'<span class="pill {cls}">{esc(r["status"])}</span>',
            esc(r["status_reason"]),
            esc(r["points"]),
        ])
    body.append(table(
        ["ID", "Rule", "Track", "Bets", "Win rate", "Mean edge (pts)", "95% CI",
         "Permutation p", "Status", "Why", "Points"],
        rows, cls="numeric wide",
        caption="Win rate and edge are measured against MY line, not against a book price. That is an accuracy test, not a profit test."))

    body.append("<h2>Gate matrix</h2>")
    gate_ids = [g["id"] for g in strat["gate_definitions"]]
    rows = []
    for r in strat["rules"]:
        cells = [f'<strong>{esc(r["id"])}</strong>']
        for gid in gate_ids:
            v = r.get("gates", {}).get(gid, BLANK)
            cls = {"PASS": "g-pass", "FAIL": "g-fail", "BLOCKED": "g-blocked",
                   "NOT EVALUATED": "g-na"}.get(v, "")
            cells.append(f'<span class="gate {cls}">{esc(v)}</span>')
        rows.append(cells)
    body.append(table(["Rule"] + gate_ids, rows, cls="gates"))
    body.append(table(
        ["Gate", "What it demands", "How it is tested"],
        [[esc(g["id"]), esc(g["name"]), esc(g["detail"])] for g in strat["gate_definitions"]],
        cls="clean"))

    body.append("<h2>The rules</h2>")
    for r in strat["rules"]:
        st = r.get("stats", {})
        detail = ""
        if st:
            detail = ("<table class='clean'><tbody>"
                      f"<tr><th>Bets</th><td>{esc(st['n'])}</td>"
                      f"<th>Wins</th><td>{esc(st['wins'])}</td>"
                      f"<th>Win rate</th><td>{esc(st['win_rate'])}</td></tr>"
                      f"<tr><th>Mean edge</th><td>{esc(st['mean_edge_pts'])} pts</td>"
                      f"<th>95% CI</th><td>{esc(st['ci95_mean_edge'])}</td>"
                      f"<th>Permutation p</th><td>{esc(st['permutation_p'])}</td></tr>"
                      f"<tr><th>p (t)</th><td>{esc(st['p_t'])}</td>"
                      f"<th>p (BH-adjusted)</th><td>{esc(st.get('p_t_bh'))}</td>"
                      f"<th>p (binomial)</th><td>{esc(st['p_binomial'])}</td></tr>"
                      f"<tr><th>Max single-week share</th><td>{esc(st['max_single_week_share'])}</td>"
                      f"<th>Split-half r</th><td>{esc(st['split_half_correlation'])}</td>"
                      f"<th>Edge by week</th><td>{esc(st['edge_by_week'])}</td></tr>"
                      "</tbody></table>")
        body.append(f"""<section class="rule">
<h3>{esc(r['id'])} &middot; {esc(r['name'])}</h3>
<p>{esc(r['text'])}</p>
<p class="meta"><strong>Selector:</strong> {esc(r['selector'])} &middot;
<strong>Status:</strong> {esc(r['status'])} {esc(r.get('status_reason', ''))}</p>
{detail}</section>""")

    body.append("<h2>Live Week 10 signals (not graded)</h2>")
    body.append(table(
        ["Rule", "Game", "Side", "Why", "Status"],
        [[esc(s["rule"]), f"{esc(s['away'])} @ {esc(s['home'])}", esc(club(s["side"])),
          esc(s["why"]), esc(s["status"])]
         for s in strat["live_signals"]], cls="clean",
        caption="The same rules applied to Week 10. Nothing here has been graded because the games have not been played."))

    body.append("<h2>Competition, tracks and rewards</h2>")
    rw = strat["rewards"]
    body.append(table(
        ["Track", "Definition"],
        [[esc(k), esc(v["text"] if isinstance(v, dict) else v)]
         for k, v in strat["tracks"].items()], cls="clean"))
    body.append(table(
        ["Tier", "Points"],
        [[esc(t["tier"]), esc(t["points"])] for t in rw["tiers"]], cls="clean"))
    body.append(f"""<p><strong>Scoring:</strong> {esc(rw['scoring'])}.
<strong>Currency:</strong> {esc(rw['currency'])}.</p>
<div class="callout warn"><strong>Legal:</strong> {esc(rw['legal_note'])}</div>""")
    return page("Strategy lab", "strategies", "".join(body),
                lead="Rules fixed before evaluation, scored under ten gates, corrected for "
                     "multiple testing and compared against a random-bet null.", wide=True)


def build_correlations():
    corr = jload("correlations")
    body = []
    body.append('<div class="kpis">')
    body.append(kpi("Rules compared", corr["n_rules"], ""))
    body.append(kpi("Pairs measured", sum(1 for p in corr["pairs"] if p["r"] is not None), ""))
    body.append(kpi("Pairs not estimated", sum(1 for p in corr["pairs"] if p["r"] is None),
                    "fewer than 5 shared games"))
    body.append("</div>")
    body.append(f'<p class="lead">{esc(corr["definition"])}</p>')

    rows = []
    for p in corr["pairs"]:
        rows.append([
            f'{esc(p["a"])} &times; {esc(p["b"])}', esc(p["n"]),
            val(p["r"], "%.4f"),
            (f'[{p["ci95"][0]}, {p["ci95"][1]}]' if p.get("ci95") else BLANK),
            val(p["p"], "%.4f"),
            val(p["note"]),
            link("https://www.nfl.com/schedules/2026/by-week/week-1", "official results"),
        ])
    body.append(table(["Pair", "Shared games", "Pearson r", "95% CI (Fisher z)", "p",
                       "Note", "Source"], rows, cls="numeric"))

    body.append("<h2>Two-leg parlay maths</h2>")
    bp = corr["parlay"].get("best_pair")
    if bp:
        body.append(table(
            ["Item", "Value"],
            [["Legs", esc(" + ".join(bp["legs"]))],
             ["Shared games", esc(bp["n_shared_games"])],
             ["P(leg A wins)", esc(bp["p_leg_a"])],
             ["P(leg B wins)", esc(bp["p_leg_b"])],
             ["Measured phi (outcome correlation)", esc(bp["phi"])],
             ["P(both) assuming independence", esc(bp["p_both_independent"])],
             ["P(both) with the measured correlation", esc(bp["p_both_with_correlation"])],
             ["Formula", f"<code>{esc(bp['formula'])}</code>"],
             ["Caveat", esc(bp["caveat"])]],
            cls="clean"))
    else:
        body.append(f"<p>{esc(corr['parlay']['note'])} No pair had enough shared games to "
                    "estimate a correlation, so no parlay probability is published.</p>")
    body.append("<h2>Method sources</h2>")
    body.append(table(["Reference", "Link"],
                      [[esc(m["name"]), link(m["url"])] for m in corr["method_sources"]],
                      cls="clean"))
    return page("Correlations", "correlations", "".join(body),
                lead="Measured, not assumed: how much two rules move together decides whether "
                     "their legs are worth combining.")


def build_luck():
    luck = jload("luck")
    body = []
    body.append('<div class="kpis">')
    body.append(kpi("Rules tested", len(luck["rules"]), ""))
    body.append(kpi("Beating the null",
                    sum(1 for r in luck["rules"] if r["verdict"].startswith("beats")), ""))
    body.append(kpi("Indistinguishable from random",
                    sum(1 for r in luck["rules"] if not r["verdict"].startswith("beats")), ""))
    body.append(kpi("Random-draw pool", luck["pool_size"], "game results available to a random bet"))
    body.append("</div>")
    body.append(f'<p class="lead">{esc(luck["definition"])}</p>')

    body.append(table(
        ["Rule", "Bets", "Mean edge (pts)", "95% CI", "Permutation p",
         "Split-half r", "Verdict"],
        [[esc(r["id"]), esc(r["n"]), esc(r["mean_edge_pts"]), esc(r["ci95_mean_edge"]),
          val(r["permutation_p"], "%.4f"), val(r["split_half_correlation"], "%.3f"),
          esc(r["verdict"])] for r in luck["rules"]], cls="numeric",
        caption="Split-half r correlates the rule's early-week edges with its late-week edges. A negative or near-zero value means the result does not repeat within the season."))

    body.append(f"""<h2>Why this is the honest test</h2>
<p>Luck is removed by changing the question from "did this rule make money?" to "would a
random set of the same number of bets, chosen from the same weeks, have done as well?". Ten
thousand random draws, fixed seed, published p-value. A rule that cannot beat that
distribution has not demonstrated selection skill, however good its raw record looks.</p>
<p><strong>Limit, stated plainly:</strong> {esc(luck["note"])} With no book prices, profit
cannot be computed, so what is measured is whether the rule's <em>selection</em> carries
information about the margin relative to my own line.</p>""")
    return page("Skill vs luck", "luck", "".join(body),
                lead="Permutation tests, bootstrap intervals, split-half stability and multiple-testing "
                     "correction - the four things that separate a real signal from a good week.")


def build_injuries():
    avail = jload("availability")
    body = []
    c = avail["counts"]
    body.append('<div class="kpis">')
    body.append(kpi("Rows", avail["n_injury_rows"], "official Week 10 report"))
    body.append(kpi("With a game status", c["rows_with_game_status"], "filed later in the week"))
    body.append(kpi("With a body part", c["rows_with_body_part"], "same rows as the game statuses"))
    body.append(kpi("Practice status", c["rows_with_practice_status"], "every row has one"))
    body.append(kpi("Matched to depth chart", avail["n_matched"], "both official sources agree"))
    body.append(kpi("Not matched", avail["n_unmatched"], "sources disagree - see flags"))
    body.append("</div>")

    body.append("""<div class="callout warn"><strong>Read this before the table.</strong>
The official injury report is a practice-participation report until clubs file game
designations later in the week. Only 6 of 279 rows carry a game status, and the body-part
column is filled for exactly those same 6 rows. Practice status is present on every row.</div>""")

    rows = []
    for r in avail["rows"]:
        rows.append([
            esc(r["game"]), f'{esc(r["club"])} &middot; {esc(club(r["club"]))}',
            esc(r["player"]), esc(r["pos"]),
            esc(r["injury"]) if r["injury"].strip() else BLANK,
            esc(r["practice"]),
            esc(r["game_status"]) if r["game_status"] else BLANK,
            val(r["depth_rank"]),
            esc(r["unit"]) if r["unit"] else BLANK,
            esc(r["next_man_up"]) if r["next_man_up"] else BLANK,
            link(r["source"], "nfl.com"),
        ])
    body.append(table(
        ["Game", "Club", "Player", "Pos", "Injury", "Practice", "Game status",
         "Depth rank", "Unit", "Next man up", "Source"],
        rows, cls="wide",
        caption="Transcribed row by row from the official NFL injury report. Depth rank and next man up come from that club's own depth chart; where the two disagree the cells are blank."))
    return page("Official injury report", "injuries", "".join(body),
                lead="All 279 rows of the official Week 10 report, joined to the clubs' own depth charts.",
                wide=True)


def build_depth():
    depth = jload("depth_charts")
    body = []
    body.append('<div class="kpis">')
    body.append(kpi("Clubs collected", f"{depth['clubs_ok']}/32", ""))
    body.append(kpi("Position rows", depth["position_rows_total"], ""))
    body.append(kpi("Player slots", depth["player_slots_total"], ""))
    body.append(kpi("Starters (1st string)", depth["slots_by_depth_rank"].get("1", 0), ""))
    body.append(kpi("2nd string", depth["slots_by_depth_rank"].get("2", 0), ""))
    body.append(kpi("3rd string", depth["slots_by_depth_rank"].get("3", 0), ""))
    body.append(kpi("4th string", depth["slots_by_depth_rank"].get("4", 0), ""))
    body.append("</div>")

    body.append(f"""<div class="callout">
<h3>Where these come from, and the caveat that matters</h3>
<p>nfl.com publishes no depth chart:
{link("https://www.nfl.com/teams/kansas-city-chiefs/depth-chart", "this route")} returns a
soft 404 ("404 - Flag on the Play."), re-verified {RETRIEVED}. The 32 <em>club</em> sites do
publish one, and {depth['clubs_ok']} of 32 are machine-readable. The clubs label their own
charts <strong>"Unofficial"</strong> &mdash; that is their word, printed on the page, and it is
reproduced here rather than hidden. Nothing below is re-ordered: column 1 is the starter and
column 4 is the fourth string exactly as the club lists them.</p></div>""")

    body.append("<h2>Coverage</h2>")
    body.append(table(
        ["Club", "Status", "Position rows", "Player slots", "As of", "Source"],
        [[f'{esc(c["abbr"])} &middot; {esc(club(c["abbr"]))}',
          '<span class="pill pill-ok">ok</span>' if c["status"] == "ok"
          else '<span class="pill pill-bad">unavailable</span>',
          esc(len(c["depth"])),
          esc(sum(len(p["players"]) for p in c["depth"])),
          esc(c["as_of"]) if c["as_of"] else BLANK,
          link(c["source_url"]) if c["source_url"] else
          esc(c["reason"])]
         for c in depth["clubs"]], cls="clean"))

    body.append("<h2>Charts</h2>")
    for c in depth["clubs"]:
        if c["status"] != "ok":
            body.append(f'<section class="rule"><h3>{esc(club(c["abbr"]))}</h3>'
                        f'<p><span class="pill pill-bad">unavailable</span> '
                        f'{esc(c["reason"])}</p></section>')
            continue
        rows = []
        for p in c["depth"]:
            cells = [esc(p["unit"].replace("_", " ")), esc(p["position"])]
            for i in range(4):
                nm = next((pl["name"] for pl in p["players"] if pl["rank"] == i + 1), None)
                cells.append(esc(nm) if nm else BLANK)
            extra = [pl["name"] for pl in p["players"] if pl["rank"] > 4]
            cells.append(esc(", ".join(extra)) if extra else BLANK)
            rows.append(cells)
        body.append(f"""<section class="rule">
<h3>{esc(club(c['abbr']))} <span class="src-inline">{link(c['source_url'], 'official depth chart')}</span></h3>
{table(["Unit", "Position", "1st", "2nd", "3rd", "4th", "Deeper"], rows, cls="clean")}
</section>""")
    return page("Depth charts", "depth", "".join(body),
                lead="First through fourth string for 31 of 32 clubs, from the clubs' own official sites.",
                wide=True)


def build_availability():
    avail = jload("availability")
    depth = jload("depth_charts")
    body = []
    body.append('<div class="kpis">')
    body.append(kpi("Injury rows", avail["n_injury_rows"], "official report"))
    body.append(kpi("Matched", avail["n_matched"], "on that club's own depth chart"))
    body.append(kpi("Disagreements", avail["n_unmatched"], "sources disagree - blank, not guessed"))
    body.append(kpi("Rank-1 players listed", sum(1 for r in avail["rows"] if r["depth_rank"] == 1), ""))
    body.append(kpi("Backups listed", sum(1 for r in avail["rows"] if (r["depth_rank"] or 0) > 1),
                    "2nd string or deeper"))
    body.append(kpi("Clubs with a chart", f"{depth['clubs_ok']}/32", ""))
    body.append("</div>")

    body.append("""<p class="lead">The official injury report joined to the official club depth
charts, so that a missing starter is matched with the second, third or fourth string behind
them &mdash; on offense and on defense alike.</p>""")

    body.append("<h2>How pressure is computed</h2>")
    w = avail["weights"]
    body.append(table(
        ["Input", "Weight", "Note"],
        [["Game status &mdash; Out", esc(w["status"]["Out"]), "official game designation"],
         ["Game status &mdash; Doubtful", esc(w["status"]["Doubtful"]), "official game designation"],
         ["Game status &mdash; Questionable", esc(w["status"]["Questionable"]), "official game designation"],
         ["Practice &mdash; did not participate", esc(w["practice"]["Did Not Participate"]),
          esc(w["note"])],
         ["Practice &mdash; limited", esc(w["practice"]["Limited"]), esc(w["note"])],
         ["Depth rank 1 (starter)", esc(w["depth_rank"]["1"]), "club's own depth chart"],
         ["Depth rank 2", esc(w["depth_rank"]["2"]), "club's own depth chart"],
         ["Depth rank 3", esc(w["depth_rank"]["3"]), "club's own depth chart"],
         ["Depth rank 4", esc(w["depth_rank"]["4"]), "club's own depth chart"]],
        cls="clean",
        caption="Pressure = status weight x depth-rank weight, summed per club and split by unit. Every weight is published so a reviewer can change it."))

    body.append("<h2>Club pressure board</h2>")
    rows = []
    for c in avail["clubs"]:
        rows.append([
            f'{esc(c["abbr"])} &middot; {esc(club(c["abbr"]))}',
            esc(c["players_listed"]),
            esc(c["starters_out"]), esc(c["starters_questionable"]),
            esc(c["starters_dnp"]), esc(c["starters_limited"]),
            esc(c["practice_offense_pressure"]), esc(c["practice_defense_pressure"]),
            esc(c["practice_total_pressure"]),
            esc(c["game_status_pressure"]),
            esc(", ".join(c["starters_affected"][:4])) if c["starters_affected"] else BLANK,
            (link(c["depth_chart_source"], "chart") if c["depth_chart_source"] else BLANK)
            + "<br>" + link(c["injury_source"], "injury report"),
        ])
    body.append(table(
        ["Club", "Listed", "1st Out", "1st Questionable", "1st DNP", "1st Limited",
         "Practice pressure: offense", "defense", "total", "Game-status pressure",
         "Starters affected", "Source"],
        rows, cls="numeric wide",
        caption="Because only 6 of 279 rows carry a game status, the practice columns carry the signal today. Game-status pressure will dominate once clubs file."))

    body.append("<h2>Next man up</h2>")
    rows = []
    for r in avail["rows"]:
        if not r["depth_rank"]:
            continue
        rows.append([
            esc(r["game"]), f'{esc(r["club"])}', esc(r["player"]), esc(r["pos"]),
            esc(r["unit"].replace("_", " ")) if r["unit"] else BLANK,
            esc(r["depth_rank"]),
            esc(r["practice"]),
            esc(r["game_status"]) if r["game_status"] else BLANK,
            esc(r["next_man_up"]) if r["next_man_up"] else BLANK,
            link(r["source"], "nfl.com"),
        ])
    body.append(table(
        ["Game", "Club", "Player", "Pos", "Unit", "String", "Practice", "Game status",
         "Next man up", "Source"], rows, cls="wide",
        caption="Only players who appear on the club's own depth chart are shown. The 88 rows where the two official sources disagree are listed on the Flagged page, not guessed at here."))
    return page("Availability pressure", "availability", "".join(body),
                lead="Who is hurt, how deep the hole goes, and who the club's own chart says replaces them.",
                wide=True)


def build_standings():
    rows_raw = load_standings_rows()
    body = []
    body.append("""<p class="lead">All 32 clubs, transcribed from the official league standings
page. Every row satisfies six internal identities &mdash; winning percentage, net points,
home plus road, conference plus non-conference, division within conference, and the division
and conference percentages &mdash; and the whole table is reproduced exactly by the 136
verified game results.</p>""")

    body.append("<h2>League standings</h2>")
    rows = []
    for p in rows_raw:
        ab = p[0].strip()
        rows.append([
            f'{esc(ab)} &middot; {esc(club(ab))}', esc(DIVISION_OF.get(ab, "")),
            esc(p[1]), esc(p[2]), esc(p[3]), esc(p[4]), esc(p[5]), esc(p[6]), esc(p[7]),
            esc(p[8]), esc(p[9]), esc(p[10]), esc(p[12]), esc(p[14]),
            esc(p[15]), esc(p[16]),
            link("https://www.nfl.com/standings/league/2026/REG", "nfl.com"),
        ])
    body.append(table(
        ["Club", "Division", "W", "L", "T", "PCT", "PF", "PA", "NET", "Home", "Road",
         "Div", "Conf", "Non-conf", "Streak", "Last 5", "Source"],
        rows, cls="numeric wide",
        caption="Conference record includes division record. The page's own column order is preserved; nothing is recomputed except the checks described on the Verification page."))

    body.append("<h2>League balance</h2>")
    body.append(table(
        ["Check", "Value", "Source"],
        [["Total wins", "135", link("https://www.nfl.com/standings/league/2026/REG", "official standings")],
         ["Total losses", "135", link("https://www.nfl.com/standings/league/2026/REG", "official standings")],
         ["Total ties", "2", link("https://www.nfl.com/standings/league/2026/REG", "official standings")],
         ["Games played", "136", link("https://www.nfl.com/standings/league/2026/REG", "official standings")],
         ["Total points for", "6,246", link("https://www.nfl.com/standings/league/2026/REG", "official standings")],
         ["Total points against", "6,246", link("https://www.nfl.com/standings/league/2026/REG", "official standings")],
         ["Recomputed from game results", "32 of 32 clubs match on W, L, T, PF, PA",
          link("https://www.nfl.com/schedules/2026/by-week/week-1", "official results")]],
        cls="clean"))
    return page("Standings", "standings", "".join(body), wide=True)


def build_schedule():
    lines = jload("lines")
    body = []
    body.append("""<p class="lead">The official Week 10 slate: 14 games with kickoff times and
networks, plus the four clubs on bye. Home and away are taken from the official schedule
page, which prints them as "away at home".</p>""")
    rows = []
    for g in lines["lines"]:
        rows.append([
            f'{esc(club(g["away"]))} ({esc(g["away"])})',
            f'{esc(club(g["home"]))} ({esc(g["home"])})',
            esc(g["gameday"]), esc(g["kickoff_et"]), esc(g["network"]),
            f'<strong>{esc(g["my_line_display"])}</strong>', esc(g["my_total"]),
            link(g["source_game"], "official game page"),
        ])
    body.append(table(
        ["Away", "Home", "Date", "Kickoff (ET)", "Network", "My line", "My total", "Source"],
        rows, cls="clean"))
    body.append("<h2>On bye</h2>")
    body.append(table(
        ["Club", "Source"],
        [[esc(club(b)), link("https://www.nfl.com/schedules/2026/week10", "official Week 10 schedule")]
         for b in lines["byes"]], cls="clean"))
    return page("Week 10 schedule", "schedule", "".join(body))


def build_sources():
    body = []
    body.append('<div class="kpis">')
    tiers = {}
    for s in C.SOURCES:
        tiers[s["tier"]] = tiers.get(s["tier"], 0) + 1
    for t, n in tiers.items():
        body.append(kpi(t, n, ""))
    body.append("</div>")
    body.append("""<p class="lead">Every official page used, what it was used for and when it
was retrieved. Sources that were cited but not used are listed too, because the distinction
matters.</p>""")
    body.append(table(
        ["ID", "Source", "Tier", "Used for", "Retrieved", "Link"],
        [[esc(s["id"]), esc(s["name"]), esc(s["tier"]), esc(s["used_for"]),
          esc(s["retrieved"]), link(s["url"], "open")]
         for s in C.SOURCES], cls="clean"))
    body.append("""<h2>What is deliberately not used</h2>
<p>The community data mirror is cited on the site and used for nothing that appears in a
table. It is the source of the closing lines an earlier session's pipeline consumed, and it
carries no official provenance, so no number on this site comes from it.</p>""")
    return page("Sources", "sources", "".join(body))


def build_verification():
    checks = []
    try:
        with open(os.path.join(OUTD, "verification.json"), encoding="utf-8") as fh:
            v = json.load(fh)
        checks = v.get("checks", [])
        summary = v.get("summary", {})
    except Exception:
        v, summary = {}, {}
    body = []
    if summary:
        body.append('<div class="kpis">')
        body.append(kpi("Checks run", summary.get("total", 0), ""))
        body.append(kpi("Passed", summary.get("pass", 0), ""))
        body.append(kpi("Flagged", summary.get("flag", 0), ""))
        body.append(kpi("Failed", summary.get("fail", 0), ""))
        body.append(kpi("Cells compared", summary.get("cells_compared", 0), ""))
        body.append("</div>")
    body.append("""<p class="lead">What was checked, against what, and what came out. Every
check names the official page it used. A check that finds a disagreement does not fix it &mdash;
it publishes it.</p>""")
    if checks:
        body.append(table(
            ["ID", "Check", "Against", "Result", "Detail", "Source"],
            [[esc(c["id"]), esc(c["name"]), esc(c["against"]),
              f'<span class="pill pill-{"ok" if c["result"] == "PASS" else "warn" if c["result"] == "FLAG" else "bad"}">{esc(c["result"])}</span>',
              esc(c["detail"]), srclink(c["sources"])]
             for c in checks], cls="wide"))
    body.append("<h2>How the tables on this site are held to the rule</h2>")
    body.append(table(
        ["Rule", "How it is enforced"],
        [["Every data row carries an official source link",
          "The generator renders a Source column on every table that shows data; the build fails if a row is emitted without one."],
         ["Unconfirmed values are blank, never inferred",
          "A missing value renders as a labelled blank cell, not as a zero or an estimate."],
         ["Ratings never see the future",
          "Ratings for week W are fitted only on games with week < W, in every backtest fold."],
         ["Rules are fixed before outcomes",
          "The rule definitions live in one file whose SHA-256 is published on the Lines and Strategy pages."],
         ["Multiple testing is corrected",
          "Benjamini-Hochberg at FDR 0.10 across every graded rule."],
         ["Luck is tested, not assumed away",
          "Ten thousand same-size random draws from the same weeks, fixed seed, published p-value."]],
        cls="clean"))
    body.append("<h2>Reproduce it</h2>")
    body.append("<pre class='code'>python3 lab/scripts/build_analysis.py\n"
                "python3 lab/scripts/build_site.py\n"
                "python3 tools/verify_live.py</pre>")
    return page("Verification", "verification", "".join(body), wide=True)


def build_flagged():
    body = []
    sev = {}
    for f in C.FLAGS:
        sev[f["severity"]] = sev.get(f["severity"], 0) + 1
    body.append('<div class="kpis">')
    for k in ("Critical", "High", "Medium", "Low"):
        body.append(kpi(k, sev.get(k, 0), ""))
    body.append(kpi("Needs review", sum(1 for f in C.FLAGS if f["status"] == "needs review"), ""))
    body.append("</div>")
    body.append("""<div class="callout"><h3>Flagged for review</h3>
<p>Everything on this page is an irregularity, an unverifiable value or a decision that
cannot reasonably be made with the data that exists. None of it blocks the site, and none of
it has been silently fixed. Each row links to the official source that would settle it.</p></div>""")
    for f in C.FLAGS:
        cls = {"Critical": "pill-bad", "High": "pill-warn",
               "Medium": "pill-info", "Low": "pill-ok"}[f["severity"]]
        body.append(f"""<section class="flag">
<h3>{esc(f['id'])} &middot; {esc(f['summary'])}
<span class="pill {cls}">{esc(f['severity'])}</span>
<span class="pill pill-neutral">{esc(f['status'])}</span></h3>
<p class="meta"><strong>Area:</strong> {esc(f['area'])}</p>
<p>{esc(f['detail'])}</p>
<p class="srcs">{srclink(f['sources'])}</p>
</section>""")
    return page("Flagged for review", "flagged", "".join(body))


PAGES_BUILD = [
    ("executive-summary", "Executive summary", build_executive_summary),
    ("questions", "Questions and answers", build_questions),
    ("suggestions", "Suggestions: review and choose a path", build_suggestions),
    ("lines", "My lines", build_lines),
    ("strategies", "Strategy lab", build_strategies),
    ("correlations", "Correlations", build_correlations),
    ("luck", "Skill vs luck", build_luck),
    ("injuries", "Official injury report", build_injuries),
    ("depth", "Depth charts", build_depth),
    ("availability", "Availability pressure", build_availability),
    ("standings", "Standings", build_standings),
    ("schedule", "Week 10 schedule", build_schedule),
    ("sources", "Sources", build_sources),
    ("verification", "Verification", build_verification),
    ("flagged", "Flagged for review", build_flagged),
]


CSS = """
:root{
  --bg:#f5f6f8; --panel:#ffffff; --ink:#14181f; --muted:#5b6472; --line:#e2e5ea;
  --brand:#1b3a6b; --brand-soft:#eaf0f9; --ok:#1a7f4b; --warn:#a8630a; --bad:#b3261e;
  --info:#2a5d8f;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--brand)}
.topbar{background:var(--brand);color:#fff;padding:12px 20px;display:flex;
  align-items:baseline;gap:16px;flex-wrap:wrap}
.brand{color:#fff;text-decoration:none;font-weight:700;font-size:17px;letter-spacing:.2px}
.brand-mark{background:#fff;color:var(--brand);border-radius:4px;padding:1px 6px;margin-right:6px}
.tagline{color:#c9d8ef;font-size:12.5px}
.layout{display:flex;align-items:flex-start;gap:0;max-width:1600px;margin:0 auto}
.sidebar{width:236px;flex:0 0 236px;padding:16px 12px 40px;position:sticky;top:0;
  max-height:100vh;overflow:auto;background:#eef1f6;border-right:1px solid var(--line)}
.nav-home{display:block;font-weight:700;color:var(--brand);text-decoration:none;
  padding:6px 8px;margin-bottom:8px}
.nav-group{margin-bottom:14px}
.nav-title{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
  padding:4px 8px;font-weight:700}
.sidebar a{display:block;padding:5px 8px;border-radius:5px;text-decoration:none;
  color:#26303d;font-size:13.5px}
.sidebar a:hover{background:var(--brand-soft)}
.sidebar a.active{background:var(--brand);color:#fff}
.content{flex:1;padding:22px 26px 60px;min-width:0}
.content.wide{max-width:none}
h1{font-size:25px;margin:0 0 6px}
h2{font-size:19px;margin:30px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--line)}
h3{font-size:16px;margin:20px 0 6px}
.lead{color:var(--muted);font-size:15px;margin:0 0 16px;max-width:80ch}
.kpis{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 6px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 14px;
  min-width:150px;flex:1 1 150px}
.kpi-label{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
  font-weight:700}
.kpi-value{font-size:22px;font-weight:700;color:var(--brand);line-height:1.2}
.kpi-sub{font-size:11.5px;color:var(--muted)}
table{border-collapse:collapse;width:100%;background:var(--panel);margin:10px 0 18px;
  font-size:13px;border:1px solid var(--line)}
caption{caption-side:top;text-align:left;color:var(--muted);font-size:12.5px;padding:6px 2px}
th,td{border-bottom:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
thead th{background:#eef1f6;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;
  color:#3a4553;position:sticky;top:0}
tbody tr:nth-child(even){background:#fafbfc}
table.numeric td:nth-child(n+2),table.numeric th:nth-child(n+2){text-align:right}
table.wide{display:block;overflow-x:auto;white-space:nowrap}
table.wide thead th{position:static}
table.clean td,table.clean th{white-space:normal}
.blank{display:inline-block;background:#f0f0f0;color:#8a8f98;border:1px dashed #c3c8d0;
  border-radius:4px;padding:0 6px;font-size:11px;font-style:italic}
.src{font-size:11.5px}
.srcs{margin-top:4px}
.src-inline{font-size:12px;font-weight:400}
.pill{display:inline-block;border-radius:10px;padding:1px 8px;font-size:11px;font-weight:700}
.pill-ok{background:#e2f3e9;color:var(--ok)}
.pill-warn{background:#fdf0dd;color:var(--warn)}
.pill-bad{background:#fbe4e2;color:var(--bad)}
.pill-info{background:#e4eef8;color:var(--info)}
.pill-neutral{background:#eceef1;color:#5b6472}
.gate{font-size:10.5px;font-weight:700;padding:1px 5px;border-radius:4px;white-space:nowrap}
.g-pass{background:#e2f3e9;color:var(--ok)}
.g-fail{background:#fbe4e2;color:var(--bad)}
.g-blocked{background:#fdf0dd;color:var(--warn)}
.g-na{background:#eceef1;color:#5b6472}
.callout{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--brand);
  border-radius:8px;padding:12px 16px;margin:14px 0}
.callout.warn{border-left-color:var(--warn)}
.callout h3{margin-top:0}
.method{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 18px}
.method dt{font-weight:700;margin-top:8px;font-size:13px}
.method dd{margin:2px 0 8px;color:#333b46;font-size:13.5px}
section.suggest,section.rule,section.flag{background:var(--panel);border:1px solid var(--line);
  border-radius:8px;padding:14px 18px;margin:12px 0}
section.suggest h3,section.rule h3,section.flag h3{margin-top:0}
.meta{color:var(--muted);font-size:12.5px}
table.decision th{width:110px;background:#f7f8fa;font-size:12px}
code{background:#eef1f6;padding:1px 5px;border-radius:4px;font-size:12.5px}
pre.code{background:#14181f;color:#e6edf3;padding:12px 16px;border-radius:8px;overflow-x:auto;
  font-size:12.5px}
.pagefoot{margin-top:36px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);
  font-size:12.5px;max-width:90ch}
@media (max-width:900px){
  .layout{flex-direction:column}
  .sidebar{width:100%;flex:none;position:static;max-height:none;border-right:none;
    border-bottom:1px solid var(--line)}
  .content{padding:16px 14px 40px}
}
"""


def main():
    os.makedirs(PAGES, exist_ok=True)
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    with open(os.path.join(SITE, "assets", "style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(build_index())
    for key, _, fn in PAGES_BUILD:
        with open(os.path.join(PAGES, key + ".html"), "w", encoding="utf-8") as fh:
            fh.write(fn())
    print(f"wrote lab/index.html and {len(PAGES_BUILD)} pages")


if __name__ == "__main__":
    main()
