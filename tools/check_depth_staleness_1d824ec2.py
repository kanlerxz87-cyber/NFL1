#!/usr/bin/env python3
"""check_depth_staleness_1d824ec2.py — name every depth or lineup row the official transactions
register says a club has since moved past.

Session 1d824ec2-nfl1 (task V4), answering the brief's "flag stale depth rows against the official
transactions log" (readiness IN-22) and "treat roster turnover as a first-class data event"
(IN-20) with a printed comparison instead of an assertion.

For every player named in a committed depth or availability artifact, this reads that player's
dated events in the league's own register and reports the three cases a reader can act on:

  leaves-a-club      the register shows a trade, release, waiver claim or termination *away from*
                     the club that still prints him. Where the artifact's own capture date is
                     later than the move, the club printed him after the move happened; where it
                     is earlier, the artifact simply predates the move and needs a refresh. The
                     two are labelled separately, because only the first is a contradiction.
  on-a-reserve-list  the register shows him on a reserve list as of a date, and the artifact still
                     prints him in a depth slot. A reserve designation does not remove a player
                     from a club's roster, so this is not a contradiction; it is the difference
                     between "on the roster" and "able to play".
  arrives            (not reported as a defect) a player the register shows *joining* the club is
                     skipped unless the club's later row contradicts it.

Rules of restraint:
* artifacts are read read-only; nothing here edits another session's file;
* a finding never concludes that the club is wrong — the club's page carries its own date;
* names are matched on the printed name. Where one name carries events for several clubs, the
  club of the event must equal the club of the artifact row, so a shared name cannot manufacture a
  finding for the wrong club;
* an artifact whose rows carry no player names is reported as such rather than silently scoring 0.

Run: python3 tools/check_depth_staleness_1d824ec2.py          (writes data/reserve/depth_staleness.json)
     python3 tools/check_depth_staleness_1d824ec2.py --quiet
Exit 0 normally; 2 when the register has not been captured yet, so "could not run" is never read
as "found nothing".
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "reserve"
OUT = STORE / "depth_staleness.json"

AWAY_WORDS = re.compile(r"\b(traded|released|waived|terminated|assigned to|waiver claimed)\b", re.I)
RESERVE_WORDS = re.compile(r"reserve/", re.I)
ARRIVE_WORDS = re.compile(r"\b(traded|signed|claimed|acquired|activated|signed to the active)\b",
                          re.I)

# (label, file, reader, nature)
#   current-roster-claim : the artifact presents itself as who is available or ranked now, so an
#                          official move it has not absorbed contradicts the artifact.
#   dated-snapshot       : the artifact is a record of one dated page (a weekly report). A later
#                          move does not make it wrong, it makes it superseded, which a reader
#                          still needs to know, so it is reported under its own label.
ARTIFACTS = [
    ("depth register (official club pages)", "data/depth/official_register.json", "register",
     "current-roster-claim"),
    ("depth_chart.json (repo chart, s1-s4 columns)", "data/depth_chart.json", "depth_chart",
     "current-roster-claim"),
    ("model availability (pipeline)", "data/model/availability.json", "availability",
     "current-roster-claim"),
    ("week 10 injury report (repo copy)", "data/verified/injury_report_2026_week10.tsv",
     "injury_tsv", "dated-snapshot"),
]


SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def name_key(name: str) -> str:
    """Punctuation-insensitive printed name. A generational suffix is KEPT: two players can share
    a base name in one league, so dropping it to force a match would invent a finding. The
    suffix-free form is used only as a second, clearly labelled lookup (see `lookup_events`)."""
    n = re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()
    return re.sub(r"\s+", " ", n)


def lookup_events(name: str, events: dict) -> tuple[list[dict], str]:
    """Exact printed name first; then the same name without a generational suffix.

    Returns (events, match label). An ambiguous suffix-free match (several players behind one
    base name) is reported as ambiguous and no finding is raised from it: a comparison that could
    belong to either player is not a comparison.
    """
    key = name_key(name)
    if not key:
        return [], "no printed name"
    if events.get(key):
        return events[key], "exact printed name"
    tokens = key.split()
    if tokens and tokens[-1] in SUFFIXES:
        base = " ".join(tokens[:-1])
        hits = [e for k, evs in events.items() if k == base for e in evs]
        if hits:
            n_names = len({e.get("player") for e in hits})
            return hits, (f"base name without the generational suffix ({n_names} printed name"
                          f"{'s' if n_names != 1 else ''} behind it)")
    return [], "no dated event for this printed name"


def norm_date(v) -> str | None:
    s = str(v or "")[:10]
    return s if re.match(r"^\d{4}-\d{2}-\d{2}$", s) else None


# --- artifact readers: each returns a list of dicts with club / player / date / where / source ---

def read_register(doc: dict) -> list[dict]:
    out = []
    for r in doc.get("rows") or []:
        for nm in (r.get("names") or []):
            out.append({"club": r.get("club"), "player": nm, "date": norm_date(r.get("fetched")),
                        "where": f"{r.get('unit')}/{r.get('position')} column {r.get('column')}"
                                 f" (raw cell {r.get('raw_cell')!r})",
                        "source_url": r.get("source_url"),
                        "label": r.get("page_label")})
    return out


def read_depth_chart(doc) -> list[dict]:
    out = []
    rows = doc if isinstance(doc, list) else (doc.get("teams") if isinstance(doc, dict) else None)
    if isinstance(rows, dict):
        rows = [{**v, "code": k} for k, v in rows.items()]
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        club = r.get("code") or r.get("team")
        for col in ("s1", "s2", "s3", "s4"):
            nm = (r.get(col) or "").strip()
            if not nm:
                continue
            out.append({"club": club, "player": nm, "date": norm_date(r.get("retrieved")),
                        "where": f"{r.get('unit')}/{r.get('pos')} {col}",
                        "source_url": r.get("source_url") or r.get("src"),
                        "label": r.get("chart_label")})
    return out


def read_availability(doc: dict) -> list[dict]:
    out = []
    for t in doc.get("teams") or []:
        if not isinstance(t, dict):
            continue
        club = t.get("team") or t.get("abbr")
        for p in t.get("players") or []:
            if isinstance(p, dict) and p.get("player"):
                out.append({"club": club, "player": p["player"],
                            "date": norm_date(t.get("retrieved") or t.get("fetched")),
                            "where": f"{p.get('pos','')}/{p.get('status','')}".strip("/"),
                            "source_url": t.get("source_url"), "label": "availability layer"})
            elif isinstance(p, str):
                out.append({"club": club, "player": p,
                            "date": norm_date(t.get("retrieved")), "where": "",
                            "source_url": t.get("source_url"), "label": "availability layer"})
    return out


def read_injury_tsv(text: str) -> list[dict]:
    out = []
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return out
    head = lines[0].split("\t")
    idx = {h: i for i, h in enumerate(head)}
    for line in lines[1:]:
        c = line.split("\t")
        player = (c[idx["player"]] if "player" in idx and idx["player"] < len(c) else "").strip()
        club = (c[idx["team_abbr"]] if "team_abbr" in idx and idx["team_abbr"] < len(c) else
                (c[idx["team"]] if "team" in idx and idx["team"] < len(c) else "")).strip()
        if not player:
            continue
        out.append({"club": club, "player": player, "date": None,
                    "where": f"{c[idx['game_status']] if 'game_status' in idx and idx['game_status'] < len(c) else ''}".strip(),
                    "source_url": "https://www.nfl.com/injuries/", "label": "weekly injury report"})
    return out


READERS = {"register": read_register, "depth_chart": read_depth_chart,
           "availability": read_availability, "injury_tsv": read_injury_tsv}


def load_artifact(rel: str):
    p = ROOT / rel
    if not p.exists():
        return None, "absent"
    try:
        if p.suffix == ".tsv":
            return p.read_text(encoding="utf-8"), "text"
        return json.loads(p.read_text(encoding="utf-8")), "json"
    except Exception as exc:  # noqa: BLE001
        return None, f"unreadable ({repr(exc)[:120]})"


def classify(row: dict, evs: list[dict]) -> dict | None:
    """Return a finding for this artifact row, or None when the register does not contradict it."""
    last = None
    for e in reversed(evs):
        if not e.get("date"):
            continue
        txt = e.get("transaction") or ""
        club_from, club_to = e.get("club_from"), e.get("club_to")
        away = bool(AWAY_WORDS.search(txt))
        reserve = bool(RESERVE_WORDS.search(txt))
        if not (away or reserve):
            continue
        last = dict(e, _away=away, _reserve=reserve)
        break
    if not last:
        return None
    club = row.get("club")
    dated = last.get("date")
    if last["_away"]:
        # He left `club_from`. Only that club's rows are affected.
        if club and last.get("club_from") and club != last.get("club_from"):
            return None
        # A later event bringing him back to the same club cancels it.
        for e in evs:
            if (e.get("date") or "") > (dated or "") and e.get("club_to") == club \
                    and ARRIVE_WORDS.search(e.get("transaction") or ""):
                return None
        kind = "moved away from the club"
    else:
        same = club and (club == last.get("club_from") or club == last.get("club_to"))
        if club and not same:
            return None
        # A later off-reserve event cancels it.
        for e in evs:
            if (e.get("date") or "") > (dated or "") and re.search(
                    r"(designated to return|activated|reinstated)", e.get("transaction") or "", re.I):
                return None
        kind = "on a reserve list"
    art_date = row.get("date")
    timing = ("artifact captured after the move" if art_date and art_date > dated
              else "artifact predates the move: refresh needed" if art_date
              else "artifact carries no capture date: cannot tell which side of the move it is on")
    return {
        "artifact": row.get("_artifact"), "artifact_file": row.get("_file"),
        "artifact_nature": row.get("_nature") or "current-roster-claim",
        "artifact_date": art_date, "artifact_timing": timing,
        "club": club, "player": row["player"], "slot": row.get("where"),
        "artifact_source_url": row.get("source_url"), "artifact_label": row.get("label"),
        "kind": kind, "latest_event": f"{last.get('transaction')} ({last.get('category')})",
        "event_date": dated, "event_club_from": last.get("club_from"),
        "event_club_to": last.get("club_to"), "source_url": last.get("source_url"),
        "player_url": last.get("player_url"),
        "events_seen": len(evs),
        "match": row.get("_match") or "exact printed name",
    }


def main() -> int:
    tx_path = STORE / "transactions.json"
    if not tx_path.exists():
        print("FAIL no data/reserve/transactions.json yet: the sweep has not run, so this check "
              "could not be performed (that is not the same as finding nothing)")
        return 2
    tx = json.loads(tx_path.read_text(encoding="utf-8"))
    rows = tx.get("rows") or []
    events: dict[str, list[dict]] = {}
    for r in rows:
        events.setdefault(name_key(r.get("player")), []).append(r)
    for k in events:
        events[k].sort(key=lambda e: e.get("date") or "")

    findings: list[dict] = []
    finding_at: dict[tuple, dict] = {}
    ambiguous: list[dict] = []
    artifact_stats: list[dict] = []
    for label, rel, kind, nature in ARTIFACTS:
        doc, how = load_artifact(rel)
        if doc is None:
            artifact_stats.append({"artifact": label, "file": rel, "names": 0, "nature": nature,
                                  "status": how})
            continue
        try:
            pairs = READERS[kind](doc)
        except Exception as exc:  # noqa: BLE001
            artifact_stats.append({"artifact": label, "file": rel, "names": 0, "nature": nature,
                                   "status": f"reader failed: {repr(exc)[:160]}"})
            continue
        for p in pairs:
            p["_artifact"] = label
            p["_file"] = rel
            p["_nature"] = nature
        artifact_stats.append({"artifact": label, "file": rel, "names": len(pairs),
                               "nature": nature,
                               "status": "ok" if pairs else
                               "no player name can be read from this artifact, so a per-team view "
                               "built on it cannot name anyone"})
        for row in pairs:
            evs, match = lookup_events(row.get("player") or "", events)
            if not evs:
                continue
            if match.startswith("base name") and len({e.get("player") for e in evs}) > 1:
                ambiguous.append({"club": row.get("club"), "player": row.get("player"),
                                  "artifact": label, "why": match})
                continue
            row["_match"] = match
            f = classify(row, evs)
            if f:
                # One artifact can print the same player twice (two slots in a depth chart, a
                # duplicate row in the register). That is one staleness finding, not two: counting
                # the repetition would inflate a club's number for a formatting accident. The
                # number of artifact rows behind it is kept as `artifact_rows`.
                sig = (f.get("artifact"), f.get("club"), f.get("player"), f.get("date"),
                       f.get("kind"))
                if sig in finding_at:
                    finding_at[sig]["artifact_rows"] += 1
                    continue
                f["artifact_rows"] = 1
                finding_at[sig] = f
                findings.append(f)

    state_path = STORE / "reserve_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    on_reserve = [p for p, d in (state.get("players") or {}).items()
                  if d.get("on_reserve_as_of_capture")]
    out = {
        "generated_from": "data/reserve/transactions.json + the artifacts named on each finding",
        "note": ("A finding is a printed comparison between a committed artifact and the league's "
                 "dated register. It does not say the club's page is wrong: the page carries its "
                 "own date. It says the row cannot be treated as durable, and it links both sides "
                 "so a reader can check them."),
        "register_rows": len(rows),
        "artifacts": artifact_stats,
        "artifact_names_compared": sum(a["names"] for a in artifact_stats),
        "players_on_open_reserve": len(on_reserve),
        "ambiguous_name_matches": ambiguous,
        "findings_by_kind": {},
        "findings_by_nature": {},
        "findings_clubs": sorted({f["club"] for f in findings if f.get("club")}),
        "findings": findings,
    }
    for f in findings:
        out["findings_by_kind"][f["kind"]] = out["findings_by_kind"].get(f["kind"], 0) + 1
        nat = f["artifact_nature"]
        out["findings_by_nature"][nat] = out["findings_by_nature"].get(nat, 0) + 1
    out["contradictions_of_a_current_claim"] = sum(
        1 for f in findings if f["artifact_nature"] == "current-roster-claim")
    out["rows_superseded_by_a_later_event"] = sum(
        1 for f in findings if f["artifact_nature"] == "dated-snapshot")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    per_artifact = ", ".join(f"{a['artifact'].split(' (')[0]}={a['names']}" for a in artifact_stats)
    print(f"depth staleness vs the official register: {len(findings)} finding(s) across "
          f"{len(out['findings_clubs'])} club(s); {len(on_reserve)} players on an open reserve "
          f"designation; {out['artifact_names_compared']} artifact names compared ({per_artifact})")
    if "--quiet" not in sys.argv:
        for f in findings[:60]:
            print(f"  {f['club']:4} {f['player']:24} {f['event_date']}  {f['kind']}: "
                  f"{f['latest_event']} · {f['artifact_timing']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
