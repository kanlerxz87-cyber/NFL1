# Official injury-report snapshots (`data/snapshots/injury_report/`)

Owner: session `90c2b454-nfl1` · Task P2 · Generator: [`pipeline/capture_snapshots.py`](../../../pipeline/capture_snapshots.py) · Schedule: [`.github/workflows/capture-snapshots.yml`](../../../.github/workflows/capture-snapshots.yml)

Source: <https://www.nfl.com/injuries/> (the NFL's official weekly injury report). Every row is a
copy of a cell on that page; nothing is inferred. Blank cells stay `null`.

## Files

| File | What it is | Rule |
| --- | --- | --- |
| `heartbeat.jsonl` | One line per scheduled run: fetch time (UTC), HTTP status, SHA-256 and byte count of the raw response body, parsed row count, conflict flags, whether the parsed report changed, and the capture file written (if any). | Appended on every run, including failures. |
| `captures/<UTC time>_<hash>.json` | The parsed report at the moment of a change: every row (club, player, position, injury, practice status, game status, player link), counts, flags, and both hashes. | Written once with exclusive create. Never rewritten. |
| `changes.jsonl` | Field-level delta between consecutive captures: `added`, `removed`, or `changed` (with `from` and `to`). This is the designation history, e.g. Did Not Participate -> Limited -> Full, or Questionable -> Out. | Appended when a capture is written. |
| `manifest.json` | Index of every capture file with its file SHA-256, canonical-row SHA-256 and row count. | Append-only. `verify` re-hashes every capture against it. |
| `alerts.jsonl` | Drift and conflict alerts: fetch or parse failures, schema changes, row-count drops of more than 25%, unknown designation wording, duplicate or conflicting player rows. | Appended. |

## Two hashes, and why there are two

* **`raw_sha256`** hashes the response body exactly as received. It changes on every request
  because the page carries advertising and session markup, so it is recorded per run as evidence
  of what was fetched.
* **`canonical_sha256`** hashes the parsed rows (sorted, sorted keys). A capture file is written
  only when this changes, so the store holds designation changes rather than thousands of
  identical copies of the page.

## What is not retained

The raw HTML bytes are hashed, not stored. A replay of a past report is therefore made from the
stored parsed rows, which are the values the page printed, and the raw hash lets a reviewer confirm
the claim against a re-fetch of the same page only if the page has not moved on. This is a
deliberate size trade-off and is flagged for review.

## Pinned expectations (drift alarm)

The run fails, and writes no capture, if any of these hold: the page has no `Week N of the YYYY
Season` marker; fewer than 10 report tables are found; a report table lacks the Practice Status or
Game Status column; fewer than 100 rows are parsed; or more than 2% of rows have no player name.
Unknown designation wording is kept verbatim and flagged, never dropped or mapped.

## Terms

The row-level fields are published by the NFL on the page above. Whether a repository should keep
a copy of those rows, beyond the links, depends on the NFL's terms of use. That review is not
complete and is raised on the Flagged for Review page. Until it is complete, nothing in this
store is used as the sole evidence for a published figure without the official link beside it.
