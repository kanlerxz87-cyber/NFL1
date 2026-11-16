#!/usr/bin/env python3
"""Render the Reward Board — a pre-registered, non-monetary badge site.

Built from data/rewards/*.json. Design rules that are enforced, not aspirational:

  1. Every table row carries at least one https source link, or the build fails.
  2. A value that is not established renders as an explicit "not established" /
     "not awarded" label with the reason, never as a number and never as an empty cell.
  3. No backtest performance number (ROI, win rate, hit rate, profit, rank) is printed
     on this board. The board publishes the frozen rule, the thresholds and a
     qualification status — never a backtest result.
  4. The build stamp is derived from the registration commit and the rule fingerprint,
     never from the wall clock, so a rebuild is byte-identical (CI fails on drift).

Run:  python3 rewards/build.py
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "rewards")
OUT = HERE
REPO = "https://github.com/kanlerxz87-cyber/NFL1"

NAV = [
    ("index.html", "Reward Board"),
]


def _stamp(rule: dict) -> str:
    """Stable build stamp from the registration, never the wall clock."""
    commit = (rule.get("registration_commit") or "unavailable")[:12]
    sha = (rule.get("rule_sha256") or "unavailable")[:12]
    return f"registered commit {commit} · rule sha256 {sha}"


def load(name: str):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


RULE = load("rewards.json")
THRESH = load("thresholds.json")
BUILD_STAMP = _stamp(RULE)


def e(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def badge(text: str, kind: str = "mute") -> str:
    return f'<span class="b b-{kind}">{e(text)}</span>'


STATUS_BADGE = {
    "not_qualified": ("not qualified", "bad"),
    "no_escrow": ("no escrow", "warn"),
    "qualified": ("qualified", "ok"),
    "awarded": ("badge awarded", "ok"),
    "none": ("none awarded", "warn"),
}


def sb(status: str) -> str:
    label, kind = STATUS_BADGE.get(status, (status, "mute"))
    return badge(label, kind)


def src_links(items) -> str:
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


def table(headers, rows, caption="", cls="", num_cols=(), src_col=None, key_col=0) -> str:
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
    return (f'<div class="table-wrap"><table class="{cls}">{cap}<thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def page(path: str, title: str, kicker: str, lede: str, body: str) -> str:
    links = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == path else ""
        links.append(f'<a href="{href}"{cur}>{e(label)}</a>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · NFL Reward Board</title>
<meta name="description" content="Pre-registered, non-monetary badge rule for the NFL1 strategy competition: proper-score qualification, then prospective CLV/ROI escrow. Frozen before grading.">
<link rel="stylesheet" href="assets/rewards.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="top-in">
  <a class="brand" href="index.html"><span class="mark">NFL</span><span>Reward Board<small>frozen rule · non-monetary badges</small></span></a>
  <nav class="main" aria-label="Sections">{"".join(links)}</nav>
</div></header>
<main id="main">
  <section class="page-head">
    <p class="eyebrow">{e(kicker)}</p>
    <h1>{e(title)}</h1>
    <p class="lede">{lede}</p>
    <p class="stamp">Built {e(BUILD_STAMP)} · registration commit {e(RULE.get("registration_commit",""))[:12]} · every table row links to its source</p>
  </section>
  {body}
</main>
<footer><div class="foot-in">
  <div><strong>NFL Reward Board</strong>A pre-registered proposal (policy), not an official NFL fact. Rewards are
  non-monetary badges. No backtest performance number is published on this board.</div>
  <div>Rule: <a href="{REPO}/blob/main/rewards/REWARDS-RULE.md" rel="noopener">REWARDS-RULE.md</a> ·
  Competition: <a href="../strat/index.html">Strategy Competition</a> ·
  Repository: <a href="{REPO}" rel="noopener">kanlerxz87-cyber/NFL1</a></div>
</div></footer>
</body>
</html>
"""


def write(name: str, content: str) -> None:
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"wrote rewards/{name}")


def page_index() -> str:
    tracks = RULE["tracks"]
    awarded = RULE.get("badges_awarded", [])
    thresh = {t["id"]: t for t in THRESH["thresholds"]}

    # KPIs
    n_tracks = len(tracks)
    n_awarded = len(awarded)
    n_qualified = sum(1 for t in tracks if t["stage1_status"] == "qualified")
    kpis = "".join(
        f'<article class="kpi"><span class="label">{e(lbl)}</span>'
        f'<span class="value">{e(val)}</span>'
        f'<span class="note">{note}</span></article>'
        for lbl, val, note in [
            ("Tracks", str(n_tracks), "Single bet · Parlay · Player prop combo (the three competition tracks)"),
            ("Badges awarded", str(n_awarded), RULE.get("badges_awarded_note", "")),
            ("Stage-1 qualified", str(n_qualified), "no strategy clears all three Stage-1 conditions today (any_eligible=false)"),
            ("Monetary value", "none", "badges are non-monetary by rule; no cash value is attached"),
        ])

    # Thresholds table
    trows = []
    for t in THRESH["thresholds"]:
        trows.append([
            e(t["id"]), e(t["name"]), e(t["value"]),
            e(str(t.get("numeric", ""))), e(t["applies_to"]),
            src_links([{"t": t["source"], "u": t["source_url"]}]),
        ])
    tthr = table(["ID", "Threshold", "Frozen value", "Numeric", "Applies to", "Source"],
                 trows, caption="The frozen numeric thresholds of the reward rule",
                 num_cols=(3,), src_col=5)

    # Track status table
    srows = []
    for t in tracks:
        srows.append([
            e(t["name"]), e(t["badge"]),
            sb(t["stage1_status"]), sb(t["stage2_status"]),
            e(t["reason"]),
            src_links([{"t": "proper-score result", "u": REPO + "/blob/main/data/strat/proper_score.json"}]),
        ])
    tstat = table(["Track", "Badge", "Stage 1 (qualification)", "Stage 2 (escrow)",
                   "Status reason", "Source"],
                  srows, caption="Per-track qualification status — a badge is never fabricated",
                  src_col=5)

    # Awarded badges table (empty by design)
    if awarded:
        arows = [[e(b.get("track", "")), e(b.get("strategy", "")), e(b.get("badge", "")),
                  e(b.get("window", "")),
                  src_links([{"t": "registration", "u": REPO + "/blob/main/rewards/REWARDS-RULE.md"}])]
                 for b in awarded]
        taward = table(["Track", "Strategy", "Badge", "Escrow window", "Source"], arows,
                       caption="Badges awarded so far", src_col=4)
    else:
        taward = ('<div class="callout"><strong>No badge is awarded.</strong> '
                  + e(RULE.get("badges_awarded_note", ""))
                  + ' The rule is frozen and waiting for a strategy that clears Stage 1.</div>')

    mc = RULE["mind_changers"]
    body = f"""
<div class="callout"><strong>Read this first.</strong> {e(RULE["summary"])} This is a
<strong>pre-registered proposal (policy)</strong>, frozen before any strategy is graded against it.
It is not an official NFL fact: the league publishes no reward programme. The thresholds are taken
from this repository's own proper-score method, not invented.</div>
<div class="kpis">{kpis}</div>

<h2>The two stages</h2>
<div class="cols">
  <div class="panel"><h3>Stage 1 — Proper-Score Qualification</h3>
    <p>A strategy earns the <strong>Verified Signal</strong> badge when, on a frozen walk-forward
    out-of-sample window, its Brier skill <em>lower bound</em> is &gt; 0, its BH-adjusted p-value is
    &lt; 0.05 (and it clears Bonferroni 0.05 / N_tests), and its decided-bet sample is &ge; 200.</p>
    <p class="small">Value: 1 qualification point and Stage-2 eligibility in the track.</p>
  </div>
  <div class="panel"><h3>Stage 2 — Prospective CLV / ROI Escrow</h3>
    <p>Only Stage-1-qualified strategies enter a registered multi-week prospective escrow. The
    <strong>Top {{Track}}</strong> badge goes to the rank-1 eligible strategy whose
    prospective ROI lower bound is &gt; 0. If none qualifies, no badge is awarded.</p>
    <p class="small">Value: the track badge plus rank 1 in the track. Non-monetary.</p>
  </div>
</div>

<h2>Frozen thresholds</h2>
{tthr}

<h2>Qualification status, by track</h2>
{tstat}

<h2>Badges awarded</h2>
{taward}

<h2>Demotion and re-promotion</h2>
<p>{e(RULE["demotion"])}</p>
<p class="small">Source: <a href="{REPO}/blob/main/data/strat/demotion_rules.json" rel="noopener">data/strat/demotion_rules.json</a></p>

<h2>What would change our mind</h2>
<div class="cols">
  <div class="panel"><h3>Upside — a badge is earned</h3><p>{e(mc["upside"])}</p></div>
  <div class="panel"><h3>Downside — a badge is withdrawn</h3><p>{e(mc["downside"])}</p></div>
</div>

<h2>What this board never publishes</h2>
<ul class="tight">
  <li><strong>Backtest performance numbers.</strong> No ROI, win rate, hit rate, profit or rank
  derived from a backtest appears here. Stage 1 publishes the rule, the thresholds and a
  qualification status — never a backtest figure. The underlying proper-score result is linked,
  not re-published.</li>
  <li><strong>A badge without a cleared Stage-1 gate.</strong> No exceptions.</li>
  <li><strong>A monetary value.</strong> Badges are non-monetary by rule.</li>
</ul>

<h2>Sources</h2>
<ul class="ev">{"".join(f'<li><a href="{e(s["u"])}" rel="noopener">{e(s["t"])}</a></li>' for s in RULE["sources"])}</ul>
"""
    return page("index.html", "Reward Board", "Pre-registered competition rewards",
                "The frozen, two-stage rule that decides which strategies earn a non-monetary badge, "
                "and the honest status of every track today.", body)


def main() -> int:
    write("index.html", page_index())
    print("rewards: 1 pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
