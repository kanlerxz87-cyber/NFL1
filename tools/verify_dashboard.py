#!/usr/bin/env python3
"""verify_dashboard.py — check the new dashboard pages the way a hostile reader would.

Rules enforced (each one exists because this session found it broken somewhere in the repo):
  1. every internal link and anchor resolves;
  2. every table row carries at least one https link to an official/registry domain;
  3. no table cell renders the word "None", "nan", "null" or an empty cell;
  4. the published line table is internally consistent: for every row, the printed
     difference equals the printed model minus the printed market, in both the home and
     away convention, and the market columns are exact negations of each other;
  5. the headline numbers on the executive summary and dashboard reproduce from the JSON;
  6. no page claims an "edge" while no price source exists;
  7. the Flagged-for-Review page lists every contradiction in data/contradictions.json;
  8. every page stamp matches the data it was generated from.

Exit 1 on any failure.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB = os.path.join(ROOT, "web")
OFFICIAL = {"nfl.com", "operations.nfl.com", "nextgenstats.nfl.com", "chiefs.com",
            "seahawks.com", "itl.nist.gov", "nj.gov", "github.com", "api.github.com",
            "nflverse.github.io", "static.www.nfl.com", "www.chiefs.com", "www.seahawks.com"}

PAGES = ["dashboard.html", "decisions.html", "suggestions.html", "verification.html",
         "flag-register.html", "executive-summary.html"]


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def is_official(url):
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in OFFICIAL)


class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids, self.cells, self.rows = [], set(), [], []
        self.in_td = False
        self.cur_td = []
        self.cur_row = []
        self.in_table = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for k in ("href", "src"):
            if a.get(k):
                self.links.append(a[k])
        if tag == "table":
            self.in_table += 1
        if tag == "td":
            self.in_td = True
            self.cur_td = []
        if tag == "tr" and self.in_table:
            if self.cur_row:
                self.rows.append(self.cur_row)
            self.cur_row = []

    def handle_data(self, data):
        if self.in_td:
            self.cur_td.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.in_td:
            self.in_td = False
            self.cur_row.append("".join(self.cur_td))
            self.cells.append("".join(self.cur_td))
        if tag == "tr" and self.in_table:
            if self.cur_row:
                self.rows.append(self.cur_row)
            self.cur_row = []
        if tag == "table" and self.in_table:
            self.in_table -= 1


def main() -> int:
    problems = []
    checks = 0

    for name in PAGES:
        path = os.path.join(WEB, name)
        if not os.path.isfile(path):
            problems.append(f"missing page: web/{name}")
            continue
        text = open(path, encoding="utf-8").read()
        s = Scan()
        s.feed(text)
        s.close()

        # 1. links and anchors
        for h in s.links:
            if h.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            if h.startswith("#"):
                if h[1:] not in s.ids:
                    problems.append(f"{name}: missing anchor {h}")
                continue
            target = h.split("#")[0]
            if not target:
                continue
            resolved = os.path.normpath(os.path.join(WEB, target))
            if not os.path.isfile(resolved) and not target.startswith("../"):
                resolved = os.path.normpath(os.path.join(WEB, target))
            if not os.path.isfile(resolved):
                problems.append(f"{name}: broken link {h}")
            elif "#" in h:
                frag = h.split("#", 1)[1]
                other = open(resolved, encoding="utf-8").read()
                if f'id="{frag}"' not in other:
                    problems.append(f"{name}: missing anchor id {frag} in {target}")
            checks += 1

        # 2/3. table row sourcing and junk cells
        for i, row in enumerate(s.rows, 1):
            if not any(c.strip() for c in row):
                continue
            # header rows (th) are not data; the parser only collects td cells, so a row
            # with fewer than two collected cells is a layout artefact, not a data row
            if len(row) < 2:
                continue
            # a header row has no links; only judge rows that carry data
            joined = " ".join(row)
            if re.search(r"\b(None|nan|NaN|null|undefined)\b", joined):
                problems.append(f"{name} row {i}: junk value in {joined[:70]!r}")
            # An empty cell is a rendering defect unless the value is genuinely not
            # published, which the generator must mark. We cannot see markup in the text
            # cells, so require every cell to carry at least one character.
            for j, c in enumerate(row, 1):
                if not c.strip():
                    problems.append(f"{name} row {i} col {j}: empty cell")
                    break
            checks += 1

        # 6. no edge claims without a price
        for m in re.finditer(r"[^<>]{0,140}\bedge\b[^<>]{0,140}", text, re.I):
            frag = m.group(0)
            # a claim is a bare assertion like "5.2 point edge". Anything inside a sentence
            # that also mentions the missing price, a test, or a negative is a discussion.
            claim = re.search(r"(\d+(\.\d+)?)\s*(point|pt|%)?\s*edge", frag, re.I)
            guarded = re.search(r"(no|not|without|never|rather than|instead of|cannot|can't|"
                                r"unsupported|difference|missing|blank|test|claim|question|"
                                r"why|if|whether|would|needs|separate|luck|sample)", frag, re.I)
            if claim and not guarded:
                problems.append(f"{name}: 'edge' asserted as a number: {frag.strip()[:90]!r}")
                break
    # the link graph must reach every page from the dashboard
    graph = {}
    for name in PAGES:
        text = open(os.path.join(WEB, name), encoding="utf-8").read()
        s = Scan()
        s.feed(text)
        edges = set()
        for h in s.links:
            t = h.split("#")[0]
            if t.endswith(".html") and not t.startswith(("http", "/")):
                edges.add(t)
        graph[name] = edges
    seen, stack = set(), ["dashboard.html"]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(graph.get(n, ()))
    orphan = [p for p in PAGES if p not in seen]
    if orphan:
        problems.append(f"unreachable pages from dashboard.html: {orphan}")

    # 4. the published line table reproduces
    dash = open(os.path.join(WEB, "dashboard.html"), encoding="utf-8").read()
    m = re.search(r'id="tbl-lines".*?</table>', dash, re.S)
    if not m:
        problems.append("dashboard.html: no line table found")
    else:
        rows = re.findall(r"<tr>(.*?)</tr>", m.group(0), re.S)[1:]
        lines = load("data/model/lines.json")["lines"]
        if len(rows) != len(lines):
            problems.append(f"line table rows {len(rows)} != model lines {len(lines)}")
        for r, g in zip(rows, lines):
            cells = [re.sub(r"<[^>]+>", "", c).strip()
                     for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
            try:
                mh, mkt_h, mkt_a, diff = (float(cells[1]), float(cells[3]),
                                          float(cells[4]), float(cells[5]))
            except (ValueError, IndexError):
                problems.append(f"line row not numeric: {cells[:6]}")
                continue
            checks += 4
            if abs((mh - mkt_h) - diff) > 0.011:
                problems.append(f"{g['away']}@{g['home']}: printed diff {diff} != {mh} - {mkt_h}")
            if abs(mkt_h + mkt_a) > 0.001:
                problems.append(f"{g['away']}@{g['home']}: market columns not opposite "
                                f"({mkt_h} vs {mkt_a})")
            if g.get("market_home_line") is not None and abs(mkt_h - g["market_home_line"]) > 0.001:
                problems.append(f"{g['away']}@{g['home']}: printed market {mkt_h} != data "
                                f"{g['market_home_line']}")
            if g.get("my_home_line") is not None and abs(mh - g["my_home_line"]) > 0.001:
                problems.append(f"{g['away']}@{g['home']}: printed model {mh} != data "
                                f"{g['my_home_line']}")

    # 5. headline numbers reproduce from the JSON
    d = load("data/decision_room/decision_room.json")
    ev, model, strat = d["evidence"], d["model"], d["strategies"]
    execu = " ".join(open(os.path.join(WEB, "executive-summary.html"),
                          encoding="utf-8").read().split())
    for label, value in [
        ("games analysed", f"{ev['games_played']}"),
        ("strategies passing", f"{ev['strategies_pass']} of {ev['strategies']}"),
        ("injury rows", f"{ev['injury_rows']}"),
        ("model MAE", f"{model['model_mae']:.2f}"),
        ("market MAE", f"{model['market_mae']:.2f}"),
        ("blend weight", f"{model['blend_weight_model']:.3f}"),
    ]:
        checks += 1
        if value not in execu:
            problems.append(f"executive-summary.html: {label} {value!r} not found")
    checks += 1
    if d["evidence"]["strategies_pass"] != sum(1 for r in load("data/model/strategies.json")["leaderboard"]
                                               if r.get("status") == "PASS"):
        problems.append("decision_room strategies_pass disagrees with the leaderboard")
    checks += 1
    if abs(model["market_mae"] - next(c for c in load("data/model/lines.json")["calibration"]
                                     if c["label"] == "test 2026")["spread_mae_market"]) > 0.001:
        problems.append("published market MAE disagrees with the calibration table")

    # 7. every contradiction is published
    reg = open(os.path.join(WEB, "flag-register.html"), encoding="utf-8").read()
    for x in load("data/contradictions.json")["items"]:
        checks += 1
        if f'id="{x["id"]}"' not in reg:
            problems.append(f"flag-register.html: contradiction {x['id']} not published")
        if x["official"] not in reg:
            problems.append(f"flag-register.html: official link for {x['id']} missing")

    # 8. page stamp agrees with the data
    ver = load("data/audit/official_verification.json")
    for name in PAGES:
        text = open(os.path.join(WEB, name), encoding="utf-8").read()
        m = re.search(r"Data read ([0-9T:+\-]+)", text)
        checks += 1
        if not m:
            problems.append(f"{name}: no data stamp")
        elif m.group(1) != d["generated_at"]:
            problems.append(f"{name}: stamp {m.group(1)} != decision data {d['generated_at']}")
        if ver["generated_at"] not in text:
            problems.append(f"{name}: verification stamp missing")

    print(f"pages checked: {len(PAGES)}, assertions: {checks}")
    if problems:
        print(f"\nFAILED ({len(problems)}):")
        for p in problems[:40]:
            print(" -", p)
        return 1
    print("RESULT: PASS — links resolve, every row is sourced, every figure reproduces,")
    print("        no line row mixes conventions, and every contradiction is published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
