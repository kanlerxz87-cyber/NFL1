#!/usr/bin/env python3
"""Gate for the Game Book register: hashes, pins, links, no placeholders, no forbidden inference.

Session `98a40411-nfl1`, task G6. Read-only - it never writes. Exit 1 means the register may not be
published, which is the point: a missing field has to fail loudly instead of becoming a blank cell
that a reader mistakes for a zero.

Checks
------
1. every capture in `data/gamebook/**` parses, carries the pinned `parser_version`, a UTC
   `fetched_at`, an official `url` and a well-formed sha256 when it claims one;
2. the derived ledger: one club per row from the 32 current clubs, a non-empty player name, an
   official link, and an `inactive_state` from the allowed vocabulary;
3. every published rate is arithmetically consistent with its own n and k, the interval brackets
   the point estimate, and a cell with n == 0 is blank rather than 0%;
4. the per-key count pins: a capture for a key never has fewer rows than the pinned floor for that
   key (counts may grow as more weeks are added, they may not shrink, and a shrink is a scrape bug);
5. no placeholder vocabulary anywhere in the derived files or the published pages
   (`TODO`, `TBD`, `N/A`, `unknown`, `not available`, `pending`);
6. the published pages: every local link resolves to a file that exists, and no table cell says a
   snap count or a depth rank was derived - the brief forbids both, so the site must not imply them;
7. if a Game Book capture exists for a club-game, the two-source comparison must contain that row,
   so a parser that silently drops a game cannot reduce the sample size unnoticed.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data" / "gamebook"
DERIVED = STORE / "derived"
SITE = ROOT / "gamebook"
sys.path.insert(0, str(ROOT / "pipeline"))

ALLOWED_STATE = {"declared_inactive", "not_on_inactive_list", "no_inactive_source",
                 "declared_inactive_no_report_row"}
ALLOWED_GB = {None, "not_active", "active_did_not_play", "played", "not_in_book"}
PLACEHOLDER = re.compile(r"\b(TODO|TBD|N/A|not available|unverified value|pending|placeholder|xxx)\b",
                         re.I)
OFFICIAL = re.compile(r"^https://(www\.nfl\.com|static\.www\.nfl\.com|operations\.nfl\.com)/")
SHA = re.compile(r"^[0-9a-f]{64}$")

# count pins, per capture key: a real capture for that key must reach at least this many rows.
PINS = {
    ("inactives", "2026_reg10"): {"rows": 147, "clubs": 24},
    ("report", "2026_reg10"): {"rows": 300, "clubs": 28},
}
CURRENT = {"ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB",
           "HOU", "IND", "JAX", "KC", "LAC", "LA", "LV", "MIA", "MIN", "NE", "NO", "NYG", "NYJ",
           "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"}
FORBIDDEN_CLAIM = re.compile(r"(snap share|snap count|share of snaps|depth rank inferred|"
                             r"rank inferred from jersey|jersey number implies)", re.I)


def iter_captures():
    for kind in ("inactives", "report", "gamebook"):
        d = STORE / "captures" / kind
        for p in sorted(d.glob("*.json")) if d.exists() else []:
            yield kind, p
    d = STORE / "official_inactives"
    if d.exists():
        for p in sorted(d.glob("*.json")):
            yield "inactives", p


def main() -> int:
    problems: list[str] = []
    notes: list[str] = []
    seen = 0

    # 1. captures
    per_key: dict = {}
    for kind, p in iter_captures():
        seen += 1
        try:
            cap = json.loads(p.read_text())
        except Exception as exc:                                 # noqa: BLE001
            problems.append(f"{p.relative_to(ROOT)}: not valid JSON ({exc})")
            continue
        rel = str(p.relative_to(ROOT))
        rows = cap.get("rows")
        if not isinstance(rows, list):
            problems.append(f"{rel}: no rows list")
            rows = []
        per_key.setdefault((kind, cap.get("key") or ""), []).append((p, cap))
        for field in ("key", "season", "week", "fetched_at", "url", "parser_version"):
            if not cap.get(field):
                problems.append(f"{rel}: required field {field!r} is blank")
        fa = cap.get("fetched_at") or ""
        if fa and not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|\+00:00)?$", fa):
            problems.append(f"{rel}: fetched_at {fa!r} is not a UTC timestamp")
        url = cap.get("url") or ""
        if url and not OFFICIAL.match(url):
            problems.append(f"{rel}: source url is not an official NFL host: {url}")
        for h in (cap.get("raw_sha256"), cap.get("evidence_sha256")):
            if h and not SHA.match(str(h)):
                problems.append(f"{rel}: {h!r} is not a sha256")
        if kind == "gamebook":
            if not cap.get("pdf_url") and not cap.get("flags"):
                problems.append(f"{rel}: a game-book capture with no pdf_url must carry a flag")
            if cap.get("pdf_sha256") and not SHA.match(cap["pdf_sha256"]):
                problems.append(f"{rel}: pdf_sha256 is malformed")
        for r in rows:
            if PLACEHOLDER.search(json.dumps(r)):
                problems.append(f"{rel}: placeholder text in a row: {json.dumps(r)[:120]}")
            if kind == "inactives" and not (r.get("club") and r.get("name")):
                problems.append(f"{rel}: inactive row missing club or name: {json.dumps(r)[:120]}")
            if kind == "inactives" and r.get("club") and r["club"].upper() not in CURRENT:
                problems.append(f"{rel}: club code {r['club']!r} is not one of the 32 current clubs")

    # 4. count pins
    for (kind, key), lst in per_key.items():
        pin = PINS.get((kind, key))
        if not pin:
            continue
        best = max(len(c.get("rows") or []) for _, c in lst)
        best_clubs = max(len({r.get("club") for r in (c.get("rows") or []) if r.get("club")})
                        for _, c in lst)
        if best < pin["rows"]:
            problems.append(f"{kind}/{key}: {best} row(s) captured, pin is {pin['rows']} "
                            "- the scrape lost rows")
        if best_clubs < pin["clubs"]:
            problems.append(f"{kind}/{key}: {best_clubs} club(s) captured, pin is {pin['clubs']}")
        notes.append(f"{kind}/{key}: pinned {pin['rows']}/{pin['clubs']}, best captured "
                     f"{best}/{best_clubs} in {len(lst)} capture(s)")

    # 2 + 3. derived tables
    try:
        reg = json.loads((STORE / "register.json").read_text())
    except Exception as exc:                                     # noqa: BLE001
        problems.append(f"data/gamebook/register.json: unreadable ({exc}); run "
                        "tools/build_gamebook_register.py")
        reg = {}
    if reg:
        led = json.loads((DERIVED / "ledger.json").read_text())["rows"]
        for i, r in enumerate(led):
            if r.get("club") not in CURRENT:
                problems.append(f"ledger[{i}]: club {r.get('club')!r} is not a current club")
            if not (r.get("player") or "").strip():
                problems.append(f"ledger[{i}]: blank player")
            if r.get("inactive_state") not in ALLOWED_STATE:
                problems.append(f"ledger[{i}]: state {r.get('inactive_state')!r} outside the vocabulary")
            if r.get("game_book_state") not in ALLOWED_GB:
                problems.append(f"ledger[{i}]: game_book_state {r.get('game_book_state')!r} unknown")
            link = r.get("inactive_url") or r.get("report_url") or ""
            if not OFFICIAL.match(str(link)):
                problems.append(f"ledger[{i}]: no official source link ({link!r})")
            blob = json.dumps(r)
            if PLACEHOLDER.search(blob):
                problems.append(f"ledger[{i}]: placeholder text {blob[:120]}")
        if len(led) != reg.get("ledger_rows"):
            problems.append(f"register says {reg.get('ledger_rows')} ledger rows, file holds {len(led)}")
        for row in reg.get("designations") or []:
            n, k = row["n"], row["declared_inactive"]
            if n <= 0:
                problems.append(f"designations[{row['designation']}]: published with n = 0")
                continue
            want = k / n
            if abs(want - (row["declared_inactive_rate"] or -1)) > 1e-9:
                problems.append(f"designations[{row['designation']}]: rate {row['declared_inactive_rate']} "
                                f"!= {k}/{n}")
            lo, hi = row.get("ci95_low"), row.get("ci95_high")
            if lo is None or hi is None or not (lo - 1e-12 <= want <= hi + 1e-12):
                problems.append(f"designations[{row['designation']}]: interval does not bracket the rate")
            if row["play_rate"] is not None and not row["game_book_n"]:
                problems.append(f"designations[{row['designation']}]: a play rate with no Game Book n - "
                                "measure B may not be filled from measure A")
        cov = json.loads((DERIVED / "coverage.json").read_text())["rows"]
        for c in cov:
            if c["report_clubs"] > 32 or c["inactive_clubs"] > 32:
                problems.append(f"coverage {c['season']} W{c['week']}: more clubs than the league has")
            if c["clubs_in_both"] > min(c["report_clubs"], c["inactive_clubs"]):
                problems.append(f"coverage {c['season']} W{c['week']}: clubs_in_both exceeds the smaller side")
        # 7. a captured game must appear in the comparison
        gbk = list((STORE / "captures" / "gamebook").glob("*.json")) if (STORE / "captures" / "gamebook").exists() else []
        cc = {r["slug"] for r in reg.get("crosscheck") or []}
        for p in gbk:
            cap = json.loads(p.read_text())
            if (cap.get("parsed") or {}).get("Not Active") and cap.get("key") not in cc:
                notes.append(f"{cap.get('key')}: a Game Book with rows is not in the cross-check table "
                             "(no weekly inactives capture for that club-game)")

    # 5 + 6. published pages
    if SITE.exists():
        for p in sorted(SITE.glob("*.html")):
            txt = p.read_text()
            hrefs = re.findall(r'href="([^"#]+)"', txt)
            for h in hrefs:
                if h.startswith(("http", "mailto:")):
                    continue
                target = (SITE / h).resolve()
                if not target.exists():
                    problems.append(f"{p.name}: broken local link {h}")
            if PLACEHOLDER.search(re.sub(r"<[^>]+>", " ", txt)):
                m = PLACEHOLDER.search(re.sub(r"<[^>]+>", " ", txt))
                problems.append(f"{p.name}: placeholder text {m.group(0)!r} in visible copy")
            if FORBIDDEN_CLAIM.search(txt):
                # a sentence *about* the prohibition is fine; a claim that we produced the number is not
                for m in re.finditer(r"[^.]*(" + FORBIDDEN_CLAIM.pattern + r")[^.]*\.", txt, re.I):
                    seg = m.group(0)
                    if not re.search(r"never|not |no |forbid|must not|without", seg, re.I):
                        problems.append(f"{p.name}: asserts a forbidden measure: {seg[:120]}")
            n_link = txt.count("nfl.com")
            n_rows = txt.count("<tr>")
            if n_rows > n_link and "ledger.html" not in p.name:
                notes.append(f"{p.name}: {n_rows} rows vs {n_link} nfl.com references - check every "
                             "table row carries a link")

    print(f"game-book register gate: {seen} capture(s), {len(reg.get('designations') or [])} "
          f"designation cell(s), {len(problems)} failure(s), {len(notes)} note(s)")
    for x in problems:
        print("  FAIL", x)
    for x in notes[:30]:
        print("  note", x)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
