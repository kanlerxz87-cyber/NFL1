#!/usr/bin/env python3
"""Pre-registration gate (session d4027f66-nfl1). Stdlib only.

FAILS (exit 1) when:
  * a registered rule file is missing or its sha256 differs from the registry (it was edited),
  * git history is available and the earliest commit adding the rule file is not the recorded
    registration commit,
  * a leaderboard row shows a rank, score, sample size or reward, or any backtest field,
    for a strategy that is not in a registration's `registered_strategies`.
FLAGS (exit 0) when git history is unavailable (for example a shallow CI checkout), so the
commit-hash check is reported as not performed rather than silently passed.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "data" / "preregistration" / "registry.json"
LB = ROOT / "data" / "leaderboard.json"


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def main() -> int:
    fails: list[str] = []
    flags: list[str] = []
    reg = json.loads(REG.read_text(encoding="utf-8"))
    registered: set[str] = set()
    for entry in reg["registrations"]:
        registered.update(entry.get("registered_strategies", []))
        path = ROOT / entry["file"]
        if not path.exists():
            fails.append(f"{entry['rule_id']}: rule file missing: {entry['file']}")
            continue
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha != entry["sha256"]:
            fails.append(f"{entry['rule_id']}: sha256 {sha[:12]}… differs from registered {entry['sha256'][:12]}… (file was edited after registration)")
        commits = _git("log", "--diff-filter=A", "--follow", "--format=%H", "--", entry["file"])
        if not commits:
            flags.append(f"{entry['rule_id']}: git history unavailable here; commit-hash check not performed "
                         f"(recorded registration {entry['registration_commit'][:12]})")
        else:
            first = commits.splitlines()[-1]
            if first != entry["registration_commit"]:
                fails.append(f"{entry['rule_id']}: first commit adding the rule is {first[:12]}, "
                             f"registry records {entry['registration_commit'][:12]}")
            else:
                flags.append(f"{entry['rule_id']}: registration commit {first[:12]} verified in git history")

    rows = json.loads(LB.read_text(encoding="utf-8"))
    numeric_fields = ("rank", "score", "sample_size", "reward")
    shown = 0
    for row in rows:
        if any("backtest" in k.lower() for k in row):
            fails.append(f"{row.get('strategy_id')}: leaderboard row has a backtest field")
        has_number = any(str(row.get(f, "")).strip() for f in numeric_fields)
        if has_number:
            shown += 1
            if row.get("strategy_id") not in registered:
                fails.append(f"{row.get('strategy_id')}: rank/score/sample/reward shown without a registration")
    print(f"leaderboard rows: {len(rows)}; rows with a ranked number: {shown}; registered strategies: {len(registered)}")
    for f in flags:
        print(f"FLAG  {f}")
    for f in fails:
        print(f"FAIL  {f}")
    if fails:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
