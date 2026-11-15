#!/usr/bin/env python3
"""tools/stamp_preregistration.py — bind the frozen rule text to a commit (C1).

The problem
-----------
A git hash cannot be written inside the commit that it names: changing the file changes the hash.
So a registration file that claims "registration_commit: <hash of the commit that contains me>"
is either wrong or, if written in a later commit, records a commit that does not contain the text
it claims to freeze.

The mechanism used here
-----------------------
Two steps, in this order:

  1. the registry (`data/strat/preregistration.json`) is committed;
  2. this stamp records (a) the hash of the last commit that changed the registry and (b) the
     SHA-256 of the registry **as committed** (`git show <commit>:<path>`).

`tools/check_preregistration.py` re-reads `git show <commit>:<path>` and compares its SHA-256 to
the stamp.  Editing a frozen rule after registration therefore breaks the build with a hash
mismatch, which is exactly the guarantee the brief asks for: "commit the rule text … before the
evaluation window opens. The commit hash is the registration."

Run: python3 tools/stamp_preregistration.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = "data/strat/preregistration.json"
STAMP = "data/strat/preregistration_stamp.json"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main() -> int:
    last = git("log", "-1", "--format=%H", "--", PATH)
    if not last:
        print(f"FAIL: {PATH} has never been committed, so it cannot be stamped")
        return 1
    blob = subprocess.run(["git", "show", f"{last}:{PATH}"], cwd=ROOT,
                          capture_output=True, text=True).stdout.encode()
    digest = hashlib.sha256(blob).hexdigest()

    with open(os.path.join(ROOT, PATH), encoding="utf-8") as fh:
        registry = json.load(fh)
    frozen = {
        f"{r['id']} {r['name']}": hashlib.sha256(
            json.dumps({"definition": r["definition"], "inputs": r["inputs"],
                        "sample_window": r["sample_window"], "gates": r["gates"]},
                       sort_keys=True).encode()).hexdigest()
        for r in registry["records"]
    }

    stamp = {
        "generated_at_utc": git("log", "-1", "--format=%cI", "--", PATH),
        "path": PATH,
        "registration_commit": last,
        "registration_commit_subject": git("log", "-1", "--format=%s", "--", PATH),
        "file_sha256_as_committed": digest,
        "n_records": len(registry["records"]),
        "rule_sha256": frozen,
        "rule": ("The stamp is valid only when git show <registration_commit>:<path> hashes to "
                 "file_sha256_as_committed. Any edit to a frozen rule after that commit changes the "
                 "hash and fails tools/check_preregistration.py."),
    }
    os.makedirs(os.path.join(ROOT, "data", "strat"), exist_ok=True)
    with open(os.path.join(ROOT, STAMP), "w", encoding="utf-8") as fh:
        json.dump(stamp, fh, indent=1)
        fh.write("\n")
    print(f"stamped {PATH} at commit {last[:8]} ({stamp['registration_commit_subject'][:60]})")
    print(f"  file sha256 as committed: {digest}")
    print(f"  {len(frozen)} rule fingerprints recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
