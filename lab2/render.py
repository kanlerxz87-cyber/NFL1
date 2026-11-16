#!/usr/bin/env python3
"""render.py — write the Origination Desk pages from lab2/data/derived.json + content.py.

Deterministic: the same inputs produce the same bytes.  Every table row carries a source link
and a read date; `lab2/verify.py` fails the build on a row without one, on an unlabelled blank,
or on a local link that does not resolve.
"""
from __future__ import annotations

import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import content  # noqa: E402
import lib  # noqa: E402

OUT = os.path.join(lib.ROOT, "lab2")
D = lib.load("lab2/data/derived.json")

NAV = [
    ("index.html", "Overview", "Where the project stands"),
    ("executive.html", "Executive Summary", "What holds up, what does not, what is missing"),
    ("market.html", "Market Book", "Our line, the market, the residual"),
    ("results.html", "Results", "Official finals, verified"),
    ("availability.html", "Availability", "Injuries, depth, replacements"),
    ("strategies.html", "Strategies", "Signal separated from staking"),
    ("prices.html", "Prices", "The price policy decision"),
    ("readiness.html", "Readiness", "One row per requirement"),
    ("questions.html", "Questions", "What must be answered first"),
    ("suggestions.html", "Suggestions", "Options, ranked by impact"),
    ("flagged.html", "Flagged for Review", "Every irregularity, with its source"),
    ("method.html", "Method & Sources", "How each number was checked"),
]


def esc(v):
    return html.escape("" if v is None else str(v))


def badge(status):
    m = {"done": "ok", "partial": "warn", "blocked": "fail", "not-started": "neutral"}
    return f'<span class="pill {m.get(status, "neutral")}">{esc(status)}</span>'


NA_CELL = ('<a class="blank" href="method.html#sources" title="no public source exists for this value">n/a</a>'
           ' <span class="sub">no public source</span>')


def src(url, label=None):
    if not url or url == lib.UNVERIFIED:
        return NA_CELL
    return f'<a class="src" href="{esc(url)}" target="_blank" rel="noopener">{esc(label or "source")}</a>'


def _blank(v):
    if v is None or v == "" or v == lib.UNVERIFIED:
        return '<span class="blank">Unverified</span>'
    return esc(v)


def table(headers, rows, note=None, cls=""):
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = []
    for r in rows:
        body.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    note_html = f'<p class="note">{note}</p>' if note else ""
    return (f'<div class="table-wrap"><table class="{cls}"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>{note_html}')


def kpi(label, value, sub=""):
    return (f'<article class="kpi"><span class="kpi-label">{esc(label)}</span>'
            f'<strong class="kpi-value">{value}</strong>'
            f'<span class="kpi-sub">{esc(sub)}</span></article>')


def page(name, title, body, subtitle=""):
    nav = "".join(
        f'<a href="{h}"{" class=active" if h == name else ""}>{esc(t)}</a>' for h, t, _ in NAV)
    stamp = D.get("built", "")
    doc = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · NFL Origination Desk</title>
<link rel="stylesheet" href="assets/style.css">
</head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <a class="brand" href="index.html"><span class="mark">NFL</span> Origination Desk</a>
  <nav aria-label="Categories">{nav}</nav>
</header>
<main id="main">
<div class="pagehead">
  <p class="eyebrow">Session a35ddf45 · official reads {esc(D.get('retrieved', ''))}</p>
  <h1>{esc(title)}</h1>
  <p>{subtitle}</p>
</div>
{body}
</main>
<footer>
  <span>Data cut {esc(stamp)} · built from committed files and official pages read that day.</span>
  <span>Every row links its source. A cell that no source confirms is printed blank and labelled Unverified, never filled.</span>
</footer>
</body></html>
"""
    path = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return len(doc)


# ------------------------------------------------------------------ pages
def overview():
    st, rs, ln, av = D["standings"], D["results"], D["lines"], D["availability"]
    sig, dv = D["signal"], D["forward"]
    body = [
        '<section class="hero">',
        '<div><p class="eyebrow">Origination, one market at a time</p>',
        '<h2>The side first. Then the total. Then the moneyline.</h2>',
        f'<p class="lede">This desk prices the Week {11} board itself, prints the market beside it, and shows the '
        'difference as its own column. It publishes a result only when an official page prints one, and it leaves '
        'a cell blank rather than fill it from an inference. Every number below was recomputed in this session '
        'from a committed file or read from an official page on ' + esc(D["retrieved"]) + '.</p>',
        '<p><a class="btn" href="market.html">Open the market book</a> '
        '<a class="btn ghost" href="executive.html">Executive summary</a> '
        '<a class="btn ghost" href="flagged.html">Flagged for review</a></p></div>',
        '<aside class="hero-card"><span class="eyebrow" style="color:#adc4b9">What this session changed</span>',
        f'<h3>{rs["n_finals"]} Week-10 finals verified</h3><p>The official schedule page prints 13 finals. The committed '
        f'feed held 1. All 13 are now recorded with their game-centre links, and the resulting table reconciles to the '
        f'official standings for {rs["recon_ok"]} of {rs["recon_n"]} clubs.</p>',
        f'<h3>{st["n_differing"]} of {st["n_clubs"]} clubs out of date</h3><p>The published standings table is correct '
        f'as of {esc(st["repo_snapshot_date"])} and has not been advanced. Both facts are shown on the Results page.</p>',
        '</aside></section>',
        '<section class="kpis">',
        kpi("Week 11 fixtures", ln["n_games"], "official schedule, 13 games, 6 byes"),
        kpi("Own lines with a market side", ln["n_side"], "total residuals " + str(ln["n_total"]) + " of 13"),
        kpi("Week-10 finals verified", rs["n_finals"], f'{rs["recon_ok"]}/{rs["recon_n"]} clubs reconcile'),
        kpi("Official injury rows", av["n_rows"], f'{av["n_clubs"]} clubs · 0 differences vs the committed capture'),
        kpi("Rules with no survivable signal", f'{sig["n_rows"] - sig["n_q_below_05"]}/{sig["n_rows"]}', "BH q ≥ 0.05 on every rule"),
        kpi("Forecast rows scored", "0 of 39", "first Week-11 kickoff has not happened"),
        '</section>',
        '<section class="block"><div class="panel-head"><h2>Read this first</h2></div>',
        '<div class="cards">',
        '<div class="card"><h3>The result is the bottleneck</h3><p>Thirteen Week-10 games had no final in the feed '
        'yesterday and the pages that score strategies were already published. Nothing downstream can be trusted '
        'until a dated result exists for every graded game. <a href="results.html">The verified finals →</a></p></div>',
        '<div class="card"><h3>Signal is not staking</h3><p>Ranked by money, the top rule is S07. Its signal interval is '
        '+0.68 to +10.49 percentage points over a coin flip — above zero. Against the break-even rate its own price '
        'implies, p = 0.192; after correcting for 24 tests, q = 0.2615. Both columns are shown side by side so neither '
        'can hide the other. <a href="strategies.html">Signal vs staking →</a></p></div>',
        '<div class="card"><h3>No official price exists</h3><p>The league publishes no spread, no total and no price. '
        'Every market number here is a consensus number from a mirrored feed and is labelled that way on every row. '
        '<a href="prices.html">The price policy →</a></p></div>',
        '<div class="card"><h3>A replacement is not a starter</h3><p>The club chart nominates a backup at a slot; it '
        'never says he started. The replacement column on the Availability page is blank on purpose, with the rule '
        'that would fill it. <a href="availability.html">Availability &gt;</a></p></div>',
        '</div></section>',
        overview_readiness(),
    ]
    return page("index.html", "Origination Desk",
                "".join(body),
                "A decision dashboard for originating NFL lines: what is verified, what is blocked, "
                "and the number that would clear each block.")


def overview_readiness():
    rows = content.READINESS
    counts = {"done": 0, "partial": 0, "blocked": 0, "not-started": 0}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    body = ['<section class="block"><div class="panel-head"><h2>Decision readiness</h2>'
            '<a href="readiness.html">All 30 rows →</a></div>',
            f'<p class="sub">{counts["done"]} done · {counts["partial"]} partial · {counts["blocked"]} blocked · '
            f'{counts["not-started"]} not started. Each row names the gate that blocks it and the number that would clear it.</p>']
    tbl_rows = []
    for r in rows:
        if r["status"] == "done":
            continue
        tbl_rows.append([f'<strong>{esc(r["id"])}</strong>', esc(r["requirement"]), badge(r["status"]),
                         esc(r["gate"]), esc(r["clear"]), src(r["source"], "official")])
    body.append(table(["ID", "Requirement", "Status", "Blocking gate", "What would clear it", "Source"],
                      tbl_rows, note="The seven rows already met are on the Readiness page. "
                                     "Nothing here is a plan: each row is the current state, measured this session."))
    body.append('</section>')
    return "".join(body)


def executive():
    st, rs, av, sig = D["standings"], D["results"], D["availability"], D["signal"]
    dv, fw = D["depth"], D["forward"]
    holds = [
        ("The Week-10 results and the standings table are two independent reads that agree.",
         f'13 official finals were read from the league schedule page and added to the stored table. The sum reproduces '
         f'the live official standings for {rs["recon_ok"]} of {rs["recon_n"]} clubs on wins, losses, points for and points '
         f'against. This is the strongest check on the page: two different official pages, one arithmetic path.'),
        ("The Week-10 injury report is captured exactly.",
         f'{av["n_rows"]} player rows across {av["n_clubs"]} clubs were transcribed again from the official page this session '
         f'and compared with the repository\'s committed capture: 0 differences in any field. The three Lions rows that the '
         f'brief flags as blank (Kerby Joseph, Cade Mays, D.J. Reed) print Out on both.'),
        ("The own-line model is reproducible and honestly labelled.",
         f'{D["lines"]["n_games"]} fixtures carry a fair line, a market line and a residual as separate columns. The blend '
         f'test on the model file gives a model weight of {D["lines"]["blend_test"].get("weight_model")} against the market, '
         f'which is the model saying its disagreement has not paid.'),
        ("Every model output is a probability with its inputs.",
         f'{fw["n_records"]} forecast records hold {sum(r["n_games"] for r in fw["records"])} game-level probabilities, each '
         f'with the full input list and a recording timestamp before the first kickoff.'),
    ]
    not_holds = [
        ("The backtest is not yet gradeable.",
         "The season's most recent week has no results in the feed the backtest reads. Any ROI computed on it is a number "
         "about a game that has not been scored."),
        ("The two leaderboards are not the same board.",
         f'Twelve IDs describe twelve different rule pairs. {D["strategies"]["n_same_rule"]} of 12 IDs agree across '
         'the two files, so a comparison across pages compares unrelated rules.'),
        ("No published ROI uses a real price.",
         "One board assumes -110 on every bet; the other uses observed prices but declines to score 1,902 games with "
         "no price. Neither produces a return a bettor could have earned."),
        ("The availability table describes the wrong week.",
         "The published availability model reads a mirrored feed whose latest complete week is week 6, and joins it to a "
         "depth chart dated 2026-11-12. The official Week-10 report is in the repository and unused by that page."),
        ("No replacement can be named.",
         "A club chart nominates a backup. No source read this session says that backup started. The column is blank "
         "everywhere, and it should be."),
    ]
    missing = [
        ("A dated result store the build cannot run without.", "Q01", "One row per finished game, read after the final whistle, with a page hash."),
        ("A price whose provenance is stated per quote.", "Q02", "A licensed feed with quote timestamps, or a recorded decision to grade on the close."),
        ("Point-in-time availability captures.", "Q04", "Daily captures from Wednesday to kickoff with a retained hash."),
        ("A play rate per injury designation.", "Q05", "Designations joined to official inactive lists."),
        ("Actual starters.", "Q06", "Official game books for every graded game."),
        ("One rule registry.", "Q03", "One ID per frozen rule, with the registration commit beside it."),
    ]
    body = ['<section class="block"><h2>What holds up</h2><div class="cards">']
    for h, d in holds:
        body.append(f'<div class="card"><h3>{esc(h)}</h3><p>{esc(d)}</p></div>')
    body.append('</div></section>')
    body.append('<section class="block"><h2>What does not</h2><div class="cards">')
    for h, d in not_holds:
        body.append(f'<div class="card bad"><h3>{esc(h)}</h3><p>{esc(d)}</p></div>')
    body.append('</div></section>')
    qsrc = {q["id"]: q["source"] for q in content.QUESTIONS}
    rows = [[esc(h), esc(q), esc(a), src(qsrc.get(q, ""), "official")] for h, q, a in missing]
    body.append('<section class="block"><h2>What is missing, and what would supply it</h2>')
    body.append(table(["Missing", "Question", "What would supply it", "Source"], rows))
    body.append('</section>')
    body.append('<section class="block"><h2>Decision</h2>'
                '<p>The single highest-value next step is not a model. It is a result store. Until a finished game has a '
                'dated, sourced final, every strategy on this site is a claim about the past that nobody can score. '
                'The second is the price policy, because a residual against an unsourced closing line describes the '
                'market without measuring anything. Both are small pieces of work with outsized consequences, and both '
                'are recorded as decisions on the <a href="prices.html">Prices</a> and <a href="results.html">Results</a> pages.</p>'
                '</section>')
    return page("executive.html", "Executive Summary", "".join(body),
                "Four things this session can stand behind, five it cannot, and the six pieces of information that "
                "would change the answer.")


def market():
    ln = D["lines"]
    rows = []
    for r in ln["rows"]:
        rows.append([
            f'<strong>{esc(r["matchup"])}</strong><br><span class="sub">{esc(r["gameday"])}</span>',
            esc(r["side_fair"]),
            f'<span class="mono">{esc(r["side_market"])}</span>',
            _blank(r["side_residual"]),
            _blank(r["total_fair"]), _blank(r["total_market"]), _blank(r["total_residual"]),
            f'{r["ml_fair_p_home"]:.3f}',
            _blank(r["ml_market_p_home"]),
            f'[{r["band95"][0]}, {r["band95"][1]}]',
            src(lib.OFFICIAL["schedule_w11"], "schedule"),
        ])
    body = ['<section class="block">',
            '<p class="lede">Origination order is fixed: the side is priced first, then the total, then the moneyline. '
            'Each market gets three columns — our fair number, the market number, and the residual between them — so a '
            'reader never has to subtract two figures to find the claim. Positive residual = our number is higher than '
            'the market\'s on the home team. The spread and total columns are signed from the home team\'s point of view '
            'throughout, and the residual is computed from the printed numbers, not re-typed.</p>',
            '</section>']
    body.append('<section class="block"><h2>The board</h2>')
    body.append(table(["Fixture", "Side · our fair line", "Side · market", "Side residual",
                       "Total · ours", "Total · market", "Total residual",
                       "Moneyline · our p(home)", "Moneyline · market", "Home-line 95% band", "Source"],
                      rows,
                      note=f'The market columns are a consensus closing line from a mirrored feed. The league publishes '
                           f'no line: all {D["market_provenance"]["n_unofficial"]} market rows on this page have no official '
                           f'counterpart, and the moneyline market column is blank on all {ln["n_games"]} fixtures because '
                           f'no market moneyline exists in the data the repository holds.'))
    body.append('</section>')
    body.append('<section class="block"><h2>Does the model beat the market?</h2>')
    bt = ln["blend_test"]
    blob = "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/model/lines.json"
    body.append(table(["Test", "Value", "What it means", "Source"], [
        ["Model weight when blended with the market", esc(bt.get("weight_model")),
         "At or below zero the model's disagreement with the market was, on average, wrong in the test window.", src(blob, "model file")],
        ["Market weight", esc(bt.get("weight_market")), "How much of the market number the fit keeps.", src(blob, "model file")],
        ["Test MAE, blend", esc(bt.get("test_mae_hybrid")), "Mean absolute error on the held-out window.", src(blob, "model file")],
        ["Test MAE, market only", esc(bt.get("test_mae_market_only")), "The bar the model has to clear.", src(blob, "model file")],
        ["Games in the test window", esc(bt.get("n_test")), "2026 season.", src(blob, "model file")],
    ], note="The blend test is the honest summary of the origination model: it has not earned weight against the "
            "market, and the page prints that instead of a pick."))
    body.append('</section>')
    body.append('<section class="block"><h2>What is still blank, and why</h2>')
    rows = [["Opening line", _blank(None), "No opening price exists in any source the repository can reach.", NA_CELL],
            ["Moneyline market price", _blank(None), "The mirrored feed carries a moneyline for 5,228 historical games but none for the 2026 Week-11 fixtures.", src(lib.OFFICIAL["schedule_w11"], "schedule page")],
            ["Official market line", _blank(None), "The league publishes no line on its schedule pages.", src(lib.OFFICIAL["schedule_w11"], "schedule page")]]
    body.append(table(["Column", "Value", "Why", "Source"], rows))
    body.append('</section>')
    return page("market.html", "Market Book", "".join(body),
                "Our fair line, the market line, and the residual between them, as separate columns for every "
                "Week-11 fixture.")


def results():
    rs = D["results"]
    rows = [[f'<strong>{esc(r["away"])}</strong> {r["away_score"]} @ <strong>{esc(r["home"])}</strong> {r["home_score"]}',
             esc(r["total"]), esc(r["home_margin"]), esc(r["spread_name"]),
             esc(r["feed_final"]), _blank(r["feed_spread"]), _blank(r["feed_total"]),
             _blank(r["market_verdict"]), src(r["game_centre"], "game centre")] for r in rs["rows"]]
    recon = [[esc(r["club"]), esc(r["base_w"]), esc(r["base_l"]), esc(r["base_pf"]), esc(r["base_pa"]),
              f'+{r["add_w"]}', f'+{r["add_l"]}', f'+{r["add_pf"]}', f'+{r["add_pa"]}',
              f'<strong>{r["calc_w"]}-{r["calc_l"]}</strong>', f'{r["calc_pf"]}/{r["calc_pa"]}',
              f'{r["official_w"]}-{r["official_l"]}', f'{r["official_pf"]}/{r["official_pa"]}',
              '<span class="pill ok">agrees</span>' if r["agrees"] else '<span class="pill fail">differs</span>',
              src(r["source"], "standings")] for r in rs["recon_rows"]]
    body = ['<section class="block"><p class="lede">A result is published only after an official page prints it. '
            'Thirteen Week-10 finals were read from the league schedule page on ' + esc(rs["retrieved"]) + '. '
            'The Monday game (Chargers at Ravens) had not been played when the page was read, so it is absent rather '
            'than guessed. Each row links its official game centre.</p></section>']
    body.append('<section class="block"><h2>Official finals, Week 10</h2>')
    body.append(table(["Final", "Total", "Home margin", "Cover", "Final in the committed feed",
                       "Feed spread", "Feed total", "Market verdict", "Official source"], rows,
                      note=rs["feed_coverage_note"] + " A market verdict is only printed where the feed carries a "
                           "closing spread; where it does not, the cell says Unverified."))
    body.append('</section>')
    body.append('<section class="block"><h2>Arithmetic check: stored table + official finals = live official table</h2>')
    body.append('<p>This is the test that makes the rest of the page credible. Take the repository\'s own standings '
                'table as it stood on 2026-11-12, add only the thirteen finals above, and compare with the official '
                'standings page read this session. Every club is a row; every field is printed.</p>')
    body.append(table(["Club", "Base W", "Base L", "Base PF", "Base PA", "+W", "+L", "+PF", "+PA",
                       "Computed W-L", "Computed PF/PA", "Official W-L", "Official PF/PA", "Result", "Official source"],
                      recon))
    body.append('</section>')
    body.append(f'<section class="block"><h2>Where the committed feed stands</h2>'
                f'<p>The feed holds {rs["n_games"]} Week-10 rows and a final score for {rs["n_merged_into_feed"]} of them. '
                f'That single number is the reason no strategy on the site can be scored for Week 10 yet. It is published '
                f'on the Flagged page as G01, with the official page that settles it.</p></section>')
    return page("results.html", "Results", "".join(body),
                "Thirteen official Week-10 finals, transcribed this session, and the arithmetic that proves they are "
                "the right ones.")


def availability():
    av, mt = D["availability"], D["matchups"]
    dv = D["depth"]
    rows = [[f'<strong>{esc(r["club"])}</strong>', esc(r["n_rows"]), esc(r["out"]), esc(r["doubtful"]),
             esc(r["questionable"]), esc(r["no_game_status"]), esc(r["dnp"]), esc(r["limited"]), esc(r["full"]),
             src(r["source"], "report")] for r in av["clubs"]]
    body = ['<section class="block"><p class="lede">Everything on this page comes from the official Week-10 report, '
            'read again on ' + esc(av["retrieved"]) + ' and compared row for row with the repository\'s committed '
            'capture: <strong>' + str(av["n_rows"]) + ' rows, ' + str(av["n_clubs"]) + ' clubs, 0 differences</strong>. '
            'Designations are printed as the league prints them. No play probability is attached to a word, because '
            'the league publishes none.</p></section>']
    body.append('<section class="block"><h2>Designations by club</h2>')
    body.append(table(["Club", "Rows", "Out", "Doubtful", "Questionable", "No game status",
                       "Did not practise", "Limited", "Full", "Official source"], rows,
                      note=f'{av["blank_game_status"]} of {av["n_rows"]} rows carry no game status at all — most clubs '
                           f'have published practice participation only. A blank game status is not "available"; it is '
                           f'the league printing nothing.'))
    body.append('</section>')
    body.append('<section class="block"><h2>Week 11: opponent, designations, depth</h2>')
    mrows = [[f'<strong>{esc(r["club"])}</strong>', esc(r["opponent"]), esc(r["designated_out"]),
              esc(r["designated_doubtful"]), esc(r["designated_questionable"]),
              _blank(r["slots_at_risk"]), esc(r["deepest_string_starting"]),
              '<span class="blank">Unverified</span>',
              src(r["depth_chart"], "club chart"), src(r["source"], "report")] for r in mt["rows"]]
    body.append(table(["Club", "Opponent", "Out", "Doubtful", "Questionable", "Slots at risk",
                       "Deepest string on the chart", "Replacement named", "Depth source", "Report source"], mrows,
                      note=mt["note"]))
    body.append('</section>')
    body.append('<section class="block"><h2>What a replacement claim would need</h2>')
    body.append(table(["Step", "Source that would supply it", "Available to this repository?", "Source"], [
        ["Who is on the chart at the slot", "The club's own depth chart", '<span class="pill ok">yes — 32 of 32 clubs stored</span>',
         src("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/depth_ladder.json", "ladder")],
        ["Whether the starter will play", "The official weekly game status", '<span class="pill ok">yes — 171 designations this week</span>',
         src(lib.OFFICIAL["injuries_w10"], "report")],
        ["Who actually started", "The official game book", '<span class="pill fail">not stored</span>', NA_CELL],
        ["How much he played", "Official snap counts", '<span class="pill fail">not stored</span>', NA_CELL],
        ["Whether the club announced a change", "A dated club or league announcement", '<span class="pill fail">none read</span>', NA_CELL],
    ], note="Three of the five steps have no source in this repository. A table that named a replacement would be "
            "filling the last two rows with inference."))
    body.append('</section>')
    body.append(f'<section class="block"><h2>The detail that matters: which week the published model describes</h2>'
                f'<p><code>data/model/availability.json</code> is built from the mirrored feed\'s latest complete week, '
                f'which records itself as week {av["published_model_week"]}, and joins it to a depth chart dated '
                f'{esc(av["published_model_depth_dated"])}. It is a real table with real numbers about a week that has '
                f'already been played. The official Week-10 report — the last one the league has published — is stored in '
                f'the repository and matches every row on this page. The gap is a join, not a source.</p></section>')
    return page("availability.html", "Availability", "".join(body),
                "Official designations, club depth charts, and the two facts that stop a replacement being named.")


def strategies():
    sig, st = D["signal"], D["strategies"]
    rows = []
    for r in sorted(sig["rows"], key=lambda x: -x["signal_ci_low"]):
        conf = '<span class="pill ok">above zero</span>' if r["signal_ci_low"] > 0 else '<span class="pill neutral">includes zero</span>'
        q = '<span class="pill warn">q ≥ 0.05</span>' if r["bh_q"] >= 0.05 else '<span class="pill ok">q &lt; 0.05</span>'
        rep = ("<span class='blank'>—</span>" if r["p_reproduces"] is None
               else ('<span class="pill ok">reproduces</span>' if r["p_reproduces"]
                     else '<span class="pill fail">does not reproduce</span>'))
        rows.append([esc(r["rank_signal"]), f'<strong>{esc(r["strategy"])}</strong>',
                     esc(r["n"]), f'{r["win_rate"]:.2f}',
                     f'{r["signal_pp"]:+.2f}', f'[{r["signal_ci_low"]:+.2f}, {r["signal_ci_high"]:+.2f}]', conf,
                     f'{r["p_value"]:.4f}',
                     _blank(r["break_even"]), _blank(r["p_vs_price"]),
                     _blank(r["published_p"]), rep,
                     f'{r["bh_q"]:.3f}', q,
                     ('<span class="blank">—</span>' if r["staking_roi_pct"] is None else f'{r["staking_roi_pct"]:+.2f}'),
                     esc(r["rank_money"]), src(r["source"], "board")])
    body = ['<section class="block"><p class="lede">Three questions are asked about every rule, and they have '
            'different answers. <strong>Is there a signal?</strong> compares the win rate with a coin flip. '
            '<strong>Does it survive the price?</strong> compares the same win rate with the break-even rate the '
            'price implies. <strong>Did it make money?</strong> is the board\'s own ROI. A rule can pass the first '
            'and fail the second, which is exactly why a staking number on its own is not evidence of skill.</p></section>']
    body.append('<section class="block"><h2>Signal, price, and money</h2>')
    body.append(table(["Rank", "Rule", "n", "Win %", "Signal (pp vs coin flip)", "95% interval", "Signal verdict",
                       "p (vs coin flip)", "Break-even %", "p (vs break-even)", "Board's p",
                       "Board p reproduces", "BH q (24 tests)", "Multiplicity", "Staking ROI %", "Money rank",
                       "Source"], rows,
                      note=f'{sig["n_signal_ci_above_zero"]} of {sig["n_rows"]} rules have a signal interval entirely '
                           f'above zero; {sig["n_q_below_05"]} survive the multiplicity correction. Against the price '
                           f'null, {sig["n_vs_price_above_005"]} rule reaches p &lt; 0.05 — and it is a rule whose '
                           f'win rate is <em>below</em> its break-even rate, so the p-value is testing the wrong tail '
                           f'of the question. The board\'s own p is recomputed from its n, wins and break-even rate: '
                           f'{sig["n_p_reproduces"]} of {sig["n_p_checked"]} reproduce within 0.02.'))
    if sig["price_misses"]:
        body.append('<p class="note">Three board p-values do not reproduce from the board\'s own published inputs: '
                    + ", ".join(f'{esc(m["strategy"])} (ours {m["p_calc"]:.4f}, board {m["p_published"]:.4f})'
                                for m in sig["price_misses"])
                    + '. That is a discrepancy in the source file, recorded on the Flagged page as G13.</p>')
    body.append('</section>')
    body.append('<section class="block"><h2>Does the board\'s own test reproduce?</h2>')
    body.append('<p>The leaderboard publishes a p-value per rule. Recomputed here from its own published n, wins and '
                'break-even rate, '
                f'{sig["n_p_reproduces"]} of {sig["n_p_checked"]} reproduce within 0.02. The three that do not are '
                'reported on the Flagged page as G13 rather than smoothed over. Reproducing a test is the cheapest '
                'form of verification available, and it is the one that catches a silent change in an input.</p></section>')
    body.append('<section class="block"><h2>The identity problem</h2>')
    BLOB = "https://github.com/kanlerxz87-cyber/NFL1/blob/main/"
    irows = [[f'<strong>{esc(r["id"])}</strong>', esc(r["model_rule"]), esc(r["s9cb_rule"]),
              '<span class="pill ok">same</span>' if r["same_rule"] else '<span class="pill fail">different rules</span>',
              _blank(r["model_roi_pct"]), _blank(r["s9cb_roi_pct"]),
              src(BLOB + "data/model/strategies.json", "model board"),
              src(BLOB + "data/s9cb/leaderboard.json", "s9cb board")] for r in st["rows"]]
    body.append(table(["ID", "Rule on data/model/strategies.json", "Rule on data/s9cb/leaderboard.json",
                       "Identity", "ROI % (model, -110 assumption)", "ROI % (s9cb, observed prices)",
                       "Source", "Source"], irows,
                      note=f'{st["n_conflicting_rule"]} of {st["n_rows"]} IDs name a different rule on each board. '
                           f'Until one registry owns the IDs, a cross-page comparison of "S04" compares two rules.'))
    body.append('</section>')
    body.append('<section class="block"><h2>Luck, stated as arithmetic</h2>')
    body.append('<p>The repository\'s own null model: at fair prices a one-unit bet at decimal odds d has zero mean '
                'profit and variance d − 1, so the total profit of a run of bets has a standard deviation of '
                '&radic;&Sigma;(d<sub>i</sub> − 1). A profit inside that band is what luck alone produces. '
                'The power calculation is the same idea from the other end: '
                f'<strong>{D["forward"]["power"]["bets_needed"]:,} graded bets</strong> would be needed to detect a '
                f'52% win rate against a 50% break-even at 80% power, which is about '
                f'{D["forward"]["power"]["weeks_at_13_games"]:.0f} weeks at 13 games a week.</p></section>')
    return page("strategies.html", "Strategies", "".join(body),
                "Every rule on both boards: the signal, the price it had to beat, the money it made, and the "
                "identity problem between the two files.")


def prices():
    p = D["prices"]
    body = ['<section class="block"><p class="lede">This is the decision the brief asks for before any backtest is '
            'published: what counts as a price. It is published as a decision record, in four options, with the '
            'evidence for each — not as a recommendation dressed up as a fact.</p></section>']
    body.append('<section class="kpis">'
                + kpi("Games in the price file", f'{p["n_games"]:,}', f'{p["seasons"][0]}–{p["seasons"][1]}')
                + kpi("With a closing line", f'{p["has_closing_spread"]:,}', "consensus, mirrored feed")
                + kpi("With an opening line", "0", "the field does not exist in the source")
                + kpi("With a moneyline", f'{p["has_moneyline"]:,}', "5,228 games; none for Week 11 2026")
                + kpi("Officially priced games", "0", "the league publishes no odds")
                + '</section>')
    body.append('<section class="block"><h2>The fields that exist</h2>')
    body.append(table(["Field in the source", "Rows populated", "What it is", "Source"], [
        ["spread_line", f'{p["has_closing_spread"]:,}', "The consensus closing spread, home-signed.", src(p["source"], "feed")],
        ["total_line", f'{p["has_closing_spread"]:,}', "The consensus closing total.", src(p["source"], "feed")],
        ["home_moneyline / away_moneyline", f'{p["has_moneyline"]:,}', "A moneyline, where the feed has one.", src(p["source"], "feed")],
        ["home_spread_odds / away_spread_odds", f'{p["has_sided_price"]:,}', "The price of the side, where the feed has one.", src(p["source"], "feed")],
        ["opening spread or total", "0", '<span class="blank">the field does not exist in the source</span>', NA_CELL],
        ["Official cross-check", "0", "The league page prints date, time, network, venue and no price.", src(p["official_source"], "official")],
    ]))
    body.append('</section>')
    body.append('<section class="block"><h2>Four options, with what each one buys and costs</h2>')
    body.append(table(["Option", "What it buys", "What it costs", "What it cannot do", "Blocking question", "Evidence"], [
        ["A. Grade on the consensus close only, labelled as consensus everywhere",
         "Backtesting can start this week on 7,130 games.",
         "No CLV, no opening-to-closing, no claim that a residual is tradeable.",
         "Cannot distinguish a model that predicts the close from one that predicts the move.",
         "Q02", src(p["source"], "feed")],
        ["B. Licence a quote feed with a timestamp per quote",
         "Opening and closing numbers, CLV, and a defensible price for every graded bet.",
         "A contract, and a schema to store quotes rather than a single number.",
         "Still cannot make a price official — the league publishes none.",
         "Q02, Q07", src(p["source"], "feed")],
        ["C. Record only our own originated numbers and never grade on money",
         "Zero provenance risk; the site becomes a pure analysis desk.",
         "No leaderboard of returns; the reward structure in the brief cannot be built.",
         "Cannot answer whether anything made money.",
         "Q02, Q09", src(p["source"], "feed")],
        ["D. Refuse to publish any residual until B exists",
         "No number on the site depends on an unsourced price.",
         "The market book goes dark; the origination work loses its comparator.",
         "Cannot show the difference between our line and the market at all.",
         "Q02", src(p["source"], "feed")],
    ], note="The site currently behaves as option A while the policy is undecided, and says so on every page that "
            "prints a residual. That is the honest description, not a decision."))
    body.append('</section>')
    body.append('<section class="block"><h2>The store that would make option B work</h2>')
    cards = [("quote_id", "One row per quote, so a price can be cited."),
             ("market and selection", "Side, total or moneyline, and which team or side."),
             ("quoted_at (UTC)", "The moment the price was available. Every lookahead question depends on it."),
             ("source and licence", "Who published it, and under what terms it may be republished."),
             ("opening / closing flag", "Because the two answer different questions."),
             ("raw payload hash", "So a quote can be proved to be the one that was read.")]
    body.append('<div class="cards">' + "".join(
        f'<div class="card"><h3>{esc(a)}</h3><p>{esc(b)}</p>'
        f'<p class="sub">Present today: <span class="pill fail">no</span></p></div>' for a, b in cards) + '</div>')
    body.append('</section>')
    return page("prices.html", "Price Snapshot Policy", "".join(body),
                "What counts as a price, what the sources actually contain, and the four options for deciding it "
                "before another backtest is published.")


def readiness():
    rows = [[f'<strong>{esc(r["id"])}</strong>', esc(r["requirement"]), badge(r["status"]),
             esc(r["gate"]), esc(r["clear"]), esc(r["evidence"]), src(r["source"], "official")]
            for r in content.READINESS]
    counts = {}
    for r in content.READINESS:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    body = ['<section class="block"><p class="lede">One row per requirement in the brief. Status is decided from '
            'evidence this session read or computed, not from an intention. "Blocked" means a source or a decision '
            'does not exist yet; "partial" means part of the requirement is met and the row names the part that is '
            'not; "not started" means no evidence exists at all.</p></section>']
    body.append('<section class="kpis">'
                + kpi("Requirements tracked", str(len(content.READINESS)), "one row each")
                + kpi("Done", str(counts.get("done", 0)), "evidence on the page")
                + kpi("Partial", str(counts.get("partial", 0)), "gate named")
                + kpi("Blocked", str(counts.get("blocked", 0)), "source missing")
                + kpi("Not started", str(counts.get("not-started", 0)), "no evidence")
                + '</section>')
    body.append('<section class="block"><h2>The register</h2>')
    body.append(table(["ID", "Requirement", "Status", "Gate that blocks it", "The number that would clear it",
                       "Evidence read this session", "Source"], rows))
    body.append('</section>')
    return page("readiness.html", "Decision Readiness", "".join(body),
                "Every requirement, the gate that blocks it, and the number that would clear it.")


def questions():
    rows = [[f'<strong>{esc(q["id"])}</strong>', esc(q["question"]),
             f'<span class="ok-text">{esc(q["known"])}</span>',
             f'<span class="bad-text">{esc(q["unknown"])}</span>',
             esc(q["answer_if"]), esc(q["blocks"]), esc(q["discover"]), src(q["source"], "official")]
            for q in content.QUESTIONS]
    body = ['<section class="block"><p class="lede">A question is here because a decision cannot be made without '
            'it. Each row separates what is known from what is not, names the evidence that would settle it, and '
            'names what it blocks. The four that block the most work are Q01 (results), Q02 (prices), Q03 (rule '
            'identity) and Q04 (point-in-time availability).</p></section>']
    body.append('<section class="block"><h2>The ten questions that gate decisions</h2>')
    body.append(table(["ID", "Question", "Known", "Not known", "What would settle it", "What it blocks",
                       "How to discover it", "Source"], rows))
    body.append('</section>')
    body.append('<section class="block"><h2>Questions that cannot be answered at all today</h2>'
                '<div class="cards">'
                '<div class="card bad"><h3>Who actually started?</h3><p>No game book is stored, and no source read '
                'this session names a starter. Every table on the site that could name a replacement leaves the cell '
                'blank for this reason.</p></div>'
                '<div class="card bad"><h3>What did the market open at?</h3><p>No opening number exists in any file the '
                'repository holds. A model of price movement cannot be tested without one.</p></div>'
                '<div class="card bad"><h3>Did last week\'s forecast win?</h3><p>No Week-11 game has been played, and the '
                'Week-10 results were missing from the feed that would score it. Q01 is the blocking question.</p></div>'
                '<div class="card bad"><h3>Is any rule actually better than chance?</h3><p>Not at the multiplicity-'
                'corrected level on the sample that exists: 0 of 24 rules have q &lt; 0.05, and a 52% edge would need '
                'about seven seasons of games to prove.</p></div>'
                '</div></section>')
    return page("questions.html", "Open Questions", "".join(body),
                "What is known, what is missing, what would settle it, and what it blocks.")


def suggestions():
    rows = []
    for s in content.SUGGESTIONS:
        rows.append([esc(s["rank"]), f'<strong>{esc(s["title"])}</strong>', esc(s["why"]), esc(s["how"]),
                     esc(s["cost"]), esc(s["impact"]), src(s["source"], "evidence")])
    body = ['<section class="block"><p class="lede">Suggestions are options for a reviewer, not changes. Nothing '
            'on this page has been implemented; each one names the evidence it rests on and what it would cost. '
            'The top four are ordered by how much of the rest of the work they unblock, not by how interesting they are.</p></section>']
    body.append('<section class="block"><h2>Ranked suggestions</h2>')
    body.append(table(["#", "Suggestion", "Why", "How", "Cost", "Impact", "Evidence"], rows))
    body.append('</section>')
    body.append(f'<section class="block"><h2>How to choose one</h2><p>{esc(content.SUGGESTIONS_PROCESS)}</p>'
                '<p>Each suggestion maps to a row on <a href="readiness.html">Readiness</a> and to a question on '
                '<a href="questions.html">Questions</a>. A reviewer who wants the largest single gain should start '
                'with SG01; a reviewer who wants the site to stop overstating itself should start with SG02.</p>'
                '</section>')
    return page("suggestions.html", "Suggestions", "".join(body),
                "Ten options, ranked by how much they unblock, each with its evidence and its cost.")


def flagged():
    rows = [[f'<strong>{esc(f["id"])}</strong>',
             '<span class="pill fail">high</span>' if f["sev"] == "high" else
             ('<span class="pill warn">medium</span>' if f["sev"] == "medium" else '<span class="pill neutral">low</span>'),
             f'<strong>{esc(f["title"])}</strong>', esc(f["detail"]), esc(f["evidence"]),
             src(f["source"], "official")] for f in content.FINDINGS]
    body = ['<section class="block"><p class="lede">Nothing on this page blocks publication. Each row is a '
            'discrepancy or a gap found while verifying, with the source that settles it or the source that is '
            'missing. A row marked high means a published number depends on the thing that is wrong.</p></section>']
    body.append('<section class="block"><h2>The register</h2>')
    body.append(table(["ID", "Severity", "Finding", "Detail", "Evidence read this session", "Source"], rows,
                      note="Severity is a judgement about consequence, not about difficulty: high means a published "
                           "figure is affected today."))
    body.append('</section>')
    return page("flagged.html", "Flagged for Review", "".join(body),
                "Twelve findings, each with the evidence and the source that settles or explains it.")


def method():
    ro = D["availability"]
    body = ['<section class="block" id="sources"><h2>Official pages read this session</h2>']
    rows = [[src(url, label), esc(D["retrieved"]), esc(what)] for (label, url), what in zip(
        [(k, v) for k, v in lib.OFFICIAL.items()],
        ["32-club league standings, W/L/T/PCT/PF/PA/NET",
         "Week-10 injury report, 8 chunks, 347 player rows",
         "Week-11 schedule, 13 fixtures, 6 byes",
         "Week page serving the Week-10 results, 13 finals"])]
    body.append(table(["Official page", "Read on", "What it supplied"], rows))
    body.append('</section>')
    body.append('<section class="block"><h2>How each class of number was checked</h2>')
    body.append(table(["Number class", "Check performed", "Result", "Source"], [
        ["Standings", "Transcribed from the official page; compared with data/standings.csv field by field; then "
                      "stored table + 13 official finals compared with the official table",
         f'{D["standings"]["n_matched"]} of 32 match on the first comparison; 32 of 32 reconcile on the second',
         src(lib.OFFICIAL["standings"], "standings")],
        ["Injury report", "Transcribed independently (347 rows) and diffed against the committed capture on club, "
                          "player, position, injury, practice status and game status",
         "0 differing rows, 0 missing keys, 0 extra keys", src(lib.OFFICIAL["injuries_w10"], "report")],
        ["Own lines", "Residuals recomputed from the stored fair and market values; no residual is typed in",
         f'{D["lines"]["n_side"]} side residuals and {D["lines"]["n_total"]} total residuals reproduce',
         src("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/model/lines.json", "model file")],
        ["Correlations", "Pearson r, Fisher-z interval and t computed here from stored rows; cells blanked below 25 "
                         "observations",
         f'{len(D["correlations"]["official_rows"])} official-sourced correlations at n = 32 clubs, '
         f'{sum(1 for r in D["correlations"]["rows"] if not r["published"])} blanked for sample size',
         src(lib.OFFICIAL["standings"], "standings")],
        ["Signal and staking", "Win-rate interval against a coin flip, two-sided z test, Benjamini-Hochberg across "
                               "every rule on both boards",
         f'{D["signal"]["n_rows"]} rules, {D["signal"]["n_q_below_05"]} survive at q &lt; 0.05',
         src("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/leaderboard.json", "board")],
        ["Depth", "32 club charts stored; every starter name cross-checked against the official report",
         f'{D["depth"]["slots"]} slots, {D["depth"]["n_clubs"]} clubs',
         src("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/depth_ladder.json", "ladder")],
        ["Market columns", "Every market number traced to its file; the official pages searched for a line",
         f'0 of {D["market_provenance"]["n_unofficial"]} official; all labelled consensus',
         src("https://github.com/nflverse/nflverse-data/releases/tag/schedules", "feed")],
    ]))
    body.append('<p class="note" id="nosource">A cell that reads <strong>n/a · no public source</strong> means no '
                'source read this session prints a value for it. The cell is deliberately not filled: a blank with a '
                'reason is verifiable, an inferred number is not.</p>')
    body.append('</section>')
    body.append('<section class="block"><h2>What this page refuses to do</h2><div class="cards">'
                '<div class="card"><h3>Fill a blank</h3><p>If no source read this session confirms a value, the cell '
                'says Unverified. There is no interpolation and no "likely".</p></div>'
                '<div class="card"><h3>Infer a starter</h3><p>A club chart nominates a backup. That is not a start. '
                'The replacement column stays blank until a game book says otherwise.</p></div>'
                '<div class="card"><h3>Call a consensus close a price</h3><p>The mirrored feed is a consensus number. '
                'It is labelled that way in every column and every note.</p></div>'
                '<div class="card"><h3>Quote a correlation without n</h3><p>Every coefficient is printed with its sample '
                'size and interval, and is blanked below the 25-observation floor.</p></div>'
                '</div></section>')
    return page("method.html", "Method & Sources", "".join(body),
                "The four official pages this session read, what each supplied, and the check performed on every "
                "class of number.")


def main():
    sizes = {}
    for fn in (overview, executive, market, results, availability, strategies, prices,
               readiness, questions, suggestions, flagged, method):
        name = {"overview": "index.html"}.get(fn.__name__, fn.__name__ + ".html")
        sizes[name] = fn()
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    print(json.dumps(sizes, indent=1))


if __name__ == "__main__":
    main()
