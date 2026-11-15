#!/usr/bin/env python3
"""Cross-page conflict audit for three Week 10 injury rows (Detroit Lions).

What it does, and nothing more:
  1. Reads the OFFICIAL values that were read from https://www.nfl.com/injuries/
     on 2026-11-15 (fetched through the fetch tool; quoted below, row by row).
  2. Scans every published HTML page in the repository for a table row that
     names one of the three players.
  3. For each hit, records the practice and game-status cells the page shows
     and compares them with the official values. Writes room/data/lions_w10_conflicts.json.

Nothing is filled in: a cell the page does not show is recorded as "blank".
Run:  python3 room/audit_lions_w10.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "data", "lions_w10_conflicts.json")
OFFICIAL_URL = "https://www.nfl.com/injuries/"
REPO_BLOB = "https://github.com/kanlerxz87-cyber/NFL1/blob/main/"

# Official values, read from nfl.com/injuries (Week 10, Detroit Lions block), 2026-11-15.
OFFICIAL = {
    "Kerby Joseph": {"pos": "S", "injury": "Knee", "practice": "Did Not Participate In Practice", "game": "Out"},
    "Cade Mays": {"pos": "C", "injury": "Ankle", "practice": "Did Not Participate In Practice", "game": "Out"},
    "D.J. Reed": {"pos": "CB", "injury": "Hip", "practice": "Did Not Participate In Practice", "game": "Out"},
}

PRACTICE_LABELS = [
    ("Did Not Participate", "DNP"),
    ("Limited", "LP"),
    ("Full Participation", "FP"),
    ("Full", "FP"),
]
SKIP_DIRS = {".git", "node_modules"}


class _Rows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def _practice(cells: list[str]) -> str:
    # Cell by cell, first cell that carries a practice label wins. Cells longer than
    # 120 characters (embedded JSON, notes) are not status cells and are ignored.
    for c in cells:
        if len(c) > 120:
            continue
        if c in ("DNP", "LP", "FP"):  # abbreviation written as the whole cell
            return c
        for needle, code in PRACTICE_LABELS:
            if needle in c:
                return code
    return "blank"


def _game(cells: list[str]) -> str:
    for c in cells:
        if c in ("Out", "Questionable", "Doubtful"):
            return c
    return "blank"


def _html_files() -> list[str]:
    out = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if f.endswith(".html"):
                out.append(os.path.join(dp, f))
    return sorted(out)


def audit() -> dict:
    hits = []
    seen = set()
    skipped = 0
    for path in _html_files():
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        p = _Rows()
        with open(path, encoding="utf-8", errors="replace") as fh:
            p.feed(fh.read())
        for cells in p.rows:
            for name, off in OFFICIAL.items():
                if not any(name in c for c in cells):
                    continue
                practice = _practice(cells)
                game = _game(cells)
                if practice == "blank" and game == "blank":
                    # A depth-chart or roster row, not an injury-report claim: out of scope.
                    skipped += 1
                    continue
                key = (rel, name, practice, game)
                if key in seen:
                    continue
                seen.add(key)
                problems = []
                differs = False
                if game == "blank":
                    problems.append(f"game cell blank, official {off['game']}")
                elif game != off["game"]:
                    problems.append(f"game shows {game}, official {off['game']}")
                    differs = True
                if practice == "blank":
                    problems.append("practice cell blank, official DNP")
                elif practice != "DNP":
                    problems.append(f"practice shows {practice}, official DNP")
                    differs = True
                result = "differs" if differs else ("missing" if problems else "matches official")
                hits.append({
                    "page": rel,
                    "page_url": REPO_BLOB + rel,
                    "player": name,
                    "club": "DET",
                    "practice_shown": practice,
                    "game_shown": game,
                    "official_practice": "DNP",
                    "official_game": off["game"],
                    "result": result,
                    "detail": "; ".join(problems) if problems else "",
                    "official_url": OFFICIAL_URL,
                })
    order = {"differs": 0, "missing": 1, "matches official": 2}
    hits.sort(key=lambda h: (order[h["result"]], h["page"], h["player"]))
    return {
        "meta": {
            "official_url": OFFICIAL_URL,
            "official_read": "2026-11-15",
            "official_values": OFFICIAL,
            "method": "Every published HTML page in the repository is parsed. Every table row that names one of the three players and makes an injury or practice claim is compared with the official values above. differs = the page shows a different value; missing = the cell the official value belongs in is blank; matches official = the shown values equal the official values. Rows that name a player with no injury claim (depth charts, rosters) are skipped and counted.",
            "rows_checked": len(hits),
            "rows_skipped_not_injury_claims": skipped,
            "pages_checked": len({h["page"] for h in hits}),
            "differs": sum(1 for h in hits if h["result"] == "differs"),
            "missing": sum(1 for h in hits if h["result"] == "missing"),
            "matches": sum(1 for h in hits if h["result"] == "matches official"),
            "reproduce": "python3 room/audit_lions_w10.py",
        },
        "rows": hits,
    }


def main() -> int:
    data = audit()
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    m = data["meta"]
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {m['rows_checked']} rows on {m['pages_checked']} pages, "
          f"{m['differs']} differ, {m['missing']} missing, {m['matches']} match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
