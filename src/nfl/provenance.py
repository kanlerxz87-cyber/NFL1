"""Provenance taxonomy.

Every published number on the site carries exactly one of these tiers, so a
reviewer can tell at a glance what is transcribed fact, what is arithmetic on
that fact, what depends on an assumption, and what is simply not known yet.
"""
from __future__ import annotations

VERIFIED = "VERIFIED"
DERIVED = "DERIVED"
MODELED = "MODELED"
UNAVAILABLE = "UNAVAILABLE"

TIERS = (VERIFIED, DERIVED, MODELED, UNAVAILABLE)

TIER_DEFINITIONS = {
    VERIFIED: "Transcribed character-for-character from an official source. "
              "A clickable official URL is attached. No transformation applied.",
    DERIVED: "Deterministic arithmetic on VERIFIED values only (ratios, sums, "
             "differences, correlations, least-squares fits). Fully reproducible "
             "from the cited source with no external assumption.",
    MODELED: "Depends on at least one analyst prior or un-fitted coefficient. "
             "Must never be staked on until it passes the validation gates.",
    UNAVAILABLE: "Not obtainable from an official source in this environment. "
                 "Left blank on purpose and listed on the Flagged for Review "
                 "page with the exact source that would resolve it.",
}

BLANK = None


def blank(reason: str, resolving_source: str) -> dict:
    """Canonical representation of a deliberately empty cell."""
    return {"value": BLANK, "tier": UNAVAILABLE,
            "reason": reason, "resolving_source": resolving_source}
