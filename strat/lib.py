#!/usr/bin/env python3
"""strat/lib.py — shared helpers for the Strategy Competition sub-site.

Design rules (enforced by strat/verify.py):

  * a number is only printed when it was computed from a file in this repository or from an
    official source fetched in the same run; otherwise the cell is an explicit blank that says
    why it is blank;
  * every table row carries an <a class="src" href="https://..."> link;
  * every page is deterministic: the same inputs produce byte-identical output;
  * no page asserts that a strategy is profitable.  The vocabulary is *eligible*, *ineligible*,
    *paper*, *live*, *demote* — never "winner".

Sources are named in SOURCES with the exact URL that was fetched.  The two GitHub-hosted
extracts are labelled as third-party (nflverse), because the source code is published there
even though the underlying numbers are the NFL's Game Statistics and Information System feed.
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "strat")
SITE = os.path.join(ROOT, "strat")

# --------------------------------------------------------------------------- sources
SOURCES = {
    "schedules": ("https://www.nfl.com/schedules/", "NFL schedules (official)"),
    "schedule_w10": ("https://www.nfl.com/schedules/2026/REG10",
                     "NFL Week 10 schedule 2026 (official)"),
    "injuries_w10": ("https://www.nfl.com/injuries/league/2026/reg10",
                     "NFL Week 10 injury report 2026 (official)"),
    "standings": ("https://www.nfl.com/standings/league/2026/reg",
                  "NFL standings 2026 (official)"),
    "gameday_w10_was_nyg": ("https://www.nfl.com/games/commanders-at-giants-2026-reg-10",
                            "NFL Game Center WAS@NYG (official)"),
    "nflverse": ("https://github.com/nflverse/nflverse-data",
                 "nflverse data repository (third-party extract of the NFL GSIS feed)"),
    "nflverse_schedules": ("https://github.com/nflverse/nflverse-data/releases/tag/schedules",
                           "nflverse schedules release (third-party)"),
    "nflverse_injuries": ("https://github.com/nflverse/nflverse-data/releases/tag/injuries",
                          "nflverse injuries release (third-party)"),
    "nflverse_players": ("https://github.com/nflverse/nflverse-data/releases/tag/players",
                         "nflverse player-week release (third-party)"),
    "terms": ("https://www.nfl.com/legal/terms/", "NFL.com Terms of Use (official)"),
    "repo": ("https://github.com/kanlerxz87-cyber/NFL1", "This repository"),
}

# every published page and the nav label it carries
NAV = [
    ("index.html", "Overview"),
    ("leaderboard.html", "Proper-Score Leaderboard"),
    ("preregister.html", "Pre-Registration"),
    ("demotion.html", "Demotion Gate"),
    ("what-would-change.html", "What Would Change Our Mind"),
    ("totals.html", "Two Totals"),
    ("reconciliation.html", "Official Reconciliation"),
    ("questions.html", "Open Questions"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged for Review"),
    ("method.html", "Method & Sources"),
    ("executive-summary.html", "Executive Summary"),
]


# --------------------------------------------------------------------------- io
def load(name: str):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def clean(o):
    """Convert to strict JSON: NaN and infinity become null, numpy scalars become Python.

    A null is the machine-readable form of "this value is not confirmed", which the renderer
    turns into an explicit blank cell rather than a number.
    """
    import math as _m
    try:
        import numpy as _np
    except Exception:  # pragma: no cover
        _np = None
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if _np is not None:
        if isinstance(o, _np.integer):
            return int(o)
        if isinstance(o, _np.floating):
            o = float(o)
        if isinstance(o, _np.bool_):
            return bool(o)
        if isinstance(o, _np.ndarray):
            return [clean(v) for v in o.tolist()]
    if isinstance(o, float):
        return None if (_m.isnan(o) or _m.isinf(o)) else o
    return o


def write_json(name: str, obj) -> None:
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, name)
    text = json.dumps(clean(obj), indent=1, sort_keys=False, allow_nan=False) + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote data/strat/{name}")


def write_page(name: str, text: str) -> None:
    os.makedirs(SITE, exist_ok=True)
    path = os.path.join(SITE, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote strat/{name}")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- html
def e(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def blank(reason: str) -> str:
    return f'<span class="blank" title="{e(reason)}">blank</span>'


def src(key: str, label: str | None = None) -> str:
    url, name = SOURCES[key]
    return (f'<a class="src" href="{e(url)}" target="_blank" rel="noopener">'
            f'{e(label or name)} ↗</a>')


def artifact(path: str, label: str | None = None) -> str:
    """Link to the committed artifact this row's text was read from.

    The repository is hosted on github.com, which this project's source allow-list treats as an
    official host for its own artifacts.  A definitional row (a rule we wrote) has no external
    publisher, so the committed file *is* its source, and saying otherwise would be dishonest.
    """
    url = f"https://github.com/kanlerxz87-cyber/NFL1/blob/main/{path}"
    return (f'<a class="src" href="{e(url)}" target="_blank" rel="noopener">'
            f'{e(label or path)} ↗</a>')


def num(v, fmt="{:.2f}", reason="not confirmed from a source") -> str:
    if v is None or (isinstance(v, float) and v != v):
        return blank(reason)
    return fmt.format(v)


def pct(v, reason="not confirmed from a source") -> str:
    if v is None:
        return blank(reason)
    return f"{v:.2f}%"


def badge(status: str) -> str:
    s = str(status or "").upper()
    cls = "neutral"
    if s in ("PASS", "ELIGIBLE", "DONE", "LIVE", "MET", "ANSWERED", "REPRODUCED"):
        cls = "pass"
    elif s in ("WATCH", "PARTIAL", "PAPER", "UNVERIFIED", "IN PROGRESS", "OPEN"):
        cls = "warn"
    elif s in ("FAIL", "INELIGIBLE", "BLOCKED", "DEMOTE", "NOT MET", "NOT STARTED"):
        cls = "fail"
    return f'<span class="badge {cls}">{e(s)}</span>'


def table(headers, rows, note: str = "", cls: str = "") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows
    )
    out = (f'<div class="table-wrap"><table class="{cls}"><thead><tr>{head}</tr></thead>'
           f"<tbody>{body}</tbody></table></div>")
    if note:
        out += f'<p class="note">{note}</p>'
    return out


def kpi(label: str, value, sub: str = "") -> str:
    return (f'<div class="kpi"><span class="kpi-label">{e(label)}</span>'
            f'<span class="kpi-value">{e(value)}</span>'
            f'<span class="kpi-sub">{e(sub)}</span></div>')


def page(name: str, title: str, standfirst: str, body: str, built: str,
         stamp_label: str = "Built") -> str:
    ACTIVE = ' class="active"'
    nav = "".join(
        f'<a href="{href}"{ACTIVE if href == name else ""}>{e(label)}</a>'
        for href, label in NAV
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · NFL Strategy Competition</title>
<meta name="description" content="Pre-registered NFL line-origination strategies, ranked by benchmark-relative proper scores with uncertainty. Every row carries an official source link; blank means unverified.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <a class="brand" href="../index.html"><span class="mark">NFL</span><span class="brand-text">Strategy Competition</span></a>
  <nav aria-label="Strategy competition sections">{nav}</nav>
</header>
<main id="main">
  <section class="page-head">
    <p class="eyebrow">Strategy competition</p>
    <h1>{e(title)}</h1>
    <p class="standfirst">{standfirst}</p>
    <p class="timestamp">{e(stamp_label)} {e(built)} UTC · every table row links to its source · a blank cell means the value is not confirmed</p>
  </section>
{body}
</main>
<footer>
  <p>NFL Strategy Competition · part of the NFL Decision Lab. Prices, results and injury data are
  described at <a href="method.html">Method &amp; Sources</a>. Nothing on this site is a recommendation
  to bet, and no strategy is claimed to be profitable: the leaderboard publishes scores,
  uncertainty and the gate that fails.</p>
  <p><a href="../index.html">← Back to the NFL Decision Lab</a> · <a href="executive-summary.html">Executive summary</a> · <a href="questions.html">Open questions</a></p>
</footer>
</body>
</html>
"""
