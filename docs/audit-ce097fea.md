# Repository audit — session `ce097fea-nfl1`, 2026-11-16

Scope: read the repository's committed data line by line and check it against the official page it
claims to come from. Anything that cannot be confirmed from an official source is left blank and
flagged. Every claim below carries the page that settles it.

Live output of this audit: <https://kanlerxz87-cyber.github.io/NFL1/console/>

---

## 1. What the repository is

`kanlerxz87-cyber/NFL1` is not one site. It is six overlapping generations of the same project,
each built by a different session, each with its own navigation and its own copies of the numbers:

| Generation | Entry point | Built by |
|---|---|---|
| Root site | `index.html` + `pages/` | `pipeline/gen_site.py` |
| Decision dashboard | `web/dashboard.html` | `tools/build_dashboard.py` |
| Second dashboard | `docs/index.html` | `tools/build_docs_site.py` |
| Independent verification lab | `verified-lab/` | `scripts/verified/` |
| Large-sample research build | `research/` | `s9cb/site.py` |
| Decision room, review room, strategy competition, pre-registration | `room/`, `review-room/`, `strat/`, `prereg/` | various |
| **Decision Console (this session)** | `console/index.html` | `console/build.py` |

No generation was deleted or rewritten by this session. A seventh was added rather than a merge
attempted, because seven other sessions had open pull requests at the time and merging them blind
would have destroyed work nobody had reviewed. Recorded as flag **CE-08**.

---

## 2. Line-by-line checks performed

### 2.1 Official standings — 32 of 32

Read from <https://www.nfl.com/standings/league/2026/REG> and
<https://www.nfl.com/standings/conference/2026/REG> on 2026-11-16. All 32 clubs transcribed to
`data/session-ce097fea/official_standings_2026-11-16.json`.

Internal consistency of the official table, as published:

| Check | Value | Result |
|---|---|---|
| Total wins | 148 | equals total losses (148) |
| Total ties | 2 | one tied game, counted once per club |
| Total points for | 6,880 | equals total points against (6,880) |
| Games represented | 149 | 160 possible minus 11 bye slots |

The table is arithmetically self-consistent. (Three weeks earlier another session found three cells
where nfl.com contradicted its own arithmetic; none of those is present today.)

### 2.2 Reconciliation — 32 of 32 clubs

Recomputed the standings from every game result in `data/s9cb/games.csv` plus the 12 Week-10 finals
this session transcribed from <https://www.nfl.com/schedules/2026/REG11>, then compared W/L/T/PF/PA
cell by cell with the official table.

| Basis | Clubs reconciling |
|---|---|
| Feed alone | 8 of 32 |
| Feed + this session's official Week-10 transcription | **32 of 32** |

The 8 that reconcile from the feed alone are the four clubs on bye (CHI, DEN, PHI, TB), the two in
the Monday-night fixture (LAC, BAL), and two others whose Sunday results happened not to move them.
Reproduce with `python3 data/session-ce097fea/reconcile.py`; it exits non-zero on any mismatch.

### 2.3 Official injury report — 347 of 347

Re-read the whole Week 10 report at <https://www.nfl.com/injuries/league/2026/reg10> (all 8 rendered
chunks) and compared with the capture committed on 2026-11-15:

| Check | Result |
|---|---|
| Rows | 347 against 347 |
| Clubs | 28 (four clubs on bye: CHI, DEN, PHI, TB) |
| Fixtures | 14 |
| "No injuries reported" sections on the page | 0 |
| Rows present on only one side | 0 |
| Field differences on shared rows | 0 |
| sha256 of this session's rows file | `9fe77d36a25618542553e690a5a44dac3449769b56e45cccd711cb1e2669cd5f` |

That hash is **identical** to the one already recorded in `data/capture/manifest.json`. The committed
2026-11-15 capture is therefore faithful, and the official page did not move in the 24 hours between
the two reads. Files: `data/session-ce097fea/capture/injury_rows_2026-11-16.tsv`,
`games_reg10_2026-11-16.tsv`, `manifest_2026-11-16.json`.

Game-status distribution as published: Out 70, Questionable 90, Doubtful 11, no designation 176.

### 2.4 Lions game-status designations

`Kerby Joseph`, `Cade Mays` and `D.J. Reed` are published with a blank game-status cell in a hand copy
still committed inside the repository. The official page lists all three as **Out**. Re-confirmed on
2026-11-16. The blank is wrong; the 347-row capture supersedes that file.

### 2.5 Week 11 availability

<https://www.nfl.com/injuries/league/2026/reg11> serves the Week 10 page, and the week selector offers
Week 1 to Week 10 only. There is no official forward-looking availability data today, so no Week-11
line may carry an injury feature. Flag **CE-05**.

### 2.6 A verified non-issue

`Myles Garrett` appears in the Los Angeles Rams section of the injury report, which looks like a
mis-scrape. The official page itself lists him there, with "Knee, Not injury related - resting
player". Not a capture error. Flag **CE-09**, closed.

---

## 3. Irregularities found

Full table with the settling link for each: <https://kanlerxz87-cyber.github.io/NFL1/console/flagged.html>

| ID | Severity | What it is |
|---|---|---|
| CE-01 | high | The results feed is 12 games behind the official schedule. Snapshot taken 2026-11-15 13:21 UTC, before the Week 10 Sunday kickoffs. |
| CE-02 | medium | Injury captures carry a date but no clock time, and hold rendered text rather than raw bytes. |
| CE-03 | medium | Club codes: nfl.com prints `AZ` and `LA`; the repository stores both `AZ`/`ARI` and `LA`/`LAR`. |
| CE-04 | medium | `data/standings.json` is stale — Buffalo 7-1 there, 8-1 official today. |
| CE-05 | info | Week 11 injury report is not published. |
| CE-06 | medium | The Week 10 report is still live on the Monday after the games; it can be misread as forward-looking. |
| CE-07 | low | No venue has been transcribed from an official game-centre page. |
| CE-08 | low | Seven pull requests from other sessions are open; this session did not merge them. |

Carried from earlier sessions and still open: CAP-01 (no row-count pin on the injury scraper),
CAP-03 (a committed 254-row hand copy is stale), CAP-05 (club codes), R26-01 (a strategy's rule and
its results in the same commit), LB-01 (backtest figures printed on the landing leaderboard).

---

## 4. What this session did not check

Stated so the audit is not read as more complete than it is.

- Every page of the six earlier site generations was not re-verified cell by cell. Spot checks only.
- The ratings, own lines and win probabilities in `data/s9cb/lines.json` and `data/model/lines.json`
  were not recomputed. Their inputs come from a hash-pinned feed, but the model code was not re-run.
- The depth register (`data/depth/official_register.tsv`) was not re-read against the 32 club pages.
- Contents of the seven open pull requests were not reviewed.
- Historical injury rows in `data/s9cb/injuries.csv` (56,829 rows) were counted, not verified.
- The seven brief lines marked *not assessed* in the readiness register were not investigated.

---

## 5. Files added by this session

| Path | Contents |
|---|---|
| `data/session-ce097fea/capture/injury_rows_2026-11-16.tsv` | 347 official Week 10 injury rows |
| `data/session-ce097fea/capture/games_reg10_2026-11-16.tsv` | 14 fixtures, results, per-game official URL |
| `data/session-ce097fea/capture/manifest_2026-11-16.json` | capture provenance, counts, sha256 |
| `data/session-ce097fea/official_standings_2026-11-16.json` | 32 clubs, official |
| `data/session-ce097fea/injury_capture_delta.json` | mechanical delta against the 11-15 capture |
| `data/session-ce097fea/standings_verification_2026-11-16.json` | feed-only comparison and freshness gap |
| `data/session-ce097fea/standings_reconciliation_2026-11-16.json` | all 32 clubs, official vs recomputed |
| `data/session-ce097fea/reconcile.py` | recomputes the reconciliation; exits non-zero on a mismatch |
| `console/build.py`, `console/verify.py`, `console/style.css` | the sub-site generator, its gate, its stylesheet |
| `console/data/*.json` | requirements, questions, suggestions, decisions, flags registers |
| `console/*.html` | 10 generated pages |
| `docs/audit-ce097fea.md` | this file |
