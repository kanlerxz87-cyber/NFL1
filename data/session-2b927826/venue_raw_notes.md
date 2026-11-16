# Venue transcription notes — Week 11 2026 (official nfl.com Game Centre)
Fetched 2026-11-16. Source of every value: the "Game Info" block of the official game centre
(Location / Stadium), or the "Hotel" destination parameter printed on the official schedule page.
No value is taken from a third-party feed.

| game | official URL | Location printed | Stadium printed | where read |
|---|---|---|---|---|
| IND at HOU | https://www.nfl.com/games/colts-at-texans-2026-reg-11 | HOUSTON, TX | RELIANT STADIUM | Game Info block |
| ARI at KC | https://www.nfl.com/games/cardinals-at-chiefs-2026-reg-11 | KANSAS CITY, MO | ARROWHEAD STADIUM | Game Info block |
| MIN at SF | https://www.nfl.com/games/vikings-at-49ers-2026-reg-11 | MEXICO CITY | ESTADIO BANORTE | Game Info block |
| CIN at WAS | https://www.nfl.com/games/bengals-at-commanders-2026-reg-11 | LANDOVER, MD | NORTHWEST STADIUM | Game Info block |
| MIA at BUF | https://www.nfl.com/games/dolphins-at-bills-2026-reg-11 | (pending) | (pending) | |
| BAL at CAR | https://www.nfl.com/games/ravens-at-panthers-2026-reg-11 | (pending) | (pending) | |
| NO at CHI | https://www.nfl.com/games/saints-at-bears-2026-reg-11 | (pending) | (pending) | |
| TEN at DAL | https://www.nfl.com/games/titans-at-cowboys-2026-reg-11 | (pending) | (pending) | |
| TB at DET | https://www.nfl.com/games/buccaneers-at-lions-2026-reg-11 | (pending) | (pending) | |
| PIT at PHI | https://www.nfl.com/games/steelers-at-eagles-2026-reg-11 | (pending) | (pending) | |
| NYJ at LAC | https://www.nfl.com/games/jets-at-chargers-2026-reg-11 | (pending) | (pending) | |
| JAX at NYG | https://www.nfl.com/games/jaguars-at-giants-2026-reg-11 | (pending) | (pending) | |
| LV at DEN | https://www.nfl.com/games/raiders-at-broncos-2026-reg-11 | (pending) | (pending) | |

## Discrepancies found so far against the committed feed (`data/s9cb/games.csv`, unofficial)
- ARI at KC: feed prints `GEHA Field at Arrowhead Stadium`; official game centre prints
  `ARROWHEAD STADIUM` (the schedule page's hotel link prints `GEHA Field at Arrowhead Stadium`).
  Both are official strings but not identical: recorded as printed, difference flagged.
- IND at HOU: feed and game centre agree on `Reliant Stadium`.
