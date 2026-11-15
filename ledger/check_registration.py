#!/usr/bin/env python3
"""Fail if the pre-registration file changed after the results were computed.

The hash stored in results.json is the hash of preregistration.json at the moment the study ran.
If someone edits the registration afterwards, this fails: a registration's only value is that it
was fixed before the results were seen, so editing it must require a new version file.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
res = json.load(open(os.path.join(ROOT, "data/session-c84a41a4/results.json"), encoding="utf-8"))
reg = res["registration"]
path = os.path.join(ROOT, reg["file"])
h = hashlib.sha256(open(path, "rb").read()).hexdigest()
if h != reg["sha256"]:
    print(f"FAIL: {reg['file']} has changed since the results were computed.")
    print(f"  registered: {reg['sha256']}")
    print(f"  on disk   : {h}")
    print("Publish a new preregistration-vN.json with its own declared date instead of editing it.")
    sys.exit(1)
print(f"OK: registration {reg['version']} unchanged since the results were computed ({h[:16]}…)")
