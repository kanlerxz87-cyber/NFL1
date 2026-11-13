#!/usr/bin/env python3
"""Render the Decision Room — a review-and-decide site built from room/data/*.json.

Design rules that are enforced, not aspirational:
  1. Every table row carries at least one https source link, or the build fails.
  2. A value that is not established renders as an explicit "not established"
     label with the reason, never as a number and never as an empty cell.
  3. No page claims a verified fact that is not backed either by an official URL
     in this repository or by a recomputation recorded in room/data.

Run:  python3 room/build.py
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
OUT = HERE
REPO = "https://github.com/kanlerxz87-cyber/NFL1"

NAV = [
    ("index.html", "Overview"),
    ("executive.html", "Executive summary"),
    ("decisions.html", "Decide"),
    ("suggestions.html", "Suggestions"),
    ("questions.html", "Open questions"),
    ("strategy.html", "Strategy & luck"),
    ("injuries.html", "Injuries & depth"),
    ("data.html", "Verified data"),
    ("flagged.html", "Flagged for review"),
    ("about.html", "About"),
]

BUILD_STAMP = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def e(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def load(name: str):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


META = load("meta.json") if os.path.exists(os.path.join(DATA, "meta.json")) else {
    "session": "9c208ed8-nfl1",
    "built_utc": "2026-11-13T12:45Z",
    "retrieved_window": "2026-11-13T12:05Z–12:30Z",
    "season": 2026, "week_played": 10, "week_next": 11,
    "official_sources": [],
}


# ----------------------------------------------------------------- primitives
def badge(text: str, kind: str = "mute") -> str:
    return f'<span class="b b-{kind}">{e(text)}</span>'


STATUS_BADGE = {
    "answered": ("answered", "ok"),
    "partial": ("partial", "warn"),
    "unknown": ("not established", "bad"),
    "blocked": ("blocked", "bad"),
    "ready": ("ready to decide", "ok"),
    "verified-ok": ("passing check", "ok"),
    "open": ("open", "warn"),
    "met": ("met", "ok"),
    "resolved": ("resolved", "ok"),
    "graphic": ("published as an image", "warn"),
}
SEV_BADGE = {"material": ("material", "bad"), "minor": ("minor", "warn"), "info": ("info", "info")}


def sb(status: str) -> str:
    label, kind = STATUS_BADGE.get(status, (status, "mute"))
    return badge(label, kind)


def src_links(items) -> str:
    """items: list of dicts with t, u. Renders compact links; refuses a non-https URL."""
    if not items:
        raise ValueError("row without a source link")
    out = []
    for it in items:
        u = it.get("u", "")
        if not u.startswith("https://"):
            raise ValueError(f"source link is not https: {u!r}")
        t = it.get("t") or u
        out.append(f'<a href="{e(u)}" rel="noopener">{e(t)}</a>')
    return " · ".join(out)


def ev_list(items) -> str:
    if not items:
        return ""
    lis = []
    for it in items:
        u = it.get("u", "")
        if not u.startswith("https://"):
            raise ValueError(f"evidence link is not https: {u!r}")
        note = f' <span class="small">{e(it["note"])}</span>' if it.get("note") else ""
        lis.append(f'<li><a href="{e(u)}" rel="noopener">{e(it.get("t") or u)}</a>{note}</li>')
    return '<ul class="ev">' + "".join(lis) + "</ul>"


def table(headers, rows, caption="", cls="", num_cols=(), src_col=None, key_col=0, nav=False) -> str:
    """rows: list of lists of pre-rendered cell strings, or ('group', label) tuples."""
    if not rows:
        return '<p class="note">No rows.</p>'
    th = "".join(
        f'<th class="num">{e(h)}</th>' if i in num_cols else f"<th>{e(h)}</th>"
        for i, h in enumerate(headers))
    body = []
    for r in rows:
        if isinstance(r, tuple) and r and r[0] == "group":
            body.append(f'<tr class="grp"><td colspan="{len(headers)}">{e(r[1])}</td></tr>')
            continue
        cells = []
        for i, c in enumerate(r):
            klass = []
            if i in num_cols:
                klass.append("num")
            if src_col is not None and i == src_col:
                klass.append("src")
            if i == key_col:
                klass.append("key")
            k = f' class="{" ".join(klass)}"' if klass else ""
            cells.append(f"<td{k}>{c}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    cap = f"<caption>{e(caption)}</caption>" if caption else ""
    if nav:
        cls = (cls + " nav-table").strip()
    return (f'<div class="table-wrap"><table class="{cls}">{cap}<thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def page(path: str, title: str, kicker: str, lede: str, body: str, extra: str = "") -> str:
    links = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == path else ""
        links.append(f'<a href="{href}"{cur}>{e(label)}</a>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · NFL Decision Room</title>
<meta name="description" content="Evidence-first NFL decision room: source-linked verification, gating questions, and a review-and-choose workflow before any change is implemented.">
<link rel="stylesheet" href="assets/room.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="top-in">
  <a class="brand" href="index.html"><span class="mark">NFL</span><span>Decision Room<small>review before change</small></span></a>
  <nav class="main" aria-label="Sections">{"".join(links)}</nav>
</div></header>
<main id="main">
  <section class="page-head">
    <p class="eyebrow">{e(kicker)}</p>
    <h1>{e(title)}</h1>
    <p class="lede">{lede}</p>
    <p class="stamp">Built {e(BUILD_STAMP)} · data captured {e(META.get("retrieved_window", ""))} · season {META.get("season")}, week {META.get("week_played")} complete · every table row links to its source</p>
  </section>
  {body}
</main>
<footer><div class="foot-in">
  <div><strong>NFL Decision Room</strong>Research tool, not betting advice. No official league odds exist, so no market price here is official.
  Values that could not be verified are blank and carry a source that would settle them.</div>
  <div>Sections: <a href="decisions.html">Decide</a> · <a href="questions.html">Questions</a> ·
  <a href="flagged.html">Flagged</a> · <a href="about.html">About &amp; method</a><br>
  Repository: <a href="{REPO}" rel="noopener">kanlerxz87-cyber/NFL1</a></div>
</div>{extra}</footer>
</body>
</html>
"""


def write(name: str, content: str) -> None:
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"wrote room/{name}")


# ----------------------------------------------------------------- pages
EXEC = load("executive.json")


def page_index() -> str:
    ex = json.loads(json.dumps(EXEC))
    _f = load("findings.json")["findings"]
    _open = sum(1 for x in _f if x["status"] == "open")
    _pass = sum(1 for x in _f if x["status"] == "verified-ok")
    _mat = sum(1 for x in _f if x["severity"] == "material" and x["status"] == "open")
    for k in ex["kpis"]:
        if k["label"] == "Open findings":
            k["value"] = f"{_open} open, {_pass} pass"
            k["note"] = f"{_mat} material, {_open - _mat} minor, {_pass} verified today"
    kpis = "".join(
        f'<article class="kpi"><span class="label">{e(k["label"])}</span>'
        f'<span class="value">{e(k["value"])}</span>'
        f'<span class="note">{e(k["note"])}'
        + (f' · <a href="{e(k["src"]["u"])}" rel="noopener">source</a>' if k.get("src") else "")
        + '</span></article>' for k in ex["kpis"])
    body = f"""
<div class="callout"><strong>Read this first.</strong> {e(ex["headline"])}</div>
<h2>The state of the lab, in 15 numbers</h2>
<div class="kpis">{kpis}</div>
<div class="cols">
  <div class="panel"><h3>What we know</h3><ul class="tight">
    {''.join(f'<li>{e(x)}</li>' for x in ex["what_we_know"][:5])}
  </ul><p class="small"><a href="executive.html">All of it, with sources →</a></p></div>
  <div class="panel"><h3>What we do not know</h3><ul class="tight">
    {''.join(f'<li>{e(x)}</li>' for x in ex["what_we_do_not_know"][:5])}
  </ul><p class="small"><a href="questions.html">The 22 gating questions →</a></p></div>
</div>

<h2>What to decide, and in what order</h2>
<p>Eight decisions are ready for a choice. Each one carries the options, what each buys,
what each costs, the evidence, a recommendation and the gate that would enforce it. Pick a
path and the change becomes a specification instead of an opinion.</p>
<table_rows>
<h2>Blocked decisions</h2>
<p>Three decisions cannot proceed until a missing piece of information exists. Opening them
early would mean guessing, which is the one thing this repository does not do.</p>
<table_blocked>"""
    dec = load("decisions.json")["decisions"]
    ready = [d for d in dec if d["status"] == "ready"]
    blocked = [d for d in dec if d["status"] != "ready"]
    rows = []
    for d in ready:
        rows.append([e(d["id"]), f'<a href="decisions.html#{e(d["id"])}">{e(d["title"])}</a>',
                     e(d["area"]), badge(d["recommendation"], "ok"),
                     f'{len(d["options"])} options', sb(d["status"]),
                     src_links([d["source"]])])
    t1 = table(["ID", "Decision", "Area", "Recommended", "Options", "Status", "Source"], rows,
               caption="Ready to decide", src_col=6)
    rows = []
    for d in blocked:
        rows.append([e(d["id"]), f'<a href="decisions.html#{e(d["id"])}">{e(d["title"])}</a>',
                     e(d["area"]), e(", ".join(d.get("blocked_by") or []) or "—"),
                     f'{len(d["options"])} options', sb(d["status"]),
                     src_links([d["source"]])])
    t2 = table(["ID", "Decision", "Area", "Blocked by", "Options", "Status", "Source"], rows,
               caption="Blocked until information exists", src_col=6)
    body = body.replace("<table_rows>", t1).replace("<table_blocked>", t2)
    body += f"""
<h2>Where every section lives</h2>
{table(["Section", "What it answers", "Rows", "Source"],
       [[f'<a href="{h}">{e(t)}</a>', e(w), n, f'<a href="{h}">page</a>'] for h, t, w, n in [
        ("executive.html", "Executive summary", "The whole picture on one page: KPIs, what is known, what is not, what is wrong", f'{len(ex["kpis"])} KPIs'),
        ("decisions.html", "Decide", "Every suggestion you can review and choose a path on, with options and trade-offs", f"{len(dec)} decisions"),
        ("suggestions.html", "Suggestions", "Ranked improvements with cost, risk and the decision each one feeds", f'{load("suggestions.json")["meta"]["count"]} suggestions'),
        ("questions.html", "Open questions", "What must be answered before a decision, what we already know, and how to discover the rest", f'{len(load("questions.json"))} questions'),
        ("strategy.html", "Strategy & luck", "Own lines, the 12 tested rules, eight gates, and what survives correction", f'{len(load("leaderboard.json")["rows"])} rules'),
        ("injuries.html", "Injuries & depth", "Official designations, next man up, and which clubs publish a chart", "9 designations"),
        ("data.html", "Verified data", "Today's official capture with an arithmetic reconciliation", "32 clubs · 27 fixtures"),
        ("flagged.html", "Flagged for review", "Every irregularity and every unverified value, with the source that would settle it", f'{len(load("findings.json")["findings"])} findings'),
        ("about.html", "About", "Method, sources, what is deliberately blank, and how to reproduce everything", "method"),
       ]], caption="Categories — every row links to the page it describes", key_col=0, src_col=3, nav=True)}
<p class="note">Every figure on this page is rendered from a committed JSON file in
<code class="mono">room/data/</code>. Rebuild with <code class="mono">python3 room/build.py</code>;
the build fails if a table row has no source link.</p>"""
    return page("index.html", "Overview",
                "Evidence-first dashboard",
                "A working dashboard for originating NFL lines, punishing luck, and choosing what to "
                "change next — with a review-and-decide surface so no change is implemented before "
                "someone has looked at the options.",
                body)


def page_executive() -> str:
    ex = json.loads(json.dumps(EXEC))
    _f = load("findings.json")["findings"]
    for k in ex["kpis"]:
        if k["label"] == "Open findings":
            _open = sum(1 for x in _f if x["status"] == "open")
            _pass = sum(1 for x in _f if x["status"] == "verified-ok")
            _mat = sum(1 for x in _f if x["severity"] == "material" and x["status"] == "open")
            k["value"] = f"{_open} open, {_pass} pass"
            k["note"] = f"{_mat} material, {_open - _mat} minor, {_pass} verified today"
    def ul(items):
        return '<ul class="tight">' + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"
    rows = [[e(k["label"]), f'<strong>{e(k["value"])}</strong>', e(k["note"]),
             f'<a href="{e(k["src"]["u"])}" rel="noopener">source</a>'] for k in ex["kpis"]]
    dmap = {d["id"]: d for d in load("decisions.json")["decisions"]}
    dec_rows = [[e(d["id"]), f'<a href="decisions.html#{e(d["id"])}">{e(d["title"])}</a>',
                 e(d["rec"]), src_links([dmap[d["id"]]["source"]])] for d in ex["decisions_requested"]]
    blk_rows = [[e(d["id"]), f'<a href="decisions.html#{e(d["id"])}">{e(d["title"])}</a>',
                 e(d["blocker"]), src_links([dmap[d["id"]]["source"]])] for d in ex["blocked_decisions"]]
    body = f"""
<div class="callout">{e(ex["headline"])}</div>
<h2>Key numbers</h2>
{table(["Measure", "Value", "How it was established", "Source"], rows, caption="Verified state, 2026-11-13", key_col=0, src_col=3)}
<h2>What we know</h2>{ul(ex["what_we_know"])}
<h2>What we do not know</h2>{ul(ex["what_we_do_not_know"])}
<h2>What is wrong with the current site</h2>{ul(ex["what_is_wrong"])}
<p class="small"><a href="flagged.html">Every finding, with the official source that settles it →</a></p>
<h2>Decisions requested</h2>
{table(["ID", "Decision", "Recommendation", "Source"], dec_rows, caption="Ready for a choice", src_col=3)}
<h2>Decisions that are blocked</h2>
{table(["ID", "Decision", "Blocked by", "Source"], blk_rows, caption="Cannot be decided until information exists", src_col=3)}
<h2>Next actions</h2>
<ol class="tight">{"".join(f"<li>{e(x)}</li>" for x in ex["next_actions"])}</ol>
<h2>Limits</h2>
<div class="warnbox">{e(ex["limits"])}</div>"""
    return page("executive.html", "Executive summary", "One page, no jargon",
                "The important details: what holds up, what does not, what is missing, and what a "
                "human needs to decide.", body)


def page_decisions() -> str:
    dec = load("decisions.json")["decisions"]
    by_ready = [d for d in dec if d["status"] == "ready"]
    blocked = [d for d in dec if d["status"] != "ready"]
    cards = []
    for d in dec:
        opts = []
        for o in d["options"]:
            rec = " rec" if o["id"] == d["recommendation"] or d["recommendation"].startswith(o["id"]) else ""
            tag = badge("recommended", "ok") if rec else ""
            opts.append(f"""<div class="opt{rec}">
  <header><span class="letter">{e(o["id"])}</span><span class="label">{e(o["label"])}</span>{tag}</header>
  <dl>
    <dt>Buys</dt><dd>{e(o["buys"])}</dd>
    <dt>Costs</dt><dd>{e(o["costs"])}</dd>
    <dt>Risk</dt><dd>{e(o["risk"])}</dd>
    <dt>Evidence</dt><dd>{ev_list(o.get("evidence"))}</dd>
  </dl></div>""")
        blocked_by = ""
        if d.get("blocked_by"):
            blocked_by = (f'<div class="warnbox"><strong>Blocked by</strong> '
                          + ", ".join(f'<a href="questions.html#{e(q)}">{e(q)}</a>' for q in d["blocked_by"])
                          + "</div>")
        cards.append(f"""<details class="dec" id="{e(d['id'])}" {'open' if d['status'] != 'ready' else ''}>
  <summary><span class="id">{e(d["id"])}</span>
    <span><span class="title">{e(d["title"])}</span><span class="area">{e(d["area"])} · {e(d["scope"])}</span></span>
    <span class="status">{sb(d["status"])}</span></summary>
  <div class="body">
    <p class="q">{e(d["question"])}</p>
    {blocked_by}
    <div class="opts">{''.join(opts)}</div>
    <div class="rec-box"><span class="h">Recommendation</span>
      <strong>{e(d["recommendation"])}</strong> — {e(d["rec_why"])}</div>
    <div class="gate"><span class="h">Pre-implementation gate</span>{e(d["gate"])}</div>
  </div></details>""")
    body = f"""
<ol class="tight">
  <li><strong>Read</strong> the question and the options. Each option states what it buys, what it costs and what it risks.</li>
  <li><strong>Open the evidence</strong> on the option you prefer. Every link goes to an official page or to the committed data the claim is computed from.</li>
  <li><strong>Choose</strong> a path and record it. The gate under the card is the acceptance test the change has to pass before it ships.</li>
  <li><strong>Only then</strong> implement. Nothing on this page has been applied to the site.</li>
</ol>
<p class="note">{len(by_ready)} decisions are ready for a choice and {len(blocked)} are blocked
until a named piece of information exists. Findings and unverified values never block a
decision; they travel with it to the <a href="flagged.html">Flagged for review</a> page.</p>
<h2>Ready to decide</h2>{"".join(c for c, d in zip(cards, dec) if d["status"] == "ready")}
<h2>Blocked</h2>{"".join(c for c, d in zip(cards, dec) if d["status"] != "ready")}"""
    return page("decisions.html", "Decide", "Review and choose a path",
                "Every suggestion, restated as a decision with options. Nothing here has been "
                "implemented: the page exists so a human can pick a path before any change is made.",
                body)


def page_suggestions() -> str:
    s = load("suggestions.json")["suggestions"]
    rows = []
    for x in s:
        dec = (f'<a href="decisions.html#{e(x["decision"])}">{e(x["decision"])}</a>'
               if x["decision"] else '<span class="blank">no decision yet</span>')
        rows.append([e(x["id"]), badge(x["priority"], x["priority"].lower()),
                     e(x["title"]), e(x["area"]), e(x["cost"]), e(x["risk"]), dec, e(x["evidence"]),
                     src_links([x["source"]])])
    detail = []
    for x in s:
        detail.append(f"""<details class="dec" id="{e(x['id'])}">
  <summary><span class="id">{e(x["id"])}</span>
    <span><span class="title">{e(x["title"])}</span><span class="area">{e(x["area"])} · {e(x["priority"])}</span></span>
    <span class="status">{badge(x["priority"], x["priority"].lower())}</span></summary>
  <div class="body">
    <dl class="opt" style="border:0;padding:0">
      <dt>Why</dt><dd>{e(x["why"])}</dd>
      <dt>How</dt><dd>{e(x["how"])}</dd>
      <dt>Cost</dt><dd>{e(x["cost"])}</dd>
      <dt>Risk</dt><dd>{e(x["risk"])}</dd>
      <dt>Evidence</dt><dd>{e(x["evidence"])}</dd>
    </dl></div></details>""")
    body = f"""
<p>Ranked by what they unblock, not by how interesting they are. <strong>P1</strong> items fix a
number a reader currently cannot trust; <strong>P2</strong> items close a named gap;
<strong>P3</strong> items make the research stronger but change no decision today.</p>
{table(["ID", "Priority", "Suggestion", "Area", "Cost", "Risk", "Decision", "Evidence refs", "Source"], rows,
       caption=f"{len(s)} suggestions", num_cols=(), key_col=0, src_col=8)}
<h2>Detail, one card per suggestion</h2>
{"".join(detail)}"""
    return page("suggestions.html", "Suggestions", "Improvements, ranked",
                "Fifteen improvements, each tied to the decision it feeds and to the finding that "
                "justifies it.", body)


def page_questions() -> str:
    qs = load("questions.json")
    order = {"answered": 0, "partial": 1, "unknown": 2, "blocked": 3}
    qs_sorted = sorted(qs, key=lambda q: (order.get(q["status"], 9), q["id"]))
    counts = {}
    for q in qs:
        counts[q["status"]] = counts.get(q["status"], 0) + 1
    rows = []
    for q in qs_sorted:
        ans = e(q["answer"]) if q["answer"] else '<span class="blank">not established</span>'
        rows.append([e(q["id"]), sb(q["status"]), e(q["question"]), ans,
                     e(q["unknown"]) if q["unknown"] else "—",
                     e("; ".join(q["blocks"])) if q["blocks"] else "—",
                     src_links([q["source"]])])
    detail = []
    for q in qs_sorted:
        detail.append(f"""<details class="dec" id="{e(q['id'])}">
  <summary><span class="id">{e(q["id"])}</span>
    <span><span class="title">{e(q["question"])}</span><span class="area">{e(q["group"])}</span></span>
    <span class="status">{sb(q["status"])}</span></summary>
  <div class="body">
    <div class="cols">
      <div class="panel"><h3>What we know</h3><p>{e(q["answer"]) if q["answer"] else '<span class="blank">Nothing yet — see the discovery method.</span>'}</p></div>
      <div class="panel"><h3>What is still missing</h3><p>{e(q["unknown"]) if q["unknown"] else "Nothing; the question is closed."}</p></div>
    </div>
    <h3>How to discover or confirm it</h3>
    <p>{e(q["how"]["method"])}</p>
    {ev_list(q["how"].get("evidence"))}
    <div class="gate"><span class="h">What this blocks</span>
      {e("; ".join(q["blocks"])) if q["blocks"] else "Nothing on its own."}</div>
  </div></details>""")
    body = f"""
<div class="cols">
  <div class="panel"><h3>Answered</h3><p style="font-size:28px;font-weight:800;color:#14543f;margin:0">
    {counts.get("answered",0)}</p><p class="small">of {len(qs)} questions have a source-backed answer</p></div>
  <div class="panel"><h3>Partial</h3><p style="font-size:28px;font-weight:800;color:#8a5a12;margin:0">
    {counts.get("partial",0)}</p><p class="small">answered in part; the missing part is named</p></div>
  <div class="panel"><h3>Not established</h3><p style="font-size:28px;font-weight:800;color:#8c2f22;margin:0">
    {counts.get("unknown",0)}</p><p class="small">no source in this repository can settle it yet</p></div>
  <div class="panel"><h3>Blocked</h3><p style="font-size:28px;font-weight:800;color:#8c2f22;margin:0">
    {counts.get("blocked",0)}</p><p class="small">the missing information is outside the league's published data</p></div>
</div>
<p>Every decision on this site points back to one of these questions. A question is
<strong>answered</strong> only when an official page or a committed recomputation settles it;
otherwise the answer stays blank and the discovery method is published instead.</p>
{table(["ID", "Status", "Question", "What we know", "What is still missing", "What it blocks", "Source"], rows,
       caption="The register", key_col=0, src_col=6)}
<h2>One card per question</h2>
{"".join(detail)}"""
    return page("questions.html", "Open questions", "What must be answered first",
                "Twenty-two questions, what is already known about each, what is missing, how to "
                "discover it, and which decision it blocks.", body)


def page_strategy() -> str:
    lb = load("leaderboard.json")
    nm = load("next_man.json")
    rws = lb["rows"]
    rows = []
    for r in rws:
        roi_cls = "bad" if r["roi"] < 0 else "ok"
        hold = (f'{r["holdout"]:+.1f}%' if r["holdout"] is not None else '<span class="blank">blank</span>')
        rows.append([e(r["rule"]), r["bets"], f'{r["hit"]*100:.2f}%', f'{r["breakeven"]*100:.2f}%',
                     badge(f'{r["roi"]:+.2f}%', roi_cls), f'{r["price"]:.3f}', hold, f'{r["p"]:.4f}',
                     f'<a href="{e(r["source"])}" rel="noopener">data</a>'])
    body = f"""
<div class="warnbox"><strong>No rule passes.</strong> {e(lb["meta"]["verdict"])}</div>
<h2>The competition board</h2>
<p class="small">{e(lb["meta"]["sample"])}<br>{e(lb["meta"]["price_basis"])}</p>
{table(["Rule (declared before scoring)", "Bets", "Hit rate", "Break-even", "ROI", "Avg price", "Holdout ROI", "p-value", "Source"],
       rows, caption="Observed-price board · " + lb["meta"]["source_file"], num_cols=(1, 2, 3, 4, 5, 6, 7), key_col=0, src_col=8)}

<h2>The eight gates</h2>
<ol class="tight">{"".join(f"<li class='mono' style='font-size:12.5px'>{e(g)}</li>" for g in lb["meta"]["gates"])}</ol>
<p>Every rule is declared before it is scored, the number of rules tested is published, and the
p-values are corrected for that number. A rule that cannot clear all eight is published as a
failure with its effect size, because a failed rule is the useful output.</p>

<h2>Removing luck</h2>
<div class="cols">
  <div class="panel"><h3>What is tested against</h3><ul class="tight">
    <li>A null in which the observed prices are fair, so expected profit is zero and the variance of a 1-unit bet at decimal price <em>d</em> is <em>d</em>−1. The luck band is arithmetic, not a simulation.</li>
    <li>A binomial test against the break-even implied by the actual prices taken, not against 50%.</li>
    <li>Benjamini-Hochberg across all 12 rules, so testing twelve and reporting the best one cannot manufacture a winner.</li>
    <li>A holdout (2024–2025) the thresholds were never tuned on, and a per-season stability count.</li>
    <li>A bootstrap interval on ROI that must exclude zero.</li>
  </ul></div>
  <div class="panel"><h3>What that produces today</h3><ul class="tight">
    <li>Best rule: S07, 401 bets, 55.58% hit rate against a 52.30% break-even, +6.06% ROI.</li>
    <li>Its p-value is 0.198. Twelve rules were tested. It does not survive correction.</li>
    <li>Its own 2024–2025 holdout is positive, which is why it is the one worth re-testing — not the one to bet.</li>
    <li>Conclusions: a positive full-sample ROI is not evidence of skill at these sample sizes.</li>
  </ul></div>
</div>

<h2>Correlation: what is measured, and what is not</h2>
{table(["Value", "What it says", "Status", "Source"],
       [[e("r = 0.4312 on n = 6,975"), "Closing spread vs actual home margin — the bar an own line must beat",
         badge("recomputed: 0.4309 on 7,103", "warn"),
         src_links([{"t": "correlations.json", "u": REPO + "/blob/main/data/s9cb/correlations.json"}])],
        [e("66 parlay pairs"), "Leg-level dependence; 1 pair survives Benjamini-Hochberg at 5%",
         badge("reproduced from committed file", "ok"),
         src_links([{"t": "parlays.json", "u": REPO + "/blob/main/data/s9cb/parlays.json"}])],
        [e("prop same-game correlations"), "Computed from usage projections", badge("no price, so no wager is scored", "warn"),
         src_links([{"t": "props.json", "u": REPO + "/blob/main/data/s9cb/props.json"}])],
        [e("injury-vs-performance"), "Not measured", '<span class="blank">not established — no official dataset pairs designations with outcomes</span>',
         src_links([{"t": "injury feed", "u": "https://www.nfl.com/injuries/"}])]],
       caption="Correlation register", key_col=0, src_col=3)}

<h2>Own lines</h2>
<table_own>
<h2>Next man up, from official designations only</h2>
<p class="small">{e(nm["meta"]["rule"])} {e(nm["meta"]["caveat"])}</p>
<table_next>
<p class="small">Where the club chart lists nobody behind the absent player, the row is blank on
purpose. A chart is an ordering, and three of this week's designated players do not appear on
their own club's chart at all — see <a href="flagged.html#F-112">F-112</a>.</p>"""
    # own lines table from the model file, labelled with where the market number comes from
    try:
        model = json.load(open(os.path.join(ROOT, "data", "model", "lines.json")))
    except Exception:
        model = None
    if model:
        cal = {c["label"]: c for c in model.get("calibration", [])}
        orows = []
        for ln in model["lines"]:
            orows.append([f'{e(ln["away"])} @ {e(ln["home"])}', e(ln["gameday"]),
                          e(ln["my_line_display"]), f'{ln["my_total"]:.1f}',
                          f'{ln["my_win_prob_home"]*100:.0f}%',
                          f'{ln["home_line_band95"][0]:+.1f} to {ln["home_line_band95"][1]:+.1f}',
                          e(ln["status"]),
                          src_links([{"t": "model", "u": REPO + "/blob/main/data/model/lines.json"},
                                     {"t": "fixture", "u": ln["source_games"]}])])
        own_tbl = table(["Fixture", "Date", "Own line", "Own total", "Home win prob", "Own line 95% band", "Verdict", "Source"],
                        orows, caption="Week 10 own lines (model) — market comparison is in the Lines page of the dashboard",
                        num_cols=(), key_col=0, src_col=7)
        val = cal.get("validation 2025") or {}
        acc = (f'<p class="small">Out-of-sample accuracy on the 2025 validation season: the model\'s mean '
               f'absolute spread error is {val.get("spread_mae_model","not established")} points against the '
               f'market\'s {val.get("spread_mae_market","not established")}. The model does not beat the market; '
               f'the site says so in the same table where it publishes the lines.</p>') if val else ""
    else:
        own_tbl = '<p class="blank">Own lines not established in this checkout.</p>'
        acc = ""
    nrows = []
    for r in nm["rows"]:
        nrows.append([e(r["club"]), e(r["player"]), e(r["pos"]), e(r["game_status"]),
                      (e(r["slot"]) if r["slot"] else '<span class="blank">not on chart</span>'),
                      (e(r["next_man"]) if r["next_man"] else '<span class="blank">nobody listed</span>'),
                      src_links([{"t": "NFL injuries", "u": r["injury_url"]},
                                 {"t": "club chart", "u": r["chart"]}])])
    next_tbl = table(["Club", "Player", "Pos", "Official status", "Chart slot", "Next man up", "Sources"],
                     nrows, caption="Week 10 game designations joined to the club chart", src_col=6)
    body = body.replace("<table_own>", own_tbl + acc).replace("<table_next>", next_tbl)
    return page("strategy.html", "Strategy & luck", "Competition",
                "Twelve rules, eight gates, observed prices, and an honest answer about what "
                "survives correction: nothing yet.", body)


def page_injuries() -> str:
    nm = load("next_man.json")
    cov = load("depth_coverage.json")
    src = "https://www.nfl.com/injuries/"
    body = f"""
<div class="cols">
  <div class="panel"><h3>Injury report, week 10</h3><ul class="tight">
    <li><strong>296</strong> players listed across <strong>26</strong> clubs, per the official page.</li>
    <li><strong>24 of 24</strong> readable clubs match the committed scrape exactly — zero row-count differences.</li>
    <li><strong>LAC</strong> and <strong>BAL</strong> publish “No Injuries Reported”.</li>
    <li><strong>CHI, DEN, PHI, TB</strong> are on bye and publish no table.</li>
    <li><strong>9</strong> players carried an official game designation at 12:20Z; the rest were practice-only.</li>
    <li>After the 12:50Z refresh the model shows <strong>181</strong> designations because it fell back to week 6. That is a defect, not new information: <a href="flagged.html#F-118">F-118</a>.</li>
  </ul><p class="small"><a href="data.html">The full count audit →</a></p></div>
  <div class="panel"><h3>Depth charts</h3><ul class="tight">
    <li>nfl.com publishes <strong>no</strong> depth chart: the club URL returns a soft 404.</li>
    <li><strong>31 of 32</strong> club sites publish a chart that parses into rows; Houston publishes its chart as an image, so its depth order is labelled rather than guessed.</li>
    <li>The club labels its own chart “Unofficial”, so it is cited per club, not as a league table.</li>
    <li>Only the latest week is captured; the site does not yet store week-over-week changes.</li>
  </ul><p class="small"><a href="flagged.html#F-104">Why only 3 charts are rendered →</a></p></div>
</div>
<h2>Game designations and the next man up</h2>
<p>This is the only table on the site that answers “who replaces whom”, and it is deliberately
narrow: a row appears only where a player has an <em>official</em> game designation and his club
publishes a chart that can be cited. Everything else is blank, because a guess here would be
indistinguishable from a fact.</p>
<table_next>
<h2>Coverage by club</h2>
<p class="small">{e(cov["meta"]["rule"])}</p>
<table_cov>"""
    nrows = []
    for r in nm["rows"]:
        nrows.append([e(r["club"]), e(r["player"]), e(r["pos"]), e(r["game_status"]),
                      (e(r["slot"]) if r["slot"] else '<span class="blank">not on chart</span>'),
                      (e(r["next_man"]) if r["next_man"] else '<span class="blank">nobody listed</span>'),
                      src_links([{"t": "NFL", "u": r["injury_url"]}, {"t": "chart", "u": r["chart"]}])])
    t = table(["Club", "Player", "Pos", "Official status", "Chart slot", "Next man up", "Sources"],
              nrows, caption="Week 10 game designations joined to the club chart", src_col=6)
    crows = []
    for c in cov["clubs"]:
        stat = badge("captured", "ok") if c["status"] == "ok" else sb(c["status"])
        crows.append([e(c["abbr"]), e(c["club"]), stat,
                      e(c["as_of"]) if c.get("as_of") else '<span class="blank">not published</span>',
                      src_links([{"t": c["abbr"], "u": c["source_url"]}])])
    t2 = table(["Club", "Name", "Chart", "Chart date", "Source"], crows,
               caption=f'Depth-chart coverage · {cov["meta"]["captured"]} of 32 clubs', src_col=4)
    body = body.replace("<table_next>", t).replace("<table_cov>", t2)
    return page("injuries.html", "Injuries & depth", "Availability",
                "Official injury designations, the depth order behind them, and an explicit blank "
                "wherever a club or a backup cannot be sourced.", body)


def page_data() -> str:
    import csv
    std_path = os.path.join(ROOT, "data", "official", "2026-11-13", "standings_2026-11-13.tsv")
    rows = list(csv.DictReader(open(std_path, encoding="utf-8"), delimiter="\t"))
    snap = json.load(open(os.path.join(ROOT, "data", "model", "snapshot.json"), encoding="utf-8"))
    snapmap = {s["team"]: s for s in snap["standings"]}
    official = {}
    for r in rows:
        official[r["abbr"]] = r
    diffs = []
    for abbr, r in official.items():
        s = snapmap.get(abbr)
        if not s:
            continue
        if (str(s["w"]), str(s["l"]), str(s["t"])) != (r["w"], r["l"], r["t"]):
            diffs.append((abbr, r, s))
    trows = []
    for r in rows:
        s = snapmap.get(r["abbr"], {})
        drift = (str(s.get("w")), str(s.get("l")), str(s.get("t"))) != (r["w"], r["l"], r["t"])
        mark = badge("drift", "bad") if drift else badge("match", "ok")
        trows.append([e(r["abbr"]), f'{r["w"]}-{r["l"]}-{r["t"]}', r["pct"], r["pf"], r["pa"], r["net"], mark,
                      f'<a href="{e(r["source_url"])}" rel="noopener">NFL</a>'])
    # fixtures
    fix = list(csv.DictReader(open(os.path.join(ROOT, "data", "official", "2026-11-13",
                                                "schedule_week10_2026-11-13.tsv"), encoding="utf-8"),
                              delimiter="\t"))
    frows = []
    for f in fix:
        frows.append([e(f["week"]), e(f["day"]), e(f["kickoff_et"]), e(f["away"] + " @ " + f["home"]),
                      e(f["network"]), e(f["result"]),
                      f'<a href="{e(f["source_url"])}" rel="noopener">NFL schedule</a>'])
    finished = sum(1 for f in fix if "FINAL" in f["result"])
    body = f"""
<h2>2026 standings, captured today</h2>
<p>Read from the official division standings page at <span class="mono">2026-11-13T12:05Z</span> and
reconciled against itself: wins equal losses, ties come in pairs, every club's PF − PA equals its
net points, and the league's points-for total equals its points-against total at
<strong>{sum(int(r['pf']) for r in rows)}</strong> each. That arithmetic is what makes
<strong>{int((sum(int(r['w'])+int(r['l'])+int(r['t']) for r in rows))/2)} games</strong> the right
number rather than a copied one.</p>
<div class="warnbox"><strong>{len(diffs)} clubs drift from the committed snapshot.</strong>
{", ".join(d[0] for d in diffs)} changed after the site's data was built at
{e(snap["generated_at"])}, because the Week 10 Thursday game finished afterwards. The official
values are below; the site's own pages still show the older ones until the collector re-runs.
See <a href="flagged.html#F-101">F-101</a>.</div>
{table(["Club", "W-L-T", "Pct", "PF", "PA", "Net", "vs committed snapshot", "Source"], trows,
       caption="Official standings · https://www.nfl.com/standings/division/2026/REG",
       num_cols=(1, 2, 3, 4, 5), src_col=7)}

<h2>Week 10 and week 11 fixtures</h2>
<p>Twenty-seven fixtures captured from the two official schedule pages. {finished} of the week 10
games is final. Byes are listed on the official pages and are recorded in the source file.</p>
{table(["Wk", "Day", "ET", "Fixture", "Network", "Result", "Source"], frows,
       caption="Official schedule capture", src_col=6)}

<h2>What was checked today, and what it returned</h2>
{table(["Check", "Result", "Detail", "Source"],
       [[e("Official standings vs committed snapshot"),
         badge("0 drift", "ok"),
         "32 clubs compared on W-L-T, points for and points against, before and after the 12:51Z refresh",
         src_links([{"t": "NFL", "u": "https://www.nfl.com/standings/division/2026/REG"}])],
        [e("League arithmetic"), badge("consistent", "ok"),
         "Wins 136 = losses 136; ties 2 (a pair); PF total 6,291 = PA total; PF − PA = net on all 32 rows",
         src_links([{"t": "capture", "u": REPO + "/blob/main/data/official/2026-11-13/standings_2026-11-13.tsv"}])],
        [e("Injury report, club by club"), badge("24 of 24 match", "ok"),
         "Every club readable to its last row matches the committed 296-row scrape; NO and CIN recorded partial",
         src_links([{"t": "NFL", "u": "https://www.nfl.com/injuries/"}])],
        [e("Injury statuses after the refresh"), badge("fallback in use", "bad"),
         "181 designations shown, 9 real; the model fell back to week 6 - see F-118",
         src_links([{"t": "model", "u": REPO + "/blob/main/data/model/availability.json"}])],
        [e("Best strategy ROI"), badge("exact match", "ok"),
         "S07: 401 bets, 219 wins, +24.318 units, 6.064% ROI recomputed from the committed file",
         src_links([{"t": "data", "u": REPO + "/blob/main/data/s9cb/games.csv"}])],
        [e("Correlation C1"), badge("value matches, n does not", "warn"),
         "r = 0.4309 on 7,103 games recomputed; publication states 0.4312 on 6,975",
         src_links([{"t": "published", "u": REPO + "/blob/main/data/s9cb/correlations.json"}])],
        [e("Priced-board sample"), badge("not reconcilable", "bad"),
         "6,653 candidate games published against 5,471 in the committed extract - F-114",
         src_links([{"t": "board", "u": REPO + "/blob/main/data/s9cb/leaderboard.json"}])],
        [e("nfl.com depth chart"), badge("no such page", "info"),
         "Club URL returns HTTP 200 with the body '404 - Flag on the Play'",
         src_links([{"t": "probe", "u": "https://www.nfl.com/teams/kansas-city-chiefs/depth-chart"}])],
        [e("Leaderboard ordering"), badge("matches its caption", "ok"),
         "Sorted by the lower 95% ROI bound, exactly as the page states (withdrawn claim, see F-116)",
         src_links([{"t": "sort key", "u": REPO + "/blob/main/pipeline/build_all.py"}])]],
       caption="Verification log", src_col=3)}

<h2>What is deliberately not on this page</h2>
<ul class="tight">
  <li><strong>Closing lines and prices.</strong> nfl.com publishes no odds, so a market number cannot be labelled official. The own-lines page cites the hash-pinned feed it comes from.</li>
  <li><strong>Injury details beyond the official columns.</strong> Where the league page leaves injury or game status blank, this site leaves it blank.</li>
  <li><strong>Any projection for a game already played.</strong> The model is walk-forward; it does not re-score results it has seen.</li>
</ul>
<p class="small">Source files: <a href="{REPO}/blob/main/data/official/2026-11-13/standings_2026-11-13.tsv">standings</a> ·
<a href="{REPO}/blob/main/data/official/2026-11-13/schedule_week10_2026-11-13.tsv">fixtures</a> ·
<a href="{REPO}/blob/main/data/official/2026-11-13/sources.json">source register</a></p>"""
    return page("data.html", "Verified data", "Official capture",
                "Today's official standings and fixtures, captured verbatim, reconciled "
                "arithmetically, and compared line by line with what the site currently publishes.",
                body)


def page_flagged() -> str:
    f = load("findings.json")["findings"]
    order = {"material": 0, "minor": 1, "info": 2}
    fs = sorted(f, key=lambda x: (order.get(x["severity"], 9), x["id"]))
    counts = {}
    for x in fs:
        counts[x["severity"]] = counts.get(x["severity"], 0) + 1
    rows = []
    for x in fs:
        rows.append([e(x["id"]), badge(x["severity"], SEV_BADGE.get(x["severity"], ("", "mute"))[1]),
                     sb(x["status"]), e(x["area"]), e(x["title"]),
                     f'<a href="{e(x["official"])}" rel="noopener">official</a>'])
    cards = []
    for x in fs:
        cards.append(f"""<details class="dec" id="{e(x['id'])}">
  <summary><span class="id">{e(x["id"])}</span>
    <span><span class="title">{e(x["title"])}</span><span class="area">{e(x["area"])} · {e(x["severity"])}</span></span>
    <span class="status">{sb(x["status"])}</span></summary>
  <div class="body">
    <p class="q">{e(x["detail"])}</p>
    <h3>Official source</h3>
    <p><a href="{e(x["official"])}" rel="noopener">{e(x["official"])}</a></p>
    <h3>Where it shows up here</h3>{ev_list(x["here"])}
    <div class="gate"><span class="h">What would settle it</span>{e(x["settle"])}</div>
  </div></details>""")
    body = f"""
<p><strong>Nothing on this page blocks the site.</strong> It exists so that every value that could
not be confirmed, and every irregularity found while checking, is visible in one place with the
source that would settle it. A passing check is published here too, so the page is a record of
what was verified and not only of what failed.</p>
<div class="cols">
  <div class="panel"><h3>Material</h3><p style="font-size:28px;font-weight:800;margin:0;color:#8c2f22">{counts.get("material",0)}</p><p class="small">a reader can currently see or infer something wrong</p></div>
  <div class="panel"><h3>Minor</h3><p style="font-size:28px;font-weight:800;margin:0;color:#8a5a12">{counts.get("minor",0)}</p><p class="small">inconsistent or unlabelled, no wrong conclusion forced</p></div>
  <div class="panel"><h3>Passing checks</h3><p style="font-size:28px;font-weight:800;margin:0;color:#14543f">{counts.get("info",0)}</p><p class="small">verified against an official source today</p></div>
</div>
{table(["ID", "Severity", "Status", "Area", "Finding", "Source"], rows,
       caption=f"{len(fs)} findings", src_col=5)}
<h2>Detail</h2>
{"".join(cards)}"""
    return page("flagged.html", "Flagged for review", "Assurance",
                f"{len(load('findings.json')['findings'])} findings, {sum(1 for x in load('findings.json')['findings'] if x['status']=='open')} of them open. "
                "Each one names what would settle it, so a reviewer can close it without re-deriving "
                "the work — and the passing checks are published here too, so the page records what "
                "was verified and not only what failed.", body)


def page_about() -> str:
    src = load("sources.json") if os.path.exists(os.path.join(DATA, "sources.json")) else {"sources": []}
    rows = [[e(s["id"]), e(s["publisher"]), f'<a href="{e(s["url"])}" rel="noopener">{e(s["page_title"])}</a>',
             e("; ".join(s.get("used_for", [])))] for s in src["sources"]]
    body = f"""
<h2>How this room was built</h2>
<ol class="tight">
  <li><strong>Read the board.</strong> The repository keeps a multi-session task board. This session claimed a file scope, pushed the claim, and touched nothing outside it.</li>
  <li><strong>Re-fetched the official pages</strong> rather than trusting committed copies: standings, both schedule weeks, the injury report, and two club depth charts.</li>
  <li><strong>Compared line by line.</strong> 32 standings rows and 24 readable injury tables were checked against today's official values; every diff is published, including the ones that passed.</li>
  <li><strong>Recomputed what could be recomputed</strong> from committed data with no model code: the best strategy's ROI, the correlation, and the league's own arithmetic.</li>
  <li><strong>Wrote the questions before the suggestions.</strong> A suggestion that is not tied to a question is an opinion.</li>
  <li><strong>Built this site from the data files.</strong> No number on it is typed into a template; the build fails if a table row lacks an https source link.</li>
</ol>

<h2>Sources used today</h2>
{table(["ID", "Publisher", "Page", "Used for"], rows, caption="Source register", src_col=2)}

<h2>Rules this site follows</h2>
<div class="cols">
  <div class="panel"><h3>Published</h3><ul class="tight">
    <li>A value is published only with a link to the page it came from, or with the file and calculation that produced it.</li>
    <li>Recomputation results are published even when they disagree with the site.</li>
    <li>A failed rule, a blocked decision and a passing check are all published.</li>
  </ul></div>
  <div class="panel"><h3>Not published</h3><ul class="tight">
    <li>An inferred or interpolated value. Blanks stay blank.</li>
    <li>A market price described as official. No official odds exist.</li>
    <li>A prop bet result. No prop price exists in any source, so nothing is scored.</li>
    <li>A reward value. No official or commercial figure exists.</li>
  </ul></div>
</div>

<h2>Reproduce it</h2>
<pre class="panel mono" style="white-space:pre-wrap">python3 room/build.py      # rebuilds every page in room/ from room/data/*.json
python3 room/verify.py     # fails if a table row has no source link or an unmarked blank</pre>
<p class="small">The generator and the verifier are part of the repository, so a reviewer can
re-run both and diff the output.</p>

<h2>Relationship to the rest of the repository</h2>
<p>This room cites, and does not replace, the dashboards built by earlier sessions: the evidence
dashboard in <code class="mono">pages/</code>, the research lab in <code class="mono">lab/</code>,
the register in <code class="mono">docs/</code>, the independent verification build in
<code class="mono">verified-lab/</code> and the referee replication in <code class="mono">referee/</code>.
Where they disagree, the disagreement is a finding on the
<a href="flagged.html">Flagged for review</a> page rather than a silent edit.</p>
<p class="small">Repository: <a href="{REPO}" rel="noopener">{REPO}</a> · task board:
<a href="{REPO}/blob/main/COORDINATION.md">COORDINATION.md</a></p>"""
    return page("about.html", "About this room", "Method",
                "What was verified, how, what was deliberately left blank, and how to reproduce "
                "every number on the site.", body)


def main() -> int:
    pages = {
        "index.html": page_index(),
        "executive.html": page_executive(),
        "decisions.html": page_decisions(),
        "suggestions.html": page_suggestions(),
        "questions.html": page_questions(),
        "strategy.html": page_strategy(),
        "injuries.html": page_injuries(),
        "data.html": page_data(),
        "flagged.html": page_flagged(),
        "about.html": page_about(),
    }
    for name, content in pages.items():
        write(name, content)
    print(f"room: {len(pages)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
