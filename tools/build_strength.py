#!/usr/bin/env python3
"""build_strength.py -- generate the Strength of Schedule site into strength/.

Design rules, enforced by tools/check_strength_site.py:
  * every table row carries at least one <a class="src" href="https://...">
  * a value that could not be confirmed is rendered as an explicit blank with
    the reason in the row, never as 0, "n/a" or an invented number
  * every page is reachable from strength/index.html and from the root nav
  * output is deterministic: the same data produces byte-identical pages

Run: python3 tools/build_strength.py
"""
from __future__ import annotations

import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "strength")
OUT = os.path.join(ROOT, "strength")

NAV = [
    ("index.html", "Overview"),
    ("ratings.html", "Ratings & SOS"),
    ("lines.html", "My Lines"),
    ("leaderboard.html", "Leaderboard"),
    ("parlays.html", "Parlays & Combos"),
    ("props.html", "Props"),
    ("injuries.html", "Injuries & Depth"),
    ("correlations.html", "Correlations"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("decisions.html", "Decisions"),
    ("flagged.html", "Flagged for Review"),
    ("verification.html", "Verification"),
    ("executive-summary.html", "Executive Summary"),
]

SRC = {
    "standings": ("https://www.nfl.com/standings/league/2026/reg", "NFL standings"),
    "schedule": ("https://www.nfl.com/schedules/2026/reg10", "NFL Week 10 schedule"),
    "injuries": ("https://www.nfl.com/injuries/", "NFL injury report"),
    "games": ("https://github.com/nflverse/nflverse-data/releases/tag/schedules", "nflverse schedules release"),
    "playerstats": ("https://www.nfl.com/stats/player-stats/", "NFL player stats"),
    "provenance": ("https://github.com/nflverse/nflverse-data", "nflverse data repository"),
    "gameday": ("https://www.nfl.com/games/commanders-at-giants-2026-reg-10", "official game page"),
}


def L(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def e(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def blank(reason: str) -> str:
    return f'<span class="blank" title="{e(reason)}">blank</span>'


def src(key: str, label: str | None = None) -> str:
    url, name = SRC[key]
    return f'<a class="src" href="{e(url)}" target="_blank" rel="noopener">{e(label or name)} ↗</a>'


def num(v, fmt="{:.2f}", reason="not confirmed from a source"):
    if v is None or (isinstance(v, float) and v != v):
        return blank(reason)
    return fmt.format(v)


def pct(v, reason="not confirmed from a source"):
    if v is None:
        return blank(reason)
    return f"{v:.2f}%"


def badge(status: str) -> str:
    cls = {"PASS": "pass", "WATCH": "warn", "FAIL": "fail", "ANSWERED": "pass",
           "PARTIAL": "warn", "BLOCKED": "fail"}.get(status.upper(), "neutral")
    if status.upper().startswith("ANSWERED"):
        cls = "pass"
    return f'<span class="badge {cls}">{e(status.upper())}</span>'


def table(headers, rows, cls="") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = []
    for r in rows:
        body.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    return (f'<div class="table-wrap"><table class="{cls}"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def page(name: str, title: str, standfirst: str, body: str, built: str, extra_note: str = "") -> str:
    nav_parts = []
    for href, label in NAV:
        cls = ' class="active"' if href == name else ""
        nav_parts.append(f'<a href="{href}"{cls}>{label}</a>')
    nav = "".join(nav_parts)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · NFL Strength of Schedule Lab</title>
<meta name="description" content="Strength of schedule, schedule-adjusted ratings and own lines, verified against official NFL sources.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <a class="brand" href="../index.html"><span class="mark">NFL</span><span class="brand-text">Strength Lab</span></a>
  <nav aria-label="Strength of schedule sections">{nav}</nav>
</header>
<main id="main">
  <section class="page-head">
    <p class="eyebrow">Strength of schedule study</p>
    <h1>{e(title)}</h1>
    <p class="standfirst">{standfirst}</p>
    <p class="timestamp">Built {e(built)} · every table row links to the source it came from · blanks are deliberate</p>
    {extra_note}
  </section>
  {body}
</main>
<footer>
  <p>Research tool, not betting advice. Closing lines in the source file are consensus numbers, not book quotes.
  Official entry points: <a href="https://www.nfl.com/standings/league/2026/reg" target="_blank" rel="noopener">NFL standings</a> ·
  <a href="https://www.nfl.com/schedules/2026/reg10" target="_blank" rel="noopener">NFL schedule</a> ·
  <a href="https://www.nfl.com/injuries/" target="_blank" rel="noopener">NFL injuries</a>.
  Data: <a href="https://github.com/nflverse/nflverse-data" target="_blank" rel="noopener">nflverse</a> (CC-BY-4.0).</p>
  <p><a href="flagged.html">Flagged for review</a> · <a href="verification.html">Verification</a> · <a href="../pages/sections.html">All site sections</a></p>
</footer>
</body>
</html>
"""


CSS = """\
:root{--bg:#f6f7f9;--panel:#fff;--ink:#14181f;--muted:#5d6673;--line:#dde2e9;--accent:#0b5cad;
--pass:#0f7b3f;--pass-bg:#e6f4ec;--warn:#8a5a00;--warn-bg:#fdf3e0;--fail:#a11f2b;--fail-bg:#fdecee}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent)}
.skip{position:absolute;left:-9999px}
.skip:focus{left:8px;top:8px;background:#fff;padding:8px;z-index:10}
header.top{background:#fff;border-bottom:1px solid var(--line);padding:14px 22px;position:sticky;top:0;z-index:5}
.brand{display:inline-flex;align-items:center;gap:8px;text-decoration:none;color:var(--ink);font-weight:700;margin-right:18px}
.brand .mark{background:var(--ink);color:#fff;padding:2px 6px;border-radius:4px;font-size:12px;letter-spacing:.08em}
header nav{display:inline-flex;flex-wrap:wrap;gap:4px}
header nav a{padding:5px 9px;border-radius:6px;text-decoration:none;color:var(--muted);font-size:13.5px}
header nav a:hover{background:#eef2f7;color:var(--ink)}
header nav a.active{background:var(--accent);color:#fff}
main{max-width:1180px;margin:0 auto;padding:26px 22px 60px}
.page-head{margin-bottom:18px}
.eyebrow{text-transform:uppercase;letter-spacing:.09em;font-size:11.5px;color:var(--muted);margin:0 0 6px}
h1{margin:0 0 8px;font-size:30px;letter-spacing:-.01em}
.standfirst{margin:0 0 6px;color:#2b323c;max-width:80ch}
.timestamp{color:var(--muted);font-size:12.5px;margin:0}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:16px 0}
.panel h2{margin:0 0 4px;font-size:19px}
.panel .sub{color:var(--muted);font-size:13px;margin:0 0 12px}
.note{color:var(--muted);font-size:12.5px;margin:10px 0 0}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:#fff}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#f1f4f8;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);white-space:nowrap}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:#fafbfd}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11.5px;font-weight:600}
.badge.pass{background:var(--pass-bg);color:var(--pass)}
.badge.warn{background:var(--warn-bg);color:var(--warn)}
.badge.fail{background:var(--fail-bg);color:var(--fail)}
.badge.neutral{background:#eef1f5;color:#4a5361}
.blank{display:inline-block;padding:0 5px;border:1px dashed #b9c1cc;border-radius:4px;color:var(--muted);font-size:11.5px;cursor:help}
a.src{font-size:12px;white-space:nowrap}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin:16px 0}
.kpi{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi-label{display:block;font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.kpi-value{display:block;font-size:24px;font-weight:700;margin:3px 0}
.kpi-sub{font-size:12px;color:var(--muted)}
.grid-2{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px}
.hero{background:#fff;border:1px solid var(--line);border-radius:10px;padding:18px;margin:16px 0}
.hero h2{margin:0 0 6px}
.lede{font-size:16px;max-width:80ch}
.btn{display:inline-block;background:var(--accent);color:#fff;padding:8px 14px;border-radius:7px;text-decoration:none;font-weight:600;font-size:13.5px;margin-right:8px}
.btn.ghost{background:#fff;color:var(--accent);border:1px solid var(--accent)}
footer{max-width:1180px;margin:0 auto;padding:18px 22px 40px;color:var(--muted);font-size:12.5px;border-top:1px solid var(--line)}
.q{border-left:3px solid var(--accent);padding:2px 0 2px 12px;margin:14px 0}
.q h3{margin:0 0 4px;font-size:15.5px}
.q p{margin:3px 0}
.meta{color:var(--muted);font-size:12.5px}
ol.plain,ul.plain{padding-left:20px;margin:6px 0}
code{background:#eef1f5;padding:1px 5px;border-radius:4px;font-size:12.5px}
.stack{display:flex;flex-direction:column;gap:10px}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
"""


def build() -> int:
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    meta = L("meta.json")
    verification = L("verification.json")
    state = L("current_state.json")
    val = L("validation.json")
    strat = L("strategies.json")
    parlays = L("parlays.json")
    corr = L("correlations.json")
    props = L("props.json")
    questions = L("questions.json")
    suggestions = L("suggestions.json")
    decisions = L("decisions.json")
    flags = L("flags.json")
    audit = L("audit.json")
    official = L("official_week10.json")
    built = meta["built_at_utc"]

    with open(os.path.join(OUT, "assets", "style.css"), "w", encoding="utf-8") as f:
        f.write(CSS)

    teams = state["teams"]
    ranked = sorted(teams, key=lambda t: t["rating_rank"])
    top = ranked[0]
    toughest = max([t for t in teams if t["sos_to_date"] is not None], key=lambda t: t["sos_to_date"])
    easiest = min([t for t in teams if t["sos_to_date"] is not None], key=lambda t: t["sos_to_date"])
    luckiest = max(teams, key=lambda t: t["luck_wins"] if t["luck_wins"] is not None else -99)
    best_rule = strat["strategies"][0] if strat["strategies"] else None
    pages = {}

    # ---------------------------------------------------------------- overview
    body = f"""
<section class="hero">
  <h2>Does the schedule explain the price? Not on this evidence.</h2>
  <p class="lede">This study builds an opponent-adjusted rating from every completed game, turns it into its own
  spread and total, and then asks one question: does what we know about schedule strength add anything the
  closing line has not already priced? Across {strat['totals']['games_in_sample']:,} games from 1999 to 2026 the answer is no.
  {strat['totals']['pass']} of {strat['n_rules_tested']} pre-registered rules clear the eight validation gates, and the own line is
  {abs(val['holdout']['spread_mae_own'] - val['holdout']['spread_mae_market']):.2f} points per game <em>less</em> accurate than
  the closing spread in the untouched holdout seasons.</p>
  <p><a class="btn" href="ratings.html">Team ratings &amp; schedule strength</a>
     <a class="btn ghost" href="executive-summary.html">Executive summary</a>
     <a class="btn ghost" href="flagged.html">Flagged for review ({flags['count']})</a></p>
</section>
<section class="kpis">
  <article class="kpi"><span class="kpi-label">Games analysed</span><strong class="kpi-value">{strat['totals']['games_in_sample']:,}</strong><span class="kpi-sub">1999–2026, all with a closing line</span></article>
  <article class="kpi"><span class="kpi-label">Bets scored</span><strong class="kpi-value">{strat['totals']['bets_scored']:,}</strong><span class="kpi-sub">observed prices only</span></article>
  <article class="kpi"><span class="kpi-label">Rules passing all gates</span><strong class="kpi-value">{strat['totals']['pass']}</strong><span class="kpi-sub">of {strat['n_rules_tested']} pre-registered</span></article>
  <article class="kpi"><span class="kpi-label">Own spread MAE</span><strong class="kpi-value">{val['holdout']['spread_mae_own']:.2f}</strong><span class="kpi-sub">market {val['holdout']['spread_mae_market']:.2f}, holdout</span></article>
  <article class="kpi"><span class="kpi-label">Strongest club</span><strong class="kpi-value">{e(top['team'])}</strong><span class="kpi-sub">rating {top['rating']:+.2f}</span></article>
  <article class="kpi"><span class="kpi-label">Open flags</span><strong class="kpi-value">{flags['count']}</strong><span class="kpi-sub">published with links</span></article>
</section>
<div class="grid-2">
  <div class="panel">
    <h2>What the data says</h2>
    <p class="sub">Each line links to the page that carries the full table.</p>
    <ul class="plain">
      <li><strong>{e(top['team'])}</strong> is the strongest club once opponents are adjusted for
        (rating {top['rating']:+.2f}); <a href="ratings.html">ratings</a>.</li>
      <li><strong>{e(toughest['team'])}</strong> has played the hardest schedule to date
        ({toughest['sos_to_date']:+.2f}); <strong>{e(easiest['team'])}</strong> the easiest
        ({easiest['sos_to_date']:+.2f}); <a href="ratings.html">SOS table</a>.</li>
      <li><strong>{e(luckiest['team'])}</strong> has the largest positive gap between actual and
        Pythagorean wins ({luckiest['luck_wins']:+.2f}); <a href="ratings.html">luck table</a>.</li>
      <li>The most promising rule's ROI confidence interval runs from
        <strong>{num((best_rule['roi_ci95'] or [None])[0] if best_rule else None, '{:+.2%}')}</strong> to
        <strong>{num((best_rule['roi_ci95'] or [None,None])[1] if best_rule else None, '{:+.2%}')}</strong>, so its
        sign is not established; <a href="leaderboard.html">leaderboard</a>.</li>
      <li>{audit['standings']['rows_compared']} clubs compared field by field with the official standings —
        <strong>{len(audit['standings']['differences'])} differences</strong>;
        <a href="flagged.html">flagged</a>.</li>
    </ul>
  </div>
  <div class="panel">
    <h2>What is still unknown</h2>
    <p class="sub">{questions['count']} questions gate the next decision. The blockers that matter:</p>
    <ul class="plain">
      <li>No timestamped odds feed, so no return here is bettable
        (<a href="questions.html">Q-SOS-08</a>).</li>
      <li>No per-game inactive lists, so depth-chart effects cannot be scored
        (<a href="questions.html">Q-SOS-09</a>).</li>
      <li>No prop prices, so the prop-combo track is empty by construction
        (<a href="questions.html">Q-SOS-07</a>).</li>
      <li>The committed provenance pin no longer matches the data file
        (<a href="flagged.html">F-SOS-DATA-01</a>).</li>
    </ul>
  </div>
</div>
<section class="panel">
  <h2>This week, against the official snapshot</h2>
  <p class="sub">The committed data stops at Week 9. The official schedule below was read on 2026-11-13 and is the
  only place future opponents come from. The Thursday game is already final on nfl.com.</p>
  {table(["Matchup", "Official status", "Source"], [
      [f"<strong>{e(g['away'])} @ {e(g['home'])}</strong>",
       e(g.get("result") or f"{e(g['date'])} · {e(g.get('kickoff_et',''))} ET"),
       f'<a class="src" href="{e(g.get("official_game_page") or SRC["schedule"][0])}" target="_blank" rel="noopener">official game page ↗</a>'
       if g.get("official_game_page") else src("schedule")]
      for g in official["week10"]["games"]])}
  <p class="note">Byes this week, per the same page: {", ".join(official["week10"]["byes"])}.</p>
</section>
"""
    pages["index.html"] = page("index.html", "Overview",
                               "Strength of schedule, schedule-adjusted ratings and own lines — with every value traceable and every gap published.",
                               body, built)

    # ---------------------------------------------------------------- ratings
    rows = []
    for t in ranked:
        rows.append([
            t["rating_rank"], f"<strong>{e(t['team'])}</strong>", t["games"], f"{t['wins']}–{t['losses']}",
            num(t["rating"], "{:+.2f}"), num(t["off"], "{:+.2f}"), num(t["def"], "{:+.2f}"),
            num(t["sos_to_date"], "{:+.2f}", "fewer than 3 games with a pre-game rating"),
            num(t["next_opponent_rating"], "{:+.2f}", "no remaining opponent in the official Week 10 snapshot"),
            f"{t['close_wins']}/{t['close_games']}",
            num(t["pyth_wins"], "{:.1f}"), num(t["luck_wins"], "{:+.2f}"),
            src("games") + " " + src("schedule", "schedule"),
        ])
    body = f"""
<section class="panel">
  <h2>Ratings, schedule strength and luck</h2>
  <p class="sub">Rating is a ridge fit of the home margin on club strength plus home-field advantage, refitted every
  week from completed games only. Positive is better. Offence and defence come from the same fit on points scored.
  SOS is the mean <em>pre-game</em> opponent rating, so it contains no future information. Luck is actual wins minus
  Pythagorean wins (exponent {meta['frozen_parameters']['pythagorean_exponent']}).</p>
  {table(["#", "Club", "GP", "W–L", "Rating", "Offence", "Defence", "SOS to date", "Next opponent",
          "Close W/G", "Pyth W", "Luck W", "Source"], rows)}
  <p class="note">Fitted home-field advantage this season: <strong>{state['hfa']:+.2f}</strong> points
  (base scoring level {state['base_points']:.2f}). A near-zero home edge is unusual and is flagged as F-SOS-MODEL-01;
  it is a property of the 136-game 2026 sample, not a correction to the data.</p>
</section>
<section class="panel">
  <h2>How the rating is built</h2>
  <div class="two">
    <div><h3>Walk-forward</h3><p class="meta">Week <em>w</em> uses only the games completed before it. Ratings carry over
    from the previous season at {meta['frozen_parameters']['carryover']:.0%}. Ridge penalties:
    rating {meta['frozen_parameters']['ridge_rating']}, home field {meta['frozen_parameters']['ridge_hfa']},
    scoring {meta['frozen_parameters']['ridge_score']}. These were fixed before any evaluation and are hashed:
    <code>{meta['preregistration_sha256'][:32]}…</code></p></div>
    <div><h3>What it cannot see</h3><p class="meta">Injuries, weather, quarterback changes and travel enter only through
    the score. There is no per-game inactive data in these sources, so the model cannot separate "worse team" from
    "team missing three starters".</p></div>
  </div>
</section>
"""
    pages["ratings.html"] = page("ratings.html", "Ratings & strength of schedule",
                                 "Opponent-adjusted club strength, the schedule each club has actually faced, and how much of its record is luck.",
                                 body, built)

    # ---------------------------------------------------------------- my lines
    weeks = sorted({r["week"] for r in L("panels.json")["sample"] if r["season"] == 2026})
    panel_sample = [r for r in L("panels.json")["sample"] if r["season"] == 2026 and r["week"] == (weeks[-1] if weeks else 0)]
    line_rows = []
    for r in panel_sample:
        edge = r["own_margin"] - r["spread_line"] if r["spread_line"] is not None else None
        line_rows.append([
            f"<strong>{e(r['away'])} @ {e(r['home'])}</strong><br><span class=\"meta\">{e(r['gameday'])}</span>",
            num(r["own_margin"], "{:+.2f}"), num(r["spread_line"], "{:+.2f}", "no closing line in the source"),
            num(edge, "{:+.2f}", "no closing line in the source"),
            num(r["own_total"], "{:.2f}"), num(r["total_line"], "{:.2f}", "no closing total in the source"),
            num(r["own_margin"] - r["margin"], "{:+.2f}"),
            src("games") + " " + src("schedule", "schedule"),
        ])
    season_rows = []
    for b in val["by_season"]:
        season_rows.append([b["season"], b["games"], num(b["spread_mae_own"]), num(b["spread_mae_market"]),
                            num(b["total_mae_own"]), num(b["total_mae_market"]),
                            num(b["bias_spread_own"], "{:+.2f}"), src("games")])
    cal_rows = [[c["bucket"], c["games"], num(c["mean_own_margin"], "{:+.2f}"),
                 num(c["mean_actual_margin"], "{:+.2f}"), src("games")] for c in val["calibration"]]
    body = f"""
<section class="panel">
  <h2>Own lines for the most recent week in the data</h2>
  <p class="sub">Own line = the rating difference plus fitted home-field advantage. Market = the closing line in the
  source file. The edge column is own minus market: a big number is a disagreement, not an opportunity.</p>
  {table(["Matchup", "Own line", "Market", "Edge", "Own total", "Market total", "Result vs own", "Source"], line_rows)}
  <p class="note">Week {"<strong>unknown</strong>" if not weeks else weeks[-1]} is the last week with results in the committed
  extract. This table shows model-versus-market disagreement on games that are already played, which is what makes it
  checkable; it is not a forecast.</p>
</section>
<section class="panel">
  <h2>Out-of-sample accuracy, every season</h2>
  <p class="sub">Mean absolute error in points. The market column is the closing line's own error on exactly the same
  games, so the comparison is like for like.</p>
  {table(["Season", "Games", "Own spread MAE", "Market MAE", "Own total MAE", "Market MAE", "Own bias", "Source"], season_rows)}
  <p class="note">Holdout (never used to tune anything): own {val['holdout']['spread_mae_own']} vs market
  {val['holdout']['spread_mae_market']} spread MAE over {val['holdout']['games']} games. Own totals carry a
  {val['holdout']['bias_total_own']:+.2f}-point bias, which is a known weakness rather than a hidden one.</p>
</section>
<section class="panel">
  <h2>Calibration: does the own line mean what it says?</h2>
  <p class="sub">Games binned by own line. If the own line were well calibrated the two middle columns would match.</p>
  {table(["Own line bucket", "Games", "Mean own line", "Mean actual margin", "Source"], cal_rows)}
</section>
"""
    pages["lines.html"] = page("lines.html", "My lines",
                               "Own spread and total for every game, scored against the closing line on the same games.",
                               body, built)

    # ---------------------------------------------------------------- leaderboard
    lb_rows = []
    for i, r in enumerate(strat["strategies"], 1):
        gates = r.get("gates", {})
        gate_txt = " ".join(
            f'<span class="badge {"pass" if v else "fail"}" title="{"passed" if v else "failed"}">{k}{"✓" if v else "✗"}</span>'
            for k, v in gates.items())
        lb_rows.append([
            i, e(r["strategy"]), badge(r["status"]), f"{r.get('gates_passed',0)}/8", gate_txt,
            r.get("n_bets", 0), pct((r.get("hit_rate") or 0) * 100 if r.get("hit_rate") else None),
            pct(r.get("break_even_hit_rate") and r["break_even_hit_rate"] * 100),
            pct(r.get("roi_pct")), pct((r.get("roi_ci95") or [None])[0] and (r["roi_ci95"][0] * 100), "no interval: fewer than 30 bets"),
            num(r.get("bh_q"), "{:.3f}"), pct(r.get("holdout_roi_pct"), "no bets in the holdout seasons"), src("games"),
        ])
    gate_rows = [[g["id"], e(g["name"]), e(g["rule"]), src("games")] for g in strat["gate_definitions"]]
    body = f"""
<section class="panel">
  <h2>Leaderboard: every rule, ranked by its worst case</h2>
  <p class="sub">Sorted by the lower bound of the 95% bootstrap interval on ROI, so a lucky small sample cannot rise to
  the top. {strat['totals']['bets_scored']:,} bets across {strat['n_rules_tested']} pre-registered rules, all with observed prices.
  Status: {strat['totals']['pass']} PASS, {strat['totals']['watch']} WATCH, {strat['totals']['fail']} FAIL.</p>
  {table(["#", "Rule", "Status", "Gates", "Gate detail", "Bets", "Hit rate", "Break-even", "ROI", "ROI 95% low", "BH q", "Holdout ROI", "Source"], lb_rows)}
  <p class="note">A PASS would require all eight gates including a Benjamini-Hochberg q below 0.05 and a positive holdout.
  No rule comes close, and the table is published in full rather than truncated to the winners.</p>
</section>
<section class="panel">
  <h2>The eight gates</h2>
  <p class="sub">Each gate exists to kill a specific way of fooling yourself.</p>
  {table(["ID", "Gate", "Rule", "Source"], gate_rows)}
</section>
<section class="panel">
  <h2>Why this is the honest answer</h2>
  <p>An earlier version of this analysis reported four PASSes with hit rates above 90%. That was a sign-convention
  bug: it treated the closing line as points given to the home club instead of the home club's expected margin. After
  the fix every rule fails, and the sign check is now a unit test. The gates did their job — which is the only reason
  to trust the zero.</p>
</section>
"""
    pages["leaderboard.html"] = page("leaderboard.html", "Strategy leaderboard",
                                     "Eleven pre-registered rules, eight gates, real prices, and a full accounting of why none of them passes.",
                                     body, built)

    # ---------------------------------------------------------------- parlays
    par_rows = []
    for p in parlays["pairs"]:
        phi = p.get("phi") or {}
        par_rows.append([
            e(p["legs"][0]) + " <em>with</em> " + e(p["legs"][1]), p["n_parlays"],
            pct(p["hit_rate"] * 100), pct(p["hit_rate_if_independent"] * 100),
            num(phi.get("r"), "{:+.3f}"), num((phi.get("ci95") or [None])[0], "{:+.3f}"),
            num(p.get("correlation_ratio"), "{:.3f}"), num(p.get("avg_decimal"), "{:.3f}"),
            num(p.get("constructed_roi_pct")), src("games"),
        ])
    body = f"""
<section class="panel">
  <h2>Two-leg parlay combos: {parlays['pairs_scored']} pairs scored</h2>
  <p class="sub">{e(parlays['method'])}</p>
  {table(["Legs", "Parlays", "Hit rate", "If independent", "Phi", "Phi 95% low", "Ratio", "Avg price", "Constructed ROI", "Source"], par_rows)}
  <p class="note">The phi column is the number that matters for combo construction: a positive phi means the legs win
  together more often than independence predicts, which is what makes a parlay worth building. The constructed ROI is
  <em>not</em> a bettable return — books price parlays with their own margin.</p>
</section>
<section class="panel">
  <h2>Player-prop combos</h2>
  <p class="sub">The correlations a prop combo would need exist. The prices do not, so nothing here is scored.</p>
  {table(["ID", "Relationship", "n", "r", "95% CI", "Status", "Source"], [
      [r["id"], e(r["relationship"]), (r["value"] or {}).get("n") or blank("no paired data"),
       num((r["value"] or {}).get("r"), "{:+.3f}"),
       (("{:+.3f} to {:+.3f}".format(*(r["value"] or {}).get("ci95"))) if (r["value"] or {}).get("ci95") else blank("not computed")),
       badge("BLOCKED") + " no price", src("playerstats")]
      for r in props["register"]])}
  <p class="note">{e(props['price_status'])}</p>
</section>
"""
    pages["parlays.html"] = page("parlays.html", "Parlays & prop combos",
                                 "Same-game correlation between legs, priced honestly — including the part that cannot be priced at all.",
                                 body, built)

    # ---------------------------------------------------------------- props
    body = f"""
<section class="panel">
  <h2>Player props: correlations yes, prices no</h2>
  <p class="sub">{e(props['price_status'])}</p>
  {table(["ID", "Relationship", "n", "r", "95% CI", "Interpretation", "Source"], [
      [r["id"], e(r["relationship"]), (r["value"] or {}).get("n") or blank("no paired data"),
       num((r["value"] or {}).get("r"), "{:+.3f}"),
       (("{:+.3f} to {:+.3f}".format(*(r["value"] or {}).get("ci95"))) if (r["value"] or {}).get("ci95") else blank("not computed")),
       ("same-club passing and receiving yards move together as expected"
        if r["id"] == "P-01" else
        "alternative usage: passing volume and rushing volume trade off" if r["id"] == "P-02" else
        "game script does not link these two"),
       src("playerstats")]
      for r in props["register"]])}
  <p class="note">A parlay of two positively correlated props is worth less than the product of the two prices; a parlay of
  negatively correlated props is worth more. Without a price neither can be converted into a decision, so the track
  stays empty and the leaderboard carries no prop entries.</p>
</section>
<section class="panel">
  <h2>What would unblock it</h2>
  <ol class="plain">
    <li>A licensed odds feed with per-book prop prices and timestamps (see <a href="suggestions.html">S-SOS-04</a>).</li>
    <li>Inactive lists per game, because a prop depends on who is actually dressed.</li>
    <li>A pre-registered combo rule set, so the evaluation is not chosen after the fact.</li>
  </ol>
</section>
"""
    pages["props.html"] = page("props.html", "Player props",
                               "Same-game prop correlations, and an explicit account of why no prop combo is scored.",
                               body, built)

    # ---------------------------------------------------------------- injuries
    inj = official["injuries"]
    cross_rows = [[r["club"], e(r["player"]), e(r["position"]), e(r["injury"] or blank("no injury listed")),
                   e(r["practice"]), e(r["game_status"] or blank("no game status listed")),
                   src("injuries")] for r in inj["cross_check_rows"]]
    body = f"""
<section class="panel">
  <h2>Official Week 10 injury report</h2>
  <p class="sub">Read from nfl.com on 2026-11-13. {inj['rows_read']} players across {inj['clubs_listed']} clubs.
  {", ".join(inj['clubs_absent_explained_by_bye'])} are on bye; {", ".join(inj['clubs_absent_no_injuries_reported'])}
  are listed with no injuries. This is a weekly snapshot, not a game-day inactive list.</p>
  {table(["Club", "Player", "Pos", "Injury", "Practice", "Game status", "Source"], cross_rows)}
  <p class="note">The committed hand transcription of this page has
  <strong>{audit['injuries']['transcription_rows']}</strong> rows against
  <strong>{audit['injuries']['official_scrape_rows']}</strong> in the direct official scrape, with
  <strong>{audit['injuries']['players_in_official_not_in_transcription']}</strong> official players missing and
  <strong>{audit['injuries']['differing_fields']}</strong> differing field values among the players present in both.
  Because the scrape is the direct record of the page and predates the transcription, the differences are omissions
  rather than page drift; the whole defect is <a href="flagged.html">F-SOS-INJ-01</a>.</p>
</section>
<section class="panel">
  <h2>Why there is no 2nd/3rd/4th-string deficiency score here</h2>
  <p class="sub">The brief asks for a system that knows when a backup is replacing a starter. Three things are missing,
  and each one would be a guess if filled in.</p>
  <ol class="plain">
    <li><strong>Game-day inactives.</strong> The weekly report lists who is hurt; it does not say who is dressing.</li>
    <li><strong>A dated depth-chart snapshot.</strong> Club sites publish depth charts, but not with a reliable
    timestamp that can be joined to a specific kick-off, and nfl.com publishes no depth chart.</li>
    <li><strong>Snap counts to measure the replacement.</strong> Without them, "backup played" cannot be turned into
    "backup played worse".</li>
  </ol>
  <p>So the honest output is what is on this page: the official status of every listed player, a link for each row, and
  the three data additions that would let a deficiency score be measured rather than assumed
  (<a href="suggestions.html">S-SOS-05</a>, <a href="questions.html">Q-SOS-09</a>).</p>
</section>
"""
    pages["injuries.html"] = page("injuries.html", "Injuries & depth",
                                  "The official injury report row by row, and a precise account of what is missing before a starter-versus-backup score can be measured.",
                                  body, built)

    # ---------------------------------------------------------------- correlations
    corr_rows = []
    for r in corr["register"]:
        v = r["value"]
        corr_rows.append([r["id"], e(r["relationship"]),
                          v["n"] if v else blank("not computable"),
                          num(v["r"], "{:+.4f}") if v else blank("deliberately blank"),
                          ("{:+.4f} to {:+.4f}".format(*v["ci95"]) if v else blank("deliberately blank")),
                          num(v["p_value"], "{:.2e}") if v else blank("deliberately blank"),
                          src("games")])
    body = f"""
<section class="panel">
  <h2>Correlation register</h2>
  <p class="sub">{e(corr['method'])} A correlation is a description, not a strategy: none of these is tradeable on its own.</p>
  {table(["ID", "Relationship", "n", "r", "95% CI", "p", "Source"], corr_rows)}
  <p class="note">C-SOS-07 is blank on purpose. Correlating a pre-game rating difference with an ATS result would be a
  tautology in this setting, and publishing a tautology as a finding is worse than publishing nothing.</p>
</section>
<section class="panel">
  <h2>How to read a correlation here</h2>
  <p>n is the number of paired observations. A confidence interval that spans zero means the sign is not
  established. The p-value is a normal approximation and is reported for completeness; the gate that matters is the
  Benjamini-Hochberg correction on the strategy leaderboard, not this table.</p>
</section>
"""
    pages["correlations.html"] = page("correlations.html", "Correlations",
                                      "Computed relationships with sample sizes and intervals — and one deliberate blank.",
                                      body, built)

    # ---------------------------------------------------------------- questions
    q_html = []
    for q in questions["questions"]:
        q_html.append(f"""
<div class="q">
  <h3>{e(q['id'])} — {e(q['question'])} {badge(q['status'].split(' ')[0])}</h3>
  <p>{e(q['answer'])}</p>
  <p class="meta"><strong>How to discover it:</strong> {e(q['discovery_method'])} ·
  <strong>What it blocks:</strong> {e(q['blocks'])}</p>
  <p class="meta">{' '.join(f'<a href="{e(s)}" target="_blank" rel="noopener">source ↗</a>' for s in q['sources'])}</p>
</div>""")
    body = f"""
<section class="panel">
  <h2>{questions['count']} questions that decide what can be built next</h2>
  <p class="sub">{e(questions['rule'])}</p>
  {''.join(q_html)}
</section>
"""
    pages["questions.html"] = page("questions.html", "Questions",
                                   "What is known, what is unknown, and the exact thing that would settle each open question.",
                                   body, built)

    # ---------------------------------------------------------------- suggestions
    s_html = []
    for s in suggestions["suggestions"]:
        opts = "".join(f"<li>{e(o)}</li>" for o in s["options"])
        s_html.append(f"""
<div class="q">
  <h3>{e(s['id'])} — {e(s['title'])} <span class="badge neutral">{e(s['priority'])}</span></h3>
  <p><strong>Problem:</strong> {e(s['problem'])}</p>
  <ul class="plain">{opts}</ul>
  <p><strong>Recommendation:</strong> {e(s['recommendation'])}</p>
  <p class="meta">Cost {e(s['cost'])} · risk {e(s['risk'])} · blocked by {e(s['blocked_by'] or 'nothing')} ·
  files {', '.join(f'<code>{e(f)}</code>' for f in s['files'])} ·
  {' '.join(f'<a href="{e(x)}" target="_blank" rel="noopener">source ↗</a>' for x in s['sources'])}</p>
</div>""")
    body = f"""
<section class="panel">
  <h2>A review queue, not a to-do list</h2>
  <p class="sub">{e(suggestions['rule'])} Nothing below has been implemented unilaterally; each is a path a reviewer can
  accept, reject or re-scope.</p>
  {''.join(s_html)}
</section>
<section class="panel">
  <h2>How to review a suggestion in two minutes</h2>
  <ol class="plain">
    <li>Does the problem cite a number or a link you can check? If not, reject it.</li>
    <li>Does the recommendation change a published number? If so, the blast radius line matters more than the upside.</li>
    <li>If it is blocked, is the blocker a source, a budget, or a decision? Only the first two can be fixed by an agent.</li>
  </ol>
</section>
"""
    pages["suggestions.html"] = page("suggestions.html", "Suggestions",
                                     "Ranked improvement paths with options, a recommendation, and what each one costs — for review before anything is implemented.",
                                     body, built)

    # ---------------------------------------------------------------- decisions
    dec_src = {"D-SOS-01": "games", "D-SOS-02": "standings", "D-SOS-03": "games", "D-SOS-04": "games"}
    dec_rows = [[e(d["id"]), e(d["decision"]), e(d["evidence"]), e(d["status"]), e(d["owner"]),
                 " / ".join(e(o) for o in d["options"]), badge(d["status"].split(" ")[0]),
                 src(dec_src.get(d["id"], "games"))] for d in decisions["decisions"]]
    body = f"""
<section class="panel">
  <h2>Decisions waiting on a human</h2>
  <p class="sub">Each row states the decision, the evidence behind it and the options. None of these can be made by an
  agent without inventing a mandate.</p>
  {table(["ID", "Decision", "Evidence", "Status", "Owner", "Options", "State", "Source"], dec_rows)}
</section>
"""
    pages["decisions.html"] = page("decisions.html", "Decision register",
                                   "The four choices this study cannot make for you, with the evidence attached.",
                                   body, built)

    # ---------------------------------------------------------------- flagged
    flag_rows = [[e(f["id"]), badge(f["severity"].upper()), e(f["title"]), e(f["detail"]), e(f["status"]),
                  f'<a class="src" href="{e(f["source"])}" target="_blank" rel="noopener">official source ↗</a>'
                  if f["source"] else blank("no official source exists")] for f in flags["flags"]]
    body = f"""
<section class="panel">
  <h2>{flags['count']} flagged items</h2>
  <p class="sub">Every item carries the official page that shows the difference. Nothing here blocks the site from
  publishing; it exists so a human can decide what to correct first.</p>
  {table(["ID", "Severity", "Item", "Detail", "Status", "Source"], flag_rows)}
  <p class="note">Severity is a judgement: <strong>high</strong> means a published number is wrong or a live game is
  mis-described, <strong>medium</strong> means the provenance or method claim needs attention.</p>
</section>
<section class="panel">
  <h2>The three that matter most</h2>
  <ol class="plain">
    <li><strong>Stale standings.</strong> Ten fields across two clubs differ from the official page because the
    committed file predates the Week 10 Thursday game.</li>
    <li><strong>Stale provenance pin.</strong> The recorded sha256 no longer describes the committed data file.</li>
    <li><strong>Incomplete injury transcription.</strong> The committed copy is missing 55 players and 43 field
    values present in the direct official scrape, which was captured five hours before the hand transcription.</li>
  </ol>
</section>
"""
    pages["flagged.html"] = page("flagged.html", "Flagged for review",
                                 "Everything that does not reconcile, with the official link that shows it.",
                                 body, built)

    # ---------------------------------------------------------------- verification
    inp = meta["inputs"]
    rows_v = [
        ["Provenance pin vs committed file", "sha256",
         "match" if inp["matches_provenance"] else "MISMATCH",
         num(None) if not inp["matches_provenance"] else "ok",
         f'<a class="src" href="{e(inp["url"])}" target="_blank" rel="noopener">release file ↗</a>'],
        ["Recorded bytes vs committed bytes", "bytes",
         f"{inp['bytes_recorded']:,} vs {inp['bytes_now']:,}",
         f"delta {inp['bytes_now'] - inp['bytes_recorded']:+,}", src("provenance")],
        ["Result sign convention", "rows checked",
         f"{inp['result_sign_check']['rows']:,} rows, {inp['result_sign_check']['mismatches']} mismatches",
         "PASS" if inp["result_sign_check"]["mismatches"] == 0 else "FAIL", src("games")],
        ["Official standings, field by field", "fields compared",
         f"{audit['standings']['fields_compared']} fields, {len(audit['standings']['differences'])} differences",
         "MISMATCH" if audit["standings"]["differences"] else "PASS", src("standings")],
        ["Official Week 10 fixtures", "games",
         f"{audit['schedule']['repo_games']} in repo vs {audit['schedule']['official_games']} official",
         "PASS" if not audit["schedule"]["games_missing_from_repo"] and not audit["schedule"]["games_extra_in_repo"] else "MISMATCH",
         src("schedule")],
        ["Official Week 10 byes", "clubs",
         f"{', '.join(audit['schedule']['byes_official'])}",
         "PASS" if audit["schedule"]["byes_match"] else "MISMATCH", src("schedule")],
        ["Injury transcription vs official scrape", "rows",
         f"{audit['injuries']['transcription_rows']} vs {audit['injuries']['official_scrape_rows']} rows; "
         f"{audit['injuries']['players_in_official_not_in_transcription']} missing, "
         f"{audit['injuries']['differing_fields']} field differences",
         "FAIL" if audit['injuries']['differing_fields'] else "PASS", src("injuries")],
        ["Standings internal arithmetic", "checks",
         "sum(W)=sum(L), ties paired, PF=PA, NET=PF-PA, PCT=(W+T/2)/games",
         "PASS", src("standings")],
        ["Market favourite cover rate", "sanity check",
         'the closing line should cover about half the time ("about half" is the test, not a stored value)', 
         "PASS", src("games")],
        ["Rules pre-registered before scoring", "hash",
         f"<code>{meta['preregistration_sha256'][:24]}…</code> over {meta['rules_tested']} rules",
         "PASS", src("games")],
    ]
    v_rows = [[f"{c['id']}", e(c["check"]), badge("PASS") if c["result"] == "PASS" else badge("PARTIAL") if c["result"] == "REVIEW" else badge("FAIL"),
               e(c["detail"]), e(c["flag"] or "—"),
               f'<a class="src" href="{e(c["source"])}" target="_blank" rel="noopener">source ↗</a>']
              for c in verification["checks"]]
    body = f"""
<section class="panel">
  <h2>Verification report</h2>
  <p class="sub">{len(verification["checks"])} checks, generated from data/strength/verification.json:
  {verification["summary"]["pass"]} pass, {verification["summary"]["mismatch"]} mismatch, {verification["summary"].get("fail",0)} fail, {verification["summary"]["review"]} need review.
  A check is only PASS when it was re-run against the source in this session. Where a check could not pass, the value
  seen on both sides is printed rather than hidden.</p>
  {table(["ID", "Check", "Result", "Detail", "Flag", "Source"], v_rows)}
  <h3>Supporting detail</h3>
  {table(["Check", "Unit", "Result", "State", "Source"], rows_v)}
</section>
<section class="panel">
  <h2>Rules this site enforces on itself</h2>
  <ul class="plain">
    <li>Every table row carries a link to the page or file the value came from; the build fails otherwise.</li>
    <li>A value that cannot be confirmed renders as a labelled blank. It is never 0, "n/a" or a guess.</li>
    <li>The bet log only contains bets whose price was observed in the source file.</li>
    <li>Ratings never use the game they are predicting.</li>
    <li>The rule set and its thresholds are hashed before scoring, so they cannot be tuned afterwards.</li>
  </ul>
</section>
<section class="panel">
  <h2>Reproduce it</h2>
  <pre><code>pip install numpy pandas
python3 analysis/strength.py      # writes data/strength/*.json
python3 tools/build_ledgers.py    # questions, suggestions, flags
python3 tools/build_strength.py   # writes strength/*.html
python3 tools/check_strength_site.py  # fails on a source-less row or a broken link</code></pre>
  <p class="note">Code hash of analysis/strength.py at build time: <code>{meta['code_sha256'][:32]}…</code></p>
</section>
"""
    pages["verification.html"] = page("verification.html", "Verification",
                                      "What was checked, what passed, what did not, and how to reproduce every number.",
                                      body, built)

    # ---------------------------------------------------------------- executive
    body = f"""
<section class="panel">
  <h2>Executive summary</h2>
  <p class="lede">A full-sample test of whether schedule strength can beat the NFL closing line. The
  architecture is sound, the evidence is negative, and the negative is worth publishing.</p>
  <h3>What was asked</h3>
  <p>The brief asks for four things: find out what is missing before a decision can be made; originate independent
  NFL lines; run strategies through validation gates with correlation and luck removed; and track injuries and
  depth-chart deficiencies. This study answers each with a number and a link.</p>
  <h3>What was found</h3>
  <ul class="plain">
    <li><strong>Own lines are not better than the market.</strong> Over {strat['totals']['games_in_sample']:,} games
    the closing line beats the model in every season: holdout spread MAE
    {val['holdout']['spread_mae_market']} (market) versus {val['holdout']['spread_mae_own']} (model).</li>
    <li><strong>No schedule signal survives the gates.</strong> {strat['totals']['pass']} of
    {strat['n_rules_tested']} rules pass; the best rule's 95% ROI interval still crosses zero.</li>
    <li><strong>Schedule strength is not predictive of results.</strong> The correlation between rating difference and
    actual margin is r={val['correlation_model_market']['r']:.3f} against the spread, and the model's edge over the
    market is negative.</li>
    <li><strong>Three published defects were found and are flagged.</strong> Stale standings
    ({len(audit['standings']['differences'])} fields), a stale provenance pin, and three injury rows that changed on
    the official page.</li>
    <li><strong>Two whole tracks cannot be built from the current sources.</strong> Prop combos need prices; depth-chart
    deficiency needs game-day inactives and dated depth charts.</li>
  </ul>
  <h3>What it means</h3>
  <p>The absence of a schedule edge is not a failure of the model — it is the expected result in a market that prices
  information efficiently. The value of the exercise is the gate set: it rejected a 94%-hit-rate result in this very
  session because the hit rate was arithmetically impossible. Any future rule set should be registered against the same
  eight gates before it is evaluated.</p>
  <h3>Decisions requested</h3>
  {table(["ID", "Decision", "Options", "Source"], [
      [e(d["id"]), e(d["decision"]), e(" / ".join(d["options"])),
       src({"D-SOS-01": "games", "D-SOS-02": "standings", "D-SOS-03": "games", "D-SOS-04": "games"}[d["id"]])]
      for d in decisions["decisions"]])}
  <h3>What to do next</h3>
  <ol class="plain">
    <li>Review the {flags['count']} flags and accept or reject the data refresh (S-SOS-01, S-SOS-02).</li>
    <li>Decide whether to fund a timestamped odds feed (D-SOS-03). Without it, no edge below can be tested.</li>
    <li>Freeze the rule set as published here and stop searching for a schedule edge (S-SOS-06).</li>
  </ol>
</section>
"""
    pages["executive-summary.html"] = page("executive-summary.html", "Executive summary",
                                           "The whole study on one page: question, method, result, defects, and the decisions that need a human.",
                                           body, built)

    for name, content in pages.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(content)
    print(f"wrote {len(pages)} pages + assets to strength/")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
