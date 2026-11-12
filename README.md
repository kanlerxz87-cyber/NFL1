# NFL1 — NFL decision-intelligence dashboard

**Live site:** https://kanlerxz87-cyber.github.io/NFL1/
**Data snapshot:** 2026 NFL regular season, Week 10, retrieved 2026-11-12 (UTC).

A clean, static GitHub Pages dashboard built from a JSON data layer. Every table row links to an official
source. If an official source publishes no value, the cell is left blank and the item is flagged on the
[Flagged for Review](flagged.html) page. No value is inferred or filled in.

## Pages

| Page | Contents |
| --- | --- |
| [index.html](index.html) | Landing dashboard, counts, decision posture |
| [executive-summary.html](executive-summary.html) | Executive summary |
| [requirements.html](requirements.html) | Full requirements inventory and analysis |
| [questions.html](questions.html) | Decision questions, known/unknown information, answers, discovery actions |
| [suggestions.html](suggestions.html) | Improvement suggestions + Review & Choose a Path gate |
| [strategy-lab.html](strategy-lab.html) | Own lines, signal research, strategies, validation gates, correlations, skill vs luck |
| [leaderboard.html](leaderboard.html) | Competition rules, rewards and the (empty) ranked board |
| [bet-types.html](bet-types.html) | Single bets, parlays, player prop combos, official risk data |
| [injuries.html](injuries.html) | Official injury report, filing policy, inactives, tracking design |
| [depth-chart.html](depth-chart.html) | 1st/2nd/3rd/4th string for offense and defense |
| [data-tables.html](data-tables.html) | Standings, derived metrics, correlations, bet facts, findings |
| [verification.html](verification.html) | Verification policy, official source registry, line-by-line audit |
| [flagged.html](flagged.html) | Flagged for Review (does not block the merge) |
| [deployment.html](deployment.html) | Pages configuration, PR, merge and deploy record |

## Rebuild and verify

```bash
python3 tools/seed_data.py              # regenerate data/*.json from transcribed official values
python3 tools/compute_correlations.py   # recompute Pearson r from official standings
python3 tools/build.py                 # generate the HTML pages and docs/*.md
python3 tools/verify.py                # source links, unverified blanks, internal links
```

`tools/verify.py` also runs in GitHub Actions on every push and pull request. GitHub Pages publishes
`main / /` (legacy build); `.nojekyll` keeps the generated HTML unchanged.

## Coordination

[COORDINATION.md](COORDINATION.md) is the shared task board for parallel agent sessions. All work in this
session stayed on the current branch with disjoint file scopes; conflicts and deviations are logged there and
on the Flagged for Review page.

## Sources

The complete registry of 25 official sources, with links for manual review, is in
[data/sources.json](data/sources.json) and on the [Verification page](verification.html). Sources include
NFL.com, NFL Football Operations, official club sites, NFL Next Gen Stats, the NIST/SEMATECH e-Handbook,
the New Jersey Division of Gaming Enforcement, GitHub Docs and the GitHub REST API.
