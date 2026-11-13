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

# Flat navigation, ordered by category. Kept byte-identical to the canonical list in
# scripts/verified/normalize_nav.py so that running one after the other is a no-op
# (both generators touch index.html and pages/*.html).
NAV = [
    ("index.html", "Overview"),
    ("pages/executive.html", "Executive Summary"),
    ("pages/lines.html", "My Lines"),
    ("pages/correlations.html", "Correlations"),
    ("pages/strategies.html", "Strategy Lab"),
    ("pages/luck.html", "Skill vs Luck"),
    ("pages/parlays.html", "Parlays & Combos"),
    ("pages/props.html", "Player Props"),
    ("pages/injuries.html", "Injuries"),
    ("pages/depth.html", "Depth & Deficiency"),
    ("pages/questions.html", "Questions"),
    ("pages/suggestions.html", "Suggestions"),
    ("pages/evidence.html", "Evidence"),
    ("pages/review.html", "Flagged for Review"),
    ("pages/sections.html", "All Sections"),
    # Session ca779bcc-nfl1: the strength-of-schedule study is its own sub-site under
    # strength/; the entry keeps it reachable from the root dashboard.
    ("room/index.html", "Decision Room"),
    ("strength/index.html", "SOS Study"),
    # pages produced by the other generators in this repository, kept in the shared
    # navigation so no session's page can become unreachable
    ("pages/executive-summary.html", "Executive Summary (companion)"),
    ("pages/teams.html", "Teams"),
    ("pages/standings.html", "Standings"),
    ("pages/availability.html", "Availability"),
    ("pages/data.html", "Verified Data"),
    ("pages/analysis.html", "Validation & Correlation"),
    ("pages/decisions.html", "Decision Register"),
    ("pages/verified.html", "Verified Artifacts"),
    ("pages/models.html", "Models"),
    ("pages/flagged.html", "Flagged (companion)"),
]

# Sidebar: the same pages grouped by category, rendered on every page so the site reads
# as a dashboard rather than a list of links.
SIDEBAR = [
    ("Overview", [("index.html", "Overview"),
                  ("pages/executive.html", "Executive Summary"),
                  ("pages/sections.html", "All Sections")]),
    ("Lines & model", [("pages/lines.html", "My Lines"),
                           ("pages/correlations.html", "Correlations")]),
    ("Competition", [("pages/strategies.html", "Strategy Lab"),
                     ("pages/luck.html", "Skill vs Luck"),
                     ("pages/parlays.html", "Parlays & Combos"),
                     ("pages/props.html", "Player Props")]),
    ("Availability", [("pages/injuries.html", "Injuries"),
                      ("pages/depth.html", "Depth & Deficiency")]),
    ("Decisions", [("pages/questions.html", "Questions"),
                   ("pages/suggestions.html", "Suggestions")]),
    ("Evidence", [("pages/evidence.html", "Evidence"),
                  ("pages/review.html", "Flagged for Review")]),
    # Pages produced by the other generators in this repository. They are kept one click
    # away rather than in the header so the header stays readable; every one of them is
    # also listed on the All Sections page.
    ("Companion pages", [("room/index.html", "Decision Room"),
                         ("strength/index.html", "SOS Study"),
                         ("pages/teams.html", "Teams"),
                         ("pages/standings.html", "Standings"),
                         ("pages/availability.html", "Availability"),
                         ("pages/data.html", "Verified data"),
                         ("pages/analysis.html", "Validation & correlation"),
                         ("pages/decisions.html", "Decision register"),
                         ("pages/verified.html", "Verified artifacts"),
                         ("pages/models.html", "Models"),
                         ("pages/executive-summary.html", "Executive summary (companion)"),
                         ("pages/flagged.html", "Flagged (companion)")]),
]

SOURCE = {
    "standings": "https://www.nfl.com/standings/league/2026/reg",
    "divisions": "https://www.nfl.com/standings/division/2026/REG",
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


def signal_cell(status) -> str:
    # Labels describe the size of the model-market gap only. None is a validated signal:
    # no strategy has passed the eight gates, so no label may read as a recommendation.
    mapping = {"gap-large-unvalidated": ("warn", "large gap · unvalidated"),
               "gap-unvalidated": ("neutral", "gap · unvalidated"),
               "small-difference": ("neutral", "small difference"),
               # legacy names written by earlier builds of lines.json
               "actionable": ("warn", "large gap · unvalidated"),
               "watch": ("neutral", "gap · unvalidated"),
               "no-edge": ("neutral", "small difference")}
    cls, text = mapping.get(status or "", ("neutral", status or "unknown"))
    return f'<span class="badge {cls}">{esc(text)}</span>'


def team_line(team, home_margin) -> str:
    """Render a home-margin line as the favourite's spread, e.g. NYG -2.5 (home favoured)."""
    if home_margin is None:
        return '<span class="missing">blank</span>'
    return f"{esc(team)} {-float(home_margin):+.1f}"


def kpi(label, value, sub="") -> str:
    shown = esc(value) if value is not None else "&mdash;"
    return (f'<article class="kpi"><span class="kpi-label">{esc(label)}</span>'
            f'<strong class="kpi-value">{shown}</strong>'
            f'<span class="kpi-sub">{esc(sub)}</span></article>')


def _target(href: str, is_index: bool) -> str:
    """Resolve a nav href the same way scripts/verified/normalize_nav.py does.

    Both generators rewrite the <nav> block on index.html and pages/*.html, so their
    output has to be byte-identical or the later one silently rewrites the earlier one's
    links. index.html links to pages/x.html; a page inside pages/ links to a bare
    filename and to ../index.html.
    """
    if href == "index.html":
        return "index.html" if is_index else "../index.html"
    if "/" in href:
        # a sub-site path such as room/index.html: already relative to the repo root
        return href if is_index else "../" + href
    return ("pages/" + href) if is_index else href


def _is_active(href: str, current: str) -> bool:
    """True when this nav entry is the page being rendered.

    A sub-site entry (room/index.html, strength/index.html) shares its basename with the
    root index.html, so the basename alone is not enough — the whole href has to match
    when it carries a directory. Rule contributed by session ca779bcc-nfl1.
    """
    return href == current if "/" in href else href.split("/")[-1] == current


def _nav_block(current: str, is_index: bool) -> str:
    items = []
    for href, label in NAV:
        target = _target(href, is_index)
        cls = ' class="active"' if _is_active(href, current) else ""
        items.append(f'    <a href="{esc(target)}"{cls}>{esc(label)}</a>')
    return "<nav>\n" + "\n".join(items) + "\n  </nav>"


def _sidebar_block(current: str, is_index: bool) -> str:
    groups = []
    for group, items in SIDEBAR:
        links = []
        for href, label in items:
            target = _target(href, is_index)
            cls = ' class="active"' if _is_active(href, current) else ""
            links.append(f'<a href="{esc(target)}"{cls}>{esc(label)}</a>')
        groups.append(f'<div class="navgroup"><span>{group}</span>{"".join(links)}</div>')
    return f'<aside class="sidebar" aria-label="Categories">{"".join(groups)}</aside>'


def page(path: str, title: str, body: str, subtitle: str = "", generated: str = "") -> str:
    prefix = "../" if path.startswith("pages/") else ""
    is_index = not path.startswith("pages/")
    current = path.split("/")[-1]
    nav = _nav_block(current, is_index)
    sidebar = _sidebar_block(current, is_index)
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
  {nav}
</header>
<div class="shell">
{sidebar}
<main id="main">
  <section class="page-head">
    <p class="eyebrow">Evidence-first dashboard</p>
    <h1>{esc(title)}</h1>
    {sub}
    {stamp}
  </section>
  {body}
</main>
</div>
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
    ladder = load_rel("data/depth_ladder.json")
    lb9 = load_rel("data/s9cb/leaderboard.json")
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
            team_line(g["home"], g.get("market_home_line")),
            num(g.get("market_total")),
            num(g.get("edge_home_line"), 2),
            num(g.get("edge_total"), 2),
            signal_cell(g.get("status")),
            src(g.get("source_games") or SOURCE["schedule"], "NFL schedule"),
        ])
    lines_tbl = table(
        ["Matchup", "My line", "My total", "Market line", "Market total",
         "Edge (line)", "Edge (total)", "Signal", "Source"],
        rows, note=("Lines are the favourite's spread (NYG -2.6 = NYG favoured by 2.6). Edges are model "
                    "minus market. Labels give the size of the gap only: "
                    f"{counts.get('strategies_passing_all_gates', 0)} of "
                    f"{counts.get('strategies_tested', 0)} strategies pass all gates, so no line here "
                    "is a validated signal. Every line is a pre-game prediction: this build predates "
                    "the Week 10 Thursday kick-off, so WAS @ NYG is still listed even though it has "
                    "since finished 24-21 to the Commanders (flag F41). See the Lines page for error "
                    "bands and the accuracy table."))

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
    av_tbl = table(["Team", "Club", "Starters out", "Starters doubtful", "Starters questionable",
                    "Starters practice-only", "Attrition index", "Backup yrs exp", "Source"], av_rows,
                   note=("Starter counts use only players matched to the depth chart at rank 1. Backups and "
                         "unmatched players are not counted (F21). Attrition index is a documented model weight, "
                         "not an NFL statistic. Mid-week, most clubs have published practice participation only."))

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

    lc = ladder.get("counts", {})
    depth_rows = []
    for cl in sorted(ladder.get("clubs", []),
                     key=lambda x: (-x["slots_missing_starter"], -x["slots_starter_at_risk"],
                                    x["abbr"]))[:6]:
        if cl["chart_status"] != "ok":
            depth_rows.append([f'<strong>{esc(cl["abbr"])}</strong>', esc(cl["club"]),
                               '<span class="missing">blank</span>',
                               '<span class="missing">blank</span>',
                               badge("no chart published"),
                               src("https://www.nfl.com/teams/", "nfl.com")])
            continue
        depth_rows.append([f'<strong>{esc(cl["abbr"])}</strong>', esc(cl["club"]),
                           num(cl["slots_missing_starter"]),
                           num(cl["slots_starter_at_risk"]),
                           esc(cl["deepest_string_starting"] or "1st string"),
                           src(cl["chart_url"], "club chart")])
    depth_panel = f"""
<section class="panel">
  <div class="panel-head">
    <h2>Depth: which line a backup is starting on</h2>
    <a href="pages/depth.html">Full 1st-to-4th string ladder &rarr;</a></div>
  {table(["Club", "Name", "Slots on a backup", "Starters at risk", "Deepest string starting",
          "Source"], depth_rows)}
  <p class="note">{lc.get('slots', 0)} position slots across {lc.get('clubs_with_chart', 0)} of 32
  clubs (Houston publishes no chart). {lc.get('slots_started_by_a_backup', 0)} lines are being
  started by a backup because the club's own first string is Out or Doubtful on the official
  nfl.com report; {lc.get('slots_starter_at_risk', 0)} more have a first string who is
  Questionable, did not practise, or was limited. Clubs with no filed report this week show zero,
  which is not the same as healthy.</p>
</section>"""

    t9 = (lb9 or {}).get("totals", {})
    research_panel = f"""
<section class="panel">
  <div class="panel-head">
    <h2>The large-sample study behind every verdict</h2>
    <a href="pages/luck.html">How luck is removed &rarr;</a></div>
  <div class="grid-3">
    <div class="stat"><h4>{num(t9.get('bets_scored'))} bets scored</h4>
      <p>Across {num(t9.get('games_in_sample'))} games from
      {esc(str(min(t9.get('seasons', [0]))))} to {esc(str(max(t9.get('seasons', [0]))))}, at
      prices taken from the source for every scored bet. No -110 assumption anywhere.</p></div>
    <div class="stat"><h4>{(lb9 or {}).get('n_strategies', 0)} strategies, 0 proven</h4>
      <p>Every rule is fixed before evaluation and must clear all eight gates. The closest is
      S07 (fade the road favourite of 7+): 6.06% ROI over 401 bets, 6 of 8 gates, and a 95% luck
      band of -37.2 to +37.2 units.</p></div>
    <div class="stat"><h4>Our line adds something, but is worse</h4>
      <p>Our spread error is 10.70 points against the market's 10.24, yet the disagreement
      between them still carries information (weight 0.161, t = 3.35). Both facts are published;
      neither is enough to call a signal.</p></div>
  </div>
</section>"""

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
    {counts.get('starters_flagged_unavailable', 0)} starters flagged ·
    {lc.get('slots', 0)} depth slots · 0 invented values.</p>
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
  <p class="note">Re-checked on 2026-11-13 against the live nfl.com pages: the Week 10 injury
  snapshot still matches (296 rows, 26 clubs), the 14 fixtures and four byes still match, and
  30 of 32 standings rows still match. Two standings rows do not: the committed snapshot
  predates the Week 10 Thursday game, so NYG and WAS are stale. That is flag
  <a href="pages/review.html">F41</a>, not a silent edit.</p>
</section>

{depth_panel}
{research_panel}
<section class="panel">
  <div class="panel-head"><h2>What we know, what we don't</h2><a href="pages/questions.html">{len(QUESTIONS)} questions that gate decisions →</a></div>
  <div class="grid-3">
    <div class="stat"><h4>Answered</h4><p>{sum(1 for q in QUESTIONS if q['status'].lower().startswith(('answered', 'partially')))} of {len(QUESTIONS)} questions have a verified answer or partial answer.</p></div>
    <div class="stat"><h4>Blocked</h4><p>{sum(1 for q in QUESTIONS if 'blocked' in q['status'].lower())} questions cannot be answered with today's sources, mostly pricing and legality.</p></div>
    <div class="stat"><h4>Next</h4><p>{len(SUGGESTIONS)} suggestions are ranked at <a href="pages/suggestions.html">Suggestions</a>; {sum(1 for d in DECISIONS if 'implemented' not in d['status'].lower())} decision records need a human choice.</p></div>
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
            team_line(g["home"], g.get("market_home_line")),
            num(g.get("market_total")),
            num(g.get("edge_home_line"), 2),
            num(g.get("edge_total"), 2),
            signal_cell(g.get("status")),
            src(g.get("source_games") or SOURCE["schedule"], "NFL schedule"),
        ])
    fx_tbl = table(["Matchup", "My line", "95% band (home margin)", "My total", "P(home win)",
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
        # A missing side of a comparison is a fact about the comparison, not a blank to sweep
        # away: render it as an explicit label so the cell is never empty.
        BLANK = '<span class="missing">no comparable value in this build</span>'
        conf = [[f"<strong>{esc(c['item'])}</strong>",
                 esc(c["this_pipeline"]) if c.get("this_pipeline") not in (None, "") else BLANK,
                 esc(c["companion"]) if c.get("companion") not in (None, "") else BLANK,
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
                f"{len(QUESTIONS)} questions, what we know, what we are missing, and how to find it.",
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
                f"{len(SUGGESTIONS)} improvements, {len(DECISIONS)} decision records, and a review process for choosing before implementing.",
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
        ["F14", "two models", "Two independently built models disagree on the week 10 WAS @ NYG margin (replication table on the Evidence page). Both are inside their own error bands; neither is promoted.",
         src(SOURCE["schedule"], "NFL schedule"), badge("needs review")],
        ["F15", "signal labels", "Week 10 signal labels earlier read 'actionable' for any gap of 3+ points, with no validation gate. Labels now state the size of the gap and that it is unvalidated; no strategy has passed all gates.",
         src(SOURCE["schedules"], "closing lines"), badge("resolved")],
        ["F16", "publication lag", "Pages rendered at 05:07 UTC showed Out counts that the 18:53 UTC data and the official page no longer matched (NE: 2 shown, 3 on nfl.com). The renderer now runs in the data workflow, and check_committed_site.py fails the build if a page's build time is older than the data.",
         src(SOURCE["injuries"], "NFL injuries"), badge("resolved")],
        ["F17", "depth chart", "2nd-, 3rd- and 4th-string tracking uses the nflverse depth-chart mirror (community data). The official nfl.com depth-chart page returns 404 (checked 2026-11-12), so backup status is not official.",
         src("https://www.nfl.com/teams/kansas-city-chiefs/depth-chart", "nfl.com 404 check"), badge("needs review")],
        ["F18", "official reconciliation", "Checked against nfl.com on 2026-11-12: all 6 game designations match (WAS 2 Out, NYG 1 Questionable, NE 3 Out), and every practice row for WAS, NYG, NE, DET, KC and ATL matches. Other clubs' practice rows are not hand-reconciled; see data/verified/live_check_2026-11-12.tsv.",
         src(SOURCE["injuries"], "NFL injuries"), badge("needs review")],
        ["F19", "companion pages", "Pages from earlier generators (executive-summary, data, verified, analysis, decisions, teams, standings, availability) are not re-rendered by the data workflow. They are kept for review and may lag the data.",
         src(SOURCE["repo"], "repository"), badge("needs review")],
        ["F21", "starter-only availability", "The availability model counts only players matched to the depth chart at rank 1. Official Out or Questionable players who are backups, or who fail to match, are dropped without a row. In the 22:30 UTC build, 5 of the 6 official game designations are absent from the starter list (Brown, Henderson, Patrick, Yankoff, Harrison). Only Carlton Davis III is counted. This does not meet the 2nd/3rd/4th-string requirement.",
         src(SOURCE["injuries"], "NFL injuries"), badge("needs review")],
        ["F22", "scrape completeness", "The 18:53 UTC scrape returned 276 official rows; the nfl.com page lists 279. The 22:30 UTC scrape returned 279, including JAX BJ Green II, IND CJ Allen and IND Grover Stewart, which the earlier scrape missed. Cause not diagnosed; any row-count drop between scrapes should block publication.",
         src(SOURCE["injuries"], "NFL injuries"), badge("needs review")],
        ["F20", "CI checks", "Some CI workflows regenerate pages and then check the regenerated copies, so the committed bytes are not what is checked. tools/check_committed_site.py checks the committed files.",
         src(SOURCE["repo"] + "/blob/main/.github/workflows/pages.yml", "pages workflow"), badge("needs review")],
        ["F23", "site navigation", "The landing page linked only to pages/*: the root section pages and the referee/ and verified-lab/ sub-sites had no inbound link. Fixed by adding a categorized All Sections index (pages/sections.html) to the navigation.",
         src(SOURCE["repo"], "repository"), badge("resolved")],
        ["F24", "correlation C5", "The division-game flag compared only the division word, counting 10 AFC West vs NFC West games as division games (52 instead of 42; r=-0.1297 instead of -0.1048). Fixed: the flag now keys on conference + division, verified against the official division standings; audit_numbers.py gates it.",
         src(SOURCE["divisions"], "NFL division standings"), badge("resolved")],
        ["F25", "CI coverage", "Data-bot commits carry [skip ci], so the verification workflows never run on them: refreshed data reaches main ungated until the next human push. Their F20 covers regenerate-then-check; this row is the [skip ci] angle: bot pushes run no verify at all. Needs a reviewer decision (suggestions S13 and root S24).",
         src(SOURCE["repo"], "repository"), badge("needs review")],
    ])

    # --- session c56ebee8-nfl1, fresh official re-verification on 2026-11-13 -------
    flags.append([
        "F41",
        "standings freshness",
        "Independent confirmation, 2026-11-13. Session 9411723a raised F41 for the standings "
        "snapshot lagging the live table. This session reached the same conclusion by a separate "
        "comparison: 30 of 32 rows match nfl.com exactly, and the two that do not are the Giants "
        "and the Commanders, because the committed snapshot predates the Week 10 Thursday game "
        "(Commanders 24, Giants 21, final). Official now reads NYG 5-3-1 / 203 PF / 196 PA and "
        "WAS 3-5-1 / 196 PF / 223 PA; the repository publishes 5-2-1 / 182 / 172 and "
        "2-5-1 / 172 / 202. A third session (1e159b2e, check N5) transcribed all 32 clubs "
        "independently and also reports 30 of 32. Three independent checks agree. The same lag "
        "means WAS @ NYG still appears in the Week 10 own-lines table even though it has since "
        "kicked off; those lines are a legitimate pre-game prediction and the page now says so.",
        src(SOURCE["standings"], "NFL standings"), badge("confirmed x3")])
    flags.extend([
        ["F42", "depth chart source",
         "nfl.com publishes no depth chart at all: "
         "https://www.nfl.com/teams/kansas-city-chiefs/depth-chart returns HTTP 404 (re-checked "
         "2026-11-13, the same result recorded on 2026-11-12). The 1st-to-4th string ladder on "
         "the Depth & Deficiency page therefore comes from the 31 clubs' own sites. Houston "
         "publishes no chart, so its rows are blank by design rather than zero.",
         src("https://www.nfl.com/teams/kansas-city-chiefs/depth-chart", "nfl.com 404"),
         badge("needs review")],
        ["F43", "depth chart parsing",
         "16 cells in the club depth charts hold what look like two players run together by the "
         "scraper (for example 'Zaven Collins Baron Browning' at Arizona's OLB 1). They are "
         "published verbatim and flagged on the Depth & Deficiency page. Splitting them would "
         "invent a player, so it is not done; a reviewer can settle each one on the club page.",
         src("https://www.azcardinals.com/team/depth-chart", "club chart"),
         badge("needs review")],
        ["F44", "depth chart gap",
         "One line (PHI defence, DT) lists a second string and no first string. That is a gap in "
         "the club's chart, not an injury, so it is excluded from every deficiency count and "
         "published on its own.",
         src("https://www.philadelphiaeagles.com/team/depth-chart", "club chart"),
         badge("needs review")],
        ["F45", "injury snapshot re-verified",
         "The committed official injury snapshot (296 rows across 26 clubs, scraped "
         "2026-11-12T23:37Z) was re-checked row count by row count against nfl.com on 2026-11-13: "
         "296 rows, 26 clubs, and 24 of 26 club counts identical. The two that differ are the "
         "known club-code aliases (nfl.com AZ/LA vs this repository's ARI/LAR), not missing rows. "
         "Fourteen named rows were compared field by field and all match.",
         src(SOURCE["injuries"], "NFL injuries"), badge("verified")],
        ["F46", "site generations",
         "Seven independently built site generations now coexist in this repository (root "
         "dashboard, root section pages, docs/, dashboard/, lab/, research/, referee/, "
         "verified-lab/). They disagree in places because they were built from different inputs. "
         "Which one is authoritative is open question Q21; picking one and archiving the rest is "
         "the single highest-value review decision left.",
         src(SOURCE["repo"], "repository"), badge("needs review")],
        ["F47", "2nd/3rd/4th string",
         "F21 recorded that the availability model tracks rank 1 only, so it cannot meet the "
         "brief's 2nd/3rd/4th-string requirement. The Depth & Deficiency page now publishes the "
         "full ladder for 31 clubs (933 slots, ranks 1 to 6 as the club lists them) and identifies "
         "which line a backup is starting on. F21 stays open for the attrition index itself, which "
         "is still starter-only.",
         src("https://www.nfl.com/teams/", "club charts"), badge("partially resolved")],
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

    coverage_rows = [
        ["Own NFL lines for the current week", "<a href=\"lines.html\">My Lines</a>", badge("implemented"),
         src(SOURCE["schedule"], "NFL schedule"), "F15"],
        ["Strategy leaderboard: single bets", "<a href=\"strategies.html\">Strategy Lab</a>", badge("implemented"),
         src(SOURCE["schedules"], "closing lines"), "GATES"],
        ["Parlays and player-prop combos", "<a href=\"parlays.html\">Parlays &amp; Combos</a>", badge("implemented"),
         src(SOURCE["schedules"], "closing lines"), "F02"],
        ["Correlation values", "<a href=\"correlations.html\">Correlations</a>", badge("implemented"),
         src(SOURCE["schedules"], "closing lines"), "—"],
        ["Validation gates and luck removal", "<a href=\"luck.html\">Skill vs Luck</a>", badge("implemented"),
         src(SOURCE["schedules"], "closing lines"), "GATES"],
        ["Injury tracking from the official report", "<a href=\"injuries.html\">Injuries &amp; Depth</a>", badge("implemented"),
         src(SOURCE["injuries"], "NFL injuries"), "F18"],
        ["2nd-, 3rd- and 4th-string backups, offence and defence", "<a href=\"depth.html\">Depth &amp; Deficiency</a>", badge("implemented"),
         src("https://www.nfl.com/teams/", "official club charts"), "F42, F43"],
        ["2nd- to 4th-string effect on the attrition index", "<a href=\"injuries.html\">Injuries &amp; Depth</a>", badge("partial"),
         src(SOURCE["injuries"], "NFL injuries"), "F17, F21"],
        ["Suggestions to choose a path before any change", "<a href=\"suggestions.html\">Suggestions</a>", badge("implemented"),
         src(SOURCE["ops"], "NFL operations"), "—"],
        ["Clear questions: known, unknown, answers", "<a href=\"questions.html\">Questions</a>", badge("implemented"),
         src(SOURCE["ops"], "NFL operations"), "—"],
        ["Executive summary", "<a href=\"executive.html\">Executive Summary</a>", badge("implemented"),
         src(SOURCE["repo"], "repository"), "—"],
        ["Live site with category pages and source links on every table row", "<a href=\"../index.html\">Overview</a>", badge("partial"),
         src(SOURCE["repo"], "repository"), "F16, F19"],
        ["Rewards competition with real value", "<a href=\"review.html\">Flagged for Review</a>", badge("blocked"),
         src(SOURCE["ops"], "NFL operations"), "F04"],
        ["Line-by-line check against official sources", "<a href=\"evidence.html\">Evidence</a>", badge("partial"),
         src(SOURCE["standings"], "NFL standings"), "F08, F18"],
        ["Repository review and flagged irregularities", "<a href=\"review.html\">Flagged for Review</a>", badge("implemented"),
         src(SOURCE["repo"], "repository"), "F19, F20"],
    ]
    coverage_tbl = table(["Requirement", "Where it lives", "Status", "Source", "Flag"], coverage_rows)

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
  <p class="lede"><strong>Re-checked on 2026-11-13.</strong> Every committed snapshot was compared
  again with the live official pages. The Week 10 injury report still matches exactly
  (296 rows, 26 clubs); the 14 Week 10 fixtures and the four byes still match; and 30 of 32
  standings rows still match. Two standings rows do not: the snapshot predates the Week 10
  Thursday game, so the Giants' and the Commanders' rows are one game behind. That is published as
  flag <a href="review.html">F41</a> rather than edited silently, because a dated evidence record
  should be re-scraped, not quietly corrected.</p>

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
    <li><strong>Availability is only partly measured.</strong> The injury table names the unavailable
    starters that the depth chart could match, with the next man at that slot, his experience and his
    2026 snaps. It does not yet show backups who are out, so 2nd- and 3rd-string exposure is
    understated (F17, F21).</li>
  </ul>

  <h3>What remains unresolved</h3>
  <ul class="tight">
    <li>No official or book-level prices: edge, CLV and prop value are unmeasurable (F01, F02).</li>
    <li>Depth chart rank is not participation; the injury effect is not yet quantified (F03).</li>
    <li>Availability counts starters only and drops unmatched records: 5 of 6 official game designations are missing from the starter list (F21).</li>
    <li>Rewards with real value need legal review (F04).</li>
    <li>Model history covers 2024-2026 only, so confidence intervals are wide (F06).</li>
    <li>Weather, travel and inactives are missing, so those signals are untested (F09, F10).</li>
    <li>Two of 32 standings rows are one game behind the live official table (F41).</li>
    <li>Seven site generations coexist and disagree in places. Choosing one as authoritative is
    the highest-value review decision outstanding (F46, question Q21).</li>
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

<section class="panel">
  <h2>Brief coverage: what is implemented, partial or blocked</h2>
  <p>Each requirement from the brief, where it lives, and how far the evidence goes. Nothing is marked
  implemented unless it is on a page with its source.</p>
  {coverage_tbl}
</section>

<section class="grid-2">
  <div class="panel">
    <h2>How to read the site</h2>
    <ul class="tight">
      <li><a href="lines.html">My Lines</a> — own spread, total, win probability, error bands, ratings, and the accuracy table.</li>
      <li><a href="correlations.html">Correlations</a> — eleven measured relationships with intervals, on 6,975 games.</li>
      <li><a href="strategies.html">Strategy Lab</a> — leaderboard, gate matrix, parlay maths, rewards rules.</li>
      <li><a href="luck.html">Skill vs Luck</a> — the fair-price null, the luck band, power, and the eight gates.</li>
      <li><a href="parlays.html">Parlays &amp; Combos</a> — dependence between legs, across games and inside one.</li>
      <li><a href="props.html">Props</a> — projections with intervals and deliberately blank market columns.</li>
      <li><a href="injuries.html">Injuries &amp; Depth</a> — starters out, replacements, attrition index.</li>
      <li><a href="depth.html">Depth &amp; Deficiency</a> — 1st to 4th string, offence and defence, for 31 clubs.</li>
      <li><a href="questions.html">Questions</a> — the decision gate: known, unknown, how to find out.</li>
      <li><a href="suggestions.html">Suggestions</a> — {len(SUGGESTIONS)} ranked changes and {len(DECISIONS)} decision records.</li>
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


def sections_page(dash):
    """Categorized index of every published section (flag F37 / suggestion S21).

    A crawl of index.html and pages/*.html on 2026-11-12 found no inbound link to
    the fifteen root section pages or to the referee/ and verified-lab/ sub-sites,
    so a reader could only reach them by typing URLs. This page fixes that without
    disturbing the flat header navigation the other generators share.
    """
    def link(href, label):
        # this page lives in pages/, so root targets need ../ and sister pages do not
        if href.startswith("pages/"):
            target = href[len("pages/"):]
        else:
            target = "../" + href
        return f'<a href="{esc(target)}">{esc(label)}</a>'

    rows = [
        ["Dashboard", link("index.html", "Overview"),
         "Season state, this week's own lines, leaderboard top, availability pressure, verification summary"],
        ["Dashboard", link("pages/sections.html", "All Sections"),
         "This page: every published section, grouped by category"],
        ["Lines & model", link("pages/lines.html", "My Lines"),
         "Own spread, total and win probability with error bands, ratings, out-of-sample accuracy"],
        ["Lines & model", link("pages/analysis.html", "Validation & Correlation"),
         "Forward test, luck removal, measured correlation values (including C5)"],
        ["Lines & model", link("pages/verified.html", "Verified Artifacts"),
         "Every artifact generated from verified inputs, with its guarding check"],
        ["Lines & model", link("pages/correlations.html", "Correlations"),
         "Eleven game-level relationships with n, r, confidence interval and p on 6,975 games"],
        ["Competition", link("pages/strategies.html", "Strategy Lab"),
         "Leaderboard, gate matrix, parlay maths, reward rules"],
        ["Competition", link("leaderboard.html", "Leaderboard competition"),
         "Competition rules, reward tiers, ranked board (root register)"],
        ["Competition", link("strategy-lab.html", "Strategy lab (research register)"),
         "Own-line pipeline, signal research, candidate strategies, validation gates"],
        ["Competition", link("bet-types.html", "Bet types & risk"),
         "Single bets, parlays, player prop combos, official loss data"],
        ["Competition", link("pages/luck.html", "Skill vs Luck"),
         "Every strategy against a fair-price null: luck band, z, power, and the eight gates"],
        ["Competition", link("pages/parlays.html", "Parlays & Combos"),
         "66 two-leg parlays tested for dependence, plus same-game prop correlations"],
        ["Competition", link("pages/props.html", "Player Props"),
         "Shrunk usage projections with intervals; market columns deliberately blank"],
        ["Official data", link("pages/injuries.html", "Injuries & Depth"),
         "Official game status joined to depth-chart rank, next man up, attrition index"],
        ["Official data", link("pages/availability.html", "Availability & Deficiencies"),
         "Starter availability, backup exposure, clubs without a published report"],
        ["Official data", link("injuries.html", "Injuries (register)"),
         "Official injury report rows, filing policy, inactives, tracking design"],
        ["Official data", link("pages/depth.html", "Depth & Deficiency"),
         "1st to 4th string for every club, offence and defence separately, joined to the official report"],
        ["Official data", link("depth-chart.html", "Depth charts & backup exposure"),
         "1st to 4th string for offense and defense where official charts publish them"],
        ["Official data", link("pages/standings.html", "Standings"),
         "Official 2026 standings, all 32 clubs"],
        ["Official data", link("pages/teams.html", "Teams"),
         "Club directory with official links"],
        ["Official data", link("pages/data.html", "Verified Data"),
         "Official-source dataset, refreshed and re-checked automatically"],
        ["Official data", link("data-tables.html", "Standings, data & findings"),
         "Derived metrics, correlation register, official bet facts, findings"],
        ["Governance", link("requirements.html", "Requirements inventory"),
         "Every requirement from the brief, decomposed with per-row official links"],
        ["Governance", link("pages/executive.html", "Executive Summary"),
         "What was built, what the evidence says, what is unresolved, decisions requested"],
        ["Governance", link("pages/executive-summary.html", "Executive Summary (companion)"),
         "Companion summary produced by the earlier dashboard generation"],
        ["Governance", link("executive-summary.html", "Executive summary (root register)"),
         "Root section page: verified facts, gaps, posture"],
        ["Governance", link("pages/questions.html", "Questions & Information Gaps"),
         "Decision-gating questions: known, unknown, discovery, what each one blocks"],
        ["Governance", link("questions.html", "Decision questions (root register)"),
         "Root register of questions, answers and discovery actions"],
        ["Governance", link("pages/suggestions.html", "Suggestions & Paths"),
         "Improvement suggestions, decision records, review process"],
        ["Governance", link("suggestions.html", "Suggestions & choose a path"),
         "Root register with the Review and Choose a Path gate"],
        ["Governance", link("pages/decisions.html", "Decision Register"),
         "Questions, missing information, and options to choose between"],
        ["Assurance", link("pages/review.html", "Flagged for Review"),
         "Every irregularity, unverified value and blocked decision, with the settling source"],
        ["Assurance", link("pages/flagged.html", "Flagged (register)"),
         "Flag register from the companion dashboard generation"],
        ["Assurance", link("flagged.html", "Flagged for Review (root register)"),
         "Full root flag register (F01 to F40) with official source links"],
        ["Assurance", link("verification.html", "Verification & sources"),
         "Verification policy, official source registry, line-by-line audit"],
        ["Assurance", link("pages/evidence.html", "Evidence & Verification"),
         "Provenance (URL and sha256 per file) and checks against nfl.com"],
        ["Assurance", link("integration.html", "Combined integration verification"),
         "Line-by-line re-verification of every merged session's data"],
        ["Assurance", link("deployment.html", "Deployment & pull request"),
         "Pages configuration, pull request, merge and deploy record"],
        ["Independent sub-sites", link("referee/index.html", "Referee"),
         "Independent official-source audit and replication of published numbers"],
        ["Independent sub-sites", link("verified-lab/index.html", "Verified Lab"),
         "Hand transcription of nfl.com with a 34-check harness and 103 tests"],
        ["Independent sub-sites", link("dashboard/index.html", "Dashboard (session 6a232e79)"),
         "Live re-verified dashboard: depth charts, injuries, lines, questions, flagged, sources"],
        ["Independent sub-sites", link("lab/index.html", "Decision lab (session 1505ac8e)"),
         "Consolidated decision lab: live-verified data, own lines, ten-gate strategy lab, depth charts"],
        ["Companion register", link("docs/index.html", "Register (session 87deb7ab)"),
         "Independently built requirements, questions, suggestions and strategy registers"],
        ["Independent sub-sites", link("strength/index.html", "Strength of schedule study (session ca779bcc)"),
         "Walk-forward ratings, SOS, own lines, gated leaderboard, questions, suggestions, flagged items (14 pages)"],
        ["Historical", link("legacy-site.html", "Earlier dashboard"),
         "The first integrated dashboard, preserved verbatim"],
    ]
    body = f"""
<section class="panel">
  <h2>All published sections</h2>
  <p>Every page and sub-site this repository publishes, grouped by category, so any
  finding can be reached in one click from the landing navigation. Six generations
  are published side by side (root dashboard, root section pages, docs/, dashboard/,
  lab/, plus the referee and verified-lab sub-sites); nothing is hidden or merged
  silently. Which one is authoritative is open question Q21 on the Questions page.</p>
  {table(["Category", "Section", "What it contains"], rows,
         note=f"{len(rows)} sections. Every link resolves locally; flags F37 to F39 record why "
              f"this page was added and what still needs a reviewer decision.")}
</section>
"""
    return page("pages/sections.html", "All Sections", body,
                "Every published page and sub-site, grouped by category.",
                dash.get("generated_at"))


def load_rel(rel: str, default=None):
    """Load a JSON file by repo-relative path (used for data outside data/model)."""
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return {} if default is None else default
    with open(p) as f:
        return json.load(f)


# ------------------------------------------------------- depth and deficiency
UNIT_LABEL = {"offense": "Offense", "defense": "Defense", "special_teams": "Special teams"}


def depth_page(ladder, snap):
    c = ladder.get("counts", {})
    clubs = ladder.get("clubs", [])
    deficient = ladder.get("deficient_slots", [])
    gaps = ladder.get("chart_gaps", [])
    merged = ladder.get("merged_name_flags", [])

    rows = []
    for cl in sorted(clubs, key=lambda x: (-x["slots_missing_starter"],
                                           -x["slots_starter_at_risk"], x["abbr"])):
        if cl["chart_status"] != "ok":
            rows.append([f'<strong>{esc(cl["abbr"])}</strong>', esc(cl["club"]),
                         '<span class="missing">blank</span>',
                         '<span class="missing">blank</span>',
                         '<span class="missing">blank</span>',
                         '<span class="missing">blank</span>',
                         '<span class="missing">blank</span>',
                         badge("no chart published"),
                         src("https://www.nfl.com/teams/", "nfl.com")])
            continue
        report = ("published" if cl["report_published"]
                  else badge("no report this week"))
        rows.append([
            f'<strong>{esc(cl["abbr"])}</strong>',
            esc(cl["club"]),
            num(cl["slots"]),
            num(cl["offense_missing_starter"]),
            num(cl["defense_missing_starter"]),
            num(cl["slots_starter_at_risk"]),
            esc(cl["deepest_string_starting"] or "1st string"),
            report,
            src(cl["chart_url"], "club chart"),
        ])

    def slot_rows(unit):
        out = []
        for s in deficient:
            if s["unit"] != unit:
                continue
            out.append([
                f'<strong>{esc(s["abbr"])}</strong>',
                esc(s["position"]),
                esc(s["string_label"]),
                esc(s["starter_name"] or "blank"),
                esc(s["starter_status"]),
                esc(s["out_above"] or "&mdash;"),
                src(s["chart_url"], "chart"),
            ])
        return out

    club_note = ("Slots on a backup counts only lines where the club's own chart lists a first "
                 "string who is Out or Doubtful on the official nfl.com report. Starters at risk "
                 "counts lines whose first string is Questionable, did not practise, or was limited. "
                 "Clubs on a bye or with no filed report (BAL, LAC, CHI, DEN, PHI, TB this week) "
                 "show zero: the absence of a report is not evidence of health.")
    merged_rows = [[f'<strong>{esc(m["abbr"])}</strong>',
                    UNIT_LABEL.get(m["unit"], esc(m["unit"])),
                    esc(m["position"]), num(m["rank"]), esc(m["raw"]),
                    src(m["chart_url"], "chart")] for m in merged]
    merged_note = (f"{len(merged)} cells hold what look like two players run together by the "
                   f"scraper (for example two co-starters on one line). They are published "
                   f"verbatim and flagged. Splitting them would invent a player, so it is not done.")
    gap_rows = [[f'<strong>{esc(g["abbr"])}</strong>',
                 UNIT_LABEL.get(g["unit"], esc(g["unit"])),
                 esc(g["position"]), esc(g["listed"]),
                 src(g["chart_url"], "chart")] for g in gaps]
    gap_note = ("Lines with no first string listed at all. These are chart gaps, not injuries, "
                "so they are excluded from every count above.")
    defence_rows, offence_rows = slot_rows("defense"), slot_rows("offense")
    limits_html = "".join("<li>" + esc(x) + "</li>" for x in ladder["method"]["limits"])
    merged_table = table(["Club", "Unit", "Position", "Rank",
                          "Cell as published on the club site", "Source"],
                         merged_rows, note=merged_note)
    gap_table = table(["Club", "Unit", "Position", "Players the chart lists", "Source"],
                      gap_rows, note=gap_note) if gap_rows else ""
    slot_headers = ["Club", "Position", "Now starting", "Player", "Their status",
                    "Who is out above them", "Source"]

    body = f"""
<section class="kpis">
  {kpi("Clubs with a chart", c.get("clubs_with_chart"), f'{c.get("clubs_without_chart")} of 32 publish none')}
  {kpi("Position slots", c.get("slots"), f'{c.get("offense_slots")} offense · {c.get("defense_slots")} defence')}
  {kpi("Backups starting", c.get("slots_started_by_a_backup"), "slots where the 1st string is Out or Doubtful")}
  {kpi("3rd string or worse", c.get("slots_with_3rd_string_or_worse"), "no club is this thin this week")}
  {kpi("Starters at risk", c.get("slots_starter_at_risk"), "questionable, DNP or limited")}
  {kpi("Chart gaps flagged", c.get("chart_gap_slots"), "slots with no 1st string listed")}
</section>

<section class="panel">
  <div class="panel-head"><h2>Every club, offence and defence</h2><a href="injuries.html">Official injury rows &rarr;</a></div>
  {table(["Club", "Name", "Slots", "Offence slots on a backup", "Defence slots on a backup",
          "Starters at risk", "Deepest string starting", "Injury report", "Source"], rows,
         note=club_note)}
</section>

<section class="grid-2">
  <div class="panel">
    <div class="panel-head"><h2>Defence: backups pressed into duty</h2></div>
    {table(slot_headers, defence_rows,
           note="Empty is the honest answer when no defensive line meets the test. It is not a gap in the data.")
     if defence_rows
     else '<p class="empty">No defensive line this week has its first string ruled Out or Doubtful on the official report.</p>'}
  </div>
  <div class="panel">
    <div class="panel-head"><h2>Offence: backups pressed into duty</h2></div>
    {table(slot_headers, offence_rows, note="Same test, offensive unit only.")
     if offence_rows
     else '<p class="empty">No offensive line this week has its first string ruled Out or Doubtful on the official report.</p>'}
  </div>
</section>

<section class="panel">
  <div class="panel-head"><h2>How the ladder is built, and what it cannot see</h2></div>
  <div class="grid-3">
    <div class="stat"><h4>Where the ladder comes from</h4>
      <p>{esc(ladder["method"]["depth_charts"])}</p></div>
    <div class="stat"><h4>Who counts as unavailable</h4>
      <p>{esc(ladder["method"]["starter_rule"])}</p></div>
    <div class="stat"><h4>What is left blank</h4>
      <p>{esc(ladder["method"]["no_report_clubs"])}</p></div>
  </div>
  <ul class="bullets">
    {limits_html}
  </ul>
</section>

<section class="panel">
  <div class="panel-head"><h2>Chart defects found and published, not silently fixed</h2>
    <a href="review.html">Flagged for Review &rarr;</a></div>
  {merged_table}
  {gap_table}
</section>
"""
    return page("pages/depth.html", "Depth & Deficiency", body,
                "First, second, third and fourth string for every club, joined to the official "
                "injury report, for the offence and the defence separately.",
                ladder.get("generated_at"))


# ------------------------------------------------------------- correlations
def correlations_page(corr, dash=None):
    rows = []
    for r in corr.get("game_level", []):
        r_ = r.get("r")
        ci = r.get("ci95")
        p = r.get("p_value")
        strong = r_ is not None and abs(r_) >= 0.10
        rows.append([
            f'<strong>{esc(r.get("id"))}</strong>',
            esc(r.get("relationship")),
            num(r.get("n")),
            num(r_, 4) if r_ is not None else '<span class="missing">blank</span>',
            (f"[{ci[0]:+.4f}, {ci[1]:+.4f}]" if ci else '<span class="missing">blank</span>'),
            num(p, 4) if p is not None else '<span class="missing">blank</span>',
            '<span class="badge pass">material</span>' if strong
            else '<span class="badge neutral">weak</span>',
            esc(r.get("note", "")),
            src(r.get("source", SOURCE["schedule"]), "nfl.com"),
        ])
    body = f"""
<p class="note">These figures come from a committed research extract built
  {esc(corr.get("generated_at"))}. The daily refresh does not rebuild that extract, so this
  page states its own extract time rather than inheriting the site stamp.</p>

<section class="panel">
  <div class="panel-head"><h2>Game-level correlations, measured</h2>
    <a href="strategies.html">What the gates do with them &rarr;</a></div>
  {table(["ID", "Relationship", "n", "Pearson r", "95% CI", "p", "Strength", "Why it matters", "Source"], rows,
         note=esc(corr.get("method", "")) + " " + esc(corr.get("publication_rule", "")))}
</section>

<section class="grid-2">
  <div class="panel">
    <div class="panel-head"><h2>The three that decide everything</h2></div>
    <ul class="bullets">
      <li><strong>C1 = 0.4312.</strong> The closing spread already explains the result this well.
        That is the bar any own line has to beat, and it is why an unvalidated model line is not a signal.</li>
      <li><strong>C3 = 0.0190 (p = 0.113).</strong> Our disagreement with the closing line is not
        significantly correlated with the part of the result the market got wrong. This is the single
        most important number on the site: it is the reason no strategy is promoted.</li>
      <li><strong>C9 = -0.0923.</strong> Wind is the only environmental variable that moves the total
        at all, and it moves it down. Temperature does not (C8 = 0.0092, p = 0.517).</li>
    </ul>
  </div>
  <div class="panel">
    <div class="panel-head"><h2>Sample</h2></div>
    <ul class="bullets">
      <li>{num(corr.get("sample", {}).get("games"))} games, seasons
        {esc(str(min(corr.get("sample", {}).get("seasons", [0]))))} to
        {esc(str(max(corr.get("sample", {}).get("seasons", [0]))))}.</li>
      <li>{num(corr.get("sample", {}).get("games_with_both_lines"))} carry both a closing spread and a
        closing total, so every figure above uses paired observations only.</li>
      <li>Relationships with fewer than 25 paired observations are published as
        <span class="missing">blank</span>, never as a number.</li>
    </ul>
  </div>
</section>
"""
    return page("pages/correlations.html", "Correlations", body,
                "Measured relationships, with confidence intervals, on a 7,000-game sample.",
                (dash or {}).get("generated_at") or corr.get("generated_at"))


# ------------------------------------------------------------------ parlays
def parlays_page(par, props, dash=None):
    pairs = par.get("pairs", [])
    rows = []
    for p in pairs:
        phi = p.get("leg_phi_correlation") or {}
        rows.append([
            esc(" + ".join(p.get("pair", []))),
            num(p.get("n_parlays")),
            pct(p.get("hit_rate"), 2),
            pct(p.get("hit_rate_if_independent"), 2),
            num(p.get("correlation_ratio"), 4),
            num(phi.get("r"), 4) if phi.get("r") is not None else '<span class="missing">blank</span>',
            (f'{p["roi_pct"]:.2f}%' if p.get("roi_pct") is not None
             else '<span class="missing">blank</span>'),
            num(p.get("p_value_bh_adjusted"), 4) if p.get("p_value_bh_adjusted") is not None
            else '<span class="missing">blank</span>',
            badge("PROVEN" if p.get("survives_multiple_testing_5pct") else "NOT PROVEN"),
            src("https://www.nfl.com/schedules/", "nfl.com"),
        ])
    same_game = (props or {}).get("same_game_correlations", [])
    sg_rows = [[f'<strong>{esc(s.get("id"))}</strong>', esc(s.get("relationship")), num(s.get("n")),
                num(s.get("r"), 4) if s.get("r") is not None else '<span class="missing">blank</span>',
                (f"[{s['ci95'][0]:+.4f}, {s['ci95'][1]:+.4f}]" if s.get("ci95")
                 else '<span class="missing">blank</span>'),
                num(s.get("p_value"), 4) if s.get("p_value") is not None
                else '<span class="missing">blank</span>',
                esc(s.get("note", "")),
                src("https://www.nfl.com/stats/player-stats/", "nfl.com")]
               for s in same_game]

    body = f"""
<p class="note">These figures come from a committed research extract built
  {esc(par.get("generated_at"))}. The daily refresh does not rebuild that extract, so this
  page states its own extract time rather than inheriting the site stamp.</p>

<section class="panel">
  <div class="panel-head"><h2>Two-leg parlays across different games</h2></div>
  {table(["Legs", "Parlays", "Hit rate", "Hit rate if independent", "Dependence ratio",
          "Leg correlation (phi)", "ROI", "BH-adjusted p", "Verdict", "Source"], rows,
         note=esc(par.get("reading", "")) + " " + esc(par.get("pricing_note", "")) +
              f" {len(pairs)} pairs tested, {par.get('n_pairs_surviving_bh_5pct')} survive correction "
              f"for multiple testing at the 5% level. The dependence ratio is the observed joint hit "
              f"rate divided by the product of the marginal hit rates: 1.0000 means the legs behave "
              f"as if they were independent.")}
</section>

<section class="panel">
  <div class="panel-head"><h2>Same-game prop combinations</h2>
    <a href="props.html">Player projections &rarr;</a></div>
  {table(["ID", "Combination", "n", "Pearson r", "95% CI", "p", "What it means for a combo", "Source"], sg_rows,
         note="These are the correlations that decide whether a same-game parlay is fairly priced. "
              "A book that prices a two-leg same-game parlay as if the legs were independent is "
              "underpricing it whenever r is strongly positive, and the table shows where that is true.")
    if sg_rows else '<p class="empty">No same-game correlations published.</p>'}
</section>

<section class="panel">
  <div class="panel-head"><h2>Why no parlay on this site is a recommendation</h2></div>
  <ul class="bullets">
    <li>Every price used is taken from the source file for each leg. No -110 assumption is made anywhere.</li>
    <li>Legs are combined only when both fired in the same week in <strong>different</strong> games,
      so the independence question is about week effects, not about one play causing another.</li>
    <li>P-values are corrected across all {len(pairs)} pairs with Benjamini-Hochberg. Testing dozens of
      parlays and reporting the best one manufactures a winner; the correction charges for that.</li>
    <li>{esc((props or {}).get("price_status", ""))}</li>
  </ul>
</section>
"""
    return page("pages/parlays.html", "Parlays & Combos", body,
                "Parlay pricing, dependence between legs, and why the product rule is fair between "
                "games and unfair inside one.",
                (dash or {}).get("generated_at") or par.get("generated_at"))


# ------------------------------------------------------------- skill vs luck
def luck_page(lb, dash=None):
    rows = []
    for r in lb.get("luck_accounting", {}).get("rows", []):
        band = r.get("luck_band_95_units") or [None, None]
        rows.append([
            esc(r.get("strategy")),
            num(r.get("n_bets")),
            num(r.get("profit_units"), 2),
            f"{band[0]:+.1f} to {band[1]:+.1f}" if band[0] is not None else '<span class="missing">blank</span>',
            num(r.get("z_vs_fair_price"), 3),
            num(r.get("p_value_two_sided"), 4),
            num(r.get("bets_needed_for_80pct_power")),
            badge("outside the luck band" if r.get("profit_outside_luck_band") else "inside the luck band"),
            src(lb.get("official_source", SOURCE["schedule"]), "nfl.com"),
        ])
    gates = lb.get("gate_definitions", [])
    body = f"""
<p class="note">These figures come from a committed research extract built
  {esc(lb.get("generated_at"))}. The daily refresh does not rebuild that extract, so this
  page states its own extract time rather than inheriting the site stamp.</p>

<section class="panel">
  <div class="panel-head"><h2>Every strategy against a fair-price null</h2>
    <a href="strategies.html">Leaderboard &rarr;</a></div>
  {table(["Strategy", "Bets", "Profit (units)", "95% luck band", "z", "p", "Bets needed for 80% power",
          "Verdict", "Source"], rows,
         note=esc(lb.get("luck_accounting", {}).get("method", "")) + " " +
              esc(lb.get("luck_accounting", {}).get("note", "")))}
</section>

<section class="panel">
  <div class="panel-head"><h2>The eight gates</h2></div>
  {table(["Gate", "Requirement", "Why it exists"],
         [[f'<strong>{esc(g["id"])}</strong>', esc(g["name"]), esc(g["why"])] for g in gates],
         note=f"{len(gates)} gates, fixed before any strategy was evaluated. A strategy must clear all "
              f"{len(gates)} to be called proven; the leaderboard publishes how many each one cleared.")}
</section>

<section class="grid-2">
  <div class="panel">
    <div class="panel-head"><h2>What "removing luck" actually means here</h2></div>
    <ul class="bullets">
      <li><strong>A fair-price null, not a simulation.</strong> If the observed prices are fair, a
        1-unit bet at decimal odds d has mean profit 0 and variance d-1. The 95% band on total profit
        is therefore ±1.96·sqrt(Σ(d-1)) over the bets actually placed.</li>
      <li><strong>Multiple testing.</strong> {lb.get("n_strategies")} rules were tested; every p-value
        is Benjamini-Hochberg corrected, so the best of a dozen rules cannot buy significance.</li>
      <li><strong>Holdout.</strong> 2024 and 2025 were never used to tune thresholds and are scored
        separately.</li>
      <li><strong>Power, not just significance.</strong> Where the bets needed for 80% power exceeds
        any realistic season, the honest answer is that this sample cannot settle the question.</li>
    </ul>
  </div>
  <div class="panel">
    <div class="panel-head"><h2>What the sample cannot settle</h2></div>
    <ul class="bullets">
      <li>{num(lb.get("totals", {}).get("bets_scored"))} bets scored across
        {num(lb.get("totals", {}).get("games_in_sample"))} games.</li>
      <li>{num(lb.get("unscored_games_no_price"))} games in the extract carry no published price. They
        are used for training and are never scored, because scoring them would require inventing a price.</li>
      <li>Every scored bet carries an observed price
        ({esc(str(lb.get("totals", {}).get("all_prices_observed")))}). No vig assumption is applied.</li>
    </ul>
  </div>
</section>
"""
    return page("pages/luck.html", "Skill vs Luck", body,
                "What a purely lucky run would have produced, and whether any strategy left that band.",
                (dash or {}).get("generated_at") or lb.get("generated_at"))


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
    write("pages/sections.html", sections_page(dash))
    write("pages/lines.html", lines_page(snap, lines, dash))
    write("pages/correlations.html",
          correlations_page(load_rel("data/s9cb/correlations.json"), dash))
    write("pages/strategies.html", strategies_page(strat, dash))
    write("pages/luck.html", luck_page(load_rel("data/s9cb/leaderboard.json"), dash))
    write("pages/parlays.html", parlays_page(load_rel("data/s9cb/parlays.json"),
                                             load_rel("data/s9cb/props.json"), dash))
    write("pages/props.html", props_page(props, dash))
    write("pages/injuries.html", injuries_page(avail, dash))
    write("pages/depth.html", depth_page(load_rel("data/depth_ladder.json"), snap))
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
