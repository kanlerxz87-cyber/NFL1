#!/usr/bin/env python3
"""normalize_nav.py — ensure every page carries the same canonical navigation.

Additive and idempotent: the <nav> block is rewritten to one shared list, preserving the
current page's `active` state. No page content outside <nav> is touched.
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANON = [
    ("index.html", "Overview"),
    ("lines.html", "My Lines"),
    ("strategies.html", "Strategy Lab"),
    ("injuries.html", "Injuries & Depth"),
    ("props.html", "Player Props"),
    ("audit.html", "Official Audit"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("decisions.html", "Decision Register"),
    ("analysis.html", "Validation & Correlation"),
    ("evidence.html", "Evidence"),
    ("review.html", "Flagged for Review"),
    ("executive.html", "Executive Summary"),
]


def build(page_name: str, is_index: bool) -> str:
    items = []
    for href, label in CANON:
        # index.html sits at the repo root; every sister page sits one level down in pages/
        if is_index:
            target = "index.html" if href == "index.html" else f"pages/{href}"
        else:
            target = "../index.html" if href == "index.html" else href
        cls = ' class="active"' if href == page_name else ""
        items.append(f'    <a href="{target}"{cls}>{label}</a>')
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
