#!/usr/bin/env python3
"""Recompute the 2026 standings from game results and check them against the official table.

Reads, in this order:
  1. data/s9cb/games.csv                              - game results (hash-pinned feed)
  2. data/session-ce097fea/capture/games_reg10_*.tsv  - Week-10 finals transcribed from the official
                                                        schedule page, used only for games the feed
                                                        snapshot predates
  3. data/session-ce097fea/official_standings_*.json  - the official table, as read from nfl.com

Writes:
  data/session-ce097fea/standings_reconciliation_*.json  - all 32 clubs, official vs recomputed
  data/session-ce097fea/standings_verification_*.json    - the feed-only comparison and the freshness gap

Exits non-zero if any club fails to reconcile, so a build that calls this fails loudly.
"""

import csv
import json
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
S9 = ROOT / "data" / "s9cb"
SESS = ROOT / "data" / "session-ce097fea"
CAP = SESS / "capture"
DATE = "2026-11-16"

FEED_CODES = {"ARI": "AZ", "LA": "LAR"}


def norm(code):
    return FEED_CODES.get(code, code)


def load_feed():
    g = pd.read_csv(S9 / "games.csv")
    return g[(g.season == 2026)].dropna(subset=["away_score", "home_score"])


def load_page_finals():
    p = CAP / f"games_reg10_{DATE}.tsv"
    with open(p, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    return [(r["game_id"], r["away"], r["home"], r["away_score"], r["home_score"]) for r in rows]


def tally(records):
    """records: iterable of (away, home, away_score, home_score)"""
    tbl = {}

    def add(t, w, l, t_, pf, pa):
        r = tbl.setdefault(t, {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0})
        r["w"] += w
        r["l"] += l
        r["t"] += t_
        r["pf"] += pf
        r["pa"] += pa

    for aw, hm, a, h in records:
        a, h = int(a), int(h)
        if a > h:
            add(aw, 1, 0, 0, a, h)
            add(hm, 0, 1, 0, h, a)
        elif a < h:
            add(aw, 0, 1, 0, a, h)
            add(hm, 1, 0, 0, h, a)
        else:
            add(aw, 0, 0, 1, a, h)
            add(hm, 0, 0, 1, h, a)
    return tbl


def main():
    feed = load_feed()
    page = load_page_finals()
    official = json.loads((SESS / f"official_standings_{DATE}.json").read_text(encoding="utf-8"))["rows"]

    feed_records = [(norm(r.away_team), norm(r.home_team), int(r.away_score), int(r.home_score))
                    for _, r in feed.iterrows()]
    feed_tbl = tally(feed_records)

    have = {(a, h) for a, h, _, _ in feed_records}
    added = []
    for gid, aw, hm, a, h in page:
        if not a or not h:
            continue                      # fixture had not kicked off
        if (aw, hm) in have:
            continue                      # the feed already holds this result
        added.append((aw, hm, a, h))
    full_tbl = tally(feed_records + added)

    def compare(tbl):
        rows, bad = [], []
        for r in official:
            c = tbl.get(r["code"])
            if c is None:
                rows.append({"code": r["code"], "team": r["team"], "matched": False,
                             "official": {k: r[k] for k in ("w", "l", "t", "pf", "pa")},
                             "recomputed": None, "note": "club absent from the recomputation"})
                bad.append(r["code"])
                continue
            diffs = {k: {"official": r[k], "recomputed": int(c[k])}
                     for k in ("w", "l", "t", "pf", "pa") if int(c[k]) != int(r[k])}
            rows.append({"code": r["code"], "team": r["team"], "matched": not diffs,
                         "official": {k: r[k] for k in ("w", "l", "t", "pf", "pa")},
                         "recomputed": {k: int(c[k]) for k in ("w", "l", "t", "pf", "pa")}})
            if diffs:
                bad.append(r["code"])
        return rows, bad

    full_rows, full_bad = compare(full_tbl)
    feed_rows, feed_bad = compare(feed_tbl)

    feed_w10 = {(norm(r.away_team), norm(r.home_team)): (int(r.away_score), int(r.home_score))
                for _, r in feed[feed.week == 10].iterrows()}
    page_finals = {(m[1], m[2]): (int(m[3]), int(m[4])) for m in page if m[3] and m[4]}
    agreeing = sum(1 for k in set(feed_w10) & set(page_finals) if feed_w10[k] == page_finals[k])

    rec = {
        "generated": DATE,
        "method": (
            "Recomputed the 2026 standings from every game result in the nflverse feed "
            "(data/s9cb/games.csv, a parsed copy of the NFL GSIS feed) plus this session's transcription "
            "of the Week-10 finals that the feed snapshot predates, then compared W/L/T/PF/PA cell by "
            "cell against the official nfl.com standings table captured the same day. The Monday-night "
            "fixture (LAC at BAL) had not kicked off and is excluded from both sides."),
        "official_source": json.loads((SESS / f"official_standings_{DATE}.json").read_text(encoding="utf-8"))["source_url"],
        "week10_source": "https://www.nfl.com/schedules/2026/REG11",
        "feed": "data/s9cb/games.csv (nflverse schedules release; sha256 in data/s9cb/provenance.json)",
        "games_added_from_official_page": [f"{a} {s1} at {h} {s2}" for a, h, s1, s2 in added],
        "clubs": len(official),
        "matched": len(official) - len(full_bad),
        "rows": full_rows,
        "mismatches": [r for r in full_rows if not r["matched"]],
    }
    ver = {
        "generated": DATE,
        "feed_snapshot_note": (
            "games.csv was fetched 2026-11-15T13:21Z (per data/s9cb/provenance.json), i.e. before the "
            "Week 10 Sunday games. The recomputation from the feed alone therefore covers Week 1-9 plus "
            "the Thursday game only, which is why only the clubs that did not play on Sunday reconcile."),
        "clubs": len(official),
        "matched": len(official) - len(feed_bad),
        "rows": feed_rows,
        "week10_score_check": {
            "feed_scored": len(feed_w10),
            "page_finals": len(page_finals),
            "agreeing": agreeing,
        },
    }
    (SESS / f"standings_reconciliation_{DATE}.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    (SESS / f"standings_verification_{DATE}.json").write_text(json.dumps(ver, indent=1) + "\n", encoding="utf-8")

    print(f"feed-only reconciliation : {ver['matched']}/{ver['clubs']} clubs")
    print(f"feed + official Week-10  : {rec['matched']}/{rec['clubs']} clubs")
    print(f"week-10 games added from the official page: {len(added)}")
    print(f"week-10 scores agreeing where the feed has them: {agreeing}/{len(feed_w10)}")
    if rec["mismatches"]:
        for m in rec["mismatches"]:
            print("  MISMATCH", json.dumps(m))
        sys.exit(1)
    print("OK: every club reconciles")


if __name__ == "__main__":
    main()
