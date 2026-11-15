#!/usr/bin/env python3
"""Strip leading jersey numbers from depth-chart cells; keep the raw string.

Session e1fa878e-nfl1, flag F-7810-06. The Packers club chart prints a jersey number
before each name ("9 Christian Watson"). Joins on player name need the bare name, so:

  s1..s4        -> bare player name (number removed)
  jersey_s1..s4 -> the number as printed ("" when the cell had none)
  raw_s1..s4    -> the cell exactly as published (never edited)

Idempotent: a cell already stripped keeps its name, and raw_* is only written once.
Only the leading token is treated as a number, and only when it is 1-2 digits and is
followed by a space and a name. Nothing else in a cell is altered.

Run: python3 tools/normalize_depth_names.py
Reads and writes data/depth_chart.json. Source of the raw strings: the cited club charts
(see data/depth_chart_meta.json and the S-ids in each row).
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "depth_chart.json")
NUM = re.compile(r"^(\d{1,2}) (\S.*)$")


def split(cell: str):
    m = NUM.match(cell or "")
    return (m.group(1), m.group(2)) if m else ("", cell or "")


def main():
    rows = json.load(open(PATH, encoding="utf-8"))
    changed = 0
    for r in rows:
        for k in ("s1", "s2", "s3", "s4"):
            n = k[1]
            raw = r.get(f"raw_s{n}", r.get(k, ""))
            jersey, name = split(raw)
            r[f"raw_s{n}"] = raw
            r[f"jersey_s{n}"] = jersey
            if r.get(k, "") != name:
                changed += 1
            r[k] = name
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")
    numbered = sum(1 for r in rows for n in "1234" if r[f"jersey_s{n}"])
    print(f"rows: {len(rows)}  cells renamed: {changed}  cells with a jersey number: {numbered}")


if __name__ == "__main__":
    main()
