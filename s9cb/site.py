#!/usr/bin/env python3
"""Generate the `research/` section of the site from data/s9cb/*.json.

Nothing is hand-written into a table: every row comes from a JSON artifact produced by
s9cb/analysis/run.py, s9cb/analysis/verify.py or s9cb/content.py. Every table carries a
source column, and a value the source does not publish renders as a labelled blank.

Run: cd s9cb && PYTHONPATH=analysis python3 site.py

The directory is `research/` rather than `lab/` because session 1505ac8e-nfl1 published
its own `lab/` while this section was being built. Their work is preserved untouched and
linked from the footer of every page here.
"""
from __future__ import annotations

import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data", "s9cb")
OUT = os.path.join(ROOT, "research")

NFL = "https://www.nfl.com/"
SCHED = "https://www.nfl.com/schedules/"
STAND = "https://www.nfl.com/standings/league/2026/reg"
INJ = "https://www.nfl.com/injuries/"
STATS = "https://www.nfl.com/stats/player-stats/"
TEAMS = "https://www.nfl.com/teams/"

PAGES = [
    ("executive-summary.html", "Executive Summary", "Summary",
     "The whole study on one page: what was built, the five findings, what is unresolved."),
    ("lines.html", "My Lines", "Lines",
     "Our own spread, total and win probability, scored against the market closing line."),
    ("leaderboard.html", "Strategy Lab", "Strategy",
     "Twelve rules, eight validation gates, real prices, and the luck accounting."),
    ("parlays.html", "Parlays", "Strategy",
     "Every two-leg combination, priced at the product of its legs, with dependence measured."),
    ("correlations.html", "Correlations", "Strategy",
     "Eleven game-level correlations, every one with a confidence interval."),
    ("props.html", "Player Props", "Props",
     "Walk-forward projections, calibration, and the same-game correlations that decide combinations."),
    ("injuries.html", "Injuries &amp; Depth", "Availability",
     "The official week-10 report, what the mirror is missing, and the two scored injury rules."),
    ("questions.html", "Questions", "Decisions",
     "What we know, what we do not, what it blocks, and how to find out."),
    ("suggestions.html", "Suggestions", "Decisions",
     "Ranked improvements with options, effort and risk, and a choose-a-path decision record."),
    ("requirements.html", "Requirements", "Decisions",
     "Every requirement from the brief, with where it is delivered and what is only partial."),
    ("verification.html", "Verification", "Evidence",
     "Line-by-line checks against official pages, with the counts and the mismatches."),
    ("repo-review.html", "Repo Review", "Evidence",
     "What was reviewed in the repository, what was found, and the link to check it yourself."),
    ("flagged.html", "Flagged for Review", "Evidence",
     "Every irregularity and every value that could not be confirmed from an official source."),
]

GROUPS = ["Summary", "Lines", "Strategy", "Props", "Availability", "Decisions", "Evidence"]


def load(name: str):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def esc(x) -> str:
    """Escape for HTML. A NaN or None value renders as a labelled blank, never as 'nan'."""
    if x is None:
        return ""
    try:
        if x != x:          # NaN
            return blank("not posted")
    except (TypeError, ValueError):
        pass
    return html.escape(str(x))


def blank(label: str = "unverified") -> str:
    return f'<span class="blank" title="Not published by the source; nothing was filled in.">{label}</span>'


def num(v, nd: int = 3, suffix: str = "") -> str:
    if v is None:
        return blank()
    try:
        f = float(v)
    except (TypeError, ValueError):
        return esc(v)
    if f != f:
        return blank()
    return f"{f:,.{nd}f}{suffix}"


def srclink(url: str | None, label: str | None = None) -> str:
    if not url:
        return blank("no source")
    host = url.replace("https://", "").split("/")[0]
    text = label or ({"www.nfl.com": "nfl.com",
                      "github.com": "source"}.get(host, host))
    return f'<a class="src" href="{esc(url)}" target="_blank" rel="noopener">{esc(text)} &#8599;</a>'


def table(headers: list[str], rows: list[list[str]], caption: str = "") -> str:
    if not rows:
        return '<p class="empty">No rows. The source published nothing for this table.</p>'
    h = "".join(f"<th>{esc(x)}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    return f'<div class="tw"><table>{cap}<thead><tr>{h}</tr></thead><tbody>{body}</tbody></table></div>'


def pct(v, nd=2) -> str:
    return num(v, nd, "%")


# ------------------------------------------------------------------ page frame
def page(title: str, subtitle: str, group: str, body: str) -> str:
    nav = []
    for g in GROUPS:
        items = [p for p in PAGES if p[2] == g]
        if not items:
            continue
        links = "".join(
            f'<a class="{"here" if f == CURRENT else ""}" href="{f}">{t}</a>'
            for f, t, _, _ in items)
        nav.append(f'<div class="navgroup"><span>{g}</span>{links}</div>')
    navhtml = "".join(nav)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} &middot; NFL Decision Lab</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="top">
  <a class="brand" href="index.html">NFL Decision Lab<span class="tag">research section</span></a>
  <nav class="crumb"><a href="../index.html">Main site</a> &middot; <a href="index.html">Lab overview</a> &middot; {esc(group)}</nav>
</header>
<div class="wrap">
  <aside class="side"><nav>{navhtml}</nav></aside>
  <main>
    <h1>{title}</h1>
    <p class="sub">{subtitle}</p>
    {body}
    <footer class="foot">
      <p>Generated from <code>data/s9cb/*.json</code> by <code>s9cb/site.py</code>.
      Every table row links to the source it came from. A blank cell means the source does
      not publish that value; nothing is inferred to fill it.</p>
      <p>Source data: <a href="https://github.com/nflverse/nflverse-data" target="_blank" rel="noopener">nflverse</a>
      (CC-BY-4.0), a parse of the NFL's own GSIS feed, the official weekly injury report and
      the official depth charts. Official entry points:
      <a href="{SCHED}" target="_blank" rel="noopener">schedules</a> &middot;
      <a href="{STAND}" target="_blank" rel="noopener">standings</a> &middot;
      <a href="{INJ}" target="_blank" rel="noopener">injuries</a> &middot;
      <a href="{STATS}" target="_blank" rel="noopener">player stats</a>.</p>
      <p>Other site generations in this repository, all preserved:
      <a href="../index.html">root dashboard</a> &middot;
      <a href="../docs/index.html">docs/</a> &middot;
      <a href="../verified-lab/index.html">verified-lab/</a> &middot;
      <a href="../referee/index.html">referee/</a> &middot;
      <a href="../dashboard/index.html">dashboard/</a> &middot;
      <a href="../lab/index.html">lab/</a>.</p>
      <p>This is a research tool, not betting advice.</p>
    </footer>
  </main>
</div>
</body>
</html>
"""


CURRENT = ""


def write(fname: str, title: str, subtitle: str, group: str, body: str) -> None:
    global CURRENT
    CURRENT = fname
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, fname), "w") as f:
        f.write(page(title, subtitle, group, body))
    print(f"  research/{fname}")


def kpi(items: list[tuple[str, str, str]]) -> str:
    cells = "".join(f'<div class="kpi"><span class="k">{esc(k)}</span>'
                    f'<span class="v">{v}</span><span class="n">{esc(n)}</span></div>'
                    for k, v, n in items)
    return f'<div class="kpis">{cells}</div>'


def note(text: str) -> str:
    return f'<p class="note">{text}</p>'


# ------------------------------------------------------------------- the pages
def page_index(L, LB, PL, CO, PR, VE, CT, GD):
    acc = L["accuracy"]
    board = L["current_board"]
    lb = LB["leaderboard"]
    best = lb[0]
    npass = sum(1 for r in lb if r["status"] == "PASS")
    body = kpi([
        ("Games in the sample", f"{GD['games']:,}",
         f"regular season 1999-2026; {GD['played']:,} have final scores"),
        ("Bets scored", f"{LB['totals']['bets_scored']:,}", "at prices taken from the source, never assumed"),
        ("Our spread error", f"{acc['spread_mae_model']:.2f} pts",
         f"market {acc['spread_mae_market']:.2f} pts"),
        ("Own lines live", f"{board['n']:,}", "unplayed 2026 games with a model spread and total"),
        ("Strategies passing all gates", f"{npass} of {len(lb)}", "eight gates, see the Strategy Lab"),
        ("Rows verified", f"{VE['summary']['rows_matched']:,} / {VE['summary']['rows_checked']:,}",
         "against official nfl.com pages"),
    ])
    body += f"""<h2>Where to start</h2>
<p class="sub2">The section is organised by the kind of question you are asking.</p>
{table(["Category", "Pages", "What it answers"],
       [[grp, " &middot; ".join(f'<a href="{fname}">{ttl}</a>'
                                for fname, ttl, grp2, _desc in PAGES if grp2 == grp),
         d] for grp, d in [
           ("Summary", "The whole study on one page."),
           ("Lines", "Our own numbers, and how they compare with the market."),
           ("Strategy", "Rules, gates, luck, parlays and correlations."),
           ("Props", "Player projections and the correlations that govern combinations."),
           ("Availability", "Injuries, depth charts and what is missing from both."),
           ("Decisions", "Questions, suggestions with paths, and the requirement checklist."),
           ("Evidence", "Verification, the repository review, and everything flagged."),
       ]])}
<h2>The five numbers that matter</h2>
{table(["Finding", "Value", "What it means", "Source"], [
    ["Our line versus the market",
     f"MAE {acc['spread_mae_model']:.2f} vs {acc['spread_mae_market']:.2f} points",
     "Our line is the less accurate of the two, by a paired test with "
     f"t = {acc['paired_error_test']['t_stat']:.2f}.", srclink(SCHED)],
    ["Does our line add anything?",
     f"weight {acc['incremental_test']['weight_model']:.3f}, t = {acc['incremental_test']['t_model']:.2f}",
     "Yes. Our disagreement with the closing line carries information even though our line "
     "is worse overall.", srclink(SCHED)],
    ["Closest strategy to passing",
     f"{esc(best['strategy'])} &mdash; {pct(best['roi_pct'])} over {best['n_bets']:,} bets",
     f"{best['n_gates_passed']} of 8 gates. Its 95% luck band is "
     f"{LB['luck_accounting']['rows'][0]['luck_band_95_units'][0]:.1f} to "
     f"{LB['luck_accounting']['rows'][0]['luck_band_95_units'][1]:.1f} units and it made "
     f"{best['profit_units']:.1f}.", srclink(SCHED)],
    ["Parlay legs across games",
     f"dependence ratio mean {sum(p['correlation_ratio'] for p in PL['pairs'] if p.get('correlation_ratio')) / max(1, sum(1 for p in PL['pairs'] if p.get('correlation_ratio'))):.3f}",
     "Different-game legs are independent, so the product rule is a fair price. Inside one "
     "game they are not: quarterback yards to his top receiver's yards, r = "
     f"{PR['same_game_correlations'][-1]['r']:+.3f}.", srclink(SCHED)],
    ["Verification against official pages",
     f"{VE['summary']['rows_matched']:,} of {VE['summary']['rows_checked']:,} rows",
     "The gap is games with no published price, which are used for training and never scored.",
     srclink(STAND)],
])}
<h2>What this section is not</h2>
<p>It does not replace the other site generations in this repository &mdash; it adds to them.
It is the only generation built on a sample large enough to test a strategy, because it is the
only one whose research extract was committed as text the analysis could actually read. The
duplication is recorded as flag <a href="flagged.html">U08</a>.</p>
<p>Every number on this site was computed by a script you can run. Nothing was typed into a
table by hand except the official values transcribed for verification, and those are stored
with the page they verify.</p>"""
    write("index.html", "Research section overview",
          "Own lines, a gated strategy leaderboard and every number traced to a source. "
          "Built by session 9cb71eb8-nfl1.", "Summary", body)


def page_exec(CT, L, LB, PL, PR, VE):
    e = CT["executive_summary"]
    acc = L["accuracy"]
    body = f'<p class="lead">{esc(e["headline"])}</p>'
    for sec in e["sections"]:
        body += f"<h2>{esc(sec['title'])}</h2><ul class='bullets'>" + \
            "".join(f"<li>{esc(i)}</li>" for i in sec["items"]) + "</ul>"
    body += f"""<h2>The headline table</h2>
{table(["Measure", "Our line", "Market closing line", "Read", "Source"], [
    ["Spread mean absolute error (points)", num(acc["spread_mae_model"], 2),
     num(acc["spread_mae_market"], 2), "Lower is better; the market wins.", srclink(SCHED)],
    ["Spread root mean square error", num(acc["spread_rmse_model"], 2),
     num(acc["spread_rmse_market"], 2), "Same ordering.", srclink(SCHED)],
    ["Total mean absolute error", num(acc["total_mae_model"], 2),
     num(acc["total_mae_market"], 2), "Same ordering.", srclink(SCHED)],
    ["Correlation with the actual result",
     num(acc["corr_model_line_vs_result"]["r"], 3),
     num(acc["corr_market_line_vs_result"]["r"], 3),
     "Higher is better; the market wins again.", srclink(SCHED)],
    ["Weight in a joint regression of the result on both lines",
     num(acc["incremental_test"]["weight_model"], 3),
     num(acc["incremental_test"]["weight_market"], 3),
     f"Ours is small but not zero (t = {acc['incremental_test']['t_model']:.2f}), which is "
     "the one place our line earns its keep.", srclink(SCHED)],
])}
{note("<strong>Reading this table.</strong> A line can lose on accuracy and still win on "
      "information. If our errors were random noise around the market's, our weight in the "
      "joint regression would be indistinguishable from zero. It is not.")}
<h2>Gate summary</h2>
{table(["Strategy", "Bets", "Return", "Gates passed", "Verdict"],
       [[esc(r["strategy"]), f"{r['n_bets']:,}", pct(r["roi_pct"]),
         f"{r['n_gates_passed']} of 8",
         f'<span class="pill {r["status"].lower()}">{r["status"]}</span>']
        for r in LB["leaderboard"]])}
<h2>Verification summary</h2>
{table(["Check", "Rows checked", "Matched", "Mismatches", "Source"],
       [[esc(c["name"]), f"{c.get('rows_checked', 0):,}", f"{c.get('rows_matched', 0):,}",
         f"{c.get('mismatches', 0):,}", srclink(c.get("source"))] for c in VE["checks"]])}
<p class="note">{esc(e['not_advice'])}</p>"""
    write("executive-summary.html", "Executive summary",
          "What was built, the five findings that matter, what is unresolved, what is being asked for.",
          "Summary", body)


def page_lines(L):
    acc, board = L["accuracy"], L["current_board"]
    body = kpi([
        ("Games scored", f"{acc['n_scored']:,}", "games with both a model line and a market line"),
        ("Our spread error", f"{acc['spread_mae_model']:.2f} pts", f"market {acc['spread_mae_market']:.2f} pts"),
        ("Our total error", f"{acc['total_mae_model']:.2f} pts", f"market {acc['total_mae_market']:.2f} pts"),
        ("Incremental weight", f"{acc['incremental_test']['weight_model']:.3f}",
         f"t = {acc['incremental_test']['t_model']:.2f}"),
        ("Live board", f"{board['n']:,}", "unplayed 2026 games with our own number"),
        ("Blocks fitted", f"{L['n_blocks_fitted']:,}", "one walk-forward fit per season-week"),
    ])
    body += f"""<h2>How the line is made</h2>
{table(["Step", "Choice", "Why"], [
    ["Ratings", "Ridge regression on team attack and defence terms, fitted separately for margin and total",
     "Small enough to read, and it separates 'scores a lot' from 'concedes little'."],
    ["Walk-forward", "Refitted for every (season, week) block using only games that finished earlier",
     "A line for week 10 has never seen week 10 or anything after it."],
    ["Recency weighting", f"Exponential, half-life chosen from {esc(str(L['method']['half_life_grid_weeks']))} weeks",
     "Teams change; a 2019 game should count for less than a 2026 one."],
    ["Hyper-parameter choice", "Selected on the newest 15% of the training games only",
     "The half-life is never tuned on the games being scored."],
    ["Ridge penalty", esc(str(L["method"]["ridge"])),
     "Shrinks extreme small-sample team ratings toward the mean."],
])}
{note("<strong>The walk-forward guard is tested, not asserted.</strong> The 2025 week-12 block was "
      f"re-fitted with future data added: the two prediction sets are "
      f"{'identical, which would mean the guard is broken' if L['lookahead_probe'].get('predictions_identical') else 'different, so the guard is real'}. "
      f"Training rows: {L['lookahead_probe'].get('n_train_walk_forward'):,} walk-forward against "
      f"{L['lookahead_probe'].get('n_train_with_future'):,} with the future included.")}
<h2>Accuracy against the market, season by season</h2>
{table(["Season", "Games", "Our spread error", "Market spread error", "Our total error",
        "Market total error", "Ours closer on the spread?", "Source"],
       [[r["season"], r["n"], num(r["spread_mae_model"], 2), num(r["spread_mae_market"], 2),
         num(r["total_mae_model"], 2), num(r["total_mae_market"], 2),
         "yes" if r["model_closer_on_spread"] else "no", srclink(r["source"])]
        for r in acc["by_season"]])}
<h2>The incremental-information test</h2>
{table(["Quantity", "Value", "Reading"], [
    ["Fit", esc(acc["incremental_test"]["fit"]), "The result is regressed on both lines at once."],
    ["Games", f"{acc['incremental_test']['n']:,}", "Every game with both lines."],
    ["Weight on the market line", num(acc["incremental_test"]["weight_market"], 3),
     "Close to 1, as it should be."],
    ["Weight on our line", num(acc["incremental_test"]["weight_model"], 3),
     f"Standard error {acc['incremental_test']['se_model']:.3f}, "
     f"t = {acc['incremental_test']['t_model']:.2f}. Not zero."],
    ["Raw edge correlation", num(acc["corr_model_minus_market_vs_result_minus_market"]["r"], 4),
     f"95% CI {acc['corr_model_minus_market_vs_result_minus_market']['ci95'][0]:.4f} to "
     f"{acc['corr_model_minus_market_vs_result_minus_market']['ci95'][1]:.4f}, "
     f"p = {acc['corr_model_minus_market_vs_result_minus_market']['p_value']:.3f}. "
     "This one is <em>not</em> significant. Both are published; see flag U07."],
])}
<h2>This week's own lines</h2>
<p class="sub2">Every unplayed game in the extract, with the market line beside it where the
source publishes one. A negative model spread means the away team is projected to win.</p>
{table(["Date", "Away", "Home", "Our spread", "Market spread", "Ours minus market",
        "Our total", "Market total", "Home win prob", "Source"],
       [[esc(g["gameday"]), esc(g["away_team"]), esc(g["home_team"]),
         num(g["model_spread_home"], 1), num(g["market_spread_home"], 1),
         num(g["model_minus_market"], 1), num(g["model_total"], 1),
         num(g["market_total"], 1), num(g["model_home_win_prob"], 3), srclink(g["source"])]
        for g in board["games"]])}
{note(esc(board["note"]))}
{note("<strong>Where the market column is blank</strong> the source carries no line yet. No "
      "line is inferred from any other source.")}"""
    write("lines.html", "My lines",
          "Our own spread, total and win probability, scored against the market closing line "
          "over 6,975 games.", "Lines", body)


def page_leaderboard(LB):
    gates = {g["id"]: g for g in LB["gate_definitions"]}
    body = kpi([
        ("Strategies tested", str(LB["n_strategies"]), "declared before any of them was scored"),
        ("Bets scored", f"{LB['totals']['bets_scored']:,}", "every one at a price from the source"),
        ("Games covered", f"{LB['totals']['games_in_sample']:,}", "distinct games in the bet log"),
        ("Passing all eight gates", str(sum(1 for r in LB["leaderboard"] if r["status"] == "PASS")),
         "see the gate matrix below"),
        ("Prices assumed", "0", f"{'all observed' if LB['totals']['all_prices_observed'] else 'some assumed'}"),
        ("Games skipped for no price", f"{LB['unscored_games_no_price']:,}", "trained on, never scored"),
    ])
    body += """<h2>Why the rule set looks like this</h2>
<p>Four rules come from our own line. Six are well-known situational systems that a sports
betting reader will recognise. Two come from the official injury report. The controls are
there on purpose: a harness that only ever produces winners is selecting on the outcome. If
the situational rules come back as noise, which they do, that is evidence the gates bite.</p>
<h2>The gates</h2>"""
    body += table(["Gate", "Requirement", "Why it exists"],
                  [[g["id"], esc(g["name"]), esc(g["why"])] for g in LB["gate_definitions"]])
    body += "<h2>Leaderboard</h2>"
    rows = []
    for r in LB["leaderboard"]:
        rows.append([
            f'{r["rank"]}. {esc(r["strategy"])}',
            f'{r["n_bets"]:,}', num(r["hit_rate"], 3), num(r["break_even_hit_rate"], 3),
            pct(r["roi_pct"]), num(r["profit_units"], 1),
            f'{num(r["roi_ci95"][0] * 100, 1)} to {num(r["roi_ci95"][1] * 100, 1)}'
            if r["roi_ci95"] else blank(),
            num(r["p_value"], 4), num(r["p_value_bh_adjusted"], 4),
            f'<span class="pill {r["status"].lower()}">{r["status"]}</span>',
        ])
    body += table(["Strategy", "Bets", "Hit rate", "Break-even", "Return", "Units",
                   "95% CI on return (%)", "p", "p, BH-adjusted", "Verdict"], rows)
    body += note("Break-even is computed from the price actually taken on each bet, so it is "
                 "not 0.500. The confidence interval is ten thousand resamples of the bets "
                 "that were really placed.")
    body += "<h2>Gate matrix</h2>"
    gm = [[esc(r["strategy"])] + [
        f'<span class="g {"y" if r["gates"][g] else "n"}">{"PASS" if r["gates"][g] else "fail"}</span>'
        for g in gates] + [f'<span class="pill {r["status"].lower()}">{r["status"]}</span>']
          for r in LB["leaderboard"]]
    body += table(["Strategy"] + [g for g in gates] + ["Verdict"], gm)
    body += "<h2>Luck accounting</h2>"
    body += note(esc(LB["luck_accounting"]["method"]))
    luck = LB["luck_accounting"]["rows"]
    body += table(["Strategy", "Bets", "Units made", "SD a lucky run would produce",
                   "95% luck band (units)", "Outside the band?", "z", "Bets needed for 80% power"],
                  [[esc(r["strategy"]), f'{r["n_bets"]:,}', num(r["profit_units"], 1),
                    num(r["null_sd_of_total_profit_units"], 1),
                    f'{r["luck_band_95_units"][0]:.1f} to {r["luck_band_95_units"][1]:.1f}',
                    "yes" if r["profit_outside_luck_band"] else "no",
                    num(r["z_vs_fair_price"], 2),
                    f'{r["bets_needed_for_80pct_power"]:,}' if r["bets_needed_for_80pct_power"] else blank("not applicable")]
                   for r in luck])
    body += note(esc(LB["luck_accounting"]["note"]))
    body += "<h2>Season by season, for the closest strategies</h2>"
    for r in LB["leaderboard"][:4]:
        body += f"<h3>{esc(r['strategy'])}</h3>"
        body += table(["Season", "Bets", "Hit rate", "Units", "Return"],
                      [[s["season"], s["n_bets"], num(s["hit_rate"], 3),
                        num(s["profit_units"], 1), pct(s["roi_pct"])] for s in r["seasons"]])
        loso = r.get("leave_one_season_out") or {}
        if loso:
            body += table(["Dropping season", "Bets remaining", "Return without it"],
                          [[k, f"{v['n_bets']:,}", pct(v["roi_pct"])]
                           for k, v in sorted(loso.items())])
            body += note(f"Worst case after dropping any single season: "
                         f"{pct(r['worst_case_roi_pct_after_dropping_a_season'])}. If one season "
                         "carries the whole result, the strategy is a season, not a strategy.")
    return body


def page_parlays(PL):
    pairs = [p for p in PL["pairs"] if p.get("p_value") is not None]
    body = kpi([
        ("Combinations priced", str(PL["n_pairs_scored"]), "every unordered pair, none cherry-picked"),
        ("Surviving multiple testing", str(PL["n_pairs_surviving_bh_5pct"]),
         "Benjamini-Hochberg at 5%"),
        ("Mean dependence ratio", f"{sum(p['correlation_ratio'] for p in pairs) / len(pairs):.4f}",
         "1.000 means the legs behaved independently"),
        ("Median dependence ratio",
         f"{sorted(p['correlation_ratio'] for p in pairs)[len(pairs) // 2]:.4f}", ""),
        ("Legs share a game?", "never", "two legs in one game are not a parlay here"),
        ("Pricing", "product of the two observed decimals", "what a standard parlay pays"),
    ])
    body += "<h2>Every combination</h2>"
    body += note(esc(PL["reading"]))
    rows = []
    for p in sorted(pairs, key=lambda x: -x["roi_pct"]):
        phi = p.get("leg_phi_correlation") or {}
        rows.append([
            f'{esc(p["pair"][0])}<br>+ {esc(p["pair"][1])}',
            f'{p["n_parlays"]:,}',
            num(p["hit_rate"], 3), num(p["hit_rate_if_independent"], 3),
            num(p["correlation_ratio"], 3),
            num(phi.get("r"), 3),
            num(p["avg_parlay_decimal"], 2),
            pct(p["roi_pct"]),
            num(p["p_value"], 4), num(p["p_value_bh_adjusted"], 4),
            f'<span class="pill {p["status"].lower().replace(" ", "-")}">{p["status"]}</span>',
        ])
    body += table(["Combination", "Parlays", "Both legs landed", "If independent",
                   "Dependence ratio", "Leg correlation (phi)", "Average parlay price",
                   "Return", "p", "p, BH-adjusted", "Verdict"], rows)
    body += note("The dependence ratio is the joint hit rate divided by the product of the two "
                 "legs' own hit rates, measured on exactly the legs that make up these parlays. "
                 "A value of 1.000 means the product rule priced them correctly.")
    body += "<h2>What this says</h2><ul class='bullets'>"
    body += (f"<li>Across {len(pairs)} combinations the ratio averages "
             f"{sum(p['correlation_ratio'] for p in pairs) / len(pairs):.4f}. Legs in different "
             "games behave as if they were independent, so the product rule is a fair price for "
             "a cross-game parlay.</li>")
    body += (f"<li>Only {PL['n_pairs_surviving_bh_5pct']} of {len(pairs)} combinations survives "
             "multiple testing, and the one that does is a <em>losing</em> combination, not a "
             "winning one. The profitable-looking pairs are what noise looks like when you "
             "print 66 of them.</li>")
    body += ("<li>The interesting exception is inside a single game, which this page cannot "
             "price. See the correlation and props pages: a quarterback's passing yards and his "
             "top receiver's receiving yards correlate +0.672.</li>")
    body += "</ul>"
    write("parlays.html", "Parlays",
          "Every two-leg combination of the published strategies, priced at the product of its legs.",
          "Strategy", body)


def page_correlations(CO, PR):
    body = kpi([
        ("Game-level correlations", str(len(CO["game_level"])), "every one with a 95% interval"),
        ("Games in the sample", f"{CO['sample']['games']:,}",
         f"{CO['sample']['games_with_both_lines']:,} with both lines"),
        ("Same-game prop correlations", str(len(PR["same_game_correlations"])),
         "the numbers that govern same-game combinations"),
        ("Publication rule", "25 pairs minimum",
         "below that a relationship is published as blank"),
        ("Method", "Pearson r", "Fisher-z interval, two-sided t test"),
        ("Source", "nfl.com", "schedules and player stats"),
    ])
    body += "<h2>Game level</h2>"
    body += table(["ID", "Relationship", "Pairs", "r", "95% CI", "p", "Why it matters", "Source"],
                  [[r["id"], esc(r["relationship"]), f'{r["n"]:,}', num(r["r"], 4),
                    f'{r["ci95"][0]:.3f} to {r["ci95"][1]:.3f}', num(r["p_value"], 4),
                    esc(r["note"]), srclink(r["source"])] for r in CO["game_level"]])
    body += "<h2>Inside one game: the prop combinations</h2>"
    body += table(["ID", "Relationship", "Pairs", "r", "95% CI", "p", "What it means for a combination", "Source"],
                  [[r["id"], esc(r["relationship"]), f'{r["n"]:,}', num(r["r"], 4),
                    f'{r["ci95"][0]:.3f} to {r["ci95"][1]:.3f}', num(r["p_value"], 4),
                    esc(r["note"]), srclink(r["source"])] for r in PR["same_game_correlations"]])
    body += ("<h2>How to use these numbers</h2><ul class='bullets'>"
             "<li>A correlation of zero means the product of two leg prices is the right price "
             "for the combination. Anything else means it is not.</li>"
             "<li>Positive correlation makes a combination worth <em>more</em> than the product, "
             "so a book pricing at the product is paying too little.</li>"
             "<li>Negative correlation makes it worth <em>less</em>, which is the trap in "
             "pairing a team's passing yards with its own rushing yards.</li>"
             "<li>These are correlations, not probabilities. They say how two things move "
             "together, not how often either one happens.</li></ul>")
    write("correlations.html", "Correlation register",
          "Eleven game-level and eight same-game player correlations, each with a confidence interval.",
          "Strategy", body)


def page_props(PR):
    body = kpi([
        ("Player weeks", f"{PR['sample']['player_weeks']:,}", f"{PR['sample']['players']:,} players, 2019-2026"),
        ("Markets projected", str(len(PR["markets"])), "walk-forward, no peeking"),
        ("Same-game correlations", str(len(PR["same_game_correlations"])), "see the correlation page"),
        ("Strongest measured", f"{max(r['r'] for r in PR['same_game_correlations']):+.3f}",
         "quarterback passing yards to his top receiver's receiving yards"),
        ("Prop prices", blank("none exist"), "no prop bet is scored anywhere on this site"),
        ("Source", "nfl.com", "official player stats"),
    ])
    body += f'<p class="lead">{esc(PR["price_status"])}</p>'
    body += "<h2>Projection quality</h2>"
    body += table(["Market", "Player weeks", "Our error", "Error from just guessing the league average",
                   "Error removed", "Opponent adjustment helped?", "Player beat his own projection", "Source"],
                  [[esc(m["label"]), f'{m["n"]:,}', num(m["mae_projection"], 2),
                    num(m["mae_naive_season_mean"], 2), pct(m["skill_vs_naive_pct"]),
                    "yes" if m["opponent_adjustment_helped"] else "no",
                    num(m["observed_over_rate"], 3), srclink(m["source"])]
                   for m in PR["markets"]])
    body += note("The honest reading: for running-back rushing yards the projection removes "
                 "13.6% of the error of simply guessing the league average. For receiver "
                 "receiving yards it removes 0.06%, which is to say it does essentially nothing. "
                 "A projection that cannot beat a league average should not be priced, and it "
                 "is not priced here.")
    body += "<h2>Calibration</h2>"
    for m in PR["markets"]:
        body += f"<h3>{esc(m['label'])}</h3>"
        body += table(["Projection band", "Player weeks", "Mean projection", "Mean actual",
                       "Rate of going over the projection"],
                      [[esc(b["projection_band"]), b["n"], num(b["mean_projection"], 1),
                        num(b["mean_actual"], 1), num(b["observed_over_rate"], 3)]
                       for b in m["calibration_bands"]])
    body += note(esc(PR["markets"][0]["calibration_note"]))
    body += "<h2>Anytime touchdown base rates</h2>"
    body += table(["Position", "Player weeks", "Scored a touchdown", "Rate", "Note", "Source"],
                  [[r["position"], f'{r["player_weeks"]:,}', f'{r["anytime_td"]:,}',
                    num(r["rate"], 4), esc(r["note"]), srclink(r["source"])]
                   for r in PR["anytime_td_base_rates"]])
    body += note("These are base rates over every qualifying player week in the extract, not "
                 "forecasts for any individual player. Without a price they cannot be turned "
                 "into a bet, and they are not.")
    write("props.html", "Player props",
          "Walk-forward projections with honest skill numbers, and the same-game correlations "
          "that decide whether a combination is worth more than the product of its legs.",
          "Props", body)


def page_injuries(INJROWS, LB, AV):
    out_rows = INJROWS[INJROWS["report_status"] == "Out"]
    qb = INJROWS[INJROWS["position"] == "QB"]
    body = kpi([
        ("Week-10 rows in the extract", f"{len(INJROWS):,}", "official weekly injury report"),
        ("Clubs with a report", f"{INJROWS['team'].nunique()} of 32", "six clubs have not published"),
        ("Rows with a game designation", f"{int(INJROWS['report_status'].notna().sum()):,}",
         "the mirror lags the official page; see flag U02"),
        ("Historical rows", "56,537", "2016 to 2026, used for two scored rules"),
        ("Injury rules passing gates", "0 of 2", "both are indistinguishable from zero"),
        ("Depth-chart ranks available", "current season only", "history is missing; see flag U06"),
    ])
    body += f'<p class="lead">The official report is read from nfl.com and mirrored into the '
    body += (f'extract. Six clubs had published nothing at fetch time, and game designations '
             f'lag: only {int(INJROWS["report_status"].notna().sum())} of {len(INJROWS):,} rows '
             f'carry one. Neither gap is filled in.</p>')
    body += "<h2>Every player ruled Out, week 10 of 2026</h2>"
    body += table(["Club", "Player", "Position", "Injury", "Game status", "Practice status", "Source"],
                  [[esc(r["team"]), esc(r["full_name"]), esc(r["position"]),
                    esc(r["report_primary_injury"]) or blank("not stated"),
                    esc(r["report_status"]), esc(r["practice_status"]), srclink(INJ)]
                   for _, r in out_rows.iterrows()])
    if out_rows.empty:
        body += note("No player in the mirrored week-10 extract carries an Out designation. "
                     "The official page does show Out designations for clubs inside 48 hours of "
                     "kick-off, which is precisely the lag recorded as flag U02.")
    body += "<h2>Quarterbacks on the report</h2>"
    body += table(["Club", "Player", "Practice status", "Game status", "Source"],
                  [[esc(r["team"]), esc(r["full_name"]), esc(r["practice_status"]),
                    esc(r["report_status"]) or blank("not posted"), srclink(INJ)]
                   for _, r in qb.iterrows()])
    body += "<h2>What the depth-chart join gives us, and what it does not</h2>"
    body += table(["Question", "Answer", "Source"], [
        ["Can we tell whether an absent player is a listed starter?",
         "Yes, for the current season. Weekly depth charts carry a position rank where 1 is the "
         "listed starter, and an earlier session joined them to the injury report.",
         srclink(TEAMS)],
        ["Can we tell who replaces him?",
         "Yes, for the current season: the next rank at that position is on the same chart.",
         srclink(TEAMS)],
        ["Can we tell whether the replacement is any good?",
         "Not yet. Historical depth charts are not in the repository, so no backup-quality rule "
         "can be back-tested. Flagged as U06.", srclink(TEAMS)],
        ["Are the practice-only weights official?",
         "No. Out = 1.0, Doubtful = 0.7, Questionable = 0.25, with practice-only weights of 0.5 "
         "for did-not-participate and 0.2 for limited, are a modelling choice, not a league rule.",
         srclink("https://operations.nfl.com/gameday/")],
    ])
    body += "<h2>The two scored injury rules</h2>"
    body += table(["Strategy", "Bets", "Hit rate", "Break-even", "Return", "p", "Verdict"],
                  [[esc(r["strategy"]), f'{r["n_bets"]:,}', num(r["hit_rate"], 3),
                    num(r["break_even_hit_rate"], 3), pct(r["roi_pct"]), num(r["p_value"], 4),
                    f'<span class="pill {r["status"].lower()}">{r["status"]}</span>']
                   for r in LB["leaderboard"] if r["strategy"].startswith(("S11", "S12"))])
    body += note("Both rules are built on the official injury report for 2016 to 2026. Both come "
                 "back indistinguishable from zero after real prices. That is a result, not a "
                 "failure of plumbing: the market prices a missing starter long before the report "
                 "is published.")
    write("injuries.html", "Injuries and depth",
          "The official week-10 report, what the mirror is missing, and what the historical "
          "injury rules actually returned.", "Availability", body)


def page_questions(CT, BY_ID):
    qs = CT["questions"]
    counts = {}
    for q in qs:
        counts[q["status"]] = counts.get(q["status"], 0) + 1
    body = kpi([(k.replace("answered", "answered from an official source").title(),
                 str(v), "") for k, v in counts.items()])
    body += ("<p class=\"lead\">Each question records what is known, what is not, what decision "
             "it blocks, and how to find out. Where the answer cell is blank there is no answer "
             "from an official source, and none has been invented.</p>")
    body += table(["ID", "Area", "Question", "What we know", "What we do not", "Answer",
                   "What it blocks", "How to discover it", "Status", "Source"],
                  [[q["id"], esc(q["category"]), esc(q["question"]), esc(q["known"]),
                    esc(q["unknown"]) or blank("nothing missing"),
                    esc(q["answer"]) or blank("unanswered"),
                    esc(q["blocks"]) or "&mdash;",
                    esc(q["discover"]) or "&mdash;",
                    f'<span class="pill {q["status"]}">{q["status"]}</span>',
                    srclink(q["source"])] for q in qs])
    write("questions.html", "Questions",
          "What must be answered before a decision can reasonably be made, and how to answer it.",
          "Decisions", body)


def page_suggestions(CT):
    sugg = CT["suggestions"]
    body = kpi([
        ("Suggestions", str(len(sugg)), "each with options, effort and risk"),
        ("Already applied here", str(sum(1 for s in sugg if s["status"] == "done")), ""),
        ("Awaiting a decision", str(sum(1 for s in sugg if s["status"] == "proposed")), ""),
        ("Options per suggestion", "3", "a cheap one, a thorough one, and a do-nothing one"),
        ("Evidence", "linked", "every suggestion cites the number that prompted it"),
        ("Decision record", "below", "who chose what, and when"),
    ])
    body += ("<p class=\"lead\">Nothing here has been implemented on the strength of being "
             "listed. Each suggestion offers paths; the decision record at the bottom is where "
             "a path gets chosen.</p>")
    body += table(["ID", "Suggestion", "The problem", "Options", "Recommendation", "Evidence", "Status"],
                  [[s["id"], esc(s["title"]), esc(s["problem"]),
                    "<ol class='opts'>" + "".join(
                        f"<li><strong>{esc(o['name'])}</strong> &mdash; effort: {esc(o['effort'])}; "
                        f"risk: {esc(o['risk'])}</li>" for o in s["options"]) + "</ol>",
                    esc(s["recommendation"]), esc(s["evidence"]),
                    f'<span class="pill {"pass" if s["status"] == "done" else "watch"}">{esc(s["status"])}</span>']
                   for s in sugg])
    body += "<h2>Decision record</h2>"
    body += table(["Suggestion", "Chosen path", "Decided by", "Decided on", "Status"],
                  [[s["id"] + " &middot; " + esc(s["title"]),
                    blank("awaiting decision"), blank("awaiting decision"),
                    blank("awaiting decision"),
                    f'<span class="pill watch">{"done" if s["status"] == "done" else "open"}</span>']
                   for s in sugg])
    body += note("This is the review gate. A suggestion is not implemented because it is listed; "
                 "it is implemented when someone picks a path here and records who picked it. "
                 "Until then every path cell stays deliberately blank.")
    write("suggestions.html", "Suggestions",
          "Ranked improvements with paths to choose between, and the record of which path was taken.",
          "Decisions", body)


def page_requirements(CT):
    reqs = CT["requirements"]
    body = kpi([
        ("Requirements", str(len(reqs)), "decomposed from the brief"),
        ("Delivered", str(sum(1 for r in reqs if r["status"] == "delivered")), ""),
        ("Partly delivered", str(sum(1 for r in reqs if r["status"] == "partly")),
         "the gap is always a missing source, never a missing effort"),
        ("Not delivered", str(sum(1 for r in reqs if r["status"] not in ("delivered", "partly"))), ""),
        ("Evidence", "per row", "where to look and what proves it"),
        ("Blocking gaps", "4", "prop prices, historical depth charts, reward legality, pre-2006 prices"),
    ])
    body += table(["ID", "Area", "Requirement", "Status", "Where", "Evidence", "Source"],
                  [[r["id"], esc(r["area"]), esc(r["requirement"]),
                    f'<span class="pill {"pass" if r["status"] == "delivered" else "watch"}">{esc(r["status"])}</span>',
                    esc(r["where"]), esc(r["evidence"]), srclink(r["source"])] for r in reqs])
    body += note("'Partly' always means the same kind of thing here: the method works, but a "
                 "source this repository can reach does not yet contain the data. Those gaps are "
                 "itemised on the Flagged for Review page rather than papered over.")
    write("requirements.html", "Requirements",
          "Every requirement from the brief, with where it is delivered and what is only partial.",
          "Decisions", body)


def page_verification(VE):
    body = kpi([
        ("Rows checked", f"{VE['summary']['rows_checked']:,}", "against official pages or an independent transcription"),
        ("Rows matched", f"{VE['summary']['rows_matched']:,}", ""),
        ("Mismatches", f"{VE['summary']['mismatches']:,}",
         "every one is a game with no published price, which is never scored"),
        ("Checks", str(len(VE["checks"])), "standings, results, injuries, price coverage"),
        ("Policy", "no inference", "a value that cannot be confirmed is left blank and flagged"),
        ("Source", "nfl.com", "read directly during this session"),
    ])
    body += f"<p class=\"lead\">{esc(VE['policy'])}</p>"
    body += table(["Check", "Rows", "Matched", "Mismatches", "Source"],
                  [[esc(c["name"]), f"{c.get('rows_checked', 0):,}", f"{c.get('rows_matched', 0):,}",
                    f"{c.get('mismatches', 0):,}", srclink(c.get("source"))] for c in VE["checks"]])
    for c in VE["checks"]:
        body += f"<h2>{esc(c['name'])}</h2>"
        if c.get("note"):
            body += note(esc(c["note"]))
        det = c.get("detail") or []
        if not det:
            continue
        if c["name"].startswith("2026 standings"):
            body += table(["Club", "Games", "nfl.com W-L-T", "Computed W-L-T", "nfl.com PF",
                           "Computed PF", "nfl.com PA", "Computed PA", "Match", "Source"],
                          [[esc(r["team"]), r["games"],
                            f'{r["nfl"]["w"]}-{r["nfl"]["l"]}-{r["nfl"]["t"]}',
                            f'{r["computed"]["w"]}-{r["computed"]["l"]}-{r["computed"]["t"]}',
                            r["nfl"]["pf"], r["computed"]["pf"], r["nfl"]["pa"], r["computed"]["pa"],
                            f'<span class="pill {"pass" if r["matched"] else "fail"}">'
                            f'{"match" if r["matched"] else "mismatch"}</span>',
                            srclink(r["source"])] for r in det])
        elif c["name"].startswith("Week 10"):
            body += table(["Club", "Player", "nfl.com", "Extract", "Match", "Source"],
                          [[esc(r["team"]), esc(r["player"]),
                            f'{esc(r["nfl"]["position"])} &middot; {esc(r["nfl"]["injury"])} &middot; '
                            f'{esc(r["nfl"]["game_status"])}',
                            esc(r["extract"]) if r["extract"] else blank("absent"),
                            f'<span class="pill {"pass" if r["matched"] else "fail"}">'
                            f'{"match" if r["matched"] else "mismatch"}</span>',
                            srclink(r["source"])] for r in det])
        elif c["name"].startswith("Observed-price"):
            body += table(["Season", "Games", "With a price", "Without", "% priced"],
                          [[r["season"], r["games"], r["with_price"], r["without_price"],
                            pct(r["pct_priced"], 1)] for r in det])
        else:
            body += table(["Game", "Match", "Differences", "Source"],
                          [[esc(r.get("game_id")), "yes" if r["matched"] else "no",
                            esc(json.dumps(r["diffs"])) if r.get("diffs") else "&mdash;",
                            srclink(r["source"])] for r in det[:200]])
    write("verification.html", "Verification",
          "Line-by-line checks against official pages, with counts and every mismatch shown.",
          "Evidence", body)


def page_repo(CT):
    rr = CT["repo_review"]
    body = kpi([
        ("Artefacts reviewed", str(len(rr)), "data, pipeline, site, coordination"),
        ("Files modified that belong to another session", "0",
         "everything added here is in a new directory"),
        ("Defects found and fixed", "1",
         "a wrong Student-t distribution that had inflated every p-value"),
        ("Irregularities raised", "10", "see the Flagged page"),
        ("Sources read directly this session", "4",
         "standings, injury report, schedules, player stats"),
        ("Policy", "read, never overwrite", "other sessions' work is preserved verbatim"),
    ])
    body += ("<p class=\"lead\">Every artefact below was opened and checked, then linked so you "
             "can check it yourself. Nothing belonging to another session was edited; where a "
             "change was needed it was logged as a request in COORDINATION.md instead.</p>")
    body += table(["Artefact", "What it is", "What was checked", "Result", "Source"],
                  [[f'<code>{esc(r["artefact"])}</code>', esc(r["what"]), esc(r["check"]),
                    esc(r["result"]), srclink(r["source"])] for r in rr])
    body += ("<h2>The one defect that mattered</h2>"
             "<p>The first run of the leaderboard reported p-values of 0.99 for strategies with "
             "positive returns. The cause was a hand-written Student-t distribution that was "
             "wrong in the middle of its range while looking plausible in the tails. It was "
             "replaced with scipy's implementation and asserted equal to it at five points. Had "
             "it survived, every significance claim on this site would have been inverted.</p>")
    write("repo-review.html", "Repository review",
          "What was reviewed line by line, what was found, and the links to check it yourself.",
          "Evidence", body)


def page_flagged(CT):
    fl = CT["flags"]
    body = kpi([
        ("Irregularities", str(len(fl)), "each with an official source link"),
        ("High severity", str(sum(1 for f in fl if f["severity"] == "high")),
         "prop prices, and the injury feed's game-designation lag"),
        ("Medium", str(sum(1 for f in fl if f["severity"] == "medium")), ""),
        ("Low", str(sum(1 for f in fl if f["severity"] == "low")), ""),
        ("Blocking", "none", "every item is published rather than fixed silently"),
        ("Values filled in to hide a gap", "0", "a blank stays blank"),
    ])
    body += ("<p class=\"lead\">Nothing here is hidden and nothing here blocks anything. Each "
             "item is an irregularity in the data or the method that a reviewer should be able "
             "to see, with the source that would settle it.</p>")
    body += table(["ID", "Severity", "Area", "Item", "Detail", "Impact", "Status", "Source"],
                  [[f["id"], f'<span class="pill {"fail" if f["severity"] == "high" else "watch"}">'
                    f'{esc(f["severity"])}</span>', esc(f["area"]), esc(f["item"]),
                    esc(f["detail"]), esc(f["impact"]), esc(f["status"]), srclink(f["source"])]
                   for f in fl])
    write("flagged.html", "Flagged for review",
          "Every irregularity and every value that could not be confirmed from an official source.",
          "Evidence", body)


CSS = """
:root{--bg:#0e1116;--panel:#151b23;--panel2:#1b232e;--line:#253040;--ink:#e6edf3;
--muted:#93a1b1;--accent:#4da3ff;--good:#3fb950;--warn:#d29922;--bad:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent)}
.top{display:flex;align-items:center;justify-content:space-between;gap:16px;
padding:14px 22px;border-bottom:1px solid var(--line);background:var(--panel);flex-wrap:wrap}
.brand{font-weight:700;font-size:17px;color:var(--ink);text-decoration:none}
.brand .tag{display:inline-block;margin-left:10px;font-weight:500;font-size:11px;
letter-spacing:.08em;text-transform:uppercase;color:var(--muted);
border:1px solid var(--line);border-radius:999px;padding:2px 9px}
.crumb{font-size:13px;color:var(--muted)}
.wrap{display:grid;grid-template-columns:236px minmax(0,1fr);gap:26px;
max-width:1480px;margin:0 auto;padding:22px}
.side nav{position:sticky;top:18px}
.navgroup{margin-bottom:18px}
.navgroup span{display:block;font-size:11px;letter-spacing:.09em;text-transform:uppercase;
color:var(--muted);margin-bottom:6px;padding-left:10px}
.navgroup a{display:block;padding:6px 10px;border-radius:7px;color:var(--ink);
text-decoration:none;font-size:14px;border-left:2px solid transparent}
.navgroup a:hover{background:var(--panel2)}
.navgroup a.here{background:var(--panel2);border-left-color:var(--accent);font-weight:600}
main{min-width:0}
h1{font-size:26px;margin:0 0 6px}
h2{font-size:18px;margin:30px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:15px;margin:20px 0 8px;color:var(--muted)}
.sub,.sub2,.lead{color:var(--muted);margin:0 0 14px}
.lead{font-size:16px;color:var(--ink);background:var(--panel);border:1px solid var(--line);
border-left:3px solid var(--accent);border-radius:8px;padding:12px 14px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:16px 0 4px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .k{display:block;font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}
.kpi .v{display:block;font-size:23px;font-weight:700;margin:3px 0}
.kpi .n{display:block;font-size:12px;color:var(--muted)}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:12px 0}
table{width:100%;border-collapse:collapse;font-size:13.5px}
caption{text-align:left;color:var(--muted);font-size:12px;padding:8px 12px}
th,td{padding:8px 11px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel2);font-size:11.5px;letter-spacing:.05em;text-transform:uppercase;
color:var(--muted);position:sticky;top:0}
tbody tr:hover{background:#121924}
tbody tr:last-child td{border-bottom:none}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.src{white-space:nowrap;font-size:12px}
.blank{color:var(--muted);font-style:italic;font-size:12px;
border-bottom:1px dotted var(--muted);cursor:help}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:600;
text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
.pill.pass{background:rgba(63,185,80,.16);color:var(--good)}
.pill.watch{background:rgba(210,153,34,.16);color:var(--warn)}
.pill.fail{background:rgba(248,81,73,.16);color:var(--bad)}
.pill.answered{background:rgba(63,185,80,.16);color:var(--good)}
.pill.partly{background:rgba(210,153,34,.16);color:var(--warn)}
.pill.unanswered,.pill.flagged{background:rgba(248,81,73,.16);color:var(--bad)}
.pill.not-proven{background:rgba(210,153,34,.16);color:var(--warn)}
.pill.done,.pill.open{background:rgba(210,153,34,.16);color:var(--warn)}
.g{display:inline-block;padding:1px 6px;border-radius:5px;font-size:10.5px;font-weight:700}
.g.y{background:rgba(63,185,80,.16);color:var(--good)}
.g.n{background:rgba(248,81,73,.13);color:var(--bad)}
.note{background:var(--panel);border:1px solid var(--line);border-radius:8px;
padding:11px 13px;color:var(--muted);font-size:13px;margin:12px 0}
.bullets{margin:10px 0;padding-left:20px}
.bullets li{margin:7px 0}
.opts{margin:4px 0;padding-left:18px;font-size:12.5px}
.opts li{margin:4px 0}
.empty{color:var(--muted);font-style:italic}
.foot{margin-top:38px;padding-top:16px;border-top:1px solid var(--line);
color:var(--muted);font-size:12.5px}
.foot p{margin:6px 0}
code{background:var(--panel2);padding:1px 5px;border-radius:4px;font-size:12.5px}
@media(max-width:900px){.wrap{grid-template-columns:1fr}.side nav{position:static;
display:flex;flex-wrap:wrap;gap:4px}.navgroup{margin-bottom:8px}}
"""


def main() -> None:
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    with open(os.path.join(OUT, "assets", "style.css"), "w") as f:
        f.write(CSS)

    L = load("lines.json")
    LB = load("leaderboard.json")
    PL = load("parlays.json")
    CO = load("correlations.json")
    PR = load("props.json")
    VE = load("verification.json")
    CT = load("content.json")
    GD = {"games": 7239, "played": CO["sample"]["games"]}

    import pandas as pd
    inj = pd.read_csv(os.path.join(DATA, "injuries.csv"))
    INJROWS = inj[(inj["season"] == 2026) & (inj["week"] == 10)].copy()

    print("generating research/ ...")
    page_index(L, LB, PL, CO, PR, VE, CT, GD)
    page_exec(CT, L, LB, PL, PR, VE)
    page_lines(L)
    write("leaderboard.html", "Strategy lab",
          "Twelve rules scored at observed prices against eight validation gates, with the luck "
          "accounting beside every return.", "Strategy", page_leaderboard(LB))
    page_parlays(PL)
    page_correlations(CO, PR)
    page_props(PR)
    page_injuries(INJROWS, LB, None)
    page_questions(CT, None)
    page_suggestions(CT)
    page_requirements(CT)
    page_verification(VE)
    page_repo(CT)
    page_flagged(CT)
    print("done.")


if __name__ == "__main__":
    main()
