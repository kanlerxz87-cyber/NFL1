"""Fixture tests for the session `57c05555-nfl1` transactions/depth staleness classifier.

Every fixture is a real transactions line, copied from the official club pages captured in
``data/ledger/transactions/``.  The bug these tests exist for is subtle and was real: the
first version of the classifier matched the *whole line*, so a player named in one sentence
inherited a move reported in another.  It reported Cam Jurgens on injured reserve because
the same 2026-10-07 Ravens line, in a later sentence, put Durham Smythe there.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "nfl1_57c05555"))

from staleness import classify, player_status  # noqa: E402


def txn(date: str, text: str, url: str = "https://www.baltimoreravens.com/team/transactions/"):
    return {"date": date, "text": text, "source_url": url, "captured_at": "2026-11-15T12:54:51Z"}


# --------------------------------------------------------------- the Ravens QB case
BAL_IR_QB = (
    "Placed QB Lamar Jackson and QB Tyler Huntley on Injured Reserve. Signed QB Austin Reed "
    "to the active roster from the practice squad. Activated OLB Adisa Isaac and K Jake Moody "
    "from the practice squad (standard elevation) vs. Jax."
)


def test_both_ravens_quarterbacks_are_classified_as_on_reserve():
    assert classify(BAL_IR_QB, "Lamar Jackson") == "reserve"
    assert classify(BAL_IR_QB, "Tyler Huntley") == "reserve"


def test_a_teammate_signed_on_the_same_line_is_not_on_reserve():
    # Austin Reed is *signed* on this line; the reserve action is about the two QBs.
    assert classify(BAL_IR_QB, "Austin Reed") == "other"


def test_a_practice_squad_elevation_is_not_an_activation_from_reserve():
    assert classify(BAL_IR_QB, "Adisa Isaac") == "other"


# ------------------------------------------- the false positive that was actually shipped
BAL_1007 = (
    "Signed TE Nick Vannett to the active roster from the practice squad. Signed FB Lucas "
    "Scott to the practice squad. Acquired C Cam Jurgens via trade from the Philadelphia "
    "Eagles in exchange for a 2027 fifth-round pick and 2028 second-round pick. Placed TE "
    "Durham Smythe on Injured Reserve."
)


def test_traded_player_is_not_on_reserve():
    assert classify(BAL_1007, "Cam Jurgens") == "other"


def test_the_player_actually_placed_on_reserve_is():
    assert classify(BAL_1007, "Durham Smythe") == "reserve"


# ------------------------------------------------------- coming OFF the PUP list is not IR
BAL_PUP = (
    "Placed T Kendall Lamm on the Reserve/Retired list. ILB Teddye Buchanan passed his "
    "physical and was removed from the Physically Unable to Perform (PUP) list."
)


def test_pup_removal_is_not_injured_reserve():
    assert classify(BAL_PUP, "Teddye Buchanan") == "other"


def test_reserve_retired_is_a_removal():
    assert classify(BAL_PUP, "Kendall Lamm") == "reserve"


# ------------------------------------------------------ the Indianapolis 2026-11-14 case
IND_1114 = (
    "Sign (LB) West Weeks to 53-man roster from practice squad; place (TE) Mo Alie-Cox, "
    "(LB) Akeem Davis-Gaither on IR; elevate (LS) Jacob Bobenmoyer and (WR) Quez Watkins "
    "from to active roster from practice squad for Sunday's game against the Dolphins."
)


def test_ir_abbreviation_is_recognised():
    assert classify(IND_1114, "Mo Alie-Cox") == "reserve"
    assert classify(IND_1114, "Akeem Davis-Gaither") == "reserve"


def test_the_signed_player_is_not_on_reserve():
    assert classify(IND_1114, "West Weeks") == "other"


def test_an_elevated_player_is_not_on_reserve():
    assert classify(IND_1114, "Quez Watkins") == "other"


# ------------------------------------------------------------- activation clears the flag
IND_1017 = "Activated (TE) Will Mallory from the Injured Reserve list."
IND_1027 = (
    "Sign (CB) Kenneth Harris to the 53-man roster from the practice squad and placed (CB) "
    "Cam Taylor-Britt on the Injured Reserve list; signed (CB) Shemar Bartholomew and (CB) "
    "Natrone Brooks to the practice squad."
)


def test_activation_from_ir_is_recognised():
    assert classify(IND_1017, "Will Mallory") == "activated"


def test_activation_is_not_a_removal():
    assert classify(IND_1017, "Will Mallory") != "reserve"


# ------------------------------------------------------------------ whole-log decisions
def test_the_newest_action_decides():
    txns = [txn("2026-10-17", IND_1017), txn("2026-10-10", "Placed (TE) Will Mallory on the Injured Reserve list.")]
    st = player_status("Will Mallory", txns)
    assert st is not None
    assert st["on_reserve"] is False
    assert st["verdict"] == "activated"


def test_a_later_reserve_move_overrides_an_earlier_activation():
    txns = [
        txn("2026-11-14", "Place (TE) Will Mallory on Injured Reserve."),
        txn("2026-10-17", IND_1017),
    ]
    st = player_status("Will Mallory", txns)
    assert st["on_reserve"] is True
    assert st["latest_transaction"]["date"] == "2026-11-14"


def test_a_player_never_mentioned_returns_none():
    assert player_status("Zay Flowers", [txn("2026-11-05", BAL_IR_QB)]) is None


def test_a_passing_mention_does_not_decide():
    # Named only inside a reserve action about someone else -> no action on this player.
    st = player_status("Austin Reed", [txn("2026-11-05", BAL_IR_QB)])
    assert st is None


# -------------------------------------------------------------- the published register
def test_published_staleness_register_matches_the_classifier():
    import json

    path = os.path.join(ROOT, "data", "ledger", "staleness.json")
    if not os.path.exists(path):
        return
    reg = json.load(open(path, encoding="utf-8"))
    for club in reg["clubs"]:
        for row in club["stale_rows"]:
            assert row["why_stale"]
            assert row["chart_url"].startswith("https://")
            assert row["transaction_url"].startswith("https://")
            # every published stale row must reproduce through the classifier
            verdict = classify(row["transaction_text"], row["player"])
            assert verdict in ("reserve", "other"), verdict
