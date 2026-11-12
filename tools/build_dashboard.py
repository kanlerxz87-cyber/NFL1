#!/usr/bin/env python3
"""Build the clean dashboard under dashboard/ from committed, verified data.

Rules enforced in code (checked independently by tools/verify_dashboard.py):
  * A value is printed only when it is verified against an official source or re-derived
    from committed files this session. Everything else is a blank cell with a flag ID.
  * Every table row carries at least one source link. Official links point to nfl.com or
    a club page. Repository links are labelled 'internal' and are flagged as not official.
  * No value is inferred. Club codes are mapped only where nfl.com itself uses a different code.

Run:  python3 tools/build_dashboard.py   (then python3 tools/verify_dashboard.py)
"""
import html
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "dashboard")
REPO_BLOB = "https://github.com/kanlerxz87-cyber/NFL1/blob/main/"
REPO_TREE = "https://github.com/kanlerxz87-cyber/NFL1/tree/main/"
NFL_INJ = "https://www.nfl.com/injuries/"
NFL_SCHED = "https://www.nfl.com/schedules/2026/REG10"
NFL_STAND = "https://www.nfl.com/standings/league/2026/reg"


def J(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def e(s):
    return html.escape("" if s is None else str(s), quote=True)


# ---------------------------------------------------------------- clubs
CLUBS = {
    "ARI": ("Arizona Cardinals", "arizona-cardinals"), "ATL": ("Atlanta Falcons", "atlanta-falcons"),
    "BAL": ("Baltimore Ravens", "baltimore-ravens"), "BUF": ("Buffalo Bills", "buffalo-bills"),
    "CAR": ("Carolina Panthers", "carolina-panthers"), "CHI": ("Chicago Bears", "chicago-bears"),
    "CIN": ("Cincinnati Bengals", "cincinnati-bengals"), "CLE": ("Cleveland Browns", "cleveland-browns"),
    "DAL": ("Dallas Cowboys", "dallas-cowboys"), "DEN": ("Denver Broncos", "denver-broncos"),
    "DET": ("Detroit Lions", "detroit-lions"), "GB": ("Green Bay Packers", "green-bay-packers"),
    "HOU": ("Houston Texans", "houston-texans"), "IND": ("Indianapolis Colts", "indianapolis-colts"),
    "JAX": ("Jacksonville Jaguars", "jacksonville-jaguars"), "KC": ("Kansas City Chiefs", "kansas-city-chiefs"),
    "LV": ("Las Vegas Raiders", "las-vegas-raiders"), "LAC": ("Los Angeles Chargers", "los-angeles-chargers"),
    "LA": ("Los Angeles Rams", "los-angeles-rams"), "MIA": ("Miami Dolphins", "miami-dolphins"),
    "MIN": ("Minnesota Vikings", "minnesota-vikings"), "NE": ("New England Patriots", "new-england-patriots"),
    "NO": ("New Orleans Saints", "new-orleans-saints"), "NYG": ("New York Giants", "new-york-giants"),
    "NYJ": ("New York Jets", "new-york-jets"), "PHI": ("Philadelphia Eagles", "philadelphia-eagles"),
    "PIT": ("Pittsburgh Steelers", "pittsburgh-steelers"), "SF": ("San Francisco 49ers", "san-francisco-49ers"),
    "SEA": ("Seattle Seahawks", "seattle-seahawks"), "TB": ("Tampa Bay Buccaneers", "tampa-bay-buccaneers"),
    "TEN": ("Tennessee Titans", "tennessee-titans"), "WAS": ("Washington Commanders", "washington-commanders"),
}
# nfl.com's own codes for the Rams and Cardinals (display only; pipeline codes are LA and ARI)
CLUBS["LAR"] = CLUBS["LA"]
CLUBS["AZ"] = CLUBS["ARI"]
# nfl.com club codes that differ from the pipeline codes (documented in the pipeline)
NFL_CODE = {"LA": "LAR", "ARI": "AZ"}

PRACTICE = {
    "FULL": "Full Participation in Practice",
    "LIM": "Limited Participation in Practice",
    "DNP": "Did Not Participate In Practice",
}


# ---------------------------------------------------------------- cell helpers
def badge(kind):
    label = {
        "ok": "Verified", "bad": "Mismatch", "warn": "Unverified",
        "muted": "Not re-checked", "internal": "Internal file", "third": "Third-party",
    }[kind]
    return f'<span class="b {kind}">{label}</span>'


def link(url, label=None, kind=None):
    if kind is None:
        if url.startswith(REPO_BLOB) or url.startswith(REPO_TREE):
            kind = "internal"
        elif re.match(r"https://(www\.)?(nfl\.com|operations\.nfl\.com|nextgenstats\.nfl\.com|chiefs\.com|packers\.com|49ers\.com|static\.www\.nfl\.com|itl\.nist\.gov|nj\.gov|docs\.github\.com)", url):
            kind = "official"
        else:
            kind = "other"
    tag = {"official": "", "internal": '<span class="src-int">internal</span> ', "other": '<span class="src-oth">not official</span> '}[kind]
    return f'<a href="{e(url)}" target="_blank" rel="noopener">{tag}{e(label or url)}</a>'


def val(v, source_url, src_label=None, extra=""):
    """A verified value cell."""
    return f'<td class="v" data-verified="true">{e(v)}{extra}</td>'


def blank(flag):
    """An unverified value cell: always empty, always flagged."""
    return (f'<td class="blank" data-verified="false" title="Unverified: left blank. See flag {e(flag)}">'
            f'<span class="flagtag">⚑ {e(flag)}</span></td>')


def td(content, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f"<td{c}>{content}</td>"


def table(headers, rows, cls="", row_attr=""):
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = "\n".join(f"<tr{row_attr}>{r}</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>\n{body}\n</tbody></table></div>'


# ---------------------------------------------------------------- page chrome
NAV = [
    ("index.html", "Overview"),
    ("lines.html", "Lines & markets"),
    ("strategies.html", "Strategies"),
    ("injuries.html", "Injuries"),
    ("depth.html", "Depth & backups"),
    ("verification.html", "Verification"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged for review"),
    ("repo.html", "Repo review"),
    ("executive.html", "Executive summary"),
    ("sources.html", "Sources"),
]


def page(fname, title, lead, body):
    parts = []
    for href, label in NAV:
        cls = ' class="on"' if href == fname else ""
        parts.append(f'<a href="{href}"{cls}>{e(label)}</a>')
    nav = "".join(parts)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · NFL Decision Dashboard</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="top">
  <a class="brand" href="index.html">NFL Decision Dashboard</a>
  <nav>{nav}</nav>
</header>
<main>
<h1>{e(title)}</h1>
<p class="lead">{lead}</p>
{body}
</main>
<footer>
  <p>Built 2026-11-12 from committed files in <a href="{REPO_TREE}">the repository</a>. Official values are checked against the nfl.com pages linked in each row.
  Blank cells are unverified and are never filled in. A flag ID (⚑) points to the <a href="flagged.html">Flagged for review</a> page.</p>
  <p>Research and education only. This is not betting advice. No official NFL betting odds exist, and no prices are shown.</p>
</footer>
</body>
</html>
"""


def legend():
    return ('<div class="legend">' + badge("ok") + ' value checked against an official page this session · '
            + badge("bad") + ' source and repo disagree · ' + badge("warn") + ' cannot be confirmed from an official source; cell left blank · '
            + badge("muted") + ' carried from an earlier session, not re-read here · '
            + badge("internal") + ' repository file, not an official source</div>')


def card(href, title, big, text):
    return (f'<a class="card" href="{href}"><div class="card-big">{e(big)}</div>'
            f'<h3>{e(title)}</h3><p>{e(text)}</p></a>')


# ---------------------------------------------------------------- data
def load():
    d = {}
    d["sources"] = {s["id"]: s for s in J("data/sources.json")}
    d["questions"] = J("data/questions.json")
    d["suggestions"] = J("data/suggestions.json")
    d["flags"] = J("data/flags.json")
    d["reqs"] = J("data/requirements.json")
    d["lines"] = J("data/model/lines.json")
    d["strat"] = J("data/model/strategies.json")
    d["rec"] = J("data/dashboard/recomputed.json")
    d["inj"] = J("data/dashboard/injury_verification.json")
    d["sched"] = J("data/dashboard/schedule_2026_w10.json")
    d["sched_check"] = J("data/dashboard/schedule_check.json")
    d["review"] = J("data/dashboard/review.json")["findings"]
    d["gate6a"] = J("data/dashboard/decision_gate_6a.json")
    d["depth"] = J("data/depth_chart.json")
    d["avail"] = J("data/model/availability.json")
    d["dashboard"] = J("data/model/dashboard.json")
    d["official_rows"] = read_psv()
    d["verification"] = J("data/dashboard/verification.json")
    return d


def read_psv():
    rows = []
    with open(os.path.join(ROOT, "data/dashboard/official_injuries_2026_w10.psv"), encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            team, player, pos, injury, practice, game = line.split("|")
            rows.append({"team": team, "player": player, "pos": pos, "injury": injury, "practice": PRACTICE[practice], "game": game})
    return rows


def src_url(d, code):
    s = d["sources"].get(code)
    return s["url"] if s else None


def flag_src(d, f):
    """Map a legacy flag/question source code (S01 ...) to its URL; keep it visible."""
    code = f.get("src")
    url = src_url(d, code) if code else None
    return url or NFL_INJ


# ---------------------------------------------------------------- pages
def page_index(d):
    rec = d["rec"]
    n_strat = len(rec["strategies"])
    gate_match = sum(1 for s in rec["strategies"] if not s["gate_mismatches_vs_published"])
    inj = d["inj"]["counts"]
    sched = d["sched_check"]
    new_q = len(d["gate6a"]["questions"])
    new_s = len(d["gate6a"]["suggestions"])
    head_rows = [
        td("Official Week 10 games matched to model rows") + val(f'{sched["matched"]} of {sched["official_games"]}', NFL_SCHED) + td(link(NFL_SCHED, "nfl.com schedule, Week 10")),
        td("Official injury rows on the page") + val(str(inj["official_rows"]), NFL_INJ) + td(link(NFL_INJ, "nfl.com injury report")),
        td("Official rows matching the committed scrape on every field") + val(str(inj["matched_all_fields"]), NFL_INJ) + td(link(NFL_INJ, "nfl.com injury report")),
        td("Official rows with a game status (Out, Questionable)") + val(str(len(d["inj"]["official_game_status_rows"])), NFL_INJ) + td(link(NFL_INJ, "nfl.com injury report")),
        td("Standings correlations reproduced") + val(f'{sum(1 for c in rec["standings_correlations"] if c["agrees_to_3dp"])} of {len(rec["standings_correlations"])}', NFL_STAND) + td(link(NFL_STAND, "nfl.com standings 2026 REG")),
        td("Strategy gate results reproduced from committed JSON") + val(f'{gate_match} of {n_strat}', "https://github.com/kanlerxz87-cyber/NFL1/blob/main/tools/recompute_strategy_gates.py") + td(link(REPO_BLOB + "data/dashboard/recomputed.json", "recomputed.json (internal)")),
        td("Clubs with any depth chart in the repo") + val("3 of 32", "https://www.nfl.com/teams/washington-commanders/depth-chart") + td(link("https://www.chiefs.com/team/depth-chart", "chiefs.com (labelled unofficial)")),
        td("Own line / market line values") + blank("UNV-LINE") + td(link(NFL_SCHED, "no official odds source exists; see flag UNV-LINE")),
    ]
    head_tbl = table(["Item", "Value", "Source"], head_rows)
    cards = "".join([
        card("lines.html", "Lines & markets", f'{sched["matched"]}/{sched["official_games"]}',
             "Week 10 games match the official schedule. Own and market line values are blank: no official line source exists."),
        card("strategies.html", "Strategies", f"{gate_match}/{n_strat}",
             "Strategy gate results that reproduce from the committed data. Performance values are blank (unverified)."),
        card("injuries.html", "Injuries", f'{inj["official_rows"]} rows',
             f'{inj["matched_all_fields"]} match the official page on every field; {inj["field_differences"]} differ; {inj["missing_from_scrape"]} missing from the scrape.'),
        card("depth.html", "Depth & backups", "3 of 32",
             "Clubs with any depth chart in the repo. No labelled official depth chart was found for the other 29."),
        card("questions.html", "Questions", f'{len(d["questions"]) + new_q}',
             "Questions that gate each decision: known, unknown, discovery route, and what each one blocks."),
        card("suggestions.html", "Suggestions", f'{len(d["suggestions"]) + new_s}',
             "Improvement options with a recommended path. None is implemented. You choose."),
        card("flagged.html", "Flagged for review", f'{len(d["review"]) + len(d["flags"])}',
             "Every irregularity and unverified value, with its source link. These do not block anything."),
        card("repo.html", "Repo review", "5+ site generations",
             "What each folder publishes, which generator writes it, and where the conflicts are."),
        card("executive.html", "Executive summary", "Read first",
             "What was verified, what was not, what the model shows, and the decisions needed."),
        card("sources.html", "Sources", f'{len(d["sources"])} registered',
             "Official and third-party sources, with the pages read in this session."),
    ])
    body = f"""
{legend()}
<section class="hero">
  <p><strong>What this is.</strong> A checked view of the NFL Decision Lab repository. Every value
  here is either confirmed against an official NFL page this session or left blank and flagged.
  It shows the model's own results as unverified findings, not as facts.</p>
  <p><strong>Headline.</strong> The Week 10 schedule matches nfl.com (14 of 14). The official injury report (279 rows) is transcribed and checked against the live page. The committed injury scrape matches all 279 rows on the latest refresh (22:40Z). An earlier refresh (22:36Z) did not (RV-02, resolved on the later refresh). The depth data covers 3 of 32 clubs.
  No model strategy passes all gates after recomputation, and the model's own lines do not beat the market in the 2026 test window
  (unverified model output). Nothing here is ready for a betting decision.</p>
</section>
<div class="cards">{cards}</div>
<h2>Headline numbers and where each comes from</h2>
{head_tbl}
"""
    return page("index.html", "Overview", "Verified NFL data, checked line by line. Blank means unverified.", body)


def page_lines(d):
    sched = d["sched"]["games"]
    chk = d["sched_check"]
    rows = []
    for i, g in enumerate(sched, 1):
        matchup = f'{CLUBS[g["away"]][0]} @ {CLUBS[g["home"]][0]}'
        rows.append(
            td(str(i)) + td(e(g["weekday"]) + " " + e(g["date"])) + td(e(g["time_et"])) + td(e(g["network"]))
            + td(f'<strong>{e(g["away"])} @ {e(g["home"])}</strong><br><span class="muted">{e(matchup)}</span>')
            + td(f'<span class="b ok">Verified</span> {link(g["game_url"], "nfl.com game page")}')
            + td(f'<span class="b ok">Matched</span> <span class="small">model row present</span>' if chk["result"] == "PASS" else badge("bad"))
            + blank("UNV-LINE") + blank("UNV-LINE") + blank("UNV-LINE") + blank("UNV-SIGNAL")
        )
    tbl = table(["#", "Day", "Kickoff (ET)", "Network", "Matchup", "Official source", "Schedule check",
                 "Own line", "Market line", "Edge", "Signal"], rows)
    lm = d["lines"]["sign_convention_check"]
    body = f"""
{legend()}
<h2>Week 10 games</h2>
<p>Matchups, days, times and networks are taken from the nfl.com schedule page (read 2026-11-12).
The schedule check compares the 14 games with the model's rows: {chk["matched"]} of {chk["official_games"]} match on away team, home team and date.
The model's line, total, edge and signal columns are blank. The repo gives no official source for betting lines,
so they cannot be verified (flags UNV-LINE and UNV-SIGNAL).</p>
{tbl}
<p class="small">Bye teams in Week 10 (nfl.com): {", ".join(e(x) for x in d["sched"]["byes_week_10"])}.
nfl.com uses LAR and AZ for the Rams and Cardinals; the pipeline uses LA and ARI. Mapping only.
Week 10 games are in the official schedule; the Munich game is listed at 9:30 AM ET.</p>

<h2>Model validation (unverified model output)</h2>
<div class="callout warn">
<p><strong>Read this before using any line.</strong> These are the model's own results, copied from
<a href="{REPO_BLOB}data/model/lines.json">data/model/lines.json</a>. They are not official values and are not shown in tables.</p>
<ul>
<li>The test window (2026, 136 games) shows the model's spread error at 9.98 points against the market's 9.49 points. The model is further from the outcome than the market.</li>
<li>The blend test gives the model a negative weight (about −0.33). In this window, adding the model made predictions worse than the market alone.</li>
<li>The 95% band on a single home spread is about 52 points wide (for example WAS @ NYG). A single edge is therefore not distinguishable from zero.</li>
<li>The Overview labelled LA @ ARI 'actionable'. That label is not supported by the test above and should be removed (flag RV-11).</li>
<li>The repo calls the mirrored market line a 'closing line' (lines.json). No official page publishes betting lines, and the nflverse dictionary page read this session does not confirm the field definitions (flag RV-12).</li>
</ul>
<p class="small">Sign convention (repo check, not an official definition): the mirrored line correlates {lm["corr_market_line_vs_home_margin"]} with the home margin over {lm["n_games"]:,} games, which the repo reads as home-favourite-positive.</p>
</div>
"""
    return page("lines.html", "Lines & markets", "Week 10 schedule verified against nfl.com. Own lines and market values are blank until an official source exists.", body)


def page_strategies(d):
    rec = {s["strategy"]: s for s in d["rec"]["strategies"]}
    rows = []
    for x in d["strat"]["leaderboard"]:
        r = rec[x["strategy"]]
        sid, _, rule = x["strategy"].partition(" ")
        ok = not r["gate_mismatches_vs_published"]
        check = (f'<span class="b ok">Matches</span> <span class="small">gates re-derived: {r["recomputed_gates_passed"]} of 8</span>'
                 if ok else f'<span class="b bad">Differs</span>')
        rows.append(
            td(f'<strong>{e(sid)}</strong>') + td(e(rule))
            + td(check)
            + blank("UNV-PERF") + blank("UNV-PERF") + blank("UNV-PERF") + blank("UNV-PERF") + blank("UNV-PERF") + blank("UNV-PERF")
            + td(f'<span class="b internal">Internal file</span> {link(REPO_BLOB + "data/model/strategies.json", "strategies.json")}')
        )
    t1 = table(["ID", "Strategy rule", "Gate check (recomputed)", "Published status", "Graded bets", "Win %", "ROI", "ROI 95% low", "BH q", "Source"], rows)
    gate_rows = [
        td(f'<strong>{e(g["id"])}</strong>') + td(e(g["rule"])) + td(f'<span class="b internal">Internal rule</span> {link(REPO_BLOB + "data/model/strategies.json", "strategies.json")}')
        for g in d["strat"]["gate_definitions"]
    ]
    t2 = table(["Gate", "Rule (as published)", "Source"], gate_rows)
    corr_rows = []
    for c in d["rec"]["standings_correlations"]:
        agree = c["agrees_to_3dp"]
        corr_rows.append(
            td(f'<strong>{e(c["id"])}</strong>') + td(e(c["pair"]))
            + val(f'{c["r_recomputed"]:.4f}', NFL_STAND) + td(f'{c["r_published"]:.4f}')
            + td(f'<span class="b ok">Agrees</span>' if agree else '<span class="b bad">Differs</span>')
            + td(link(NFL_STAND, "nfl.com standings 2026 REG"))
        )
    t3 = table(["ID", "Pair (standings)", "r, recomputed", "r, published", "Check", "Source"], corr_rows)
    body = f"""
{legend()}
<div class="callout">
<p><strong>What the leaderboard can and cannot show.</strong> Strategy performance depends on betting prices.
No official NFL source publishes betting odds, so every performance cell is blank. The gate results below were
re-derived from the committed JSON. That confirms the model is internally consistent. It does not confirm that any strategy would win.</p>
</div>
<h2>Strategy catalogue and gate check</h2>
{t1}
<h2>Validation gates (as published)</h2>
{t2}
<h2>Correlations: what was recomputed</h2>
<p>These six values are standings identities. They are not betting correlations and do not measure skill.
They reproduce from the 32 standings rows, so the recomputation agrees with the published values.</p>
{t3}
<h2>Findings (model output, unverified)</h2>
<div class="callout warn">
<ul>
<li><strong>S11 is labelled WATCH with 6 of 8 gates.</strong> It fails significance (G5) and stability (G6, 13 of 22 seasons positive). The status rule counts gates, so WATCH does not mean significance (RV-08).</li>
<li><strong>S04 and S06 are the same bet.</strong> They share 207 games and have correlation 1.0 on that overlap. Nine of twelve strategies show |corr| = 1.0 on the diversification gate (RV-09).</li>
<li><strong>Benjamini-Hochberg q-values are identical (0.9889).</strong> This reproduces from the published p-values, so it is not a bug. It means no strategy is distinguishable from chance after correction (RV-10).</li>
<li><strong>Parlays and player-prop combos.</strong> No prices are published for them, so no performance value is shown (flag UNV-PERF).</li>
<li><strong>Rewards.</strong> Any monetary reward needs legal review before use (flag F05, from the earlier flags list).</li>
</ul>
</div>
"""
    return page("strategies.html", "Strategies", "Leaderboard, gates and correlations. Performance cells are blank: no official odds source exists.", body)


def page_injuries(d):
    inj = d["inj"]
    c = inj["counts"]
    diffs = {(x["team"], x["player"]): x["diffs"] for x in inj["field_differences"]}
    missing = {(x["team"], x["player"]) for x in inj["missing_from_scrape"]}
    rows = []
    for r in d["official_rows"]:
        key = (r["team"], r["player"])
        if key in missing:
            check = '<span class="b bad">Missing from scrape</span>'
        elif key in diffs:
            parts = []
            for fld, vals in diffs[key].items():
                parts.append(f'{e(fld)}: scrape "{e(vals.get("scraped") or "blank")}"')
            check = '<span class="b bad">Scrape differs</span> <span class="small">' + "; ".join(parts) + '</span>'
        else:
            check = '<span class="b ok">Matched</span>'
        rows.append(
            td(f'<strong>{e(r["team"])}</strong>') + td(e(r["player"])) + td(e(r["pos"]))
            + val(r["injury"] or "", NFL_INJ) + val(r["practice"], NFL_INJ) + val(r["game"] or "", NFL_INJ)
            + td(check) + td(link(NFL_INJ, "nfl.com injury report"))
        )
    tbl = table(["Club", "Player", "Pos", "Injury (official)", "Practice (official)", "Game status (official)", "Scrape check", "Source"], rows)
    summary = f"""
<div class="stats">
<div><b>{c["official_rows"]}</b><span>official rows (nfl.com, Week 10)</span></div>
<div><b>{c["matched_all_fields"]}</b><span>match on every field</span></div>
<div><b>{c["field_differences"]}</b><span>rows with a field that differs in the scrape</span></div>
<div><b>{c["missing_from_scrape"]}</b><span>missing from scrape</span></div>
<div><b>{len(d["inj"]["official_game_status_rows"])}</b><span>official game designations</span></div>
<div><b>{c["clubs_on_official_page"]}</b><span>clubs with rows (LAC and BAL read 'No Injuries Reported')</span></div>
</div>"""
    body = f"""
{legend()}
{summary}
<div class="callout">
<p><strong>How this table was checked.</strong> All 7 chunks of the nfl.com page were read on 2026-11-12. Each of the
{c["official_rows"]} rows was transcribed and compared with the committed scrape field by field
(<a href="{REPO_BLOB}data/dashboard/injury_verification.json">injury_verification.json</a>,
script <a href="{REPO_BLOB}tools/verify_official_injuries.py">verify_official_injuries.py</a>).
The official values are shown. The scrape check column shows where the committed scrape disagrees.</p>
<p><strong>Game designations are rare.</strong> Only {len(d["inj"]["official_game_status_rows"])} rows carry a game status this week.
Most rows show practice status only. The old Overview phrase "starters flagged 103, official game status" mixed the two (RV-01).</p>
</div>
<h2>Official report, Week 10</h2>
{tbl}
<h2>In the committed scrape but not on the official page ({len(inj["extra_in_scrape"])})</h2>
<div class="callout warn"><p>Rows in <a href="{REPO_BLOB}data/model/official_injuries.json">data/model/official_injuries.json</a> that are not on the nfl.com page read on 2026-11-12. {"None on the latest refresh." if not inj["extra_in_scrape"] else "They are listed here, not in the official table above (flag RV-02)."} The 22:36Z refresh had 16 such rows (RV-02).</p></div>
{table(["Club", "Player", "Source of claim", "Status"], [td(e(x["team"])) + td(e(x["player"])) + td(link(REPO_BLOB + "data/model/official_injuries.json", "official_injuries.json (internal)")) + td('<span class="b bad">Not on official page</span>') for x in inj["extra_in_scrape"]])}
<h2>Official news ahead of the page</h2>
<div class="callout warn">
<p>On the same nfl.com page, a news item reports <strong>Sam Darnold ruled out</strong> for Seahawks' Week 10 game vs. Raiders,
with Drew Lock expected to start. The injury row for Darnold shows only <em>Did Not Participate In Practice</em> and no game status.
The model shows Darnold as practice-only (RV-07).
<a href="https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again">nfl.com news item</a> (linked from the nfl.com player page; article body not read).</p>
</div>
"""
    return page("injuries.html", "Injuries", "Official Week 10 injury report, checked row by row against the committed scrape.", body)


def page_depth(d):
    depth = d["depth"]
    by_club = {}
    for r in depth:
        by_club.setdefault(r["code"], []).append(r)
    probe = {"WAS": "404 (re-checked 2026-11-12)", "BUF": "404 (committed probe log, 2026-11-12 04:45Z)",
             "KC": "404 (committed probe log, 2026-11-12 04:45Z)"}
    rows = []
    for code in sorted(CLUBS):
        name, slug = CLUBS[code]
        url = f"https://www.nfl.com/teams/{slug}/depth-chart"
        n = len(by_club.get(code, []))
        if code in probe:
            status = f'<span class="b bad">{e(probe[code])}</span>'
        else:
            status = '<span class="b muted">Not probed this session</span>'
        if n:
            lbl = by_club[code][0]["chart_label"]
            repo = f'{n} rows; label "{e(lbl)}"'
        else:
            repo = '<span class="blank-inline">none in repo</span>'
        rows.append(td(f'<strong>{e(code)}</strong> {e(name)}') + td(link(url, "nfl.com depth-chart URL (built from club slug; not probed)" if code not in probe else "nfl.com depth-chart URL"))
                    + td(status) + td(repo))
    tbl = table(["Club", "Official depth-chart page", "Status", "Rows in repo (2nd to 4th string)"], rows)
    kc = [
        ("WR, row 2", "Xavier Worthy; (blank); Cyrus Allen in row 3", "Cyrus Allen shifted into slot 3; Josh Downs missing"),
        ("DT, row 1", "Chris Jones; Peter Woods; (row 3 blank)", "Marcus Harris missing"),
        ("KR", "(row 1 blank); Emmett Johnson in row 2", "Emmett Johnson and Cyrus Allen shifted"),
        ("PR", "(row 1 blank); Emmett Johnson in row 2", "Emmett Johnson and Cyrus Allen shifted"),
    ]
    kc_rows = [td(e(a)) + td(e(b)) + td(f'<span class="b bad">Differs</span> {e(c)}') + td(link("https://www.chiefs.com/team/depth-chart", "chiefs.com depth chart")) for a, b, c in kc]
    kc_tbl = table(["Position", "Repo rows (depth_chart.json)", "Difference from club page (RV-06)", "Source"], kc_rows)
    body = f"""
{legend()}
<div class="callout warn">
<p><strong>Only 3 of 32 clubs have any depth data in the repo (SF, KC, GB).</strong> The brief asks for 2nd, 3rd and 4th-string
tracking for every club. The model's availability table uses depth rank 1 for all {d["avail"]["counts"]["starters_impacted"]} starters, so no backup is identified
by the model (RV-04, RV-05). Backup columns are therefore not shown.</p>
</div>
<h2>Club by club</h2>
{tbl}
<h2>Kansas City rows checked against the club page</h2>
<p>24 of the 28 KC rows match chiefs.com line by line (checked 2026-11-12). The four that differ are listed below. chiefs.com titles its own page
"Unofficial Depth Chart", so the repo label "Unofficial" is right and the registry label "Official club depth chart" is wrong (RV-06, RV-22).</p>
{kc_tbl}
<h2>Sources not checked here</h2>
<p>The Green Bay and San Francisco rows (labelled 'Unofficial' and 'Depth Chart') were not compared with their club pages in this session.
Their status is unverified (flag UNV-DEPTH).</p>
"""
    return page("depth.html", "Depth & backups", "Depth-chart coverage by club. Three clubs have data. None is labelled official on the club's own page.", body)


def page_verification(d):
    v = d["verification"]
    badge_for = {"PASS": "ok", "FAIL": "bad", "CONFLICT": "bad"}
    rows = []
    for c in v["checks"]:
        rows.append(
            td(f'<strong>{e(c["id"])}</strong>') + td(e(c["name"]))
            + td(f'<span class="b {badge_for.get(c["result"], "muted")}">{e(c["result"])}</span>')
            + td(f'{c["rows_matched"]} of {c["rows_checked"]}')
            + td(str(c["mismatches"]))
            + td(e(c["notes"]))
            + td(link(c["source"], c["source"]) if c["source"].startswith("http") else link(REPO_BLOB + c["source"], c["source"]))
            + td(f'<span class="small">{e(c["artifact"])}</span>')
        )
    t = table(["ID", "Check", "Result", "Matched", "Mismatches", "Notes", "Source", "Artifact"], rows)
    UNV_SRC = {
        "Betting lines and closing prices": (NFL_SCHED, "nfl.com schedule page (no betting lines shown)"),
        "Strategy return, win rate and ROI": (REPO_BLOB + "data/model/strategies.json", "strategies.json"),
        "Player-prop prices": (REPO_BLOB + "data/model/props.json", "props.json"),
        "Depth charts for 29 of 32 clubs": ("https://www.nfl.com/teams/washington-commanders/depth-chart", "nfl.com depth chart (WAS: 404)"),
        "Game times for unplayed games beyond Week 10": (REPO_BLOB + "data/model/verification.json", "verification.json"),
    }
    un_rows = []
    for u in v["unverified_not_checked_here"]:
        url, lab = UNV_SRC[u["item"]]
        un_rows.append(td(e(u["item"])) + td(e(u["handling"])) + td(link(url, lab)))
    un = table(["Not checked here", "Handling", "Source"], un_rows)
    sm = v["summary"]
    body = f"""
{legend()}
<div class="stats">
<div><b>{sm["PASS"]}</b><span>checks pass</span></div>
<div><b>{sm["FAIL"]}</b><span>checks fail (see notes)</span></div>
<div><b>{sm["CONFLICT"]}</b><span>conflict with the model's own check</span></div>
</div>
<div class="callout">
<p><strong>Rule used.</strong> {e(v["rule"])}</p>
</div>
<h2>Checks run this session</h2>
{t}
<h2>Not checked here</h2>
{un}
"""
    return page("verification.html", "Verification", "Independent checks run on 2026-11-12, with every result and every conflict shown.", body)


def page_questions(d):
    checks = {
        "Q05": ("Mismatch: depth covers 3 of 32 clubs (RV-15)", "bad"),
        "Q07": ("Verified flag with blank answer (RV-14)", "warn"), "Q09": ("Verified flag with blank answer (RV-14)", "warn"),
        "Q10": ("Verified flag with blank answer (RV-14)", "warn"), "Q11": ("Verified flag with blank answer (RV-14)", "warn"),
        "Q12": ("Verified flag with blank answer (RV-14)", "warn"), "Q13": ("Verified flag with blank answer (RV-14)", "warn"),
        "Q20": ("Verified flag with blank answer (RV-14)", "warn"), "Q22": ("Verified flag with blank answer (RV-14)", "warn"),
        "Q23": ("Not re-checked this session (RV-25)", "muted"),
    }
    rows = []
    for q in d["questions"]:
        ans = (q.get("answer") or "").strip()
        ver = checks.get(q["id"], ("Not re-checked this session", "muted"))
        ans_cell = td(e(ans)) if ans else blank("UNV-ANSWER")
        src = flag_src(d, q)
        rows.append(td(f'<strong>{e(q["id"])}</strong>') + td(e(q["question"])) + td(e(q.get("known") or ""))
                    + td(e(q.get("unknown") or "")) + ans_cell
                    + td(f'<span class="b {ver[1]}">{e(ver[0])}</span>')
                    + td(link(src, q.get("src") or "source")))
    old = table(["ID", "Question", "Known", "Unknown", "Answer", "Check this session", "Source"], rows)
    new_rows = []
    for q in d["gate6a"]["questions"]:
        new_rows.append(td(f'<strong>{e(q["id"])}</strong>') + td(e(q["question"])) + td(e(q["known"])) + td(e(q["unknown"]))
                        + blank("UNV-ANSWER") + td(f'<span class="b warn">Open</span> <span class="small">{e(q["discovery"])}</span>')
                        + td(link(q["source_url"], "source")))
    new = table(["ID", "Question", "Known", "Unknown", "Answer", "Discovery route", "Source"], new_rows)
    body = f"""
{legend()}
<p>Each question says what is known, what is not, and how to find out. Answers are shown only where the source supports them.
Blank answers are unanswered, not 'no'. Items marked 'verified' in the repo but with no answer are flagged (RV-14).</p>
<h2>Existing questions ({len(d["questions"])})</h2>
{old}
<h2>Questions raised by this review ({len(d["gate6a"]["questions"])})</h2>
{new}
"""
    return page("questions.html", "Questions", "What must be known before a decision. Answers only where a source supports them.", body)


def page_suggestions(d):
    rows = []
    for s in d["suggestions"]:
        src = flag_src(d, s)
        rows.append(td(f'<strong>{e(s["id"])}</strong>') + td(e(s.get("area", ""))) + td(e(s["title"]))
                    + td(e(s.get("decision_impact", ""))) + td(e(s.get("recommended_path", "")))
                    + td(f'<span class="b warn">{e(s.get("status", ""))}</span>') + td("Pending your decision", "pending")
                    + td(link(src, s.get("src") or "source")))
    old = table(["ID", "Area", "Suggestion", "Impact", "Recommended path", "Status", "Your choice", "Source"], rows)
    new_rows = []
    for s in d["gate6a"]["suggestions"]:
        new_rows.append(td(f'<strong>{e(s["id"])}</strong>') + td(e(s["area"])) + td(e(s["title"]))
                        + td(e(s["decision_impact"])) + td(e(s["recommended_path"]))
                        + td(f'<span class="b warn">{e(s["status"])}</span>') + td("Pending your decision", "pending")
                        + td(link(s["source_url"], "source")))
    new = table(["ID", "Area", "Suggestion", "Impact", "Recommended path", "Status", "Your choice", "Source"], new_rows)
    body = f"""
<div class="callout">
<p><strong>No change has been made.</strong> Each option below is a proposal. Pick a path for each item, or ask for a different one.
Nothing is implemented, merged or published from this page until you decide.</p>
</div>
<h2>Proposals from this review ({len(d["gate6a"]["suggestions"])})</h2>
{new}
<h2>Earlier suggestions ({len(d["suggestions"])})</h2>
{old}
"""
    return page("suggestions.html", "Suggestions", "Options to choose from before anything is changed. None is implemented.", body)


def page_flagged(d):
    sev = {"High": "bad", "Medium": "warn", "Low": "muted"}
    rows = []
    for f in d["review"]:
        st = f["status"]
        cls = {"Verified": "ok", "Verified mismatch": "bad", "Unverified": "warn", "Not re-checked": "muted"}.get(st, "muted")
        rows.append(td(f'<strong>{e(f["id"])}</strong>') + td(f'<span class="b {sev.get(f["severity"], "muted")}">{e(f["severity"])}</span>')
                    + td(e(f["area"])) + td(e(f["finding"])) + td(e(f["evidence"]))
                    + td(f'<span class="b {cls}">{e(st)}</span>') + td(e(f["action"]))
                    + td(link(f["source_url"], None, f.get("source_type") and None)))
    a = table(["ID", "Severity", "Area", "Finding", "Evidence", "Status", "Action", "Source"], rows)
    rows2 = []
    for f in d["flags"]:
        src = flag_src(d, f)
        rows2.append(td(f'<strong>{e(f["id"])}</strong>') + td(e(f["category"])) + td(e(f["description"]))
                     + td(e(f["impact"])) + td(e(f["status"])) + td(e(f["action"])) + td(link(src, f.get("src") or "source")))
    b = table(["ID", "Category", "Description", "Impact", "Status", "Action", "Source"], rows2)
    body = f"""
<div class="callout warn">
<p><strong>Flagged for review.</strong> These items do not block anything. They are published so you can review them and request changes.
Each has a source link. Items marked <em>Unverified</em> are blank in the tables.</p>
</div>
<h2>This review ({len(d["review"])})</h2>
{a}
<h2>Earlier flags ({len(d["flags"])})</h2>
{b}
"""
    return page("flagged.html", "Flagged for review", "Irregularities, unverified values and open questions, with their sources.", body)


def page_repo(d):
    def count(path):
        n = 0
        full = os.path.join(ROOT, path)
        if os.path.isfile(full):
            return 1
        for _, _, files in os.walk(full):
            n += len(files)
        return n
    inventory = [
        ("index.html, pages/, styles.css", "Root site (earlier sessions). Overview plus subpages under pages/.", "tools/build.py and pipeline/gen_site.py both write index.html (RV-17)", "Conflict (RV-17)", "index.html"),
        ("pages/", "Subpages of the root site", "pipeline/gen_site.py; scripts/verified/build_site.py", "Two generators (RV-17)", "pages"),
        ("docs/", "Second site generation with its own index, plus reports", "tools/build_docs_site.py", "Overlaps root (RV-21)", "docs"),
        ("referee/", "Independent verification site (earlier session)", "referee/tools/build_site.py", "Overlaps root (RV-21)", "referee"),
        ("verified-lab/", "Verification subsystem and sub-site (earlier session)", "not located by grep", "Generator unknown", "verified-lab"),
        ("site/", "Templates and assets for the tools/build.py generation", "tools/build.py", "Overlaps root (RV-21)", "site"),
        ("dashboard/", "This clean dashboard (session 6a232e79)", "tools/build_dashboard.py", "New, self-contained", "dashboard"),
        ("data/", "Committed data: model outputs, verified transcriptions, questions, flags", "pipeline/ and tools/", "Mixed sources (RV-21)", "data"),
        ("data/model/", "Pipeline outputs (lines, strategies, availability, injuries)", "pipeline/build_all.py", "Errors log stale (RV-18)", "data/model"),
        ("pipeline/", "Collector, scraper, model builder", "-", "Scrape on latest refresh 9040190: 279 of 279 match; the 22:36Z refresh regressed (RV-02, resolved)", "pipeline"),
        ("analysis/", "Analysis engine from earlier session", "-", "Not reviewed line by line", "analysis"),
        ("tools/", "Generators and verifiers", "-", "Several write the same files", "tools"),
        ("scripts/", "Verification scripts and builders", "-", "Not reviewed line by line", "scripts"),
        (".github/workflows/", "CI: collect, verify, pages", "-", "Three workflows, overlapping purpose", ".github/workflows"),
        ("README.md", "Repository README (generated by tools/build.py)", "tools/build.py (template)", "Duplicated blocks (RV-19)", "README.md"),
        ("COORDINATION.md", "Shared task board", "hand-edited", "Concatenated boards (RV-20)", "COORDINATION.md"),
    ]
    rows = []
    for name, what, gen, status, path in inventory:
        n = count(path)
        rows.append(td(f'<strong>{e(name)}</strong>') + td(e(what)) + td(e(gen)) + td(f"{n} file(s)")
                    + td(f'<span class="small">{e(status)}</span>') + td(link(REPO_TREE + path if not path.endswith(".md") and not path.endswith("html") else REPO_BLOB + path, "view on GitHub")))
    inv = table(["Path", "What it is", "Written by", "Files", "Review status", "Source"], rows)
    req_rows = []
    for r in d["reqs"]:
        src = flag_src(d, r)
        req_rows.append(td(f'<strong>{e(r["id"])}</strong>') + td(e(r["category"])) + td(e(r["requirement"]))
                        + td(e(r.get("analysis", ""))) + td(f'<span class="small">{e(r["status"])}</span>') + td(link(src, r.get("src") or "source")))
    reqs = table(["ID", "Category", "Requirement (from the brief)", "Analysis", "Status", "Source"], req_rows)
    body = f"""
{legend()}
<h2>What each folder publishes</h2>
<p>The repo publishes several overlapping sites from one branch. The root Overview is the live landing page. This dashboard
is a new, separate site. Conflicts are listed in <a href="flagged.html">Flagged for review</a>.</p>
{inv}
<h2>Requirements tracker ({len(d["reqs"])})</h2>
{reqs}
"""
    return page("repo.html", "Repo review", "What the repository contains, which generator writes each part, and where the conflicts are.", body)


def page_executive(d):
    body = f"""
<div class="callout">
<p><strong>Decision status: no decision is ready.</strong> The data that is verified is the schedule and the official injury report.
The data the model produces (lines, strategy performance, prop lines) cannot be confirmed from an official source, so it is shown as unverified or left blank.</p>
</div>
<h2>What was verified</h2>
<ul>
<li><strong>Week 10 schedule.</strong> All 14 games, days, kickoff times and networks match the nfl.com schedule page
(<a href="{NFL_SCHED}">nfl.com/schedules/2026/REG10</a>). The four bye teams are CHI, DEN, PHI and TB.</li>
<li><strong>Injury report.</strong> 279 official rows on <a href="{NFL_INJ}">nfl.com/injuries</a>. The committed scrape on the latest refresh (22:40Z) matches all 279 rows on every field. The 22:36Z refresh had 295 rows, 37 field differences and 16 extra rows (RV-02, resolved on the later refresh).</li>
<li><strong>Official game designations.</strong> Six rows only (Out: Lucas Patrick, Colson Yankoff, Ben Brown, Carlton Davis III, TreVeyon Henderson; Questionable: Malik Harrison).</li>
<li><strong>Strategy gates.</strong> All 12 gate results reproduce from the committed JSON, so the model is consistent with its own rules.</li>
<li><strong>Standings correlations.</strong> All six reproduce from the 32 standings rows.</li>
</ul>
<h2>What could not be verified, and why</h2>
<ul>
<li><strong>Betting lines and prices.</strong> No official NFL source publishes them. Every own-line, market-line and edge value is blank (flag UNV-LINE).</li>
<li><strong>Strategy performance.</strong> Depends on those prices. Blank (flag UNV-PERF).</li>
<li><strong>Depth charts for backups.</strong> Official depth-chart pages are not found for the clubs checked (WAS: 404; BUF and KC: 404 in the committed log). Only 3 clubs have any rows, and the club page for KC calls its chart unofficial.</li>
<li><strong>Prop lines.</strong> Model output only; no prices (flag RV-26).</li>
</ul>
<h2>What the model shows (unverified model output)</h2>
<ul>
<li>In the 2026 test window the model's own spread is further from the result than the market (9.98 vs 9.49 points). Its blend weight is negative.</li>
<li>None of the 12 strategies passes all 8 gates after recomputation. S11 reaches 6 of 8; it fails significance and stability.</li>
<li>S04 and S06 are the same bet and should be merged. Diversification numbers depend on overlap-only correlations and are not reliable.</li>
</ul>
<h2>Irregularities that need a decision</h2>
<ul>
<li>The headline "103 starters flagged, official game status" is not supported. The committed data says {d["avail"]["counts"]["starters_impacted"]} starters are impacted, and {d["avail"]["counts"]["rows_practice_only_starters"]} of them are practice-only (RV-01).</li>
<li>The injury scrape was wrong on the 22:36Z refresh and correct on the 22:40Z refresh (RV-02). A per-refresh gate is still needed. The dashboard shows official page values. The Overview's NE row is stale (RV-28).</li>
<li>Two generators overwrite the root index.html, and five site generations overlap (RV-17, RV-21).</li>
<li>The Overview says "actionable" for a line the model's own validation does not support (RV-11).</li>
</ul>
<h2>Decisions needed from you</h2>
<p>See <a href="suggestions.html">Suggestions</a> (choose a path for each) and <a href="questions.html">Questions</a>.
The first decisions are: a depth-chart source for all 32 clubs (S-6A-03), whether to keep the "actionable" language (S-6A-04), and which site is canonical (S-6A-07).</p>
<h2>Source links</h2>
<p><a href="{NFL_SCHED}">nfl.com schedule</a> · <a href="{NFL_INJ}">nfl.com injury report</a> · <a href="{NFL_STAND}">nfl.com standings</a> ·
<a href="https://www.chiefs.com/team/depth-chart">chiefs.com depth chart</a> · <a href="https://nflreadr.nflverse.com/articles/dictionary_schedules.html">nflreadr schedule dictionary (third party)</a></p>
"""
    return page("executive.html", "Executive summary", "What is verified, what is not, what the model shows, and the decisions still open.", body)


def page_sources(d):
    rows = []
    for s in d["sources"].values():
        rows.append(td(f'<strong>{e(s["id"])}</strong>') + td(e(s["publisher"])) + td(link(s["url"], s["url"]))
                    + td(e(s.get("kind", ""))) + td(e(s.get("what", ""))) + td(e(s.get("retrieved", ""))))
    reg = table(["ID", "Publisher", "URL", "Kind", "What it is", "Retrieved"], rows)
    fetched = [
        ("https://www.nfl.com/injuries/", "nfl.com injury report", "7 chunks read, all rows transcribed", "Verified (279 rows)"),
        ("https://www.nfl.com/schedules/2026/REG10", "nfl.com schedule, Week 10", "3 chunks read", "Verified (14 games)"),
        ("https://www.nfl.com/teams/washington-commanders/depth-chart", "nfl.com depth chart, Washington", "1 chunk; 404 page", "Verified 404"),
        ("https://www.chiefs.com/team/depth-chart", "chiefs.com depth chart, Kansas City", "1 chunk; titled 'Unofficial Depth Chart'", "Verified (24 of 28 rows match)"),
        ("https://nflreadr.nflverse.com/articles/dictionary_schedules.html", "nflverse schedule dictionary (third party)", "1 chunk; 25 of 45 fields visible", "Partial"),
        ("https://www.nfl.com/players/sam-darnold/", "nfl.com player page, Sam Darnold", "1 chunk of 4; lists the news item with its summary", "Verified (link and summary)"),
        ("https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again", "nfl.com news item, Darnold ruled out", "headline and summary seen on the player page; body not read", "Headline and summary verified"),
    ]
    frows = [td(link(u, lab)) + td(e(what)) + td(e(res)) for u, lab, what, res in fetched]
    fetch_tbl = table(["Official URL", "What it is", "How it was read", "Result"], frows)
    body = f"""
{legend()}
<h2>Pages read in this session</h2>
<p>These pages were read on 2026-11-12. Results are in the rows above and in <a href="flagged.html">Flagged for review</a>.</p>
{fetch_tbl}
<h2>Source registry ({len(d["sources"])})</h2>
<p>The registry is the repo's own list (data/sources.json). Some entries are labelled differently from what their pages say (see RV-22).</p>
{reg}
"""
    return page("sources.html", "Sources", "Where every value comes from, and which pages were read in this session.", body)


CSS = """
:root{--ink:#1c2430;--mut:#5b6573;--line:#dfe4ea;--bg:#f6f8fa;--ok:#15703a;--okbg:#e5f5ec;--bad:#a4262c;--badbg:#fbe9ea;--warn:#8a5a00;--warnbg:#fff4d6;--int:#2c5ea8;--intbg:#e8f0fb;--mu:#55606e;--mubg:#eceff3;--acc:#1f4e8c}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
header.top{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:center;padding:12px 24px;background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
.brand{font-weight:700;color:var(--ink);text-decoration:none;font-size:16px}
nav{display:flex;flex-wrap:wrap;gap:4px 14px}
nav a{color:var(--mut);text-decoration:none;font-size:14px;padding:4px 2px;border-bottom:2px solid transparent}
nav a:hover{color:var(--ink)} nav a.on{color:var(--acc);border-bottom-color:var(--acc);font-weight:600}
main{max-width:1240px;margin:0 auto;padding:24px}
h1{font-size:26px;margin:4px 0 6px} h2{font-size:19px;margin:28px 0 8px}
.lead{color:var(--mut);margin:0 0 14px}
a{color:var(--acc)}
.legend{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;font-size:13px;color:var(--mut);margin:6px 0 16px;padding:10px 12px;background:#fff;border:1px solid var(--line);border-radius:8px}
.b{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:999px;white-space:nowrap}
.b.ok{background:var(--okbg);color:var(--ok)} .b.bad{background:var(--badbg);color:var(--bad)}
.b.warn{background:var(--warnbg);color:var(--warn)} .b.muted{background:var(--mubg);color:var(--mu)}
.b.internal{background:var(--intbg);color:var(--int)}
.b.high,.b.High{background:var(--badbg);color:var(--bad)} .b.Medium{background:var(--warnbg);color:var(--warn)} .b.Low{background:var(--mubg);color:var(--mu)}
.src-int{font-size:11px;color:var(--int);background:var(--intbg);padding:0 5px;border-radius:4px}
.src-oth{font-size:11px;color:var(--warn);background:var(--warnbg);padding:0 5px;border-radius:4px}
.flagtag{font-size:12px;color:var(--warn);font-weight:600}
.tw{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px;margin:8px 0 18px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#f1f4f8;font-weight:600;position:sticky;top:0;white-space:nowrap}
tbody tr:hover{background:#fafcff}
td.blank{background:repeating-linear-gradient(45deg,#fff,#fff 6px,#fbfbf3 6px,#fbfbf3 12px);color:#9aa3ad}
td.v{font-variant-numeric:tabular-nums}
td.pending{color:var(--mut);font-style:italic}
.small{font-size:12px;color:var(--mut)} .muted{color:var(--mut)}
.blank-inline{color:#9aa3ad;font-style:italic}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;margin:14px 0}
.card{display:block;background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 16px;text-decoration:none;color:var(--ink)}
.card:hover{border-color:var(--acc);box-shadow:0 2px 10px rgba(31,78,140,.08)}
.card-big{font-size:24px;font-weight:700;color:var(--acc)} .card h3{margin:4px 0 4px;font-size:16px} .card p{margin:0;color:var(--mut);font-size:13.5px}
.hero{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:12px 0}
.hero p{margin:6px 0}
.callout{background:#fff;border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:8px;padding:12px 16px;margin:12px 0}
.callout.warn{border-left-color:#c58a00;background:#fffdf6}
.callout p{margin:6px 0} .callout ul{margin:6px 0 6px 18px;padding:0}
.stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px;margin:12px 0}
.stats div{background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.stats b{display:block;font-size:22px;color:var(--acc)} .stats span{font-size:12.5px;color:var(--mut)}
footer{max-width:1240px;margin:0 auto;padding:18px 24px 40px;color:var(--mut);font-size:12.5px}
ul li{margin:4px 0}
@media (max-width:700px){main{padding:14px}h1{font-size:21px}}
"""


def main():
    d = load()
    out = {
        "index.html": page_index(d),
        "lines.html": page_lines(d),
        "strategies.html": page_strategies(d),
        "injuries.html": page_injuries(d),
        "depth.html": page_depth(d),
        "verification.html": page_verification(d),
        "questions.html": page_questions(d),
        "suggestions.html": page_suggestions(d),
        "flagged.html": page_flagged(d),
        "repo.html": page_repo(d),
        "executive.html": page_executive(d),
        "sources.html": page_sources(d),
    }
    os.makedirs(OUT, exist_ok=True)
    for name, text in out.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(text)
    with open(os.path.join(OUT, "style.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    with open(os.path.join(OUT, ".nojekyll"), "w") as f:
        f.write("")
    print(f"wrote {len(out)} pages + style.css to dashboard/")


if __name__ == "__main__":
    sys.exit(main())
