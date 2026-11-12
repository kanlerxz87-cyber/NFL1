"""Static site kit: layout, styling and small render helpers.

The site is generated as plain static HTML with no build step, no JavaScript
framework and no third-party assets, so GitHub Pages can serve it directly and
every page is viewable as source. Data tables are rendered from
data/processed/site_data.json only - the generator never contains a number.
"""
from __future__ import annotations

import html
import os
import pathlib
import re
from typing import Any, Iterable, Sequence

_URL_RE = re.compile(r"https?://[^\s,;)\]]+")


def first_url(text: str | None) -> str | None:
    """Pull the first real URL out of free text, or return None.

    Naive whitespace splitting turns a resolving source that begins 'A licensed
    odds API' into href="A", which is a broken link. Never guess a URL.
    """
    if not text:
        return None
    m = _URL_RE.search(text)
    return m.group(0).rstrip(".,;") if m else None

#: Where the built site is written, and therefore where GitHub Pages serves it
#: from. The repository's Pages source is fixed to `main` at `/` and the API
#: refuses to change it (403 - the integration token lacks `pages:write`), so
#: the site is published from the repository root rather than from `docs/`.
#: Override with NFL1_SITE_OUT for a scratch build.
SITE_OUT = pathlib.Path(os.environ["NFL1_SITE_OUT"]).resolve() \
    if os.environ.get("NFL1_SITE_OUT") else pathlib.Path(__file__).resolve().parents[2]

REPO_URL = "https://github.com/kanlerxz87-cyber/NFL1"

#: category -> [(slug, label)]
NAV: dict[str, list[tuple[str, str]]] = {
    "Overview": [
        ("index", "Dashboard"),
        ("executive-summary", "Executive Summary"),
        ("open-questions", "Open Questions"),
        ("suggestions", "Suggestions Board"),
        ("flagged", "Flagged for Review"),
    ],
    "Verified Data": [
        ("data-standings", "Standings 2026"),
        ("data-schedule", "Week 10 Schedule"),
        ("data-injuries", "Injury Report"),
        ("data-news", "Official News Feed"),
    ],
    "Analysis": [
        ("analysis-ratings", "Team Ratings"),
        ("analysis-luck", "Luck Table"),
        ("analysis-correlation", "Correlations"),
        ("availability-depth", "Availability & Depth"),
    ],
    "Line Origination": [
        ("lines-week10", "Week 10 Board"),
        ("methodology", "Methodology"),
    ],
    "Strategies": [
        ("strategies-leaderboard", "Leaderboard"),
        ("strategies-catalogue", "Strategy Catalogue"),
        ("strategies-gates", "Validation Gates"),
    ],
    "Integrity": [
        ("verification", "Verification Report"),
        ("sources", "Source Register"),
    ],
}
ALL_PAGES = [(s, l, c) for c, items in NAV.items() for s, l in items]
SLUG_TO_LABEL = {s: l for s, l, _ in ALL_PAGES}
SLUG_TO_CATEGORY = {s: c for s, l, c in ALL_PAGES}

CSS = """
:root{
  --bg:#f6f7f9; --panel:#ffffff; --ink:#14181f; --muted:#5b6673;
  --line:#e2e6eb; --line2:#eef1f4; --accent:#1b5fd9; --accent-soft:#eaf1fd;
  --ok:#0f7b47; --ok-bg:#e7f6ed; --warn:#8a5a00; --warn-bg:#fdf3dc;
  --bad:#a32020; --bad-bg:#fdeaea; --info:#1b5fd9; --info-bg:#eaf1fd;
  --na:#5b6673; --na-bg:#eef1f4;
  --radius:10px; --shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.04);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
code{background:var(--line2);padding:.1em .35em;border-radius:4px;font-size:.88em}
pre{background:#0f1419;color:#e6edf3;padding:14px 16px;border-radius:var(--radius);
  overflow:auto;font-size:12.5px;line-height:1.5}
pre code{background:none;padding:0;color:inherit}
.wrap{display:grid;grid-template-columns:238px minmax(0,1fr);gap:26px;
  max-width:1420px;margin:0 auto;padding:22px 22px 60px}
header.top{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:12px;align-items:baseline;
  justify-content:space-between;padding-bottom:14px;border-bottom:1px solid var(--line);margin-bottom:6px}
header.top h1{font-size:19px;margin:0;letter-spacing:-.2px}
header.top .sub{color:var(--muted);font-size:13px}
nav.side{position:sticky;top:22px;align-self:start;max-height:calc(100vh - 44px);overflow:auto}
nav.side .grp{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
  margin:16px 0 6px;font-weight:700}
nav.side a{display:block;padding:5px 9px;border-radius:7px;color:var(--ink);font-size:13.5px}
nav.side a:hover{background:var(--line2);text-decoration:none}
nav.side a.on{background:var(--accent-soft);color:var(--accent);font-weight:650}
main{min-width:0}
h2.pg{font-size:24px;margin:4px 0 4px;letter-spacing:-.4px}
p.lead{color:var(--muted);margin:0 0 20px;max-width:82ch}
section{margin:26px 0}
h3{font-size:16.5px;margin:26px 0 8px;letter-spacing:-.2px}
h4{font-size:14px;margin:18px 0 6px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:16px 18px;box-shadow:var(--shadow);margin:12px 0}
.grid{display:grid;gap:12px}
.g2{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}
.g4{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
  padding:13px 15px;box-shadow:var(--shadow)}
.kpi .k{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:700}
.kpi .v{font-size:26px;font-weight:700;letter-spacing:-.8px;margin:3px 0 1px;font-variant-numeric:tabular-nums}
.kpi .n{font-size:12px;color:var(--muted);line-height:1.4}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius);
  background:var(--panel);box-shadow:var(--shadow);margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line2);vertical-align:top}
thead th{position:sticky;top:0;background:#fafbfc;border-bottom:1px solid var(--line);
  font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
  font-weight:700;white-space:nowrap;z-index:1}
tbody tr:hover{background:#fbfcfd}
tbody tr:last-child td{border-bottom:none}
td.num,th.num{text-align:right}
td.c,th.c{text-align:center}
.badge{display:inline-block;padding:1.5px 7px;border-radius:999px;font-size:10.5px;
  font-weight:700;letter-spacing:.04em;text-transform:uppercase;white-space:nowrap;
  border:1px solid transparent}
.b-VERIFIED,.b-PASS,.b-APPROVED,.b-ACTIVE{background:var(--ok-bg);color:var(--ok);border-color:#bfe6cd}
.b-DERIVED,.b-INFO,.b-RUN{background:var(--info-bg);color:var(--info);border-color:#c5d9f8}
.b-MODELED,.b-FLAG,.b-PROVISIONAL,.b-PARTIAL{background:var(--warn-bg);color:var(--warn);border-color:#f0dcae}
.b-UNAVAILABLE,.b-FAIL,.b-REJECTED,.b-BLOCKED,.b-NOT_STAKEABLE,.b-NOT_RUN{background:var(--na-bg);color:var(--na);border-color:#dfe4ea}
.b-MECHANICAL,.b-REDUNDANT{background:var(--na-bg);color:var(--na);border-color:#dfe4ea}
.b-CANDIDATE{background:var(--info-bg);color:var(--info);border-color:#c5d9f8}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;
  background:var(--line2);color:var(--muted);white-space:nowrap}
.blank{color:#98a2ae;font-style:italic}
.src{font-size:11.5px;white-space:nowrap}
.note{font-size:12.5px;color:var(--muted);margin:6px 0 0;max-width:96ch}
.callout{border-left:3px solid var(--accent);background:var(--accent-soft);
  padding:11px 14px;border-radius:0 8px 8px 0;margin:12px 0;font-size:13.5px}
.callout.warn{border-left-color:#d9a400;background:var(--warn-bg)}
.callout.bad{border-left-color:var(--bad);background:var(--bad-bg)}
.callout.ok{border-left-color:var(--ok);background:var(--ok-bg)}
.callout p:first-child{margin-top:0}.callout p:last-child{margin-bottom:0}
footer{grid-column:1/-1;margin-top:34px;padding-top:14px;border-top:1px solid var(--line);
  color:var(--muted);font-size:12px;display:flex;flex-wrap:wrap;gap:8px 18px;justify-content:space-between}
.md table{margin:10px 0}
.md ul,.md ol{padding-left:22px;margin:8px 0}
.md li{margin:3px 0}
.md h2{font-size:19px;margin:26px 0 6px;letter-spacing:-.3px}
.md h3{font-size:15.5px}
.md blockquote{border-left:3px solid var(--line);margin:10px 0;padding:2px 0 2px 14px;color:var(--muted)}
.toc{columns:2;column-gap:26px;font-size:13px}
@media(max-width:900px){
  .wrap{grid-template-columns:1fr;padding:14px 14px 40px}
  nav.side{position:static;max-height:none;order:2;border-top:1px solid var(--line);padding-top:10px}
  main{order:1}
  .toc{columns:1}
}
@media print{nav.side,header.top .sub{display:none}.wrap{display:block}}
"""


def esc(v: Any) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def fmt(v: Any, nd: int = 2, signed: bool = False, blank_text: str = "—") -> str:
    """Render a value, or the blank marker. Never renders a guess."""
    if v is None or v == "":
        return f'<span class="blank" title="not available from an official source">{blank_text}</span>'
    if isinstance(v, float):
        s = f"{v:+.{nd}f}" if signed else f"{v:.{nd}f}"
        return s
    if isinstance(v, int) and signed:
        return f"{v:+d}"
    return esc(v)


def badge(tier: str | None, label: str | None = None) -> str:
    if not tier:
        return ""
    t = str(tier)
    return f'<span class="badge b-{esc(t)}">{esc(label or t)}</span>'


def src(url: str | None, label: str = "source") -> str:
    if not url:
        return ""
    return f'<a class="src" href="{esc(url)}" rel="noopener noreferrer" target="_blank">{esc(label)} ↗</a>'


def table(headers: Sequence[str], rows: Iterable[Sequence[str]],
          aligns: Sequence[str] | None = None, cls: str = "",
          caption: str = "") -> str:
    """aligns entries: '' left, 'num' right, 'c' centre."""
    aligns = list(aligns or [""] * len(headers))
    out = []
    if caption:
        out.append(f'<div class="scroll"><div style="padding:9px 12px 0;font-size:12px;color:var(--muted)">{caption}</div>')
    else:
        out.append('<div class="scroll">')
    out.append(f'<table class="{esc(cls)}"><thead><tr>')
    for h, a in zip(headers, aligns):
        out.append(f'<th class="{a}">{h}</th>')
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>")
        for cell, a in zip(r, aligns):
            out.append(f'<td class="{a}">{cell}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def kpi(label: str, value: Any, note: str = "") -> str:
    return (f'<div class="kpi"><div class="k">{esc(label)}</div>'
            f'<div class="v">{value}</div>'
            f'<div class="n">{note}</div></div>')


def callout(text: str, kind: str = "") -> str:
    return f'<div class="callout {kind}">{text}</div>'


def panel(inner: str, title: str = "") -> str:
    head = f"<h3 style='margin-top:0'>{title}</h3>" if title else ""
    return f'<div class="panel">{head}{inner}</div>'


def _nav_html(slug: str, prefix: str) -> str:
    out = ['<nav class="side">']
    for cat, items in NAV.items():
        out.append(f'<div class="grp">{esc(cat)}</div>')
        for s, label in items:
            on = " class=\"on\"" if s == slug else ""
            out.append(f'<a href="{prefix}{s}.html"{on}>{esc(label)}</a>')
    out.append(f'<div class="grp">Repository</div>')
    out.append(f'<a href="{REPO_URL}" target="_blank" rel="noopener noreferrer">GitHub ↗</a>')
    out.append(f'<a href="{REPO_URL}/blob/main/COORDINATION.md" target="_blank" rel="noopener noreferrer">Coordination board ↗</a>')
    out.append("</nav>")
    return "".join(out)


def render_page(slug: str, title: str, body: str, subtitle: str = "",
                generated: str = "") -> str:
    """Every page lives at the root of the published site, so links are flat."""
    nav = _nav_html(slug, "")
    sub = f'<div class="sub">{subtitle}</div>' if subtitle else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · NFL1</title>
<meta name="description" content="{esc(title)} - NFL1 verified-data analysis dashboard.">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header class="top">
<h1>NFL1 <span style="color:var(--muted);font-weight:500">/ {esc(SLUG_TO_LABEL.get(slug, title))}</span></h1>
{sub}
</header>
{nav}
<main>
{body}
</main>
<footer>
<span>Generated by <code>scripts/build_site.py</code> from <code>data/processed/site_data.json</code>. {esc(generated)}</span>
<span>Every published value carries a provenance tier. Blank cells are deliberate.</span>
</footer>
</div>
</body>
</html>
"""
