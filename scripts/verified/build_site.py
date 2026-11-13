#!/usr/bin/env python3
"""
build_site.py — renders the verified-data pages from the data files, so the site and the
data can never drift apart. Every table row is emitted from data/verified/*, and every
row that came from an official page carries that page's URL.

Run:  python3 scripts/verified/build_site.py
Out:  pages/data.html, pages/verified-lines.html, pages/analysis.html, pages/decisions.html
      pages/verified.html   (index of this session's deliverables)
"""
from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "verified"
MODEL = DATA / "model"
PAGES = ROOT / "pages"

# Single source of truth: the canonical navigation lives in normalize_nav.py so that
# generated pages and hand-maintained pages can never disagree.
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_nav", Path(__file__).with_name("normalize_nav.py"))
_nav = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_nav)
NAV = _nav.CANON


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def rows_csv(name: str) -> list[dict]:
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def page(title: str, active: str, body: str, subtitle: str = "") -> str:
    # generated pages live in pages/, so hrefs differ from the canonical (root-relative) list
    nav_items = []
    for h, t in NAV:
        if active.startswith("pages/"):
            if h == "index.html":
                href = "../index.html"
            elif "/" in h:
                # sub-site entries (room/index.html, strength/index.html) sit at the
                # repository root — one level up from pages/
                href = "../" + h
            else:
                href = h
        else:
            href = "index.html" if h == "index.html" else f"pages/{h}"
        cls = ' class="active"' if h == active else ""
        nav_items.append(f'      <a href="{href}"{cls}>{esc(t)}</a>')
    nav = "\n".join(nav_items)
    sub = f'\n  <p class="muted">{subtitle}</p>' if subtitle else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — NFL1</title>
<link rel="stylesheet" href="../assets/css/style.css">
</head>
<body>
<header>
  <div class="brand">NFL1 — NFL Analytics Dashboard</div>
  <nav>
{nav}
  </nav>
</header>
<main>
  <h1>{esc(title)}</h1>{sub}
{body}
</main>
<footer class="muted" style="max-width:1200px;margin:0 auto;padding:24px">
  Generated from data/verified by scripts/verified/build_site.py. Blank means unverified — never inferred.
</footer>
</body>
</html>
"""


def badge(kind: str, text: str) -> str:
    return f'<span class="badge {kind}">{esc(text)}</span>'


def table(headers: list[str], body: list[list[str]], css_class: str = "table-wrap") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    trs = "\n".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body)
    return f'<div class="{css_class}"><table><thead><tr>{head}</tr></thead><tbody>\n{trs}\n</tbody></table></div>'


def src(url: str, label: str = "Official source") -> str:
    if not url:
        return badge("warn", "unverified")
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


# --------------------------------------------------------------------------- pages
def build_data() -> str:
    st = rows_csv("standings_2026.csv")
    games = rows_csv("games_2026.csv")
    inj = rows_csv("injuries_week10.csv")
    noinj = rows_csv("no_injuries_week10.csv")
    byes = rows_csv("byes_2026.csv")
    fx = rows_csv("week10_fixtures_2026.csv")
    v = load_json(MODEL / "validation.json")

    checks = v["checks"]
    passed = sum(1 for c in checks if c["ok"])

    body = f"""
  <div class="grid">
    <div class="stat"><div class="label">Completed games verified</div><div class="value">{len(games)}</div>
      <div class="muted">2026 regular season weeks 1–9</div></div>
    <div class="stat"><div class="label">Reconciliation</div><div class="value">{v.get('teams_fully_reconciled', 0)}/32</div>
      <div class="muted">teams whose game-by-game totals reproduce the official standings exactly</div></div>
    <div class="stat"><div class="label">Validation checks</div><div class="value">{passed}/{len(checks)}</div>
      <div class="muted"><a href="analysis.html">see gate results</a></div></div>
    <div class="stat"><div class="label">Injury rows captured</div><div class="value">{len(inj)}</div>
      <div class="muted">only rows with an official game status</div></div>
  </div>

  <h2>What "verified" means here</h2>
  <div class="card">
    <p>Each value was read from an official NFL page and stored with that page's URL and a retrieval
    timestamp. The dataset is then re-checked by an automated gate that recomputes every team's
    record and points from the game-by-game scores and compares it to the official standings table.
    If a single score were wrong, at least one team's totals would stop matching.</p>
    <p class="muted">Retrieval date: 2026-11-12 (UTC). Environment note: outbound HTTP from the
    build sandbox reaches only github.com, so all official NFL pages were read through the agent
    page-fetch channel; a bulk download (nflverse release) is blocked and is documented as such.</p>
  </div>

  <h2>Official standings — 2026 regular season</h2>
  <p class="muted">Source for every row: <a href="https://www.nfl.com/standings/" target="_blank" rel="noopener">nfl.com/standings</a>.
  Conference/division grouping is as published on that page.</p>
  {table(["Team","Conf","Div","W","L","T","PF","PA","Net","Streak","Source"],
         [[esc(r["team"]), esc(r["conference"]), esc(r["division"]), esc(r["w"]), esc(r["l"]),
           esc(r["t"]), esc(r["pf"]), esc(r["pa"]), esc(r["net_pts"]), esc(r["streak"]),
           src(r["source_url"])] for r in st])}

  <h2>Week 10 official injury report — captured rows</h2>
  <p class="muted">Only rows where the official page states a game status are stored as verified.
  Players listed without a game status are <em>not</em> treated as available or unavailable —
  that information is not asserted by the source, so it is left out rather than guessed.</p>
  {table(["Team","Player","Pos","Injury","Practice","Game status","Source"],
         [[esc(r["team_abbr"]), esc(r["player"]), esc(r["position"]), esc(r["injury"]) or badgeless(),
           esc(r["practice_status"]), badge("danger" if r["game_status"]=="Out" else "warn", r["game_status"]),
           src(r["source_url"])] for r in inj])}

  <h3>Teams reporting no injuries</h3>
  <p class="muted">Published explicitly by the source for Week 10 — a genuinely verified "clear" state.</p>
  {table(["Team","Week","Official state","Source"],
         [[esc(r["team_abbr"]), esc(r["week"]), esc(r["reported_state"]), src(r["source_url"])] for r in noinj])}

  <h2>Byes and Week 10 fixtures</h2>
  <p class="muted">Needed so that rest advantage and the prediction set are not guessed.</p>
  {table(["Week","Team on bye","Source"],
         [[esc(r["week"]), esc(r["team_abbr"]), src(r["source_url"])] for r in sorted(byes, key=lambda r:(int(r["week"]), r["team_abbr"]))])}
  {table(["Game","Away","Home","Kickoff ET","Note","Source"],
         [[esc(r["game_id"]), esc(r["away_abbr"]), esc(r["home_abbr"]), esc(r["kickoff_et"]),
           esc(r["note"]) or "—", src(r["source_url"])] for r in fx])}

  <h2>Validation gate output</h2>
  {table(["Check","Result","Detail"],
         [[esc(c["check"]), badge("ok","PASS") if c["ok"] else badge("danger","FAIL"), esc(c["detail"])] for c in checks])}

  <div class="card">
    <h3>How to reproduce</h3>
    <pre class="muted">python3 scripts/verified/validate_verified.py
python3 analysis/engine.py
python3 analysis/luck.py
python3 analysis/correlations.py
python3 scripts/verified/build_site.py</pre>
    <p class="muted">Data files: data/verified/games_2026.csv, standings_2026.csv,
    injuries_week10.csv, no_injuries_week10.csv, byes_2026.csv, week10_fixtures_2026.csv.</p>
  </div>
"""
    return body


def badgeless() -> str:
    return '<span class="muted">—</span>'


def build_lines() -> str:
    L = load_json(MODEL / "lines_week10.json")
    bt = load_json(MODEL / "backtest.json")
    rows = []
    for g in L["games"]:
        spread = -g["model_margin_home"]
        rows.append([
            esc(g["gameday"]), f'{esc(g["away"])} @ {esc(g["home"])}',
            f'{spread:+.1f}' if g["model_margin_home"] else "0.0",
            f'{g["model_total"]:.1f}',
            f'{g["away_power"]:+.1f} / {g["home_power"]:+.1f}',
            f'±{g["margin_sd"]:.1f}',
            badge("warn", "blank"),
            src(g["source_url"], "NFL schedule"),
        ])

    body = f"""
  <div class="card" style="border-color:#f59e0b">
    <h3>{badge("danger","Read this first")} These are model numbers, not market edges</h3>
    <p>{esc(L["meta"]["validation_verdict"])}</p>
    <p class="muted">{esc(L["meta"]["why_no_market"])}</p>
    <p><strong>Consequence:</strong> the table below cannot tell you whether any game is worth a
    bet. Judging value requires the actual price offered, and no official price source was
    available. Every market-line cell is therefore left blank rather than estimated.</p>
  </div>

  <h2>Your own lines — Week 10, 2026</h2>
  <p class="muted">Generated only from completed weeks 1–9 ({bt["n_games_evaluated"]} games).
  Model margin is from the home team's perspective; the spread shown is the home handicap
  (negative = home favoured). Uncertainty bands are the model's own forward-test residual
  standard deviation ({bt["residual_sd_margin"]:.2f} points on margin,
  {bt["residual_sd_total"]:.2f} on total).</p>
  {table(["Date","Matchup","Model spread (home)","Model total","Power (away / home)","Margin SD","Market line","Fixture source"], rows)}

  <h2>How the number is built</h2>
  <div class="card">
    <p>Ridge-regularised opponent-adjusted points model, fitted on verified final scores:</p>
    <pre class="muted">home points = μ + offence[home] − defence[away] + HFA
away points = μ + offence[away] − defence[home]</pre>
    <p>Estimated from the captured season: home-field advantage
    <strong>{bt.get("hfa_points_estimate")} points</strong>
    (ridge penalty λ = {bt.get("lambda_selected_full")}, chosen by nested cross-validation inside
    the training window only).</p>
    <p class="muted">The home-field estimate is close to zero because this season's verified
    results show home teams winning only
    {load_json(MODEL / "correlations.json")["home_win"]["rate"]:.1%} of decided games —
    see the correlation page before assuming a normal home edge.</p>
  </div>

  <h2>Why no props or parlays are priced yet</h2>
  <div class="card">
    <p>Player-prop lines need per-player usage and yardage distributions. That requires an official
    player-statistics feed at row level, which was not obtainable here; inventing distributions
    from memory would break the no-hallucination rule. Parity with single bets also requires
    measured same-game correlations, which <em>are</em> published (see
    <a href="analysis.html">Validation &amp; Correlation</a>) so the dependency structure is ready
    — only the player-level inputs are missing.</p>
    {table(["Product","Status","Blocking requirement"],
      [[badge("ok","Ready"), "Single-game spread / total lines", "market price feed to turn model numbers into decisions"],
       [badge("warn","Partial"), "Parlay maths and correlation adjustment", "measured correlations exist; joint-probability model for >2 legs"],
       [badge("danger","Blocked"), "Player prop lines and prop combos", "official row-level player usage/yardage data"],
       [badge("warn","Partial"), "Leaderboard with rewards", "prize terms, eligibility, audit — see Decision Register"]])}
  </div>
"""
    return body


def build_analysis() -> str:
    bt = load_json(MODEL / "backtest.json")
    lk = load_json(MODEL / "luck.json")
    co = load_json(MODEL / "correlations.json")

    lb = [[esc(r["strategy"]), f'{r["mae_margin"]:.2f}', f'{r["rmse_margin"]:.2f}',
           f'{r["mae_total"]:.2f}', f'{r["side_accuracy"]:.1%}',
           "—" if r["corr_margin"] is None else f'{r["corr_margin"]:+.3f}',
           badge("ok","rank 1") if r["strategy"]==bt["leaderboard"][0]["strategy"] else '<span class="muted">—</span>']
          for r in bt["leaderboard"]]

    luck_rows = []
    for r in lk["leaderboard"]:
        sig = r["survives_multiple_testing_5pct"]
        luck_rows.append([
            esc(r["strategy"]),
            f'{r["accuracy"]:.1%}',
            f'[{r["acc_ci95"][0]:.2f}, {r["acc_ci95"][1]:.2f}]',
            f'{r["p_value_vs_coinflip"]:.4f}',
            f'{r["p_value_holm_adjusted"]:.4f}',
            badge("ok","survives") if sig else badge("warn","not significant"),
            f'{r["brier"]:.3f}',
            f'{r["brier_skill_score"]:+.3f}',
            f'{r["units_at_assumed_price"] / r["n_decided"] * 100:+.1f}',
        ])

    corr_rows = [[esc(c["id"]), esc(c["relationship"]), "—" if c["r"] is None else f'{c["r"]:+.4f}',
                  esc(c["n"]),
                  f'[{c["ci95"][0]:+.3f}, {c["ci95"][1]:+.3f}]' if c["ci95"][0] is not None else "—",
                  "—" if c["p_value"] is None else f'{c["p_value"]:.4f}',
                  badge("warn","assume dependent") if c["independent_at_5pct"] is False else badge("ok","no detectable dependence"),
                  esc(c["note"])] for c in co["correlations"]]

    body = f"""
  <div class="grid">
    <div class="stat"><div class="label">Forward-test games</div><div class="value">{bt["n_games_evaluated"]}</div>
      <div class="muted">weeks {bt["weeks"][0]}–{bt["weeks"][-1]}, expanding window</div></div>
    <div class="stat"><div class="label">Best margin MAE</div><div class="value">{bt["leaderboard"][0]["mae_margin"]:.2f}</div>
      <div class="muted">{esc(bt["leaderboard"][0]["strategy"])}</div></div>
    <div class="stat"><div class="label">Significant after correction</div><div class="value">{"Yes" if lk["gate_summary"]["any_strategy_significant_after_multiple_testing"] else "No"}</div>
      <div class="muted">Holm–Bonferroni at 5%</div></div>
    <div class="stat"><div class="label">ATS measured</div><div class="value">No</div>
      <div class="muted">needs observed closing lines</div></div>
  </div>

  <h2>1 · Prediction accuracy against explicit baselines</h2>
  <p class="muted">Out-of-sample only: week <em>W</em> is predicted from weeks &lt; <em>W</em>.
  A lower MAE is better. Baselines are published so the model can be judged, not marketed.</p>
  {table(["Strategy","MAE margin","RMSE margin","MAE total","Winner accuracy","Corr(margin)",""], lb)}

  <div class="card" style="border-color:#ef4444">
    <h3>{badge("danger","Gate verdict")} {esc(bt["verdict"])}</h3>
    <p>Paired bootstrap, 10,000 resamples: {esc(bt["paired_bootstrap_model_vs_best_baseline"]["comparison"])},
    mean absolute-error difference
    <strong>{bt["paired_bootstrap_model_vs_best_baseline"]["mean_abs_err_difference"]:+.3f}</strong> points,
    95% CI [{bt["paired_bootstrap_model_vs_best_baseline"]["ci95"][0]:+.3f},
    {bt["paired_bootstrap_model_vs_best_baseline"]["ci95"][1]:+.3f}].
    P(model better) = {bt["paired_bootstrap_model_vs_best_baseline"]["p_model_better"]:.1%}.</p>
    <p class="muted">Translation: the sophisticated-looking ratings model does <strong>not</strong>
    improve on simply assuming an average game. Publishing it as a signal would be a false claim,
    so it is labelled a failure and withheld from any recommendation.</p>
  </div>

  <h2>2 · Removing luck</h2>
  <p class="muted">Metric: <strong>{esc(lk["metric_definition"]["metric"])}</strong>. Note that this is
  <strong>not</strong> {esc(lk["metric_definition"]["not_measured"])} —
  {esc(lk["metric_definition"]["why_ats_missing"])}</p>
  {table(["Strategy","Accuracy","95% CI","p vs coinflip","p (Holm)","Multiple testing","Brier","Brier skill","P/L per 100 bets @ −110 (scenario)"], luck_rows)}
  <p class="muted">The last column applies a fixed −110 price to every pick purely to express
  accuracy in units. <strong>It is not a market quote, not a realised return, and not evidence of
  profit</strong> — the same strategies have negative Brier skill, meaning their probabilities are
  worse than saying 50/50.</p>
  <div class="card">
    <h3>What this says</h3>
    <p>Two baseline strategies reach {lk["leaderboard"][0]["accuracy"]:.1%} straight-up accuracy, which looks
    impressive in isolation (p = {lk["leaderboard"][0]["p_value_vs_coinflip"]:.4f}). But four strategies were
    tested, so the honest threshold is the Holm-adjusted p-value of
    {lk["leaderboard"][0]["p_value_holm_adjusted"]:.4f} — <strong>not significant</strong>.
    Calibration is also poor in the extreme bucket (predicted
    {lk["leaderboard"][0]["calibration"][0]["mean_pred"]:.0%}, observed
    {lk["leaderboard"][0]["calibration"][0]["observed"]:.0%}), and Brier skill is
    {lk["leaderboard"][0]["brier_skill_score"]:+.3f}, i.e. worse than always saying 50/50.</p>
    <p class="muted">{esc(lk["metric_definition"]["interpretation_warning"])}</p>
    <p class="muted">{esc(lk["assumptions"]["note"])}</p>
  </div>

  <h2>3 · Correlation values</h2>
  <p class="muted">Computed from {co["n_games"]} verified games. These are the numbers required to size
  parlays and same-game combos; they are measured, not assumed.</p>
  {table(["ID","Relationship","r","n","95% CI","p","Verdict for parlay use","Note"], corr_rows)}
  <div class="card">
    <h3>Correlation findings that change decisions</h3>
    <ul>
      <li><strong>Home advantage is absent in this sample.</strong> Home teams won
        {co["home_win"]["rate"]:.1%} of decided games (95% CI
        {co["home_win"]["ci95"][0]:.1%}–{co["home_win"]["ci95"][1]:.1%}), which covers 50%.
        Any strategy that implicitly assumes a home edge is leaning on a factor the verified data
        does not currently support.</li>
      <li><strong>Points scored tracks opponent quality (r = {co["correlations"][2]["r"]:+.3f}).</strong>
        This is real dependence and is why legs from the same game must never be multiplied
        as if independent.</li>
      <li><strong>Margin and total are not independent enough to assume away</strong>
        (r = {co["correlations"][0]["r"]:+.3f}, p = {co["correlations"][0]["p_value"]:.3f}) —
        treat spread + total in one ticket as a dependent pair until a larger sample says otherwise.</li>
    </ul>
  </div>

  <h2>4 · Parlay arithmetic</h2>
  {table(["Legs","Assumed leg probability","Independent combination","Fair decimal odds","Break-even decimal at −110"],
    [[esc(p["legs"]), f'{p["assumed_leg_prob_each"]:.0%}', f'{p["independent_prob"]:.2%}',
      f'{p["fair_odds_decimal_independent"]:.2f}', f'{p["break_even_decimal_at_110_juice"]:.3f}']
     for p in co["parlay_math"]["rows"]])}
  <p class="muted">{esc(co["parlay_math"]["warning"])}</p>

  <h2>5 · What would change the verdict</h2>
  <div class="card">
    <ul>
      {''.join(f'<li>{esc(x)}</li>' for x in lk["gate_summary"]["required_before_any_real_use"])}
      <li>Re-run every week automatically as official results publish, so the sample grows without
        hand entry.</li>
    </ul>
  </div>
"""
    return body


def build_decisions() -> str:
    d = load_json(DATA / "decisions.json")
    q = load_json(DATA / "questions.json")
    sug = load_json(DATA / "suggestions.json")

    body = f"""
  <div class="card">
    <p>This page exists so a reviewer can choose a path <em>before</em> anything is implemented.
    Each item states the decision, the evidence available, the evidence still missing, and what
    would have to be true to proceed. Nothing here is approved.</p>
  </div>

  <h2>Decision register</h2>
  {table(["ID","Decision","Evidence we have","Evidence we lack","Recommendation","Blocking","Owner"],
    [[esc(x["id"]), f'<strong>{esc(x["decision"])}</strong>', esc(x["have"]), esc(x["lack"]),
      esc(x["recommendation"]), badge("danger","blocked") if x["blocking"] else badge("ok","ready"),
      esc(x["owner"])] for x in d])}

  <h2>Questions, information needed, and answers</h2>
  <p class="muted">Every row is a question a reasonable decision would have to answer. "Answer" is
  filled only where the verified data actually resolves it; otherwise it states precisely what is
  missing, which is itself the useful output.</p>
  {table(["#","Question","Information / evidence required","Answer from verified evidence","Status"],
    [[esc(x["id"]), esc(x["question"]), esc(x["requires"]), esc(x["answer"]),
      badge("ok","answered") if x["status"]=="answered" else
      (badge("warn","partial") if x["status"]=="partial" else badge("danger","unknown"))]
     for x in q])}

  <h2>Suggestions queue — pick a path, then implement</h2>
  {table(["Priority","Suggestion","Why it matters","What it costs / risks","Acceptance test"],
    [[esc(x["priority"]), f'<strong>{esc(x["suggestion"])}</strong>', esc(x["why"]),
      esc(x["cost"]), esc(x["acceptance"])] for x in sug])}
"""
    return body


def build_verified_index() -> str:
    files = sorted(p for p in DATA.rglob("*") if p.is_file())
    body = f"""
  <div class="card">
    <p>Every artifact this session produced, machine-readable, with the check that guards it.
    Items still unverified are not in here — they are on the
    <a href="flagged.html">Flagged for Review</a> page.</p>
  </div>
  <h2>Data files</h2>
  {table(["File","Rows","Carries source URL"],
    [[esc(str(p.relative_to(ROOT))), str(sum(1 for _ in p.open()) - 1) if p.suffix==".csv" else "—",
      badge("ok","yes") if p.suffix==".csv" else badge("warn","derived/no external claim")]
     for p in files])}
"""
    return body


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pages = {
        "data.html": ("Verified Data", "Official-source dataset, refreshed and re-checked automatically", build_data),
        # Session 65df4799-nfl1: renamed from lines.html — pipeline/gen_site.py owns
        # pages/lines.html ("My Lines"), and both generators were silently clobbering
        # each other on the same path. The verified sub-site's page keeps its content.
        "verified-lines.html": ("Own Lines", "Model-generated spreads and totals, with the validation verdict attached", build_lines),
        "analysis.html": ("Validation & Correlation", "Forward test, luck removal, and measured correlation values", build_analysis),
        "decisions.html": ("Decision Register", "Questions, missing information, and options to choose between", build_decisions),
        "verified.html": ("Verified Artifacts", "Everything generated from verified inputs", build_verified_index),
    }
    for fname, (title, subtitle, fn) in pages.items():
        sub = f"{subtitle} · generated {stamp}"
        (PAGES / fname).write_text(page(title, f"pages/{fname}", fn(), sub), encoding="utf-8")
        print("wrote pages/" + fname)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
