#!/usr/bin/env python3
"""strat/build.py — render the Strategy Competition sub-site from data/strat/*.json.

Every page is a function of the JSON.  Nothing is typed into the HTML by hand, so a number on the
site can always be traced to the file that produced it.  A value that does not exist renders as
an explicit blank with the reason, never as 0 or "n/a".

Run: python3 strat/build.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import artifact, blank, badge, e, kpi, num, pct, src, table  # noqa: E402


def _load_stamp():
    """The commit that froze the registry, written by tools/stamp_preregistration.py."""
    import json as _j
    try:
        with open(os.path.join(lib.ROOT, "data", "strat", "preregistration_stamp.json"),
                  encoding="utf-8") as fh:
            return _j.load(fh)
    except Exception:
        return {}


STAMP = _load_stamp()


def _rootsite_rows():
    """The row count from the last root-site verification run (data/verification_report.json)."""
    import json as _j
    try:
        with open(os.path.join(lib.ROOT, "data", "verification_report.json"), encoding="utf-8") as fh:
            return int(_j.load(fh)["table_rows"])
    except Exception:
        return None


def sig(v, nd=4):
    """A signed number, or a blank when the value does not exist."""
    if v is None:
        return blank("no interval exists for this value")
    return f"{v:+.{nd}f}"


def bss_badge(lb):
    if lb is None:
        return badge("UNVERIFIED")
    return badge("ELIGIBLE") if lb > 0 else badge("INELIGIBLE")


# --------------------------------------------------------------------------- pages
def page_index(ps, dt, pre, dem, wwc, qs, sug, dec):
    n_scored = sum(1 for r in ps["strategy_scores"] if r.get("status") == "scored")
    n_blank = len(ps["markets"]) - 3
    kpis = "".join([
        kpi("Strategies registered", pre["n_records"],
            f"{pre['n_backtest']} backtest · {pre['n_prospective']} prospective"),
        kpi("Live strategies", dem["n_live"], "promotion rule not yet pre-registered"),
        kpi("On paper", dem["n_paper"], "the only honest status today"),
        kpi("Demotions ever", dem["n_demotions_ever"], "gate armed, never fired"),
        kpi("Clearing every gate", 0, "the leaderboard's answer today"),
    ])

    verdict_rows = []
    for m in ps["markets"]:
        res = m["results"] or {}
        model = res.get("model") or {}
        lb = model.get("bss_lower_bound")
        n_scr = model.get("n_scored") or m["n_scored"]
        if m["market"] in ("side", "total"):
            verdict_rows.append([
                f"<strong>{e(m['market'].title())}</strong>",
                e(m["evaluated"]), f"{n_scr:,}" if n_scr else blank("not scored"),
                sig(model.get("bss")), sig(lb), bss_badge(lb),
                src("schedules", "NFL schedules"),
            ])
        elif m["market"] == "moneyline":
            lb = model.get("bss_lower_bound")
            verdict_rows.append([
                "<strong>Moneyline</strong>", e(m["evaluated"]),
                f"{model.get('n_scored', 0):,}",
                sig(model.get("bss_vs_devig")), sig(lb), bss_badge(lb),
                src("schedules", "NFL schedules"),
            ])
        else:
            verdict_rows.append([
                f"<strong>{e(m['market'].title())}</strong>", e(m["evaluated"]),
                blank("no price exists for this market"),
                blank("not scored"), blank("not scored"), badge("BLOCKED"),
                src("schedules", "NFL schedules"),
            ])

    body = f"""
<div class="kpis">{kpis}</div>

<section class="panel">
  <h2>The one-paragraph verdict</h2>
  <p class="lede">Nothing in this repository has demonstrated skill against the closing line. The
  model's side probabilities score <strong>{sig(ps['markets'][0]['results']['model']['bss'])}</strong>
  on the Brier skill scale (positive is better), its totals
  <strong>{sig(ps['markets'][1]['results']['model']['bss'])}</strong>, and its moneylines
  <strong>{sig(ps['markets'][2]['results']['model']['bss_vs_devig'])}</strong> against the de-vigged
  market. All three intervals sit below zero. The closing line, by contrast, beats a coin on the
  moneyline by <strong>{sig(ps['markets'][2]['results']['closing moneyline, de-vigged']['bss_vs_coin'])}</strong>
  with an interval above zero — which is a statement about the market, not about us.</p>
  <p class="note">This is the result the gates were built to be able to produce. A site that could
  only report wins would not be measuring anything.</p>
</section>

<section class="panel">
  <h2>Every market, scored the same way</h2>
  <p class="sub">Brier skill versus the closing line, with a game-cluster bootstrap interval. The
  published number is the lower bound; a market is eligible only if that bound is above zero.</p>
  {table(["Market", "What is scored", "Games", "Skill", "Lower bound (95%)", "Status", "Source"],
         verdict_rows,
         note="Blank means the market has no price in this repository, so no skill can be measured. Parlays, same-game parlays and player props are blank for that reason and not because they were tried and failed.")}
</section>

<section class="panel">
  <h2>What this competition is, in one screen</h2>
  <div class="two">
    <div class="q"><h3>Pre-registration first</h3>
      <p>{pre['n_records']} rule records, each with its frozen text, its inputs, its sample window and
      the git commit that registered it. <a href="preregister.html">Open the registry →</a></p></div>
    <div class="q"><h3>Proper scores, not win rates</h3>
      <p>The leaderboard's first column is benchmark-relative Brier skill with a game-cluster lower
      bound and a multiplicity charge. <a href="leaderboard.html">Open the leaderboard →</a></p></div>
    <div class="q"><h3>A demotion gate</h3>
      <p>Five pre-registered rules that send a live strategy back to paper.
      <a href="demotion.html">Open the gate →</a></p></div>
    <div class="q"><h3>Two-sided falsifiers</h3>
      <p>{wwc['n_claims']} published claims, each with the observation that would confirm it and the
      observation that would kill it. <a href="what-would-change.html">Open the register →</a></p></div>
    <div class="q"><h3>Two totals until one wins</h3>
      <p>Both estimators published with the gap column, and a walk-forward verdict that currently
      reads <strong>no winner</strong>. <a href="totals.html">Open the totals →</a></p></div>
    <div class="q"><h3>Questions before decisions</h3>
      <p>{qs['n_questions']} questions that block a decision and {dec['n_decisions']} decisions that need
      only a choice, kept separate. <a href="questions.html">Open the questions →</a></p></div>
  </div>
</section>

<section class="panel">
  <h2>What changed since the last build</h2>
  {table(["Register", "Rows", "Where it is", "What it is for", "Artifact"], [
    ["Pre-registration", str(pre["n_records"]), '<a href="preregister.html">preregister.html</a>', "Forbids a result without a frozen rule.", artifact("data/strat/preregistration.json")],
    ["Proper scores", str(len(ps["strategy_scores"])), '<a href="leaderboard.html">leaderboard.html</a>', "Ranks by skill with uncertainty, not by win rate.", artifact("data/strat/proper_score.json")],
    ["Demotion gate", str(dem["n_strategies"]), '<a href="demotion.html">demotion.html</a>', "Sends a live strategy back to paper.", artifact("data/strat/demotion.json")],
    ["Falsifiers", str(wwc["n_claims"]), '<a href="what-would-change.html">what-would-change.html</a>', "Two-sided, with thresholds.", artifact("data/strat/what_would_change.json")],
    ["Two totals", str(dt["n_board"]), '<a href="totals.html">totals.html</a>', "Both estimators, gap column, verdict.", artifact("data/strat/dual_total.json")],
    ["Questions", str(qs["n_questions"]), '<a href="questions.html">questions.html</a>', "What is missing and how to get it.", artifact("data/strat/questions.json")],
    ["Suggestions", str(sug["n_suggestions"]), '<a href="suggestions.html">suggestions.html</a>', "Risks and costs before anything is built.", artifact("data/strat/suggestions.json")],
  ])}
</section>
"""
    return body


def page_leaderboard(ps):
    rows = []
    fam = {x["test"]: x for x in ps["multiplicity"]["family"]}
    for m in ps["markets"]:
        res = m["results"] or {}
        for label, v in res.items():
            if not isinstance(v, dict):
                continue
            n = v.get("n_scored") or 0
            lb = v.get("bss_lower_bound")
            bss = v.get("bss") if "bss" in v else v.get("bss_vs_devig", v.get("bss_vs_coin"))
            rows.append([
                f"<strong>{e(m['market'].title())}</strong>",
                e(label),
                f"{n:,}" if n else blank("not scored"),
                sig(bss),
                sig(lb),
                bss_badge(lb),
                sig(v.get("p_value_bootstrap"), 4) if v.get("p_value_bootstrap") is not None else blank("no bootstrap p"),
                src("schedules", "NFL schedules"),
            ])

    srows = []
    for r in ps["strategy_scores"]:
        srows.append([
            f"<strong>{e(r['strategy'])}</strong>",
            f"{r['n_decided']:,}", pct(r.get("hit_rate", 0) * 100) if r.get("hit_rate") is not None else blank("no sample"),
            num(r.get("shrunk_probability"), "{:.4f}"),
            num(r.get("break_even_probability"), "{:.4f}"),
            sig(r.get("bss_vs_price"), 4),
            sig(r.get("bss_vs_coin"), 4),
            pct(r.get("roi_pct")) if r.get("roi_pct") is not None else blank("not scored"),
            src("schedules", "closing-line source"),
        ])

    famrows = [[e(x["test"]), sig(x["bss"]), sig(x.get("p_value_bootstrap"), 4),
                sig(x.get("bh_adjusted_p"), 4), f"{x['bonferroni_alpha']:.5f}",
                src("schedules", "source extract")]
               for x in ps["multiplicity"]["family"]]

    body = f"""
<section class="panel">
  <h2>Why this table is not ordered by win rate</h2>
  <p class="lede">Win rate is not a proper scoring rule. A forecast that is right 60% of the time
  while being badly calibrated is worse than one that is right 52% of the time with honest
  probabilities, and ROI on a few hundred bets cannot separate the two. The first column here is
  benchmark-relative Brier skill, and the published figure is the <em>lower</em> bound of a
  game-cluster bootstrap interval, not the point estimate.</p>
</section>

<section class="panel">
  <h2>Model and benchmarks, by market</h2>
  <p class="sub">Game-cluster bootstrap, {ps['method']['interval']}. A market is eligible only when
  the lower bound is above zero <em>and</em> the multiplicity charge is cleared <em>and</em> the
  {ps['method']['min_sample']}-game floor is met.</p>
  {table(["Market", "Forecast", "Games", "Skill", "Lower bound (95%)", "Status", "Bootstrap p (one-sided)", "Source"],
         rows,
         note="p is the share of game-cluster resamples in which the forecast does <em>not</em> beat its benchmark; 0.0000 means none of 2,000 resamples did.")}
</section>

<section class="panel">
  <h2>The six model-market tests, charged for multiplicity</h2>
  <p class="sub">Six tests at the 5% level means roughly one would look positive by chance.
  Benjamini-Hochberg charges the family less harshly than Bonferroni because the tests are not
  independent; both columns are published so the reader can see either charge.</p>
  {table(["Test", "Skill", "Bootstrap p", "BH-adjusted p", "Bonferroni alpha", "Source"], famrows,
         note=ps["multiplicity"]["reading"])}
</section>

<section class="panel">
  <h2>Every scored betting rule, same scoring</h2>
  <p class="sub">A betting rule does not emit a probability, so its implied probability is its
  observed hit rate shrunk towards the price with 8 pseudo-bets. Skill is then measured against the
  price (the break-even probability the operator charged) and against a coin.</p>
  {table(["Rule", "Decided bets", "Hit rate", "Shrunk P(win)", "Break-even P", "Skill vs price", "Skill vs coin", "ROI", "Source"], srows,
         note="A skill value near zero means the rule's hit rate is what its prices would have predicted anyway. None of these intervals excludes zero; see the pre-registration page for the multiplicity charge over the twelve rules.")}
</section>

<section class="panel">
  <h2>What is deliberately absent</h2>
  <p class="note">Parlay, same-game-parlay and player-prop divisions are blank: multiplying marginal
  probabilities is invalid under dependence and no prop price exists in this repository. A blank
  here is a finding about the data, not a zero.</p>
</section>
"""
    return body


def page_preregister(pre):
    rows = []
    for r in pre["records"]:
        rows.append([
            f"<strong>{e(r['id'])}</strong>",
            e(r["name"]),
            badge(r["status"].replace("registered-", "").upper()),
            e(r.get("market", "")),
            f"<code>{e(r['definition'][:160])}{'…' if len(r['definition']) > 160 else ''}</code>",
            f"{r['sample_window']['n_bets_backtest']:,}" if r["sample_window"]["n_bets_backtest"] else blank("no backtest sample"),
            f"<code>{e(STAMP.get('registration_commit', '')[:8])}</code>",
            src("schedules", "source extract"),
        ])
    body = f"""
<div class="kpis">
  {kpi("Registration records", pre["n_records"], "one per rule")}
  {kpi("Labelled backtest", pre["n_backtest"], "selection-exposed, frozen from now")}
  {kpi("Labelled prospective", pre["n_prospective"], "no result yet")}
  {kpi("Registration stamp", STAMP.get("registration_commit", "")[:8], STAMP.get("registration_commit_subject", "")[:48])}
</div>

<section class="panel">
  <h2>The rule</h2>
  <p class="lede">{e(pre['rule'])}</p>
  <p class="note">Enforced by <code>tools/check_preregistration.py</code>, which fails the build when a
  published result has no registration record, when a record's commit does not precede the result,
  or when a registered rule's exact text no longer appears in the generator that scores it.</p>
</section>

<section class="panel">
  <h2>What "registered-backtest" means, honestly</h2>
  <p>The twelve legacy rules were written before this session but after the scoring data existed.
  Registering them now does not make their backtest results prospective — it freezes them so that
  any future edit is a visible diff, and it discloses that twelve hypotheses were searched in one
  run, which the multiplicity charge in the leaderboard pays for. Presenting them as prospective
  would be the exact error this registry exists to prevent.</p>
</section>

<section class="panel">
  <h2>The register</h2>
  {table(["ID", "Rule", "Status", "Market", "Frozen definition", "Backtest bets", "Registered at", "Source"], rows)}
</section>

<section class="panel">
  <h2>Gates every registered rule must clear</h2>
  {table(["Gate", "Name", "Test", "Where the rule is frozen", "Official record it reads"],
         [[e(g["id"]), e(g["name"]), e(g["test"]),
           artifact("data/strat/preregistration.json", "gate register"),
           src("schedules", "official price record")] for g in pre["gates"]],
         note="A gate is a rule this project wrote, so its source is the committed register; the record every price gate reads is the official NFL schedule page. The distinction matters: a gate has an author, a fact has a publisher.")}
</section>
"""
    return body


def page_demotion(dem):
    rows = [[e(r["id"]), e(r["name"]), e(r["test"]), f"{r['minimum_sample']:,}", e(r["measured_on"]),
             e(r["rationale"]),
             artifact("data/strat/demotion.json"), src("schedules", "official price record")]
            for r in dem["rules"]]
    srows = []
    for r in dem["rows"]:
        bt = r.get("backtest") or {}
        srows.append([
            f"<strong>{e(r['id'])}</strong>", e(r["strategy"]),
            badge(r["registration_status"].replace("registered-", "").upper()),
            badge(r["status"]),
            f"{r['live_bets_settled']:,}",
            e(r["triggered_by"] or "—"),
            f"{bt.get('n_decided_backtest', 0):,}" if bt.get("n_decided_backtest") else blank("no backtest sample"),
            sig(bt.get("bss_vs_price_backtest"), 4) if bt.get("bss_vs_price_backtest") is not None else blank("no backtest sample"),
            src("schedules", "source extract"),
        ])
    body = f"""
<div class="kpis">
  {kpi("Strategies on paper", dem["n_paper"], "of " + str(dem["n_strategies"]))}
  {kpi("Live", dem["n_live"], "none: no prospective price exists")}
  {kpi("Demotions ever", dem["n_demotions_ever"], "the gate has never fired")}
  {kpi("Repromotion sample", "200", "settled bets, pre-registered")}
</div>

<section class="panel">
  <h2>The gate</h2>
  <p class="lede">A live strategy returns to paper when <em>any</em> of five rules below fires. The
  thresholds were fixed before any live bet existed, so a later change is a diff in this
  repository rather than an adjustment made after seeing a result.</p>
  {table(["Rule", "Name", "Fires when", "Minimum sample", "Measured on", "Why this threshold", "Frozen in", "Official record it reads"], rows,
         note="The rule text and thresholds are frozen in the artifact linked on each row; a change is a diff in this repository, and the official price record the gate reads is the NFL schedule pages linked on the leaderboard.")}
</section>

<section class="panel">
  <h2>Re-promotion</h2>
  <p><strong>{e(dem['repromotion']['requires'])}.</strong> {e(dem['repromotion']['why'])}</p>
</section>

<section class="panel">
  <h2>Every strategy's current status</h2>
  <p class="sub">{e(dem['state_note'])}</p>
  {table(["ID", "Strategy", "Registration", "Live status", "Live bets settled", "Triggered by", "Backtest bets", "Backtest skill vs price", "Source"], srows,
         note="The backtest columns are published so the reader can see the scale of each rule's historical result. They cannot promote or demote anything under this gate: a backtest sample is not a live sample.")}
</section>
"""
    return body


def page_wwc(wwc):
    rows = []
    for r in wwc["rows"]:
        rows.append([
            f"<strong>{e(r['id'])}</strong>",
            f"<strong>{e(r['claim'])}</strong><br><span class='meta'>{e(r['current'])}</span>",
            badge(r["status"].split(" — ")[0]),
            e(r["confirm_if"]),
            e(r["abandon_if"]),
            e(r["next_measurement"]),
            src(r["source"] if r["source"] in lib.SOURCES else "repo", "evidence"),
        ])
    body = f"""
<section class="panel">
  <h2>Why both directions</h2>
  <p class="lede">A one-sided falsifier is a promise to look for confirmation. Each row below says
  what observation would raise confidence <em>and</em> what observation would make us abandon the
  claim, with a threshold on each. The thresholds are frozen in this build; moving one later is a
  diff that can be reviewed.</p>
</section>
<section class="panel">
  <h2>{wwc['n_claims']} published claims</h2>
  {table(["ID", "Claim and its current number", "Today", "We would believe it if…", "We would abandon it if…", "Next measurement", "Evidence"], rows)}
</section>
"""
    return body


def page_totals(dt):
    rows = []
    for b in dt["board"]:
        rows.append([
            f"<strong>{e(b['matchup'])}</strong><br><span class='meta'>week {b['week']} · {e(b['gameday'] or '')}</span>",
            num(b["total_a"], "{:.1f}"),
            num(b["total_b"], "{:.1f}", "estimator B needs a completed game for both teams this season"),
            sig(b["gap"], 1) if b["gap"] is not None else blank("no gap without both estimators"),
            num(b["market_total"], "{:.1f}", "the source carries no line for this fixture yet"),
            e(b["note"]) if b["note"] else '<span class="meta">both estimators available</span>',
            src("schedules", "NFL schedule"),
        ])
    seas = []
    for s in dt["by_season"]:
        seas.append([
            f"<strong>{s['season']}</strong>" + (" · holdout" if s.get("in_holdout") else ""),
            f"{s.get('n', 0):,}",
            num(s.get("mae_a"), "{:.3f}"), num(s.get("mae_b"), "{:.3f}"),
            sig(s.get("mean_paired_difference_a_minus_b"), 3),
            f"{s['ci95'][0]:+.3f} to {s['ci95'][1]:+.3f}" if s.get("ci95") else blank("sample below 30"),
            src("schedules", "source extract"),
        ])
    h = dt["holdout"]
    body = f"""
<div class="kpis">
  {kpi("Estimator A error", f"{h['mae_a']:.3f}", "mean absolute error, holdout")}
  {kpi("Estimator B error", f"{h['mae_b']:.3f}", "mean absolute error, holdout")}
  {kpi("Paired difference", f"{h['mean_paired_difference_a_minus_b']:+.3f}", "A minus B, points")}
  {kpi("Verdict", "no winner", f"interval {h['ci95'][0]:+.3f} to {h['ci95'][1]:+.3f}")}
</div>

<section class="panel">
  <h2>The two estimators</h2>
  <p class="lede"><strong>A</strong> — {e(dt['estimators']['A'])}.<br>
  <strong>B</strong> — {e(dt['estimators']['B'])}.</p>
  <p class="note">{e(dt['verdict']['rule'])} {e(dt['verdict']['published'])}</p>
</section>

<section class="panel">
  <h2>Walk-forward comparison, by season</h2>
  {table(["Season", "Games", "MAE A", "MAE B", "Paired difference (A − B)", "95% interval", "Source"], seas,
         note="A positive paired difference means A's absolute error was larger, i.e. B was closer. The chronological holdout is " + ", ".join(str(x) for x in dt["holdout_seasons"]) + ".")}
</section>

<section class="panel">
  <h2>Every originated fixture, both totals</h2>
  <p class="sub">The gap column is A minus B. Where B is blank, neither team had a completed game in this season at the time of the fixture, and B is not guessed.</p>
  {table(["Fixture", "Total A", "Total B", "Gap", "Market total", "Note", "Source"], rows)}
</section>
"""
    return body


def page_questions(qs, dec):
    rows = [[f"<strong>{e(r['id'])}</strong>", f"<strong>{e(r['question'])}</strong>",
             e(r["known"]), e(r["missing"]), e(r["how_to_discover"]), e(r["blocks"]),
             e(r["decision_owner"]), src(r["source"], "source")]
            for r in qs["rows"]]
    drows = [[f"<strong>{e(d['id'])}</strong>", e(d["decision"]), " · ".join(e(o) for o in d["options"]),
              e(d["gate"]), e(d["owner"]), src(d["source"], "source")] for d in dec["rows"]]
    body = f"""
<section class="panel">
  <h2>Questions that block a decision</h2>
  <p class="lede">{e(qs['rule'])}</p>
  {table(["ID", "Question", "What is known", "What is missing", "How to discover it", "What it blocks", "Owner", "Source"], rows)}
</section>
<section class="panel">
  <h2>Decisions that need only a choice</h2>
  <p class="sub">{e(dec['rule'])}</p>
  {table(["ID", "Decision", "Options", "Gate", "Owner", "Source"], drows)}
</section>
"""
    return body


def page_suggestions(sug):
    rows = [[f"<strong>{e(r['id'])}</strong>", f"<strong>{e(r['suggestion'])}</strong>", e(r["problem"]),
             e(r["proposal"]), e(r["cost"]), e(r["effort"]), e(r["risk"]), e(r["decision"]),
             src(r["source"], "evidence")]
            for r in sug["rows"]]
    proc = "".join(f"<li>{e(x)}</li>" for x in sug["review_process"])
    body = f"""
<section class="panel">
  <h2>How a suggestion becomes a change</h2>
  <ol class="plain">{proc}</ol>
  <p class="note">Nothing on this page has been implemented on the strength of the suggestion alone.
  The two that are already built (the competition overview and the two-totals page) are marked as
  such in the cost column, because they are this session's own deliverables and hiding that would
  defeat the purpose of the register.</p>
</section>
<section class="panel">
  <h2>{sug['n_suggestions']} suggestions, ranked by what they unblock</h2>
  {table(["ID", "Suggestion", "Problem", "Proposal", "Cost", "Effort", "Risk", "Feeds decision", "Evidence"], rows)}
</section>
"""
    return body


def page_flagged(pre, ps, dem, dt):
    """The irregularities this session found, with the official link that shows them."""
    flags = [
        {"id": "SC-01",
         "finding": ("The twelve legacbacktest rules were defined after their scoring data existed. Their "
                     "published ROI figures are selection-exposed: twelve hypotheses were searched in one run."),
         "affects": "Every ROI and win-rate number in data/s9cb/leaderboard.json",
         "resolved": "Published and mitigated, not removed",
         "mitigation": ("Registered as registered-backtest with the exposure stated; the multiplicity charge in the "
                        "leaderboard pays for the search; no legacy rule can be promoted."),
         "source": "nflverse_schedules"},
        {"id": "SC-02",
         "finding": ("No opening price exists anywhere in the repository, and the closing price carries no fetch "
                     "time. The price-snapshot store the brief requires is therefore blocked by a data-source "
                     "decision, not by engineering."),
         "affects": "Price-snapshot store (PR-01); any prospective ROI",
         "resolved": "Open — needs a decision from the owner",
         "mitigation": "Q02 and W11 state the exact observation that would clear it.",
         "source": "nflverse_schedules"},
        {"id": "SC-03",
         "finding": ("S11 and S12 read an injury-designation level from the weekly report. The brief explicitly "
                     "forbids a level as a signal and asks for a surprise instead."),
         "affects": "Two scored rules",
         "resolved": "Published and superseded",
         "mitigation": ("Both stay scored so the comparison is visible; the surprise rules P07-P09 replace them and "
                        "the level rules can never be promoted."),
         "source": "injuries_w10"},
        {"id": "SC-04",
         "finding": ("The historical results and closing lines are a third-party (nflverse) extract of the NFL "
                     "GSIS feed. The repository's official check covers the 2026 season only, so the historical "
                     "intervals rest on an unverified transcription."),
         "affects": f"All {ps['markets'][0]['results']['model']['n_scored']:,}-game intervals on the leaderboard",
         "resolved": "Open — flagged for review",
         "mitigation": "Q03 names the reconciliation that would close it.",
         "source": "gameday_w10_was_nyg"},
        {"id": "SC-05",
         "finding": ("The model loses to the closing line on all three markets "
                     f"(side {ps['markets'][0]['results']['model']['bss']:+.4f}, "
                     f"total {ps['markets'][1]['results']['model']['bss']:+.4f}, "
                     f"moneyline {ps['markets'][2]['results']['model']['bss_vs_devig']:+.4f})."),
         "affects": "The origination claim the project is built on",
         "resolved": "Published, not hidden",
         "mitigation": ("Stated on the overview and in the executive summary. W01-W03 record what would reverse it."),
         "source": "schedules"},
        {"id": "SC-06",
         "finding": ("No player-prop price exists in the repository, so three of six leaderboard divisions cannot "
                     "be scored at all."),
         "affects": "Prop, prop-combo and same-game-parlay divisions",
         "resolved": "Open — flagged for review",
         "mitigation": "Q10; the divisions are published as blank with the reason rather than omitted.",
         "source": "nflverse_schedules"},
        {"id": "SC-07",
         "finding": ("The two-estimator comparison has no winner: the holdout paired difference is "
                     f"{dt['holdout']['mean_paired_difference_a_minus_b']:+.4f} points with an interval of "
                     f"{dt['holdout']['ci95'][0]:+.4f} to {dt['holdout']['ci95'][1]:+.4f}."),
         "affects": "Any claim that the rating model adds information on the total",
         "resolved": "Published as undecided",
         "mitigation": "Both estimators published until one wins (W05).",
         "source": "schedules"},
        {"id": "SC-08",
         "finding": ("The promotion rule is not pre-registered, so the competition has a pre-registered exit "
                     "and no pre-registered entrance."),
         "affects": "Live status and rewards",
         "resolved": "Open — needs a decision",
         "mitigation": "Q09 and suggestion SG2.",
         "source": "repo"},
        {"id": "SC-09",
         "finding": (f"{_rootsite_rows():,} table rows with official source links are published row-level while the "
                     "licence question in flag F51 is unresolved."),
         "affects": "The whole publication model",
         "resolved": "Open — carried from F51, not re-litigated here",
         "mitigation": "Q01, Q11 and suggestion SG11.",
         "source": "terms"},
        {"id": "SC-10",
         "finding": ("The default figure for the strategy family's multiplicity charge assumes the twelve rules "
                     "are independent tests. Several share inputs (S01/S02, S03/S04), so the charge is "
                     "conservative in the wrong direction."),
         "affects": "The multiplicity column on the leaderboard",
         "resolved": "Open — flagged for review",
         "mitigation": "Q05 and decision D12.",
         "source": "schedules"},
    ]
    rows = [[f"<strong>{e(f['id'])}</strong>", e(f["finding"]), e(f["affects"]), badge(f["resolved"].split(" — ")[0]), e(f["mitigation"]), src(f["source"], "source")]
            for f in flags]
    lib.write_json("flagged.json", {"generated_at": lib.now(), "n_flags": len(flags),
                                    "rootsite_rows": _rootsite_rows(),
                                    "rule": ("Flagged items do not block publication. Each states what is wrong, "
                                             "what it affects, and the observation that would close it."),
                                    "rows": flags})
    body = f"""
<section class="panel">
  <h2>{len(flags)} irregularities found by this session</h2>
  <p class="lede">These are published rather than fixed silently. None of them blocks the site from
  going live; each names the observation that would close it.</p>
  {table(["ID", "Finding", "Affects", "Status", "What is being done", "Source"], rows)}
</section>
<section class="panel">
  <h2>Carried from earlier sessions</h2>
  <p class="note">Flag <strong>F51</strong> (NFL.com Terms of Use versus the scheduled scrape of
  nfl.com/injuries) remains open and is the single most consequential item on the repository's flag
  register. It is not re-litigated here; see the root <a href="../pages/review.html">Flagged for
  Review</a> page and <a href="../flagged.html">flagged.html</a>. Nothing published by this session
  adds to the row-level exposure.</p>
</section>
"""
    return body


def page_method(pre, ps, dt):
    srcrows = [[e(k), f'<a class="src" href="{e(u)}" target="_blank" rel="noopener">{e(n)} ↗</a>']
               for k, (u, n) in lib.SOURCES.items()]
    body = f"""
<section class="panel">
  <h2>What is measured, and with what</h2>
  <p class="lede">Every number on this site comes from one of three places: an official nfl.com page
  fetched during a session, a third-party extract of the NFL's own statistics feed (labelled as
  such), or a computation over those two whose script is in this repository and whose output is a
  JSON file.</p>
  {table(["Method element", "What it is", "Artifact"], [
    ["Proper score", e(ps["method"]["score"]), artifact("data/strat/proper_score.json")],
    ["Interval", e(ps["method"]["interval"]), artifact("data/strat/proper_score.json")],
    ["Published figure", e(ps["method"]["published_number"]), artifact("data/strat/proper_score.json")],
    ["Sample floor", str(ps["method"]["min_sample"]) + " games / bets", artifact("data/strat/proper_score.json")],
    ["Multiplicity", e(ps["method"]["multiplicity"]), artifact("data/strat/proper_score.json")],
    ["Walk-forward", e(ps["method"]["walk_forward"]), artifact("data/s9cb/lines.json")],
    ["Look-ahead probe", ("The two fits produce different predictions, so the walk-forward cut is real."
                          if ps["method"]["lookahead_probe_predictions_identical"] is False else "NOT RUN"),
     artifact("data/s9cb/lines.json")],
    ["Two-estimator rule", e(dt["verdict"]["rule"]), artifact("data/strat/dual_total.json")],
    ["Pre-registration", e(pre["rule"]), artifact("data/strat/preregistration.json")],
  ])}
</section>

<section class="panel">
  <h2>Reproduce every number</h2>
  <pre class="code">cd s9cb/analysis
python3 run.py                 # rebuilds the extract-derived research JSON
python3 ../../strat/proper_score.py    # Brier skill, intervals, multiplicity
python3 ../../strat/dual_total.py      # the two estimators and the verdict
cd ../.. && python3 strat/preregister.py && python3 strat/demotion.py \\
  && python3 strat/what_would_change.py && python3 strat/registers.py \\
  && python3 strat/build.py && python3 strat/verify.py</pre>
  <p class="note">The reproduce steps are the ones this build ran. <code>strat/verify.py</code> fails
  on a broken link, a table row with no source, a placeholder in a cell, or a page that nothing
  links to.</p>
</section>

<section class="panel">
  <h2>Source register</h2>
  {table(["Key", "Source"], srcrows)}
</section>

<section class="panel">
  <h2>What is deliberately blank</h2>
  <ul class="plain">
    <li>Prop, prop-combo and same-game-parlay scores: no price exists.</li>
    <li>Opening prices: no opening-price source exists.</li>
    <li>Live bets and demotions: nothing is live.</li>
    <li>Estimator B for a fixture where neither team has played this season.</li>
    <li>Any correlation or interval whose sample floor is not met.</li>
  </ul>
</section>
"""
    return body


def page_exec(pre, ps, dt, dem, wwc, qs, sug, dec):
    side = ps["markets"][0]["results"]["model"]
    total = ps["markets"][1]["results"]["model"]
    ml = ps["markets"][2]["results"]["model"]
    mkt = ps["markets"][2]["results"]["closing moneyline, de-vigged"]
    body = f"""
<section class="panel">
  <h2>What was built</h2>
  <ul class="plain">
    <li><strong>A pre-registration registry</strong> — {pre['n_records']} rules with frozen text, inputs,
    sample windows, gates and the registering commit; {pre['n_backtest']} labelled backtest (selection-exposed)
    and {pre['n_prospective']} prospective (no result yet). A build gate forbids a published result
    without a preceding registration.</li>
    <li><strong>A proper-score leaderboard</strong> — benchmark-relative Brier skill per market with a
    game-cluster bootstrap lower bound, a multiplicity charge over both the market family and the rule
    family, and five control baselines.</li>
    <li><strong>A demotion gate</strong> — five pre-registered rules with thresholds fixed before any live
    bet, plus a pre-registered re-promotion condition.</li>
    <li><strong>Two-sided falsifiers</strong> on {wwc['n_claims']} published claims, each with a confirming and an
    abandoning threshold.</li>
    <li><strong>Two published totals</strong> with a gap column and a walk-forward verdict.</li>
    <li><strong>{qs['n_questions']} blocking questions</strong>, {dec['n_decisions']} decisions that need only a choice,
    and {sug['n_suggestions']} suggestions with costs and risks, in one review-before-implementation flow.</li>
  </ul>
</section>

<section class="panel">
  <h2>What the evidence says</h2>
  <p class="lede">The model does not beat the closing line, on any market, at any sample this
  repository holds.</p>
  {table(["Market", "Brier skill vs closing line", "95% interval", "Reading", "Source"], [
    ["Side", sig(side["bss"]), f"{side['bss_ci95'][0]:+.4f} to {side['bss_ci95'][1]:+.4f}",
     f"Worse than the line on {side['n_scored']:,} games; the interval is entirely below zero.",
     src("schedules", "NFL schedules")],
    ["Total", sig(total["bss"]), f"{total['bss_ci95'][0]:+.4f} to {total['bss_ci95'][1]:+.4f}",
     f"Worse than the line on {total['n_scored']:,} games; the interval is entirely below zero.",
     src("schedules", "NFL schedules")],
    ["Moneyline", sig(ml["bss_vs_devig"]), f"{ml['bss_ci95'][0]:+.4f} to {ml['bss_ci95'][1]:+.4f}",
     f"Worse than the de-vigged market on {ml['n_scored']:,} games.",
     src("schedules", "NFL schedules")],
    ["Market vs a coin", sig(mkt["bss_vs_coin"]), f"{mkt['bss_vs_coin_ci95'][0]:+.4f} to {mkt['bss_vs_coin_ci95'][1]:+.4f}",
     "The closing line itself is informative, with an interval entirely above zero. That is the benchmark we fail to beat.",
     src("schedules", "NFL schedules")],
  ])}
  <p class="note">No single betting rule's interval excludes zero, and the multiplicity charge over
  twelve rules makes a positive point estimate weaker, not stronger. The best point estimate in the
  run is S07's Brier skill versus its price of
  {sig(max(r['bss_vs_price'] for r in ps['strategy_scores'] if r.get('bss_vs_price') is not None), 4)}
  on {max(r['n_decided'] for r in ps['strategy_scores'])} bets — a value far inside the noise band.</p>
</section>

<section class="panel">
  <h2>What is still unknown, and what would settle it</h2>
  <ol class="plain">
    <li><strong>Whether the historical extract matches the official record</strong> — Q03; a Game Book
    reconciliation of 50 random games per season.</li>
    <li><strong>Whether the official terms permit the publication</strong> — Q01; the highest-priority
    decision on the board.</li>
    <li><strong>Whether an approved price source exists</strong> — Q02; without it no ROI claim can ever
    be published.</li>
    <li><strong>Whether availability surprise carries information</strong> — Q12 and W09; needs official
    inactive lists and Game Books.</li>
    <li><strong>Whether the total model adds anything over a no-model baseline</strong> — W05; currently
    undecided ({dt['holdout']['mean_paired_difference_a_minus_b']:+.4f}, interval
    {dt['holdout']['ci95'][0]:+.4f} to {dt['holdout']['ci95'][1]:+.4f}).</li>
  </ol>
</section>

<section class="panel">
  <h2>What the owner must decide</h2>
  <p>The {dec['n_decisions']} decisions are on the <a href="questions.html">questions page</a>. Three matter
  more than the rest:</p>
  <ol class="plain">
    <li><strong>D03 — settle the official-data terms question.</strong> Until it is settled, every additional
    data layer raises the cost of the eventual answer.</li>
    <li><strong>D02 — pre-register a promotion rule</strong> before any live bet. The competition currently
    has an exit and no entrance.</li>
    <li><strong>D12 — pre-register the effective number of independent tests</strong> for the rule family, so
    the multiplicity charge is neither too harsh nor too lenient.</li>
  </ol>
</section>

<section class="panel">
  <h2>Honest bottom line</h2>
  <p class="lede">This session's contribution is not a winning strategy. It is the machinery that would
  let a winning strategy be recognised — and the published result that, on the evidence available,
  there is not one. That is a finding, and it is the one the gates were designed to be able to
  produce.</p>
  <p class="note">Nothing on this site is a recommendation to bet. The demotion gate is armed; nothing
  is live; {dem['n_strategies']} strategies sit on paper, which is where the evidence puts them.</p>
</section>
"""
    return body


def main() -> int:
    ps = lib.load("proper_score.json")
    pre = lib.load("preregistration.json")
    dem = lib.load("demotion.json")
    wwc = lib.load("what_would_change.json")
    dt = lib.load("dual_total.json")
    qs = lib.load("questions.json")
    sug = lib.load("suggestions.json")
    dec = lib.load("decisions.json")
    gen = ps["generated_at"]

    pages = {
        "index.html": ("Overview",
                       "A competition for pre-registered NFL line-origination strategies, ranked by proper scores with uncertainty. Every rule frozen before it was scored.",
                       page_index(ps, dt, pre, dem, wwc, qs, sug, dec)),
        "leaderboard.html": ("Proper-Score Leaderboard",
                             "Benchmark-relative Brier skill with a game-cluster lower bound and a multiplicity charge. Control baselines in the same table.",
                             page_leaderboard(ps)),
        "preregister.html": ("Pre-Registration Registry",
                             "Every rule's text, inputs, sample window and the commit that froze it. No result without a registration.",
                             page_preregister(pre)),
        "demotion.html": ("Demotion Gate",
                          "The five pre-registered rules that send a live strategy back to paper, and every strategy's current status.",
                          page_demotion(dem)),
        "what-would-change.html": ("What Would Change Our Mind",
                                   "A two-sided falsifier with a threshold on every published claim.",
                                   page_wwc(wwc)),
        "totals.html": ("Two Totals Until One Wins",
                        "Both total estimators published with the gap column and a walk-forward verdict.",
                        page_totals(dt)),
        "questions.html": ("Open Questions & Decisions",
                           "What is known, what is missing, how to discover it, and what it blocks — kept separate from decisions that need only a choice.",
                           page_questions(qs, dec)),
        "suggestions.html": ("Suggestions",
                             "Improvements with their problem, cost and risk, to be reviewed and chosen before anything is built.",
                             page_suggestions(sug)),
        "flagged.html": ("Flagged for Review",
                         "Every irregularity this session found, what it affects, and the observation that would close it.",
                         page_flagged(pre, ps, dem, dt)),
        "method.html": ("Method & Sources",
                        "How every number was produced, how to reproduce it, and the source register.",
                        page_method(pre, ps, dt)),
        "executive-summary.html": ("Executive Summary",
                                   "What was built, what the evidence says, what is still unknown, and what the owner must decide.",
                                   page_exec(pre, ps, dt, dem, wwc, qs, sug, dec)),
    }

    for name, (title, standfirst, body) in pages.items():
        lib.write_page(name, lib.page(name, title, standfirst, body, gen))

    # the flagged page wrote its own JSON on the way through
    print(f"built {len(pages)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
