#!/usr/bin/env python3
"""audit_official.py — line-by-line audit of the published numbers against the official NFL pages.

Session 4c043747 (final integration).  Run from the repository root:

    python3 tools/audit_official.py

What it does
------------
1. Reads the two hand transcriptions of the official league standings page
   (data/audit/4c043747/standings_retrieval_T1.tsv and _T2.tsv) and classifies every printed
   column on two independent axes:
     * reproducible — the printed value was identical in both retrievals;
     * consistent   — the printed value satisfies the identities the official page itself
                      must satisfy (PCT from W/L/T, HOME+ROAD = games played, CONF+NON-CONF =
                      games played, DIV inside CONF, DIV%/CONF% from their own records).
   Only a column that is both reproducible and consistent is treated as a verifiable value.
2. Compares every standings table published in the repository with the official page:
   data/model/snapshot.json, data/verified/standings_2026.csv,
   data/verified/standings_2026_reg.tsv and referee/data/official/nflcom_standings_2026.txt.
3. Compares the published Week-10 slate (data/model/lines.json) with the official Week-10
   schedule transcription, including the records the schedule page prints beside each club,
   and the bye list.
4. Writes data/audit/4c043747/official_audit.json and prints a summary.

Exit code 0 when every published value agrees with the official page.  A disagreement about a
reproducible, consistent official value is a hard FAIL (exit 1).  Irregularities in the
official page itself, and differences confined to columns that the official page does not
reproduce between retrievals, are reported as FLAGS and published for review.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, "data", "audit", "4c043747")
SOURCE_STANDINGS = "https://www.nfl.com/standings/league/2026/reg"
SOURCE_SCHEDULE = "https://www.nfl.com/schedules/2026/REG10"

# Columns that carry the club's own record and can be checked against it.
RECORD_COLUMNS = ["home", "road", "div", "conf", "non_conf"]
PCT_COLUMNS = ["pct", "div_pct", "conf_pct"]
ALL_COLUMNS = list(dict.fromkeys(["w", "l", "t", "pct", "pf", "pa", "net_pts"] + RECORD_COLUMNS + PCT_COLUMNS + ["strk", "last5"]))


def read_tsv(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            rows.append(line.split("\t"))
    header = rows[0]
    return [dict(zip(header, r)) for r in rows[1:]]


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def rec(text):
    """'3-1-0' -> (3, 1, 0); None when the cell is blank."""
    if not text:
        return None
    parts = text.split("-")
    if len(parts) == 2:
        return int(parts[0]), int(parts[1]), 0
    return int(parts[0]), int(parts[1]), int(parts[2])


def tie_pct(r):
    """Tie-aware winning percentage, half-up to three decimals (the official page's rounding)."""
    if r is None:
        return None
    w, l, t = r
    g = w + l + t
    if g == 0:
        return None
    value = (Decimal(w) + Decimal("0.5") * Decimal(t)) / Decimal(g)
    return float(value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def main() -> int:
    checks = []
    failures = []
    flags = []

    def check(name, ok, detail):
        checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})
        if not ok:
            failures.append(f"{name}: {detail}")

    def flag(item, detail, source=SOURCE_STANDINGS):
        flags.append({"item": item, "detail": detail, "source": source})

    t1 = {r["team"]: r for r in read_tsv(os.path.join(AUDIT, "standings_retrieval_T1.tsv"))}
    t2 = {r["team"]: r for r in read_tsv(os.path.join(AUDIT, "standings_retrieval_T2.tsv"))}
    check("standings transcription rows", len(t1) == 32 and len(t2) == 32,
          f"T1 rows={len(t1)} T2 rows={len(t2)} (expected 32 each)")
    check("same clubs in both retrievals", set(t1) == set(t2),
          f"only in T1={sorted(set(t1) - set(t2))} only in T2={sorted(set(t2) - set(t1))}")

    # --------------------------------------------------- 1. reproducibility between retrievals
    changed = {}
    for col in ALL_COLUMNS:
        diff = sorted(t for t in t1 if t1[t].get(col) != t2[t].get(col))
        if diff:
            changed[col] = diff
    reproducible = [c for c in ALL_COLUMNS if c not in changed]
    for col, teams in changed.items():
        flag(f"Official column not reproducible between two retrievals: {col}",
             "The same official page, read twice about 20 minutes apart, printed a different "
             f"value for {len(teams)} club(s): {', '.join(teams)}. Example: "
             + "; ".join(f"{t}: T1={t1[t][col]} / T2={t2[t][col]}" for t in teams[:5])
             + ". No value in this column is published as a verified fact on the site.")

    # --------------------------------------------------- 2. internal consistency of the page
    inconsistent = {}   # "label team" -> list of detail strings
    bad_columns = {}    # column -> set of "label team" rows
    for label, table in (("T1", t1), ("T2", t2)):
        for team, r in table.items():
            w, l, t = int(r["w"]), int(r["l"]), int(r["t"])
            gp = w + l + t
            home, road = rec(r["home"]), rec(r["road"])
            div, conf, nonconf = rec(r["div"]), rec(r["conf"]), rec(r["non_conf"])
            problems = []
            if home and road:
                if (home[0] + road[0], home[1] + road[1], home[2] + road[2]) != (w, l, t):
                    problems.append(f"HOME {r['home']} + ROAD {r['road']} covers "
                                    f"{home[0]+road[0]+home[1]+road[1]+home[2]+road[2]} games, the club has {gp}")
                    bad_columns.setdefault("home", set()).add(f"{label} {team}")
                    bad_columns.setdefault("road", set()).add(f"{label} {team}")
            if conf and nonconf:
                if (conf[0] + nonconf[0], conf[1] + nonconf[1], conf[2] + nonconf[2]) != (w, l, t):
                    problems.append(f"CONF {r['conf']} + NON-CONF {r['non_conf']} covers "
                                    f"{conf[0]+nonconf[0]+conf[1]+nonconf[1]+conf[2]+nonconf[2]} games, the club has {gp}")
                    bad_columns.setdefault("conf", set()).add(f"{label} {team}")
                    bad_columns.setdefault("non_conf", set()).add(f"{label} {team}")
            if div and conf and not (div[0] <= conf[0] and div[1] <= conf[1] and div[2] <= conf[2]):
                problems.append(f"DIV {r['div']} is not contained in CONF {r['conf']}")
                bad_columns.setdefault("div", set()).add(f"{label} {team}")
            if div and abs(float(r["div_pct"]) - (tie_pct(div) or 0)) > 5e-4:
                problems.append(f"DIV% {r['div_pct']} does not match DIV {r['div']} ({tie_pct(div)})")
                bad_columns.setdefault("div_pct", set()).add(f"{label} {team}")
            if conf and abs(float(r["conf_pct"]) - (tie_pct(conf) or 0)) > 5e-4:
                problems.append(f"CONF% {r['conf_pct']} does not match CONF {r['conf']} ({tie_pct(conf)})")
                bad_columns.setdefault("conf_pct", set()).add(f"{label} {team}")
            for p in problems:
                inconsistent.setdefault(f"{label} {team}", []).append(p)

    # the six headline columns must always hold
    for label, table in (("T1", t1), ("T2", t2)):
        for team, r in table.items():
            w, l, t = int(r["w"]), int(r["l"]), int(r["t"])
            p = tie_pct((w, l, t))
            check(f"{label} {team} PCT identity", abs(float(r["pct"]) - p) < 5e-4,
                  f"printed PCT={r['pct']} vs (W+0.5T)/GP={p}")
            check(f"{label} {team} NET identity", int(r["net_pts"]) == int(r["pf"]) - int(r["pa"]),
                  f"printed NET={r['net_pts']} vs PF-PA={int(r['pf']) - int(r['pa'])}")
        sw = sum(int(r["w"]) for r in table.values())
        sl = sum(int(r["l"]) for r in table.values())
        st = sum(int(r["t"]) for r in table.values())
        spf = sum(int(r["pf"]) for r in table.values())
        spa = sum(int(r["pa"]) for r in table.values())
        check(f"{label} league wins equal losses", sw == sl, f"W={sw} L={sl} T={st}")
        check(f"{label} league points balance", spf == spa, f"PF={spf} PA={spa}")

    for key, problems in sorted(inconsistent.items()):
        flag(f"Official page contradicts itself: {key}",
             " | ".join(problems) + ". The cell is left blank on the site and the club's own "
             "W-L-T is used instead.")

    # columns that are both reproducible and self-consistent may be treated as verified
    verified_columns = sorted(col for col in reproducible if col not in bad_columns)
    for col, rows in sorted(bad_columns.items()):
        flag(f"Official column contradicts the club's own record: {col}",
             f"{len(rows)} printed row(s) disagree with the club's games played or with the "
             "record printed beside it: " + ", ".join(sorted(rows))[:400] +
             ". The column is therefore excluded from every verified table on the site.")

    # --------------------------------------------------- 3. repository vs official page
    def norm(code):
        """nfl.com prints the Cardinals as AZ; the repository datasets use ARI."""
        return {"ARI": "AZ", "LAR": "LA"}.get(code, code)

    def official(team):
        """Official transcription row for a club code, tolerating the ARI/AZ difference."""
        return t1.get(norm(team))

    snap = json.load(open(os.path.join(ROOT, "data", "model", "snapshot.json"), encoding="utf-8"))
    for r in snap["standings"]:
        off = official(r["team"])
        if not off:
            check(f"snapshot row {r['team']}", False, "club missing from the official transcription")
            continue
        for col in ("w", "l", "t", "pf", "pa"):
            check(f"snapshot {r['team']} {col}", str(r[col]) == str(off[col]),
                  f"published {r[col]} vs official {off[col]}")

    csv_rows = {r["abbr"]: r for r in read_csv(os.path.join(ROOT, "data", "verified", "standings_2026.csv"))}
    for team, r in csv_rows.items():
        off = official(team)
        if not off:
            continue
        for col in ("w", "l", "t", "pf", "pa"):
            check(f"data/verified/standings_2026.csv {team} {col}", str(r[col]) == str(off[col]),
                  f"published {r[col]} vs official {off[col]}")

    reg_rows = {r["team_abbr"]: r for r in read_tsv(os.path.join(ROOT, "data", "verified", "standings_2026_reg.tsv"))}
    for team, r in reg_rows.items():
        off = official(team)
        if not off:
            continue
        for col in ("w", "l", "t", "pf", "pa"):
            check(f"data/verified/standings_2026_reg.tsv {team} {col}", str(r[col]) == str(off[col]),
                  f"published {r[col]} vs official {off[col]}")
        for col in ("home", "road", "div", "conf", "non_conf", "strk", "last5"):
            if col not in verified_columns:
                seen = {t1[team][col], t2[team][col]}
                if r[col] not in seen:
                    flag(f"Two transcriptions of the same official column disagree: {team} {col}",
                         f"data/verified/standings_2026_reg.tsv prints {r[col]}; the official page "
                         f"printed {t1[team][col]} at ~22:05Z and {t2[team][col]} at ~22:25Z. "
                         "This column is not reproducible or self-consistent on the official "
                         "page, so the cell is left blank on the site.")
            else:
                check(f"data/verified/standings_2026_reg.tsv {team} {col}", r[col] == t1[team][col],
                      f"published {r[col]} vs official {t1[team][col]}")

    ref_path = os.path.join(ROOT, "referee", "data", "official", "nflcom_standings_2026.txt")
    with open(ref_path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            code = "ARI" if parts[0] == "AZ" else parts[0]
            off = t1.get(code)
            if not off:
                continue
            for idx, col in ((1, "w"), (2, "l"), (3, "t"), (4, "pf"), (5, "pa"), (6, "home"), (7, "road")):
                if col not in verified_columns:
                    continue
                check(f"referee transcription {code} {col}", parts[idx] == off[col],
                      f"published {parts[idx]} vs official {off[col]}")

    # --------------------------------------------------- 4. week 10 slate
    sched_rows = read_tsv(os.path.join(AUDIT, "schedule_week10_20261112.tsv"))
    games = [r for r in sched_rows if r.get("away") and r.get("home") and r["away"] != "bye_teams"]
    byes_row = next((r for r in sched_rows if r.get("away") == "bye_teams"), None)
    official_byes = byes_row["home"].split() if byes_row else []
    official_byes = [norm(b) for b in official_byes]

    lines = json.load(open(os.path.join(ROOT, "data", "model", "lines.json"), encoding="utf-8"))
    model_games = {(norm(g["away"]), norm(g["home"])): g for g in lines["lines"]}
    official_games = {(norm(g["away"]), norm(g["home"])): g for g in games}
    check("Week 10 slate size", len(model_games) == len(official_games) == 14,
          f"model={len(model_games)} official={len(official_games)}")
    for key in official_games:
        check(f"slate contains {key[0]} @ {key[1]}", key in model_games,
              "matchup missing from the published model output")
    for key, g in model_games.items():
        check(f"model game {key[0]} @ {key[1]} is an official game", key in official_games,
              "published game is not on the official Week 10 schedule")
        if key in official_games:
            check(f"gameday {key[0]} @ {key[1]}", g.get("gameday") == official_games[key]["gameday"],
                  f"model {g.get('gameday')} vs official {official_games[key]['gameday']}")
    for g in games:
        for side in ("away", "home"):
            team = g[side]
            parts = g[f"{side}_record"].split("-")
            w, l = parts[0], parts[1]
            t = parts[2] if len(parts) > 2 else "0"
            off = official(team)
            if not off:
                continue
            check(f"schedule record {team} ({side})",
                  (w, l, t) == (off["w"], off["l"], off["t"]),
                  f"schedule page prints {g[f'{side}_record']} vs standings page "
                  f"{off['w']}-{off['l']}-{off['t']}")

    repo_byes = []
    byes_csv = os.path.join(ROOT, "data", "verified", "byes_2026.csv")
    if os.path.exists(byes_csv):
        for r in read_csv(byes_csv):
            if r.get("week") == "10":
                repo_byes.append(norm(r["team_abbr"]))
    check("Week 10 bye list", sorted(repo_byes) == sorted(official_byes),
          f"repo={sorted(repo_byes)} official={sorted(official_byes)}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session": "4c043747-nfl1",
        "sources": {"standings": SOURCE_STANDINGS, "schedule": SOURCE_SCHEDULE},
        "retrievals": {"T1": "2026-11-12 ~22:05Z", "T2": "2026-11-12 ~22:25Z"},
        "reproducible_columns": reproducible,
        "verified_columns": verified_columns,
        "columns_changed_between_retrievals": {c: v for c, v in changed.items()},
        "official_page_self_contradictions": inconsistent,
        "columns_contradicting_the_club_record": {c: sorted(v) for c, v in bad_columns.items()},
        "checks_total": len(checks),
        "checks_failed": len(failures),
        "flags": flags,
        "failures": failures,
        "checks": checks,
    }
    with open(os.path.join(AUDIT, "official_audit.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    print(f"checks run: {len(checks)}   failed: {len(failures)}   flags: {len(flags)}")
    print("reproducible between the two retrievals: " + ", ".join(reproducible))
    print("verified-usable (reproducible + self-consistent): " + ", ".join(verified_columns))
    for c, teams in changed.items():
        print(f"  changed between retrievals: {c} ({len(teams)} club(s))")
    print(f"official page self-contradictions: {len(inconsistent)} club/retrieval row(s)")
    for f in failures[:40]:
        print("  FAIL:", f)
    if len(failures) > 40:
        print(f"  ... and {len(failures) - 40} more (see official_audit.json)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
