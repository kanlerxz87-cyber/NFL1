#!/usr/bin/env python3
"""build_reserve_site.py — render the transactions/reserve sub-site from the stored register.

Session 1d824ec2-nfl1 (task V6). Outputs:

    reserve/index.html   what was captured, when, per category and month; the per-club reserve
                         panel; the "absent from the weekly report, present on a reserve list"
                         panel; the depth-staleness panel; the method and the limits.
    reserve/rows.html    every captured row, newest first, each with its official link.

Every value on the two pages is read from a file in `data/reserve/` (which is itself rebuilt only
from the immutable captures) or from the injury report the pipeline already stores. Nothing is
typed in here, and no timestamp comes from the clock: the same inputs always produce the same
bytes, so a committed page can be proven to be the current build.

Run:  python3 tools/build_reserve_site.py           (writes the two pages)
      python3 tools/build_reserve_site.py --check   (fails if the committed pages differ)
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "reserve"
OUT_DIR = ROOT / "reserve"

CSS = """
:root{--ink:#17202a;--muted:#5b6672;--line:#d9dee5;--bg:#f6f8fa;--ok:#1d6b3a;--warn:#8a5a00;--bad:#9b1c1c;--link:#0b5cad}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#fff;border-bottom:1px solid var(--line);padding:14px 22px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between}
header a{color:var(--link);text-decoration:none;font-weight:600}header nav a{margin-left:14px;font-weight:500}
main{max-width:1180px;margin:0 auto;padding:22px}
h1{font-size:24px;margin:4px 0 6px}h2{font-size:18px;margin:28px 0 8px}
.lede{color:var(--muted);max-width:900px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.kpi{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--muted);font-size:13px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden;font-size:14px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#eef2f6;font-weight:600;position:sticky;top:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.wrap{overflow-x:auto;max-height:620px;border-radius:8px}
.flag{border-left:4px solid var(--warn)}.open{color:var(--warn);font-weight:600}
.blank{color:var(--muted);font-style:italic}
.note{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 14px;color:var(--muted)}
footer{color:var(--muted);font-size:13px;margin:30px 0 10px}
code{background:#eef2f6;padding:1px 4px;border-radius:4px}
"""


def esc(v) -> str:
    if v is None or v == "":
        return '<span class="blank">not printed</span>'
    return html.escape(str(v))


def link(url: str, label: str | None = None) -> str:
    if not url:
        return '<span class="blank">no source link</span>'
    return (f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">'
            f'{html.escape(label or url)}</a>')


def kpi(label: str, value, note: str = "", tone: str = "") -> str:
    style = f' style="border-left:4px solid var(--{tone})"' if tone else ""
    return (f'<div class="kpi"{style}><b>{esc(value)}</b><span>{html.escape(label)}</span>'
            f'{f"<span>{html.escape(note)}</span>" if note else ""}</div>')


def table(headers: list[tuple[str, str]], rows: list[list[str]], caption: str = "") -> str:
    head = "".join(f'<th class="{c}">{html.escape(h)}</th>' for h, c in headers)
    body = []
    for r in rows:
        body.append("<tr>" + "".join(f'<td class="{c}">{cell}</td>'
                                     for cell, (_h, c) in zip(r, headers)) + "</tr>")
    cap = f"<caption>{html.escape(caption)}</caption>" if caption else ""
    return (f'<div class="wrap"><table>{cap}<thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body) or "<tr><td colspan=%d>No row. </td></tr>" % len(headers)}'
            f"</tbody></table></div>")


def load(name: str):
    p = STORE / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def shell(title: str, lede: str, body: str, stamp: str) -> str:
    nav = ('<nav><a href="../index.html">Overview</a>'
           '<a href="index.html">Transactions &amp; reserve</a>'
           '<a href="rows.html">Every row</a>'
           '<a href="../pages/review.html">Flagged for Review</a></nav>')
    head = (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head>\n<body>\n')
    return (head + f'<header><a href="../index.html">NFL Decision Lab</a>{nav}</header>\n<main>\n'
            f"<h1>{html.escape(title.split(' ·')[0])}</h1>\n"
            f'<p class="lede">{lede}</p>\n{body}\n'
            f'<footer>Rendered by <code>tools/build_reserve_site.py</code> from '
            f'<code>data/reserve/</code> · build stamp from the data: {esc(stamp)}. '
            f"Every row links to the page it was read from; a cell the official page leaves empty "
            f"is printed as <em>not printed</em>, never filled.</footer>\n</main>\n</body></html>\n")


def _artifact_rows(rendered):
    """zip helper: the artifact table re-uses its rendered cells and adds a repo link."""
    return rendered


def build_index(coverage, transactions, state, join, staleness, manifest) -> tuple[str, str]:
    stamp = (coverage or {}).get("generated_at_utc") or (transactions or {}).get("generated_at_utc") \
        or "no capture yet"
    rows_n = (transactions or {}).get("count", 0)
    pages_n = (coverage or {}).get("n_pages", 0)
    n_flags = len((coverage or {}).get("flags") or [])
    n_reserve = sum(c.get("n_on_reserve", 0) for c in ((state or {}).get("by_club") or {}).values())
    n_players = len((state or {}).get("players") or {})
    n_clubs = len([c for c in ((state or {}).get("by_club") or {}) if c != "UNKNOWN"])
    missing_date = sum(1 for r in (transactions or {}).get("rows") or [] if not r.get("date"))
    pos_printed = sum(1 for r in (transactions or {}).get("rows") or [] if r.get("position_printed"))

    out = ['<div class="kpis">']
    out.append(kpi("Pages captured", pages_n, "category × month fetches with a hash"))
    out.append(kpi("Transaction rows", rows_n, "every row links to its page"))
    out.append(kpi("Clubs with a dated event", n_clubs, "of 32"))
    out.append(kpi("Players on an open reserve designation", n_reserve,
                   "an event that no later transaction closed"))
    out.append(kpi("Flags on record", n_flags, "published, not hidden",
                   tone="warn" if n_flags else "ok"))
    out.append(kpi("Rows with no parseable date", missing_date,
                   "kept, never dropped", tone="warn" if missing_date else "ok"))
    out.append("</div>")

    out.append(
        '<p>Why this page exists: the weekly injury report and the reserve list are two different '
        'official records. A player on injured reserve is <em>not</em> on the weekly report at all, '
        'so a count taken from the report alone understates who a club cannot play. This is the '
        'league\u2019s own dated register of those moves \u2014 captured, hashed, and replayable.</p>')

    # Coverage: what we hold, of what, read when.
    out.append("<h2 id=\"coverage\">Coverage: what was captured, and when</h2>")
    cov_rows = []
    pages = (coverage or {}).get("pages") or {}
    official_base = "https://www.nfl.com/transactions/league/"
    for key in sorted(pages):
        p = pages[key]
        cat, month = key.split("/", 1)
        cov_rows.append([esc(key), esc(p.get("status")),
                         esc(p.get("rows_last_read") if p.get("rows_last_read") is not None
                             else p.get("rows")),
                         esc(p.get("rows_in_the_union")),
                         esc(p.get("captures_for_page")),
                         esc(p.get("cap_oldest_printed")),
                         f'<code>{esc((p.get("canonical_sha256") or "")[:16])}</code>',
                         esc(p.get("captured_at_utc")),
                         esc(p.get("http_status")),
                         link(p.get("url"), "official page"),
                         esc("; ".join(p.get("flags") or []))])
    headers = [("Category / month", ""), ("Status", ""), ("Rows in the newest read", "num"),
               ("Rows in the union of all reads", "num"), ("Reads of this page", "num"),
               ("Oldest row printed by the source", ""),
               ("Content SHA-256 (first 16)", ""), ("Read at (UTC)", ""), ("HTTP", "num"),
               ("Source", ""), ("Flags on this page", "")]
    out.append(table(headers, cov_rows))
    capped = (coverage or {}).get("pages_capped") or []
    incomplete = (coverage or {}).get("months_incomplete_at_source") or []
    # A capped page in a CLOSED month can never be completed by re-reading: the league prints only
    # the last 25 rows of that month, forever. A capped page in the CURRENT month can be, by reading
    # the running page often. The difference decides whether a gap is recoverable, so it is computed
    # from the capture stamp and published, not left for a reader to infer.
    stamp_month = str((coverage or {}).get("captured_at") or "")[:7]
    closed_partial = sorted(k for k in incomplete if k.split("/")[-1] < stamp_month)
    if capped:
        out.append(
            '<div class="flag note"><span class="open">The printed cap: the source shows at most '
            '25 rows per '
            'category-and-month page.</span> '
            + str((coverage or {}).get("cap_explained") or "")
            + f' {len(capped)} page(s) sit at that cap; {len(incomplete)} of them are '
              '<b>incomplete at the source</b> for their month (the oldest row printed is later '
              'than the first of the month), which is a limit of the league\u2019s page and not a '
              'gap in this capture. Rows are recovered by reading the running page repeatedly: the '
              'register below is the union of every read, so a row never disappears when it slides '
              'out of the printed window. '
              + (f"Capped pages: {', '.join(capped)}." if capped else "")
              + (f" <b>{len(closed_partial)} of them are in a month that has already closed</b>, so "
                 "re-reading cannot recover the rows the league did not print: those months are "
                 "permanent partial views of the official page, and every count taken from them is a "
                 "floor, not a total. Months still running are completed by the sweep."
                 if closed_partial else
                 " Every capped page is in the month still being captured, so the sweep completes it."
                 if incomplete else "")
              + "</div>")
    out.append('<p class="note">A month that was never fetched is absent from this table rather '
               'than shown as zero: absence is a gap in our capture, zero is a claim about the '
               'league. The pinned category and month list lives in '
               '<code>pipeline/collect_transactions.py</code>.</p>')

    # The decision panel: per club, what the report says, what the reserve list adds.
    out.append("<h2 id=\"clubs\">Per club: the weekly report plus the reserve list</h2>")
    club_rows = []
    clubs = (join or {}).get("clubs") or {}
    by_club = (state or {}).get("by_club") or {}
    for club in sorted(set(clubs) | set(by_club)):
        j = clubs.get(club) or {}
        ev = by_club.get(club) or {}
        names = "; ".join(f"{p['player']} ({p['opened']})" for p in ev.get("players_on_reserve") or [])
        month_for_link = None
        for p in (ev.get("players_on_reserve") or []):
            if p.get("opened"):
                month_for_link = p["opened"][:7]
        src = (official_base + "reserve-list/" + month_for_link.replace("-", "/")) if month_for_link \
            else None
        club_rows.append([
            f'<a href="../injuries.html" title="club view on the injury page">{esc(club)}</a>',
            esc(j.get("report_rows")),
            esc(j.get("n_on_reserve")),
            esc(j.get("on_reserve_not_in_report")),
            esc(j.get("unavailable_total_report_plus_reserve")),
            esc(names),
            link(src or "https://www.nfl.com/transactions/", "reserve list" if src
                 else "the register"),
        ])
    out.append(table([("Club", ""), ("Weekly report rows", "num"), ("On a reserve list", "num"),
                      ("On a reserve list, never on the report", "num"),
                      ("Unavailable, both records counted", "num"),
                      ("Named players on an open reserve designation (date opened)", ""),
                      ("Source", "")], club_rows))
    tot = (join or {}).get("totals") or {}
    js = (join or {}).get("join_source") or {}
    out.append('<p class="note">The weekly-report column is the official report the pipeline '
               f'stores: {esc(js.get("url"))} · week {esc(js.get("week"))} · '
               f'{esc(js.get("report_rows"))} rows · read {esc(js.get("generated_at"))} · '
               f'page SHA-256 <code>{esc((js.get("html_sha256") or "")[:16])}</code>. '
               f'Across the clubs captured: {esc(tot.get("report_rows"))} report rows, '
               f'{esc(tot.get("on_reserve"))} players on an open reserve designation, '
               f'{esc(tot.get("on_reserve_not_in_report"))} of them absent from the report '
               f'exactly because they are on the reserve list, '
               f'{esc(tot.get("named_in_both"))} named in both.</p>')
    if (join or {}).get("error"):
        out.append('<div class="flag note"><span class="open">No join published.</span> '
                   + esc(join["error"]) + "</div>")

    # Depth staleness
    out.append("<h2 id=\"staleness\">Depth and report rows the register says are out of date"
               "</h2>")
    st_rows = []
    for f in (staleness or {}).get("findings") or []:
        artifact_cell = (f'{esc(f.get("artifact"))}<br><span class="blank">{esc(f.get("artifact_nature"))}'
                         f' · captured {esc(f.get("artifact_date"))}</span>')
        links = [link(f.get("source_url"), "official transaction")]
        art_src = f.get("artifact_source_url")
        if art_src and str(art_src).startswith(("http://", "https://")):
            links.append(link(art_src, "the artifact's own page"))
        elif art_src:
            # The staleness file stores a source KEY (S15) for the artifact side, because the
            # artifact's own file records keys, not URLs. A key is not a link: resolving it here
            # would send a reader to a file named "S15". It is printed as what it is, and the row
            # still carries the dated official link to the event above it.
            links.append(f'<code title="source key recorded in the artifact">{esc(art_src)}</code>')
        if f.get("player_url"):
            links.append(link(f["player_url"], "official player page"))
        st_rows.append([artifact_cell, esc(f.get("club")), esc(f.get("player")),
                        esc(f.get("slot")), esc(f.get("latest_event")),
                        esc(f.get("event_date")), " ".join(links)])
    out.append(table([("Repo artifact", ""), ("Club", ""), ("Player", ""),
                      ("Slot or column it is printed in", ""),
                      ("What the official register says happened", ""), ("Dated", ""),
                      ("Sources", "")], st_rows))
    arts = []
    for a in (staleness or {}).get("artifacts") or []:
        f = a.get("file") or ""
        arts.append([esc(a.get("artifact")),
                     (f'<a href="https://github.com/kanlerxz87-cyber/NFL1/blob/main/{f}"'
                      f' target="_blank" rel="noopener"><code>{esc(f)}</code></a>'),
                     esc(a.get("nature")), esc(a.get("names")), esc(a.get("status"))])
    out.append(table([("Artifact compared", ""), ("File", ""), ("What it claims to be", ""),
                      ("Player names read", ""), ("Status", ""), ("Open the file", "")],
                     [a_row + [link(a.get("url"), "repo file")] for a, a_row in
                      zip(((staleness or {}).get("artifacts") or []), _artifact_rows(arts))]
                     if arts else []))
    out.append('<p class="note">'
               f'{esc((staleness or {}).get("contradictions_of_a_current_claim", 0))} finding(s) '
               'contradict an artifact that claims to be current; '
               f'{esc((staleness or {}).get("rows_superseded_by_a_later_event", 0))} row(s) belong '
               'to a dated snapshot and are superseded rather than wrong. A depth row is a claim '
               'about who a club lists; a weekly report row is a claim about one day. They fail in '
               'different ways, so they are counted separately.</p>')
    out.append('<p class="note">'
               + esc((staleness or {}).get("note") or "no staleness file yet")
               + "</p>")

    # Flags
    out.append("<h2 id=\"flags\">Flags raised by the capture</h2>")
    fl_rows = []
    for f in (coverage or {}).get("flags") or []:
        fl_rows.append([esc(f.get("page")), esc(f.get("flag")),
                        link((pages.get(f.get("page") or "") or {}).get("url"), "the page")])
    if not fl_rows:
        out.append('<p class="note">No flag is open on the current captures. A flag is raised '
                   "whenever a printed cell is blank where a value is expected, a club code is "
                   "not one of the 32, a date cannot be read, or a page that must carry rows "
                   "carries none.</p>")
    else:
        out.append(table([("Page", ""), ("Flag", ""), ("Source", "")], fl_rows))

    # Method + limits
    out.append("<h2 id=\"method\">Method, and what this cannot say</h2>")
    meth = (
        "<ul>"
        "<li><b>Source.</b> <a href=\"https://www.nfl.com/transactions/\">www.nfl.com/transactions/"
        "</a>, the league's own register, six categories by month. It is the same host as the "
        "injury report; no third-party odds or news-aggregator data is used here.</li>"
        "<li><b>Capture.</b> The fetcher records the UTC time, the HTTP status, the byte count and "
        "the SHA-256 of the raw page, then parses each table by <em>header name</em>, never by "
        "column position. A capture file is written only when the parsed content changes, with "
        "exclusive-create, so history is append-only and a replay is possible.</li>"
        "<li><b>Blank is blank.</b> The Position column on these pages is usually empty. It is "
        f"stored empty and printed as <em>not printed</em>: {esc(pos_printed)} of {esc(rows_n)} "
        "rows carry a printed position. No position is inferred from the player's club roster.</li>"
        "<li><b>Club codes.</b> The register prints <code>AZ</code> for Arizona and <code>LA</code> "
        "for the Rams; the repository uses <code>ARI</code> and <code>LA</code>. The printed code is "
        "kept, and the mapping is recorded, because the same club appears under two codes in "
        "different official files (flag CAP-05 on the review page).</li>"
        "<li><b>What it cannot say.</b> It cannot say who the backup is, which depth slot a reserve "
        "move empties, or how much a return is worth: those need the depth chart and snap counts, "
        "and the league publishes neither in a form this repository can verify. It cannot be used "
        "as a price. It says only who moved, when, and to or from what list.</li>"
        "</ul>")
    out.append('<div class="note">' + meth + "</div>")
    if manifest:
        out.append('<p class="note">Manifest: '
                   f'{esc(len(manifest.get("captures") or []))} capture file(s), '
                   f"parser <code>{esc(manifest.get('parser'))}</code>, "
                   f"categories {esc(', '.join(manifest.get('categories') or []))}, "
                   f"months {esc(', '.join(manifest.get('months') or []))}.</p>")

    lede = ("Dated roster events from the league's own transactions register \u2014 trades, "
            "signings, reserve lists, waivers, terminations \u2014 captured with a timestamp and a "
            "hash, joined to the official weekly injury report so that \u201cnot listed\u201d is never "
            "read as \u201cavailable\u201d.")
    return shell("Official transactions and reserve list \u00b7 NFL Decision Lab", lede,
                 "\n".join(out), stamp), stamp


def build_rows(transactions, coverage) -> str:
    stamp = (transactions or {}).get("generated_at_utc") or "no capture yet"
    rows = []
    for r in reversed((transactions or {}).get("rows") or []):
        rows.append([esc(r.get("date") or r.get("date_printed")), esc(r.get("category")),
                     esc(r.get("club_from")), esc(r.get("club_to")),
                     link(r.get("player_url"), r.get("player")) if r.get("player_url")
                     else esc(r.get("player")),
                     esc(r.get("position_printed")), esc(r.get("transaction")),
                     link(r.get("source_url"), "official row page")])
    headers = [("Date", ""), ("Category", ""), ("From", ""), ("To", ""), ("Player", ""),
               ("Position", ""), ("Transaction", ""), ("Source", "")]
    body = [f'<p>Rows in the register as captured: <b>{len(rows)}</b>. Newest first. '
            'A row whose date could not be read keeps its printed text and is listed with the '
            "flag the parser raised; it is never dropped.</p>",
            table(headers, rows)]
    return shell("Every captured transaction row \u00b7 NFL Decision Lab",
                 "The full register as stored, one row per printed line, each linked to the page "
                 "it was read from.", "\n".join(body), stamp)


def build() -> tuple[list[Path], str]:
    coverage = load("coverage.json")
    transactions = load("transactions.json")
    state = load("reserve_state.json")
    join = load("report_vs_reserve.json")
    staleness = load("depth_staleness.json")
    manifest = json.loads((STORE / "manifest.json").read_text(encoding="utf-8")) \
        if (STORE / "manifest.json").exists() else None
    index, stamp = build_index(coverage, transactions, state, join, staleness, manifest)
    rows_page = build_rows(transactions, coverage)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "index.html").write_text(index, encoding="utf-8")
    (OUT_DIR / "rows.html").write_text(rows_page, encoding="utf-8")
    return [OUT_DIR / "index.html", OUT_DIR / "rows.html"], stamp


def main() -> int:
    paths, stamp = build()
    if "--check" in sys.argv:
        import subprocess
        r = subprocess.run(["git", "diff", "--exit-code", "--", "reserve/"], cwd=ROOT)
        if r.returncode != 0:
            print("FAILED: the committed reserve pages differ from a rebuild from data/reserve/")
            return 1
        print("OK: reserve/index.html and reserve/rows.html are exactly the current build")
        return 0
    print("wrote " + ", ".join(str(p.relative_to(ROOT)) for p in paths) + f" (data stamp {stamp})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
