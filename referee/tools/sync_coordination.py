#!/usr/bin/env python3
"""Rebuild COORDINATION.md as: (version on origin/main, minus any old copy of our block) + our block.

Other sessions' content is taken verbatim from origin/main, so nothing of theirs is discarded.
Usage: python3 referee/tools/sync_coordination.py   (run from the repo root after `git fetch origin`)
"""
import pathlib
import subprocess

MARK = "## Session `73fdd6c4`"
base = subprocess.run(["git", "show", "origin/main:COORDINATION.md"], capture_output=True, text=True, check=True).stdout
if MARK in base:  # our block already reached main: strip it and re-append the current one
    head = base.split(MARK)[0].rstrip()
    if head.endswith("---"):
        head = head[:-3].rstrip()
    base = head + "\n"
block = pathlib.Path("referee/coordination_block.md").read_text()
pathlib.Path("COORDINATION.md").write_text(base.rstrip("\n") + "\n" + block)
print("COORDINATION.md rebuilt:", len(base.splitlines()), "lines from origin/main +", len(block.splitlines()), "lines of session block")
