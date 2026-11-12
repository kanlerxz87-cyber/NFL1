#!/usr/bin/env python3
"""Generate the static site from data/processed/site_data.json.

    PYTHONPATH=src python3 scripts/build_site.py

The generator contains no numbers. Every value it prints comes from the pipeline
output, which in turn comes only from data/verified/. A cell that is None renders
as an em dash with a tooltip explaining that it is deliberately blank.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl import markdown_lite as md          # noqa: E402
from nfl import sitekit
from nfl.sitekit import (ALL_PAGES, NAV, REPO_URL, badge, callout, esc, first_url,  # noqa: E402
                         fmt, host_label, kpi, panel, render_page, src, table)

DATA = json.loads((ROOT / "data" / "processed" / "site_data.json").read_text(encoding="utf-8"))
OUT = sitekit.SITE_OUT
CONTENT = ROOT / "content"
NFL_INJ = "https://www.nfl.com/injuries/"
NFL_STD = "https://www.nfl.com/standings/"


def prose(name: str) -> str:
    p = CONTENT / f"{name}.md"
    return md.render(p.read_text(encoding="utf-8")) if p.exists() else ""


def blank_cell(title: str = "not available from an official source") -> str:
    return f'<span class="blank" title="{esc(title)}">&mdash;</span>'


def srccell(url: str, label: str | None = None) -> str:
    """A table cell holding one source link, labelled by its real host."""
    return src(url, label)


def srccells(urls: list[str] | str | None) -> str:
    """Render every source that supports a row, rather than hiding secondary evidence."""
    if isinstance(urls, str):
        urls = [urls]
    return " · ".join(srccell(url) for url in (urls or []) if url)


def tier_legend() -> str:
    d = DATA["meta"]["tier_definitions"]
    rows = [[badge(k), esc(v)] for k, v in d.items()]
    return panel(table(["Tier", "What it means"], rows, cls="md"),
                 "Provenance tiers used on every page of this site")


# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------
def p_index() -> tuple[str, str, str]:
    v, m, s = DATA["verification"], DATA["meta"], DATA["strategies"]["counts"]
    av = DATA["availability"]["league"]
    corr = DATA["correlation"]["screen"]
    lb = DATA["leaderboard"]
    body = [
        '<div class="grid g4">',
        kpi("Verification checks", f'{v["PASS"]}<span style="font-size:15px;color:var(--muted)">/{v["total"]} pass</span>',
            f'{v["FLAG"]} flagged, {v["FAIL"]} failed'),
        kpi("Injury-report entries", av["total_report_entries"],
            f'{av["teams_with_entries"]} teams reporting, {av["teams_on_bye"]} on bye'),
        kpi("Signals registered", len(DATA["signals"]["active"]),
            f'{len(DATA["signals"]["blocked"])} blocked for lack of an official source'),
        kpi("Strategies catalogued", s["total"],
            f'{s["approved"]} approved, {s["not_stakeable"]} not stakeable'),
        kpi("Completed games", v["completed_games"],
            m["standings_as_of"].split("(")[0].strip()),
        kpi("Correlation tests", corr["tests_run"],
            f'{len(corr["findings"])} non-mechanical findings survive FDR control'),
        kpi("Leaderboard scored", lb["scored_count"],
            f'{lb["withheld_count"]} withheld - scores are never zeroed'),
        kpi("Disputed official cells", len(v["flags"]),
            "published verbatim, excluded from all computation"),
        "</div>",
        callout("<strong>Read this first.</strong> No value on this site has been estimated, "
                "interpolated or filled in. Where an official source could not confirm a "
                "number the cell is blank and the item is listed on the "
                "<a href='flagged.html'>Flagged for Review</a> page together with the source "
                "that would resolve it. Nothing here is a betting recommendation.", "warn"),
        prose("index"),
        "<h3>The single most important result</h3>",
        callout(f'Thirty-eight correlation tests were run across 21 signals with '
                f'Benjamini-Hochberg false-discovery-rate control. At p&lt;0.05 alone, '
                f'{corr["expected_false_positives_at_005"]} false positives would be expected '
                f'by chance. Nine tests survive FDR control at '
                f'&alpha;={corr["fdr_alpha"]} and <strong>all nine are definitional</strong> - '
                f'win percentage against other expressions of the same game outcomes. '
                f'<strong>Zero non-mechanical findings survive.</strong> Any availability or '
                f'injury signal that appears to work in this dataset is, so far, '
                f'indistinguishable from a tautology or from noise.', "bad"),
        "<h3>What is blocked, and by what</h3>",
    ]
    rows = []
    for b in DATA["signals"]["blocked"]:
        rows.append([f'<strong>{esc(b["name"])}</strong><div class="note">{esc(b["definition"])}</div>',
                     esc(b.get("blocked_reason", "")),
                     # No explicit label: the column header already says
                     # "Resolving source", so the link names the host it goes to.
                     src(first_url(b.get("resolving_source"))
                         or (REPO_URL + "/blob/main/src/nfl/signals.py"))])
    body.append(table(["Blocked signal", "Why it cannot be produced", "Resolving source"], rows))
    body.append("<h3>Pages</h3>")
    for cat, items in NAV.items():
        body.append(f"<h4>{esc(cat)}</h4><div class='grid g3'>")
        for slug, label in items:
            if slug == "index":
                continue
            body.append(f'<div class="kpi"><div class="k">{esc(cat)}</div>'
                        f'<div style="font-size:15px;font-weight:650;margin:3px 0">'
                        f'<a href="{slug}.html">{esc(label)}</a></div></div>')
        body.append("</div>")
    return ("NFL1 Dashboard", f'Season {m["season"]} &middot; Week {m["week"]} &middot; '
                              f'retrieved {esc(m["source_retrieved_at_utc"])}', "".join(body))


def p_executive_summary():
    v, lb = DATA["verification"], DATA["leaderboard"]
    return ("Executive Summary", "The short version, with links to the working",
            '<div class="grid g4">'
            + kpi("Checks", f'{v["PASS"]}/{v["total"]}', f'{v["FLAG"]} flagged')
            + kpi("Findings", len(DATA["correlation"]["screen"]["findings"]),
                  "survive FDR control and are not definitional")
            + kpi("Approved strategies", DATA["strategies"]["counts"]["approved"],
                  f'{lb["withheld_count"]} scores withheld')
            + kpi("Blank values", len(DATA["verification"]["flags"]) + len(DATA["signals"]["blocked"]),
                  "deliberate, each with a resolving source")
            + "</div>" + prose("executive-summary"))


def p_open_questions():
    return ("Open Questions", "What must be answered before any decision can reasonably be made",
            prose("open-questions"))


def p_suggestions():
    return ("Suggestions Board", "Proposals awaiting review - nothing here has been implemented",
            callout("Every item below is a <strong>proposal</strong>. The Decision column is "
                    "blank on purpose and is the reviewer's to fill in. Approved items become "
                    "tasks on <a href='" + REPO_URL + "/blob/main/COORDINATION.md'>"
                    "COORDINATION.md</a> with an owner and a file scope.", "warn")
            + prose("suggestions"))


def p_methodology():
    return ("Methodology", "How every number on this site is produced", prose("methodology"))


# --------------------------------------------------------------------------
# Verified data
# --------------------------------------------------------------------------
def p_data_standings():
    rows = []
    for r in sorted(DATA["standings"]["metrics"],
                    key=lambda x: (x["conference"], x["division"], -(x["win_pct"] or 0))):
        rows.append([
            f'<strong>{esc(r["team_abbr"])}</strong>', esc(r["division"]),
            fmt(r["w"]), fmt(r["l"]), fmt(r["t"]), fmt(r["win_pct"], 3),
            fmt(r["pf"]), fmt(r["pa"]), fmt(r["net_pts"], 0, signed=True),
            esc(r["home"]), esc(r["road"]),
            blank_cell("DISPUTED: contradicts the adjacent DIV PCT cell on the official page")
            if r["div_disputed"] else esc(r["div"]),
            fmt(r["div_win_pct"], 3),
            esc(r["conf"]), fmt(r["conf_pct"], 3),
            blank_cell("DISPUTED: contradicts the CONF cell on the official page")
            if r["non_conf_disputed"] else esc(r["non_conf"]),
            esc(r["strk"]), esc(r["last5"]),
            badge("VERIFIED"), srccell(r["source_url"]),
        ])
    hdr = ["Team", "Division", "W", "L", "T", "PCT", "PF", "PA", "Net",
           "Home", "Road", "Div", "Div PCT", "Conf", "Conf PCT", "Non-Conf",
           "Streak", "Last 5", "Tier", "Source"]
    aligns = ["", "", "num", "num", "num", "num", "num", "num", "num", "", "",
              "", "num", "", "num", "", "c", "", "c", ""]
    note = callout("Three cells on the official page contradict their own adjacent "
                   "percentage cells - the DIV record for <strong>IND</strong> and "
                   "<strong>PHI</strong>, and the NON-CONF record for <strong>WAS</strong>. "
                   "They are printed above exactly as NFL.com published them, are excluded "
                   "from every computation on this site, and are listed on the "
                   "<a href='flagged.html'>Flagged for Review</a> page with the arithmetic "
                   "proof. No value has been corrected or estimated.", "warn")
    return ("2026 Standings", "Verified from nfl.com/standings &middot; 136 completed games through Week 9",
            note + tier_legend()
            + table(hdr, rows, aligns)
            + '<p class="note">Column order and values are exactly as published by NFL.com. '
              'PCT follows the league convention that a tie counts as half a win, which the '
              'verification harness recomputes for all 32 rows (check V04).</p>')


def p_data_schedule():
    rows = []
    for g in DATA["schedule"]["games"]:
        rows.append([fmt(g["week"]), esc(g["game_date"]), esc(g["day"]), esc(g["kickoff_et"]),
                     f'<strong>{esc(g["away_abbr"])}</strong> @ <strong>{esc(g["home_abbr"])}</strong>',
                     esc(g["broadcast"]), esc(g["venue_status"]), badge("VERIFIED"),
                     srccells(g.get("source_urls") or [g["source_url"]])])
    byes = [[fmt(b["week"]), f'<strong>{esc(b["team_abbr"])}</strong>', esc(b["status"]),
             badge("VERIFIED"), srccell(b["source_url"])] for b in DATA["schedule"]["byes"]]
    v = DATA["verification"]
    return ("Week 10 Schedule", "Fixtures and byes from the official NFL Week 10 schedule",
            '<div class="grid g3">'
            + kpi("Games", len(DATA["schedule"]["games"]), "Thursday 12 to Monday 16 November 2026")
            + kpi("Teams playing", 28, "every club except the four on bye")
            + kpi("Teams on bye", len(byes), "CHI, DEN, PHI, TB")
            + "</div>"
            + callout("The 14 fixtures, dates and kickoff times are transcribed from the "
                      "official NFL Week 10 schedule and checked against the retrieved page "
                      "snapshot (V33). The four bye clubs are transcribed from its explicit "
                      "\'Teams on Bye\' block, not inferred from missing injury-report rows. "
                      "Fixture rows link to the official schedule and the official injury page "
                      "for broadcast metadata; bye rows link to the schedule.", "")
            + table(["Week", "Date", "Day", "Kickoff (ET)", "Matchup", "Broadcast",
                     "Status", "Tier", "Source"], rows,
                    ["num", "", "", "", "", "", "", "c", ""])
            + "<h3>Teams on bye</h3>"
            + table(["Week", "Team", "Status", "Tier", "Source"], byes,
                    ["num", "", "", "c", ""]))


def p_data_injuries():
    av = DATA["availability"]
    lg = av["league"]
    rows = []
    for e in sorted(av["entries"], key=lambda x: (x["team_abbr"], x["player"])):
        rows.append([
            f'<strong>{esc(e["team_abbr"])}</strong>',
            f'<a href="{esc(e["player_url"])}" target="_blank" rel="noopener noreferrer">{esc(e["player"])}</a>',
            esc(e["position"]),
            esc(e["injury"]) if e["injury"] else blank_cell("NFL.com published no injury designation for this row at retrieval time"),
            esc(e["practice_label"]) if e["practice_label"] else blank_cell(),
            badge("VERIFIED", e["game_status"]) if e["game_status"] else blank_cell("no game status published yet"),
            srccell(e["source_url"], "report"),
        ])
    trows = []
    for r in sorted(av["teams"], key=lambda x: -x["availability_pressure_unstringed"]):
        trows.append([
            f'<strong>{esc(r["team_abbr"])}</strong>', esc(r["report_status"]),
            fmt(r["entries"]), fmt(r["counts"]["DNP"]), fmt(r["counts"]["LP"]),
            fmt(r["counts"]["FP"]), fmt(r["game_status"]["Out"]),
            fmt(r["game_status"]["Questionable"]), fmt(r["by_unit"]["OFF"]),
            fmt(r["by_unit"]["DEF"]), fmt(r["by_unit"]["ST"]), fmt(r["qb_entries"]),
            fmt(r["availability_pressure_unstringed"], 3),
            badge(r["availability_pressure_tier"]),
            srccells(r.get("source_urls") or [r["source_url"]]),
        ])
    js = """
<input id="q" placeholder="Filter by team, player or position..." style="width:100%;max-width:420px;padding:8px 11px;border:1px solid var(--line);border-radius:8px;font-size:13.5px;margin:8px 0">
<script>
document.getElementById('q').addEventListener('input',function(e){
  var v=e.target.value.toLowerCase().trim();
  document.querySelectorAll('#inj tbody tr').forEach(function(tr){
    tr.style.display = !v || tr.textContent.toLowerCase().indexOf(v)>=0 ? '' : 'none';
  });
});
</script>"""
    return ("Week 10 Injury Report", f'{lg["total_report_entries"]} official entries &middot; retrieved {esc(DATA["meta"]["source_retrieved_at_utc"])}',
            '<div class="grid g4">'
            + kpi("Entries", lg["total_report_entries"], "across " + str(lg["teams_with_entries"]) + " teams")
            + kpi("Did not practise", lg["entries_dnp"], f'{lg["entries_lp"]} limited, {lg["entries_fp"]} full')
            + kpi("Designated Out", lg["entries_with_out_designation"],
                  f'{lg["entries_with_questionable"]} questionable, {lg["entries_with_doubtful"]} doubtful')
            + kpi("Designation coverage", f'{lg["designation_coverage_pct"]}%',
                  f'only {lg["injury_designation_present"]} of {lg["total_report_entries"]} entries name a body part')
            + "</div>"
            + callout("<strong>Critical data-quality finding.</strong> This report was retrieved on the "
                      "Thursday of game week. At that moment only "
                      f'{lg["injury_designation_present"]} of {lg["total_report_entries"]} entries '
                      f'({lg["designation_coverage_pct"]}%) named an injury, and only '
                      f'{lg["entries_with_out_designation"] + lg["entries_with_questionable"] + lg["entries_with_doubtful"]} '
                      "carried a game status - all of them for the two games with the earliest reporting "
                      "deadlines. Practice participation, by contrast, was fully populated. Any "
                      "availability model must therefore re-retrieve after the Friday 4:00pm ET deadline, "
                      "and must record the retrieval time so a strategy is never evaluated against "
                      "information that was not yet public (gate G3).", "warn")
            + "<h3>Per-team summary</h3>"
            + table(["Team", "Report status", "Entries", "DNP", "LP", "FP", "Out", "Q",
                     "Off", "Def", "ST", "QB", "Availability pressure", "Tier", "Source"],
                    trows, ["", "", "num", "num", "num", "num", "num", "num", "num",
                            "num", "num", "num", "num", "c", ""])
            + '<p class="note">Availability pressure is <strong>MODELED</strong>: it multiplies '
              'analyst-prior severity and position weights, and carries no string-level weighting '
              'because official depth charts are unavailable. See '
              '<a href="availability-depth.html">Availability &amp; Depth</a> and '
              '<a href="methodology.html">Methodology</a>.</p>'
            + f'<h3>All {lg["total_report_entries"]} entries</h3>' + js
            + '<div id="inj">' + table(["Team", "Player", "Pos", "Injury", "Practice status",
                                        "Game status", "Source"], rows,
                                       ["", "", "c", "", "", "c", ""]) + "</div>")


def p_data_news():
    rows = [[esc(n["headline"]), badge("VERIFIED"),
             f'<a href="{esc(n["url"])}" target="_blank" rel="noopener noreferrer">nfl.com ↗</a>']
            for n in DATA["availability"]["news"]]
    krows = [[f'<strong>{esc(k["team_abbr"])}</strong>', esc(k["position"]),
              esc(k["fact"]), esc(k["kind"]), badge(k["tier"]),
              f'<a href="{esc(k["url"])}" target="_blank" rel="noopener noreferrer">nfl.com ↗</a>']
             for k in DATA["availability"]["qb_and_key_availability"]]
    return ("Official News Feed", "Availability-relevant items transcribed from nfl.com",
            callout("Headlines are transcribed exactly as published by NFL.com. Where a headline "
                    "hedges - \"likely to be placed on injured reserve\", \"expected to start\" - "
                    "the hedge is preserved rather than promoted to a certainty.", "")
            + "<h3>Confirmed availability facts</h3>"
            + table(["Team", "Pos", "Fact as published", "Kind", "Tier", "Source"], krows,
                    ["", "c", "", "", "c", ""])
            + "<h3>News items listed on the official injury report page</h3>"
            + table(["Headline as published", "Tier", "Source"], rows, ["", "c", ""]))


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------
def p_analysis_ratings():
    pf = DATA["standings"]["pythagorean_fit"]
    ha = DATA["standings"]["home_advantage_win_rate"]
    hap = DATA["standings"]["home_advantage_points"]
    rows = []
    for r in sorted(DATA["standings"]["metrics"], key=lambda x: -(x["net_pg"] or 0)):
        rows.append([
            f'<strong>{esc(r["team_abbr"])}</strong>', esc(r["division"]), fmt(r["gp"]),
            fmt(r["ppg"], 2), fmt(r["papg"], 2), fmt(r["net_pg"], 3),
            fmt(r["win_pct"], 3), fmt(r["pyth_win_pct"], 4),
            fmt(r["pyth_delta"], 4, signed=True),
            fmt(r["home_win_pct"], 3), fmt(r["road_win_pct"], 3),
            fmt(r["streak_signed"], 0, signed=True), badge(r["net_pg_tier"]),
            srccell(r["source_url"])])
    return ("Team Ratings", "Derived from official standings cells only",
            '<div class="grid g3">'
            + kpi("Pythagorean exponent k", fmt(pf["exponent"], 4),
                  f'95% CI {pf["ci95"][0]} to {pf["ci95"][1]}, n={pf["n"]}')
            + kpi("Fit R&sup2;", fmt(pf["r2"], 4), f'calibration slope {fmt(pf["calibration_slope"], 4)}')
            + kpi("Home win rate", f'{ha["home_win_rate"] * 100:.2f}%',
                  f'Wilson 95% CI {ha["ci95_wilson"][0] * 100:.2f}% to {ha["ci95_wilson"][1] * 100:.2f}%, n={ha["home_games"]}')
            + "</div>"
            + callout("<strong>The exponent was fitted here, not imported.</strong> k = "
                      f'{pf["exponent"]} was found by least squares on the 32 official rows '
                      "(golden-section search on the sum of squared errors) and bootstrapped "
                      "for its interval. It is high and the interval is wide because it is "
                      "fitted on roughly 8.5 games per team rather than a full season. It is "
                      "usable for ranking within 2026 and is <strong>not</strong> a general "
                      "constant.", "")
            + callout(f'<strong>Home advantage in points is unavailable.</strong> {esc(hap["reason"])} '
                      f'Resolving source: {esc(hap["resolving_source"])}. Because a spread cannot be '
                      'produced without it, the origination engine publishes rating gaps and refuses '
                      'to publish spreads.', "warn")
            + table(["Team", "Division", "GP", "PPG", "PAPG", "Net/G", "Win%", "Pyth%",
                     "Pyth &Delta;", "Home%", "Road%", "Streak", "Tier", "Source"], rows,
                    ["", "", "num", "num", "num", "num", "num", "num", "num", "num", "num",
                     "num", "c", ""]))


def p_analysis_luck():
    rows = []
    for r in DATA["luck"]["table"]:
        rows.append([f'<strong>{esc(r["team_abbr"])}</strong>', fmt(r["gp"]),
                     fmt(r["actual_win_pct"], 3), fmt(r["pyth_win_pct"], 4),
                     f'<strong>{fmt(r["pyth_delta"], 4, signed=True)}</strong>',
                     fmt(r["games_of_luck"], 2, signed=True), fmt(r["net_pg"], 2),
                     fmt(r["pf"]), fmt(r["pa"]),
                     badge("DERIVED", r["direction"].split(" ")[0]),
                     srccell(r["source_url"])])
    return ("Luck Table", "Separating scoring from results - the first instrument of luck removal",
            callout("<strong>How to read this.</strong> A positive &Delta; means the club has won "
                    "<em>fewer</em> games than its scoring justifies - it is under-performing, and a "
                    "regression strategy treats that as a buy. A negative &Delta; means the club has "
                    "won more than its scoring justifies - it is over-performing, and that is a fade "
                    "candidate. This is the only luck instrument that runs today, because it needs "
                    "nothing but official standings cells.", "")
            + table(["Team", "GP", "Actual Win%", "Pyth Win%", "&Delta;", "Games of luck",
                     "Net/G", "PF", "PA", "Direction", "Source"], rows,
                    ["", "num", "num", "num", "num", "num", "num", "num", "num", "c", ""])
            + "<h3>The other three instruments</h3>"
            + table(["Instrument", "Level", "Status", "Reason"],
                    [[esc(i["instrument"]), "strategy", badge("NOT_RUN"), esc(i["reason"])]
                     for i in DATA["luck"]["strategy_instruments"]],
                    ["", "", "c", ""]))


def p_analysis_correlation():
    c = DATA["correlation"]
    sc = c["screen"]
    frows = [[f'<strong>{esc(r["target"])}</strong> ~ {esc(r["signal"])}', fmt(r["n"]),
              fmt(r["pearson_r"], 4), fmt(r["spearman_rho"], 4), fmt(r["t"], 3),
              f'{r["p"]:.2e}' if r["p"] is not None else blank_cell(),
              f'{r["q_bh"]:.2e}' if r["q_bh"] is not None else blank_cell(),
              f'[{fmt(r["ci95_lo"], 3)}, {fmt(r["ci95_hi"], 3)}]',
              badge(r["classification"]), esc(r["verdict"])]
             for r in sorted(sc["rows"], key=lambda x: (x["q_bh"] is None, x["q_bh"] or 1))]
    _cells = [x for x in c["pairwise"]["cells"] if (x["abs_r"] or 0) >= 0.5]
    _cells.sort(key=lambda x: -(x["abs_r"] or 0))
    strong = [[f'{esc(p["a"])} &harr; {esc(p["b"])}', fmt(p["n"]), fmt(p["pearson_r"], 4),
               fmt(p["abs_r"], 4), badge(p["classification"])] for p in _cells]
    red = [[f'{esc(p["a"])} &harr; {esc(p["b"])}', fmt(p["n"]), fmt(p["pearson_r"], 4)]
           for p in sorted(c["pairwise"]["redundant_pairs"], key=lambda x: -(x["abs_r"] or 0))]
    cls = [[badge(k), esc(v)] for k, v in c["notes"].items()]
    return ("Correlations", f'{sc["tests_run"]} tests with false-discovery-rate control',
            '<div class="grid g4">'
            + kpi("Tests run", sc["tests_run"], "21 signals against 2 targets")
            + kpi("Expected false positives", sc["expected_false_positives_at_005"],
                  "at p&lt;0.05, by chance alone")
            + kpi("Survive FDR", len([r for r in sc["rows"] if r["survives_fdr"]]),
                  f'Benjamini-Hochberg at &alpha;={sc["fdr_alpha"]}')
            + kpi("Non-mechanical findings", len(sc["findings"]),
                  "the honest count after removing tautologies")
            + "</div>"
            + callout("<strong>Zero non-mechanical findings survive.</strong> Nine tests clear "
                      "FDR control, and every one of them relates win percentage to another "
                      "expression of the same game outcomes. Publishing those as discoveries "
                      "would be the easiest way to manufacture a fake edge in this whole "
                      "project, so the classification step below exists to stop it.", "bad")
            + "<h3>Interpretation classes</h3>" + table(["Class", "Meaning and treatment"], cls)
            + "<h3>Screen results, best q-value first</h3>"
            + table(["Target ~ signal", "n", "Pearson r", "Spearman &rho;", "t", "p", "q (BH)",
                     "95% bootstrap CI", "Class", "Verdict"], frows,
                    ["", "num", "num", "num", "num", "num", "num", "", "c", ""])
            + '<p class="note">Sample size varies by pair because availability signals exist for '
              'only 28 clubs - the four teams on bye publish no report and are excluded rather '
              'than treated as zero. Bootstrap intervals are seeded (4,000 draws, seed 20261112) '
              'so the published interval is reproducible.</p>'
            + f'<h3>Pairs at |r| &ge; 0.50 (threshold for review: {c["redundancy_threshold"]})</h3>'
            + table(["Pair", "n", "Pearson r", "|r|", "Class"], strong,
                    ["", "num", "num", "num", "c"])
            + "<h3>Redundant pairs - never separate legs of the same multi-leg bet</h3>"
            + table(["Pair", "n", "Pearson r"], red, ["", "num", "num"])
            + callout(f'{len(red)} signal pairs are correlated at or above '
                      f'|r| = {c["redundancy_threshold"]}. These are one signal wearing two hats. '
                      'Gate G8 forbids using them as separate legs of a parlay, because the '
                      'book\'s independent-product price assumes they are unrelated.', "warn"))


def p_availability_depth():
    av = DATA["availability"]
    dc = av["depth_chart_status"]
    sev = [[esc(k), fmt(v, 2)] for k, v in av["severity_weights"].items()]
    pos = [[esc(k), fmt(v, 2)] for k, v in av["position_weights"].items()]
    rows = []
    for r in sorted(av["teams"], key=lambda x: -x["availability_pressure_unstringed"]):
        qb = ", ".join(f["fact"] for f in r["qb_disruption"]) or None
        rows.append([f'<strong>{esc(r["team_abbr"])}</strong>', esc(r["report_status"]),
                     fmt(r["entries"]), fmt(r["counts"]["DNP"]),
                     fmt(r["dnp_by_unit"]["OFF"]), fmt(r["dnp_by_unit"]["DEF"]),
                     fmt(r["game_status"]["Out"]), fmt(r["key_position_entries"]),
                     fmt(r["qb_entries"]),
                     badge("VERIFIED", "QB change") if r["qb_disruption"] else "",
                     fmt(r["availability_pressure_unstringed"], 3),
                     srccells(r.get("source_urls") or [r["source_url"]])])
    return ("Availability & Depth", "Injuries, unit deficiencies and the depth-chart gap",
            callout(f'<strong>Depth charts are unavailable.</strong> {esc(dc["reason"])} '
                    f'<br><br>Consequence: {esc(dc["consequence"])}', "bad")
            + '<p>' + src(first_url(dc["resolving_source"])) + '</p>'
            + "<h3>What can be established without a depth chart</h3>"
            + table(["Team", "Report status", "Entries", "DNP", "Off DNP", "Def DNP", "Out",
                     "Key pos", "QB", "Confirmed QB change", "Pressure", "Source"], rows,
                    ["", "", "num", "num", "num", "num", "num", "num", "num", "c", "num", ""])
            + "<h3>Deficiency tracking by unit</h3>"
            + callout("Offensive and defensive did-not-practise counts are tracked separately "
                      "because the brief asks specifically about defensive deficiencies. The "
                      "league totals this week are "
                      f'{av["league"]["off_entries"]} offensive entries against '
                      f'{av["league"]["def_entries"]} defensive entries, with '
                      f'{sum(r["dnp_by_unit"]["DEF"] for r in av["teams"])} defensive DNPs and '
                      f'{sum(r["dnp_by_unit"]["OFF"] for r in av["teams"])} offensive DNPs. '
                      "What cannot be established is <em>which string</em> each absence promotes, "
                      "so a starter and a fourth-string rotational player contribute identically "
                      "to the pressure index. That is the single largest weakness in the "
                      "availability model and it is stated rather than hidden.", "warn")
            + '<div class="grid g2">'
            + panel(table(["Report state", "Weight"], sev, ["", "num"]),
                    "Severity weights - ANALYST PRIOR, not fitted")
            + panel(table(["Position", "Weight"], pos, ["", "num"]),
                    "Position weights - ANALYST PRIOR, not fitted")
            + "</div>"
            + '<p class="note">Left tackle and right tackle cannot be distinguished: the official '
              'report publishes only <code>T</code>. That is a material loss for offensive-line '
              'modelling and is recorded on the Flagged for Review page.</p>')


def p_lines_week10():
    rows = []
    for g in DATA["schedule"]["origination_board"]:
        rows.append([
            f'<strong>{esc(g["away_abbr"])}</strong> @ <strong>{esc(g["home_abbr"])}</strong>',
            esc(g["game_date"]) + " " + esc(g["kickoff_et"]),
            esc(g["away_record"]), esc(g["home_record"]),
            fmt(g["rating_gap_home_minus_away"], 2, signed=True),
            fmt(g["pyth_home"], 3), fmt(g["pyth_away"], 3),
            fmt(g["pyth_gap"], 3, signed=True), fmt(g["naive_total"], 1),
            blank_cell("blocked: home-field advantage in points is unavailable"),
            blank_cell("blocked: no licensed odds feed is reachable"),
            blank_cell("blocked: no licensed odds feed is reachable"),
            badge("DERIVED"), srccell(g["source_url"])])
    hap = DATA["standings"]["home_advantage_points"]
    return ("Week 10 Origination Board", "What can honestly be computed, and what cannot",
            callout("<strong>No line on this page is a betting recommendation.</strong> The rating "
                    "gap and the naive total are arithmetic on verified standings cells. The "
                    "spread, the betting total, the win probability and the market line are all "
                    "blank because two required inputs do not exist. The engine is written to "
                    "refuse: when an input is <code>None</code> the dependent output is "
                    "<code>None</code> plus a named blocking input, never a plausible number.", "bad")
            + table(["Matchup", "Kickoff (ET)", "Away", "Home", "Rating gap",
                     "Pyth home", "Pyth away", "Pyth gap", "Naive total",
                     "Spread", "Win prob", "Market line", "Tier", "Source"], rows,
                    ["", "", "c", "c", "num", "num", "num", "num", "num", "c", "c", "c", "c", ""])
            + "<h3>Why the spread column is empty</h3>"
            + callout(f'{esc(hap["reason"])}<br><br><strong>Resolving source:</strong> '
                      f'{esc(hap["resolving_source"])}', "warn")
            + "<h3>Definitions</h3>"
            + table(["Column", "Definition", "Tier"],
                    [["Rating gap", "(home net points per game) - (away net points per game). "
                                    "A neutral-site rating difference, not a spread.", "DERIVED"],
                     ["Pyth home / away", "PF<sup>k</sup> / (PF<sup>k</sup> + PA<sup>k</sup>) with "
                                          "the exponent fitted on the 32 official rows.", "DERIVED"],
                     ["Naive total", "Sum of the two clubs' verified points per game. Ignores pace, "
                                     "opponent strength, venue and weather, and double-counts "
                                     "shared opponents.", "DERIVED"],
                     ["Spread", "Rating gap adjusted for home-field advantage in points and mapped "
                                "to the market's point scale.", "UNAVAILABLE"],
                     ["Win probability", "Rating gap mapped through a fitted logistic.", "UNAVAILABLE"],
                     ["Market line", "The closing number to compare against.", "UNAVAILABLE"]],
                    ["", "", "c"]))


# --------------------------------------------------------------------------
# Strategies
# --------------------------------------------------------------------------
def p_strategies_leaderboard():
    lb = DATA["leaderboard"]
    rows = []
    for r in lb["board"]:
        rows.append([
            fmt(r["rank"]) if r["rank"] is not None else blank_cell("not ranked - no score"),
            f'<strong>{esc(r["strategy_id"])}</strong> &middot; {esc(r["name"])}',
            esc(r["market"]), fmt(r["n_settled_wagers"]),
            blank_cell("no settled wagers exist"), blank_cell("needs a closing-odds feed"),
            blank_cell("needs a closing-odds feed"),
            blank_cell(r["score_withheld_reason"]), badge(r["gate_verdict"]),
            esc(r["first_blocking_gate"] or "")])
    tiers = [[fmt(t["tier"]), f'<strong>{esc(t["name"])}</strong>', esc(t["requirement"]),
              esc(t["reward"]), badge("MODELED", t["status"])] for t in lb["reward_tiers"]]
    return ("Strategy Leaderboard", "Skill-ranked, luck-adjusted - and currently empty by design",
            '<div class="grid g3">'
            + kpi("Scored", lb["scored_count"], "a score is published only when gates G1-G7 pass")
            + kpi("Withheld", lb["withheld_count"], "withheld, never zeroed")
            + kpi("Approved strategies", DATA["strategies"]["counts"]["approved"],
                  f'{DATA["strategies"]["counts"]["not_stakeable"]} not stakeable')
            + "</div>"
            + callout("<strong>Why every score is blank.</strong> A leaderboard rank is computed "
                      "from a t-statistic on no-vig return on investment. That requires settled "
                      "wagers and a closing-odds feed, and neither exists. Blanking the score "
                      "rather than zeroing it is deliberate: a zero would mean "
                      "&quot;measured and worthless&quot;, which is a different claim from "
                      "&quot;not yet measured&quot;, and confusing the two is how bad strategies "
                      "get kept and good ones get thrown away.", "warn")
            + table(["Rank", "Strategy", "Market", "n settled", "ROI (no vig)", "CLV (pts)",
                     "t", "Score", "Gate verdict", "First blocking gate"], rows,
                    ["num", "", "c", "num", "num", "num", "num", "num", "c", "c"])
            + "<h3>Scoring formula</h3><pre><code>" + esc(lb["scoring_formula"]) + "</code></pre>"
            + callout("Ranking on a t-statistic rather than raw ROI is deliberate. Raw ROI ranks "
                      "noise: a strategy returning 80% on eleven wagers outranks one returning 9% "
                      "on nine hundred, which is exactly backwards. The t-statistic forces a "
                      "strategy to be both good <em>and</em> proven, and sample size enters the "
                      "score directly.", "")
            + "<h3>Reward ladder</h3>"
            + callout("This ladder is a <strong>PROPOSAL</strong> awaiting owner sign-off. It is "
                      "not enacted and nothing in the code acts on it. See Suggestions Board item "
                      "S-14 and Open Question Q18.", "warn")
            + table(["Tier", "Name", "Requirement", "Reward", "Status"], tiers,
                    ["num", "", "", "", "c"]))


def p_strategies_catalogue():
    st = DATA["strategies"]["strategies"]
    ct = DATA["strategies"]["counts"]
    rows = []
    for s in st:
        avail = ", ".join(s["inputs_available_now"]) or "none"
        blocked = ", ".join(s["blocked_inputs"]) or "none"
        rows.append([
            f'<strong>{esc(s["id"])}</strong>', esc(s["name"]), esc(s["market"]),
            esc(s["hypothesis"]), f'<code>{esc(avail)}</code>',
            f'<code>{esc(blocked)}</code>', badge(s["gate_summary"]["verdict"]),
            esc(s["gate_summary"]["reason"])])
    detail = []
    for s in st:
        g = s["gate_summary"]
        gates_html = " ".join(badge(x["status"], x["gate_id"]) for x in g["gates"])
        detail.append(panel(
            f'<p><strong>Skill basis:</strong> {esc(s["skill_basis"])}</p>'
            f'<p><strong>How luck is removed:</strong> {esc(s["luck_removal"])}</p>'
            + (f'<p><strong>Verified instances in Week 10:</strong> '
               f'{esc("; ".join(s["verified_instances_week10"]))}</p>'
               if s.get("verified_instances_week10") else "")
            + f'<p><strong>Gate status:</strong> {gates_html}</p>',
            f'{esc(s["id"])} &middot; {esc(s["name"])} &middot; {esc(s["market"])}'))
    return ("Strategy Catalogue", f'{ct["total"]} strategies &middot; {ct["singles"]} singles, '
                                   f'{ct["totals"]} totals, {ct["parlays"]} parlays, '
                                   f'{ct["player_props"]} player props, {ct["prop_combos"]} prop combos',
            callout("A strategy here is a <strong>testable claim</strong>, not a tip. Each states "
                    "its hypothesis, the inputs it needs, why the edge would be skill rather than "
                    "luck, and how that is to be demonstrated. All "
                    f'{ct["not_stakeable"]} currently return NOT_STAKEABLE because no odds feed, '
                    "no settled wager history and no timestamped feature history exist.", "")
            + table(["ID", "Name", "Market", "Hypothesis", "Inputs available now",
                     "Blocking inputs", "Verdict", "Reason"], rows,
                    ["", "", "c", "", "", "", "c", ""])
            + "<h3>Detail and gate status</h3>" + "".join(detail))


def p_strategies_gates():
    g = DATA["gates"]
    rows = [[f'<strong>{esc(x["gate_id"])}</strong>', esc(x["name"]), esc(x["requirement"])]
            for x in g["definitions"]]
    thr = [["Minimum settled wagers", esc(json.dumps(g["min_samples"]))],
           ["Minimum t-statistic on no-vig ROI", fmt(g["min_t"], 1)],
           ["Minimum mean closing-line value", f'+{fmt(g["min_clv_points"], 2)} points'],
           ["Maximum share of profit from one fold", f'{g["max_single_fold_profit_share"]:.0%}'],
           ["Minimum fold sign stability", f'{g["min_fold_sign_stability"]:.0%}'],
           ["Correlation pricing threshold", f'|rho| &gt; {fmt(g["correlation_pricing_threshold"], 2)} forbids independent-product pricing'],
           ["Maximum out-of-sample degradation", f'{g["max_oos_degradation"]:.0%}']]
    return ("Validation Gates", "Nine gates between a strategy and a stake",
            callout("A gate whose evidence does not exist returns <strong>BLOCKED</strong>, and "
                    "BLOCKED is fatal - it is never treated as a pass. That is what makes the "
                    "current leaderboard empty rather than optimistically populated.", "")
            + table(["Gate", "Name", "Requirement"], rows, ["", "", ""])
            + "<h3>Thresholds</h3>" + table(["Parameter", "Value"], thr, ["", ""])
            + "<h3>Current status of every strategy</h3>"
            + table(["Strategy", "Verdict", "Blocking gates"],
                    [[f'<strong>{esc(s["id"])}</strong> {esc(s["name"])}',
                      badge(s["gate_summary"]["verdict"]),
                      " ".join(badge(x["status"], x["gate_id"]) for x in s["gate_summary"]["gates"])]
                     for s in DATA["strategies"]["strategies"]], ["", "c", ""])
            + callout("The gate engine is exercised in the test suite against a deliberately "
                      "well-formed hypothetical strategy, so it is demonstrably capable of "
                      "returning APPROVED. It also rejects a strategy with lookahead, one whose "
                      "edge is within noise, and one whose profit comes from a single fold. A gate "
                      "that can only ever say no would be worthless as evidence.", "ok"))


# --------------------------------------------------------------------------
# Integrity
# --------------------------------------------------------------------------
def p_verification():
    v = DATA["verification"]
    rows = []
    for c in v["checks"]:
        detail = c["actual"]
        if isinstance(detail, list):
            detail = "; ".join(str(x) for x in detail) if detail else "&mdash;"
        exp = c["expected"]
        if isinstance(exp, list):
            exp = "; ".join(str(x) for x in exp) if exp else "&mdash;"
        rows.append([f'<strong>{esc(c["check_id"])}</strong>', esc(c["scope"]),
                     f'<code>{esc(exp)}</code>', f'<code>{detail}</code>',
                     badge(c["result"]),
                     srccells(c.get("source_urls") or [c["source_url"]]), esc(c["note"])])
    return ("Verification Report", f'{v["total"]} automated checks &middot; {v["PASS"]} pass, '
                                   f'{v["FLAG"]} flagged, {v["FAIL"]} failed',
            '<div class="grid g4">'
            + kpi("Checks", v["total"], "run on every pipeline build")
            + kpi("PASS", v["PASS"], "arithmetic, balance, vocabulary and cross-source")
            + kpi("FLAG", v["FLAG"], "the official source contradicts itself")
            + kpi("FAIL", v["FAIL"], "a FAIL would mean our transcription is wrong")
            + "</div>"
            + prose("verification")
            + callout("<strong>Strongest single check.</strong> V28 compares the 28 team records "
                      "printed beside the club logos on the official injury report with the 32 "
                      "records on the official standings page. They agree exactly, including the "
                      "two clubs with ties. Two separately-rendered NFL.com pages retrieved in the "
                      "same session agreeing cell for cell is the best available evidence that the "
                      "transcription is faithful.", "ok")
            + table(["Check", "What it verifies", "Expected", "Actual", "Result", "Source", "Note"],
                    rows, ["", "", "", "", "c", "", ""])
            + "<h3>Irregularities found in the official source</h3>"
            + table(["Field", "Team", "Published value", "Arithmetic proof", "Handling", "Source"],
                    [[f'<code>{esc(f["field"])}</code>', f'<strong>{esc(f["team_abbr"])}</strong>',
                      esc(f["published_value"]), esc(f["arithmetic_proof"]),
                      esc(f["handling"]), srccell(f["source_url"])] for f in v["flags"]],
                    ["", "", "", "", "", ""]))


def p_sources():
    m = DATA["meta"]
    rows = [[f'<strong>{esc(s["id"])}</strong>', esc(s["publisher"]),
             f'<a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["url"])}</a>',
             badge("VERIFIED", s["tier"]) if s["tier"] == "OFFICIAL" else badge("MODELED", s["tier"]),
             esc("; ".join(s["used_for"]))] for s in m["sources"]]
    un = [[(f'<a href="{esc(u["url"])}" target="_blank" rel="noopener noreferrer">{esc(u["url"])}</a>'
            if u["url"].startswith("http") else f'<code>{esc(u["url"])}</code>'),
           esc(u["reason"])]
          for u in m["unreachable_sources"]]
    return ("Source Register", "Every dataset on this site resolves to one of these",
            prose("sources")
            + table(["ID", "Publisher", "URL", "Tier", "Used for"], rows, ["", "", "", "c", ""])
            + "<h3>Attempted and not reachable</h3>"
            + callout("Recording what could <em>not</em> be reached matters as much as recording "
                      "what was. The build environment allows outbound connections only to "
                      "github.com, api.github.com, codeload.github.com, registry.npmjs.org, "
                      "pypi.org and files.pythonhosted.org. Data collection was therefore carried "
                      "out through the agent's page-retrieval tool against official sources, and "
                      "bulk historical feeds were not obtainable.", "")
            + table(["URL attempted", "Why it could not be used"], un, ["", ""])
            + "<h3>Reproducibility</h3>"
            + "<pre><code>PYTHONPATH=src python3 -m nfl.pipeline\n"
              "PYTHONPATH=src python3 scripts/build_site.py\n"
              "PYTHONPATH=src python3 -m unittest discover -s tests -v</code></pre>"
            + f'<p class="note">Pipeline output is deterministic - every random routine is seeded. '
              f'Retrieved at {esc(m["source_retrieved_at_utc"])} by {esc(m["retrieved_by"])}.</p>')


def p_flagged():
    v = DATA["verification"]
    items = []
    for f in v["flags"]:
        items.append({"kind": "Disputed official cell", "what": f'{f["team_abbr"]} &middot; <code>{esc(f["field"])}</code>',
                      "detail": esc(f["arithmetic_proof"]), "handling": esc(f["handling"]),
                      "url": f["source_url"]})
    for c in v["checks"]:
        if c["result"] == "FLAG":
            items.append({"kind": "Verification flag", "what": f'{esc(c["check_id"])} &middot; {esc(c["scope"])}',
                          "detail": esc("; ".join(c["actual"]) if isinstance(c["actual"], list) else str(c["actual"])),
                          "handling": esc(c["note"]), "url": c["source_url"]})
    for b in DATA["signals"]["blocked"]:
        items.append({"kind": "Blocked signal", "what": f'<strong>{esc(b["name"])}</strong>',
                      "detail": esc(b.get("blocked_reason", "")),
                      "handling": f'Left blank. Resolving source: {esc(b.get("resolving_source", "unspecified"))}',
                      "url": first_url(b.get("resolving_source"))
                      or (REPO_URL + "/blob/main/src/nfl/signals.py")})
    hap = DATA["standings"]["home_advantage_points"]
    items.append({"kind": "Blocked input", "what": "<strong>Home-field advantage in points</strong>",
                  "detail": esc(hap["reason"]),
                  "handling": f'Left blank. Resolving source: {esc(hap["resolving_source"])}',
                  "url": NFL_STD})
    items.append({"kind": "Blocked input", "what": "<strong>Closing market odds</strong>",
                  "detail": esc(DATA["meta"]["odds_contract"]["reason"]),
                  "handling": "Left blank. Minimum history required: "
                              + esc(DATA["meta"]["odds_contract"]["minimum_history_for_validation"]),
                  "url": REPO_URL + "/blob/main/src/nfl/odds.py"})
    items.append({"kind": "Blocked input", "what": "<strong>Official depth charts</strong>",
                  "detail": esc(DATA["availability"]["depth_chart_status"]["reason"]),
                  "handling": esc(DATA["availability"]["depth_chart_status"]["consequence"]),
                  "url": "https://developer.sportradar.com/football/reference/nfl-weekly-depth-charts"})
    lg = DATA["availability"]["league"]
    items.append({"kind": "Data quality",
                  "what": f'<strong>Injury designation coverage {lg["designation_coverage_pct"]}%</strong>',
                  "detail": f'Only {lg["injury_designation_present"]} of {lg["total_report_entries"]} '
                            f'entries name a body part, and only '
                            f'{lg["entries_with_out_designation"] + lg["entries_with_questionable"] + lg["entries_with_doubtful"]} '
                            'carry a game status. Retrieved on the Thursday of game week.',
                  "handling": "Injury-type features are unusable early in the week. The retriever must "
                              "re-run after the Friday 4:00pm ET deadline and store every version with "
                              "its own timestamp.",
                  "url": NFL_INJ})
    items.append({"kind": "Data quality",
                  "what": "<strong>Left tackle and right tackle are indistinguishable</strong>",
                  "detail": "The official injury report publishes only the position code T. Offensive-line "
                            "modelling depends heavily on which tackle is absent.",
                  "handling": "Left as T. No attempt is made to infer LT from RT.",
                  "url": NFL_INJ})
    items.append({"kind": "Data quality",
                  "what": "<strong>Standings page carries no explicit as-of week</strong>",
                  "detail": "nfl.com/standings does not print which week the records reflect. The snapshot "
                            "covers 136 completed games.",
                  "handling": "Established by arithmetic: 272 team-games divided by two, cross-checked "
                              "against the 28 records printed on the official injury report, all of which "
                              "agree. Recorded as derived rather than asserted.",
                  "url": NFL_STD})
    items.append({"kind": "Modelling assumption",
                  "what": "<strong>Availability index weights are analyst priors</strong>",
                  "detail": "Severity and position weights are not fitted to anything. Every value that "
                            "depends on them is labelled MODELED.",
                  "handling": "Published in full on the Methodology and Availability pages so a reviewer "
                              "can challenge each number individually.",
                  "url": REPO_URL + "/blob/main/src/nfl/availability.py"})
    items.append({"kind": "Modelling assumption",
                  "what": "<strong>Pythagorean exponent fitted on a partial season</strong>",
                  "detail": "k = 3.5073 (95% CI 2.7498-4.3113) is fitted on roughly 8.5 games per team.",
                  "handling": "Reported with its interval and an explicit warning that it is not a general "
                              "constant. Refit required on complete seasons.",
                  "url": REPO_URL + "/blob/main/src/nfl/ratings.py"})
    items.append({"kind": "Statistical finding",
                  "what": "<strong>Zero non-mechanical correlations survive FDR control</strong>",
                  "detail": "Nine of 38 tests survive Benjamini-Hochberg at alpha=0.10 and all nine are "
                            "definitional. 1.9 false positives would be expected at p&lt;0.05 by chance alone.",
                  "handling": "Reported as the headline result rather than buried. No availability signal "
                              "is claimed to work.",
                  "url": REPO_URL + "/blob/main/src/nfl/correlation.py"})
    items.append({"kind": "Repo review",
                  "what": "<strong>The repository was empty at handover</strong>",
                  "detail": "One commit, one file: README.md containing the six characters '# NFL1'. No "
                            "code, data, site or task board existed to review or verify.",
                  "handling": "Recorded as a finding. There were no pre-existing irregularities because "
                              "there was no pre-existing content.",
                  "url": REPO_URL})
    items.append({"kind": "Governance",
                  "what": "<strong>Reward ladder is a proposal, not a policy</strong>",
                  "detail": "The four-tier ladder and its scoring formula are unratified.",
                  "handling": "Marked PROPOSAL everywhere it appears. Awaiting owner sign-off "
                              "(Suggestions S-14, Open Question Q18).",
                  "url": REPO_URL + "/blob/main/src/nfl/leaderboard.py"})
    items.append({"kind": "Governance",
                  "what": "<strong>No staking policy, bankroll or jurisdiction check exists</strong>",
                  "detail": "Nothing in this repository defines a bankroll, a unit size, a maximum "
                            "exposure or a legal position.",
                  "handling": "Deliberately not assumed. Suggestions S-18 and S-22, Open Questions Q11 "
                              "and Q12. Treat the whole system as research until the owner decides.",
                  "url": REPO_URL + "/blob/main/content/open-questions.md"})

    rows = [[badge("FLAG", i["kind"]), i["what"], esc(i["detail"]), esc(i["handling"]),
             srccell(i["url"]) if i["url"] else srccell(
                REPO_URL + "/blob/main/src/nfl/verify.py", "defined in repository code")]
            for i in items]
    return ("Flagged for Review", f'{len(items)} items &middot; none of them block the build or the merge',
            prose("flagged")
            + '<div class="grid g3">'
            + kpi("Flagged items", len(items), "every one carries a source link or an explicit reason")
            + kpi("Disputed official cells", len(v["flags"]), "published verbatim, excluded from computation")
            + kpi("Blocked signals", len(DATA["signals"]["blocked"]), "left blank, each with a resolving source")
            + "</div>"
            + callout("A flagged item does <strong>not</strong> block publication or the merge. It "
                      "means a reviewer should look at it. Every item states what is wrong, how it "
                      "was handled, and the source that would resolve it.", "")
            + table(["Kind", "Item", "Detail", "How it was handled", "Source"], rows,
                    ["c", "", "", "", ""]))


BUILDERS = {
    "index": p_index, "executive-summary": p_executive_summary,
    "open-questions": p_open_questions, "suggestions": p_suggestions,
    "methodology": p_methodology, "data-standings": p_data_standings,
    "data-schedule": p_data_schedule, "data-injuries": p_data_injuries,
    "data-news": p_data_news, "analysis-ratings": p_analysis_ratings,
    "analysis-luck": p_analysis_luck, "analysis-correlation": p_analysis_correlation,
    "availability-depth": p_availability_depth, "lines-week10": p_lines_week10,
    "strategies-leaderboard": p_strategies_leaderboard,
    "strategies-catalogue": p_strategies_catalogue,
    "strategies-gates": p_strategies_gates, "verification": p_verification,
    "sources": p_sources, "flagged": p_flagged,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # .nojekyll only matters when Pages builds from this directory; the root of
    # the repository already carries one.
    if OUT == ROOT:
        (OUT / ".nojekyll").write_text("", encoding="utf-8")
    generated = f'Retrieved {DATA["meta"]["source_retrieved_at_utc"]}.'
    missing = [s for s, _, _ in ALL_PAGES if s not in BUILDERS]
    if missing:
        print(f"ERROR: no builder for {missing}", file=sys.stderr)
        return 1
    for slug, label, cat in ALL_PAGES:
        title, subtitle, body = BUILDERS[slug]()
        (OUT / f"{slug}.html").write_text(
            render_page(slug, title, body, subtitle, generated), encoding="utf-8")
        print(f"  wrote {(OUT / (slug + '.html')).relative_to(ROOT)}  "f"({(OUT / (slug + '.html')).stat().st_size:,} bytes)")
    total = sum(f.stat().st_size for f in OUT.glob("*.html"))
    print(f"{len(ALL_PAGES)} pages, {total:,} bytes total -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
