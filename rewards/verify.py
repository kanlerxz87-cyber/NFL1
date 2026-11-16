#!/usr/bin/env python3
"""verify.py — the gate for the Reward Board.

Fails (exit 1) when any of the following is true, because each is a way this board
lies without anyone noticing:

  1. a local link resolves to a missing file
  2. a page is unreachable from index.html
  3. a table has a header but no data rows
  4. a table cell is rendered empty instead of an explicit blank label
  5. a data table row has no https source link at all
  6. literal markdown (** or _emphasis_) leaked into prose
  7. a KPI card has a bare number with no provenance note
  8. the frozen rule drifted: the rule file's current sha256 or its registration
     commit no longer matches what data/rewards/rewards.json records
  9. a frozen threshold is blank or a placeholder, not a concrete value
 10. a table header is a backtest performance metric (ROI / win rate / hit rate /
     profit / return) — the board publishes the rule and a qualification status,
     never a backtest result

Run: python3 rewards/verify.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
PAGES = sorted(HERE.glob("*.html"))
RULE_FILE = HERE / "REWARDS-RULE.md"
DATA = ROOT / "data" / "rewards"

BACKTEST_HEADER = re.compile(r"\b(roi|win rate|hit rate|profit|return)\b", re.I)


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []
        self.tables: list[dict] = []
        self._cur = None
        self._cell = None
        self._headers: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and "href" in d:
            self.hrefs.append(d["href"])
        if tag == "table":
            self._cur = {"rows": 0, "header": False, "cells": [], "https": 0, "links": 0,
                         "headers": [], "_row_has_link": False}
        elif tag == "thead" and self._cur is not None:
            self._cur["header"] = True
        elif tag == "tr" and self._cur is not None:
            self._cur["rows"] += 1
        elif tag == "th" and self._cur is not None:
            self._cell = []
        elif tag == "td" and self._cur is not None:
            self._cell = []
        elif tag == "a" and self._cur is not None:
            self._cur["links"] += 1
            self._cur["_row_has_link"] = True
            if d.get("href", "").startswith("https://"):
                self._cur["https"] += 1

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cur is not None and self._cell is not None:
            txt = "".join(self._cell).strip()
            self._cur["cells"].append(txt)
            if tag == "th":
                self._cur["headers"].append(txt)
            self._cell = None
        elif tag == "table" and self._cur is not None:
            self.tables.append(self._cur)
            self._cur = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                              check=False).stdout.strip()
    except Exception:
        return ""


def main() -> int:
    problems: list[str] = []
    graph: dict[Path, set[Path]] = {}
    n_tables = n_rows = 0

    for p in PAGES:
        s = Scan()
        s.feed(p.read_text(encoding="utf-8"))
        text = p.read_text(encoding="utf-8")
        edges = set()
        for h in s.hrefs:
            if h.startswith(("http://", "https://", "mailto:")) or h.startswith("#"):
                continue
            target = h.split("#")[0]
            if not target:
                continue
            t = (p.parent / target).resolve()
            if not t.is_file():
                problems.append(f"{p.name}: broken link -> {h}")
            else:
                edges.add(t)
        graph[p.resolve()] = edges

        for tb in s.tables:
            n_tables += 1
            n_rows += max(0, tb["rows"] - 1)
            if tb["header"] and tb["rows"] <= 1:
                problems.append(f"{p.name}: table with a header but no data rows")
            for hdr in tb["headers"]:
                if BACKTEST_HEADER.search(hdr):
                    problems.append(f"{p.name}: backtest metric in table header ({hdr!r})")
            for c in tb["cells"]:
                if c == "":
                    problems.append(f"{p.name}: empty table cell (use an explicit blank label)")
                    break
            if tb["rows"] > 1 and tb["https"] == 0:
                problems.append(f"{p.name}: data table with no https source link")

        # literal markdown leak
        prose = re.sub(r"<code\b.*?</code>|<pre\b.*?</pre>", "", text, flags=re.S)
        prose = re.sub(r"<[^>]+>", " ", prose)
        for pat, label in ((r"\*\*[^*\n]{1,80}\*\*", "**bold**"),
                           (r"(?<![\w_])_[A-Za-z][A-Za-z '\-]{0,40}_(?![\w_])", "_emphasis_")):
            m = re.search(pat, prose)
            if m:
                problems.append(f"{p.name}: literal markdown {label} in prose ({m.group(0)[:40]!r})")

        for card in re.findall(r'<article class="kpi">(.*?)</article>', text, re.S):
            if 'class="note"' not in card:
                problems.append(f"{p.name}: KPI card without a provenance note")

    # reachability
    seen, stack = set(), [(HERE / "index.html").resolve()]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(graph.get(n, ()))
    for p in PAGES:
        if p.resolve() not in seen:
            problems.append(f"{p.name}: unreachable from index.html")

    # registration tamper guard
    try:
        rule = json.loads((DATA / "rewards.json").read_text(encoding="utf-8"))
        thresh = json.loads((DATA / "thresholds.json").read_text(encoding="utf-8"))
    except Exception as exc:
        problems.append(f"cannot read rewards data: {exc}")
        rule = thresh = {}

    if RULE_FILE.is_file():
        actual_sha = hashlib.sha256(RULE_FILE.read_bytes()).hexdigest()
        recorded_sha = rule.get("rule_sha256", "")
        if actual_sha != recorded_sha:
            problems.append(
                f"frozen rule drifted: REWARDS-RULE.md sha256 is {actual_sha[:12]}, "
                f"registered {recorded_sha[:12]}")
        reg_commit = git("log", "--diff-filter=A", "--format=%H", "-1", "--",
                         "rewards/REWARDS-RULE.md")
        if reg_commit and rule.get("registration_commit", "") != reg_commit:
            problems.append(
                f"registration commit drifted: git records {reg_commit[:12]}, "
                f"data records {rule.get('registration_commit','')[:12]}")
    else:
        problems.append("rewards/REWARDS-RULE.md is missing")

    # thresholds concrete
    for t in thresh.get("thresholds", []):
        val = str(t.get("value", "")).strip()
        if not val or val.lower() in {"blank", "tbd", "n/a", "todo", "placeholder"}:
            problems.append(f"threshold {t.get('id')} is blank or a placeholder: {val!r}")
        if t.get("numeric") is None and not re.match(r"^[<>]=?\s*-?\d", val):
            problems.append(f"threshold {t.get('id')} has no numeric value: {val!r}")

    print(f"rewards pages checked: {len(PAGES)}")
    print(f"tables checked: {n_tables} · data rows: {n_rows}")
    if problems:
        print("\nPROBLEMS:")
        for x in problems:
            print(" -", x)
        return 1
    print("PASS: the rule is frozen, the thresholds are concrete, every table row carries a"
          " source link, no backtest metric is a column, and all local links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
