# NFL1 — NFL decision-intelligence dashboard

**Live site:** https://kanlerxz87-cyber.github.io/NFL1/
**Data snapshot:** 2026 NFL regular season, Week 10, retrieved 2026-11-12 (UTC).

A clean, static GitHub Pages dashboard built from a JSON data layer. Every table row links to an official
source. If an official source publishes no value, the cell is left blank and the item is flagged on the
[Flagged for Review](flagged.html) page. No value is inferred or filled in.

## The site

| Section | Entry point | What it holds |
| --- | --- | --- |
| Landing dashboard | [index.html](index.html) | Season state, this week's own lines, leaderboard head, availability pressure, decisions requested, and a map of every published page |
| Decision Lab | [pages/lines.html](pages/lines.html) | Own lines, strategy lab, injuries & depth, player props, official-source audit, questions, suggestions, decision register, evidence, flags, executive summary |
| Governance registers | [dashboard.html](dashboard.html) | Requirements inventory, decision questions, suggestions & paths, strategy lab, leaderboard rules, bet types, injuries, depth charts, data tables, verification policy, flags, deployment record |
| Independent build | [docs/index.html](docs/index.html) | Session `87deb7ab`: 13 pages built from its own data namespace |
| Independent verification | [verified-lab/index.html](verified-lab/index.html) | Session `a2cea255`: 20 pages, a 34-check harness and a hand transcription of the official pages |
| Independent audit | [referee/index.html](referee/index.html) | Session `73fdd6c4`: replication, luck and line audits against the official pages |
| Preserved earlier dashboard | [legacy-site.html](legacy-site.html) | The first session's dashboard, kept verbatim (historical) |

## Rebuild and verify

One command builds every published page, in a fixed order, from the data files:

```bash
python3 tools/build_site_all.py            # build
python3 tools/build_site_all.py --check    # build, then fail if the committed pages differ
```

The gates that run in CI on every push and pull request:

```bash
python3 tools/compute_correlations.py      # recompute Pearson r from the official standings
python3 tools/verify_combined.py           # re-verify the merged CSV snapshots and every local link
python3 scripts/verified/validate_verified.py   # the official data must reconcile
python3 tools/audit_official.py            # audit every published number against nfl.com
python3 tools/check_reachability.py         # no broken link, no orphan page, every source-linked row has a link
python3 tools/verify.py                    # every table row has an official source link; blanks stay blank
```

`tools/build_site_all.py` owns the file map, so exactly one generator writes each published file:
`pipeline/gen_site.py` writes the landing page and the Decision Lab, `tools/build.py` writes the
governance registers and `dashboard.html`, `scripts/verified/build_site.py` writes the verified-data
pages, and the three independent sessions keep their own sub-sites. The daily data refresh
(`.github/workflows/collect-data.yml`) rebuilds the pages and commits the data and the pages
together, so a page can never show numbers the repository does not also hold.

## Official-source audit

`data/audit/4c043747/` holds two verbatim transcriptions of the official league standings page,
taken about 20 minutes apart, plus the official Week 10 schedule. `tools/audit_official.py` compares
them with every standings table published in this repository and with the published Week 10 slate,
then publishes the result on [pages/audit.html](pages/audit.html). Only a column that was identical
in both retrievals *and* consistent with the club's own record is treated as a verified value.

## Combined site (final integration)

`main` already contained a dashboard produced by earlier parallel sessions. Both site generations are
published: this dashboard at `/`, and the earlier dashboard preserved at
[legacy-site.html](legacy-site.html) with its `pages/` subpages, `styles.css`, `assets/` and
`data/*.csv` snapshots. The pre-integration coordination board and README are preserved in
`docs/COORDINATION-archive-main.md` and `docs/README-session-533256e1.md`. See
[integration.html](integration.html) for the line-by-line combined-data check and the local link audit
across both site generations. Residual combined-site issues are published as flags F25–F29 on
[flagged.html](flagged.html).

## Coordination

[COORDINATION.md](COORDINATION.md) is the shared task board for parallel agent sessions. All work in this
session stayed on the current branch with disjoint file scopes; conflicts and deviations are logged there and
on the Flagged for Review page.

## Sources

The complete registry of 25 official sources, with links for manual review, is in
[data/sources.json](data/sources.json) and on the [Verification page](verification.html). Sources include
NFL.com, NFL Football Operations, official club sites, NFL Next Gen Stats, the NIST/SEMATECH e-Handbook,
the New Jersey Division of Gaming Enforcement, GitHub Docs and the GitHub REST API.
