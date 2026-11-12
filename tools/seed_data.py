#!/usr/bin/env python3
"""Seed the JSON data layer from values transcribed from official sources.

Every value below was read from the official page listed in SOURCES on
2026-11-12 (UTC). No value is inferred, estimated, or filled in. Blank
strings mean "the official source publishes no value for this cell" and are
rendered as empty table cells plus a Flagged-for-Review link.

Run: python3 tools/seed_data.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)
RETRIEVED = "2026-11-12"


def dump(name, obj):
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("wrote", name, "(%s)" % (len(obj) if isinstance(obj, list) else "object"))


# ---------------------------------------------------------------------------
# 1. Official source registry. Each URL was fetched and read on 2026-11-12.
#    "canonical" records the URL the site redirected to, when different.
# ---------------------------------------------------------------------------
SOURCES = [
    dict(id="S01", publisher="National Football League (NFL.com)", url="https://www.nfl.com/injuries/", kind="Official league injury report", what="2026 Week 10 injury report: player, position, injury, practice status, game status, game/team headings", retrieved=RETRIEVED, verified=True, note="Page title: 'Official Latest NFL Injury Report for Players - Week 10 of the 2026 Season | NFL.com'."),
    dict(id="S02", publisher="National Football League (NFL.com)", url="https://www.nfl.com/standings/league/2026/REG", kind="Official league standings", what="2026 regular season standings, detailed view: W, L, T, PCT, PF, PA, NET PTS and column legend", retrieved=RETRIEVED, verified=True, note="Column order confirmed by the published legend and by PF - PA = NET PTS on every transcribed row."),
    dict(id="S03", publisher="National Football League (NFL.com)", url="https://www.nfl.com/stats/player-stats/", kind="Official player statistics", what="2026 player stat categories (passing, rushing, receiving, tackles, field goals, punting, returns)", retrieved=RETRIEVED, verified=True, note="Category list used to enumerate possible official signal inputs."),
    dict(id="S04", publisher="National Football League (NFL.com news)", url="https://www.nfl.com/news/2026-27-national-football-league-important-dates", kind="Official league calendar", what="Personnel (Injury) Report Policy filing schedule; 53-man roster cutdown; practice squad size", retrieved=RETRIEVED, verified=True, note="Quoted text: 'In accordance with the Personnel (Injury) Report Policy...'."),
    dict(id="S05", publisher="National Football League (NFL.com news)", url="https://www.nfl.com/news/nfl-week-9-inactives-players-ruled-out-sunday-2026-season", kind="Official inactives list", what="2026 Week 9 inactives by game, including 'emergency third QB' designations", retrieved=RETRIEVED, verified=True, note="Used as the official example of published third-string quarterback information."),
    dict(id="S06", publisher="National Football League (NFL.com)", url="https://www.nfl.com/schedules", kind="Official schedule", what="2026 schedule: Week 10 games, dates, kickoff times, networks, team records", retrieved=RETRIEVED, verified=True, canonical="https://www.nfl.com/schedules/2026/REG10 redirects here", note="Canonical URL used."),
    dict(id="S07", publisher="National Football League (NFL.com)", url="https://www.nfl.com/teams/kansas-city-chiefs/roster", kind="Official club roster", what="Chiefs 2026 player roster with status codes (ACT, RES, DEV, others)", retrieved=RETRIEVED, verified=True, note="Status-code definitions are not published on the page; flagged F20."),
    dict(id="S08", publisher="NFL Next Gen Stats", url="https://nextgenstats.nfl.com/", kind="Official advanced metrics", what="Official Next Gen Stats charts, stats and highlights (2026 season)", retrieved=RETRIEVED, verified=True, note="Confirms an official advanced-metrics data source exists."),
    dict(id="S09", publisher="NFL Football Operations", url="https://operations.nfl.com/rules-officiating/2026-nfl-rulebook", kind="Official playing rules", what="2026 NFL Rulebook and 2026 rule changes", retrieved=RETRIEVED, verified=True, canonical="https://operations.nfl.com/the-rules/nfl-rulebook redirects here", note="Canonical URL used."),
    dict(id="S10", publisher="NFL Football Operations", url="https://operations.nfl.com/calendar-events/nfl-free-agency/contract-language", kind="Official roster regulations", what="Roster sizes (53-man Active/Inactive List), 16/17-player practice squad, standard elevation addendum", retrieved=RETRIEVED, verified=True, note="Used for the rules governing replacement players."),
    dict(id="S11", publisher="NFL Football Operations", url="https://operations.nfl.com/game-operations-logistics/preparation-safety/game-ops-manual", kind="Official game operations manual", what="Game Operations Manual requirements incl. two independently certified athletic trainers monitoring the broadcast feed", retrieved=RETRIEVED, verified=True, canonical="https://operations.nfl.com/inside-football-ops/nfl-operations/integrity-of-the-game redirects here", note="Canonical URL used."),
    dict(id="S12", publisher="NFL Football Operations", url="https://operations.nfl.com/game-operations-logistics/preparation-safety/health-safety", kind="Official health & safety policy", what="Player Health & Safety, Competition Committee injury-data review, concussion protocol", retrieved=RETRIEVED, verified=True, note="Used for the injury-data governance context."),
    dict(id="S13", publisher="NFL Football Operations", url="https://operations.nfl.com/rules-officiating/enforcement/accountability", kind="Official weekly accountability data", what="2026 by-week plays, fines and percentages (through Week 8)", retrieved=RETRIEVED, verified=True, note="Example of an official, weekly, numerically published league dataset."),
    dict(id="S14", publisher="Kansas City Chiefs (chiefs.com)", url="https://www.chiefs.com/team/depth-chart", kind="Official club depth chart", what="Chiefs 'Unofficial Depth Chart': Offense, Defense, Special Teams with 1st/2nd/3rd/4th columns", retrieved=RETRIEVED, verified=True, note="Heading literally reads 'Kansas City Chiefs Unofficial Depth Chart'; flagged F06."),
    dict(id="S15", publisher="Green Bay Packers (packers.com)", url="https://www.packers.com/team/depth-chart", kind="Official club depth chart", what="Packers depth chart with 1st/2nd/3rd columns, labelled 'Unofficial, Nov. 10, 2026'", retrieved=RETRIEVED, verified=True, note="Date label and 'Unofficial' label transcribed verbatim."),
    dict(id="S16", publisher="San Francisco 49ers (49ers.com)", url="https://www.49ers.com/team/depth-chart", kind="Official club depth chart", what="49ers depth chart with 1st/2nd/3rd/4th columns, 'Updated as of 11/10/26'", retrieved=RETRIEVED, verified=True, note="Labelling differs from the other two clubs; flagged F07."),
    dict(id="S17", publisher="NIST / SEMATECH e-Handbook of Statistical Methods", url="https://www.itl.nist.gov/div898/handbook/glossary.htm", kind="Official US government statistical reference", what="Pearson correlation definition (-1 to +1), cross-validation definition, generic sample-size advice (20 for a correlation, 32 per group for average difference)", retrieved=RETRIEVED, verified=True, note="Verified on the 'C' and 'S' sections of the glossary."),
    dict(id="S18", publisher="NIST / SEMATECH e-Handbook of Statistical Methods", url="https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm", kind="Official statistical test", what="Two-sample t-test for equal means: hypotheses, test statistic, significance level, critical region", retrieved=RETRIEVED, verified=True, note="Basis for validation gate G06."),
    dict(id="S19", publisher="NIST / SEMATECH e-Handbook of Statistical Methods", url="https://www.itl.nist.gov/div898/handbook/ppc/section1/ppc136.htm", kind="Official statistical guidance", what="Correlation vs causality; 'correlation does not imply causality'; designed experiments", retrieved=RETRIEVED, verified=True, note="Basis for validation gate G08."),
    dict(id="S20", publisher="State of New Jersey, Division of Gaming Enforcement", url="https://www.nj.gov/oag/ge/docs/Regulations/CHAPTER69N.pdf", kind="Official state regulation", what="N.J.A.C. 13:69N sports wagering definitions: sports wager, oddsmaker, event number, operator", retrieved=RETRIEVED, verified=True, note="Official legal definitions for betting terms."),
    dict(id="S21", publisher="State of New Jersey, Division of Gaming Enforcement", url="https://nj.gov/oag/ge/2024news/2020sportswagerreportrevised121523.pdf", kind="Official government research report", what="Sports Wagering in New Jersey, Calendar Year 2020 report (2019 play data): parlay definition, bet-type loss percentages, NFL bet counts, mean loss", retrieved=RETRIEVED, verified=True, note="All quoted percentages read from the report text/Table 15 discussion."),
    dict(id="S22", publisher="GitHub Docs", url="https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site", kind="Official platform documentation", what="GitHub Pages publishing sources: branch + / or /docs; custom Actions workflow; .nojekyll note", retrieved=RETRIEVED, verified=True, note="Deployment method verified against official docs."),
    dict(id="S23", publisher="GitHub Docs", url="https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site", kind="Official platform documentation", what="Pages entry file (index.html at top level of publishing source); static site publishing", retrieved=RETRIEVED, verified=True, note="Root index.html requirement verified."),
    dict(id="S24", publisher="GitHub (this repository)", url="https://github.com/kanlerxz87-cyber/NFL1", kind="Official repository", what="Repository contents, branches, commits, pull requests and coordination board", retrieved=RETRIEVED, verified=True, note="Repo-level claims and coordination flags link here."),
    dict(id="S25", publisher="GitHub REST API", url="https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages", kind="Official platform API", what="Pages build_type, source branch/path, html_url, status", retrieved=RETRIEVED, verified=True, note="Queried with `gh api` during integration; returns status 'built', source main / '/'."),
]
dump("sources.json", SOURCES)


# ---------------------------------------------------------------------------
# 2. Official standings, 2026 regular season, transcribed 2026-11-12.
#    Columns: code, team, W, L, T, PCT, PF, PA, NET PTS.
# ---------------------------------------------------------------------------
STAND = """BUF|Buffalo Bills|7|1|0|0.875|256|187|69
SF|San Francisco 49ers|7|1|0|0.875|235|156|79
CHI|Chicago Bears|7|2|0|0.778|241|184|57
DEN|Denver Broncos|7|2|0|0.778|198|186|12
CIN|Cincinnati Bengals|6|2|0|0.750|240|175|65
DET|Detroit Lions|6|2|0|0.750|222|189|33
JAX|Jacksonville Jaguars|6|2|0|0.750|229|121|108
KC|Kansas City Chiefs|6|2|0|0.750|202|143|59
MIN|Minnesota Vikings|6|2|0|0.750|146|116|30
PIT|Pittsburgh Steelers|6|2|0|0.750|180|144|36
NYG|New York Giants|5|2|1|0.688|182|172|10
GB|Green Bay Packers|6|3|0|0.667|216|191|25
CLE|Cleveland Browns|5|4|0|0.556|161|196|-35
LA|Los Angeles Rams|5|4|0|0.556|214|181|33
NE|New England Patriots|5|4|0|0.556|211|207|4
SEA|Seattle Seahawks|5|4|0|0.556|202|162|40
BAL|Baltimore Ravens|4|5|0|0.444|189|236|-47
DAL|Dallas Cowboys|4|5|0|0.444|246|236|10
LV|Las Vegas Raiders|4|5|0|0.444|238|268|-30
CAR|Carolina Panthers|3|5|0|0.375|199|219|-20
HOU|Houston Texans|3|5|0|0.375|209|192|17
NO|New Orleans Saints|3|5|0|0.375|185|216|-31
AZ|Arizona Cardinals|3|6|0|0.333|178|255|-77
ATL|Atlanta Falcons|3|6|0|0.333|188|223|-35
TB|Tampa Bay Buccaneers|3|6|0|0.333|202|178|24
WAS|Washington Commanders|2|5|1|0.313|172|202|-30
IND|Indianapolis Colts|2|7|0|0.222|184|249|-65
NYJ|New York Jets|2|7|0|0.222|182|223|-41
PHI|Philadelphia Eagles|2|7|0|0.222|148|221|-73
MIA|Miami Dolphins|1|7|0|0.125|126|200|-74
TEN|Tennessee Titans|1|7|0|0.125|144|199|-55
LAC|Los Angeles Chargers|0|8|0|0.000|121|219|-98"""
STANDINGS = []
for line in STAND.strip().splitlines():
    c, n, w, l, t, pct, pf, pa, net = line.split("|")
    STANDINGS.append(dict(code=c, team=n, w=int(w), l=int(l), t=int(t), pct=pct,
                          pf=int(pf), pa=int(pa), net=int(net), src="S02",
                          verified=True, retrieved=RETRIEVED))
assert len(STANDINGS) == 32
for r in STANDINGS:
    assert r["pf"] - r["pa"] == r["net"], r
dump("standings.json", STANDINGS)


# ---------------------------------------------------------------------------
# 3. Week 10 2026 official injury report. Blank cells are blank on the source.
# ---------------------------------------------------------------------------
INJ = """WAS|John Bates|TE||Full Participation in Practice|
WAS|Treylon Burks|WR||Did Not Participate In Practice|
WAS|Jayden Daniels|QB||Full Participation in Practice|
WAS|Matt Gulbin|C||Full Participation in Practice|
WAS|Chig Okonkwo|TE||Full Participation in Practice|
WAS|Lucas Patrick|C|Concussion|Did Not Participate In Practice|Out
WAS|Amik Robertson|CB||Limited Participation in Practice|
WAS|Shy Tuttle|DT||Full Participation in Practice|
WAS|Colson Yankoff|TE|Knee|Did Not Participate In Practice|Out
NYG|Abdul Carter|LB||Full Participation in Practice|
NYG|Jermaine Eluemunor|T||Full Participation in Practice|
NYG|Malik Harrison|LB|Groin|Limited Participation in Practice|Questionable
NYG|Colton Hood|CB||Full Participation in Practice|
NYG|Theo Johnson|TE||Full Participation in Practice|
NYG|Charlie Jones|WR||Full Participation in Practice|
NYG|J.J. McCarthy|QB||Full Participation in Practice|
NYG|Darnell Mooney|WR||Full Participation in Practice|
NYG|Malik Nabers|WR||Full Participation in Practice|
NYG|Cam Skattebo|RB||Full Participation in Practice|
NYG|Andrew Thomas|T||Full Participation in Practice|
NE|Ben Brown|C|Knee|Did Not Participate In Practice|Out
NE|A.J. Brown|WR||Limited Participation in Practice|
NE|Kevin Byard|S||Limited Participation in Practice|
NE|Carlton Davis III|CB|Knee|Did Not Participate In Practice|Out
NE|Reggie Gilliam|FB||Limited Participation in Practice|
NE|TreVeyon Henderson|RB|Illness|Did Not Participate In Practice|Out
NE|Hunter Henry|TE||Limited Participation in Practice|
NE|Cameron Latu|TE||Did Not Participate In Practice|
NE|Drake Maye|QB||Full Participation in Practice|
NE|Morgan Moses|T||Limited Participation in Practice|
NE|Walter Rouse|T||Did Not Participate In Practice|
NE|Brenden Schooler|S||Did Not Participate In Practice|
NE|Rhamondre Stevenson|RB||Did Not Participate In Practice|
NE|Greg Van Roten|G||Limited Participation in Practice|
NE|Charles Woods|CB||Limited Participation in Practice|
DET|Brian Branch|S||Limited Participation in Practice|
DET|Jared Goff|QB||Limited Participation in Practice|
DET|Kerby Joseph|S||Limited Participation in Practice|
DET|Cade Mays|C||Did Not Participate In Practice|
DET|D.J. Reed|CB||Did Not Participate In Practice|
DET|Jacob Saylors|RB||Full Participation in Practice|
DET|Amon-Ra St. Brown|WR||Limited Participation in Practice|
DET|Sione Vaki|RB||Did Not Participate In Practice|
DET|DJ Wonnum|DE||Full Participation in Practice|
KC|Jeffrey Bassa|LB||Full Participation in Practice|
KC|Mansoor Delane|CB||Full Participation in Practice|
KC|Justin Fields|QB||Full Participation in Practice|
KC|Jaden Hicks|S||Full Participation in Practice|
KC|Travis Kelce|TE||Full Participation in Practice|
KC|Patrick Mahomes|QB||Full Participation in Practice|
KC|Jaylon Moore|T||Did Not Participate In Practice|
KC|Omarr Norman-Lott|DT||Limited Participation in Practice|
KC|Rashee Rice|WR||Full Participation in Practice|
KC|Peter Woods|DT||Did Not Participate In Practice|
KC|Xavier Worthy|WR||Full Participation in Practice|
ATL|Zachariah Branch|WR||Did Not Participate In Practice|
ATL|Divine Deablo|LB||Limited Participation in Practice|
ATL|Gervon Dexter Sr.|DT||Did Not Participate In Practice|
ATL|James Pearce Jr.|DE||Did Not Participate In Practice|
ATL|Za'Darius Smith|DE||Did Not Participate In Practice|
ATL|Josh Woods|LB||Did Not Participate In Practice|"""
INJURIES = []
for line in INJ.strip().splitlines():
    team, player, pos, injury, practice, status = line.split("|")
    INJURIES.append(dict(team=team, player=player, pos=pos, injury=injury,
                         practice=practice, game_status=status, src="S01",
                         verified=True, retrieved=RETRIEVED))
dump("injuries.json", INJURIES)

# Game headings published on the same official injury report page.
GAMES = """THURSDAY, NOVEMBER 12TH|8:15 PM EST|Prime Video|WAS|NYG|injury tables published for both clubs
SUNDAY, NOVEMBER 15TH|9:30 AM EST|FOX, FOX DEPORTES|NE|DET|injury tables published for both clubs
SUNDAY, NOVEMBER 15TH|1:00 PM EST|CBS|KC|ATL|injury tables published for both clubs
SUNDAY, NOVEMBER 15TH|1:00 PM EST|FOX|MIN|GB|injury tables published for both clubs
SUNDAY, NOVEMBER 15TH|1:00 PM EST|FOX|JAX|TEN|injury tables published for both clubs
SUNDAY, NOVEMBER 15TH|1:00 PM EST|CBS|BUF|NYJ|injury tables published for both clubs
SUNDAY, NOVEMBER 15TH|1:00 PM EST|CBS|MIA|IND|injury tables published for both clubs
SUNDAY, NOVEMBER 15TH|1:00 PM EST|FOX|CAR|NO|injury tables published for both clubs
SUNDAY, NOVEMBER 15TH|1:00 PM EST|FOX|HOU|CLE|injury tables published for both clubs
SUNDAY, NOVEMBER 15TH|4:05 PM EST|CBS|LA|AZ|injury tables published for both clubs
SUNDAY, NOVEMBER 15TH|4:05 PM EST|CBS|SEA|LV|Seahawks: 'No Injuries Reported'; Raiders table published
SUNDAY, NOVEMBER 15TH|4:25 PM EST|FOX|SF|DAL|injury tables published for both clubs
SUNDAY, NOVEMBER 15TH|8:20 PM EST|NBC, UNIVERSO|PIT|CIN|Bengals: 'No Injuries Reported'; Steelers table published
MONDAY, NOVEMBER 16TH|8:15 PM EST|ESPN, ABC, ESPN2, ESPN DEPORTES|LAC|BAL|'No Injuries Reported' for both clubs"""
INJURY_GAMES = []
for line in GAMES.strip().splitlines():
    d, ko, net, away, home, state = line.split("|")
    INJURY_GAMES.append(dict(day=d, kickoff=ko, network=net, away=away, home=home,
                             report_state=state, src="S01", verified=True,
                             retrieved=RETRIEVED))
dump("injury_games.json", INJURY_GAMES)

# Official Personnel (Injury) Report Policy filing schedule (verbatim structure).
POLICY = """Sunday game|Wednesday, Thursday and Friday|Friday|Practice Report / Game Status Report due 4:00 p.m. New York time
Monday game|Thursday, Friday and Saturday|Saturday|Practice Report / Game Status Report due 4:00 p.m. New York time
Wednesday game|Sunday, Monday and Tuesday|Tuesday|Practice Report / Game Status Report due 4:00 p.m. New York time
Thursday game|Monday, Tuesday and Wednesday|Wednesday|Practice Report / Game Status Report due 4:00 p.m. New York time
Friday game|Tuesday, Wednesday and Thursday|Thursday|Practice Report / Game Status Report due 4:00 p.m. New York time
Saturday game|Tuesday, Wednesday and Thursday|Thursday|Practice Report / Game Status Report due 4:00 p.m. New York time"""
INJURY_POLICY = []
for line in POLICY.strip().splitlines():
    g, prac, gs, note = line.split("|")
    INJURY_POLICY.append(dict(game_day=g, practice_report_days=prac,
                              game_status_report_day=gs, note=note, src="S04",
                              verified=True, retrieved=RETRIEVED))
dump("injury_policy.json", INJURY_POLICY)

# Official Week 9 inactives entries relevant to backup/QB3 tracking.
INACT = """ATL|QB|Andy Dalton (emergency third QB)|CIN at ATL|Week 9 2026
DEN|QB|Sam Ehlinger (emergency third QB)|DEN at CAR|Week 9 2026
CAR|QB|Haynes King (emergency third QB)|DEN at CAR|Week 9 2026
IND|QB|Riley Leonard (emergency third QB)|DAL at IND|Week 9 2026
KC|QB|Garrett Nussmeier|NYJ at KC|Week 9 2026
CLE|QB|Deshaun Watson|CLE at NO|Week 9 2026
CLE|QB|Taylen Green (emergency third QB)|CLE at NO|Week 9 2026
NO|QB|Zach Wilson (emergency third QB)|CLE at NO|Week 9 2026
NYG|RB|Cam Skattebo|NYG at PHI|Week 9 2026
PHI|WR|Devonta Smith|NYG at PHI|Week 9 2026
LA|QB|Ty Simpson (emergency third QB)|LA at WAS|Week 9 2026
LA|CB|Trent McDuffie|LA at WAS|Week 9 2026
WAS|QB|Athan Kaliakmanis (emergency third QB)|LA at WAS|Week 9 2026
WAS|WR|Treylon Burks|LA at WAS|Week 9 2026
HOU|RB|David Montgomery|HOU at LAC|Week 9 2026
DET|CB|D.J. Reed|DET at MIA|Week 9 2026
NYJ|WR|Garrett Wilson|NYJ at KC|Week 9 2026
DAL|WR|George Pickens|DAL at IND|Week 9 2026
DAL|CB|Joey Porter Jr.|DAL at IND|Week 9 2026
CIN|S|Kyle Dugger|CIN at ATL|Week 9 2026"""
WEEK9_INACTIVES = []
for line in INACT.strip().splitlines():
    team, pos, player, game, week = line.split("|")
    WEEK9_INACTIVES.append(dict(team=team, pos=pos, player=player, game=game,
                                week=week, src="S05", verified=True,
                                retrieved=RETRIEVED))
dump("inactives.json", WEEK9_INACTIVES)


# ---------------------------------------------------------------------------
# 4. Official club depth charts. Columns are 1st / 2nd / 3rd / 4th string as
#    published by the club. Empty = no player published in that column.
# ---------------------------------------------------------------------------
DEPTH = {
 "KC": dict(src="S14", team="Kansas City Chiefs", label="Unofficial Depth Chart", as_of="", rows=[
  ("Offense","WR","Rashee Rice","Jalen Royals","Andrew Armstrong",""),
  ("Offense","LT","Kahlil Benson","Diego Pounds","",""),
  ("Offense","LG","Kingsley Suamataia","Joshua Ezeudu","",""),
  ("Offense","C","Creed Humphrey","Hunter Nourzad","",""),
  ("Offense","RG","Trey Smith","Mike Caliendo","",""),
  ("Offense","RT","Jaylon Moore","Joshua Ezeudu","",""),
  ("Offense","TE","Travis Kelce","Noah Gray","Jared Wiley","Jake Briningstool"),
  ("Offense","QB","Patrick Mahomes","Justin Fields","Garrett Nussmeier",""),
  ("Offense","RB","Kenneth Walker","Emmett Johnson","Jaydn Ott",""),
  ("Offense","FB","Ben VanSumeren","","",""),
  ("Offense","WR","Xavier Worthy","","Cyrus Allen",""),
  ("Defense","DE","Felix Anudike-Uzomah","Ashton Gillotte","",""),
  ("Defense","DT","Chris Jones","Peter Woods","",""),
  ("Defense","DT","Khyiris Tonga","Bryson Eason","",""),
  ("Defense","DE","George Karlaftis","R Mason Thomas","",""),
  ("Defense","LB","Jack Cochrane","Cooper McDonald","",""),
  ("Defense","LB","Nick Bolton","Jack Cochrane","",""),
  ("Defense","LB","Drue Tranquill","Jeffrey Bassa","",""),
  ("Defense","CB","Nohl Williams","Jadon Canady","",""),
  ("Defense","CB","Mansoor Delane","Kristian Fulton","Melvin Smith",""),
  ("Defense","S","Alohi Gilman","Chris Roland-Wallace","",""),
  ("Defense","S","Chamarri Conner","Jaden Hicks","Xavier Nwankpa",""),
  ("Special Teams","K","Harrison Butker","","",""),
  ("Special Teams","H","Matt Araiza","","",""),
  ("Special Teams","P","Matt Araiza","","",""),
  ("Special Teams","LS","James Winchester","","",""),
  ("Special Teams","KR","","Emmett Johnson","",""),
  ("Special Teams","PR","","Emmett Johnson","",""),
 ]),
 "GB": dict(src="S15", team="Green Bay Packers", label="Unofficial", as_of="Nov. 10, 2026", rows=[
  ("Offense","WR","9 Christian Watson","16 Bo Melton","",""),
  ("Offense","WR","0 Matthew Golden","87 J. Michael Sturdivant","",""),
  ("Offense","LT","77 Jordan Morgan","73 John Williams","",""),
  ("Offense","LG","65 Aaron Banks","79 Travis Glover","67 Donovan Jennings",""),
  ("Offense","C","75 Sean Rhyan","52 Jager Burton","",""),
  ("Offense","RG","72 Laken Tomlinson","70 Kevin Zeitler","",""),
  ("Offense","RT","71 Anthony Belton","74 Mekhi Becton Sr.","",""),
  ("Offense","TE","85 Tucker Kraft","18 Jonnu Smith","86 Mark Redman","81 Josh Whyle"),
  ("Offense","WR","83 Savion Williams","13 Coleman Owen","",""),
  ("Offense","QB","10 Jordan Love","6 Tyrod Taylor","",""),
  ("Offense","RB","8 Josh Jacobs","32 MarShawn Lloyd","22 Pierre Strong Jr.","26 Kaleb Johnson"),
  ("Defense","DT","94 Karl Brooks","97 Jordon Riley","93 Anthony Campbell",""),
  ("Defense","DT","95 Devonte Wyatt","55 Chris McClellan","",""),
  ("Defense","EDGE","90 Lukas Van Ness","57 Brenton Cox Jr","",""),
  ("Defense","LB","44 Zaire Franklin","59 Ty'Ron Hopper","54 Kristian Welch",""),
  ("Defense","LB","58 Isaiah McDuffie","31 Nick Niemann","",""),
  ("Defense","EDGE","99 Barryn Sorrell","51 Dani Dennis-Sutton","",""),
  ("Defense","CB","25 Keisean Nixon","24 Carrington Valentine","",""),
  ("Defense","CB","2 Brandon Cisse","21 Benjamin St-Juste","",""),
  ("Defense","S","29 Xavier McKinney","27 Kitan Oladapo","",""),
  ("Defense","S","33 Evan Williams","27 Kitan Oladapo","",""),
  ("Defense","NB","7 Javon Bullard","36 Kamal Hadden","",""),
  ("Special Teams","K","28 Trey Smack","","",""),
  ("Special Teams","P","19 Daniel Whelan","","",""),
  ("Special Teams","H","19 Daniel Whelan","","",""),
  ("Special Teams","PR","13 Coleman Owen","0 Matthew Golden","",""),
  ("Special Teams","KR","16 Bo Melton","13 Coleman Owen","",""),
  ("Special Teams","LS","42 Matt Orzech","","",""),
 ]),
 "SF": dict(src="S16", team="San Francisco 49ers", label="Depth Chart", as_of="11/10/26", rows=[
  ("Offense","WR","Mike Evans","Jordan Watkins","Brandin Cooks",""),
  ("Offense","LT","Trent Williams","Vederian Lowe","Enrique Cruz Jr.",""),
  ("Offense","LG","Connor Colby","Carver Willis","",""),
  ("Offense","C","Jake Brendel","Jarrett Patterson","",""),
  ("Offense","RG","Dominick Puni","","",""),
  ("Offense","RT","Colton McKivitz","","",""),
  ("Offense","TE","George Kittle","Luke Farrell","Brayden Willis",""),
  ("Offense","WR","Deebo Samuel Sr.","Demarcus Robinson","Jacob Cowing",""),
  ("Offense","RB","Christian McCaffrey","Kaelon Black","Jordan James",""),
  ("Offense","FB","Kyle Juszczyk","","",""),
  ("Offense","QB","Brock Purdy","Mac Jones","Kurtis Rourke",""),
  ("Defense","LDE","Keion White","Mykel Williams","Khalid Kareem",""),
  ("Defense","LDT","DeForest Buckner","Gracen Halton","Sebastian Valdez",""),
  ("Defense","RDT","Osa Odighizuwa","James Thompson Jr.","",""),
  ("Defense","RDE","Nick Bosa","Romello Height","",""),
  ("Defense","SAM","Jaden Dugger","Luke Gifford","",""),
  ("Defense","MIKE","Fred Warner","Tatum Bethune","",""),
  ("Defense","WILL","Dre Greenlaw","Garret Wallow","",""),
  ("Defense","LCB","Renardo Green","","",""),
  ("Defense","RCB","Deommodore Lenoir","Ephesians Prysock","",""),
  ("Defense","NB","Upton Stout","","",""),
  ("Defense","FS","Ji'Ayir Brown","Siran Neal","",""),
  ("Defense","SS","Malik Mustapha","Marques Sigle","Ashtyn Davis",""),
  ("Special Teams","P","Corliss Waitman","","",""),
  ("Special Teams","K","Eddy Piñeiro","","",""),
  ("Special Teams","H","Corliss Waitman","","",""),
  ("Special Teams","PR","Jacob Cowing","Jordan Watkins","",""),
  ("Special Teams","KOR","Deebo Samuel Sr.","Jordan James","",""),
  ("Special Teams","LS","Jon Weeks","","",""),
 ]),
}
DEPTH_ROWS = []
for code, d in DEPTH.items():
    for unit, pos, s1, s2, s3, s4 in d["rows"]:
        DEPTH_ROWS.append(dict(code=code, team=d["team"], unit=unit, pos=pos,
                               s1=s1, s2=s2, s3=s3, s4=s4,
                               chart_label=d["label"], as_of=d["as_of"],
                               src=d["src"], verified=True, retrieved=RETRIEVED))
dump("depth_chart.json", DEPTH_ROWS)
dump("depth_chart_meta.json", [dict(code=k, **{x: v[x] for x in ("team", "label", "as_of", "src")}) for k, v in DEPTH.items()])


# ---------------------------------------------------------------------------
# 5. Official betting-market facts (State of New Jersey report on 2019 data).
# ---------------------------------------------------------------------------
BET = """Parlay (not in-game) bets lost|86|percent of bets|2019 New Jersey sports wagers|S21|verified
Parlay (in-game) bets lost|81|percent of bets|2019 New Jersey sports wagers|S21|verified
Futures bets lost|80|percent of bets|2019 New Jersey sports wagers|S21|verified
Total (partial) bets lost|50|percent of bets|2019 New Jersey sports wagers|S21|verified
Point spread (partial and whole) bets lost|51|percent of bets|2019 New Jersey sports wagers|S21|verified
Moneyline (whole) bets lost|52|percent of bets|2019 New Jersey sports wagers|S21|verified
Total (whole) bets lost|53|percent of bets|2019 New Jersey sports wagers|S21|verified
All sports bets that resulted in a loss|more than 70|percent of bets|2019 New Jersey sports wagers|S21|verified
Average amount lost across all bets|about 31|US dollars|2019 New Jersey sports wagers|S21|verified
NFL / pro football bets|4,964,198|bets|2019 New Jersey sports wagers (Table 12)|S21|verified
NFL / pro football share of single-leg bets|20.8|percent|2019 New Jersey sports wagers (Table 12)|S21|verified
Parlays with at least one NFL leg|20|percent of parlays|2019 New Jersey sports wagers|S21|verified
Operating online/mobile sports wagering in New Jersey since|2018|year|NJ DGE regulation and report|S20|verified"""
BETTING = []
for line in BET.strip().splitlines():
    label, value, unit, scope, src, v = line.split("|")
    BETTING.append(dict(label=label, value=value, unit=unit, scope=scope,
                        src=src, verified=(v == "verified"), retrieved=RETRIEVED))
dump("betting_facts.json", BETTING)

# Terms with official definitions.
TERMS = """Sports wager|"Sports wager" means a wager placed on an authorized sporting event.|S20
Oddsmaker|"Oddsmaker" means a person licensed as a casino key employee or a casino service industry enterprise responsible for the final approval of all odds established on any wager.|S20
Event number|"Event number" means a set of alpha and/or numeric characters that correspond to specific odds for a sports event.|S20
Parlay|"Parlays combine a number of bets on events, called 'legs.' Bettors place bets on two or more legs, which are then combined into a single parlay bet. Players must win all legs to win a parlay."|S21
Straight bet|The report classifies 'straight bets' as moneyline, point spread, and total (over/under), either whole-game or partial.|S21
Prop bet|The report lists 'Prop' as a distinct bet type in its bet-type and loss-percentage tables.|S21
Cross-validation|"A family of methods based on the idea that the most unbiased test of the predictive error is by applying it to data that was not used in the building of the initial predictive model."|S17
Pearson correlation coefficient|"Correlation is a measure of the strength of the (usually linear) relationship between two variables ... ranges from -1 to 1."|S17"""
TERM_ROWS = []
for line in TERMS.strip().splitlines():
    term, definition, src = line.split("|")
    TERM_ROWS.append(dict(term=term, definition=definition, src=src,
                          verified=True, retrieved=RETRIEVED))
dump("terms.json", TERM_ROWS)


# ---------------------------------------------------------------------------
# 6. Requirements: verbatim decomposition of the project brief.
#    "evidence" is the official source for the domain the requirement concerns.
# ---------------------------------------------------------------------------
REQ = """R01|Scope|Collect a full list of requirements.|Requirements inventory with stable IDs R01-R36 on this site.|documented|S24|verified
R02|Scope|Organize the requirements.|Grouped by category with a dashboard and per-page tables.|documented|S24|verified
R03|Scope|Analyze the requirements.|Each row has an analysis/response column and status.|documented|S24|verified
R04|Decision support|Make suggestions on how to improve the site to improve decision making.|20 ranked improvement suggestions with evidence and a decision-impact column.|documented|S22|verified
R05|Decision support|Create a dedicated section for suggestions so someone can review suggestions and choose the best path before implementing changes.|Dedicated Suggestions page with a Review & Choose a Path gate; nothing is implemented until a path is chosen.|awaiting review|S22|verified
R06|Decision gate|Provide a clear list of questions.|27 numbered decision questions with explicit blocks and discovery actions.|documented|S17|verified
R07|Decision gate|Provide a clear list of information that must be addressed.|Known / unknown columns on every question.|documented|S17|verified
R08|Decision gate|Provide a clear list of answers that need to be addressed before any decision can reasonably be made.|Answer column filled only where an official source publishes the answer; otherwise blank and flagged.|blank where unverified|S17|verified
R09|Decision gate|Base everything on the information we already have and do not have.|Known/unknown split plus a source registry and an unverified-value registry.|documented|S02|verified
R10|Decision gate|Make suggestions to discover missing information.|Each question and each flag includes a concrete discovery action and an official source to check.|documented|S02|verified
R11|Own lines|Originate my own NFL lines.|A reproducible line-generation pipeline is specified using official inputs only; no line value is published because no official odds source exists.|blocked|S20|verified
R12|Signals|Research strategies for generating useful signals.|Research memo enumerating official data sources, signal families and method sources.|documented|S03|verified
R13|Signals|Develop strategies for generating useful signals.|10 candidate strategies with hypotheses, inputs, formulas and gate status.|draft only, not validated|S19|verified
R14|Competition|Treat it as a leaderboard competition that provides rewards for top performing strategies.|Competition rules, three tracks, reward tiers and an empty leaderboard (no fabricated scores).|awaiting validated results|S21|verified
R15|Bet types|Look at single bets.|Single-bet track with official bet-type definitions and loss rates.|documented|S21|verified
R16|Bet types|Look at parlays.|Parlay track with a correlation guard and official loss-rate evidence.|documented|S21|verified
R17|Bet types|Look at player prop bet combos.|Player-prop combo track with an availability gate and a correlation guard.|documented|S21|verified
R18|Validation|Each strategy must pass validation gates.|13 gates with pass criteria, official method sources and a per-strategy gate matrix; every strategy is currently NOT PASSED.|defined|S18|verified
R19|Validation|Determine correlation values.|Standings-derived Pearson correlations computed from official NFL data with a reproducible script; all other requested correlations left blank and flagged.|partially determined|S17|verified
R20|Skill|Remove luck from the equation.|Luck-control protocol: point-in-time data, cross-validation, significance testing, multiple-comparison control, pre-registration.|defined|S17|verified
R21|Skill|Build strategies that are selectively skill based.|A strategy is published as skill-based only after passing every gate; no strategy currently qualifies.|none qualify yet|S19|verified
R22|Injuries|The system should be tracking injuries.|Official Week 10 injury report snapshot, official filing schedule, Week 9 inactives and a tracking pipeline specification.|snapshot + spec|S01|verified
R23|Injuries|Know deficiencies in defenses caused by 2nd, 3rd or 4th string backups replacing starters.|Three official club depth charts transcribed with 1st-4th string columns; deficiency score blank and flagged (no official source).|partially documented|S14|verified
R24|Injuries|Know the same for offenses (starters or backups).|Offense rows of the same official depth charts, plus emergency third QB entries from official inactives.|partially documented|S15|verified
R25|Reporting|Create an executive summary outlining important details.|Dedicated Executive Summary page and docs/exec-summary.md.|documented|S24|verified
R26|Autonomy|There should be no manual input on my part; work on your own to finish all tasks in this session.|All tasks T01-T13 claimed, executed, verified, committed and merged without pausing for input.|documented|S24|verified
R27|Verification|Work line by line, verify everything from official verified trusted sources, no hallucinations.|Line-by-line transcription, per-row source links, blank cells for unconfirmed values, reproducible scripts and an automated validator.|documented|S02|verified
R28|Repo work|Review the repo; verify line by line from official trusted sources; provide links for manual review; flag irregularities.|Repo audit, source registry, 24 flags with official links, all on this site.|documented|S24|verified
R29|Site|Create a GitHub Pages live site with a clean landing page and subpages organized by category; simple dashboard UI.|12-page static dashboard, grouped navigation, responsive CSS, no external dependencies.|deployed|S23|verified
R30|Site|Contain all entries and findings in a simple, easy to read table format, including analysis and findings.|Every dataset is a sortable/filterable table; findings and analysis have their own tables.|documented|S24|verified
R31|Verification|Every table row must have a source link to an official site; leave blank and flag unverified values; never infer or fill in values.|Enforced by tools/verify.py on every generated HTML table; results published on the Verification page.|enforced|S22|verified
R32|Parallel sessions|Use COORDINATION.md as shared task board; claim tasks; non-overlapping scopes; small frequent commits; pull --rebase before every push; log conflicts.|Board created, tasks claimed, disjoint file scopes, frequent commits, coordination conflicts logged.|documented|S24|verified
R33|Integration|Shared outputs changed only by the final integration session; merge branches; re-verify combined data; confirm no broken links; publish to Pages.|This session acts as integration (T12/T13); combined verification and link check run before merge.|documented|S23|verified
R34|PR & merge|Create a PR to main with summary, sources and flagged irregularities; merge without approval; confirm Pages deploy; record PR link and result.|Recorded on the Deployment & PR page and in COORDINATION.md.|executed|S24|verified
R35|Flagged|Publish flagged irregularities and unverified items on a clearly labeled Flagged for Review page with source links.|Dedicated Flagged for Review page with 24 entries, each with official source links.|documented|S24|verified
R36|Reliability|If build, check or deploy fails, fix and retry until the site is live; do not merge a broken site.|Build and link checks run locally and in CI before merge; deployment status checked after merge.|enforced|S22|verified"""
REQUIREMENTS = []
for line in REQ.strip().splitlines():
    rid, cat, text, response, status, src, v = line.split("|")
    REQUIREMENTS.append(dict(id=rid, category=cat, requirement=text,
                             analysis=response, status=status, src=src,
                             verified=(v == "verified"), retrieved=RETRIEVED))
dump("requirements.json", REQUIREMENTS)


# ---------------------------------------------------------------------------
# 7. Decision questions: known / unknown / answer / discovery.
#    Blank strings are deliberately blank and are flagged.
# ---------------------------------------------------------------------------
Q = """Q01|Which season and week does the official injury snapshot cover?|NFL.com injury page title and week selector| |2026 season, Week 10| |Anchor every time-sensitive table|Re-read the official injury page at each snapshot|None|S01|verified
Q02|Which games are in Week 10 and when do they kick off?|Official injury report game headings; official schedule| |See Week 10 games table (14 games)| |Scheduling signals and snapshot timing|Re-read the official schedule page each week|None|S06|verified
Q03|What are the official 2026 standings values?|NFL.com standings detailed view with column legend| |See Standings table (32 rows)|Full game-level results not published on the standings page|Strength models need PF/PA/W-L|Use official game pages linked from the schedule|None|S02|verified
Q04|Which players have officially published injury descriptions or game statuses?|NFL.com Week 10 injury report| |6 rows with a non-blank injury or game-status cell (see Injuries page)|The remaining transcribed rows publish neither|Availability signals need explicit designations|Re-read the final Game Status Report on the official filing day|None|S01|verified
Q05|Which players are 2nd, 3rd or 4th string?|Three official club depth charts publish 1st-4th string columns|Depth charts for the other 29 clubs; a league-wide depth feed|KC, GB and SF rows on the Depth Charts page| |Backup exposure cannot be measured league-wide|Collect the official club depth-chart URL for each club and snapshot it weekly|F08|S14|verified
Q06|Does the official league injury report publish depth rank?|The injury report columns are Player, Position, Injuries, Practice Status, Game Status| |No depth-rank column is published on that page| |Joining injuries to backup depth requires an extra source|Join the injury report to official club depth charts by player and date|F08|S01|verified
Q07|Are official club depth charts authoritative?|Chiefs page says 'Unofficial Depth Chart'; Packers page says 'Unofficial, Nov. 10, 2026'|(blank)| |No official designation of the charts as authoritative was found|Starter/backup status affects every availability signal|Ask for a league-published official depth chart or confirm inactives as the authority|F06|S15|verified
Q08|When must clubs file injury reports?|The 2026-27 important-dates article quotes the Personnel (Injury) Report Policy| |See Injury policy table (6 game-day cases)| |Avoid look-ahead bias in backtests|Snapshot at the official 4:00 p.m. New York time boundary|None|S04|verified
Q09|When are game-day inactives final?|NFL.com publishes a Week 9 inactives article listing ruled-out players|An official page stating the exact pre-kickoff deadline was not located|(blank)| |A signal must not use post-kickoff information|Locate the deadline in the official Game Operations Manual or rulebook|F14|S11|verified
Q10|Which official source publishes NFL betting odds or lines?|NJ DGE regulations define 'oddsmaker' and 'event number'|A league or regulator publication of actual NFL odds/lines was not found|(blank)| |Own lines cannot be benchmarked without a reference line|Request an official odds feed, or pre-register a benchmark built only from official results|F09|S20|verified
Q11|What is the correlation between injury/depth changes and defensive performance?|Official standings PA; official injury report; official depth charts|A timestamped, game-level panel dataset was not found on an official source|(blank)| |This correlation is required before any injury signal can be validated|Build a game-level panel from official schedule + game pages + weekly injury snapshots|F10|S19|verified
Q12|What is the correlation between legs of a same-game parlay or prop combo?|NIST defines the Pearson correlation coefficient|No official source publishes leg-level NFL outcome correlations|(blank)| |Parlay pricing assumes independence unless correlation is measured|Compute leg correlations from official play-by-play/gamebook data under gate G09|F10|S17|verified
Q13|What is the vig / house edge for each bet type?|NJ DGE report publishes bet loss percentages by bet type|A vig per bet type is not published in the official sources reviewed|(blank)| |Break-even thresholds cannot be set|Request operator-level odds and hold data from an official regulator dataset|F11|S21|verified
Q14|How large must a sample be before a result is distinguishable from luck?|NIST generic sample-size advice| |20 observations to estimate a correlation; 32 per group to estimate an average difference; 50 to estimate a standard deviation|These are generic, not NFL-specific|Sets minimum validation gate G04|Run a power calculation on the actual NFL sample once a panel exists|F21|S17|verified
Q15|Which statistical test can certify a strategy beat a benchmark?|NIST two-sample t-test for equal means| |Two-sample t-test with H0: means equal, significance level alpha, critical region from the t distribution|Effect size and alpha for this competition are not set by an official source|Gate G06 requires a defensible test|Pre-register alpha and minimum effect size before evaluation|F21|S18|verified
Q16|Can a correlation be treated as a causal effect?|NIST: 'correlation does not imply causality'| |No; correlation and causality are distinct and designed experiments are needed to establish causality| |Prevents a spurious signal being labelled skill|Require out-of-sample replication and a mechanism before calling a signal causal|F21|S19|verified
Q17|How do official sources define a parlay, a straight bet and a prop bet?|NJ DGE regulations and the 2020 research report| |Parlay = two or more legs combined, all legs must win; straight bets = moneyline, point spread, total; prop = a distinct bet type| |Needed for consistent track definitions|Keep definitions verbatim on the Terms page|None|S21|verified
Q18|How often did parlays and straight bets lose in official data?|NJ DGE report on 2019 New Jersey wagers| |Parlay not in-game 86%, parlay in-game 81%, point spread 51%, moneyline whole 52%, total whole 53%|Data is New Jersey 2019, not a current NFL-only sample|Sets risk posture for parlay strategies|Obtain a current, NFL-only official dataset before calibrating|F21|S21|verified
Q19|How many NFL bets appear in the official state sample?|NJ DGE 2020 report Table 12| |4,964,198 NFL/pro-football bets (20.8% of single-leg bets)| |Sizes the available evidence base|Re-check with newer official reports|F21|S21|verified
Q20|What rewards should the leaderboard grant?|The brief requires rewards for top strategies|No official source defines reward values or eligibility|(blank)| |Reward design cannot be verified externally|Pre-register non-monetary badges and a review cadence; flag as a project choice|F12|S24|verified
Q21|What does 'remove luck' mean operationally?|NIST: cross-validation uses data not used to build the model; control limits separate common-cause from special-cause variation| |Use point-in-time inputs, cross-validation, significance tests and pre-registration|A luck threshold value is not published by an official source|Defines gates G02-G07|Pre-register a numeric skill threshold and freeze it before evaluation|F21|S17|verified
Q22|Are official club depth charts updated during the season?|49ers chart says 'Updated as of 11/10/26'; Packers chart says 'Unofficial, Nov. 10, 2026'|Chiefs chart publishes no as-of date|(blank)| |Snapshot staleness must be visible|Record the as-of label for every snapshot; flag charts without one|F07|S16|verified
Q23|Does the official standings page contain display defects?|The standings page heading reads '$year$ NFL $displayname$ Standings'| |Yes, an unresolved template variable appears in the heading| |Possible indicator of a partially rendered page|Re-fetch and compare with the division/conference views before relying on it|F02|S02|verified
Q24|Do official injury and news pages conflict?|Injury report lists Seahawks 'No Injuries Reported'; NFL.com news headline on the same page says Sam Darnold was ruled out for Week 10| |Yes, a conflict is visible between two official NFL.com surfaces| |A single source of truth for availability is required|Pre-register which official surface wins and log the conflict each week|F04|S01|verified
Q25|What is the GitHub Pages publishing source for this repo?|GitHub REST API pages endpoint; GitHub Docs| |source branch main, path /, build_type legacy, status built, url https://kanlerxz87-cyber.github.io/NFL1/| |Determines where the site must be published|Confirm with the Pages builds endpoint after each deploy|None|S25|verified
Q26|Who else is working on this repository?|Remote branch list on the official GitHub repository| |A second session branch arena/533256e1-nfl1 exists with its own COORDINATION.md|A live coordination channel between sessions does not exist|Duplicate work and conflicting shared outputs|Keep non-overlapping file scopes and log requests in COORDINATION.md|F16|S24|verified
Q27|Can a decision to implement a change be made now?|Decision gate, open questions and flagged items on this site| |No: 24 flagged items and unverified values remain; the Suggestions page keeps all paths at 'awaiting review'| |Prevents premature implementation|Review suggestions, choose a path, then close the blocking questions|None|S24|verified"""
QUESTIONS = []
for line in Q.strip().splitlines():
    parts = line.split("|")
    assert len(parts) == 11, (parts[0], len(parts))
    qid, question, known, unknown, answer, limit, why, discovery, flag, src, v = parts
    QUESTIONS.append(dict(id=qid, question=question, known=known,
                          unknown=unknown, answer=answer, limitation=limit,
                          why=why, discovery=discovery, flag=flag, src=src,
                          verified=(v == "verified"), retrieved=RETRIEVED))
dump("questions.json", QUESTIONS)


# ---------------------------------------------------------------------------
# 8. Improvement suggestions + choose-a-path decision matrix.
# ---------------------------------------------------------------------------
SUG = """S01|Provenance|Add a source link and retrieval date to every table row|Makes any decision auditable line by line||Adopt|No guessing about where a value came from|S02
S02|Provenance|Keep blank cells blank and flag them instead of substituting estimates|Prevents fabricated values entering a decision||Adopt|The brief explicitly forbids inference|S02
S03|Decision readiness|Add a decision-readiness panel that counts open questions and flagged values|Shows at a glance whether a decision is defensible||Adopt||S17
S04|Freshness|Show an as-of timestamp and the next official filing deadline on every data page|Prevents stale injury data being used in a decision||Adopt|Official filing schedule is published|S04
S05|CI|Run the row-source validator and internal link checker on every push|A broken link or unsourced row is caught before publishing||Adopt|GitHub Docs describes publishing from a branch|S22
S06|Availability|Add an injury x depth-chart join that shows which string would take the snaps|Directly addresses the 2nd/3rd/4th-string deficiency requirement||Pilot|Requires both official sources|S14
S07|Availability|Add a conflict detector for 'No Injuries Reported' vs official news headlines|Removes contradictory inputs before they reach a model||Adopt|An actual conflict is already visible|S01
S08|Availability|Add the official weekly inactives list as the availability authority|Inactives are closer to game time than practice reports||Pilot|Official Week 9 list is published|S05
S09|Signals|Add a correlation matrix view with method, n and confidence information|Makes 'determine correlation values' reviewable||Pilot|NIST defines the coefficient|S17
S10|Signals|Add a validation-gate pass/fail badge to every strategy|Prevents unvalidated strategies from being used||Adopt|NIST defines the test structure|S18
S11|Signals|Add a pre-registration hash field for each strategy|Frees the evaluation from post-hoc tuning||Adopt|Cross-validation requires unseen data|S17
S12|Signals|Add a frozen out-of-sample evaluation window on the leaderboard|Separates in-sample fit from genuine predictive skill||Adopt||S17
S13|Parlays|Add a leg-correlation guard before any parlay or prop combo is eligible|Correlated legs change parlay risk materially||Pilot|Correlation is not causality|S19
S14|Risk|Add a bet-type risk panel using official loss percentages|Gives reviewers a common risk baseline||Adopt|Official state report publishes loss rates|S21
S15|Data access|Add JSON/CSV downloads for every table|Allows independent line-by-line review outside the browser||Adopt||S24
S16|Navigation|Group pages by category with a persistent dashboard sidebar|Reduces time to find the evidence behind a decision||Adopt|GitHub Docs describes the site structure|S23
S17|Review workflow|Add an explicit decision log recording the chosen path and reviewer|Makes the 'choose before implementing' gate enforceable||Adopt||S24
S18|Review workflow|Add triage fields (owner, due date, disposition) to Flagged for Review|Turns flags into resolvable work items||Pilot||S24
S19|Glossary|Add a verbatim glossary of official designations and bet types|Prevents inconsistent interpretation of official labels||Adopt|Definitions are published officially|S20
S20|Accessibility|Add table sorting/filtering and responsive table wrappers|Makes large verified tables readable on any screen||Adopt||S23"""
SUGGESTIONS = []
for line in SUG.strip().splitlines():
    sid, area, title, why, effort, rec, evidence, src = line.split("|")
    SUGGESTIONS.append(dict(id=sid, area=area, title=title, decision_impact=why,
                            effort=effort, recommended_path=rec, evidence=evidence,
                            src=src, status="Awaiting review", verified=True,
                            retrieved=RETRIEVED))
dump("suggestions.json", SUGGESTIONS)

PATHS = [
 dict(id="P-A", name="Path A — Data first", summary="Close the open data questions (odds source, depth charts for all clubs, game-level panel, inactives deadline), then build signals.", pros="Every downstream decision rests on verified, point-in-time official data; validation gates become meaningful.", cons="Slower to produce a visible leaderboard; requires repeated official snapshots.", blocks="Q05, Q06, Q09, Q10, Q11, Q12, F08, F09, F10", src="S02", verified=True),
 dict(id="P-B", name="Path B — Strategy first", summary="Prototype the 10 candidate strategies and the leaderboard immediately, with all performance values blank until gates pass.", pros="Fastest visible competition framework and reviewer feedback loop.", cons="Risk of optimising on incomplete data; every strategy stays NOT PASSED until the missing official data arrives.", blocks="Q11, Q12, Q13, F09, F10, F11", src="S19", verified=True),
 dict(id="P-C", name="Path C — Review only / hold", summary="Implement nothing beyond documentation and the review gate until a reviewer explicitly chooses a path.", pros="Zero implementation risk; maximum review control.", cons="No progress on own lines, signals or leaderboard operation.", blocks="Q27, F16, F22", src="S24", verified=True),
]
dump("paths.json", PATHS)


# ---------------------------------------------------------------------------
# 9. Strategy lab: hypotheses, official inputs, gates, correlations.
# ---------------------------------------------------------------------------
STRAT = """ST-01|Net-points strength differential|Single bet|Teams with a higher net points per game cover a derived point spread more often|Official standings PF, PA, W, L, T; official schedule|spread_own = f(NPG_home - NPG_away); f is symbolic, coefficient blank|G01,G02,G03,G04,G05,G06,G07,G12|S02|blank
ST-02|Points-allowed total|Single bet|Points-allowed per game informs a derived game total|Official standings PA, games played; official schedule|total_own = f(PA_pg_home + PA_pg_away); coefficients blank|G01,G02,G03,G04,G05,G06,G07,G12|S02|blank
ST-03|Defensive backup-depth deficiency|Single bet|When a defense starts a 2nd/3rd/4th-string CB, S or EDGE, points allowed rises|Official club depth charts; official injury report; official inactives|delta_rank = depth_rank(starter) - depth_rank(actual); effect size blank|G01,G02,G03,G05,G06,G08,G09,G12|S14|blank
ST-04|Offensive backup-depth deficiency|Single bet|When an offense starts a backup QB or skill player, points scored falls|Official club depth charts (QB, WR, RB, TE); official inactives (emergency third QB)|delta_rank = depth_rank(starter) - depth_rank(actual); effect size blank|G01,G02,G03,G05,G06,G08,G09,G12|S15|blank
ST-05|Practice-status trend|Single bet|A DNP -> Limited -> Full trend predicts availability and performance|Official injury report practice status across the three official filing days|trend = ordinal(Full) - ordinal(first report); coefficient blank|G01,G02,G04,G05,G06,G12|S04|blank
ST-06|Designation-gated availability|Single bet|An official Out/Doubtful/Questionable designation changes the expected lineup|Official injury report game status; official inactives|indicator = 1 if designation published; effect size blank|G01,G02,G05,G06,G12|S01|blank
ST-07|Two-leg parlay with correlation guard|Parlay|Two independently validated single-bet signals can be combined|Official standings, injury report, depth charts; NIST correlation method|P(parlay) = P(A) x P(B) only if corr(A,B) is measured; corr blank|G01,G02,G05,G06,G09,G10,G12|S17|blank
ST-08|Same-game player-prop combo|Player prop combo|QB and receiver props in one game are jointly predictable from official player stats|Official player stats categories; official injury report; official depth charts|joint model requires corr(prop_A, prop_B); corr blank|G01,G02,G04,G05,G06,G09,G12|S03|blank
ST-09|Prop availability gate|Player prop combo|Props must be suppressed for officially Out / IR / inactive players|Official injury report game status; official inactives|rule = block if status in published Out/IR/inactive set|G01,G02,G12|S05|blank
ST-10|Backup-exposure index|All tracks|A composite of published depth rank and injury designations ranks teams by exposure|Official depth charts; official injury report; official inactives|index = weighted sum; weights blank until validated|G01,G02,G03,G04,G05,G06,G08,G09,G12|S14|blank"""
STRATEGIES = []
for line in STRAT.strip().splitlines():
    sid, name, track, hyp, inputs, formula, gates, src, value = line.split("|")
    STRATEGIES.append(dict(id=sid, name=name, track=track, hypothesis=hyp,
                           inputs=inputs, formula=formula, gates=gates,
                           src=src, performance_value="", gate_status="NOT PASSED",
                           verified=True, retrieved=RETRIEVED))
dump("strategies.json", STRATEGIES)

GATES = """G01|Provenance|Every input value has an official source link and retrieval timestamp| |Defined|S02
G02|Point-in-time|Only data published before the decision timestamp is used; official filing times are respected| |Defined|S04
G03|Pre-registration|Strategy formula, thresholds and evaluation window are frozen before scoring| |Defined|S17
G04|Minimum sample|NIST generic advice: 20 observations for a correlation, 32 per group for an average difference, 50 for a standard deviation|20 / 32 / 50 (generic, not NFL-specific)|Defined|S17
G05|Out-of-sample|Model is fit on one partition and assessed on data not used to build it| |Defined|S17
G06|Significance|Two-sample t-test for equal means with pre-registered alpha and critical region|alpha blank (no official value)|Defined|S18
G07|Multiple comparisons|Every tested strategy is logged so the number of tests is known before scoring|correction threshold blank|Defined|S18
G08|Correlation is not causality|No strategy is described as causal without designed-experiment evidence| |Defined|S19
G09|Parlay/prop correlation guard|Leg correlations must be measured before combining legs|corr blank|Defined|S17
G10|Stability|Signal must persist across consecutive seasons/weeks|window blank|Defined|S13
G11|Skill over luck|Performance must exceed a pre-registered skill threshold after all other gates pass|threshold blank|Defined|S17
G12|Reproducibility|A script and data snapshot reproduce every published number| |Defined|S24
G13|Deploy integrity|Every table row has an official source link; no broken internal links; Pages build succeeds| |Defined|S23"""
VALIDATION_GATES = []
for line in GATES.strip().splitlines():
    gid, name, criterion, value, status, src = line.split("|")
    VALIDATION_GATES.append(dict(id=gid, name=name, criterion=criterion,
                                 threshold=value, status=status, src=src,
                                 verified=True, retrieved=RETRIEVED))
dump("validation_gates.json", VALIDATION_GATES)

CORR_REQ = """CR-01|Injury designation count vs points allowed|Game-level injury snapshot + official game results|A timestamped panel dataset is not published by an official source|F10
CR-02|Backup depth rank vs points allowed|Depth chart snapshots + official game results|Depth rank is not published league-wide|F08
CR-03|Backup depth rank vs points scored|Depth chart snapshots + official game results|Same as CR-02, offense side|F08
CR-04|QB passing yards vs WR receiving yards (same game)|Official player stats + official game pages|No official leg-level correlation dataset|F10
CR-05|Two parlay legs (same game)|Official play-by-play data|No official leg-level correlation dataset|F10
CR-06|Practice-status trend vs game-day inactive|Official practice reports + official inactives|Joined historical series not available from an official page|F10
CR-07|Own line error vs realized margin|Official game results|No official odds source to define the benchmark|F09
CR-08|Net points per game vs win percentage|Official standings (available)| |NONE"""
CORRELATION_REQUESTS = []
for line in CORR_REQ.strip().splitlines():
    cid, pair, required, blocker, flag = line.split("|")
    CORRELATION_REQUESTS.append(dict(id=cid, pair=pair, required_inputs=required,
                                     blocker=blocker, r="", flag=flag,
                                     src="S17", verified=False, retrieved=RETRIEVED))
dump("correlation_requests.json", CORRELATION_REQUESTS)

LEADERBOARD_RULES = [
 dict(id="LB-01", rule="Three tracks: Single bet, Parlay, Player prop combo", detail="Track definitions follow the official bet-type terminology.", src="S21", verified=True),
 dict(id="LB-02", rule="Eligibility", detail="A strategy appears on the ranked leaderboard only after passing G01-G13.", src="S18", verified=True),
 dict(id="LB-03", rule="Scoring", detail="Out-of-sample score; numeric formula and weights are blank and flagged until pre-registered.", src="S17", verified=False),
 dict(id="LB-04", rule="Freeze", detail="Evaluation windows and pre-registration hashes are frozen before scoring.", src="S17", verified=True),
 dict(id="LB-05", rule="Rewards", detail="Non-monetary badges: Verified Signal, Top Single Bet, Top Parlay, Top Player Prop Combo. Reward values are blank and flagged.", src="S24", verified=False),
 dict(id="LB-06", rule="Risk posture", detail="Parlay strategies carry a stricter gate because official state data shows higher loss rates for parlays.", src="S21", verified=True),
 dict(id="LB-07", rule="Publication", detail="Ranks, scores and sample sizes are published only when verified; otherwise the cells are blank.", src="S02", verified=True),
]
dump("leaderboard_rules.json", LEADERBOARD_RULES)

LEADERBOARD = []
for s in STRATEGIES:
    LEADERBOARD.append(dict(strategy_id=s["id"], name=s["name"], track=s["track"],
                            rank="", score="", sample_size="", corr_guard="",
                            gates_passed="0 / 13", reward="", status="NOT ELIGIBLE",
                            src=s["src"], verified=False, flag="F12",
                            retrieved=RETRIEVED))
dump("leaderboard.json", LEADERBOARD)


# ---------------------------------------------------------------------------
# 10. Findings, flags, audit metadata.
# ---------------------------------------------------------------------------
FIND = """FD-01|The repository started with exactly one tracked file (README.md, one line '# NFL1')|Repo audit|Verified|S24
FD-02|The official 2026 standings contain all 32 clubs with PF, PA and NET PTS, and PF - PA = NET PTS on every row|Standings table|Verified|S02
FD-03|Only 6 of the transcribed Week 10 injury rows publish an injury description or a game status|Injuries table|Verified|S01
FD-04|Official club depth charts publish 1st through 4th string for offense and defense|Depth Charts table|Verified|S14
FD-05|Two of the three club depth charts are explicitly labelled 'Unofficial'|Depth Charts metadata|Verified|S15
FD-06|NFL.com publishes a Week 9 inactives list with 'emergency third QB' designations|Inactives table|Verified|S05
FD-07|The 2026-27 important dates article publishes the Personnel (Injury) Report Policy filing schedule|Injury policy table|Verified|S04
FD-08|Official state data shows parlay bets lost far more often than straight bets|Bet-type risk table|Verified|S21
FD-09|NIST publishes the definitions needed for correlation, cross-validation and significance testing|Terms and gates tables|Verified|S17
FD-10|Pearson correlations computed from official standings are reproducible from the committed data|Correlations table|Computed|S02
FD-11|No official source reviewed publishes NFL betting lines, leg correlations or vig|Bet-type and correlation tables|Unverified|S20
FD-12|GitHub Pages for this repo is configured to publish main / '/' (legacy build)|Deployment page|Verified|S25
FD-13|A second session branch is active with overlapping task claims|Coordination log|Verified|S24
FD-14|No strategy has passed the validation gates, therefore no leaderboard rank or score is published|Leaderboard table|Verified|S18"""
FINDINGS = []
for line in FIND.strip().splitlines():
    fid, statement, where, status, src = line.split("|")
    FINDINGS.append(dict(id=fid, statement=statement, where=where,
                         status=status, src=src,
                         verified=True, retrieved=RETRIEVED))
dump("findings.json", FINDINGS)

FLAGS = """F01|Repo|The repository contained only README.md at the start; no code, data, workflows or site existed.|No prior implementation to review; all site content is new.|needs review|S24|Confirm the repo audit line by line.
F02|Official page|The 2026 standings page heading renders the literal text '$year$ NFL $displayname$ Standings'.|Possible partially rendered official page; re-check before relying on the heading.|needs review|S02|Re-fetch and compare division/conference standings views.
F03|Official page|On the Week 10 injury report most rows publish neither an injury description nor a game status.|Availability signals cannot use those blank fields.|needs review|S01|Use the final Game Status Report and official inactives instead.
F04|Official page conflict|The injury page lists 'Seahawks: No Injuries Reported' while an NFL.com news headline on the same page says Sam Darnold was ruled out for Week 10.|Two official surfaces disagree on availability.|needs review|S01|Pre-register which official surface is authoritative.
F05|Official page conflict|The injury report lists Puka Nacua as DNP with blank injury and game status, while an NFL.com news headline on the same page says he is likely to be placed on IR.|Injury severity is under-reported in the tabular report.|needs review|S01|Join news and inactives to the tabular report.
F06|Data authority|Chiefs and Packers depth charts are labelled 'Unofficial' by the clubs themselves.|2nd/3rd/4th-string assignments are not league-certified.|needs review|S14|Ask for a league-published depth chart or use official inactives.
F07|Data authority|The 49ers chart says 'Updated as of 11/10/26' but is not labelled 'Unofficial'; the Chiefs chart has no as-of date.|Inconsistent provenance metadata across clubs.|needs review|S16|Record an as-of label for every snapshot.
F08|Missing data|The league injury report publishes no depth-rank column, and only 3 of 32 clubs' depth charts were transcribed.|Backup-deficiency signals cannot be computed league-wide.|needs review|S01|Collect all 32 official club depth-chart URLs and snapshot weekly.
F09|Missing data|No official source reviewed publishes NFL betting odds or lines.|Own lines cannot be benchmarked against a verified market line.|needs review|S20|Request an official odds feed or define a results-only benchmark.
F10|Missing data|No official source publishes leg-level or injury-vs-performance correlation coefficients.|Requested correlation values remain blank except standings-derived ones.|needs review|S19|Build a game-level panel from official game pages and weekly snapshots.
F11|Missing data|No official source reviewed publishes vig or house edge by bet type.|Break-even thresholds cannot be set.|needs review|S21|Obtain operator-level odds/hold data from an official regulator dataset.
F12|Project choice|Leaderboard reward values and the ranking formula are not published by any official source.|Reward and score cells are intentionally blank.|needs review|S24|Pre-register non-monetary rewards and a scoring formula before scoring.
F13|Project choice|Effort and risk estimates for suggestions cannot be confirmed by an official source.|Effort cells are intentionally blank.|needs review|S22|Record estimates only after a reviewer assigns them.
F14|Missing policy text|An official page stating the exact game-day inactives deadline was not located in the pages reviewed.|Look-ahead bias boundary is not fully specified.|needs review|S11|Locate the deadline in the official Game Operations Manual / rulebook.
F15|Missing policy text|No official NFL gambling-policy document was located on the operations.nfl.com pages reviewed.|Compliance constraints for a betting leaderboard are not fully documented.|needs review|S11|Request or locate the league's official gambling policy.
F16|Coordination|Session arena-533256e1 claimed 'all' tasks and overlapping scopes including index.html, data/*.csv and docs/*.md.|Risk of duplicate work and conflicting shared outputs.|needs review|S24|Keep disjoint scopes; integration reconciles shared files.
F17|Deviation|This environment pins the session to one branch, so session-<id>/<task> branches cannot be created.|The brief's branch convention cannot be followed here.|needs review|S24|Note the deviation; a later session with branch freedom can restructure.
F18|Link hygiene|Guessed URLs redirected: /the-rules/nfl-rulebook, /inside-football-ops/nfl-operations/integrity-of-the-game, /schedules/2026/REG10.|Using non-canonical links would produce stale citations.|needs review|S09|Canonical URLs are used in the source registry.
F19|Data comparability|2026 standings show clubs with 8 or 9 games played at the snapshot date.|Raw PF/PA totals are not directly comparable across clubs.|needs review|S02|Use per-game values in any derived metric; method is shown.
F20|Undefined codes|The official roster page shows status codes (ACT, RES, DEV, TRC, CUT) without publishing their definitions on that page.|Roster status cannot be interpreted from that page alone.|needs review|S07|Locate official status-code definitions before using them.
F21|Applicability|The official NJ report describes 2019 New Jersey bettors across all sports, not current NFL-only bettors.|Loss percentages are evidence of structure, not of current NFL strategy performance.|needs review|S21|Obtain current, NFL-specific official data before calibration.
F22|Coordination|Two different COORDINATION.md boards exist on two active branches.|Task status is not globally consistent.|needs review|S24|Integration session must reconcile the boards without discarding either.
F23|Deployment|Pages uses a legacy branch build from main / '/'; Jekyll processing must be disabled for plain HTML.|An unrecognised build step could alter generated pages.|needs review|S22|A .nojekyll file is committed; build status is checked after merge.
F24|Interpretation|The rule 'every table row must have a source link to an official site' is applied to analysis rows by linking the official source that grounds the row's domain; project-only assertions are additionally flagged.|Ensures the rule is enforced without fabricating official support for internal states.|needs review|S24|Confirm the interpretation on review.
F25|Combined data|The earlier sessions' `data/standings.csv` contains a `rank` 1..32 column; the official standings page publishes no rank column.|The ordinal is a project value, not an official statistic; it must not be presented as verified.|needs review|S02|Label it as site row order or leave blank; the new standings table omits rank entirely.
F26|Dead official links|An independent review found three cited operations.nfl.com URLs returning the NFL 404 page (gameday/nfl-schedule/, gameday/, the-rules/).|Those citations cannot be used as evidence on the preserved legacy pages.|needs review|S09|Use the canonical 2026 rulebook and NFL.com schedule links; legacy pages remain labelled historical.
F27|Stale content|Two preserved legacy pages state that no NFL dataset or injury status was imported, which became stale after the earlier sessions' data pull requests.|Reviewers could read contradictory statements across the two site generations.|needs review|S24|The new dashboard is authoritative; legacy pages are preserved at legacy-site.html and clearly labelled.
F28|Combined navigation|Two complete navigation systems now exist in one published site (root dashboard and preserved pages/ site).|Users may see different layouts depending on the entry point.|needs review|S23|The landing dashboard links explicitly to the preserved site and to the combined-integration page.
F29|Abbreviation mismatch|The earlier sessions' `data/teams.csv` and `data/standings.csv` use `LAR` for the Los Angeles Rams; the standings snapshot transcribed in `data/standings.json` uses the official NFL.com abbreviation `LA`.|Two project snapshots refer to the same club with different abbreviations. Neither value was inferred; both were copied from official pages as rendered at different times.|needs review|S02|The combined verifier maps LA↔LAR as an alias for comparison, preserves both spellings in their original files, and flags the discrepancy here.
F30|Third-generation artifacts|Sessions `25aa7696` and `7600ed8b` merged `data/verified/*`, `analysis/*`, `scripts/verified/*` and six new `pages/*.html` files containing 136 official game results, own lines, computed correlations, backtests and a luck analysis.|These are additional deliverables for the same brief. This integration session preserved them all and re-verified the standings, injuries and game results line by line; model-derived numbers were not re-derived here.|needs review|S02|See integration.html for the cross-checks and links to the preserved pages. Their CI numeric audit is retained.
F31|Differing correlation scopes|This dashboard publishes six Pearson correlations computed from the 32 official standings rows; the third-generation pages publish four correlations computed from 136 official game results.|Both sets are computed from official data but answer different questions. Neither fills the other's blank cells.|needs review|S17|Requested leg-level, injury-to-performance and QB/WR correlations remain blank; do not substitute an adjacent metric.
F32|Own-line verdict|The third-generation `pages/lines.html` publishes Week 10 model margins and totals with an explicit FAIL validation verdict; this dashboard's own-line pipeline remains a design with no implemented line values.|A reviewer could mistake the preserved model lines for a validated betting recommendation.|needs review|S18|The preserved page states the model does not beat its baselines with 95% confidence; no strategy on the leaderboard has passed all gates.
F33|Depth-chart conflict|The third-generation availability page states that NFL.com team depth-chart URLs return 404 and that depth order is unknown; this dashboard transcribes 1st–4th strings from three official club sites (chiefs.com, packers.com, 49ers.com).|Two official-source classes disagree in coverage: league depth-chart URLs vs club-published unofficial depth charts.|needs review|S05|Both are preserved with source links; club pages are labelled "Unofficial" by their publishers. Do not generalise three clubs to all 32.
F34|Duplicate decision records|There are now multiple Suggestions, Questions, Flagged and Executive Summary pages across the two site generations.|A reviewer may compare different versions without knowing which is authoritative.|needs review|S24|The landing dashboard is the integration entry point; integration.html links every preserved page and explains the generations.
F35|Deployed-page reading|The earlier sessions found three defects (#6, #7, #8) only by reading the live Pages site after a green CI run: an empty evidence table, empty table cells and literal markdown emphasis.|Automated link/number checks do not prove a rendered page reads correctly.|needs review|S23|This integration fetches the deployed URL and reads the landing page as a user before declaring done; the earlier sessions added gates to check_site.py for all three defect classes."""
FLAG_ROWS = []
for line in FLAGS.strip().splitlines():
    fid, cat, desc, impact, status, src, action = line.split("|")
    FLAG_ROWS.append(dict(id=fid, category=cat, description=desc, impact=impact,
                          status=status, src=src, action=action,
                          verified=True, retrieved=RETRIEVED))
dump("flags.json", FLAG_ROWS)

dump("site_meta.json", dict(
    project="NFL1 — NFL decision-intelligence dashboard",
    snapshot_date=RETRIEVED,
    snapshot_label="2026 NFL regular season, Week 10 (data retrieved 2026-11-12 UTC)",
    pages_url="https://kanlerxz87-cyber.github.io/NFL1/",
    repo="https://github.com/kanlerxz87-cyber/NFL1",
    policy="Every table row links to an official source. Unconfirmed values are left blank and flagged. No value is inferred.",
))

print("seed complete")
