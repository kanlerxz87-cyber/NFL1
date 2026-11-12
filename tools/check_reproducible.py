#!/usr/bin/env python3
"""check_reproducible.py — a rebuild must change nothing except the clock.

Why the clock is special
------------------------
Every page stamps when it read its data, and the verification layer stamps when it ran. Those
are honest timestamps: they must move when the build actually runs. Everything else on the page
is a function of committed JSON, so a clean rebuild must reproduce it byte for byte.

What this asserts
-----------------
After the build steps, `git diff` may only touch lines that are *entirely* a build stamp:

    Data read 2026-11-12T22:40:47+00:00 · verification run ...
    Data built 2026-11-12T18:53:41+00:00 · every value links to its source
    "generated_at": "2026-11-12T22:40:47+00:00",

A changed number, a changed row, a changed link, or a changed file *outside* the stamp lines is
a reproducibility failure — it means the published page cannot be derived from what is committed.

Run after the build steps:  python3 tools/check_reproducible.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

STAMP = re.compile(
    r'^\s*(?:Data read|Data built|Data snapshot|Verification run|verification run|'
    r'"?generated_at"?\s*:)?\s*["\']?'
    r'(?:\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\+00:00|Z))'
    r'["\']?\s*(?:·.*)?$'
)

# Files whose entire content is a build artefact with a clock in it.
CLOCK_FILES = {
    "data/decision_room/decision_room.json",
}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout


def main() -> int:
    status = git("status", "--porcelain")
    if not status.strip():
        print("clean rebuild: committed output is exactly what the build produces.")
        return 0

    bad = []
    only_clock = []
    for line in status.splitlines():
        code, path = line[:2], line[3:].strip()
        if not path:
            continue
        full = os.path.join(ROOT, path)
        if code.strip() == "M" and os.path.isfile(full):
            diff = git("diff", "-U0", "--", path)
            changed = [l[1:] for l in diff.splitlines()
                       if (l.startswith("+") or l.startswith("-"))
                       and not l.startswith(("+++", "---"))]
            non_stamp = [c for c in changed if c.strip() and not STAMP.match(c)]
            if non_stamp:
                bad.append((path, non_stamp[:3]))
            else:
                only_clock.append(path)
        else:
            bad.append((path, [f"file {code.strip() or 'added/removed'}"]))

    if only_clock:
        print(f"{len(only_clock)} file(s) changed only in their build stamp (expected):")
        for p in sorted(only_clock):
            print(f"  {p}")

    if bad:
        print(f"\nREPRODUCIBILITY FAILURE — {len(bad)} path(s) changed beyond the timestamp:")
        for path, sample in bad:
            print(f"  {path}")
            for s in sample:
                print(f"      {s[:160]}")
        print("\nThe published pages cannot be derived from the committed data. "
              "Commit the rebuilt output, or fix the generator.")
        return 1

    print("\nRESULT: PASS — every substantive byte reproduces from the committed data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
