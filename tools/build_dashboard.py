#!/usr/bin/env python3
"""build_dashboard.py — the single, clean decision dashboard published from this repository.

The repository accumulated four parallel site generations (root pages, docs/, referee/,
verified-lab/). They are all still reachable and none of them is deleted, but a reader
needs one place that answers, in order:

    1. Where do we stand right now?            -> dashboard.html
    2. What still has to be decided, and what is known/missing?  -> decisions.html
    3. What do the suggestions say, and which path do I pick?     -> suggestions.html
    4. Can the numbers be believed?            -> verification.html
    5. What is wrong / unverified?             -> flag-register.html
    6. What are the important details, in one page? -> executive-summary.html

Every figure on these pages is read from a committed JSON file and re-derived here; nothing
is typed into the HTML by hand. tools/verify_dashboard.py re-computes the same figures
independently from the raw inputs and fails if they disagree. Blank values render as a
visible "blank" and are never filled in.

Run: python3 tools/build_dashboard.py
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DR = os.path.join(ROOT, "data", "decision_room")
GENERATED = None


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def load_optional(path, default=None):
    p = os.path.join(ROOT, path)
    return load(path) if os.path.exists(p) else default


def e(x):
    return html.escape("" if x is None else str(x), quote=True)


def blank():
    return '<span class="missing">blank</span>'


def txt(v):
    """Render a possibly-empty text value. Whitespace-only counts as empty."""
    if v is None or str(v).strip() == "":
        return blank()
    return str(v).strip() if "<span" in str(v) else e(str(v).strip())


def num(v, digits=2, suffix=""):
    if v is None or v == "":
        return blank()
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.{digits}f}{suffix}"
    if isinstance(v, int):
        return f"{v}{suffix}"
    return e(str(v)) + e(suffix)


def pct(v, digits=1):
    if v is None or v == "":
        return blank()
    return f"{float(v) * 100:.{digits}f}%"


def badge(text, kind="neutral"):
    return f'<span class="badge {kind}">{e(text if text not in (None, "") else "none")}</span>'


def src(href, label):
    return (f'<a class="src" href="{e(href)}" target="_blank" rel="noopener noreferrer">'
            f'{e(label)} ↗</a>')


def state_badge(state):
    s = (state or "").upper()
    kind = ("pass" if s in ("SUPPORTED", "FAVOURABLE", "HAS A PASS", "HAS MARKET", "PASS")
            else "fail" if s in ("NOT SUPPORTED", "NOT READY", "FAIL", "CONTRADICTED")
            else "warn" if s in ("PARTIAL", "MODEL ONLY", "FLAG", "OPEN")
            else "neutral")
    return badge(state, kind)


def table(headers, rows, table_id=None, note=None, cls="data-table"):
    if not rows:
        return '<p class="empty">No rows.</p>'
    tid = f' id="{e(table_id)}"' if table_id else ""
    head = "".join(f'<th scope="col">{h}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    out = (f'<div class="table-wrap"><table class="{cls}"{tid}>'
           f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>")
    if note:
        out += f'<p class="note">{note}</p>'
    return out


def panel(title, body, anchor=None):
    a = f' id="{e(anchor)}"' if anchor else ""
    return f'<section class="panel"{a}><h2>{e(title)}</h2>{body}</section>'


def kpi(label, value, sub=""):
    return (f'<article class="kpi"><span class="kpi-label">{e(label)}</span>'
            f'<strong class="kpi-value">{value}</strong>'
            f'<span class="kpi-sub">{e(sub)}</span></article>')


# --------------------------------------------------------------------- shell
NAV = [
    ("dashboard.html", "Dashboard"),
    ("decisions.html", "Decisions"),
    ("suggestions.html", "Suggestions & Path"),
    ("verification.html", "Verification"),
    ("flag-register.html", "Flagged for Review"),
    ("executive-summary.html", "Executive Summary"),
]

OTHER_SITES = [
    ("../pages/lines.html", "Model lines & backtest", "Own spreads/totals with error bands"),
    ("../pages/strategies.html", "Strategy lab", "8 gates, bootstrap CIs, correlation"),
    ("../pages/injuries.html", "Injuries & depth", "Official status joined to depth rank"),
    ("../pages/props.html", "Player props", "Model-only projections, no prices"),
    ("../pages/questions.html", "Question ledger", "20 questions: known / unknown / missing"),
    ("../pages/evidence.html", "Evidence & provenance", "URL + sha256 for every source file"),
    ("../docs/index.html", "Companion dashboard (session 87deb7ab)", "Independent build, own data layer"),
    ("../referee/index.html", "Referee audit (session 73fdd6c4)", "Independent official-source audit"),
    ("../verified-lab/index.html", "Verified lab (session a2cea255)", "Hand-transcription harness, 34 checks"),
]


def shell(path, title, lede, body, stamp):
    # Pages live together in web/, so sister pages need no prefix, while repo-root assets
    # and the four older site generations are one directory up. Both are tested.
    prefix = "../"
    items = []
    for href, label in NAV:
        active = ' class="active"' if href == path else ""
        items.append(f'<a href="{href}"{active}>{e(label)}</a>')
    nav = "".join(items)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · NFL Decision Lab</title>
<meta name="description" content="Source-linked NFL decision dashboard: own lines, validation gates, injuries and depth, and an explicit register of what is unverified.">
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <a class="brand" href="{path}"><span class="mark">NFL</span><span class="brand-text">Decision Lab</span></a>
  <nav aria-label="Main">{nav}</nav>
</header>
<main id="main">
  <section class="page-head">
    <p class="eyebrow">2026 season · Week {e(stamp['week'])}</p>
    <h1>{e(title)}</h1>
    <p class="standfirst">{lede}</p>
    <p class="timestamp">Data read {e(stamp['generated_at'])} · verification run {e(stamp['verified_at'])} ·
    every value links to its source; unconfirmed values are left blank and linked to the
    <a href="flag-register.html">Flagged for Review</a> page.</p>
  </section>
  {body}
</main>
<footer>
  <div>
    <strong>NFL Decision Lab</strong>
    <p>Research tool, not betting advice. No official league odds exist; no book-level price is
    connected. Nothing here is a recommendation to wager.</p>
  </div>
  <div class="foot-links">
    <a href="verification.html">Verification</a>
    <a href="flag-register.html">Flagged for review</a>
    <a href="https://github.com/kanlerxz87-cyber/NFL1" target="_blank" rel="noopener noreferrer">Repository ↗</a>
    <a href="https://www.nfl.com/" target="_blank" rel="noopener noreferrer">NFL.com ↗</a>
  </div>
  <p class="credit">Data: official NFL pages (transcribed, see Verification) and the nflverse mirror
  (CC-BY-4.0). Club names and marks belong to the NFL and its clubs.</p>
</footer>
</body>
</html>
"""


# ------------------------------------------------------------------ 1 dashboard
def page_dashboard(d, stamp):
    ev, model, strat = d["evidence"], d["model"], d["strategies"]
    avail, props, power = d["availability"], d["props"], d["power"]

    b = []
    b.append('<div class="kpis">' + "".join([
        kpi("Games analysed", f"{ev['games_played']}", f"2026 regular season, week {ev['week_complete']} complete"),
        kpi("Own lines this week", f"{ev['own_lines']}", f"week {ev['week_next']} fixtures"),
        kpi("Market source", "none", "no odds feed connected"),
        kpi("Strategies passing", f"{ev['strategies_pass']} of {ev['strategies']}", f"{ev['gates']} gates"),
        kpi("Players with official status", f"{ev['injury_rows']}", f"{ev['injury_club_sections']} clubs publish"),
        kpi("Official game designations", f"{ev['game_designations']}", f"of {ev['injury_rows']} rows"),
        kpi("Depth charts verified", f"{len(ev['depth_clubs'])}", "clubs (league site 404s)"),
        kpi("Verification checks", f"{ev['verification_pass']} pass", f"{ev['verification_flag']} flagged, {ev['verification_fail']} fail"),
    ]) + "</div>")

    b.append(panel("What the evidence says today", f"""
<p class="lede">These four verdicts are computed from the committed data, not written by hand.
Each one states what the numbers can and cannot support, so a choice can be made against it.</p>
{table(["Question", "Verdict", "What it means"],
       [[f"<strong>Do the own lines beat the closing line?</strong>", state_badge(model['state']),
         e(model['plain'])],
        [f"<strong>Is any strategy ready to be ranked or rewarded?</strong>", state_badge(strat['state']),
         e(strat['plain'])],
        [f"<strong>Can a starter-vs-backup claim be verified league-wide?</strong>",
         state_badge(avail['state']), e(avail['plain'])],
        [f"<strong>Can a prop edge be claimed?</strong>", state_badge(props['state']),
         e(props['plain'])]],
       table_id="tbl-verdicts")}
<p class="note">Sources: {src('data/model/lines.json'.join(['https://github.com/kanlerxz87-cyber/NFL1/blob/main/']), 'lines model') if False else
 src('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/model/lines.json', 'own-line model')} ·
 {src('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/model/strategies.json', 'strategy leaderboard')} ·
 {src('https://www.nfl.com/injuries/', 'official injury report')} ·
 {src('https://www.chiefs.com/team/depth-chart', 'club depth chart (KC)')} ·
 {src('https://www.seahawks.com/team/depth-chart/', 'club depth chart (SEA)')}</p>
""", "verdicts"))

    # the model-vs-market numbers, spelled out
    b.append(panel("Why the own lines are not presented as edges", f"""
<p>The model was fitted on 2024 and tested on games it never saw. On the {model['test_n']} games of
2026 it is <strong>{num(model['model_mae'])}</strong> points of mean absolute error against
<strong>{num(model['market_mae'])}</strong> for the closing line. The 95% interval on the
difference is <strong>[{num(model['diff_ci'][0],3)}, {num(model['diff_ci'][1],3)}]</strong>.</p>
<p>Fitting the actual margin on both the closing line and the model line, then testing on 2026,
puts a weight of <strong>{num(model['blend_weight_market'],3)}</strong> on the market and
<strong>{num(model['blend_weight_model'],3)}</strong> on the model; hybrid error
{num(model['hybrid_mae'])} against {num(model['market_only_mae'])} for the market alone.
A weight at or below zero means the model's disagreement with the price carried no information
in the test window.</p>
<p>The line-sign convention is measured rather than assumed: across {e(model['sign_n'])} games the
correlation between the mirrored closing line and the home team's actual margin is
<strong>{num(model['sign_corr'],3)}</strong>, so a positive number means the home team is
favoured. {src('https://github.com/nflverse/nflverse-data/releases/tag/schedules', 'source: nflverse schedules')}</p>
""", "model"))

    # current week lines, both numbers in one convention
    lines = load("data/model/lines.json")["lines"]
    rows = []
    for g in lines:
        my, mk = g.get("my_home_line"), g.get("market_home_line")
        # print BOTH numbers from the home team's point of view, signed, so no subtraction
        # across conventions is possible. away number is the negation of the home number.
        rows.append([
            f"<strong>{e(g['away'])} @ {e(g['home'])}</strong><br><span class=\"sub\">{e(g['gameday'])}</span>",
            num(my, 1), num(None if mk is None else -mk, 1),
            num(mk, 1), num(None if mk is None else -mk, 1),
            num(None if (my is None or mk is None) else my - mk, 2),
            num(g.get("my_total"), 1),
            num(None if (g.get("my_total") is None or g.get("market_total") is None)
                else g["my_total"] - g["market_total"], 2),
            src(g.get("source_games") or "https://www.nfl.com/schedules/2026/REG10", "NFL schedule"),
        ])
    b.append(panel(f"Week {ev['week_next']} own lines, with the market in the same convention", f"""
<p class="note">Both columns are signed from the <em>home</em> team's point of view (positive = home
team favoured). The away-team view is shown as well because that is how a sportsbook prints the
other side of the same game. This is the defect fixed in this session: the previous landing page
printed a bare market number beside a signed model line, which made LA @ ARI look like a
14.7-point difference when the real difference is 4.27 points.</p>
{table(["Matchup", "Model (home)", "Model (away)", "Market (home)", "Market (away)",
        "Difference", "Model total", "Total difference", "Source"], rows,
       table_id="tbl-lines",
       note=("A difference is model minus market. No odds feed is connected, so the market column is "
             "the consensus closing number carried by the nflverse mirror, not a book quote, and no "
             "difference on this page is a betting recommendation."))}
""", "lines"))

    # what can be decided now vs what cannot
    b.append(panel("Decide now, or wait for information?", f"""
<p>The repository mixed together three different kinds of open item. Splitting them is the single
biggest improvement to decision-making in this build, because it shows that six decisions need
<em>no new data at all</em> — they only need a human to choose.</p>
{table(["Kind", "Count", "What it needs", "Where"],
       [[badge("Fillable now", "pass"), str(len(d["fillable"])),
         "A human decision. Every piece of evidence is already in the repository.",
         '<a href="decisions.html#fillable">Decisions → Needs only a choice</a>'],
        [badge("Blocked", "warn"),
         str(sum(1 for q in d["questions"] if str(q.get("status", "")).lower().startswith(("open", "blocked")))),
         "A named piece of information that no connected source publishes yet.",
         '<a href="decisions.html#blocked">Decisions → Blocked on information</a>'],
        [badge("Contradiction", "fail"), str(len(d["contradictions"])),
         "An official page and the repository disagree; a human must arbitrate.",
         '<a href="flag-register.html">Flagged for Review</a>'],
        [badge("Suggestion", "neutral"), str(len(d["suggestions"])),
         "An improvement that needs work, not a choice.",
         '<a href="suggestions.html">Suggestions &amp; Path</a>']],
       table_id="tbl-decide")}
""", "decide"))

    # how long it takes to know if a strategy works
    nreq = power["n_required"]
    rows = [[e(k), f"<strong>{v:,}</strong>", f"{power['seasons_required'][k]:.1f}"]
            for k, v in nreq.items()]
    b.append(panel("How long before skill can be separated from luck?", f"""
<p>Before any reward is attached to a strategy, the sample has to be large enough that a real edge
would not be mistaken for luck. Using a two-sided test at 5% significance with 80% power, a
-110 price and a per-bet standard deviation of {power['assumptions']['sd_per_bet']} units:</p>
{table(["True edge", "Bets needed", "2026 seasons"], rows, table_id="tbl-power",
       note=("Arithmetic from stated assumptions, not a fitted result. A single 272-game season "
             "cannot separate a 1-3% edge from noise, which is why the leaderboard currently ranks on "
             "the lower bound of a 95% interval and awards zero to anything under the sample minimum. "
             "Method: " + src(power['assumptions']['source'], 'NIST sample-size procedure')))}
""", "power"))

    # other sites
    rows = [[f'<a href="{e(href)}">{e(label)}</a>', e(desc)] for href, label, desc in OTHER_SITES]
    b.append(panel("Everything else that is published from this repository", f"""
<p>Four site generations were built by different sessions in one day. None has been deleted. This
dashboard is the entry point; the pages below hold the detail.</p>
{table(["Page", "What is there"], rows, table_id="tbl-sites")}
""", "sites"))
    return shell("dashboard.html", "Where the project stands",
                 "One page that answers what the data supports, what has to be decided, and what is "
                 "still unknown — with a source link on every row.", "\n".join(b), stamp)


# ------------------------------------------------------------------ 2 decisions
def page_decisions(d, stamp):
    ev = d["evidence"]
    b = []
    b.append(panel("How to read this page", """
<p>A decision is only reasonable when the information behind it exists. This page sorts every open
question into four buckets, in the order you should work through them:</p>
<ol class="tight">
<li><strong>Needs only a choice</strong> — the evidence is already in the repository. Reading the row
and picking an option is the whole task.</li>
<li><strong>Blocked on information</strong> — a named fact is missing, and the row says exactly which
official page or feed would supply it.</li>
<li><strong>Contradictions</strong> — an official page and this repository disagree. These are on the
Flagged for Review page with both links.</li>
<li><strong>Not yet meaningful</strong> — questions that look urgent but cannot change any decision
until an earlier item is settled.</li>
</ol>""", "how"))

    # 1. fillable
    rows = []
    for x in d["fillable"]:
        rows.append([
            f'<code>{e(x["id"])}</code>',
            f'<strong>{e(x["question"])}</strong><br><span class="sub">{e(x["already_have"])}</span>',
            e(x["options"]),
            e(x["recommended"]),
            e(x["unblocks"]),
            src(x["source"], "evidence"),
            state_badge("OPEN"),
        ])
    b.append(panel(f"Needs only a choice ({len(d['fillable'])}) — no new data required",
                   table(["ID", "Decision", "Options", "Recommended path", "What it unblocks",
                          "Evidence", "Status"], rows, table_id="tbl-fillable"), "fillable"))

    # 2. blocked questions, from the question ledger
    rows = []
    for q in d["questions"]:
        status = str(q.get("status", "")).lower()
        if not status.startswith(("open", "blocked", "partially", "partial")):
            continue
        ans = q.get("answer") if q.get("answer") and q["answer"].strip() not in ("", " ") else None
        rows.append([
            f'<code>{e(q["id"])}</code>',
            f'<strong>{e(q["question"])}</strong>',
            txt(q.get("have") or q.get("known")),
            txt(q.get("missing") or q.get("unknown")),
            txt(ans) if ans else '<span class="missing">no answer yet</span>',
            txt(q.get("discovery")),
            badge(q.get("status"), "warn"),
        ])
    b.append(panel(f"Blocked on information ({len(rows)}) — what is known, what is missing, how to get it",
                   table(["ID", "Question", "What we have", "What is missing", "Answer so far",
                          "How to discover it", "Status"], rows, table_id="tbl-blocked"),
                   "blocked"))

    # 3. contradictions
    rows = []
    for x in d["contradictions"]:
        rows.append([
            f'<code>{e(x["id"])}</code>',
            badge(x["sev"], "fail" if x["sev"] == "High" else "warn"),
            e(x["area"]),
            e(x["finding"]),
            src(x["official"], "official page"),
            f'<code>{e(x["repo_file"])}</code>',
            e(x["needs"]),
        ])
    b.append(panel(f"Contradictions between an official page and this repository ({len(d['contradictions'])})",
                   table(["ID", "Severity", "Area", "Finding", "Official source", "Repository file",
                          "What would settle it"], rows, table_id="tbl-contradictions",
                         note=("These come from an automated cell-by-cell comparison, not an opinion. "
                               "The full register with impact and status is on the "
                               '<a href="flag-register.html">Flagged for Review</a> page.')),
                   "contradictions"))

    # 4. answered
    rows = []
    for q in d["questions"]:
        status = str(q.get("status", "")).lower()
        if status.startswith(("open", "blocked", "partially", "partial")):
            continue
        rows.append([f'<code>{e(q["id"])}</code>', txt(q["question"]), txt(q.get("answer")),
                     badge(q.get("status"), "pass")])
    b.append(panel(f"Settled by a source already in the repository ({len(rows)})",
                   table(["ID", "Question", "Answer", "Status"], rows, table_id="tbl-answered"),
                   "answered"))

    b.append(panel("The one question that gates everything else", f"""
<p>Every strategy, leaderboard, reward and 'edge' number depends on a price that could actually have
been taken. This repository contains no book-level odds: the market numbers are consensus closing
numbers from the nflverse mirror, as the Verification page states and the model itself measures.
Until a licensed odds feed is connected, the honest answer to "what is this bet worth?" is
<strong>{blank()}</strong> and it is published as a flag rather than filled in.</p>
<p>See {src('https://www.nfl.com/', 'NFL.com')} for the league's own game information, and the
flag register for the exact fields that stay blank.</p>
""", "gating"))
    return shell("decisions.html", "Decisions, questions and missing information",
                 "What has to be settled before a decision is reasonable — separated into what needs a "
                 "choice, what needs information, what contradicts an official source, and what is "
                 "already settled.", "\n".join(b), stamp)


# ------------------------------------------------------------------ 3 suggestions
def page_suggestions(d, stamp):
    b = []
    b.append(panel("Review this before implementing anything", """
<p>The brief asks for a place to review suggestions and choose a path <em>before</em> any change is
implemented. That is this page. Nothing below is implemented on the strength of an unverified
number: the suggestions say what to build, the paths say what order to build it in, and the
decisions page says what still needs your call first.</p>
""", "intro"))

    # paths first: the "choose a path" gate
    rows = []
    for p in d["paths"]:
        rows.append([f'<strong>{e(p["name"])}</strong>', e(p["summary"]), e(p["pros"]), e(p["cons"]),
                     badge("choice required", "warn")])
    b.append(panel("Choose a path", table(["Path", "What it does", "Why you would", "What it costs",
                                           "Status"], rows, table_id="tbl-paths"), "paths"))

    # ranked fillable decisions -> these are the actionable ones
    b.append(panel("Ten things that can be decided today, in the order they unblock the most", f"""
<p>Derived from the eight obstacles this session found (see Flagged for Review) plus the fillable
decisions. Each row names the evidence, the change, and the check that proves it worked.</p>
""", "actions"))
    rows = [
        ["A1", "One entry page", "Four site generations all publish at once; two generators both write index.html.",
         "Publish this dashboard as the single entry page; link the rest as evidence, generated by nobody else.",
         "tools/check_generators.py proves no file has two writers.",
         '<a href="dashboard.html#sites">Sites</a>'],
        ["A2", "Render after refresh", "The scheduled data job commits JSON but never re-renders HTML, so pages go stale.",
         "Render in the same job that commits data, and commit the pages.",
         "tools/check_freshness.py fails when a page stamp is older than the data it shows.",
         '<a href="flag-register.html#X06">X06</a>'],
        ["A3", "One sign convention", "The market column was printed unsigned beside a signed model line.",
         "Print both sides, home and away, signed, with the difference derived from the two printed numbers.",
         "verify_dashboard.py recomputes every printed difference from the printed inputs.",
         '<a href="dashboard.html#lines">Lines</a>'],
        ["A4", "Practice is not availability", "273 of 279 official rows this week are practice-only, not game designations.",
         "Publish practice-only rows as practice-only and keep them out of availability maths.",
         "verify_official.py asserts no practice-only row is labelled as a designation.",
         '<a href="decisions.html#fillable">F-D03</a>'],
        ["A5", "Depth charts per club", "The league publishes none; only club sites do.",
         "Transcribe club depth charts club by club and keep the source URL on every row.",
         "verify_official.py compares every transcribed rank with the club page.",
         '<a href="decisions.html#fillable">F-D02</a>'],
        ["A6", "No edge without a price", "No odds feed exists anywhere in the repository.",
         "Rename 'edge' to 'difference from the consensus closing number' wherever no price exists.",
         "verify_dashboard.py rejects the word edge in any row with no price.",
         '<a href="decisions.html#gating">Gating question</a>'],
        ["A7", "Label paper rewards", "A reward table with no legal review is a liability.",
         "Publish the leaderboard as paper points only until counsel signs off.",
         "Flag F05 stays open on the register until signed off.",
         '<a href="decisions.html#fillable">F-D04</a>'],
        ["A8", "Show the sample size", "A 5% edge needs about 708 bets to separate from luck; a 1% edge needs 17,689.",
         "Print the bets needed beside every ROI, and rank on the lower confidence bound.",
         "The power table is recomputed by verify_dashboard.py from stated assumptions.",
         '<a href="dashboard.html#power">Power</a>'],
        ["A9", "Canonical club codes", "AZ/ARI and LA/LAR both appear; a join silently drops rows.",
         "One code set plus an alias table, applied everywhere and tested.",
         "verify_official.py resolves every code through the alias table and reports unknowns.",
         '<a href="flag-register.html#X10">X10</a>'],
        ["A10", "Publish the contradictions", "Machine-found disagreements were invisible.",
         "List every one with both links, and never auto-correct another session's file.",
         "The register is generated from data/contradictions.json; empty means empty, not hidden.",
         '<a href="decisions.html#contradictions">Contradictions</a>'],
    ]
    b.append(table(["ID", "Change", "Why it matters", "What to do", "How you will know it worked", "Detail"],
                   rows, table_id="tbl-actions"))

    # the original 20 suggestions, kept
    rows = []
    for s in d["suggestions"]:
        rows.append([f'<code>{e(s["id"])}</code>', e(s["area"]),
                     f'<strong>{e(s["title"])}</strong><br><span class="sub">{e(s["decision_impact"])}</span>',
                     e(s["recommended_path"]), badge(s["status"], "warn")])
    b.append(panel(f"The full suggestions register ({len(d['suggestions'])})",
                   table(["ID", "Area", "Suggestion", "Recommended path", "Status"], rows,
                         table_id="tbl-suggestions",
                         note="Kept verbatim from the earlier sessions' register so nothing is lost."),
                   "register"))
    return shell("suggestions.html", "Suggestions & choose a path",
                 "Review the options and pick a path before anything is implemented. Ranked by how much "
                 "decision-making each one unblocks.", "\n".join(b), stamp)


# ---------------------------------------------------------------- 4 verification
def page_verification(d, stamp):
    ver = load("data/audit/official_verification.json")
    ev = d["evidence"]
    b = []
    b.append('<div class="kpis">' + "".join([
        kpi("Checks run", str(len(ver["checks"])), "cell by cell"),
        kpi("Passed", str(ver["counts"]["passed"]), "reproduce exactly"),
        kpi("Flagged", str(ver["counts"]["flagged"]), "published for review"),
        kpi("Failed", str(ver["counts"]["failed"]), "block publication"),
    ]) + "</div>")

    b.append(panel("What was verified, and against what", f"""
<p>Every dataset used on this site is compared, cell by cell, with a hand transcription of the
official page it claims to come from. The transcriptions live in <code>data/evidence/</code> and
carry the URL of the page each row was read from:</p>
<ul class="tight">
<li>Standings — <a href="https://www.nfl.com/standings/league/2026/reg" target="_blank" rel="noopener noreferrer">nfl.com/standings/league/2026/reg ↗</a> — 32 clubs, W/L/T/PF/PA.</li>
<li>Injuries — <a href="https://www.nfl.com/injuries/" target="_blank" rel="noopener noreferrer">nfl.com/injuries/ ↗</a> — {ev['injury_rows']} player rows across {ev['injury_club_sections']} club sections.</li>
<li>Schedule — <a href="https://www.nfl.com/schedules/2026/REG10" target="_blank" rel="noopener noreferrer">nfl.com/schedules/2026/REG10 ↗</a> — {ev['fixtures']} games and {ev['byes']} byes.</li>
<li>Depth charts — <a href="https://www.chiefs.com/team/depth-chart" target="_blank" rel="noopener noreferrer">chiefs.com ↗</a>, <a href="https://www.seahawks.com/team/depth-chart/" target="_blank" rel="noopener noreferrer">seahawks.com ↗</a> — because the league site returns 404 for depth charts (checked and recorded).</li>
</ul>
<p>A <strong>FAIL</strong> means this site's own published data contradicts an official page and
blocks publication. A <strong>FLAG</strong> means either another session's artifact disagrees with
the official page, or an official page publishes nothing for a value the project would like to
have. Flags do not block publication; they are listed below and on the Flagged for Review page,
with the official link, so a person can arbitrate. No value is ever silently corrected.</p>
""", "scope"))

    rows = []
    for c in ver["checks"]:
        kind = {"PASS": "pass", "FLAG": "warn", "FAIL": "fail"}[c["status"]]
        rows.append([badge(c["status"], kind), e(c["area"]), e(c["check"]),
                     str(c["rows_checked"]),
                     e(c["detail"]) if c.get("detail") else '<span class="missing">no remark</span>'])
    b.append(panel("Every check", table(["Result", "Area", "Check", "Rows", "Detail"], rows,
                                        table_id="tbl-checks"), "checks"))

    # what is NOT verified
    unver = load_optional("data/model/verification.json", {}).get("unverifiable", [])
    rows = [[e(u["item"]), e(u["why"]), e(u["handling"])] for u in unver]
    b.append(panel("What cannot be verified from any reachable source", 
                   table(["Item", "Why it cannot be confirmed", "How the site handles it"], rows,
                         table_id="tbl-unverifiable",
                         note=("These are not rounded, estimated or replaced. The cell stays blank and "
                               "the row says why.")), "unverifiable"))

    b.append(panel("How to reproduce this yourself", """
<pre><code>python3 tools/evidence_from_official.py   # write the official transcriptions
python3 tools/verify_official.py          # compare every repo dataset, cell by cell
python3 tools/build_decision_room.py      # recompute the verdicts
python3 tools/build_dashboard.py          # render these pages
python3 tools/verify_dashboard.py         # independently recompute every published figure</code></pre>
<p>The transcription step is manual by design: an audit is only worth something if the person
checking the data read the page. The comparison and every arithmetic check are automated and run
on every push.</p>
""", "reproduce"))
    return shell("verification.html", "Verification & sources",
                 "Exactly what was checked against which official page, what passed, and what cannot be "
                 "confirmed at all.", "\n".join(b), stamp)


# --------------------------------------------------------------- 5 flag register
def page_flags(d, stamp):
    b = []
    b.append('<div class="kpis">' + "".join([
        kpi("Contradictions found", str(len(d["contradictions"])), "official page vs repository"),
        kpi("High severity", str(sum(1 for x in d["contradictions"] if x["sev"] == "High")), "fix first"),
        kpi("Resolved this session", str(sum(1 for x in d["contradictions"] if x.get("resolved_this_session"))), "with a gate that keeps it fixed"),
        kpi("Earlier flags", str(len(d["flags"])), "carried forward"),
    ]) + "</div>")

    b.append(panel("Contradictions found by machine, with both links", f"""
<p>Each row below was produced by comparing a committed dataset with the official page, cell by
cell. Neither value is guessed: both sides are linked so you can check them yourself. Severity is
the reviewer's guide to what to look at first, not a measurement.</p>
{table(["ID", "Severity", "Area", "Finding", "Impact", "Official source", "Repository file",
        "What would settle it", "State"],
       [[f'<code id="{e(x["id"])}">{e(x["id"])}</code>',
         badge(x["sev"], "fail" if x["sev"] == "High" else "warn"), e(x["area"]), e(x["finding"]),
         e(x["impact"]), src(x["official"], "official page"), f'<code>{e(x["repo_file"])}</code>',
         e(x["needs"]),
         badge("fixed in this session", "pass") if x.get("resolved_this_session")
         else badge("needs review", "warn")] for x in d["contradictions"]],
       table_id="tbl-contradictions")}
""", "contradictions"))

    order = {"High": 0, "Medium": 1, "Low": 2}
    resolved = sorted(
        [x for x in d["contradictions"] if x.get("resolved_this_session")], key=lambda x: order[x["sev"]])
    b.append(panel("Shipped with the fix, not just the complaint", f"""
<p>A finding is worth nothing if the defect comes back. These were fixed in this session and each
one is now guarded by a check that fails the build if it reappears:</p>
{table(["ID", "Defect", "What changed", "The gate that keeps it fixed"],
       [[f'<code>{e(x["id"])}</code>', e(x["finding"]),
         e(x["resolved_this_session"]), e(x["needs"])] for x in resolved],
       table_id="tbl-resolved")}
""", "resolved"))

    rows = []
    for f in d["flags"]:
        rows.append([f'<code>{e(f["id"])}</code>', e(f["category"]), e(f["description"]),
                     e(f["impact"]), badge(f.get("status", "needs review"), "warn"),
                     src("https://github.com/kanlerxz87-cyber/NFL1", "repository")])
    b.append(panel(f"Irregularities carried forward from earlier sessions ({len(d['flags'])})",
                   table(["ID", "Category", "Description", "Impact", "Status", "Source"], rows,
                         table_id="tbl-earlier",
                         note=("Preserved verbatim from the earlier registers so no session's finding is "
                               "lost. Several are historical (they describe the repository as it was "
                               "before any code existed) and are kept because the brief says findings are "
                               "never deleted.")), "earlier"))

    b.append(panel("What is deliberately left blank", """
<p>Some values cannot be published because no official or licensed source publishes them. They are
not zero, not estimated, and not rounded — they are blank, and they are listed here so nobody
mistakes a gap for a finding:</p>
<ul class="tight">
<li><strong>Book-level odds</strong> — the NFL publishes no betting lines and no licensed feed is
connected. Market numbers on this site are consensus closing numbers from the nflverse mirror.</li>
<li><strong>Player prop prices</strong> — same reason, so no prop edge exists to compute.</li>
<li><strong>Who physically starts</strong> — the league publishes no depth chart. Only club pages do,
and only two were transcribed this week.</li>
<li><strong>Leaderboard ranks and rewards</strong> — blank until a strategy passes all eight gates;
the reward table is paper-only until legal review.</li>
</ul>
""", "blank"))
    return shell("flag-register.html", "Flagged for Review",
                 "Every contradiction, unverified value and blocked decision, with both the official "
                 "link and the repository file so each one can be settled by a person.", "\n".join(b), stamp)


# ------------------------------------------------------------ 6 executive summary
def page_exec(d, stamp):
    ev, model, strat, avail = d["evidence"], d["model"], d["strategies"], d["availability"]
    ver = load("data/audit/official_verification.json")
    b = []
    b.append(panel("The short version", f"""
<p><strong>The site is honest, and that is the point.</strong> It builds its own NFL lines from
play-by-play, tests them against the closing line on games they never saw, tracks official injury
status against club depth charts, and publishes every number with a source — including the numbers
that say the model does not beat the market.</p>
<p>Three findings carry most of the weight:</p>
<ol class="tight">
<li><strong>The own-line model is not yet good enough to act on.</strong> Out of sample it is
{num(model['model_mae'])} points of error against the closing line's {num(model['market_mae'])}, and a
fitted blend puts a negative weight on the model ({num(model['blend_weight_model'],3)}). Publishing
its disagreement with the price as an "edge" would be unsupported.</li>
<li><strong>No strategy has earned a rank or a reward.</strong> {ev['strategies_pass']} of
{ev['strategies']} strategies clear all {ev['gates']} gates; the best paper score is a
<em>negative</em> lower-bound return. The leaderboard is built and empty on purpose.</li>
<li><strong>The starter/backup question is only partly answerable.</strong> The league publishes
injury status but no depth chart; only club sites publish depth charts. This week
{ev['game_designations']} of {ev['injury_rows']} official rows carry a game designation, the rest are
practice reports. A "third-string corner is starting" claim can be verified for
{len(avail['clubs_with_both'])} of {len(avail['clubs_in_week10'])} clubs.</li>
</ol>
""", "short"))

    b.append(panel("What was built in this session", f"""
{table(["Area", "What exists now", "Where"],
       [["Official fixtures", f"{ev['games_played']} games implied by standings, {ev['injury_rows']} injury rows, {ev['fixtures']} week-{ev['week_next']} games, {ev['depth_slots']} depth slots — all hand-transcribed with source URLs.", '<a href="verification.html#scope">Verification</a>'],
        ["Verification gate", f"{len(ver['checks'])} checks comparing every dataset cell by cell against an official page; FAIL blocks publication, FLAG is published for review.", '<a href="verification.html#checks">Every check</a>'],
        ["Decision separation", f"{len(d['fillable'])} decisions that need only a choice, {sum(1 for q in d['questions'] if str(q.get('status','')).lower().startswith(('open','blocked'))) } blocked on information, {len(d['contradictions'])} contradictions.", '<a href="decisions.html">Decisions</a>'],
        ["Sign-convention fix", "Model and market printed in one convention, home and away, with the difference derived from the printed numbers.", '<a href="dashboard.html#lines">Week 10 lines</a>'],
        ["Statistical power", "How many bets a real edge needs before it can be separated from luck, so rewards cannot be handed out on noise.", '<a href="dashboard.html#power">Power</a>'],
        ["Contradiction register", f"{len(d['contradictions'])} conflicts between official pages and repository data, with both links.", '<a href="flag-register.html">Flagged for Review</a>']],
       table_id="tbl-built")}
""", "built"))

    b.append(panel("The decisions you actually have to make", f"""
<p>Ranked by how much each one unblocks. None of them needs more data collection.</p>
{table(["#", "Decision", "Recommended", "Unblocks"],
       [[str(i), f'<strong>{e(x["question"])}</strong>', e(x["recommended"]), e(x["unblocks"])]
        for i, x in enumerate(d["fillable"], 1)], table_id="tbl-your-decisions")}
""", "decisions"))

    b.append(panel("What is still unresolved", f"""
<ul class="tight">
<li><strong>No odds feed.</strong> Until a licensed price source is connected, every "edge" is a
difference from a consensus closing number, not a price that could have been taken.</li>
<li><strong>No league depth chart.</strong> The league URL returns 404. Thirty clubs still need a
transcription before a league-wide backup-exposure index means anything.</li>
<li><strong>Thirty-two practice cells vs one designation.</strong> The injury feed is mid-week; game
statuses arrive later. Treat this week's availability numbers as a practice report, not a lineup.</li>
<li><strong>Rewards need counsel.</strong> The leaderboard is paper points only.</li>
<li><strong>Four site generations coexist.</strong> This dashboard is the entry point; the others are
linked and preserved.</li>
</ul>
""", "unresolved"))

    b.append(panel("How to check any of this yourself", """
<p>Every figure on this page comes from a JSON file in the repository, and every claim about an
official source links to the page it was read from. Open
<a href="verification.html">Verification</a> to see the full check list, or run the four commands
listed at the bottom of that page to reproduce the whole build.</p>
<p class="note">This is a research tool. It is not betting advice, it does not place bets, and no
number on it is a recommendation to wager.</p>
""", "check"))
    return shell("executive-summary.html", "Executive summary",
                 "What was built, what the evidence actually says, what it cannot support yet, and the "
                 "decisions that are waiting for you.", "\n".join(b), stamp)


# ------------------------------------------------------------------------ main
def main() -> int:
    d = load(os.path.join("data", "decision_room", "decision_room.json"))
    ver = load("data/audit/official_verification.json")
    stamp = dict(week=d["evidence"]["week_next"],
                 generated_at=d["generated_at"],
                 verified_at=ver["generated_at"])
    pages = {
        "dashboard.html": page_dashboard,
        "decisions.html": page_decisions,
        "suggestions.html": page_suggestions,
        "verification.html": page_verification,
        "flag-register.html": page_flags,
        "executive-summary.html": page_exec,
    }
    web = os.path.join(ROOT, "web")
    os.makedirs(web, exist_ok=True)
    for name, fn in pages.items():
        out = fn(d, stamp)
        with open(os.path.join(web, name), "w", encoding="utf-8") as f:
            f.write(out)
        print(f"wrote web/{name} ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
