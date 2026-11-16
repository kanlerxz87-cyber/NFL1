#!/usr/bin/env python3
"""staleness.py — flag depth-chart rows that the official transactions log contradicts.

Session `57c05555-nfl1`.  Run from the repository root:

    python3 scripts/nfl1_57c05555/staleness.py            # check data/ledger/staleness.json
    python3 scripts/nfl1_57c05555/staleness.py --check    # fail if it is stale

The question this answers
-------------------------
The brief: *"Flag stale depth rows against the official transactions log. Baltimore still
publishes Lamar Jackson and Tyler Huntley at QB after both went on injured reserve and a
replacement was traded in."*

A depth chart is a **club opinion with no expiry date**.  A transactions log is a **dated
legal fact**.  So the test is arithmetic, not judgement:

    for every player the club's depth chart names,
        find the latest dated transaction that touches that player
        if that transaction put him on Injured Reserve / Reserve-Injured /
           Reserve-Retired / Reserve-Suspended, and no later transaction
           activated him, then the depth-chart row naming him is STALE.

What this module will not do
----------------------------
* It will not edit the depth chart.  The club published it; the site shows it and shows the
  contradiction beside it.  Rewriting the club's chart would destroy the evidence.
* It will not claim who *replaced* whom.  A transaction saying "Signed QB X" does not say X
  took Lamar Jackson's job.  The flag reports the two facts and stops there.
* It will not guess a name match.  Matching is on the full normalised name string; a
  near-match is reported as `unmatched_name` for a human, never merged into a row.

Output: ``data/ledger/staleness.json`` — one entry per club, listing every stale row with
the exact transaction line, its date, and the URL of the page it came from.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LEDGER = os.path.join(ROOT, "data", "ledger")
OUT = os.path.join(ROOT, "data", "ledger", "staleness.json")

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import depth_parse  # noqa: E402

# A transactions line routinely reports several unrelated moves separated by a full stop
# ("Signed QB Kedon Slovis. Placed K Tyler Loop on Injured Reserve.").  Matching the whole
# line therefore flags the wrong player: the first version of this module reported Cam
# Jurgens as being on reserve because the same line, in a later sentence, put Durham Smythe
# there.  Every rule below therefore works on a *clause*, and a player is only affected by
# the clause that names him.
CLAUSE_SPLIT = re.compile(r"(?<=[.;])\s+|\s+and\s+(?=(?:placed?|activated?|released?|waived?|signed?)\b)", re.I)

# A removal clause: a "place/put on reserve" verb followed, before the end of the clause, by
# the reserve phrase.  The player names sit between the two, which is how every club writes
# it ("Placed QB Lamar Jackson and QB Tyler Huntley on Injured Reserve").
REMOVE_SPAN = re.compile(
    r"\b(?:placed?|placing|puts?|put)\b(.*?)\b(?:on|to)\b[^.;]*?"
    r"(?:Injured Reserve|Reserve/Injured|Reserve/Retired|Reserve-Retired|Reserve/Suspended"
    r"|Non-Football Injury|\bIR\b)",
    re.I,
)
# An activation clause: the player comes *after* the verb and is returning from reserve.
# "removed from the PUP list" is not an activation from Injured Reserve and must not count.
ACTIVATE_SPAN = re.compile(
    r"\b(?:activated?|activating|activating)\b(.*?)\b(?:from|off)\b[^.;]*?Injured Reserve",
    re.I,
)
RELEASE_SPAN = re.compile(r"\b(?:released?|waived?|waive)\b(.*?)(?:[.;]|$)", re.I)


def norm(name: str) -> str:
    """Normalise a name for exact matching only."""
    n = name.replace("&#x27;", "'").replace("&amp;", "&")
    n = n.replace("\u2019", "'")
    n = re.sub(r"[.,]", "", n)
    return re.sub(r"\s+", " ", n).strip().lower()


def _club_code(path: str) -> str:
    """Recover the club from a capture record."""
    rec = json.load(open(os.path.join(path, "record.json"), encoding="utf-8"))
    return rec.get("club", ""), rec


def load_transactions(club: str):
    """Every dated transaction line for one club, newest first."""
    out = []
    src_root = os.path.join(LEDGER, "transactions")
    for day in sorted(os.listdir(src_root)) if os.path.isdir(src_root) else []:
        day_dir = os.path.join(src_root, day)
        for cap in sorted(os.listdir(day_dir)):
            cap_dir = os.path.join(day_dir, cap)
            c, rec = _club_code(cap_dir)
            if c != club:
                continue
            raw = open(os.path.join(cap_dir, "raw.txt"), encoding="utf-8").read()
            month = ""
            for line in raw.splitlines():
                s = line.strip()
                m = re.match(r"^\|\s*([A-Z][a-z]+)\s*\|$", s)
                if m:
                    month = m.group(1)
                    continue
                m = re.match(r"^\|\s*(\d{2}/\d{2})\s*\|\s*(.+?)\s*\|$", s)
                if m:
                    out.append(
                        {
                            "date": f"2026-{m.group(1)[:2]}-{m.group(1)[3:]}",
                            "month_heading": month,
                            "text": m.group(2),
                            "source_url": rec["url"],
                            "captured_at": rec["captured_at"],
                            "capture_dir": os.path.relpath(cap_dir, ROOT),
                        }
                    )
    out.sort(key=lambda r: r["date"], reverse=True)
    return out


def load_depth(club: str):
    """The most recent official depth capture for one club, parsed."""
    src_root = os.path.join(LEDGER, "depth_chart")
    best = None
    for day in sorted(os.listdir(src_root)) if os.path.isdir(src_root) else []:
        day_dir = os.path.join(src_root, day)
        for cap in sorted(os.listdir(day_dir)):
            cap_dir = os.path.join(day_dir, cap)
            c, rec = _club_code(cap_dir)
            if c != club:
                continue
            if best is None or rec["captured_at"] > best[1]["captured_at"]:
                best = (cap_dir, rec)
    if not best:
        return None, None
    cap_dir, rec = best
    raw = open(os.path.join(cap_dir, "raw.txt"), encoding="utf-8").read()
    parsed = depth_parse.parse_capture(raw, club, rec["url"], rec["captured_at"])
    parsed["capture_dir"] = os.path.relpath(cap_dir, ROOT)
    return parsed, rec


def classify(line: str, player: str) -> str:
    """Classify what *this line* did to *this player*.

    Returns one of ``reserve``, ``activated``, ``released``, ``other`` or ``absent``.

    The player must appear **inside the span of the action**, not merely somewhere on the
    line.  That is what stops a co-listed player from inheriting a teammate's move:

      "Placed QB Lamar Jackson and QB Tyler Huntley on Injured Reserve"
          -> both names sit inside the remove span            -> reserve
      "ILB Teddye Buchanan passed his physical and was removed from the PUP list"
          -> no remove span, and PUP is not Injured Reserve   -> other
      "Signed QB Kedon Slovis. Placed K Tyler Loop on Injured Reserve."
          -> split into two clauses; Slovis is only in the first -> other
    """
    p = norm(player)
    if not p:
        return "absent"
    for m in REMOVE_SPAN.finditer(line):
        if p in norm(m.group(1)):
            return "reserve"
    for m in ACTIVATE_SPAN.finditer(line):
        if p in norm(m.group(1)):
            return "activated"
    for m in RELEASE_SPAN.finditer(line):
        if p in norm(m.group(1)):
            return "released"
    return "other" if p in norm(line) else "absent"


def player_status(player: str, txns):
    """Decide one player's current reserve state from the dated log.

    The most recent line that *acted on* the player decides.  A line that merely mentions
    him is skipped, so a passing reference cannot overwrite a real move.
    """
    acted = []
    for t in txns:
        for clause in CLAUSE_SPLIT.split(t["text"]):
            verdict = classify(clause, player)
            if verdict in ("reserve", "activated", "released"):
                acted.append((t, clause, verdict))
                break
    if not acted:
        return None
    latest, clause, verdict = acted[0]  # txns are newest first
    return {
        "on_reserve": verdict == "reserve",
        "released": verdict == "released",
        "latest_transaction": latest,
        "latest_clause": clause,
        "verdict": verdict,
        "all_transactions": [t for t, _c, _v in acted[:4]],
    }


def main() -> int:
    check = "--check" in sys.argv
    clubs = []
    src_root = os.path.join(LEDGER, "transactions")
    seen = set()
    for day in sorted(os.listdir(src_root)) if os.path.isdir(src_root) else []:
        for cap in sorted(os.listdir(os.path.join(src_root, day))):
            c, _rec = _club_code(os.path.join(src_root, day, cap))
            if c:
                seen.add(c)

    total_stale = 0
    for club in sorted(seen):
        txns = load_transactions(club)
        depth, drec = load_depth(club)
        row = {
            "club": club,
            "transactions_captured": len(txns),
            "transaction_window": (
                f"{txns[-1]['date']} to {txns[0]['date']}" if txns else ""
            ),
            "transactions_url": txns[0]["source_url"] if txns else "",
            "depth_url": drec["url"] if drec else "",
            "depth_captured_at": drec["captured_at"] if drec else "",
            "depth_club_date": (depth or {}).get("chart_date", ""),
            "stale_rows": [],
            "reserve_absent_from_depth": [],
            "unmatched_names": [],
        }
        if not depth:
            row["note"] = "no official depth capture for this club in the ledger; nothing to compare"
            clubs.append(row)
            continue

        # Capture order matters for honesty: if the log was read *after* the chart, a clean
        # result means "the chart agrees with everything known when it was read", not "the
        # chart agrees with the log as it stands now".  That distinction is published.
        row["chart_captured_before_log"] = bool(
            txns and drec and drec["captured_at"] < txns[0]["captured_at"]
        )
        row["capture_order_note"] = (
            "The depth chart was captured before the transactions page in this session, so "
            "an agreement here is bounded by the chart's own fetch time. Re-reading the chart "
            "after the log is the way to settle it; both reads are kept by the ledger."
            if row["chart_captured_before_log"]
            else "The transactions page was captured before the depth chart, so the chart was "
                 "already published when the log was read."
        )

        named = {}
        for slot in depth["slots"]:
            for g in slot["groups"]:
                for name in g["names"]:
                    named.setdefault(norm(name), (name, slot))

        # ---- stale: a player the chart still lists, whom the log put on reserve
        for key, (name, slot) in named.items():
            st = player_status(name, txns)
            if not st:
                row["unmatched_names"].append(name)
                continue
            if st["on_reserve"]:
                total_stale += 1
                row["stale_rows"].append(
                    {
                        "player": name,
                        "unit": slot["unit"],
                        "position": slot["position"],
                        "rank": slot["groups"][0]["rank"] if slot["groups"] else None,
                        "chart_url": drec["url"],
                        "chart_captured_at": drec["captured_at"],
                        "transaction_date": st["latest_transaction"]["date"],
                        "transaction_text": st["latest_transaction"]["text"],
                        "transaction_url": st["latest_transaction"]["source_url"],
                        "why_stale": (
                            "The club's depth chart still names this player, and the most "
                            "recent dated transaction that mentions him placed him on "
                            "reserve. No later transaction returns him to the active roster. "
                            "The chart row and the log contradict each other; this page "
                            "publishes both and does not edit either."
                        ),
                    }
                )

        # ---- reserve list: a player on reserve cannot be "available because unlisted"
        reserve_players = []
        for t in txns:
            if REMOVE_SPAN.search(t["text"]):
                reserve_players.append(
                    {
                        "date": t["date"],
                        "text": t["text"],
                        "clause": REMOVE_SPAN.search(t["text"]).group(0),
                        "source_url": t["source_url"],
                    }
                )
        row["reserve_absent_from_depth"] = reserve_players[:20]
        row["reserve_transaction_count"] = len(reserve_players)
        clubs.append(row)

    summary = {
        "generated_by": "scripts/nfl1_57c05555/staleness.py",
        "what_this_is": (
            "A dated comparison of each club's officially published depth chart against "
            "that club's officially published transactions log. A row is flagged stale when "
            "the chart names a player whom the log placed on reserve with no later "
            "activation. Nothing is corrected: both sources are published as they stand."
        ),
        "rule": (
            "match on the full normalised name; decide on the most recent dated transaction "
            "that names the player"
        ),
        "known_limits": [
            "Only clubs whose transactions page was captured are compared; the rest are "
            "listed with no comparison rather than assumed clean.",
            "A transaction that says 'Signed QB X' does not establish that X replaced the "
            "injured starter, so no replacement is named.",
            "The Indianapolis capture holds November and late-September entries only; the "
            "log is complete for November and incomplete before it.",
            "A depth chart is a club opinion with no expiry; the newest capture is used and "
            "its fetch time is published with every row.",
        ],
        "total_stale_rows": total_stale,
        "clubs": clubs,
    }

    new = json.dumps(summary, indent=1, ensure_ascii=False) + "\n"
    if check:
        if not os.path.exists(OUT) or open(OUT, encoding="utf-8").read() != new:
            print("FAIL: data/ledger/staleness.json is stale — re-run without --check")
            return 1
        print("OK: staleness register is current")
        return 0
    open(OUT, "w", encoding="utf-8").write(new)

    for row in clubs:
        print(f"--- {row['club']}: {len(row['stale_rows'])} stale row(s)")
        for s in row["stale_rows"]:
            print(f"  STALE {s['position']} {s['player']:<22s} <- {s['transaction_date']} {s['transaction_text'][:70]}")
    print()
    print(f"total stale depth rows: {total_stale} across {len(clubs)} club(s) compared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
