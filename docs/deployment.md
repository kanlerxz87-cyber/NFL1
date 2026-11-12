# Deployment and PR record

| ID | Item | Value | How checked | Official source | Verified |
| --- | --- | --- | --- | --- | --- |
| D-01 | GitHub Pages publishing source | main / '/', build_type legacy, status built | gh api repos/kanlerxz87-cyber/NFL1/pages | [S25](https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages) | yes |
| D-02 | Live site URL | https://kanlerxz87-cyber.github.io/NFL1/ | GitHub Pages API html_url | [S25](https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages) | yes |
| D-03 | Entry file requirement | index.html at the top level of the publishing source | GitHub Docs: Creating a GitHub Pages site | [S23](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site) | yes |
| D-04 | Pull request number | 12 | gh pr create --base main --head arena/80731db4-nfl1; gh pr view 12 | [S24](https://github.com/kanlerxz87-cyber/NFL1) | yes |
| D-05 | Pull request URL | https://github.com/kanlerxz87-cyber/NFL1/pull/12 | gh pr view 12 --json url | [S24](https://github.com/kanlerxz87-cyber/NFL1) | yes |
| D-06 | Merge result | MERGED 2026-11-12T05:01:26Z, commit 4904617614a1391f3fb492990877704c3f694c7d | gh pr merge 12 --merge; gh pr view 12 --json state,mergedAt,mergeCommit | [S24](https://github.com/kanlerxz87-cyber/NFL1) | yes |
| D-07 | Post-merge Pages build status | built (commit 4904617); Actions deploy run 43158573277 success; live site fetched and read | gh api repos/kanlerxz87-cyber/NFL1/pages/builds; gh run view 43158573277; fetch of live URL | [S25](https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages) | yes |

Publishing rules: [GitHub Docs](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) and [creating a Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site). Configuration confirmed with `gh api repos/kanlerxz87-cyber/NFL1/pages`.
