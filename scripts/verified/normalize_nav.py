#!/usr/bin/env python3
"""normalize_nav.py — ensure every page carries the same canonical navigation.

Additive and idempotent: the <nav> block is rewritten to one shared list, preserving the
current page's `active` state. No page content outside <nav> is touched.
"""
from __future__ import annotations
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANON = [
    ("index.html", "Overview"),
    ("executive.html", "Executive Summary"),
    ("web/dashboard.html", "Decision Dashboard"),
    ("./dashboard.html", "Governance Registers"),
    ("lines.html", "My Lines"),
    ("correlations.html", "Correlations"),
    ("strategies.html", "Strategy Lab"),
    ("luck.html", "Skill vs Luck"),
    ("parlays.html", "Parlays & Combos"),
    ("props.html", "Player Props"),
    ("injuries.html", "Injuries"),
    ("depth.html", "Depth & Deficiency"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("evidence.html", "Evidence"),
    ("audit.html", "Official Audit"),
    ("review.html", "Flagged for Review"),
    ("sections.html", "All Sections"),
    # Session ca779bcc-nfl1: the strength-of-schedule study is its own sub-site under
    # strength/; the target rule below keeps its href correct from both levels.
    ("room/index.html", "Decision Room"),
    ("strength/index.html", "SOS Study"),
    # Sessions d23c65ad/c56ebee8: the review room and the s9cb research sub-site join
    # the shared bar so no published page can become unreachable.
    ("review-room/index.html", "Review Room"),
    ("research/index.html", "s9cb Research"),
    # pages produced by the other generators in this repository, kept in the shared
    # navigation so no session's page can become unreachable
    ("executive-summary.html", "Executive Summary (companion)"),
    ("teams.html", "Teams"),
    ("standings.html", "Standings"),
    ("availability.html", "Availability"),
    ("depth-strings.html", "Depth Strings"),
    ("data.html", "Verified Data"),
    ("verified-lines.html", "Own Lines"),
    ("analysis.html", "Validation & Correlation"),
    ("decisions.html", "Decision Register"),
    ("verified.html", "Verified Artifacts"),
    ("models.html", "Models"),
    ("flagged.html", "Flagged (companion)"),
]


def build(page_name: str, is_index: bool) -> str:
    items = []
    for href, label in CANON:
        # index.html sits at the repo root; every sister page sits one level down in pages/
        if href == "index.html":
            target = "index.html" if is_index else "../index.html"
        elif "/" in href:
            target = href if is_index else "../" + href
        else:
            target = ("pages/" + href) if is_index else href
        cls = (' class="active"' if ((href == page_name) if "/" in href
                                    else href.split("/")[-1] == page_name) else "")
        items.append(f'    <a href="{html.escape(target, quote=True)}"{cls}>{html.escape(label)}</a>')
    return "<nav>\n" + "\n".join(items) + "\n  </nav>"


def main() -> int:
    changed = 0
    for p in [ROOT / "index.html", *sorted((ROOT / "pages").glob("*.html"))]:
        t = p.read_text(encoding="utf-8")
        new = build(p.name, p.name == "index.html")
        m = re.search(r"<nav[^>]*>.*?</nav>", t, flags=re.S)
        if m:
            if m.group(0) == new:
                continue
            p.write_text(t[:m.start()] + new + t[m.end():], encoding="utf-8")
            changed += 1
            continue
        # No nav block at all: inject the canonical one right after <body> so the page
        # links every sister page. Additive - no existing content is removed.
        mb = re.search(r"<body[^>]*>", t)
        if not mb:
            print(f"skip (no nav, no body): {p.relative_to(ROOT)}")
            continue
        p.write_text(t[:mb.end()] + "\n  " + new + t[mb.end():], encoding="utf-8")
        changed += 1
    print(f"navigation normalized on {changed} page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
