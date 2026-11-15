#!/usr/bin/env python3
"""Render the prereg/*.html pages from the JSON data layer (session 0c5215c1-nfl1).

Run: python3 prereg/build.py
Owner of output: this script (see tools/check_generators.py — prereg/ is a new,
single-owner sub-site; no other generator writes these paths).
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "prereg")

NAV = [("index.html", "Overview & prospective board"),
       ("registry.html", "Registry (all entries)"),
       ("forecasts.html", "Forecast record"),
       ("archive.html", "Backtest archive")]


def jload(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def link(url: str, label: str | None = None) -> str:
    host = url.replace("https://", "").split("/")[0]
    return f'<a href="{esc(url)}" rel="noopener">{esc(label or host)}</a>'


def page(name: str, title: str, body: str, active: str) -> str:
    nav = " · ".join(
        f'<a href="{u}"{" class=active" if u == active else ""}>{esc(t)}</a>'
        for u, t in NAV)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · NFL1 pre-registration</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <div class="wrap">
    <h1>Pre-registration <span class="sub">NFL1 · strategy freeze ledger</span></h1>
    <nav>{nav}</nav>
    <p class="crumb"><a href="../index.html">NFL1 landing page</a> / {esc(title)}</p>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="wrap">
<p>Session <code>0c5215c1-nfl1</code> · generated {esc(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))} ·
policy: <a href="README.md">prereg/README.md</a> · gate: <code>python3 prereg/verify.py</code> ·
every table row carries its own source link; blank cells are labelled, never inferred.</p>
</footer>
</body>
</html>
"""


def write(name: str, content: str) -> None:
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as fh:
        fh.write(content)


# ----------------------------------------------------------------- overview
def overview(reg, corpus, ctl, fc, sched) -> str:
    kinds = reg["counts"]["by_kind"]
    mc = corpus["membership_counts"]

    # prospective board: prospective + prospective-eligible entries only, no numbers
    board_rows = []
    for e in reg["entries"]:
        r = e["registration"]
        if r["kind"] == "retrospective":
            continue
        if e["entry_type"] == "collection" and r["kind"] == "prospective-eligible":
            status = "registered · no forecasts recorded yet"
            fc_cell = "—"
        elif e["id"] == "SB-01":
            status = "registered · Week 11 forecasts recorded before kickoff"
            fc_cell = link("forecasts.html", "13 forecasts, 2026-11-15")
        else:
            status = "registered · eligible for first evaluation"
            fc_cell = "—"
        board_rows.append(
            f"<tr><td><code>{esc(e['id'])}</code></td><td>{esc(e['strategy'])}</td>"
            f"<td>{esc(r['kind'])}</td>"
            f"<td>{link('https://github.com/kanlerxz87-cyber/NFL1/commit/' + r['commit'], r['commit'][:8])}</td>"
            f"<td>{fc_cell}</td><td>{esc(status)}</td>"
            f"<td>{link(e['source']['u'], e['source']['t'])}</td></tr>")

    return f"""
<section>
<h2>What this page is</h2>
<p>The brief requires: <em>“Pre-register every strategy; forbid backtest numbers from ever
appearing on the leaderboard”</em> and <em>“Freeze a rule before it sees data … the commit hash
is the registration.”</em> This sub-site is the freeze ledger. Historical results live only on
the <a href="archive.html">backtest archive</a>, which is explicitly not a leaderboard.</p>
<ul>
<li><strong>Registration kinds.</strong>
 <code>prospective</code> (registration precedes every forecast and result) ·
 <code>prospective-eligible</code> (never evaluated; first evaluation must cite the hash) ·
 <code>retrospective</code> (rules and results already existed together — disclosure only,
 never a pre-registration claim; flag R26-01 pattern).</li>
<li><strong>Every entry</strong> carries a two-sided <em>what would change our mind</em> field
 (upside trigger + downside trigger) — readiness PR-24.</li>
<li><strong>Corpus.</strong> {esc(corpus['corpus_id'])} — {mc['completed_total']:,} completed
 games frozen with a train/validation/holdout split; the 2025–2026 holdout is
 <strong>closed</strong> until a recorded decision opens it — readiness PR-09.</li>
<li><strong>Controls.</strong> a random-side and a favourites-only control are registered for
 every future board run — readiness PR-17.</li>
</ul>
</section>

<section id="prospective-board">
<h2>Prospective board <span class="tag">registration-hashed · no backtest numbers</span></h2>
<p class="note">Only entries whose registration hash precedes their forecasts may appear here.
Numbers appear <em>only</em> after the forecasts settle. Nothing has settled yet — an empty
scoreboard is the honest state on 2026-11-15.</p>
<table class="data">
<thead><tr><th>Entry</th><th>Strategy</th><th>Kind</th><th>Registered at</th>
<th>Forecasts</th><th>Status</th><th>Source</th></tr></thead>
<tbody>
{''.join(board_rows)}
</tbody></table>
<p class="note">Counts: {kinds.get('prospective', 0)} prospective ·
{kinds.get('prospective-eligible', 0)} prospective-eligible ·
{kinds.get('retrospective', 0)} retrospective entries (the retrospective ones are listed on
the <a href="registry.html">registry</a> and the <a href="archive.html">archive</a>, never
here as ranked results).</p>
</section>

<section>
<h2>Registry at a glance</h2>
<table class="data">
<thead><tr><th>Item</th><th>Value</th><th>Detail</th></tr></thead>
<tbody>
<tr><td>Registered entries</td><td>{reg['counts']['entries']}</td>
<td>{link('registry.html', 'full registry')}</td></tr>
<tr><td>Collections</td><td>{reg['counts']['collections']}</td>
<td>{link('registry.html', 'per-collection registration hashes')}</td></tr>
<tr><td>Frozen corpus</td><td>{esc(corpus['corpus_id'])}</td>
<td>{link('archive.html', 'corpus + controls')}</td></tr>
<tr><td>Holdout (2025–2026)</td><td>closed</td>
<td>{link('archive.html', 'opening rule')}</td></tr>
<tr><td>Forecast record</td><td>SB-01 · 13 games</td>
<td>{link('forecasts.html', 'recorded ' + fc['recorded_at_utc'])}</td></tr>
<tr><td>Official schedule source</td><td>nfl.com Week 11</td>
<td>{link(sched['source_url'], sched['source_url'])}</td></tr>
</tbody></table>
</section>

<section>
<h2>Gate</h2>
<p><code>python3 prereg/verify.py</code> — registration files unchanged since commit
<code>{esc(fc['registration_commit'][:8])}</code>, every forecast timestamped before its kickoff, probabilities reproduce
from stored aggregates, corpus membership recomputes, holdout closed, every entry has both
mind-changer sides, the prospective board prints no ROI/win-rate columns, and every table row
on these pages carries a link.</p>
</section>
"""


# ----------------------------------------------------------------- registry
def registry(reg) -> str:
    rows = []
    for e in reg["entries"]:
        r = e["registration"]
        kind_cls = {"prospective": "k-pro", "prospective-eligible": "k-pre",
                    "retrospective": "k-ret"}[r["kind"]]
        commit = (link(f"https://github.com/kanlerxz87-cyber/NFL1/commit/{r['commit']}",
                       r["commit"][:8]))
        rows.append(
            f"<tr><td><code>{esc(e['id'])}</code></td>"
            f"<td>{esc(e['strategy'])}<br><span class='muted'>{esc(e['entry_type'])} · "
            f"track {esc(e.get('track', ''))}</span></td>"
            f"<td><span class='kind {kind_cls}'>{esc(r['kind'])}</span></td>"
            f"<td>{commit}<br><span class='muted'>{esc(r.get('commit_date', ''))}</span></td>"
            f"<td>{esc(e.get('sample_window', ''))}</td>"
            f"<td class='mind'>{esc(e['would_change_our_mind']['upside'])}</td>"
            f"<td class='mind'>{esc(e['would_change_our_mind']['downside'])}</td>"
            f"<td>{link(e['source']['u'], e['source']['t'])}</td></tr>")
    return f"""
<section>
<h2>Registration registry <span class="tag">{reg['counts']['entries']} entries</span></h2>
<p class="note">Every strategy entry in this repository, with its registration hash and a
two-sided <em>what would change our mind</em> field (readiness PR-15 and PR-24). A
<code>retrospective</code> row means the rules and their results were already committed
together — it is disclosure, not pre-registration, and it can never become prospective under
the same id.</p>
<table class="data wide">
<thead><tr><th>ID</th><th>Strategy</th><th>Kind</th><th>Registered at</th>
<th>Sample window</th><th>What would change our mind — for</th>
<th>What would change our mind — against</th><th>Source</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody></table>
</section>
"""


# ----------------------------------------------------------------- forecasts
def forecasts(fc, sched) -> str:
    byid = {g["game_id"]: g for g in sched["games"]}
    rows = []
    for g in fc["games"]:
        s = byid[g["game_id"]]
        rows.append(
            f"<tr><td>{esc(s['matchup'])}<br><span class='muted'>{esc(g['game_id'])}</span></td>"
            f"<td>{esc(s['day'])} {esc(s['kickoff_local_as_printed'])} ET<br>"
            f"<span class='muted'>{esc(g['kickoff_utc'])}</span></td>"
            f"<td>{g['p_home']:.6f}</td><td><strong>{esc(g['pick'])}</strong></td>"
            f"<td>{esc(s['network'])}</td>"
            f"<td>{link(g['official_url'], g['official_url'])}</td></tr>")
    mfs = "".join(f"<li><code>{esc(k)}</code> sha256 {esc(v)}</li>"
                  for k, v in fc["model_files"].items())
    return f"""
<section>
<h2>SB-01 forecast record <span class="tag k-pro">prospective</span></h2>
<p>Recorded <strong>{esc(fc['recorded_at_utc'])}</strong> — every kickoff in this table is
later than that timestamp (earliest kickoff {esc(min(g['kickoff_utc'] for g in fc['games']))}).
Registration: commit
{link('https://github.com/kanlerxz87-cyber/NFL1/commit/' + fc['registration_commit'], fc['registration_commit'][:8])}
(rule text, policy and model code; <strong>no results in that commit</strong>). Track:
singles only. Model: Pythagorean exponent 2.0, zero free parameters
(<a href="SB-01-rule.md">full rule text</a>).</p>
<ul class="plain">
<li>Input at record time: <code>{esc(fc['input']['file'])}</code> —
sha256 {esc(fc['input']['sha256_at_record'])}, {fc['input']['rows_completed']:,} completed rows.</li>
<li>Official schedule: {link(fc['schedule_source']['url'], fc['schedule_source']['url'])}
(retrieved {esc(fc['schedule_source']['retrieved_at'])}).</li>
<li>Model files pinned at record time:{mfs}</li>
<li>Reproduce with <code>python3 prereg/shadow_baseline.py --check</code> — probabilities
recompute from the stored PF/PA aggregates (gate SB-G3).</li>
</ul>
<table class="data">
<thead><tr><th>Game</th><th>Kickoff</th><th>P(home win)</th><th>Pick</th><th>Network</th>
<th>Source (official game centre)</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody></table>
<p class="note">This window is a <strong>pipeline test, not a skill sample</strong>: gate
SB-G4 requires ≥200 settled forecasts with a Brier-skill interval above zero before any skill
claim. Scoring happens only after every game is final on the official schedule page.</p>
</section>
"""


# ----------------------------------------------------------------- archive
def archive(reg, corpus, ctl, src) -> str:
    mc = corpus["membership_counts"]
    ctrl_rows = "".join(
        f"<tr><td><code>{esc(c['id'])}</code> {esc(c['name'])}</td><td>{esc(c['market'])}</td>"
        f"<td>{c.get('n_games', c.get('n_scored', '—')):,}</td>"
        f"<td>{(str(round(100 * c['expected_roi'], 3)) + '%') if 'expected_roi' in c else ''}"
        f"{(str(round(c['roi_pct'], 3)) + '%') if 'roi_pct' in c else ''}</td>"
        f"<td>{esc(c.get('hit_rate', '—'))}</td>"
        f"<td>{esc(c['role'])}</td>"
        f"<td>{link(c['source']['u'], c['source']['t'])}</td></tr>"
        for c in ctl["controls"])

    strat_rows = []
    for cid, info in src.items():
        for s in info["rows"]:
            strat_rows.append(
                f"<tr><td>{esc(info['title'])}</td><td>{esc(s['name'])}</td>"
                f"<td>{esc(s.get('n', '—'))}</td><td>{esc(s.get('roi', '—'))}</td>"
                f"<td>{esc(s.get('status', '—'))}</td>"
                f"<td>{link(info['url'], info['label'])}</td></tr>")

    coll_rows = "".join(
        f"<tr><td>{esc(i['title'])}</td><td><span class='kind k-ret'>{esc(i['kind'])}</span></td>"
        f"<td>{i['n']}</td><td>{esc(i['window'])}</td><td>{esc(i['basis'])}</td>"
        f"<td>{esc(i['verdict'])}</td><td>{link(i['url'], i['label'])}</td></tr>"
        for i in src.values())

    return f"""
<section>
<h2>Backtest archive <span class="tag k-ret">retrospective · not a leaderboard</span></h2>
<p class="banner">These are historical numbers. The brief forbids backtest numbers from
appearing on the leaderboard, so they are kept here, outside the
<a href="index.html">prospective board</a>, with no ranks, no rewards and no
“top strategy” language. Each collection was scored under its own gates and its own price
policy — the columns are <em>not</em> comparable across collections.</p>
</section>

<section>
<h2>Frozen corpus <span class="tag">{esc(corpus['corpus_id'])}</span></h2>
<table class="data">
<thead><tr><th>Item</th><th>Value</th><th>Detail</th></tr></thead>
<tbody>
<tr><td>File</td><td><code>{esc(corpus['file'])}</code></td>
<td>{link('https://github.com/nflverse/nflverse-data/releases/tag/schedules', 'nflverse schedules release (CC-BY-4.0)')}</td></tr>
<tr><td>sha256 at freeze</td><td><code>{esc(corpus['sha256_at_freeze'])}</code></td>
<td>{corpus['bytes_at_freeze']:,} bytes, {corpus['rows_at_freeze']:,} rows —
{link('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/prereg/corpus.json', 'corpus record')}</td></tr>
<tr><td>Membership rule</td><td>{esc(corpus['membership_rule'])}</td>
<td>{mc['completed_total']:,} games — {link('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/prereg/corpus.json', 'corpus record')}</td></tr>
<tr><td>Train 1999–2022</td><td>{mc['train_1999_2022']:,} games</td>
<td>fitting, thresholds — {link('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/prereg/corpus.json', 'corpus record')}</td></tr>
<tr><td>Validation 2023–2024</td><td>{mc['validation_2023_2024']:,} games</td>
<td>model selection only — {link('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/prereg/corpus.json', 'corpus record')}</td></tr>
<tr><td>Holdout 2025–2026</td><td>{mc['holdout_2025_2026']:,} games — <strong>closed</strong></td>
<td>opening requires a dated <code>holdout_opened</code> record —
{link('https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/prereg/corpus.json', 'corpus record')}</td></tr>
<tr><td>Official verification tier</td><td>2026 only</td>
<td>{link('https://www.nfl.com/schedules/', 'nfl.com schedules')} — 136 committed rows in
<code>data/verified/games_2026.csv</code> each with its official week-page URL, plus the
official WAS 24–21 NYG final absent from that file (flag F49); 1999–2025 are community-mirror
values, labelled unverified (readiness PR-02)</td></tr>
<tr><td>Price policy</td><td>observed prices only</td>
<td>{link('https://github.com/kanlerxz87-cyber/NFL1/blob/main/room/data/decisions.json', 'open decision PR-10 (retire the -110 assumption)')}</td></tr>
</tbody></table>
</section>

<section>
<h2>Controls <span class="tag">registered for every future board run</span></h2>
<p class="note">No-skill references computed on the frozen corpus at observed prices
(readiness PR-17). A strategy whose interval overlaps a control interval is not
distinguishable from no skill.</p>
<table class="data">
<thead><tr><th>Control</th><th>Market</th><th>n</th><th>ROI (expected/realised)</th>
<th>Hit rate</th><th>Role</th><th>Source</th></tr></thead>
<tbody>
{ctrl_rows}
</tbody></table>
<p class="note">Method notes: CTRL-01 is analytic (no RNG) —
<code>0.25·(dec_away + dec_home) − 1</code> per priced game. CTRL-02 bets the favourite
(home iff <code>spread_line &gt; 0</code>, the sign convention proved from the data and used
by the s9cb scorer); pushes excluded. The favourites-only control <em>losing</em> at observed
prices is the vig any strategy must first overcome — which is why raw win rate cannot rank
strategies.</p>
</section>

<section>
<h2>Collections, as published by their own gates</h2>
<table class="data">
<thead><tr><th>Collection</th><th>Kind</th><th>Strategies</th><th>Window</th>
<th>Price basis</th><th>Published verdict</th><th>Source</th></tr></thead>
<tbody>
{coll_rows}
</tbody></table>
</section>

<section>
<h2>Per-strategy published results (historical)</h2>
<table class="data">
<thead><tr><th>Collection</th><th>Strategy</th><th>n</th><th>ROI</th><th>Status</th>
<th>Source</th></tr></thead>
<tbody>
{''.join(strat_rows)}
</tbody></table>
<p class="note">Blank-and-labelled cells (<code>never evaluated</code>,
<code>not stakeable</code>) mean exactly that — no value is inferred. Retrospective rows are
disclosure; none of them may be presented as a pre-registered result.</p>
</section>
"""


def archive_sources() -> dict:
    """Per-collection published results, read from the committed source files."""
    out = {}

    def add(cid, title, label, url, rows, kind, window, basis, verdict, n):
        out[cid] = dict(title=title, label=label, url=url, rows=rows, kind=kind,
                        window=window, basis=basis, verdict=verdict, n=n)

    lb = jload("data/s9cb/leaderboard.json")
    rows = [{"name": r["strategy"],
             "n": f"{r['n_bets']:,}",
             "roi": f"{r['roi_pct']:.2f}%",
             "status": f"{r['status']} ({r['n_gates_passed']}/8)"} for r in lb["leaderboard"]]
    npass = sum(1 for r in lb["leaderboard"] if r["status"] == "PASS")
    nwatch = sum(1 for r in lb["leaderboard"] if r["status"] == "WATCH")
    add("s9cb-12", "s9cb: 12 rules at observed prices", "data/s9cb/leaderboard.json",
        "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/leaderboard.json",
        rows, "retrospective", "2006–2026", "observed prices",
        f"{npass} PASS / {nwatch} WATCH / {12 - npass - nwatch} FAIL", 12)

    md = jload("data/model/strategies.json")
    rows = [{"name": r["strategy"], "n": f"{r['n_graded']:,}",
             "roi": f"{100 * r['roi']:.2f}%",
             "status": f"{r['status']} ({r['gates_passed']}/8)"} for r in md["leaderboard"]]
    npass = sum(1 for r in md["leaderboard"] if r["status"] == "PASS")
    nwatch = sum(1 for r in md["leaderboard"] if r["status"] == "WATCH")
    add("model-12", "root model: 12 strategies", "data/model/strategies.json",
        "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/model/strategies.json",
        rows, "retrospective", "2005–2026", "-110 assumption (retired pending PR-10)",
        f"{npass} PASS / {nwatch} WATCH / {12 - npass - nwatch} FAIL", 12)

    st = jload("data/strength/strategies.json")
    rows = [{"name": r["strategy"], "n": f"{r['n_bets']:,}",
             "roi": f"{r['roi_pct']:.2f}%",
             "status": f"{r['status']} ({len([g for g in r['gates'].values() if g == 'PASS'])}/8)"}
            for r in st["strategies"]]
    npass = sum(1 for r in st["strategies"] if r["status"] == "PASS")
    add("strength-11", "strength-of-schedule: 11 rules", "data/strength/strategies.json",
        "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/strength/strategies.json",
        rows, "retrospective", "1999–2026", "observed prices",
        f"{npass} PASS / 0 WATCH / {11 - npass} FAIL", 11)

    pe = jload("data/personnel/leaderboard.json")
    rows = [{"name": r["strategy"], "n": f"{r['n_bets']:,}",
             "roi": f"{r['roi_pct']:.2f}%",
             "status": f"{r['status']} ({r['n_gates_passed']}/8)"} for r in pe["leaderboard"]]
    npass = sum(1 for r in pe["leaderboard"] if r["status"] == "PASS")
    nwatch = sum(1 for r in pe["leaderboard"] if r["status"] == "WATCH")
    add("personnel-5", "personnel-deficiency: 5 rules", "data/personnel/leaderboard.json",
        "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/personnel/leaderboard.json",
        rows, "retrospective", "2019–2026", "observed prices",
        f"{npass} PASS / {nwatch} WATCH / {5 - npass - nwatch} FAIL (family of 17)", 5)

    lab = jload("data/session-1505ac8e/strategies.json")
    rows = []
    for r in lab["rules"]:
        if r.get("graded") and r.get("stats"):
            roi = f"edge {r['stats']['mean_edge_pts']:.1f} pts (mean)"
        else:
            roi = "—"
        rows.append({"name": f"{r['id']} {r['name']}",
                     "n": f"{r.get('n_bets', 0):,}" if r.get("graded") else "—",
                     "roi": roi, "status": r["status"]})
    npass = sum(1 for r in lab["rules"] if r["status"] == "PASS")
    add("lab-9", "lab unified study: 9 rules", "data/session-1505ac8e/strategies.json",
        "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-1505ac8e/strategies.json",
        rows, "retrospective", "2026 weeks 4–9", "edge points, not ROI",
        f"{npass} PASS / {sum(1 for r in lab['rules'] if r['status'] == 'WATCH')} WATCH / "
        f"{sum(1 for r in lab['rules'] if r['status'] == 'FAIL')} FAIL", 9)

    vl = jload("data/processed/site_data.json")
    counts = vl["strategies"]["counts"]
    rows = [{"name": f"{r['id']} {r['name']}", "n": "—", "roi": "—",
             "status": "not stakeable (no prices)"} for r in vl["strategies"]["strategies"]]
    add("verifiedlab-13", "verified-lab: 13 strategies", "data/processed/site_data.json",
        "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/processed/site_data.json",
        rows, "retrospective", "2026", "no prices published",
        f"{counts['not_stakeable']} not stakeable, {counts['approved']} approved", 13)

    fd = jload("data/strategies.json")
    rows = [{"name": f"{r['id']} {r['name']}", "n": "—", "roi": "—",
             "status": "never evaluated"} for r in fd]
    add("foundation-10", "foundation design register: 10 strategies", "data/strategies.json",
        "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/strategies.json",
        rows, "prospective-eligible", "design only", "n/a",
        "performance fields null — registered before first evaluation", 10)

    sg = jload("data/session-87deb7ab/strategies.json")
    rows = [{"name": f"{r['id']} {r['name']}", "n": "—", "roi": "—",
             "status": r.get("status", "Proposed")} for r in sg["signals"]]
    add("signals-18", "signal catalogue: 18 proposed signals", "data/session-87deb7ab/strategies.json",
        "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/session-87deb7ab/strategies.json",
        rows, "prospective-eligible", "design only", "n/a",
        "status Proposed on every signal — registered before first evaluation", 18)

    return out


def main() -> int:
    reg = jload("data/prereg/registrations.json")
    corpus = jload("data/prereg/corpus.json")
    ctl = jload("data/prereg/controls.json")
    fc = jload("data/prereg/forecasts/SB-01_week11_2026.json")
    sched = jload("data/prereg/official/week11_2026_schedule.json")

    write("index.html", page("index", "Overview & prospective board",
                             overview(reg, corpus, ctl, fc, sched), "index.html"))
    write("registry.html", page("registry", "Registry (all entries)",
                                registry(reg), "registry.html"))
    write("forecasts.html", page("forecasts", "Forecast record",
                                 forecasts(fc, sched), "forecasts.html"))
    write("archive.html", page("archive", "Backtest archive",
                               archive(reg, corpus, ctl, archive_sources()),
                               "archive.html"))
    print("wrote prereg/{index,registry,forecasts,archive}.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
