#!/usr/bin/env python3
"""The decision register for the Review Room.

Rules for editing this file, so it stays useful rather than decorative:

  * One dict per decision. `options` are real alternatives, each with what it costs, what
    it buys, and what could go wrong. A decision with only one option is not a decision.
  * `evidence` must point at something a reviewer can open: a page in this repository or an
    official URL. `evidence_kind` says which.
  * `blocked_by` lists question ids (from `questions.py`) or gap ids. A decision is only
    `ready` when nothing blocks it; otherwise it is `blocked`, and the reason is a field.
  * `owner_action` is the one thing the reader must do. If a decision needs no action from
    the reader it does not belong here.
  * `recommended` names an option id, or is "" when this analysis genuinely cannot choose.
    It is never filled in to look decisive.

Nothing here is generated from data; it is the judgement layer, and it is labelled as such
on the page. The numbers it cites come from the data files and are checked by the site
generator so a stale number cannot sit here unnoticed.
"""

DECISIONS = [
    {
        "id": "D01",
        "title": "Which site generation is the one published product?",
        "area": "Architecture",
        "why_it_matters": (
            "Six generations of this site now exist in one repository (root dashboard, "
            "pages/, lab/, research/, verified-lab/, referee/, dashboard/). The same "
            "question is answered differently on different generations, so a reader cannot "
            "tell which number is current. Every later decision depends on a single answer "
            "being current."),
        "status": "blocked",
        "blocked_by": ["Q28", "G01"],
        "options": [
            {"id": "A", "label": "Declare the root dashboard authoritative and redirect the rest",
             "cost": "Low: one nav entry per generation plus a banner on each superseded page.",
             "buys": "One number per question, reachable from one place. Readers stop comparing generations.",
             "risk": "Working pages from other sessions become second-class; their extra detail is harder to find.",
             "effort": "1 session"},
            {"id": "B", "label": "Declare the research section authoritative and redirect the rest",
             "cost": "Medium: the research section carries the largest samples and the gate matrix, but not the official-source depth-chart join.",
             "buys": "The biggest evidence base becomes the front door.",
             "risk": "The official-source verification pages (the ones that made every value auditable) fall behind a redirect.",
             "effort": "1 session"},
            {"id": "C", "label": "Keep all generations and publish a comparison table on the landing page",
             "cost": "Ongoing: every change must be made in the place(s) that own it.",
             "buys": "Nothing is deleted; every session's work stays visible.",
             "risk": "Duplicated, drifting numbers remain the reader's problem, which is the current state.",
             "effort": "Ongoing tax"},
        ],
        "recommended": "A",
        "recommendation_reason": (
            "The root dashboard is the only generation whose CI regenerates it from the data "
            "layer and whose figures an independent audit recomputes (47 checks). Its "
            "weakness is breadth, not correctness. Option C preserves the current defect."),
        "evidence": ["pages/sections.html", "docs/audit-b6e68100.md"],
        "evidence_kind": "repository",
        "owner_action": "Say which letter you want; nothing is redirected until you do.",
    },
    {
        "id": "D02",
        "title": "Buy a licensed odds feed, or publish without one?",
        "area": "Data",
        "why_it_matters": (
            "The project wants to originate its own lines and rank strategies for reward. "
            "Without a timestamped, book-level price there is no closing-line value, no "
            "prop pricing and no honest ROI. Everything currently published is scored "
            "against a mirrored closing price, not against a price a bettor could have taken."),
        "status": "blocked",
        "blocked_by": ["Q01 (price, book, timestamp)", "G02"],
        "options": [
            {"id": "A", "label": "Licence one odds API and store every quote append-only",
             "cost": "Recurring fee, contract, integration; probably the largest single cost in this project.",
             "buys": "Real prices at real times: CLV, prop markets, parlay pricing and honest ROI all become possible.",
             "risk": "Vendor terms can restrict redistribution, which would affect publishing every price on a public site.",
             "effort": "2-3 sessions plus a contract"},
            {"id": "B", "label": "Publish model lines only, no ROI or leaderboard rewards",
             "cost": "Nothing to buy; drop the reward and ROI claims from the site.",
             "buys": "Every published claim stays supportable.",
             "risk": "The leaderboard, which is the point of the project, becomes an accuracy contest rather than a profit contest.",
             "effort": "1 session"},
            {"id": "C", "label": "Keep the mirrored closing line and label every result as indicative",
             "cost": "Already paid.",
             "buys": "Large samples now (7,103 played games, 5,228 priced).",
             "risk": "It answers 'did the model beat the close', not 'could you have made money'. Those are different questions and the site must not blur them.",
             "effort": "Done, if labelled"},
        ],
        "recommended": "A",
        "recommendation_reason": (
            "The project's stated goal (originate lines, reward top strategies) cannot be "
            "measured honestly without prices. Until A is funded, C is the only defensible "
            "publication mode and the label has to be on every table."),
        "evidence": ["pages/lines.html", "pages/strategies.html"],
        "evidence_kind": "repository",
        "owner_action": "Approve or decline the licence; if declined, choose B or C.",
    },
    {
        "id": "D03",
        "title": "What exactly does the leaderboard reward, and can it be paid?",
        "area": "Competition",
        "why_it_matters": (
            "A reward on a leaderboard is a policy statement, and if it is money it is a "
            "regulated activity in most US states. No official source reviewed defines a "
            "reward formula, and the site currently publishes none."),
        "status": "blocked",
        "blocked_by": ["Q20 (what rewards)", "Q27", "G03 legal review"],
        "options": [
            {"id": "A", "label": "No money: rank and badge only",
             "cost": "Low. A ranking rule and a badge.",
             "buys": "No licensing, no jurisdiction problem, no payout accounting.",
             "risk": "Weaker incentive; the leaderboard becomes editorial rather than a contest.",
             "effort": "1 session"},
            {"id": "B", "label": "Prize pool with an entry rule and full terms",
             "cost": "High: legal review of every state the site can be read in, payout accounting, tax reporting, dispute process.",
             "buys": "A real contest, which is what the brief asks for.",
             "risk": "Likely requires a licence or exemption in several jurisdictions; the project may not be eligible at all.",
             "effort": "Multi-month, outside a code session"},
            {"id": "C", "label": "Rank-only now, with the reward formula pre-registered for later",
             "cost": "Low.",
             "buys": "The ranking rule can be frozen now, so scores cannot be tuned to whoever is winning.",
             "risk": "Formula announced but unpayable until a decision is made.",
             "effort": "1 session"},
        ],
        "recommended": "C",
        "recommendation_reason": (
            "Pre-registering the formula is the part that protects the science, and it costs "
            "nothing. Paying is a legal question this analysis cannot answer, so it stays "
            "open rather than being guessed."),
        "evidence": ["pages/strategies.html", "pages/review.html"],
        "evidence_kind": "repository",
        "owner_action": "Choose A or B; C happens automatically if nothing is chosen.",
    },
    {
        "id": "D04",
        "title": "How should the personnel-deficiency signal be used, now that it has been tested against the price?",
        "area": "Signals",
        "why_it_matters": (
            "This session tested thirteen personnel measures against the closing line on up to "
            "7,083 played games, and separately asked whether the market's own number already "
            "contains them. The measures are readable and descriptive — who is out, who is "
            "starting in place of whom — but as a group they did not show a reliable information "
            "edge after correction, and none of the five bet rules built on them passed the "
            "gates. The live counts and corrected p-values are on the Signals and Week 10 pages; "
            "they are read from the data files, not repeated here. Deciding what that negative "
            "result means for the project is the owner's call, not the analysis's."),
        "status": "ready",
        "blocked_by": [],
        "options": [
            {"id": "A", "label": "Keep the deficiency register as a descriptive dashboard and publish no personnel-driven bets",
             "cost": "None: already built.",
             "buys": "Honest presentation: the register answers 'who is out and who is next', not 'who covers'.",
             "risk": "The brief asked for personnel signals; this answers it with a negative result, which is still an answer.",
             "effort": "Done"},
            {"id": "B", "label": "Collect player-level defensive data and retest with a production-loss measure on defence",
             "cost": "One collection change plus one analysis pass; needs per-player defensive snaps and statistics, which the current extract lacks.",
             "buys": "A real test of the '2nd/3rd/4th string defender' question instead of a count of names on a report.",
             "risk": "Likely also a negative result; the market prices injuries quickly and publicly.",
             "effort": "1 session"},
            {"id": "C", "label": "Test the reaction instead of the level: how fast does the line move after a designation?",
             "cost": "Needs a timestamped odds history, which is D02.",
             "buys": "The realistic question: the information is public, so the edge can only be in speed.",
             "risk": "Blocked until D02 is decided; unmeasurable with closing lines only.",
             "effort": "Blocked"},
        ],
        "recommended": "A",
        "recommendation_reason": (
            "A is what the evidence supports today and costs nothing. B is worth doing only "
            "as a deliberate second attempt, and C is the only option with a plausible route "
            "to an edge, but it depends on D02."),
        "evidence": ["review-room/evidence.html", "review-room/decisions.html"],
        "evidence_kind": "repository",
        "owner_action": "Accept the negative result, or commission B or C.",
    },
    {
        "id": "D05",
        "title": "Stop publishing implied or model-only numbers where a verified value is missing?",
        "area": "Integrity",
        "why_it_matters": (
            "The brief says: if a value cannot be confirmed from an official source, leave it "
            "blank and flag it. The site mostly obeys this, but prop market columns are "
            "model-only and several legacy pages publish derived figures with no official "
            "counterpart. Deciding the rule once fixes every page instead of page by page."),
        "status": "ready",
        "blocked_by": [],
        "options": [
            {"id": "A", "label": "Hard rule: a cell is either official-sourced or blank with a flag",
             "cost": "Some tables shrink visibly; some pages lose their point.",
             "buys": "One rule, mechanically checkable, no exceptions to argue about.",
             "risk": "Model output (own lines, projections) is not official by definition, so it must be labelled as model output rather than deleted.",
             "effort": "1 session"},
            {"id": "B", "label": "Two classes: official facts, and model estimates clearly marked",
             "cost": "Costs a per-cell or per-column marker.",
             "buys": "Keeps the model content while never presenting it as an official value.",
             "risk": "Reader must respect the distinction; marking has to be consistent or it degrades.",
             "effort": "1-2 sessions"},
        ],
        "recommended": "B",
        "recommendation_reason": (
            "The site's purpose includes originating lines, which are by definition not "
            "official. B keeps that purpose while obeying the blank-and-flag rule for anything "
            "claiming to be a fact."),
        "evidence": ["pages/evidence.html", "pages/props.html", "pages/review.html"],
        "evidence_kind": "repository",
        "owner_action": "Pick A or B; B is the default if the model pages are to survive.",
    },
    {
        "id": "D06",
        "title": "What is the publication gate for a number that changed after it was verified?",
        "area": "Operations",
        "why_it_matters": (
            "This session found the committed standings were one game stale (the Week 10 "
            "Thursday game was missing) and that the official injury page changes during the "
            "day. A published value can therefore be correct when verified and wrong when "
            "read. The repository has no rule for that."),
        "status": "ready",
        "blocked_by": [],
        "options": [
            {"id": "A", "label": "Show an as-of timestamp and the source's own refresh window on every time-sensitive table",
             "cost": "Low: the timestamps already exist in the data files.",
             "buys": "The reader can tell how old a number is and whether it can still change.",
             "risk": "None material; a timestamp does not fix staleness, it only discloses it.",
             "effort": "1 session"},
            {"id": "B", "label": "Refresh time-sensitive sources immediately before each publication and block the build if older than a threshold",
             "cost": "Medium: a refresh step and a freshness check in CI.",
             "buys": "A stale number cannot be published silently.",
             "risk": "A source that is offline blocks publication of everything; needs an override path that is itself logged.",
             "effort": "1-2 sessions"},
            {"id": "C", "label": "Do nothing beyond the existing flags",
             "cost": "None.",
             "buys": "Nothing.",
             "risk": "The staleness found this session recurs and is only caught by a reader noticing.",
             "effort": "None"},
        ],
        "recommended": "A",
        "recommendation_reason": (
            "A is cheap and can be done in this session; B is the better control once the "
            "refresh path is stable. C leaves a known defect in place."),
        "evidence": ["review-room/verification.html"],
        "evidence_kind": "repository",
        "owner_action": "Confirm A now and whether to fund B later.",
    },
    {
        "id": "D07",
        "title": "How should the two independent analyses of correlation be reconciled?",
        "area": "Verification",
        "why_it_matters": (
            "Different sessions computed the same correlations on different scopes (32 "
            "standings rows vs 136 games vs 7,103 games) and published values that cannot be "
            "compared. A reader comparing two pages sees two numbers for one concept."),
        "status": "ready",
        "blocked_by": [],
        "options": [
            {"id": "A", "label": "Publish one correlation register with the scope in the column header",
             "cost": "Low: merge on presentation, keep every underlying computation.",
             "buys": "No two numbers with the same name.",
             "risk": "Requires deleting or relabelling the smaller-scope figures from display.",
             "effort": "1 session"},
            {"id": "B", "label": "Keep both and add a comparability warning",
             "cost": "Low.",
             "buys": "Nothing is removed.",
             "risk": "The reader still has to do the reconciliation.",
             "effort": "1 session"},
        ],
        "recommended": "A",
        "recommendation_reason": (
            "The correlation question is the one most likely to be quoted out of context. "
            "One register with the scope in the header removes the ambiguity at the source."),
        "evidence": ["pages/analysis.html", "review-room/evidence.html"],
        "evidence_kind": "repository",
        "owner_action": "Confirm A; it can be applied at the next integration.",
    },
]
