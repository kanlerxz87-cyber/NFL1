#!/usr/bin/env python3
"""V4 - Snapshot of every parallel session: branch tip, last commit, files, pull requests, and which files
already on main the branch modifies. Facts come from git and the GitHub CLI; the 'claimed' and 'observation'
texts are this session's reading of each branch's COORDINATION.md and are marked as such.

Run from the repository root after:  git fetch -q origin '+refs/heads/*:refs/remotes/origin/*'
Output: referee/data/sessions.json     (standard library only; needs git, and gh for pull-request state)
"""
import datetime
import json
import os
import subprocess

REPO = os.path.join(os.path.dirname(__file__), "..", "..")
OUT = os.path.join(REPO, "referee", "data", "sessions.json")
GH = "https://github.com/kanlerxz87-cyber/NFL1"

NOTES = {
    "690e397b": {"claimed": "Evidence-first framework site (landing page, evidence, models, questions, suggestions, review pages).",
                 "observation": "Merged first. Its pages cite three operations.nfl.com addresses that return 404 (see flag R-11)."},
    "533256e1": {"claimed": "Dashboard site with official data tables (teams, standings, Week 10 injury rows); integration and merge.",
                 "observation": "All 84 data rows match the official pages (see Replication). Recorded itself as the integration session."},
    "15e79a53": {"claimed": "Independent review of the merged site (docs/review/merged-site.md).",
                 "observation": "Adjacent role to this session. Its findings on the three data tables agree with this session's row-by-row check."},
    "7600ed8b": {"claimed": "Q1-Q7: automated data pipeline, own lines, strategy leaderboard, injury/depth model, props, decision ledger, and final site integration.",
                 "observation": "Most active branch. 131 of its published numbers replicated here, 18 could not be tested, none contradicted. "
                                "Claims final integration and rewrites pages already on main."},
    "25aa7696": {"claimed": "Its own V1-V4: official-source dataset (136 games), own lines, new site pages, requirement ledger.",
                 "observation": "All 136 transcribed scores match the dataset. One published correlation uses a wrong division-game count (flag R-04). "
                                "Rewrites pages already on main and the deploy workflow."},
    "80731db4": {"claimed": "T01-T13: full project, including site build, final integration and merge.",
                 "observation": "Only the coordination board has been pushed. No task output is on GitHub."},
    "946c1684": {"claimed": "T0-T14: full project. Board marks T0-T13 as done.",
                 "observation": "The board says done, but none of the files it lists (data/, scripts/, src/) are on the pushed branch."},
    "87deb7ab": {"claimed": "T-01 to T-17: full project. Board marks T-01 and T-17 (data/standings.json, data/injuries.json) as done.",
                 "observation": "Only the coordination board has been pushed. The files listed as done are not on the pushed branch."},
    "73fdd6c4": {"claimed": "V1-V5: independent verification, in referee/ only.",
                 "observation": "This session. Edits nothing outside referee/ except its own block in COORDINATION.md."},
}


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True).stdout.strip()


def main():
    try:
        prs = json.loads(subprocess.run(["gh", "pr", "list", "--state", "all", "--limit", "100", "--json", "number,state,headRefName,title,mergedAt,url"],
                                        capture_output=True, text=True, cwd=REPO, check=True).stdout)
    except Exception:
        prs = None
    main_sha = git("rev-parse", "origin/main")
    now = datetime.datetime.now(datetime.timezone.utc)
    sessions = []
    for sid, note in NOTES.items():
        ref = f"origin/arena/{sid}-nfl1"
        sha = git("rev-parse", ref)
        if not sha or " " in sha:
            continue
        base = git("merge-base", "origin/main", ref)
        last = git("log", "-1", "--format=%cI", ref)
        last_dt = datetime.datetime.fromisoformat(last).astimezone(datetime.timezone.utc)
        files = git("ls-tree", "-r", "--name-only", ref).splitlines()
        changed = [l.split("\t") for l in git("diff", "--name-status", base, ref).splitlines()]
        modifies = sorted(p[-1] for p in changed if p[0] != "A")
        mine = sorted([p for p in (prs or []) if p["headRefName"] == f"arena/{sid}-nfl1"], key=lambda p: p["number"])
        ahead = int(git("rev-list", "--count", f"origin/main..{ref}") or 0)
        idle = int((now - last_dt).total_seconds() // 60)
        if mine and all(p["state"] == "MERGED" for p in mine) and ahead <= 1:
            state = "merged"
        elif len(files) <= 2:
            state = "claim only"
        else:
            state = "active, not merged"
        if sid == "73fdd6c4":
            state = "this session"
        sessions.append({"session": sid, "branch": f"arena/{sid}-nfl1", "branch_url": f"{GH}/tree/arena/{sid}-nfl1",
                         "tip": sha, "last_commit_utc": last_dt.strftime("%Y-%m-%d %H:%M:%S"), "minutes_since_last_commit": idle,
                         "files_on_branch": len(files), "commits_not_on_main": ahead,
                         "modifies_files_already_on_main": [m for m in modifies if not (sid == "73fdd6c4" and m == "COORDINATION.md")] if sid == "73fdd6c4" else modifies,
                         "pull_requests": [{"number": p["number"], "state": p["state"], "title": p["title"], "url": p["url"]} for p in mine],
                         "state": state, "claimed": note["claimed"], "observation": note["observation"]})
    owners = {}
    for s in sessions:
        if s["state"] in ("merged", "this session"):
            continue
        for f in s["modifies_files_already_on_main"]:
            owners.setdefault(f, []).append(s["session"])
    overlaps = [{"file": f, "modified_by_unmerged_branches": o, "file_url": f"{GH}/blob/main/{f}"} for f, o in sorted(owners.items())]
    out = {"generated_by": "referee/tools/snapshot_sessions.py", "as_of_utc": now.strftime("%Y-%m-%d %H:%M:%S"),
           "main": main_sha, "pull_request_state_available": prs is not None, "sessions": sessions, "overlaps": overlaps}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    for s in sessions:
        print(s["session"], s["state"].ljust(18), s["last_commit_utc"][11:], f"{s['minutes_since_last_commit']:>3} min", f"{s['files_on_branch']:>3} files",
              "PRs", [p["number"] for p in s["pull_requests"]], "modifies", len(s["modifies_files_already_on_main"]))
    print("overlapping files:", len(overlaps), [o["file"] for o in overlaps if len(o["modified_by_unmerged_branches"]) > 1])


if __name__ == "__main__":
    main()
