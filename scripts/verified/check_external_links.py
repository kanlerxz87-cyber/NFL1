#!/usr/bin/env python3
"""
check_external_links.py — report dead external source links.

Motivation: a static-site build gate that only checks internal links let three dead
`operations.nfl.com` URLs survive on `main` until an independent review caught them.

Design constraints:
  * An unreachable site is NOT treated as a fabricated value. The check reports status and
    only fails on a definite negative answer (HTTP 404/410) or an explicit redirect to a
    404 page — never on timeouts, DNS failures or 403, which are environment problems.
  * Offline mode (`--offline`) skips network entirely and just inventories the URLs, so CI
    without outbound access still exercises the parse path.

Exit codes: 0 = clean or inconclusive, 1 = at least one link returned 404/410.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATTERN = re.compile(r'href="(https?://[^"]+)"')
UA = {"User-Agent": "Mozilla/5.0 (compatible; NFL1-link-check/1.0)"}
DEAD = {404, 410}
IGNORE_PREFIX = ("https://github.com/kanlerxz87-cyber/NFL1",)


def collect() -> dict[str, set[str]]:
    urls: dict[str, set[str]] = {}
    for p in [ROOT / "index.html", *sorted((ROOT / "pages").glob("*.html"))]:
        for u in PATTERN.findall(p.read_text(encoding="utf-8")):
            if u.startswith(IGNORE_PREFIX):
                continue
            urls.setdefault(u, set()).add(p.name)
    return urls


def probe(url: str, timeout: float) -> tuple[int | None, str]:
    req = urllib.request.Request(url, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(4000) if r.status == 200 else b""
            if b"404 - FLAG ON THE PLAY" in body or b"404 - Flag on the Play" in body:
                return 404, "served an NFL.com 404 page"
            return r.status, "ok"
    except urllib.error.HTTPError as e:
        return e.code, f"HTTP {e.code}"
    except Exception as e:                                    # noqa: BLE001
        return None, f"unreachable ({type(e).__name__})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="inventory only, no network calls")
    ap.add_argument("--timeout", type=float, default=12.0)
    args = ap.parse_args()

    urls = collect()
    print(f"external source links found: {len(urls)}")
    if args.offline:
        for u in sorted(urls):
            print("  (not probed)", u)
        print("offline mode: no network checks performed")
        return 0

    dead, unknown = [], []
    for u in sorted(urls):
        status, note = probe(u, args.timeout)
        pages = ", ".join(sorted(urls[u]))
        if status in DEAD or (status == 404):
            dead.append((u, note, pages))
            print(f"  DEAD {status} {u}  [{pages}]")
        elif status is None or status >= 400:
            unknown.append((u, note))
            print(f"  SKIP {note} {u}")
        else:
            print(f"  ok   {status} {u}")

    print(f"\nsummary: {len(urls)} links, {len(dead)} dead, {len(unknown)} unverifiable from here")
    if dead:
        print("\nDEAD LINKS (must be replaced before publishing):")
        for u, note, pages in dead:
            print(f" - {u}  ({note})  used in: {pages}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
