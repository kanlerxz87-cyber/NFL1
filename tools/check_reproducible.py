#!/usr/bin/env python3
"""check_reproducible.py — a rebuild must change nothing except timestamps.

Why timestamps are special
--------------------------
Every page stamps when it read its data, and the verification layer stamps when it ran. Those
must move when the build actually runs; pinning them would make the stamp a lie. Everything
else on a page is a function of committed JSON, so a clean rebuild must reproduce it exactly.

The test
--------
Take `git diff -U0`, pair each removed line with the added line that replaced it, replace every
ISO-8601 timestamp in both with a placeholder, and require the pair to be identical:

    - <p class="timestamp">Data read 2026-11-12T22:40:47+00:00 · verification run ...
    + <p class="timestamp">Data read 2026-11-12T22:44:54+00:00 · verification run ...

is a pass. A changed number, row, link, label or file is a failure, because it means the
published page cannot be derived from what is committed.

Run after the build steps:  python3 tools/check_reproducible.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

ISO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?")
DATE_ONLY = re.compile(r"\d{4}-\d{2}-\d{2}")


def norm(line: str) -> str:
    return DATE_ONLY.sub("<DATE>", ISO.sub("<TS>", line)).rstrip()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout


def main() -> int:
    status = git("status", "--porcelain")
    if not status.strip():
        print("clean rebuild: committed output is exactly what the build produces.")
        return 0

    bad: list[tuple[str, list[str]]] = []
    clock_only: list[str] = []

    for entry in status.splitlines():
        code, path = entry[:2].strip(), entry[3:].strip()
        if not path:
            continue
        if code != "M":
            bad.append((path, [f"file is {code or 'changed'} — a rebuild created or removed it"]))
            continue

        diff = git("diff", "-U0", "--", path)
        removed, added = [], []
        for raw in diff.splitlines():
            if raw.startswith(("---", "+++")):
                continue
            if raw.startswith("-"):
                removed.append(raw[1:])
            elif raw.startswith("+"):
                added.append(raw[1:])

        # pair them positionally; any length mismatch is already a structural change
        if len(removed) != len(added):
            bad.append((path, [f"{len(removed)} line(s) removed, {len(added)} added"]))
            continue

        offenders = []
        for old, new in zip(removed, added):
            if norm(old) != norm(new):
                offenders.append(new.strip()[:160])
        if offenders:
            bad.append((path, offenders[:4]))
        else:
            clock_only.append(path)

    if clock_only:
        print(f"{len(clock_only)} file(s) changed only in their timestamps (expected):")
        for p in sorted(clock_only):
            print(f"  {p}")

    if bad:
        print(f"\nREPRODUCIBILITY FAILURE — {len(bad)} path(s) changed beyond the timestamps:")
        for path, sample in bad:
            print(f"  {path}")
            for s in sample:
                print(f"      {s}")
        print("\nThe published output cannot be derived from the committed data. "
              "Commit the rebuilt output, or fix the generator.")
        return 1

    print("\nRESULT: PASS — every substantive byte reproduces from the committed data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
