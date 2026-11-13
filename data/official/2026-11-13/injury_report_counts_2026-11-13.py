#!/usr/bin/env python3
"""Per-club row counts read off the official nfl.com Week 10 injury report.

READING INSTRUCTIONS FOR A REVIEWER
-----------------------------------
Open https://www.nfl.com/injuries/ and count the rows in each club table.
This file records ONLY what the page showed at 2026-11-13T12:20Z. It is a count
audit, not a full transcript: it exists to check the committed 296-row scrape
(`data/model/availability.json`) club by club. No player value is inferred, no
row is filled in, and clubs whose table could not be read to the last row are
marked `partial` instead of guessed.
"""
# (club, rows, did_not_participate, limited, full, game_designations, status, note)
CLUBS = [
    ("WAS",  9, 3, 1,  5, 2, "complete", "Lucas Patrick C Out; Colson Yankoff TE Out"),
    ("NYG", 11, 0, 1, 10, 1, "complete", "Malik Harrison LB Questionable"),
    ("NE",  15, 3, 11, 1, 3, "complete", "Ben Brown C Out; Carlton Davis III CB Out; TreVeyon Henderson RB Out"),
    ("DET",  9, 3, 1,  5, 3, "complete", "Kerby Joseph S Out; Cade Mays C Out; D.J. Reed CB Out"),
    ("KC",  12, 2, 2,  8, 0, "complete", ""),
    ("ATL",  9, 4, 5,  0, 0, "complete", ""),
    ("MIN",  9, 6, 2,  1, 0, "complete", ""),
    ("GB",  16, 6, 8,  2, 0, "complete", ""),
    ("JAX", 11, 4, 6,  1, 0, "complete", ""),
    ("TEN", 12, 5, 2,  5, 0, "complete", ""),
    ("BUF", 12, 1, 7,  4, 0, "complete", ""),
    ("NYJ",  8, 3, 4,  1, 0, "complete", ""),
    ("MIA", 11, 2, 5,  4, 0, "complete", ""),
    ("IND", 13, 7, 0,  6, 0, "complete", ""),
    ("CAR", 12, 1, 3,  8, 0, "complete", ""),
    ("HOU", 13, 5, 6,  2, 0, "complete", ""),
    ("CLE", 12, 4, 8,  0, 0, "complete", ""),
    ("LA",  10, 5, 4,  1, 0, "complete", "Rams are labelled LA on nfl.com and LAR on the club site"),
    ("AZ",  15, 6, 5,  4, 0, "complete", ""),
    ("SEA", 15, 7, 6,  2, 0, "complete", ""),
    ("LV",   4, 0, 2,  2, 0, "complete", ""),
    ("SF",  12, 7, 4,  1, 0, "complete", ""),
    ("DAL", 18, 11, 2, 5, 0, "complete", ""),
    ("PIT",  8, 1, 2,  5, 0, "complete", ""),
    ("NO",   None, None, None, None, None, "partial", "table began mid-page; first read row was Kelvin Banks Jr. T — earlier rows not captured"),
    ("CIN",  None, None, None, None, None, "partial", "table header read but the first rows fall between page chunks"),
    ("LAC",  0, 0, 0, 0, 0, "complete", "page states 'No Injuries Reported'"),
    ("BAL",  0, 0, 0, 0, 0, "complete", "page states 'No Injuries Reported'"),
]
BYE = ["CHI", "DEN", "PHI", "TB"]   # listed under "Teams on Bye" on the official Week 10 schedule
SOURCE = "https://www.nfl.com/injuries/"
RETRIEVED = "2026-11-13T12:20Z"
