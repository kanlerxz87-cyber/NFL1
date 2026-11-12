#!/usr/bin/env python3
"""build_availability.py — renders pages/availability.html from availability.json."""
from __future__ import annotations
import json
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("bs", ROOT / "scripts/verified/build_site.py")
bs = importlib.util.module_from_spec(spec); spec.loader.exec_module(bs)

A = json.loads((ROOT / "data/verified/model/availability.json").read_text())


def main() -> int:
    t = A["totals"]
    rows = []
    for x in A["teams"]:
        if x["verified_out"] + x["verified_questionable"] == 0 and not x["reported_clean"]:
            continue
        names = ", ".join(f'{p["player"]} ({p["pos"]}, {p["status"]})' for p in x["players"]) or "—"
        rows.append([bs.esc(x["team"]), x["verified_out"], x["verified_questionable"],
                     x["offence"], x["defence"], x["specialists"],
                     bs.badge("ok", "no injuries reported") if x["reported_clean"] else bs.badge("warn", "no status stated"),
                     bs.esc(names),
                     bs.badge("danger", "unknown")])

    qb = [[bs.esc(x["team"]), bs.esc(x["change"]), bs.esc(x["status"]),
           bs.esc(x["replacement_stated"]),
           f'<a href="{bs.esc(x["article_url"])}" target="_blank" rel="noopener">NFL.com article</a>',
           bs.badge("warn", "headline-level")] for x in A["official_qb_changes"]]

    body = f"""
  <div class="grid">
    <div class="stat"><div class="label">Verified out</div><div class="value">{t["verified_out"]}</div>
      <div class="muted">players with an official "Out" game status</div></div>
    <div class="stat"><div class="label">Verified questionable</div><div class="value">{t["verified_questionable"]}</div>
      <div class="muted">officially listed as Questionable</div></div>
    <div class="stat"><div class="label">Teams reporting clean</div><div class="value">{t["teams_with_clean_report"]}</div>
      <div class="muted">official "No Injuries Reported"</div></div>
    <div class="stat"><div class="label">Depth order known</div><div class="value">0/32</div>
      <div class="muted">the NFL publishes no depth charts</div></div>
  </div>

  <div class="card" style="border-color:#f59e0b">
    <h3>{bs.badge("warn","Scope limit")} What this page can and cannot tell you</h3>
    <p><strong>Can:</strong> name every player the official Week 10 report marks Out or Questionable,
    count them by unit for each team, and confirm which teams have a clean report.</p>
    <p><strong>Cannot:</strong> tell you whether an absent player was the starter, the 3rd-string
    backup, or whether his replacement is a downgrade. Official depth charts are not published —
    the depth-chart URL returns a 404 (checked 2026-11-12) — so the "starters vs backups" column is
    deliberately blank. Filling it would mean inventing the order.</p>
    <p class="muted">{bs.esc(A["coverage_note"])}</p>
  </div>

  <h2>Verified availability by team — Week 10</h2>
  <p class="muted">Source for every row: <a href="{A["sources"]["injury_report"]}" target="_blank" rel="noopener">nfl.com/injuries</a>,
  retrieved 2026-11-12. Teams with no verified absence and no clean-report statement are omitted
  rather than shown as healthy.</p>
  {bs.table(["Team","Out","Questionable","Offence","Defence","Specialists","Official clean report","Named players (position, status)","Replacement seniority"], rows)}

  <h2>Officially stated quarterback changes</h2>
  <p class="muted">These are the only starter-replacement events an official NFL source states
  directly. They are recorded at headline level, which is a weaker level of verification than a
  published depth chart — hence the badge. Performance impact is <strong>not</strong> measured.</p>
  {bs.table(["Team","Change","Status as stated","Replacement as stated","Source","Verification level"], qb)}

  <h2>Why the deficiency model is blocked, and what unblocks it</h2>
  <div class="card">
    <table>
      <thead><tr><th>Requirement</th><th>Status</th><th>What would satisfy it</th></tr></thead>
      <tbody>
        <tr><td>Who is the starter?</td><td>{bs.badge("danger","blocked")}</td>
            <td>An official or licensed depth chart with dates; the NFL does not publish one.</td></tr>
        <tr><td>Who replaced him?</td><td>{bs.badge("warn","partial")}</td>
            <td>Snap counts / participation per game, tied to the absence.</td></tr>
        <tr><td>How much did it cost?</td><td>{bs.badge("danger","blocked")}</td>
            <td>Per-player value estimates plus the participation data above, then a validated model.</td></tr>
        <tr><td>Injury status itself</td><td>{bs.badge("ok","verified")}</td>
            <td>Done — official Week 10 statuses captured with links.</td></tr>
      </tbody>
    </table>
  </div>
"""
    stamp = "2026-11-12"
    (ROOT / "pages/availability.html").write_text(
        bs.page("Availability & Deficiencies",
                "availability.html", body,
                f"Injury-driven availability from official sources, with honest gaps · generated {stamp}"),
        encoding="utf-8")
    print("wrote pages/availability.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
