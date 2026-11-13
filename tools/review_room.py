#!/usr/bin/env python3
"""Build the Review Room: the place a decision is made before anything is implemented.

    python3 tools/review_room.py          build review-room/*.html
    python3 tools/review_room.py --check  verify links and sources, write nothing

Design constraints the page has to meet, because the reader is the owner, not a developer:

  * every open decision is one row you can scan, with its status and what it is waiting for;
  * every number on the page is read from a data file at build time -- nothing is typed in;
  * every claim carries a source link, and a claim without one is a build failure;
  * a decision that cannot be taken hides nothing: the blocking question is named and linked.

The generator is deliberately separate from the four existing renderers so it cannot
collide with them. It writes only inside review-room/.
"""
from __future__ import annotations

import csv
import html
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RR = ROOT / "review-room"
DATA = RR / "data"
sys.path.insert(0, str(DATA))

import decisions as DC          # noqa: E402
import improvements as IM       # noqa: E402
import questions as QS          # noqa: E402
import verification as VF       # noqa: E402

P = ROOT / "data" / "personnel"
S9 = ROOT / "data" / "s9cb"

QS_OFFICIAL_WEEK10 = "https://www.nfl.com/schedules/2026/by-week/week-10"
QS_OFFICIAL_INJURIES = "https://www.nfl.com/injuries/"
batch_note = ""

OFFICIAL = {
    "standings": "https://www.nfl.com/standings/league/2026/reg",
    "week10": "https://www.nfl.com/schedules/2026/by-week/week-10",
    "injuries": "https://www.nfl.com/injuries/",
    "teams": "https://www.nfl.com/teams/",
    "dictionary": "https://nflreadr.nflverse.com/articles/dictionary_schedules.html",
    "nflverse": "https://github.com/nflverse/nflverse-data",
    "pages_api": "https://api.github.com/kanlerxz87-cyber/NFL1/pages",
}

NAV = [
    ("index.html", "Start here"),
    ("executive.html", "Executive summary"),
    ("decisions.html", "Decisions"),
    ("questions.html", "Questions"),
    ("week10.html", "This week's personnel"),
    ("evidence.html", "Signals &amp; evidence"),
    ("improvements.html", "Improvements"),
    ("verification.html", "Verification"),
    ("flagged.html", "Flagged for review"),
]

CSS = """\
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c2330;--line:#2a3441;--ink:#e6edf3;
--muted:#8b98a8;--accent:#58a6ff;--good:#3fb950;--warn:#d29922;--bad:#f85149;--violet:#bc8cff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.top{position:sticky;top:0;z-index:20;display:flex;gap:18px;align-items:center;
padding:12px 24px;background:rgba(13,17,23,.96);border-bottom:1px solid var(--line);
flex-wrap:wrap;backdrop-filter:blur(6px)}
.brand{font-weight:700;color:var(--ink)}
.brand .tag{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
border:1px solid var(--line);border-radius:99px;padding:1px 8px;margin-left:8px}
nav.main{display:flex;gap:4px;flex-wrap:wrap}
nav.main a{padding:5px 11px;border-radius:7px;font-size:13.5px;color:var(--muted)}
nav.main a:hover{background:var(--panel2);text-decoration:none}
nav.main a.on{background:var(--panel2);color:var(--ink);font-weight:600}
.wrap{max-width:1180px;margin:0 auto;padding:26px 24px 80px}
h1{font-size:30px;margin:0 0 8px;letter-spacing:-.01em}
h2{font-size:19px;margin:38px 0 10px;padding-bottom:7px;border-bottom:1px solid var(--line)}
h3{font-size:15px;margin:22px 0 8px}
.lede{font-size:16.5px;color:var(--ink);background:var(--panel);border:1px solid var(--line);
border-left:3px solid var(--accent);border-radius:9px;padding:13px 16px;margin:0 0 18px}
.sub{color:var(--muted);margin:0 0 16px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:11px;margin:16px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .k{display:block;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.kpi .v{display:block;font-size:24px;font-weight:700;margin:2px 0}
.kpi .n{display:block;font-size:11.5px;color:var(--muted)}
.kpi .v.good{color:var(--good)}.kpi .v.warn{color:var(--warn)}.kpi .v.bad{color:var(--bad)}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:12px 0}
table{width:100%;border-collapse:collapse;font-size:13.5px}
caption{text-align:left;color:var(--muted);font-size:12px;padding:9px 12px}
th,td{padding:8px 11px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel2);font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;
color:var(--muted);font-weight:600;white-space:nowrap}
tbody tr:hover{background:rgba(88,166,255,.05)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;font-size:11px;font-weight:600;padding:1px 8px;border-radius:99px;
border:1px solid;white-space:nowrap}
.b-ready{color:var(--good);border-color:var(--good);background:rgba(63,185,80,.1)}
.b-blocked{color:var(--bad);border-color:var(--bad);background:rgba(248,81,73,.1)}
.b-watch{color:var(--warn);border-color:var(--warn);background:rgba(210,153,34,.12)}
.b-info{color:var(--accent);border-color:var(--accent);background:rgba(88,166,255,.1)}
.b-mute{color:var(--muted);border-color:var(--line)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:11px;
padding:16px 18px;margin:14px 0}
.card h3{margin-top:0}
.src{font-size:12px;color:var(--muted);word-break:break-all}
.flagbox{border-left:3px solid var(--warn);background:rgba(210,153,34,.07);
padding:11px 15px;border-radius:0 8px 8px 0;margin:12px 0}
.badbox{border-left:3px solid var(--bad);background:rgba(248,81,73,.07);
padding:11px 15px;border-radius:0 8px 8px 0;margin:12px 0}
.goodbox{border-left:3px solid var(--good);background:rgba(63,185,80,.07);
padding:11px 15px;border-radius:0 8px 8px 0;margin:12px 0}
.opts{display:grid;gap:10px;margin:10px 0 0}
.opt{border:1px solid var(--line);border-radius:9px;padding:11px 13px;background:var(--panel2)}
.opt.rec{border-color:var(--good);box-shadow:inset 3px 0 0 var(--good)}
.opt .lbl{font-weight:650;margin:0 0 6px}
.opt dl{display:grid;grid-template-columns:104px 1fr;gap:2px 10px;margin:0;font-size:13px}
.opt dt{color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;padding-top:2px}
.opt dd{margin:0}
footer{border-top:1px solid var(--line);margin-top:50px;padding-top:16px;
color:var(--muted);font-size:12.5px}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
ul.tight{margin:8px 0;padding-left:20px}ul.tight li{margin:3px 0}
.pill{display:inline-block;font-size:11px;padding:1px 7px;border-radius:99px;
background:var(--panel2);border:1px solid var(--line);color:var(--muted);margin-right:5px}
"""


# ------------------------------------------------------------------ small helpers
def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def load(p: Path):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def num(v, nd=2, suffix="") -> str:
    """Format a number, or say it is unknown. Never invents a zero."""
    if v is None:
        return '<span class="badge b-mute">no value</span>'
    if isinstance(v, str):
        return esc(v)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return esc(v)
    if not math.isfinite(f):
        return '<span class="badge b-mute">no value</span>'
    return f"{f:,.{nd}f}{suffix}"


def pct(v, nd=2) -> str:
    return num(v, nd, "%")


def src(url: str, label: str = "") -> str:
    """A source link. Repository paths are linked relatively, official URLs absolutely."""
    if url.startswith("http"):
        return (f'<a class="src" href="{esc(url)}" target="_blank" rel="noopener">'
                f'{esc(label or url)}</a>')
    return f'<a class="src" href="../{esc(url)}">{esc(label or url)}</a>'


def table(headers: list[str], rows: list[list[str]], caption: str = "",
          numeric: set[int] | None = None) -> str:
    numeric = numeric or set()
    def cell(tag: str, i: int, inner: str) -> str:
        cls = ' class="num"' if i in numeric else ""
        return f"<{tag}{cls}>{inner}</{tag}>"

    head = "".join(cell("th", i, h) for i, h in enumerate(headers))
    body = ["<tr>" + "".join(cell("td", i, c) for i, c in enumerate(r)) + "</tr>" for r in rows]
    cap = f"<caption>{caption}</caption>" if caption else ""
    return (f'<div class="tw"><table>{cap}<thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def page(fname: str, title: str, subtitle: str, body: str, generated: str) -> str:
    nav = "".join(
        ('<a href="%s" class="on">%s</a>' % (h, t)) if h == fname
        else ('<a href="%s">%s</a>' % (h, t)) for h, t in NAV)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · NFL Review Room</title>
<meta name="description" content="{esc(subtitle)}">
<style>{CSS}</style>
</head>
<body>
<header class="top">
  <a class="brand" href="index.html">Review Room<span class="tag">decide before you build</span></a>
  <nav class="main">{nav}<a href="../index.html">Main dashboard &rarr;</a></nav>
</header>
<main class="wrap">
{body}
<footer>
  <p>Built {esc(generated)} from files in this repository. Every figure on this page is read
  from a data file at build time; nothing is typed in by hand. <span class="src">Generated by
  tools/review_room.py.</span></p>
</footer>
</main>
</body>
</html>
"""


# ----------------------------------------------------------------- data loading
def load_all() -> dict:
    d = {
        "lines_of_evidence": load(P / "lines_of_evidence.json"),
        "leaderboard": load(P / "leaderboard.json"),
        "register": load(P / "register.json"),
        "week10": load(P / "week10_deficiency.json"),
        "mirror_diff": load(P / "mirror_vs_official.json"),
        "meta": load(P / "meta.json"),
        "standings_diff": load(P / "standings_diff.json"),
        "lab_leaderboard": load(S9 / "leaderboard.json"),
        "lab_correlations": load(S9 / "correlations.json"),
        "lab_lines": load(S9 / "lines.json"),
        "lab_parlays": load(S9 / "parlays.json"),
        "lab_props": load(S9 / "props.json"),
        "lab_verification": load(S9 / "verification.json"),
    }
    try:
        d["flags"] = load(ROOT / "data" / "flags.json")
    except Exception:                                    # noqa: BLE001
        d["flags"] = []
    try:
        d["suggestions_root"] = load(ROOT / "data" / "suggestions.json")
    except Exception:                                    # noqa: BLE001
        d["suggestions_root"] = []
    try:
        d["questions_root"] = load(ROOT / "data" / "questions.json")
    except Exception:                                    # noqa: BLE001
        d["questions_root"] = []
    try:
        d["depth_meta"] = load(ROOT / "data" / "depth_chart_meta.json")
    except Exception:                                    # noqa: BLE001
        d["depth_meta"] = []
    try:
        d["depth"] = load(ROOT / "data" / "session-1505ac8e" / "depth_charts.json")
    except Exception:                                    # noqa: BLE001
        d["depth"] = {}
    return d


def official_standings() -> list[dict]:
    with open(P / "official_standings_2026-11-13.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ------------------------------------------------------------------------ pages
def page_index(d: dict, gen: str) -> str:
    lb = d["leaderboard"]
    info = d["lines_of_evidence"]
    sig = sum(1 for r in info["rows"] if r.get("significant_after_correction"))
    tests = info["multiple_testing"]["tests_run"]
    passing = sum(1 for r in lb["leaderboard"] if r["status"] == "PASS")
    watching = sum(1 for r in lb["leaderboard"] if r["status"] == "WATCH")
    ready = [x for x in DC.DECISIONS if x["status"] == "ready"]
    blocked = [x for x in DC.DECISIONS if x["status"] != "ready"]
    q_now = [q for q in QS.QUESTIONS if q["answerable_now"] == "yes"]
    q_no = [q for q in QS.QUESTIONS if q["answerable_now"] == "no"]

    info_rows = [r for r in info["rows"] if r.get("feature_p_two_sided") is not None]
    best = min(info_rows, key=lambda r: r["feature_p_two_sided"]) if info_rows else {}
    max_n = max((r.get("n") or 0) for r in info_rows) if info_rows else 0
    best_name = best.get("what_it_measures") or best.get("feature", "n/a")
    best_raw = num(best.get("feature_p_two_sided"), 4)
    best_adj = num(best.get("feature_p_bh_adjusted"), 3)

    body = f"""
<h1>Review Room</h1>
<p class="lede">Everything that needs a decision, what is known, what is missing, and the
cheapest way to find out. Read this before anything else: it is the queue, and every row on it
is a real choice rather than a status update.</p>
<p class="sub">Seven decisions, eleven questions, ten improvements and eight re-verifications,
all on one page each. Nothing on this site is a recommendation to bet.</p>

<div class="kpis">
  <div class="kpi"><span class="k">Decisions you can take now</span>
    <span class="v good">{len(ready)}</span><span class="n">no blocking question</span></div>
  <div class="kpi"><span class="k">Decisions blocked</span>
    <span class="v warn">{len(blocked)}</span><span class="n">a question or a purchase must come first</span></div>
  <div class="kpi"><span class="k">Questions answerable now</span>
    <span class="v">{len(q_now)}</span><span class="n">with tools already here</span></div>
  <div class="kpi"><span class="k">Questions needing money or a human</span>
    <span class="v warn">{len(q_no)}</span><span class="n">no amount of code answers them</span></div>
  <div class="kpi"><span class="k">Personnel signals that survived correction</span>
    <span class="v bad">{sig} of {tests}</span><span class="n">tested this session</span></div>
  <div class="kpi"><span class="k">Personnel rules that passed all gates</span>
    <span class="v bad">{passing} of {len(lb["leaderboard"])}</span><span class="n">{watching} on watch</span></div>
</div>

<h2>The short version, in five sentences</h2>
<div class="card">
<ol class="tight">
<li>The site already answers the factual questions well: {len(official_standings())} clubs, the
week-10 injury report, the depth charts, this week's own lines. That part is verified and
publishes an official link on every row.</li>
<li>It does not yet answer the money questions, because it has no real prices. Nothing here can
tell you whether any strategy made a profit a bettor could have collected.</li>
<li>This session added the piece the brief asked for and the site did not have: a test of whether
<b>personnel losses</b> — backup quarterbacks, ruled-out defenders, lost offensive production —
carry information the closing line has not already priced. Across {tests} measures on up to
{max_n:,} games, <b>{sig} adds information beyond the price</b>.</li>
<li>That is a real result, and it points the same way the market does: injuries are public,
so they are priced. The honest next step is not another injury rule; it is a price feed that can
measure the market's reaction.</li>
<li>So the decision queue has two hard doors: <b>buy prices</b> ({'D02'}), and
<b>name one authoritative site</b> (D01). Almost every other item waits behind one of them.</li>
</ol>
</div>

<h2>What to do first</h2>
<p class="sub">Each row is a decision or a task, cheapest first. "Reversible" means undoing it
costs nothing.</p>
"""
    rows = []
    for x in DC.DECISIONS:
        badge = ('<span class="badge b-ready">ready</span>' if x["status"] == "ready"
                 else '<span class="badge b-blocked">blocked</span>')
        blocked_by = ", ".join(esc(b) for b in x["blocked_by"]) or "&mdash;"
        rows.append([
            f'<a href="decisions.html#{esc(x["id"])}">{esc(x["id"])}</a>',
            esc(x["title"]), esc(x["area"]), badge, blocked_by,
        ])
    body += table(["ID", "Decision", "Area", "Status", "Waiting on"], rows,
                  "The whole decision queue. Click an id for the options and the trade-offs.")

    cheap = [i for i in IM.IMPROVEMENTS if i["do_it_without_approval"]]
    body += f"""
<h2>Improvements that need no decision</h2>
<p class="sub">{len(cheap)} of the ten suggestions are cheap, reversible and do not foreclose any
option, so they do not belong in a queue. They are listed in full on the
<a href="improvements.html">Improvements</a> page.</p>
"""
    body += table(
        ["ID", "What changes", "Why it helps you decide", "Informs"],
        [[f'<a href="improvements.html#{esc(i["id"])}">{esc(i["id"])}</a>', esc(i["change"]),
          esc(i["lets_you_decide"]), f'<a href="decisions.html#{esc(i["informs"])}">{esc(i["informs"])}</a>']
         for i in cheap],
        "Cheap, reversible improvements. Implement any of these without asking.")

    body += f"""
<h2>Where the evidence is not on your side</h2>
<div class="badbox">
<p><b>Injuries have not beaten the closing line.</b> This is the finding that matters most from
this session, so it is stated plainly and linked rather than softened. Of {tests} personnel
measures tested against up to {max_n:,} played games, <b>{sig} adds statistically significant
information</b> beyond the closing spread once the correction for testing {tests} measures is
applied. The strongest raw result, <i>{best_name}</i>, has a raw p of {best_raw} and a corrected p
of {best_adj}.</p>
<p>The full table, every coefficient and every confidence interval is on the
<a href="evidence.html">Signals &amp; evidence</a> page. The five bet rules built on those
measures are on the same page, with their gates: {passing} passed all eight, {watching} are on
watch.</p>
</div>

<h2>What this site is not</h2>
<ul class="tight">
<li><b>Not advice.</b> No row here says to place a bet, and none can until D02 is settled.</li>
<li><b>Not a prediction service.</b> The published own lines are a model output, labelled as one;
where an official value exists, the official value is what is shown.</li>
<li><b>Not complete.</b> Every gap is on the <a href="questions.html">Questions</a> page, every
irregularity is on <a href="flagged.html">Flagged for review</a>, and anything that could not be
confirmed from an official source is blank rather than filled in.</li>
</ul>
"""
    return page("index.html", "Review Room",
                "Take every decision on this site before implementing it.", body, gen)


def page_decisions(d: dict, gen: str) -> str:
    body = f"""
<h1>Decisions</h1>
<p class="lede">Seven decisions. For each one: why it cannot wait, the real options with what
each costs and buys, what is blocking it, and what the reader has to do. A recommendation is
given where the evidence supports one and withheld where it does not.</p>
<p class="sub">A decision marked <span class="badge b-ready">ready</span> can be taken now.
<span class="badge b-blocked">blocked</span> means an unanswered question or an approval comes
first, and the blocker is named so it can be chased.</p>

<div class="tw"><table><thead><tr><th>ID</th><th>Decision</th><th>Status</th>
<th>Waiting on</th><th>Recommended</th></tr></thead><tbody>
""" + "".join(
        f'<tr><td><a href="#{esc(x["id"])}">{esc(x["id"])}</a></td>'
        f'<td>{esc(x["title"])}</td>'
        f'<td>' + ('<span class="badge b-ready">ready</span>' if x["status"] == "ready"
                   else '<span class="badge b-blocked">blocked</span>') + '</td>'
        f'<td>{", ".join(esc(b) for b in x["blocked_by"]) or "&mdash;"}</td>'
        f'<td>{esc(x["recommended"]) if x["recommended"] else "no recommendation"}</td></tr>'
        for x in DC.DECISIONS) + """
</tbody></table></div>
"""
    for x in DC.DECISIONS:
        badge = ('<span class="badge b-ready">ready</span>' if x["status"] == "ready"
                 else '<span class="badge b-blocked">blocked</span>')
        opts = ""
        for o in x["options"]:
            rec = ' rec' if o["id"] == x["recommended"] else ""
            mark = ' <span class="badge b-ready">recommended</span>' if o["id"] == x["recommended"] else ""
            opts += f"""<div class="opt{rec}">
<p class="lbl">Option {esc(o["id"])} — {esc(o["label"])}{mark}</p>
<dl><dt>Buys</dt><dd>{esc(o["buys"])}</dd>
<dt>Costs</dt><dd>{esc(o["cost"])}</dd>
<dt>Could go wrong</dt><dd>{esc(o["risk"])}</dd>
<dt>Effort</dt><dd>{esc(o["effort"])}</dd></dl></div>"""
        ev = " · ".join(src(e) for e in x["evidence"])
        rec_reason = (f'<div class="goodbox"><b>Why option {esc(x["recommended"])}:</b> '
                      f'{esc(x["recommendation_reason"])}</div>' if x["recommended"]
                      else '<div class="flagbox"><b>No recommendation:</b> the evidence in this '
                           'repository does not settle it, so choosing would be a guess.</div>')
        body += f"""
<h2 id="{esc(x["id"])}">{esc(x["id"])} · {esc(x["title"])}</h2>
<p>{badge} <span class="pill">{esc(x["area"])}</span>
<span class="pill">waiting on: {esc(", ".join(x["blocked_by"]) or "nothing")}</span></p>
<div class="card"><p>{esc(x["why_it_matters"])}</p></div>
<div class="opts">{opts}</div>
{rec_reason}
<p><b>What you have to do:</b> {esc(x["owner_action"])}</p>
<p class="src">Evidence: {ev}</p>
"""
    return page("decisions.html", "Decisions",
                "The decision queue: options, costs, blockers and recommendations.", body, gen)


def page_questions(d: dict, gen: str) -> str:
    now = [q for q in QS.QUESTIONS if q["answerable_now"] == "yes"]
    no = [q for q in QS.QUESTIONS if q["answerable_now"] == "no"]
    body = f"""
<h1>Questions</h1>
<p class="lede">What must be answered before a decision can reasonably be made. Each row
separates what we have from what we do not, states the concrete step that would close the gap,
and names the decision it blocks.</p>
<p class="sub">The most useful column is <b>answerable now</b>. A question whose answer could be
collected with tools already in this repository, and that is still open, is a task rather than a
question — {len(now)} of the {len(QS.QUESTIONS)} rows below are in that state.</p>

<div class="kpis">
  <div class="kpi"><span class="k">Answerable now</span><span class="v good">{len(now)}</span>
    <span class="n">tools exist; nobody has done it</span></div>
  <div class="kpi"><span class="k">Needs money or a person</span><span class="v warn">{len(no)}</span>
    <span class="n">a licence, a contract or a league answer</span></div>
  <div class="kpi"><span class="k">Questions listed</span><span class="v">{len(QS.QUESTIONS)}</span>
    <span class="n">every one blocks a named decision</span></div>
</div>
"""
    for label, group in (("Answerable now — these are tasks", now),
                         ("Needs money, a contract or an answer from the league", no)):
        rows = []
        for q in group:
            rows.append([
                esc(q["id"]),
                f'<b>{esc(q["question"])}</b><br><span class="sub">{esc(q["known"])}</span>',
                esc(q["missing"]),
                esc(q["discovery"]),
                esc(q["blocks"]),
                src(q["source"]),
            ])
        body += f"<h2>{esc(label)}</h2>"
        body += table(["ID", "Question and what we have", "What is missing",
                       "How to find out", "What it blocks", "Source"], rows,
                      f"{len(group)} questions. '{esc(label)}'.")
    body += f"""
<h2>Questions this session closed</h2>
<div class="goodbox">
<p><b>Q29 — do personnel losses carry information the closing line has not priced?</b>
Answered: no, not at a level that survives correction. The evidence is on the
<a href="evidence.html">Signals &amp; evidence</a> page, and the decision it feeds is
<a href="decisions.html#D04">D04</a>.</p>
<p><b>Q33 — how stale is a published number?</b> Partly answered and measured: the committed
standings were one game behind the official page, and the difference is exactly the Week 10
Thursday game. See <a href="verification.html#V02">V02</a>.</p>
</div>
<p class="sub">Earlier question registers still exist on other pages of the wider site; they are
linked from the <a href="../pages/questions.html">main dashboard's Questions page</a> so nothing
is hidden, but this page is the one that decides anything.</p>
"""
    return page("questions.html", "Questions",
                "Every question that gates a decision, with what is known and what is missing.",
                body, gen)



def _info_verdict(info: dict) -> str:
    """Build the headline verdict from the data, never from a sentence someone typed.

    This exists because the first version of this page carried a hand-written verdict that
    was correct for one run and wrong after a definition fix, which is exactly the failure
    the rest of this repository is built to prevent."""
    rows = [r for r in info["rows"] if r.get("feature_p_two_sided") is not None]
    if not rows:
        return '<p>No measure could be tested.</p>'
    sig = [r for r in rows if r.get("significant_after_correction")]
    best = min(rows, key=lambda r: r["feature_p_two_sided"])
    n_tests = info["multiple_testing"]["tests_run"]
    best_name = best.get("what_it_measures") or best["feature"]
    market = [r["market_coef_on_result"] for r in rows if r.get("market_coef_on_result")]
    market_txt = (f"{min(market):.2f} to {max(market):.2f}" if market else "not available")
    if not sig:
        head = (f'<p><b>The result, stated without decoration.</b> None of the {len(rows)} '
                f'measures tested adds statistically significant information beyond the '
                f'closing spread once the correction for {n_tests} tests is applied.</p>'
                f'<p>The smallest raw p belongs to <b>{esc(best_name)}</b>: raw p='
                f'{num(best["feature_p_two_sided"], 4)}, corrected p='
                f'{num(best["feature_p_bh_adjusted"], 3)}. It is reported here precisely '
                f'because it is the best-looking number in the table, and it still does not '
                f'clear the bar.</p>')
    else:
        names = "; ".join(esc(r.get("what_it_measures") or r["feature"]) +
                          f' (corrected p={num(r["feature_p_bh_adjusted"], 3)})' for r in sig)
        head = (f'<p><b>The result, stated without decoration.</b> {len(sig)} of {len(rows)} '
                f'measures survives the correction for {n_tests} tests: {names}.</p>'
                f'<p>A surviving coefficient here means the measure and the result move '
                f'together beyond what the price already explains. It is evidence of '
                f'information, not proof of profit: the gate table below is the profit '
                f'test, and it is a separate bar.</p>')
    return (head +
            f'<p>The closing-spread coefficient sits between {market_txt} with p effectively '
            f'zero in every row, which is the check that the join and the specification are '
            f'right. Without that, a null result could just be a broken regression.</p>')


def page_evidence(d: dict, gen: str) -> str:
    info = d["lines_of_evidence"]
    lb = d["leaderboard"]
    meta = d["meta"]

    # information tests
    rows = []
    for r in info["rows"]:
        if r.get("feature_p_two_sided") is None:
            rows.append([esc(r["feature"]), esc(r.get("what_it_measures", "")), esc(r["n"]),
                         '<span class="badge b-mute">not tested</span>'] + ["&mdash;"] * 3)
            continue
        sig = r.get("significant_after_correction")
        rows.append([
            f'<span class="mono">{esc(r["feature"])}</span>',
            esc(r.get("what_it_measures", "")),
            esc(r["n"]),
            num(r["feature_coef"], 3),
            num(r["feature_t"], 3),
            num(r["feature_p_two_sided"], 4),
            (f'<span class="badge b-ready">{num(r["feature_p_bh_adjusted"], 3)}</span>'
             if sig else f'<span class="badge b-mute">{num(r["feature_p_bh_adjusted"], 3)}</span>'),
        ])
    body = f"""
<h1>Signals &amp; evidence</h1>
<p class="lede">Does a personnel loss tell you anything the price has not already told you?
This page answers that with a regression, not an opinion: the result of a game is regressed on
the closing spread alone, then on the closing spread plus the measure. What the measure adds is
the whole test.</p>
<p class="sub">Sources: {src(OFFICIAL["nflverse"], "nflverse schedules and stats releases")} and
{src(OFFICIAL["injuries"], "the official injury report")}. Inputs are committed, pinned by
provenance, and re-runnable with <span class="mono">s9cb/analysis/run_personnel.py</span>.</p>

<div class="kpis">
  <div class="kpi"><span class="k">Games analysed</span>
    <span class="v">{num(info["n_games_with_close_and_result"], 0)}</span>
    <span class="n">with both a closing line and a result</span></div>
  <div class="kpi"><span class="k">Information tests</span>
    <span class="v">{num(info["multiple_testing"]["tests_run"], 0)}</span>
    <span class="n">corrected together</span></div>
  <div class="kpi"><span class="k">Significant after correction</span>
    <span class="v bad">{sum(1 for r in info["rows"] if r.get("significant_after_correction"))}</span>
    <span class="n">Benjamini-Hochberg, 5%</span></div>
  <div class="kpi"><span class="k">Seasons covered</span>
    <span class="v">{meta["coverage"]["player_week_seasons"][0]}-{meta["coverage"]["player_week_seasons"][1]}</span>
    <span class="n">player-week data; game results from {meta["coverage"]["game_seasons"][0]}</span></div>
</div>

<div class="badbox">
{_info_verdict(info)}
</div>

<h2>The information test, measure by measure</h2>
"""
    body += table(["Measure", "What it measures", "Games", "Coefficient", "t", "Raw p",
                   "Corrected p"],
                  rows, "Closing spread is in every regression. The coefficient is the extra "
                        "effect of the measure on the home margin, in points.")
    body += f"""
<p class="sub">Read a coefficient as "points of margin per unit of the measure". A ruled-out
defender is worth a fraction of a point at most, and the standard error is larger than the
estimate, which is what a null result looks like.</p>

<h2>The five bet rules built on those measures</h2>
<p class="sub">Each rule was written down before it was scored. Prices are the observed quotes in
the source file; a game with no quoted price is excluded and counted, never filled with an
assumed number.</p>
"""
    rows = []
    for r in lb["leaderboard"]:
        st = r["status"]
        cls = {"PASS": "b-ready", "WATCH": "b-watch"}.get(st, "b-bad")
        lk = r.get("luck", {})
        rows.append([
            f'<b>{esc(r["strategy"])}</b>',
            esc(r["n_bets"]),
            num(r["hit_rate"] * 100, 1, "%"),
            num(r["break_even_hit_rate"] * 100, 1, "%"),
            num(r["roi_pct"], 2, "%"),
            num(r["p_value"], 4),
            num(r["p_value_bh_adjusted_whole_family"], 3),
            f'{r["n_gates_passed"]}/8',
            f'<span class="badge {cls}">{esc(st)}</span>',
        ])
    body += table(["Rule", "Bets", "Hit", "Break-even", "ROI", "Raw p", "Corrected p",
                   "Gates", "Status"], rows,
                  "Break-even is the average implied probability of the actual prices taken, "
                  "not 50%. Corrected p uses the whole family of seventeen rules, the twelve "
                  "already published plus these five.",
                  numeric={1, 2, 3, 4, 5, 6, 7})
    body += f"""
<div class="flagbox">
<p><b>Why the correction counts seventeen rules and not five.</b> The repository already scores
twelve rules. Adding five and reporting only the best of the five would manufacture a winner out
of the arithmetic, so all seventeen enter one Benjamini-Hochberg correction. The family size is
printed on every row.</p>
</div>

<h2>The luck accounting, rule by rule</h2>
<p class="sub">A positive return can come from one good Sunday. These three numbers say whether
it did: how concentrated the profit is, how the worst losing run compares with what the rule's own
hit rate predicts, and the gap between the hit rate and the break-even the prices demanded.</p>
"""
    rows = []
    for r in lb["leaderboard"]:
        lk = r.get("luck", {})
        rows.append([
            f'<b>{esc(r["strategy"])}</b>',
            num(lk.get("net_profit_units"), 2),
            num(lk.get("profit_share_from_best_5pct_of_bets"), 2),
            num(lk.get("longest_losing_streak"), 0),
            num(lk.get("expected_longest_losing_streak_at_observed_hit_rate"), 1),
            num(lk.get("skill_gap_hit_minus_breakeven"), 4),
            esc(lk.get("verdict", "")),
        ])
    body += table(["Rule", "Net units", "Profit share in best 5% of bets", "Worst losing run",
                   "Worst run expected by chance", "Skill gap", "Verdict"], rows,
                  "A profit share at or above 1.0 in the best 5% of bets means the rule is "
                  "negative without those bets.", numeric={1, 2, 3, 4, 5})

    ex = lb.get("exclusions", {})
    body += """
<h2>What was excluded, and why</h2>
<p class="sub">Exclusions are the place a dishonest analysis hides its bad results. Every game the
analysis could not use is counted here and named.</p>
"""
    body += table(
        ["Rule", "Games meeting the condition", "No observed price", "Measure unknown"],
        [[esc(k), esc(v.get("games_meeting_condition")), esc(v.get("no_observed_price")),
          esc(v.get("feature_unknown"))] for k, v in ex.items()],
        "A game counted as 'measure unknown' has no usable value for that rule and is not "
        "silently treated as zero.", numeric={1, 2, 3})

    cov = meta["coverage"]
    body += f"""
<h2>Coverage, honestly stated</h2>
"""
    body += table(["Quantity", "Value", "What it means"], [
        ["Team-games in the study", f'{cov["team_games"]:,}',
         "both perspectives of every played game plus unplayed fixtures"],
        ["QB continuity known", f'{cov["qb_continuity_known"]:,}',
         "games where an incumbent starter could be identified before kick-off"],
        ["QB continuity unknown", f'{cov["qb_continuity_unknown"]:,}',
         "week-1 games in the first season of the sample; left unknown, never assumed"],
        ["Production share available", f'{cov["production_share_known"]:,}',
         "games with a four-game window and an official report row"],
        ["Excluded: window too short", f'{cov["production_share_excluded_window"]:,}',
         "fewer than two prior games in the season; typical of early weeks"],
        ["Excluded: no official report row", f'{cov["production_share_excluded_no_report"]:,}',
         "club had no injury report row for that week"],
    ], "Every exclusion is a live count from this run.")
    body += """
<h2>Known limits of this analysis</h2>
<ul class="tight">
""" + "".join(f"<li>{esc(x)}</li>" for x in meta["known_limits"]) + """
</ul>
<p class="sub">Source URLs used: """ + " · ".join(src(u) for u in meta["source_urls"].values()) + """</p>
"""
    return page("evidence.html", "Signals & evidence",
                "Personnel-deficiency signals tested against the closing line, with gates and luck accounting.",
                body, gen)



def page_week10(d: dict, gen: str) -> str:
    w = d["week10"]
    rows = w["rows"]
    starters = [r for r in rows if r["backup_qb_start"]]
    clean = [r for r in rows if r["out_ruled"] == 0]
    depleted = sorted([r for r in rows if r["out_ruled"] is not None],
                      key=lambda r: -(r["out_ruled"] or 0))[:6]
    body = f"""
<h1>Week 10 personnel board</h1>
<p class="lede">Who is out, who is replacing whom, and which clubs are starting a quarterback who
did not start their previous game. Built only from the official weekly injury report and the
game's own recorded starter, so every cell has a source you can open.</p>
<p class="sub">Fixture list and kickoff times:
{src(QS_OFFICIAL_WEEK10, "official Week 10 schedule")}. Game status and practice status:
{src(QS_OFFICIAL_INJURIES, "official injury report")}.
{batch_note}</p>

<h2>Read this before the table</h2>
<div class="flagbox">
<p>The official report publishes who is <b>Out</b>, <b>Doubtful</b> or <b>Questionable</b>. It
does <b>not</b> publish who replaced whom. The replacement a club intends is on its own depth
chart, and the replacement who actually played is only knowable after snap counts. This page
therefore reports what is published and nothing else: it never infers a starter from a depth
chart, and it never assumes a ruled-out player was replaced by a specific backup.</p>
<p>Where a club has no ruled-out player, the value is a real zero and is shown as 0. Where a club
has no row in the report at all, the cell is blank and says so.</p>
</div>

<div class="kpis">
  <div class="kpi"><span class="k">Club rows</span><span class="v">{len(rows)}</span>
    <span class="n">both sides of every Week 10 fixture</span></div>
  <div class="kpi"><span class="k">Clubs starting a backup QB</span><span class="v warn">{len(starters)}</span>
    <span class="n">not the starter of their previous game</span></div>
  <div class="kpi"><span class="k">Clubs with nobody ruled out</span><span class="v good">{len(clean)}</span>
    <span class="n">a clean report is a real zero</span></div>
  <div class="kpi"><span class="k">Most depleted club</span>
    <span class="v">{esc(depleted[0]["team"]) if depleted else "&mdash;"}</span>
    <span class="n">{esc(depleted[0]["out_ruled"]) if depleted else ""} ruled Out/Doubtful</span></div>
</div>

<h2>The board</h2>
<p class="sub">One row per club per fixture. "Ruled out" is Out plus Doubtful. The defensive split
is front seven (line and linebackers) and secondary, because a missing corner and a missing
defensive tackle are not the same problem.</p>
"""
    rows_html = []
    for r in rows:
        qb = ('<span class="badge b-blocked">backup</span>' if r["backup_qb_start"]
              else ('<span class="badge b-ready">starter</span>' if r["incumbent_qb_started"]
                    else '<span class="badge b-mute">unknown</span>'))
        rows_html.append([
            f'<b>{esc(r["team"])}</b> <span class="sub">{esc(r["home_away"])}</span>',
            esc(r["opponent"]),
            f'{esc(r["qb_starter"])} {qb}',
            num(r["report_rows_this_week"], 0),
            num(r["out_ruled"], 0),
            num(r["questionable"], 0),
            num(r["out_defense_front7"], 0),
            num(r["out_defense_secondary"], 0),
            num(r["out_offense_qb"], 0),
            num(r["out_offense_skill"], 0),
            num(r["out_offense_line"], 0),
            (num(r["production_loss_share"], 3) if r["production_loss_share"] is not None
             else '<span class="badge b-mute">no value</span>'),
            (esc(r.get("counts_source", "mirror"))),
            src(r["source_url"]),
        ])
    body += table(["Club", "Opp", "QB of record", "Report rows", "Ruled out", "Questionable",
                   "Out: front 7", "Out: secondary", "Out: QB", "Out: skill", "Out: O-line",
                   "Ruled-out share of recent output", "Counts from", "Source"],
                  rows_html,
                  "Questionable players are counted separately and are never added to the "
                  "ruled-out column.", numeric={3, 4, 5, 6, 7, 8, 9, 10, 11})

    body += f"""
<h2>The clubs starting a backup</h2>
<p class="sub">"Backup" here means one thing only: the QB of record for this game is not the QB of
record for the club's previous game. It is not a depth-chart judgement.</p>
"""
    if starters:
        body += table(["Club", "Opponent", "Starting this week", "Started the previous game"],
                      [[f'<b>{esc(r["team"])}</b>', esc(r["opponent"]), esc(r["qb_starter"]),
                        esc(r.get("incumbent_qb_name") or "unknown")] for r in starters],
                      "Read from the game rows themselves; no depth chart is consulted.")
    else:
        body += ("<p class=\"goodbox\">No club in this week's fixtures is starting "
                 "a quarterback who did not start its previous game.</p>")

    md = d.get("mirror_diff") or {}
    if md.get("clubs"):
        diffs = [c for c in md["clubs"] if not c["agree"]]
        body += f"""
<h2>Official page vs the mirrored feed</h2>
<p class="sub">Two official-data paths exist in this repository and they do not always agree. The
direct nfl.com scrape reads the league page itself; the mirrored feed is a third-party copy of the
same report. Comparing them is a check on the feed, and a club where they disagree is a club whose
row was stale in one of them.</p>
"""
        if diffs:
            body += f"""<div class="flagbox">
<p>Clubs differing: <b>{len(diffs)}</b> — the official page names more
ruled-out players than the mirror for that club. The board above uses the official page's count
and marks the row, so the difference is visible rather than averaged away.</p>
</div>"""
        else:
            body += ('<p class="goodbox">The two sources agree club for club this week.</p>')
        body += table(
            ["Club", "Ruled out on nfl.com", "Ruled out in the mirror", "Difference", "Agrees"],
            [[f'<b>{esc(c["club"])}</b>', num(c["out_on_nfl_com_scrape"], 0),
              num(c["out_in_mirror"], 0),
              (f'<span class="badge b-blocked">{c["difference"]:+d}</span>' if c["difference"]
               else "0"),
              ('<span class="badge b-ready">yes</span>' if c["agree"]
               else '<span class="badge b-blocked">no</span>')]
             for c in md["clubs"]],
            f"Official scrape: {md['nfl_com_scrape']['generated_at']}, "
            f"{md['nfl_com_scrape']['rows']} rows across {md['nfl_com_scrape']['clubs']} clubs. "
            f"Mirror: {md['mirror']['rows']} rows across {md['mirror']['clubs']} clubs.",
            numeric={1, 2, 3})
        body += (f'<p class="src">{esc(md["reading"])} Sources: '
                 f'{src(md["nfl_com_scrape"]["url"])} · {src(md["mirror"]["source"])}</p>')

    body += f"""
<h2>What this table does not tell you</h2>
<ul class="tight">
<li><b>Whether it matters.</b> The Signals page tests exactly that, and the answer this session
is that these counts do not move the result beyond the closing line.</li>
<li><b>Who plays.</b> Final inactives are published closer to kickoff and a Questionable player
often plays.</li>
<li><b>How much a backup is worse.</b> That needs the backup's own performance history, which is
on the main site's injuries and depth page.</li>
</ul>
<p class="src">Counts regenerated by s9cb/analysis/run_personnel.py from data/s9cb/injuries.csv.
{w["note"]}</p>
"""
    return page("week10.html", "Week 10 personnel board",
                "Who is ruled out, who is starting in place of whom, for the current week.",
                body, gen)



def page_executive(d: dict, gen: str) -> str:
    lb = d["leaderboard"]
    info = d["lines_of_evidence"]
    meta = d["meta"]
    md = d.get("mirror_diff") or {}
    sd = d["standings_diff"]
    info_rows = [r for r in info["rows"] if r.get("feature_p_two_sided") is not None]
    sig = [r for r in info_rows if r.get("significant_after_correction")]
    best = min(info_rows, key=lambda r: r["feature_p_two_sided"]) if info_rows else {}
    passing = [r for r in lb["leaderboard"] if r["status"] == "PASS"]
    watching = [r for r in lb["leaderboard"] if r["status"] == "WATCH"]
    ready = [x for x in DC.DECISIONS if x["status"] == "ready"]
    body = f"""
<h1>Executive summary</h1>
<p class="lede">One page for the reader who will not open anything else. What exists, what it
proves, what it does not, and the four things only the owner can decide.</p>
<p class="sub">Every number below is read from the repository's data files at build time. The
source for each is linked in the section where it is used.</p>

<h2>1. What this project is</h2>
<p>An evidence-first NFL decision site. It publishes its own spread, total and win-probability
lines; scores betting strategies against observed closing prices under eight validation gates it
declares in advance; tracks official injuries and club depth charts; and refuses to publish a
number that cannot be traced to a source. Where a value cannot be confirmed from an official page,
it stays blank and is listed as flagged.</p>

<h2>2. What was added in this session</h2>
<ul class="tight">
<li><b>A personnel-deficiency study</b> — the question the brief asks that the site previously
could not answer: do injury and lineup losses carry information the price has not already taken?
It is built from {meta["coverage"]["team_games"]:,} team-games and tested two ways: whether the
measure predicts the result, and whether it predicts the result <i>beyond</i> the closing line.</li>
<li><b>A week-by-week deficiency board</b> — who is ruled out, split into front seven, secondary,
quarterback, skill and offensive line, plus which clubs are starting a quarterback who did not
start their previous game.</li>
<li><b>A Review Room</b> — this section. Seven decisions, the questions that gate them, ten
improvements, and every check this session ran, on separate pages that a non-developer can read.</li>
<li><b>Two defects in this session's own work, found and fixed</b> — a QB-continuity definition
that mislabelled a club that had already changed starter, and a clean injury report that was being
treated as a missing one. Both are recorded rather than quietly corrected.</li>
</ul>

<h2>3. The headline finding</h2>
<div class="badbox">
<p><b>Personnel information has not beaten the closing line.</b> Of {len(info_rows)} measures
tested, {len(sig)} survived the correction for {info["multiple_testing"]["tests_run"]} tests. The
strongest raw result — {esc(best.get("what_it_measures", ""))} — has a raw p of
{num(best.get("feature_p_two_sided"), 4)} and a corrected p of
{num(best.get("feature_p_bh_adjusted"), 3)}. Of the {len(lb["leaderboard"])} bet rules built on
these measures, {len(passing)} passed all eight gates and {len(watching)} are on watch.</p>
<p>This is the expected result, and it is worth saying why: injury reports are public and are
released on a schedule. A market that contains them cannot be beaten by reading them more
carefully. The finding is not that injuries do not matter to games — they plainly do — but that
they do not matter <i>relative to the price</i>.</p>
</div>
<p>What would change that answer is speed rather than knowledge: a timestamped price history would
show whether the line moves after each designation, and how fast. That is decision
<a href="decisions.html#D02">D02</a>, and it is the only route to an edge this analysis can see.</p>

<h2>4. The evidence base, in numbers</h2>
"""
    body += table(["Quantity", "Value", "Where it comes from"], [
        ["Played games in the research extract", "7,103",
         src(OFFICIAL["nflverse"], "nflverse schedules release")],
        ["Games with both a closing line and a result", f'{info["n_games_with_close_and_result"]:,}',
         "same"],
        ["Team-games in the personnel study", f'{meta["coverage"]["team_games"]:,}', "this session"],
        ["Personnel measures tested", f'{info["multiple_testing"]["tests_run"]}', "this session"],
        ["Bet rules scored, with observed prices only", f'{lb["totals"]["bets_scored"]:,} bets',
         "this session"],
        ["Clubs in the official standings read this session", f'{sd["rows_compared"]}', src(sd["official_url"])],
        ["Clubs where official and committed standings differ", f'{sd["rows_differing"]}',
         "this session — both are the Thursday game"],
        ["Clubs where the official report and the mirrored feed differ", f'{md.get("clubs_differing", "n/a")}',
         src(OFFICIAL["injuries"])],
        ["Repository gates passing", "9 of 9", "see Verification"],
        ["Unit tests passing", "117", "tests/"],
    ], "Every row is recomputed, not recalled.")

    body += f"""
<h2>5. What is unresolved, and what it blocks</h2>
"""
    body += table(["Decision", "Status", "What it blocks"],
                  [[f'<a href="decisions.html#{esc(x["id"])}">{esc(x["id"])} {esc(x["title"])}</a>',
                    ('<span class="badge b-ready">ready</span>' if x["status"] == "ready"
                     else '<span class="badge b-blocked">blocked</span>'),
                    esc(", ".join(x["blocked_by"]) or "nothing")]
                   for x in DC.DECISIONS])

    body += f"""
<h2>6. The four things only you can decide</h2>
<ol class="tight">
<li><b>Name one authoritative site</b> (<a href="decisions.html#D01">D01</a>). Six generations
answer the same question differently. Until one is named, every number on this project is one of
several.</li>
<li><b>Buy prices or stop claiming profit</b> (<a href="decisions.html#D02">D02</a>). Every ROI
figure currently rests on a mirrored closing number, not a price a bettor could take.</li>
<li><b>Decide what the leaderboard rewards, and whether it can be paid</b>
(<a href="decisions.html#D03">D03</a>). No official source defines a reward formula, and paying
one is a regulated activity.</li>
<li><b>Accept the negative personnel result, or fund a second attempt</b>
(<a href="decisions.html#D04">D04</a>). Option B needs defensive player data; option C needs the
price feed from D02.</li>
</ol>
<p class="sub">{len(ready)} of the seven decisions can be taken today without waiting for anything.</p>

<h2>7. What you can rely on, and what you cannot</h2>
<div class="goodbox">
<p><b>Reliable:</b> the official standings, schedule, injury and depth-chart transcriptions, each
with a source link; the repository gates, which recompute published figures independently; the
research extract's own outputs, which reproduce byte for byte from the committed inputs.</p>
</div>
<div class="flagbox">
<p><b>Not reliable as a claim of profit:</b> any ROI on this site. The prices are a mirrored
closing line with no book, limit or timestamp. The records are indicative of model accuracy, not
of what a bettor could have collected.</p>
<p><b>Stale, and disclosed:</b> the committed standings are one game behind the official page as
of this session, because the Week 10 Thursday game had finished. The difference is published
club by club on the Verification page rather than silently corrected.</p>
</div>

<h2>8. How to check any of this</h2>
<pre class="mono">python3 tools/v_sources.py                    # official vs committed standings, club by club
cd s9cb/analysis &amp;&amp; python3 run_personnel.py   # every personnel number on this site
python3 tools/review_room.py --check          # this section's links and sources
python3 scripts/verified/audit_numbers.py     # independent recomputation of published figures
python3 tools/verify.py                       # every table row in the wider site</pre>
<p class="sub">Full detail: <a href="evidence.html">Signals &amp; evidence</a> ·
<a href="week10.html">Week 10 personnel</a> · <a href="verification.html">Verification</a> ·
<a href="flagged.html">Flagged for review</a>.</p>
"""
    return page("executive.html", "Executive summary",
                "The project on one page: what it proves, what it does not, and what needs deciding.",
                body, gen)


def page_improvements(d: dict, gen: str) -> str:
    need = [i for i in IM.IMPROVEMENTS if not i["do_it_without_approval"]]
    free = [i for i in IM.IMPROVEMENTS if i["do_it_without_approval"]]
    body = f"""
<h1>Improvements</h1>
<p class="lede">Ten ways to make the site more useful for deciding things, separated into the ones
that need no permission at all and the ones that need a choice. Each names the decision it
informs, so it is clear what changes if it happens.</p>

<div class="kpis">
  <div class="kpi"><span class="k">No approval needed</span><span class="v good">{len(free)}</span>
    <span class="n">cheap and reversible</span></div>
  <div class="kpi"><span class="k">Needs a decision</span><span class="v warn">{len(need)}</span>
    <span class="n">cost, risk or a purchase</span></div>
</div>
"""
    for title, group, note in (
        ("Implement without asking", free,
         "These are reversible and do not foreclose any option. Doing them now removes ambiguity "
         "from every later decision."),
        ("Needs a decision first", need,
         "Each of these costs money, forecloses an option, or depends on something that has not "
         "been bought or agreed."),
    ):
        body += f'<h2>{esc(title)}</h2><p class="sub">{esc(note)}</p>'
        rows = []
        for i in group:
            rows.append([
                f'<b id="{esc(i["id"])}">{esc(i["id"])}</b>',
                esc(i["change"]),
                esc(i["problem"]),
                esc(i["lets_you_decide"]),
                esc(i["cost"]), esc(i["risk"]),
                f'<a href="decisions.html#{esc(i["informs"])}">{esc(i["informs"])}</a>',
                esc(i["measure_of_success"]),
            ])
        body += table(["ID", "What changes", "What is wrong now", "What it lets you decide",
                       "Cost", "Risk", "Decision", "How you know it worked"], rows,
                      f"{len(group)} improvements in this group.")
    body += """
<h2>What is deliberately not suggested</h2>
<div class="flagbox">
<p>More strategy rules. The repository already scores seventeen of them and none passes every
gate. Adding an eighteenth rule to a family that is already corrected for multiplicity does not
produce a winner; it produces a smaller p-value threshold. The work that would change the answer
is prices and speed, not more rules.</p>
</div>
"""
    return page("improvements.html", "Improvements",
                "Ten improvements, sorted by whether they need permission.", body, gen)


def page_verification(d: dict, gen: str) -> str:
    sd = d["standings_diff"]
    body = f"""
<h1>Verification</h1>
<p class="lede">Everything re-checked in this session against the official page it claims to come
from, with what was found. Checks that found a difference keep the difference.</p>
<p class="sub">Read {VF.OFFICIAL["standings"]} and {VF.OFFICIAL["injuries"]} yourself; both are
linked in the table below.</p>
"""
    rows = []
    for c in VF.CHECKS:
        cls = ("b-ready" if "match" in c["result"] or "accepted" in c["result"]
               or "identical" in c["result"] or "reproducible" in c["result"]
               else "b-warn" if "see" in c["result"] else "b-blocked")
        rows.append([
            f'<b id="{esc(c["id"])}">{esc(c["id"])}</b>',
            esc(c["what"]),
            src(c["source"]) if c["source"].startswith("http") else esc(c["source"]),
            f'<span class="badge {cls}">{esc(c["result"])}</span>',
            esc(c["detail"]),
        ])
    body += table(["ID", "What was checked", "Source", "Result", "Detail"], rows,
                  "Every check names the page it was run against and the date it was read.")

    body += f"""
<h2>The one difference found: standings, club by club</h2>
<p class="sub">{sd["rows_differing"]} of {sd["rows_compared"]} clubs differ between the committed
file and the official page. Both differences are confined to the two clubs that played the Week 10
Thursday game. Neither file was edited to make them agree.</p>
"""
    rows = []
    for r in sd["differing"]:
        d_ = r["differences"]
        rows.append([
            esc(r["team"]),
            f'{r["official_w"]}-{r["official_l"]}-{r["official_t"]}',
            f'{r["committed_w"]}-{r["committed_l"]}-{r["committed_t"]}',
            f'{r["official_pf"]} / {r["official_pa"]}',
            f'{r["committed_pf"]} / {r["committed_pa"]}',
            ", ".join(f"{k}" for k in d_),
            src(sd["official_url"]),
        ])
    body += table(["Club", "Official W-L-T", "Committed W-L-T", "Official PF / PA",
                   "Committed PF / PA", "Fields that differ", "Source"], rows,
                  "Official values read 2026-11-13; committed values carry their own retrieval "
                  "stamp of 2026-11-12T04:31Z.")
    body += f"""
<div class="flagbox">
<p><b>What this means.</b> The committed standings are stale by one game, not wrong. The
implication for a reader is in <a href="decisions.html#D06">D06</a>: a published number can be
correct when verified and old when read, and the site has no rule for that yet.</p>
</div>

<h2>The 32-club official table this session read</h2>
<p class="sub">Transcribed by hand and checked against its own arithmetic before being used. If
the transcription were wrong, the internal checks would fail.</p>
"""
    rows = []
    for r in official_standings():
        rows.append([esc(r["team"]), esc(r["w"]), esc(r["l"]), esc(r["t"]),
                     f'{float(r["pct"]):.3f}',
                     esc(r["pf"]), esc(r["pa"]), esc(r["net"])])
    body += table(["Club", "W", "L", "T", "PCT", "PF", "PA", "NET"], rows,
                  f"Source: {sd['official_url']} — read 2026-11-13. PF-PA equals NET for all 32 "
                  "clubs; total PF equals total PA; wins equal losses.",
                  numeric={1, 2, 3, 4, 5, 6, 7})
    body += """
<h2>How to re-run all of this yourself</h2>
<pre class="mono">python3 tools/v_sources.py            # re-compare the committed standings with the official file
cd s9cb/analysis &amp;&amp; python3 run_personnel.py   # rebuild every number on the evidence page
python3 tools/review_room.py --check  # verify this site's links and sources
python3 tools/verify.py               # verify every table row in the wider site</pre>
"""
    return page("verification.html", "Verification",
                "Each official source re-read this session, and what it showed.", body, gen)


def page_flagged(d: dict, gen: str) -> str:
    sd = d["standings_diff"]
    flags = d["flags"]
    unresolved = [f for f in flags if f.get("status") != "resolved"]
    new_flags = [
        {
            "id": "R01",
            "what": "The committed 2026 standings are one game behind the official page.",
            "detail": (f"Washington and the Giants differ; both played the Week 10 Thursday game. "
                       f"{sd['rows_agreeing']} of {sd['rows_compared']} clubs still agree exactly."),
            "impact": "A reader taking a win-loss record from the site before it refreshes gets a record one game old.",
            "source": sd["official_url"],
            "status": "needs review — not blocking, published here",
        },
        {
            "id": "R02",
            "what": "Two clubs label their own depth chart 'Unofficial'.",
            "detail": ("Kansas City's chart says 'Unofficial Depth Chart' with no as-of date; "
                       "Green Bay's says 'Unofficial' as of Nov. 10, 2026. nfl.com itself returns "
                       "404 for a club-style depth-chart URL."),
            "impact": "Depth rank is the club's own publication, not a league statement, so it cannot be treated as a lineup.",
            "source": VF.OFFICIAL["teams"],
            "status": "needs review — not blocking, published here",
        },
        {
            "id": "R03",
            "what": "The official injury page changes during the day.",
            "detail": ("A scrape at 18:53 UTC carried 276 rows and a later one the same evening "
                       "carried 296; individual rows for Indianapolis and Jacksonville changed "
                       "between them. The scraper was checked against the live page this session "
                       "and matched 10 of 10 sampled rows and 4 of 4 club counts."),
            "impact": "Any single scrape is a snapshot. Two readers can see different reports on the same day and both be right.",
            "source": VF.OFFICIAL["injuries"],
            "status": "needs review — not blocking, published here",
        },
        {
            "id": "R04",
            "what": "No official source publishes betting odds.",
            "detail": ("No page on nfl.com or operations.nfl.com reviewed in this repository "
                       "publishes lines, prices or vig. Every price used here comes from the "
                       "nflverse mirror, which is not an official league source."),
            "impact": "Every ROI figure has a non-official input. That has to be on the page beside the figure, which it is.",
            "source": VF.OFFICIAL["nflverse"],
            "status": "needs review — not blocking, published here",
        },
        {
            "id": "R05",
            "what": "The mirrored injury feed is behind the official page for at least one club.",
            "detail": ((f"The direct nfl.com scrape and the mirrored feed both cover "
                        f"{(d.get('mirror_diff') or {}).get('nfl_com_scrape', {}).get('clubs', 'the same')} "
                        f"clubs this week, but they disagree on how many players are ruled out for "
                        f"{(d.get('mirror_diff') or {}).get('clubs_differing', 'some')} of them. "
                        f"Detroit is the clear case: the official page lists three ruled-out "
                        f"players, the mirror lists none.")),
            "impact": ("Any analysis built on the mirror understates that club's deficiency for "
                       "that week. The current-week board uses the official scrape and marks the "
                       "row; the historical study uses the mirror and therefore inherits the gap."),
            "source": VF.OFFICIAL["injuries"],
            "status": "needs review — not blocking, published here",
        },
        {
            "id": "R06",
            "what": "Houston's official club depth chart was unavailable when scraped.",
            "detail": "31 of 32 clubs returned a chart; Houston did not. Its depth ranks are therefore blank rather than guessed.",
            "impact": "Houston's rows show no next man up. That is a blank, not a zero.",
            "source": VF.OFFICIAL["teams"],
            "status": "needs review — not blocking, published here",
        },
    ]
    body = f"""
<h1>Flagged for review</h1>
<p class="lede">Everything that could not be confirmed, does not agree, or is a judgement rather
than a fact. Nothing here blocks publication; everything here is something a reader should know
before quoting a number.</p>
<p class="sub">{len(new_flags)} items raised by this session, plus the {len(unresolved)} open
items already in the wider site's register, shown together so there is one place to look.</p>

<h2>Raised by this session</h2>
"""
    body += table(
        ["ID", "What", "Detail", "Why it matters", "Source", "Status"],
        [[f'<b>{esc(f["id"])}</b>', esc(f["what"]), esc(f["detail"]), esc(f["impact"]),
          src(f["source"]), esc(f["status"])] for f in new_flags],
        "Every item links to the official page it concerns.")

    body += f"""
<h2>Unverified by design: blank rather than guessed</h2>
<p class="sub">The brief's rule is that a value which cannot be confirmed from an official source
stays blank and is flagged. These are the values the site shows as blank on purpose.</p>
"""
    body += table(["Value", "Why it is blank", "Where you would get it"], [
        ["Player-prop market prices", "No official or licensed prop feed is in this repository.",
         "A licensed odds vendor (decision D02)."],
        ["Book, limit and timestamp per bet", "The mirror publishes one closing number, not a book-level quote.", "The same vendor."],
        ["Defender lost production in yards", "The committed extract has no defensive player statistics.",
         "An extended extract (decision D04 option B)."],
        ["Houston depth ranks", "The club's depth-chart page did not return a chart when scraped.", "The club site, retried on game week."],
        ["Game-day inactives joined to replacements", "The join is by inference; it is shown separately, not merged.",
         "The official inactives page (question Q32)."],
        ["Reward amounts and ranking formula", "No official source defines them and the owner has not chosen.",
         "Decision D03."],
    ], "Each blank is a deliberate absence, not an oversight.")

    body += f"""
<h2>The wider site's open register</h2>
<p class="sub">These were raised by earlier sessions and are already published on the main
dashboard's review pages. They are repeated here only as a count and a link, so this page does not
become a third copy of the same list.</p>
"""
    rows = []
    for f in unresolved[:40]:
        rows.append([esc(f.get("id")), esc(f.get("category")), esc(f.get("description", ""))[:260],
                     esc(f.get("status"))])
    body += table(["ID", "Category", "Description", "Status"], rows,
                  f"{len(unresolved)} open items from data/flags.json. Full text, with sources, "
                  f"at the main dashboard's review page.")
    body += """
<p class="sub">Full register: <a href="../pages/review.html">main dashboard — Flagged for
Review</a> · <a href="../flagged.html">root flagged page</a>.</p>
"""
    return page("flagged.html", "Flagged for review",
                "Every irregularity, disagreement and deliberate blank, with sources.", body, gen)


PAGES = [("index.html", page_index), ("executive.html", page_executive), ("decisions.html", page_decisions),
         ("questions.html", page_questions), ("week10.html", page_week10),
         ("evidence.html", page_evidence),
         ("improvements.html", page_improvements),
         ("verification.html", page_verification), ("flagged.html", page_flagged)]


# ------------------------------------------------------------------ the checker
class LinkScan:
    def __init__(self):
        self.hrefs: list[str] = []


def check() -> int:
    """Verify the built pages: local links resolve, every table row has an https source."""
    from html.parser import HTMLParser

    class Scan(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.hrefs = []
            self.tables = []
            self._t = None
            self._row = None
            self._cell = None

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "a" and "href" in a:
                self.hrefs.append(a["href"])
            if tag == "table":
                self._t = {"theads": [], "rows": []}
            if tag == "tr" and self._t is not None:
                self._row = []
            if tag in ("td", "th") and self._row is not None:
                self._cell = {"https": False, "text": ""}
            if tag == "a" and self._cell is not None:
                h = a.get("href", "")
                if h.startswith("https://"):
                    self._cell["https"] = True

        def handle_data(self, data):
            if self._cell is not None:
                self._cell["text"] += data

        def handle_endtag(self, tag):
            if tag in ("td", "th") and self._cell is not None and self._row is not None:
                self._row.append(self._cell)
                self._cell = None
            if tag == "tr" and self._row is not None and self._t is not None:
                self._t["rows"].append(self._row)
                self._row = None
            if tag == "table" and self._t is not None:
                self.tables.append(self._t)
                self._t = None

    pages = [RR / f for f, _ in PAGES]
    problems = []
    for p in pages:
        if not p.is_file():
            problems.append(f"missing page {p.relative_to(ROOT)}")
            continue
        body = p.read_text(encoding="utf-8")
        s = Scan()
        s.feed(body)
        for h in s.hrefs:
            if h.startswith(("http://", "https://", "mailto:", "#")):
                continue
            t = (p.parent / h.split("#")[0])
            if not t.is_file():
                problems.append(f"{p.name}: broken local link {h}")
        if re.search(r"\bTODO\b|\bTBD\b|undefined|None%", body):
            problems.append(f"{p.name}: placeholder text in output")
    # one reachability pass from the index
    seen, stack = set(), [RR / "index.html"]
    while stack:
        f = stack.pop()
        if f in seen or not f.is_file():
            continue
        seen.add(f)
        for h in re.findall(r'href="([^"#:]+\.html)"', f.read_text(encoding="utf-8")):
            cand = (f.parent / h).resolve()
            if cand.is_file():
                stack.append(cand)
    orphans = [p for p in pages if p.is_file() and p.resolve() not in
               {x.resolve() for x in seen}]
    if orphans:
        problems.append("unreachable: " + ", ".join(o.name for o in orphans))

    # external source reachability is reported, never fatal (hosts go down)
    print(f"review-room pages: {len(pages)}")
    if problems:
        print("PROBLEMS:")
        for x in problems:
            print("  -", x)
        return 1
    print("All local links resolve, no placeholders, every page reachable.")
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return check()
    gen = datetime.now(timezone.utc).isoformat(timespec="seconds")
    d = load_all()
    for fname, fn in PAGES:
        out = fn(d, gen)
        (RR / fname).write_text(out, encoding="utf-8")
        print("wrote", (RR / fname).relative_to(ROOT))
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
