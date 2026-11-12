#!/usr/bin/env python3
"""Resolve the two shared files (COORDINATION.md, README.md) after merging main.

Strategy — never discard another session's work:
  * start from origin/main's version of the file
  * if main's own copy carries unresolved conflict markers, resolve them by keeping
    both variants where they differ and the more precise wording where equivalent
  * re-attach this session's appended section, taken from our version
  * strip any stray conflict-marker lines

Run from the repository root while a `git merge` conflict is in progress.
"""
from __future__ import annotations

import re
import subprocess
import sys

FILES = {
    "COORDINATION.md": "## Session `87deb7ab-nfl1` — verified dashboard",
    "README.md": "## Session `87deb7ab-nfl1` additions (PR #14)",
}

MARK = re.compile(r"^<<<<<<< [^\n]*\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*\n", re.S | re.M)


def resolve_main_conflicts(text: str, label: str) -> str:
    """Collapse any conflict blocks in *main's* copy, keeping all content."""
    blocks: list[tuple[str, str]] = []

    def grab(m: re.Match) -> str:
        blocks.append((m.group(1), m.group(2)))
        return "\x00BLOCK%d\x00" % (len(blocks) - 1)

    out = MARK.sub(grab, text)
    for i, (up, st) in enumerate(blocks):
        only_stashed = [l for l in st.split("\n") if l.strip() and l not in up]
        if not st.strip():
            merged = up.rstrip("\n") + "\n"
        elif only_stashed:
            merged = up.rstrip("\n") + "\n" + st.rstrip("\n") + "\n"
        else:
            merged = up.rstrip("\n") + "\n"
        print(f"   [{label}] conflict block {i}: upstream {len(up)}b, stashed {len(st)}b, "
              f"stashed-only lines {len(only_stashed)} -> kept "
              f"{'BOTH' if only_stashed and st.strip() else 'upstream'}")
        out = out.replace("\x00BLOCK%d\x00" % i, merged)
    return out


def strip_markers(text: str) -> str:
    text = re.sub(r"^<<<<<<< .*$", "", text, flags=re.M)
    text = re.sub(r"^=======$", "", text, flags=re.M)
    text = re.sub(r"^>>>>>>> .*$", "", text, flags=re.M)
    return text


def main() -> int:
    for f, marker in FILES.items():
        base = subprocess.run(["git", "show", f"origin/main:{f}"],
                              capture_output=True, text=True).stdout
        try:
            mine = open(f, encoding="utf-8").read()
        except FileNotFoundError:
            open(f, "w", encoding="utf-8").write(base)
            print(f"{f}: missing locally, took main's")
            continue

        if "<<<<<<<" in base:
            print(f"  {f}: main's copy has conflict markers - resolving:")
            base = resolve_main_conflicts(base, f)

        i = mine.find(marker)
        if i < 0:
            print(f"  {f}: no appendix found in our copy - keeping main's version")
            open(f, "w", encoding="utf-8").write(base)
            continue

        appendix = strip_markers(mine[i:])
        out = base.rstrip("\n") + "\n\n\n---\n\n" + appendix.lstrip("\n")
        open(f, "w", encoding="utf-8").write(out)
        lost = [l for l in base.split("\n") if l.strip() and l not in out]
        print(f"  {f}: rebuilt = main ({len(base)}b) + appendix ({len(appendix)}b); "
              f"main lines lost: {len(lost)}; markers: {out.count('<<<<<<<')}")
        for l in lost[:3]:
            print("     LOST:", l[:120])
    return 0


if __name__ == "__main__":
    sys.exit(main())
