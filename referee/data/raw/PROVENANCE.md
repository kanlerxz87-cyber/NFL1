# Provenance of `games.csv`

| Field | Value |
|---|---|
| File | `data/games.csv` from the public repository `nflverse/nfldata` |
| Repository | https://github.com/nflverse/nfldata |
| Commit | `692e5f9f8ac9f4e2ee751c630817a7c290a04390` ("Automated data update", 2026-11-12T03:45:18Z) |
| Permalink | https://github.com/nflverse/nfldata/blob/692e5f9f8ac9f4e2ee751c630817a7c290a04390/data/games.csv |
| Column documentation | https://github.com/nflverse/nfldata/blob/692e5f9f8ac9f4e2ee751c630817a7c290a04390/DATASETS.md#games |
| Retrieved | 2026-11-12 (UTC) by session 73fdd6c4 with `git clone --depth 1` |
| Status | Community-maintained dataset. It is **not** an official NFL source. The audit in `referee/analysis/audit_results.py` checks its scores against official nfl.com standings. Its betting-line columns have no official source and are unverified. |

# Provenance of `closing_lines.csv`

| Field | Value |
|---|---|
| File | `data/closing_lines.csv` from the same repository and commit as `games.csv` |
| Permalink | https://github.com/nflverse/nfldata/blob/692e5f9f8ac9f4e2ee751c630817a7c290a04390/data/closing_lines.csv |
| Use | Second copy of closing spread, total and moneyline (2006-2018) used only to cross-check the line columns of `games.csv` |
| Status | Community-maintained, **not** official, and not independent of `games.csv` (same maintainer). Agreement between the two files does not verify either one. |
