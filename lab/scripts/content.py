#!/usr/bin/env python3
"""Session 1505ac8e - the written layer: questions, suggestions, decisions, flags.

Everything here is prose about what the data does and does not support. Each row that
asserts a fact carries a source URL to an official page. Where something is unknown, the
cell says so; nothing is filled in to look complete.
"""

from __future__ import annotations

NFL_STANDINGS = "https://www.nfl.com/standings/league/2026/REG"
NFL_INJURIES = "https://www.nfl.com/injuries/"
NFL_SCHEDULE = "https://www.nfl.com/schedules/2026/week10"
NFL_GAMES = "https://www.nfl.com/schedules/2026/by-week/week-1"
NFL_TIEBREAK = "http://www.nfl.com/standings/tiebreakingprocedures"
NFL_DEPTH_404 = "https://www.nfl.com/teams/kansas-city-chiefs/depth-chart"
CHIEFS_DEPTH = "https://www.chiefs.com/team/depth-chart"
NFL_OPERATIONS = "https://operations.nfl.com/gameday/"
NIST_CORR = "https://www.itl.nist.gov/div898/handbook/eda/section3/eda367.htm"
NIST_BOOTSTRAP = "https://www.itl.nist.gov/div898/handbook/eda/section3/eda366.htm"
NJ_DGE = "https://www.nj.gov/oag/ge/"
SPORTRADAR_DEPTH = ("https://developer.sportradar.com/football/reference/"
                    "nfl-weekly-depth-charts")
GENIUS_NFL = ("https://investors.geniussports.com/news/announcements/"
              "announcements-details/2023/National-Football-League-Extends-Strategic-"
              "Partnership-with-Genius-Sports-as-Exclusive-Official-NFL-Data-and-Watch--"
              "Bet-Distribution-Partner/default.aspx")
NFLVERSE = "https://github.com/nflverse/nflverse-data"
GH_PAGES = "https://docs.github.com/en/pages"
SRS_REF = "https://www.sports-reference.com/blog/2023/08/sports-reference-srs-ratings/"

# ---------------------------------------------------------------------------
# Questions: what we know, what we do not, what it blocks, how to find out
# ---------------------------------------------------------------------------

QUESTIONS = [
    dict(id="Q01", group="Prices and the market",
         question="Is there any official source of NFL betting prices?",
         know=("No. nfl.com publishes standings, schedules, injuries and stats but no odds. "
               "The NFL's authorised route for betting data is its commercial partnership, "
               "which is not a public feed."),
         know_src=[("NFL.com standings", NFL_STANDINGS),
                   ("Genius Sports - NFL exclusive data partnership", GENIUS_NFL)],
         unknown=("Every price: point spread prices, moneylines, totals prices, and all "
                  "player-prop prices."),
         blocks=("Any statement about profit. Gate G4 (beat the break-even vig), every edge "
                 "number, and the whole player-prop track."),
         discover=("S-01: license a book or official feed; or S-02: log prices yourself at a "
                   "fixed time each week into a versioned file. Until then the lab measures "
                   "skill against its own line, which is an accuracy test, not a profit test."),
         status="OPEN - BLOCKING"),
    dict(id="Q02", group="Prices and the market",
         question="Do historical closing lines exist anywhere in this repository?",
         know=("Only for Week 10, and only from a community mirror of unknown provenance. "
               "No historical series is verified in this repo."),
         know_src=[("nflverse community data mirror", NFLVERSE)],
         unknown="A verified week-by-week closing-line series for 2026 (or any season).",
         blocks="Rule S7 (model-vs-market disagreement) cannot be scored at all.",
         discover=("S-02 (start a dated price log now) or S-03 (buy a historical odds file). "
                   "Both are listed on the Suggestions page with costs."),
         status="OPEN - BLOCKING"),
    dict(id="Q03", group="Injuries and depth",
         question="When does the official injury report carry game statuses?",
         know=("As of the 2026-11-12 retrieval, 6 of 279 rows had a game status (5 Out, "
               "1 Questionable) and the same 6 rows were the only ones with a body part "
               "filled in. 279 of 279 rows had a practice status."),
         know_src=[("Official NFL injury report, Week 10", NFL_INJURIES)],
         unknown=("The league's written rule for when clubs must file game designations. "
                  "Earlier sessions tried three official URLs and got 404s."),
         blocks=("Any availability signal keyed on Out/Questionable. The lab falls back to "
                 "practice participation, which is a weaker proxy."),
         discover=("S-06: re-scrape the official report on Friday and Sunday and record what "
                   "changes; S-07: ask the league or read the Game Operations Manual for the "
                   "filing deadline and cite the exact clause."),
         status="OPEN"),
    dict(id="Q04", group="Injuries and depth",
         question="Why do 76 of 279 injury rows not appear on that club's own depth chart?",
         know=("203 of 279 injury rows match a player on the club's official depth chart. "
               "76 do not. Two official sources disagree about who is on which club."),
         know_src=[("Official NFL injury report, Week 10", NFL_INJURIES),
                   ("Official club depth charts (31 of 32 clubs)", CHIEFS_DEPTH)],
         unknown="Which of the two official sources is authoritative for a given player.",
         blocks=("Treating the injury report as a club-accurate input. The lab only scores a "
                 "player when both sources agree, which is conservative by design."),
         discover=("S-08: add the official club roster pages as a third source and decide by "
                   "two-out-of-three; S-09: use the league's credentialed Sportradar depth "
                   "chart feed, which is the sanctioned source."),
         status="OPEN - needs a decision"),
    dict(id="Q05", group="Injuries and depth",
         question="Does an official depth chart exist at the league level?",
         know=("No. https://www.nfl.com/teams/<club>/depth-chart returns a soft 404 "
               "('404 - Flag on the Play.'), verified again on 2026-11-12. The 32 club sites "
               "do publish one, and 31 of 32 are machine-readable."),
         know_src=[("nfl.com depth chart (404)", NFL_DEPTH_404),
                   ("chiefs.com official depth chart", CHIEFS_DEPTH),
                   ("Sportradar NFL weekly depth charts (credentialed)", SPORTRADAR_DEPTH)],
         unknown=("Nothing material - the gap is now closed for 31 clubs. Houston's chart is "
                  "rendered in the browser and is not present in the page source."),
         blocks="Nothing today. It blocked this requirement entirely before this session.",
         discover=("S-09 for the league-sanctioned feed, or S-10 (a headless-browser scrape) "
                   "for the one club that needs it."),
         status="ANSWERED - residual gap: 1 club"),
    dict(id="Q06", group="Model and own lines",
         question="How much history does the model have?",
         know=("One season. 136 completed 2026 games are transcribed and verified against the "
               "official standings (32 clubs x W, L, T, PF, PA, 160 of 160 cells match). "
               "Earlier seasons exist only in an unverified community mirror."),
         know_src=[("Official 2026 standings", NFL_STANDINGS),
                   ("Official 2026 game results", NFL_GAMES)],
         unknown="Whether any 2026 result survives in a second, independent season.",
         blocks=("Gate G6 (multi-season stability). No rule can be certified without it, "
                 "whatever it does in 2026."),
         discover=("S-04: transcribe 2024 and 2025 results from the official schedule pages "
                   "the same way 2026 was done. Slow but fully verifiable."),
         status="OPEN - BLOCKING"),
    dict(id="Q07", group="Model and own lines",
         question="Are my lines actually better than doing very little?",
         know=("Walk-forward over weeks 4-9: mean absolute spread error 10.10 points, against "
               "10.95 for 'always predict the home-field number' and 10.92 for 'always "
               "predict zero'. The model wins, but by under a point."),
         know_src=[("Official 2026 game results", NFL_GAMES)],
         unknown=("Whether that margin is stable. It is measured on 6 weeks of one season."),
         blocks="Any claim that the own-line pipeline has an edge over a naive baseline.",
         discover=("S-04 (more seasons) and S-11 (add weather, travel and rest to the model "
                   "and re-run the same walk-forward)."),
         status="PARTIALLY ANSWERED"),
    dict(id="Q08", group="Model and own lines",
         question="Is the home-field term real in this data?",
         know=("It is fitted, not assumed, and published for every fold. It is small relative "
               "to the 13-point residual spread."),
         know_src=[("Official 2026 game results", NFL_GAMES)],
         unknown="Nothing. This one is answered by the fit.",
         blocks="Nothing.",
         discover="None needed.",
         status="ANSWERED"),
    dict(id="Q09", group="Strategy validation",
         question="Can any rule be certified as skill rather than luck today?",
         know=("No. Seven rules were graded on weeks 4-9. All seven fail at least one gate. "
               "The nearest is S1 (rest edge): 26 bets, 73% wins against my line, permutation "
               "p = 0.0005 - but it fails the 30-bet minimum and cannot be checked in a second "
               "season."),
         know_src=[("NIST/SEMATECH - correlation and resampling", NIST_CORR),
                   ("NIST/SEMATECH - bootstrap", NIST_BOOTSTRAP)],
         unknown="Everything that would let a rule pass: more bets, and more seasons.",
         blocks="The leaderboard has no certified entries, by design.",
         discover=("S-04 (seasons) first; S-05 (lower the sample floor only after the seasons "
                   "exist, never before)."),
         status="ANSWERED - the answer is no, and that is the useful answer"),
    dict(id="Q10", group="Strategy validation",
         question="What is the parlay correlation actually worth?",
         know=("Measured, not assumed. Every pair of graded rules has a Pearson r over the "
               "games both rules bet, with a Fisher z interval. The least-correlated pair is "
               "used for the two-leg parlay maths."),
         know_src=[("NIST/SEMATECH - correlation", NIST_CORR)],
         unknown=("The correlation of bet OUTCOMES against real prices, because there are no "
                  "prices. What is published is the correlation of edges against my line."),
         blocks="Pricing a parlay. The correlation itself is fine.",
         discover="S-01 or S-02: prices first, then re-run the same correlation code.",
         status="PARTIALLY ANSWERED"),
    dict(id="Q11", group="Competition and rewards",
         question="Can the leaderboard award anything of value?",
         know=("Not without legal review, which has not happened. The board therefore awards "
               "paper points only and says so on the page."),
         know_src=[("New Jersey Division of Gaming Enforcement", NJ_DGE)],
         unknown="Whether the operator wants a real prize, and in which jurisdiction.",
         blocks="Any reward with monetary value.",
         discover=("S-12: decide the reward question explicitly, and if real prizes are "
                   "wanted, get counsel before a single point is awarded."),
         status="OPEN - needs a decision"),
    dict(id="Q12", group="Site and governance",
         question="There are four site generations in this repository. Which is the site?",
         know=("Root index.html + pages/ (session 7600ed8b lineage), docs/ (87deb7ab), "
               "verified-lab/ (a2cea255), dashboard/ (6a232e79 / 3d5c5e2d) and lab/ (this "
               "session). All five are live and all five are reachable from the published "
               "Pages site."),
         know_src=[("GitHub Pages documentation", GH_PAGES)],
         unknown="Which one the operator wants to keep.",
         blocks="A single clean landing page. Right now a visitor has to know which door to use.",
         discover=("S-13: pick one canonical root and reduce the others to an archive link. "
                   "Three options with costs are on the Suggestions page."),
         status="OPEN - needs a decision"),
    dict(id="Q13", group="Site and governance",
         question="Who may edit the shared outputs?",
         know=("Two CI jobs regenerate index.html and pages/ from different generators "
               "(tools/build.py in verify.yml, scripts/verified/build_site.py in pages.yml). "
               "Any hand edit to those files can be overwritten by the next run."),
         know_src=[("GitHub Pages documentation", GH_PAGES)],
         unknown="Which generator is authoritative.",
         blocks="Safe editing of the root site.",
         discover="S-14: retire one generator, or make the second write to a different directory.",
         status="OPEN"),
    dict(id="Q14", group="Data and coverage",
         question="Is the committed injury snapshot the current one?",
         know=("No. The repository holds 254 Week-10 injury rows; the live official page now "
               "carries 279. The data is a snapshot, not a live feed."),
         know_src=[("Official NFL injury report, Week 10", NFL_INJURIES)],
         unknown="Nothing - this is a staleness observation, not a mystery.",
         blocks="Treating any committed injury file as current.",
         discover=("S-06: schedule the scraper daily during the week so the gap closes on its "
                   "own instead of widening."),
         status="ANSWERED - flagged as stale"),
    dict(id="Q15", group="Data and coverage",
         question="Do the previously published league-balance figures still hold?",
         know=("No. An earlier session published W = L = 134, T = 4, PF = PA = 6,267. The "
               "live official page gives W = L = 135, T = 2, PF = PA = 6,246, and the 136 "
               "verified game results reproduce that exactly."),
         know_src=[("Official 2026 standings", NFL_STANDINGS),
                   ("Official 2026 game results", NFL_GAMES)],
         unknown="Nothing. The current figures are verified two ways.",
         blocks="Reusing the older figures as a checksum.",
         discover="S-15: recompute the league-balance check in CI on every refresh.",
         status="ANSWERED - older figures superseded"),
    dict(id="Q16", group="Data and coverage",
         question="Does nfl.com still contradict its own arithmetic?",
         know=("No, not on the 2026-11-12 retrieval. An earlier session flagged three cells "
               "(WAS non_conf, IND div, PHI div). All 32 rows now satisfy every identity "
               "tested: PCT, NET, HOME+ROAD, CONF+NON-CONF, DIV<=CONF, and the division and "
               "conference percentages."),
         know_src=[("Official 2026 standings", NFL_STANDINGS),
                   ("Official tie-breaking procedures", NFL_TIEBREAK)],
         unknown=("Whether the earlier flags were transcription errors or a page that has since "
                  "been corrected. Both are possible; the files are preserved either way."),
         blocks="Nothing today. It does mean the three flags should be re-checked, not trusted.",
         discover="S-15: run the identity checks automatically on every refresh.",
         status="ANSWERED - earlier flags no longer reproduce"),
    dict(id="Q17", group="Data and coverage",
         question="Why do three sessions spell club abbreviations three ways?",
         know=("nfl.com uses LA and AZ; one committed file uses LAR; another uses ARI. After "
               "aliasing, all 32 clubs agree across every file compared."),
         know_src=[("Official 2026 standings", NFL_STANDINGS)],
         unknown="Nothing - the mapping is complete and published.",
         blocks="Joining files without the alias table.",
         discover="S-16: adopt one official code set and make the build fail on any other.",
         status="ANSWERED - handled by an alias table"),
    dict(id="Q18", group="Model and own lines",
         question="Should the model know about injuries and rest?",
         know=("It does not. Ratings are built from scores only. That is deliberate: it keeps "
               "the walk-forward clean and it is why the rest edge shows up as a signal "
               "rather than being swallowed by the model."),
         know_src=[("Official 2026 game results", NFL_GAMES)],
         unknown="How much error would disappear if availability were added.",
         blocks="Nothing. It is a design choice, and the choice is published.",
         discover=("S-11: add rest, and then availability, as explicit regressors and compare "
                   "the walk-forward error against the current model."),
         status="ANSWERED - deliberate"),
    dict(id="Q19", group="Strategy validation",
         question="Is the outcome measure circular?",
         know=("Partly, and it is labelled as such. Edge = actual margin minus MY predicted "
               "margin. Rules that select on my prediction are therefore self-referential; "
               "gate G10 exists to catch exactly that, and rule S8 fails it on purpose."),
         know_src=[("NIST/SEMATECH - bootstrap", NIST_BOOTSTRAP)],
         unknown="Nothing. This is disclosed rather than hidden.",
         blocks="Certifying any rule whose selector uses the model's own number.",
         discover=("S-01: with real prices the outcome becomes profit, and the circularity "
                   "disappears."),
         status="ANSWERED - disclosed"),
    dict(id="Q20", group="Data and coverage",
         question="Are the Week 10 games in the standings yet?",
         know=("No. Washington and the Giants are both listed at 8 games played, and the "
               "Thursday night game between them had not kicked off when the page was "
               "retrieved. The standings cover weeks 1-9."),
         know_src=[("Official 2026 standings", NFL_STANDINGS),
                   ("Official Week 10 schedule", NFL_SCHEDULE)],
         unknown="Nothing.",
         blocks="Nothing, as long as the cut-off is stated. It is stated on every page.",
         discover="None needed.",
         status="ANSWERED"),
]

# ---------------------------------------------------------------------------
# Suggestions: each one offers paths and waits for a decision. Nothing here is
# implemented in this session, by design.
# ---------------------------------------------------------------------------

SUGGESTIONS = [
    dict(id="S-01", title="License or log real prices",
         category="Data acquisition", priority="Critical",
         problem=("Nothing about profit can be measured, and gates G4 and the whole prop "
                  "track are blocked, because there is not a single verified price in the "
                  "repository."),
         options=[
             dict(label="A. License an odds feed",
                  detail="A commercial NFL odds or official-data licence. Complete history, "
                         "clean licensing, costs money and may restrict redistribution.",
                  cost="$$$", effort="Low", risk="Contract terms"),
             dict(label="B. Log prices yourself",
                  detail="Capture spreads, totals and prices at a fixed clock time each week "
                         "into a dated, versioned file. Free and fully auditable; history only "
                         "starts the day you begin.",
                  cost="$", effort="Medium", risk="Gaps if a week is missed"),
             dict(label="C. Do nothing",
                  detail="Keep the lab as an accuracy exercise and say plainly that no "
                         "profitability claim is made.",
                  cost="$0", effort="None", risk="The leaderboard can never certify anything"),
         ],
         recommendation="B now, A later if the project proves out. B costs nothing and starts "
                        "the clock on the one asset that cannot be bought retroactively.",
         unblocks="G4, every edge number, the prop track, and rules S7.",
         decision=dict(status="PROPOSED", by="", date="",
                       note="No price work was started this session.")),
    dict(id="S-02", title="Start a dated closing-line log",
         category="Data acquisition", priority="Critical",
         problem="There is no verified closing-line history, so rule S7 cannot be scored.",
         options=[
             dict(label="A. Log every market every week",
                  detail="Spread, total, moneyline and every prop, captured at a fixed time.",
                  cost="$", effort="High", risk="Storage grows fast"),
             dict(label="B. Log spreads and totals only",
                  detail="Enough to grade S1-S8; prop combos stay blocked for now.",
                  cost="$", effort="Medium", risk="Prop track stays empty"),
         ],
         recommendation="B. It unblocks most of the board for a fraction of the work.",
         unblocks="S7 and any future market-comparison rule.",
         decision=dict(status="PROPOSED", by="", date="", note="")),
    dict(id="S-03", title="Buy a historical odds file",
         category="Data acquisition", priority="Medium",
         problem="If the board must be graded historically, self-logging cannot reach back.",
         options=[
             dict(label="A. Purchase a back-file",
                  detail="One-off purchase of historical NFL closing lines.",
                  cost="$$", effort="Low", risk="Provenance must still be checked"),
             dict(label="B. Reconstruct from public archives",
                  detail="Slower, patchier, and harder to verify.",
                  cost="$", effort="High", risk="Coverage gaps"),
         ],
         recommendation="Only after S-01 is decided. Buying history before deciding the "
                        "licence model risks paying twice.",
         unblocks="Historical grading of every rule.",
         decision=dict(status="PROPOSED", by="", date="", note="")),
    dict(id="S-04", title="Transcribe two more seasons from official pages",
         category="Data acquisition", priority="Critical",
         problem=("Gate G6 needs a second season and there is only one. Nothing can be "
                  "certified until this exists."),
         options=[
             dict(label="A. Transcribe 2024 and 2025 the way 2026 was done",
                  detail="Game results read off the official schedule pages and reconciled "
                         "against the official standings. Fully verifiable, slow.",
                  cost="$0", effort="High", risk="Transcription error, mitigated by the "
                                                 "standings reconciliation"),
             dict(label="B. Use the community mirror unverified",
                  detail="Fast, but the whole point of this project is that unverified inputs "
                         "are not trusted.",
                  cost="$0", effort="Low", risk="Provenance"),
         ],
         recommendation="A. The reconciliation against official standings is what makes the "
                        "2026 data trustworthy, and the same trick works for any season.",
         unblocks="G6, and with it any chance of a certified rule.",
         decision=dict(status="PROPOSED", by="", date="", note="")),
    dict(id="S-05", title="Do not lower the 30-bet floor yet",
         category="Validation", priority="High",
         problem=("S1 looks strong (26 bets, 73%, permutation p = 0.0005) and it is tempting "
                  "to lower the sample floor to 20 so it passes."),
         options=[
             dict(label="A. Keep 30 and wait for more seasons",
                  detail="The floor exists to stop one lucky season from certifying a rule.",
                  cost="$0", effort="None", risk="Board stays empty for now"),
             dict(label="B. Lower to 20",
                  detail="S1 would pass G1, and would still fail G6, so it still could not be "
                         "certified - but the board would look busier.",
                  cost="$0", effort="Low", risk="Certifies noise"),
         ],
         recommendation="A. Lowering a gate to make a result pass is the exact failure mode "
                        "the gates were built to prevent.",
         unblocks="Nothing - it protects the board instead.",
         decision=dict(status="PROPOSED", by="", date="", note="")),
    dict(id="S-06", title="Re-scrape the injury report on a weekday schedule",
         category="Data acquisition", priority="High",
         problem=("One club's report was missing at scrape time in an earlier session and the "
                  "committed snapshot is 25 rows behind the live page."),
         options=[
             dict(label="A. Daily during the week, hourly on Friday and Sunday",
                  detail="Closes the staleness gap and captures when game statuses appear.",
                  cost="$0", effort="Medium", risk="More commits"),
             dict(label="B. Weekly only",
                  detail="Cheaper, but the report is filed late in the week, so a weekly "
                         "scrape can easily land on an empty page.",
                  cost="$0", effort="Low", risk="Mostly-empty snapshots"),
         ],
         recommendation="A. It also answers Q03 empirically - capture when the statuses land.",
         unblocks="A usable availability signal, and an answer to Q03.",
         decision=dict(status="PROPOSED", by="", date="", note="")),
    dict(id="S-07", title="Find the written rule for game-status filing",
         category="Injuries and depth", priority="Medium",
         problem="Three official URLs 404'd for earlier sessions; the deadline is unknown.",
         options=[
             dict(label="A. Read the Game Operations Manual",
                  detail="Search the NFL Football Operations library for the injury-report "
                         "section and cite the clause.",
                  cost="$0", effort="Medium", risk="May be behind a PDF"),
             dict(label="B. Infer it empirically",
                  detail="Scrape hourly for a week and record when designations appear.",
                  cost="$0", effort="Medium", risk="Describes behaviour, not the rule"),
         ],
         recommendation="Do both. The manual gives the rule; the scrape proves it is followed.",
         unblocks="Confidence in the availability signal's timing.",
         decision=dict(status="PROPOSED", by="", date="", note="")),
    dict(id="S-08", title="Add club rosters as a third source for player identity",
         category="Injuries and depth", priority="High",
         problem="76 injury rows name players who are not on that club's own depth chart.",
         options=[
             dict(label="A. Two-out-of-three across report, depth chart and roster",
                  detail="Resolve each disagreement by majority and publish the dissenters.",
                  cost="$0", effort="Medium", risk="Still two officials disagreeing"),
             dict(label="B. Trust the depth chart only",
                  detail="Conservative: score only players the club itself lists.",
                  cost="$0", effort="Low", risk="Drops real injuries"),
         ],
         recommendation="A, with B as the fallback until the roster pages are collected.",
         unblocks="Trust in the availability model's inputs.",
         decision=dict(status="PROPOSED", by="", date="", note="Currently running B.")),
    dict(id="S-09", title="Use the league's sanctioned depth-chart feed",
         category="Injuries and depth", priority="Medium",
         problem="Club charts are self-published, labelled 'Unofficial', and differ in format.",
         options=[
             dict(label="A. Credentialed Sportradar weekly depth charts",
                  detail="The league's official data partner; consistent format, authorised "
                         "source, requires credentials and probably payment.",
                  cost="$$", effort="Low", risk="Licence terms"),
             dict(label="B. Keep scraping the 32 club sites",
                  detail="Free, official, and works for 31 of 32 today.",
                  cost="$0", effort="Medium", risk="Format drift"),
         ],
         recommendation="B for now, A if availability becomes a scored input rather than a "
                        "displayed one.",
         unblocks="A league-authoritative depth chart.",
         decision=dict(status="PROPOSED", by="", date="", note="Currently running B.")),
    dict(id="S-10", title="Scrape the one club whose chart needs a browser",
         category="Injuries and depth", priority="Low",
         problem="Houston's depth chart is rendered client-side; the page source has no table.",
         options=[
             dict(label="A. Headless browser in CI",
                  detail="Render the page, then parse. Adds a heavy dependency to the workflow.",
                  cost="$", effort="Medium", risk="Slow, fragile"),
             dict(label="B. Leave it blank and flag it",
                  detail="One club out of 32, clearly marked on the page.",
                  cost="$0", effort="None", risk="Incomplete coverage"),
         ],
         recommendation="B for now. Revisit when the club count matters to a scored signal.",
         unblocks="Full 32-club coverage.",
         decision=dict(status="PROPOSED", by="", date="", note="Currently running B.")),
    dict(id="S-11", title="Add rest, travel and weather to the ratings",
         category="Modelling", priority="Medium",
         problem=("The model reads scores only, and the single strongest signal found (rest) "
                  "is therefore left on the table."),
         options=[
             dict(label="A. Add rest first",
                  detail="Rest is derivable from official game dates, so it costs nothing and "
                         "is fully verifiable.",
                  cost="$0", effort="Low", risk="Overfitting on one season"),
             dict(label="B. Add travel and weather too",
                  detail="Needs non-NFL sources (distances, forecasts) and a provenance policy "
                         "for them.",
                  cost="$", effort="High", risk="Provenance"),
         ],
         recommendation="A, measured against the existing walk-forward. Only then consider B.",
         unblocks="A lower error and a sharper read on whether the rest edge is real.",
         decision=dict(status="PROPOSED", by="", date="", note="")),
    dict(id="S-12", title="Decide the rewards question",
         category="Competition", priority="High",
         problem="The brief asks for rewards; anything of value needs legal review.",
         options=[
             dict(label="A. Paper points only",
                  detail="What runs today. No legal exposure, no prize.",
                  cost="$0", effort="None", risk="Lower motivation"),
             dict(label="B. Real prizes after counsel",
                  detail="Get advice first, then offer prizes in permitted jurisdictions.",
                  cost="$$$", effort="High", risk="Regulatory"),
         ],
         recommendation="A until someone with authority asks for B in writing.",
         unblocks="The competition's reward tier.",
         decision=dict(status="PROPOSED", by="", date="", note="Running A.")),
    dict(id="S-13", title="Pick one canonical site root",
         category="Site and governance", priority="High",
         problem="Four site generations are live; a visitor has to guess which door to use.",
         options=[
             dict(label="A. Make lab/ the root",
                  detail="Move this site to the top and reduce the other three to an archive "
                         "page. Cleanest result, touches other sessions' files.",
                  cost="$0", effort="Medium", risk="Cross-session change"),
             dict(label="B. Keep the root, make lab/ a sub-site",
                  detail="Zero disruption; the landing page still points four ways.",
                  cost="$0", effort="Low", risk="Ambiguity persists"),
             dict(label="C. Publish a site index at the root only",
                  detail="One page that names and links all four generations honestly.",
                  cost="$0", effort="Low", risk="An extra click"),
         ],
         recommendation="C now, A when the other sessions are finished. C is honest and costs "
                        "nothing; A is the right end state but should not be done unilaterally. "
                        "A sixth generation would make this worse - that is the argument for "
                        "deciding it soon.",
         unblocks="A single clean landing page.",
         decision=dict(status="PROPOSED", by="", date="", note="Running C: lab/ links all four.")),
    dict(id="S-14", title="Retire one of the two page generators",
         category="Site and governance", priority="Medium",
         problem="Two CI jobs regenerate index.html and pages/ from different generators.",
         options=[
             dict(label="A. Keep one, delete the other",
                  detail="Needs an owner for the surviving generator.",
                  cost="$0", effort="Medium", risk="Cross-session change"),
             dict(label="B. Make the second write elsewhere",
                  detail="Both keep running; they stop fighting over the same files.",
                  cost="$0", effort="Low", risk="Two similar sites"),
         ],
         recommendation="B as the safe step; A once there is one owner.",
         unblocks="Safe editing of the root site.",
         decision=dict(status="PROPOSED", by="", date="", note="")),
    dict(id="S-15", title="Run the integrity checks in CI on every refresh",
         category="Verification", priority="High",
         problem=("Two published figures (league balance, and three 'nfl.com contradicts "
                  "itself' cells) went stale without anything noticing."),
         options=[
             dict(label="A. Add the checks to the refresh workflow",
                  detail="Recompute every identity and fail loudly on any mismatch.",
                  cost="$0", effort="Low", risk="None"),
             dict(label="B. Check on commit only",
                  detail="Catches less; the page can change without a commit.",
                  cost="$0", effort="Low", risk="Silent drift"),
         ],
         recommendation="A. These checks already exist in this session's verifier; wiring them "
                        "up is the only work.",
         unblocks="Automatic detection of stale or self-contradictory official data.",
         decision=dict(status="PROPOSED", by="", date="", note="")),
    dict(id="S-16", title="Adopt one club code set and enforce it",
         category="Site and governance", priority="Low",
         problem="Three spellings (LA/LAR, AZ/ARI) across sessions force alias handling.",
         options=[
             dict(label="A. Enforce the nfl.com codes in the build",
                  detail="Fail the build on any other spelling, keep the alias table for reads.",
                  cost="$0", effort="Low", risk="Touches other sessions' files"),
             dict(label="B. Keep the alias table",
                  detail="Works today; a new spelling would slip through silently.",
                  cost="$0", effort="None", risk="Silent drift"),
         ],
         recommendation="B now, A when one owner controls the whole data layer.",
         unblocks="Joins without an alias table.",
         decision=dict(status="PROPOSED", by="", date="", note="Running B.")),
]

DECISION_RECORDS = [
    dict(id="D-1505-01", title="Where this session's site lives",
         decision=("Built in a new lab/ directory rather than editing the existing root "
                   "index.html."),
         rationale=("Two CI jobs already regenerate the root pages from different generators, "
                    "so a hand-built fifth generation there would be overwritten. lab/ is "
                    "additive and destroys nothing."),
         consequence="Five site generations are now live; see suggestion S-13.",
         status="DECIDED - reversible"),
    dict(id="D-1505-02", title="No suggestion is implemented in this session",
         decision="Every suggestion is published as PROPOSED with options and a recommendation.",
         rationale=("The brief asks for a review step where the best path is chosen before "
                    "anything changes. Implementing a suggestion would remove that choice."),
         consequence="The board is empty of decisions and full of choices, on purpose.",
         status="DECIDED"),
    dict(id="D-1505-03", title="Unverifiable values stay blank",
         decision="Market lines, edges, prop prices and any unconfirmed cell render as a "
                  "labelled blank.",
         rationale="The brief forbids inferring or filling values.",
         consequence="Several tables have visibly empty columns. That is the point.",
         status="DECIDED"),
    dict(id="D-1505-04", title="Depth charts come from club sites, not nfl.com",
         decision="Scrape the 32 official club sites; nfl.com publishes no depth chart.",
         rationale="Verified 404 on nfl.com; verified working on 31 of 32 club sites.",
         consequence=("The clubs label their own charts 'Unofficial', and that label is "
                      "published with the data."),
         status="DECIDED - reversible"),
]

# ---------------------------------------------------------------------------
# Flags: everything this session found that a reviewer should look at
# ---------------------------------------------------------------------------

FLAGS = [
    dict(id="NFL1-01", severity="Critical", area="Prices",
         summary="No official or book betting prices exist in this repository.",
         detail=("Every edge, every ROI figure and the whole player-prop track are blank "
                 "because there is no price to compute them from. Gates G4 and the prop track "
                 "are blocked. The NFL's authorised betting-data route is a commercial "
                 "partnership, not a public feed."),
         sources=[("Genius Sports - NFL exclusive data partnership", GENIUS_NFL),
                  ("New Jersey Division of Gaming Enforcement", NJ_DGE)],
         status="needs review"),
    dict(id="NFL1-02", severity="High", area="Depth charts",
         summary="nfl.com publishes no depth chart; club sites do.",
         detail=("https://www.nfl.com/teams/kansas-city-chiefs/depth-chart returns a soft 404 "
                 "('404 - Flag on the Play.'), re-verified 2026-11-12. An earlier session "
                 "recorded this as blocking (flag F-001). The 32 official club sites do "
                 "publish one, and 31 of 32 were collected."),
         sources=[("nfl.com depth chart (404)", NFL_DEPTH_404),
                  ("chiefs.com official depth chart", CHIEFS_DEPTH)],
         status="resolved for 31 clubs"),
    dict(id="NFL1-03", severity="Medium", area="Depth charts",
         summary="Houston's depth chart cannot be scraped; it is rendered in the browser.",
         detail=("The page title confirms a depth chart exists, but no table is present in the "
                 "server HTML. Recorded as unavailable rather than filled from elsewhere. "
                 "1 of 32 clubs."),
         sources=[("houstontexans.com depth chart",
                   "https://www.houstontexans.com/team/depth-chart")],
         status="needs review"),
    dict(id="NFL1-04", severity="Medium", area="Depth charts",
         summary="The clubs themselves label these charts 'Unofficial'.",
         detail=("chiefs.com's page title is literally 'Kansas City Chiefs Unofficial Depth "
                 "Chart' and packers.com prints 'Unofficial, Nov. 10, 2026'. The label is the "
                 "clubs' own caveat and is carried on the site, not hidden."),
         sources=[("chiefs.com official depth chart", CHIEFS_DEPTH),
                  ("packers.com official depth chart",
                   "https://www.packers.com/team/depth-chart")],
         status="needs review"),
    dict(id="NFL1-05", severity="High", area="Injuries",
         summary="Only 6 of 279 injury rows carry a game status.",
         detail=("5 Out and 1 Questionable as of the 2026-11-12 retrieval; the other 273 are "
                 "blank. Game designations are filed later in the week. Any availability "
                 "signal keyed on Out/Questionable is therefore near-empty until then."),
         sources=[("Official NFL injury report, Week 10", NFL_INJURIES)],
         status="needs review"),
    dict(id="NFL1-06", severity="Medium", area="Injuries",
         summary="Only 6 of 279 injury rows carry a body part - the same 6.",
         detail=("The Injuries column is empty on 273 rows. It is filled for exactly the rows "
                 "that have a game status, which suggests the two columns are filed together."),
         sources=[("Official NFL injury report, Week 10", NFL_INJURIES)],
         status="needs review"),
    dict(id="NFL1-07", severity="High", area="Injuries",
         summary="76 of 279 injury rows do not appear on the club's own depth chart.",
         detail=("203 rows match a player listed at a matching position on that club's "
                 "official depth chart. 76 do not. Two official sources disagree about club "
                 "membership. The lab scores only the 203 that agree, which is conservative."),
         sources=[("Official NFL injury report, Week 10", NFL_INJURIES),
                  ("Official club depth charts (31 clubs)", CHIEFS_DEPTH)],
         status="needs review"),
    dict(id="NFL1-08", severity="High", area="Repository state",
         summary="The committed injury snapshot is 25 rows behind the live official page.",
         detail=("The repository holds 254 Week-10 injury rows; the live page carried 279 at "
                 "retrieval. Committed injury data is a snapshot, not a feed."),
         sources=[("Official NFL injury report, Week 10", NFL_INJURIES)],
         status="needs review"),
    dict(id="NFL1-09", severity="High", area="Repository state",
         summary="A previously published league-balance figure no longer matches the official page.",
         detail=("An earlier session published W = L = 134, T = 4, PF = PA = 6,267. The live "
                 "official page gives W = L = 135, T = 2, PF = PA = 6,246, and the 136 "
                 "verified game results reproduce that exactly for all 32 clubs."),
         sources=[("Official 2026 standings", NFL_STANDINGS),
                  ("Official 2026 game results", NFL_GAMES)],
         status="needs review"),
    dict(id="NFL1-10", severity="Medium", area="Repository state",
         summary="Three 'nfl.com contradicts its own arithmetic' flags no longer reproduce.",
         detail=("WAS non_conf, IND div and PHI div were published as self-contradictory. On "
                 "the 2026-11-12 retrieval all 32 rows satisfy every identity tested. Either "
                 "the page was corrected or the earlier transcription was wrong; both are "
                 "possible and the record is preserved either way."),
         sources=[("Official 2026 standings", NFL_STANDINGS)],
         status="needs review"),
    dict(id="NFL1-11", severity="Low", area="Repository state",
         summary="Three spellings of two club codes across sessions.",
         detail=("nfl.com uses LA and AZ; a committed file uses LAR; a model artifact uses "
                 "ARI. An alias table reconciles them and all 32 clubs then agree."),
         sources=[("Official 2026 standings", NFL_STANDINGS)],
         status="handled"),
    dict(id="NFL1-12", severity="High", area="Validation",
         summary="No rule can be certified: one season and no prices.",
         detail=("Seven rules were graded on weeks 4-9 of 2026. All seven fail at least one "
                 "gate. G4 needs prices, G6 needs a second season, and both are blocked. The "
                 "nearest miss is S1 (rest edge): 26 bets, 73% against my line, permutation "
                 "p = 0.0005, failing only the 30-bet minimum and the multi-season check."),
         sources=[("Official 2026 game results", NFL_GAMES),
                  ("NIST/SEMATECH - bootstrap", NIST_BOOTSTRAP)],
         status="needs review"),
    dict(id="NFL1-13", severity="Medium", area="Validation",
         summary="The outcome measure is partly circular, and one rule demonstrates it.",
         detail=("Edge is measured against my own predicted margin, so any rule that selects "
                 "on that number is self-referential. Gate G10 catches it; rule S8 exists "
                 "purely to prove the gate fires, and it does."),
         sources=[("NIST/SEMATECH - bootstrap", NIST_BOOTSTRAP)],
         status="disclosed by design"),
    dict(id="NFL1-14", severity="Medium", area="Modelling",
         summary="Practice-participation weights are this project's assumption, not an NFL rule.",
         detail=("DNP 0.5 and Limited 0.2, scaled by depth rank. They are published next to "
                 "the scores they produce so a reviewer can change them."),
         sources=[("Official NFL injury report, Week 10", NFL_INJURIES)],
         status="needs review"),
    dict(id="NFL1-15", severity="High", area="Competition",
         summary="Rewards of value need legal review that has not happened.",
         detail="The leaderboard awards paper points only and says so on the page.",
         sources=[("New Jersey Division of Gaming Enforcement", NJ_DGE)],
         status="needs review"),
    dict(id="NFL1-16", severity="Medium", area="Site",
         summary="Five site generations are live at once.",
         detail=("Root index.html + pages/, docs/, verified-lab/, dashboard/ and lab/. All are "
                 "preserved and all are linked from this site. See suggestion S-13 for three "
                 "options."),
         sources=[("GitHub Pages documentation", GH_PAGES)],
         status="needs review"),
    dict(id="NFL1-17", severity="Medium", area="Site",
         summary="Two CI jobs regenerate the same root pages from different generators.",
         detail=("tools/build.py (Verify NFL1 site) and scripts/verified/build_site.py "
                 "(Verify NFL Decision Lab site build) both write index.html and pages/. "
                 "That is why this session built into lab/ instead."),
         sources=[("GitHub Pages documentation", GH_PAGES)],
         status="needs review"),
    dict(id="NFL1-18", severity="Low", area="Repository state",
         summary="COORDINATION.md begins with a stray 'EAD' fragment on line 1.",
         detail=("The shared task board's first line is the three characters 'EAD', followed "
                 "by a blank line and then the real heading. It looks like the tail of a "
                 "truncated 'README' written by a generator. Not fixed here because the file "
                 "is shared; logged for whichever session owns it next."),
         sources=[("This repository", "https://github.com/kanlerxz87-cyber/NFL1")],
         status="needs review"),
    dict(id="NFL1-19", severity="Low", area="Data coverage",
         summary="Week 10 is in progress; standings cover weeks 1-9 only.",
         detail=("Washington and the Giants are both listed at 8 games played and their "
                 "Thursday night game had not kicked off at retrieval time. The cut-off is "
                 "stated on every page that shows standings."),
         sources=[("Official 2026 standings", NFL_STANDINGS),
                  ("Official Week 10 schedule", NFL_SCHEDULE)],
         status="informational"),
    dict(id="NFL1-20", severity="Medium", area="Data coverage",
         summary="The ratings use 2026 only.",
         detail=("Only the 136 games transcribed and reconciled against the official standings "
                 "are used. Earlier seasons exist in a community mirror that this project "
                 "does not treat as verified, so they are not used."),
         sources=[("nflverse community data mirror", NFLVERSE),
                  ("Official 2026 game results", NFL_GAMES)],
         status="needs review"),
]

SOURCES = [
    dict(id="SRC-01", name="NFL.com 2026 league standings", tier="Official - league",
         url=NFL_STANDINGS, used_for="All 32 club records, points for/against, splits, streak",
         retrieved="2026-11-12"),
    dict(id="SRC-02", name="NFL.com official injury report, Week 10", tier="Official - league",
         url=NFL_INJURIES, used_for="279 player rows: practice participation and game status",
         retrieved="2026-11-12"),
    dict(id="SRC-03", name="NFL.com Week 10 schedule", tier="Official - league",
         url=NFL_SCHEDULE, used_for="14 games, kickoff times, networks, official home/away, byes",
         retrieved="2026-11-12"),
    dict(id="SRC-04", name="NFL.com game results by week", tier="Official - league",
         url=NFL_GAMES, used_for="136 completed 2026 games (scores and dates)",
         retrieved="2026-11-12 (by an earlier session; reconciled here)"),
    dict(id="SRC-05", name="Official club depth charts (31 of 32 clubs)",
         tier="Official - club", url=CHIEFS_DEPTH,
         used_for="1st through 4th string by position, offense / defense / special teams",
         retrieved="2026-11-12"),
    dict(id="SRC-06", name="NFL.com depth chart route", tier="Official - league",
         url=NFL_DEPTH_404, used_for="Probed and confirmed 404 - the league publishes no chart",
         retrieved="2026-11-12"),
    dict(id="SRC-07", name="NFL Football Operations", tier="Official - league",
         url=NFL_OPERATIONS, used_for="Gameday operations reference",
         retrieved="2026-11-12"),
    dict(id="SRC-08", name="NFL tie-breaking procedures", tier="Official - league",
         url=NFL_TIEBREAK, used_for="Standings interpretation", retrieved="2026-11-12"),
    dict(id="SRC-09", name="NIST/SEMATECH e-Handbook - correlation", tier="Standards body",
         url=NIST_CORR, used_for="Pearson r and the Fisher z interval", retrieved="2026-11-12"),
    dict(id="SRC-10", name="NIST/SEMATECH e-Handbook - bootstrap", tier="Standards body",
         url=NIST_BOOTSTRAP, used_for="Bootstrap confidence intervals", retrieved="2026-11-12"),
    dict(id="SRC-11", name="New Jersey Division of Gaming Enforcement", tier="Regulator",
         url=NJ_DGE, used_for="Why the leaderboard awards no prize of value",
         retrieved="2026-11-12"),
    dict(id="SRC-12", name="Sportradar NFL weekly depth charts", tier="Official partner",
         url=SPORTRADAR_DEPTH,
         used_for="Cited as the league-sanctioned feed; not used (credentials required)",
         retrieved="2026-11-12"),
    dict(id="SRC-13", name="Genius Sports - NFL data partnership", tier="Official partner",
         url=GENIUS_NFL, used_for="Why no public official odds exist", retrieved="2026-11-12"),
    dict(id="SRC-14", name="nflverse community data mirror", tier="Community - not verified",
         url=NFLVERSE,
         used_for="Cited only as the source of numbers this project does NOT use",
         retrieved="2026-11-12"),
    dict(id="SRC-15", name="GitHub Pages documentation", tier="Platform",
         url=GH_PAGES, used_for="Deployment model for this site", retrieved="2026-11-12"),
]

SITE_GENERATIONS = [
    dict(path="./", name="NFL Decision Lab (root)",
         owner="sessions 7600ed8b / 25aa7696 / 80731db4 lineage",
         note="The original dashboard: own lines, strategy gates, availability, props."),
    dict(path="docs/", name="Verified dashboard (docs/)", owner="session 87deb7ab",
         note="A second, independently built dashboard with 13 pages."),
    dict(path="verified-lab/", name="Independent verification subsystem",
         owner="session a2cea255",
         note="Hand transcription of nfl.com, a 34-check harness and 103 tests."),
    dict(path="referee/", name="Referee audit", owner="session 73fdd6c4",
         note="Independent official-source audit and replication."),
    dict(path="dashboard/", name="Dashboard (dashboard/)", owner="session 6a232e79 / 3d5c5e2d",
         note="Live-site freshness and signal-honesty pass; 12 pages."),
    dict(path="lab/", name="Consolidated decision lab (this site)", owner="session 1505ac8e",
         note="Live re-verification, decision register, suggestions review, depth charts."),
]
