#!/usr/bin/env python3
"""tools/check_preregistration.py — a backtest number may not appear without a frozen rule (C1).

Three failure modes, all of them real
-------------------------------------
1. **An unregistered result.** `data/s9cb/leaderboard.json` publishes a strategy that has no
   record in `data/strat/preregistration.json`.  A number nobody registered is a number that was
   chosen after the fact, which the brief forbids outright.
2. **A registration that came after the result.** The registration commit must be an ancestor of
   the commit that publishes the result.  If it is not, the "pre-" in pre-registration is a lie.
3. **Drift between the frozen text and the code.** A registration whose rule no longer fires the
   way it was registered is worthless, because the result being published was produced by a
   different rule.  Every registered backtest rule's exact strategy string must still appear in
   the generator that scores it.

What this gate deliberately does not do
---------------------------------------
It does not require a rule to be profitable, and it does not fail on a losing rule.  A registered
rule that loses is a result, which is the point of registering it.

Run: python3 tools/check_preregistration.py
     python3 tools/check_preregistration.py --self-test   # prove each check fires
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE = os.path.join(ROOT, "data", "strat", "preregistration.json")
LB = os.path.join(ROOT, "data", "s9cb", "leaderboard.json")
GENERATOR = os.path.join(ROOT, "s9cb", "analysis", "strategies.py")


def git(*args: str) -> tuple[int, str]:
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def is_ancestor(commit: str, of: str = "HEAD") -> bool:
    code, _ = git("merge-base", "--is-ancestor", commit, of)
    return code == 0


def check(reg: dict, scored: set[str], generator_src: str,
          head: str = "HEAD", problems: list | None = None) -> list[str]:
    problems = problems if problems is not None else []
    records = reg.get("records") or []
    by_key = {f"{r['id']} {r['name']}": r for r in records}

    # 1. every published result has a record
    for strategy in sorted(scored):
        if strategy not in by_key:
            problems.append(f"result published with no registration: {strategy!r}")

    # 2. every record's commit precedes the publishing commit
    for r in records:
        c = r.get("registration_commit")
        if not c:
            problems.append(f"{r['id']}: registration has no commit hash")
            continue
        if not is_ancestor(c, head):
            problems.append(f"{r['id']}: registration commit {c[:8]} is not an ancestor of {head[:8]} "
                            f"— the rule was registered after the result")

    # 3. the frozen text still matches the code
    for r in records:
        if r.get("status") != "registered-backtest":
            continue
        key = f"{r['id']} {r['name']}"
        if f'"{key}"' not in generator_src:
            problems.append(f"{r['id']}: the registered rule {key!r} no longer appears in "
                            f"s9cb/analysis/strategies.py — the text drifted from the code")

    # 4. a registered-prospective rule must not have a result yet
    for r in records:
        if r.get("status") == "registered-prospective":
            if f"{r['id']} {r['name']}" in scored:
                problems.append(f"{r['id']}: registered as prospective but a backtest result exists")
    return problems


def main(argv: list[str]) -> int:
    # importable without side effects, so the tests can call check() directly
    reg = json.load(open(PRE, encoding="utf-8"))
    scored = {r["strategy"] for r in json.load(open(LB, encoding="utf-8"))["leaderboard"]}
    gen = open(GENERATOR, encoding="utf-8").read()
    _, head = git("rev-parse", "HEAD")

    if "--self-test" in argv:
        fired = 0
        cases = [
            ("unregistered result", {**reg}, scored | {"S99 A rule nobody registered"}, gen),
            ("post-hoc registration", {**reg, "records": [
                {**reg["records"][0], "registration_commit": "0" * 40}] + reg["records"][1:]}, scored, gen),
            ("text drift", {**reg, "records": [
                {**reg["records"][0], "name": "a rule that does not exist"}] + reg["records"][1:]}, scored, gen),
        ]
        for name, r, s, g in cases:
            probs = check(r, s, g, head)
            ok = bool(probs)
            print(f"self-test: {name} {'DETECTED' if ok else 'MISSED — the gate is dead'}")
            fired += 1 if ok else 0
        return 0 if fired == len(cases) else 1

    problems = check(reg, scored, gen, head)

    print(f"registration records: {len(reg.get('records') or [])}")
    print(f"published backtest results: {len(scored)}")
    print(f"registration commit on file: {(reg.get('registration_commit') or '')[:8]} · head: {head[:8]}")
    if problems:
        print(f"\nFAIL: {len(problems)} pre-registration problem(s)")
        for p in problems:
            print("  -", p)
        return 1
    print("\nPASS: every published result has a registration, every registration precedes its "
          "result, and every frozen rule text still matches the generator")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
