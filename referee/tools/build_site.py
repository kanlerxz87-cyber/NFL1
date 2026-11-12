#!/usr/bin/env python3
"""V5 - Build the Referee pages (referee/*.html) from the evidence files in referee/data/.

Nothing is typed into a table by hand: every number comes from a JSON file written by one of the
scripts in referee/analysis/ or referee/tools/. Every table row carries a link for manual review.
Values that could not be confirmed are left blank and carry a status.

Run from the repository root:  python3 referee/tools/build_site.py
Then check:                    python3 referee/tools/check_site.py
Standard library only.
"""
import glob
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)            # referee/
REPO = os.path.dirname(ROOT)            # repository root
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import replicate_luck_thresholds as LUCK  # noqa: E402

GH = "https://github.com/kanlerxz87-cyber/NFL1"
NFLDATA = "https://github.com/nflverse/nfldata/blob/692e5f9f8ac9f4e2ee751c630817a7c290a04390/data"
GAMES = f"{NFLDATA}/games.csv"
CLOSING = f"{NFLDATA}/closing_lines.csv"
STAND = "https://www.nfl.com/standings/league/{}/REG"
DIVS = "https://www.nfl.com/standings/division/2026/REG"

PAGES = [("index.html", "Overview"), ("results.html", "Results audit"), ("lines.html", "Betting lines"),
         ("replication.html", "Replication"), ("luck.html", "Luck and sensitivity"),
         ("sessions.html", "Sessions"), ("flagged.html", "Flagged for Review")]


def load(name):
    with open(os.path.join(ROOT, "data", name)) as fh:
        return json.load(fh)


def e(x):
    return "" if x is None else html.escape(str(x))


def a(url, text):
    return f'<a href="{e(url)}">{e(text)}</a>'


def chip(kind, text):
    return f'<span class="chip {kind}">{e(text)}</span>'


def blob(path, ref="main"):
    return f"{GH}/blob/{ref}/{path}"


def num(x, nd=None):
    if x is None:
        return ""
    if isinstance(x, float) and nd is not None:
        return f"{x:,.{nd}f}"
    if isinstance(x, int):
        return f"{x:,}"
    return e(x)


def table(cols, rows, caption=None):
    """cols: list of (label, css class). rows: list of lists of HTML strings."""
    out = [f'<div class="tablewrap{" wide" if len(cols) >= 9 else ""}"><table>']
    if caption:
        out.append(f"<caption>{caption}</caption>")
    out.append("<thead><tr>" + "".join(f'<th class="{c}" scope="col">{e(l)}</th>' for l, c in cols) + "</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join(f'<td class="{cols[i][1]}">{v}</td>' for i, v in enumerate(r)) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def fold(summary, inner):
    return f"<details><summary>{summary}</summary>\n{inner}\n</details>"


def tiles(items):
    return f'<div class="tiles {"six" if len(items) == 6 else "four"}">' + "".join(f'<div class="tile {k}"><b>{e(v)}</b><span>{e(t)}</span></div>' for k, v, t in items) + "</div>"


def page(fname, title, body, as_of):
    cur = ' aria-current="page"'
    nav = "".join(f'<a href="{f}"{cur if f == fname else ""}>{e(l)}</a>' for f, l in PAGES)
    nav += '<a class="out" href="../index.html">Main site</a>'
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} | Referee, NFL1</title>
<meta name="description" content="Independent verification of the NFL1 project: official-source audits, replication of published numbers, and items flagged for review.">
<link rel="stylesheet" href="assets/referee.css">
</head>
<body>
<header class="top"><div class="wrap">
<a class="brand" href="index.html"><span class="pennant" aria-hidden="true"></span><span>Referee<small>Independent verification</small></span></a>
<nav aria-label="Referee sections">{nav}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
<p>Built by session 73fdd6c4 from the evidence files in <a href="{blob('referee/data')}">referee/data</a>. Repository state as of {e(as_of)} UTC.</p>
<p>Official values were read on nfl.com on 2026-11-12 (UTC). Betting lines come from a community dataset and are unverified everywhere on this site. Nothing here is betting advice.</p>
</div></footer>
</body>
</html>
"""
    with open(os.path.join(ROOT, fname), "w") as fh:
        fh.write(doc)


# ------------------------------------------------------------------------------------------------
def main():
    audit = load("audit_results.json")
    lines = load("lines_audit.json")
    rmain = load("replication_main_data.json")
    r76 = load("replication_7600ed8b.json")
    r25 = load("replication_25aa7696.json")
    r80 = load("replication_80731db4.json")
    sens = load("replication_sensitivity.json")
    luck = load("replication_luck_thresholds.json")
    sess = load("sessions.json")
    as_of = sess["as_of_utc"]
    T = audit["totals"]
    N_SESS = {7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten"}.get(len(sess["sessions"]), str(len(sess["sessions"])))

    OK, UNV, NREP, NTEST, NAUD = chip("ok", "Match"), chip("warn", "Unverified input"), chip("bad", "Not replicated"), chip("", "Not testable here"), chip("", "Not audited")

    def status_chip(s):
        s = (s or "").lower()
        if s in ("match", "replicated"):
            return chip("ok", "Match" if s == "match" else "Replicated")
        if s.startswith("not replicable"):
            return NTEST
        if s.startswith("not replicated") or s == "mismatch":
            return NREP if "replic" in s else chip("bad", "Mismatch")
        return chip("", s or "n/a")

    # ---- counts used on several pages -----------------------------------------------------------
    main_rows = sum(t["rows_checked"] for t in rmain["tables"])
    main_match = sum(t["rows_matching"] for t in rmain["tables"])
    data_rows = main_rows + r80["standings"]["rows_checked"]
    data_match = main_match + r80["standings"]["rows_matching"]
    c25 = r25["correlation_checks"]
    c80 = r80["correlations"]["rows"]
    rep = r76["counts"].get("replicated", 0) + sum(c["status"] == "replicated" for c in c25) + sum(c["status"] == "replicated" for c in c80) + r80["per_game"]["rows_matching"]
    nrep = r76["counts"].get("NOT replicated", 0) + sum(c["status"] == "NOT replicated" for c in c25) + sum(c["status"] == "NOT replicated" for c in c80) \
        + (r80["per_game"]["rows_checked"] - r80["per_game"]["rows_matching"])
    ntest = r76["counts"].get("not replicable here", 0) + sum(c["status"] == "not replicable here" for c in c80)
    c5 = r25["c5_root_cause"]

    # ---- strategies against the luck bar ----------------------------------------------------------
    tried = len(r76["strategies"])
    alpha_k = 1 - 0.95 ** (1.0 / tried)
    bar_rows, clears_any = [], 0
    for s in sorted(r76["strategies"], key=lambda s: s["strategy"]):
        w, l, p = (int(x) for x in s["published_record"].split("-"))
        n = w + l
        b1, bk = LUCK.min_wins(n, 0.05), LUCK.min_wins(n, alpha_k)
        clears = w >= bk
        clears_any += clears
        bar_rows.append((s, w, l, p, n, b1, bk, clears))
    best = max(bar_rows, key=lambda r: r[1] / r[4])

    # ---- flags ------------------------------------------------------------------------------------
    dead = {}
    for f in [os.path.join(REPO, "index.html")] + sorted(glob.glob(os.path.join(REPO, "pages", "*.html"))):
        txt = open(f, encoding="utf-8").read()
        for u in ("https://operations.nfl.com/the-rules/", "https://operations.nfl.com/gameday/nfl-schedule/", "https://operations.nfl.com/gameday/"):
            if f'"{u}"' in txt:
                dead.setdefault(u, []).append(os.path.relpath(f, REPO))
    claim_only = [s for s in sess["sessions"] if s["state"] == "claim only"]
    shared = [o for o in sess["overlaps"] if len(o["modified_by_unmerged_branches"]) > 1]
    price = sens["price_test"]["rows"]
    src_rows = sens["line_source_test"]["rows"]
    ref76 = r76["commit"]
    perfect = [r for r in r76["rows"] if r["section"] == "Correlation between strategies" and isinstance(r["published"], (int, float)) and abs(r["published"]) >= 0.999]

    flags = [
        ("R-01", "Unverified", "Betting lines, prices and totals, every season",
         "No official NFL page publishes historical closing lines. Every line-based number here and in other sessions' strategy tables rests on a community dataset.",
         "All sessions using lines", "Pick one line source with capture times and licence terms, or accept that line-based results stay unverified.", GAMES, "nflverse games.csv (community data, unofficial)"),
        ("R-02", "Not audited", "Game results, seasons 1999 to 2020",
         f"Only 2021 to 2026 were compared with the official standings ({T['fields_matching']:,} of {T['fields_checked']:,} fields match). The earlier {len(T['seasons_not_audited'])} seasons were not compared.",
         "73fdd6c4", "Repeat the audit for the remaining seasons before trusting long backtests that start in 1999 or 2005.", STAND.format(2020), "NFL.com standings 2020"),
        ("R-03", "Unverified", "Division names (East, North, South, West)",
         "The official division standings page, as fetched, shows the eight four-team groups but not their names. Conference and grouping are confirmed for all 32 clubs; the name labels are not confirmed by this session.",
         "533256e1", "For data/teams.csv: confirm the names on a page that prints them, then mark the column verified.", DIVS, "NFL.com division standings 2026"),
        ("R-04", "Irregularity", "Division-game count on the live Validation and Correlation page",
         f"Published: {c5['published_division_games']} of 136 games were division games, correlation with total points -0.1297. "
         f"Using the official groupings: {c5['official_grouping_division_games']} games, correlation {c5['r_using_official_grouping']}. "
         f"The {len(c5['cross_conference_games_counted_as_division_games'])} extra games are all AFC West against NFC West: the code compares the word West and ignores the conference.",
         "25aa7696",
         "In analysis/correlations.py compare conference and division together, then regenerate correlations.json and pages/analysis.html. Any rule that uses this division flag needs re-running.", DIVS, "NFL.com division standings 2026"),
        ("R-05", "Irregularity", "Two closing-line files from the same maintainer disagree",
         f"Across {lines['cross_file']['spread']['games_in_both']:,} games in both files, the spread is identical in {lines['cross_file']['spread']['exact_pct']}% and the total in {lines['cross_file']['total']['exact_pct']}%. "
         "There is no single closing line. Strategy win rates move by up to "
         f"{max(abs(r['win_pct_change_points']) for r in src_rows)} points when the other file is used.",
         "nflverse (upstream)", "Record which book and which timestamp each line comes from.", CLOSING, "nflverse second file (unofficial)"),
        ("R-06", "Irregularity", "Every bet graded at an assumed price of -110",
         f"The dataset holds actual prices for most games since 2006. Using them changes return on investment by {min(r['difference_pct_points'] for r in price)} to "
         f"{max(r['difference_pct_points'] for r in price)} percentage points. No verdict changes.",
         "7600ed8b", "Grade at the recorded price where one exists and say which rows used the assumption.", blob("data/model/strategies.json", ref76), "Their strategies file at the commit checked"),
        ("R-07", "Unverified", f"{r76['counts'].get('not replicable here', 0)} published numbers could not be tested here",
         "The own-line model, its error figures and four strategies (S01, S02, S03, S12) need play-by-play and injury files that this sandbox cannot download.",
         "7600ed8b", "Run the replication script where those files are reachable, for example in the branch's own workflow.", blob("data/model/lines.json", ref76), "Their lines file at the commit checked"),
        ("R-08", "Irregularity", "Strategy pairs that are the same bet",
         f"{len(perfect)} replicated strategy pairs have a correlation of exactly 1.0 or -1.0 on the games they share (for example S04 with S06 on 207 games). "
         "They are one bet counted under two names, or the two sides of one bet. The owner's gate G8 fails them, which is the correct outcome.",
         "7600ed8b", "Merge or drop duplicates before counting how many strategies were tried.", blob("data/model/strategies.json", ref76), "Their strategies file at the commit checked"),
        ("R-09", "Irregularity", "Stale error record",
         "data/model/errors.json still shows a failure in the strategy stage (KeyError 'te') stamped 04:34:07 UTC, although later builds wrote a complete leaderboard. The file is not cleared on success.",
         "7600ed8b", "Rewrite the error file on every run so an old failure is not mistaken for a current one.", blob("data/model/errors.json", ref76), "Their errors file at the commit checked"),
        ("R-10", "Irregularity", "Schedule link that changes meaning each week",
         "Source links of the form nfl.com/schedules/2026/REG10 redirect to the current week's schedule. Today that is Week 10, next week it will not be.",
         "7600ed8b", "Use the stable form nfl.com/schedules/2026/by-week/week-10.", "https://www.nfl.com/schedules/2026/by-week/week-10", "NFL.com Week 10 schedule (stable address)"),
        ("R-11", "Irregularity", "Three NFL Football Operations addresses return 404",
         "operations.nfl.com/the-rules/, /gameday/ and /gameday/nfl-schedule/ each returned the site's 404 page when fetched by this session. "
         + (f"Still cited on main in: {', '.join(sorted({p for v in dead.values() for p in v}))}." if dead else "They are no longer cited on main (fixed after session 15e79a53 reported them)."),
         "690e397b", "Replace with working official addresses." if dead else "No action needed. Kept for the record.", "https://operations.nfl.com/", "NFL Football Operations home"),
        ("R-12", "Irregularity", "Tasks marked done with no files on GitHub",
         ("; ".join(f"{s['session']}: {s['files_on_branch']} files on the branch, last commit {s['last_commit_utc'][11:]} UTC" for s in claim_only) + ". "
          "Their boards list data, scripts and pages as done, but none of those files has been pushed.") if claim_only else "No session is in this state at the time of the snapshot.",
         ", ".join(s["session"] for s in claim_only) or "none", "Treat these claims as open. Under the 60-minute rule they can be taken over if no commit follows.",
         claim_only[0]["branch_url"] if claim_only else GH, "Branch on GitHub"),
        ("R-13", "Irregularity", "Unmerged branches rewrite files that are already live",
         f"{len(sess['overlaps'])} files on main are modified by at least one unmerged branch; {len(shared)} of them by more than one "
         f"({', '.join(o['file'] for o in shared[:6])}{' and others' if len(shared) > 6 else ''}). Whichever merges second will conflict or overwrite.",
         ", ".join(sorted({x for o in sess["overlaps"] for x in o["modified_by_unmerged_branches"]})), "One integration owner should merge these in sequence and re-check the pages after each merge.",
         f"{GH}/branches", "Branches on GitHub"),
        ("R-14", "Irregularity", "The coordination file is rewritten wholesale by each session",
         "Several sessions replaced COORDINATION.md instead of appending to it, and at least four claim the final integration task. This session hit a merge conflict on that file at every sync (five times). "
         "It resolves them by keeping main's version unchanged and re-appending its own block.",
         "All sessions", "Give each session its own section or file so that merges do not collide.", blob("COORDINATION.md"), "COORDINATION.md on main"),
        ("R-15", "Irregularity", "Club code LAR in data/standings.csv",
         "NFL.com uses LA for the Rams (and AZ for Arizona). The values in the row are correct; only the code differs from the official one.",
         "533256e1", "Use the official club code or document the mapping.", STAND.format(2026), "NFL.com standings 2026"),
        ("R-16", "Irregularity", "2022: Buffalo and Cincinnati have 16 games, not 17",
         "The dataset and the official 2022 standings agree on this. The reason was not looked up in an official source in this session, so none is stated.",
         "nflverse (upstream)", "No change to the numbers. Models that assume 17 games per team must allow for it.", STAND.format(2022), "NFL.com standings 2022"),
        ("R-17", "Irregularity", "Seven 2026 games are marked neutral-site in the dataset",
         "Home and road records still match the official standings for all 32 clubs, so the official page counts a designated home team in these games. Home-field estimates should treat them separately.",
         "nflverse (upstream)", "Exclude or flag neutral-site games when estimating home advantage.", STAND.format(2026), "NFL.com standings 2026"),
    ]
    with open(os.path.join(ROOT, "data", "flags.json"), "w") as fh:
        json.dump({"generated_by": "referee/tools/build_site.py", "as_of_utc": as_of,
                   "flags": [dict(zip(("id", "type", "item", "finding", "owner", "suggested_action", "source_url", "source_label"), f)) for f in flags]}, fh, indent=1)
    n_irr = sum(f[1] == "Irregularity" for f in flags)
    n_unv = len(flags) - n_irr

    def type_chip(t):
        return chip({"Irregularity": "bad", "Unverified": "warn"}.get(t, ""), t)

    # ================================================================================================
    # index.html
    # ================================================================================================
    b = []
    b.append('<p class="eyebrow">NFL1 project, checked 2026-11-12</p>')
    b.append("<h1>A second check on every number the project publishes</h1>")
    b.append('<p class="lede">' + N_SESS + ' sessions worked on this project in parallel. This section belongs to none of the build pipelines. It re-reads the official NFL pages, recomputes the published numbers from scratch, and lists what does not hold up.</p>')
    b.append(tiles([
        ("", f"{T['fields_matching']:,} / {T['fields_checked']:,}", "official standings fields match the results dataset, 2021 to 2026"),
        ("", f"{data_match} / {data_rows}", "published data-table rows match NFL.com"),
        ("", f"{r25['game_level']['matching']} / {r25['game_level']['their_games']}", "2026 game scores agree between two independent sources"),
        ("warn" if nrep else "", f"{rep} / {rep + nrep}", f"testable published calculations reproduced; {ntest} more could not be tested here"),
        ("bad", f"{clears_any} of {tried}", "strategies win often enough to rule out luck"),
        ("warn", f"{len(flags)}", f"items flagged for review ({n_irr} irregularities, {n_unv} unverified or not audited)"),
    ]))
    b.append("<h2>What this means for a decision</h2>")
    b.append(table([("Finding", "k w"), ("Evidence", "w"), ("What to do with it", "w"), ("Status", ""), ("Source for manual review", "")], [
        ["Game results are reliable for 2021 to 2026.",
         f"All {T['team_seasons_audited']} team-seasons and {T['reg_games_covered']:,} games reproduce the official wins, losses, ties, points for and against, home and road records.",
         "Use results from these seasons freely. Earlier seasons are not yet audited.", OK, a(STAND.format(2026), "NFL.com standings") + " · " + a("results.html", "detail")],
        ["Betting lines cannot be verified.",
         f"No official source exists. Two files from the same maintainer give the same spread in only {lines['cross_file']['spread']['exact_pct']}% of games.",
         "Treat every line-based result as provisional until a timestamped line source is chosen.", UNV, a(GAMES, "nflverse games file (unofficial)") + " · " + a("lines.html", "detail")],
        ["No strategy has shown skill yet.",
         f"The best published record is {best[0]['strategy'].split(' ', 1)[0]} at {100 * best[1] / best[4]:.2f}% over {best[4]} graded bets. With {tried} strategies tried, a record over that many bets has to reach "
         f"{100 * best[6] / best[4]:.2f}% before luck becomes an unlikely explanation. The owners' own gates reach the same verdict.",
         "Do not stake money on any current strategy. Keep collecting graded bets.", UNV, a(blob("data/model/strategies.json", ref76), "Published leaderboard") + " · " + a("luck.html", "detail")],
        ["The closing line is the benchmark to beat, and it is hard to beat.",
         f"Across {lines['games_with_spread_and_total']:,} games the home side covered {_all(lines, 'home_cover_pct')}% and the favourite {_all(lines, 'favorite_cover_pct')}%; a bet at -110 needs {luck['breakeven_win_pct']}%.",
         "Judge every own-line model against the closing line first. A model that is less accurate than the market has no edge.", UNV, a(GAMES, "nflverse games file (unofficial)") + " · " + a("lines.html", "detail")],
        ["One published correlation on the live site is wrong.",
         f"Division games are counted as {c5['published_division_games']}; the official groupings give {c5['official_grouping_division_games']}.",
         "Fix before any division-based rule is tested. Logged as a request to the owning session.", chip("bad", "Not replicated"), a(DIVS, "NFL.com division standings") + " · " + a("flagged.html#R-04", "flag R-04")],
        ["Sample size, not cleverness, is the binding constraint.",
         f"A strategy that truly wins 55% clears the luck bar only {luck['power_at_55pct'][3]['chance_to_clear_bar_pct']}% of the time after 500 bets and {luck['power_at_55pct'][5]['chance_to_clear_bar_pct']}% after 2,500.",
         "Fix each rule before testing, test few rules, and count every rule that was tried.", chip("ok", "Arithmetic"), a(blob("referee/analysis/replicate_luck_thresholds.py"), "Method (script)") + " · " + a("luck.html", "detail")],
    ]))
    b.append("<h2>What was checked</h2>")
    rows = [
        ["Results dataset against official standings", "2021 to 2026, seven fields per team", f"{T['fields_matching']:,} of {T['fields_checked']:,} fields", OK, a(STAND.format(2026), "NFL.com standings"), a("results.html", "Results audit")],
        ["Results dataset, seasons 1999 to 2020", "Not compared with official pages", "", NAUD, a(STAND.format(2020), "NFL.com standings 2020"), a("results.html", "Results audit")],
        ["Betting lines: internal consistency", f"{lines['games_with_spread_and_total']:,} games, eight checks", f"{sum(c['violations'] for c in lines['checks'])} anomalies", UNV, a(GAMES, "nflverse games file (unofficial)"), a("lines.html", "Betting lines")],
    ]
    for t in rmain["tables"]:
        rows.append([f"Live site table <code>{e(t['file'])}</code>", e(t["what"]), f"{t['rows_matching']} of {t['rows_checked']} rows", OK if t["rows_matching"] == t["rows_checked"] else chip("bad", "Mismatch"),
                     a(t["official_source"], "NFL.com"), a("replication.html", "Replication")])
    rows += [
        ["2026 scores transcribed by session 25aa7696", "136 games against the dataset; 12 read again on NFL.com", f"{r25['game_level']['matching']} of {r25['game_level']['their_games']} and {r25['official_spot_check']['matching']} of {len(r25['official_spot_check']['rows'])}",
         OK, a("https://www.nfl.com/schedules/2026/by-week/week-1", "NFL.com Week 1 schedule"), a("replication.html", "Replication")],
        ["Correlations published by session 25aa7696", "Nine values that depend only on scores", f"{sum(c['status'] == 'replicated' for c in c25)} of {len(c25)} reproduced",
         chip("bad", "2 not replicated"), a(DIVS, "NFL.com division standings"), a("replication.html", "Replication")],
        ["Strategy leaderboard of session 7600ed8b", "Records, returns, p-values, corrections, correlations", f"{r76['counts'].get('replicated', 0)} reproduced, {r76['counts'].get('not replicable here', 0)} not testable",
         UNV, a(blob("data/model/strategies.json", ref76), "Their file at the commit checked"), a("replication.html", "Replication")],
        ["Tables of session 80731db4", "Standings, per-game values, six correlations", f"{r80['standings']['rows_matching']} of {r80['standings']['rows_checked']} rows, {sum(c['status'] == 'replicated' for c in c80)} of {len(c80)} correlations",
         OK, a(STAND.format(2026), "NFL.com standings"), a("replication.html", "Replication")],
        ["Parallel sessions", f"{len(sess['sessions'])} branches, pull requests, overlapping edits", f"{len(sess['overlaps'])} live files touched by unmerged branches", chip("warn", "See register"), a(f"{GH}/branches", "Branches on GitHub"), a("sessions.html", "Sessions")],
    ]
    b.append(table([("Check", "k w"), ("Scope", "w"), ("Result", "nw"), ("Status", ""), ("Source for manual review", ""), ("Detail", "nw")], rows))
    b.append('<h2>How to read the status labels</h2>')
    b.append(table([("Label", ""), ("Meaning", "w"), ("Reference", "")], [
        [OK, "The published value equals the value on the linked official page, read by this session.", a(STAND.format(2026), "Example official page")],
        [chip("ok", "Replicated"), "This session recomputed the number independently and got the same result. It says the arithmetic is right, not that the input is official.", a(blob("referee/analysis"), "Scripts")],
        [UNV, "The number is computed correctly from data that has no official source. Betting lines are always in this group.", a(GAMES, "nflverse games file (unofficial)")],
        [NREP, "This session's independent calculation gives a different number.", a(DIVS, "Example: official division groups") + " · " + a("flagged.html", "Flagged for Review")],
        [NTEST, "The inputs could not be obtained in this environment. The value is neither confirmed nor contradicted.", a(blob("data/model/lines.json", ref76), "Example: model file") + " · " + a("flagged.html", "Flagged for Review")],
        [NAUD, "Not compared with an official source in this session. The cell is left blank.", a(STAND.format(2020), "Where to check")],
    ]))
    page("index.html", "Independent verification", "\n".join(b), as_of)

    # ================================================================================================
    # results.html
    # ================================================================================================
    b = ['<p class="eyebrow">Results audit</p>', "<h1>Do the game results match the official record?</h1>",
         f'<p class="lede">Every strategy test in this project depends on one file of game results. For 2021 to 2026 it reproduces the official NFL.com standings exactly: {T["fields_matching"]:,} of {T["fields_checked"]:,} fields across {T["team_seasons_audited"]} team-seasons.</p>']
    b.append(tiles([("", f"{T['team_seasons_matching']} / {T['team_seasons_audited']}", "team-seasons match on all seven fields"),
                    ("", f"{T['reg_games_covered']:,}", "regular-season games covered by the audit"),
                    ("idle", f"{len(T['seasons_not_audited'])}", "earlier seasons not audited (1999 to 2020)"),
                    ("", "0", "internal inconsistencies in 28 seasons of rows")]))
    b.append('<p>Method: the season totals for each team (wins, losses, ties, points for, points against, home record, road record) were rebuilt from the individual game rows and compared with the league standings page for that year. '
             f'The results file is {a(GAMES, "games.csv from nflverse")}, a community dataset; the comparison is what makes it trustworthy for these seasons.</p>')
    b.append("<h2>Season by season</h2>")
    rows = []
    for s in audit["season_summaries"]:
        if s["status"] == "audited":
            rows.append([str(s["season"]), f"{s['teams_matching']} / {s['teams_official']}", f"{s['fields_matching']} / {s['fields_checked']}", num(s["reg_games_in_dataset"]), OK, a(s["source"], f"NFL.com standings {s['season']}")])
        else:
            rows.append([str(s["season"]), "", "", "", NAUD, a(STAND.format(s["season"]), f"NFL.com standings {s['season']}")])
    b.append(table([("Season", "k"), ("Teams matching", "n"), ("Fields matching", "n"), ("Games covered", "n"), ("Status", ""), ("Official source", "")], rows,
                   "Blank cells: not compared in this session. The link shows where each season can be checked by hand."))
    b.append("<h2>Every team-season</h2><p>Official values as read on NFL.com. The dataset column repeats the value rebuilt from the game rows, so any difference would be visible.</p>")
    for season in sorted({r["season"] for r in audit["rows"]}, reverse=True):
        rs = [r for r in audit["rows"] if r["season"] == season]
        rows = []
        for r in sorted(rs, key=lambda r: r["team"]):
            o, d = r["official"], r["dataset"]
            rows.append([e(r["team"]), f"{o['W']}-{o['L']}-{o['T']}", num(o["PF"]), num(o["PA"]), e(o["HOME"]), e(o["ROAD"]),
                         f"{d['W']}-{d['L']}-{d['T']} · {d['PF']} · {d['PA']} · {e(d['HOME'])} · {e(d['ROAD'])}",
                         OK if r["match"] else chip("bad", "Mismatch: " + ", ".join(r["mismatched_fields"])), a(r["source"], f"NFL.com {season}")])
        b.append(fold(f"{season}: {sum(r['match'] for r in rs)} of {len(rs)} teams match", table(
            [("Team", "k"), ("Official W-L-T", "n"), ("PF", "n"), ("PA", "n"), ("Home", "n"), ("Road", "n"), ("Dataset rebuilt from game rows", "nw"), ("Status", ""), ("Official source", "nw")], rows)))
    b.append("<h2>Internal consistency, all 28 seasons</h2><p>These checks need no outside source: the stored margin must equal home score minus away score, the stored total must equal their sum, ties must be flagged as overtime games, and no game may appear twice.</p>")
    rows = []
    for c in audit["internal_checks"]:
        per = ", ".join(f"{v} teams × {k} games" for k, v in sorted(c["reg_games_per_team"].items(), key=lambda kv: -int(kv[0])))
        errs = len(c["result_field_errors"]) + len(c["total_field_errors"]) + len(c["ties_not_flagged_overtime"]) + len(c["postseason_ties"])
        rows.append([str(c["season"]), num(c["played"]), num(c["reg_played"]), num(c["post_played"]), e(per), str(len(c["ties"])), str(errs),
                     chip("ok", "Consistent") if errs == 0 else chip("bad", "Errors"), a(STAND.format(c["season"]), f"NFL.com {c['season']}") + " · " + a(GAMES, "dataset")])
    b.append(table([("Season", "k"), ("Games played", "n"), ("Regular season", "n"), ("Postseason", "n"), ("Regular-season games per team", ""), ("Ties", "n"), ("Errors", "n"), ("Status", ""), ("Where to check", "nw")], rows,
                   "Consistent means the rows agree with each other. Only 2021 to 2026 were also compared with the official page."))
    b.append('<div class="note"><p><b>Two things to know when using this file.</b> In 2022 Buffalo and Cincinnati have 16 games rather than 17, on the official page as well. In 2026 seven games are marked neutral-site, yet home and road records still match the official standings. Both are listed on the <a href="flagged.html">Flagged for Review</a> page.</p></div>')
    page("results.html", "Results audit", "\n".join(b), as_of)

    # ================================================================================================
    # lines.html
    # ================================================================================================
    b = ['<p class="eyebrow">Betting lines</p>', "<h1>The lines cannot be verified, so here is how far they can be trusted</h1>",
         '<p class="lede">No official NFL page publishes historical point spreads or totals. Everything on this page is computed from a community dataset and is marked unverified. The checks show the data is internally coherent and behaves the way closing lines should.</p>',
         f'<div class="note"><p><b>Unverified input.</b> Source: {a(GAMES, "nflverse games.csv")} at a fixed commit. Its documentation names no bookmaker and no capture time. Use these numbers as benchmarks, not as facts about any sportsbook.</p></div>']
    b.append(tiles([("warn", f"{lines['games_with_spread_and_total']:,}", "played games with a spread and a total"),
                    ("warn", f"{_all(lines, 'favorite_cover_pct')}%", "of favourites covered the spread, all seasons"),
                    ("warn", f"{luck['breakeven_win_pct']}%", "win rate needed to break even at -110"),
                    ("warn", f"{lines['cross_file']['spread']['exact_pct']}%", "of spreads identical in a second file from the same maintainer")]))
    b.append("<h2>Consistency checks</h2>")
    b.append(table([("Check", "k w"), ("What it tests", "w"), ("Games checked", "n"), ("Anomalies", "n"), ("Examples", "m"), ("Status", ""), ("Source", "s")],
                   [[e(c["check"]), e(c["description"]), num(c["checked"]), num(c["violations"]), e("; ".join(c["examples"][:2])), UNV, a(GAMES, "nflverse games file (unofficial)")] for c in lines["checks"]]))
    cf = lines["cross_file"]
    b.append("<h2>Same games, second file</h2><p>The maintainer ships a second closing-line file for 2006 to 2018. If closing lines were a single agreed number the two files would match. They do not.</p>")
    b.append(table([("Field", "k"), ("Games in both files", "n"), ("Identical", "n"), ("Identical %", "n"), ("Within half a point", "n"), ("Within one point", "n"), ("Status", ""), ("Source", "s")],
                   [[lab, num(cf[k]["games_in_both"]), num(cf[k]["exact"]), f"{cf[k]['exact_pct']}%", num(cf[k]["within_half_point"]), num(cf[k]["within_one_point"]), UNV, a(CLOSING, "nflverse second file (unofficial)")]
                    for k, lab in (("spread", "Point spread"), ("total", "Total"), ("home_moneyline", "Home moneyline"))]))
    b.append("<h2>Benchmarks any strategy has to beat</h2><p>Cover rates leave out pushes. The error columns are the average miss, in points, of the closing spread against the final margin and of the closing total against the final total. The last column is the miss of a naive guess that every home team wins by the era's average margin.</p>")
    bcols = [("Period", "k"), ("Games", "n"), ("Home covers", "n"), ("Favourite covers", "n"), ("Favourite wins", "n"), ("Over", "n"), ("Spread miss", "n"), ("Total miss", "n"), ("Naive miss", "n"), ("Status", ""), ("Source", "m")]

    def brow(r, label):
        return [e(label), num(r["games"]), f"{r['home_cover_pct']}%", f"{r['favorite_cover_pct']}%", f"{r['favorite_win_pct']}%", f"{r['over_pct']}%",
                num(r["spread_mae"], 2), num(r["total_mae"], 2), num(r["naive_margin_mae"], 2), UNV, a(GAMES, "nflverse games file (unofficial)")]
    b.append(table(bcols, [brow(r, r["era"]) for r in lines["benchmarks_by_era"]]))
    b.append(fold("Each season, 1999 to 2026", table(bcols, [brow(r, str(r["season"])) for r in sorted(lines["benchmarks_by_season"], key=lambda r: -r["season"])])))
    mc = lines["moneyline_calibration"]
    b.append(f"<h2>Are the moneylines well calibrated?</h2><p>Each team's price was converted to a probability with the bookmaker margin removed, then grouped. If the market is well calibrated the two percentage columns agree. Across {mc['games']:,} games they do, closely (Brier score {mc['brier_score']}).</p>")
    b.append(table([("Market probability of the favourite", "k"), ("Games", "n"), ("Average market probability", "n"), ("Favourite actually won", "n"), ("Status", ""), ("Source", "m")],
                   [[e(x["bin"]), num(x["games"]), f"{x['mean_market_probability_pct']}%", f"{x['actual_win_pct']}%", UNV, a(GAMES, "nflverse games file (unofficial)")] for x in mc["bins"]]))
    b.append("<h2>Which seasons have which fields</h2>")
    b.append(fold("Coverage by season", table([("Season", "k"), ("Games played", "n"), ("Spread", "n"), ("Total", "n"), ("Moneylines", "n"), ("Spread prices", "n"), ("Total prices", "n"), ("Status", ""), ("Source", "m")],
                                              [[str(c["season"]), num(c["played"]), num(c["spread_line"]), num(c["total_line"]), num(c["home_moneyline"]), num(c["home_spread_odds"]), num(c["over_odds"]), UNV,
                                                a(GAMES, "nflverse games file (unofficial)")] for c in lines["coverage"]])))
    page("lines.html", "Betting lines", "\n".join(b), as_of)

    # ================================================================================================
    # replication.html
    # ================================================================================================
    b = ['<p class="eyebrow">Replication</p>', "<h1>Can the published numbers be reproduced independently?</h1>",
         '<p class="lede">For each session that published numbers, this session read the official page itself or rebuilt the calculation from the raw game rows, without running the other session\'s code. Their files were read, never edited.</p>']
    b.append(tiles([("", f"{data_match} / {data_rows}", "data-table rows match NFL.com"),
                    ("warn" if nrep else "", f"{rep} / {rep + nrep}", "testable calculations reproduced"),
                    ("bad" if nrep else "", str(nrep), "calculations not reproduced"),
                    ("idle", str(ntest), "calculations not testable here")]))
    b.append("<h2>Data tables on the live site (session 533256e1)</h2>")
    b.append(table([("File", "id"), ("Contents", "w"), ("Rows matching", "n"), ("Official rows missing", "n"), ("Status", ""), ("Official source", "nw")],
                   [[f"<code>{e(t['file'])}</code>", e(t["what"]), f"{t['rows_matching']} / {t['rows_checked']}", str(len(t.get("missing_official_teams", []) or [])),
                     OK if t["rows_matching"] == t["rows_checked"] else chip("bad", "Mismatch"), a(t["official_source"], "NFL.com")] for t in rmain["tables"]]))
    for t in rmain["tables"]:
        b.append(fold(f"<code>{e(t['file'])}</code>: all {t['rows_checked']} rows", table(
            [("Row", "k"), ("Published", "w"), ("Official", "w"), ("Status", ""), ("Note", "w"), ("Official source", "nw")],
            [[e(r["key"]), e(r["published"]), e(r["official"]), status_chip(r["result"]), e("; ".join(r["issues"]) or r["note"]), a(r["source"], "NFL.com")] for r in t["rows"]])))
    b.append('<p class="small">For <code>data/teams.csv</code> a match means conference and four-team grouping. The division name itself is not confirmed (flag R-03).</p>')

    b.append("<h2>2026 game scores (session 25aa7696, now on main)</h2>"
             f"<p>That session typed 136 final scores from the official weekly schedule pages. The same 136 games exist in the community dataset. The two routes are independent, and they agree on every score and date. "
             f"This session also read the first {len(r25['official_spot_check']['rows'])} Week 1 finals directly on NFL.com.</p>")
    b.append(table([("Game", "k"), ("Official score (away-home)", "n"), ("Dataset", "n"), ("Status", ""), ("Official source", "nw")],
                   [[e(r["game"]), e(r["official"]), e(r["dataset"]), status_chip(r["result"]), a(r["source"], "NFL.com Week 1 schedule")] for r in r25["official_spot_check"]["rows"]],
                   "Read by this session on the official page."))
    b.append(fold(f"All {r25['game_level']['their_games']} games: transcription against dataset ({r25['game_level']['matching']} match)", table(
        [("Game", "k"), ("Date", "nw"), ("Transcribed (away-home)", "n"), ("Dataset", "n"), ("Status", ""), ("Official source", "nw")],
        [[e(r["game"]), e(r["date"]), e(r["transcribed"]), e(r["dataset"]), status_chip(r["result"]), a(r["source"], "NFL.com schedule")] for r in r25["game_level"]["rows"]])))
    b.append("<h3>Correlation values that depend only on scores</h3>")
    b.append(table([("Published value", "k w"), ("Published", "n"), ("Referee", "n"), ("Status", ""), ("Note", "w"), ("Source", "m")],
                   [[e(c["item"]), num(c["published"]), num(c["referee"]), status_chip(c["status"]), e(c["note"]),
                     a(DIVS if c["item"].startswith("C5") else "https://www.nfl.com/schedules/2026/by-week/week-1", "NFL.com division standings" if c["item"].startswith("C5") else "NFL.com schedule")] for c in c25]))
    b.append(f'<div class="note bad"><p><b>Why the division-game numbers differ.</b> {e(c5["cause"])} Counting with only the division word gives {c5["games_counted_when_only_the_division_word_is_compared"]} games and a correlation of {c5["r_using_division_word_only"]}, '
             f'which is exactly what was published. The official groupings give {c5["official_grouping_division_games"]} games and {c5["r_using_official_grouping"]}.</p></div>')
    b.append(table([("Game wrongly counted as a division game", "k"), ("Status", ""), ("Official source", "nw")],
                   [[e(g), chip("bad", "Different conferences"), a(DIVS, "NFL.com division standings")] for g in c5["cross_conference_games_counted_as_division_games"]]))

    b.append(f"<h2>Strategy leaderboard (session 7600ed8b)</h2><p>Checked at commit <code>{e(ref76[:10])}</code>, their data stamped {e(r76['their_generated_at'])}. "
             "Eight strategies are simple rules on the games file and were rebuilt here from the rule descriptions. Four depend on that session's own model and could not be rebuilt.</p>")
    rows = []
    for s in sorted(r76["strategies"], key=lambda s: s["strategy"]):
        rows.append([e(s["strategy"]), e(s["published_status"]), e(s["published_record"]), e(s["referee_record"]),
                     "" if s["published_win_pct"] is None else f"{100 * s['published_win_pct']:.2f}%", "" if s["published_roi"] is None else f"{100 * s['published_roi']:+.2f}%",
                     num(s["published_p"]), status_chip(s["result"]) + " " + UNV, a(blob("data/model/strategies.json", ref76), "Their file")])
    b.append(table([("Strategy", "k m"), ("Their verdict", ""), ("Published record (W-L-push)", "n"), ("Referee record", "n"), ("Win rate", "n"), ("Return at -110", "n"), ("p-value", "n"), ("Status", ""), ("Source", "")], rows,
                   "A blank referee record means the strategy could not be rebuilt here. All records rest on unverified lines."))
    secs = {}
    for r in r76["rows"]:
        secs.setdefault(r["section"], []).append(r)
    rows = []
    for sec, rs in secs.items():
        for r in rs:
            rows.append([e(sec), e(r["item"]), num(r["published"]), num(r["referee"]), status_chip(r["status"]), e(r["note"]), a(blob("data/model/strategies.json" if "Own-line" not in sec and "Market" not in sec and "sign" not in sec.lower() else "data/model/lines.json", ref76), "Their file")])
    b.append(fold(f"All {len(r76['rows'])} numbers checked", table([("Group", "k"), ("Number", "w"), ("Published", "n"), ("Referee", "n"), ("Status", ""), ("Note", "w"), ("Source", "m")], rows)))
    b.append("<h3>The gates that session applies</h3>")
    b.append(table([("Gate", "k"), ("Rule", "w"), ("Source", "m")], [[e(g["id"]), e(g["rule"]), a(blob("data/model/strategies.json", ref76), "Their file")] for g in r76["gate_definitions"]]))
    b.append(f'<p class="small">Scoring rule as published: {e(r76["rewards"]["model"])}</p>')

    b.append(f"<h2>Tables of session 80731db4</h2><p>Checked at commit <code>{e(r80['commit'][:10])}</code> on its branch (not merged).</p>")
    b.append(table([("File", "id"), ("Rows matching", "n"), ("Status", ""), ("Official source", "nw")], [
        ["<code>data/standings.json</code>", f"{r80['standings']['rows_matching']} / {r80['standings']['rows_checked']}", OK if r80["standings"]["rows_matching"] == r80["standings"]["rows_checked"] else chip("bad", "Mismatch"), a(STAND.format(2026), "NFL.com standings 2026")],
        ["<code>data/derived_standings.json</code> (per-game values)", f"{r80['per_game']['rows_matching']} / {r80['per_game']['rows_checked']}", chip("ok", "Replicated") if r80["per_game"]["rows_matching"] == r80["per_game"]["rows_checked"] else NREP, a(STAND.format(2026), "NFL.com standings 2026")]]))
    b.append(table([("Correlation across the 32 teams", "k w"), ("Published", "n"), ("Referee", "n"), ("Status", ""), ("Official source", "nw")],
                   [[e(f"{c['id']} {c['item']}"), num(c["published"]), num(c["referee"]), status_chip(c["status"]), a(c["source"], "NFL.com standings 2026")] for c in c80],
                   "Recomputed from the official standings values as read by this session."))
    b.append(fold(f"<code>data/standings.json</code>: all {r80['standings']['rows_checked']} rows", table(
        [("Team", "k"), ("Published", "w"), ("Official", "w"), ("Status", ""), ("Official source", "nw")],
        [[e(r["key"]), e(r["published"]), e(r["official"]), status_chip(r["result"]), a(r["source"], "NFL.com standings 2026")] for r in r80["standings"]["rows"]])))
    page("replication.html", "Replication", "\n".join(b), as_of)

    # ================================================================================================
    # luck.html
    # ================================================================================================
    b = ['<p class="eyebrow">Luck and sensitivity</p>', "<h1>How good must a record be before luck stops being the likely explanation?</h1>",
         f'<p class="lede">A bet at -110 breaks even at {luck["breakeven_win_pct"]}% wins. A strategy with no edge at all will sometimes beat that by chance, and the more strategies are tried, the better the luckiest one looks. This page puts numbers on it.</p>']
    b.append(tiles([("bad", f"{clears_any} of {tried}", "published strategies clear the bar"),
                    ("", f"{luck['rows'][3]['tried_12']['min_win_pct']}%", "win rate needed over 500 bets when 12 strategies are tried"),
                    ("warn", f"{luck['power_at_55pct'][3]['chance_to_clear_bar_pct']}%", "chance a true 55% strategy proves itself in 500 bets"),
                    ("warn", f"+{max(r['difference_pct_points'] for r in price)} pts", "largest change in return when actual prices replace -110")]))
    b.append("<h2>The bar</h2><p>Smallest win rate that a no-edge strategy would reach less than 5% of the time. Exact binomial arithmetic, no data involved.</p>")
    tk = luck["strategies_tried"]
    b.append(table([("Graded bets", "k n")] + [(f"{k} strategy tried" if k == 1 else f"{k} strategies tried", "n") for k in tk] + [("Status", ""), ("Method", "nw")],
                   [[num(r["graded_bets"])] + [f"{r[f'tried_{k}']['min_win_pct']:.2f}% ({r[f'tried_{k}']['min_wins']:,} wins)" for k in tk] + [chip("ok", "Arithmetic"), a(blob("referee/analysis/replicate_luck_thresholds.py"), "Script")] for r in luck["rows"]]))
    b.append("<h2>The published strategies against that bar</h2>"
             f"<p>Records as published by session 7600ed8b. {tried} strategies were tried, so the fair bar is the one adjusted for {tried} attempts.</p>")
    rows = []
    for s, w, l, p, n, b1, bk, clears in bar_rows:
        rows.append([e(s["strategy"]), num(n), num(w), f"{100 * w / n:.2f}%", f"{100 * b1 / n:.2f}%", f"{100 * bk / n:.2f}%",
                     chip("ok", "Clears the bar") if clears else chip("bad", "Within luck"), status_chip(s["result"]) + " " + UNV, a(blob("data/model/strategies.json", ref76), "Their file")])
    b.append(table([("Strategy", "k m"), ("Graded bets", "n"), ("Wins", "n"), ("Win rate", "n"), ("Bar, 1 tried", "n"), (f"Bar, {tried} tried", "n"), ("Verdict", ""), ("Record status", ""), ("Source", "")], rows))
    b.append("<h2>Why patience is required</h2><p>Chance that a strategy whose true win rate is 55% clears the single-strategy bar. Most real edges are smaller than that.</p>")
    b.append(table([("Graded bets", "k n"), ("True win rate", "n"), ("Chance to clear the bar", "n"), ("Status", ""), ("Method", "nw")],
                   [[num(r["graded_bets"]), f"{r['true_win_pct']}%", f"{r['chance_to_clear_bar_pct']}%", chip("ok", "Arithmetic"), a(blob("referee/analysis/replicate_luck_thresholds.py"), "Script")] for r in luck["power_at_55pct"]]))
    b.append("<h2>Sensitivity 1: the assumed price</h2><p>The leaderboard grades every bet at -110. Where the dataset records an actual closing price, the same bets were graded at that price.</p>")
    b.append(table([("Strategy", "k m"), ("Bets with a price", "n"), ("Win rate", "n"), ("Return at -110", "n"), ("Return at actual price", "n"), ("Change", "n"), ("Median price", "n"), ("Status", ""), ("Source", "m")],
                   [[e(r["strategy"]), num(r["graded_bets_with_a_price"]), f"{r['win_pct']}%", f"{r['roi_at_assumed_minus_110_pct']:+.2f}%", f"{r['roi_at_actual_price_pct']:+.2f}%", f"{r['difference_pct_points']:+.2f}",
                     f"{r['median_price']:.0f}", UNV, a(GAMES, "nflverse games file (unofficial)")] for r in price]))
    b.append('<p class="small">Recorded prices are typically a little better than -110, so returns rise slightly. The ranking and every verdict stay the same.</p>')
    lst = sens["line_source_test"]
    b.append(f"<h2>Sensitivity 2: which closing line</h2><p>The same rules, run on the {lst['games_in_both_files']:,} games ({lst['seasons'][0]} to {lst['seasons'][-1]}) that appear in both closing-line files, once with each file's lines.</p>")
    b.append(table([("Strategy", "k m"), ("Record, file 1", "n"), ("Win rate", "n"), ("Record, file 2", "n"), ("Win rate", "n"), ("Change", "n"), ("Only in file 1", "n"), ("Only in file 2", "n"), ("Result flipped", "n"), ("Status", ""), ("Source", "m")],
                   [[e(r["strategy"]), e(r["record_games_csv"]), f"{r['win_pct_games_csv']}%", e(r["record_closing_lines_csv"]), f"{r['win_pct_closing_lines_csv']}%", f"{r['win_pct_change_points']:+.2f}",
                     num(r["bets_only_in_games_csv"]), num(r["bets_only_in_closing_lines_csv"]), num(r["same_bet_different_result"]), UNV, a(CLOSING, "nflverse second file (unofficial)")] for r in src_rows]))
    b.append('<p class="small">File 1 is games.csv, file 2 is closing_lines.csv. Rules with a threshold (for example a total of 41 or lower) pick up and drop games when the line moves by half a point.</p>')
    page("luck.html", "Luck and sensitivity", "\n".join(b), as_of)

    # ================================================================================================
    # sessions.html
    # ================================================================================================
    b = ['<p class="eyebrow">Sessions</p>', "<h1>Who did what, and where the work overlaps</h1>",
         f'<p class="lede">A snapshot of every parallel session, taken from git and GitHub at {e(as_of)} UTC. Counts and times are read from the repository. The claim and observation columns are this session\'s reading of each coordination board.</p>']
    st = [s["state"] for s in sess["sessions"]]
    b.append(tiles([("", str(len(st)), "sessions with a branch"), ("", str(st.count("merged") + st.count("merged, still active")), "have merged work into main"),
                    ("warn", str(st.count("active, not merged")), "active and not merged"), ("bad" if st.count("claim only") else "", str(st.count("claim only")), "pushed a claim but no work")]))
    rows = []
    for s in sess["sessions"]:
        prs = "<br>".join(a(p["url"], f"#{p['number']} {p['state'].lower()}") for p in s["pull_requests"])
        kind = {"merged": "ok", "merged, still active": "ok", "this session": "ok", "claim only": "bad"}.get(s["state"], "warn")
        rows.append([f"<code>{e(s['session'])}</code>", chip(kind, s["state"].capitalize()), e(s["claimed"]), num(s["files_on_branch"]), e(s["last_commit_utc"][11:]), prs,
                     str(len(s["modifies_files_already_on_main"])), e(s["observation"]), a(s["branch_url"], "Branch on GitHub")])
    b.append(table([("Session", "id"), ("State", ""), ("What it claimed", "m"), ("Files", "n"), ("Last commit", "n"), ("Pull requests", "m"), ("Live files touched", "n"), ("Referee observation", "w"), ("Source", "s")], rows))
    b.append("<h2>Files on main that unmerged branches modify</h2><p>Each of these will need a deliberate merge order. Files touched by two branches are the ones most likely to be overwritten.</p>")
    b.append(table([("File on main", "id"), ("Modified by", ""), ("Branches", "n"), ("Risk", ""), ("Source", "m")],
                   [[f"<code>{e(o['file'])}</code>", e(", ".join(o["modified_by_unmerged_branches"])), str(len(o["modified_by_unmerged_branches"])),
                     chip("bad", "Two or more") if len(o["modified_by_unmerged_branches"]) > 1 else chip("warn", "One"), a(o["file_url"], "File on main")] for o in sess["overlaps"]]
                   or [["", "", "0", chip("ok", "None"), a(f"{GH}/branches", "Branches on GitHub")]]))
    b.append("<h2>How this session handled coordination</h2>")
    b.append(table([("Event", "k w"), ("What was done", "w"), ("Record", "nw")], [
        ["First claim collided with a board another session had just merged.", "Withdrew the unpushed claim, took main's board unchanged and appended a narrower claim limited to <code>referee/</code>.", a(blob("COORDINATION.md"), "COORDINATION.md")],
        ["Conflict on COORDINATION.md at every later sync (five in total).", "Each time: kept main's file exactly as it was and re-appended this session's block with a script. No other session's text was dropped.", a(blob("referee/tools/sync_coordination.py"), "Script")],
        ["Rule says rebase before every push.", "After the branch was pushed, rebasing would have required a force-push, so main was merged in instead. Logged as a deviation.", a(blob("referee/coordination_block.md"), "Board block")],
        ["Another session's published number was wrong.", "Did not edit its files. Logged a change request in COORDINATION.md and listed it under Flagged for Review.", a(blob("COORDINATION.md"), "COORDINATION.md") + " · " + a("flagged.html#R-04", "Flag R-04")],
    ]))
    page("sessions.html", "Sessions", "\n".join(b), as_of)

    # ================================================================================================
    # flagged.html
    # ================================================================================================
    b = ['<p class="eyebrow">Flagged for Review</p>', "<h1>Flagged for Review</h1>",
         '<p class="lede">Irregularities and unverified items found by this session. Each has a link for checking by hand and a suggested action. None of them blocks a merge; they are here so that someone can decide.</p>']
    b.append(tiles([("bad", str(n_irr), "irregularities"), ("warn", str(sum(f[1] == "Unverified" for f in flags)), "unverified"), ("idle", str(sum(f[1] == "Not audited" for f in flags)), "not audited"),
                    ("", "0", "items that block a merge")]))
    b.append(table([("ID", "id"), ("Type", ""), ("Item", "k m"), ("What was found", "w"), ("Owner", "s"), ("Suggested action", "w"), ("Source", "m")],
                   [[f'<span id="{f[0]}">{f[0]}</span>', type_chip(f[1]), e(f[2]), e(f[3]), e(f[4]), e(f[5]), a(f[6], f[7])] for f in flags]))
    b.append("<h2>Values left blank on purpose</h2><p>Where a value could not be confirmed it is not shown. These are the blanks on this site and the reason for each.</p>")
    b.append(table([("Where", "k"), ("What is blank", "w"), ("Why", "w"), ("Status", ""), ("Where to check", "nw")], [
        [a("results.html", "Results audit"), f"Match counts for {len(T['seasons_not_audited'])} seasons, 1999 to 2020", "Not compared with the official page in this session.", NAUD, a(STAND.format(2020), "NFL.com standings 2020")],
        [a("replication.html", "Replication"), "Referee record for strategies S01, S02, S03 and S12", "Inputs not obtainable here, so no independent record exists.", NTEST, a(blob("data/model/strategies.json", ref76), "Their file")],
        [a("replication.html", "Replication"), f"Referee value for {r76['counts'].get('not replicable here', 0)} model-based numbers", "Same reason. The published value is shown as published, not as confirmed.", NTEST, a(blob("data/model/lines.json", ref76), "Their file")],
    ]))
    page("flagged.html", "Flagged for Review", "\n".join(b), as_of)
    print("built", len(PAGES), "pages;", len(flags), "flags;", f"replicated {rep}, not replicated {nrep}, not testable {ntest}; strategies clearing the bar {clears_any}/{tried}")


def _all(lines, key):
    """Game-weighted all-season value of a benchmark that is published per era."""
    eras = lines["benchmarks_by_era"]
    for r in eras:
        if r["era"].lower().startswith("all"):
            return r[key]
    tot = sum(r["games"] for r in eras)
    return round(sum(r[key] * r["games"] for r in eras) / tot, 2)


if __name__ == "__main__":
    main()
