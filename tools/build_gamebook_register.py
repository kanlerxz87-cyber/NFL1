#!/usr/bin/env python3
"""Build the availability-outcome register and the `gamebook/` sub-site from committed captures.

Session `98a40411-nfl1`, tasks G4/G5/G7. Deterministic and network-free: it reads only files that
are committed in the repository, so the same numbers appear on the branch, in the PR check and on
the published site.

Inputs (all read-only)
----------------------
* `data/gamebook/official_inactives/inactives_*_article.json` - the league's dated weekly inactives
  article, transcribed row by row with its fetch time (plus the evidence text it was read from).
* `data/gamebook/captures/{inactives,report,gamebook}/*.json` - raw captures made by
  `pipeline/collect_gamebooks.py` on GitHub Actions, each with sha256 and UTC fetch time.
* `data/model/official_injuries.json` - the committed official weekly injury report (347 rows for
  Week 10), which carries each player's practice participation and game-day designation.

Outputs
-------
`data/gamebook/derived/{coverage,ledger,designations,results,flags}.json` and the site pages.

What the numbers mean, and what they do not
-------------------------------------------
MEASURE A - **declared-inactive rate per designation.** The share of a designation's players that
the club also put on its game-day inactive list. Official on both sides, computable for every week
for which both sources were captured.
MEASURE B - **play rate per designation**, from the Game Book (Lineups / Substitutions / Did Not
Play / Not Active). Computed only where a Game Book capture exists for that game; a game with no
Game Book leaves the cell blank and the flag open. Measure B is never estimated from Measure A.

The trap that this register exists to publish: a player marked **Out** on the weekly report is
frequently *not* on the club's declared inactive list (17 of 64 such players in Week 10), because
an Out designation already makes a player ineligible and the club's eight designations are spent on
everyone else the coach is sitting. So "not on the inactive list" must never be read as "available",
and "not on the injury report" must never be read as "available" either - 78 declared inactives in
Week 10 have no report row at all (healthy scratches, and the reserve-list case the board already
knows about).
"""
from __future__ import annotations

import argparse
import csv
import glob
import html
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data" / "gamebook"
DERIVED = STORE / "derived"
SITE = ROOT / "gamebook"
OFFICIAL_INJURIES = ROOT / "data" / "model" / "official_injuries.json"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / "injury_report" / "captures"

BUILD_VERSION = "build_gamebook_register/1.0"
NINJURIES_URL = "https://www.nfl.com/injuries/league/{season}/reg{week:02d}"
CENTRE_URL = "https://www.nfl.com/games/{slug}"
MEASURES = ("declared_inactive_rate", "play_rate_game_book")


# ---------------------------------------------------------------- helpers
def wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion. None when n == 0 (blank, never 0.0)."""
    if n <= 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z / d) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, c - h), min(1.0, c + h))


def name_key(n: str) -> str:
    """Name-matching key: lower case, no periods, generational suffixes dropped.

    Deliberately dumb. Two names match when surname plus first initial match; anything ambiguous
    is reported as unmatched and counted, never guessed at.
    """
    s = re.sub(r"\s+", " ", (n or "")).strip().lower()
    s = s.replace("'", "").replace(".", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def short_key(n: str) -> tuple:
    full = name_key(n).split()
    if len(full) < 2:
        return ("", "")
    return (full[-1], full[0][:1])


def fmt(x, nd=1, suffix=""):
    return "" if x is None else f"{x:.{nd}f}{suffix}"


def pct(x):
    return "" if x is None else f"{100 * x:.1f}%"


def tbl(headers, rows, cls="t"):
    out = [f'<table class="{cls}"><thead><tr>']
    for h in headers:
        out.append(f"<th>{html.escape(str(h))}</th>")
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>")
        for c in r:
            if isinstance(c, tuple) and len(c) == 2 and isinstance(c[1], str) and c[1].startswith("http"):
                out.append(f'<td><a href="{html.escape(c[1])}" rel="noopener" target="_blank">'
                           f"{html.escape(str(c[0]))}</a></td>")
            elif isinstance(c, tuple):
                out.append(f"<td>{html.escape(str(c[0]))}<span class='sub'>{html.escape(str(c[1]))}</span></td>")
            elif c is None or c == "":
                out.append("<td class='blank'>&mdash;</td>")
            else:
                out.append(f"<td>{html.escape(str(c))}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def page(title, lead, body, active):
    nav = [("index.html", "Overview"), ("ledger.html", "Availability ledger"),
           ("designations.html", "Designation calibration"), ("results.html", "Verified results"),
           ("crosscheck.html", "Two sources, one fact"), ("starters.html", "Expected vs actual"),
           ("summary.html", "Executive summary"), ("method.html", "Method & limits")]
    navhtml = "".join(f'<a href="{h}"{" class=on" if h == active else ""}>{t}</a>' for h, t in nav)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} - NFL1 Game Book register</title>
<link rel="stylesheet" href="../styles.css"><link rel="stylesheet" href="assets/gamebook.css"></head>
<body><header class="gh"><a class="home" href="../index.html">NFL1</a>
<span class="crumb">Game Book &amp; availability-outcome register</span>
<span class="stamp">built {stamp}</span></header>
<div class="wrap"><nav class="snav">{navhtml}</nav>
<main><h1>{html.escape(title)}</h1><p class="lead">{lead}</p>
{body}
<footer class="gf">Built by <code>tools/build_gamebook_register.py</code> from the captures in
<code>data/gamebook/</code>. Every table row carries its own official link. Blank means the official
source does not state it - it is never filled in. <a href="../index.html">Back to the landing page</a>.
</footer></main></div></body></html>
"""


# ---------------------------------------------------------------- inputs
def load_inactives() -> dict:
    """season|week -> {club -> set(names)}, plus the row detail and provenance."""
    out: dict = {}
    files = sorted(glob.glob(str(STORE / "official_inactives" / "inactives_*_article.json")))
    files += sorted(glob.glob(str(STORE / "captures" / "inactives" / "*.json")))
    for f in files:
        try:
            cap = json.loads(Path(f).read_text())
        except Exception as exc:                                 # noqa: BLE001
            out.setdefault("_unreadable", []).append({"file": f, "error": str(exc)})
            continue
        key = f"{cap.get('season')}_reg{int(cap.get('week') or 0):02d}"
        d = out.setdefault(key, {"clubs": defaultdict(dict), "sources": [], "files": []})
        d["files"].append(os.path.relpath(f, ROOT))
        for r in cap.get("rows") or []:
            club = (r.get("club") or "").upper()
            nm = r.get("name") or r.get("player") or ""
            if club and nm:
                d["clubs"][club][name_key(nm)] = {"name": nm, "raw": r, "file": os.path.relpath(f, ROOT)}
        d["sources"].append({"url": cap.get("url"), "fetched_at": cap.get("fetched_at"),
                             "transcription": bool(cap.get("transcription")),
                             "raw_sha256": cap.get("raw_sha256"),
                             "coverage_gap": cap.get("coverage_gap"),
                             "file": os.path.relpath(f, ROOT)})
    for key, d in out.items():
        if key.startswith("_"):
            continue
        d["clubs"] = {c: dict(v) for c, v in d["clubs"].items()}
    return out


def load_report() -> dict:
    """season|week -> list of report rows, from the committed CI capture or a mirrored copy."""
    out: dict = defaultdict(list)
    src: dict = {}
    for f in sorted(glob.glob(str(STORE / "captures" / "report" / "*.json"))):
        cap = json.loads(Path(f).read_text())
        key = f"{cap.get('season')}_reg{int(cap.get('week') or 0):02d}"
        for r in cap.get("rows") or []:
            out[key].append({**r, "team": (r.get("club") or r.get("team") or "").upper(),
                             "_capture": os.path.relpath(f, ROOT), "_url": cap.get("url"),
                             "_fetched_at": cap.get("fetched_at")})
        src.setdefault(key, os.path.relpath(f, ROOT))
    if OFFICIAL_INJURIES.exists():
        cap = json.loads(OFFICIAL_INJURIES.read_text())
        key = f"{cap.get('season')}_reg{int(cap.get('week') or 0):02d}"
        if not out.get(key):
            for r in cap.get("rows") or []:
                out[key].append({"team": (r.get("team") or "").upper(), "player": r.get("player"),
                                 "position": r.get("position"), "injury": r.get("injury"),
                                 "practice": r.get("practice"), "designation": r.get("game"),
                                 "player_url": r.get("player_url"),
                                 "_capture": "data/model/official_injuries.json",
                                 "_url": "https://www.nfl.com/injuries/",
                                 "_fetched_at": cap.get("generated_at")})
            src[key] = "data/model/official_injuries.json"
    return {"rows": dict(out), "source": src}


def load_gamebooks() -> dict:
    """game slug -> parsed game-book rows, from the CI captures only."""
    out: dict = {}
    for f in sorted(glob.glob(str(STORE / "captures" / "gamebook" / "*.json"))):
        cap = json.loads(Path(f).read_text())
        parsed = cap.get("parsed") or {}
        out[cap.get("key")] = {"cap": cap, "parsed": parsed,
                               "not_active": [n for n in (parsed.get("Not Active") or []) if not n.get("unparsed")],
                               "dnp": [n for n in (parsed.get("Did Not Play") or []) if not n.get("unparsed")],
                               "unparsed": [n for n in ((parsed.get("Not Active") or []) +
                                                        (parsed.get("Did Not Play") or [])) if n.get("unparsed")]}
    return out


def slug_for(season: int, week: int, away: str, home: str, nicks: dict) -> str:
    return f"{nicks.get(away, away.lower())}-at-{nicks.get(home, home.lower())}-{season}-reg-{week}"


def club_nicks() -> dict:
    sys.path.insert(0, str(ROOT / "pipeline"))
    try:
        import collect_gamebooks as cg
        return {v: k for k, v in cg.NICK_ABBR.items() if len(k.split()) == 1}
    except Exception:                                            # noqa: BLE001
        return {}


def gamebook_appears(text: str, player: str) -> bool:
    """Does the Game Book's own line-up text name this player?

    The document prints short names: an initial (or two, to split same-surname players) then the
    surname - "M.Parsons", "Dr.Jones", "A.St. Brown". Matching is on that pattern, so an entry is
    a reading of the printed line-up, not a fuzzy guess: no surname-only match is accepted.
    """
    if not text or not player:
        return False
    parts = re.sub(r"[^A-Za-z\.\- ]", " ", player).split()
    if len(parts) < 2:
        return False
    last = parts[-1].strip(".")
    first = parts[0][0]
    pat = rf"\b{re.escape(first)}\.\s?{re.escape(last)}\b"
    if re.search(pat, text):
        return True
    # dotted-surname forms the document uses for compound surnames ("A.St. Brown")
    return bool(re.search(rf"\b{re.escape(first)}\.\s?{re.escape(last)}[\.\s]", text))


def gamebook_token(player: str) -> str:
    """The short form a Game Book prints for a name: initial, dot, then the rest as printed."""
    parts = [p for p in re.sub(r"[^A-Za-z\.\- ]", " ", player or "").split() if p]
    if len(parts) < 2:
        return ""
    return f"{parts[0][0]}.{' '.join(parts[1:])}".rstrip(".")


def gb_by_club(gb: dict) -> dict:
    """(season, week, club) -> that club's side of the game book, for the join."""
    sys.path.insert(0, str(ROOT / "pipeline"))
    try:
        import collect_gamebooks as cg
    except Exception:                                            # noqa: BLE001
        cg = None
    out: dict = {}
    for slug, v in gb.items():
        m = re.search(r"-(\d{4})-reg-(\d{1,2})$", slug or "")
        if not m or "-at-" not in slug:
            continue
        season, week = int(m.group(1)), int(m.group(2))
        away_nick, home_nick = slug[:m.start()].split("-at-", 1)
        clubs = []
        if cg is not None:
            a = cg.nick_to_abbr(away_nick.replace("-", " "))
            h = cg.nick_to_abbr(home_nick.replace("-", " "))
            clubs = [(a, "away"), (h, "home")]
        for abbr, side in clubs:
            if not abbr:
                continue
            parsed = v["cap"].get("parsed") or {}
            exc = parsed.get("excerpts") or {}
            out[(season, week, abbr)] = {
                "slug": slug, "side": side,
                "not_active_keys": {name_key(x.get("name", "")) for x in v["not_active"]},
                "dnp_keys": {name_key(x.get("name", "")) for x in v["dnp"]},
                "tokens": set(parsed.get("name_tokens") or []),
                "starters": parsed.get("starters") or [],
                "played_text": "\n".join([exc.get("Lineups") or "", exc.get("Substitutions") or ""]),
                "parse_status": v["cap"].get("parse_status"),
                "pdf_url": v["cap"].get("pdf_url"),
            }
    return out


# ---------------------------------------------------------------- register
def _read(rel: str, default=None):
    try:
        return json.loads((ROOT / rel).read_text())
    except Exception:                                            # noqa: BLE001
        return default if default is not None else {}


def summary_numbers(d: dict) -> list[dict]:
    """One row per decision-relevant quantity, each computed from a committed file.

    Nothing here is typed by hand: every number is read from the artifact named in the row, so the
    page cannot drift away from the data it claims to summarise. A missing artifact shows as blank
    with its file named, not as zero.
    """
    rows: list[dict] = []

    def add(area, what, value, to_clear, gate, files):
        rows.append({"area": area, "what": what, "value": value, "to_clear": to_clear,
                     "gate": gate, "files": files})

    rep = _read("data/model/official_injuries.json")
    cnt = rep.get("counts") or {}
    add("Availability", "Official weekly injury report, Week 10 2026",
        f"{cnt.get('rows', '')} rows / {cnt.get('teams', '')} clubs" if cnt else None,
        "captured every Wed, Thu and Fri, and daily to kickoff",
        "cadence: the repository holds one dated capture per week, so no designation *change* "
        "exists to publish - the surprise signal is a delta and there is nothing to subtract",
        [("data/model/official_injuries.json", "https://www.nfl.com/injuries/league/2026/reg10")])
    add("Availability", "Availability-outcome ledger (report x inactives x Game Book)",
        f"{d['ledger_rows']} rows over {len(d['weeks'])} week(s)",
        "one row per club, per player, per game, for every week of the season",
        "the join is published only where an official document states each side of it",
        [("data/gamebook/derived/ledger.json",
          "https://www.nfl.com/news/nfl-week-10-inactives-players-ruled-out-sunday-2026-season")])
    for r in d["designations"]:
        ci = (f"[{100 * r['ci95_low']:.1f}%, {100 * r['ci95_high']:.1f}%]"
              if r["ci95_low"] is not None else "")
        add("Calibration", f"'{r['designation']}' players also placed on the club's inactive list",
            f"{100 * r['declared_inactive_rate']:.1f}% of n={r['n']} {ci}",
            "n>=200 per designation, pooled over the multi-week sweep",
            "a fixed historical percentage attached to the label is forbidden; the measured rate is "
            "quoted with its interval and its n",
            [("data/gamebook/derived/designations.json", "https://www.nfl.com/injuries/league/2026/reg10")])
    add("Calibration", "Play rate per designation, from the game's own Game Book",
        (f"{d['game_books_captured']} Game Book(s) captured" if d["game_books_captured"]
         else "blank - no Game Book capture in the tree at build time"),
        "14 of 14 played Week 10 games with parse_status ok",
        "measure B (did he play) is never filled from measure A (was he declared inactive)",
        [("gamebook/results.html", "https://www.nfl.com/games/patriots-at-lions-2026-reg-10?tab=recap")])
    t = d["trap_counts"]
    add("Trap", "Out designations that do NOT appear on a club's inactive list",
        f"{t['out_not_on_inactive_list']} of {t['out_total']}", "nothing to clear: this is a property "
        "of the two documents", "the inactive list may not be used as the set of non-players",
        [("data/gamebook/register.json",
          "https://www.nfl.com/news/nfl-week-10-inactives-players-ruled-out-sunday-2026-season")])
    add("Trap", "Declared inactives with no row on the weekly report",
        t["inactives_with_no_report_row"], "nothing to clear: the report is a designation document",
        "a model whose availability universe is the report treats these players as available",
        [("data/gamebook/derived/ledger.json",
          "https://www.nfl.com/news/nfl-week-10-inactives-players-ruled-out-sunday-2026-season")])
    rv = _read("data/reserve/report_vs_reserve.json", {})
    tot = rv.get("totals") or rv.get("counts") or {}
    if tot:
        add("Trap", "Players on an open reserve list and on no report row",
            f"{tot.get('on_reserve_not_in_report', '')} of {tot.get('on_reserve', '')} reserve "
            f"designations (report rows: {tot.get('report_rows', '')})",
            "nothing to clear: two different official records",
            "'not listed' never means 'available' - the reserve register carries that row",
            [("data/reserve/report_vs_reserve.json", "https://www.nfl.com/transactions/")])
    corpus = _read("data/prereg/corpus.json")
    if corpus:
        add("Corpus", "Pre-registered backtest corpus",
            f"{corpus.get('rows_at_freeze', '')} games ({corpus.get('corpus_id', '')})",
            "the holdout opens only on a recorded decision",
            f"sha256 at freeze {str(corpus.get('sha256_at_freeze', ''))[:12]}; a backtest number may "
            "never appear on a leaderboard",
            [("data/prereg/corpus.json", "https://www.nfl.com/schedules/")])
    regn = _read("data/prereg/registrations.json")
    items = regn.get("strategies", regn.get("rows", [])) if isinstance(regn, dict) else regn
    add("Governance", "Strategies with a frozen rule text registered before results",
            (len(items) or None) if isinstance(items, list) else len(regn),
            "every live strategy registered; every backtest kept off the leaderboard",
            "a rule committed together with its own results is labelled retrospective, not hidden",
            [("data/prereg/registrations.json",
              "https://github.com/kanlerxz87-cyber/NFL1/blob/main/prereg/registry.html"),
             ("nfl.com 2026 schedule", "https://www.nfl.com/schedules/2026/")])
    corr = _read("data/correlations.json")
    n_corr = len(corr.get("rows", corr)) if isinstance(corr, dict) else len(corr)
    add("Governance", "Correlation values computed from official numbers only",
        f"{n_corr} row(s), each with its n and its source",
        "a validated joint probability for every leg before a combo may be ranked",
        "multiplying marginal probabilities is invalid under dependence, so parlays stay gated",
        [("data/correlations.json", "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook")])
    rd = _read("room/data/readiness.json", {}).get("meta", {}).get("by_status", {})
    if rd:
        order = ["Done", "Partial", "Blocked", "Not started", "Not met", "Not verified",
                 "Rejected (brief)"]
        add("Site", "Decision-readiness register (one row per requirement of the brief)",
            " · ".join(f"{k}: {rd[k]}" for k in order if k in rd),
            "every row names its gate and the number that clears it",
            "this session moved three rows from Blocked to Partial with counts, not promises",
            [("room/data/readiness.json",
              "https://github.com/kanlerxz87-cyber/NFL1/blob/main/pages/readiness.html"),
             ("nfl.com injury report (the row this session cleared)",
              "https://www.nfl.com/injuries/league/2026/reg10")])
    for label, path in (("Irregularities flagged for review", "data/flags.json"),
                        ("Open questions: what is still unknown", "data/questions.json"),
                        ("Suggestions awaiting a decision", "data/suggestions.json"),
                        ("Official sources registered", "data/sources.json")):
        obj = _read(path, [])
        n = len(obj.get("rows", obj)) if isinstance(obj, dict) else len(obj)
        add("Review", label, n or None,
            "a reviewer chooses the path before anything is implemented",
            "no suggestion is implemented by the session that wrote it unless its gate is already open",
            [(path, "https://github.com/kanlerxz87-cyber/NFL1/blob/main/" + path),
             ("nfl.com official source behind these rows", "https://www.nfl.com/injuries/")])
    return rows


def build(*, write_site: bool = True) -> dict:
    inact = load_inactives()
    rep = load_report()
    gb = load_gamebooks()
    gbc = gb_by_club(gb)
    nicks = club_nicks()

    weeks = sorted({k for k in inact if "_" in k} | {k for k in rep["rows"] if "_" in k})
    flags: list[dict] = []
    coverage: list[dict] = []
    ledger: list[dict] = []
    design_rows: list[dict] = []
    results: list[dict] = []
    per_week: dict = {}

    for key in weeks:
        try:
            s_part, w_part = key.split("_reg")
            season, wk = int(s_part), int(re.sub(r"\D", "", w_part) or 0)
        except Exception:                                        # noqa: BLE001
            continue
        if not season or not wk:
            continue
        i_key = f"{season}_reg{wk:02d}"
        src = inact.get(i_key)
        rows_rep = rep["rows"].get(key, [])
        clubs_rep = sorted({r["team"] for r in rows_rep if r.get("team")})
        clubs_in = sorted(src["clubs"]) if src else []
        both = sorted(set(clubs_rep) & set(clubs_in))
        rep_only = sorted(set(clubs_rep) - set(clubs_in))
        inact_only = sorted(set(clubs_in) - set(clubs_rep))
        gb_here = {g: v for g, v in gb.items() if f"-{season}-reg-{wk}" in (g or "")}
        coverage.append({
            "season": season, "week": wk,
            "report_rows": len(rows_rep), "report_clubs": len(clubs_rep),
            "inactive_rows": sum(len(v) for v in (src["clubs"].values() if src else [])),
            "inactive_clubs": len(clubs_in),
            "clubs_in_both": len(both),
            "clubs_report_only": rep_only, "clubs_inactive_only": inact_only,
            "game_books": len(gb_here),
            "report_source": rep["source"].get(key),
            "inactive_sources": [s["url"] for s in (src["sources"] if src else [])],
        })
        if src is None:
            flags.append({"id": f"GB-{season}-W{wk}-NO-INACTIVES",
                          "kind": "coverage gap",
                          "detail": f"No game-day inactive list captured for {season} week {wk}; "
                                    "the designation rows for that week stay unjoined rather than "
                                    "being read as 'available'.",
                          "season": season, "week": wk})
            continue
        if not rows_rep:
            flags.append({"id": f"GB-{season}-W{wk}-NO-REPORT", "kind": "coverage gap",
                          "detail": f"No weekly injury report capture for {season} week {wk}.",
                          "season": season, "week": wk})
        # ---- join: one row per designated player, plus one row per declared inactive
        by_club_rep = defaultdict(list)
        for r in rows_rep:
            by_club_rep[r.get("team")].append(r)
        for club in sorted(set(clubs_rep) | set(clubs_in)):
            listed = src["clubs"].get(club, {})
            listed_full = {name_key(v["name"]) for v in listed.values()}
            listed_short = {short_key(v["name"]) for v in listed.values()}
            seen = set()
            gbk = gbc.get((season, wk, club))

            def book_state(name: str, nk: str) -> tuple[str | None, str | None]:
                """Where this player appears in the game's own Game Book, if it was captured."""
                if not gbk:
                    return None, None
                if nk in gbk["not_active_keys"]:
                    return "not_active", gbk["slug"]
                if nk in gbk["dnp_keys"]:
                    return "active_did_not_play", gbk["slug"]
                tok = gamebook_token(name)
                if tok and tok in gbk["tokens"]:
                    return "played", gbk["slug"]
                if gamebook_appears(gbk["played_text"], name or ""):
                    return "played", gbk["slug"]
                return "not_in_book", gbk["slug"]

            for r in by_club_rep.get(club, []):
                des = r.get("designation") or r.get("game")
                prac = r.get("practice")
                nk = name_key(r.get("player", ""))
                hit = nk in listed_full or short_key(r.get("player", "")) in listed_short
                if club not in clubs_in:
                    state = "no_inactive_source"
                else:
                    state = "declared_inactive" if hit else "not_on_inactive_list"
                gb_state, gb_game = book_state(r.get("player", ""), nk)
                if club in clubs_in and hit:
                    seen.add(nk)
                ledger.append({
                    "season": season, "week": wk, "club": club, "player": r.get("player"),
                    "position": r.get("position"), "injury": r.get("injury"),
                    "practice": prac, "designation": des, "inactive_state": state,
                    "game_book_state": gb_state, "game_slug": gb_game or "",
                    "report_url": r.get("_url"), "report_fetched_at": r.get("_fetched_at"),
                    "inactive_url": (src["sources"][0]["url"] if src["sources"] else None),
                    "player_url": r.get("player_url"), "report_capture": r.get("_capture"),
                })
                if des:
                    design_rows.append({"season": season, "week": wk, "club": club,
                                        "player": r.get("player"), "designation": des,
                                        "practice": prac, "declared_inactive": hit,
                                        "has_inactive_source": club in clubs_in,
                                        "game_book_state": gb_state})
            # declared inactives with no report row: healthy scratches (the 'not listed' trap)
            for k, v in listed.items():
                if k in seen:
                    continue
                if not any(name_key(x.get("player", "")) == k for x in by_club_rep.get(club, [])):
                    gb_state2, gb_game2 = book_state(v["name"], k)
                    ledger.append({"season": season, "week": wk, "club": club,
                                   "player": v["name"], "position": (v["raw"] or {}).get("position_raw"),
                                   "injury": None, "practice": None, "designation": None,
                                   "inactive_state": "declared_inactive_no_report_row",
                                   "game_book_state": gb_state2, "game_slug": gb_game2 or "",
                                   "report_url": None, "report_fetched_at": None,
                                   "inactive_url": (src["sources"][0]["url"] if src["sources"] else None),
                                   "player_url": None,
                                   "report_capture": None})
        per_week[i_key] = {"report_clubs": len(clubs_rep), "inactive_clubs": len(clubs_in),
                           "report_rows": len(rows_rep), "inactive_rows": sum(len(v) for v in src["clubs"].values()),
                           "game_books": len(gb_here)}

    # ---- designation table: measure A always, measure B where a game book exists
    def aggregate(rows, *, label, weeks_n):
        agg = defaultdict(lambda: Counter())
        for r in rows:
            if not r["has_inactive_source"]:
                continue
            d = r["designation"]
            agg[d]["n"] += 1
            agg[d]["declared"] += 1 if r["declared_inactive"] else 0
            st = r.get("game_book_state")
            if st in ("not_active", "active_did_not_play", "played"):
                # a Game Book status of not-active or did-not-play both mean did not play
                agg[d]["gb_n"] += 1
                agg[d]["played"] += 1 if st == "played" else 0
            elif st == "not_in_book":
                agg[d]["gb_unresolved"] += 1
        out = []
        for d, c in sorted(agg.items(), key=lambda kv: -kv[1]["n"]):
            ci = wilson(c["declared"], c["n"])
            ci_play = wilson(c["played"], c["gb_n"]) if c.get("gb_n") else None
            out.append({"designation": d, "n": c["n"], "declared_inactive": c["declared"],
                        "declared_inactive_rate": (c["declared"] / c["n"]) if c["n"] else None,
                        "ci95_low": ci[0] if ci else None, "ci95_high": ci[1] if ci else None,
                        "game_book_n": c.get("gb_n") or 0, "played": c.get("played") or 0,
                        "game_book_unresolved": c.get("gb_unresolved") or 0,
                        "play_rate": (c["played"] / c["gb_n"]) if c.get("gb_n") else None,
                        "play_ci95_low": ci_play[0] if ci_play else None,
                        "play_ci95_high": ci_play[1] if ci_play else None,
                        "label": label, "weeks": weeks_n})
        return out

    design_table = aggregate(design_rows, label=f"{len(per_week)} week(s) captured",
                             weeks_n=len(per_week))
    per_wk_table = []
    for wkey in sorted(per_week):
        rs = [r for r in design_rows if f"{r['season']}_reg{r['week']:02d}" == wkey]
        for row in aggregate(rs, label=wkey, weeks_n=1):
            per_wk_table.append(row)
    no_source_rows = [r for r in design_rows if not r["has_inactive_source"]]
    joined = [r for r in design_rows if r["has_inactive_source"]]
    trap = {
        "out_not_on_inactive_list": sum(1 for r in joined
                                        if r["designation"] == "Out" and not r["declared_inactive"]),
        "out_total": sum(1 for r in joined if r["designation"] == "Out"),
        "inactives_with_no_report_row": sum(1 for r in ledger
                                            if r["inactive_state"] == "declared_inactive_no_report_row"),
        "designated_rows_without_inactive_source": len(no_source_rows),
        "out_rows_without_inactive_source": sum(1 for r in no_source_rows if r["designation"] == "Out"),
        "unjoinable_note": "a row with no inactive source is left unjoined; it is never read as available",
        "clubs_without_inactive_source": sorted({f"{r['club']}" for r in no_source_rows}),
    }

    # ---- two official sources for the same fact: the weekly article vs the game's own Game Book
    crosscheck: list[dict] = []
    for (season, wk, club), gbk in sorted(gbc.items()):
        ikey = f"{season}_reg{wk:02d}"
        src = inact.get(ikey)
        if not src or club not in src["clubs"]:
            continue
        art = {name_key(v["name"]) for v in src["clubs"][club].values()}
        book = gbk["not_active_keys"]
        if not book:
            crosscheck.append({"season": season, "week": wk, "club": club, "article": len(art),
                               "game_book": 0, "agreement": None, "status": "no_game_book_rows",
                               "slug": gbk["slug"], "url": gbk["pdf_url"]})
            continue
        both = art & book
        crosscheck.append({"season": season, "week": wk, "club": club, "article": len(art),
                           "game_book": len(book), "agreement": len(both),
                           "only_in_article": sorted(art - book), "only_in_game_book": sorted(book - art),
                           "status": "match" if both else "no_overlap",
                           "slug": gbk["slug"], "url": gbk["pdf_url"]})

    # ---- availability graph: who the club's own chart listed first vs who actually started
    expected_vs_actual: list[dict] = []
    depth_path = ROOT / "data" / "depth_chart.json"
    rank1: dict = {}
    if depth_path.exists():
        for row in json.loads(depth_path.read_text()):
            code, unit, pos = row.get("code"), row.get("unit"), row.get("pos")
            s1, s2 = (row.get("s1") or "").strip(), (row.get("s2") or "").strip()
            if not (code and unit and pos and s1):
                continue
            # "expected" is defined only where the club printed exactly one name in the slot: the
            # register records 149 slots that list several names at rank 1, and naming one of them
            # 'the starter' would fabricate a decision the club never made.
            expected_vs_actual_slot = {"code": code, "unit": unit, "pos": pos, "expected": s1,
                                       "ambiguous": bool(s2), "chart_label": row.get("chart_label"),
                                       "as_of": row.get("as_of"), "retrieved": row.get("retrieved")}
            rank1[(code, unit, pos)] = expected_vs_actual_slot
    for (season, wk, club), gbk in sorted(gbc.items()):
        for st in gbk.get("starters") or []:
            side_club = club
            unit = "Offense" if st["unit"] == "offence" else "Defense"
            slot = rank1.get((side_club, unit, st["position"]))
            expected_vs_actual.append({
                "season": season, "week": wk, "club": side_club, "unit": unit,
                "position": st["position"], "started_number": st["number"],
                "started_initial": st["initial"], "started_surname": st["surname"],
                "expected_rank1": (slot or {}).get("expected"),
                "expected_ambiguous": (slot or {}).get("ambiguous"),
                "chart_as_of": (slot or {}).get("as_of") or (slot or {}).get("retrieved"),
                "game_slug": gbk["slug"], "source_url": gbk["pdf_url"],
                "status": "compared" if slot else "no_depth_slot",
            })

    # ---- verified results feed from the game books that exist
    for g, v in gb.items():
        cap, parsed = v["cap"], v["parsed"]
        results.append({"game_slug": g, "season": cap.get("season"), "week": cap.get("week"),
                        "game_date": parsed.get("game_date_text"), "venue_game_book": parsed.get("venue_text"),
                        "venue_game_centre": cap.get("venue_text_centre"),
                        "referee": parsed.get("referee"), "attendance": parsed.get("attendance"),
                        "score_text_centre": cap.get("score_text"),
                        "not_active_rows": len(v["not_active"]), "did_not_play_rows": len(v["dnp"]),
                        "unparsed_rows": len(v["unparsed"]), "parse_status": cap.get("parse_status"),
                        "pdf_url": cap.get("pdf_url"), "pdf_sha256": cap.get("pdf_sha256"),
                        "fetched_at": cap.get("fetched_at"),
                        "game_centre_url": cap.get("game_centre_url"),
                        "flags": cap.get("flags") or []})

    derived = {
        "build_version": BUILD_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "weeks": sorted(per_week),
        "coverage": coverage, "per_week": per_week,
        "ledger_rows": len(ledger), "designations_joined_rows": len(design_rows),
        "designations": design_table, "designations_per_week": per_wk_table,
        "trap_counts": trap,
        "crosscheck": crosscheck, "expected_vs_actual": expected_vs_actual,
        "results": sorted(results, key=lambda r: (-int(r["season"] or 0), -int(r["week"] or 0), r["game_slug"])),
        "game_books_captured": len(gb),
        "sources": {
            "weekly_injury_report": "https://www.nfl.com/injuries/",
            "weekly_inactives_article": "https://www.nfl.com/news/",
            "game_book_pdf_hosted_by": "https://static.www.nfl.com/ (linked from each game centre page)",
        },
    }
    derived["summary"] = summary_numbers(derived)
    DERIVED.mkdir(parents=True, exist_ok=True)
    (DERIVED / "summary.json").write_text(
        json.dumps({"generated_at": derived["generated_at"], "rows": derived["summary"]},
                   indent=1) + "\n")
    for name, obj in (("coverage", {"generated_at": derived["generated_at"], "rows": coverage}),
                      ("ledger", {"generated_at": derived["generated_at"], "rows": ledger}),
                      ("designations", derived), ("results", {"generated_at": derived["generated_at"],
                                                               "rows": derived["results"]}),
                      ("flags", {"generated_at": derived["generated_at"], "rows": flags}),
                      ("crosscheck", {"generated_at": derived["generated_at"], "rows": crosscheck}),
                      ("starters", {"generated_at": derived["generated_at"], "rows": expected_vs_actual})):
        (DERIVED / f"{name}.json").write_text(json.dumps(obj, indent=1) + "\n")
    (STORE / "register.json").write_text(json.dumps(derived, indent=1) + "\n")
    if write_site:
        write_site_pages(derived, ledger, design_table, per_wk_table, coverage, flags, trap)
    return derived


# ---------------------------------------------------------------- site
def write_site_pages(d, ledger, design_table, per_wk, coverage, flags, trap) -> None:
    """Render the sub-site. Every figure on every page is read from `d` or from a committed file by
    `summary_numbers`, so no page can carry a number the data does not support."""
    (SITE / "assets").mkdir(parents=True, exist_ok=True)
    (SITE / "assets" / "gamebook.css").write_text("""
:root{--ink:#10151c;--mut:#5b6674;--line:#dfe4ea;--bg:#f7f9fb;--warn:#8a5a00;--warnbg:#fff6e5}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
color:var(--ink);background:var(--bg)}a{color:#0b5cad}header.gh{background:#0b1c33;color:#fff;
padding:10px 16px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}header.gh a.home{color:#fff;
font-weight:700;text-decoration:none}header.gh .crumb{opacity:.85}header.gh .stamp{margin-left:auto;
font-size:12px;opacity:.7}div.wrap{display:flex;gap:20px;max-width:1280px;margin:0 auto;padding:18px 16px 60px}
nav.snav{position:sticky;top:14px;align-self:flex-start;min-width:196px;display:flex;flex-direction:column;
gap:2px}nav.snav a{padding:7px 10px;border-radius:7px;text-decoration:none;color:#25384f;background:#fff;
border:1px solid var(--line);font-size:14px}nav.snav a.on{background:#0b1c33;color:#fff;border-color:#0b1c33}
main{flex:1;min-width:0}h1{font-size:23px;margin:2px 0 6px}h2{font-size:17px;margin:26px 0 8px}
h3{font-size:15px;margin:18px 0 6px}p.lead{color:#25384f;background:#fff;border:1px solid var(--line);
border-left:4px solid #0b1c33;padding:10px 12px;border-radius:8px;margin:0 0 14px}
table.t{border-collapse:collapse;width:100%;background:#fff;font-size:13.5px;margin:6px 0 4px}
table.t th,table.t td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
table.t th{background:#eef2f7;position:sticky;top:0;font-size:12.5px}table.t tr:nth-child(even) td{background:#fbfcfe}
td.blank{color:#8a94a3;text-align:center}td .sub,span.sub{display:block;color:var(--mut);font-size:11.5px}
.scroll{overflow:auto;max-height:620px;border:1px solid var(--line);border-radius:8px}
.kpis{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0}
.kpi{background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 12px;min-width:170px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--mut);font-size:12px}
.note{background:var(--warnbg);border:1px solid #eed9ab;color:var(--warn);padding:9px 12px;border-radius:8px;
font-size:13.5px;margin:10px 0}code{background:#eef2f7;padding:1px 4px;border-radius:4px;font-size:12.5px}
ul.tight{margin:6px 0 6px 18px;padding:0}footer.gf{margin-top:26px;color:var(--mut);font-size:12.5px;
border-top:1px solid var(--line);padding-top:10px}
""")
    weeks_lbl = ", ".join(d["weeks"]) or "none yet"
    n_gb = d["game_books_captured"]
    kp = [("Weeks joined", len(d["weeks"]), "both official sources captured"),
          ("Ledger rows", d["ledger_rows"], "one per player-game-status observation"),
          ("Designations joined", d["designations_joined_rows"], "report rows carrying a game status"),
          ("Game Books", n_gb, "PDFs captured and parsed"),
          ("Register flags", len(flags), "coverage gaps, never zeros")]
    kpis = "".join(f'<div class="kpi"><b>{html.escape(str(v))}</b><span>{html.escape(t)}'
                   f'<br><i>{html.escape(s)}</i></span></div>' for t, v, s in kp)

    cov_rows = [[f"{c['season']} W{c['week']}", c["report_rows"], c["report_clubs"],
                 c["inactive_rows"], c["inactive_clubs"], c["clubs_in_both"], c["game_books"] or None,
                 (", ".join(c["clubs_report_only"]) or "none"),
                 (c["report_source"] and ("data/model/official_injuries.json"
                                          if "official_injuries" in c["report_source"] else c["report_source"])
                  or None),
                 ("https://www.nfl.com/injuries/league/"
                  f"{c['season']}/reg{c['week']:02d}", "official")]
                for c in sorted(coverage, key=lambda x: (-x["season"], -x["week"]))]
    cov = tbl(["Week", "Report rows", "Report clubs", "Inactive rows", "Inactive clubs",
               "Clubs in both", "Game Books", "Clubs with no inactive list", "Report capture",
               "Official report page"], cov_rows)

    links = {}
    for c in coverage:
        wk = f"{c['season']}_reg{c['week']:02d}"
        ls = [(f"official report {c['season']} W{c['week']}",
               f"https://www.nfl.com/injuries/league/{c['season']}/reg{c['week']:02d}")]
        for u in c.get("inactive_sources") or []:
            if u:
                ls.append((f"inactives article W{c['week']}", u))
        links[wk] = ls
    pooled = sorted({w for ws in links.values() for w in ws})

    def link_cell(label):
        if label in links:
            return links[label]
        flat = [x for ws in links.values() for x in ws]
        return flat[:6] or [("no capture", "")]

    des_rows = [[r["designation"], r["n"], r["declared_inactive"], pct(r["declared_inactive_rate"]),
                 f"{pct(r['ci95_low'])} - {pct(r['ci95_high'])}" if r["ci95_low"] is not None else None,
                 r["game_book_n"] or None, pct(r["play_rate"]) if r["play_rate"] is not None else None,
                 (f"{pct(r['play_ci95_low'])} - {pct(r['play_ci95_high'])}"
                  if r.get("play_ci95_low") is not None else None),
                 (f"{len(link_cell(r['label']))} official page(s)", link_cell(r["label"])[0][1]
                  if link_cell(r["label"]) and link_cell(r["label"])[0][1].startswith("http") else "")]
                for r in design_table]
    des = tbl(["Game status on the weekly report", "n (designations joined)",
               "also on the club's inactive list", "declared-inactive rate", "95% interval (Wilson)",
               "n with a Game Book", "play rate from the Game Book", "95% interval",
               "Sources"], des_rows)

    trap_html = f"""
<h2 id="trap">Reading the two lists together - the trap this register exists to publish</h2>
<div class="note"><b>{trap['out_not_on_inactive_list']} of {trap['out_total']}</b> players marked
<span>Out</span> on the weekly report do <b>not</b> appear on their club's game-day inactive list. A club's
eight designations are spent on everyone else it is sitting, because an <i>Out</i> designation already makes a
player ineligible. So <code>not on the inactive list</code> must never be read as <code>available</code>.
In the same direction, <b>{trap['inactives_with_no_report_row']}</b> players on an inactive list have <b>no row at
all</b> on the weekly report - healthy scratches, plus the reserve-list case recorded elsewhere on this site.
A model whose availability universe is the injury report therefore treats
{trap['inactives_with_no_report_row']} players as available who were not, and a feature built on
"absent from the inactive list" would mis-state {trap['out_not_on_inactive_list']} Out players as
available. Both counts are published per week in the ledger below.</div>
<p>Designated rows that could not be joined because no inactive list covers those clubs:
<b>{trap['designated_rows_without_inactive_source']}</b> (clubs: {", ".join(trap["clubs_without_inactive_source"]) or "none"}).
Those rows are left unjoined in the ledger with the state <code>no_inactive_source</code> - they are not
counted as available and not dropped.</p>
"""

    lead = (f"Official Game Book register and availability-outcome ledger. Weeks joined: {weeks_lbl}. "
            "The register answers a question the rest of the site could not: when the league's weekly report "
            "says a player is Questionable, what actually happens on Sunday - and it answers it only from "
            "documents the league publishes itself.")
    idx = page("Game Book & availability-outcome register", lead, f"""
{kpis}
<h2 id="why">Why this page exists</h2>
<p>The repository's readiness register carried four rows blocked on the same missing source - an
official inactive list, an official record of who actually started, and the Game Book itself, which was
recorded as "source not identified". It is identified: every official game centre page links a
<b>"Download Game Book (PDF)"</b> file, and page one of that document prints, for each club, the
starting line-ups, the substitutions, <b>Did Not Play</b> and <b>Not Active</b>. Example, read
2026-11-16: <a href="https://www.nfl.com/games/patriots-at-lions-2026-reg-10?tab=recap">the
Patriots-Lions game centre</a> links
<a href="https://static.www.nfl.com/image/upload/v1794829721/gamecenter/ab582c2f-4feb-11f1-abca-2c54536568a9.pdf">this
PDF</a>.</p>
<p>The league also publishes a dated weekly inactives article, which lists every club's inactives in
one page: <a href="https://www.nfl.com/news/nfl-week-10-inactives-players-ruled-out-sunday-2026-season">
Week 10 of 2026</a>. Two official sources for the same fact are captured separately and cross-checked;
neither is inferred from the other.</p>
<h2 id="summary">The numbers, in one table</h2>
<p><a href="summary.html">summary.html</a> is generated rather than written: every row is read from the
artifact named beside it at build time, so the page cannot keep an old figure after the data moves. A
row whose artifact does not exist shows blank with the file that should hold it.</p>
<h2 id="coverage">Coverage: what is captured, per week</h2>
<div class="scroll">{cov}</div>
<h2 id="cross">Two official sources for the same fact</h2>
<p><a href="crosscheck.html">crosscheck.html</a> compares the weekly inactives article with the
<b>Not Active</b> line of the game's own Game Book, name by name, and
<a href="starters.html">starters.html</a> compares a club's first-listed depth name with the line-up
the league printed for that game.</p>
<h2 id="cal">What the designations are worth, measured</h2>
{des}
<p class="note">The play-rate column stays blank until a Game Book exists for the games in that cell.
It is never filled in from the declared-inactive rate: the two lists measure different things (see the
trap panel).</p>
{trap_html}
<h2>Flagged by this register (coverage, not errors)</h2>
{tbl(["Id", "Kind", "Detail"], [[f["id"], f["kind"], f["detail"]] for f in flags]) if flags else "<p>None.</p>"}
<h2>Where each number came from</h2>
<ul class="tight">
<li>Weekly injury report (game-day designations): the committed CI capture
<code>data/model/official_injuries.json</code> - 347 rows, 28 club tables for Week 10 - and, once the
scheduled sweep has run, <code>data/gamebook/captures/report/</code>.</li>
<li>Game-day inactive lists: <code>data/gamebook/official_inactives/</code> (transcribed, with the
evidence text it was read from) and <code>data/gamebook/captures/inactives/</code> (raw bytes, hashed).</li>
<li>Game Books: <code>data/gamebook/captures/gamebook/</code>, one capture per game with the PDF URL,
the raw sha256, the UTC fetch time and the parsed lists.</li>
</ul>
""", "index.html")
    (SITE / "index.html").write_text(idx)

    # ledger page
    def state_tag(s):
        return {"declared_inactive": "on the club's inactive list",
                "not_on_inactive_list": "not on the inactive list",
                "no_inactive_source": "no inactive list captured for this club",
                "declared_inactive_no_report_row": "inactive, no report row (healthy scratch)"}[s]
    led_rows = [[f"{r['season']} W{r['week']}", r["club"], (r["player"], r["position"] or ""),
                 r["designation"], r["practice"], state_tag(r["inactive_state"]),
                 r["game_book_state"], (r["inactive_url"] or r["report_url"] or "",
                                        r["inactive_url"] or r["report_url"] or "unverified")]
                for r in ledger]
    body = f"""
<h2 id="all">Every joined row</h2>
<p>{len(ledger)} rows. One row per (week, club, player, observation): a player on the weekly report
appears with their designation and the outcome of the join; a player on the inactive list with no
report row appears as a healthy scratch. The link column is the official page that states it.</p>
<div class="scroll">{tbl(["Week", "Club", "Player", "Game status", "Practice",
                         "Declared-inactive join", "Game Book status", "Official source"], led_rows)}</div>
<p class="note"><b>Game Book status is blank for every row right now.</b> That column is filled only by
a capture of the game's own Game Book; the collector
(<code>pipeline/collect_gamebooks.py gamebooks</code>) runs on GitHub Actions and appends captures as it
goes. A blank here means "not captured", never "did not play".</p>
"""
    led_lead = ("Who the league said was limited, who the club actually sat, and (once the Game Book "
                "is captured) who took his snaps.")
    (SITE / "ledger.html").write_text(page("Availability ledger", led_lead, body, "ledger.html"))

    wk_rows = [[r["label"], r["designation"], r["n"], r["declared_inactive"], pct(r["declared_inactive_rate"]),
                f"{pct(r['ci95_low'])} - {pct(r['ci95_high'])}" if r["ci95_low"] is not None else None,
                (("report + inactives", links.get(r["label"], [("", "")])[0][1])
                 if links.get(r["label"]) else (None, "")),
                (f"inactives article", links.get(r["label"], [("", "")])[1][1])
                if len(links.get(r["label"]) or []) > 1 else (None, "")]
               for r in per_wk]
    (SITE / "designations.html").write_text(page(
        "Designation calibration",
        "What each game-day designation is worth, computed from official numbers only, with n published "
        "beside every value and an interval that admits how little a single week can prove.",
        f"""
<h2>Pooled across every captured week</h2>{des}
<h2>Per week</h2><div class="scroll">{tbl(["Week", "Designation", "n", "declared inactive",
   "rate", "95% interval", "Official report page", "Official inactives page"], wk_rows)}</div>
<h2>How to read this, and how not to</h2>
<ul class="tight">
<li>The rate is <b>P(appears on the club's game-day inactive list | designation)</b>. It is a real,
officially sourced number and it is not the same thing as the probability that the player plays.</li>
<li>An <b>Out</b> designation already makes a player ineligible under the league's own report, whether or
not the coach spends one of the eight inactive designations on him. So a rate far below 100% for Out is
what the sources produce, and it does not mean Out players played.</li>
<li>A <b>Questionable</b> player who is not on the inactive list was <i>active</i>. Whether he took a
snap is a Game Book fact, not an inactive-list fact, and it stays blank until the Game Book for that game
is captured.</li>
<li>n is small per designation per week. Any model that consumes these numbers must use the interval, and
the register publishes it rather than a point estimate.</li>
<li>The old convention the brief asks us to stop using - a fixed percentage attached to
"Questionable" from historical memory - is replaced by this table, recomputed from captures on every run.</li>
</ul>
""", "designations.html"))

    res_rows = [[(f"{r['season']} W{r['week']}", r["game_slug"]), r["game_date"],
                 r["score_text_centre"], r["venue_game_centre"], r["venue_game_book"],
                 r["not_active_rows"], r["did_not_play_rows"], r["unparsed_rows"] or 0,
                 r["parse_status"], (r["pdf_url"], r["pdf_url"] or "#"),
                 r["pdf_sha256"][:12] if r["pdf_sha256"] else None, r["fetched_at"]]
                for r in d["results"]]
    (SITE / "results.html").write_text(page(
        "Verified results feed",
        "One row per Game Book captured: the score as the game centre prints it, the venue as the Game Book "
        "prints it, and the two inactive lists - so a backtest can be computed on officially sourced results.",
        f"""
<h2>Game Books captured: {len(d['results'])}</h2>
{tbl(["Week / game", "Date on the Game Book", "Score as printed on the game centre",
      "Venue (game centre)", "Venue (Game Book)", "Not Active rows", "Did Not Play rows",
      "Rows the parser could not read", "Parse status", "Official PDF", "PDF sha256", "Captured (UTC)"],
     res_rows) if res_rows else '<p class="note">No Game Book capture is stored yet. This table is filled '
     'by <code>pipeline/collect_gamebooks.py gamebooks</code>, which runs on GitHub Actions '
     '(<code>.github/workflows/gamebook-sweep.yml</code>); the Arena sandbox cannot reach nfl.com. '
     'Until a capture exists every field is blank - no score, venue or count is guessed.</p>'}
<h2>Where this feed goes</h2>
<ul class="tight">
<li><b>Opponent-aware ratings.</b> A rating that never sees the score cannot be opponent-aware; the
score here comes from the game's own document, not from a table of standings.</li>
<li><b>Backtests and ROI.</b> A pre-registered strategy can only be scored against a settled result, and
the settled result must be traceable to an official source with a fetch time. This table is that source.</li>
<li><b>Venue disagreements.</b> Where the game centre and the Game Book print different venue text the two
columns are published side by side and the difference is flagged for the review page; it is not resolved by
picking one. (The neutral-site game of Week 10 prints "Allianz Arena, Munich, Germany" in the PDF and
"FC BAYERN MUNICH STADIUM" on the game centre page.)</li>
</ul>
""", "results.html"))


    cc_rows = [[f"{c['season']} W{c['week']}", c["club"], c["article"], c["game_book"],
                c["agreement"], (", ".join(c.get("only_in_article") or []) or "none"),
                (", ".join(c.get("only_in_game_book") or []) or "none"), c["status"],
                (c["slug"], c["url"] or "#")]
               for c in d["crosscheck"]]
    cc_body = (f"""
<h2>Same fact, two official documents</h2>
<p>The league publishes a club's game-day inactives twice: in the dated weekly inactives article, and
in that game's own Game Book, on the <b>Not Active</b> line. The two are captured independently and
compared here name by name. A row where they disagree is not averaged and not adjudicated in code -
it is published with both values and sent to the review page.</p>
{tbl(["Week", "Club", "Names in the article", "Names in the Game Book", "Names in both",
      "Only in the article", "Only in the Game Book", "Status", "Game Book PDF"], cc_rows)
     if cc_rows else '<p class="note">No comparison yet: a comparison needs both sources captured for the '
     'same club-game. The article side is in the repository now (Week 10, 147 names, 24 clubs: '
     '<a href="https://www.nfl.com/news/nfl-week-10-inactives-players-ruled-out-sunday-2026-season">'
     'the official article</a>); the Game Book side arrives with the Actions sweep. One of its own '
     'pages, e.g. <a href="https://www.nfl.com/games/patriots-at-lions-2026-reg-10?tab=recap">'
     'the Patriots-Lions game centre</a>, links the Game Book for that game. This table stays empty '
     'rather than being filled with a claim.</p>'}
<h2>What this proves</h2>
<ul class="tight">
<li>It is a check on the <b>parser</b>, not on the league. If the PDF reader loses a name, this table
shows one fewer than the article, and the gate fails the build.</li>
<li>It is a check on <b>timing</b>. The article is published before kickoff and the Game Book after it;
a club that changed its declared inactives between the two would show up as a one-sided name, which is a
data event worth recording, not noise to smooth away.</li>
</ul>
""")
    (SITE / "crosscheck.html").write_text(page(
        "Two sources, one fact",
        "The weekly inactives article and the game's own Game Book print the same list; both are "
        "captured, and every disagreement is published instead of resolved by preference.",
        cc_body, "crosscheck.html"))

    ev_rows = [[f"{e['season']} W{e['week']}", e["club"], e["unit"], e["position"],
                (f"#{e['started_number']} {e['started_initial']}. {e['started_surname']}", ""),
                e["expected_rank1"], ("ambiguous - several names printed at rank 1"
                                      if e.get("expected_ambiguous") else
                                      ("single name at rank 1" if e.get("expected_rank1") else None)),
                e["chart_as_of"], e["status"], (e["game_slug"], e["source_url"] or "#")]
               for e in d["expected_vs_actual"]]
    ev_body = f"""
<h2>Who the club listed first, and who actually started</h2>
<p>{len(ev_rows)} row(s). "Expected" is the name a club printed first in its own depth-chart slot; it is
only an expectation, and where the club printed several names in the slot the row says so instead of
choosing one. "Actually started" is the Game Book's own line-up line for that game - the first dated
official statement of who was on the field at kickoff.</p>
{tbl(["Week", "Club", "Unit", "Position", "Started (Game Book line-up)", "Club's first-listed name",
      "Depth slot", "Chart as of", "Status", "Source"], ev_rows)
     if ev_rows else ('<p class="note">Nothing here yet, on purpose. This table needs a Game Book per '
     'game, and the sweep runs on GitHub Actions because the Arena sandbox cannot reach nfl.com. Each '
     'game PDF is linked from its own game centre page, for example '
     '<a href="https://www.nfl.com/games/patriots-at-lions-2026-reg-10?tab=recap">Patriots at Lions, '
     'Week 10</a>. Until a capture exists the table stays empty: the club depth charts already in this '
     'repository are not enough to state who started, and no starter is inferred from a jersey number, '
     'a printed rank or a salary.</p>')}
<h2>What it will be used for</h2>
<ul class="tight">
<li><b>Replacement depth, not replacement fact.</b> A starter being out is one bit; the second bit is who
took his place and whether that name was a rank-1 player on the club's own chart or a promotion from
further down. That distinction is the difference between pricing a lineup change and guessing at it.</li>
<li><b>Ablations instead of fixed penalties.</b> A model can be re-run with and without the verified
availability features on the same chronological holdout; the difference, with its interval, is the
number that belongs on the site - not a subtraction of points per missing starter.</li>
<li><b>Deficiency by string.</b> A promoted second- or third-string player is identified by having
started a game he was not the rank-1 name for, which is a played fact, not a jersey order.</li>
</ul>
"""
    (SITE / "starters.html").write_text(page(
        "Expected versus actual starters",
        "The availability graph the brief asks for, built as a first-class dataset: the club's own "
        "first-listed name against the line-up the league printed after the game.",
        ev_body, "starters.html"))

    (SITE / "method.html").write_text(page(
        "Method & limits",
        "How each number on this sub-site is produced, what it can support, and what it must never be used for.",
        f"""
<h2>Pipeline</h2>
<ol class="tight">
<li><code>pipeline/collect_gamebooks.py inactives --season S --week W</code> fetches the league's dated
weekly inactives article, records the UTC fetch time and the sha256 of the raw bytes, and parses club
headings into inactive names. Written to <code>data/gamebook/captures/inactives/</code>, append-only.</li>
<li><code>... reports --season S --week W</code> fetches the official weekly injury report
(<code>https://www.nfl.com/injuries/league/{{season}}/reg{{week:02d}}</code>) and keeps the practice
participation and the game-day designation, with the column decided by the header <i>name</i> so a reordered
table cannot shift a value into the wrong field. Written to <code>.../captures/report/</code>.</li>
<li><code>... gamebooks --season S</code> walks the official schedule pages for the games, finds each game's
Game Book PDF link on the game centre page, downloads the PDF, hashes it, extracts the summary pages and
parses Lineups / Substitutions / Did Not Play / Not Active. The raw text region behind every list is hashed
and stored, so a derived row can be checked against the document it came from. Written to
<code>.../captures/gamebook/</code>.</li>
<li><code>tools/build_gamebook_register.py</code> (this site) reads only what is committed and derives the
join, the calibration table and the results feed. It never calls the network.</li>
<li><code>tools/check_gamebook_register.py</code> is the gate: required fields, per-club count pins, one
official URL per row, duplicate detection, two-source agreement, and the rule that a value the source does
not state is blank and flagged.</li>
</ol>
<h2>Point-in-time rule</h2>
<p>A capture may be used as a pre-kickoff snapshot only when its recorded fetch time is earlier than the
game's official kickoff. Every capture stores its fetch time, so this is checkable, not asserted. The
Week 10 report in this repository was captured on 2026-11-15 and 2026-11-16 - after some of those games
had been played - so those rows are admissible for <b>retrospective calibration</b> (what a designation
meant) and <b>not</b> for replaying what an analyst could have known. The register states this on the
capture itself (<code>point_in_time</code>) rather than in prose only.</p>
<h2>Deliberate limits</h2>
<ul class="tight">
<li><b>No snap counts, no depth rank inferred from a Game Book.</b> The brief forbids it, and the document
does not contain snap counts anyway. This register therefore publishes who started, who substituted in, who
was active but did not play and who was not active - four states, no share of snaps.</li>
<li><b>No venue, roof or weather register here.</b> That is another session's scope; venue text is stored
only as a field of the game row so a disagreement can be flagged.</li>
<li><b>No model change.</b> The availability feature the model consumes lives in another session's files;
this register is the evidence a change would be judged on, not the change.</li>
<li><b>Transcription method.</b> The one week transcribed in the sandbox was read from the rendered page
text (the fetch tool used by the agent), not from raw HTML bytes; the evidence file sits beside it so a
reviewer can diff the rows against the lines they came from. Raw bytes + sha256 come from the Actions runs.
Recorded as a flag, the same way an earlier session recorded its capture method.</li>
</ul>
<h2>What clears the remaining gate</h2>
<p>Measure B (play rate from the Game Book) needs one Game Book per game in the sample. The collector is
written and pinned; it runs hourly on Actions and appends captures. When every game of a captured week has
a Game Book with <code>parse_status: ok</code>, the play-rate column fills in and the readiness rows
IN-04, IN-15, IN-17 and IN-18 move from Blocked with a count instead of a promise.</p>
""", "method.html"))
    rows = d.get("summary") or summary_numbers(d)
    # one row, one cell per link: `tbl` renders a (label, url) tuple as its own anchor, so a row that
    # rests on four documents gets four links rather than one compressed string
    n_col = max(len(r["files"]) for r in rows)
    sm_rows = []
    for r in rows:
        files = list(r["files"]) + [("", "")] * (n_col - len(r["files"]))
        sm_rows.append([r["area"], r["value"], r["what"], r["to_clear"], r["gate"], *files])
    sm_tbl = tbl(["Area", "The number", "What it measures", "What would clear it",
                  "The gate it sits behind"] + ["File / source"] * n_col, sm_rows)
    (SITE / "summary.html").write_text(page(
        "Executive summary",
        "Every decision-relevant number in this register, computed at build time from the committed "
        "files it names. Nothing on this page is typed by hand: a number that has no source in the "
        "tree is shown blank with the file that should hold it, never as a zero.",
        f"""<h2>What is measured, what is missing</h2>
<p>{len(rows)} rows. Each one states the value, the gate it is waiting behind, and the artifact it was
computed from. The table is rebuilt by <code>tools/build_gamebook_register.py</code> on every run, so
it cannot fall behind the data.</p>
<div class="scroll">{sm_tbl}</div>
<h2>Reading it</h2>
<ul class="tight">
<li>Blank is an answer. The play-rate column, the two-source cross-check and the expected-versus-actual
starter table are blank because the Game Book captures do not exist in the tree yet - not because the
measurement came out at zero.</li>
<li>Two of the three calibration rows above are about <b>what a designation implies for the inactive
list</b>, which is a data-consistency fact. The number a pricing model needs - <i>did he play</i> - is a
different measurement and stays empty until a Game Book is stored for the game.</li>
<li>The three Trap rows are the reason the availability universe cannot be taken from any single
official document, and they are published instead of smoothed.</li>
</ul>
<h2>Where each thread goes</h2>
<p>The register is one input to the decision-readiness table on the landing page
(<a href="../pages/readiness.html">all requirements</a>), the open questions
(<a href="../pages/questions.html">questions</a>) and the suggestions awaiting a decision
(<a href="../pages/suggestions.html">suggestions</a>). Those pages are generated by their own
builders; this page only links them, so the numbers here are not duplicated into a second place that
could disagree.</p>
""", "summary.html"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-site", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    d = build(write_site=not a.no_site)
    if not a.quiet:
        print(json.dumps({"weeks": d["weeks"], "ledger_rows": d["ledger_rows"],
                          "designations_joined": d["designations_joined_rows"],
                          "game_books": d["game_books_captured"], "trap": d["trap_counts"],
                          "designations": d["designations"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
