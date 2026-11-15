#!/usr/bin/env python3
"""Render pages/snapshots.html: the ledger of official injury-report captures.

Session 90c2b454-nfl1, task P3. Reads only data/snapshots/injury_report/ (written by
pipeline/capture_snapshots.py) and renders it with the site's own page template from
pipeline/gen_site.py, so the page carries the same navigation and sidebar as every other page.

Every table row links to an official nfl.com page: the injury report itself, or the player's
nfl.com profile when the capture carries one. Nothing is inferred; a blank cell stays blank.

Usage (from the repository root):
    python3 tools/build_snapshots_page.py
"""
from __future__ import annotations

import html
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import gen_site as g  # noqa: E402  (shared page template, nav and table helpers)

STORE = ROOT / "data" / "snapshots" / "injury_report"
SOURCE_URL = "https://www.nfl.com/injuries/"
REPO = "https://github.com/kanlerxz87-cyber/NFL1/blob/main/"
OUT = "pages/snapshots.html"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def short(h: str | None, n: int = 12) -> str:
    return f"<code>{html.escape(h[:n])}</code>" if h else "&mdash;"


def yesno(v) -> str:
    return "yes" if v is True else "no" if v is False else "&mdash;"


def build() -> str:
    beats = read_jsonl(STORE / "heartbeat.jsonl")
    changes = read_jsonl(STORE / "changes.jsonl")
    alerts = read_jsonl(STORE / "alerts.jsonl")
    manifest = read_json(STORE / "manifest.json", {"captures": []})["captures"]

    # Player profile links, taken from each capture file (the page's own links).
    player_url: dict[tuple[str, str], str] = {}
    for entry in manifest:
        cap = read_json(ROOT / entry["file"], {"rows": []})
        for r in cap["rows"]:
            if r.get("player_url"):
                player_url[(r["club"] or "", r["player"])] = r["player_url"]

    latest_beat = beats[-1] if beats else {}
    latest_cap = manifest[-1] if manifest else None
    ok_runs = sum(1 for b in beats if b.get("status") == "ok")
    failed_runs = sum(1 for b in beats if b.get("status") != "ok")
    delta_rows = [(c["captured_at_utc"], d) for c in changes for d in c["delta"]]
    # Same stamp format as every other page ("+00:00"), which tools/check_committed_site.py parses.
    # The stamp is the newest of the snapshot read time and the dashboard build time, so the page
    # is never older than the data it is published beside (and a rebuild stays byte-identical).
    from datetime import datetime
    times = [datetime.fromisoformat(t.replace("Z", "+00:00"))
             for t in (latest_beat.get("fetched_at_utc"),
                       read_json(ROOT / "data" / "model" / "dashboard.json", {}).get("generated_at"))
             if t]
    generated = max(times).isoformat() if times else ""

    kpis = "".join([
        g.kpi("Latest run", latest_beat.get("fetched_at_utc", "none yet"),
              f"status: {latest_beat.get('status', 'n/a')}"),
        g.kpi("Scheduled runs recorded", str(len(beats)), f"{ok_runs} ok · {failed_runs} failed"),
        g.kpi("Immutable captures", str(len(manifest)),
              "written only when the parsed report changed"),
        g.kpi("Report rows (latest)", str(latest_cap["rows"]) if latest_cap else None,
              f"Week {latest_cap['week']} of {latest_cap['season']}" if latest_cap else "no capture yet"),
        g.kpi("Designation changes recorded", str(len(delta_rows)),
              "field-level deltas between consecutive captures"),
        g.kpi("Alerts raised", str(len(alerts)), "drift, conflict and failure alerts (see below)"),
    ])

    # 1. Run ledger, newest first.
    run_rows = []
    for b in reversed(beats):
        status = b.get("status", "")
        flags = "; ".join(b.get("flags") or []) or (b.get("error") or "&mdash;")
        cap = b.get("capture")
        cap_cell = (f'<a href="{REPO}{html.escape(cap)}" target="_blank" rel="noopener">'
                    f"{html.escape(Path(cap).name)}</a>") if cap else "&mdash;"
        run_rows.append([
            html.escape(b.get("fetched_at_utc", "")),
            f'<span class="{"ok" if status == "ok" else "fail"}">{html.escape(status)}</span>',
            html.escape(str(b.get("http_status", "&mdash;"))),
            short(b.get("raw_sha256")),
            html.escape(str(b.get("raw_bytes", "&mdash;"))),
            html.escape(str(b.get("rows", "&mdash;"))),
            html.escape(str(b.get("clubs", "&mdash;"))),
            yesno(b.get("changed")),
            cap_cell,
            html.escape(flags),
            g.src(SOURCE_URL, "nfl.com/injuries"),
        ])
    runs_html = g.table(
        ["Fetched (UTC)", "Status", "HTTP", "Raw SHA-256", "Raw bytes", "Rows", "Clubs",
         "Changed?", "Capture written", "Flags / error", "Source"],
        run_rows, cls="dense",
        note=("Every scheduled run appends a line here, including failed ones. \"Changed? no\" means the "
              "page was re-read and the parsed designations were identical to the last capture. The raw "
              "hash differs between requests because the page carries advertising and session markup; "
              "that is why the store also keeps a canonical hash of the parsed rows."))

    # 2. Designation deltas, newest first. This is the \"delta, never the level\" view.
    delta_html_rows = []
    for at, d in reversed(delta_rows[-500:]):
        club, player = d["club"], d["player"]
        link = player_url.get((club, player), SOURCE_URL)
        if d["change"] == "changed":
            what = f"{d['field'].replace('_', ' ')}"
            frm, to = html.escape(str(d["from"] or "blank")), html.escape(str(d["to"] or "blank"))
        else:
            what = d["change"]
            frm = "&mdash;" if d["change"] == "added" else html.escape(json.dumps(d.get("from", {})))
            to = html.escape(json.dumps(d.get("to", {}))) if d["change"] == "added" else "&mdash;"
        delta_html_rows.append([
            html.escape(at), html.escape(club or "blank"), html.escape(player),
            html.escape(what), frm, to,
            g.src(link, "nfl.com player" if link != SOURCE_URL else "nfl.com/injuries"),
        ])
    deltas_html = g.table(
        ["Captured (UTC)", "Club", "Player", "Field / change", "From", "To", "Source"],
        delta_html_rows, cls="dense",
        note=("Changes between consecutive captures only. A row here means the official page changed "
              "between two reads; it does not say why. Practice and game-status wording is shown exactly "
              "as the page prints it."))

    # 3. Immutable capture files.
    cap_rows = []
    for e in reversed(manifest):
        cap_rows.append([
            html.escape(e["captured_at_utc"]),
            html.escape(f"Week {e['week']} · {e['season']}"),
            html.escape(str(e["rows"])),
            f'<a href="{REPO}{html.escape(e["file"])}" target="_blank" rel="noopener">'
            f'{html.escape(Path(e["file"]).name)}</a>',
            short(e["sha256"], 16),
            short(e["canonical_sha256"], 16),
            short(e["raw_sha256"], 16),
            g.src(SOURCE_URL, "nfl.com/injuries"),
        ])
    caps_html = g.table(
        ["Captured (UTC)", "Report", "Rows", "File", "File SHA-256", "Canonical SHA-256",
         "Raw SHA-256 (page)", "Source"],
        cap_rows, cls="dense",
        note=("Each file is written once and never rewritten. The file hash lets anyone confirm a stored "
              "capture is byte-identical to the one recorded here; the canonical hash covers the parsed rows."))

    # 4. Alerts.
    alert_rows = []
    for a in reversed(alerts[-200:]):
        alert_rows.append([html.escape(a.get("at_utc", "")), html.escape(a.get("kind", "")),
                           html.escape(a.get("message", "")), g.src(SOURCE_URL, "nfl.com/injuries")])
    alerts_html = g.table(["Raised (UTC)", "Kind", "Message", "Source"], alert_rows, cls="dense",
                          note="Drift and conflict alerts. A parse that breaks its pinned expectations fails the run "
                               "and writes no capture; the failure is still recorded here.")

    body = f"""
  <section class="panel">
    <div class="kpis">{kpis}</div>
    <p class="note">What this page is: a ledger of the NFL's official injury report
    (<a href="{SOURCE_URL}" target="_blank" rel="noopener">nfl.com/injuries</a>), read every six hours
    by a scheduled job. It exists so that a designation can be replayed as it stood at each read, and so
    that changes between reads (Questionable to Out, Did Not Participate to Limited to Full) are visible.
    Rows are copied from the page; blank cells stay blank.
    Method and retention rules: <a href="{REPO}data/snapshots/injury_report/README.md" target="_blank" rel="noopener">README</a>
    · <a href="{REPO}pipeline/capture_snapshots.py" target="_blank" rel="noopener">capture code</a>
    · <a href="{REPO}.github/workflows/capture-snapshots.yml" target="_blank" rel="noopener">schedule</a>.
    Limits: the raw page bytes are hashed, not kept; the terms-of-use review for keeping row-level copies is open
    (see Flagged for Review).</p>
  </section>
  <section class="panel">
    <div class="panel-head"><h2>Designation changes between captures</h2>
      <span class="badge">delta, not level</span></div>
    {deltas_html}
  </section>
  <section class="panel">
    <div class="panel-head"><h2>Run ledger</h2><span class="badge">every scheduled read</span></div>
    {runs_html}
  </section>
  <section class="panel">
    <div class="panel-head"><h2>Immutable capture files</h2><span class="badge">append-only</span></div>
    {caps_html}
  </section>
  <section class="panel">
    <div class="panel-head"><h2>Alerts: drift, conflicts and failures</h2></div>
    {alerts_html}
  </section>
"""
    return g.page(OUT, "Official Injury Snapshots",
                  body,
                  subtitle=("A dated ledger of every official injury-report read: raw hashes, parsed "
                            "captures, and the designation changes between them."),
                  generated=generated)


def canonical_nav(content: str) -> str:
    """Swap the nav block for the canonical one from normalize_nav.py.

    gen_site's template writes root-relative links (../pages/x.html) into this
    page, which normalize_nav.py then rewrites to pages-relative links on every
    site build. Without this step the bot's capture re-render and the site build
    disagree on the nav, so the page never reaches a fixed point.
    """
    import importlib.util as ilu
    import re as _re
    spec = ilu.spec_from_file_location("_nav", ROOT / "scripts" / "verified" / "normalize_nav.py")
    nav = ilu.module_from_spec(spec)
    spec.loader.exec_module(nav)
    new = nav.build("snapshots.html", False)
    m = _re.search(r"<nav[^>]*>.*?</nav>", content, flags=_re.S)
    if not m:
        raise SystemExit("snapshots page has no nav block to canonicalise")
    return content[:m.start()] + new + content[m.end():]


def main() -> int:
    content = canonical_nav(build())
    g.write(OUT, content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
