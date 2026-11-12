# Injury and backup-depth tracking

Official Week 10 2026 injury report snapshot, official filing policy, official Week 9 inactives and three official club depth charts. Blank cells are blank on the official pages.

## Designations published in the transcribed rows

| Club | Player | Pos | Injury | Practice | Game status | Official source | Verified |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WAS | Lucas Patrick | C | Concussion | Did Not Participate In Practice | Out | [S01](https://www.nfl.com/injuries/) | yes |
| WAS | Colson Yankoff | TE | Knee | Did Not Participate In Practice | Out | [S01](https://www.nfl.com/injuries/) | yes |
| NYG | Malik Harrison | LB | Groin | Limited Participation in Practice | Questionable | [S01](https://www.nfl.com/injuries/) | yes |
| NE | Ben Brown | C | Knee | Did Not Participate In Practice | Out | [S01](https://www.nfl.com/injuries/) | yes |
| NE | Carlton Davis III | CB | Knee | Did Not Participate In Practice | Out | [S01](https://www.nfl.com/injuries/) | yes |
| NE | TreVeyon Henderson | RB | Illness | Did Not Participate In Practice | Out | [S01](https://www.nfl.com/injuries/) | yes |

## Filing policy

| Game day | Practice days | Game Status Report | Official source | Verified |
| --- | --- | --- | --- | --- |
| Sunday game | Wednesday, Thursday and Friday | Friday | [S04](https://www.nfl.com/news/2026-27-national-football-league-important-dates) | yes |
| Monday game | Thursday, Friday and Saturday | Saturday | [S04](https://www.nfl.com/news/2026-27-national-football-league-important-dates) | yes |
| Wednesday game | Sunday, Monday and Tuesday | Tuesday | [S04](https://www.nfl.com/news/2026-27-national-football-league-important-dates) | yes |
| Thursday game | Monday, Tuesday and Wednesday | Wednesday | [S04](https://www.nfl.com/news/2026-27-national-football-league-important-dates) | yes |
| Friday game | Tuesday, Wednesday and Thursday | Thursday | [S04](https://www.nfl.com/news/2026-27-national-football-league-important-dates) | yes |
| Saturday game | Tuesday, Wednesday and Thursday | Thursday | [S04](https://www.nfl.com/news/2026-27-national-football-league-important-dates) | yes |

## Tracking pipeline

| ID | Stage | Detail | Official source | Verified |
| --- | --- | --- | --- | --- |
| TR-01 | Ingest | Weekly official injury report (practice status + game status) at the published filing boundary | [S01](https://www.nfl.com/injuries/) | yes |
| TR-02 | Join | Join each player to the official club depth chart by club, position and player name | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| TR-03 | Resolve | Use the official inactives list to determine who actually dressed | [S05](https://www.nfl.com/news/nfl-week-9-inactives-players-ruled-out-sunday-2026-season) | yes |
| TR-04 | Classify | Label the replacement as 2nd / 3rd / 4th string using the published depth columns | [S16](https://www.49ers.com/team/depth-chart) | yes |
| TR-05 | Score | Compute a backup-exposure or deficiency index | [S19](https://www.itl.nist.gov/div898/handbook/ppc/section1/ppc136.htm) | NO — flagged |
| TR-06 | Validate | Require every validation gate before the score may feed a strategy | [S18](https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm) | yes |

## Official depth charts

| Club | Unit | Pos | 1st | 2nd | 3rd | 4th | Official source | Verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KC | Offense | WR | Rashee Rice | Jalen Royals | Andrew Armstrong |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Offense | LT | Kahlil Benson | Diego Pounds |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Offense | LG | Kingsley Suamataia | Joshua Ezeudu |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Offense | C | Creed Humphrey | Hunter Nourzad |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Offense | RG | Trey Smith | Mike Caliendo |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Offense | RT | Jaylon Moore | Joshua Ezeudu |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Offense | TE | Travis Kelce | Noah Gray | Jared Wiley | Jake Briningstool | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Offense | QB | Patrick Mahomes | Justin Fields | Garrett Nussmeier |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Offense | RB | Kenneth Walker | Emmett Johnson | Jaydn Ott |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Offense | FB | Ben VanSumeren |  |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Offense | WR | Xavier Worthy |  | Cyrus Allen |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Defense | DE | Felix Anudike-Uzomah | Ashton Gillotte |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Defense | DT | Chris Jones | Peter Woods |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Defense | DT | Khyiris Tonga | Bryson Eason |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Defense | DE | George Karlaftis | R Mason Thomas |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Defense | LB | Jack Cochrane | Cooper McDonald |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Defense | LB | Nick Bolton | Jack Cochrane |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Defense | LB | Drue Tranquill | Jeffrey Bassa |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Defense | CB | Nohl Williams | Jadon Canady |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Defense | CB | Mansoor Delane | Kristian Fulton | Melvin Smith |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Defense | S | Alohi Gilman | Chris Roland-Wallace |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Defense | S | Chamarri Conner | Jaden Hicks | Xavier Nwankpa |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Special Teams | K | Harrison Butker |  |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Special Teams | H | Matt Araiza |  |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Special Teams | P | Matt Araiza |  |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Special Teams | LS | James Winchester |  |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Special Teams | KR |  | Emmett Johnson |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| KC | Special Teams | PR |  | Emmett Johnson |  |  | [S14](https://www.chiefs.com/team/depth-chart) | yes |
| GB | Offense | WR | 9 Christian Watson | 16 Bo Melton |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Offense | WR | 0 Matthew Golden | 87 J. Michael Sturdivant |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Offense | LT | 77 Jordan Morgan | 73 John Williams |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Offense | LG | 65 Aaron Banks | 79 Travis Glover | 67 Donovan Jennings |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Offense | C | 75 Sean Rhyan | 52 Jager Burton |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Offense | RG | 72 Laken Tomlinson | 70 Kevin Zeitler |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Offense | RT | 71 Anthony Belton | 74 Mekhi Becton Sr. |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Offense | TE | 85 Tucker Kraft | 18 Jonnu Smith | 86 Mark Redman | 81 Josh Whyle | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Offense | WR | 83 Savion Williams | 13 Coleman Owen |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Offense | QB | 10 Jordan Love | 6 Tyrod Taylor |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Offense | RB | 8 Josh Jacobs | 32 MarShawn Lloyd | 22 Pierre Strong Jr. | 26 Kaleb Johnson | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Defense | DT | 94 Karl Brooks | 97 Jordon Riley | 93 Anthony Campbell |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Defense | DT | 95 Devonte Wyatt | 55 Chris McClellan |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Defense | EDGE | 90 Lukas Van Ness | 57 Brenton Cox Jr |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Defense | LB | 44 Zaire Franklin | 59 Ty'Ron Hopper | 54 Kristian Welch |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Defense | LB | 58 Isaiah McDuffie | 31 Nick Niemann |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Defense | EDGE | 99 Barryn Sorrell | 51 Dani Dennis-Sutton |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Defense | CB | 25 Keisean Nixon | 24 Carrington Valentine |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Defense | CB | 2 Brandon Cisse | 21 Benjamin St-Juste |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Defense | S | 29 Xavier McKinney | 27 Kitan Oladapo |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Defense | S | 33 Evan Williams | 27 Kitan Oladapo |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Defense | NB | 7 Javon Bullard | 36 Kamal Hadden |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Special Teams | K | 28 Trey Smack |  |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Special Teams | P | 19 Daniel Whelan |  |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Special Teams | H | 19 Daniel Whelan |  |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Special Teams | PR | 13 Coleman Owen | 0 Matthew Golden |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Special Teams | KR | 16 Bo Melton | 13 Coleman Owen |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| GB | Special Teams | LS | 42 Matt Orzech |  |  |  | [S15](https://www.packers.com/team/depth-chart) | yes |
| SF | Offense | WR | Mike Evans | Jordan Watkins | Brandin Cooks |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Offense | LT | Trent Williams | Vederian Lowe | Enrique Cruz Jr. |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Offense | LG | Connor Colby | Carver Willis |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Offense | C | Jake Brendel | Jarrett Patterson |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Offense | RG | Dominick Puni |  |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Offense | RT | Colton McKivitz |  |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Offense | TE | George Kittle | Luke Farrell | Brayden Willis |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Offense | WR | Deebo Samuel Sr. | Demarcus Robinson | Jacob Cowing |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Offense | RB | Christian McCaffrey | Kaelon Black | Jordan James |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Offense | FB | Kyle Juszczyk |  |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Offense | QB | Brock Purdy | Mac Jones | Kurtis Rourke |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | LDE | Keion White | Mykel Williams | Khalid Kareem |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | LDT | DeForest Buckner | Gracen Halton | Sebastian Valdez |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | RDT | Osa Odighizuwa | James Thompson Jr. |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | RDE | Nick Bosa | Romello Height |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | SAM | Jaden Dugger | Luke Gifford |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | MIKE | Fred Warner | Tatum Bethune |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | WILL | Dre Greenlaw | Garret Wallow |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | LCB | Renardo Green |  |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | RCB | Deommodore Lenoir | Ephesians Prysock |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | NB | Upton Stout |  |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | FS | Ji'Ayir Brown | Siran Neal |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Defense | SS | Malik Mustapha | Marques Sigle | Ashtyn Davis |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Special Teams | P | Corliss Waitman |  |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Special Teams | K | Eddy Piñeiro |  |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Special Teams | H | Corliss Waitman |  |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Special Teams | PR | Jacob Cowing | Jordan Watkins |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Special Teams | KOR | Deebo Samuel Sr. | Jordan James |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
| SF | Special Teams | LS | Jon Weeks |  |  |  | [S16](https://www.49ers.com/team/depth-chart) | yes |
