# Deployment and PR record

| ID | Item | Value | How checked | Official source | Verified |
| --- | --- | --- | --- | --- | --- |
| D-01 | GitHub Pages publishing source | main / '/', build_type legacy, status built | gh api repos/kanlerxz87-cyber/NFL1/pages | [S25](https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages) | yes |
| D-02 | Live site URL | https://kanlerxz87-cyber.github.io/NFL1/ | GitHub Pages API html_url | [S25](https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages) | yes |
| D-03 | Entry file requirement | index.html at the top level of the publishing source | GitHub Docs: Creating a GitHub Pages site | [S23](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site) | yes |
| D-04 | Pull request number |  | Created by the integration session before merge | [S24](https://github.com/kanlerxz87-cyber/NFL1) | NO — flagged |
| D-05 | Pull request URL |  | Created by the integration session before merge | [S24](https://github.com/kanlerxz87-cyber/NFL1) | NO — flagged |
| D-06 | Merge result |  | gh pr merge with an explicit PR number | [S24](https://github.com/kanlerxz87-cyber/NFL1) | NO — flagged |
| D-07 | Post-merge Pages build status |  | GitHub Pages builds endpoint plus a live-site fetch | [S25](https://api.github.com/repos/kanlerxz87-cyber/NFL1/pages) | NO — flagged |

Publishing rules: [GitHub Docs](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) and [creating a Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site). Configuration confirmed with `gh api repos/kanlerxz87-cyber/NFL1/pages`.
