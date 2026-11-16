#!/usr/bin/env python3
"""Render schedule_announcement/index.html from data/schedule_announcement/schedule_announcement.json.

The page shows the league's dated schedule announcement beside the live Week 11 schedule page.
Every table row carries an official https link. Nothing is inferred: values come only from the
JSON, which records what was read from each official URL and when.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "schedule_announcement" / "schedule_announcement.json"
OUT = ROOT / "schedule_announcement" / "index.html"


def esc(v):
    return html.escape(str(v), quote=True)


def link(url, label=None):
    return f'<a href="{esc(url)}" rel="noopener">{esc(label or url)}</a>'


def build_html(d):
    a = d["announcement"]
    live = d["live_schedule"]
    ann_rows = "\n".join(
        f"""<tr><td>{esc(r['id'])}</td><td>{esc(r['what'])}</td>
<td>{esc(r['printed'])}{('<br><small class="muted">Derived: ' + esc(r['derived_utc']) + ' UTC. ' + esc(r['derived_note']) + '</small>') if r.get('derived_utc') else ''}</td>
<td>{link(r['source_url'], 'official link')}</td></tr>"""
        for r in a["rows"]
    )
    fixture_rows = "\n".join(
        f"""<tr><td>{esc(f['matchup'])}{('<br><small class="muted">' + esc(f['note']) + '</small>') if f.get('note') else ''}</td>
<td>{esc(f['day'])}</td><td>{esc(f['kickoff_et'])} ET</td><td>{esc(f['network'])}</td>
<td>{link(f['official_url'], 'game page')}</td></tr>"""
        for f in live["fixtures"]
    )
    bye = ", ".join(live["teams_on_bye"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Schedule announcement beside the live schedule | NFL1</title>
<style>
:root {{ --ink:#1b2430; --muted:#5b6573; --line:#dfe4ea; --bg:#f6f8fa; --accent:#1f5fbf; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif; color:var(--ink); background:var(--bg); line-height:1.45; }}
header {{ background:#fff; border-bottom:1px solid var(--line); padding:16px 24px; }}
header a {{ color:var(--accent); text-decoration:none; font-size:14px; }}
h1 {{ font-size:22px; margin:6px 0 4px; }}
main {{ padding:20px 24px 40px; max-width:1280px; margin:0 auto; }}
.muted {{ color:var(--muted); }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; align-items:start; }}
@media (max-width:900px) {{ .grid {{ grid-template-columns:1fr; }} }}
.card {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:16px; }}
.card h2 {{ font-size:17px; margin:0 0 6px; }}
table {{ width:100%; border-collapse:collapse; font-size:14px; margin-top:8px; }}
th, td {{ text-align:left; padding:8px 6px; border-top:1px solid var(--line); vertical-align:top; }}
th {{ color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.03em; }}
.kpi {{ display:flex; gap:12px; flex-wrap:wrap; margin:12px 0; }}
.kpi div {{ background:var(--bg); border:1px solid var(--line); border-radius:6px; padding:8px 12px; font-size:13px; }}
.kpi b {{ display:block; font-size:18px; }}
.note {{ font-size:13px; color:var(--muted); margin-top:10px; }}
.unverified {{ color:#8a5a00; }}
</style></head>
<body>
<header>
  <a href="../index.html">&larr; NFL1 home</a>
  <h1>Schedule announcement, beside the live schedule page</h1>
  <div class="muted">Task IN-31 · captured {esc(d['captured_at_utc'])} · every row links to an official NFL page</div>
</header>
<main>
<div class="kpi">
  <div>Announced release<b>Thu 14 May 2026, 8 p.m. ET</b></div>
  <div>Announcement issued<b>{esc(a['issued_date'])}</b></div>
  <div>Live Week {live['week']} fixtures<b>{len(live['fixtures'])}</b></div>
  <div>Teams on bye<b>{len(live['teams_on_bye'])}</b></div>
</div>
<div class="grid">
  <section class="card">
    <h2>Left: the league's dated announcement</h2>
    <div class="muted">{esc(a['title'])}</div>
    <div class="muted">Official release: {link(a['official_url'], 'media.nfl.com')} · mirror: {link(a['mirror_url'], 'nfl.com/news')}</div>
    <table>
      <thead><tr><th>ID</th><th>Item</th><th>Printed in the release</th><th>Source</th></tr></thead>
      <tbody>
{ann_rows}
      </tbody>
    </table>
    <p class="note">Only the printed text is shown. The UTC conversion in A1 is arithmetic on the printed Eastern time and is marked as derived.</p>
  </section>
  <section class="card">
    <h2>Right: the live schedule page (Week {live['week']}, {live['season']})</h2>
    <div class="muted">Read from {link(live['official_url'], 'nfl.com/schedules/2026/by-week/week-11')} on {esc(d['captured_at_utc'][:10])} UTC, all {live['chunks_read']} chunks.</div>
    <table>
      <thead><tr><th>Matchup</th><th>Day</th><th>Kickoff</th><th>Network</th><th>Source</th></tr></thead>
      <tbody>
{fixture_rows}
      </tbody>
    </table>
    <p class="note">Teams on bye, printed on the same page: {esc(bye)} (source: {link(live['teams_on_bye_source_url'], 'Week 11 schedule')}).</p>
    <p class="note">Cross-check: {esc(d['cross_check']['result'])}. Compared against {esc(d['cross_check']['against'])}.</p>
  </section>
</div>
<p class="note unverified">What is not shown: broadcast-partner game announcements (A2) and the international-game reveal on 13 May (A3) are announced dates only. This page does not verify whether they happened; the live page read is the evidence for the schedule itself.</p>
</main>
</body></html>
"""


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_html(d), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
