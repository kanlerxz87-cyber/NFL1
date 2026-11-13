#!/usr/bin/env python3
"""Build the official-roster backup register from the official injury report and rosters.

Inputs (both produced from nfl.com pages):
  data/model/official_injuries.json         Week 10 official injury report rows (scraped by pipeline/)
  data/backup-register/rosters_2026.json    official club roster pages (scraped by tools/scrape_rosters.py)

For every official GAME designation (Out / Doubtful / Questionable) it lists the same-position-group
players on that club's official roster whose roster status is ACT. Depth order is NOT shown: nfl.com
publishes no depth chart, so 2nd/3rd/4th-string rank is left blank and flagged. Nothing is inferred:
an unmatched player, a position disagreement or an unknown status is written as a flag.

Outputs:
  data/backup-register/register.json, register.csv, and pages/backup-register.html
"""
from __future__ import annotations

import csv
import html
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
INJ = os.path.join(ROOT, "data", "model", "official_injuries.json")
ROSTERS = os.path.join(ROOT, "data", "backup-register", "rosters_2026.json")
OUT_DIR = os.path.join(ROOT, "data", "backup-register")
PAGE = os.path.join(ROOT, "pages", "backup-register.html")
INJURY_URL = "https://www.nfl.com/injuries/"
GAME_STATUSES = ("Out", "Doubtful", "Questionable")
# Analyst mapping of nfl.com position codes into position groups. Used only to decide which
# roster players count as same-position backups. Generic "DB" cannot be assigned to CB or S,
# so it is listed but never counted.
GROUP = {
    "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
    "T": "OL", "OT": "OL", "G": "OL", "OG": "OL", "C": "OL", "OL": "OL",
    "DE": "DL", "DT": "DL", "DL": "DL", "NT": "DL",
    "LB": "LB", "OLB": "LB", "ILB": "LB", "MLB": "LB",
    "CB": "CB", "S": "S", "SAF": "S", "FS": "S", "SS": "S",
    "K": "K", "P": "P", "LS": "LS",
}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def name_key(name: str) -> str:
    words = re.sub(r"[^a-z ]", "", (name or "").lower().replace("-", " ")).split()
    return " ".join(w for w in words if w not in SUFFIXES)


def slug_key(slug: str) -> str:
    s = re.sub(r"-(\d+|x\d+)$", "", slug.lower())
    parts = [p for p in s.split("-") if p and p not in SUFFIXES]
    return "".join(re.sub(r"[^a-z]", "", p) for p in parts)


def letters(name: str) -> str:
    return "".join(ch for ch in name_key(name) if ch.isalpha())


def player_slug(url: str | None) -> str | None:
    m = re.search(r"/players/([^/]+)/?$", url or "")
    return m.group(1) if m else None


def main() -> int:
    with open(INJ, encoding="utf-8") as f:
        inj = json.load(f)
    with open(ROSTERS, encoding="utf-8") as f:
        rost = json.load(f)

    week = inj.get("week")
    flags: list[dict] = []

    def flag(fid: str, kind: str, text: str, url: str | None) -> None:
        flags.append({"id": fid, "kind": kind, "text": text, "source": url})

    if inj.get("status") != "ok" or week != 10:
        flag("X-INJ", "source", f"official injury file status={inj.get('status')} week={week}; expected ok / week 10", INJURY_URL)
    if rost.get("status") != "ok":
        flag("X-ROS", "source", f"roster scrape status={rost.get('status')}; some clubs may be missing", TEAMS_URL_FALLBACK)

    clubs = {c["abbr"]: c for c in rost.get("clubs", []) if c.get("abbr")}
    for c in rost.get("clubs", []):
        for w in c.get("warnings", []):
            flag("X-ROW", "roster parse", f"{c.get('slug')}: {w}", c.get("url"))
        if c.get("error"):
            flag("X-CLUB", "roster fetch", f"{c.get('slug')}: {c['error']}", c.get("url"))

    # Roster status values and roster-vs-slug name checks (possible name/link mismatch).
    status_values = Counter()
    name_link_mismatch = []
    for abbr, c in clubs.items():
        for p in c["players"]:
            status_values[p.get("status") or ""] += 1
            slug = player_slug(p.get("player_url"))
            if slug and letters(p["name"]) != slug_key(slug):
                name_link_mismatch.append({"club": abbr, "name": p["name"], "slug": slug, "url": p["player_url"]})
    for m in name_link_mismatch:
        flag("X-LINK", "name/link mismatch",
             f"{m['club']}: roster name '{m['name']}' links to /players/{m['slug']}/ — check the player page",
             m["url"])

    # Unknown game designations in the injury report (anything other than the three statuses we use).
    designations = []
    unknown_game = Counter()
    for r in inj.get("rows", []):
        g = r.get("game")
        if not g:
            continue
        if g not in GAME_STATUSES:
            unknown_game[g] += 1
            continue
        designations.append(r)
    for g, n in unknown_game.items():
        flag("X-GAME", "unknown designation", f"{n} row(s) carry game status '{g}', not counted", INJURY_URL)

    entries = []
    for r in designations:
        abbr = r.get("team")
        club = clubs.get(abbr)
        slug_url = club["url"] if club else None
        entry = {
            "week": week, "club": abbr, "player": r.get("player"),
            "injury_position": r.get("position"), "game_status": r.get("game"),
            "injury": r.get("injury"), "practice_status": r.get("practice"),
            "injury_player_url": r.get("player_url"), "injury_source": INJURY_URL,
            "roster_url": slug_url, "roster_position": None, "roster_status": None,
            "roster_experience": None, "match": None, "backups": [], "backup_count": 0,
            "non_active_same_group": 0, "unassigned_db": [], "depth_rank": None,
            "depth_note": "nfl.com publishes no depth order; rank intentionally blank", "row_flags": [],
        }
        if club is None:
            entry["match"] = "club not in roster scrape"
            entry["row_flags"].append("club missing from roster scrape")
            flag("X-CLUB-MAP", "club mapping", f"{r.get('player')} ({abbr}): club not in roster scrape", INJURY_URL)
            entries.append(entry)
            continue
        matches = [p for p in club["players"] if name_key(p["name"]) == name_key(r.get("player"))]
        if len(matches) != 1:
            entry["match"] = f"{len(matches)} roster matches"
            entry["row_flags"].append("not matched to exactly one roster row; no backup list shown")
            flag("X-MATCH", "unmatched designation",
                 f"{r.get('player')} ({abbr}, {r.get('game')}): {len(matches)} roster matches on the official roster",
                 INJURY_URL)
            entries.append(entry)
            continue
        me = matches[0]
        entry["match"] = "exact name on official roster"
        entry["roster_position"] = me.get("position")
        entry["roster_status"] = me.get("status")
        entry["roster_experience"] = me.get("experience")
        entry["roster_player_url"] = me.get("player_url")
        inj_pos = (r.get("position") or "").upper()
        if me.get("position") and inj_pos != me["position"].upper():
            entry["row_flags"].append(f"position differs: injury report {inj_pos}, roster {me['position']}")
            flag("X-POS", "position disagreement",
                 f"{r.get('player')} ({abbr}): injury report says {inj_pos}, roster says {me['position']}; "
                 "group taken from the injury report", INJURY_URL)
        group = GROUP.get(inj_pos)
        if group is None:
            entry["row_flags"].append(f"position {inj_pos or '(blank)'} has no group mapping; backups not counted")
            flag("X-GROUP", "no position group", f"{r.get('player')} ({abbr}): position '{inj_pos}' not in mapping", INJURY_URL)
            entries.append(entry)
            continue
        same_group = []
        for p in club["players"]:
            if p is me or name_key(p["name"]) == name_key(me["name"]):
                continue
            pos = (p.get("position") or "").upper()
            if pos == "DB":
                entry["unassigned_db"].append(p["name"])
                continue
            if GROUP.get(pos) != group:
                continue
            if (p.get("status") or "").upper() != "ACT":
                entry["non_active_same_group"] += 1
                continue
            same_group.append({
                "name": p["name"], "position": p.get("position"), "status": p.get("status"),
                "experience": p.get("experience"), "college": p.get("college"),
                "player_url": p.get("player_url"), "roster_url": club["url"],
            })
        same_group.sort(key=lambda x: x["name"])
        entry["backups"] = same_group
        entry["backup_count"] = len(same_group)
        entry["unassigned_db"] = sorted(entry["unassigned_db"])
        entries.append(entry)

    entries.sort(key=lambda e: (e["club"] or "", e["player"] or ""))

    club_rows = []
    for abbr in sorted({e["club"] for e in entries if e["club"]}):
        es = [e for e in entries if e["club"] == abbr]
        counts = [e["backup_count"] for e in es if e["match"] == "exact name on official roster"]
        club_rows.append({
            "club": abbr, "roster_url": clubs.get(abbr, {}).get("url"),
            "designations": len(es), "matched": len(counts),
            "min_active_same_group_backups": min(counts) if counts else None,
            "designated_players": ", ".join(f"{e['player']} ({e['game_status']})" for e in es),
        })

    summary = {
        "designations_total": len(entries),
        "by_status": dict(Counter(e["game_status"] for e in entries)),
        "matched_to_roster": sum(1 for e in entries if e["match"] == "exact name on official roster"),
        "unmatched": sum(1 for e in entries if e["match"] != "exact name on official roster"),
        "with_zero_active_backups": sum(1 for e in entries if e["match"] == "exact name on official roster" and e["backup_count"] == 0),
        "clubs_with_designations": len(club_rows),
        "rosters_parsed": sum(1 for c in rost.get("clubs", []) if c.get("players")),
        "roster_status_values": dict(status_values),
        "name_link_mismatches": len(name_link_mismatch),
    }

    payload = {
        "generated_at": now_iso(),
        "status": "ok" if inj.get("status") == "ok" and rost.get("status") == "ok" else "partial",
        "week": week,
        "season": 2026,
        "sources": {
            "injury_report": {"url": INJURY_URL, "generated_at": inj.get("generated_at"),
                              "html_sha256": inj.get("html_sha256"), "rows": len(inj.get("rows", []))},
            "rosters": {"index": rost.get("source_index"), "generated_at": rost.get("generated_at"),
                        "clubs": [{"club": c.get("abbr"), "url": c.get("url"), "sha256": c.get("sha256"),
                                   "players": c.get("player_count")} for c in rost.get("clubs", [])]},
        },
        "method": [
            "Designations: official nfl.com game status Out, Doubtful or Questionable (week 10 report).",
            "Match: the injury row is matched to the official roster row of the same club by full name; "
            "no match or more than one match is flagged and no backups are listed.",
            "Backups: other players on the same club's official roster with roster status ACT and the same "
            "position group (mapping in tools/build_backup_register.py). Listed alphabetically, not ranked.",
            "Depth order (2nd / 3rd / 4th string) is not published by nfl.com, so it is left blank.",
            "Generic 'DB' roster players cannot be assigned to CB or S, so they are listed but not counted.",
            "Roster pages show the roster at the time they were fetched; they are not a Week 10 snapshot.",
        ],
        "summary": summary,
        "clubs": club_rows,
        "entries": entries,
        "flags": flags,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "register.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    fields = ["week", "club", "player", "injury_position", "game_status", "injury", "practice_status",
              "match", "roster_position", "roster_status", "roster_experience", "backup_count",
              "backups", "depth_rank", "injury_source", "roster_url"]
    with open(os.path.join(OUT_DIR, "register.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for e in entries:
            row = {k: e.get(k) for k in fields}
            row["backups"] = "; ".join(b["name"] for b in e["backups"])
            w.writerow(row)

    # Every rendered row must carry an https source link (the rule the whole site follows).
    for e in entries:
        assert e["injury_source"].startswith("https://"), e["player"]
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(render(payload))
    print(json.dumps(summary, indent=1))
    return 0


TEAMS_URL_FALLBACK = "https://www.nfl.com/teams/"


def link(url: str | None, label: str) -> str:
    if not url:
        return "<span class='blank'>blank</span>"
    return f"<a class='src' href='{html.escape(url)}' target='_blank' rel='noopener'>{html.escape(label)}</a>"


def render(p: dict) -> str:
    s = p["summary"]
    entries = p["entries"]
    rows = []
    for e in entries:
        backups = "<br>".join(
            f"{link(b['player_url'], b['name'])} <small>{html.escape(b['position'] or '')}"
            f" · exp {html.escape(str(b['experience'] or 'blank'))}"
            f" · {html.escape(b['college'] or 'blank')}</small>" for b in e["backups"]) or "<em>none listed as ACT in the same group</em>"
        flags_txt = "; ".join(e["row_flags"]) or "—"
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(e['club'] or '')}</strong></td>"
            f"<td>{link(e.get('injury_player_url'), e['player'] or '')}<br><small>{html.escape(e.get('roster_position') or e.get('injury_position') or '')}</small></td>"
            f"<td><strong>{html.escape(e['game_status'] or '')}</strong></td>"
            f"<td>{html.escape(e['injury'] or 'blank')}<br><small>{html.escape(e['practice_status'] or 'blank')}</small></td>"
            f"<td>{html.escape(e['match'] or '')}<br><small>roster status: {html.escape(str(e['roster_status'] or 'blank'))}</small></td>"
            f"<td>{e['backup_count'] if e['match'] == 'exact name on official roster' else 'blank'}"
            f"<br><small>not counted (non-ACT same group): {e['non_active_same_group']}</small></td>"
            f"<td>{backups}</td>"
            "<td><span class='blank'>blank</span><br><small>nfl.com publishes no depth order</small></td>"
            f"<td>{link(INJURY_URL, 'injury report')}<br>{link(e.get('roster_url'), 'club roster')}</td>"
            f"<td><small>{html.escape(flags_txt)}</small></td>"
            "</tr>")
    club_rows = "".join(
        f"<tr><td><strong>{html.escape(c['club'])}</strong></td><td>{c['designations']}</td>"
        f"<td>{c['min_active_same_group_backups'] if c['min_active_same_group_backups'] is not None else 'blank'}</td>"
        f"<td><small>{html.escape(c['designated_players'])}</small></td>"
        f"<td>{link(c['roster_url'], 'club roster')}</td></tr>" for c in p["clubs"])
    flag_rows = "".join(
        f"<tr><td>{html.escape(f['id'])}</td><td>{html.escape(f['kind'])}</td><td>{html.escape(f['text'])}</td>"
        f"<td>{link(f['source'], 'source')}</td></tr>" for f in p["flags"]) or \
        "<tr><td colspan='4'>No flags.</td></tr>"
    method = "".join(f"<li>{html.escape(m)}</li>" for m in p["method"])
    nav = [
        ("../index.html", "Overview"), ("sections.html", "All Sections"), ("lines.html", "My Lines"),
        ("strategies.html", "Strategy Lab"), ("injuries.html", "Injuries &amp; Depth"),
        ("props.html", "Props"), ("questions.html", "Questions"), ("suggestions.html", "Suggestions"),
        ("evidence.html", "Evidence"), ("review.html", "Flagged for Review"), ("executive.html", "Executive Summary"),
    ]
    nav_html = "".join(f"<a href='{h}'>{t}</a>" for h, t in nav)
    gen = html.escape(p["generated_at"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Backup Register · NFL Decision Lab</title>
<meta name="description" content="Official game designations joined to same-position active backups on each club's official nfl.com roster.">
<link rel="stylesheet" href="../assets/style.css">
<style>
 .blank{{color:#8a6d00;font-style:italic}}
 table.reg{{font-size:.9rem}}
 table.reg td small{{color:#555}}
 .wrap{{overflow-x:auto}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <a class="brand" href="../index.html"><span class="mark">NFL</span><span class="brand-text">Decision Lab</span></a>
  <nav aria-label="Main">{nav_html}</nav>
</header>
<main id="main">
  <section class="page-head">
    <p class="eyebrow">Evidence-first dashboard · new register</p>
    <h1>Backup Register (official rosters)</h1>
    <p class="standfirst">Every official Week {p['week']} game designation (Out, Doubtful, Questionable), joined to the
    same-position players who are ACT on that club's official nfl.com roster. Depth order is blank because nfl.com
    does not publish one.</p>
    <p class="timestamp">Built {gen} · status {html.escape(p['status'])} · every row links to its source</p>
  </section>
  <section class="kpis">
    <article class="kpi"><span class="kpi-label">Game designations</span><strong class="kpi-value">{s['designations_total']}</strong><span class="kpi-sub">Out {s['by_status'].get('Out', 0)} · Doubtful {s['by_status'].get('Doubtful', 0)} · Questionable {s['by_status'].get('Questionable', 0)}</span></article>
    <article class="kpi"><span class="kpi-label">Matched to official roster</span><strong class="kpi-value">{s['matched_to_roster']}</strong><span class="kpi-sub">unmatched {s['unmatched']}</span></article>
    <article class="kpi"><span class="kpi-label">Zero active same-group backups</span><strong class="kpi-value">{s['with_zero_active_backups']}</strong><span class="kpi-sub">on the official roster</span></article>
    <article class="kpi"><span class="kpi-label">Rosters parsed</span><strong class="kpi-value">{s['rosters_parsed']}</strong><span class="kpi-sub">of 32 official club pages</span></article>
    <article class="kpi"><span class="kpi-label">Depth order</span><strong class="kpi-value">blank</strong><span class="kpi-sub">no official source (flagged)</span></article>
  </section>
  <section class="panel">
    <h2>Designated players and their same-position backups</h2>
    <p>Backups are players on the same club with roster status ACT and the same position group. They are listed alphabetically,
    not ranked. A count of zero means no other ACT player in that group is on the official roster; it is not a claim about who
    would start.</p>
    <div class="wrap"><table class="reg">
      <thead><tr><th>Club</th><th>Player</th><th>Game status</th><th>Injury · practice</th><th>Match</th><th>Active same-group backups</th><th>Backups (official roster)</th><th>Depth order (2nd/3rd/4th)</th><th>Sources</th><th>Flags</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table></div>
  </section>
  <section class="panel">
    <h2>By club</h2>
    <div class="wrap"><table class="reg">
      <thead><tr><th>Club</th><th>Designations</th><th>Lowest active same-group backup count</th><th>Designated players</th><th>Source</th></tr></thead>
      <tbody>{club_rows}</tbody>
    </table></div>
  </section>
  <section class="panel">
    <h2>Flagged for review</h2>
    <p>Each flag is an irregularity or an unverified item. None of them changes a value on this page; they say what could not be confirmed.</p>
    <div class="wrap"><table class="reg">
      <thead><tr><th>ID</th><th>Kind</th><th>What needs review</th><th>Source</th></tr></thead>
      <tbody>{flag_rows}</tbody>
    </table></div>
  </section>
  <section class="panel">
    <h2>Method and limits</h2>
    <ul>{method}</ul>
    <p>Sources: <a class="src" href="{INJURY_URL}" target="_blank" rel="noopener">nfl.com/injuries</a> ·
    <a class="src" href="https://www.nfl.com/teams/" target="_blank" rel="noopener">nfl.com team directory</a> ·
    per-club rosters at <code>nfl.com/teams/&lt;club&gt;/roster</code> (linked in every row).</p>
  </section>
</main>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
