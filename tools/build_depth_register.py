#!/usr/bin/env python3
"""Build the official depth register from verbatim club depth-chart captures.

Input : data/depth/official_raw/<CLUB>_<date>.md   (one file per club capture)
Output: data/depth/official_register.json           (one row per printed name, plus summary)
        data/depth/official_register.tsv            (same rows, flat, for spreadsheets)
        data/depth/comparison.json                  (repo rows vs the official captures)

Rules (fixed, not inferred):
* A printed cell is kept verbatim in `raw_cell`. A jersey prefix ("9 Christian Watson") is
  stripped into `jersey` and `name`; the raw string is never discarded.
* A cell holding several bracketed names ("[Cooper Kupp] [Rashid Shaheed]") is ONE printed
  slot with two players: `shared_slot` is true and `names` lists both.
* A cell that is empty while a later cell in the same printed row is filled is recorded as
  an empty gap (`empty_gap`), so a skipped slot is visible rather than silently shifted.
* The printed column number is the printed order, nothing more. No slot is designated the
  "starter": a position group can list several first-column players (`rank1_count`).
* Every row carries its club's page URL, page label and fetch date.

Run:  python3 tools/build_depth_register.py            (writes the outputs)
      python3 tools/build_depth_register.py --check    (fails if committed outputs differ)
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "depth" / "official_raw"
OUT_JSON = ROOT / "data" / "depth" / "official_register.json"
OUT_TSV = ROOT / "data" / "depth" / "official_register.tsv"
OUT_CMP = ROOT / "data" / "depth" / "comparison.json"

REQUIRED_META = ("club", "club_name", "url", "page_title", "page_label", "fetched", "capture_method")
EXPECTED_SECTIONS = ["Offense", "Defense", "Special Teams"]
JERSEY_RE = re.compile(r"^(\d{1,2})\s+(.+)$")
BRACKET_RE = re.compile(r"\[([^\]]+)\]")


def parse_raw(path: Path) -> dict:
    """Parse one verbatim capture. Raises ValueError on any structural drift."""
    text = path.read_text(encoding="utf-8").splitlines()
    if not text or not text[0].startswith("# "):
        raise ValueError(f"{path.name}: missing title line")
    meta: dict[str, str] = {}
    i = 1
    while i < len(text) and text[i].strip() != "---":
        if ": " not in text[i]:
            raise ValueError(f"{path.name}: metadata line without key: {text[i]!r}")
        k, v = text[i].split(": ", 1)
        meta[k.strip()] = v.strip()
        i += 1
    if i >= len(text):
        raise ValueError(f"{path.name}: metadata block not closed by '---'")
    missing = [k for k in REQUIRED_META if not meta.get(k)]
    if missing:
        raise ValueError(f"{path.name}: missing metadata {missing}")
    if not meta["url"].startswith("https://"):
        raise ValueError(f"{path.name}: url is not https")

    sections: list[tuple[str, list[str]]] = []
    for line in text[i + 1:]:
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif line.startswith("|") and sections:
            sections[-1][1].append(line)
    names = [s for s, _ in sections]
    if names != EXPECTED_SECTIONS:
        raise ValueError(f"{path.name}: sections {names} != {EXPECTED_SECTIONS}")
    return {"meta": meta, "sections": sections, "file": path.name}


def split_cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [c.strip() for c in body.split("|")]


def cell_names(cell: str) -> tuple[list[str], list[str]]:
    """Return (names, jerseys) for one printed cell. Empty cell -> ([], [])."""
    if not cell:
        return [], []
    if "[" in cell:
        raw_names = BRACKET_RE.findall(cell)
    else:
        raw_names = [cell]
    names, jerseys = [], []
    for rn in raw_names:
        m = JERSEY_RE.match(rn)
        if m:
            jerseys.append(m.group(1))
            names.append(m.group(2).strip())
        else:
            jerseys.append("")
            names.append(rn.strip())
    return names, jerseys


def build_rows(parsed: dict) -> list[dict]:
    meta = parsed["meta"]
    club = meta["club"]
    rows: list[dict] = []
    for unit, lines in parsed["sections"]:
        label = ""
        group_ordinal = 0
        printed_row = 0
        for line in lines:
            if re.fullmatch(r"\|[\s\-|]*\|", line):  # markdown separator
                continue
            cells = split_cells(line)
            if cells and cells[0].strip().lower() == "position":  # header row
                continue
            pos_cell = cells[0]
            players = cells[1:]
            continuation = pos_cell == ""
            if not continuation:
                label = pos_cell
                group_ordinal += 1
            printed_row += 1
            last_filled = max((j for j, c in enumerate(players) if c), default=-1)
            for j, raw in enumerate(players):
                col = j + 1
                if not raw:
                    if j < last_filled:
                        rows.append(_row(meta, parsed, unit, label, group_ordinal, printed_row,
                                         continuation, col, "", [], [], empty_gap=True))
                    continue
                names, jerseys = cell_names(raw)
                rows.append(_row(meta, parsed, unit, label, group_ordinal, printed_row,
                                 continuation, col, raw, names, jerseys, empty_gap=False))
    return rows


def _row(meta, parsed, unit, label, group_ordinal, printed_row, continuation, col, raw,
         names, jerseys, empty_gap):
    club = meta["club"]
    return {
        "club": club,
        "club_name": meta["club_name"],
        "unit": unit,
        "position": label,
        "group_id": f"{club}|{unit}|{label}",
        "group_ordinal": group_ordinal,
        "printed_row": printed_row,
        "continuation_row": continuation,
        "column": col,
        "raw_cell": raw,
        "names": names,
        "name": names[0] if len(names) == 1 else "",
        "jersey": jerseys[0] if len(names) == 1 else "",
        "jersey_stripped": bool(len(names) == 1 and jerseys and jerseys[0]),
        "shared_slot": len(names) > 1,
        "empty_gap": empty_gap,
        "source_url": meta["url"],
        "page_title": meta["page_title"],
        "page_label": meta["page_label"],
        "fetched": meta["fetched"],
    }


def summarise(rows: list[dict], metas: dict[str, dict]) -> dict:
    per_club: dict[str, dict] = {}
    for club, meta in metas.items():
        crow = [r for r in rows if r["club"] == club]
        groups: dict[str, list[dict]] = defaultdict(list)
        for r in crow:
            groups[r["group_id"]].append(r)
        rank1 = {}
        for gid, grows in groups.items():
            names1 = sorted({n for r in grows if r["column"] == 1 for n in r["names"]})
            rank1[gid] = names1
        multi = {g: n for g, n in rank1.items() if len(n) > 1}
        # the same player printed in more than one slot of the club
        seen: dict[str, list[str]] = defaultdict(list)
        for r in crow:
            for n in r["names"]:
                seen[n].append(f"{r['unit']}/{r['position']}/col{r['column']}")
        dups = {n: v for n, v in seen.items() if len(v) > 1}
        per_club[club] = {
            "club_name": meta["club_name"],
            "page_label": meta["page_label"],
            "source_url": meta["url"],
            "fetched": meta["fetched"],
            "printed_names": sum(len(r["names"]) for r in crow),
            "slot_groups": len(groups),
            "groups_with_more_than_one_rank1": len(multi),
            "groups_with_more_than_one_rank1_detail": multi,
            "cells_with_jersey_prefix_stripped": sum(1 for r in crow if r["jersey_stripped"]),
            "shared_slots": sum(1 for r in crow if r["shared_slot"]),
            "empty_gaps": sum(1 for r in crow if r["empty_gap"]),
            "continuation_rows": sum(1 for r in crow if r["continuation_row"] and not r["empty_gap"]),
            "players_in_more_than_one_slot": dups,
        }
    return {
        "clubs": per_club,
        "totals": {
            "clubs": len(per_club),
            "printed_names": len([n for r in rows for n in r["names"]]),
            "slot_groups": sum(v["slot_groups"] for v in per_club.values()),
            "groups_with_more_than_one_rank1": sum(v["groups_with_more_than_one_rank1"] for v in per_club.values()),
            "cells_with_jersey_prefix_stripped": sum(v["cells_with_jersey_prefix_stripped"] for v in per_club.values()),
            "shared_slots": sum(v["shared_slots"] for v in per_club.values()),
            "empty_gaps": sum(v["empty_gaps"] for v in per_club.values()),
        },
    }


def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def compare_repo(rows: list[dict]) -> dict:
    """Compare the repo's older tables with the official captures, name by name."""
    off: dict[tuple, str] = {}
    off_any: dict[tuple, list] = defaultdict(list)
    for r in rows:
        for n in r["names"]:
            off[(r["club"], norm(n), r["column"], r["position"])] = r["source_url"]
            off_any[(r["club"], norm(n))].append((r["position"], r["column"]))

    out = {}
    repo_path = ROOT / "data" / "depth_chart.json"
    repo = json.loads(repo_path.read_text(encoding="utf-8"))
    repo_items = []
    for rr in repo:
        for i in range(1, 5):
            nm = (rr.get(f"s{i}") or "").strip()
            if nm:
                repo_items.append((rr["code"], rr["unit"], rr["pos"], i, nm))
    clubs_in_official = {r["club"] for r in rows}
    mism = []
    for club, unit, pos, col, nm in repo_items:
        if club not in clubs_in_official:
            continue
        bare = JERSEY_RE.match(nm)
        bare_name = bare.group(2) if bare else nm
        key = (club, norm(bare_name), col, pos)
        if key in off:
            continue
        where = off_any.get((club, norm(bare_name)))
        if where:
            why = f"official page prints this player at {where}"
        else:
            why = "player not printed on the official page"
        mism.append({
            "club": club, "unit": unit, "position": pos, "column": col,
            "repo_value": nm, "difference": why,
            "repo_source": "data/depth_chart.json",
        })
    repo_keys = {(c, norm(JERSEY_RE.match(n).group(2) if JERSEY_RE.match(n) else n))
                 for c, _u, _p, _i, n in repo_items}
    repo_clubs = {c for c, *_ in repo_items}
    omitted = []
    for r in rows:
        if r["club"] not in repo_clubs:
            continue
        for n in r["names"]:
            if (r["club"], norm(n)) not in repo_keys:
                omitted.append({"club": r["club"], "unit": r["unit"], "position": r["position"],
                                "column": r["column"], "official_value": n,
                                "difference": "official page prints this player; repo file does not contain him",
                                "official_source": r["source_url"]})
    out["data/depth_chart.json"] = {
        "compared_cells": len(repo_items),
        "compared_clubs": sorted(clubs_in_official),
        "differences": mism,
        "official_players_missing_from_repo": omitted,
    }

    ev_path = ROOT / "data" / "evidence" / "depth_charts.json"
    ev = json.loads(ev_path.read_text(encoding="utf-8"))["rows"]
    ev_mism = []
    for e in ev:
        club = e["club"]
        if club not in clubs_in_official:
            continue
        key = (club, norm(e["player"]), e["depth_rank"], e["position"])
        if key in off:
            continue
        where = off_any.get((club, norm(e["player"])))
        ev_mism.append({
            "club": club, "unit": e["unit"], "position": e["position"],
            "depth_rank": e["depth_rank"], "player": e["player"],
            "difference": (f"official page prints this player at {where}" if where
                           else "player not printed on the official page"),
            "repo_source": "data/evidence/depth_charts.json",
        })
    out["data/evidence/depth_charts.json"] = {
        "compared_rows": len([e for e in ev if e["club"] in clubs_in_official]),
        "compared_clubs": sorted({e["club"] for e in ev} & clubs_in_official),
        "differences": ev_mism,
    }
    return out


def build() -> tuple[str, str, str]:
    raws = sorted(RAW_DIR.glob("*.md"))
    if not raws:
        raise SystemExit("no raw captures found in data/depth/official_raw/")
    parsed = [parse_raw(p) for p in raws]
    metas = {p["meta"]["club"]: p["meta"] for p in parsed}
    rows: list[dict] = []
    for p in parsed:
        rows.extend(build_rows(p))
    summary = summarise(rows, metas)
    cmp_out = compare_repo(rows)
    doc = {
        "_readme": ("Official depth register. Each row is one printed name in one printed slot, "
                    "from a verbatim capture of a club's own depth-chart page. Columns are printed "
                    "order only; no slot is designated a starter. Generated by "
                    "tools/build_depth_register.py; do not edit by hand."),
        "method": {
            "captures": [p["file"] for p in parsed],
            "jersey_rule": "a leading 1-2 digit number followed by a space is stripped into `jersey`; raw_cell keeps the printed text",
            "shared_rule": "two or more bracketed names in one cell = one printed slot, shared_slot=true",
            "empty_rule": "an empty cell that is followed by a filled cell in the same printed row = empty_gap=true",
        },
        "summary": summary,
        "rows": rows,
    }
    js = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    cols = ["club", "unit", "position", "group_ordinal", "printed_row", "continuation_row", "column",
            "raw_cell", "name", "jersey", "shared_slot", "empty_gap", "source_url", "page_label", "fetched"]
    tsv_lines = ["\t".join(cols)]
    for r in rows:
        tsv_lines.append("\t".join(
            ("" if r[c] is None else str(r[c])).replace("\t", " ")
            if not isinstance(r[c], bool) else ("yes" if r[c] else "no")
            for c in cols))
    tsv = "\n".join(tsv_lines) + "\n"
    cmp_js = json.dumps(cmp_out, indent=2, ensure_ascii=False) + "\n"
    return js, tsv, cmp_js


def main(argv: list[str]) -> int:
    js, tsv, cmp_js = build()
    if "--check" in argv:
        ok = True
        for path, text in ((OUT_JSON, js), (OUT_TSV, tsv), (OUT_CMP, cmp_js)):
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                print(f"STALE: {path.relative_to(ROOT)} differs from the captures")
                ok = False
        print("PASS: committed depth register matches the captures" if ok else "FAIL")
        return 0 if ok else 1
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(js, encoding="utf-8")
    OUT_TSV.write_text(tsv, encoding="utf-8")
    OUT_CMP.write_text(cmp_js, encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}, {OUT_TSV.relative_to(ROOT)}, {OUT_CMP.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
