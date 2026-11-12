## How to read this page

A decision is only as good as the information behind it. This page lists every question that
must be answered before a betting, modelling or product decision can reasonably be made, and
separates for each one what is **already known and verified**, what is **not known**, and the
**concrete action that would discover it**.

Nothing here is rhetorical. Each question names the decision it blocks. Where the answer is
already in hand it is stated with its source. Where it is not, the cell is blank rather than
filled with a plausible guess.

Priority key: **P0** blocks the entire programme, **P1** blocks a category of work,
**P2** improves quality but is not blocking.

---

### Q01 · What closing line does the market settle on for each game?
**Category:** Market data · **Priority:** P0 · **Blocks:** every ROI, edge, CLV and
leaderboard computation; gates G5, G6 and G9.
**Have:** nothing. No odds of any kind are stored.
**Do not have:** opening lines, closing lines, line movement, stake limits, or which
sportsbook.
**Discover it by:** connecting a licensed odds or market-data provider. Historical closing
lines for at least three full regular seasons (roughly 1,500 games) are the minimum for any
credible validation. Community mirrors exist but are not an official source and would need
to be reconciled against a licensed feed before use.
**Answer:** *blank - unresolved.*

### Q02 · What is home-field advantage worth in points in the current NFL?
**Category:** Model · **Priority:** P0 · **Blocks:** converting a rating gap into a point
spread; the entire origination product.
**Have:** league home win rate of 49.63% (Wilson 95% CI 41.36%-57.93%, n=136 home games),
computed from the official HOME and ROAD cells on
[nfl.com/standings](https://www.nfl.com/standings/).
**Do not have:** game-level final scores with home/away designation, which are needed to
express the advantage in *points* rather than in win rate.
**Discover it by:** retrieving the official per-week score pages
(`nfl.com/scores/2026/week-1` through `week-9`, and equivalent pages for prior seasons) or
the `games.csv` asset of the nflverse schedules release, then regressing margin on venue.
**Answer:** win rate is known and is *not* above 50% so far in 2026; the point value is
*blank - unresolved*.

### Q03 · Which backup replaces an absent starter, and what string is he?
**Category:** Data · **Priority:** P0 · **Blocks:** the depth-deficiency requirement;
strategy S2 (QB disruption), X1 (opportunity transfer), X2 (pass volume vs missing corner),
X3 (rush-attempt transfer); signal `string_level_drop`.
**Have:** 254 official injury-report entries with position and practice status; eight
official news items, four of which name a confirmed starting-quarterback change.
**Do not have:** any depth chart. NFL.com publishes none. String level (1st/2nd/3rd/4th) is
unknown for every player in the dataset.
**Discover it by:** obtaining credentials for Sportradar's NFL Official API - Sportradar is
the NFL's official data partner and its weekly depth-chart endpoint is the sanctioned feed
([developer.sportradar.com](https://developer.sportradar.com/football/reference/nfl-weekly-depth-charts)).
Club websites publish charts but in inconsistent, unversioned formats that would need
per-team scraping and a stability guarantee.
**Answer:** *blank - unresolved.*

### Q04 · When exactly was each injury report retrieved, and did it change afterwards?
**Category:** Operations · **Priority:** P0 · **Blocks:** gate G3 (no lookahead) for any
availability-based strategy.
**Have:** one retrieval timestamp for the whole snapshot
(2026-11-12T04:30:00Z), and the finding that only 2.36% of entries carried an injury
designation and 2.36% carried a game status at that moment.
**Do not have:** any historical series of reports, so it is impossible to know how a
Thursday-morning report differs from the final Friday 4:00pm ET version.
**Discover it by:** running the retriever on a schedule - Wednesday, Thursday, Friday
evening and Saturday - and storing every version with its own timestamp. Two weeks of that
produces the first usable measurement of how much information arrives and when.
**Answer:** the early-week report is nearly empty of designations; the magnitude of later
revision is *blank - unresolved*.

### Q05 · Is the 2026 home win rate of 49.63% a real shift or noise?
**Category:** Model · **Priority:** P1 · **Blocks:** strategy S5 (home-advantage
mispricing).
**Have:** n=136 home games, rate 49.63%, Wilson 95% CI 41.36%-57.93%. The interval
includes 50%.
**Do not have:** prior-season home win rates for comparison, and any market pricing of home
field.
**Discover it by:** computing the same statistic for 2023-2025 from official standings or
official game results, then testing whether 2026 differs. Note the observations are not
independent - each game contributes one home and one road record - so the interval is
indicative only.
**Answer:** *not established either way. Do not act on it.*

### Q06 · Is the fitted Pythagorean exponent of 3.5073 trustworthy?
**Category:** Model · **Priority:** P1 · **Blocks:** the calibration of every rating.
**Have:** exponent 3.5073, 95% bootstrap CI 2.7498-4.3113, n=32, R²=0.7715, calibration
slope 0.9991, all fitted on official 2026 PF and PA.
**Do not have:** a full-season fit, and out-of-sample confirmation on a different season.
**Discover it by:** refitting on complete seasons and holding one season out. An exponent
fitted on roughly 8.5 games per team is expected to be unstable and biased upward, because
early-season scoring is noisier than season-long scoring.
**Answer:** usable for ranking within 2026; **not** usable as a general constant.

### Q07 · Do any availability signals actually predict anything?
**Category:** Model · **Priority:** P1 · **Blocks:** strategies S2, S3, X1, X2, X3.
**Have:** a 38-test correlation screen with Benjamini-Hochberg FDR control. Expected false
positives at p<0.05 alone: 1.9. Nine tests survive FDR at α=0.10 and **all nine are
definitional** - win percentage against other expressions of the same results.
**Do not have:** any statistically significant association between an availability signal
and an outcome. The strongest non-mechanical leads are `qb_entries` vs `win_pct`
(r=+0.346, q=0.246) and `qb_disruption` vs `win_pct` (r=-0.270, q=0.482). Neither survives.
**Discover it by:** building a panel dataset - team-weeks over multiple seasons with the
report as it stood before kickoff and the game result - rather than a single cross-section
of 28 teams. Cross-sectional n=28 cannot detect a realistic effect size.
**Answer:** **no evidence of an availability edge exists in the current data.**

### Q08 · Are these correlations contemporaneous or predictive?
**Category:** Model · **Priority:** P1 · **Blocks:** every forward-looking claim.
**Have:** a single-week cross-section. Injury counts and records are measured at the same
moment in time.
**Do not have:** any lead-lag structure. A team that has lost more games may simply report
more injuries *because* it lost, which is reverse causation.
**Discover it by:** time-stamping features strictly before kickoff and correlating week-*t*
features against week-*t* results across a season.
**Answer:** the current correlations are **contemporaneous and must not be read as
predictive.**

### Q09 · How are leg correlations to be measured for parlays and prop combos?
**Category:** Model · **Priority:** P1 · **Blocks:** gate G8; strategies P1, P2, P3, X2, X4.
**Have:** a complete pairwise correlation matrix over 21 team-level signals with n printed
for every cell, five redundant pairs at |r|≥0.80, and a working first-order correlation
adjustment in `odds.parlay_fair_prob`.
**Do not have:** any correlation between *betting outcomes* - which is what a parlay
actually needs. Signal-to-signal correlation is not the same thing.
**Discover it by:** settling a history of individual legs, then measuring the empirical
co-occurrence of leg wins within the same game and across the same slate.
**Answer:** the machinery is built; the input does not exist.

### Q10 · What is the vig, and does any model edge survive it?
**Category:** Market · **Priority:** P0 · **Blocks:** gate G6.
**Have:** exact, unit-tested arithmetic for American/decimal conversion, overround,
multiplicative de-vig, Shin/power de-vig, parlay fair probability and edge at posted
prices.
**Do not have:** a single real price to apply it to.
**Discover it by:** Q01.
**Answer:** *blank - unresolved.*

### Q11 · How much bankroll, and what staking rule?
**Category:** Risk · **Priority:** P1 · **Blocks:** any live or paper-trading deployment;
reward tier 1.
**Have:** nothing. No bankroll, no unit size, no maximum exposure, no correlation limits
across simultaneous wagers.
**Do not have:** an owner decision.
**Discover it by:** an owner decision recorded on the Suggestions Board. Fractional Kelly
with a hard cap is the conventional starting point, but the fraction and the cap are the
owner's to set, not the system's to assume.
**Answer:** *blank - awaiting owner decision.*

### Q12 · Is this activity permitted for the owner, and where?
**Category:** Legal / compliance · **Priority:** P0 · **Blocks:** any deployment with real
money.
**Have:** nothing. Jurisdiction is unknown to the system.
**Do not have:** confirmation that sports wagering is legal for the owner in the owner's
jurisdiction, that any intended operator is licensed there, and that automated
data collection complies with each source's terms of use.
**Discover it by:** owner confirmation. This is not a technical question and the system
deliberately does not attempt to answer it.
**Answer:** *blank - owner must confirm. Treat everything here as research until they do.*

### Q13 · Which sportsbooks, and can the model's stake actually be placed?
**Category:** Execution · **Priority:** P2 · **Blocks:** gate G9 (capacity).
**Have:** the gate logic, including a limit-to-stake ratio test.
**Do not have:** any limit data.
**Discover it by:** recording posted limits alongside every captured price.
**Answer:** *blank - unresolved.*

### Q14 · How is the model to be re-fit each week without leaking the future?
**Category:** Operations · **Priority:** P1 · **Blocks:** gate G3.
**Have:** the walk-forward requirement written into gate G3 and the retrieval-timestamp
discipline built into the ingestion layer.
**Do not have:** a scheduler, an immutable feature store, or a record of which data version
produced which prediction.
**Discover it by:** implementing an append-only feature store keyed by
`(game_id, feature_name, retrieved_at)` and forbidding any read that is not filtered by
`retrieved_at < kickoff`.
**Answer:** designed, not yet implemented.

### Q15 · Should the three inconsistent official cells be trusted at all?
**Category:** Data integrity · **Priority:** P1 · **Blocks:** use of division and
non-conference splits.
**Have:** three specific cells that contradict their own adjacent cells on NFL.com - the
DIV record for Indianapolis and Philadelphia, and the NON-CONF record for Washington - each
with an arithmetic proof and a note that the printed cell is character-identical to a
neighbouring cell, which is consistent with a rendering duplication defect.
**Do not have:** a second official retrieval of the same view to determine whether the
defect is in the source or in the retrieval.
**Discover it by:** re-retrieving
[nfl.com/standings/division/2026/REG](https://www.nfl.com/standings/division/2026/REG)
independently, and cross-checking the three clubs' division records against the official
conference standings view.
**Answer:** cells are excluded from all computation and flagged. Root cause *unresolved*.

### Q16 · What is a player's opportunity, independent of his output?
**Category:** Model · **Priority:** P1 · **Blocks:** every player-prop strategy.
**Have:** nothing at player level. No snap counts, no route participation, no target share,
no rush-attempt share.
**Do not have:** NFL Next Gen Stats, which is the official source for tracking-derived
opportunity measures.
**Discover it by:** [nfl.com/nextgenstats](https://www.nfl.com/nextgenstats/) plus official
game logs. Snap share is the minimum viable opportunity measure.
**Answer:** *blank - unresolved.*

### Q17 · How much does one absence actually move a line?
**Category:** Model · **Priority:** P1 · **Blocks:** sizing of S2, S3, X1, X2, X3.
**Have:** the position and severity weight tables used by the availability index, published
in full on the Methodology page.
**Do not have:** any evidence those weights are right. They are analyst priors, not fitted
values, and every number that depends on them is labelled MODELED.
**Discover it by:** measuring observed line movement between the announcement of a confirmed
absence and the next posted price. This needs Q01 and Q03 first.
**Answer:** *blank - priors only, deliberately labelled.*

### Q18 · What is the reward structure for top-performing strategies?
**Category:** Product · **Priority:** P2 · **Blocks:** leaderboard promotion decisions.
**Have:** a four-tier reward ladder proposed in `src/nfl/leaderboard.py` and published on
the Leaderboard page, explicitly marked PROPOSAL.
**Do not have:** owner approval, and any statement of what a "reward" concretely is -
bankroll allocation, promotion to live tracking, or something else.
**Discover it by:** an owner decision on the Suggestions Board (item S-14).
**Answer:** proposed, awaiting sign-off.

### Q19 · How is a strategy retired, and who decides?
**Category:** Governance · **Priority:** P2 · **Blocks:** catalogue hygiene.
**Have:** gate G3, G5 and the placebo test as automatic retirement triggers, and tier 4 of
the reward ladder which archives a rejected strategy with its reason recorded.
**Do not have:** a named owner of the decision, or a review cadence.
**Discover it by:** an owner decision on the Suggestions Board (item S-15).
**Answer:** mechanism built, governance *unresolved*.

### Q20 · Are concurrent sessions actually coordinating?
**Category:** Operations · **Priority:** P2 · **Blocks:** safe multi-agent work on this repo.
**Have:** `COORDINATION.md` as the shared task board with claims, scopes, statuses, sources
and handoff rules.
**Do not have:** any second session to coordinate with; this session is the only one that
has written to the repository.
**Discover it by:** any subsequent session reading the board before claiming work.
**Answer:** board is live and current.

### Q21 · Does the site build and deploy cleanly, with no broken links?
**Category:** Product · **Priority:** P1 · **Blocks:** publication.
**Have:** a static generator with no build-time dependencies beyond the standard library,
and a link checker in the test suite.
**Do not have:** a confirmed successful GitHub Pages deployment for this content.
**Discover it by:** the link-check test, the Pages build status, and a manual pass over the
live URL after the merge.
**Answer:** verified locally; see the Verification Report and the pull request.

### Q22 · What should be believed on this site, and what should not?
**Category:** Governance · **Priority:** P0 · **Blocks:** every downstream use.
**Have:** a four-tier provenance system - VERIFIED, DERIVED, MODELED, UNAVAILABLE - applied
to every published number, with the definitions printed on every page that uses them.
**Do not have:** any validated betting edge. Nothing on this site has ever been measured
against a market.
**Discover it by:** Q01, Q02 and Q03.
**Answer:** **believe the VERIFIED tables and the DERIVED arithmetic. Do not act on any
MODELED value. Treat every blank as genuinely unknown.**
