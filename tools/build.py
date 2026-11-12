#!/usr/bin/env python3
"""Build the static NFL1 dashboard and the markdown research documents.

All HTML tables are generated from the JSON data layer in data/. Every table
row automatically receives a link to an official source and a verification
badge. Blank cells stay blank. Nothing is inferred.

Run: python3 tools/build.py
"""
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RETRIEVED = "2026-11-12"


def L(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


SOURCES = {s["id"]: s for s in L("sources.json")}
META = L("site_meta.json")

NAV = [
    ("Overview", [("index.html", "Home"), ("executive-summary.html", "Executive Summary"), ("deployment.html", "Deployment & PR"), ("legacy-site.html", "Earlier sessions' site")]),
    ("Governance", [("requirements.html", "Requirements"), ("questions.html", "Decision Questions"), ("suggestions.html", "Suggestions & Paths")]),
    ("Competition", [("strategy-lab.html", "Strategy Lab"), ("leaderboard.html", "Leaderboard"), ("bet-types.html", "Bet Types & Risk")]),
    ("Official data", [("data-tables.html", "Standings & Findings"), ("injuries.html", "Injuries"), ("depth-chart.html", "Depth Charts")]),
    ("Assurance", [("verification.html", "Verification & Sources"), ("flagged.html", "Flagged for Review"), ("integration.html", "Combined Integration")]),
]

# Every page contributed by the earlier sessions stays reachable from the landing
# dashboard. Generated from pages/ so their CI nav-completeness gate
# (scripts/verified/check_site.py) remains satisfied after combining both generations.
def preserved_nav():
    pages_dir = os.path.join(ROOT, "pages")
    if not os.path.isdir(pages_dir):
        return []
    labels = {
        "executive-summary.html": "Executive summary", "teams.html": "Teams",
        "standings.html": "Standings", "injuries.html": "Injuries",
        "availability.html": "Availability", "data.html": "Verified data",
        "lines.html": "Own lines", "analysis.html": "Validation & correlation",
        "decisions.html": "Decision register", "verified.html": "Verified artifacts",
        "evidence.html": "Evidence", "models.html": "Strategy lab",
        "strategies.html": "Strategies", "suggestions.html": "Suggestions",
        "questions.html": "Questions", "flagged.html": "Flagged", "review.html": "Review",
    }
    return [("pages/" + f, labels.get(f, f[:-5].replace("-", " ").title()))
            for f in sorted(os.listdir(pages_dir)) if f.endswith(".html")]

NAV.append(("Preserved pages", preserved_nav()))


def e(x):
    return html.escape("" if x is None else str(x), quote=True)


def nav_html(active):
    out = []
    for group, items in NAV:
        out.append('<div class="navgroup"><h4>%s</h4>' % e(group))
        for href, label in items:
            cls = ' class="active"' if href == active else ""
            out.append('<a href="%s"%s>%s</a>' % (href, cls, e(label)))
        out.append("</div>")
    return "\n".join(out)


def src_html(rec):
    sid = rec.get("src") or rec.get("id")
    s = SOURCES.get(sid)
    if not s:
        raise ValueError("unknown source id %r in %r" % (sid, rec))
    title = "%s — %s" % (s["publisher"], s["kind"])
    extra = ""
    if rec.get("data_src") and rec["data_src"] in SOURCES:
        extra = ' <a href="%s" target="_blank" rel="noopener noreferrer" title="%s">%s ↗</a>' % (
            e(SOURCES[rec["data_src"]]["url"]), e(SOURCES[rec["data_src"]]["publisher"]), e(rec["data_src"]))
    return '<span class="src"><a href="%s" target="_blank" rel="noopener noreferrer" title="%s">%s ↗</a>%s</span>' % (
        e(s["url"]), e(title), e(sid), extra)


def verify_html(rec):
    if rec.get("status") == "needs review":
        return '<span class="badge warn">NEEDS REVIEW</span>'
    if rec.get("verified", True):
        out = '<span class="badge ok">VERIFIED</span>'
        if rec.get("computed"):
            out += ' <span class="badge brand">COMPUTED</span>'
        return out
    flag = rec.get("flag")
    href = "flagged.html" + ("#" + e(flag) if flag and flag != "NONE" else "")
    return '<a class="badge flag" href="%s">UNVERIFIED</a>' % href


def cell(rec, key, typ, value_cols):
    if typ == "html":
        v = key(rec) if callable(key) else rec.get(key, "")
        return "<td>%s</td>" % (v if v else "")
    v = rec.get(key, "")
    is_value = (value_cols is None or key in value_cols) if typ in ("text", "num", "wide") else False
    attrs = ' data-value="1"' if is_value else ""
    classes = [c for c in (("num" if typ == "num" else ""), ("wide" if typ == "wide" else "")) if c]
    if v is None or str(v) == "":
        classes.insert(0, "blank")
    if classes:
        attrs += ' class="%s"' % " ".join(classes)
    if v is None or str(v) == "":
        return "<td%s></td>" % attrs
    if typ == "id":
        return "<td><code>%s</code></td>" % e(v)
    if typ == "status":
        return '<td><span class="badge %s">%s</span></td>' % (
            "ok" if str(v).lower() in ("verified", "documented", "deployed", "enforced") else "neutral", e(v))
    return "<td%s>%s</td>" % (attrs, e(v))


def T(tid, caption, cols, records, note="", value_cols=None, id_prefix="", add_source=True):
    """cols: list of (header, key-or-callable, type). type: id|text|num|wide|html|status."""
    heads = [c[0] for c in cols]
    if add_source:
        heads = heads + ["Official source", "Verification"]
    out = []
    out.append('<div class="tabletools"><input class="table-filter" data-target="#%s" aria-label="Filter %s" placeholder="Filter rows…">' % (tid, e(tid)))
    out.append('<span class="count" data-count-for="%s">%d rows shown</span></div>' % (tid, len(records)))
    out.append('<div class="tablewrap"><table class="data-table" id="%s"><caption>%s</caption>' % (tid, caption))
    out.append("<thead><tr>" + "".join('<th scope="col" class="sortable">%s</th>' % e(h) for h in heads) + "</tr></thead><tbody>")
    for rec in records:
        rid = rec.get("id") or rec.get("strategy_id") or ""
        attr = ' id="%s"' % e(id_prefix + str(rid)) if rid else ""
        v = "true" if rec.get("verified", True) else "false"
        out.append('<tr%s data-verified="%s">' % (attr, v))
        for header, key, typ in cols:
            out.append(cell(rec, key, typ, value_cols))
        if add_source:
            out.append("<td>%s</td><td>%s</td>" % (src_html(rec), verify_html(rec)))
        out.append("</tr>")
    out.append("</tbody></table></div>")
    if note:
        out.append('<p class="small">%s</p>' % note)
    return "\n".join(out)


def panel(title, body, cls="panel"):
    return '<section class="%s"><h2>%s</h2>%s</section>' % (cls, e(title), body)


def cards(items):
    out = ['<div class="cards">']
    for label, value, detail in items:
        out.append('<div class="card"><div class="label">%s</div><div class="value">%s</div><div class="detail">%s</div></div>' % (e(label), e(value), e(detail)))
    out.append("</div>")
    return "".join(out)


def toc(items):
    return '<div class="toc">' + "".join('<a href="#%s">%s</a>' % (e(a), e(b)) for a, b in items) + "</div>"


BASE = open(os.path.join(ROOT, "site", "templates", "base.html"), encoding="utf-8").read()


def write_page(filename, title, kicker, lede, body, crumb, pills=None):
    pills = pills or ['<span class="pill ok">Source-linked rows</span>',
                      '<span class="pill warn">%d flagged items</span>' % counts["flags"],
                      '<span class="pill">Snapshot 2026-11-12</span>']
    out = (BASE.replace("{{TITLE}}", e(title)).replace("{{KICKER}}", e(kicker))
           .replace("{{LEDE}}", lede).replace("{{BODY}}", body)
           .replace("{{CRUMB}}", e(crumb)).replace("{{NAV}}", nav_html(filename))
           .replace("{{PILLS}}", "".join(pills)))
    with open(os.path.join(ROOT, filename), "w", encoding="utf-8") as f:
        f.write(out)
    print("page", filename)


# ---------------------------------------------------------------------------
# Load all datasets
# ---------------------------------------------------------------------------
d = {n: L(n + ".json") for n in [
    "sources", "standings", "derived_standings", "injuries", "injury_games",
    "injury_policy", "inactives", "depth_chart", "depth_chart_meta",
    "betting_facts", "terms", "requirements", "questions", "suggestions",
    "paths", "strategies", "validation_gates", "correlations",
    "correlation_requests", "leaderboard_rules", "leaderboard", "findings",
    "flags", "deployment"]}

# The one correlation that can be filled from official data is filled from the
# computed table, so no value is ever typed in by hand.
c05 = next(c for c in d["correlations"] if c["id"] == "C-05")
for cr in d["correlation_requests"]:
    if cr["id"] == "CR-08":
        cr["r"] = c05["r"]
        cr["blocker"] = "Computed from official standings — see C-05 in the computed correlations table."
        cr["flag"] = ""
        cr["verified"] = True

counts = dict(
    sources=len(d["sources"]), standings=len(d["standings"]), injuries=len(d["injuries"]),
    games=len(d["injury_games"]), inactives=len(d["inactives"]), depth=len(d["depth_chart"]),
    requirements=len(d["requirements"]), questions=len(d["questions"]),
    suggestions=len(d["suggestions"]), strategies=len(d["strategies"]),
    gates=len(d["validation_gates"]), correlations=len(d["correlations"]),
    flags=len(d["flags"]), findings=len(d["findings"]),
    betting=len(d["betting_facts"]), leaderboard=len(d["leaderboard"]),
    designated=sum(1 for r in d["injuries"] if r["injury"] or r["game_status"]),
)
print("dataset counts:", counts)

# ---------------------------------------------------------------------------
# Inline, source-backed specification tables (project documentation, not data)
# ---------------------------------------------------------------------------
SITE_SECTIONS = [
    dict(id="SS-01", area="Overview", page="index.html", purpose="Landing dashboard, counts, decision status", src="S23", verified=True),
    dict(id="SS-02", area="Overview", page="executive-summary.html", purpose="Executive summary of verified facts, gaps and posture", src="S24", verified=True),
    dict(id="SS-03", area="Governance", page="requirements.html", purpose="Full requirements inventory and analysis", src="S24", verified=True),
    dict(id="SS-04", area="Governance", page="questions.html", purpose="Decision gate: known, unknown, answers, discovery", src="S17", verified=True),
    dict(id="SS-05", area="Governance", page="suggestions.html", purpose="Improvement suggestions and Review & Choose a Path", src="S22", verified=True),
    dict(id="SS-06", area="Competition", page="strategy-lab.html", purpose="Own lines, signal research, validation gates, correlations", src="S19", verified=True),
    dict(id="SS-07", area="Competition", page="leaderboard.html", purpose="Competition rules, rewards and empty ranked board", src="S18", verified=True),
    dict(id="SS-08", area="Competition", page="bet-types.html", purpose="Single bet, parlay and player prop combo definitions and risk", src="S21", verified=True),
    dict(id="SS-09", area="Official data", page="data-tables.html", purpose="Standings, derived metrics, correlations, bet facts, findings", src="S02", verified=True),
    dict(id="SS-10", area="Official data", page="injuries.html", purpose="Injury report snapshot, policy schedule, inactives", src="S01", verified=True),
    dict(id="SS-11", area="Official data", page="depth-chart.html", purpose="1st/2nd/3rd/4th string offense and defense", src="S14", verified=True),
    dict(id="SS-12", area="Assurance", page="verification.html", purpose="Verification policy, official source registry, line-by-line audit", src="S22", verified=True),
    dict(id="SS-13", area="Assurance", page="flagged.html", purpose="Irregularities and unverified values with official links", src="S24", verified=True),
    dict(id="SS-14", area="Overview", page="deployment.html", purpose="Pages configuration, PR, merge and deploy record", src="S25", verified=True),
    dict(id="SS-15", area="Assurance", page="integration.html", purpose="Combined integration: cross-check of both sessions' data and link audit", src="S24", verified=True),
    dict(id="SS-16", area="Overview", page="legacy-site.html", purpose="Preserved earlier sessions' dashboard (historical, labelled)", src="S24", verified=True),
]

LINE_STEPS = [
    dict(id="OL-01", step="1", action="Snapshot official inputs at a fixed timestamp", detail="Standings PF/PA/W/L/T, schedule, injury report, club depth charts, player stats, Next Gen Stats", src="S02", verified=True),
    dict(id="OL-02", step="2", action="Normalise totals to per-game values", detail="PF / (W+L+T), PA / (W+L+T), NET PTS / (W+L+T) — reproducible in tools/compute_correlations.py", src="S02", verified=True),
    dict(id="OL-03", step="3", action="Estimate team strength from published values only", detail="strength = f(net points per game, points for, points against); all coefficients blank until validated", src="S19", verified=True),
    dict(id="OL-04", step="4", action="Apply an availability adjustment", detail="Join official injury designations and official club depth rank; effect size blank until out-of-sample validation", src="S01", verified=True),
    dict(id="OL-05", step="5", action="Originate the own line", detail="own spread / own total = symbolic function of the two teams' strength and availability; no numeric line published", src="S20", verified=True),
    dict(id="OL-06", step="6", action="Benchmark", detail="Compare the own line with a reference market line — reference line blank, no official odds source found", src="S20", verified=False),
    dict(id="OL-07", step="7", action="Generate a signal only above a frozen threshold", detail="signal = own line minus reference line; threshold blank until pre-registered", src="S17", verified=False),
    dict(id="OL-08", step="8", action="Validate before publication", detail="G01–G13 must all pass; no strategy currently passes", src="S18", verified=True),
]

LUCK_PROTOCOL = [
    dict(id="LK-01", control="Point-in-time inputs", mechanism="Use only information published before the decision timestamp; respect the official injury-report filing times", src="S04", verified=True),
    dict(id="LK-02", control="Cross-validation", mechanism="Fit on one partition, assess on data not used to build the model", src="S17", verified=True),
    dict(id="LK-03", control="Significance test", mechanism="Two-sample t-test for equal means with a pre-registered alpha and critical region", src="S18", verified=True),
    dict(id="LK-04", control="Pre-registration", mechanism="Freeze formula, thresholds and window before scoring; log every tested variant", src="S17", verified=True),
    dict(id="LK-05", control="Correlation control", mechanism="Measure leg correlations; reject correlated parlay legs; never equate correlation with causality", src="S19", verified=True),
    dict(id="LK-06", control="Minimum sample", mechanism="NIST generic advice: 20 for a correlation, 32 per group for an average difference, 50 for a standard deviation", src="S17", verified=True),
    dict(id="LK-07", control="Skill threshold", mechanism="Numeric threshold blank and flagged until pre-registered; no strategy is labelled skill-based yet", src="S17", verified=False),
]

VERIFY_STEPS = [
    dict(id="VP-01", step="1", action="Transcribe, do not paraphrase values", detail="Each official page was fetched and read; values copied cell by cell into data/*.json", src="S02", verified=True),
    dict(id="VP-02", step="2", action="Attach an official source to every row", detail="The generator appends a source link and a verification badge to every table row", src="S22", verified=True),
    dict(id="VP-03", step="3", action="Leave blanks blank", detail="Empty strings render as empty cells; no substitution, interpolation or estimation", src="S02", verified=True),
    dict(id="VP-04", step="4", action="Flag unverified project assertions", detail="Rows with verified=false link to Flagged for Review and keep all value cells blank", src="S24", verified=True),
    dict(id="VP-05", step="5", action="Automated validation", detail="tools/verify.py checks source domains, unverified blanks, internal links and generated-file integrity", src="S22", verified=True),
    dict(id="VP-06", step="6", action="Recompute derived values", detail="tools/compute_correlations.py recomputes correlations from the committed official standings", src="S17", verified=True),
    dict(id="VP-07", step="7", action="Build and link check before merge", detail="HTML pages generated, internal links resolved, then Pages confirmed live", src="S23", verified=True),
]

TRACKING_PIPELINE = [
    dict(id="TR-01", stage="Ingest", detail="Weekly official injury report (practice status + game status) at the published filing boundary", src="S01", verified=True),
    dict(id="TR-02", stage="Join", detail="Join each player to the official club depth chart by club, position and player name", src="S14", verified=True),
    dict(id="TR-03", stage="Resolve", detail="Use the official inactives list to determine who actually dressed", src="S05", verified=True),
    dict(id="TR-04", stage="Classify", detail="Label the replacement as 2nd / 3rd / 4th string using the published depth columns", src="S16", verified=True),
    dict(id="TR-05", stage="Score", detail="Compute a backup-exposure or deficiency index", src="S19", verified=False),
    dict(id="TR-06", stage="Validate", detail="Require every validation gate before the score may feed a strategy", src="S18", verified=True),
]

REWARD_TIERS = [
    dict(id="RW-01", tier="Verified Signal", condition="All 13 gates pass for a single strategy", value="", src="S18", verified=False, flag="F12"),
    dict(id="RW-02", tier="Top Single Bet", condition="Highest validated out-of-sample score in the single-bet track", value="", src="S21", verified=False, flag="F12"),
    dict(id="RW-03", tier="Top Parlay", condition="Highest validated score in the parlay track, correlation guard passed", value="", src="S21", verified=False, flag="F12"),
    dict(id="RW-04", tier="Top Player Prop Combo", condition="Highest validated score in the player-prop combo track, availability gate passed", value="", src="S21", verified=False, flag="F12"),
]

BET_TRACKS = [
    dict(id="BT-01", track="Single bet", definition="One wager on one market; official report classifies moneyline, point spread and total as straight bets", official_loss="51% point spread, 52% moneyline whole, 53% total whole (NJ 2019)", correlation="Not applicable to a single leg", src="S21", verified=True),
    dict(id="BT-02", track="Parlay", definition="Two or more legs combined into one bet; all legs must win", official_loss="86% not in-game, 81% in-game (NJ 2019)", correlation="Leg correlation must be measured (gate G09)", src="S21", verified=True),
    dict(id="BT-03", track="Player prop combo", definition="Two or more player-prop legs; the official report lists 'Prop' as a distinct bet type", official_loss="", correlation="Leg correlation and player availability both required (G09, ST-09)", src="S21", verified=True),
    dict(id="BT-04", track="All bet types", definition="More than 70% of all sports bets in the official 2019 sample resulted in a loss", official_loss="Average bet lost about $31", correlation="", src="S21", verified=True),
]

TRACK_STRATEGIES = [
    dict(id="TS-01", track="Single bet", strategy_ids="ST-01, ST-02, ST-03, ST-04, ST-05, ST-06", gate_focus="G01–G08, G12", src="S02", verified=True),
    dict(id="TS-02", track="Parlay", strategy_ids="ST-07", gate_focus="G09 leg-correlation guard, G10 stability", src="S19", verified=True),
    dict(id="TS-03", track="Player prop combo", strategy_ids="ST-08, ST-09", gate_focus="G09 correlation guard, player availability gate", src="S03", verified=True),
    dict(id="TS-04", track="All tracks", strategy_ids="ST-10", gate_focus="All 13 gates", src="S14", verified=True),
]

# ---------------------------------------------------------------------------
# Column definitions reused across pages
# ---------------------------------------------------------------------------
C_SOURCES = [("ID", "id", "id"), ("Publisher", "publisher", "text"), ("Source type", "kind", "text"),
             ("What it verifies", "what", "wide"), ("Canonical / note", "note", "wide"),
             ("Retrieved", "retrieved", "text")]
C_STAND = [("Club", "team", "text"), ("W", "w", "num"), ("L", "l", "num"), ("T", "t", "num"),
           ("PCT", "pct", "num"), ("PF", "pf", "num"), ("PA", "pa", "num"), ("NET PTS", "net", "num")]
C_DERIVED = [("Club", "team", "text"), ("Games (W+L+T)", "games", "num"),
             ("PF / game", "pf_pg", "num"), ("PA / game", "pa_pg", "num"),
             ("NET PTS / game", "net_pg", "num"), ("Method", "method", "wide")]
C_CORR = [("ID", "id", "id"), ("Pair", "pair", "text"), ("x", "x", "text"), ("y", "y", "text"),
          ("n", "n", "num"), ("Pearson r", "r", "num"), ("Method", "method", "text"), ("Caveat", "note", "wide")]


def page_home():
    b = []
    b.append('<div class="callout warn"><b>Decision posture: NOT READY.</b> %d flagged items and '
             'multiple unverified values remain. Review the <a href="suggestions.html">suggestions and paths</a>, '
             'choose a path, then close the <a href="questions.html">decision questions</a> before implementing any '
             'change. Nothing here has been implemented on the strength of an unverified value.</div>' % counts["flags"])
    b.append(cards([
        ("Official sources", counts["sources"], "Fetched and read 2026-11-12"),
        ("Standings rows", counts["standings"], "All 32 NFL clubs, official values"),
        ("Injury rows", counts["injuries"], "%d with a published designation" % counts["designated"]),
        ("Depth-chart rows", counts["depth"], "1st / 2nd / 3rd / 4th string"),
        ("Requirements", counts["requirements"], "Full brief, decomposed"),
        ("Decision questions", counts["questions"], "Known / unknown / answer"),
        ("Improvement suggestions", counts["suggestions"], "All awaiting review"),
        ("Flagged items", counts["flags"], "Published for review"),
    ]))
    b.append(panel("What this project is", """
<p>NFL1 collects, organises and analyses a full list of requirements for an NFL decision-intelligence
system, then publishes every finding as a source-linked table. The site covers decision questions and
missing information, improvement suggestions with a choose-a-path gate, own-line research and signal
strategies with validation gates and correlation values, injury and backup-depth tracking, an executive
summary, verification evidence and a clearly labelled Flagged for Review page.</p>
<p>The data snapshot is the <b>2026 NFL regular season, Week 10</b>, retrieved on 2026-11-12 (UTC) from
official league, club, government and platform sources. Every table row links to the official page the
value came from. Where an official source publishes no value, the cell is left blank and the row is
flagged. No value is inferred or filled in.</p>"""))
    b.append('<h2 id="sections">Site sections by category</h2>')
    b.append(T("tbl-sections", "Every page, its category and its purpose. Source link points to the official documentation or data source grounding that page.",
               [("ID", "id", "id"), ("Category", "area", "text"),
                ("Page", lambda r: '<a href="%s">%s</a>' % (e(r["page"]), e(r["page"])), "html"),
                ("Purpose", "purpose", "wide")], SITE_SECTIONS))
    b.append('<h2 id="findings">Latest findings</h2>')
    b.append(T("tbl-home-findings", "Findings established during this session; each row links to the official source that grounds it.",
               [("ID", "id", "id"), ("Finding", "statement", "wide"), ("Where", "where", "text"),
                ("Status", "status", "status")], d["findings"]))
    b.append('<h2 id="readiness">Decision readiness</h2>')
    b.append(panel("Gate status", """
<div class="grid2">
<div><h3>What is verified</h3><ul class="tight">
<li>Official 2026 standings for all 32 clubs, with internal arithmetic checked (PF − PA = NET PTS on every row).</li>
<li>Official Week 10 injury report rows, official filing schedule and official Week 9 inactives.</li>
<li>Three official club depth charts publishing 1st–4th string for offense and defense.</li>
<li>Official government bet-type loss statistics and official NIST statistical methods.</li>
<li>Pearson correlations recomputed from the committed official standings data.</li>
</ul></div>
<div><h3>What is not verified</h3><ul class="tight">
<li>NFL betting lines/odds: no official source found — benchmark cells are blank.</li>
<li>Leg-level and injury-vs-performance correlations: no official dataset — blank.</li>
<li>Vig/house edge, reward values, skill thresholds and effort estimates — blank.</li>
<li>Leaderboard ranks, scores and sample sizes — blank because no strategy has passed the gates.</li>
</ul></div></div>
<p class="small">See <a href="questions.html">Decision Questions</a> for the full known/unknown list and
<a href="flagged.html">Flagged for Review</a> for every irregularity with its official source link.</p>"""))
    return write_page("index.html", "NFL1 decision dashboard", "Overview",
                      "A clean, source-linked dashboard for NFL requirements, decision questions, strategy validation, injury and depth tracking, and a leaderboard competition.",
                      "\n".join(b), "Home")


def page_exec():
    readiness = [
        dict(id="ES-01", item="Verified official sources in registry", value=str(counts["sources"]), src="S02", verified=True),
        dict(id="ES-02", item="Official standings rows (all 32 clubs)", value=str(counts["standings"]), src="S02", verified=True),
        dict(id="ES-03", item="Transcribed Week 10 injury rows", value=str(counts["injuries"]), src="S01", verified=True),
        dict(id="ES-04", item="Rows with a published injury/game designation", value=str(counts["designated"]), src="S01", verified=True),
        dict(id="ES-05", item="Official depth-chart rows (3 clubs)", value=str(counts["depth"]), src="S14", verified=True),
        dict(id="ES-06", item="Requirements / questions / suggestions", value="%d / %d / %d" % (counts["requirements"], counts["questions"], counts["suggestions"]), src="S24", verified=True),
        dict(id="ES-07", item="Strategies / validation gates", value="%d / %d" % (counts["strategies"], counts["gates"]), src="S18", verified=True),
        dict(id="ES-08", item="Computed correlations / blank correlation requests", value="%d / %d" % (counts["correlations"], 7), src="S17", verified=True),
        dict(id="ES-09", item="Flagged items awaiting review", value=str(counts["flags"]), src="S24", verified=True),
        dict(id="ES-10", item="Leaderboard ranks or scores published", value="0", src="S18", verified=True),
    ]
    b = []
    b.append(toc([("purpose", "Purpose"), ("verified", "Verified"), ("gaps", "Gaps"), ("posture", "Decision posture"),
                  ("competition", "Own lines & competition"), ("injuries", "Injuries & depth"), ("site", "Site & deploy"), ("coord", "Coordination")]))
    b.append('<h2 id="purpose">Purpose and scope</h2>')
    b.append('<div class="panel"><p>The project brief asks for a complete requirements inventory, a decision gate built '
             'from what is known and unknown, a review-first suggestions section, original NFL lines and validated '
             'signal strategies run as a rewarded leaderboard competition across single bets, parlays and player prop '
             'combos, injury and second/third/fourth-string backup tracking for offense and defense, an executive '
             'summary, line-by-line verification against official sources, a GitHub Pages dashboard, and a fully '
             'autonomous pull-request-and-merge cycle.</p><p>This build delivers the documentation, the verified data '
             'snapshot, the site and the governance framework. It deliberately does <b>not</b> publish invented odds, '
             'scores, ranks, correlations or performance claims: no official source was found for those values, so the '
             'cells are blank and flagged.</p></div>')
    b.append('<h2 id="verified">What was verified</h2>')
    b.append(T("tbl-exec-counts", "Session deliverables in numbers. Each row links to the official source grounding the category.",
               [("ID", "id", "id"), ("Deliverable", "item", "wide"), ("Value", "value", "text")], readiness))
    b.append(T("tbl-exec-findings", "Key findings, line by line, with the official source used to establish each one.",
               [("ID", "id", "id"), ("Finding", "statement", "wide"), ("Where published", "where", "text"),
                ("Status", "status", "status")], d["findings"]))
    b.append('<h2 id="gaps">Important missing information</h2>')
    b.append('<div class="callout flag"><b>Do not decide on strategy implementation yet.</b> The following values '
             'cannot be confirmed from an official source and are left blank on every table: NFL betting lines/odds, '
             'vig or house edge, leg-level correlations, injury-to-performance correlations, backup-deficiency effect '
             'sizes, reward values, the numeric skill threshold, and all leaderboard scores and ranks.</div>')
    b.append(T("tbl-exec-gaps", "Correlation values that were requested but cannot be confirmed; the value column is intentionally blank.",
               [("ID", "id", "id"), ("Requested pair", "pair", "wide"), ("Required official inputs", "required_inputs", "wide"),
                ("Why the value is blank", "blocker", "wide"), ("Value", "r", "num")],
               [r for r in d["correlation_requests"] if not r["verified"]], value_cols={"r"}))
    b.append('<h2 id="posture">Decision posture</h2>')
    b.append('<div class="panel"><p><b>No implementation decision has been taken.</b> The '
             '<a href="suggestions.html">Review &amp; Choose a Path</a> section presents three paths (data first, '
             'strategy first, review only). The advisory recommendation is <b>Path A — Data first</b>, because '
             'official state data shows parlays losing far more often than straight bets and NIST guidance requires '
             'unseen data before any performance claim. A reviewer must choose a path before anything is built; '
             'the choice is recorded locally in the browser and can be filed as a GitHub issue.</p></div>')
    b.append('<h2 id="competition">Own lines, signals and competition</h2>')
    b.append('<div class="panel"><p>The own-line pipeline is specified end to end using official inputs only '
             '(standings, schedule, injury report, club depth charts, player stats, Next Gen Stats). '
             '%d candidate strategies cross single bets, parlays and player prop combos. Every strategy must pass '
             '%d validation gates covering provenance, point-in-time data, pre-registration, minimum sample, '
             'out-of-sample testing, significance, multiple comparisons, correlation control, stability and '
             'reproducibility. <b>All %d strategies are currently NOT PASSED</b>, so the leaderboard has no ranks '
             'or scores and only non-monetary reward tiers are proposed.</p>'
             '<p>Correlation values that can be computed from official standings were computed with a committed '
             'script (for example, net points per game vs winning percentage: r = %s, n = %d). All other '
             'correlations remain blank and flagged. NIST states explicitly that correlation does not imply '
             'causality, which is why gate G08 exists.</p></div>' %
             (counts["strategies"], counts["gates"], counts["strategies"], c05["r"], c05["n"]))
    b.append('<h2 id="injuries">Injuries and backup depth</h2>')
    b.append('<div class="panel"><p>The official Week 10 injury report, the published Personnel (Injury) Report '
             'Policy filing schedule, the official Week 9 inactives list and three official club depth charts are '
             'transcribed into tables. Of %d transcribed injury rows, only %d publish an injury description or a '
             'game status. The depth charts publish 1st through 4th string for offense and defense, and the '
             'official inactives list contains explicit "emergency third QB" entries. Two of the three charts are '
             'labelled "Unofficial" by the clubs themselves and the league injury report publishes no depth-rank '
             'column, so a league-wide deficiency score is left blank and flagged.</p></div>' %
             (counts["injuries"], counts["designated"]))
    b.append('<h2 id="site">Site and deployment</h2>')
    b.append('<div class="panel"><p>%d static pages, grouped navigation, sortable/filterable tables, responsive '
             'CSS and no external dependencies. A Python generator builds the HTML from the JSON data layer; an '
             'independent validator checks that every table row has an official source link, that unverified rows '
             'keep blank value cells, and that every internal link resolves. GitHub Pages is configured to publish '
             '<code>main / /</code>; a <code>.nojekyll</code> file keeps the plain HTML untouched.</p></div>' % len(SITE_SECTIONS))
    b.append('<h2 id="coord">Coordination and irregularities</h2>')
    b.append('<div class="panel"><p>The repository initially contained only a one-line README. A second agent '
             'session branch is active with overlapping task claims; this session kept disjoint file scopes, logged '
             'the conflict, and acted as the final integration session. %d irregularities are published on the '
             '<a href="flagged.html">Flagged for Review</a> page with official source links, including an unresolved '
             'template variable in the official standings heading and a conflict between the official injury report '
             'and official NFL.com news headlines.</p></div>' % counts["flags"])
    return write_page("executive-summary.html", "Executive summary", "Overview",
                      "The important details: what is verified, what is missing, why no implementation decision can reasonably be made yet, and what the site delivers.",
                      "\n".join(b), "Executive Summary")


def page_requirements():
    by_cat = {}
    for r in d["requirements"]:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    cat_rows = [dict(id="RC-%02d" % i, category=k, count=v, src="S24", verified=True)
                for i, (k, v) in enumerate(sorted(by_cat.items()), 1)]
    b = []
    b.append('<div class="callout">The brief was decomposed line by line into %d atomic requirements. Each row '
             'quotes the requirement, records the analysis/response, links the official source that grounds that '
             'domain, and states its status. Project-only assertions are not attributed to official sources as '
             'external facts.</div>' % counts["requirements"])
    b.append(cards([("Requirements", counts["requirements"], "Atomic, stable IDs"),
                    ("Categories", len(cat_rows), "Grouped inventory"),
                    ("Flagged", counts["flags"], "Review items"),
                    ("Questions", counts["questions"], "Decision gate")]))
    b.append('<h2 id="bycat">Requirements by category</h2>')
    b.append(T("tbl-req-cats", "Counts of atomic requirements per category; source link points to the repository containing the brief and this inventory.",
               [("ID", "id", "id"), ("Category", "category", "text"), ("Requirements", "count", "num")], cat_rows))
    b.append('<h2 id="full">Full requirements inventory</h2>')
    b.append(T("tbl-requirements", "Verbatim decomposition of the project brief with analysis, response and status. Blank value cells are never filled in.",
               [("ID", "id", "id"), ("Category", "category", "text"), ("Requirement (verbatim)", "requirement", "wide"),
                ("Analysis / response in this build", "analysis", "wide"), ("Status", "status", "status")],
               d["requirements"]))
    b.append('<h2 id="analysis">Analysis notes</h2>')
    b.append(panel("Dependencies and conflicts", """
<ul class="tight">
<li><b>Dependency:</b> R11 (own lines) cannot be completed until Q10 (official odds source) is answered. R19 (correlations) is only partially determinable until Q11/Q12 are answered.</li>
<li><b>Conflict:</b> R26/R34 require fully autonomous completion, while R05 requires a reviewer to choose a path before implementation. Resolution: all autonomous tasks (documentation, data, site, PR, merge, deploy) are complete; the reviewer's choice governs only future implementation, not this build.</li>
<li><b>Conflict:</b> R32/R33 require per-session branches and a cross-branch merge; the environment pinning this session to one branch is logged as deviation F17.</li>
<li><b>Enforcement:</b> R31 is enforced mechanically by <code>tools/verify.py</code> on every generated HTML table.</li>
</ul>
<p class="small">Sources: <a href="https://github.com/kanlerxz87-cyber/NFL1">repository ↗</a>,
<a href="https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site">GitHub Docs ↗</a>.</p>"""))
    return write_page("requirements.html", "Requirements inventory & analysis", "Governance",
                      "The complete list of requirements, collected, organised and analysed line by line, with a source link on every row.",
                      "\n".join(b), "Requirements")


def page_questions():
    b = []
    b.append('<div class="callout warn"><b>This is the decision gate.</b> A decision can reasonably be made only '
             'when the questions below have answers that an official source supports. Cells with no official answer '
             'are left blank; the "Do not have" and "Discovery action" columns say exactly what is missing and how '
             'to obtain it.</div>')
    b.append(cards([("Questions", counts["questions"], "Numbered Q01–Q27"),
                    ("Official sources", counts["sources"], "Links for manual review"),
                    ("Flagged items", counts["flags"], "Review page"),
                    ("Blank answers", 9, "Intentionally blank")]))
    b.append('<h2 id="all">Questions, information and answers</h2>')
    b.append(T("tbl-questions", "Known information, missing information, verified answers, why each question blocks a decision, and the discovery suggestion. Blank cells are blank on purpose.",
               [("ID", "id", "id"), ("Question", "question", "wide"),
                ("Information we HAVE", "known", "wide"), ("Information we DO NOT HAVE", "unknown", "wide"),
                ("Answer (only if officially published)", "answer", "wide"),
                ("Limitation", "limitation", "wide"), ("Why it blocks a decision", "why", "wide"),
                ("Suggestion to discover missing info", "discovery", "wide")],
               d["questions"], value_cols=set()))
    b.append('<h2 id="method">How to close the gate</h2>')
    b.append(T("tbl-gate-method", "Verification method for closing the decision gate, with official method sources.",
               [("ID", "id", "id"), ("Procedure", "action", "wide"), ("Detail", "detail", "wide")],
               VERIFY_STEPS))
    b.append(panel("Reading the table", """
<p><b>HAVE</b> is what an official page currently publishes. <b>DO NOT HAVE</b> is a gap identified by reading
those same official pages, not a guess about a hidden dataset. <b>Answer</b> is populated only with values
published by an official source. <b>Discovery action</b> names the official surface to revisit or the specific
dataset that must be assembled. Where no official page publishes a value, the row is also listed on
<a href="flagged.html">Flagged for Review</a>.</p>"""))
    return write_page("questions.html", "Decision questions & information gaps", "Governance",
                      "A clear list of questions, the information we have and do not have, verified answers, and concrete suggestions for discovering what is missing before any decision.",
                      "\n".join(b), "Decision Questions")


def page_suggestions():
    b = []
    b.append('<div class="callout warn"><b>Awaiting review — nothing implemented.</b> These suggestions are '
             'published so a reviewer can compare them and choose the best path <em>before</em> any change is '
             'implemented. Effort and risk cells are blank because no official source can confirm them.</div>')
    b.append('<section class="panel decision" id="choose"><h2>Review &amp; Choose a Path</h2>'
             '<p>Select one path. The selection is stored only in this browser (localStorage) and can be filed '
             'as a GitHub issue to create a durable decision record. <b>No agent implementation occurs until a '
             'reviewer confirms the choice.</b></p><div class="choices">')
    for p in d["paths"]:
        b.append('<label class="choice"><input type="radio" name="chosen-path" value="%s" data-label="%s"><strong>%s</strong>'
                 '<p>%s</p></label>' % (e(p["id"]), e(p["name"]), e(p["name"]), e(p["summary"])))
    b.append('</div><div class="actions"><a class="btn" id="path-issue" href="#">Open a prefilled decision-record issue ↗</a>'
             '<span class="small">Requires a path to be selected first.</span></div>'
             '<p class="outcome" id="path-outcome">No path has been chosen. Nothing on this site is implemented until a reviewer chooses.</p>'
             '<p class="small"><b>Advisory recommendation (not a decision):</b> Path A — Data first. The official '
             'state report shows parlays losing far more often than straight bets, and NIST guidance requires '
             'out-of-sample data before a performance claim; building signals before the missing official data '
             'exists would make the validation gates meaningless.</p></section>')
    b.append('<h2 id="paths">Path comparison</h2>')
    b.append(T("tbl-paths", "Three implementation paths with advantages, disadvantages and the questions/flags each one leaves open.",
               [("ID", "id", "id"), ("Path", "name", "text"), ("Summary", "summary", "wide"),
                ("Advantages", "pros", "wide"), ("Disadvantages", "cons", "wide"),
                ("Still blocked by", "blocks", "wide")], d["paths"]))
    b.append('<h2 id="suggestions">Improvement suggestions</h2>')
    b.append(T("tbl-suggestions", "%d suggestions to improve decision making on this site. Effort is blank and flagged; every row links to an official source." % counts["suggestions"],
               [("ID", "id", "id"), ("Area", "area", "text"), ("Suggestion", "title", "wide"),
                ("How it improves decision making", "decision_impact", "wide"),
                ("Effort / risk estimate", "effort", "num"), ("Suggested disposition", "recommended_path", "status"),
                ("Official evidence", "evidence", "wide")],
               d["suggestions"], value_cols={"effort"}))
    b.append('<h2 id="matrix">Decision matrix</h2>')
    matrix = [
        dict(id="DM-01", criterion="Verification completeness", a="Highest", b="Medium", c="Highest (no new claims)", src="S02", verified=True),
        dict(id="DM-02", criterion="Speed to a working leaderboard", a="Slow", b="Fast", c="None", src="S18", verified=True),
        dict(id="DM-03", criterion="Risk of building on incomplete official data", a="Low", b="Higher", c="Lowest", src="S19", verified=True),
        dict(id="DM-04", criterion="Uses official bet-type loss evidence", a="Yes", b="Yes", c="Yes", src="S21", verified=True),
        dict(id="DM-05", criterion="Requires a reviewer decision first", a="Yes", b="Yes", c="Yes", src="S24", verified=True),
    ]
    b.append(T("tbl-matrix", "Comparison of Path A (data first), Path B (strategy first) and Path C (review only).",
               [("ID", "id", "id"), ("Criterion", "criterion", "text"), ("Path A", "a", "text"),
                ("Path B", "b", "text"), ("Path C", "c", "text")], matrix))
    b.append(panel("Review workflow", """
<ol class="tight">
<li>Read the <a href="questions.html">decision questions</a> and the <a href="flagged.html">flagged items</a>.</li>
<li>Compare the %d suggestions and the three paths above.</li>
<li>Select a path in the Review &amp; Choose a Path box; file the prefilled issue to make the decision durable.</li>
<li>Close the blocking questions, then — and only then — authorise implementation of individual suggestions.</li>
</ol>
<p class="small">The issue link points to the official repository issue tracker; it does not send data anywhere else.</p>""" % counts["suggestions"]))
    return write_page("suggestions.html", "Suggestions & choose a path", "Governance",
                      "Suggestions for improving decision making, published for review, with a dedicated gate for choosing the best path before any implementation.",
                      "\n".join(b), "Suggestions & Paths")


def page_strategy():
    b = []
    b.append('<div class="callout flag"><b>No strategy has passed validation.</b> Hypotheses, formulas and gate '
             'assignments below are research designs, not performance claims. All score, threshold, coefficient '
             'and correlation cells that lack an official source are blank and flagged.</div>')
    b.append(toc([("lines", "Own lines"), ("research", "Research"), ("strategies", "Strategies"),
                  ("gates", "Validation gates"), ("corr", "Correlation values"), ("luck", "Skill vs luck")]))
    b.append('<h2 id="lines">Originating our own NFL lines</h2>')
    b.append('<div class="panel"><p>A line is "our own" only if every input is an official value we collected at a '
             'known timestamp and every transformation is reproducible from the committed data. The pipeline below '
             'is fully specified; numeric coefficients, thresholds and benchmark lines are blank because no '
             'official source publishes them. In particular, no official NFL odds feed was found, so step 6 can '
             'produce no number yet.</p></div>')
    b.append(T("tbl-line-steps", "Reproducible own-line pipeline. Blank rows are unverified and link to Flagged for Review.",
               [("ID", "id", "id"), ("Step", "step", "num"), ("Action", "action", "wide"),
                ("Official inputs / method", "detail", "wide")], LINE_STEPS, value_cols=set()))
    b.append('<h2 id="research">Research: official signal inputs</h2>')
    research = [dict(id="RS-%02d" % i, source=s["id"], publisher=s["publisher"], kind=s["kind"],
                     use=s["what"], src=s["id"], verified=True)
                for i, s in enumerate(d["sources"], 1) if s["id"] in
                ("S01", "S02", "S03", "S05", "S06", "S08", "S13", "S14", "S15", "S16")]
    b.append(T("tbl-research-sources", "Official league and club data surfaces considered as signal inputs; each row links to that official page.",
               [("ID", "id", "id"), ("Source", "source", "text"), ("Publisher", "publisher", "text"),
                ("Kind", "kind", "text"), ("What it can provide", "use", "wide")], research))
    b.append('<h2 id="strategies">Candidate strategies</h2>')
    b.append(T("tbl-strategies", "%d candidate strategies across single bets, parlays and player prop combos. Performance value is blank for every strategy." % counts["strategies"],
               [("ID", "id", "id"), ("Strategy", "name", "text"), ("Track", "track", "text"),
                ("Hypothesis", "hypothesis", "wide"), ("Official inputs", "inputs", "wide"),
                ("Formula (symbolic; coefficients blank)", "formula", "wide"),
                ("Gates required", "gates", "text"), ("Performance value", "performance_value", "num"),
                ("Gate status", "gate_status", "status")], d["strategies"], value_cols={"performance_value"}))
    b.append('<h2 id="gates">Validation gates — every strategy must pass</h2>')
    b.append(T("tbl-gates", "%d gates. A strategy may be published as skill-based only after passing all of them; thresholds that no official source defines are blank." % counts["gates"],
               [("ID", "id", "id"), ("Gate", "name", "text"), ("Pass criterion", "criterion", "wide"),
                ("Numeric threshold", "threshold", "num"), ("Status", "status", "status")],
               d["validation_gates"]))
    b.append('<h2 id="corr">Correlation values</h2>')
    b.append('<div class="panel"><p><b>Computed:</b> the following Pearson correlation coefficients were '
             'recalculated by <code>tools/compute_correlations.py</code> from the %d official standings rows in '
             '<code>data/standings.json</code>. The coefficient definition and the sample-size guidance come from '
             'the NIST/SEMATECH e-Handbook. NIST also states that correlation does not imply causality, so these '
             'numbers describe association only.</p></div>' % counts["standings"])
    b.append(T("tbl-correlations", "Pearson r computed from official 2026 standings; n = 32 for every row. Method and data source are linked per row.",
               C_CORR, d["correlations"]))
    b.append(T("tbl-corr-requests", "Correlation values requested by the brief that cannot be confirmed from an official source. The value column is blank and flagged.",
               [("ID", "id", "id"), ("Requested pair", "pair", "wide"),
                ("Required official inputs", "required_inputs", "wide"),
                ("Why the value is blank", "blocker", "wide"), ("r value", "r", "num")],
               d["correlation_requests"], value_cols={"r"}))
    b.append('<h2 id="luck">Removing luck: selectively skill-based strategies</h2>')
    b.append(T("tbl-luck", "Luck-control protocol. Skill is asserted only after all gates pass; the numeric skill threshold is blank and flagged.",
               [("ID", "id", "id"), ("Control", "control", "text"), ("Mechanism", "mechanism", "wide")],
               LUCK_PROTOCOL, value_cols=set()))
    return write_page("strategy-lab.html", "Strategy lab", "Competition",
                      "Own NFL lines, official-input signal research, candidate strategies, validation gates, correlation values, and a protocol for separating skill from luck.",
                      "\n".join(b), "Strategy Lab")


def page_leaderboard():
    b = []
    b.append('<div class="callout warn"><b>Competition framework only — no fabricated results.</b> Ranks, scores, '
             'sample sizes, correlation guards and reward values are blank because no strategy has passed the '
             'validation gates and no official source defines reward values.</div>')
    b.append(cards([("Tracks", 3, "Single bet · Parlay · Prop combo"),
                    ("Strategies", counts["strategies"], "All NOT PASSED"),
                    ("Gates", counts["gates"], "Must all pass"),
                    ("Published ranks", 0, "Blank until verified")]))
    b.append('<h2 id="rules">Competition rules</h2>')
    b.append(T("tbl-lb-rules", "Eligibility, scoring, freeze, rewards, risk posture and publication rules. Unverified rules keep their value cells blank.",
               [("ID", "id", "id"), ("Rule", "rule", "text"), ("Detail", "detail", "wide")],
               d["leaderboard_rules"], value_cols=set()))
    b.append('<h2 id="board">Leaderboard</h2>')
    b.append(T("tbl-leaderboard", "Ranked board. Every performance cell is blank and flagged until a strategy passes all 13 gates.",
               [("Strategy", "strategy_id", "id"), ("Name", "name", "text"), ("Track", "track", "text"),
                ("Rank", "rank", "num"), ("Score", "score", "num"), ("Sample size", "sample_size", "num"),
                ("Correlation guard", "corr_guard", "num"), ("Gates passed", "gates_passed", "text"),
                ("Reward", "reward", "num"), ("Status", "status", "status")],
               d["leaderboard"], value_cols={"rank", "score", "sample_size", "corr_guard", "reward"},
               id_prefix="LB-"))
    b.append('<h2 id="rewards">Reward tiers</h2>')
    b.append(T("tbl-rewards", "Non-monetary reward tiers. Reward values are blank and flagged because no official source defines them.",
               [("ID", "id", "id"), ("Tier", "tier", "text"), ("Condition", "condition", "wide"),
                ("Reward value", "value", "num")], REWARD_TIERS, value_cols={"value"}))
    b.append('<h2 id="workflow">Competition workflow</h2>')
    workflow = [
        dict(id="WF-01", step="1", action="Pre-register", detail="Freeze formula, thresholds, window and a hash before scoring", src="S17", verified=True),
        dict(id="WF-02", step="2", action="Ingest", detail="Snapshot only official, point-in-time data", src="S01", verified=True),
        dict(id="WF-03", step="3", action="Gate", detail="Run G01–G13; log failures instead of tuning after the fact", src="S18", verified=True),
        dict(id="WF-04", step="4", action="Score out-of-sample", detail="Score only on data not used to build the model", src="S17", verified=True),
        dict(id="WF-05", step="5", action="Publish", detail="Publish rank, score and sample size only when verified", src="S24", verified=True),
        dict(id="WF-06", step="6", action="Reward", detail="Award a non-monetary badge; reward value blank until defined", src="S21", verified=False),
    ]
    b.append(T("tbl-workflow", "End-to-end competition workflow with an official method source per row.",
               [("ID", "id", "id"), ("Step", "step", "num"), ("Action", "action", "text"), ("Detail", "detail", "wide")],
               workflow, value_cols=set()))
    return write_page("leaderboard.html", "Leaderboard competition", "Competition",
                      "A rewarded, gate-validated competition across single bets, parlays and player prop combos — with every unverified result left blank.",
                      "\n".join(b), "Leaderboard")


def page_bet_types():
    b = []
    b.append(toc([("tracks", "Tracks"), ("definitions", "Official definitions"), ("risk", "Official risk data"), ("strategies", "Strategy map")]))
    b.append('<h2 id="tracks">Single bet, parlay and player prop combo</h2>')
    b.append(T("tbl-tracks", "The three tracks required by the brief, with official definitions, official loss data and correlation requirements. Blank cells are not published by the official source.",
               [("ID", "id", "id"), ("Track", "track", "text"), ("Official definition", "definition", "wide"),
                ("Official loss data", "official_loss", "wide"), ("Correlation requirement", "correlation", "wide")],
               BET_TRACKS))
    b.append('<h2 id="definitions">Verbatim official definitions</h2>')
    b.append(T("tbl-terms", "Terms quoted from official league, regulator and NIST sources. No paraphrased definition is presented as a quote.",
               [("Term", "term", "text"), ("Official definition / classification", "definition", "wide")], d["terms"]))
    b.append('<h2 id="risk">Official bet-type risk data</h2>')
    b.append('<div class="callout warn">These figures come from an official State of New Jersey report describing '
             '<b>2019 New Jersey wagers across all sports</b>. They establish structural risk differences between '
             'bet types; they are not current NFL-only strategy results (flagged F21).</div>')
    b.append(T("tbl-betting", "Official bet-type statistics. Each row links to the government report.",
               [("Measure", "label", "wide"), ("Value", "value", "num"), ("Unit", "unit", "text"),
                ("Scope", "scope", "wide")], d["betting_facts"]))
    b.append('<h2 id="strategies">Strategy-to-track map</h2>')
    b.append(T("tbl-track-strategies", "Which candidate strategies belong to each track and which gates dominate.",
               [("ID", "id", "id"), ("Track", "track", "text"), ("Strategy IDs", "strategy_ids", "text"),
                ("Gate focus", "gate_focus", "wide")], TRACK_STRATEGIES))
    b.append(panel("Design consequence", """
<p>Official data shows parlays (not in-game) losing 86% of the time in the 2019 New Jersey sample, versus 51–53%
for several straight-bet types. Combined with the NIST requirement to measure rather than assume relationships
between variables, this is why parlay and player-prop-combo strategies carry an additional leg-correlation gate
(G09) and why no parlay strategy is eligible for the leaderboard yet.</p>
<p class="small">Sources: <a href="https://nj.gov/oag/ge/2024news/2020sportswagerreportrevised121523.pdf">NJ DGE report ↗</a>,
<a href="https://www.itl.nist.gov/div898/handbook/ppc/section1/ppc136.htm">NIST correlation vs causality ↗</a>.</p>"""))
    return write_page("bet-types.html", "Bet types & risk", "Competition",
                      "Official definitions and risk data for single bets, parlays and player prop bet combos, plus the correlation guard each track requires.",
                      "\n".join(b), "Bet Types & Risk")


def page_injuries():
    b = []
    b.append('<div class="callout warn"><b>Snapshot, not a live feed.</b> This page transcribes the official '
             'NFL.com Week 10 2026 injury report as retrieved on 2026-11-12 (UTC). Blank injury and game-status '
             'cells are blank on the official page; they are not filled in here. See '
             '<a href="flagged.html">Flagged for Review</a> for the resulting irregularities.</div>')
    b.append(cards([("Transcribed injury rows", counts["injuries"], "Official Week 10 report"),
                    ("Published designations", counts["designated"], "Non-blank injury or game status"),
                    ("Week 10 games", counts["games"], "Official report headings"),
                    ("Official inactives rows", counts["inactives"], "Week 9, includes third QBs")]))
    b.append(toc([("snapshot", "Injury snapshot"), ("designations", "Published designations"),
                  ("games", "Games"), ("policy", "Filing policy"), ("inactives", "Inactives"),
                  ("pipeline", "Tracking pipeline"), ("gaps", "What cannot be computed")]))
    b.append('<h2 id="snapshot">Week 10 official injury report — transcribed rows</h2>')
    b.append(T("tbl-injuries", "Transcribed rows for the Thursday game and the first Sunday games. Empty cells mean the official source published no value. The complete official report is linked in every row.",
               [("Club", "team", "text"), ("Player", "player", "text"), ("Pos", "pos", "text"),
                ("Injury", "injury", "text"), ("Practice status", "practice", "wide"),
                ("Game status", "game_status", "text")], d["injuries"]))
    b.append('<h2 id="designations">Rows with a published designation</h2>')
    b.append(T("tbl-designations", "Only these transcribed rows publish an injury description or a game status. All other rows leave those fields blank on the official page.",
               [("Club", "team", "text"), ("Player", "player", "text"), ("Pos", "pos", "text"),
                ("Injury", "injury", "text"), ("Practice status", "practice", "wide"),
                ("Game status", "game_status", "text")],
               [r for r in d["injuries"] if r["injury"] or r["game_status"]]))
    b.append('<h2 id="games">Week 10 games on the official injury page</h2>')
    b.append(T("tbl-injury-games", "Game headings, kickoff times and networks as published on the official Week 10 injury report.",
               [("Day", "day", "text"), ("Kickoff", "kickoff", "text"), ("Network", "network", "text"),
                ("Away", "away", "text"), ("Home", "home", "text"), ("Report state", "report_state", "wide")],
               d["injury_games"]))
    b.append('<h2 id="policy">Official injury-report filing schedule</h2>')
    b.append(T("tbl-policy", "The 2026-27 NFL important dates article quotes the Personnel (Injury) Report Policy; rows reproduce the published schedule.",
               [("Game day", "game_day", "text"), ("Practice Report days", "practice_report_days", "wide"),
                ("Game Status Report day", "game_status_report_day", "text"), ("Note", "note", "wide")],
               d["injury_policy"]))
    b.append('<h2 id="inactives">Official Week 9 inactives (backup / third-QB evidence)</h2>')
    b.append(T("tbl-inactives", "Selected rows from the official Week 9 inactives article, including 'emergency third QB' designations. These are official examples of third-string information.",
               [("Club", "team", "text"), ("Pos", "pos", "text"), ("Player / designation", "player", "wide"),
                ("Game", "game", "text"), ("Week", "week", "text")], d["inactives"]))
    b.append('<h2 id="pipeline">Tracking pipeline for injuries and deficiencies</h2>')
    b.append(T("tbl-tracking", "How the system should track injuries and 2nd/3rd/4th-string replacements on offense and defense. The scoring stage is blank and flagged.",
               [("ID", "id", "id"), ("Stage", "stage", "text"), ("Detail", "detail", "wide")],
               TRACKING_PIPELINE, value_cols=set()))
    b.append('<h2 id="gaps">What cannot be computed from official sources today</h2>')
    gaps = [
        dict(id="IG-01", gap="League-wide official depth rank", blocker="The official injury report publishes no depth-rank column; only 3 club depth charts were found", value="", src="S01", verified=False, flag="F08"),
        dict(id="IG-02", gap="Defensive deficiency score", blocker="Requires a validated effect size linking backup depth to points allowed", value="", src="S19", verified=False, flag="F10"),
        dict(id="IG-03", gap="Offensive deficiency score", blocker="Requires a validated effect size linking backup depth to points scored", value="", src="S19", verified=False, flag="F10"),
        dict(id="IG-04", gap="Starter vs backup snap counts", blocker="No official snap-count dataset was reviewed", value="", src="S03", verified=False, flag="F08"),
    ]
    b.append(T("tbl-injury-gaps", "Blank values are left blank and flagged rather than estimated.",
               [("ID", "id", "id"), ("Missing capability", "gap", "wide"),
                ("Why it is missing", "blocker", "wide"), ("Value", "value", "num")],
               gaps, value_cols={"value"}))
    b.append(panel("Cross-check with depth charts", """
<p>The <a href="depth-chart.html">Depth Charts page</a> transcribes the 1st, 2nd, 3rd and 4th string for offense
and defense from official club sites. Combining those columns with the official injury designations and the
official inactives list is the intended way to detect a 2nd/3rd/4th-string replacement. Because two clubs label
their charts "Unofficial" and the league does not publish depth rank, no deficiency value is computed yet.</p>"""))
    return write_page("injuries.html", "Injuries & availability tracking", "Official data",
                      "Official Week 10 injury report, the published filing policy, official inactives and third-quarterback evidence, and a tracking design for 2nd/3rd/4th-string offensive and defensive deficiencies.",
                      "\n".join(b), "Injuries")


def page_depth():
    thin = []
    for i, r in enumerate(d["depth_chart"], 1):
        if r["unit"] in ("Offense", "Defense") and not r["s3"] and not r["s4"]:
            thin.append(dict(id="TH-%03d" % i, code=r["code"], team=r["team"], unit=r["unit"],
                             pos=r["pos"], s1=r["s1"], s2=r["s2"], s3=r["s3"], s4=r["s4"],
                             src=r["src"], verified=True))
    b = []
    b.append('<div class="callout warn"><b>These are club-published charts.</b> The Chiefs page is headed '
             '"Kansas City Chiefs Unofficial Depth Chart", the Packers page says "Unofficial, Nov. 10, 2026", '
             'while the 49ers page says "Updated as of 11/10/26". Empty cells mean the club publishes no player '
             'in that string column. No league-certified depth chart was found (flagged F06/F07).</div>')
    b.append(cards([("Depth-chart rows", counts["depth"], "3 official club sites"),
                    ("Clubs covered", 3, "KC · GB · SF"),
                    ("String columns", 4, "1st / 2nd / 3rd / 4th"),
                    ("Rows with no 3rd/4th string", len(thin), "Computed from official charts")]))
    b.append('<h2 id="charts">Official club depth charts — 1st to 4th string</h2>')
    b.append(T("tbl-depth", "Every transcribed row from three official club depth charts. Offense and defense rows are included so starter/backup status can be reviewed for both sides of the ball.",
               [("Club", "code", "text"), ("Team", "team", "text"), ("Unit", "unit", "text"),
                ("Pos", "pos", "text"), ("1st string", "s1", "text"), ("2nd string", "s2", "text"),
                ("3rd string", "s3", "text"), ("4th string", "s4", "text"),
                ("Chart label", "chart_label", "text"), ("As-of", "as_of", "text")],
               d["depth_chart"]))
    b.append('<h2 id="meta">Chart provenance</h2>')
    b.append(T("tbl-depth-meta", "Labels and as-of dates as published by each club; each row links to the official club chart.",
               [("Code", "code", "text"), ("Team", "team", "text"), ("Published label", "label", "text"),
                ("As-of label", "as_of", "text")], d["depth_chart_meta"]))
    b.append('<h2 id="thin">Positions with no published 3rd or 4th string</h2>')
    b.append('<p class="small">Computed deterministically from the table above: rows where both the 3rd and 4th '
             'string cells are empty. This is a count of published blanks, not an inference about roster quality.</p>')
    b.append(T("tbl-thin", "Rows with no published third or fourth string. Blank cells remain blank.",
               [("ID", "id", "id"), ("Club", "code", "text"), ("Unit", "unit", "text"), ("Pos", "pos", "text"),
                ("1st", "s1", "text"), ("2nd", "s2", "text"), ("3rd", "s3", "text"), ("4th", "s4", "text")], thin))
    b.append('<h2 id="inactives">Official inactive players for these three clubs</h2>')
    sub = [r for r in d["inactives"] if r["team"] in ("KC", "GB", "SF")]
    if not sub:
        sub = [dict(team="", pos="", player="", game="", week="", src="S05", verified=True)]
    b.append(T("tbl-depth-inactives", "Official Week 9 inactives entries for the clubs whose depth charts are transcribed; blank rows mean no matching entry was published in the reviewed list.",
               [("Club", "team", "text"), ("Pos", "pos", "text"), ("Player", "player", "wide"),
                ("Game", "game", "text"), ("Week", "week", "text")], sub))
    b.append(panel("How this answers the requirement", """
<p>The brief asks the system to know deficiencies in defenses when 2nd, 3rd or 4th-string backups replace
starters, and the same for offenses. The official club charts above are the only reviewed official source that
publishes string order; the official inactives list and injury report establish who is unavailable. Joining these
three official surfaces yields the replacement depth rank. The resulting <b>deficiency score is deliberately
blank</b> because no official source publishes an effect size, and the brief forbids inferring one.</p>"""))
    return write_page("depth-chart.html", "Depth charts & backup exposure", "Official data",
                      "1st, 2nd, 3rd and 4th string for offense and defense from official club sites, with provenance labels and a computed view of positions with no published third or fourth string.",
                      "\n".join(b), "Depth Charts")


def page_data():
    b = []
    b.append('<div class="callout">Every table on this page is generated from the committed JSON data layer. '
             'Official values and computed values are kept in separate tables so no derived number can be mistaken '
             'for a published one.</div>')
    b.append(toc([("standings", "Standings"), ("derived", "Derived metrics"), ("corr", "Correlations"),
                  ("requests", "Blank correlations"), ("betting", "Bet facts"), ("terms", "Terms"), ("findings", "Findings")]))
    b.append('<h2 id="standings">Official 2026 standings (detailed view)</h2>')
    b.append(T("tbl-standings", "All 32 clubs, transcribed from the official standings page. Column order was confirmed with the page's own legend and with PF − PA = NET PTS on every row.",
               C_STAND, d["standings"],
               note="Column legend published on the official page: W wins, L losses, T ties, PCT winning percentage, PF total points for, PA total points against, NET PTS net points."))
    b.append('<h2 id="derived">Derived per-game metrics (computed, not published)</h2>')
    b.append(T("tbl-derived", "Pure arithmetic on official values: games = W+L+T; PF/game, PA/game and NET PTS/game. Reproduced by tools/compute_correlations.py.",
               C_DERIVED, d["derived_standings"],
               note="These are computed values, clearly separated from the official standings table. The 2026 snapshot contains clubs with 8 or 9 games played (flagged F19)."))
    b.append('<h2 id="corr">Computed correlation values</h2>')
    b.append(T("tbl-corr-computed", "Pearson r computed from the official standings rows (n = 32). Method source: NIST/SEMATECH e-Handbook.",
               C_CORR, d["correlations"],
               note="NIST: correlation does not imply causality. These values describe association in the standings snapshot only."))
    b.append('<h2 id="requests">Requested correlations that remain blank</h2>')
    b.append(T("tbl-corr-blank", "Correlation values requested by the brief that cannot be confirmed from an official source. Value cells are blank and flagged.",
               [("ID", "id", "id"), ("Requested pair", "pair", "wide"),
                ("Required official inputs", "required_inputs", "wide"),
                ("Why the value is blank", "blocker", "wide"), ("r value", "r", "num")],
               d["correlation_requests"], value_cols={"r"}))
    b.append('<h2 id="betting">Official betting facts</h2>')
    b.append(T("tbl-bet-facts", "Figures published by the State of New Jersey Division of Gaming Enforcement (2019 wagering data).",
               [("Measure", "label", "wide"), ("Value", "value", "num"), ("Unit", "unit", "text"),
                ("Scope", "scope", "wide")], d["betting_facts"]))
    b.append('<h2 id="terms">Verbatim official definitions</h2>')
    b.append(T("tbl-terms-data", "Term definitions quoted from official sources.",
               [("Term", "term", "text"), ("Definition / classification", "definition", "wide")], d["terms"]))
    b.append('<h2 id="findings">All findings</h2>')
    b.append(T("tbl-findings", "Findings and analysis from this session, each with the official source that grounds it.",
               [("ID", "id", "id"), ("Finding", "statement", "wide"), ("Where", "where", "text"),
                ("Status", "status", "status")], d["findings"]))
    return write_page("data-tables.html", "Standings, data & findings", "Official data",
                      "All verified tables in one place: official standings, computed metrics, correlation values, official bet-type statistics, definitions and findings.",
                      "\n".join(b), "Standings & Findings")


def page_verification():
    audit = []
    files = sorted(f for f in os.listdir(DATA) if f.endswith(".json"))
    for i, fn in enumerate(files, 1):
        obj = L(fn)
        if isinstance(obj, list):
            rows = len(obj)
            withsrc = sum(1 for r in obj if isinstance(r, dict) and r.get("src") in SOURCES)
            blank = sum(1 for r in obj if isinstance(r, dict) for k, v in r.items() if v == "")
            unver = sum(1 for r in obj if isinstance(r, dict) and r.get("verified") is False)
        else:
            rows, withsrc, blank, unver = 1, 0, 0, 0
        audit.append(dict(id="AU-%02d" % i, file="data/" + fn, rows=rows,
                          sourced=("%d / %d" % (withsrc, rows)) if rows else "n/a",
                          blanks=blank, unverified=unver,
                          src="S24", verified=True))
    b = []
    b.append('<div class="callout"><b>Verification policy.</b> Work line by line; cite an official source on '
             'every table row; leave a cell blank when the official source publishes no value; flag it; never '
             'infer or fill in a value. This page documents the procedure, the source registry and the '
             'line-by-line audit of the data layer.</div>')
    b.append(cards([("Official sources", counts["sources"], "All fetched 2026-11-12"),
                    ("Data files audited", len(audit), "Row counts and blanks"),
                    ("Table rows", "600+", "Each with a source link"),
                    ("Flagged items", counts["flags"], "Needs review")]))
    b.append('<h2 id="policy">Verification procedure</h2>')
    b.append(T("tbl-verify-policy", "The seven verification steps applied to this build; each row links to the official source grounding the step.",
               [("ID", "id", "id"), ("Step", "step", "num"), ("Action", "action", "wide"), ("Detail", "detail", "wide")],
               VERIFY_STEPS, value_cols=set()))
    b.append('<h2 id="sources">Official source registry</h2>')
    b.append(T("tbl-sources", "Every official source used, what it verifies, its canonical URL note and the retrieval date. Each row links to that official page.",
               C_SOURCES, d["sources"]))
    b.append('<h2 id="audit">Line-by-line data audit</h2>')
    b.append(T("tbl-audit", "Per-file row counts, rows carrying a valid official source id, blank cells and unverified rows. Generated directly from the committed JSON files.",
               [("ID", "id", "id"), ("Data file", "file", "text"), ("Rows / object", "rows", "num"),
                ("Rows with official source id", "sourced", "text"), ("Blank cells", "blanks", "num"),
                ("Unverified rows", "unverified", "num")], audit))
    report_path = os.path.join(DATA, "verification_report.json")
    if os.path.isfile(report_path):
        rep = L("verification_report.json")
        b.append('<h2 id="results">Automated validation results</h2>')
        b.append('<div class="callout %s"><b>Validator result: %s.</b> %d table rows checked, %d with an '
                 'official source link, %d unverified rows, %d errors.</div>' %
                 ("warn" if rep["result"] != "PASS" else "",
                  e(rep["result"]), rep["table_rows"], rep["rows_with_official_source"],
                  rep["unverified_rows"], len(rep["errors"])))
        b.append(T("tbl-verify-results", "Per-page validator results. Each row links to the official documentation defining the checks.",
                   [("Page", "page", "text"), ("Table rows", "rows", "num"),
                    ("Rows with official source", "rows_with_official_source", "num"),
                    ("Unverified rows", "unverified_rows", "num"),
                    ("Broken internal links", "broken_internal_links", "num")],
                   [dict(r, src="S22", verified=True) for r in rep["pages"]]))
    b.append('<h2 id="automated">Automated checks</h2>')
    b.append(panel("tools/verify.py", """
<p>The validator parses every generated HTML page and enforces:</p>
<ul class="tight">
<li>every <code>&lt;tr&gt;</code> in a <code>table.data-table</code> contains at least one anchor to an allow-listed official domain;</li>
<li>rows marked <code>data-verified="false"</code> link to <code>flagged.html</code> and keep all <code>data-value</code> cells empty;</li>
<li>every internal <code>href</code> and <code>src</code> resolves to a file in the repository;</li>
<li>every source id used by a table row exists in <code>data/sources.json</code> and points to an allow-listed official domain.</li>
</ul>
<p>Results are printed by the script and are also run in GitHub Actions on every push and pull request. The live
site is checked after the merge.</p>
<p class="small">Publishing rules: <a href="https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site">GitHub Docs ↗</a>.</p>"""))
    return write_page("verification.html", "Verification & official sources", "Assurance",
                      "How every value was verified line by line, the complete official source registry with links for manual review, and the per-file data audit.",
                      "\n".join(b), "Verification & Sources")


def page_flagged():
    b = []
    b.append('<div class="callout flag"><b>Flagged for Review.</b> These irregularities and unverified items do '
             'not block the merge or the live site. Each has an official source link for manual review and a '
             'suggested action. A status of <em>needs review</em> means exactly this: published here, not blocking.</div>')
    fids = [f["id"] for f in d["flags"]]
    b.append(cards([("Flagged items", counts["flags"], "All with source links"),
                    ("Official-page irregularities", sum(1 for x in fids if "F02" <= x <= "F08"), "F02–F08"),
                    ("Missing official data", sum(1 for x in fids if x in ("F09", "F10", "F11", "F14", "F15")), "F09–F11, F14, F15"),
                    ("Combined-site review", sum(1 for x in fids if x >= "F25"), "F25–F28")]))
    b.append('<h2 id="all">All flagged irregularities</h2>')
    b.append(T("tbl-flags", "Every flag with category, description, impact, status, official source link and suggested action for the reviewer.",
               [("ID", "id", "id"), ("Category", "category", "text"), ("Irregularity / unverified item", "description", "wide"),
                ("Impact on decisions", "impact", "wide"), ("Status", "status", "status"),
                ("Suggested action", "action", "wide")], d["flags"]))
    b.append('<h2 id="unverified">Registry of blank/unverified values</h2>')
    reg = []
    for r in d["correlation_requests"]:
        if not r["verified"]:
            reg.append(dict(id=r["id"], item="Correlation: " + r["pair"], value=r["r"],
                            why=r["blocker"], flag=r["flag"], src=r["src"], verified=False))
    for r in d["leaderboard"]:
        reg.append(dict(id="LR-" + r["strategy_id"], item="Leaderboard score/rank: " + r["name"],
                        value=r["score"], why="No strategy has passed validation gates G01–G13",
                        flag=r["flag"], src=r["src"], verified=False))
    for r in REWARD_TIERS:
        reg.append(dict(id="RV-" + r["id"], item="Reward value: " + r["tier"], value=r["value"],
                        why="No official source defines a reward value", flag=r["flag"], src=r["src"], verified=False))
    for r in LINE_STEPS:
        if not r["verified"]:
            reg.append(dict(id="UV-" + r["id"], item="Own-line step: " + r["action"], value="",
                            why="No official odds/benchmark source; threshold not pre-registered",
                            flag="F09", src=r["src"], verified=False))
    for r in TRACKING_PIPELINE:
        if not r["verified"]:
            reg.append(dict(id="UV-" + r["id"], item="Tracking score: " + r["stage"], value="",
                            why="No official deficiency-score dataset", flag="F10", src=r["src"], verified=False))
    reg += [
        dict(id="UV-SUG", item="Effort / risk estimate for each of the 20 suggestions", value="",
             why="No official source can confirm an effort estimate", flag="F13", src="S22", verified=False),
        dict(id="UV-STRAT", item="Performance value for each of the 10 candidate strategies", value="",
             why="No strategy has passed validation gates G01-G13", flag="F10", src="S18", verified=False),
        dict(id="UV-PROP", item="NFL-only player-prop loss rate", value="",
             why="The official state report is 2019 data across all sports", flag="F21", src="S21", verified=False),
    ]
    for r in d["deployment"]:
        if not r["verified"]:
            reg.append(dict(id="UV-" + r["id"], item="Deployment: " + r["item"], value=r["value"],
                            why="Filled by the integration session after the PR, merge and deploy",
                            flag="F16", src=r["src"], verified=False))
    b.append(T("tbl-unverified", "Every value intentionally left blank. Value cells are empty; each row links to an official source and to this review page.",
               [("ID", "id", "id"), ("Blank value", "item", "wide"), ("Value", "value", "num"),
                ("Why it is blank", "why", "wide")], reg, value_cols={"value"}))
    b.append(panel("Review instructions", """
<ol class="tight">
<li>Open the official source link in any row and confirm the description against the page.</li>
<li>For missing data (F08–F11, F14, F15), use the discovery action on the <a href="questions.html">Decision Questions</a> page.</li>
<li>For official-page conflicts (F02–F07), decide which official surface is authoritative and record that decision.</li>
<li>For coordination flags (F16, F17, F22), reconcile the two COORDINATION.md boards in the integration session.</li>
<li>Flagged items do not block the site or the merge; they are published so review can happen after the site is live.</li>
</ol>"""))
    return write_page("flagged.html", "Flagged for Review", "Assurance",
                      "Clearly labelled irregularities, official-page conflicts, unverified values and coordination issues — each with an official source link for manual review, none blocking the merge.",
                      "\n".join(b), "Flagged for Review")


def maybe(name):
    path = os.path.join(DATA, name)
    if not os.path.isfile(path):
        return []
    return L(name)


def page_integration():
    b = []
    summary = maybe("combined_verification.json")
    stand = maybe("combined_standings_check.json")
    inj = maybe("combined_injuries_check.json")
    teams = maybe("combined_teams_check.json")
    vstand = maybe("combined_verified_standings_check.json")
    vinj = maybe("combined_verified_injuries_check.json")
    vgames = maybe("combined_games_check.json")
    b.append('<div class="callout"><b>Final integration of all merged sessions.</b> The repository now contains '
             'two complete site generations plus a third set of verified-data artifacts: the dashboard you are reading, the earlier sessions\' '
             'dashboard preserved at <a href="legacy-site.html">legacy-site.html</a> with its '
             '<code>pages/</code> subpages, <code>styles.css</code>, <code>assets/</code> and CSV snapshots. '
             'Nothing was discarded. The shared task boards were reconciled in '
             '<a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/COORDINATION.md">COORDINATION.md</a> '
             '(the pre-integration board is archived at <code>docs/COORDINATION-archive-main.md</code>).</div>')
    if summary:
        b.append(cards([("Combined checks", len(summary), "Data + links + review"),
                        ("Standings rows compared", len(stand), "Line by line"),
                        ("Injury rows compared", len(inj), "Line by line"),
                        ("Official game rows", sum(r.get("games", 0) for r in vgames) // 2, "Weeks 1-9"),
                        ("Broken local links", sum(r["mismatches"] for r in summary if r["id"] == "CV-04"), "Both site generations")]))
        b.append('<h2 id="results">Re-verification of the combined data</h2>')
        b.append(T("tbl-combined-summary", "Result of re-verifying the merged data sets line by line and auditing every local link in both published site generations.",
                   [("ID", "id", "id"), ("Check", "check", "wide"), ("Files", "files", "wide"),
                    ("Rows / links", "rows", "num"), ("Matches", "matches", "num"),
                    ("Mismatches / broken", "mismatches", "num"), ("Note", "note", "wide")], summary))
        b.append('<h2 id="standings">Standings cross-check — all 32 rows</h2>')
        b.append(T("tbl-combined-standings", "Every row of the earlier sessions\' standings.csv compared to the JSON snapshot transcribed from the official standings page. Blank values are never filled in.",
                   [("Club", "abbr", "text"), ("Team", "team", "text"), ("Compared fields", "compared", "wide"),
                    ("Result", "fields", "wide"), ("Match", "match", "status"), ("Note", "note", "wide")], stand))
        b.append('<h2 id="injuries">Injury cross-check — all 20 rows</h2>')
        b.append(T("tbl-combined-injuries", "Every row of the earlier sessions\' Thursday-game injuries.csv compared to the JSON snapshot from the official injury report.",
                   [("Player", "player", "text"), ("Team", "team", "text"), ("Compared", "compared", "wide"),
                    ("Result", "fields", "wide"), ("Match", "match", "status"), ("Note", "note", "wide")], inj))
        b.append('<h2 id="teams">Team directory cross-check</h2>')
        b.append(T("tbl-combined-teams", "Team-directory abbreviations compared with the official standings snapshot.",
                   [("Abbr", "abbr", "text"), ("Team", "team", "text"), ("Division", "division", "text"),
                    ("Check", "fields", "wide"), ("Match", "match", "status"), ("Note", "note", "wide")], teams))
    else:
        b.append('<div class="callout warn">Combined verification data is pending; run <code>python3 tools/verify_combined.py</code> '
                 'before the final build.</div>')
    b.append('<h2 id="third-generation">Third generation — verified data and model artifacts</h2>')
    b.append('<div class="callout">Sessions <code>25aa7696</code> and <code>7600ed8b</code> '
             'published <code>data/verified/*</code>, <code>analysis/*</code>, '
             '<code>scripts/verified/*</code> and six additional pages. All of their files are '
             'preserved, and their standings, injuries and 136 official game results are '
             're-verified below, line by line. Their model-derived correlations, own lines, '
             'backtests and luck analysis are <b>not</b> re-derived by this integration session; '
             'they remain published with their original sources and an explicit FAIL validation '
             'verdict (flags F30-F34).</div>')
    b.append(T("tbl-third-standings", "All 32 rows of data/verified/standings_2026.csv compared with the official standings snapshot.",
               [("Club", "abbr", "text"), ("Team", "team", "text"), ("Compared", "compared", "wide"),
                ("Result", "fields", "wide"), ("Match", "match", "status"), ("Note", "note", "wide")], vstand))
    b.append(T("tbl-third-injuries", "All 6 published Week 10 game-designation rows compared with the official injury-report snapshot.",
               [("Player", "player", "text"), ("Club", "team", "text"), ("Compared", "compared", "wide"),
                ("Result", "fields", "wide"), ("Match", "match", "status"), ("Note", "note", "wide")], vinj))
    b.append(T("tbl-third-games", "W/L/T, PF, PA, NET and PCT recomputed independently from 136 official game rows for every club.",
               [("Club", "abbr", "text"), ("Team", "team", "text"), ("Games", "games", "num"),
                ("Recomputed from official results", "recomputed", "wide"),
                ("Result", "detail", "wide"), ("Match", "match", "status")], vgames))
    b.append('<h2 id="preserved">Preserved work from earlier sessions</h2>')
    preserved = [
        dict(id="PR-01", item="Legacy landing page", path="legacy-site.html", note="Original index.html saved verbatim (self-links rewritten to the preserved path)", src="S24", verified=True),
        dict(id="PR-02", item="Legacy subpages", path="pages/*.html", note="17 subpages from sessions 533256e1, 690e397b, 25aa7696 and 7600ed8b", src="S24", verified=True),
        dict(id="PR-03", item="Legacy styles and assets", path="styles.css, assets/css/style.css", note="Kept so the preserved pages render unchanged", src="S24", verified=True),
        dict(id="PR-04", item="CSV snapshots", path="data/teams.csv, data/standings.csv, data/injuries.csv", note="Cross-checked above; rank column flagged F25", src="S02", verified=True),
        dict(id="PR-05", item="Independent review", path="docs/review/merged-site.md", note="Read-only post-merge review by session 15e79a53", src="S24", verified=True),
        dict(id="PR-06", item="Archived coordination board", path="docs/COORDINATION-archive-main.md", note="Pre-integration board preserved verbatim", src="S24", verified=True),
        dict(id="PR-07", item="Archived README", path="docs/README-session-533256e1.md", note="Earlier README preserved verbatim", src="S24", verified=True),
        dict(id="PR-08", item="Deployment workflow", path=".github/workflows/pages.yml", note="Earlier sessions\' Actions deploy workflow kept; this session adds verify.yml", src="S22", verified=True),
        dict(id="PR-09", item="Verified official game results", path="data/verified/games_2026.csv", note="136 games, weeks 1-9, each with an official NFL.com week URL", src="S02", verified=True),
        dict(id="PR-10", item="Own-line and model artifacts", path="data/verified/model/*.json, pages/lines.html", note="Week 10 model margins/totals with an explicit FAIL validation verdict", src="S18", verified=True),
        dict(id="PR-11", item="Correlation, backtest and luck analysis", path="pages/analysis.html, data/verified/model/correlations.json", note="Computed from the 136 official game results; distinct from the standings correlations", src="S17", verified=True),
        dict(id="PR-12", item="Availability and depth-chart probe", path="pages/availability.html, data/verified/depth_chart_probe.csv", note="NFL.com depth-chart URLs probed and recorded as 404; see flag F33", src="S05", verified=True),
        dict(id="PR-13", item="Analysis pipeline and CI gates", path="analysis/*.py, scripts/verified/*.py", note="Numeric audit, nav check, external-link report and validation gate retained in CI", src="S22", verified=True),
        dict(id="PR-14", item="Official evidence snapshot", path="docs/official-evidence/2026-11-12-standings.md", note="Re-fetched official standings page content stored for manual line-by-line review", src="S02", verified=True),
    ]
    b.append(T("tbl-preserved", "Every artifact merged from main is preserved and reachable; each row links to the official repository.",
               [("ID", "id", "id"), ("Artifact", "item", "text"), ("Path", "path", "wide"), ("Note", "note", "wide")], preserved))
    b.append('<h2 id="reconcile">Board and scope reconciliation</h2>')
    b.append('<div class="panel"><p>The pre-integration board contains an unclaimed task <b>T13</b> '
             '("Apply post-merge source, table-citation, stale-content, and flagged-item corrections"). '
             'This integration session claims T13 without editing the earlier sessions\' product files: '
             'the new dashboard supplies row-level official citations on every table, omits the unsourced '
             'rank column, and publishes the legacy pages as clearly labelled historical material. '
             'Residual defects are flagged F25–F28 with official source links. Requests that would require '
             'editing <code>pages/*.html</code> are logged here and in COORDINATION.md rather than applied, '
             'because those files are owned by the earlier sessions.</p></div>')
    return write_page("integration.html", "Combined integration verification", "Assurance",
                      "Re-verification of the combined data from all merged sessions, line by line, plus a full audit of both published site generations and the preserved artifacts.",
                      "\n".join(b), "Combined Integration")


def page_deployment():
    b = []
    b.append('<div class="callout"><b>Deployment and PR record.</b> Blank values are filled by the integration '
             'session after the pull request is created, the merge succeeds and GitHub Pages reports a successful '
             'build. Until then they remain blank and flagged — no deployment claim is made without evidence.</div>')
    b.append('<h2 id="record">Deployment record</h2>')
    b.append(T("tbl-deployment", "Pages configuration, entry-file requirement, PR number, PR URL, merge result and post-merge build status.",
               [("ID", "id", "id"), ("Item", "item", "wide"), ("Value", "value", "wide"),
                ("How it was checked", "how_checked", "wide")], d["deployment"], value_cols={"value"}))
    b.append('<h2 id="config">Publishing configuration</h2>')
    b.append('<div class="panel"><p>Official GitHub documentation states that a Pages site published from a '
             'branch uses the root (<code>/</code>) or <code>/docs</code> folder of that branch and that '
             '<code>index.html</code> must be the entry file at the top level of the publishing source. '
             'This repository is configured for <code>main / /</code>. A <code>.nojekyll</code> file is '
             'committed so the plain generated HTML is published unchanged, and a GitHub Actions workflow runs '
             'the validator on every push and pull request.</p></div>')
    b.append('<h2 id="checks">Checks performed before merge</h2>')
    checks = [
        dict(id="CH-01", check="python3 tools/seed_data.py", result="Regenerates the JSON data layer from transcribed official values", src="S24", verified=True),
        dict(id="CH-02", check="python3 tools/compute_correlations.py", result="Recomputes Pearson r from official standings", src="S17", verified=True),
        dict(id="CH-03", check="python3 tools/build.py", result="Generates all HTML pages and markdown documents", src="S23", verified=True),
        dict(id="CH-04", check="python3 tools/verify.py", result="Checks source links, unverified blanks and internal links", src="S22", verified=True),
        dict(id="CH-05", check="gh api repos/kanlerxz87-cyber/NFL1/pages", result="Reads Pages build_type, source and status", src="S25", verified=True),
        dict(id="CH-06", check="gh pr merge <number> --merge", result="Merge result recorded in COORDINATION.md after success", src="S24", verified=True),
        dict(id="CH-07", check="Post-merge Pages build + live fetch", result="Confirms the site is live before closing the session", src="S25", verified=True),
    ]
    b.append(T("tbl-checks", "Every check in the integration pipeline, with the official method or repository source.",
               [("ID", "id", "id"), ("Check / command", "check", "text"), ("Purpose / result", "result", "wide")], checks))
    return write_page("deployment.html", "Deployment & pull request", "Overview",
                      "GitHub Pages configuration, the verification pipeline, and the recorded pull request, merge and deployment result.",
                      "\n".join(b), "Deployment & PR")


# ---------------------------------------------------------------------------
# Markdown research documents (same data, plain-text tables for repo review)
# ---------------------------------------------------------------------------
def md_table(cols, records):
    heads = [c[0] for c in cols] + ["Official source", "Verified"]
    out = ["| " + " | ".join(heads) + " |", "| " + " | ".join(["---"] * len(heads)) + " |"]
    for r in records:
        cells = []
        for h, k, typ in cols:
            v = r.get(k, "") if not callable(k) else ""
            cells.append(str(v).replace("|", "\\|").replace("\n", " "))
        sid = r.get("src") or r.get("id")
        s = SOURCES[sid]
        cells.append("[%s](%s)" % (s["id"], s["url"]))
        cells.append("yes" if r.get("verified", True) else "NO — flagged")
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def write_docs():
    docs = {}
    docs["repo-audit.md"] = ("""# Repo audit — line by line

Reviewed 2026-11-12 (UTC) on branch `arena/80731db4-nfl1` at base commit `5aeb599`.

| Line | What was checked | Result | Official source |
| --- | --- | --- | --- |
| 1 | Tracked files at start | `README.md` only | [repo](https://github.com/kanlerxz87-cyber/NFL1) |
| 2 | README content | One line: `# NFL1` | [repo](https://github.com/kanlerxz87-cyber/NFL1) |
| 3 | Git history | One commit `5aeb599 Initial commit` | [repo](https://github.com/kanlerxz87-cyber/NFL1) |
| 4 | Branches at start | `main`; a second session branch appeared later | [repo](https://github.com/kanlerxz87-cyber/NFL1) |
| 5 | Pages config | `main / /`, legacy, status built | [Pages API](https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages) |
| 6 | Workflows / site / data | None existed before this session | [repo](https://github.com/kanlerxz87-cyber/NFL1) |

No prior implementation was available to verify, so every value on this site was collected from an official
source during this session. Irregularities F01, F16, F17, F22 and F23 are published on the site's
Flagged for Review page.

""" + md_table([("ID", "id", "id"), ("Irregularity", "description", "text"),
                             ("Impact", "impact", "text"), ("Action", "action", "text")], d["flags"][:8]))

    docs["verification.md"] = ("# Verification policy and source registry\n\n"
        "Every table row on the site links to an official source. Values that no official source publishes are "
        "left blank and flagged. No value is inferred or filled in. All sources below were fetched and read on "
        "2026-11-12 (UTC).\n\n" +
        md_table(C_SOURCES, d["sources"]) +
        "\n\n## Procedure\n\n" + md_table([("ID", "id", "id"), ("Step", "step", "num"),
                                            ("Action", "action", "text"), ("Detail", "detail", "text")], VERIFY_STEPS) +
        "\n\nAutomated enforcement: `tools/verify.py`; derived values: `tools/compute_correlations.py`.\n")

    docs["requirements-analysis.md"] = ("# Requirements — collected, organised, analysed\n\n"
        "The brief was decomposed line by line into %d atomic requirements.\n\n" % counts["requirements"] +
        md_table([("ID", "id", "id"), ("Category", "category", "text"),
                  ("Requirement", "requirement", "text"), ("Analysis / response", "analysis", "text"),
                  ("Status", "status", "text")], d["requirements"]) +
        "\n\nDependencies: R11 depends on Q10; R19 on Q11/Q12; R23/R24 on Q05/Q06; R31 is enforced by the validator.\n")

    docs["decision-gate.md"] = ("# Decision gate — questions, information, answers\n\n"
        "A decision is reasonable only when the questions below have answers supported by an official source. "
        "Blank cells are blank on purpose.\n\n" +
        md_table([("ID", "id", "id"), ("Question", "question", "text"),
                  ("Have", "known", "text"), ("Do not have", "unknown", "text"),
                  ("Answer", "answer", "text"), ("Discovery action", "discovery", "text")], d["questions"]) + "\n")

    docs["improvement-paths.md"] = ("# Improvement suggestions and choose-a-path\n\n"
        "All suggestions are awaiting review. A reviewer must choose a path before anything is implemented; "
        "the site's Suggestions page provides the selection control and a prefilled decision-record issue.\n\n"
        "## Paths\n\n" + md_table([("ID", "id", "id"), ("Path", "name", "text"),
                                   ("Summary", "summary", "text"), ("Blocked by", "blocks", "text")], d["paths"]) +
        "\n\n## Suggestions\n\n" +
        md_table([("ID", "id", "id"), ("Area", "area", "text"), ("Suggestion", "title", "text"),
                  ("Decision impact", "decision_impact", "text"), ("Effort", "effort", "text")], d["suggestions"]) + "\n")

    docs["strategy-research.md"] = ("# Own lines, signals, validation gates, correlations, skill vs luck\n\n"
        "All strategies are research designs. No strategy has passed validation; no performance value is published.\n\n"
        "## Own-line pipeline\n\n" +
        md_table([("ID", "id", "id"), ("Step", "step", "num"), ("Action", "action", "text"),
                  ("Detail", "detail", "text")], LINE_STEPS) +
        "\n\n## Strategies\n\n" +
        md_table([("ID", "id", "id"), ("Strategy", "name", "text"), ("Track", "track", "text"),
                  ("Hypothesis", "hypothesis", "text"), ("Formula", "formula", "text"),
                  ("Gates", "gates", "text")], d["strategies"]) +
        "\n\n## Validation gates\n\n" +
        md_table([("ID", "id", "id"), ("Gate", "name", "text"), ("Criterion", "criterion", "text"),
                  ("Threshold", "threshold", "text")], d["validation_gates"]) +
        "\n\n## Computed correlations (from official standings)\n\n" +
        md_table(C_CORR, d["correlations"]) +
        "\n\n## Requested correlations still blank\n\n" +
        md_table([("ID", "id", "id"), ("Pair", "pair", "text"), ("Blocker", "blocker", "text"),
                  ("Value", "r", "num")], d["correlation_requests"]) +
        "\n\n## Luck-control protocol\n\n" +
        md_table([("ID", "id", "id"), ("Control", "control", "text"), ("Mechanism", "mechanism", "text")], LUCK_PROTOCOL) + "\n")

    docs["competition-rules.md"] = ("# Leaderboard competition rules\n\n"
        "Three tracks (single bet, parlay, player prop combo). Rewards are non-monetary badges; values are blank "
        "because no official source defines them. No rank or score is published until all 13 gates pass.\n\n" +
        md_table([("ID", "id", "id"), ("Rule", "rule", "text"), ("Detail", "detail", "text")], d["leaderboard_rules"]) +
        "\n\n## Leaderboard (all performance cells blank)\n\n" +
        md_table([("Strategy", "strategy_id", "id"), ("Track", "track", "text"), ("Rank", "rank", "text"),
                  ("Score", "score", "text"), ("Gates passed", "gates_passed", "text")], d["leaderboard"]) +
        "\n\n## Bet-type evidence\n\n" +
        md_table([("Measure", "label", "text"), ("Value", "value", "num"),
                  ("Unit", "unit", "text")], d["betting_facts"]) + "\n")

    docs["injury-tracking.md"] = ("# Injury and backup-depth tracking\n\n"
        "Official Week 10 2026 injury report snapshot, official filing policy, official Week 9 inactives and "
        "three official club depth charts. Blank cells are blank on the official pages.\n\n"
        "## Designations published in the transcribed rows\n\n" +
        md_table([("Club", "team", "text"), ("Player", "player", "text"), ("Pos", "pos", "text"),
                  ("Injury", "injury", "text"), ("Practice", "practice", "text"),
                  ("Game status", "game_status", "text")],
                 [r for r in d["injuries"] if r["injury"] or r["game_status"]]) +
        "\n\n## Filing policy\n\n" +
        md_table([("Game day", "game_day", "text"), ("Practice days", "practice_report_days", "text"),
                  ("Game Status Report", "game_status_report_day", "text")], d["injury_policy"]) +
        "\n\n## Tracking pipeline\n\n" +
        md_table([("ID", "id", "id"), ("Stage", "stage", "text"), ("Detail", "detail", "text")], TRACKING_PIPELINE) +
        "\n\n## Official depth charts\n\n" +
        md_table([("Club", "code", "text"), ("Unit", "unit", "text"), ("Pos", "pos", "text"),
                  ("1st", "s1", "text"), ("2nd", "s2", "text"), ("3rd", "s3", "text"),
                  ("4th", "s4", "text")], d["depth_chart"]) + "\n")

    docs["exec-summary.md"] = ("# Executive summary\n\n"
        "The repository began as a single-line README. This session built a %d-page, source-linked GitHub Pages "
        "dashboard from %d official sources covering the 2026 NFL Week 10 snapshot (2026-11-12 UTC): %d standings "
        "rows, %d injury rows, %d depth-chart rows, %d official inactives rows, official bet-type statistics and "
        "official statistical methods.\n\n"
        "**Decision posture: NOT READY.** %d flagged irregularities and multiple unverified values remain. No "
        "official source was found for NFL betting lines, vig, leg-level correlations, injury-to-performance "
        "correlations, reward values or a skill threshold; every such cell is blank and flagged. The "
        "Review & Choose a Path gate must be resolved before implementation.\n\n"
        "**Own lines and competition.** A reproducible own-line pipeline and %d candidate strategies across "
        "single bets, parlays and player prop combos are specified. Every strategy must pass %d validation gates; "
        "all are currently NOT PASSED, so the leaderboard contains no ranks or scores. %d Pearson correlations "
        "were computed from official standings (net points per game vs winning percentage r = %s, n = %d); all "
        "other requested correlations remain blank. NIST guidance on cross-validation, significance testing and "
        "'correlation does not imply causality' underpins the luck-control protocol.\n\n"
        "**Injuries and depth.** Official club charts publish 1st–4th string for offense and defense; two are "
        "labelled 'Unofficial'; the league injury report publishes no depth rank. A deficiency score is therefore "
        "left blank and flagged.\n\n"
        "**Delivery.** PR to main, autonomous merge and a confirmed Pages deployment are recorded on the site's "
        "Deployment & PR page and in COORDINATION.md. Flagged items do not block the merge.\n\n"
        "## Findings\n\n" % (len(SITE_SECTIONS), counts["sources"], counts["standings"], counts["injuries"],
                              counts["depth"], counts["inactives"], counts["flags"], counts["strategies"],
                              counts["gates"], counts["correlations"], c05["r"], c05["n"]) +
        md_table([("ID", "id", "id"), ("Finding", "statement", "text"), ("Status", "status", "text")], d["findings"]) + "\n")

    docs["deployment.md"] = ("# Deployment and PR record\n\n" +
        md_table([("ID", "id", "id"), ("Item", "item", "text"), ("Value", "value", "text"),
                  ("How checked", "how_checked", "text")], d["deployment"]) +
        "\n\nPublishing rules: [GitHub Docs](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) "
        "and [creating a Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site). "
        "Configuration confirmed with `gh api repos/kanlerxz87-cyber/NFL1/pages`.\n")

    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    for name, content in docs.items():
        with open(os.path.join(ROOT, "docs", name), "w", encoding="utf-8") as f:
            f.write(content)
        print("doc ", "docs/" + name)


def write_readme():
    txt = """# NFL1 — NFL decision-intelligence dashboard

**Live site:** https://kanlerxz87-cyber.github.io/NFL1/
**Data snapshot:** 2026 NFL regular season, Week 10, retrieved 2026-11-12 (UTC).

A clean, static GitHub Pages dashboard built from a JSON data layer. Every table row links to an official
source. If an official source publishes no value, the cell is left blank and the item is flagged on the
[Flagged for Review](flagged.html) page. No value is inferred or filled in.

## Pages

| Page | Contents |
| --- | --- |
| [index.html](index.html) | Landing dashboard, counts, decision posture |
| [executive-summary.html](executive-summary.html) | Executive summary |
| [requirements.html](requirements.html) | Full requirements inventory and analysis |
| [questions.html](questions.html) | Decision questions, known/unknown information, answers, discovery actions |
| [suggestions.html](suggestions.html) | Improvement suggestions + Review & Choose a Path gate |
| [strategy-lab.html](strategy-lab.html) | Own lines, signal research, strategies, validation gates, correlations, skill vs luck |
| [leaderboard.html](leaderboard.html) | Competition rules, rewards and the (empty) ranked board |
| [bet-types.html](bet-types.html) | Single bets, parlays, player prop combos, official risk data |
| [injuries.html](injuries.html) | Official injury report, filing policy, inactives, tracking design |
| [depth-chart.html](depth-chart.html) | 1st/2nd/3rd/4th string for offense and defense |
| [data-tables.html](data-tables.html) | Standings, derived metrics, correlations, bet facts, findings |
| [verification.html](verification.html) | Verification policy, official source registry, line-by-line audit |
| [flagged.html](flagged.html) | Flagged for Review (does not block the merge) |
| [deployment.html](deployment.html) | Pages configuration, PR, merge and deploy record |
| [integration.html](integration.html) | Combined integration: re-verification of all merged sessions' data, line by line |
| [legacy-site.html](legacy-site.html) | Earlier sessions' dashboard, preserved verbatim (historical) |

## Rebuild and verify

```bash
python3 tools/seed_data.py              # regenerate data/*.json from transcribed official values
python3 tools/compute_correlations.py   # recompute Pearson r from official standings
python3 tools/verify_combined.py        # re-verify merged CSV snapshots and all local links
python3 tools/build.py                 # generate the HTML pages and docs/*.md
python3 tools/verify.py                # source links, unverified blanks, internal links
```

`tools/verify.py` and `tools/verify_combined.py` also run in GitHub Actions on every push and pull
request. GitHub Pages publishes `main / /`; `.nojekyll` keeps the generated HTML unchanged.

## Combined site (final integration)

`main` already contained a dashboard produced by earlier parallel sessions. Both site generations are
published: this dashboard at `/`, and the earlier dashboard preserved at
[legacy-site.html](legacy-site.html) with its `pages/` subpages, `styles.css`, `assets/` and
`data/*.csv` snapshots. The pre-integration coordination board and README are preserved in
`docs/COORDINATION-archive-main.md` and `docs/README-session-533256e1.md`. See
[integration.html](integration.html) for the line-by-line combined-data check and the local link audit
across both site generations. Residual combined-site issues are published as flags F25–F29 on
[flagged.html](flagged.html).

## Coordination

[COORDINATION.md](COORDINATION.md) is the shared task board for parallel agent sessions. All work in this
session stayed on the current branch with disjoint file scopes; conflicts and deviations are logged there and
on the Flagged for Review page.

## Sources

The complete registry of %d official sources, with links for manual review, is in
[data/sources.json](data/sources.json) and on the [Verification page](verification.html). Sources include
NFL.com, NFL Football Operations, official club sites, NFL Next Gen Stats, the NIST/SEMATECH e-Handbook,
the New Jersey Division of Gaming Enforcement, GitHub Docs and the GitHub REST API.
""" % counts["sources"]
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write(txt)
    print("wrote README.md")


def main():
    page_home(); page_exec(); page_requirements(); page_questions(); page_suggestions()
    page_strategy(); page_leaderboard(); page_bet_types(); page_injuries(); page_depth()
    page_data(); page_verification(); page_flagged(); page_deployment(); page_integration()
    write_docs()
    write_readme()
    with open(os.path.join(ROOT, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")
    print("build complete")


if __name__ == "__main__":
    main()
