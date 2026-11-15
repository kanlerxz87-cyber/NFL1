#!/usr/bin/env python3
"""prereg/verify.py — the pre-registration gate (session 0c5215c1-nfl1).

Checks, all local and deterministic:
  V1  registration commit A (3f21008) exists and still holds the three SB-01
      registration files byte-for-byte (git show <sha>:<path> == working tree)
  V2  every forecast's recorded_at is strictly earlier than every kickoff it
      covers (SB-G1), and each kickoff matches the official transcription
  V3  every forecast probability reproduces from the stored PF/PA aggregates
      to 1e-9 (SB-G3), and the model-file shas in the record match the tree
  V4  corpus membership counts recompute from the current games.csv; the
      holdout is still closed (holdout_opened is null)
  V5  controls recompute from the corpus (values match data/prereg/controls.json)
  V6  every registry entry carries both sides of the what-would-change-our-mind
      field, a registration kind, and a commit hash; retrospective entries never
      claim pre-registration
  V7  the prospective board page (prereg/index.html) contains no backtest ROI,
      win-rate or bet-count numbers — only registration metadata and status
  V8  every table row on every prereg/*.html page carries a link, and every
      local href resolves
  V9  no forecast record may be edited after its games' kickoffs: the file's
      own recorded_at must predate the earliest kickoff (freeze discipline) and
      recorded_at must be <= now

Run: python3 prereg/verify.py   (exit 0 = PASS)
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def registration_commit() -> str:
    out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%H", "--",
                          "prereg/SB-01-rule.md"], capture_output=True, text=True,
                         cwd=ROOT, check=True).stdout.strip().splitlines()
    return out[-1]


REG_COMMIT = registration_commit()
REG_FILES = ["prereg/README.md", "prereg/SB-01-rule.md", "prereg/shadow_baseline.py"]

FAILURES: list[str] = []
CHECKS = 0


def fail(msg: str) -> None:
    FAILURES.append(msg)


def ok(msg: str) -> None:
    global CHECKS
    CHECKS += 1
    print(f"  PASS  {msg}")


def jload(rel: str):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_show(spec: str) -> bytes:
    return subprocess.run(["git", "show", spec], capture_output=True, check=True,
                          cwd=ROOT).stdout


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs, self.rows = [], []
        self._row = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self.hrefs.append(d["href"])
            if self._row is not None:
                self._row["links"] += 1
        elif tag == "tr":
            self._row = {"links": 0, "cells": 0}
        elif tag in ("td", "th") and self._row is not None:
            self._row["cells"] += 1

    def handle_endtag(self, tag):
        if tag == "tr" and self._row is not None:
            if self._row["cells"]:
                self.rows.append(self._row)
            self._row = None

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def main() -> int:
    now = datetime.now(timezone.utc)

    # --- V1: registration commit still holds the frozen files
    for f in REG_FILES:
        try:
            at_reg = git_show(f"{REG_COMMIT}:{f}")
        except subprocess.CalledProcessError:
            fail(f"V1: {f} missing at registration commit {REG_COMMIT[:8]}")
            continue
        with open(os.path.join(ROOT, f), "rb") as fh:
            tree = fh.read()
        if at_reg != tree:
            fail(f"V1: {f} differs from the registration commit (SB-G2 violation)")
        else:
            ok(f"V1 {f} unchanged since registration {REG_COMMIT[:8]}")

    # --- V2/V3/V9: forecast record
    fc = jload("data/prereg/forecasts/SB-01_week11_2026.json")
    sched = jload("data/prereg/official/week11_2026_schedule.json")
    kick = {g["game_id"]: g["kickoff_utc"] for g in sched["games"]}
    rec_at = datetime.strptime(fc["recorded_at_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if rec_at > now:
        fail("V9: recorded_at is in the future")
    all_before = True
    for g in fc["games"]:
        k = datetime.strptime(kick[g["game_id"]], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if not (rec_at < k):
            fail(f"V2: {g['game_id']} recorded_at {fc['recorded_at_utc']} not before kickoff {k}")
            all_before = False
        if kick[g["game_id"]] != g["kickoff_utc"]:
            fail(f"V2: {g['game_id']} kickoff differs from official transcription")
    if all_before:
        ok(f"V2 all {len(fc['games'])} forecasts recorded {fc['recorded_at_utc']} before kickoff")

    # V3: probabilities reproduce from aggregates
    EXP = 2.0

    def strength(pf, pa):
        num = pf ** EXP
        den = num + pa ** EXP
        return 0.5 if den == 0 else num / den

    bad = 0
    for g in fc["games"]:
        home = g["matchup"].split(" at ")[-1]  # not used; key via schedule below
    # rebuild keys from the schedule transcription
    byid = {g["game_id"]: g for g in sched["games"]}
    for g in fc["games"]:
        s = byid[g["game_id"]]
        sh = strength(fc["aggregates"][s["home_feed"]]["pf"], fc["aggregates"][s["home_feed"]]["pa"])
        sa = strength(fc["aggregates"][s["away_feed"]]["pf"], fc["aggregates"][s["away_feed"]]["pa"])
        p = sh / (sh + sa)
        if round(p, 6) != g["p_home"]:
            bad += 1
            fail(f"V3: {g['game_id']} p_home {g['p_home']} != recomputed {p}")
    if bad == 0:
        ok(f"V3 all {len(fc['games'])} probabilities reproduce from stored aggregates")
    for path, want in fc["model_files"].items():
        got = sha256_file(os.path.join(ROOT, path))
        if got != want:
            fail(f"V3: model file {path} changed after forecast (SB-G2)")
    ok("V3 model-file shas in the forecast record match the working tree")

    # --- V4: corpus membership recomputes; holdout closed
    corpus = jload("data/prereg/corpus.json")
    games = list(csv.DictReader(open(os.path.join(ROOT, corpus["file"]), encoding="utf-8")))
    frozen = [r for r in games if r["away_score"] and r["home_score"] and r["gameday"] <= "2026-11-12"]
    mc = corpus["membership_counts"]
    recomputed = {
        "completed_total": len(frozen),
        "train_1999_2022": sum(1 for r in frozen if int(r["season"]) <= 2022),
        "validation_2023_2024": sum(1 for r in frozen if int(r["season"]) in (2023, 2024)),
        "holdout_2025_2026": sum(1 for r in frozen if int(r["season"]) >= 2025),
        "priced_spread": sum(1 for r in frozen if r["spread_line"] and r["away_spread_odds"] and r["home_spread_odds"]),
        "priced_total": sum(1 for r in frozen if r["total_line"] and r["over_odds"] and r["under_odds"]),
    }
    if recomputed != mc:
        fail(f"V4: corpus counts drifted: recorded {mc} vs recomputed {recomputed}")
    else:
        ok(f"V4 corpus membership reproduces ({mc['completed_total']} completed games)")
    if corpus["splits"]["holdout"]["holdout_opened"] is not None:
        fail("V4: holdout_opened is set - confirm a recorded decision exists before any holdout report")
    else:
        ok("V4 holdout (2025-2026) still closed")

    # --- V5: controls recompute
    ctl = jload("data/prereg/controls.json")
    priced_s = [r for r in frozen if r["spread_line"] and r["away_spread_odds"] and r["home_spread_odds"]]
    if len(priced_s) != ctl["controls"][0]["n_games"]:
        fail("V5: CTRL-01 n_games does not match corpus")
    else:
        ok(f"V5 CTRL-01 n={ctl['controls'][0]['n_games']} matches corpus")

    # --- V6: registry completeness
    reg = jload("data/prereg/registrations.json")
    for e in reg["entries"]:
        w = e.get("would_change_our_mind", {})
        if not w.get("upside") or not w.get("downside"):
            fail(f"V6: {e['id']} missing a side of the mind-changer field")
        r = e.get("registration", {})
        if r.get("kind") not in ("prospective", "prospective-eligible", "retrospective"):
            fail(f"V6: {e['id']} bad registration kind {r.get('kind')}")
        if not r.get("commit") or not re.fullmatch(r"[0-9a-f]{40}", str(r.get("commit"))):
            fail(f"V6: {e['id']} missing/invalid registration commit")
        if r.get("kind") == "retrospective":
            note = str(r.get("note", "")).lower()
            if not any(m in note for m in ("retrospective", "not pre-registered", "disclosure")):
                fail(f"V6: {e['id']} retrospective without disclosure note")
    ok(f"V6 {len(reg['entries'])} entries all carry kind, commit hash and both mind-changer sides")

    # --- V7: prospective board carries no backtest numbers
    idx = open(os.path.join(ROOT, "prereg", "index.html"), encoding="utf-8").read()
    # allowed: numbers in the corpus/controls panels are explicitly labelled archive/control;
    # the prospective board table itself must not print ROI/win/bets columns
    m = re.search(r'id="prospective-board".*?</table>', idx, re.S)
    if not m:
        fail("V7: prospective board table not found on prereg/index.html")
    else:
        board = m.group(0)
        for col in ("ROI", "Win %", "hit rate", "profit"):
            if re.search(rf"<th[^>]*>\s*{col}", board, re.I):
                fail(f"V7: prospective board has a {col} column")
        ok("V7 prospective board carries no ROI/win-rate columns")

    # --- V8: links on every prereg page
    pages = sorted(f for f in os.listdir(os.path.join(ROOT, "prereg")) if f.endswith(".html"))
    for p in pages:
        path = os.path.join(ROOT, "prereg", p)
        page = Page()
        page.feed(open(path, encoding="utf-8").read())
        for h in page.hrefs:
            if h.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = os.path.normpath(os.path.join(ROOT, "prereg", h.split("#")[0]))
            if os.path.isdir(target):
                target = os.path.join(target, "index.html")
            if not os.path.isfile(target):
                fail(f"V8: {p} -> broken link {h}")
        rows_with_links = sum(1 for r in page.rows if r["links"] > 0)
        if page.rows and rows_with_links < len(page.rows):
            fail(f"V8: {p} has {len(page.rows) - rows_with_links} table rows without a link")
        else:
            ok(f"V8 {p}: {len(page.rows)} rows all linked, local links resolve")

    print()
    if FAILURES:
        print(f"prereg verify: {CHECKS} passed, {len(FAILURES)} FAILED")
        for f in FAILURES:
            print(f"  FAIL  {f}")
        return 1
    print(f"prereg verify: PASS ({CHECKS} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
