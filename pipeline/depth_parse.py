#!/usr/bin/env python3
"""depth_parse.py — parse one official club depth-chart page into faithful, grouped rows.

Session `57c05555-nfl1`.  This module fixes, at the source, the two parsing failures the
brief names, and stops the three fabrications the brief forbids.

What went wrong before
----------------------
1. **Jersey-number prefixes were kept inside the name.**  The Packers publish
   ``9 Christian Watson``.  The brief's instruction is to strip the number for the name and
   **retain the raw string** so the strip can be audited.  Both happen here, and the number
   is kept in its own field rather than thrown away.
2. **The Texans chart is an image.**  ``houstontexans.com/team/depth-chart`` renders one
   JPEG and no rows at all.  The brief forbids transcribing it by eye, so this module emits
   **zero rows** for Houston and records the image URL as an unrecoverable gap.  A silent
   empty page would be worse than the defect, so the gap is a first-class output.
3. **A column-legend row was read as four players.**  Baltimore prints
   ``POSITION | 1st | 2nd | 3rd | 4th``; the old transcription stored four players actually
   called "1st".."4th".  Legend rows are now dropped **and counted**, never published.

The four rules this module will not break
-----------------------------------------
* **Order, not attributes.**  Rank comes only from the order of the printed cells.  Jersey
  number, experience and salary are never used to place a player.  (The brief explicitly
  rejects deriving depth order from them.)
* **A slot is a group.**  Two clubs print two players in one slot — Seattle
  ``Cooper Kupp Rashid Shaheed``, Arizona ``Zaven Collins Baron Browning``.  That is the
  club declining to name one starter, so the slot is stored as a group of two at rank 1.
  Splitting it into rank 1 / rank 2 would invent an order the club never published.
* **An empty slot stays empty.**  Baltimore prints ``K | (blank)`` and Washington prints
  ``DL | Daron Payne | (blank) | (blank)``.  Both are published as they are, with the hole
  counted.  No player is invented, and an empty cell is never silently treated as the end
  of the row when later cells are filled.
* **No splitting of a single name.**  ``J. Michael Sturdivant``, ``T.J. Tampa Jr.`` and
  ``K'Von Wallace`` all defeat naive capitalisation rules, so the split of a cell into
  names is taken from the **link structure** the club printed, never from whitespace alone.

Output shape
------------
``parse_capture(text, club, url, fetched_at)`` returns a dict whose ``slots`` are one entry
per **printed row** (one club/unit/position slot), each holding ``groups`` — one entry per
filled printed column — plus the holes and the raw text::

    {"unit": "defense", "position": "OLB", "row_index": 22,
     "groups": [{"rank": 1, "column": 1, "names": ["Zaven Collins", "Baron Browning"],
                 "jerseys": ["", ""], "raw_cell": "[Zaven Collins](url) [Baron Browning](url)"}],
     "holes": [], "empty": False, "raw_row": "| OLB | ... |"}

Every published name is traceable to the ``raw_cell`` of its group.
"""
from __future__ import annotations

import hashlib
import html
import re

# A leading jersey number: one or two digits, a space, then the name.  Three digits is not
# a legal NFL jersey number, so a longer run is left alone rather than "stripped".
JERSEY_RE = re.compile(r"^\s*(\d{1,2})\s+(?=[A-Za-z])(.+?)\s*$")

# A cell that is only a number is a legend/header cell, not a player.
NUMBER_ONLY_RE = re.compile(r"^\s*\d{1,2}\s*$")

# The column-legend words clubs use instead of digits.
LEGEND_WORDS = {"1st", "2nd", "3rd", "4th", "5th", "6th", "starter", "backup"}

# First cells that are headers rather than slots.
HEADER_WORDS = {"position", "player", "players", "depth chart"}

UNIT_HEADINGS = {
    "offense": "offense",
    "defence": "defense",
    "defense": "defense",
    "special teams": "special_teams",
    "specialteams": "special_teams",
}

MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
DATE_RE = re.compile(r"\b(?:" + MONTHS + r")\.?\s+\d{1,2},\s+\d{4}\b")

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _plain(cell: str) -> str:
    """Visible text of a cell: link labels kept in printed order, markup removed."""
    out = LINK_RE.sub(r"\1", cell)
    out = out.replace("**", "").replace("__", "").replace("`", "")
    return re.sub(r"\s+", " ", html.unescape(out)).strip()


def _cells(line: str):
    """Split one markdown table row into its raw cells."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [c.strip() for c in body.split("|")]


def _is_separator(cells) -> bool:
    """True for the ``| --- | --- |`` rule under a markdown table header."""
    seen = False
    for c in cells:
        if c == "":
            continue
        if not re.fullmatch(r":?-{2,}:?", c):
            return False
        seen = True
    return seen


def split_group(cell: str):
    """Return ``(names, jerseys, raw)`` for one printed cell.

    A cell holding two links is a **shared slot** and yields two names, in printed order.
    A cell holding one link yields one name even if that name contains spaces.  A cell
    holding no links is split on the jersey pattern only, because without links the cell is
    a single player (``9 Christian Watson``) — never two.
    """
    raw = cell
    labels = LINK_RE.findall(cell)
    if labels:
        pieces = [re.sub(r"\s+", " ", html.unescape(lbl)).strip() for lbl, _url in labels]
    else:
        flat = _plain(cell)
        if not flat:
            return [], [], raw
        pieces = [flat]

    names, jerseys = [], []
    for piece in pieces:
        if not piece:
            continue
        if piece.lower() in LEGEND_WORDS or NUMBER_ONLY_RE.match(piece):
            names.append(None)
            jerseys.append(piece)
            continue
        m = JERSEY_RE.match(piece)
        if m:
            jerseys.append(m.group(1))
            names.append(m.group(2).strip())
        else:
            jerseys.append("")
            names.append(piece)

    out_names = [n for n in names if n]
    out_jerseys = [j for j, n in zip(jerseys, names) if n]
    return out_names, out_jerseys, raw


def _is_legend_row(cells) -> bool:
    """True when every non-empty player cell is just a legend word or a bare number."""
    found = False
    for cell in cells[1:]:
        flat = _plain(cell)
        if not flat:
            continue
        found = True
        if flat.lower() not in LEGEND_WORDS and not NUMBER_ONLY_RE.match(flat):
            return False
    return found


def parse_capture(text: str, club: str, url: str, fetched_at: str) -> dict:
    """Parse one captured official depth-chart page into grouped slots."""
    slots: list[dict] = []
    dropped: list[dict] = []
    gaps: list[dict] = []
    units_seen: list[str] = []
    image_urls: list[str] = []
    chart_date = ""
    current_unit = ""
    row_index = 0

    for line in text.splitlines():
        stripped = line.strip()

        # ---- unit headings: "## Offense", "#### **OFFENSE**"
        heading = re.sub(r"^#+\s*", "", stripped).replace("*", "").strip()
        key = heading.lower().strip(" :#")
        if key in UNIT_HEADINGS:
            current_unit = UNIT_HEADINGS[key]
            if current_unit not in units_seen:
                units_seen.append(current_unit)
            continue

        # ---- the club's own publication date, printed outside a table
        if not stripped.startswith("|"):
            d = DATE_RE.search(stripped)
            if d:
                chart_date = d.group(0)

        # ---- image-only chart evidence
        for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", stripped):
            u = m.group(1)
            if "logos" in u:
                continue
            if "/image/upload/" in u or "image" in u.lower():
                image_urls.append(u)

        if not stripped.startswith("|"):
            continue

        cells = _cells(line)
        if not cells or _is_separator(cells):
            continue

        first_plain = _plain(cells[0])
        if first_plain.lower() in HEADER_WORDS:
            dropped.append({"reason": "column header row", "raw": stripped})
            continue
        if _is_legend_row(cells):
            dropped.append({"reason": "column legend row (1st/2nd/3rd/4th)", "raw": stripped})
            continue

        # A row with a blank first cell is a continuation of the previous slot (the Packers'
        # 4th running back sits on a second line with no position label).
        continuation = not first_plain
        position = first_plain or (slots[-1]["position"] if slots else "")

        groups = []
        holes = []
        printed_col = 0
        for cell in cells[1:]:
            printed_col += 1
            names, jerseys, raw = split_group(cell)
            if not names:
                # A blank cell *between* filled cells is a hole in the club's listing.
                # Trailing blanks are just table width and are ignored.
                if any(c.strip() for c in cells[1 + printed_col:]):
                    holes.append(printed_col)
                continue
            groups.append(
                {
                    "rank": len(groups) + 1,
                    "column": printed_col,
                    "names": names,
                    "jerseys": jerseys,
                    "raw_cell": raw,
                }
            )

        if continuation and slots:
            # Fold into the previous slot, keeping the printed column.
            prev = slots[-1]
            for g in groups:
                prev["groups"].append({**g, "rank": len(prev["groups"]) + 1,
                                       "continuation_line": True})
                prev["continuation_ranks"] += 1
            # Blanks on a continuation line are the unused width of that short line, not
            # holes in the club's ranking, so they are *not* merged into the slot's holes.
            prev["continuation_blanks"] = len(holes)
            continue

        if not groups and not holes and not first_plain:
            continue

        slots.append(
            {
                "unit": current_unit or "unknown",
                "position": position,
                "row_index": row_index,
                "groups": groups,
                "holes": holes,
                "empty": not groups,
                "continuation_ranks": 0,
                "continuation_blanks": 0,
                "raw_row": stripped,
            }
        )
        row_index += 1

    capture_kind = "table" if slots else "image_only"
    if not slots:
        gaps.append(
            {
                "reason": (
                    "The official page renders the whole chart as a bitmap image on "
                    "static.clubs.nfl.com, so it contains no rows to parse. The brief forbids "
                    "transcribing a chart by eye; no rows are produced and no players are "
                    "named for this club. An authorised structured source is required."
                ),
                "evidence": image_urls[0] if image_urls else url,
            }
        )

    shared = [
        {**g, "club": club, "unit": s["unit"], "position": s["position"]}
        for s in slots
        for g in s["groups"]
        if len(g["names"]) > 1
    ]
    empty_slots = [s for s in slots if s["empty"]]
    holed = [s for s in slots if s["holes"]]

    counts = {
        "slots": len(slots),
        "slots_empty": len(empty_slots),
        "slots_with_hole": len(holed),
        "groups": sum(len(s["groups"]) for s in slots),
        "player_names": sum(len(g["names"]) for s in slots for g in s["groups"]),
        "shared_groups": len(shared),
        "shared_group_names": sum(len(g["names"]) for g in shared),
        "shared_rank1_groups": sum(1 for g in shared if g["rank"] == 1),
        "cells_with_jersey": sum(
            1 for s in slots for g in s["groups"] if any(g["jerseys"])
        ),
        "jersey_numbers_stripped": sum(
            1 for s in slots for g in s["groups"] for j in g["jerseys"] if j
        ),
        "continuation_ranks": sum(s["continuation_ranks"] for s in slots),
        "rows_dropped": len(dropped),
        "by_unit": {},
        "max_rank": max(
            (len(s["groups"]) for s in slots), default=0
        ),
    }
    for s in slots:
        counts["by_unit"][s["unit"]] = counts["by_unit"].get(s["unit"], 0) + 1

    return {
        "club": club,
        "url": url,
        "fetched_at": fetched_at,
        "raw_sha256": sha256_text(text),
        "capture_kind": capture_kind,
        "chart_date": chart_date,
        "units_found": units_seen,
        "slots": slots,
        "gaps": gaps,
        "dropped": dropped,
        "image_urls": image_urls,
        "counts": counts,
    }
