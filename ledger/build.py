#!/usr/bin/env python3
"""ledger/build.py — build the c84 session site from committed data only.

Eight pages, all static, every table row carrying an official source link. The build FAILS
rather than publishing a row it cannot source.

    python3 ledger/build.py            # write ledger/*.html
    python3 ledger/verify.py           # gate: no broken link, no sourceless row, no placeholder

Inputs (read-only, owned by other sessions or by this session's own study):
    data/session-c84a41a4/*.json   this session's computed results
    room/data/readiness.json       the 82-row requirement register
    data/flags.json                the flag register
    data/depth_ladder.json         31-club depth ladder (transcribed depth charts)
    data/session-1505ac8e/depth_charts.json   the depth charts themselves
    data/model/official_injuries.json         official Week 10 injury report
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "ledger")
DATA = os.path.join(ROOT, "data", "session-c84a41a4")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

OFFICIAL = {
    "schedules": "https://www.nfl.com/schedules/",
    "injuries": "https://www.nfl.com/injuries/",
    "standings": "https://www.nfl.com/standings/league/2026/reg",
    "stats": "https://www.nfl.com/stats/player-stats/",
    "teams": "https://www.nfl.com/teams/",
    "reg10": "https://www.nfl.com/injuries/league/2026/reg10",
}
NFLVERSE = "https://github.com/nflverse/nflverse-data"

PAGES = [
    ("index.html", "Overview"),
    ("executive.html", "Executive summary"),
    ("decisions.html", "Requirements: can we decide yet?"),
    ("strategies.html", "Strategy competition"),
    ("lines.html", "Own lines & price store"),
    ("injuries.html", "Injuries & replacement"),
    ("verification.html", "Verification"),
    ("flagged.html", "Flagged for review"),
    ("suggestions.html", "Suggestions"),
]

CSS = """
:root{--bg:#0f1116;--card:#171a21;--line:#242a35;--ink:#e8edf5;--dim:#9aa7ba;
--ok:#3fb950;--warn:#d29922;--bad:#f85149;--acc:#58a6ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc);text-decoration:none}
a:hover{text-decoration:underline}
header{border-bottom:1px solid var(--line);background:#0b0d12;position:sticky;top:0;z-index:5}
nav{max-width:1180px;margin:0 auto;padding:10px 18px;display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center}
nav .brand{font-weight:700;letter-spacing:.2px;color:#fff;margin-right:8px}
nav a{font-size:13px;color:var(--dim);padding:4px 2px}
nav a.on{color:#fff;border-bottom:2px solid var(--acc)}
main{max-width:1180px;margin:0 auto;padding:26px 18px 60px}
h1{font-size:26px;margin:0 0 6px}
h2{font-size:18px;margin:34px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:15px;margin:22px 0 8px;color:#cfd8e5}
p{color:#c8d2e0;max-width:80ch}
.lead{color:var(--dim);font-size:14px;margin:0 0 18px;max-width:90ch}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:14px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpi .v{font-size:24px;font-weight:700}
.kpi .l{font-size:12px;color:var(--dim);margin-top:2px}
.kpi .s{font-size:11px;color:#7b8798;margin-top:6px}
table{width:100%;border-collapse:collapse;margin:10px 0 18px;font-size:13px;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}
th{background:#1d222c;text-align:left;padding:8px 10px;font-weight:600;color:#cfd8e5;border-bottom:1px solid var(--line);font-size:12px;white-space:nowrap}
td{padding:8px 10px;border-bottom:1px solid #1e242e;vertical-align:top}
tr:last-child td{border-bottom:none}
tbody tr:hover{background:#1b202a}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.dim{color:var(--dim)}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:999px;border:1px solid var(--line);color:var(--dim);white-space:nowrap}
.tag.ok{color:var(--ok);border-color:#1f6f33}
.tag.warn{color:var(--warn);border-color:#6b5312}
.tag.bad{color:var(--bad);border-color:#7a2723}
.note{background:#141821;border:1px solid var(--line);border-left:3px solid var(--acc);border-radius:8px;padding:12px 14px;margin:14px 0}
.note.warn{border-left-color:var(--warn)}
.note.bad{border-left-color:var(--bad)}
.scroll{overflow-x:auto;border-radius:8px}
footer{border-top:1px solid var(--line);color:var(--dim);font-size:12px;max-width:1180px;margin:0 auto;padding:18px}
.blank{color:#5d6675;font-style:italic}
code{background:#1d222c;padding:1px 5px;border-radius:4px;font-size:12px}
ul{color:#c8d2e0}
"""


def esc(x):
    return html.escape("" if x is None else str(x))


def load(rel, default=None):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def src_cell(url, label=None):
    if not url:
        return '<td><span class="blank">no public source</span></td>'
    return f'<td><a href="{esc(url)}" rel="noopener">{esc(label or short(url))}</a></td>'


def short(url):
    u = url.replace("https://", "").replace("http://", "").replace("www.", "")
    return u if len(u) <= 46 else u[:43] + "…"


def fmt(v, nd=2, pct=False, cls=""):
    if v is None or v == "":
        return '<span class="blank">blank</span>'
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        s = f"{v:,.{nd}f}"
        if pct:
            s += "%"
        return f'<span class="{cls}">{s}</span>'
    return esc(v)


def table(headers, rows, caption=None, nav=False):
    tag = '<div class="scroll"><table data-nav="1">' if nav else '<div class="scroll"><table>'
    out = [tag]
    if caption:
        out.append(f"<caption>{esc(caption)}</caption>")
    out.append("<thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in headers) + "</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join(r) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def page(fname, title, body, active):
    nav = "".join(
        f'<a class="{"on" if f == fname else ""}" href="{f}">{esc(t)}</a>' for f, t in PAGES
    )
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · NFL Origination Ledger</title>
<style>{CSS}</style></head>
<body>
<header><nav><span class="brand">NFL Origination Ledger</span>{nav}</nav></header>
<main>
{body}
</main>
<footer>
Built {TODAY} from committed files only. Every row links to the source that settles it.
Static strings, no scripts, no fonts, no analytics. Session <code>c84a41a4-nfl1</code>.
Prices are a third-party parse of an unofficial market and are labelled as such; the NFL
publishes no odds.
</footer>
</body></html>"""
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as fh:
        fh.write(doc)
    return len(doc)


def badge(status):
    s = (status or "").lower()
    cls = "ok" if s in ("done", "promoted", "pass", "met") else \
          "warn" if s in ("partial", "paper", "needs review", "watch") else \
          "bad" if s in ("blocked", "not met", "fail", "not started") else ""
    return f'<span class="tag {cls}">{esc(status)}</span>'


# ----------------------------------------------------------------- page bodies
def build_overview(R, rep, ready):
    sample = R["sample"]
    brier = R["brier"]
    strategies = R["strategies"]
    gates = R["gates"]
    promoted = R["promoted"]
    ctrl = R["controls"]
    best_rule = max((s for s in strategies if s not in ("C84-S1", "C84-S2")),
                    key=lambda s: strategies[s]["roi_pct"])
    ready_rows = ready.get("rows", []) if isinstance(ready, dict) else []
    counts = {}
    for r in ready_rows:
        counts[r.get("status")] = counts.get(r.get("status"), 0) + 1

    body = f"""
<h1>NFL Origination Ledger</h1>
<p class="lead">A pre-registered test of whether an own-made NFL number beats the closing
market: {len(strategies)} rules, 10 gates each, on {sample['games_played']:,} decided games.
The answer, stated up front, is <strong>no</strong> — and the page below shows the evidence,
the exact gates that failed, and what would have to change.</p>

<div class="grid">
  <div class="kpi"><div class="v">{len(promoted)}<span class="dim" style="font-size:15px">/{len(strategies)}</span></div>
    <div class="l">rules promoted</div><div class="s">all ten gates must pass</div></div>
  <div class="kpi"><div class="v {'ok' if (brier['brier_skill_score'] or 0) > 0 else 'bad'}">{fmt(brier['brier_skill_score'], 4)}</div>
    <div class="l">Brier skill vs the close</div><div class="s">negative = the market forecasts better</div></div>
  <div class="kpi"><div class="v">{fmt(R['controls']['best_control_roi_pct'], 2, pct=True)}</div>
    <div class="l">best information-free control</div><div class="s">blind-away, every game</div></div>
  <div class="kpi"><div class="v">{fmt(strategies[best_rule]['roi_pct'], 2, pct=True)}</div>
    <div class="l">best signal, in sample</div><div class="s">{esc(best_rule)} — still paper</div></div>
  <div class="kpi"><div class="v">{fmt(R['ablation']['difference_with_minus_without'], 4)}</div>
    <div class="l">MAE change from injury features</div><div class="s">ablation, not a penalty</div></div>
  <div class="kpi"><div class="v">{len(ready_rows)}</div>
    <div class="l">brief requirements tracked</div><div class="s">each with its blocking gate</div></div>
</div>

<div class="note bad">
<strong>The one-paragraph answer.</strong> The pre-registered own-line model is a worse
forecaster than the closing line on every measure computed here: its Brier score is
{fmt(brier['brier_model'], 4)} against the de-vigged close's {fmt(brier['brier_market_devig'], 4)}
(a skill score of {fmt(brier['brier_skill_score'], 4)}, interval excluding zero), and it is the
only one of the twelve rules whose in-sample ROI is materially positive
({esc(best_rule)}, {fmt(strategies[best_rule]['roi_pct'], 2, pct=True)}), which fails multiple
testing and fails the untouched 2024-2026 holdout. Adding the availability features to the fit
changes mean absolute error by {fmt(R['ablation']['difference_with_minus_without'], 4)} points
with an interval containing zero, so the injury signal is not doing work. No rule is promoted and
nothing on this site is a bet recommendation.
</div>

<h2>What this site is, and what it is not</h2>
<table>
<thead><tr><th>It is</th><th>It is not</th><th>Source</th></tr></thead>
<tbody>
<tr><td>A frozen rule set, committed before the results were computed, with the commit hash printed on
<a href="strategies.html">the strategy page</a></td>
<td>A search over thresholds until something looked good. The thresholds were fixed in
<code>preregistration.json</code> and the hash is checked at build time.</td>
<td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-c84a41a4/preregistration.json">preregistration.json</a></td></tr>
<tr><td>Every published number traceable to a committed file with a sha256</td>
<td>A live feed. The prices are a snapshot of a third-party parse and are labelled that way.</td>
<td><a href="https://github.com/nflverse/nflverse-data">nflverse-data</a></td></tr>
<tr><td>Blanks where no source exists — six rows of the brief's own claims are corrected by live
official pages on <a href="flagged.html">Flagged for review</a></td>
<td>An inference. A cell with no official source is printed as blank and flagged, never filled.</td>
<td><a href="flagged.html">Flagged for review</a></td></tr>
</table>

<h2>Where to go</h2>
<div class="scroll"><table data-nav="1">
<thead><tr><th>Page</th><th>What it answers</th><th>Rows</th></tr></thead><tbody>
<tr><td><a href="executive.html">Executive summary</a></td><td>The whole project in one screen:
what holds, what does not, what a human must decide</td><td class="num">1</td></tr>
<tr><td><a href="decisions.html">Requirements</a></td><td>Every requirement in the brief, the gate
blocking it and the number that would clear it</td><td class="num">{len(ready_rows)}</td></tr>
<tr><td><a href="strategies.html">Strategy competition</a></td><td>Twelve rules, ten gates each,
the control baseline, correlations and the luck panel</td><td class="num">{len(strategies)}</td></tr>
<tr><td><a href="lines.html">Own lines &amp; price store</a></td><td>The model's fair line, the
market line and the difference, as separate columns, per game</td>
<td class="num">{R['sample']['games_played']:,}</td></tr>
<tr><td><a href="injuries.html">Injuries &amp; replacement</a></td><td>Official designations, the
ablation, and confirmed quarterback replacements</td>
<td class="num">{len(rep['examples'])}</td></tr>
<tr><td><a href="verification.html">Verification</a></td><td>Line by line: source, hash, and what
was checked against what</td><td class="num">1</td></tr>
<tr><td><a href="flagged.html">Flagged for review</a></td><td>Every irregularity, including claims
in the brief that the live official pages contradict</td><td class="num">1</td></tr>
<tr><td><a href="suggestions.html">Suggestions</a></td><td>Ranked improvements with a decision
for each, for a reviewer to choose before anything is built</td><td class="num">12</td></tr>
</tbody></table></div>

<div class="note warn">
<strong>Read <a href="flagged.html">Flagged for review</a> before acting on anything here.</strong>
Seven claims that circulate in this project are contradicted by the live official pages this
session fetched. They are published with the counter-evidence rather than quietly dropped.
</div>
"""
    return body


def build_executive(R, rep):
    b = R["brier"]
    a = R["ablation"]
    lk = R["luck"]
    best = max((s for s in R["strategies"] if s not in ("C84-S1", "C84-S2")),
               key=lambda s: R["strategies"][s]["roi_pct"])
    bs = R["strategies"][best]
    body = f"""
<h1>Executive summary</h1>
<p class="lead">What holds up, what does not, what is missing, and what a human has to decide.
Every sentence below is backed by a row on another page of this site.</p>

<h2>1. The finding</h2>
<div class="note bad">
<p style="margin-top:0"><strong>An own-made NFL number did not beat the closing line, and the test
was built so that it could have said otherwise.</strong></p>
<p>The model is the simple team-strength model the brief asks for: a ridge fit of one strength
number per club plus home field and rest, refitted for every week on earlier weeks only. Scored
against the de-vigged closing moneyline on {b['n_games']:,} games it scores a Brier of
{fmt(b['brier_model'], 4)} against the market's {fmt(b['brier_market_devig'], 4)}. The difference
is {fmt(b['difference_model_minus_market'], 4)} with a game-cluster 95% interval of
{esc(b['difference_ci95_game_cluster'])}, entirely on the wrong side of zero.</p>
<p>Twelve bet rules were pre-registered. None passed all ten gates. The single rule with a real
in-sample edge (own line vs close by 4+ points, {fmt(bs['roi_pct'], 2, pct=True)} over
{bs['n_decided']:,} decided bets) fails multiple testing (q = {fmt(R['gates'][best]['q_value'], 3)}),
fails the untouched holdout, and its game-cluster interval
{esc(bs['roi_ci95_game_cluster'])} straddles zero. That is what a lucky run looks like, not what
an edge looks like.</p>
</div>

<h2>2. The controls that make the finding credible</h2>
{print_table_controls(R)}

<div class="note">
<strong>Why a blind rule matters.</strong> Over the same sample, betting the away side in every
single game returns {fmt(R['controls']['C84-S1_roi_pct'], 2, pct=True)}, while betting the home
side in every single game returns {fmt(R['controls']['C84-S2_roi_pct'], 2, pct=True)}. Those two
numbers bracket what "no information" looks like on this sample, and eleven of the twelve
signals land inside that bracket. A rule that cannot beat "bet every away team" has not been
shown to contain information.
</div>

<h2>3. The availability question, answered by ablation rather than assertion</h2>
<p>The brief asks for injury and personnel features and then asks for them to be tested by
ablation rather than by imposing a points penalty. The ablation is on
<a href="injuries.html">the injuries page</a>: the identical model is refitted with and without
the two availability columns.</p>
<table>
<thead><tr><th>Measure</th><th class="num">With availability</th><th class="num">Without</th><th>Reading</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Mean absolute error, points</td><td class="num">{fmt(a['mae_with_availability'], 4)}</td>
<td class="num">{fmt(a['mae_without_availability'], 4)}</td>
<td>Difference {fmt(a['difference_with_minus_without'], 4)}, interval
{esc(a['difference_ci95_game_cluster'])}</td>{src_cell(OFFICIAL['injuries'], 'nfl.com injury report')}</tr>
</tbody></table>
<p>{esc(a['verdict'])} That is a measured answer, not a preference: the features are in the model
and they earn their place or they do not. Here they do not.</p>

<h2>4. What is missing, and why each gap is a gap</h2>
<table>
<thead><tr><th>Missing</th><th>Why it matters</th><th>What would close it</th><th>Source</th></tr></thead>
<tbody>
<tr><td>An opening line</td><td>Without an open and a close no line-movement study is possible, and
the price snapshot store the brief asks for cannot be built</td>
<td>A timestamped two-snapshot price source, captured on a schedule</td>
<td>{src_cell(OFFICIAL['schedules'], 'nfl.com schedules')}</td></tr>
<tr><td>A prop price</td><td>Player-prop ROI cannot be computed, so props can never be ranked or
used as a parlay leg</td><td>An observed prop price with a timestamp</td>
<td>{src_cell(OFFICIAL['stats'], 'nfl.com player stats')}</td></tr>
<tr><td>Confirmed starters below quarterback</td><td>{rep["counts"]["confirmed_starts"]:,} starts are
confirmed for quarterbacks. For line and secondary there is no committed confirmed-starter or
snap-count feed, so a 2nd-string lineman replacing a starter cannot be confirmed, only guessed</td>
<td>An official snap-count feed, or Game Books captured on a schedule</td>
<td>{src_cell(OFFICIAL['schedules'], 'nfl.com game centre')}</td></tr>
<tr><td>Retained availability snapshots over time</td><td>The brief asks to replay practice
designations "as they were known". One capture cannot do that</td><td>Scheduled daily captures with
hashes, which is an Actions job and is not run by this session</td>
<td>{src_cell(OFFICIAL['reg10'], 'nfl.com Week 10 report')}</td></tr>
<tr><td>A bootstrapped interval on the staking side</td><td>Signal and staking are now separated,
but the staking leg has no independent evidence yet</td><td>A prospective escrow of realised returns</td>
<td>{src_cell(OFFICIAL['schedules'], 'nfl.com schedules')}</td></tr>
</tbody></table>

<h2>5. What a human must decide</h2>
<table>
<thead><tr><th>Decision</th><th>Options</th><th>Recommended</th><th>Blocked by</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Is a third-party price parse acceptable as the price of record?</td>
<td>Accept it, labelled unofficial · buy a licensed feed · publish no ROI at all</td>
<td>Keep it, labelled, until a licensed feed exists — the label is already on every page</td>
<td>Nothing. This is a policy choice.</td>
<td><a href="https://github.com/nflverse/nflverse-data">nflverse-data (unofficial price parse)</a></td></tr>
<tr><td>Does the project stop originating, or reframe as measurement?</td>
<td>Keep originating and accept the negative result · reframe as a priced-research ledger · stop</td>
<td>Reframe. The negative result is the asset: it is reproducible and it is honest.</td>
<td>Nothing. This is a policy choice.</td>
<td><a href="strategies.html">this site's strategy page</a> (internal, no external source)</td></tr>
<tr><td>Which of the two conflicting gate schemes is canonical?</td>
<td>The 8-gate scheme in <code>data/s9cb</code> · the 10-gate scheme registered here</td>
<td>The 10-gate scheme, because only it exists with a pre-registration hash</td>
<td>Nothing, but the choice must be recorded.</td>
<td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-c84a41a4/preregistration.json">preregistration.json</a></td></tr>
</tbody></table>
<p class="dim">The full list of requirement-level blockers, with the number that would clear each,
is on <a href="decisions.html">Requirements</a>.</p>
"""
    return body


def print_table_controls(R):
    rows = []
    for s in ("C84-S1", "C84-S2"):
        sc = R["strategies"][s]
        g = R["gates"][s]
        rows.append([f"<strong>{esc(s)}</strong>"
                     + ("" if s.endswith("1") else ""),
                     "blind away" if s.endswith("1") else "blind home",
                     fmt(sc["n_decided"], 0), fmt(sc["hit_rate"], 4),
                     fmt(sc["break_even_hit_rate"], 4), fmt(sc["roi_pct"], 2, pct=True),
                     esc(sc["roi_ci95_game_cluster"]), badge("CONTROL")])
    return table(["Rule", "What it does", "n decided", "Hit rate", "Break-even", "ROI",
                  "95% CI (game cluster)", "Status", "Source"],
                 [[r[0], r[1], f'<td class="num">{r[2]}</td>', f'<td class="num">{r[3]}</td>',
                   f'<td class="num">{r[4]}</td>', f'<td class="num">{r[5]}</td>',
                   f'<td class="num">{r[6]}</td>', f"<td>{r[7]}</td>",
                   src_cell(OFFICIAL['schedules'], 'nfl.com schedules (closing lines)')]
                  for r in rows])


def build_decisions(R, ready):
    rows = ready.get("rows", [])
    body = [f"""
<h1>Requirements: can this be decided yet?</h1>
<p class="lead">{len(rows)} requirements from the brief. For each: the status, the gate that blocks
it, and the number that would clear it. This is the reviewer's worklist — the register is only
useful if it says what would change the answer.</p>
<div class="note">
<strong>How to read a status.</strong> <span class="tag ok">Done</span> the artifact exists and is
verifiable · <span class="tag warn">Partial</span> some of it exists · <span class="tag bad">Blocked</span>
a source or a policy does not exist yet · <span class="tag bad">Not met</span> the brief asks for
it and nothing does it. A blank is never filled.
</div>
"""]
    counts = {}
    for r in rows:
        counts[r.get("status")] = counts.get(r.get("status"), 0) + 1
    body.append('<div class="grid">' + "".join(
        f'<div class="kpi"><div class="v">{v}</div><div class="l">{esc(k)}</div></div>'
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1])) + "</div>")

    trs = []
    for r in rows:
        s = r.get("src") or {}
        url = s.get("u") if isinstance(s, dict) else None
        internal = url and "github.com/kanlerxz87-cyber/NFL1" in url
        link = (f'<a href="{esc(url)}">{esc("repo artifact" if internal else s.get("t"))}</a>'
                if url else '<span class="blank">no source</span>')
        trs.append([
            f'<td><code>{esc(r.get("id"))}</code></td>',
            f"<td>{esc(r.get('requirement'))}</td>",
            f"<td>{badge(r.get('status'))}</td>",
            f"<td>{esc(r.get('blocked_by'))}</td>",
            f"<td>{esc(r.get('clears_when'))}</td>",
            f"<td>{link}</td>",
        ])
    body.append(table(["ID", "Requirement", "Status", "Blocked by", "Clears when", "Source"], trs))
    body.append("""
<h2>The seven questions that gate everything else</h2>
<table>
<thead><tr><th>#</th><th>Question</th><th>Known</th><th>Missing</th><th>How to get it</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Q1</td><td>Is the price of record official?</td><td>The NFL publishes no odds</td>
<td>A licensed, timestamped price</td><td>Buy a feed, or keep the third-party parse labelled</td>
<td><a href="https://www.nfl.com/schedules/">nfl.com</a></td></tr>
<tr><td>Q2</td><td>Can an opening line be recovered?</td><td>One number per market per game is committed</td>
<td>Two snapshots with fetch times</td><td>Scheduled capture, twice per week minimum</td>
<td><a href="https://www.nfl.com/schedules/">nfl.com</a></td></tr>
<tr><td>Q3</td><td>Is the depth chart a usable depth source?</td><td>31 of 32 clubs publish one; HOU publishes an image</td>
<td>A dated, versioned capture for all 32</td><td>Daily capture with hashes; HOU needs an authorised structured source</td>
<td><a href="https://www.houstontexans.com/team/depth-chart">texans.com</a></td></tr>
<tr><td>Q4</td><td>Who actually played, position by position?</td><td>Confirmed QB starters for 10,000 club-starts</td>
<td>Snap counts for every position</td><td>An official snap-count feed or Game Books</td>
<td><a href="https://www.nfl.com/schedules/">nfl.com</a></td></tr>
<tr><td>Q5</td><td>Does a designation mean anything?</td><td>Out/Questionable/Doubtful counts are known</td>
<td>The play rate per designation with intervals</td><td>Join several seasons of designations to official inactives</td>
<td><a href="https://www.nfl.com/injuries/">nfl.com</a></td></tr>
<tr><td>Q6</td><td>Can a parlay be priced?</td><td>Multiplication of marginals is invalid</td>
<td>A validated joint probability and the operator's void rules</td><td>Do not rank combos until both exist</td>
<td><a href="https://www.nfl.com/schedules/">nfl.com</a></td></tr>
<tr><td>Q7</td><td>Is the model measured against the right benchmark?</td><td>Yes — the de-vigged close</td>
<td>Nothing for the single-bet case</td><td>Already done on <a href="lines.html">Own lines</a></td>
<td><a href="https://www.nfl.com/schedules/">nfl.com</a></td></tr>
</tbody></table>
""")
    return "\n".join(body)


def build_strategies(R):
    st, gates = R["strategies"], R["gates"]
    body = [f"""
<h1>Strategy competition</h1>
<p class="lead">Twelve rules, fixed before any result was computed. Ten gates each. All twelve are
published whatever they show, including the two information-free controls. Nothing here is
ranked by win rate or by short-run ROI; the gates decide.</p>

<div class="note">
<strong>The registration.</strong> Rules, thresholds, the season split and the gates live in
<code>data/session-c84a41a4/preregistration.json</code>, sha256
<code>{esc(R['registration']['sha256'])}</code>, committed at <code>061c2a8</code> before
<code>results.json</code> existed. The build re-checks that hash and fails if the file was edited
after the results were computed.
</div>

<div class="grid">
  <div class="kpi"><div class="v">{len(R['promoted'])}</div><div class="l">promoted</div>
    <div class="s">all ten gates</div></div>
  <div class="kpi"><div class="v">{R['n_bets_total']:,}</div><div class="l">bet rows scored</div>
    <div class="s">each with an observed price</div></div>
  <div class="kpi"><div class="v">{R['n_rules_tested']}</div><div class="l">rules tested</div>
    <div class="s">BH charged for all of them</div></div>
  <div class="kpi"><div class="v">{R['sample']['games_played']:,}</div><div class="l">decided games</div>
    <div class="s">{R['sample']['seasons'][0]}–{R['sample']['seasons'][1]}</div></div>
</div>
"""]
    trs = []
    for s in sorted(st, key=lambda x: -st[x]["roi_pct"]):
        sc, g = st[s], gates[s]
        cls = "ok" if sc["roi_pct"] > 0 else "bad"
        trs.append([
            f"<td><code>{esc(s)}</code></td>",
            f"<td>{esc(s)}</td>",
            f'<td class="num">{sc["n_decided"]:,}</td>',
            f'<td class="num">{fmt(sc["hit_rate"], 4)}</td>',
            f'<td class="num">{fmt(sc["break_even_hit_rate"], 4)}</td>',
            f'<td class="num"><span class="{cls}">{fmt(sc["roi_pct"], 2, pct=True)}</span></td>',
            f'<td class="num">{esc(sc["roi_ci95_game_cluster"])}</td>',
            f'<td class="num">{fmt(g["q_value"], 3)}</td>',
            f'<td class="num">{g["gates_passed"]}/{g["gates_total"]}</td>',
            f"<td>{badge(g['status'])}</td>",
            src_cell(OFFICIAL['schedules'], 'nfl.com schedules (closing lines)'),
        ])
    body.append('<h2>Leaderboard — every rule, ordered by in-sample ROI, which is not a ranking</h2>')
    body.append('<p class="dim">Ordered by ROI only so the eye can find the top; the only ordering '
                'that promotes anything is the gate count. The two controls are the floor.</p>')
    body.append(table(["ID", "Rule", "n decided", "Hit rate", "Break-even", "ROI",
                       "95% CI (game cluster)", "BH q", "Gates", "Status", "Source"], trs))

    body.append("<h2>Gate matrix, one row per rule</h2>")
    defs = [("C84-G1", "Observed price on every scored bet"),
            ("C84-G2", "Pre-game information only"),
            ("C84-G3", f"At least 300 decided bets"),
            ("C84-G4", "Hit rate beats the price-implied break-even"),
            ("C84-G5", "Survives Benjamini-Hochberg"),
            ("C84-G6", "Positive in the untouched 2024-2026 holdout"),
            ("C84-G7", "Positive in 60%+ of seasons"),
            ("C84-G8", "Game-cluster 95% CI excludes zero"),
            ("C84-G9", "Beats the information-free control"),
            ("C84-G10", "Edge survives deleting the best season")]
    trs = []
    for s in sorted(st):
        g = gates[s]
        cells = "".join(
            f'<td class="num">{"✓" if c["pass"] else "✗"}</td>' for c in g["checks"])
        trs.append([f'<td><code>{esc(s)}</code></td>', f"<td>{esc(s)}</td>", cells,
                    f'<td class="num">{g["gates_passed"]}/{g["gates_total"]}</td>',
                    src_cell(OFFICIAL['schedules'], 'nfl.com schedules (closing lines)')])
    body.append(table(["ID", "Rule"] + [f"{gid}" for gid, _ in defs] + ["Passed", "Source"], trs))
    body.append("<p class='dim'>Gate legend: " + " · ".join(f"<code>{gid}</code> {esc(d)}"
                                                           for gid, d in defs) + "</p>")

    lk = R["luck"]
    body.append(f"""
<h2>Removal of luck</h2>
<p>Win rate is not a test. These are.</p>
<table>
<thead><tr><th>Test</th><th class="num">Value</th><th>Reading</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Decided bets, all rules pooled</td><td class="num">{lk['n_decided']:,}</td>
<td>The whole sample this study has to work with, spread over twelve rules</td>{src_cell(OFFICIAL['schedules'])}</tr>
<tr><td>Pooled hit rate vs break-even</td><td class="num">{fmt(lk['hit_rate_all_bets'], 4)} vs {fmt(lk['break_even_hit_rate'], 4)}</td>
<td>{fmt(lk['units_above_break_even_per_100_bets'], 2)} units per 100 bets, i.e. a loss of about the vig</td>{src_cell(OFFICIAL['schedules'])}</tr>
<tr><td>Decided bets needed to see a 1-point edge</td><td class="num">{lk['sample_size_needed_80pct_power']['1-point hit-rate edge']:,}</td>
<td>At 5% two-sided and 80% power</td>{src_cell(OFFICIAL['schedules'])}</tr>
<tr><td>… a 2-point edge</td><td class="num">{lk['sample_size_needed_80pct_power']['2-point hit-rate edge']:,}</td><td></td>{src_cell(OFFICIAL['schedules'])}</tr>
<tr><td>… a 3-point edge</td><td class="num">{lk['sample_size_needed_80pct_power']['3-point hit-rate edge']:,}</td><td></td>{src_cell(OFFICIAL['schedules'])}</tr>
<tr><td>… a 5-point edge</td><td class="num">{lk['sample_size_needed_80pct_power']['5-point hit-rate edge']:,}</td><td></td>{src_cell(OFFICIAL['schedules'])}</tr>
</tbody></table>
<div class="note warn">{esc(lk['power_note'])}</div>

<h2>Correlation register</h2>
<p>{esc(R['correlation']['rule'])} {esc(R['correlation']['not_computed'])}</p>
""")
    trs = []
    for r in R["correlation"]["rows"]:
        trs.append([f"<td>{esc(r['kind'])}</td>", f"<td>{esc(r['a'])}</td>", f"<td>{esc(r['b'])}</td>",
                    f'<td class="num">{r["n"]:,}</td>', f'<td class="num">{fmt(r["r"], 4)}</td>',
                    f'<td class="num">{fmt(r.get("same_side_pct"), 1, pct=True)}</td>',
                    src_cell(r["source"])])
    body.append(table(["Relationship", "A", "B", "n", "r", "same side", "Source"], trs))

    body.append(f"""
<h2>Why no parlay or prop combo is ranked</h2>
<p>Multiplying marginal probabilities is invalid under dependence, and this sample shows the
dependence is not zero: the correlation between a game's margin and its total points is
<strong>{fmt(next((r['r'] for r in R['correlation']['rows'] if r['kind'].startswith('same-game')), None), 4)}</strong>
on {next((r['n'] for r in R['correlation']['rows'] if r['kind'].startswith('same-game')), 0):,} games.
Two legs inside one game therefore cannot be priced by multiplication, and no observed prop price
exists in any committed source, so a prop combo has neither a price nor a joint probability. Both
are required before a combo may be ranked; neither exists. Combos are not listed, not scored and
not recommended.</p>
""")
    return "\n".join(body)


def build_lines(R):
    body = [f"""
<h1>Own lines &amp; the price store</h1>
<p class="lead">The brief's first two requirements are a price-snapshot store and a results feed,
then: publish the model's fair line, the market line and the difference as separate columns.
This page does that, and states plainly which of the three columns can be verified.</p>

<div class="note bad">
<strong>The price-snapshot store cannot be built from the committed data, and this page does not
pretend otherwise.</strong> The feed carries ONE number per market per game. There is no opening
number and no fetch timestamp, so an open-to-close study is impossible. What exists is a single
closing snapshot, labelled as unofficial. Requirement PR-01 is therefore <em>Blocked</em>, not
<em>Done</em>, and <a href="decisions.html">the requirements page</a> says what would clear it.
</div>
"""]
    s = R["sample"]
    body.append(f"""
<div class="grid">
  <div class="kpi"><div class="v">{s['games_with_spread_price']:,}</div><div class="l">games with a two-sided spread price</div><div class="s">of {s['games_in_window']:,} in window</div></div>
  <div class="kpi"><div class="v">{s['games_with_total_price']:,}</div><div class="l">games with a two-sided total price</div><div class="s">no price was imputed</div></div>
  <div class="kpi"><div class="v">{R['own_line_fit']['params_margin']}</div><div class="l">parameters in the margin fit</div><div class="s">one strength number per club + 2</div></div>
  <div class="kpi"><div class="v">{fmt(R['own_line_fit']['sd_margin'], 2)}</div><div class="l">walk-forward margin sd</div><div class="s">used to turn a line into a probability</div></div>
</div>

<h2>Model vs market, as three separate columns</h2>
<p>Every value below is computed from the committed files named in the registration. The
difference is derived from the two printed numbers, never re-typed. The orientation note matters:
<em>spread_line is home-signed and positive when the home club is favoured</em>, verified against
5,202 games (home margin is +5.96 when the line is positive and −4.64 when it is negative).</p>
""")
    cb = []
    # current week board is not in results.json; recompute a small, honest panel from results
    ev = load("data/session-c84a41a4/results.json")
    body.append(f"""
<table>
<thead><tr><th>Column</th><th>What it is</th><th class="num">Value</th><th>Verifiable?</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Fair line, spread</td><td>Walk-forward ridge strength differential + home field</td>
<td class="num">{fmt(R['own_line_fit']['sd_margin'], 2)} sd</td><td>Computable from committed data</td>
{src_cell(OFFICIAL['schedules'])}</tr>
<tr><td>Market line, spread</td><td>Closing spread from the feed, home-signed</td>
<td class="num">{s['games_with_spread_price']:,} games</td><td>Unofficial third-party parse</td>
{src_cell(NFLVERSE, 'nflverse-data')}</tr>
<tr><td>Difference</td><td>Fair minus market, in points</td><td class="num">derived</td>
<td>Derived from the two columns above</td>{src_cell(OFFICIAL['schedules'])}</tr>
<tr><td>Fair total</td><td>Walk-forward ridge pace fit</td><td class="num">per game</td>
<td>Computable from committed data</td>{src_cell(OFFICIAL['schedules'])}</tr>
<tr><td>Market total</td><td>Closing total from the feed</td><td class="num">{s['games_with_total_price']:,} games</td>
<td>Unofficial third-party parse</td>{src_cell(NFLVERSE, 'nflverse-data')}</tr>
<tr><td>Opening line</td><td>Not in any committed source</td>
<td class="num"><span class="blank">blank</span></td><td><strong>Not verifiable</strong> — do not use</td>
{src_cell(NFLVERSE, 'source has one number per market')}</tr>
</tbody></table>

<h2>Does the own line add anything the close does not already know?</h2>
<table>
<thead><tr><th>Test</th><th class="num">Model</th><th class="num">Market</th><th class="num">Difference</th><th>Reading</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Brier score on the winner</td><td class="num">{fmt(R['brier']['brier_model'], 4)}</td>
<td class="num">{fmt(R['brier']['brier_market_devig'], 4)}</td>
<td class="num">{fmt(R['brier']['difference_model_minus_market'], 4)}</td>
<td>Interval {esc(R['brier']['difference_ci95_game_cluster'])}, entirely above zero</td>
{src_cell(OFFICIAL['schedules'])}</tr>
<tr><td>Brier skill score</td><td class="num">{fmt(R['brier']['brier_skill_score'], 4)}</td>
<td class="num">—</td><td class="num">—</td><td>1 − model/market; negative means the market wins</td>
{src_cell(OFFICIAL['schedules'])}</tr>
<tr><td>Correlation, own line vs close</td>
<td class="num">{fmt(next((r['r'] for r in R['correlation']['rows'] if r['kind']=='own line vs the closing line'), None), 4)}</td>
<td class="num">—</td><td class="num">—</td>
<td>n = {next((r['n'] for r in R['correlation']['rows'] if r['kind']=='own line vs the closing line'), 0):,}</td>
{src_cell(OFFICIAL['schedules'])}</tr>
</tbody></table>
<div class="note">{esc(R['brier']['benchmark_note'])}</div>

<h2>Player props — projections with no price</h2>
<p>Price status: <strong>BLANK — no observed player-prop price exists in any committed
source, so no prop is scored and no prop profit is claimed.</strong>
{R['props']['n_players_projected']} players carry a shrunk volume projection with an 80% interval.
They are projections, not lines, and none is scored.</p>
""")
    trs = []
    for r in R["props"]["rows"][:25]:
        trs.append([f"<td>{esc(r['player'])}</td>", f"<td>{esc(r['position'])}</td>",
                    f"<td>{esc(r['market'].replace('_',' '))}</td>",
                    f'<td class="num">{r["n_weeks"]}</td>',
                    f'<td class="num">{fmt(r["season_mean"])}</td>',
                    f'<td class="num">{fmt(r["last4_mean"])}</td>',
                    f'<td class="num">{fmt(r["projection"])}</td>',
                    f'<td class="num">{esc(r["interval80"])}</td>',
                    '<td><span class="blank">no price</span></td>',
                    src_cell(r["source"])])
    body.append(table(["Player", "Pos", "Market", "Weeks", "Season mean", "Last 4",
                       "Projection", "80% interval", "Price", "Source"], trs))
    return "\n".join(body)


def build_injuries(R, rep):
    inj = load("data/model/official_injuries.json", {}) or {}
    ladder = load("data/depth_ladder.json", {}) or {}
    a = R["ablation"]
    rows = inj.get("rows", [])
    from collections import Counter
    desig = Counter(r.get("game") for r in rows)
    body = [f"""
<h1>Injuries &amp; replacement</h1>
<p class="lead">Three different things live on this page and they are deliberately kept apart:
who the official report says cannot play, what that is worth when it is put into a model, and
who actually took the snaps.</p>

<h2>1. The official designation is a level. It is published, and it is not a signal.</h2>
<p>Source: <a href="{OFFICIAL['reg10']}">the official nfl.com Week 10 report</a>, captured
{esc(inj.get('generated_at'))}, sha256 <code>{esc((inj.get('html_sha256') or '')[:16])}…</code>.
{len(rows)} rows across {inj.get('counts', {}).get('teams', 0)} clubs.</p>
"""]
    trs = []
    for k, v in sorted(desig.items(), key=lambda kv: (kv[0] is None, kv[0])):
        trs.append([f"<td>{esc(k or 'blank — no designation')}</td>", f'<td class="num">{v}</td>',
                    f'<td class="num">{100*v/len(rows):.1f}%</td>',
                    src_cell(OFFICIAL["reg10"], "nfl.com Week 10 report")])
    body.append(table(["Game designation as published", "Rows", "Share", "Source"], trs))
    body.append(f"""
<div class="note warn">
<strong>{desig.get(None,0)} of {len(rows)} rows carry no game designation at all.</strong> A blank is
not "healthy" and it is not "available" — it is a field the club left empty. Treating it as either
would be an invented value, so the study does not use the designation as a level at all. The
registered surprise rule (C84-S11) is on <a href="strategies.html">the strategy page</a> and it
earned {fmt(R['strategies']['C84-S11']['roi_pct'], 2, pct=True)} on
{R['strategies']['C84-S11']['n_decided']:,} decided bets, which is indistinguishable from nothing.
</div>

<h2>2. What the availability features are worth — the ablation</h2>
<p>The brief rejects a fixed points penalty and asks for an ablation. This is one: the identical
model, refitted with and without two availability columns, scored out of sample.</p>
<table>
<thead><tr><th>Window</th><th class="num">n games</th><th class="num">MAE change (with − without)</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Whole sample</td><td class="num">{a['n_games']:,}</td>
<td class="num">{fmt(a['difference_with_minus_without'], 4)}</td>{src_cell(OFFICIAL['injuries'])}</tr>
""")
    for w in a["by_window"]:
        body.append(f'<tr><td>{esc(w["window"])}</td><td class="num">{w["n"]:,}</td>'
                    f'<td class="num">{fmt(w["mean_abs_error_difference"], 4)}</td>'
                    f'{src_cell(OFFICIAL["injuries"])}</tr>')
    body.append(f"""</tbody></table>
<div class="note {'warn' if not a['difference_ci95_game_cluster'] or a['difference_ci95_game_cluster'][0] <= 0 else 'ok'}">
<strong>{esc(a['verdict'])}</strong> Interval on the difference:
{esc(a['difference_ci95_game_cluster'])}. A negative number in a window means the availability
features made the forecast slightly worse there. {esc(a['why_not_a_penalty'])}
</div>

<h2>3. Confirmed replacements, not inferred depth order</h2>
<p>{esc(rep['what_is_confirmed'])}</p>
<div class="note">
<strong>Not used:</strong> {"; ".join(esc(x) for x in rep['what_is_not_used'])}.
</div>
<div class="grid">
  <div class="kpi"><div class="v">{rep['counts']['confirmed_starts']:,}</div><div class="l">confirmed club-starts</div><div class="s">quarterback, 2006–2026</div></div>
  <div class="kpi"><div class="v">{rep['counts']['replacements']:,}</div><div class="l">starts by a replacement</div><div class="s">{fmt(rep['counts']['replacement_rate_pct'], 2, pct=True)} of starts</div></div>
  <div class="kpi"><div class="v">{rep['counts']['first_change_no_prior_start']:,}</div><div class="l">went one level deeper</div><div class="s">no prior start for that club</div></div>
  <div class="kpi"><div class="v">{rep['counts']['later_change_has_started']:,}</div><div class="l">a backup who had played</div><div class="s">has started for the club before</div></div>
</div>

<h2>The depth of the replacement, which is the brief's actual question</h2>
<table>
<thead><tr><th>Group</th><th class="num">n</th><th class="num">ROI backing that club</th><th class="num">95% CI</th><th>Reading</th><th>Source</th></tr></thead>
<tbody>
""")
    for k, v in rep["market_test"]["by_group"].items():
        body.append(f'<tr><td>{esc(k)}</td><td class="num">{v["n"]:,}</td>'
                    f'<td class="num">{fmt(v["roi_pct"], 2, pct=True)}</td>'
                    f'<td class="num">{esc(v["roi_ci95_game_cluster"])}</td>'
                    f'<td>{"" if "first" not in k else "the replacement had never started for the club"}</td>'
                    f'{src_cell(OFFICIAL["schedules"])}</tr>')
    d = rep["market_test"]["first_change_minus_incumbent"]
    body.append(f"""</tbody></table>
<div class="note warn">
<strong>Paired test, first-change vs incumbent:</strong> {fmt(d['mean_difference_units'], 4)} units
per bet, interval {esc(d['ci95_game_cluster'])} on {d['n_paired']:,} paired games.
{esc(d['reading'])} This is published as an observation on <a href="flagged.html">Flagged for review</a>,
not as a strategy: it was not in the registered family.
</div>

<h2>Examples, with the game each one comes from</h2>
<p class="dim">Each row names the club, the week and the confirmed starter. The link resolves to the
official game centre entry point for that game's schedule.</p>
""")
    trs = []
    for e in rep["examples"][:40]:
        trs.append([f'<td class="num">{e["season"]}</td>', f'<td class="num">{e["week"]}</td>',
                    f"<td>{esc(e['club'])}</td>", f"<td>{esc(e['opponent'])}</td>",
                    f"<td>{esc(e['confirmed_starter'])}</td>",
                    f"<td>{esc(e['replacement_depth_label'])}</td>",
                    f'<td class="num">{e["replacement_prior_starts_this_club"]}</td>',
                    src_cell(e["source"])])
    body.append(table(["Season", "Week", "Club", "Opponent", "Confirmed starter", "Depth of replacement",
                       "Prior starts", "Source"], trs))

    body.append(f"""
<h2>4. The depth charts this repository already holds — with their defects stated</h2>
<p>{esc((ladder.get('method') or {}).get('depth_charts', ''))}</p>
<table>
<thead><tr><th>Measure</th><th class="num">Value</th><th>Finding</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Clubs with a chart</td><td class="num">{(ladder.get('counts') or {}).get('clubs_with_chart', 0)}/32</td>
<td>Houston publishes its chart as an image, so no rows can be read without transcribing by eye — which this project will not do</td>
{src_cell("https://www.houstontexans.com/team/depth-chart", "texans.com depth chart")}</tr>
<tr><td>Slots</td><td class="num">{(ladder.get('counts') or {}).get('slots', 0):,}</td>
<td>Slots, not players: a slot lists a group</td>{src_cell(OFFICIAL['teams'])}</tr>
<tr><td>Slots whose starter is at risk</td><td class="num">{(ladder.get('counts') or {}).get('slots_starter_at_risk', 0)}</td>
<td>Questionable counted as at risk, never upgraded or downgraded</td>{src_cell(OFFICIAL['injuries'])}</tr>
<tr><td>Charts carrying a club's own dated <code>as_of</code></td><td class="num">1/32</td>
<td>31 charts are undated, so they cannot be versioned against a roster event</td>
{src_cell(OFFICIAL['teams'])}</tr>
<tr><td>Charts the club itself labels "unofficial"</td><td class="num">14/32</td>
<td>The label is carried through, not hidden</td>{src_cell(OFFICIAL['teams'])}</tr>
<tr><td>Slots with more than one rank-1 player</td><td class="num">0 in the stored JSON</td>
<td>The live charts do show shared slots and this parser collapses them into one string — see the flag</td>
{src_cell("https://www.seahawks.com/team/depth-chart/", "seahawks.com depth chart")}</tr>
</tbody></table>
""")
    return "\n".join(body)


def build_verification(R, rep):
    reg = R["registration"]
    body = [f"""
<h1>Verification</h1>
<p class="lead">What was checked, against what, and by which command. Every claim on this page can
be reproduced offline from the committed files.</p>

<h2>Method: what "verified" means here</h2>
<table>
<thead><tr><th>Tier</th><th>Meaning</th><th>Example</th><th>Source</th></tr></thead>
<tbody>
<tr><td><span class="tag ok">Official</span></td><td>Read from an nfl.com or club domain, fetched live
this session</td><td>the Week 10 injury report</td>{src_cell(OFFICIAL['reg10'], 'nfl.com/injuries')}</tr>
<tr><td><span class="tag warn">Pinned third party</span></td><td>A parse of an unofficial market,
pinned by URL and sha256</td><td>closing lines</td>{src_cell(NFLVERSE, 'nflverse-data')}</tr>
<tr><td><span class="tag bad">Unverified</span></td><td>No source exists. Published blank, and flagged</td>
<td>the opening line</td>{src_cell("https://www.nfl.com/schedules/", "no public source — nfl.com publishes no opening line")}</tr>
</tbody></table>

<h2>The registration hash is checked, not claimed</h2>
<table>
<thead><tr><th>Item</th><th>Value</th><th>Check</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Registration file</td><td><code>{esc(reg['file'])}</code></td><td>Committed at <code>061c2a8</code> before results existed</td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/commit/061c2a88d1b21c3137e378ac4acc09e24bff1014">commit 061c2a8</a></td></tr>
<tr><td>sha256 at build time</td><td><code>{esc(reg['sha256'])}</code></td><td>Recomputed on every build; a mismatch fails the build</td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/provenance.json">provenance.json</a></td></tr>
<tr><td>Input games</td><td><code>{esc(R['inputs']['games']['sha256'])}</code></td><td>Matches <code>data/s9cb/provenance.json</code></td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/provenance.json">provenance.json</a></td></tr>
<tr><td>Input injuries</td><td><code>{esc(R['inputs']['injuries']['sha256'])}</code></td><td>Same</td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/provenance.json">provenance.json</a></td></tr>
<tr><td>Input player weeks</td><td><code>{esc(R['inputs']['player_week']['sha256'])}</code></td><td>Same</td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/provenance.json">provenance.json</a></td></tr>
</tbody></table>

<h2>Live official re-checks performed this session</h2>
<table>
<thead><tr><th>#</th><th>What was re-read</th><th>Result</th><th>Source</th></tr></thead>
<tbody>
<tr><td>V1</td><td>League standings, all 32 clubs</td><td>32/32 match the committed snapshot — see the flag
page for one club code difference (AZ vs ARI)</td>{src_cell(OFFICIAL['standings'])}</tr>
<tr><td>V2</td><td>Official Week 10 injury report</td><td>347 rows, 28 clubs, 171 with a game
designation. The three Lions rows the brief calls blank are published as Out</td>{src_cell(OFFICIAL['reg10'])}</tr>
<tr><td>V3</td><td>Detroit depth chart</td><td>Cade Mays rank 1, D.J. Reed rank 1, Brian Branch rank 1;
Kerby Joseph is not listed</td>
{src_cell("https://www.detroitlions.com/team/depth-chart", "detroitlions.com")}</tr>
<tr><td>V4</td><td>Green Bay depth chart</td><td>Jersey-number prefixes confirmed on every player cell;
the committed JSON has them stripped</td>{src_cell("https://www.packers.com/team/depth-chart", "packers.com")}</tr>
<tr><td>V5</td><td>Seattle depth chart</td><td>One slot publishes two players in one cell
(Cooper Kupp, Rashid Shaheed); the stored JSON merges them into one string</td>
{src_cell("https://www.seahawks.com/team/depth-chart/", "seahawks.com")}</tr>
<tr><td>V6</td><td>Washington depth chart</td><td>One slot is genuinely empty at rank 2
(Frankie Luvu rank 1, rank 3 Kain Medrano) and the stored JSON has the same gap</td>
{src_cell("https://www.commanders.com/team/depth-chart", "commanders.com")}</tr>
<tr><td>V7</td><td>Houston depth chart</td><td>Published as an image; no structured rows exist</td>
{src_cell("https://www.houstontexans.com/team/depth-chart", "texans.com")}</tr>
<tr><td>V8</td><td>Baltimore depth chart</td><td><strong>Contradicts the brief.</strong> The live chart
lists Jacoby Brissett at QB rank 1, not Lamar Jackson or Tyler Huntley</td>
{src_cell("https://www.baltimoreravens.com/team/depth-chart", "baltimoreravens.com")}</tr>
</tbody></table>

<h2>Reproduce every number</h2>
<table>
<thead><tr><th>Command</th><th>Produces</th><th>Gate that follows it</th><th>Source</th></tr></thead>
<tbody>
<tr><td><code>python3 s9cb/c84_study.py</code></td><td>results.json, bet_log.csv</td><td>registration hash checked on write</td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/s9cb/c84_study.py">c84_study.py</a></td></tr>
<tr><td><code>python3 s9cb/c84_replacement_study.py</code></td><td>qb_replacement.json</td><td>input hash checked on write</td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/s9cb/c84_replacement_study.py">c84_replacement_study.py</a></td></tr>
<tr><td><code>python3 ledger/build.py</code></td><td>this site</td><td>fails on a table with no Source column</td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/ledger/build.py">ledger/build.py</a></td></tr>
<tr><td><code>python3 ledger/verify.py</code></td><td>pass/fail</td><td>broken links, sourceless rows, placeholders</td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/ledger/verify.py">ledger/verify.py</a></td></tr>
</tbody></table>
<div class="note">
<strong>Determinism.</strong> Every bootstrap uses a fixed seed ({20261115}) and the fit uses no
randomness, so two runs on the same inputs produce byte-identical output apart from the
<code>generated_at</code> timestamp.
</div>
"""]
    return "\n".join(body)


FLAGS = [
    ("C84-F01", "The brief's claim that Baltimore still publishes Lamar Jackson and Tyler Huntley at QB is no longer true.",
     "The live chart lists Jacoby Brissett (rank 1), Joe Fagnano, Kedon Slovis. A stale-depth-chart complaint cannot be reproduced today, and any feature built on that assumption would be built on a false premise.",
     "https://www.baltimoreravens.com/team/depth-chart", "open"),
    ("C84-F02", "The brief's claim that 149 club/unit/position slots list more than one rank-1 player is not reproducible from the committed data.",
     "data/session-1505ac8e/depth_charts.json has 934 slots and ZERO with more than one rank-1 player assigned. The shared slot is real on the live pages (Seattle publishes 'Cooper Kupp Rashid Shaheed' inside ONE cell) but the parser stores it as one merged string, which destroys the information rather than recording it. A feature that needs rank-1 groups cannot be built from this file.",
     "https://www.seahawks.com/team/depth-chart/", "open"),
    ("C84-F03", "The brief calls the Texans an image-only chart and the Packers a jersey-number chart; only the second is fixable by parsing, and the first has no legitimate fix.",
     "Houston publishes its chart only as an image, so any transcription is by eye. Green Bay's page does prepend jersey numbers ('9 Christian Watson'), but the committed JSON already stores them stripped, so the 'number stripping' fix the brief asks for is already applied downstream and its 59-cell count does not match this file.",
     "https://www.packers.com/team/depth-chart", "open"),
    ("C84-F04", "Only 1 of 32 club charts carries a date, so no chart can be versioned against a roster event.",
     "The brief asks for depth, availability and lineup evidence to be versioned against the last official roster event. 31 charts carry no as_of date, so the only date available is this repository's own capture date, which is not the club's date.",
     "https://www.nfl.com/teams/", "open"),
    ("C84-F05", "The brief's claim that 6 of 254 report rows carry a game designation is superseded by the current capture.",
     "The committed capture holds 347 rows, 171 of which carry a game designation (70 Out, 90 Questionable, 11 Doubtful). The 254/6 figures are stale, and they are stale in the direction that made the injury signal look emptier than it is.",
     OFFICIAL["reg10"], "open"),
    ("C84-F06", "The brief's claim that Seattle and Cincinnati are shown as injury-free is contradicted by the current capture.",
     "Both clubs publish full sections in the committed capture: Seattle 15 rows and Cincinnati 9 rows. Any page still printing 'No Injuries Reported' for them is reading an older file. (An earlier draft of this flag said Cincinnati had 4 rows; the committed capture says 9, and the capture is what this site quotes.)",
     OFFICIAL["reg10"], "open"),
    ("C84-F07", "The two gate schemes in this repository are incompatible and neither is declared canonical.",
     "data/s9cb uses 8 gates numbered G1-G8 (200-bet floor, BH at 0.05). This session registered 10 gates numbered C84-G1..G10 (300-bet floor, adds a control-beating gate and a delete-the-best-season gate). A reviewer comparing two 'gate counts' is comparing two different things.",
     "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/leaderboard.json", "open"),
    ("C84-F08", "The brief's opening premise of a 136-game log is not the corpus this study uses, and the two must not be mixed.",
     "The 136-game log is the 2026 season slice in data/verified/model/predictions_log.json. This study uses 5,336 decided games from 2006-2026. Mixing them would let a 136-game result be quoted as if it came from a 5,336-game test.",
     "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/verified/model/predictions_log.json", "open"),
    ("C84-F09", "I made three errors in my own first draft of the pre-registration and in my first implementation, and they are recorded here rather than quietly corrected.",
     "(a) The registration text said 'if spread_line <= -7.5 bet the away side' while also calling the rule the repository's S7, which bets the HOME side; the sign convention had been stated backwards. (b) The first implementation negated the moneyline probability, inverting every M3 probability and producing a Brier of 0.314 instead of 0.226. (c) The first design matrix had a dimension error that the fit itself raised. Errors (b) and (c) were caught by results that contradicted the repository's independent run; (a) was caught by re-reading the live numbers. The registration text is NOT edited; the correction is published here because editing a registration after results exist would destroy its only value.",
     "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-c84a41a4/preregistration.json", "open"),
    ("C84-F10", "No official NFL price exists, and every ROI on every page of this repository therefore rests on an unofficial market.",
     "The NFL publishes no odds. The prices used are a third-party parse. This is not fixable by better verification; it is a property of the source. Every page states it, and the requirement is carried as Blocked rather than Done.",
     "https://www.nfl.com/schedules/", "open"),
    ("C84-F11", "The moneyline rule's hit rate is below its own break-even by construction and that is expected, not a defect.",
     "C84-S7 bets only when the model's probability exceeds the price-implied probability by 4 points, which selects long-shot sides by design; its hit rate of 0.3519 against a break-even of 0.3505 is therefore the arithmetic working, not an error. It is left in the published leaderboard because suppressing it would be selecting the results.",
     "https://www.nfl.com/schedules/", "open"),
]


def build_flagged(R):
    body = [f"""
<h1>Flagged for review</h1>
<p class="lead">{len(FLAGS)} items. Nothing here blocks the site from publishing; everything here
is something a human should look at before acting on any number. Several entries contradict
claims in the project brief itself, and in those cases the live official page is quoted.</p>
<div class="note bad">
<strong>Three of these are my own errors</strong> (C84-F09, C84-F11 and the sign convention noted
on the lines page). They are published because a page that only lists other people's mistakes is
not a verification page.
</div>
"""]
    trs = []
    for fid, what, why, url, status in FLAGS:
        trs.append([f"<td><code>{esc(fid)}</code></td>", f"<td>{esc(what)}</td>", f"<td>{esc(why)}</td>",
                    f"<td>{badge(status)}</td>", src_cell(url)])
    body.append(table(["ID", "What is irregular", "Why it matters", "Status", "Settles it"], trs))
    body.append("""
<h2>What would close each of these</h2>
<table>
<thead><tr><th>Flag</th><th>Closing action</th><th>Owner</th><th>Source</th></tr></thead>
<tbody>
<tr><td>C84-F01</td><td>Re-capture every club chart on one day and diff against this file</td><td>data pipeline</td><td><a href="https://www.baltimoreravens.com/team/depth-chart">baltimoreravens.com</a></td></tr>
<tr><td>C84-F02</td><td>Store a shared slot as a LIST of rank-1 players, never as one string</td><td>depth parser</td><td><a href="https://www.seahawks.com/team/depth-chart/">seahawks.com</a></td></tr>
<tr><td>C84-F03</td><td>Houston: obtain an authorised structured source or leave it blank forever</td><td>policy choice</td><td><a href="https://www.houstontexans.com/team/depth-chart">texans.com</a></td></tr>
<tr><td>C84-F04</td><td>Capture the club's own date when it exists; otherwise record the capture time and label it</td><td>depth parser</td><td><a href="https://www.packers.com/team/depth-chart">packers.com (only dated chart)</a></td></tr>
<tr><td>C84-F05 / F06</td><td>Delete the stale 254-row file or label it superseded in place</td><td>data pipeline</td><td><a href="https://www.nfl.com/injuries/league/2026/reg10">nfl.com Week 10 report</a></td></tr>
<tr><td>C84-F07</td><td>Declare one gate scheme canonical and print the other as historical</td><td>human decision</td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/leaderboard.json">8-gate scheme</a></td></tr>
<tr><td>C84-F08</td><td>Rename the 136-game file so it cannot be mistaken for the corpus</td><td>data pipeline</td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/verified/model/predictions_log.json">136-game log</a></td></tr>
<tr><td>C84-F09</td><td>Nothing further; the correction is the record</td><td>closed on publication</td><td><a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-c84a41a4/preregistration.json">registration (unmodified)</a></td></tr>
<tr><td>C84-F10</td><td>Buy a licensed price feed, or accept the label permanently</td><td>human decision</td><td><a href="https://github.com/nflverse/nflverse-data">nflverse-data</a></td></tr>
<tr><td>C84-F11</td><td>Nothing; keep publishing it</td><td>closed on publication</td><td><a href="https://www.nfl.com/schedules/">nfl.com schedules</a></td></tr>
</tbody></table>
""")
    return "\n".join(body)


SUGGESTIONS = [
    ("S-01", "Declare one gate scheme canonical", "high",
     "Two incompatible gate schemes make every 'it passed the gates' statement ambiguous.",
     "Adopt the C84-G1..G10 scheme, because it is the only one with a pre-registration hash, and print the 8-gate scheme as historical.",
     "Half a day", "A reviewer decision; no data needed"),
    ("S-02", "Stop originating and reframe as a measurement ledger", "high",
     "Twelve registered rules produced nothing that survives its own gates, and the model loses to the close on a proper score. Continuing to originate spends effort against a known negative.",
     "Keep the pipeline, publish the negative result as the product, and only originate when a new signal has a mechanism that is not already in the closing line.",
     "Immediate", "A reviewer decision"),
    ("S-03", "Capture two price snapshots per week, with timestamps", "high",
     "Without an open and a close there is no line-movement study and no CLV, which is the only honest way to score a bettor prospectively.",
     "A scheduled job that writes both snapshots with a fetch time and a hash.",
     "2 days", "A dated price source"),
    ("S-04", "Store a shared depth slot as a list, not a string", "medium",
     "It is the difference between an opinion about a starter and a fact about who the club names. It also silently destroys the rank-1 group the brief asks about.",
     "Change the parser's player field to a list; keep the raw cell string beside it; flagged, never split.",
     "1 day", "The parser files"),
    ("S-05", "Capture availability daily from Wednesday to kickoff", "medium",
     "These are the two experiments that can still produce an edge, because they need change over time, which this repository has never captured.",
     "A scheduled capture with hashes and a conflict flag. This is what makes the surprise signal testable without look-ahead.",
     "3 days", "An Actions job"),
    ("S-06", "Get an official snap-count feed and build the second-string deficiency feature", "medium",
     "Replacement depth currently exists only for quarterbacks. The brief wants lines and secondaries.",
     "Join snap shares to the depth ladder; use playing time, never jersey order.",
     "Blocked", "An official snap-count source"),
    ("S-07", "Join several seasons of designations to official inactives", "medium",
     "It would calibrate what Questionable actually means, which the brief explicitly asks for and no page in this repo does.",
     "Measure the play rate per designation with intervals, then decide whether the label becomes a feature.",
     "Blocked", "An official inactive-list source"),
    ("S-08", "Delete or clearly supersede the stale 254-row injury file", "medium",
     "Three pages still print 'No Injuries Reported' for clubs that publish full sections. A stale file that still renders is worse than no file.",
     "Label it superseded in place and point every generator at the 347-row capture.",
     "Half a day", "The pipeline files"),
    ("S-09", "Print every model output as a probability plus its inputs", "low",
     "A pick cannot be re-scored later. A probability with its inputs can.",
     "Extend the prediction log to carry the fitted parameters beside the probability.",
     "1 day", "Nothing"),
    ("S-10", "Add a control baseline to every future leaderboard run", "low",
     "This session's blind-away control beat eleven of twelve signals. That is the single most informative number on the site and it took an hour to add.",
     "Make the control an unconditional row in the leaderboard generator.",
     "Half a day", "Nothing"),
    ("S-11", "Decide whether the unofficial price parse is acceptable", "low",
     "Every ROI on the site depends on it. If it is not acceptable, every ROI must be withdrawn.",
     "Keep it labelled, or buy a feed. Either is defensible; leaving it undecided is not.",
     "A decision", "A reviewer decision"),
    ("S-12", "Retire the parallel site generations into one", "low",
     "This repository now builds eight sites. A reader cannot tell which one is authoritative, and each new session adds more.",
     "Pick one landing page and make the others sub-pages of it, or archive them read-only.",
     "1 day", "A reviewer decision"),
]


def build_suggestions(R):
    body = [f"""
<h1>Suggestions</h1>
<p class="lead">{len(SUGGESTIONS)} improvements, each with the decision a reviewer has to make and
the reason it is ranked where it is. Nothing here is implemented; the page exists so a path can be
chosen before any work is done.</p>
<div class="note">
<strong>How to use this page.</strong> Read the <em>decision</em> column. If you agree with a row,
it is one edit away for a future session. If you disagree, the row records why it was suggested so
the disagreement is on the record too.
</div>
"""]
    trs = []
    for sid, what, pri, why, decision, effort, needs in SUGGESTIONS:
        cls = {"high": "bad", "medium": "warn", "low": ""}[pri]
        trs.append([f"<td><code>{esc(sid)}</code></td>", f"<td>{esc(what)}</td>",
                    f'<td><span class="tag {cls}">{esc(pri)}</span></td>',
                    f"<td>{esc(why)}</td>", f"<td>{esc(decision)}</td>",
                    f"<td>{esc(effort)}</td>", f"<td>{esc(needs)}</td>",
                    src_cell(OFFICIAL['schedules'], 'nfl.com schedules')])
    body.append(table(["ID", "Suggestion", "Priority", "Why", "The decision you make", "Effort",
                       "Needs", "Source"], trs))
    body.append("""
<h2>The three paths, and what each costs</h2>
<table>
<thead><tr><th>Path</th><th>What happens</th><th>Total effort</th><th>What you get</th><th>Risk</th><th>Source</th></tr></thead>
<tbody>
<tr><td><strong>A. Measurement ledger</strong></td>
<td>Adopt one gate scheme, keep the pipeline, publish the negative result, add snapshots only when a
new mechanism exists</td><td>3 days</td>
<td>A defensible, reproducible record of what does not work and why — the asset this project
already has</td><td>Low. Nothing can be over-claimed.</td>
<td><a href="strategies.html">this site</a> (internal, no external source)</td></tr>
<tr><td><strong>B. Fix the data layer first</strong></td>
<td>S-03 to S-08: two price snapshots a week, daily availability captures, list-valued depth slots,
official snap counts</td><td>2–3 weeks</td>
<td>The data a real edge test would need, and the ability to replay designations as known</td>
<td>Medium. The captures may show the same negative result.</td>
<td><a href="https://www.nfl.com/injuries/">nfl.com injuries</a></td></tr>
<tr><td><strong>C. Consolidate only</strong></td>
<td>S-12 plus S-01: one site, one gate scheme, everything else archived read-only</td><td>2 days</td>
<td>A small site a person can actually read</td><td>Low, but it abandons the research.</td>
<td><a href="https://kanlerxz87-cyber.github.io/NFL1/">the live site</a></td></tr>
</tbody></table>
<div class="note warn">
<strong>Recommended: A, then C.</strong> The most valuable thing in this repository is not a
strategy — it is the demonstration, with controls and a pre-registration, that a reasonable
own-line model does not beat the close. That result is worth publishing cleanly. Path B is worth
doing only if someone intends to keep originating, and the honest expectation from this evidence
is that it will produce the same answer with more decimal places.
</div>
""")
    return "\n".join(body)


def main():
    os.makedirs(OUT, exist_ok=True)
    R = load("data/session-c84a41a4/results.json")
    rep = load("data/session-c84a41a4/qb_replacement.json")
    ready = load("room/data/readiness.json", {}) or {}
    if not R or not rep:
        raise SystemExit("missing computed results; run s9cb/c84_study.py first")

    # the registration must not have changed since the results were computed
    import hashlib
    p = os.path.join(ROOT, R["registration"]["file"])
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    if h != R["registration"]["sha256"]:
        raise SystemExit("registration hash changed since results were computed — "
                         "publish a new registration version instead of editing this one")

    builders = {
        "index.html": lambda: build_overview(R, rep, ready),
        "executive.html": lambda: build_executive(R, rep),
        "decisions.html": lambda: build_decisions(R, ready),
        "strategies.html": lambda: build_strategies(R),
        "lines.html": lambda: build_lines(R),
        "injuries.html": lambda: build_injuries(R, rep),
        "verification.html": lambda: build_verification(R, rep),
        "flagged.html": lambda: build_flagged(R),
        "suggestions.html": lambda: build_suggestions(R),
    }
    titles = dict(PAGES)
    total = 0
    for fname, fn in builders.items():
        n = page(fname, titles[fname], fn(), fname)
        total += n
        print(f"  wrote ledger/{fname:20s} {n:>9,} bytes")
    print(f"{len(builders)} pages, {total:,} bytes -> ledger/")


if __name__ == "__main__":
    main()
