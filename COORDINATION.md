# COORDINATION.md — Shared Task Board

Repo: `kanlerxz87-cyber/NFL1` · Default branch: `main` · Session branch: `arena/87deb7ab-nfl1`

This file is the shared coordination surface for every agent session working in this
repository. Read it before you start. Claim before you edit. Commit and push the claim
immediately.

---

## 1. How to claim a task

1. Pick a task with status `unclaimed`.
2. Write your session ID into the **Owner** column and your file scope into the **Files** column.
3. Set status to `in progress`.
4. `git add COORDINATION.md && git commit -m "claim T-xx (session-<id>)" && git pull --rebase origin <branch> && git push origin <branch>`
   — do this **before** touching any other file.
5. Never start a task another session has claimed. Keep file scopes non-overlapping.
6. If you must change a file owned by another session, log the request in §6 instead of editing it.
7. When done: fill in **Sources**, **Verification performed**, **Irregularities**, set status to `done`.
8. A claim older than 60 minutes with no commits may be taken over by another session; note the
   handoff in §5.

## 2. Status vocabulary

| Status | Meaning |
| --- | --- |
| `unclaimed` | Nobody owns it yet. |
| `in progress` | Claimed and being worked. |
| `done` | Finished, sources and verification recorded. |
| `needs review` | Published on the **Flagged for Review** page. Non-blocking. |
| `blocked` | Cannot proceed; see §6. |

## 3. Non-negotiable rules

* **No hallucinations.** Every factual value in a table must trace to a source listed in
  `docs/data-sources.html`.
* **Never infer or fill in a value.** If a value cannot be confirmed from an official source,
  leave the cell blank and raise a flag in §6 / `docs/flagged.html`.
* **Never mark a row verified** without checking it against the linked official source.
* **Shared outputs** — `docs/index.html`, the navigation, and `docs/data/sources.json` — are
  changed **only** by the final integration session (T-18).
* Small, frequent commits. `git pull --rebase` before every push.
* On merge conflict: stop, resolve **without discarding** the other session's work, log it in §5.

---

## 4. Task board

| ID | Task | Status | Owner | Files |
| --- | --- | --- | --- | --- |
| T-01 | Repository inventory and line-by-line review of pre-existing code | done | session-87deb7ab | `README.md`, `COORDINATION.md` |
| T-02 | Requirements register (full requirement list from the brief) | in progress | session-87deb7ab | `data/requirements.json`, `docs/requirements.html` |
| T-03 | Decision register — questions, known info, missing info | in progress | session-87deb7ab | `data/questions.json`, `docs/questions.html` |
| T-04 | Suggestion register + decision paths (review → choose → implement) | in progress | session-87deb7ab | `data/suggestions.json`, `docs/suggestions.html` |
| T-05 | Executive summary | in progress | session-87deb7ab | `docs/executive-summary.html` |
| T-06 | Strategy lab: origin lines, signal catalogue | in progress | session-87deb7ab | `data/strategies.json`, `docs/strategy-lab.html`, `docs/signals.html` |
| T-07 | Strategy validation gates (G0–G5) | in progress | session-87deb7ab | `data/gates.json`, `docs/strategy-lab.html` |
| T-08 | Leaderboard competition + reward structure | in progress | session-87deb7ab | `docs/strategy-lab.html` |
| T-09 | Correlation register + estimation method | in progress | session-87deb7ab | `data/correlation.json`, `docs/correlation.html` |
| T-10 | Skill-vs-luck separation methodology | in progress | session-87deb7ab | `docs/strategy-lab.html` |
| T-11 | Injury tracking + official Week 10 snapshot | in progress | session-87deb7ab | `data/injuries.json`, `docs/injury-depth.html` |
| T-12 | Offense/defense backup deficiency model (2nd/3rd/4th string) | in progress | session-87deb7ab | `docs/injury-depth.html` |
| T-13 | Source register (official vs. non-official tiering) | in progress | session-87deb7ab | `data/sources.json`, `docs/data-sources.html` |
| T-14 | Verification methodology + log | in progress | session-87deb7ab | `docs/verification.html` |
| T-15 | Flagged-for-review page | in progress | session-87deb7ab | `data/flagged.json`, `docs/flagged.html` |
| T-16 | Site scaffold: landing page, subpages, nav, CSS | in progress | session-87deb7ab | `docs/assets/css/style.css`, `docs/assets/js/*.js`, `tools/build_site.py` |
| T-17 | Official data ingestion (standings, Week 10 injury report) | done | session-87deb7ab | `data/standings.json`, `data/injuries.json` |
| T-18 | Final integration: merge, re-verify, link check, publish | unclaimed | — | `docs/**` |
| T-19 | Pull request → merge → GitHub Pages deploy verification | unclaimed | — | `COORDINATION.md` |

---

## 5. Session log

| When (UTC) | Session | Event |
| --- | --- | --- |
| 2026-11-12 | session-87deb7ab | Repository inspected. `git log` shows a single commit `5aeb599` ("Initial commit"); the only tracked file was `README.md` (6 bytes, content `# NFL1`). No code, no data, no site existed. **Finding: this is a greenfield build, not a review of an existing site.** |
| 2026-11-12 | session-87deb7ab | Claimed T-01 … T-17 (single active session; no contention observed). |
| 2026-11-12 | session-87deb7ab | Verified official sources reachable: `nfl.com/standings/`, `nfl.com/injuries/`. |
| 2026-11-12 | session-87deb7ab | **Irregularity found:** `nfl.com/teams/<team>/depth-chart` returns HTTP 404. The NFL does not publish official depth charts. Logged as F-001. |

---

## 6. Cross-scope requests and irregularities

See `docs/flagged.html` for the published, source-linked version. Summary:

| ID | Type | Summary | Status |
| --- | --- | --- | --- |
| F-001 | Data gap | No official NFL depth chart exists (`nfl.com/.../depth-chart` → 404). Depth order must be derived from snap/participation data. | needs review |
| F-002 | Data gap | The NFL publishes no official betting lines or odds. Market comparison requires a licensed/commercial feed. | needs review |
| F-003 | Feed defect | Official Week 10 injury report: the `Injuries` (body part) column is blank for 248 of 254 listed players. | needs review |
| F-004 | Feed inconsistency | Seahawks show "No Injuries Reported" while NFL.com news reports QB Sam Darnold ruled out for Week 10. Players moved to IR vanish from the injury report entirely. | needs review |
| F-005 | Timing | Snapshot taken Thursday; only Thursday/Sunday-early statuses exist. Final game statuses are due later in the week. | needs review |
| F-006 | Governance | Requirements rows are sourced from the owner's project brief, which has no public official URL. | needs review |

---

## 7. Sources used (canonical list)

Full detail with links on `docs/data-sources.html`.

| ID | Source | Tier | URL |
| --- | --- | --- | --- |
| SRC-001 | NFL.com — Official Injury Report, Week 10, 2026 | League-official | https://www.nfl.com/injuries/ |
| SRC-002 | NFL.com — 2026 Division Standings | League-official | https://www.nfl.com/standings/ |
| SRC-003 | NFL.com — News (player/lineup updates) | League-official | https://www.nfl.com/news/ |
| SRC-004 | NFL Football Operations | League-official | https://operations.nfl.com/ |
| SRC-005 | NFL Next Gen Stats | League-official | https://nextgenstats.nfl.com/ |
| SRC-006 | Genius Sports — NFL exclusive official data partnership (2023 extension, through 2027-28 season) | Primary (issuer) | https://investors.geniussports.com/news/announcements/announcements-details/2023/National-Football-League-Extends-Strategic-Partnership-with-Genius-Sports-as-Exclusive-Official-NFL-Data-and-Watch--Bet-Distribution-Partner/default.aspx |
| SRC-007 | Nevada Gaming Control Board — Gaming Revenue Report (sports pool hold %) | Government-official | https://gaming.nv.gov/about/gaming-revenue/ |
| SRC-008 | NOAA / National Weather Service — official US weather observations | Government-official | https://www.weather.gov/ |
| SRC-009 | nflverse / `nfl-data-py` (community mirror of official NFL data) | Community — NOT official | https://github.com/nflverse/nflverse |
| SRC-010 | NFL.com — 2026 regular-season schedule | League-official | https://www.nfl.com/schedules/ |
| SRC-011 | NFL.com — Transactions | League-official | https://www.nfl.com/transactions/ |
| SRC-012 | NFL Player Health & Safety | League-official | https://www.nfl.com/playerhealthandsafety/ |
