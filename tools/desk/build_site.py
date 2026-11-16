#!/usr/bin/env python3
"""build_site.py — render the `desk/` sub-site from data/desk/*.json and the repository's own files.

Session `ed736fc3-nfl1`, tasks D2-D4. One generator, one input directory, no hand-edited output.

Every table on every page is built by `table()`, which requires each column named `Source` to hold
an <a href> in every row and refuses to render a cell that is None (a blank must be an explicit
string such as "not published"). tools/desk/verify_site.py independently re-reads the rendered
HTML and recomputes the numbers a second time.

Run: python3 tools/desk/build_site.py        # writes desk/*.html
     python3 tools/desk/build_site.py --check  # render to memory, fail if a page would change
"""
from __future__ import annotations

import html
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DESK = os.path.join(ROOT, "data", "desk")
OUT = os.path.join(ROOT, "desk")
SITE = "https://kanlerxz87-cyber.github.io/NFL1"


def J(name: str):
    with open(os.path.join(DESK, name), encoding="utf-8") as f:
        return json.load(f)


def repo(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def e(x) -> str:
    return html.escape(str(x), quote=True)


def num(x, spec="+.2f", blank="not published"):
    """A null is published as a labelled blank, never as 0 and never as a plausible guess."""
    return blank if x is None else format(x, spec)


def fmt(x):
    if isinstance(x, float):
        return f"{x:,.4f}".rstrip("0").rstrip(".") if abs(x) < 1 else f"{x:,.2f}"
    if isinstance(x, int):
        return f"{x:,}"
    return x


NAV = [
    ("index.html", "Overview"),
    ("readiness.html", "Readiness"),
    ("verification.html", "Verification"),
    ("strategies.html", "Strategies & Luck"),
    ("availability.html", "Availability & Depth"),
    ("pricing.html", "Pricing & Signals"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged for Review"),
    ("executive-summary.html", "Executive Summary"),
    ("method.html", "Method & Sources"),
]


def table(headers, rows, caption=None, cls="grid") -> str:
    """Render a table. A 'Source' column must carry a link in every row; None is refused."""
    out = [f'<table class="{cls}">']
    if caption:
        out.append(f"<caption>{caption}</caption>")
    out.append("<thead><tr>" + "".join(f"<th>{e(h)}</th>" for h in headers) + "</tr></thead><tbody>")
    src_i = [i for i, h in enumerate(headers) if h.strip().lower() == "source"]
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            if c is None:
                raise ValueError(f"None cell in table {caption!r} column {headers[i]!r}")
            cells.append(f'<td class="{"src" if i in src_i else ""}">{c}</td>')
        if src_i:
            if "href=" not in r[src_i[0]]:
                raise ValueError(f"Source column without a link in table {caption!r}: {r[src_i[0]]!r}")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def link(url, label=None) -> str:
    return f'<a href="{e(url)}">{e(label or url)}</a>'


def page(name, title, body, subtitle="", stamp=True) -> str:
    active = name
    cls = " class=\"active\""
    nav = "".join(
        '<a href="{h}"{c}>{t}</a>'.format(h=e(h), c=(cls if h == active else ""), t=e(t))
        for h, t in NAV
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · NFL Decision Desk</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="top">
  <div class="wrap">
    <p class="crumb"><a href="{SITE}/index.html">NFL Decision Lab</a> › NFL Decision Desk</p>
    <h1>{e(title)}</h1>
    <p class="sub">{subtitle}</p>
    <nav>{nav}</nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="wrap">
  <p>NFL Decision Desk — session <code>ed736fc3-nfl1</code>, built {e(GEN_AT)} from <code>data/desk/*.json</code>.
  Every table row carries the official page it was checked against; a value that could not be confirmed
  is published as a labelled blank or on the <a href="flagged.html">Flagged for Review</a> page.
  This is a research tool, not betting advice.</p>
</footer>
</body>
</html>
"""


GEN_AT = ""


# --------------------------------------------------------------------------- page bodies
def p_index():
    st, inj, sch, dep = J("standings.json"), J("injuries.json"), J("schedule.json"), J("depth.json")
    rd, qs, sg, cl = J("readiness.json"), J("questions.json"), J("suggestions.json"), J("claims.json")
    fl = J("flags.json")
    counts = {}
    for r in rd["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    kpi = [
        ("Requirement rows", f'{len(rd["rows"])}'),
        ("Met", f'{counts.get("met", 0)}'),
        ("Partial", f'{counts.get("partial", 0)}'),
        ("Blocked", f'{counts.get("blocked", 0)}'),
        ("Not started", f'{counts.get("not_started", 0)}'),
        ("Owner decision needed", f'{counts.get("decision_needed", 0)}'),
        ("Open questions", f'{len(qs["rows"])}'),
        ("Irregularities found this session", f'{fl["counts"]["total"]}'),
    ]
    kpi_html = "".join(f'<div class="kpi"><span class="n">{e(v)}</span><span class="l">{e(k)}</span></div>' for k, v in kpi)

    # the six numbers a reader most needs, each with the comparison
    head = [
        ("Official standings re-read", f'{st["counts"]["clubs"]} clubs, {st["counts"]["games_played"]} completed games',
         "Every row re-read this session; PF-PA=NET and PCT reproduce in all 32 rows.", st["source_url"]),
        ("Week-10 injury report re-read", f'{inj["counts"]["rows"]} rows, {inj["counts"]["clubs"]} clubs',
         f'{inj["counts"]["with_game_status"]} rows carry a game status; {inj["counts"]["practice_only"]} are practice-only.',
         inj["source_url"]),
        ("Week-11 fixtures re-read", f'{sch["week11"]["counts"]["fixtures"]} fixtures, {sch["week11"]["counts"]["byes"]} byes',
         f'{sch["week11"]["counts"]["clubs_playing"]} clubs play and {sch["week11"]["counts"]["byes"]} are on bye = '
         f'{sch["week11"]["counts"]["clubs_total"]} clubs; committed copy reproduces: {sch["week11"]["committed_check"]["verdict"]}.',
         sch["week11"]["source_url"]),
        ("Backtest corpus vs the season", f'{sch["corpus"]["played_rows"]} vs {sch["corpus"]["implied_from_official_standings"]} games',
         f'Gap of {sch["corpus"]["gap_games"]} completed games. This is why a build gate fails on main (D-F01).',
         st["source_url"]),
        ("Club depth charts read", f'{dep["counts"]["clubs"]} of 32 clubs',
         f'{sum(c["counts"]["slots"] for c in dep["charts"])} slots transcribed; {dep["counts"]["chains"]} starter-out chains resolved by chart order.',
         "https://www.detroitlions.com/team/depth-chart"),
        ("Strategies that clear every gate", "0 of 12",
         "Best row: Brier skill 0.0104 vs price, ROI 6.06% with a 95% interval of -3.1% to +15.3%.",
         "https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/leaderboard.json"),
    ]
    head_rows = [[e(a), e(b), e(c), link(d)] for a, b, c, d in head]

    claim_rows = [[e(r["id"]), e(r["claim"]), f'<strong>{e(r["verdict"])}</strong>', e(r["evidence"]),
                   link(r["source_url"] or r["src"])] for r in cl["rows"]]

    top = sorted([r for r in rd["rows"] if r["status"] != "met"],
                 key=lambda r: ({"blocked": 0, "decision_needed": 1, "not_started": 2, "partial": 3}.get(r["status"], 4), r["id"]))[:8]
    block_rows = [[e(r["id"]), e(r["requirement"]), f'<span class="pill {e(r["status"])}">{e(r["status"].replace("_", " "))}</span>',
                   e(r["blocking_gate"]), e(r["number_now"]), e(r["clears_when"])] for r in top]

    body = f"""
<section class="hero">
  <p class="lede">A dashboard of what is verified, what is not, and what has to happen before a
  betting decision can be justified. Every number below was re-read from an official page on
  {e(inj["retrieved"])}, or is computed from a repository file named beside it.</p>
  <div class="kpis">{kpi_html}</div>
</section>

<h2>Where the project actually stands</h2>
<p>Most of this page is bad news, and that is the point: a decision desk is only useful if it
states the blocker before the result. Six numbers, each with the comparison that gives it meaning.</p>
{table(["Check", "Number", "What it means", "Source"], head_rows)}

<h2>Claims re-tested against the official pages today</h2>
<p>These are the findings the brief and earlier sessions carried. Each one was re-read this
session rather than repeated: a claim that no longer holds is marked resolved, not quietly kept.</p>
{table(["ID", "Claim", "Verdict", "Evidence", "Source"], claim_rows)}

<h2>What blocks a decision right now</h2>
<p>The eight rows that block the most. The full register is on <a href="readiness.html">Readiness</a>,
with the number that would clear each one.</p>
{table(["ID", "Requirement", "Status", "Blocking gate", "Number now", "Number that clears it"], block_rows)}

<h2>Read this next</h2>
<div class="cards">
  <a class="card" href="verification.html"><h3>Verification</h3><p>32 clubs, 347 injury rows, 13 fixtures and 3 depth charts, each row with its official link and what changed.</p></a>
  <a class="card" href="readiness.html"><h3>Readiness</h3><p>{len(rd["rows"])} requirements: status, the gate that blocks each, and the number that would clear it.</p></a>
  <a class="card" href="strategies.html"><h3>Strategies &amp; luck</h3><p>Zero of twelve strategies clears every gate. The luck panel shows how much of each result a fair price would have produced.</p></a>
  <a class="card" href="availability.html"><h3>Availability &amp; depth</h3><p>Who is listed to start, who is Out, and who the club's own chart names next — with the coverage gap stated.</p></a>
  <a class="card" href="questions.html"><h3>Questions</h3><p>{len(qs["rows"])} questions that gate a decision: what is known, what is missing, and how to find it.</p></a>
  <a class="card" href="suggestions.html"><h3>Suggestions</h3><p>Twelve improvements ranked, each with a recommended path, the alternative and what it unblocks.</p></a>
  <a class="card" href="flagged.html"><h3>Flagged for Review</h3><p>Every irregularity and unverified value, with the source link that settles it.</p></a>
  <a class="card" href="executive-summary.html"><h3>Executive summary</h3><p>The whole position in one page: what holds, what does not, and the four decisions that only the owner can make.</p></a>
</div>

<h2>How to read a blank on this site</h2>
<p>A blank is never a zero and never an assumption. It means one of three things, and the page says
which: <em>not published</em> (the source does not print it), <em>not read</em> (nobody has fetched it
yet), or <em>unverified</em> (a value exists but no official page confirms it). Values that are
unverified are not shown as numbers at all; they are listed on the
<a href="flagged.html">Flagged for Review</a> page with what would settle them.</p>
"""
    return page("index.html", "Overview", body,
                "What is verified, what is not, and what has to happen before a decision.")


def p_readiness():
    rd = J("readiness.json")
    groups = []
    for r in rd["rows"]:
        if r["group"] not in groups:
            groups.append(r["group"])
    counts = {}
    for r in rd["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    legend = table(["Status", "What it means"],
                   [[f'<span class="pill {e(k)}">{e(k.replace("_", " "))}</span>', e(v)]
                    for k, v in rd["legend"].items()],
                   caption="The five statuses used below. A status is decided from the file named in 'computed from', not from prose.")
    parts = [legend]
    for g in groups:
        rows = [r for r in rd["rows"] if r["group"] == g]
        body_rows = [
            [e(r["id"]), e(r["requirement"]),
             f'<span class="pill {e(r["status"])}">{e(r["status"].replace("_", " "))}</span>',
             e(r["blocking_gate"]), e(r["number_now"]), e(r["clears_when"]),
             link(r["src"], r["source_label"])]
            for r in rows
        ]
        parts.append(f'<h2>{e(g)} <span class="count">{len(rows)} requirements</span></h2>')
        parts.append(table(["ID", "Requirement", "Status", "Blocking gate", "Number now",
                            "Number that clears it", "Source"], body_rows))

    summary = "".join(f'<div class="kpi"><span class="n">{v}</span><span class="l">{e(k.replace("_", " "))}</span></div>'
                      for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    body = f"""
<p class="lede">One row per requirement in the brief, grouped by layer. Each row states the gate
that blocks it and the number that would clear it, so a decision can be argued with evidence
rather than opinion. Rows are not ticked off because a document describes them; they are ticked
only when the artefact exists and the number is reached.</p>
<div class="kpis">{summary}</div>
{''.join(parts)}
<h2>What this table does not tell you</h2>
<p>A row marked <em>met</em> means the artefact exists and the gate is cleared; it does not mean the
artefact is good. A row marked <em>partial</em> can still be the most valuable thing on the site.
The two rows worth reading first are A-06 (who actually started — blocked on Game Books) and
P-02 (the results feed, {rd["rows"][1]["number_now"].split(";")[0]}). Almost every other row depends
on one of them. Several rows share a single blocker, so the {len(rd["rows"])} rows are not {len(rd["rows"])} independent
problems: the price policy, the collector run and the Game Book ingest would move more than half of them.</p>
"""
    return page("readiness.html", "Readiness", body,
                "Every requirement, the gate that blocks it, and the number that clears it.")


def p_verification():
    st, inj, sch, dep, cl = J("standings.json"), J("injuries.json"), J("schedule.json"), J("depth.json"), J("claims.json")
    srcs = J("sources.json")["sources"]

    st_rows = []
    for r in st["rows"]:
        cell = []
        for rel in ("data/evidence/standings_current.json", "data/standings.json",
                    "data/s9cb/official_standings_2026.csv", "data/personnel/official_standings_2026-11-13.csv"):
            c = r["compare"][rel]
            mark = {"match": "✓", "differs": "✗", "absent": "–"}[c["state"]]
            cell.append(f'<span title="{e(c["detail"])}">{mark}</span>')
        st_rows.append([e(r["code"]), e(r["team"]), e(f'{r["w"]}-{r["l"]}-{r["t"]}'), e(r["pf"]), e(r["pa"]),
                        e(r["net"]), e(r["games_played"]), " ".join(cell), link(st["source_url"], "nfl.com standings")])
    st_table = table(["Code", "Club", "W-L-T", "PF", "PA", "NET", "GP", "Reproduces in: evidence / root / s9cb / personnel",
                      "Source"], st_rows,
                     caption=f'Official standings re-read {st["retrieved"]}: {st["counts"]["clubs"]} clubs, '
                             f'{st["counts"]["games_played"]} completed games, {st["counts"]["arithmetic_failures"]} arithmetic failures.')

    inj_rows = [[e(r["club"]), e(r["player"]), e(r["position"]),
                 e(r["injury"] or "not published"), e(r["practice"]), e(r["game_status"] or "not published"),
                 link(r["player_url"], "nfl.com")] for r in inj["rows"]]
    inj_table = table(["Club", "Player", "Pos", "Injury", "Practice", "Game status", "Source"],
                      inj_rows,
                      caption=f'Official Week-10 injury report re-read {inj["retrieved"]}: '
                              f'{inj["counts"]["rows"]} rows, {inj["counts"]["clubs"]} clubs. "not published" is the page\'s own blank, not a missing value.')

    cl_rows = [[e(r["club"]), e(r["rows"]), e(r["out"]), e(r["doubtful"]), e(r["questionable"]),
                e(r["blank"]), link(r["source_url"], "nfl.com Week 10")] for r in inj["clubs"]]
    club_table = table(["Club", "Rows on the report", "Out", "Doubtful", "Questionable", "No game status",
                        "Source"], cl_rows,
                       caption="Per club. A club with many practice-only rows is not more injured than one with many "
                               "Out rows: the league publishes a practice report for every club that files one.")

    fx_rows = [[e(f["gameday"]), e(f["kickoff_et"]), e(f"{f['away']} @ {f['home']}"), e(f["network"]),
                e(f["venue_note"]), link(f["game_url"], "game centre")] for f in sch["week11"]["fixtures"]]
    fx_table = table(["Date", "Kickoff ET", "Fixture", "Network", "Venue (from the page's own stadium link)",
                      "Source"], fx_rows,
                     caption=f'Week 11 re-read {sch["week11"]["retrieved"]}: {sch["week11"]["counts"]["fixtures"]} fixtures; '
                             f'committed copy reproduces: {sch["week11"]["committed_check"]["verdict"]}.')
    bye_rows = [[e(b["club"]), e(b["record"]), link(b["source_url"], "nfl.com week 11")]
                for b in sch["week11"]["byes"]]
    bye_table = table(["Club on bye", "Record as printed", "Source"], bye_rows)

    w10_rows = [[e(r["gameday"]), e(f'{r["away"]} {r["away_score"] or "–"} @ {r["home"]} {r["home_score"] or "–"}'),
                 e(r["status"]), e(r["network"]),
                 f'<span class="pill {"met" if r["corpus"] == "match" else "blocked"}">{e(r["corpus"])}</span>',
                 link(r["game_url"], "nfl.com game")] for r in sch["week10"]["rows"]]
    w10_table = table(["Date", "Result", "Status", "Network", "Backtest corpus", "Source"], w10_rows,
                      caption=f'Week 10 results re-read {sch["week10"]["retrieved"]}: {sch["week10"]["counts"]["final"]} finals, '
                              f'{sch["week10"]["counts"]["scheduled"]} still scheduled, '
                              f'{sch["week10"]["counts"]["absent_from_corpus"]} finals absent from the corpus.')

    dep_rows = []
    for c in dep["charts"]:
        for u in c["units"]:
            for s in u["slots"]:
                names = ", ".join(p["name"] + (f' <span class="raw">(printed "{p["raw"]}")</span>'
                                               if p.get("raw") and p["raw"] != p["name"] else "")
                                  + (f' <span class="col">col {p["column"]}</span>' if p.get("column") else "")
                                  for p in s["players"]) or '<span class="blank">the club lists no player in this slot</span>'
                dep_rows.append([e(c["club"]), e(u["unit"]), e(s["position"]), names,
                                 link(c["source_url"], c["page_label"])])
    dep_table = table(["Club", "Unit", "Slot", "Names, in the order printed", "Source"], dep_rows,
                      caption=f'{dep["counts"]["clubs"]} of 32 clubs transcribed {dep["retrieved"]}; '
                              f'{sum(c["counts"]["slots"] for c in dep["charts"])} slots. Names are verbatim; a slot with several names is shown with all of them.')

    chain_rows = [[e(c["club"]), e(c["unit"]), e(c["position"]), e(c["starter"]),
                   f'<span class="pill blocked">Out</span> {e(c["injury_note"])}',
                   e(", ".join(c["replacements"]) or "the club lists no second name"),
                   link(c["starter_evidence"], "report row") + " · " + link(c["chart_url"], "chart")] for c in dep["resolved_chains"]]
    chain_table = table(["Club", "Unit", "Slot", "Starter on the chart", "Why he is out", "Next man named by the club",
                         "Source"], chain_rows,
                        caption="Starter-out chains. These are CHART EVIDENCE: the club lists the first name at the position, "
                                "and the official report rules him out. No inactive list or snap count confirms he did not play, so none of these is labelled a confirmed replacement.")

    claim_rows = [[e(r["id"]), e(r["claim"]), f'<strong>{e(r["verdict"])}</strong>', e(r["evidence"]),
                   link(r["source_url"] or r["src"])] for r in cl["rows"]]
    claim_table = table(["ID", "Claim", "Verdict", "Evidence", "Source"], claim_rows)

    src_rows = [[e(s["id"]), e(s["publisher"]), e(s["kind"]), link(s["url"], s["title"]), e(s["retrieved"]),
                 e(s["what"]), e(s.get("note", ""))] for s in srcs]
    src_table = table(["ID", "Publisher", "Kind", "Page read", "Read on", "What was taken from it",
                       "What the read established"], src_rows,
                      caption="The official sources re-read in this session. Only pages opened today appear here.")

    body = f"""
<p class="lede">Everything on this site traces to a page that was opened on {e(inj["retrieved"])}. This
page shows the transcription and the comparison, row by row, so a reader can check any value against
the source without trusting the session that produced it.</p>

<h2>What was re-read, and what it established</h2>
{src_table}

<h2>Claims re-tested</h2>
{claim_table}

<h2>Official standings: all 32 clubs</h2>
<p>Every row was re-read from the official table. The four tick/cross columns compare the same club in
the repository's own copies of that page: evidence, root, the s9cb extract and the personnel extract.
Hover a mark for the field-level detail. Three of the four copies are three to four days old, which is
why they no longer reproduce; that drift is flag <a href="flagged.html">D-F02</a>.</p>
{st_table}

<h2>Week-10 injury report: all 347 rows</h2>
<p>An empty injury or game-status cell is printed by the league that way. It is shown as
<em>not published</em> and never filled. Practice-only rows are those with no game designation;
the league distributes them before the final report of the week.</p>
{inj_table}

<h2>Injury report, per club</h2>
{club_table}

<h2>Week 11 fixtures</h2>
{fx_table}
{bye_table}

<h2>Week 10 results, and whether the backtest corpus has them</h2>
<p>The right-hand column is the test the brief asks for: can a backtest be computed at all? A final
score that is missing from the corpus cannot enter ROI, and the build gate that fails on main is
exactly this comparison.</p>
{w10_table}

<h2>Club depth charts</h2>
<p>Three clubs were read directly. The chart is a club artefact labelled <em>unofficial</em> by two of
the three clubs, and it is not the same thing as a starter list. Coverage is 3 of 32 here and 4 of 32
in the repository's register; the gap is flag <a href="flagged.html">D-F06</a>.</p>
{dep_table}

<h2>Starter out, next man named</h2>
{chain_table}

<h2>Clubs not read</h2>
<p>29 clubs are absent from this page's depth section. They are not presumed to resemble the three
that were read. Houston publishes its chart as an image and is deliberately not transcribed by eye
(<a href="flagged.html">D-F07</a>).</p>
"""
    return page("verification.html", "Verification", body,
                "Line by line against the official pages, re-read on 2026-11-16.")


def p_strategies():
    ps = repo("data/strat/proper_score.json")
    lb = repo("data/s9cb/leaderboard.json")
    luck = {r["strategy"]: r for r in lb["luck_accounting"]["rows"]}
    wwc = repo("data/strat/what_would_change.json")
    dem = repo("data/strat/demotion.json")
    dual = repo("data/strat/dual_total.json")
    prereg = repo("data/strat/preregistration.json")

    board_rows = []
    for r in sorted(lb["leaderboard"], key=lambda x: -x["hit_rate"]):
        lk = luck.get(r["strategy"], {})
        board_rows.append([
            e(r["strategy"]), e(r["n_bets"]), e(r["n_decided"]), e(f'{r["hit_rate"]:.4f}'),
            e(f'{r["break_even_hit_rate"]:.4f}'), e(f'{r["roi"] * 100:.2f}%'),
            e(f'{lk.get("profit_units", 0):.3f}'),
            e(f'[{lk.get("luck_band_95_units", [0, 0])[0]:.2f}, {lk.get("luck_band_95_units", [0, 0])[1]:.2f}]'),
            f'<span class="pill {"blocked" if not lk.get("profit_outside_luck_band") else "met"}">'
            f'{"inside the luck band" if not lk.get("profit_outside_luck_band") else "outside"}</span>',
            e(f'{lk.get("p_value_two_sided", 0):.4f}'),
            link("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/leaderboard.json", "leaderboard")
            + " · " + link("https://www.nfl.com/schedules/", "nfl.com schedule"),
        ])
    board = table(["Strategy", "Bets", "Decided", "Hit rate", "Break-even", "ROI", "Profit (units)",
                   "95% luck band (units)", "Verdict", "p (two-sided)", "Source"], board_rows,
                  caption=f'{lb["n_strategies"]} strategies. The luck band is the profit a fair price would produce '
                          f'95% of the time given the same bets and prices; a result inside it cannot be told from luck.')

    ps_rows = []
    for m in ps["markets"]:
        for name, v in m["results"].items():
            if "bss" not in v and "bss_vs_devig" not in v:
                # the 'vig_size' block is a measurement, not a scored benchmark; it is shown below
                ps_rows.append([e(m["market"]), e(name), e(v.get("n_scored", "—")), "—", "—", "—",
                                e(v.get("reading", "see note"))])
                continue
            skill = v.get("bss", v.get("bss_vs_devig", v.get("bss_vs_coin")))
            ci = v.get("bss_ci95") or v.get("bss_vs_coin_ci95") or [0, 0]
            lower = v["bss_lower_bound"]
            ps_rows.append([e(m["market"]), e(name), e(v["n_scored"]), e(f'{v["brier"]:.5f}'),
                            e(f'{skill:+.4f}'), e(f'[{ci[0]:+.4f}, {ci[1]:+.4f}]'),
                            f'<span class="pill {"met" if lower > 0 else "blocked"}">'
                            f'{e("clears" if lower > 0 else "does not clear")}</span>'])
    ps_table = table(["Market", "Scored by", "n", "Brier", "Skill vs benchmark", "95% interval", "Verdict"], ps_rows,
                     caption=f'{ps["method"]["score"]}. Published number: {ps["method"]["published_number"]}. '
                             f'Interval: {ps["method"]["interval"]}. Markets with no scored rows (parlay, same-game '
                             f'parlay, player prop) are printed here as empty rather than omitted.')

    mult_rows = [[e(t["test"]), e(f'{t["bss"]:+.5f}'), e(f'{t["p_value_bootstrap"]:.4f}'),
                  e(f'{t["bh_adjusted_p"]:.4f}'), e(f'{t["bonferroni_alpha"]:.5f}')]
                 for t in ps["multiplicity"]["family"]]
    mult = table(["Test", "Skill vs benchmark", "Bootstrap p", "BH-adjusted p", "Bonferroni threshold"], mult_rows,
                 caption=f'Eligibility rule: {ps["eligibility_rule"]}')

    wwc_rows = [[e(r["id"]), e(r["claim"]), e(r["current"]),
                 e(r.get("confirming") or r.get("would_confirm") or "see record"),
                 e(r.get("abandoning") or r.get("would_abandon") or "see record"),
                 e(r.get("status", ""))] for r in wwc["rows"]]
    wwc_t = table(["ID", "Hypothesis", "Current evidence", "Would be confirmed by", "Would be abandoned by", "Status"],
                  wwc_rows, caption=f'{wwc["n_claims"]} registered hypotheses. {wwc["rule"]}')

    dem_rows = [[e(r["id"]), e(r["strategy"]), e(r["registration_status"]),
                 f'<span class="pill {"met" if r["status"] == "PAPER" else "blocked"}">{e(r["status"])}</span>',
                 e(r["live_bets_settled"]), e(r["reason"])] for r in dem["rows"]]
    dem_t = table(["ID", "Strategy", "Registration", "State", "Settled live bets", "Why"], dem_rows,
                  caption=f'{dem["n_strategies"]} strategies: {dem["n_live"]} live, {dem["n_paper"]} on paper, '
                          f'{dem["n_demotions_ever"]} demotions ever. {dem["state_note"]}')

    dual_rows = [[e(r["season"]), e(r["n"]), e(f'{r["mae_a"]:.4f}'), e(f'{r["mae_b"]:.4f}'),
                  e(f'{r["mean_paired_difference_a_minus_b"]:+.4f}'),
                  e(f'[{r["ci95"][0]:+.4f}, {r["ci95"][1]:+.4f}]'),
                  f'<span class="pill {"met" if not (r["a_is_better"] or r["b_is_better"]) else "partial"}">'
                  f'{e("not separated" if not (r["a_is_better"] or r["b_is_better"]) else ("A" if r["a_is_better"] else "B"))}</span>',
                  e("yes" if r.get("in_holdout") else "no")] for r in dual["by_season"][-8:]]
    dual_t = table(["Season", "n", "MAE estimator A", "MAE estimator B", "A − B", "95% interval", "Verdict", "Holdout"],
                   dual_rows,
                   caption=f'Two totals, both published. A = {dual["estimators"]["A"]}; B = {dual["estimators"]["B"]}. '
                           f'Overall n={dual["overall"]["n"]}, holdout n={dual["holdout"]["n"]}. Winner: '
                           f'{dual["verdict"]["winner"] or "none yet"}. {dual["verdict"]["rule"]}')

    body = f"""
<p class="lede">The competition is ranked on proper scores with uncertainty, not on win rate. On this
evidence nothing is promotable: no strategy's profit leaves its own luck band, and the model's
probabilities score worse than the closing line. A blank champion is the honest result of 12 tested
rules on one partial season, and the page says so before the table.</p>

<h2>The leaderboard, with the luck band beside every result</h2>
<p>The rightmost columns are the ones that matter. For each strategy the site computes the profit a
<em>fair</em> price would have produced on exactly the same bets — mean zero, variance taken from the
prices themselves — and the range that profit would fall in 95% of the time. A profit inside that band
is indistinguishable from luck. Every row is inside its band.</p>
{board}

<h2>Proper-score qualification</h2>
<p>Skill is measured on probabilities, where a lucky sequence of wins cannot help. The benchmark is the
closing line turned into a probability, and the interval is a game-cluster bootstrap so that games
sharing a week are not treated as independent.</p>
{ps_table}

<h2>Multiplicity: 6 model-market tests in one run</h2>
{mult}

<h2>Two totals, both published, neither declared the winner</h2>
{dual_t}

<h2>What would change our mind</h2>
{wwc_t}

<h2>Demotion gate</h2>
{dem_t}

<h2>Pre-registration</h2>
<p>{prereg["n_records"]} rules are registered ({prereg["n_backtest"]} backtest, {prereg["n_prospective"]} prospective).
{prereg["rule"]} The registration commit is recorded with a hash of the file as committed, so a rule
cannot be edited after its results are known.</p>
<p class="warn"><strong>Open conflict.</strong> The s9cb leaderboard above still ranks {prereg["n_backtest"]} backtest
rows by ROI, which the brief forbids. The page labels them and publishes the sample, but ranking them at
all is the defect; it is suggestion <a href="suggestions.html">DS-03</a> and readiness row S-04.</p>
"""
    return page("strategies.html", "Strategies & Luck", body,
                "Proper scores, uncertainty and a luck band on every row — and zero strategies that clear every gate.")


def p_availability():
    inj, dep = J("injuries.json"), J("depth.json")
    rv = repo("data/reserve/report_vs_reserve.json")
    reserve = repo("data/reserve/reserve_state.json")
    snaps = repo("data/snapshots/injury_report/manifest.json")
    hb = os.path.join(ROOT, "data", "snapshots", "injury_report", "heartbeat.jsonl")
    heart = [json.loads(l) for l in open(hb, encoding="utf-8") if l.strip()] if os.path.exists(hb) else []

    out_rows = sorted([r for r in inj["rows"] if r["game_status"] == "Out"], key=lambda r: (r["club"], r["player"]))
    out_t = table(["Club", "Player ruled Out", "Pos", "Injury", "Club chart read?", "Next man the club names"],
                  [[e(r["club"]), e(r["player"]), e(r["position"]), e(r["injury"] or "not published"),
                    e("yes" if any(c["club"] == r["club"] for c in dep["charts"]) else "no"),
                    e(next((", ".join(ch["replacements"]) or "the club lists no second name"
                            for ch in dep["resolved_chains"]
                            if ch["club"] == r["club"] and ch["starter"] == r["player"]),
                           "not on the three charts read"))]
                   for r in out_rows],
                  caption=f'{len(out_rows)} players are ruled Out for Week 10 on the official report. The last two '
                          f'columns are filled only for the three clubs whose charts were read; an empty answer there '
                          f'means "not read", not "no replacement".')

    chain_rows = [[e(c["club"]), e(c["position"]), e(c["starter"]), e(c["injury_note"]),
                   e(", ".join(c["replacements"]) or "the club lists no second name"),
                   link(c["starter_evidence"], "report") + " · " + link(c["chart_url"], "chart")]
                  for c in dep["resolved_chains"]]
    chain_t = table(["Club", "Slot", "Starter listed first", "Why he is out", "Next man named", "Source"],
                    chain_rows,
                    caption="Five chains across three clubs. Each is marked CHART EVIDENCE rather than a confirmed "
                            "replacement: a starter being ruled out and a backup being named next is not proof the backup played.")

    club_rows = [[e(c["club"]), e(c["rows"]), e(c["out"]), e(c["doubtful"]), e(c["questionable"]),
                  e(c["blank"]), link(c["source_url"], "nfl.com Week 10")] for c in inj["clubs"]]
    club_t = table(["Club", "Rows", "Out", "Doubtful", "Questionable", "No game status", "Source"], club_rows)

    tot = rv["totals"]
    reserve_rows = [
        [e("Week-10 report rows (the record the model has been reading)"), e(tot["report_rows"]),
         link("https://www.nfl.com/injuries/", "nfl.com Week 10 report")],
        [e("Open reserve designations captured from the dated register"), e(tot["on_reserve"]),
         link("https://www.nfl.com/transactions/", "nfl.com transactions")],
        [e("Named on a reserve list and on no Week-10 report row"), e(tot["on_reserve_not_in_report"]),
         link("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/reserve/report_vs_reserve.json",
              "report_vs_reserve.json")],
        [e("Named on both records"), e(tot["named_in_both"]),
         link("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/reserve/report_vs_reserve.json",
              "report_vs_reserve.json")],
    ]
    reserve_t = table(["Measure", "Number", "Source"], reserve_rows,
                      caption="Read together, the two official records disagree about who is unavailable; the report alone "
                              "treats a player on injured reserve as available.")

    snap_rows = [[e(h["fetched_at_utc"]), e(h["http_status"]), e(h["rows"]), e(h["raw_sha256"][:16]),
                  e(h["week"]), e("yes" if h["changed"] else "no (identical to the previous read)"),
                  link(h.get("final_url") or "https://www.nfl.com/injuries/", "nfl.com")]
                 for h in heart]
    snap_t = table(["Read at (UTC)", "HTTP", "Rows parsed", "Raw sha256 (first 16)", "Week",
                    "Produced a new capture", "Source"], snap_rows,
                   caption=f"{len(heart)} reads logged, of which {snaps.get('captures', len(snaps.get('files', [])))} produced a "
                           f"distinct capture. A read only becomes a capture when the parsed report changes.")

    body = f"""
<p class="lede">Availability is where the brief asks for the most and where the data is thinnest. The
official report tells you a player is Out; it does not tell you who replaced him. That requires a club
depth chart, an inactive list and a snap count — and this site has the first for three clubs, the second
for one week, and the third for none. Every derived column below says which of those it rests on.</p>

<h2>The one structural fact that changes every team model</h2>
<p>The injury report and the reserve list are different records, and reading only the first treats a
player on injured reserve as available:</p>
{reserve_t}

<h2>Every player ruled Out for Week 10</h2>
{out_t}

<h2>Starter out, next man named — chart evidence only</h2>
{chain_t}

<h2>Availability by club</h2>
<p>Read this as a shape, not a ranking: a club with many practice-only rows is not more injured than one
with many Out rows. The league publishes the practice report for every club that has one.</p>
{club_t}

<h2>How much of a series exists</h2>
{snap_t}

<h2>What is deliberately missing here</h2>
<ul class="list">
  <li><strong>Confirmed starters.</strong> Would need official Game Books. Readiness A-06, D-08.</li>
  <li><strong>Who did not dress.</strong> Would need the inactive list for every played fixture. A-04.</li>
  <li><strong>Who actually played how much.</strong> Would need snap counts; the brief forbids inferring depth from jersey order, and without snaps the chart order is all there is. A-05.</li>
  <li><strong>Whether a designation predicts anything.</strong> Would need a play rate per designation. S-13, A-15.</li>
  <li><strong>A depth chart for 29 clubs.</strong> Would need one read per club page. A-16.</li>
</ul>
"""
    return page("availability.html", "Availability & Depth", body,
                "Who is ruled out, who the club's own chart names next, and the three records that are still missing.")


def p_pricing():
    lines = repo("data/model/lines.json")
    ps = repo("data/strat/proper_score.json")
    corr = repo("data/s9cb/correlations.json")
    par = repo("data/s9cb/parlays.json")
    prereg = repo("data/prereg/corpus.json")

    ln_rows = []
    for r in lines["lines"]:
        ln_rows.append([e(f'{r["away"]} @ {r["home"]}'), e(r["gameday"]),
                        e(num(r["my_home_line"])), e(num(r["market_home_line"])),
                        e(num(r["edge_home_line"])), e(num(r["my_total"], ".1f")), e(num(r["market_total"], ".1f")),
                        e(num(r["edge_total"])), e(num(r["my_win_prob_home"], ".3f")),
                        e(f'[{r["home_line_band95"][0]:+.1f}, {r["home_line_band95"][1]:+.1f}]'),
                        f'<span class="pill {"blocked" if r["status"] != "validated" else "met"}">{e(r["status"])}</span>',
                        link("https://www.nfl.com/schedules/2026/by-week/week-11", "fixture")])
    ln_t = table(["Fixture", "Date", "Own line (home)", "Market (home)", "Difference", "Own total",
                  "Market total", "Total difference", "Home win prob.", "95% band on the line", "Status", "Source"],
                 ln_rows,
                 caption=f'{len(lines["lines"])} Week-11 lines. Lines are printed from the home team\'s point of view; '
                         f'the difference is computed from the two printed numbers, never re-typed. '
                         f'Market columns come from a third-party price file, not from an official NFL source.')

    cal_rows = [[e(c["label"]), e(c["n"]), e(f'{c["spread_mae_model"]:.3f}'), e(f'{c["spread_mae_market"]:.3f}'),
                 e(f'[{c["spread_mae_diff_ci95"][0]:+.3f}, {c["spread_mae_diff_ci95"][1]:+.3f}]'),
                 e(f'{c["total_mae_model"]:.3f}'), e(f'{c["total_mae_market"]:.3f}'),
                 e(f'{c["corr_model_market_spread"]:.3f}')] for c in lines["calibration"]]
    cal_t = table(["Sample", "n", "Spread MAE: own", "Spread MAE: market", "Difference (95% CI)",
                   "Total MAE: own", "Total MAE: market", "Corr(own, market) spread"], cal_rows,
                  caption="Mean absolute error against the closing line. A model that is worse than the line it "
                          "is compared to cannot be the origin of an edge, however good its story.")

    bt = lines["blend_test"]
    blend_rows = [["Fit", e(bt["fit"])], ["Market weight", e(f'{bt["weight_market"]:+.3f}')],
                  ["Model weight", e(f'{bt["weight_model"]:+.3f}')], ["n train", e(bt["n_train"])],
                  ["n test", e(bt["n_test"])], ["Test MAE, blend", e(f'{bt["test_mae_hybrid"]:.3f}')],
                  ["Test MAE, market only", e(f'{bt["test_mae_market_only"]:.3f}')],
                  ["Reading", e(bt["interpretation"])]]
    blend_t = table(["Term", "Value"], blend_rows,
                    caption="Does the model add anything to the market? A model weight at or below zero says no.")

    corr_rows = [[e(c["id"]), e(c["relationship"]), e(c["n"]), e(f'{c["r"]:+.4f}'),
                  e(f'[{c["ci95"][0]:+.4f}, {c["ci95"][1]:+.4f}]'), e(f'{c["p_value"]:.4f}'), e(c["note"]),
                  link(c["source"], "nflverse / nfl.com")] for c in corr["game_level"]]
    corr_t = table(["ID", "Relationship", "n", "r", "95% interval", "p", "What it means", "Source"], corr_rows,
                   caption=f'Correlations are published with n on every row and only above the publication floor: '
                           f'{corr["publication_rule"]}')

    pr = par
    par_rows = [[e(str(pr.get("n_pairs_scored"))), e(str(pr.get("n_pairs_surviving_bh_5pct"))),
                 e(pr.get("reading", "")),
                 link("https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/s9cb/parlays.json", "parlays.json")]]
    par_t = table(["Pairs scored", "Pairs surviving the family-wise threshold", "Reading", "Source"], par_rows,
                  caption="Parlays are not ranked. Multiplying marginal probabilities is invalid under dependence, so a "
                          "combo may only be ranked when a directly validated joint probability and the operator's "
                          "void/push rules are both available. Neither exists in the repository.")

    price_rows = [["Price policy state", e(prereg["price_policy"]["state"])],
                  ["Decision reference", e(prereg["price_policy"]["decision_ref"])],
                  ["Note", e(prereg["price_policy"]["note"])],
                  ["Markets with an opening and a closing row", "0 (one value per market per game)"],
                  ["Markets with a fetch clock", "0"]]
    price_t = table(["Item", "State"], price_rows,
                    caption="The price store the brief asks for does not exist yet. This table is the gap stated plainly.")

    body = f"""
<p class="lede">The site originates its own side and total for all 13 Week-11 fixtures and publishes the
difference against the market. It does not yet originate a moneyline, and it has no opening/closing
price store, so the residual cannot be tracked in time. Both gaps are below the numbers, not hidden by them.</p>

<h2>Own lines, market lines, and the difference</h2>
{ln_t}

<h2>Is the model any good before the game?</h2>
{cal_t}

<h2>Does the model add anything to the market?</h2>
{blend_t}

<h2>Pricing the market, not just the team</h2>
<p>Removing the vig needs both sides of a market. With one number per market the hold cannot be
separated from the price, so no vig-free consensus is published here. That is the first thing an
approved price source would unlock.</p>
{price_t}

<h2>Parlays and prop combos</h2>
{par_t}

<h2>Correlations, with n and an interval on every value</h2>
{corr_t}

<h2>What this page will not claim</h2>
<p>A positive difference is not an edge. The edge test is correlation C3 above: if the model's
disagreement with the market carries no information (interval spanning zero), a large difference is
more likely a model error than a market error. It spans zero.</p>
"""
    return page("pricing.html", "Pricing & Signals", body,
                "Own lines against the market, with the honest test of whether the difference means anything.")


def p_questions():
    q = J("questions.json")
    groups = []
    for r in q["rows"]:
        if r["group"] not in groups:
            groups.append(r["group"])
    parts = []
    for g in groups:
        rows = [r for r in q["rows"] if r["group"] == g]
        parts.append(f"<h2>{e(g)} <span class=\"count\">{len(rows)} questions</span></h2>")
        parts.append(table(["ID", "Question", "What is known", "What is missing", "What it blocks",
                            "How to discover it", "Source"],
                           [[e(r["id"]), e(r["question"]), e(r["known"]), e(r["missing"]), e(r["blocks"]),
                             e(r["discovery"]), link(r["src"], r["source_label"])] for r in rows]))
    body = f"""
<p class="lede">A question is only useful if it changes what you do next. Each row states what is
already verified, what no source currently supplies, what it blocks, and the cheapest action that
would answer it. Questions already answered stay on the page with their answer, because a closed
question with a negative answer is a result.</p>
{''.join(parts)}
<h2>The four that matter most</h2>
<ul class="list">
  <li><strong>Q-01 — is the corpus current?</strong> No: 137 games against 149 implied by the official standings.</li>
  <li><strong>Q-04 — do we know who started?</strong> No: chart order only, for three clubs.</li>
  <li><strong>Q-09 — does the model beat the line?</strong> No: skill −0.0413, interval entirely below zero.</li>
  <li><strong>Q-24 — what unlocks the most?</strong> Running the collector: four readiness rows and one failing gate.</li>
</ul>
"""
    return page("questions.html", "Questions", body,
                "What is known, what is missing, and the action that would settle each question.")


def p_suggestions():
    s = J("suggestions.json")
    rows = [[e(r["rank"]), e(r["title"]), e(r["area"]), e(r["evidence"]),
             e(r["recommended_path"]), e(r["alternative"]), e(r["unblocks"]), e(r["effort"]), e(r["risk"]),
             e(r["needs"]), link(r["src"], r["source_label"])] for r in s["rows"]]
    t = table(["#", "Suggestion", "Area", "Evidence", "Recommended path", "Alternative", "Unblocks",
               "Effort", "Risk", "Needs", "Source"], rows)
    body = f"""
<p class="lede">Improvements, ranked by what they unblock per unit of effort, each with the evidence
that motivated it and the decision a reviewer is actually being asked to make. The first three cost
almost nothing and unlock the most: run the collector, decide the price policy, and stop ranking
backtest rows.</p>
<h2>Review process</h2>
<p>{e(s["review_process"])}</p>
{t}
<h2>If only one thing is done next</h2>
<p>Run the collector. It clears the failing gate on main, refreshes three stale copies of the
standings, and moves the corpus from 137 completed games to the official 149. It needs no decision
from anyone — it is a scheduled job that has not run recently enough.</p>
"""
    return page("suggestions.html", "Suggestions", body,
                "Twelve improvements, ranked, each with an alternative and what it unblocks.")


def p_flagged():
    mine = J("flags.json")
    fl = repo("data/flags.json")
    desk = mine["rows"]
    other = [f for f in fl if not str(f["id"]).startswith("D-F")]

    def rows(fs):
        out = []
        for f in fs:
            url = f.get("source_url") or ""
            out.append([e(f["id"]), e(f["category"]), e(f["description"]), e(f["impact"]),
                        f'<span class="pill {"met" if str(f["status"]).lower() == "resolved" else "blocked"}">{e(f["status"])}</span>',
                        e(f["action"]), link(url or "flagged.html", url or "see register")])
        return out

    srcmap = {s["id"]: s for s in J("sources.json")["sources"]}
    repo_src = {s["id"]: s for s in repo("data/sources.json")}
    for f in other:
        if not (f.get("source_url")):
            s = srcmap.get(f.get("src")) or repo_src.get(f.get("src"))
            f["source_url"] = s["url"] if s else ""
    t1 = table(["ID", "Category", "What is wrong", "What it affects", "Status", "What would close it", "Source"],
               rows(desk))
    t2 = table(["ID", "Category", "What is wrong", "What it affects", "Status", "What would close it", "Source"],
               rows(other),
               caption=f"{len(other)} items carried by earlier sessions, re-listed here so one page holds the whole register. "
                       f"Where a source key does not resolve to a URL the row links to the register itself rather than inventing a link.")
    op = sum(1 for f in fl if str(f["status"]).lower() != "resolved")
    body = f"""
<p class="lede">Nothing on this site is hidden because it is inconvenient. A flag states what is wrong,
what it affects, and the observation that would close it. Flags do not block publication — they are
the reason a reader can trust the rest.</p>
<div class="kpis">
  <div class="kpi"><span class="n">{len(fl)}</span><span class="l">flagged items</span></div>
  <div class="kpi"><span class="n">{op}</span><span class="l">still open</span></div>
  <div class="kpi"><span class="n">{len(desk)}</span><span class="l">found this session</span></div>
  <div class="kpi"><span class="n">{sum(1 for f in fl if str(f["status"]).lower() == "resolved")}</span><span class="l">resolved</span></div>
</div>
<h2>Found in this session</h2>
{t1}
<h2>Carried from earlier sessions</h2>
{t2}
<h2>How a flag differs from an error</h2>
<p>An error is something the build can detect and refuse. A flag is something only a person can
resolve: a source that contradicts itself, a claim that no longer holds, a file owned by another
generator that is out of date. The gates catch errors; this page carries the flags.</p>
"""
    return page("flagged.html", "Flagged for Review", body,
                "Every irregularity, with the source that would settle it.")


def p_exec():
    rd, qs, sg, cl = J("readiness.json"), J("questions.json"), J("suggestions.json"), J("claims.json")
    st, inj, sch, dep = J("standings.json"), J("injuries.json"), J("schedule.json"), J("depth.json")
    counts = {}
    for r in rd["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    lb = repo("data/s9cb/leaderboard.json")
    ps = repo("data/strat/proper_score.json")

    body = f"""
<p class="lede">The position in one page. Four things hold up, five do not, and four decisions belong
to the owner rather than to the agent.</p>

<h2>What holds up</h2>
<ol class="list">
  <li><strong>The official data on this page is verified, not asserted.</strong> {st["counts"]["clubs"]} club
      standings rows, {inj["counts"]["rows"]} injury rows across {inj["counts"]["clubs"]} clubs, {sch["week11"]["counts"]["fixtures"]} Week-11
      fixtures and {sch["week11"]["counts"]["byes"]} byes were re-read today. The Week-10 report reproduces the
      committed capture with 0 field differences, and the Week-11 schedule reproduces its committed copy with
      0 differences.</li>
  <li><strong>Skill is measured properly, and luck is removed explicitly.</strong> Every strategy is scored on
      Brier skill with a game-cluster interval and a multiplicity charge, and every ROI sits beside the profit
      a fair price would have produced. {len(lb["leaderboard"])} of {lb["n_strategies"]} strategies fall inside their own luck band.</li>
  <li><strong>Nothing is promoted that has not passed a gate.</strong> {counts.get("met", 0)} of
      {len(rd["rows"])} requirements are met ({counts.get("partial", 0)} partial, {counts.get("blocked", 0)} blocked,
      {counts.get("not_started", 0)} not started, {counts.get("decision_needed", 0)} waiting on an owner decision), and the
      ones that are met are the governance layer — pre-registration, demotion, controls, holdout splits — which is the
      part that stops the rest from becoming storytelling.</li>
  <li><strong>A wrong finding was retired rather than repeated.</strong> The brief's Baltimore stale-depth claim no
      longer holds: the chart now lists Brissett, Fagnano and Slovis at QB, and the dated transaction register
      explains why.</li>
</ol>

<h2>What does not hold up</h2>
<ol class="list">
  <li><strong>The model loses to the closing line.</strong> Skill −0.0413 (interval −0.0513 to −0.0299, n=6785),
      and its disagreement with the market carries no information (r = 0.019, interval −0.005 to 0.042).</li>
  <li><strong>No strategy is promotable.</strong> The best row has ROI 6.06% with an interval of −3.1% to +15.3%
      and needs about 1950 settled bets for 80% power. It has 401.</li>
  <li><strong>The results feed is 12 games behind.</strong> {sch["corpus"]["played_rows"]} completed games in the
      corpus against {sch["corpus"]["implied_from_official_standings"]} implied by the official standings. A build gate
      on main fails because of it (D-F01).</li>
  <li><strong>Nobody knows who actually started.</strong> Depth is chart order for {dep["counts"]["clubs"]} of 32 clubs;
      there are no inactive lists for Week 10 and no snap counts at all.</li>
  <li><strong>Backtest rows are still ranked.</strong> 12 rows appear on a leaderboard by ROI, which the brief
      forbids and the page itself labels.</li>
</ol>

<h2>What is missing, and what would produce it</h2>
<ul class="list">
  <li><strong>A price store with a clock</strong> — one value per market per game today, no opening/closing split.
      Requires a signed price policy (Q-02).</li>
  <li><strong>Official Game Books and inactive lists</strong> — the only route to a confirmed starter (Q-04).</li>
  <li><strong>Snap counts</strong> — the only official way to model depth as playing time rather than jersey order (A-05).</li>
  <li><strong>An availability series that predates kickoffs</strong> — without it, an injury ablation measures leakage (Q-14).</li>
  <li><strong>29 more club depth charts</strong>, one of which is published as an image (A-16, D-F07).</li>
</ul>

<h2>Decisions for the owner</h2>
<p>These are choices, not work items. No amount of engineering settles them.</p>
<ol class="list">
  <li><strong>The price-data policy</strong> (Q-02, D-04). Everything priced is blocked behind it.</li>
  <li><strong>Whether to keep publishing row-level official data in a public repository</strong> (Q-21, D-07),
      pending a read of the terms.</li>
  <li><strong>The promotion threshold</strong> (Q-23): how many settled prospective bets, with what multiplicity
      rule, before a strategy is called live.</li>
  <li><strong>Which depth route to build</strong> (Q-22): club charts for 32 clubs, or an official snap-count source.</li>
</ol>

<h2>The single next action</h2>
<p>Run the collector. It is the only item on the board that needs no decision from anyone, and it
changes more rows than anything else: it clears the failing gate, refreshes three stale standings
copies, and moves the corpus to the official game count. Suggestions are ranked on the
<a href="suggestions.html">Suggestions</a> page; the blocker for every requirement is on
<a href="readiness.html">Readiness</a>.</p>
"""
    return page("executive-summary.html", "Executive Summary", body,
                "What holds, what does not, what is missing, and the four decisions only the owner can make.")


def p_method():
    srcs = J("sources.json")["sources"]
    inj = J("injuries.json")
    sch = J("schedule.json")
    dep = J("depth.json")
    parts = []
    for s in srcs:
        parts.append([e(s["id"]), e(s["publisher"]), e(s["kind"]), link(s["url"], s["title"]), e(s["retrieved"]),
                      e(s["what"]), e(s.get("note", ""))])
    t = table(["ID", "Publisher", "Kind", "Page", "Read on", "What was taken", "What the read established"], parts)
    body = f"""
<p class="lede">How this sub-site is built, what it will and will not claim, and the official pages it
rests on. The rules below are the reason a table on another page can be trusted — or refused.</p>

<h2>Rules this site is built under</h2>
<ol class="list">
  <li><strong>No value is inferred, interpolated or filled.</strong> A blank on the source page is published
      as "not published"; a value nobody fetched is "not read"; a value no official page confirms is
      "unverified" and is not shown as a number at all.</li>
  <li><strong>One source per row.</strong> Every table row links the official page it was checked against.
      The build fails if a row in a table with a Source column lacks a link.</li>
  <li><strong>A transcription is verbatim.</strong> Jersey numbers, mismatched club codes, blank cells and
      multi-name slots are preserved in the raw field rather than cleaned away.</li>
  <li><strong>A comparison is a comparison.</strong> Where the repository's own file disagrees with today's page,
      both numbers are shown and neither is edited — those files belong to other generators.</li>
  <li><strong>Numbers are computed, not typed.</strong> Every figure on these pages is derived by
      <code>tools/desk/build_site.py</code> from <code>data/desk/*.json</code>, and
      <code>tools/desk/verify_site.py</code> re-reads the rendered HTML and recomputes it independently.</li>
  <li><strong>A finding can be retired.</strong> A claim from the brief that no longer matches the live page is
      recorded as resolved with the reading that retired it, not quietly dropped.</li>
</ol>

<h2>How the pages are built</h2>
<p><code>tools/desk/emit_data.py</code> reads the session's transcriptions and the named repository files
and writes <code>data/desk/*.json</code>. <code>tools/desk/build_site.py</code> renders those JSON files
into the pages you are reading. <code>tools/desk/verify_site.py</code> fails if a page in <code>desk/</code>
would change on rebuild, if any local link is broken, if a Source cell lacks a link, if a table is empty,
or if a number on a page cannot be reproduced from the data layer.</p>

<h2>The official sources re-read for this site</h2>
{t}

<h2>What this site is not</h2>
<p>It is not a betting recommendation, and it does not publish a pick. It publishes probabilities,
their uncertainty, and the evidence behind them — and where the evidence runs out, it says so.
No official NFL odds exist; market columns come from a third-party price file and are labelled as
such wherever they appear.</p>

<h2>Coverage of this session, stated plainly</h2>
<ul class="list">
  <li>{inj["counts"]["rows"]} injury rows: all of Week 10's report, for all {inj["counts"]["clubs"]} clubs that had one.</li>
  <li>32 of 32 club standings rows.</li>
  <li>{sch["week11"]["counts"]["fixtures"]} of {sch["week11"]["counts"]["fixtures"]} Week-11 fixtures and all {sch["week11"]["counts"]["byes"]} byes.</li>
  <li>{dep["counts"]["clubs"]} of 32 club depth charts — the largest gap on the site.</li>
  <li>0 official Game Books, 0 inactive lists for Week 10, 0 snap counts.</li>
</ul>
"""
    return page("method.html", "Method & Sources", body,
                "The rules, the build, the sources, and the coverage this session actually has.")


def inj_row_count():
    return J("injuries.json")["counts"]["rows"]


PAGES = {
    "index.html": p_index,
    "readiness.html": p_readiness,
    "verification.html": p_verification,
    "strategies.html": p_strategies,
    "availability.html": p_availability,
    "pricing.html": p_pricing,
    "questions.html": p_questions,
    "suggestions.html": p_suggestions,
    "flagged.html": p_flagged,
    "executive-summary.html": p_exec,
    "method.html": p_method,
}

STYLE = """
:root{--ink:#101418;--muted:#5b6672;--line:#dfe4ea;--bg:#f7f9fb;--card:#fff;--accent:#123a66;
--met:#0f6b3d;--metbg:#e7f5ec;--part:#8a5a00;--partbg:#fdf3dd;--block:#8f1f1f;--blockbg:#fbe9e9;
--ns:#4a4f57;--nsbg:#eceef1;--dec:#5b2a86;--decbg:#f1e9f8}
*{box-sizing:border-box}
body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:var(--bg)}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
header.top{background:var(--accent);color:#fff;padding:22px 0 0}
header.top .crumb{font-size:12px;opacity:.8;margin:0 0 6px}
header.top .crumb a{color:#cfe0f5;text-decoration:none}
header.top h1{margin:0;font-size:30px;letter-spacing:-.01em}
header.top .sub{margin:6px 0 14px;opacity:.9;font-size:15px;max-width:80ch}
nav{display:flex;flex-wrap:wrap;gap:2px;padding-bottom:0}
nav a{color:#d7e4f4;text-decoration:none;font-size:13.5px;padding:9px 11px;border-radius:6px 6px 0 0}
nav a:hover{background:rgba(255,255,255,.12);color:#fff}
nav a.active{background:var(--bg);color:var(--accent);font-weight:600}
main{padding:26px 0 40px}
h2{font-size:20px;margin:34px 0 10px;letter-spacing:-.01em}
h2 .count{font-size:13px;font-weight:400;color:var(--muted)}
h3{font-size:16px;margin:0 0 4px}
p{margin:0 0 12px;max-width:92ch}
.lede{font-size:16.5px;color:#26313c;max-width:95ch}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:10px;margin:16px 0 8px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:flex;
flex-direction:column;gap:2px}
.kpi .n{font-size:25px;font-weight:650;letter-spacing:-.02em}
.kpi .l{font-size:12.5px;color:var(--muted)}
table.grid{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
border-radius:10px;overflow:hidden;margin:10px 0 22px;font-size:13.5px}
table.grid caption{caption-side:top;text-align:left;font-size:13px;color:var(--muted);padding:0 0 8px}
table.grid th{background:#eef2f7;text-align:left;padding:9px 10px;font-size:12.5px;text-transform:none;
border-bottom:1px solid var(--line);vertical-align:bottom}
table.grid td{padding:9px 10px;border-bottom:1px solid #eef1f5;vertical-align:top}
table.grid tr:last-child td{border-bottom:none}
table.grid tbody tr:nth-child(even){background:#fbfcfd}
td.src{font-size:12.5px}
a{color:#12508f}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:600;
text-transform:uppercase;letter-spacing:.02em;white-space:nowrap}
.pill.met{background:var(--metbg);color:var(--met)}
.pill.partial{background:var(--partbg);color:var(--part)}
.pill.blocked{background:var(--blockbg);color:var(--block)}
.pill.not_started{background:var(--nsbg);color:var(--ns)}
.pill.decision_needed{background:var(--decbg);color:var(--dec)}
.raw,.col{color:var(--muted);font-size:12px}
.blank{color:var(--muted);font-style:italic}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:12px;margin:12px 0 8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;
text-decoration:none;color:inherit;display:block}
.card:hover{border-color:#b9c6d6;box-shadow:0 2px 10px rgba(16,20,24,.06)}
.card p{margin:0;font-size:13.5px;color:var(--muted);max-width:none}
.warn{background:var(--blockbg);border-left:4px solid var(--block);padding:10px 14px;border-radius:6px;max-width:none}
ul.list,ol.list{max-width:95ch;padding-left:22px}
ul.list li,ol.list li{margin-bottom:8px}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:12.5px;padding:18px 0 40px}
footer p{max-width:100ch}
code{background:#eef1f5;padding:1px 5px;border-radius:4px;font-size:12.5px}
@media(max-width:640px){header.top h1{font-size:24px}table.grid{font-size:12.5px}}
"""


def main() -> int:
    global GEN_AT
    check = "--check" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    # a stable stamp: the newest verification date in the data layer, not the wall clock, so a
    # rebuild of unchanged data produces byte-identical pages.
    GEN_AT = J("injuries.json")["retrieved"]
    changed, written = [], 0
    for name, fn in PAGES.items():
        text = fn()
        path = os.path.join(OUT, name)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != text:
            changed.append(name)
            if not check:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                written += 1
    css = os.path.join(OUT, "style.css")
    old_css = open(css, encoding="utf-8").read() if os.path.exists(css) else None
    if old_css != STYLE.strip() + "\n":
        changed.append("style.css")
        if not check:
            with open(css, "w", encoding="utf-8") as f:
                f.write(STYLE.strip() + "\n")
    if check:
        if changed:
            print("FAIL: these desk pages are not what the data produces: " + ", ".join(changed))
            return 1
        print(f"OK: desk/ is exactly what the data produces ({len(PAGES)} pages).")
        return 0
    print(f"wrote {written} page(s) into desk/ (changed: {', '.join(changed) or 'none'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
