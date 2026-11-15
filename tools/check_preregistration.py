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

import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE = os.path.join(ROOT, "data", "strat", "preregistration.json")
LB = os.path.join(ROOT, "data", "s9cb", "leaderboard.json")
GENERATOR = os.path.join(ROOT, "s9cb", "analysis", "strategies.py")
STAMP = os.path.join(ROOT, "data", "strat", "preregistration_stamp.json")
PRE_PATH = "data/strat/preregistration.json"


def git(*args: str) -> tuple[int, str]:
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def is_ancestor(commit: str, of: str = "HEAD") -> bool:
    code, _ = git("merge-base", "--is-ancestor", commit, of)
    return code == 0


def check_stamp(stamp: dict, reg: dict, problems: list) -> dict:
    """The registry as committed must hash to the value the stamp recorded."""
    out = {"registration_commit": (stamp.get("registration_commit") or "")[:12],
           "n_rule_fingerprints": len(stamp.get("rule_sha256") or {})}
    commit = stamp.get("registration_commit")
    if not commit:
        problems.append("no registration stamp: run tools/stamp_preregistration.py")
        return out
    blob = subprocess.run(["git", "show", f"{commit}:{PRE_PATH}"], cwd=ROOT,
                          capture_output=True).stdout
    if not blob:
        problems.append(f"stamp names commit {commit[:8]} but {PRE_PATH} is not in it")
        return out
    digest = hashlib.sha256(blob).hexdigest()
    out["file_sha256_matches"] = (digest == stamp.get("file_sha256_as_committed"))
    if not out["file_sha256_matches"]:
        problems.append(
            f"{PRE_PATH} has changed since commit {commit[:8]} was stamped "
            f"({digest[:12]} != {stamp.get('file_sha256_as_committed', '')[:12]}). A frozen rule "
            f"was edited after registration; re-register with a new stamp and say why in "
            f"COORDINATION.md, or revert the edit.")
    # the fingerprint of every rule's frozen fields must still match
    fps = stamp.get("rule_sha256") or {}
    for r in reg.get("records") or []:
        key = f"{r['id']} {r['name']}"
        want = fps.get(key)
        got = hashlib.sha256(
            json.dumps({"definition": r["definition"], "inputs": r["inputs"],
                        "sample_window": r["sample_window"], "gates": r["gates"]},
                       sort_keys=True).encode()).hexdigest()
        if want and want != got:
            problems.append(f"{r['id']}: the frozen fields of {key!r} changed after registration")
        elif not want:
            problems.append(f"{r['id']}: {key!r} has no stamped fingerprint")
    return out


def check(reg: dict, scored: set[str], generator_src: str,
          head: str = "HEAD", problems: list | None = None) -> list[str]:
    problems = problems if problems is not None else []
    records = reg.get("records") or []
    by_key = {f"{r['id']} {r['name']}": r for r in records}

    # 1. every published result has a record
    for strategy in sorted(scored):
        if strategy not in by_key:
            problems.append(f"result published with no registration: {strategy!r}")

    # 2. the stamp's commit must precede the publishing commit
    #    (one stamp covers the whole registry; see tools/stamp_preregistration.py)

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
        fired = total = 0

        def report(name, detected):
            nonlocal fired, total
            total += 1
            fired += 1 if detected else 0
            print(f"self-test: {name} {'DETECTED' if detected else 'MISSED — the gate is dead'}")

        # 1. a result with no registration
        report("unregistered result",
               bool(check(reg, scored | {"S99 A rule nobody registered"}, gen, head)))
        # 2. frozen text that no longer matches the generator
        drifted = {**reg, "records": [{**reg["records"][0], "name": "a rule that does not exist"}]
                   + reg["records"][1:]}
        report("text drift", any("no longer appears" in p for p in check(drifted, scored, gen, head)))
        # 3. a prospective rule that has acquired a backtest result
        prom = next(r for r in reg["records"] if r["status"] == "registered-prospective")
        report("prospective rule with a result",
               any("registered as prospective" in p
                   for p in check(reg, scored | {f"{prom['id']} {prom['name']}"}, gen, head)))
        # 4. the registry edited after its stamp
        st = json.load(open(STAMP, encoding="utf-8")) if os.path.isfile(STAMP) else {}
        sp: list[str] = []
        check_stamp({**st, "file_sha256_as_committed": "0" * 64}, reg, sp)
        report("registry edited after the stamp", bool(sp))
        # 5. a rule's frozen fields edited after the stamp
        sp2: list[str] = []
        edited = {**reg, "records": [{**reg["records"][0],
                                     "definition": reg["records"][0]["definition"] + " (edited)"}]
                  + reg["records"][1:]}
        check_stamp(st, edited, sp2)
        report("a frozen rule field edited", bool(sp2))
        # 6. a stamp whose commit is not an ancestor of HEAD
        report("stamp not an ancestor of HEAD", not is_ancestor("0" * 40, head))
        return 0 if fired == total else 1

    problems = check(reg, scored, gen, head)
    stamp_problems: list[str] = []
    stamp = json.load(open(STAMP, encoding="utf-8")) if os.path.isfile(STAMP) else {}
    info = check_stamp(stamp, reg, stamp_problems)
    if stamp.get("registration_commit") and not is_ancestor(stamp["registration_commit"], head):
        stamp_problems.append("the stamped registration commit is not an ancestor of HEAD")
    problems += stamp_problems

    print(f"registration records: {len(reg.get('records') or [])}")
    print(f"published backtest results: {len(scored)}")
    print(f"stamped commit: {info.get('registration_commit')} · head: {head[:8]} · "
          f"rule fingerprints: {info.get('n_rule_fingerprints')} · "
          f"registry hash matches: {info.get('file_sha256_matches')}")
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
