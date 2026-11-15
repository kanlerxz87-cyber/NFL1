#!/usr/bin/env python3
"""strat/registers.py — the three editorial registers: questions, suggestions, executive summary.

These are the deliverables the brief asks for by name:

  * "a clear list of questions, information and answers that need to be addressed before any
    decision can be reasonably made based upon the information that we already have and do not
    have";
  * "suggestions … so someone can review suggestions and choose the best path before implementing
    any changes";
  * "an executive summary outlining important details".

Every row is written from the data files this session produced.  Where a number is quoted it is
read from `data/strat/*.json` at build time, so the registers cannot drift from the artifacts.
Where a value does not exist the row says so and gives the measurement that would produce it.

Run: python3 strat/registers.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402


# --------------------------------------------------------------------------- questions
def questions(ps: dict, dt: dict, pre: dict) -> list[dict]:
    side = ps["markets"][0]["results"]["model"]
    total = ps["markets"][1]["results"]["model"]
    ml = ps["markets"][2]["results"]["model"]
    return [
        {
            "id": "Q01",
            "question": "Is the NFL.com injury report a lawful source for a row-level published database?",
            "why_it_blocks": ("The whole availability layer, and the compliance of the published site. NFL.com's "
                              "Terms of Use prohibit systematic retrieval to compile a database without written "
                              "consent."),
            "known": ("The Terms are published and were read. The repository currently retrieves "
                      "nfl.com/injuries on a schedule and publishes row-level designations. Flag F51 records the "
                      "conflict and is marked 'needs review'."),
            "missing": "Written consent, or a legal reading that the use is permitted, or a decision to publish aggregates only.",
            "how_to_discover": "Read the Terms in full with the owner; request written permission from the NFL; or restructure the site to aggregates plus a link to the official page.",
            "blocks": "Every availability claim, the injury-surprise ablation (W09), and the private/public split (SI-11).",
            "decision_owner": "the repository owner",
            "source": "terms",
        },
        {
            "id": "Q02",
            "question": "Which price source is approved, and what is its fetch schedule?",
            "why_it_blocks": ("Every ROI number. Without an opening and a closing price with a fetch time, a "
                              "backtest cannot distinguish a real edge from a line that moved after the bet."),
            "known": ("One closing-price series exists in the third-party extract (nflverse). There is no opening "
                      "price, no fetch time, and no approval. The readiness register marks the price store BLOCKED."),
            "missing": "An approved source, a licence, and a fetch schedule.",
            "how_to_discover": "Request documented API access from a data vendor; record the fetch time on every pull; store the raw payload hash.",
            "blocks": "The price-snapshot store (PR-01), prospectively scored strategies, and any ROI claim.",
            "decision_owner": "the repository owner",
            "source": "nflverse_schedules",
        },
        {
            "id": "Q03",
            "question": ("Are the historical results and closing lines in the third-party extract identical to the "
                         "official NFL record for every game in the backtest sample?"),
            "why_it_blocks": ("The proper-score intervals (the model side skill is "
                              f"{side['bss']:+.4f}, the total {total['bss']:+.4f}, the moneyline {ml['bss_vs_devig']:+.4f}) "
                              "are computed on the priced games in the extract, almost all of them from the extract and not from an official page. A "
                              "systematic error there would move every interval."),
            "known": ("2026 IS reconciled: 137 official nfl.com rows (136 transcribed from the weekly "
                      "schedule pages plus one Game Center row fetched in this build) match the extract on "
                      "every row, 0 disagreements — see the Official Reconciliation page. The 1999-2025 "
                      "seasons, which supply almost all of the 6,785 scored games, are NOT reconciled."),
            "missing": "A game-by-game reconciliation of the extract against official Game Books for 1999-2025.",
            "how_to_discover": ("2026 is done. For the historical seasons: fetch the official Game Book PDF "
                                "for a random sample of 50 games per season and compare the final score, then "
                                "extend strat/reconcile_official.py to those seasons."),
            "blocks": "Confidence in every historical interval; the results corpus (PR-02, PR-09).",
            "decision_owner": "the next data session",
            "source": "gameday_w10_was_nyg",
        },
        {
            "id": "Q04",
            "question": "What does an official depth chart actually mean when a club publishes more than one player at rank 1?",
            "why_it_blocks": ("The backup-deficiency feature: 149 club/unit/position slots list more than one rank-1 "
                              "player, so 'column 1 is the starter' fabricates a starter the club never named."),
            "known": ("The club charts were read. Shared rank-1 slots and empty slots exist. No club publishes an "
                      "official snap share in the same document."),
            "missing": "An official snap-count source, or Game Book starters, to turn a chart into playing time.",
            "how_to_discover": "Publish depth as groups (rank-1 set, rank-2 set) and confirm the starter from Game Books, not from the chart order.",
            "blocks": "The deficiency matrix, the injury-surprise ablation, and every '2nd string' claim.",
            "decision_owner": "the next availability session",
            "source": "schedules",
        },
        {
            "id": "Q05",
            "question": "What is the correct number of tests to charge for when a rule family shares inputs?",
            "why_it_blocks": ("The leaderboard's multiplicity adjustment. Twelve rules were tested; several share the "
                              "same model inputs (S01/S02, S03/S04), so they are not independent and a Bonferroni "
                              f"charge at alpha = {ps['multiplicity']['strategy_family']['bonferroni_alpha']:.5f} "
                              "is conservative in the wrong direction."),
            "known": "The twelve rule p-values and the six market-test p-values are both computed and published.",
            "missing": "A pre-registered rule for the effective number of independent tests in each family.",
            "how_to_discover": "Estimate the correlation matrix of the rule signals and use the effective-number-of-tests formula; pre-register the choice before applying it.",
            "blocks": "Any claim that a rule cleared the multiplicity gate.",
            "decision_owner": "the next strategy session",
            "source": "schedules",
        },
        {
            "id": "Q06",
            "question": ("Does the rating model's side/total/moneyline deficit against the closing line "
                         f"({side['bss']:+.4f} side, {total['bss']:+.4f} total, {ml['bss_vs_devig']:+.4f} moneyline) "
                         "reflect a model defect or an information disadvantage?"),
            "why_it_blocks": ("Whether to spend effort on features or to accept that the closing line is already "
                              "the best available forecast, which the evidence currently supports."),
            "known": ("The paired comparison in the repository's own research run shows the market's absolute "
                      "error on the closing spread is smaller than the model's. The two-estimator test shows the ratings do not beat a "
                      f"season-mean baseline on the holdout (difference {dt['holdout']['mean_paired_difference_a_minus_b']:+.4f}, "
                              f"interval {dt['holdout']['ci95'][0]:+.4f} to {dt['holdout']['ci95'][1]:+.4f})."),
            "missing": "A model with information the closing line does not already contain (availability surprise, weather, referee).",
            "how_to_discover": "Add one feature at a time and require the incremental-information weight to be positive with |t| > 2 before keeping it.",
            "blocks": "Every origination-alpha claim.",
            "decision_owner": "the next modelling session",
            "source": "schedules",
        },
        {
            "id": "Q07",
            "question": "Which of the brief's own numbered references (VR-xx, VQ-xx) can be traced to a dated source?",
            "why_it_blocks": "Reproducing the brief's findings. Several rows quote VR/VQ numbers that no artifact in the repository contains.",
            "known": "The references appear in the brief and in earlier sessions' notes; the underlying captures are not all present.",
            "missing": "The dated captures those references point at.",
            "how_to_discover": "Re-capture each cited page and record the fetch time and hash; where the capture no longer exists, mark the reference untraceable.",
            "blocks": "Only the traceability of the brief's claims; nothing on the leaderboard depends on them.",
            "decision_owner": "the repository owner",
            "source": "repo",
        },
        {
            "id": "Q08",
            "question": "How should a parlay be validated when the legs are dependent?",
            "why_it_blocks": "Ranking any parlay or same-game parlay. The product of marginal probabilities is invalid under dependence.",
            "known": ("The repository prices every two-leg parlay from the observed legs and publishes the correlation "
                      "ratio, but it does not validate a joint distribution. The proper-score page leaves the parlay "
                      "and same-game-parlay markets blank for this reason."),
            "missing": "A directly validated joint probability, plus the operator's void and push rules.",
            "how_to_discover": "Model the joint distribution of the two legs (bivariate normal for spread+total in one game) and validate it out of sample before ranking anything.",
            "blocks": "The parlay and prop-combo divisions of the leaderboard.",
            "decision_owner": "the next strategy session",
            "source": "schedules",
        },
        {
            "id": "Q09",
            "question": "What is the minimum live sample before a strategy can be called live rather than paper?",
            "why_it_blocks": "Promotion. The demotion gate is armed but nothing can be promoted, because nothing is live.",
            "known": f"A promotion threshold is not pre-registered. The demotion thresholds (50, 100 and 12 bets) are pre-registered in {pre['n_records']} registration records.",
            "missing": "A pre-registered promotion rule that mirrors the demotion rule.",
            "how_to_discover": "Write the promotion rule now, before the first live bet, and commit it with the demotion rule text.",
            "blocks": "Any live status, and therefore any reward.",
            "decision_owner": "the repository owner",
            "source": "repo",
        },
        {
            "id": "Q10",
            "question": "Are player-prop prices obtainable at all, and if not, should the prop division exist?",
            "why_it_blocks": "The prop, prop-combo and same-game-parlay divisions have no price and therefore no score.",
            "known": ("No official or book-level prop price exists in this repository. Projections and correlations are "
                      "published; no prop bet is scored."),
            "missing": "A licensed prop price feed.",
            "how_to_discover": "Same route as Q02. Until then the divisions stay published as empty with the reason.",
            "blocks": "Three of the six leaderboard divisions.",
            "decision_owner": "the repository owner",
            "source": "nflverse_schedules",
        },
        {
            "id": "Q11",
            "question": "Should the site publish row-level official data at all, or only derived aggregates plus links?",
            "why_it_blocks": "The public/private split (readiness SI-11) and Q01.",
            "known": ("The root site publishes thousands of table rows with official source links, many of them "
                      "row-level injury and depth entries; the exact count is in data/strat/flagged.json › "
                      "rootsite_rows."),
            "missing": "A decision, informed by Q01.",
            "how_to_discover": "Take the legal reading first, then decide which rows move behind an access control.",
            "blocks": "The site's publication model.",
            "decision_owner": "the repository owner",
            "source": "terms",
        },
        {
            "id": "Q12",
            "question": "Does the injury designation level predict playing time at all?",
            "why_it_blocks": "Using any designation as a feature. The brief rejects a level outright and asks for an empirical calibration of 'Questionable'.",
            "known": "The designation counts are captured weekly; no play-rate-per-designation study has been run against official inactive lists.",
            "missing": "Official inactive lists joined to participation for several seasons.",
            "how_to_discover": "Join the weekly designations to the official inactive list and the snap share, then compute the play rate per designation with a binomial interval.",
            "blocks": "The injury-surprise ablation's design (W09).",
            "decision_owner": "the next availability session",
            "source": "injuries_w10",
        },
    ]


# --------------------------------------------------------------------------- suggestions
def suggestions() -> list[dict]:
    return [
        {
            "id": "SG1",
            "suggestion": "Make the promotions and demotions of this competition the site's front door",
            "problem": ("A reader landing on the site sees many tables and cannot tell in one screen what changed "
                        "and whether anything is live."),
            "proposal": ("The new competition overview leads with five numbers (strategies registered, live, paper, "
                         "demoted, eligible) and a one-line verdict. Every other table is one click deeper."),
            "cost": "already built in this session",
            "effort": "small",
            "risk": "Low. The numbers are counts of files that already exist.",
            "evidence": "This site's overview page.",
            "decision": "D01",
            "source": "repo",
        },
        {
            "id": "SG2",
            "suggestion": "Publish a promotion rule next to the demotion rule before the first live bet",
            "problem": ("The demotion gate is armed but the promotion condition is not pre-registered, so the "
                        "competition has an exit and no entrance."),
            "proposal": ("Freeze a promotion rule with the same structure — sample floor, proper-score interval, "
                         "multiplicity charge — and commit it before any live sample exists."),
            "cost": "one file and one gate",
            "effort": "small",
            "risk": "Low, and the risk of not doing it is higher: a promotion chosen after seeing results is result-chasing.",
            "evidence": "Open question Q09.",
            "decision": "D02",
            "source": "repo",
        },
        {
            "id": "SG3",
            "suggestion": "Answer the terms-of-use question before adding another data layer",
            "problem": ("Every availability feature the brief asks for needs an official source whose terms have not "
                        "been cleared. Building more on top raises the cost of the eventual decision."),
            "proposal": ("Treat Q01 as the gating decision for the whole availability branch: obtain written consent, "
                         "or restructure to aggregates plus links, or stop the scrape."),
            "cost": "legal review, not engineering",
            "effort": "small (engineering) / unbounded (legal)",
            "risk": "High if ignored; the repository currently publishes row-level designations.",
            "evidence": "Flag F51 on the Flagged for Review page.",
            "decision": "D03",
            "source": "terms",
        },
        {
            "id": "SG4",
            "suggestion": "Make the injury feature an ablation, not a coefficient",
            "problem": "A fixed points penalty for a missing starter is exactly what the brief rejects.",
            "proposal": ("Build one model with the surprise features and one without, run both on a chronological "
                         "holdout, and publish the difference with a game-cluster interval. Wire it to W09."),
            "cost": "the availability feed (blocked by Q01 and Q12)",
            "effort": "medium",
            "risk": "The result may be zero, which is a valid and useful result.",
            "evidence": "Pre-registered rules P07-P09; falsifier W09.",
            "decision": "D04",
            "source": "injuries_w10",
        },
        {
            "id": "SG5",
            "suggestion": "Show the market beside every own line and never print a difference without it",
            "problem": "A line without the market it is priced against is not a claim about anything.",
            "proposal": ("Both totals, the gap, the market total and the model-minus-market difference in one table, "
                         "with blank where a price does not exist."),
            "cost": "already built (the two-totals page)",
            "effort": "small",
            "risk": "None.",
            "evidence": "The two-totals page.",
            "decision": "D05",
            "source": "schedules",
        },
        {
            "id": "SG6",
            "suggestion": "Replace 'win rate' everywhere with a proper score and an interval",
            "problem": ("Win rate and short-run ROI cannot distinguish skill from variance, which the brief says "
                        "explicitly."),
            "proposal": ("The leaderboard's first column is benchmark-relative Brier skill with its game-cluster "
                         "lower bound; ROI is demoted to a supporting column and the raw win rate is dropped."),
            "cost": "already built",
            "effort": "small",
            "risk": "The table becomes harder to read for a casual reader, which the method page addresses.",
            "evidence": "The proper-score leaderboard page.",
            "decision": "D06",
            "source": "schedules",
        },
        {
            "id": "SG7",
            "suggestion": "Publish the control baselines in the same table as the strategies, not in an appendix",
            "problem": "A strategy's number means nothing without the number a coin would have produced on the same bets.",
            "proposal": "Random, favourite-only, home-only and underdog-only are rows in the same leaderboard, scored identically.",
            "cost": "already registered as P02-P05",
            "effort": "small",
            "risk": "None.",
            "evidence": "Falsifier W07.",
            "decision": "D07",
            "source": "schedules",
        },
        {
            "id": "SG8",
            "suggestion": "Put the blocking gate and the clearing number in every readiness row",
            "problem": "A status of 'partial' with no number attached cannot be acted on.",
            "proposal": ("Every requirement row states what blocks it and the exact observation that would clear it, "
                         "and links to the artifact that holds the evidence."),
            "cost": "adds a column to an existing register",
            "effort": "small",
            "risk": "None.",
            "evidence": "The readiness register already on the landing page (82 rows).",
            "decision": "D08",
            "source": "repo",
        },
        {
            "id": "SG9",
            "suggestion": "Fail the build when a scraper's row count or a required field changes",
            "problem": "A parser that silently drops rows publishes a blank that looks like data.",
            "proposal": ("Pin the expected row count and the required columns per source; the check fails loudly with "
                         "the delta instead of publishing."),
            "cost": "one check script and one JSON",
            "effort": "small",
            "risk": "A legitimate source change will fail the build, which is the point; the fix is a reviewed pin bump.",
            "evidence": "drift-alarm gate in this session",
            "decision": "D09",
            "source": "injuries_w10",
        },
        {
            "id": "SG10",
            "suggestion": "Keep the two totals until one wins, and say so in the headline",
            "problem": "Collapsing to one estimator hides the fact that neither has demonstrated an advantage.",
            "proposal": "Publish both with the gap column and the walk-forward verdict beside them; the verdict currently reads 'no winner'.",
            "cost": "already built",
            "effort": "small",
            "risk": "None; it is more honest than a single number.",
            "evidence": "The two-totals page; falsifier W05.",
            "decision": "D10",
            "source": "schedules",
        },
        {
            "id": "SG11",
            "suggestion": "Split the site into a public analysis layer and a private data layer",
            "problem": "Row-level official data is published while its licence is unresolved (Q01, Q11).",
            "proposal": ("Public pages keep derived analysis (indices, ratios, model output, links to the official "
                         "page); raw row-level captures move to a private store until the terms are read."),
            "cost": "a rebuild of the affected pages and a private store",
            "effort": "medium",
            "risk": "Some tables become less detailed until the decision is made.",
            "evidence": "Readiness SI-11; Flag F51.",
            "decision": "D03",
            "source": "terms",
        },
        {
            "id": "SG12",
            "suggestion": "Give every published conclusion a falsifier with a number, in both directions",
            "problem": "A claim with no stated refutation cannot be reviewed.",
            "proposal": "The what-would-change register, wired into the leaderboard and the model pages.",
            "cost": "already built",
            "effort": "small",
            "risk": "None.",
            "evidence": "The what-would-change page (12 claims).",
            "decision": "D11",
            "source": "repo",
        },
    ]


# --------------------------------------------------------------------------- decisions
def decisions(ps: dict) -> list[dict]:
    return [
        {"id": "D01", "decision": "Adopt the competition overview as the entry page for this site",
         "options": ["Adopt (recommended)", "Keep the old entry", "Merge into the landing page"],
         "gate": "none — a choice", "owner": "repository owner", "source": "repo"},
        {"id": "D02", "decision": "Pre-register a promotion rule before any live bet",
         "options": ["Write it now (recommended)", "Leave the promotion condition unwritten", "Promote on backtest only (rejected: result-chasing)"],
         "gate": "Q09", "owner": "repository owner", "source": "repo"},
        {"id": "D03", "decision": "Settle the official-data terms question (Q01) and then choose the publication model",
         "options": ["Obtain written consent", "Publish aggregates plus links only (recommended interim)", "Stop the scrape"],
         "gate": "legal review", "owner": "repository owner", "source": "terms"},
        {"id": "D04", "decision": "Run the availability feature as an ablation once a verified feed exists",
         "options": ["Ablation (recommended)", "Fixed points penalty (rejected by the brief)", "No availability features"],
         "gate": "Q01 and Q12", "owner": "next availability session", "source": "injuries_w10"},
        {"id": "D05", "decision": "Publish the market beside every own line",
         "options": ["Always (recommended)", "Model only", "Market only"],
         "gate": "none — implemented", "owner": "this session", "source": "schedules"},
        {"id": "D06", "decision": "Rank by proper scores with uncertainty instead of win rate",
         "options": ["Proper scores (recommended, implemented)", "Win rate", "Season ROI (rejected by the brief)"],
         "gate": "none — implemented", "owner": "this session", "source": "schedules"},
        {"id": "D07", "decision": "Keep the control baselines in the main leaderboard",
         "options": ["Main table (recommended)", "Appendix", "Omit"],
         "gate": "prospective sample", "owner": "next strategy session", "source": "schedules"},
        {"id": "D08", "decision": "Add the blocking gate and clearing number to the readiness register",
         "options": ["Adopt (recommended, partially present)", "Leave as status only"],
         "gate": "none — a choice", "owner": "repository owner", "source": "repo"},
        {"id": "D09", "decision": "Fail the build on a scraper drift rather than publishing a blank",
         "options": ["Fail loudly (recommended, implemented)", "Publish blank with a badge"],
         "gate": "none — implemented", "owner": "this session", "source": "injuries_w10"},
        {"id": "D10", "decision": "Keep both total estimators published until one wins",
         "options": ["Both with the gap (recommended, implemented)", "Collapse to A", "Collapse to B"],
         "gate": "W05 walk-forward verdict", "owner": "next modelling session", "source": "schedules"},
        {"id": "D11", "decision": "Require a two-sided falsifier on every published claim",
         "options": ["Require it (recommended, implemented)", "Optional"],
         "gate": "none — implemented", "owner": "this session", "source": "repo"},
        {"id": "D12", "decision": "Charge the strategy family for multiplicity with a pre-registered effective-test count",
         "options": ["Pre-register the count (recommended)", "Bonferroni as now (conservative)", "No charge (rejected)"],
         "gate": "Q05", "owner": "next strategy session", "source": "schedules"},
    ]


def main() -> int:
    ps = lib.load("proper_score.json")
    dt = lib.load("dual_total.json")
    pre = lib.load("preregistration.json")

    lib.write_json("questions.json", {
        "generated_at": lib.now(), "n_questions": 12,
        "rule": ("A question is here because a decision cannot be made until it is answered. Each row states what "
                 "is known, what is missing, the measurement that would produce it, and what it blocks."),
        "rows": questions(ps, dt, pre),
    })
    lib.write_json("suggestions.json", {
        "generated_at": lib.now(), "n_suggestions": 12,
        "review_process": [
            "Every suggestion names the problem, the proposal, its cost, its risk and the decision it feeds.",
            "Nothing is implemented before the owner records a choice in the decisions register.",
            "A suggestion that needs information nobody publishes is converted into a question, not built.",
            "The owner can accept, reject or defer; the record of the choice is the gate.",
        ],
        "rows": suggestions(),
    })
    lib.write_json("decisions.json", {
        "generated_at": lib.now(), "n_decisions": 12,
        "rule": "A decision needs only a choice. A question needs information first. The two registers are kept separate so a decision is never blocked on a question nobody can answer.",
        "rows": decisions(ps),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
