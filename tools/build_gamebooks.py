#!/usr/bin/env python3
"""build_gamebooks.py — parse the captured Week 10 Game Books and build the gamebooks/ sub-site.

Session d9e28eb2-nfl1 (G5).  Run from the repository root:

    python3 tools/build_gamebooks.py            # parse + build
    python3 tools/build_gamebooks.py --check    # build, then fail if anything changed

What it reads
------------
  data/gamebooks/source.json     official registry (game-centre + PDF URLs, scores, hashes)
  data/gamebooks/manifest.json   sha256 of every raw capture
  data/gamebooks/raw/*.txt       verbatim transcriptions of the official Game Book PDFs
  data/snapshots/injury_report/captures/*.json   official pre-game injury read (for the match)

What it writes
--------------
  data/gamebooks/parsed.json      structured lineups / Did Not Play / Not Active per game
  data/gamebooks/injury_match.json  every Not Active player matched to the official injury read
  gamebooks/*.html + style.css    the published sub-site

Honesty rules enforced here
---------------------------
* Only text printed in the raw capture is bound to a club.  Label rows whose content is a
  shifted substitution list (more than 10 entries, documented in each file's extraction_note)
  are NOT bound to the Did Not Play / Not Active label they sit next to.
* When a section label did not survive the extraction (CAR, KC) the structured field is null
  and a flag is raised; nothing is reconstructed.
* San Francisco's Dallas defensive starters print without names in the extraction; the name
  stays blank and a flag is raised.
* Every published row links the official PDF and the raw capture it came from.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "gamebooks", "raw")
OUT_DIR = os.path.join(ROOT, "gamebooks")

LABELS = ("Did Not Play", "Not Active")
SUBS_LEN = 10  # entry count above which a label-row cell is the shifted substitution list

# --- small helpers -------------------------------------------------------


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: str, obj: object) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def cells(row: str) -> list[str]:
    """Non-empty cells of a markdown table row."""
    if not row.startswith("|"):
        return []
    parts = [p.strip() for p in row.strip().strip("|").split("|")]
    return [p for p in parts if p]


# --- player-row patterns -------------------------------------------------

RE_POS_NAME = re.compile(r"^([A-Z][A-Z/]{0,4})\s+(\d+\s+.+)$")       # "WR 14 A.Williams" / "LOT 75 O.Brown"
RE_POS = re.compile(r"^[A-Z][A-Z/]{0,4}$")                          # standalone position cell
RE_NUM_NAME = re.compile(r"^(\d+)\s+(.+)$")                          # "14 A.Williams"
RE_NUM = re.compile(r"^\d+$")                                        # standalone number cell


def parse_player_cells(cs: list[str]) -> list[dict] | None:
    """Return 4 players [away-off, away-def, home-off, home-def] or None if not a lineup row."""
    n = len(cs)
    # 8-cell: (pos, "num name") x 4
    if n == 8:
        out = []
        for i in range(0, 8, 2):
            if not RE_POS.match(cs[i]):
                return None
            m = RE_NUM_NAME.match(cs[i + 1])
            if not m:
                return None
            out.append({"pos": cs[i], "num": m.group(1), "name": m.group(2)})
        return out
    # 4-cell inline: "POS NUM NAME" x 4
    if n == 4:
        out = []
        for c in cs:
            m = RE_POS_NAME.match(c)
            if not m:
                return None
            inner = RE_NUM_NAME.match(m.group(2))
            if not inner:
                return None
            out.append({"pos": m.group(1), "num": inner.group(1), "name": inner.group(2)})
        return out
    # 12-cell triples (pos, num, name) x 4 — San Francisco format
    if n == 12:
        out = []
        for i in range(0, 12, 3):
            if not (RE_POS.match(cs[i]) and RE_NUM.match(cs[i + 1])):
                return None
            out.append({"pos": cs[i], "num": cs[i + 1], "name": cs[i + 2]})
        return out
    # 11-cell: triples x3 + dangling (pos, num) — Dallas defense names absent from extraction
    if n == 11:
        out = []
        for i in range(0, 9, 3):
            if not (RE_POS.match(cs[i]) and RE_NUM.match(cs[i + 1])):
                return None
            out.append({"pos": cs[i], "num": cs[i + 1], "name": cs[i + 2]})
        if RE_POS.match(cs[9]) and RE_NUM.match(cs[10]):
            out.append({"pos": cs[9], "num": cs[10], "name": ""})
            return out
        return None
    return None


# --- per-game parse ------------------------------------------------------


def parse_game(path: str, meta: dict) -> dict:
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    flags: list[dict] = []
    has_note = any(l.startswith("extraction_note:") for l in lines)

    # ---- officials / weather / attendance (best effort, never inferred)
    text = "\n".join(lines)
    m = re.search(r"Referee:\s*([A-Za-z'\-]+,\s*[A-Za-z.\'\-]+)", text)
    referee = m.group(1).strip() if m else None
    m = re.search(r"Game Weather:\s*([^|\n]+)", text)
    weather = m.group(1).strip() if m else None
    att = re.findall(r"Paid Attendance:?\s*\|?\s*([\d][\d,.]*)", text)
    attendance = None
    if att:
        comma = [a for a in att if "," in a]
        attendance = comma[0] if comma else att[0]

    # ---- lineups
    start = None
    for i, l in enumerate(lines):
        if "Lineups" in l and l.startswith("|"):
            start = i
            break
    if start is None:  # KC-style prose header: first table row after an officials line
        last_off = max((i for i, l in enumerate(lines) if "Referee:" in l), default=-1)
        for i in range(last_off + 1, len(lines)):
            if lines[i].startswith("| "):
                start = i
                break

    lineups: list[list[dict]] = []
    lineups_end = None
    if start is not None:
        for i in range(start, len(lines)):
            l = lines[i]
            if i > start and any(lab in l for lab in LABELS + ("Substitutions",)):
                lineups_end = i
                break
            if not l.startswith("|"):
                continue
            cs = cells(l)
            players = parse_player_cells(cs)
            if players:
                lineups.append(players)
        if lineups_end is None:
            lineups_end = len(lines)

    away, home = meta["away"]["abbr"], meta["home"]["abbr"]
    away_name, home_name = meta["away"]["name"], meta["home"]["name"]

    structured = None
    if len(lineups) == 11:
        structured = {
            "away": {"name": away_name,
                     "offense": [r[0] for r in lineups],
                     "defense": [r[1] for r in lineups]},
            "home": {"name": home_name,
                     "offense": [r[2] for r in lineups],
                     "defense": [r[3] for r in lineups]},
        }
        # name-blank flags (San Francisco extraction)
        for side in ("away", "home"):
            for unit in ("offense", "defense"):
                for p in structured[side][unit]:
                    if p["name"] == "":
                        flags.append({
                            "code": "LINEUP_NAME_BLANK",
                            "side": side, "unit": unit,
                            "pos": p["pos"], "num": p["num"],
                            "detail": "Starter name absent from the PDF text extraction; "
                                      "position and number printed, name blank (not inferred).",
                        })
    else:
        flags.append({
            "code": "LINEUPS_INCOMPLETE",
            "detail": f"parsed {len(lineups)} lineup rows, expected 11; "
                      "see raw capture for the verbatim table.",
        })

    # ---- Did Not Play / Not Active zones (table rows only)
    dnp_idx = na_idx = None
    for i, l in enumerate(lines):
        if l.startswith("|") and dnp_idx is None and "Did Not Play" in l:
            dnp_idx = i
        elif l.startswith("|") and dnp_idx is not None and na_idx is None and "Not Active" in l:
            na_idx = i
            break
    if dnp_idx is None:
        flags.append({
            "code": "STATUS_LABELS_ABSENT",
            "detail": "No Did Not Play / Not Active table labels survived this extraction; "
                      "structured status fields are null and point at the raw capture.",
        })

    def zone(lo: int, hi: int) -> dict:
        result = {"away": None, "home": None}
        for i in range(lo, hi):
            l = lines[i]
            if not l.startswith("|"):
                continue
            cs = cells(l)
            label_pos = [j for j, c in enumerate(cs) if c in LABELS]
            content = [(j, c) for j, c in enumerate(cs) if j not in label_pos]
            if not content:
                continue
            # a label row whose content is a long list is the shifted substitution cell
            # (documented per file in its extraction_note) — never bind it to the label.
            for j, c in content:
                entries = [e for e in c.split(", ") if e]
                if label_pos and len(entries) > SUBS_LEN:
                    continue
                side = "away" if j == 0 else "home"
                if result[side] is None:
                    result[side] = []
                result[side].extend(entries)
        return result

    dnp = {"away": [], "home": []}
    na = {"away": [], "home": []}
    if dnp_idx is not None:
        dnp = zone(dnp_idx, na_idx if na_idx is not None else len(lines))
        dnp = {k: (v if v is not None else []) for k, v in dnp.items()}
    if na_idx is not None:
        end = len(lines)
        for i in range(na_idx + 1, len(lines)):
            if "Field Goals" in lines[i] or "Scoring Plays" in lines[i]:
                end = i
                break
        na = zone(na_idx, end)
        na = {k: (v if v is not None else []) for k, v in na.items()}

    # KC-style prose status sections (no table labels).  Scan only the body of the
    # capture — the extraction_note itself quotes the label text and must not trigger this.
    body_lines = [l for l in lines if not l.startswith("extraction_note:")]
    prose_dnp = None
    if dnp_idx is None and any("Did Not Play" in l and not l.startswith("|")
                               for l in body_lines):
        prose_dnp = True
        flags.append({
            "code": "STATUS_PROSE_FORMAT",
            "detail": "Status sections print as prose headings, not table labels; structured "
                      "status fields are null and the raw capture + extraction_note govern.",
        })

    # unattributed status list (KC's Not Active header did not print)
    unattributed: list[str] = []
    if meta["game"] == "chiefs-at-falcons-2026-reg-10":
        # the raw file records the list verbatim after the Atlanta Did Not Play section;
        # the paragraph wraps across lines, so accumulate until a blank/pipeline boundary.
        grab = False
        buf: list[str] = []
        for l in lines:
            if l.startswith("**Did Not Play**"):
                grab = True
                continue
            if not grab:
                continue
            if not l.strip() or l.startswith("|") or l.startswith("Paid") \
                    or l.startswith("extraction_note"):
                if buf:
                    break
                continue
            if l.strip() == "QB 1 T.Tagovailoa" and not buf:
                continue
            buf.append(l.strip())
        if buf:
            unattributed = [e for e in " ".join(buf).split(", ") if e]
        if unattributed:
            flags.append({
                "code": "STATUS_UNATTRIBUTED",
                "detail": "A status list printed without its section header; recorded "
                          "verbatim, not bound to a club.",
            })

    if not has_note:
        flags.append({"code": "NO_EXTRACTION_NOTE", "detail": "raw capture carries no extraction_note"})

    return {
        "game": meta["game"],
        "date": meta["date"],
        "away": {"abbr": away, "name": away_name, "score": meta["away"]["score"]},
        "home": {"abbr": home, "name": home_name, "score": meta["home"]["score"]},
        "venue": meta["venue"],
        "referee": referee,
        "weather": weather,
        "attendance": attendance,
        "lineups": structured,
        "did_not_play": dnp if dnp_idx is not None else {"away": None, "home": None},
        "not_active": na if na_idx is not None else {"away": None, "home": None},
        "status_unattributed": unattributed,
        "flags": flags,
        "sources": {
            "game_centre": meta["game_centre_url"],
            "game_book": meta["game_book_url"],
            "raw_file": "data/gamebooks/raw/%s.txt" % meta["game"],
            "raw_sha256": meta["raw_sha256"],
        },
    }


# --- injury-read match ---------------------------------------------------

_SUFFIX = {"jr", "sr", "ii", "iii", "iv", "v", "vi"}


def book_name_key(name: str) -> tuple[str, str] | None:
    """'D.Allar' -> ('d', 'allar'); 'S.Murphy-Bunting' -> ('s', 'murphy-bunting')."""
    name = name.strip()
    if "." not in name:
        return None
    initial, _, surname = name.partition(".")
    surname = surname.strip().lower().replace(".", "")
    if not initial or not surname:
        return None
    toks = [t for t in surname.split() if t.strip(".") not in _SUFFIX]
    surname = " ".join(toks) if toks else surname
    return initial[0].lower(), surname


def injury_name_key(full: str) -> tuple[str, str]:
    """'Drew Allar' -> ('d', 'allar'); 'A.J. Terrell' -> ('a', 'terrell');
    'Ronnie Hickman Jr.' -> ('r', 'hickman')."""
    toks = [t for t in full.split() if t.strip(".").lower() not in _SUFFIX]
    if not toks:
        toks = full.split()
    first = toks[0]
    surname = " ".join(toks[1:]).lower() if len(toks) > 1 else first.lower()
    return first[0].lower(), surname


def match_injury_read(parsed_games: list[dict], injury_path: str) -> dict:
    inj = load_json(injury_path)
    rows = inj["rows"]
    by_surname: dict[str, list[dict]] = {}
    for r in rows:
        _, sur = injury_name_key(r["player"])
        by_surname.setdefault(sur, []).append(r)

    club_alias = {"LAR": "LA", "LA": "LA"}
    results = []
    totals = {"not_active_entries": 0, "matched": 0, "not_in_report": 0,
              "ambiguous": 0, "unparseable": 0,
              "out": 0, "doubtful": 0, "questionable": 0}
    out_but_active: list[dict] = []

    for g in parsed_games:
        na = g.get("not_active") or {}
        for side in ("away", "home"):
            entries = na.get(side)
            club = g[side]["abbr"]
            if entries is None:
                continue
            for e in entries:
                totals["not_active_entries"] += 1
                m = re.search(r"\d+\s+([A-Za-z].*)$", e)
                bname = m.group(1).strip() if m else None
                key = book_name_key(bname) if bname else None
                hit = {"game": g["game"], "club": club, "side": side,
                       "entry": e, "book_name": bname}
                if key is None:
                    hit["match"] = "unparseable"
                    totals["unparseable"] += 1
                else:
                    cands = by_surname.get(key[1], [])
                    # same first initial only — a different initial is a different player,
                    # never a match; and the player must be on THIS club's injury table.
                    pool = [c for c in cands
                            if injury_name_key(c["player"])[0] == key[0]
                            and c["club"] == club_alias.get(club, club)]
                    if len(pool) == 1:
                        c = pool[0]
                        hit["match"] = "matched"
                        hit["injury_player"] = c["player"]
                        hit["game_status"] = c.get("game_status")
                        hit["injury"] = c["injury"]
                        hit["player_url"] = c.get("player_url")
                        totals["matched"] += 1
                        st = (c.get("game_status") or "").lower()
                        if st in totals:
                            totals[st] += 1
                    elif len(pool) > 1:
                        hit["match"] = "ambiguous"
                        hit["candidates"] = [c["player"] for c in pool]
                        totals["ambiguous"] += 1
                    else:
                        hit["match"] = "not_in_report"
                        totals["not_in_report"] += 1
                results.append(hit)

    # reverse check: players the official read lists Out for these clubs who are
    # NOT on that club's captured Not Active list (reported, never inferred).
    na_surnames_by_club: dict[str, set[str]] = {}
    for g in parsed_games:
        for side in ("away", "home"):
            entries = (g.get("not_active") or {}).get(side)
            if entries is None:
                continue
            club = club_alias.get(g[side]["abbr"], g[side]["abbr"])
            sset = na_surnames_by_club.setdefault(club, set())
            for e in entries:
                m = re.search(r"\d+\s+([A-Za-z].*)$", e)
                if m:
                    k = book_name_key(m.group(1).strip())
                    if k:
                        sset.add(k[1])
    for r in rows:
        if r["game_status"] != "Out":
            continue
        _, sur = injury_name_key(r["player"])
        if r["club"] in na_surnames_by_club and sur not in na_surnames_by_club[r["club"]]:
            out_but_active.append({
                "club": r["club"], "player": r["player"], "injury": r["injury"],
                "player_url": r.get("player_url"),
                "note": "listed Out on the official pre-game read but absent from every "
                        "captured Not Active list for that club's game",
            })

    return {
        "schema": "gamebooks-injury-match/1",
        "injury_read": {
            "file": os.path.relpath(injury_path, ROOT),
            "captured_at_utc": inj.get("captured_at_utc"),
            "source_url": inj.get("source_url"),
            "rows": len(rows),
            "sha256": inj.get("canonical_sha256"),
        },
        "totals": totals,
        "matches": results,
        "out_not_on_na_list": out_but_active,
    }


# --- HTML ----------------------------------------------------------------

CSS = """\
:root{--bg:#f6f7f9;--card:#fff;--ink:#16202c;--mut:#5b6774;--line:#e3e7ec;--acc:#0b5fff;--warn:#b45309;--flag:#b91c1c}
*{box-sizing:border-box}body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
header.top{background:#0e1726;color:#fff;padding:14px 22px;display:flex;gap:14px;align-items:baseline;flex-wrap:wrap}
header.top a{color:#cfe0ff;text-decoration:none}header.top .brand{font-weight:700;color:#fff;font-size:16px}
header.top .stamp{color:#93a4bb;font-size:12px;margin-left:auto}
nav.sub{background:#182338;padding:8px 22px;display:flex;gap:18px;flex-wrap:wrap}
nav.sub a{color:#d7e3f5;text-decoration:none;font-size:14px;padding:4px 2px;border-bottom:2px solid transparent}
nav.sub a.active{border-bottom-color:#5b93ff;color:#fff}
main{max-width:1100px;margin:0 auto;padding:26px 22px 60px}
h1{font-size:26px;margin:6px 0 4px}h2{font-size:19px;margin:30px 0 8px}h3{font-size:15px;margin:18px 0 6px}
p.lead{color:var(--mut);margin-top:2px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;text-decoration:none;color:inherit}
.kpi b{display:block;font-size:24px}.kpi span{color:var(--mut);font-size:12.5px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
table{border-collapse:collapse;width:100%;background:var(--card);font-size:13.5px}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
th{background:#eef1f5;font-weight:600;position:sticky;top:0}
.tablewrap{overflow-x:auto;border-radius:8px;border:1px solid var(--line);margin:10px 0}
.tablewrap table{border:0}.tablewrap th,.tablewrap td{border-left:0;border-right:0}
a.src{color:var(--acc);text-decoration:none}a.src:hover{text-decoration:underline}
.mut{color:var(--mut)}.blank{color:var(--flag);font-weight:600}
.flag{border-left:4px solid var(--flag);background:#fef2f2;padding:8px 12px;margin:8px 0;border-radius:0 8px 8px 0;font-size:13.5px}
.note{border-left:4px solid var(--warn);background:#fffbeb;padding:8px 12px;margin:8px 0;border-radius:0 8px 8px 0;font-size:13.5px}
code{background:#eef1f5;padding:1px 5px;border-radius:4px;font-size:12.5px}
.gamecard{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:14px 0}
.gamecard h3{margin-top:0;display:flex;gap:10px;flex-wrap:wrap;align-items:baseline}
.gamecard h3 .score{font-size:17px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:760px){.two{grid-template-columns:1fr}}
ul.plain{padding-left:18px}ul.plain li{margin:4px 0}
footer{color:var(--mut);font-size:12.5px;margin-top:34px;border-top:1px solid var(--line);padding-top:10px}
"""

NAV = [
    ("index.html", "Overview"),
    ("starters.html", "Starting lineups"),
    ("inactives.html", "Game-day status"),
    ("match.html", "Status vs injury read"),
    ("methods.html", "Method & flags"),
]


def page(title: str, active: str, body: str, stamp: str) -> str:
    nav = "".join(
        f'<a href="{h}"{" class=active" if h == active else ""}>{esc(l)}</a>' for h, l in NAV
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — NFL Game Books</title>
<link rel="stylesheet" href="style.css"></head><body>
<header class="top"><a class="brand" href="index.html">NFL Game Books</a>
<a href="../index.html">Main site</a>
<a href="https://github.com/kanlerxz87-cyber/NFL1">Source</a>
<span class="stamp">{esc(stamp)}</span></header>
<nav class="sub">{nav}</nav>
<main>{body}
<footer>Every cell on this site is transcribed from an official NFL Game Book PDF or the
official injury report; blanks are empty-as-extracted and flagged, never inferred.
Sources: <a class="src" href="https://www.nfl.com/schedules/2026/REG10" target="_blank" rel="noopener">nfl.com schedules</a> ·
<a class="src" href="https://www.nfl.com/injuries/league/2026/reg10" target="_blank" rel="noopener">nfl.com injuries</a>.</footer>
</main></body></html>
"""


def link(href: str, label: str, cls: str = "src") -> str:
    return f'<a class="{cls}" href="{esc(href)}" target="_blank" rel="noopener">{esc(label)}</a>'


def status_cell(v: list | None) -> str:
    if v is None:
        return '<span class="blank" title="label absent from extraction">blank — see flag</span>'
    if not v:
        return '<span class="mut">none printed</span>'
    return esc(", ".join(v))


def build_site(parsed: list[dict], match: dict, source: dict) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "style.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    stamp = "built from data/gamebooks/ · session d9e28eb2-nfl1"
    by_game = {p["game"]: p for p in parsed}
    flag_count = sum(len(p["flags"]) for p in parsed)
    na_entries = match["totals"]["not_active_entries"]
    matched = match["totals"]["matched"]

    # ---- index.html
    rows = []
    for m in source["games"]:
        p = by_game[m["game"]]
        rows.append(
            "<tr><td>{date}</td>"
            "<td><b>{away}</b> {ascore} @ <b>{home}</b> {hscore}</td>"
            "<td>{venue}</td><td>{ref}</td><td>{att}</td>"
            "<td>{gc} · {pdf} · {raw}</td></tr>".format(
                date=esc(m["date"]),
                away=esc(m["away"]["abbr"]), ascore=m["away"]["score"],
                home=esc(m["home"]["abbr"]), hscore=m["home"]["score"],
                venue=esc(m["venue"]),
                ref=esc(p["referee"] or "—"),
                att=esc(p["attendance"] or "—"),
                gc=link(m["game_centre_url"], "game centre"),
                pdf=link(m["game_book_url"], "Game Book PDF"),
                raw=f'<a class="src" href="../{esc(m["raw_file"])}">raw</a>',
            )
        )
    body = f"""
<h1>Official NFL Game Books — Week 10, 2026</h1>
<p class="lead">Verbatim captures of the league's own Game Book PDFs for every completed
Week 10 game: starting lineups (both units, both clubs), substitutions, Did Not Play,
Not Active, officials, weather, scoring and attendance. Nothing here is inferred.</p>
<div class="kpis">
<div class="kpi"><b>13 / 13</b><span>completed games captured (LAC@BAL MNF pending at capture)</span></div>
<div class="kpi"><b>{na_entries}</b><span>Not Active entries parsed and matched to the official injury read</span></div>
<div class="kpi"><b>{matched}</b><span>of them appear on the pre-game injury report</span></div>
<div class="kpi"><b>{flag_count}</b><span>extraction flags, each pointing at the PDF that settles it</span></div>
</div>
<div class="note">Method: CAP-06 transcription-of-fetch-text. Each PDF was read through the
fetch_page markdown extraction and transcribed byte-for-byte to
<code>data/gamebooks/raw/</code>; <code>data/gamebooks/manifest.json</code> pins every file
with sha256. Layout quirks in individual extractions are recorded in that file's
<code>extraction_note</code> and surfaced as flags — see <a class="src" href="methods.html">Method &amp; flags</a>.</div>
<h2>The13 games</h2>
<div class="tablewrap"><table>
<tr><th>Date</th><th>Matchup (final)</th><th>Venue</th><th>Referee</th><th>Attendance</th><th>Official sources</th></tr>
{"".join(rows)}
</table></div>
<h2>Where to look</h2>
<ul class="plain">
<li><a href="starters.html">Starting lineups</a> — the 22 offensive and defensive starters per game, as printed.</li>
<li><a href="inactives.html">Game-day status</a> — Not Active and Did Not Play per club, blanks flagged.</li>
<li><a href="match.html">Status vs injury read</a> — every Not Active entry matched against the official pre-game injury report.</li>
<li><a href="methods.html">Method &amp; flags</a> — capture protocol, per-file extraction quirks, open flags.</li>
</ul>
"""
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(page("Overview", "index.html", body, stamp))

    # ---- starters.html
    cards = []
    for m in source["games"]:
        p = by_game[m["game"]]
        if not p["lineups"]:
            cards.append(f'<div class="gamecard"><h3>{esc(m["away"]["abbr"])} @ {esc(m["home"]["abbr"])}</h3>'
                         '<div class="flag">Lineups not parsed from this extraction — see the raw capture.</div></div>')
            continue
        blanks = [fl for fl in p["flags"] if fl["code"] == "LINEUP_NAME_BLANK"]
        flag_html = ""
        if blanks:
            flag_html = ('<div class="flag">Extraction gap: '
                         + esc(", ".join(f'{b["side"]} {b["unit"]} {b["pos"]} {b["num"]}' for b in blanks))
                         + ' printed without a name in the PDF text extraction — name left blank, not inferred.</div>')

        def unit_table(side_key: str, unit: str) -> str:
            side = p["lineups"][side_key]
            trs = "".join(
                f'<tr><td>{i+1}</td><td>{esc(pl["pos"])}</td><td>{esc(pl["num"])}</td>'
                f'<td>{esc(pl["name"]) if pl["name"] else "<span class=blank>blank</span>"}</td></tr>'
                for i, pl in enumerate(side[unit])
            )
            return (f'<h3>{esc(side["name"])} — {unit}</h3>'
                    f'<div class="tablewrap"><table><tr><th>#</th><th>Pos</th><th>No.</th><th>Player</th></tr>{trs}</table></div>')

        cards.append(
            f'<div class="gamecard"><h3><span>{esc(m["away"]["abbr"])} {m["away"]["score"]} @ '
            f'{esc(m["home"]["abbr"])} {m["home"]["score"]}</span>'
            f'<span class="score mut">{esc(m["date"])}</span>'
            f'<span>{link(m["game_centre_url"], "game centre")} · {link(m["game_book_url"], "PDF")} · '
            f'<a class="src" href="../{esc(p["sources"]["raw_file"])}">raw</a></span></h3>'
            f'{flag_html}<div class="two">'
            f'{unit_table("away", "offense")}{unit_table("away", "defense")}'
            f'{unit_table("home", "offense")}{unit_table("home", "defense")}</div></div>'
        )
    body = f"""
<h1>Starting lineups</h1>
<p class="lead">The starters each club actually used in Week 10, transcribed from the Lineups
table of each official Game Book — eleven on offense and eleven on defense per club.
Jersey order is never used as a depth proxy; these are the printed starters only.</p>
{"".join(cards)}
"""
    with open(os.path.join(OUT_DIR, "starters.html"), "w", encoding="utf-8") as f:
        f.write(page("Starting lineups", "starters.html", body, stamp))

    # ---- inactives.html
    cards = []
    for m in source["games"]:
        p = by_game[m["game"]]
        fl = "".join(f'<div class="flag"><b>{esc(f["code"])}</b> — {esc(f["detail"])}</div>'
                     for f in p["flags"] if f["code"] in
                     ("STATUS_LABELS_ABSENT", "STATUS_PROSE_FORMAT", "STATUS_UNATTRIBUTED",
                      "LINEUPS_INCOMPLETE"))
        unattr = ""
        if p["status_unattributed"]:
            unattr = ('<div class="flag"><b>STATUS_UNATTRIBUTED</b> — a status list printed '
                      'without its section header; recorded verbatim, not bound to a club: '
                      + esc(", ".join(p["status_unattributed"])) + "</div>")
        na = p["not_active"]
        dnp = p["did_not_play"]
        cards.append(
            f'<div class="gamecard"><h3><span>{esc(m["away"]["abbr"])} {m["away"]["score"]} @ '
            f'{esc(m["home"]["abbr"])} {m["home"]["score"]}</span>'
            f'<span>{link(m["game_centre_url"], "game centre")} · {link(m["game_book_url"], "PDF")} · '
            f'<a class="src" href="../{esc(p["sources"]["raw_file"])}">raw</a></span></h3>'
            f'{fl}{unattr}'
            f'<div class="two">'
            f'<div><h3>{esc(m["away"]["name"])} — Not Active</h3><p>{status_cell(na["away"])}</p>'
            f'<h3>{esc(m["away"]["name"])} — Did Not Play</h3><p>{status_cell(dnp["away"])}</p></div>'
            f'<div><h3>{esc(m["home"]["name"])} — Not Active</h3><p>{status_cell(na["home"])}</p>'
            f'<h3>{esc(m["home"]["name"])} — Did Not Play</h3><p>{status_cell(dnp["home"])}</p></div>'
            f'</div></div>'
        )
    body = f"""
<h1>Game-day status</h1>
<p class="lead">Not Active (the game-day inactive list) and Did Not Play (dressed but unused)
exactly as each Game Book prints them. Where a label did not survive the PDF text extraction
the field is blank and flagged — never reconstructed.</p>
{"".join(cards)}
"""
    with open(os.path.join(OUT_DIR, "inactives.html"), "w", encoding="utf-8") as f:
        f.write(page("Game-day status", "inactives.html", body, stamp))

    # ---- match.html
    t = match["totals"]
    mrows = []
    for r in match["matches"]:
        if r["match"] == "matched":
            st = r.get("game_status")
            if st is None:
                detail = esc(r["injury"]) + ' · <span class="mut">game status blank on the official read</span>'
            else:
                cls = "blank" if st == "Out" else "mut"
                detail = (f'{esc(r["injury"])} — <span class="{cls}">{esc(st)}</span> · '
                          + link(r["player_url"], "player"))
        elif r["match"] == "not_in_report":
            detail = '<span class="blank">not on the official pre-game injury read</span>'
        elif r["match"] == "ambiguous":
            detail = '<span class="blank">ambiguous surname match: ' + esc(", ".join(r.get("candidates", []))) + "</span>"
        else:
            detail = '<span class="blank">entry not parseable</span>'
        mrows.append(
            f'<tr><td><a class="src" href="https://www.nfl.com/games/{esc(r["game"])}" '
            f'target="_blank" rel="noopener">{esc(r["club"])}</a></td>'
            f'<td>{esc(r["entry"])}</td><td>{detail}</td></tr>'
        )
    orows = "".join(
        f'<tr><td>{esc(o["club"])}</td><td>{esc(o["player"])}</td><td>{esc(o["injury"])}</td>'
        f'<td>{link(o["player_url"], "player")}</td><td>{esc(o["note"])}</td></tr>'
        for o in match["out_not_on_na_list"]
    )
    body = f"""
<h1>Status vs the official injury read</h1>
<p class="lead">Every parsed Not Active entry matched against the league's own pre-game injury
report (347 rows, captured {esc(match["injury_read"]["captured_at_utc"])} from
{link(match["injury_read"]["source_url"], "nfl.com/injuries")}). Matching is by surname plus
first initial within the same club; ambiguous surnames are reported as ambiguous, never picked.</p>
<div class="kpis">
<div class="kpi"><b>{t["not_active_entries"]}</b><span>Not Active entries matched</span></div>
<div class="kpi"><b>{t["matched"]}</b><span>found on the injury read ({t["out"]} Out · {t["doubtful"]} Doubtful · {t["questionable"]} Questionable)</span></div>
<div class="kpi"><b>{t["not_in_report"]}</b><span>not on the injury read at all</span></div>
<div class="kpi"><b>{t["ambiguous"]}</b><span>ambiguous / unparseable (never guessed)</span></div>
</div>
<h2>Not Active entries</h2>
<div class="tablewrap"><table><tr><th>Club</th><th>Not Active entry (Game Book)</th><th>Official injury read</th></tr>
{"".join(mrows)}</table></div>
<h2>Listed Out but not on any captured Not Active list</h2>
<p class="mut">Reported for review, never blocking; an Out designation and a game-day inactive
list are published by different processes at different times.</p>
<div class="tablewrap"><table><tr><th>Club</th><th>Player</th><th>Injury</th><th>Source</th><th>Note</th></tr>
{orows or '<tr><td colspan="5" class="mut">none</td></tr>'}</table></div>
"""
    with open(os.path.join(OUT_DIR, "match.html"), "w", encoding="utf-8") as f:
        f.write(page("Status vs injury read", "match.html", body, stamp))

    # ---- methods.html
    frows = []
    for m in source["games"]:
        p = by_game[m["game"]]
        for fl in p["flags"]:
            frows.append(
                f'<tr><td>{esc(m["game"])}</td><td>{esc(fl["code"])}</td><td>{esc(fl["detail"])}</td>'
                f'<td>{link(m["game_book_url"], "PDF")} · '
                f'<a class="src" href="../{esc(m["raw_file"])}">raw</a></td></tr>'
            )
    body = f"""
<h1>Method &amp; flags</h1>
<h2>Capture protocol</h2>
<ul class="plain">
<li>One read of each official game-centre page and one read of each official Game Book PDF
(<code>static.www.nfl.com</code>) during session d9e28eb2-nfl1; chunk 0 of every PDF carries
the full game summary (lineups, substitutions, Did Not Play, Not Active, officials, weather,
scoring, attendance).</li>
<li>Captures are transcribed to <code>data/gamebooks/raw/</code> — CAP-06
transcription-of-fetch-text, disclosed on every page. <code>data/gamebooks/manifest.json</code>
pins each file with sha256; <code>data/gamebooks/source.json</code> carries the game-centre
and PDF URLs per game.</li>
<li>Blanks are empty-as-extracted. A field whose label did not survive the extraction is null
in <code>data/gamebooks/parsed.json</code> and flagged here — it is never reconstructed from
context, other sources, or inference.</li>
<li>The official league inactives page (<code>nfl.com/inactives</code>) published nothing for
the 2026 season at capture time, so these Game Books are the only official game-day
inactive source in the repository.</li>
</ul>
<h2>Open flags ({len(frows)})</h2>
<div class="tablewrap"><table><tr><th>Game</th><th>Flag</th><th>What the extraction shows</th><th>Official source</th></tr>
{"".join(frows)}</table></div>
<h2>Files</h2>
<ul class="plain">
<li><code>data/gamebooks/source.json</code> — registry: scores, venues, URLs, hashes.</li>
<li><code>data/gamebooks/manifest.json</code> — sha256 of every raw capture.</li>
<li><code>data/gamebooks/parsed.json</code> — structured lineups / status per game.</li>
<li><code>data/gamebooks/injury_match.json</code> — the match shown on <a href="match.html">this site</a>.</li>
<li><code>tools/build_gamebooks.py</code> · <code>tools/check_gamebooks.py</code> ·
<code>tests/test_gamebooks.py</code> — builder, gate, tests.</li>
</ul>
"""
    with open(os.path.join(OUT_DIR, "methods.html"), "w", encoding="utf-8") as f:
        f.write(page("Method & flags", "methods.html", body, stamp))


# --- main ----------------------------------------------------------------


def build() -> dict:
    source = load_json(os.path.join(ROOT, "data", "gamebooks", "source.json"))
    manifest = load_json(os.path.join(ROOT, "data", "gamebooks", "manifest.json"))
    hashes = {f["path"]: f["sha256"] for f in manifest["files"]}

    parsed = []
    for m in source["games"]:
        rel = m["raw_file"]
        path = os.path.join(ROOT, rel)
        import hashlib
        with open(path, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        if hashes.get(rel) != actual:
            raise SystemExit(f"hash mismatch for {rel}: manifest {hashes.get(rel)} != {actual}")
        parsed.append(parse_game(path, m))

    dump_json(os.path.join(ROOT, "data", "gamebooks", "parsed.json"), {
        "schema": "gamebooks-parsed/1",
        "generated_from": {g["game"]: g["raw_sha256"] for g in source["games"]},
        "games": parsed,
    })

    injury_files = sorted(
        os.path.join(ROOT, "data", "snapshots", "injury_report", "captures", n)
        for n in os.listdir(os.path.join(ROOT, "data", "snapshots", "injury_report", "captures"))
        if n.endswith(".json")
    )
    match = match_injury_read(parsed, injury_files[-1])
    dump_json(os.path.join(ROOT, "data", "gamebooks", "injury_match.json"), match)

    build_site(parsed, match, source)
    return {"games": len(parsed), "flags": sum(len(p["flags"]) for p in parsed),
            "match": match["totals"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        watch = [os.path.join(ROOT, "gamebooks"),
                 os.path.join(ROOT, "data", "gamebooks", "parsed.json"),
                 os.path.join(ROOT, "data", "gamebooks", "injury_match.json")]

        def snapshot() -> dict:
            out = {}
            for w in watch:
                if os.path.isdir(w):
                    for dirpath, _, names in os.walk(w):
                        for n in names:
                            p = os.path.join(dirpath, n)
                            out[p] = open(p, "rb").read()
                elif os.path.exists(w):
                    out[w] = open(w, "rb").read()
            return out

        before = snapshot()
        stats = build()
        after = snapshot()
        changed = [p for p in set(before) | set(after)
                   if before.get(p) != after.get(p)]
        if changed:
            print("FAIL: build changed files:", *sorted(changed), sep="\n  ")
            return 1
        print("OK: gamebooks build is deterministic", stats)
        return 0
    stats = build()
    print("built gamebooks/:", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
