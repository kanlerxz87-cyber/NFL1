#!/usr/bin/env python3
"""strat/diff.py — the weekly 'what changed' diff instead of a static snapshot (C12, PR-25).

The requirement
---------------
"Publish a weekly 'what changed' diff instead of a static snapshot. Store each weekly snapshot and
render a diff column (rank change, rating change, availability change)."  (Readiness PR-25,
*Not started*.)

What is compared
----------------
Every build writes a snapshot of the competition state — each strategy's rank, its skill versus its
price, its ROI and its settled-bet count, plus the model's three market scores and the count of live
strategies.  The snapshot is written to `data/strat/snapshots/` and the newest one is diffed
against the one before it, so the page shows a **change column** rather than a static table.

An honest limitation, stated on the page
---------------------------------------
The backtest sample does not grow between builds unless new completed games arrive, so a diff
between two builds minutes apart is mostly zeros.  That is published as it is: a diff that showed
movement where the data did not move would be worse than no diff.  The first genuinely informative
diff will be the one after the next completed week, and the page says so.

What is deliberately blank
--------------------------
"Availability change" needs an availability feed; the injury-designation columns exist but the
starter-level availability the brief wants is blocked (readiness IN-04, IN-18).  The column is
published with the blocking reason instead of a fabricated delta.

Run: python3 strat/diff.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

SNAPDIR = os.path.join(lib.DATA, "snapshots")


def build_state(ps, pre, dem) -> dict:
    rows = sorted(ps["strategy_scores"], key=lambda r: -(r.get("bss_vs_price") or -9e9))
    state = {"model": {}, "strategies": {}}
    for i, m in enumerate(ps["markets"]):
        res = m["results"] or {}
        model = res.get("model") or {}
        key = m["market"]
        state["model"][key] = {
            "bss": model.get("bss", model.get("bss_vs_devig")),
            "n": model.get("n_scored"),
            "lower_bound": model.get("bss_lower_bound"),
        }
    for rank, r in enumerate(rows, 1):
        state["strategies"][r["strategy"]] = {
            "rank": rank if r.get("status") == "scored" else None,
            "bss_vs_price": r.get("bss_vs_price"),
            "roi_pct": r.get("roi_pct"),
            "n_decided": r.get("n_decided"),
            "status": r.get("status"),
        }
    state["live"] = dem["n_live"]
    state["registered"] = pre["n_records"]
    return state


def main() -> int:
    ps = lib.load("proper_score.json")
    pre = lib.load("preregistration.json")
    dem = lib.load("demotion.json")

    os.makedirs(SNAPDIR, exist_ok=True)
    files = sorted(f for f in os.listdir(SNAPDIR) if f.endswith(".json"))
    state = build_state(ps, pre, dem)

    # A snapshot is written only when the state changed, so the directory is a history of real
    # changes and not a list of identical files.
    payload = {"generated_at": lib.now(), "state": state}
    last = None
    if files:
        with open(os.path.join(SNAPDIR, files[-1]), encoding="utf-8") as fh:
            last = json.load(fh)
    changed = (last is None) or (last.get("state") != state)
    stamped = ps["generated_at"].replace(":", "").replace("-", "").replace("+0000", "Z")
    name = f"{stamped}.json"
    if changed:
        with open(os.path.join(SNAPDIR, name), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
            fh.write("\n")
        print(f"wrote data/strat/snapshots/{name} (state changed)")
    else:
        print("state unchanged since the last snapshot; nothing written")

    files = sorted(f for f in os.listdir(SNAPDIR) if f.endswith(".json"))
    cur = payload if changed else last
    prev = None
    if len(files) >= 2:
        with open(os.path.join(SNAPDIR, files[-2]), encoding="utf-8") as fh:
            prev = json.load(fh)

    diffs = []
    for key in ("side", "total", "moneyline"):
        c = (cur["state"]["model"].get(key) or {})
        p = ((prev or {}).get("state", {}).get("model", {}).get(key) or {})
        diffs.append({
            "item": f"Model skill, {key}",
            "current": c.get("bss"), "previous": p.get("bss"),
            "change": (c.get("bss") - p.get("bss")) if (c.get("bss") is not None and
                                                         p.get("bss") is not None) else None,
            "current_n": c.get("n"), "previous_n": p.get("n"),
            "unit": "Brier skill",
            "source": "proper_score",
        })
    for key in ("live", "registered"):
        c, p = cur["state"].get(key), (prev or {}).get("state", {}).get(key)
        diffs.append({"item": f"Strategies {key}", "current": c, "previous": p,
                      "change": (c - p) if (c is not None and p is not None) else None,
                      "unit": "count", "source": "demotion" if key == "live" else "preregistration"})

    srows = []
    for name, cur_row in sorted(cur["state"]["strategies"].items(),
                                key=lambda kv: (kv[1]["rank"] is None, kv[1]["rank"] or 999)):
        prev_row = ((prev or {}).get("state", {}).get("strategies", {}) or {}).get(name, {})
        srows.append({
            "strategy": name,
            "rank": cur_row["rank"], "previous_rank": prev_row.get("rank"),
            "rank_change": ((prev_row.get("rank") - cur_row["rank"])
                            if (cur_row["rank"] and prev_row.get("rank")) else None),
            "skill": cur_row["bss_vs_price"], "previous_skill": prev_row.get("bss_vs_price"),
            "skill_change": ((cur_row["bss_vs_price"] - prev_row["bss_vs_price"])
                             if (cur_row["bss_vs_price"] is not None and
                                 prev_row.get("bss_vs_price") is not None) else None),
            "settled": cur_row["n_decided"], "previous_settled": prev_row.get("n_decided"),
            "source": "proper_score",
        })

    lib.write_json("diff.json", {
        "generated_at": lib.now(),
        "n_snapshots": len(files),
        "current_snapshot": files[-1] if files else None,
        "previous_snapshot": files[-2] if len(files) >= 2 else None,
        "has_previous": len(files) >= 2,
        "note": ("A snapshot is written only when the state changes. The backtest sample grows only "
                 "when a new game completes, so two builds minutes apart usually show zeros — which "
                 "is the honest diff, not a missing one."),
        "availability_change": {
            "value": None,
            "reason": ("No availability delta is published. The brief asks for a change in the "
                       "surface (starters out, replacements named), which needs an official inactive "
                       "list and Game Book starters; both are blocked (readiness IN-04, IN-18). The "
                       "injury-designation level is captured and is NOT the same thing."),
        },
        "model_diffs": diffs,
        "strategy_diffs": srows,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
