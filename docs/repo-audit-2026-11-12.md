# Repository audit — 2026-11-12 (session `4c043747-nfl1`)

Final integration session. This audit is a line-by-line read of the repository as it stood on
2026-11-12 (commit `c09c739`, the only commit in the published history), followed by a fresh
verification of the published numbers against the official NFL pages.

Nothing in this document is inferred. Every claim about the official pages names the page it was
read from and the retrieval window; every claim about the repository names the file it was read
from.

## 1. Inventory

| Item | Count | Where it lives | Who writes it |
| --- | --- | --- | --- |
| Tracked files | 299 | `git ls-files` | — |
| Published HTML pages | 78 | repository root, `pages/`, `docs/`, `verified-lab/`, `referee/` | 7 generators (below) |
| Python modules | 64 | `pipeline/`, `src/nfl/`, `analysis/`, `scripts/`, `tools/`, `referee/` | — |
| JSON data files | 81 | `data/` | generators and hand transcriptions |
| CSV/TSV transcriptions | 25 | `data/`, `referee/data/` | hand transcription only |
| GitHub Actions workflows | 3 | `.github/workflows/` | — |
| Commits in the published history | 1 (squashed) | `git log origin/main` | — |

### 1.1 Who writes what

| Generator | Files it writes | Inputs |
| --- | --- | --- |
| `pipeline/gen_site.py` | `index.html`, `pages/{lines,strategies,injuries,props,evidence,questions,suggestions,review,executive,models,audit}.html` | `data/model/*.json`, `pipeline/content.py` |
| `scripts/verified/build_site.py` | `pages/{data,verified-lines,analysis,decisions,verified}.html` | `data/verified/**` |
| `scripts/verified/build_availability.py` | `pages/availability.html` | `data/verified/model/availability.json` |
| `tools/build.py` | 16 pages at the repository root, `dashboard.html`, `README.md`, `docs/*.md` | `data/*.json`, `data/site_meta.json` |
| `tools/build_docs_site.py` | `docs/*.html` (13 pages) | `data/session-87deb7ab/*.json` |
| `scripts/build_site.py` (`src/nfl/sitekit.py`) | `verified-lab/*.html` (20 pages) | `data/processed/site_data.json`, `data/verified/**` |
| `referee/tools/build_site.py` | `referee/*.html` (7 pages) | `referee/data/**`, `data/*.csv` |

### 1.2 Data layers

| Layer | Refresh | Used by |
| --- | --- | --- |
| `data/model/*.json` | daily by `.github/workflows/collect-data.yml` (nflverse releases + the official nfl.com injury scrape) | the landing page, the Decision Lab |
| `data/verified/**` | hand transcription plus `analysis/*.py` | the verified-data pages, the independent sub-sites |
| `data/session-87deb7ab/*.json` | hand transcription | the `docs/` sub-site |
| `data/*.json`, `data/*.csv` | hand transcription | the governance registers |
| `data/audit/4c043747/**` | this session, two official retrievals | the official-source audit |

## 2. Irregularities found, and what was done about them

Every item below was found by reading the repository or the official pages, not by a test that was
already in place. The "status" column says what the reader can check today.

| ID | Irregularity | Evidence | Status |
| --- | --- | --- | --- |
| I-01 | **Two generators wrote `index.html`.** `tools/build.py` wrote the governance dashboard; `pipeline/gen_site.py` wrote the Decision Lab landing page. Whichever ran last won, so the published landing page depended on the order of two unrelated scripts. | `git show c09c739:index.html` vs `tools/build.py:366` | Resolved: `tools/build.py` now writes `dashboard.html`; `index.html` has one owner. |
| I-02 | **Two generators wrote `pages/lines.html`.** `pipeline/gen_site.py` (model priced against the consensus closing line) and `scripts/verified/build_site.py` (model-only, no market prices). The published page said "no official NFL odds … are reachable here" while the landing page published market lines — the site contradicted itself. | `git show c09c739:pages/lines.html` | Resolved: the verified build now writes `pages/verified-lines.html`, with a note saying where the canonical line lives. |
| I-03 | **CI never regenerated the landing page.** `.github/workflows/pages.yml` ran `scripts/verified/build_site.py`, `build_availability.py` and `normalize_nav.py`, but not `pipeline/gen_site.py`, so `index.html` and nine Decision Lab pages were never rebuilt by any workflow. | `.github/workflows/pages.yml` (before this session) | Resolved: one build script (`tools/build_site_all.py`) runs in CI and in the data refresh. |
| I-04 | **The published site lagged the published data.** `data/model/snapshot.json` was generated at 18:53:29Z on 2026-11-12, but the pages carried the stamp `2026-11-12T05:07:59+00:00` — a 13-hour gap, because the bot committed new data without rebuilding the pages. | `data/model/snapshot.json`, `git show c09c739:index.html` | Resolved: the refresh workflow rebuilds the pages and commits them with the data. |
| I-05 | **56 of 76 published pages were unreachable from the landing page** — the whole `docs/`, `verified-lab/` and `referee/` sub-sites and 15 root pages. | link graph of the published tree before this session | Resolved: the landing page publishes a site map built from the files on disk, and `tools/check_reachability.py` fails the build if any page is orphaned. 78 of 78 pages are now reachable. |
| I-06 | **Three navigation systems** (a 21-link flat bar, a grouped sidebar, and each sub-site's own bar) disagreed about what exists, and two of them pointed at pages that no generator produces. | `scripts/verified/normalize_nav.py`, `site/templates/base.html` | Resolved: one canonical 13-link bar for the landing page and the Decision Lab; the registers keep their grouped sidebar; the sub-sites keep theirs. |
| I-07 | **The committed verification report measured a page that was no longer published.** `data/verification_report.json` claimed 996 rows, of which 31 came from an `index.html` that the tools/build generator had written; the published `index.html` is a different page. The a2cea255 session recorded the same trap in `COORDINATION.md`. | `data/verification_report.json` vs `git show c09c739:index.html` | Resolved: the report is regenerated in build order and now covers 35 published pages and 1,975 rows. |
| I-08 | **The line-by-line gate only looked at 15 pages** (965 rows) and resolved relative links against the repository root, so a link on a `pages/` page would have been reported against the wrong directory. | `tools/verify.py` (before this session) | Resolved: the gate now covers 35 pages, recognises both table conventions and resolves links against each page's own directory. |
| I-09 | **Two build stamps were wall-clock timestamps**, so a rebuild could never reproduce the committed files and no reproducibility gate was possible. | `scripts/verified/build_site.py`, `tools/build_docs_site.py` | Resolved: both stamps now come from the data they publish. `python3 tools/build_site_all.py --check` proves the committed pages are exactly what the generators produce. |
| I-10 | **A stray token `EAD` sat at the top of `COORDINATION.md`**, left over from a bad edit. | `git show c09c739:COORDINATION.md` (first line) | Resolved: removed. |
| I-11 | **The official standings page does not reproduce its own split columns.** Read at ~22:05Z and ~22:25Z on 2026-11-12, `DIV`, `DIV%`, `CONF`, `CONF%`, `NON-CONF`, `STRK` and `LAST 5` printed different values for 9 clubs, with `W`, `L`, `T`, `PCT`, `PF`, `PA` and `NET` identical for all 32. | <https://www.nfl.com/standings/league/2026/reg>, both transcriptions in `data/audit/4c043747/` | Published as flag F15; only the reproducible columns are treated as verified. |
| I-12 | **The official standings page contradicts itself in 23 printed rows**: `HOME + ROAD`, `CONF + NON-CONF`, `DIV%` or `CONF%` do not reconcile with the club's own games played. | same page, same two retrievals | Published as flag F16; the page is quoted verbatim and the disagreeing cells are left blank. |
| I-13 | **Two independent transcriptions disagree** on the official `HOME`/`ROAD` columns for JAX, LV, MIN and ATL, while every club's `W-L-T` agrees. | `data/verified/standings_2026_reg.tsv` vs `data/audit/4c043747/standings_retrieval_T1.tsv` | Published as flag F17; the affected cells are left blank rather than taken from one transcription. |

### 2.1 What the official pages confirmed

| Check | Result | Source |
| --- | --- | --- |
| 32 clubs, `W-L-T`, `PCT`, `PF`, `PA`, `NET` in `data/model/snapshot.json` | 32/32 match | <https://www.nfl.com/standings/league/2026/reg> |
| Same six columns in `data/verified/standings_2026.csv` | 32/32 match | same |
| Same six columns in `data/verified/standings_2026_reg.tsv` | 32/32 match | same |
| Same six columns in `referee/data/official/nflcom_standings_2026.txt` | 32/32 match | same |
| Week 10 slate in `data/model/lines.json` | 14/14 matchups, dates and records | <https://www.nfl.com/schedules/2026/REG10> |
| Week 10 bye list in `data/verified/byes_2026.csv` | 4/4 match (CHI, DEN, PHI, TB) | same |
| 841 automated comparisons in total | 0 failures | `tools/audit_official.py` |

## 3. Repository hygiene

| Item | Finding | Status |
| --- | --- | --- |
| Merge-conflict markers in the tree | none (`git grep -n '<<<<<<<'` is empty) | clean |
| Merge-conflict markers in `README.md` | the three blocks the a2cea255 session recorded were already gone on `main` | clean |
| Test suite | 107 tests, all passing (`python3 -m pytest tests/ -q`) | passing |
| Independent verification harness | 34 checks: 29 PASS, 5 FLAG, 0 FAIL (`PYTHONPATH=src python3 -c "from nfl import verify; print(verify.run())"`) | as published |
| Reproducible build | `python3 tools/build_site_all.py --check` → "the committed pages are exactly what the generators produce" | passing |
| Broken internal links | 0 | passing |
| Orphan pages | 0 of 78 | passing |
| Table rows without an official source link | 0 of 1,975 | passing |
| Values inferred or filled in | none; unknown values are blank and flagged | clean |

## 4. Open items for the owner

These are published on the site's **Flagged for Review** page as well, and none of them blocks
publication:

1. **The official page's split columns cannot be verified** (I-11, I-12). Until the league's page
   reproduces them, only `W-L-T`, `PCT`, `PF`, `PA` and `NET` can be published as verified facts.
2. **Four clubs' `HOME`/`ROAD` remain in dispute** (I-13) between two transcriptions.
3. **No book-level prices exist**, so no edge, closing-line value or prop price can be claimed
   (flags F01, F02, F04 — unchanged from the earlier sessions).
4. **The model does not beat the closing line** out of sample: no strategy clears all eight gates.
5. **Rewards with monetary value need legal review** (flag F04).
