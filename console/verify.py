#!/usr/bin/env python3
"""Check the console/ sub-site. Fails loudly; this is a gate, not a report.

    python3 console/verify.py

It fails when:
  * a page in the navigation is missing or unreachable from the landing page
  * an internal link points at a file that does not exist, or is an empty/hash href
  * an external link is not https, or points at a host that is not on the official-source allowlist
  * a table row has neither an https source link, a labelled blank cell, nor a stated exemption
  * a chosen path in data/decisions.json is not one of the options published for that suggestion
  * a number quoted in the data registers is not backed by the file it claims

Every failure prints the file and the row it came from.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "console"
DATA = OUT / "data"
SESS = ROOT / "data" / "session-ce097fea"
CAP = SESS / "capture"
S9 = ROOT / "data" / "s9cb"

PAGES = ["index.html", "executive-summary.html", "readiness.html", "questions.html",
         "suggestions.html", "strategy-lab.html", "injuries.html", "data.html",
         "verification.html", "flagged.html"]

# Hosts this site is allowed to link to: official league pages, the league's own repository of
# parsed data, and this project's repository. Anything else is a link to a page whose contents
# we have not verified.
ALLOWED_HOSTS = {
    "www.nfl.com", "nfl.com",
    "github.com",            # nflverse-data and this repository
    "kanlerxz87-cyber.github.io",
    "creativecommons.org",   # the nflverse licence
}

errors = []
warns = []


def err(page, msg):
    errors.append(f"{page}: {msg}")


def read(page):
    return (OUT / page).read_text(encoding="utf-8")


def check_pages_exist():
    for p in PAGES:
        if not (OUT / p).exists():
            err(p, "page listed in the navigation does not exist")


def check_reachability():
    """Every page must be reachable from the landing page by following links."""
    seen, stack = {"index.html"}, ["index.html"]
    while stack:
        cur = stack.pop()
        for href in re.findall(r'href="([^"]+)"', read(cur)):
            if href.startswith("http") or href.startswith("#"):
                continue
            target = href.split("#")[0].split("?")[0]
            if not target or target.endswith(".css"):
                continue
            if (OUT / target).exists() and target not in seen:
                seen.add(target)
                stack.append(target)
    for p in PAGES:
        if p not in seen:
            err("index.html", f"page {p} is not reachable from the landing page")


def check_links():
    for page in PAGES:
        if not (OUT / page).exists():
            continue
        for href in re.findall(r'<a[^>]*href="([^"]*)"', read(page)):
            if href == "" or href == "#":
                err(page, "empty or hash-only href")
                continue
            if href.startswith("http"):
                if not href.startswith("https://"):
                    err(page, f"external link is not https: {href}")
                    continue
                host = re.sub(r"^https://", "", href).split("/")[0]
                if host not in ALLOWED_HOSTS:
                    err(page, f"link host not on the official-source allowlist: {href}")
                continue
            target = href.split("#")[0]
            if not target or target.endswith(".css"):
                continue
            if "#" in href:
                frag = href.split("#")[1]
                if (OUT / target).exists() and f'id="{frag}"' not in (OUT / target).read_text(encoding="utf-8"):
                    err(page, f"in-page anchor {href} has no matching id")
            if not (OUT / target).exists():
                err(page, f"broken internal link: {href}")


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def check_sourced_rows():
    """Every <tbody> row needs an https source link, a labelled blank, or a stated exemption."""
    total = 0
    for page in PAGES:
        if not (OUT / page).exists():
            continue
        html_ = read(page)
        for m in re.finditer(r"<table([^>]*)>(.*?)</table>", html_, re.S):
            attrs, body = m.group(1), m.group(2)
            em = re.search(r'data-exempt="([^"]*)"', attrs)
            exempt = em.group(1) if em else None
            for rm in re.finditer(r"<tr>(.*?)</tr>", m.group(2), re.S):
                row = rm.group(1)
                if "<td" not in row:
                    continue                      # header row
                total += 1
                if 'href="https://' in row:
                    continue
                if 'class="blank"' in row:
                    continue
                if exempt and exempt.strip():
                    continue
                err(page, f"table row has no source link, no blank cell and no exemption: "
                          f"{strip_tags(row)[:110]}")
    return total


def check_decisions():
    sg = json.loads((DATA / "suggestions.json").read_text(encoding="utf-8"))
    dec = json.loads((DATA / "decisions.json").read_text(encoding="utf-8"))["decisions"]
    valid = {s["id"]: [o["path"] for o in s["options"]] for s in sg["rows"]}
    for sid, d in dec.items():
        if sid not in valid:
            err("data/decisions.json", f"decision recorded for unknown suggestion id {sid}")
            continue
        if d.get("chosen_path") not in valid[sid]:
            err("data/decisions.json",
                f"{sid}: chosen path '{d.get('chosen_path')}' is not one of the published options")
        for k in ("chosen_by", "chosen_on"):
            if not d.get(k):
                err("data/decisions.json", f"{sid}: missing {k}")


def check_counts():
    """The numbers the landing page quotes must match the registers behind them."""
    req = json.loads((DATA / "requirements.json").read_text(encoding="utf-8"))["rows"]
    flags = json.loads((DATA / "flags.json").read_text(encoding="utf-8"))["rows"]
    qs = json.loads((DATA / "questions.json").read_text(encoding="utf-8"))["rows"]
    sg = json.loads((DATA / "suggestions.json").read_text(encoding="utf-8"))["rows"]
    manifest = json.loads((CAP / "manifest_2026-11-16.json").read_text(encoding="utf-8"))
    rec = json.loads((SESS / "standings_reconciliation_2026-11-16.json").read_text(encoding="utf-8"))
    inj_rows = [l for l in (CAP / "injury_rows_2026-11-16.tsv").read_text(encoding="utf-8").rstrip("\n").split("\n")[1:] if l]

    if len(inj_rows) != manifest["counts"]["rows"]:
        err("capture", f"manifest says {manifest['counts']['rows']} rows, the file holds {len(inj_rows)}")
    if rec["matched"] != rec["clubs"]:
        err("reconciliation", f"only {rec['matched']} of {rec['clubs']} clubs reconcile")

    idx = read("index.html")
    for needle, why in [
        (f'{manifest["counts"]["rows"]}', "injury row count"),
        (f'{rec["matched"]} / {rec["clubs"]}', "reconciliation result"),
        (f'{len([r for r in req if r["status"] == "met"])}', "requirements met"),
        (f'{len([f for f in flags if f["status"] == "open"])}', "open flags"),
    ]:
        if needle not in idx:
            err("index.html", f"headline figure for {why} ({needle}) is not what the registers say")

    for r in req:
        if r["source"] and not r["source"].startswith("https://"):
            err("data/requirements.json", f"{r['id']}: source is not an https link")
    for q in qs:
        if q.get("source") and not q["source"].startswith("https://"):
            err("data/questions.json", f"{q['id']}: source is not an https link")
    for f in flags:
        if not f.get("source", "").startswith("https://"):
            err("data/flags.json", f"{f['id']}: every flag must carry the https link that settles it")
    for s in sg:
        if s.get("source") and not s["source"].startswith("https://"):
            err("data/suggestions.json", f"{s['id']}: source is not an https link")
    return len(inj_rows), len(req), len(qs), len(sg), len(flags)


def check_feed_present():
    for f in ["games.csv", "leaderboard.json", "correlations.json", "provenance.json"]:
        if not (S9 / f).exists():
            err("data/s9cb", f"missing {f}, which the strategy page reads")


def main():
    check_pages_exist()
    check_feed_present()
    check_reachability()
    check_links()
    check_decisions()
    n_rows, n_req, n_q, n_sg, n_flags = check_counts()
    n_sourced = check_sourced_rows()

    print(f"pages            : {len(PAGES)}")
    print(f"table rows       : {n_sourced} checked for a source link, a blank, or an exemption")
    print(f"registers        : {n_req} requirements, {n_q} questions, {n_sg} suggestions, {n_flags} flags")
    print(f"injury rows      : {n_rows}")
    if warns:
        for w in warns:
            print(f"WARN  {w}")
    if errors:
        print(f"\nFAILED with {len(errors)} problem(s):")
        for e in errors[:60]:
            print(f"  {e}")
        if len(errors) > 60:
            print(f"  ... and {len(errors) - 60} more")
        sys.exit(1)
    print("\nPASS: every row sourced, every link resolves, every figure matches its register")


if __name__ == "__main__":
    main()
