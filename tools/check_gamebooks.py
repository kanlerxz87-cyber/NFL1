#!/usr/bin/env python3
"""check_gamebooks.py — fail when the Game Book capture, parse or site drifts from its sources.

Session d9e28eb2-nfl1 (G7).  Run from the repository root:

    python3 tools/check_gamebooks.py

What it checks
--------------
  1. Integrity  — every raw capture matches its sha256 in data/gamebooks/manifest.json,
                  and no raw file is missing from the manifest.
  2. Registry   — data/gamebooks/source.json covers 13 games, every entry carries an
                  official nfl.com game-centre URL, an official static.www.nfl.com Game Book
                  URL and a hash that equals the manifest hash for that file.
  3. Parse      — tools/build_gamebooks.build() re-parses the raw files (it refuses to run
                  when a raw hash no longer matches the manifest), then the regenerated
                  parse is validated: every lineup is 11x4 or flagged, every blank status
                  field carries a flag, and every parsed hash equals the manifest hash.
  4. Match      — data/gamebooks/injury_match.json totals agree with its own rows, and every
                  matched row names an official player URL or an explicit blank status.
  5. Site       — gamebooks/ carries all five published pages; every Game Book URL and every
                  raw capture appears as a link in the site; every page links its siblings.

Exit 0 when everything holds, 1 otherwise.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GB = os.path.join(ROOT, "data", "gamebooks")

PAGES = ["index.html", "starters.html", "inactives.html", "match.html", "methods.html"]


def load(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main() -> int:
    problems: list[str] = []

    manifest = load(os.path.join(GB, "manifest.json"))
    source = load(os.path.join(GB, "source.json"))

    # 1. integrity
    listed = {f["path"]: f for f in manifest["files"]}
    raw_dir = os.path.join(GB, "raw")
    on_disk = sorted(
        os.path.join("data", "gamebooks", "raw", n)
        for n in os.listdir(raw_dir) if n.endswith(".txt")
    )
    for rel in on_disk:
        if rel not in listed:
            problems.append(f"raw file not in manifest: {rel}")
    for rel, meta in listed.items():
        p = os.path.join(ROOT, rel)
        if not os.path.isfile(p):
            problems.append(f"manifest file missing: {rel}")
            continue
        actual = sha256(p)
        if actual != meta["sha256"]:
            problems.append(f"sha256 mismatch: {rel}\n    manifest {meta['sha256']}\n    actual   {actual}")
        size = os.path.getsize(p)
        if size != meta["bytes"]:
            problems.append(f"byte count mismatch: {rel} ({size} != {meta['bytes']})")

    # 2. registry
    if len(source["games"]) != 13:
        problems.append(f"source.json has {len(source['games'])} games, expected 13")
    for g in source["games"]:
        if not re.match(r"^https://www\.nfl\.com/games/[a-z0-9\-]+-2026-reg-10$", g["game_centre_url"]):
            problems.append(f"{g['game']}: non-official game-centre URL {g['game_centre_url']}")
        if not re.match(r"^https://static\.www\.nfl\.com/image/upload/v\d+/gamecenter/[0-9a-f\-]+\.pdf$",
                        g["game_book_url"]):
            problems.append(f"{g['game']}: non-official Game Book URL {g['game_book_url']}")
        m = listed.get(g["raw_file"])
        if not m:
            problems.append(f"{g['game']}: raw file not in manifest")
        elif m["sha256"] != g["raw_sha256"]:
            problems.append(f"{g['game']}: source hash != manifest hash")
        if not g.get("extraction_note"):
            problems.append(f"{g['game']}: capture carries no extraction_note")

    # 3. parse (regenerate and compare)
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import build_gamebooks  # noqa: E402
    stats = build_gamebooks.build()
    parsed = load(os.path.join(GB, "parsed.json"))
    if len(parsed["games"]) != 13:
        problems.append(f"parsed.json has {len(parsed['games'])} games, expected 13")
    for g in parsed["games"]:
        codes = {f["code"] for f in g["flags"]}
        lu = g["lineups"]
        if lu is None:
            if "LINEUPS_INCOMPLETE" not in codes:
                problems.append(f"{g['game']}: lineups missing without LINEUPS_INCOMPLETE flag")
        else:
            for side in ("away", "home"):
                for unit in ("offense", "defense"):
                    players = lu[side][unit]
                    if len(players) != 11:
                        problems.append(f"{g['game']}: {side} {unit} has {len(players)} starters")
                    for p in players:
                        if not p["name"] and "LINEUP_NAME_BLANK" not in codes:
                            problems.append(f"{g['game']}: blank starter name without flag")
        for section in ("did_not_play", "not_active"):
            for side in ("away", "home"):
                v = g[section][side]
                if v is None and not ({"STATUS_LABELS_ABSENT", "STATUS_PROSE_FORMAT"} & codes):
                    problems.append(f"{g['game']}: {section}.{side} null without a status flag")
                if isinstance(v, list):
                    for e in v:
                        if not e.strip():
                            problems.append(f"{g['game']}: empty entry in {section}.{side}")
        if g["sources"]["raw_sha256"] != next(
                (x["raw_sha256"] for x in source["games"] if x["game"] == g["game"]), None):
            problems.append(f"{g['game']}: parsed hash != source hash")

    # 4. match
    match = load(os.path.join(GB, "injury_match.json"))
    t = match["totals"]
    rows = match["matches"]
    if t["not_active_entries"] != len(rows):
        problems.append(f"match totals not_active_entries {t['not_active_entries']} != rows {len(rows)}")
    counts = {"matched": 0, "not_in_report": 0, "ambiguous": 0, "unparseable": 0}
    for r in rows:
        counts[r["match"]] = counts.get(r["match"], 0) + 1
        if r["match"] == "matched":
            if not r.get("player_url"):
                problems.append(f"matched row without player_url: {r['entry']}")
            if r.get("game_status") is None and "game_status" not in r:
                problems.append(f"matched row missing game_status key: {r['entry']}")
    for k in ("matched", "not_in_report", "ambiguous"):
        if t.get(k) != counts.get(k, 0):
            problems.append(f"match totals {k}: {t.get(k)} != {counts.get(k, 0)}")
    if t["not_active_entries"] < 100:
        problems.append(f"only {t['not_active_entries']} Not Active entries parsed — capture incomplete")

    # 5. site
    site = os.path.join(ROOT, "gamebooks")
    for p in PAGES:
        if not os.path.isfile(os.path.join(site, p)):
            problems.append(f"site page missing: gamebooks/{p}")
    html_all = ""
    for p in PAGES:
        fp = os.path.join(site, p)
        if os.path.isfile(fp):
            html_all += open(fp, encoding="utf-8").read()
    for g in source["games"]:
        if g["game_book_url"] not in html_all:
            problems.append(f"{g['game']}: Game Book URL not linked from the site")
        if g["raw_file"] not in html_all and ("../" + g["raw_file"]) not in html_all:
            problems.append(f"{g['game']}: raw capture not linked from the site")
        if g["game_centre_url"] not in html_all:
            problems.append(f"{g['game']}: game-centre URL not linked from the site")
    # sibling links: every page links every other page
    for p in PAGES:
        fp = os.path.join(site, p)
        if not os.path.isfile(fp):
            continue
        text = open(fp, encoding="utf-8").read()
        for q in PAGES:
            if q != p and f'href="{q}"' not in text:
                problems.append(f"gamebooks/{p} does not link {q}")

    if problems:
        print(f"FAIL: {len(problems)} problem(s):")
        for p in problems:
            print(" -", p)
        return 1
    print("OK: gamebooks capture, parse, match and site all check out "
          f"({stats['games']} games, {stats['flags']} flags, "
          f"{stats['match']['matched']}/{stats['match']['not_active_entries']} status entries "
          "matched to the official injury read)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
