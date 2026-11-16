#!/usr/bin/env python3
"""Check the stored Lions official values against the stored verbatim page block.

Reads only files inside data/session-1a6737c5/. Exits non-zero on any mismatch, so it can
be used as a gate. It does not contact the network.

  python3 data/session-1a6737c5/verify_lions.py
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
BLOCK = HERE / "lions_w10_official_block_2026-11-16.md"
META = HERE / "lions_w10_official.json"


def parse_block(text):
    rows = {}
    for line in text.splitlines():
        if not line.startswith("| [") and not line.startswith("| ["):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        name = re.sub(r"^\[([^\]]+)\].*$", r"\1", cells[0])
        rows[name] = {
            "pos": cells[1],
            "injury": cells[2],
            "practice": cells[3],
            "game": cells[4],
        }
    return rows


def main():
    errors = []
    meta = json.loads(META.read_text(encoding="utf-8"))
    raw = BLOCK.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != meta["block_sha256"]:
        errors.append(f"block sha256 {digest} != recorded {meta['block_sha256']}")

    rows = parse_block(raw.decode("utf-8"))
    if len(rows) != meta["expected_row_count"]:
        errors.append(f"row count {len(rows)} != expected {meta['expected_row_count']}")

    for name, want in meta["official"].items():
        got = rows.get(name)
        if got is None:
            errors.append(f"{name}: missing from verbatim block")
            continue
        for key in ("pos", "injury", "practice", "game"):
            if got[key] != want[key]:
                errors.append(f"{name}.{key}: block={got[key]!r} recorded={want[key]!r}")

    for err in errors:
        print("FAIL", err)
    if errors:
        return 1
    print(f"OK: {len(rows)} rows; {len(meta['official'])} official designations match; sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
