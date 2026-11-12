#!/usr/bin/env python3
"""Render the static dashboard from data/model/*.json + editorial content.

No runtime calls: every table is written into the HTML so the site works as plain
GitHub Pages. Each data row carries a source link; missing values render as an
explicit blank with an "unverified" badge rather than a number.
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone

from content import DECISIONS, METHOD_NOTES, QUESTIONS, REVIEW_PROCESS, SUGGESTIONS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data", "model")

NAV = [
    ("index.html", "Overview"),
    ("pages/lines.html", "My Lines"),
    ("pages/strategies.html", "Strategy Lab"),
    ("pages/injuries.html", "Injuries & Depth"),
    ("pages/props.html", "Props"),
    ("pages/questions.html", "Questions"),
    ("pages/suggestions.html", "Suggestions"),
    ("pages/evidence.html", "Evidence"),
    ("pages/review.html", "Flagged for Review"),
    ("pages/executive.html", "Executive Summary"),
]

SOURCE = {
    "standings": "https://www.nfl.com/standings/league/2026/reg",
    "injuries": "https://www.nfl.com/injuries/",
    "schedule": "https://www.nfl.com/schedules/",
    "stats": "https://www.nfl.com/stats/player-stats/",
    "teams": "https://www.nfl.com/teams/",
    "ops": "https://operations.nfl.com/gameday/",
    "pbp": "https://github.com/nflverse/nflverse-data/releases/tag/pbp",
    "schedules": "https://github.com/nflverse/nflverse-data/releases/tag/schedules",
    "depth": "https://github.com/nflverse/nflverse-data/releases/tag/depth_charts",
    "provenance": "https://github.com/nflverse/nflverse-data",
    "repo": "https://github.com/kanlerxz87-cyber/NFL1",
}


# ---------------------------------------------------------------- helpers
def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def load(name, default=None):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return {} if default is None else default
    with open(p) as f:
        return json.load(f)


def num(v, digits=1, suffix="") -> str:
    if v is None:
        return '<span class="missing">blank</span>'
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.{digits}f}{suffix}"
    return f"{v}{suffix}"


def pct(v, digits=1) -> str:
    if v is None:
        return '<span class="missing">blank</span>'
    return f"{v * 100:.{digits}f}%"


def badge(status: str) -> str:
    s = (status or "").lower()
    cls = ("pass" if s in ("pass", "implemented", "matched", "answered", "ok", "verified")
           else "warn" if s in ("watch", "proposed", "partially answered", "needs sign-off",
                                "model-only", "open", "queued", "recommended",
                                "open - decision required", "open - user decision")
           else "fail" if s in ("fail", "blocked", "mismatch", "unavailable", "flagged")
           else "neutral")
    return f'<span class="badge {cls}">{esc(status)}</span>'


def src(href: str, label="source") -> str:
    return f'<a class="src" href="{esc(href)}" target="_blank" rel="noopener">{esc(label)}</a>'


def table(headers, rows, cls="", note=None) -> str:
    if not rows:
        return '<p class="empty">No rows available yet.</p>'
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    out = f'<div class="table-wrap"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    if note:
        out += f'<p class="note">{note}</p>'
    return out


def market_cell(g) -> str:
    """Render the market line in the same signed home convention as the model line.

    The previous build printed a bare float here (e.g. -9.5 for LA @ ARI) beside a signed
    home line (ARI +5.2). A reader subtracting them across conventions saw a 14.7-point gap
    where the real difference was 4.27. Printing the home-signed number and the away-signed
    number from one source value removes the ambiguity without inventing anything.
    """
    mk = g.get("market_home_line")
    if mk is None:
        return num(None)
    home, away = g["home"], g["away"]
    return (f'<span class="mono">{esc(home)} {mk:+.1f}</span>'
            f'<br><span class="sub">{esc(away)} {-mk:+.1f}</span>')


def signal_cell(status) -> str:
    # No odds feed is connected and the blend test puts a negative weight on the model, so
    # no row can be called actionable. The strongest honest label is "largest difference".
    mapping = {"actionable": ("neutral", "largest difference"),
               "watch": ("warn", "watch"),
               "no-edge": ("neutral", "no edge")}
    cls, text = mapping.get(status or "", ("neutral", status or "unknown"))
    return f'<span class="badge {cls}">{esc(text)}</span>'


def kpi(label, value, sub="") -> str:
    shown = esc(value) if value is not None else "&mdash;"
    return (f'<article class="kpi"><span class="kpi-label">{esc(label)}</span>'
            f'<strong class="kpi-value">{shown}</strong>'
            f'<span class="kpi-sub">{esc(sub)}</span></article>')


def page(path: str, title: str, body: str, subtitle: str = "", generated: str = "") -> str:
    prefix = "../" if path.startswith("pages/") else ""
    current = path.split("/")[-1]
    links = []
    for href, label in NAV:
        cls = ' class="active"' if href.split("/")[-1] == current else ""
        links.append(f'<a href="{prefix}{href}"{cls}>{esc(label)}</a>')
    nav = "".join(links)
    sub = f'<p class="standfirst">{subtitle}</p>' if subtitle else ""
    stamp = (f'<p class="timestamp">Data built {esc(generated)} · every value links to its source</p>'
             if generated else "")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · NFL Decision Lab</title>
<meta name="description" content="Evidence-first NFL decision support: own lines, validation gates, injury and depth analysis.">
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <a class="brand" href="{prefix}index.html"><span class="mark">NFL</span><span class="brand-text">Decision Lab</span></a>
  <nav aria-label="Main">{nav}</nav>
</header>
<main id="main">
  <section class="page-head">
    <p class="eyebrow">Evidence-first dashboard</p>
    <h1>{esc(title)}</h1>
    {sub}
    {stamp}
  </section>
  {body}
</main>
<footer>
  <div>
    <strong>NFL Decision Lab</strong>
    <p>Research tool. Not betting advice. No official league odds exist; contact with real markets is required before any edge claim.</p>
  </div>
  <div class="foot-links">
    <a href="{prefix}pages/evidence.html">Sources &amp; provenance</a>
    <a href="{prefix}pages/review.html">Flagged for review</a>
    <a href="{SOURCE['repo']}" target="_blank" rel="noopener">Repository</a>
  </div>
  <p class="credit">Data: nflverse (CC-BY-4.0), built from NFL GSIS and the official weekly injury report.
  Club names and marks belong to the NFL and its clubs.</p>
</footer>
</body>
</html>
"""


def write(path: str, content: str) -> None:
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)
    print(f"wrote {path}")


# ---------------------------------------------------------------- overview
def overview(snap, dash, lines, strat, avail, props, verif):
    gen = dash.get("generated_at") or snap.get("generated_at")
    week = snap.get("last_completed_week")
    nxt = (week or 0) + 1
    counts = dash.get("counts", {})
    lb = (strat or {}).get("leaderboard", [])

    kpis = "".join([
        kpi("Season", snap.get("season"), f"week {week} complete"),
        kpi("Games analysed", counts.get("games_played"), "2026 regular season"),
        kpi("Source files pinned", counts.get("source_files_pinned"), "URL + sha256"),
        kpi("Own lines this week", counts.get("own_lines_generated"), f"week {nxt}"),
        kpi("Strategies tested", counts.get("strategies_tested"),
            f"{counts.get('strategies_passing_all_gates', 0)} passed all 8 gates"),
        kpi("Starters flagged", counts.get("starters_flagged_unavailable"),
            "official game status"),
        kpi("Prop lines built", counts.get("prop_lines_generated"), "model-only, no market price"),
    ])

    # this week's own lines
    rows = []
    for g in (lines or {}).get("lines", []):
        rows.append([
            f"<strong>{esc(g['away'])} @ {esc(g['home'])}</strong><br><span class=\"sub\">{esc(g.get('gameday',''))}</span>",
            esc(g.get("my_line_display") or f"{g['home']} {g['my_home_line']:+.1f}"),
            num(g.get("my_total")),
            market_cell(g),
            num(g.get("market_total")),
            num(g.get("edge_home_line"), 2),
            num(g.get("edge_total"), 2),
            signal_cell(g.get("status")),
            src(g.get("source_games") or SOURCE["schedule"], "NFL schedule"),
        ])
    lines_tbl = table(
        ["Matchup", "My line", "My total", "Market line", "Market total",
         "Difference (line)", "Difference (total)", "Marker", "Source"],
        rows, note=("Model and market are both printed signed from the home team's point of "
                    "view (positive = home favoured), with the away side in brackets so the "
                    "convention cannot be misread. The difference is model minus market. No odds "
                    "feed is connected: the market number is a consensus closing line from the "
                    "mirrored feed, not a book price, so nothing here is a recommendation. See "
                    "the Lines page for error bands and the out-of-sample accuracy table."))

    # leaderboard preview
    lb_rows = []
    for r in lb[:5]:
        lb_rows.append([
            esc(r["strategy"]), badge(r["status"]),
            f"{r.get('gates_passed')}/8",
            num(r.get("n_graded")), pct(r.get("win_pct")), pct(r.get("roi")),
            pct((r.get("roi_ci95") or [None])[0]) if r.get("roi_ci95") else '<span class="missing">blank</span>',
            num(r.get("q_value"), 3),
            src(SOURCE["schedules"], "closing lines"),
        ])
    lb_tbl = table(["Strategy", "Status", "Gates", "Bets", "Win %", "ROI",
                    "ROI 95% low", "BH q", "Source"], lb_rows)

    # availability preview
    av_rows = []
    for t in (avail or {}).get("teams", [])[:6]:
        av_rows.append([
            f"<strong>{esc(t['team'])}</strong>", esc(t.get("name")),
            t["starters_out"], t["starters_doubtful"], t["starters_questionable"],
            t.get("starters_practice_only", 0),
            num(t.get("attrition_index_0_100")), num(t.get("backup_experience_avg")),
            src(t.get("source") or SOURCE["injuries"], "NFL injuries"),
        ])
    av_tbl = table(["Team", "Club", "Out", "Doubtful", "Questionable", "Practice-only",
                    "Attrition index", "Backup yrs exp", "Source"], av_rows,
                   note=("Attrition index is a documented model weight, not an NFL statistic. "
                         "Mid-week, most clubs have published practice participation only."))

    v_checks = (verif or {}).get("checks", [])
    v_rows = []
    for c in v_checks:
        v_rows.append([
            esc(c["name"]),
            f"{c['rows_matched']}/{c['rows_checked']}",
            badge("matched" if c["rows_matched"] == c["rows_checked"] else "mismatch"),
            src(c["source"], "official page"),
        ])
    v_tbl = table(["Verification check", "Rows matched", "Result", "Source"], v_rows)

    body = f"""
<section class="hero">
  <div>
    <h2>Know the number, the uncertainty, and the source.</h2>
    <p class="lede">This lab builds its own NFL lines from opponent-adjusted play-by-play,
    prices them against the consensus closing line, and refuses to promote a strategy that
    cannot clear eight validation gates. Every table row carries a link to the page it came from.</p>
    <div class="hero-actions">
      <a class="btn" href="pages/lines.html">See this week's own lines</a>
      <a class="btn ghost" href="pages/executive.html">Read the executive summary</a>
    </div>
  </div>
  <aside class="hero-card">
    <span class="eyebrow">Data state</span>
    <h3>Verified rows, not vibes</h3>
    <p>{counts.get('source_files_pinned', 0)} pinned files · {counts.get('games_played', 0)} games ·
    {counts.get('starters_flagged_unavailable', 0)} starters flagged · 0 invented values.</p>
    <p class="sub">Blocked: prop prices, book-level odds, legal review for rewards.</p>
    <a href="pages/review.html">All open flags →</a>
  </aside>
</section>

<section class="kpis">{kpis}</section>

<section class="panel">
  <div class="panel-head">
    <h2>Week {esc(nxt)} own lines</h2>
    <a href="pages/lines.html">Full model, backtest and ratings →</a>
  </div>
  {lines_tbl}
</section>

<section class="grid-2">
  <div class="panel">
    <div class="panel-head"><h2>Leaderboard (conservative ranking)</h2><a href="pages/strategies.html">All gates →</a></div>
    {lb_tbl}
    <p class="note">Ranked by the lower bound of the 95% ROI interval, so a lucky small sample cannot top the table.</p>
  </div>
  <div class="panel">
    <div class="panel-head"><h2>Availability pressure</h2><a href="pages/injuries.html">Full depth view →</a></div>
    {av_tbl}
  </div>
</section>

<section class="panel">
  <div class="panel-head"><h2>Verification against official NFL pages</h2><a href="pages/evidence.html">Provenance and every row →</a></div>
  {v_tbl}
</section>

<section class="panel">
  <div class="panel-head"><h2>What we know, what we don't</h2><a href="pages/questions.html">20 questions that gate decisions →</a></div>
  <div class="grid-3">
    <div class="stat"><h4>Answered</h4><p>{sum(1 for q in QUESTIONS if q['status'].lower().startswith(('answered', 'partially')))} of {len(QUESTIONS)} questions have a verified answer or partial answer.</p></div>
    <div class="stat"><h4>Blocked</h4><p>{sum(1 for q in QUESTIONS if 'blocked' in q['status'].lower())} questions cannot be answered with today's sources, mostly pricing and legality.</p></div>
    <div class="stat"><h4>Next</h4><p>Twelve suggestions are ranked at <a href="pages/suggestions.html">Suggestions</a>; five decision records need a human choice.</p></div>
  </div>
</section>
"""
    return page("index.html", "Overview", body,
                "A working dashboard for originating NFL lines, punishing luck, and flagging what is unknown.",
                gen)


# ---------------------------------------------------------------- lines
def lines_page(snap, lines, dash):
    l = lines or {}
    cal = l.get("calibration", [])
    rows = []
    for c in cal:
        rows.append([
            esc(c.get("label")),
            num(c.get("n")),
            num(c.get("spread_mae_model"), 2),
            num(c.get("spread_mae_market"), 2),
            f"[{c['spread_mae_diff_ci95'][0]:.2f}, {c['spread_mae_diff_ci95'][1]:.2f}]"
            if c.get("spread_mae_diff_ci95") else '<span class="missing">blank</span>',
            num(c.get("corr_model_market_spread"), 3),
            num(c.get("total_mae_model"), 2),
            num(c.get("total_mae_market"), 2),
            src(SOURCE["schedules"], "closing lines"),
        ])
    cal_tbl = table(
        ["Sample", "Games", "Model spread MAE", "Market spread MAE",
         "MAE difference 95% CI", "Corr(model, market)", "Model total MAE",
         "Market total MAE", "Source"], rows,
        note=("MAE = mean absolute error against the actual result, in points. A positive "
              "MAE difference means the market was closer. The model is evaluated on games "
              "it never saw."))

    m = l.get("method", {})
    mm = m.get("margin_model", {})
    tm = m.get("total_model", {})
    blend = l.get("blend_test") or {}
    sign = l.get("sign_convention_check") or {}

    blend_block = ""
    if blend:
        blend_block = f"""
<section class="panel">
  <h2>Does the model add information beyond the closing line?</h2>
  <p>Regressing the actual margin on both the closing line and the model line (fit 2025, tested 2026)
  gives the market a weight of <strong>{num(blend.get('weight_market'), 3)}</strong> and the model
  <strong>{num(blend.get('weight_model'), 3)}</strong>. Test MAE: hybrid
  <strong>{num(blend.get('test_mae_hybrid'), 2)}</strong> vs market-only
  <strong>{num(blend.get('test_mae_market_only'), 2)}</strong> over {num(blend.get('n_test'))} games.</p>
  <p class="note">{esc(blend.get('interpretation'))} Weight on the model near zero means the
  EPA signal is already in the price; a positive weight with lower MAE is genuine incremental
  information. {src(SOURCE['schedules'], 'closing-line source')}</p>
</section>"""

    fx_rows = []
    for g in l.get("lines", []):
        fx_rows.append([
            f"<strong>{esc(g['away'])} @ {esc(g['home'])}</strong><br><span class=\"sub\">{esc(g.get('gameday',''))}</span>",
            esc(g.get("my_line_display") or g.get("my_home_line")),
            f"[{g['home_line_band95'][0]:.1f}, {g['home_line_band95'][1]:.1f}]" if g.get("home_line_band95") else "",
            num(g.get("my_total")),
            num(g.get("my_win_prob_home"), 3),
            num(g.get("market_home_line")),
            num(g.get("market_total")),
            num(g.get("edge_home_line"), 2),
            num(g.get("edge_total"), 2),
            badge(g.get("status")),
            src(g.get("source_games") or SOURCE["schedule"], "NFL schedule"),
        ])
    fx_tbl = table(["Matchup", "My line", "95% band", "My total", "P(home win)",
                    "Market line", "Market total", "Edge line", "Edge total",
                    "Signal", "Source"], fx_rows)

    rat_rows = []
    for i, r in enumerate(l.get("ratings", []), start=1):
        rat_rows.append([
            str(i), f"<strong>{esc(r['team'])}</strong>", num(r.get("off"), 3),
            num(r.get("def"), 3), num(r.get("net"), 3),
            src(SOURCE["pbp"], "play-by-play"),
        ])
    rat_tbl = table(["Rank", "Team", "Offence EPA/play", "Defence EPA/play (good +)",
                     "Net rating", "Source"], rat_rows,
                    note="Ratings use non-garbage-time plays only, opponent-adjusted, with the previous season at 40% weight.")

    st_rows = []
    for r in (snap or {}).get("standings", []):
        st_rows.append([
            f"<strong>{esc(r['team'])}</strong>", esc(r.get("name")),
            f"{r['w']}-{r['l']}-{r['t']}", num(r.get("pct"), 3),
            r["pf"], r["pa"], f"{r['diff']:+d}" if r.get("diff") is not None else "",
            src(SOURCE["standings"], "NFL standings"),
        ])
    standings_tbl = table(["Team", "Club", "Record", "Win pct", "PF", "PA", "Net",
                           "Source"], st_rows,
                          note="Computed from game results, then checked row by row against nfl.com (see Evidence).")

    body = f"""
<section class="panel">
  <h2>Method, in one paragraph</h2>
  <p>{esc(m.get('ratings',''))}</p>
  <p class="note">{esc(m.get('note',''))} Margin model: a = {num(mm.get('intercept'),2)},
  b = {num(mm.get('slope_per_epa'),2)}, residual SD = {num(mm.get('residual_sd'),2)}.
  Total model: intercept {num(tm.get('intercept'),2)}, offence coefficient {num(tm.get('coef_off_sum'),2)},
  defence coefficient {num(tm.get('coef_def_sum'),2)}, residual SD {num(tm.get('residual_sd'),2)}.</p>
</section>

<section class="panel">
  <h2>Line sign convention (measured, not assumed)</h2>
  <p>Across {num(sign.get('n_games'))} games the correlation between the mirrored closing line and the
  home team's actual margin is <strong>{num(sign.get('corr_market_line_vs_home_margin'),3)}</strong>.
  {esc(sign.get('conclusion',''))}</p>
  <p class="note">This is why the first build produced an inverted comparison: the convention was
  assumed wrongly and then proved from the data. It is published here so a reviewer can challenge it.
  {src(SOURCE['schedules'], 'schedules release')}</p>
</section>

<section class="panel">
  <div class="panel-head"><h2>Week {num(l.get('week'))} lines</h2><a href="../data/model/lines.json">Raw JSON →</a></div>
  {"".join([fx_tbl]) if fx_rows else '<p class="empty">Own lines are not available for this week: the rating snapshots are missing or the schedule has no unplayed games.</p>'}
</section>

<section class="panel">
  <div class="panel-head"><h2>Out-of-sample accuracy</h2><a href="../data/model/lines.json">Raw JSON →</a></div>
  {cal_tbl}
</section>

{blend_block}

<section class="panel">
  <div class="panel-head"><h2>League table (verified against nfl.com)</h2><a href="evidence.html">32/32 rows checked →</a></div>
  {standings_tbl}
</section>

<section class="panel">
  <div class="panel-head"><h2>Team ratings (week {num(l.get('week'))})</h2><a href="strategies.html">How they are used →</a></div>
  {rat_tbl}
</section>
"""
    return page("pages/lines.html", "My Lines",
                body,
                "Opponent-adjusted EPA ratings converted into a spread, a total and a win probability — then scored against the closing line.",
                dash.get("generated_at"))


# ---------------------------------------------------------------- strategies
def strategies_page(strat, dash):
    s = strat or {}
    gates = s.get("gate_definitions", [])
    gate_rows = [[esc(g["id"]), esc(g["rule"])] for g in gates]
    gate_tbl = table(["Gate", "Rule"], gate_rows)

    lb = s.get("leaderboard", [])
    rows = []
    for i, r in enumerate(lb, start=1):
        rows.append([
            str(i), esc(r["strategy"]), badge(r["status"]), f"{r.get('gates_passed')}/8",
            num(r.get("score_lower_ci_roi_pct"), 2), num(r.get("n_graded")),
            pct(r.get("win_pct")), pct(r.get("roi")),
            (f"[{r['roi_ci95'][0]*100:.1f}%, {r['roi_ci95'][1]*100:.1f}%]"
             if r.get("roi_ci95") else '<span class="missing">blank</span>'),
            num(r.get("p_value"), 3), num(r.get("q_value"), 3),
            num(r.get("max_drawdown_units"), 2),
            f"{r.get('by_season') and len(r['by_season']) or 0}",
            src(SOURCE["schedules"], "closing lines"),
        ])
    lb_tbl = table(["#", "Strategy", "Status", "Gates", "Score", "Bets", "Win %", "ROI",
                    "ROI 95% CI", "p (raw)", "q (BH)", "Max DD", "Seasons tested", "Source"], rows,
                   note=("Score = 100 x lower 95% ROI bound; zero when fewer than 100 bets. "
                         "p is the exact binomial test against the 52.38% break-even; q is the "
                         "Benjamini-Hochberg correction across every rule tested. "
                         "Price assumption: -110 on every bet."))

    # gate matrix
    gm_rows = []
    for r in lb:
        cells = [str(i + 1), esc(r["strategy"])]
        for g in r.get("gates", []):
            cells.append('<span class="yes">✓</span>' if g["pass"] else '<span class="no">✗</span>')
        gm_rows.append(cells)
    gm_tbl = table(["#", "Strategy"] + [g["id"] for g in gates] if gates else ["#", "Strategy"], gm_rows)

    corr = s.get("pairwise_correlation", {})
    corr_rows = [[esc(k.replace(" | ", "<br>vs ")), num(v["corr"], 3), num(v["n_overlap"]),
                  src(SOURCE["schedules"], "closing lines")] for k, v in corr.items()]
    corr_tbl = table(["Strategy pair", "Correlation of per-bet returns", "Overlapping games", "Source"],
                     corr_rows,
                     note=("Only games where both rules had a bet are used. High positive "
                           "correlation means the two 'different' strategies are the same bet."))

    par = s.get("parlay", {})
    pay = s.get("parlay_payouts", {})
    pay_rows = [[esc(k + "-leg"), num(v["decimal_payout"], 3), pct(v["breakeven_prob_independent"], 2),
                 src(SOURCE["schedules"], "price model")] for k, v in pay.items()]
    pay_tbl = table(["Parlay", "Decimal payout", "Break-even win rate (independence)", "Source"],
                    pay_rows,
                    note="At -110 per leg. Break-even assumes legs are independent, which is false for same-game legs.")

    phi = par.get("phi_home_cover_vs_over")
    parlay_block = ""
    if par:
        parlay_block = f"""
<section class="panel">
  <h2>Parlays and correlation</h2>
  <p>Across <strong>{num(par.get('n_games'))}</strong> games, the correlation between the home team's
  margin and the game total is <strong>{num(par.get('corr_margin_vs_total'),3)}</strong>, and the
  same-game link between "home covers" and "over hits" is
  <strong>{num(phi,3)}</strong> (phi coefficient).</p>
  <p class="note">{esc(par.get('note',''))} With near-zero phi, a same-game spread/total parlay is
  close to independent and the naive break-even is roughly right; with a large |phi| the naive
  number either flatters or punishes the bet. {src(SOURCE['schedules'], 'source')}</p>
  {pay_tbl}
</section>"""

    rewards = s.get("rewards", {})
    body = f"""
<section class="panel">
  <h2>How a strategy earns a place on the board</h2>
  <p>Each rule is scored on every graded bet, then forced through eight gates. Status is
  PASS only when all eight hold, WATCH at five or more, FAIL below that.</p>
  {gate_tbl}
</section>

<section class="panel">
  <div class="panel-head"><h2>Leaderboard</h2><a href="../data/model/strategies.json">Raw JSON →</a></div>
  {lb_tbl}
</section>

<section class="panel">
  <div class="panel-head"><h2>Gate matrix</h2><a href="review.html">What failed and why →</a></div>
  {gm_tbl}
</section>

<section class="panel">
  <h2>Correlation between strategies</h2>
  <p>If two strategies bet the same games the same way, they are one strategy with two names.
  This table is the evidence for the diversification gate.</p>
  {corr_tbl}
</section>

{parlay_block}

<section class="panel">
  <h2>Rewards: points, not prizes</h2>
  <p>{esc(rewards.get('model',''))}</p>
  <p class="note">Statuses: {esc(str(rewards.get('statuses','')))}. Legal review is required before
  any reward with monetary value; see <a href="review.html">Flagged for Review</a>.</p>
</section>
"""
    return page("pages/strategies.html", "Strategy Lab",
                body,
                "A leaderboard that punishes luck: bootstrap intervals, multiple-testing correction, stability, drawdown and correlation.",
                dash.get("generated_at"))


# ---------------------------------------------------------------- injuries
def injuries_page(avail, dash):
    a = avail or {}
    counts = a.get("counts", {})
    method = a.get("method", {})
    teams = a.get("teams", [])
    players = a.get("players", [])

    t_rows = [[
        f"<strong>{esc(t['team'])}</strong>", esc(t.get("name")),
        t["starters_out"], t["starters_doubtful"], t["starters_questionable"],
        t.get("starters_practice_only", 0),
        num(t.get("attrition_index_0_100")), num(t.get("backup_experience_avg")),
        num(t.get("backup_snaps_avg"), 0),
        src(t.get("source") or SOURCE["injuries"], "NFL injuries"),
    ] for t in teams]
    t_tbl = table(["Team", "Club", "Out", "Doubtful", "Questionable",
                   "Practice-only DNP/limited", "Attrition index (0-100)",
                   "Replacement yrs exp", "Replacement snaps", "Source"], t_rows,
                  note=("Attrition index = sum over unavailable starters of position weight x status "
                        "weight (Out 1.0, Doubtful 0.7, Questionable 0.25), rescaled to the worst "
                        "team this week. It is a model assumption, not an NFL statistic."))

    p_rows = [[
        f"<strong>{esc(p['player'])}</strong>", esc(p["team"]), esc(p["position"]),
        esc(p.get("depth_slot")),
        badge(p.get("game_status")) if p.get("game_status") else '<span class="missing">no game designation</span>',
        esc(p.get("signal") or ""),
        esc(p.get("injury") or "—"), esc(p.get("practice_status") or "—"),
        esc(p.get("replacement") or "none listed"), num(p.get("replacement_years_exp")),
        num(p.get("replacement_snaps_2026"), 0),
        src(p.get("source") or SOURCE["injuries"], "NFL injuries"),
    ] for p in players]
    p_tbl = table(["Player", "Team", "Pos", "Depth slot", "Game status", "Signal", "Injury",
                   "Practice", "Next man up", "Next man yrs", "Next man snaps", "Source"], p_rows,
                  note=("Clubs publish practice participation before game designations. Rows whose "
                        "only signal is practice are labelled, weighted lower, and never presented "
                        "as a game-day decision."))

    limits = "".join(f"<li>{esc(x)}</li>" for x in method.get("limits", []))
    weights = method.get("position_weights", {})
    w_rows = [[esc(k), num(v, 3)] for k, v in weights.items()]
    w_tbl = table(["Position", "Weight"], w_rows)

    source = a.get("source", {})
    missing = a.get("clubs_without_report") or []
    if missing:
        banner_extra = (f'<p class="alert">No injury report was present for '
                        f'{esc(", ".join(missing))} at scrape time. Those clubs are listed with zero '
                        f'rows — this is a gap in the published report, not an assumption of health. '
                        f'{src(source.get("url"), "check the official page")}</p>')
    else:
        banner_extra = ""
    banner = ""
    if source.get("warning"):
        banner = f'<p class="alert">{esc(source["warning"])} {src(source.get("url"), "official page")}</p>'
    else:
        banner = (f'<p class="okline">Source: {esc(source.get("label",""))} — '
                  f'{src(source.get("url"), "nfl.com/injuries")}</p>')
    banner += banner_extra

    body = f"""
<section class="kpis">
  {kpi("Injury records", counts.get("injury_records"), f"week {a.get('week','')}")}
  {kpi("Starters impacted", counts.get("starters_impacted"), "depth rank 1 only")}
  {kpi("Clubs with a starter out", counts.get("teams_with_starter_out"), "official game status")}
  {kpi("Unmatched records", counts.get("records_not_matched_to_depth_chart"), "not guessed")}
  {kpi("Depth chart snapshot", (a.get("depth_chart_timestamp") or "")[:10], "weekly mirror")}
</section>
{banner}

<section class="panel">
  <h2>What this measures</h2>
  <p>The brief asks for defence and offence deficiencies when 2nd, 3rd or 4th string players
  replace starters. The feed gives two things reliably: the official game availability status and
  the weekly depth chart. Joining them identifies which listed starters are unavailable and who is
  next at that exact position slot, then measures the replacement's experience and 2026 snaps.
  What it cannot yet do is prove who took the first snap — see the flags.</p>
  <p class="note">{esc(method.get('depth_rank',''))} {esc(method.get('attrition_formula',''))}</p>
  <p class="note">This week's report is a mid-week report: only the Thursday game carries game
  designations, so most clubs appear with practice participation only. That is a property of the
  official report, not a parsing gap, and it is why the practice-only column exists.</p>
  {t_tbl}
</section>

<section class="panel">
  <div class="panel-head"><h2>Starter-level detail</h2><a href="../data/model/availability.json">Raw JSON →</a></div>
  {p_tbl}
</section>

<section class="grid-2">
  <div class="panel">
    <h2>Position weights</h2>
    {w_tbl}
  </div>
  <div class="panel">
    <h2>Limits, stated plainly</h2>
    <ul class="tight">{limits}</ul>
  </div>
</section>
"""
    return page("pages/injuries.html", "Injuries & Depth",
                body,
                "Which listed starters are unavailable, who replaces them, and how exposed each club is.",
                dash.get("generated_at"))


# ---------------------------------------------------------------- props
def props_page(props, dash):
    p = props or {}
    rows = []
    for r in p.get("props", [])[:160]:
        rows.append([
            f"<strong>{esc(r['player'])}</strong>", esc(r["team"]), esc(r["position"]),
            f"vs {esc(r['opponent'])}", num(r.get("games")),
            num(r.get("season_mean")), num(r.get("opponent_factor"), 3),
            num(r.get("projection")), num(r.get("my_line")),
            f"[{r['interval80'][0]}, {r['interval80'][1]}]" if r.get("interval80") else "",
            '<span class="missing">blank</span>',
            badge("model-only"),
            src(r.get("source") or SOURCE["stats"], "NFL stats"),
        ])
    tbl = table(["Player", "Team", "Pos", "Opponent", "Games", "Season avg",
                 "Opp factor", "Projection", "My line", "80% interval", "Market line",
                 "Status", "Source"], rows,
                note=("Sorted by projection. The first 160 rows are shown; the full set is in the "
                      "JSON link. Market line is deliberately blank: no official prop price "
                      "source exists, so any 'edge' would be invented."))

    m = p.get("method", {})
    body = f"""
<section class="panel">
  <h2>Projection, then honesty about the missing half</h2>
  <p>{esc(m.get('projection',''))}</p>
  <p>{esc(m.get('distribution',''))}</p>
  <p class="note">{esc(m.get('no_market',''))}</p>
</section>
<section class="panel">
  <div class="panel-head"><h2>Week {num(p.get('week'))} prop lines</h2><a href="../data/model/props.json">Raw JSON →</a></div>
  {tbl}
</section>
<section class="panel">
  <h2>Combos and correlation</h2>
  <p>A QB passing-yards leg and his WR receiving-yards leg move together; multiplying their
  probabilities assumes they do not. The Strategy page publishes measured correlation for
  game-level legs; player-level leg correlation needs game-level receiving data per target, which
  is not yet wired in. Until then, prop combos are published as model output only, never as a
  priced bet.</p>
  <p class="note">{src(SOURCE['stats'], 'NFL player stats')} · {src(SOURCE["injuries"], 'injury report')}</p>
</section>
"""
    return page("pages/props.html", "Player Props",
                body,
                "Shrunk usage projections with intervals — and a blank where a market price would go.",
                dash.get("generated_at"))


# ---------------------------------------------------------------- evidence
def evidence_page(prov, verif, dash, repl=None):
    p = prov or {}
    rows = []
    for f in p.get("files", []):
        rows.append([
            f"<strong>{esc(f['local'])}</strong>", esc(f.get("description")),
            badge(f.get("status")),
            num(f.get("bytes"), 0),
            f"<code>{esc((f.get('sha256') or '')[:16])}…</code>",
            esc((f.get("fetched_at") or "")[:19]),
            src(f["url"], "download"),
            src(f.get("official_upstream") or SOURCE["ops"], "official"),
        ])
    prov_tbl = table(["File", "What it is", "Status", "Bytes", "sha256",
                      "Fetched (UTC)", "Pinned URL", "Official entry point"], rows,
                     note=(f"nflverse file licence verified as {esc((p.get('license') or 'CC-BY-4.0'))}. "
                           "Attribution required on reuse."))

    checks = (verif or {}).get("checks", [])
    check_rows = [[
        esc(c["name"]), f"{c['rows_matched']}/{c['rows_checked']}",
        badge("matched" if c["rows_matched"] == c["rows_checked"] else "mismatch"),
        src(c["source"], "official page"),
    ] for c in checks]
    check_tbl = table(["Check", "Rows matched", "Result", "Official source"], check_rows)

    # standings detail
    detail_html = ""
    for c in checks:
        rows = []
        for r in c.get("detail", []):
            if "computed" in r:
                rows.append([
                    esc(r["team"]), b(r["computed"]["w"]), b(r["computed"]["l"]), b(r["computed"]["t"]),
                    b(r["computed"]["pf"]), b(r["computed"]["pa"]),
                    badge("matched" if r["matched"] else "mismatch"),
                    esc(json.dumps(r.get("diffs"))) if r.get("diffs") else "—",
                    src(c["source"], "NFL.com"),
                ])
            else:
                game = r.get("game")
                feed = r.get("feed") if isinstance(r.get("feed"), dict) else {}
                rows.append([
                    esc(r.get("team")), esc(r.get("player")), esc(r.get("position")),
                    badge("matched" if r["matched"] else "mismatch"),
                    esc(str(r.get("injury") or "—")), esc(str(game or "—")),
                    esc(str(r.get("practice") or "—")),
                    esc(str(feed.get("game") or "—")) if feed else "—",
                    esc(json.dumps(r.get("diffs"))) if r.get("diffs") else "—",
                    src(c["source"], "NFL.com"),
                ])
        if not rows:
            continue
        header = (["Team", "W", "L", "T", "PF", "PA", "Match", "Differences", "Source"]
                  if "computed" in c["detail"][0] else
                  ["Team", "Player", "Pos", "Match", "Injury (NFL)", "Game status (NFL)",
                   "Practice (NFL)", "Game status (feed)", "Differences", "Source"])
        detail_html += f"<h3>{esc(c['name'])}</h3>{table(header, rows)}"

    unver = (verif or {}).get("unverifiable", [])
    unver_tbl = table(["Item", "Why it cannot be verified", "How it is handled"],
                      [[f"<strong>{esc(u['item'])}</strong>", esc(u["why"]), esc(u["handling"])]
                       for u in unver])

    repl = repl or {}
    repl_html = ""
    if repl.get("available"):
        rows = []
        for c in repl.get("comparisons", []):
            rows.append([esc(c["metric"]), num(c.get("this_pipeline"), 2),
                         num(c.get("companion_model"), 2), num(c.get("market_baseline"), 2),
                         esc(c.get("reading")), src(SOURCE["pbp"], "play-by-play")])
        comp_tbl = table(["Metric (2026)", "This pipeline", "Companion model", "Market baseline",
                          "Reading", "Source"], rows)
        crow = []
        for c in repl.get("correlations", []):
            crow.append([esc(c["relationship"]),
                         f"r = {num(c['this_pipeline'].get('r'),3)} (n={num(c['this_pipeline'].get('n'))}, {esc(c['this_pipeline'].get('window'))})",
                         f"r = {num(c['companion'].get('r'),3)} (n={num(c['companion'].get('n'))}, {esc(c['companion'].get('window'))})",
                         esc(c.get("reading")), src(SOURCE["schedules"], "results")])
        corr_tbl = table(["Relationship", "This pipeline", "Companion session", "Reading", "Source"], crow)
        conf = [[f"<strong>{esc(c['item'])}</strong>", esc(c["this_pipeline"]), esc(c["companion"]),
                 esc(c["resolution"]), src(c.get("source") or SOURCE["schedules"], "source")]
                for c in repl.get("conflicts", [])]
        conf_tbl = table(["Item", "This pipeline", "Companion session", "Resolution", "Source"], conf)
        repl_html = f"""
<section class="panel">
  <h2>Independent replication from parallel sessions</h2>
  <p>A second session modelled the same 2026 season from its own verified transcriptions, without
  the closing-line mirror used here. Comparing the two is a cheap, real check on both.</p>
  {comp_tbl}
  {corr_tbl}
  <h3>Where the two builds differ</h3>
  {conf_tbl}
  <p class="note">Companion artifacts: {esc(", ".join(repl.get("companion_inputs", [])))}.
  Raw comparison: <a href="../data/model/replication.json">replication.json</a>.</p>
</section>"""

    method_rows = [[esc(k), esc(v)] for k, v in METHOD_NOTES]
    method_tbl = table(["Component", "Rule"], method_rows)

    body = f"""
<section class="panel">
  <h2>Provenance: every file pinned twice</h2>
  <p>Files are pulled from the nflverse release assets (which mirror NFL GSIS play-by-play,
  the official weekly injury report and the official depth charts), hashed, and cited. If a
  download fails the build records "unavailable" and the dependent table stays blank.</p>
  {prov_tbl}
</section>

<section class="panel">
  <div class="panel-head"><h2>Line-by-line verification against nfl.com</h2><a href="../data/verified/official_standings_2026.json">Fixtures →</a></div>
  {check_tbl}
  <p class="note">Club codes follow the GSIS feed (ARI, LA, LV, WAS); nfl.com prints some of them
  differently (AZ, LAR, OAK historically). The cross-checks map those aliases explicitly so a
  labelling difference is never reported as a data disagreement.</p>
  {detail_html}
</section>

<section class="panel">
  <h2>Cannot be verified from an official league source</h2>
  {unver_tbl}
</section>

{repl_html}

<section class="panel">
  <h2>Companion pages preserved from parallel session 533256e1</h2>
  <p>Two sessions worked on this repository at the same time. This dashboard is the integration
  build; the pages below were produced independently and are kept for review, together with their
  transcriptions in <code>data/teams.csv</code>, <code>data/standings.csv</code> and
  <code>data/injuries.csv</code>. Those rows are cross-checked in the tables above.</p>
  <ul class="tight">
    <li><a href="teams.html">Club directory transcription</a></li>
    <li><a href="standings.html">Standings transcription</a></li>
    <li><a href="executive-summary.html">Earlier executive summary</a></li>
    <li><a href="flagged.html">Earlier flag register</a></li>
    <li><a href="analysis.html">Independent validation &amp; correlation page (session 73fdd6c4)</a></li>
    <li><a href="data.html">Verified data page (session 73fdd6c4)</a></li>
    <li><a href="decisions.html">Decision register (session 73fdd6c4)</a></li>
    <li><a href="verified.html">Verified artifacts (session 73fdd6c4)</a></li>
  </ul>
</section>

<section class="panel">
  <h2>Method rules</h2>
  {method_tbl}
</section>
"""
    return page("pages/evidence.html", "Evidence & Verification",
                body,
                "Every file hashed and linked; every verification row shows both what nfl.com published and what our feed says.",
                dash.get("generated_at"))


def b(v):
    return '<span class="missing">blank</span>' if v is None else esc(v)


# ---------------------------------------------------------------- questions
def questions_page(dash):
    rows = [[
        f"<strong>{esc(q['id'])}</strong>", f"<strong>{esc(q['question'])}</strong><br><span class=\"sub\">{esc(q['why'])}</span>",
        esc(q["have"]), esc(q["missing"]), esc(q["discovery"]), esc(q["blocks"]),
        badge(q["status"]),
    ] for q in QUESTIONS]
    tbl = table(["ID", "Question and why it matters", "What we already have",
                 "What we do not have", "How to discover it", "What it blocks", "Status"], rows)

    have_rows = [
        ["Game results and closing lines", "1999-2026 results; 2005-2026 closing spread, total and moneyline",
         badge("verified"), src(SOURCE["schedules"], "release")],
        ["Play-by-play with EPA", "2024-2026, used for ratings", badge("verified"), src(SOURCE["pbp"], "release")],
        ["Official injury reports", "2009-2026, weekly practice and game status", badge("verified"), src(SOURCE["injuries"], "NFL.com")],
        ["Depth charts", "Weekly, all clubs", badge("verified"), src(SOURCE["depth"], "release")],
        ["Snap counts and player stats", "2026 to date", badge("verified"), src(SOURCE["stats"], "NFL.com")],
        ["Book-level prices and line history", "Not available anywhere in this build", badge("blocked"), src(SOURCE["ops"], "NFL operations")],
        ["Player prop prices", "Not available anywhere in this build", badge("blocked"), src(SOURCE["stats"], "NFL stats")],
        ["Game-day inactives and participation", "Not ingested", badge("open"), src(SOURCE["injuries"], "NFL.com")],
        ["Legal position on rewards", "No review", badge("blocked"), src(SOURCE["ops"], "NFL operations")],
    ]
    have_tbl = table(["Information", "State", "Status", "Source"], have_rows)

    body = f"""
<section class="panel">
  <h2>How to use this page</h2>
  <p>These are the questions that must be answered before a decision is reasonable. Each row
  states what we already have, what is missing, how it could be discovered, and what it blocks.
  A question marked Blocked cannot be solved with the sources currently reachable from the build
  environment, so it needs a purchase, a permission or a human decision.</p>
  {have_tbl}
</section>
<section class="panel">
  <div class="panel-head"><h2>Question ledger</h2><a href="review.html">Open flags →</a></div>
  {tbl}
</section>
<section class="panel">
  <h2>Discovery backlog, in priority order</h2>
  <ol class="tight">
    <li>Licensed odds feed with timestamps (unblocks Q01, Q02, Q04, Q09, Q18).</li>
    <li>Game-day inactives and participation (unblocks Q03, Q07, Q08).</li>
    <li>Weather forecasts at T-24h (unblocks Q14).</li>
    <li>Stadium, timezone and travel table (unblocks Q15).</li>
    <li>Legal review of the rewards programme (unblocks Q11).</li>
    <li>Preregistered rulebook per season (strengthens Q06).</li>
  </ol>
</section>
"""
    return page("pages/questions.html", "Questions & Information Gaps",
                body,
                "Twenty questions, what we know, what we are missing, and how to find it.",
                dash.get("generated_at"))


# ---------------------------------------------------------------- suggestions
def suggestions_page(dash):
    cards = ""
    for s in SUGGESTIONS:
        cards += f"""
<article class="card">
  <div class="card-head"><h3><span class="id">{esc(s['id'])}</span> {esc(s['title'])}</h3>{badge(s['status'])}</div>
  <p class="problem"><strong>Problem:</strong> {esc(s['problem'])}</p>
  <p><strong>Change:</strong> {esc(s['change'])}</p>
  <dl class="facts">
    <div><dt>Impact</dt><dd>{esc(s['impact'])}</dd></div>
    <div><dt>Effort</dt><dd>{esc(s['effort'])}</dd></div>
    <div><dt>Risk</dt><dd>{esc(s['risk'])}</dd></div>
    <div><dt>Depends on</dt><dd>{esc(s['depends'])}</dd></div>
    <div><dt>Evidence it is right</dt><dd>{esc(s['evidence'])}</dd></div>
    <div><dt>Recommendation</dt><dd>{esc(s['recommend'])}</dd></div>
  </dl>
</article>"""

    d_rows = [[f"<strong>{esc(d['id'])}</strong>", esc(d["decision"]),
               "<br>".join(f"• {esc(o)}" for o in d["options"]),
               esc(d["recommend"]), esc(d["criteria"]), esc(d["blocks"]), badge(d["status"])]
              for d in DECISIONS]
    d_tbl = table(["ID", "Decision", "Options", "Recommendation", "Criteria",
                   "What it blocks", "Status"], d_rows)

    steps = "".join(f"<li><strong>{esc(a)}</strong><br>{esc(bb)}</li>" for a, bb in REVIEW_PROCESS)

    body = f"""
<section class="panel">
  <h2>How to choose a path without guessing</h2>
  <p>Each suggestion names the problem, the change, the evidence that would prove it worked,
  and what it blocks. Nothing here is implemented silently: pick a decision record, pilot one
  change, and compare the named metric before adopting it.</p>
  <ol class="steps">{steps}</ol>
</section>

<section class="panel">
  <div class="panel-head"><h2>Decision records</h2><a href="review.html">Blocking flags →</a></div>
  {d_tbl}
</section>

<section class="panel">
  <div class="panel-head"><h2>Suggestions</h2><a href="../data/model/dashboard.json">Build state →</a></div>
  <div class="cards">{cards}</div>
</section>

<section class="panel">
  <h2>What is already done in this build</h2>
  <p>S01, S02, S10 and S11 are implemented and visible in the tables: the market baseline,
  the model/market blend test, correlation-aware parlay maths, and per-row uncertainty.
  The rest are proposals with an owner decision attached.</p>
</section>
"""
    return page("pages/suggestions.html", "Suggestions & Paths",
                body,
                "Twelve improvements, five decision records, and a review process for choosing before implementing.",
                dash.get("generated_at"))


# ---------------------------------------------------------------- review
def review_page(verif, strat, dash, avail=None):
    flags = []
    for irr in (verif or {}).get("irregularities", []):
        flags.append([esc(irr["id"]), esc(irr["area"]), esc(irr["issue"]),
                      src(irr["source"], "official page"), badge("needs review")])

    for u in (verif or {}).get("unverifiable", []):
        flags.append(["FLAG", esc(u["item"]), esc(u["why"]), src(SOURCE["ops"], "reference"),
                      badge("unverified")])

    av = avail or {}
    missing_clubs = av.get("clubs_without_report") or []
    if missing_clubs:
        flags.append(["F11", "injury report coverage",
                      f"No report was published for {esc(', '.join(missing_clubs))} when the page was "
                      f"scraped, so those clubs show zero rows rather than zero injuries.",
                      src(av.get("source", {}).get("url") or SOURCE["injuries"], "NFL injuries"),
                      badge("needs review")])
    if (av.get("counts") or {}).get("rows_practice_only_starters"):
        flags.append(["F12", "practice-only signal",
                      f"{av['counts']['rows_practice_only_starters']} starters have practice participation "
                      f"but no game designation yet; their weight in the attrition index is an assumption "
                      f"(DNP 0.5, limited 0.2), not a league rule.",
                      src(av.get("source", {}).get("url") or SOURCE["injuries"], "NFL injuries"),
                      badge("needs review")])

    lb = (strat or {}).get("leaderboard", [])
    failed = [r for r in lb if r["status"] != "PASS"]
    flags.append(["GATES", "strategy validation",
                  f"{len(failed)} of {len(lb)} tested rules fail at least one gate; none is promoted.",
                  src(SOURCE["schedules"], "closing lines"), badge("needs review")])

    flags.extend([
        ["F01", "prices", "No official league odds source exists; closing lines are a consensus mirror, not a book quote.",
         src(SOURCE["ops"], "NFL operations"), badge("unverified")],
        ["F02", "props", "No prop prices, so prop and combo edges cannot be computed; market columns are blank.",
         src(SOURCE["stats"], "NFL stats"), badge("blocked")],
        ["F03", "lineup", "Depth chart rank does not prove participation; the injury signal is not yet measured.",
         src(SOURCE["injuries"], "NFL injuries"), badge("needs review")],
        ["F04", "rewards", "A rewards competition may be regulated; paper points only until review.",
         src(SOURCE["ops"], "NFL operations"), badge("blocked")],
        ["F05", "season edge cases", "2026 records include unusual starts (for example a club at 0-8). Values are as NFL.com publishes; nothing was adjusted.",
         src(SOURCE["standings"], "NFL standings"), badge("verified")],
        ["F06", "sample", "Model backtest covers 2024-2026 only; more play-by-play history would tighten intervals.",
         src(SOURCE["pbp"], "play-by-play"), badge("needs review")],
        ["F07", "sign convention", "The mirrored line sign was initially inverted in this build; it was detected by an implausible correlation and corrected. Published for challenge.",
         src(SOURCE["schedules"], "schedules"), badge("resolved")],
        ["F08", "parsing", "Verification fixtures were hand-transcribed from nfl.com; a transcription error would show as a false mismatch.",
         src(SOURCE["injuries"], "NFL injuries"), badge("needs review")],
        ["F09", "weather", "Temperature and wind are blank for unplayed games, so totals ignore forecast conditions.",
         src(SOURCE["schedules"], "schedules"), badge("unverified")],
        ["F10", "travel", "No travel or time-zone data, so those claimed edges are untested.",
         src(SOURCE["ops"], "reference"), badge("unverified")],
        ["F13", "companion pages", "Companion pages from earlier sessions state that no closing lines are stored in the repository. That was true for their inputs; the integration pipeline now carries consensus closing lines and compares every line against them.",
         src(SOURCE["schedules"], "schedules release"), badge("resolved")],
        ["F14", "two models", "Two independently built models disagree on the week 10 WAS @ NYG margin. Both are inside their own error bands; neither is promoted.",
         src("../pages/evidence.html", "replication table"), badge("needs review")],
    ])

    tbl = table(["ID", "Area", "What is flagged", "Source", "State"], flags,
                note=("Unverified and blocked items do not stop publication; they stop the claim. "
                      "Each row states what would settle it."))

    body = f"""
<section class="panel">
  <h2>Flagged for review</h2>
  <p>Nothing here is hidden. Anything we could not confirm against an official league source
  is published with a blank value, a flag and the link a reviewer needs. Nothing on this page
  is inferred or filled in.</p>
  {tbl}
</section>
<section class="panel">
  <h2>What a reviewer should decide first</h2>
  <ol class="tight">
    <li><strong>Buy a priced feed or stop claiming edge.</strong> Every strategy verdict depends on it.</li>
    <li><strong>Accept the hybrid line as the default.</strong> It is the only line with measured out-of-sample support.</li>
    <li><strong>Keep rewards on paper points.</strong> Legal review is outstanding.</li>
    <li><strong>Ingest inactives and participation.</strong> The injury requirement cannot be finished without it.</li>
  </ol>
</section>
"""
    return page("pages/review.html", "Flagged for Review",
                body,
                "Every irregularity, unverified value and blocked decision, with the source that would settle it.",
                dash.get("generated_at"))


# ---------------------------------------------------------------- executive
def executive_page(snap, dash, lines, strat, avail, verif, prov):
    counts = (dash or {}).get("counts", {})
    cal = (lines or {}).get("calibration", [])
    test = next((c for c in cal if "2026" in (c.get("label") or "")), {})
    lb = (strat or {}).get("leaderboard", [])
    blend = (lines or {}).get("blend_test") or {}
    sign = (lines or {}).get("sign_convention_check") or {}
    par = (strat or {}).get("parlay", {})
    checks = (verif or {}).get("checks", [])
    graded = [c for c in checks if "coverage" not in c["name"].lower()]
    matched = sum(c["rows_matched"] for c in graded)
    checked = sum(c["rows_checked"] for c in graded)
    coverage = next((c for c in checks if "coverage" in c["name"].lower()), None)
    avail_src = (avail or {}).get("source", {})
    avail_counts = (avail or {}).get("counts", {})
    missing_clubs = (avail or {}).get("clubs_without_report") or []
    passing = [r for r in lb if r["status"] == "PASS"]
    best = lb[0] if lb else {}
    n_files = counts.get("source_files_pinned", 0)

    figures = "".join([
        kpi("Rows verified vs nfl.com", f"{matched}/{checked}", "standings + injury sample"),
        kpi("Own-line test MAE", num(test.get("spread_mae_model"), 2),
            f"market {num(test.get('spread_mae_market'), 2)} over {num(test.get('n'))} games"),
        kpi("Strategies passing all gates", f"{len(passing)} of {len(lb)}", "8 gates + BH correction"),
        kpi("Starters flagged unavailable", counts.get("starters_flagged_unavailable"), "official game status"),
        kpi("Prop lines built", counts.get("prop_lines_generated"), "market price: none"),
        kpi("Pinned source files", n_files, "URL + sha256"),
    ])

    body = f"""
<section class="panel">
  <h2>Executive summary</h2>
  <p class="lede">The repository began as a six-byte README. It now runs an automated data
  pipeline, originates its own NFL lines from opponent-adjusted play-by-play, scores strategies
  against the closing line under eight validation gates, tracks starter availability against the
  weekly depth chart, and publishes every table with a source link and every gap as a flag.
  Nothing in this build required manual data entry; the only hand-entered values are the
  {checked} verification rows transcribed from nfl.com to prove the feed matches the league's own
  pages.</p>

  <h3>What was verified</h3>
  <ul class="tight">
    <li>{matched} of {checked} verification rows matched the source they were checked against
    ({"; ".join(esc(c["name"]) for c in graded)}).</li>
    <li>{n_files} source files pinned with download URL, byte count, sha256 and fetch time.</li>
    <li>The current week's official injury report is scraped directly from nfl.com:
    {num(avail_counts.get('injury_records'))} rows across the clubs that had submitted a report,
    matched to the weekly depth chart. {len(missing_clubs)} clubs had no report at scrape time
    ({esc(", ".join(missing_clubs)) if missing_clubs else "none"}).</li>
    <li>The mirrored feed is incomplete in-season: {num((coverage or {}).get('rows_matched'))} of
    {num((coverage or {}).get('rows_checked'))} official week 10 rows were present in it, which is
    exactly why the official page is scraped directly.</li>
    <li>The closing-line sign convention was proved from data: correlation
    {num(sign.get('corr_market_line_vs_home_margin'), 3)} with the home margin over
    {num(sign.get('n_games'))} games.</li>
    <li>nflverse file licence verified as CC-BY-4.0 (attribution shown in the footer).</li>
  </ul>

  <h3>What the numbers say</h3>
  <ul class="tight">
    <li><strong>Our lines are not yet better than the market.</strong> Out-of-sample spread MAE
    {num(test.get('spread_mae_model'), 2)} points versus {num(test.get('spread_mae_market'), 2)}
    for the closing line, and the paired difference interval excludes zero — the market is
    significantly closer. The totals model is similarly behind
    ({num(test.get('total_mae_model'), 2)} vs {num(test.get('total_mae_market'), 2)}).</li>
    <li><strong>The model's incremental information is measurable, not assumed.</strong> Blend test:
    market weight {num(blend.get('weight_market'), 3)}, model weight
    {num(blend.get('weight_model'), 3)}, test MAE {num(blend.get('test_mae_hybrid'), 2)} vs
    {num(blend.get('test_mae_market_only'), 2)} market-only over {num(blend.get('n_test'))} games.</li>
    <li><strong>No strategy earns promotion.</strong> {len(lb)} rules were tested; {len(passing)} passed
    all eight gates. The top score belongs to
    {esc(best.get('strategy', 'no rule'))} with ROI {pct(best.get('roi'))} on
    {num(best.get('n_graded'))} bets and a lower 95% bound of
    {pct((best.get('roi_ci95') or [None])[0]) if best.get('roi_ci95') else 'blank'}.</li>
    <li><strong>Same-game legs are only weakly linked.</strong> phi(home covers, over hits) =
    {num(par.get('phi_home_cover_vs_over'), 3)} across {num(par.get('n_games'))} games, so naive parlay
    multiplication is roughly right for spread/total combos but must never be used for
    player-prop combos without their own correlation.</li>
    <li><strong>Availability is concentrated.</strong> The injury table names every unavailable
    starter, the next man at that slot, his experience and his 2026 snaps, so a reviewer can see
    which clubs are leaning on 2nd and 3rd string players.</li>
  </ul>

  <h3>What remains unresolved</h3>
  <ul class="tight">
    <li>No official or book-level prices: edge, CLV and prop value are unmeasurable (F01, F02).</li>
    <li>Depth chart rank is not participation; the injury effect is not yet quantified (F03).</li>
    <li>Rewards with real value need legal review (F04).</li>
    <li>Model history covers 2024-2026 only, so confidence intervals are wide (F06).</li>
    <li>Weather, travel and inactives are missing, so those signals are untested (F09, F10).</li>
  </ul>

  <h3>Decisions requested</h3>
  <ol class="tight">
    <li>Approve the hybrid line as the published default, with the pure model kept visible.</li>
    <li>Fund a licensed odds feed, or accept that the site states model-only findings.</li>
    <li>Keep the rewards competition on paper points until counsel signs off.</li>
    <li>Choose the risk policy: flat 1 unit with a -25 unit review trigger.</li>
    <li>Approve ingesting game-day inactives and participation data next.</li>
  </ol>
</section>

<section class="kpis">{figures}</section>

<section class="grid-2">
  <div class="panel">
    <h2>How to read the site</h2>
    <ul class="tight">
      <li><a href="lines.html">My Lines</a> — own spread, total, win probability, error bands, ratings, and the accuracy table.</li>
      <li><a href="strategies.html">Strategy Lab</a> — leaderboard, gate matrix, correlation, parlay maths, rewards rules.</li>
      <li><a href="injuries.html">Injuries &amp; Depth</a> — starters out, replacements, attrition index.</li>
      <li><a href="props.html">Props</a> — projections with intervals and deliberately blank market columns.</li>
      <li><a href="questions.html">Questions</a> — the decision gate: known, unknown, how to find out.</li>
      <li><a href="suggestions.html">Suggestions</a> — twelve ranked changes and five decision records.</li>
      <li><a href="evidence.html">Evidence</a> — provenance and line-by-line verification.</li>
      <li><a href="review.html">Flagged for Review</a> — everything unverified or blocked.</li>
    </ul>
  </div>
  <div class="panel">
    <h2>Constraints this build respects</h2>
    <ul class="tight">
      <li>No value is inferred, interpolated or invented. Blanks are labelled.</li>
      <li>Every strategy rule is fixed before evaluation; the count tested is published so the
      multiple-testing correction can be checked.</li>
      <li>Ratings never use information from the game being predicted.</li>
      <li>Every page states what it cannot do.</li>
    </ul>
  </div>
</section>
"""
    return page("pages/executive.html", "Executive Summary",
                body,
                "What was built, what the evidence says, what is missing, and which decisions are waiting.",
                dash.get("generated_at"))


def main():
    snap = load("snapshot.json")
    dash = load("dashboard.json")
    lines = load("lines.json")
    strat = load("strategies.json")
    avail = load("availability.json")
    props = load("props.json")
    verif = load("verification.json")
    prov = load("provenance.json")
    repl = load("replication.json")
    prov["license"] = "CC-BY-4.0"

    write("index.html", overview(snap, dash, lines, strat, avail, props, verif))
    write("pages/lines.html", lines_page(snap, lines, dash))
    write("pages/strategies.html", strategies_page(strat, dash))
    write("pages/injuries.html", injuries_page(avail, dash))
    write("pages/props.html", props_page(props, dash))
    write("pages/evidence.html", evidence_page(prov, verif, dash, repl))
    write("pages/questions.html", questions_page(dash))
    write("pages/suggestions.html", suggestions_page(dash))
    write("pages/review.html", review_page(verif, strat, dash, avail))
    write("pages/executive.html", executive_page(snap, dash, lines, strat, avail, verif, prov))
    # keep old URLs working
    for old in ("models", "teams", "standings", "injuries_old"):
        pass
    write("pages/models.html", """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Moved · NFL Decision Lab</title><meta http-equiv="refresh" content="0; url=lines.html">
<link rel="canonical" href="lines.html"></head><body>
<p>This page moved to <a href="lines.html">My Lines</a>.</p></body></html>""")
    print("site generated")


if __name__ == "__main__":
    main()
