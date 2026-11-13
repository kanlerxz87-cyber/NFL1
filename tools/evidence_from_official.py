#!/usr/bin/env python3
"""evidence_from_official.py — point-in-time capture of the official NFL pages.

Why this file exists
--------------------
The project has to verify every published row *against an official source*, and the
verification has to be reproducible by somebody else. The Arena sandbox cannot reach
www.nfl.com with curl (its egress is restricted), but `fetch_page` can read it. So the
official pages are transcribed into this fixture **by hand, line by line**, each row
carrying the exact official URL it was read from and the timestamp it was read.

Rules enforced by `tools/verify_official.py`:
  * every row names an official NFL URL (nfl.com or a club's *.com site on the NFL platform);
  * every value is either transcribed from that page or left as an empty string;
  * nothing is derived here — derived numbers live in `data/model/`, never in this fixture;
  * the row count per club must equal the number of player rows the official page shows.

Read on 2026-11-12 (UTC) from:
  standings …… https://www.nfl.com/standings/league/2026/reg
  injuries  …… https://www.nfl.com/injuries/            (WEEK 10, filing of Thursday 12 Nov)
  schedule  …… https://www.nfl.com/schedules/2026/REG10
  depth     …… club official depth-chart pages (URL per row)

Second capture — the "current" fixture (2026-11-13)
----------------------------------------------------
The 2026-11-12 files above are a pinned point-in-time capture used to verify pinned
hand-transcribed artifacts (data/verified/*.csv/tsv, data/standings.json). The model
side of the repo (data/model/snapshot.json, lines.json, dashboard.json) rolls forward
with the calendar — after the WAS @ NYG Thursday-night game it moved to Week 11 and
its standings include that result. verify_official.py therefore compares moving
artifacts against the *current* capture below (data/evidence/standings_current.json,
data/evidence/schedule_current.json) and pinned artifacts against the pinned capture.
Both captures are transcribed by hand from the official pages at their retrieval
stamps; nothing here is derived.

Read on 2026-11-13 (UTC) from:
  standings_current  …… https://www.nfl.com/standings/league/2026/reg   (post-TNF)
  schedule_current   …… https://www.nfl.com/schedules/2026/by-week/week-11 (13 games,
                         6 byes; matches the Week-11 rows in snapshot.json one by one)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "evidence")
RETRIEVED = "2026-11-12"

STANDINGS_URL = "https://www.nfl.com/standings/league/2026/reg"
INJURIES_URL = "https://www.nfl.com/injuries/"
SCHEDULE_URL = "https://www.nfl.com/schedules/2026/REG10"

# ----------------------------------------------------------------- 1. standings
# Transcribed from the official league standings table, 2026 regular season, read
# 2026-11-12. Columns on the official page: W L T PCT PF PA NET.
# The official page's club code is kept verbatim (AZ, LA) — no renaming, so a reviewer
# can match the row to the page without a mapping table.
STANDINGS = """
BUF|Buffalo Bills|7|1|0|256|187
SF|San Francisco 49ers|7|1|0|235|156
CHI|Chicago Bears|7|2|0|241|184
DEN|Denver Broncos|7|2|0|198|186
CIN|Cincinnati Bengals|6|2|0|240|175
DET|Detroit Lions|6|2|0|222|189
JAX|Jacksonville Jaguars|6|2|0|229|121
KC|Kansas City Chiefs|6|2|0|202|143
MIN|Minnesota Vikings|6|2|0|146|116
PIT|Pittsburgh Steelers|6|2|0|180|144
NYG|New York Giants|5|2|1|182|172
GB|Green Bay Packers|6|3|0|216|191
CLE|Cleveland Browns|5|4|0|161|196
LA|Los Angeles Rams|5|4|0|214|181
NE|New England Patriots|5|4|0|211|207
SEA|Seattle Seahawks|5|4|0|202|162
BAL|Baltimore Ravens|4|5|0|189|236
DAL|Dallas Cowboys|4|5|0|246|236
LV|Las Vegas Raiders|4|5|0|238|268
CAR|Carolina Panthers|3|5|0|199|219
HOU|Houston Texans|3|5|0|209|192
NO|New Orleans Saints|3|5|0|185|216
AZ|Arizona Cardinals|3|6|0|178|255
ATL|Atlanta Falcons|3|6|0|188|223
TB|Tampa Bay Buccaneers|3|6|0|202|178
WAS|Washington Commanders|2|5|1|172|202
IND|Indianapolis Colts|2|7|0|184|249
NYJ|New York Jets|2|7|0|182|223
PHI|Philadelphia Eagles|2|7|0|148|221
MIA|Miami Dolphins|1|7|0|126|200
TEN|Tennessee Titans|1|7|0|144|199
LAC|Los Angeles Chargers|0|8|0|121|219
"""


def standings_rows():
    rows = []
    for line in STANDINGS.strip().splitlines():
        code, name, w, l, t, pf, pa = line.split("|")
        rows.append(dict(code=code, team=name, w=int(w), l=int(l), t=int(t),
                         pf=int(pf), pa=int(pa), net=int(pf) - int(pa),
                         source=STANDINGS_URL, retrieved=RETRIEVED,
                         verified_by="hand transcription of the official league standings table"))
    return rows


# ----------------------------------------------------------------- 2. week 10 injuries
# Every player row the official Week 10 injury report shows, in page order, with the
# official club code and the club's own section on the page (clubs are grouped by game).
# Practice status is transcribed exactly as printed; "game" is the official game
# designation and stays empty when the page prints nothing.
INJURIES = """
WAS|John Bates|TE||Full Participation in Practice|
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
ATL|Josh Woods|LB||Did Not Participate In Practice|
MIN|Blake Cashman|LB||Did Not Participate In Practice|
MIN|T.J. Hockenson|TE||Did Not Participate In Practice|
MIN|Tyrion Ingram-Dawkins|DT||Did Not Participate In Practice|
MIN|Theo Jackson|S||Full Participation in Practice|
MIN|Jauan Jennings|WR||Did Not Participate In Practice|
MIN|Kyler Murray|QB||Did Not Participate In Practice|
MIN|Kyle Van Noy|LB||Did Not Participate In Practice|
MIN|Jay Ward|S||Limited Participation in Practice|
MIN|Carson Wentz|QB||Limited Participation in Practice|
GB|Aaron Banks|G||Limited Participation in Practice|
GB|Chris Brooks|RB||Limited Participation in Practice|
GB|Javon Bullard|S||Did Not Participate In Practice|
GB|Zaire Franklin|LB||Did Not Participate In Practice|
GB|Travis Glover|G||Limited Participation in Practice|
GB|Ty'Ron Hopper|LB||Limited Participation in Practice|
GB|Josh Jacobs|RB||Did Not Participate In Practice|
GB|Bo Melton|WR||Full Participation in Practice|
GB|Skyy Moore|WR||Limited Participation in Practice|
GB|Micah Parsons|LB||Limited Participation in Practice|
GB|Sean Rhyan|C||Did Not Participate In Practice|
GB|Trey Smack|K||Limited Participation in Practice|
GB|Lukas Van Ness|LB||Did Not Participate In Practice|
GB|Josh Whyle|TE||Did Not Participate In Practice|
GB|Savion Williams|WR||Limited Participation in Practice|
GB|Kevin Zeitler|G||Limited Participation in Practice|
JAX|Jessie Bates|S||Did Not Participate In Practice|
JAX|Ezra Cleveland|G||Limited Participation in Practice|
JAX|Branson Combs|LB||Limited Participation in Practice|
JAX|Jordan Davis|DT||Did Not Participate In Practice|
JAX|BJ Green II|DE||Full Participation in Practice|
JAX|Robert Hainsey|C||Limited Participation in Practice|
JAX|Antonio Johnson|S||Limited Participation in Practice|
JAX|Jakobi Meyers|WR||Did Not Participate In Practice|
JAX|Chris Rodriguez Jr.|RB||Limited Participation in Practice|
JAX|Bhayshul Tuten|RB||Did Not Participate In Practice|
JAX|Travon Walker|DE||Did Not Participate In Practice|
TEN|Cody Barton|LB||Did Not Participate In Practice|
TEN|John Franklin-Myers|DE||Full Participation in Practice|
TEN|Marcus Harris|CB||Full Participation in Practice|
TEN|Anthony Hill Jr.|LB||Did Not Participate In Practice|
TEN|Jaylon Jones|CB||Full Participation in Practice|
TEN|JC Latham|T||Full Participation in Practice|
TEN|Tony Pollard|RB||Full Participation in Practice|
TEN|Peter Skoronski|G||Did Not Participate In Practice|
TEN|Tyjae Spears|RB||Did Not Participate In Practice|
TEN|Carnell Tate|WR||Did Not Participate In Practice|
TEN|Tommy Townsend|P||Full Participation in Practice|
TEN|Kevin Winston Jr.|S||Full Participation in Practice|
BUF|Alec Anderson|G||Limited Participation in Practice|
BUF|Christian Benford|CB||Limited Participation in Practice|
BUF|Spencer Brown|T||Limited Participation in Practice|
BUF|Dion Dawkins|T||Limited Participation in Practice|
BUF|Greg Gaines|DT||Full Participation in Practice|
BUF|Jordan Hancock|CB||Full Participation in Practice|
BUF|Dalton Kincaid|TE||Limited Participation in Practice|
BUF|Connor McGovern|C||Limited Participation in Practice|
BUF|Ar'maj Reed-Adams|G||Full Participation in Practice|
BUF|T.J. Sanders|DE||Full Participation in Practice|
BUF|Tyrell Shavers|WR||Full Participation in Practice|
NYJ|Omar Cooper Jr.|WR||Limited Participation in Practice|
NYJ|Joseph Ossai|DE||Limited Participation in Practice|
NYJ|VJ Payne|S||Full Participation in Practice|
NYJ|Harrison Phillips|DT||Did Not Participate In Practice|
NYJ|Trevin Wallace|LB||Did Not Participate In Practice|
NYJ|Garrett Wilson|WR||Limited Participation in Practice|
NYJ|Nahshon Wright|CB||Limited Participation in Practice|
MIA|Tucker Addington|LS||Limited Participation in Practice|
MIA|Kaytron Allen|RB||Full Participation in Practice|
MIA|Darrell Baker Jr.|CB||Limited Participation in Practice|
MIA|Chris Bell|WR||Limited Participation in Practice|
MIA|Aaron Brewer|C||Did Not Participate In Practice|
MIA|Malik Herring|DE||Limited Participation in Practice|
MIA|Will Kacmarek|TE||Did Not Participate In Practice|
MIA|Michael Taaffe|S||Full Participation in Practice|
MIA|Dante Trader Jr.|S||Full Participation in Practice|
MIA|Jaylen Wright|RB||Full Participation in Practice|
IND|Mo Alie-Cox|TE||Did Not Participate In Practice|
IND|CJ Allen|LB||Full Participation in Practice|
IND|Jaylon Carlies|LB||Did Not Participate In Practice|
IND|Akeem Davis-Gaither|LB||Did Not Participate In Practice|
IND|A.J. Haulcy|S||Full Participation in Practice|
IND|Arden Key|DE||Full Participation in Practice|
IND|Luke Rhodes|LS||Did Not Participate In Practice|
IND|Grover Stewart|DT||Did Not Participate In Practice|
IND|Jonathan Taylor|RB||Full Participation in Practice|
IND|Jerry Tillery|DT||Did Not Participate In Practice|
IND|Jalen Travis|T||Did Not Participate In Practice|
IND|Justin Walley|CB||Full Participation in Practice|
IND|Charvarius Ward|CB||Full Participation in Practice|
CAR|Jonathon Brooks|RB||Full Participation in Practice|
CAR|Brady Christensen|G||Full Participation in Practice|
CAR|Trevor Etienne|RB||Full Participation in Practice|
CAR|Chuba Hubbard|RB||Did Not Participate In Practice|
CAR|Lee Hunter|DT||Full Participation in Practice|
CAR|Mike Jackson|CB||Full Participation in Practice|
CAR|Will Lee III|CB||Full Participation in Practice|
CAR|Xavier Legette|WR||Full Participation in Practice|
CAR|Damien Lewis|G||Full Participation in Practice|
CAR|Bobby Okereke|LB||Did Not Participate In Practice|
CAR|Jaelan Phillips|LB||Full Participation in Practice|
CAR|Torricelli Simpkins III|G||Full Participation in Practice|
NO|Kelvin Banks Jr.|T||Limited Participation in Practice|
NO|CJ Donaldson|RB||Did Not Participate In Practice|
NO|David Edwards|G||Limited Participation in Practice|
NO|Martin Emerson|CB||Limited Participation in Practice|
NO|Travis Etienne|RB||Limited Participation in Practice|
NO|Noah Fant|TE||Limited Participation in Practice|
NO|Alvin Kamara|RB||Did Not Participate In Practice|
NO|Erik McCoy|C||Did Not Participate In Practice|
NO|Christen Miller|DT||Limited Participation in Practice|
NO|Asim Richards|T||Full Participation in Practice|
HOU|Azeez Al-Shaair|LB||Did Not Participate In Practice|
HOU|Reed Blankenship|S||Limited Participation in Practice|
HOU|Tank Dell|WR||Limited Participation in Practice|
HOU|Blake Fisher|T||Full Participation in Practice|
HOU|Marvin Harrison Jr.|WR||Limited Participation in Practice|
HOU|Jacob Hummel|LB||Limited Participation in Practice|
HOU|Brevin Jordan|TE||Did Not Participate In Practice|
HOU|Woody Marks|RB||Limited Participation in Practice|
HOU|David Montgomery|RB||Did Not Participate In Practice|
HOU|Keylan Rutledge|G||Did Not Participate In Practice|
HOU|Jaylin Smith|CB||Limited Participation in Practice|
HOU|Wyatt Teller|G||Limited Participation in Practice|
HOU|Tommy Togiai|DT||Full Participation in Practice|
CLE|Austin Barber|T||Limited Participation in Practice|
CLE|Denzel Boston|WR||Did Not Participate In Practice|
CLE|Michael Burton|FB||Did Not Participate In Practice|
CLE|Maliek Collins|DT||Limited Participation in Practice|
CLE|Harold Fannin Jr.|TE||Limited Participation in Practice|
CLE|Ronnie Hickman Jr.|S||Did Not Participate In Practice|
CLE|Tytus Howard|T||Limited Participation in Practice|
CLE|Elgton Jenkins|C||Did Not Participate In Practice|
CLE|Carson Schwesinger|LB||Limited Participation in Practice|
CLE|Denzel Ward|CB||Limited Participation in Practice|
CLE|Quincy Williams|LB||Limited Participation in Practice|
LA|Davis Allen|TE||Limited Participation in Practice|
LA|Steve Avila|G||Did Not Participate In Practice|
LA|Joe Cardona|LS||Limited Participation in Practice|
LA|Kam Curl|S||Did Not Participate In Practice|
LA|Terrance Ferguson|TE||Did Not Participate In Practice|
LA|Myles Garrett|LB||Limited Participation in Practice|
LA|Trent McDuffie|CB||Did Not Participate In Practice|
LA|Puka Nacua|WR||Did Not Participate In Practice|
LA|Colby Parkinson|TE||Limited Participation in Practice|
LA|Matthew Stafford|QB||Full Participation in Practice|
AZ|Budda Baker|S||Did Not Participate In Practice|
AZ|Zachary Carter|DT||Limited Participation in Practice|
AZ|Hjalte Froholdt|C||Did Not Participate In Practice|
AZ|Jon Gaines II|G||Did Not Participate In Practice|
AZ|Bam Knight|RB||Limited Participation in Practice|
AZ|Hunter Long|TE||Limited Participation in Practice|
AZ|Roy Lopez|DT||Did Not Participate In Practice|
AZ|Max Melton|CB||Limited Participation in Practice|
AZ|Isaac Seumalo|G||Did Not Participate In Practice|
AZ|Dante Stills|DT||Limited Participation in Practice|
AZ|Josh Sweat|LB||Did Not Participate In Practice|
AZ|Jayden Williams|T||Limited Participation in Practice|
AZ|Mack Wilson|LB||Did Not Participate In Practice|
AZ|Andrew Wingard|S||Limited Participation in Practice|
SEA|AJ Barner|TE||Full Participation in Practice|
SEA|Anthony Bradford|G||Limited Participation in Practice|
SEA|Charles Cross|T||Did Not Participate In Practice|
SEA|Sam Darnold|QB||Did Not Participate In Practice|
SEA|Derick Hall|LB||Limited Participation in Practice|
SEA|Drew Lock|QB||Limited Participation in Practice|
SEA|Quenton Nelson|G||Did Not Participate In Practice|
SEA|Uchenna Nwosu|LB||Limited Participation in Practice|
SEA|Patrick O'Connell|LB||Limited Participation in Practice|
SEA|Connor O'Toole|LB||Limited Participation in Practice|
SEA|Brandon Pili|DT||Did Not Participate In Practice|
SEA|Jarran Reed|DT||Did Not Participate In Practice|
SEA|Rashid Shaheed|WR||Full Participation in Practice|
SEA|Jaxon Smith-Njigba|WR||Did Not Participate In Practice|
SEA|Leonard Williams|DT||Did Not Participate In Practice|
LV|Thomas Booker|DT||Limited Participation in Practice|
LV|Foley Fatukasi|DT||Limited Participation in Practice|
LV|Ian Thomas|TE||Full Participation in Practice|
LV|Trey Zuhn III|C||Limited Participation in Practice|
SF|Mike Evans|WR||Did Not Participate In Practice|
SF|Renardo Green|CB||Did Not Participate In Practice|
SF|Dre Greenlaw|LB||Did Not Participate In Practice|
SF|Nate Hobbs|CB||Full Participation in Practice|
SF|Deommodore Lenoir|CB||Did Not Participate In Practice|
SF|Christian McCaffrey|RB||Did Not Participate In Practice|
SF|Siran Neal|S||Limited Participation in Practice|
SF|Demarcus Robinson|WR||Full Participation in Practice|
SF|Deebo Samuel Sr.|WR||Limited Participation in Practice|
SF|Upton Stout|CB||Limited Participation in Practice|
SF|C.J. West|DT||Limited Participation in Practice|
SF|Trent Williams|T||Did Not Participate In Practice|
DAL|Jonathan Bullard|DT||Full Participation in Practice|
DAL|Donovan Ezeiruaku|LB||Did Not Participate In Practice|
DAL|Jake Ferguson|TE||Did Not Participate In Practice|
DAL|Tyler Goodson|RB||Did Not Participate In Practice|
DAL|Malik Hooker|S||Did Not Participate In Practice|
DAL|Marist Liufau|LB||Full Participation in Practice|
DAL|P.J. Locke|S||Did Not Participate In Practice|
DAL|Von Miller|LB||Did Not Participate In Practice|
DAL|Jonathan Mingo|WR||Did Not Participate In Practice|
DAL|Devin Moore|CB||Full Participation in Practice|
DAL|DeMarvion Overshown|LB||Limited Participation in Practice|
DAL|George Pickens|WR||Limited Participation in Practice|
DAL|Joey Porter Jr.|CB||Did Not Participate In Practice|
DAL|Luke Schoonmaker|TE||Full Participation in Practice|
DAL|Brevyn Spann-Ford|TE||Full Participation in Practice|
DAL|KaVontae Turpin|WR||Limited Participation in Practice|
PIT|Brandin Echols|CB||Full Participation in Practice|
PIT|DeShon Elliott|S||Limited Participation in Practice|
PIT|Derrick Harmon|DT||Limited Participation in Practice|
PIT|Cameron Heyward|DT||Did Not Participate In Practice|
PIT|Ben Skowronek|WR||Full Participation in Practice|
PIT|Doneiko Slaughter|CB||Full Participation in Practice|
PIT|Darnell Washington|TE||Did Not Participate In Practice|
PIT|T.J. Watt|LB||Did Not Participate In Practice|
CIN|Jonathan Allen|DT||Did Not Participate In Practice|
CIN|Kyle Dugger|S||Did Not Participate In Practice|
CIN|Dylan Fairchild|G||Limited Participation in Practice|
CIN|DJ Turner II|CB||Limited Participation in Practice|
"""

# Clubs the official page shows as "No Injuries Reported" for Week 10. This is a
# statement by the league, and it is transcribed as such rather than as zero rows.
NO_INJURIES_REPORTED = ["LAC", "BAL"]

# Clubs whose section the page publishes; used to prove the section count.
CLUB_ORDER = ["WAS", "NYG", "NE", "DET", "KC", "ATL", "MIN", "GB", "JAX", "TEN",
              "BUF", "NYJ", "MIA", "IND", "CAR", "NO", "HOU", "CLE", "LA", "AZ",
              "SEA", "LV", "SF", "DAL", "PIT", "CIN"]


def injury_rows():
    rows = []
    for line in INJURIES.strip().splitlines():
        club, player, pos, injury, practice, game = line.split("|")
        rows.append(dict(club=club, player=player, position=pos, injury=injury,
                         practice=practice, game_status=game,
                         player_page=f"https://www.nfl.com/players/"
                                     f"{player.lower().replace(' ', '-')}/",
                         source=INJURIES_URL, retrieved=RETRIEVED))
    return rows


# ----------------------------------------------------------------- 3. week 10 schedule
# Transcribed from the official Week 10 schedule page. Local clock time as printed on
# the official page (ET), with the date the page assigns to the game.
SCHEDULE = """
WAS|NYG|2026-11-12|20:15|Thursday Night Football|PRIME
NE|DET|2026-11-15|09:30|International Game (Munich)|FOX
KC|ATL|2026-11-15|13:00|Sunday|CBS
HOU|CLE|2026-11-15|13:00|Sunday|FOX
MIN|GB|2026-11-15|13:00|Sunday|FOX
MIA|IND|2026-11-15|13:00|Sunday|CBS
CAR|NO|2026-11-15|13:00|Sunday|FOX
BUF|NYJ|2026-11-15|13:00|Sunday|CBS
JAX|TEN|2026-11-15|13:00|Sunday|FOX
LA|AZ|2026-11-15|16:05|Sunday|CBS
SEA|LV|2026-11-15|16:05|Sunday|CBS
SF|DAL|2026-11-15|16:25|Sunday|FOX
PIT|CIN|2026-11-15|20:20|Sunday Night Football|NBC
LAC|BAL|2026-11-16|20:15|Monday Night Football|ESPN
"""

BYES_WEEK_10 = ["CHI", "DEN", "PHI", "TB"]

# ------------------------------------------- current capture (2026-11-13)
# Post-TNF league standings, hand-transcribed 2026-11-13 from the official table.
# Only NYG and WAS differ from the pinned 2026-11-12 capture (WAS @ NYG was played
# Thu 2026-11-12, final WAS 24-21 NYG per https://www.nfl.com/games/commanders-at-giants-2026-reg-10).
RETRIEVED_CURRENT = "2026-11-13"
SCHEDULE_URL_CURRENT = "https://www.nfl.com/schedules/2026/by-week/week-11"

STANDINGS_CURRENT = """
BUF|Buffalo Bills|7|1|0|256|187
SF|San Francisco 49ers|7|1|0|235|156
CHI|Chicago Bears|7|2|0|241|184
DEN|Denver Broncos|7|2|0|198|186
CIN|Cincinnati Bengals|6|2|0|240|175
DET|Detroit Lions|6|2|0|222|189
JAX|Jacksonville Jaguars|6|2|0|229|121
KC|Kansas City Chiefs|6|2|0|202|143
MIN|Minnesota Vikings|6|2|0|146|116
PIT|Pittsburgh Steelers|6|2|0|180|144
NYG|New York Giants|5|3|1|203|196
GB|Green Bay Packers|6|3|0|216|191
CLE|Cleveland Browns|5|4|0|161|196
LA|Los Angeles Rams|5|4|0|214|181
NE|New England Patriots|5|4|0|211|207
SEA|Seattle Seahawks|5|4|0|202|162
BAL|Baltimore Ravens|4|5|0|189|236
DAL|Dallas Cowboys|4|5|0|246|236
LV|Las Vegas Raiders|4|5|0|238|268
CAR|Carolina Panthers|3|5|0|199|219
HOU|Houston Texans|3|5|0|209|192
NO|New Orleans Saints|3|5|0|185|216
AZ|Arizona Cardinals|3|6|0|178|255
ATL|Atlanta Falcons|3|6|0|188|223
TB|Tampa Bay Buccaneers|3|6|0|202|178
WAS|Washington Commanders|3|5|1|196|223
IND|Indianapolis Colts|2|7|0|184|249
NYJ|New York Jets|2|7|0|182|223
PHI|Philadelphia Eagles|2|7|0|148|221
MIA|Miami Dolphins|1|7|0|126|200
TEN|Tennessee Titans|1|7|0|144|199
LAC|Los Angeles Chargers|0|8|0|121|219
"""

# Official Week 11 schedule, hand-transcribed 2026-11-13. 13 games + 6 byes = 32 clubs.
# Club codes kept as the page prints them (AZ, LA).
SCHEDULE_WEEK_11 = """
IND|HOU|2026-11-19|20:15|Thursday Night Football|PRIME
MIA|BUF|2026-11-22|13:00||CBS
BAL|CAR|2026-11-22|13:00||FOX
NO|CHI|2026-11-22|13:00||FOX
TEN|DAL|2026-11-22|13:00||FOX
TB|DET|2026-11-22|13:00||FOX
AZ|KC|2026-11-22|13:00||CBS
PIT|PHI|2026-11-22|13:00||CBS
NYJ|LAC|2026-11-22|16:05||FOX
JAX|NYG|2026-11-22|16:25||CBS
LV|DEN|2026-11-22|16:25||CBS
MIN|SF|2026-11-22|20:20|Sunday Night Football|NBC
CIN|WAS|2026-11-23|20:15|Monday Night Football|ESPN
"""

BYES_WEEK_11 = ["ATL", "CLE", "GB", "LA", "NE", "SEA"]


def standings_current_rows():
    rows = []
    for line in STANDINGS_CURRENT.strip().splitlines():
        code, name, w, l, t, pf, pa = line.split("|")
        rows.append(dict(code=code, team=name, w=int(w), l=int(l), t=int(t),
                         pf=int(pf), pa=int(pa), net=int(pf) - int(pa),
                         source=STANDINGS_URL, retrieved=RETRIEVED_CURRENT,
                         verified_by="hand transcription of the official league standings table"))
    return rows


def schedule_current_rows():
    rows = []
    for line in SCHEDULE_WEEK_11.strip().splitlines():
        away, home, day, kick, slot, net = line.split("|")
        rows.append(dict(away=away, home=home, gameday=day, kickoff_et=kick,
                         slot=slot, network=net, venue_note="",
                         source=SCHEDULE_URL_CURRENT, retrieved=RETRIEVED_CURRENT))
    return rows


def schedule_rows():
    rows = []
    for line in SCHEDULE.strip().splitlines():
        away, home, date, et, slot, net = line.split("|")
        rows.append(dict(away=away, home=home, gameday=date, kickoff_et=et,
                         slot=slot, network=net, venue_note="",
                         source=SCHEDULE_URL, retrieved=RETRIEVED))
    return rows


# ----------------------------------------------------------------- 4. depth charts
# Read from the club's own official depth-chart page (the league site returns 404 for
# /teams/<club>/depth-chart — captured as a flag). Column order on those pages is
# 1st string, 2nd string, 3rd string, 4th string, which is what makes a starter-vs-backup
# calculation possible at all. Rows transcribed verbatim; the club page is the source.
DEPTH_URL = {
    "KC": "https://www.chiefs.com/team/depth-chart",
    "SEA": "https://www.seahawks.com/team/depth-chart/",
}

DEPTH = {
    "KC": [
        ("Offense", "WR", ["Rashee Rice", "Jalen Royals", "Andrew Armstrong"]),
        ("Offense", "LT", ["Kahlil Benson", "Diego Pounds"]),
        ("Offense", "LG", ["Kingsley Suamataia", "Joshua Ezeudu"]),
        ("Offense", "C", ["Creed Humphrey", "Hunter Nourzad"]),
        ("Offense", "RG", ["Trey Smith", "Mike Caliendo"]),
        ("Offense", "RT", ["Jaylon Moore", "Joshua Ezeudu"]),
        ("Offense", "TE", ["Travis Kelce", "Noah Gray", "Jared Wiley", "Jake Briningstool"]),
        ("Offense", "QB", ["Patrick Mahomes", "Justin Fields", "Garrett Nussmeier"]),
        ("Offense", "RB", ["Kenneth Walker", "Emmett Johnson", "Jaydn Ott"]),
        ("Offense", "FB", ["Ben VanSumeren"]),
        ("Offense", "WR", ["Xavier Worthy", "Cyrus Allen", "Josh Downs"]),
        ("Defense", "DE", ["Felix Anudike-Uzomah", "Ashton Gillotte"]),
        ("Defense", "DT", ["Chris Jones", "Peter Woods", "Marcus Harris"]),
        ("Defense", "DT", ["Khyiris Tonga", "Bryson Eason"]),
        ("Defense", "DE", ["George Karlaftis", "R Mason Thomas"]),
        ("Defense", "LB", ["Jack Cochrane", "Cooper McDonald"]),
        ("Defense", "LB", ["Nick Bolton", "Jack Cochrane"]),
        ("Defense", "LB", ["Drue Tranquill", "Jeffrey Bassa"]),
        ("Defense", "CB", ["Nohl Williams", "Jadon Canady"]),
        ("Defense", "CB", ["Mansoor Delane", "Kristian Fulton", "Melvin Smith"]),
        ("Defense", "S", ["Alohi Gilman", "Chris Roland-Wallace"]),
        ("Defense", "S", ["Chamarri Conner", "Jaden Hicks", "Xavier Nwankpa"]),
        ("Special Teams", "K", ["Harrison Butker"]),
        ("Special Teams", "P", ["Matt Araiza"]),
        ("Special Teams", "H", ["Matt Araiza"]),
        ("Special Teams", "LS", ["James Winchester"]),
        ("Special Teams", "KR", ["Emmett Johnson", "Cyrus Allen"]),
        ("Special Teams", "PR", ["Emmett Johnson", "Cyrus Allen"]),
    ],
    "SEA": [
        ("Offense", "WR", ["Cooper Kupp", "Rashid Shaheed", "Irvin Charles"]),
        ("Offense", "LT", ["Charles Cross", "Josh Jones"]),
        ("Offense", "LG", ["Quenton Nelson", "Anthony Bradford"]),
        ("Offense", "C", ["Jalen Sundell", "Olu Oluwatimi"]),
        ("Offense", "RG", ["Grey Zabel", "Anthony Bradford", "Beau Stephens"]),
        ("Offense", "RT", ["Abraham Lucas", "Josh Jones"]),
        ("Offense", "TE", ["AJ Barner", "Eric Saubert", "Nick Kallerup"]),
        ("Offense", "WR", ["Jaxon Smith-Njigba", "Tory Horton"]),
        ("Offense", "QB", ["Sam Darnold", "Drew Lock", "Jalen Milroe"]),
        ("Offense", "FB", ["Brady Russell"]),
        ("Offense", "RB", ["Zach Charbonnet", "Jadarian Price", "Emanuel Wilson", "George Holani"]),
        ("Defense", "DT", ["Leonard Williams", "Rylie Mills"]),
        ("Defense", "NT", ["Byron Murphy II", "Brandon Pili", "Deven Eastern"]),
        ("Defense", "DE", ["Jarran Reed", "Mike Morris"]),
        ("Defense", "RUSH", ["DeMarcus Lawrence", "Derick Hall"]),
        ("Defense", "MLB", ["Ernest Jones IV", "Patrick O'Connell"]),
        ("Defense", "WLB", ["Drake Thomas", "Tyrice Knight", "Chazz Surratt"]),
        ("Defense", "SLB", ["Uchenna Nwosu", "Dante Fowler Jr.", "Connor O'Toole"]),
        ("Defense", "CB", ["Devon Witherspoon", "Nehemiah Pritchett"]),
        ("Defense", "CB", ["Josh Jobe", "Avery Smith"]),
        ("Defense", "S", ["Ty Okada", "Rodney Thomas II"]),
        ("Defense", "S", ["Julian Love"]),
        ("Defense", "S", ["Nick Emmanwori"]),
        ("Special Teams", "K", ["Jason Myers"]),
        ("Special Teams", "P", ["Michael Dickson"]),
        ("Special Teams", "H", ["Michael Dickson"]),
        ("Special Teams", "PR", ["Rashid Shaheed", "Tory Horton"]),
        ("Special Teams", "KR", ["Rashid Shaheed", "Velus Jones Jr.", "Tory Horton",
                                 "George Holani", "Emanuel Wilson"]),
        ("Special Teams", "LS", ["Chris Stoll"]),
    ],
}


def depth_rows():
    rows = []
    for club, slots in DEPTH.items():
        for unit, pos, players in slots:
            for i, player in enumerate(players, 1):
                rows.append(dict(club=club, unit=unit, position=pos, depth_rank=i,
                                 player=player, source=DEPTH_URL[club],
                                 retrieved=RETRIEVED))
    return rows


# ----------------------------------------------------------------- 5. write
def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    captured = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payloads = {
        "standings_2026.json": dict(
            _readme="Official league standings, hand-transcribed on 2026-11-12 from "
                    + STANDINGS_URL + ". W/L/T/PF/PA only; NET PASS = PF - PA arithmetic.",
            source_url=STANDINGS_URL, retrieved=RETRIEVED, captured_at=captured,
            rows=standings_rows()),
        "injuries_week10.json": dict(
            _readme="Official Week 10 injury report, every player row, hand-transcribed on "
                    "2026-11-12 from " + INJURIES_URL + ". Practice status verbatim; game "
                    "status blank when the page prints none.",
            source_url=INJURIES_URL, retrieved=RETRIEVED, captured_at=captured,
            club_order=CLUB_ORDER, no_injuries_reported=NO_INJURIES_REPORTED,
            rows=injury_rows()),
        "schedule_week10.json": dict(
            _readme="Official Week 10 schedule, hand-transcribed on 2026-11-12 from "
                    + SCHEDULE_URL + ". Kickoff is the local ET clock time printed on the page.",
            source_url=SCHEDULE_URL, retrieved=RETRIEVED, captured_at=captured,
            byes=BYES_WEEK_10, rows=schedule_rows()),
        "standings_current.json": dict(
            _readme="CURRENT capture: official league standings, hand-transcribed on "
                    "2026-11-13 from " + STANDINGS_URL + " after the WAS @ NYG Thursday "
                    "night game. Moving artifacts (data/model/*) are checked against "
                    "this capture; pinned artifacts stay on standings_2026.json (2026-11-12).",
            source_url=STANDINGS_URL, retrieved=RETRIEVED_CURRENT, captured_at=captured,
            rows=standings_current_rows()),
        "schedule_current.json": dict(
            _readme="CURRENT capture: official Week 11 schedule, hand-transcribed on "
                    "2026-11-13 from " + SCHEDULE_URL_CURRENT + ". Kickoff is the local ET "
                    "clock time printed on the page. 13 games + 6 byes = 32 clubs.",
            source_url=SCHEDULE_URL_CURRENT, retrieved=RETRIEVED_CURRENT, captured_at=captured,
            byes=BYES_WEEK_11, rows=schedule_current_rows()),
        "depth_charts.json": dict(
            _readme="Club depth charts transcribed from each club's own official page on "
                    "2026-11-12. The league site's /teams/<club>/depth-chart URL returns 404 "
                    "(captured in data/verified/depth_chart_probe.csv).",
            retrieved=RETRIEVED, captured_at=captured, sources=DEPTH_URL,
            rows=depth_rows()),
    }
    for name, obj in payloads.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1)
            f.write("\n")
        print(f"wrote data/evidence/{name} ({len(obj['rows'])} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
