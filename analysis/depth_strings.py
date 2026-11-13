#!/usr/bin/env python3
"""Depth-string model: who is the 2nd, 3rd and 4th string at every position, and how far
down the depth chart a club is currently projected to be at each position.

Why this module exists
----------------------
The published availability model only records *listed starters* (depth rank 1) and always
names the depth-rank-2 player as "the replacement". That answers "who is out" but not the
question the brief asks: *how many strings down is the club, and is the second string also
hurt?* A club whose first and second string wide receivers are both unavailable is in a
different situation from one missing only its starter, and the difference is invisible in a
table that only ever shows rank 1.

Everything here is a pure function over plain dictionaries so it can be unit tested without
the release-asset parquet (which only CI can download) and so the numbers can be recomputed
from the published JSON alone.

Honesty rules
-------------
* A status is only ever attached to a player when an official designation says so. A player
  with no designation is "no designation", never "healthy" and never "available".
* The string a club would field is reported as explicitly labelled numbers because they
  differ by design:
    - ``projected_string``       first listed player who is not Out. Doubtful and
                                 Questionable players still project to play, so they count.
    - ``string_if_doubtful_sits`` first listed player who is neither Out nor Doubtful or
                                 Questionable — the next certain man up.
    - ``next_man_up``            the first listed player after the projected starter who is
                                 neither Out nor Doubtful or Questionable.
* Nothing is inferred: if the depth chart does not list a fourth player, the fourth string
  is absent from the chain rather than invented.
"""
from __future__ import annotations

import re

# A player is definitively unavailable only when the official designation says so.
OUT_STATUSES = {"Out"}
UNCERTAIN_STATUSES = {"Doubtful", "Questionable"}
BLOCKED = OUT_STATUSES | UNCERTAIN_STATUSES

# Labels used on the site for a club's current depth at a position. They are built from
# what is actually known: a missing rank is reported as missing, never as "out".
ORDINALS = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}


def _label(rank, listed_below, missing_below, view):
    """Describe why the club is at ``rank`` strings — or that nobody is listed.

    ``listed_below`` is how many published ranks below ``rank`` are blocked (Out for the
    projected view, Out/Doubtful/Questionable for the certain view — by construction of
    the caller every listed rank below the answer is blocked). ``missing_below`` lists
    the rank numbers the chart does not publish at all. ``rank is None`` means every
    published player at the position is blocked — never that nobody is listed, because
    positions with no published players produce no row at all.
    """
    if rank is None:
        return ("no healthy player listed" if view == "projected"
                else "no player free of a designation")
    if rank == 1:
        return ("1st string (starter not Out)" if view == "projected"
                else "1st string (starter certain)")
    if not missing_below:
        if view == "projected":
            detail = {2: "starter out", 3: "two down", 4: "three down"}.get(
                rank, f"{rank - 1} listed out")
        else:
            detail = f"{rank - 1} listed unavailable"
        return f"{ORDINALS.get(rank, str(rank) + 'th')} string ({detail})"
    bits = []
    if listed_below:
        bits.append(f"{listed_below} listed out" if view == "projected"
                    else f"{listed_below} listed unavailable")
    bits.append("rank " + ", ".join(str(r) for r in missing_below) + " not listed")
    return f"{ORDINALS.get(rank, str(rank) + 'th')} string ({'; '.join(bits)})"


def norm_name(name: str) -> str:
    """Normalise a player name so 'D.J. Reed' and 'DJ Reed' match.

    Digits are kept: 'W1' and 'W2' are different people, and 'Chris Jones III' must not
    collapse into 'Chris Jones'.
    """
    x = re.sub(r"[^a-z0-9 ]", "", str(name or "").lower())
    return re.sub(r"\s+", " ", x).strip()


def _first(players: list[dict], blocked: set[str], after_rank: int = 0) -> int | None:
    """Lowest rank above ``after_rank`` whose designation is not in ``blocked``."""
    for p in players:
        if p["rank"] > after_rank and p["designation"] not in blocked:
            return p["rank"]
    return None


def build_depth_strings(
    chains: list[dict],
    status: dict[tuple[str, str], dict],
    max_strings: int = 4,
) -> list[dict]:
    """Turn depth chains plus official availability into one row per position.

    Parameters
    ----------
    chains:
        One dict per (team, slot) position group, shaped like::

            {"team": "NE", "unit": "Defense", "slot": 1, "position": "CB",
             "slot_name": "Left Cornerback",
             "players": [{"name": "...", "rank": 1}, {"name": "...", "rank": 2}, ...]}

    status:
        ``{(team, normalised_name): {"game_status": str|None,
                                     "practice_status": str|None,
                                     "source": str}}`` — the official designations.
    max_strings:
        How many strings to publish per position (the brief asks for 2nd, 3rd and 4th).

    Returns
    -------
    list[dict]
        One row per position that has at least one listed player, ordered by club and
        position. Every row carries the official source of the designation it uses.
    """
    rows: list[dict] = []
    for ch in chains:
        team = ch["team"]
        players = sorted(ch.get("players", []), key=lambda p: p["rank"])
        players = [p for p in players if p["rank"] <= max_strings]
        if not players:
            continue

        chain, out_ranks, uncertain_ranks = [], [], []
        ranks_present = set()
        for p in players:
            st = status.get((team, norm_name(p["name"])), {})
            game = st.get("game_status")
            practice = st.get("practice_status")
            designation = game or practice or None
            ranks_present.add(p["rank"])
            if game in OUT_STATUSES:
                out_ranks.append(p["rank"])
            elif game in UNCERTAIN_STATUSES:
                uncertain_ranks.append(p["rank"])
            chain.append({
                "rank": p["rank"],
                "player": p["name"],
                "game_status": game,
                "practice_status": practice,
                "designation": designation,
                "player_source": st.get("source"),
            })

        lowest_ranked = min(ranks_present)
        projected = _first(chain, OUT_STATUSES)
        certain = _first(chain, BLOCKED)
        next_up = _first(chain, BLOCKED, after_rank=projected or 0)

        def below_view(answer, blocked):
            if answer is None:
                return [], []
            listed = [r for r in ranks_present if r < answer and r in blocked]
            missing = [r for r in range(1, answer) if r not in ranks_present]
            return listed, missing

        proj_listed, proj_missing = below_view(projected, set(out_ranks))
        cert_listed, cert_missing = below_view(certain, set(out_ranks) | set(uncertain_ranks))

        # The starter is the rank-1 listing when the chart publishes one; chain[0] may be
        # a deeper string when rank 1 is absent, and calling that player "the starter"
        # would be an inference.
        rank1 = next((c for c in chain if c["rank"] == 1), None)
        starter_designation = rank1["designation"] if rank1 else None
        next_up_player = None
        if next_up is not None:
            for c in chain:
                if c["rank"] == next_up:
                    next_up_player = c["player"]
                    break

        rows.append({
            "team": team,
            "unit": ch.get("unit"),
            "position": ch.get("position"),
            "slot_name": ch.get("slot_name"),
            "slot": ch.get("slot"),
            "strings_published": len(chain),
            "lowest_rank_published": lowest_ranked,
            "starter": rank1["player"] if rank1 else None,
            "starter_listed": rank1 is not None,
            "starter_designation": starter_designation,
            "projected_string": projected,
            "projected_string_label": _label(projected, len(proj_listed), proj_missing,
                                              "projected"),
            "string_if_doubtful_sits": certain,
            "string_if_doubtful_sits_label": _label(certain, len(cert_listed), cert_missing,
                                                    "certain"),
            "next_man_up": next_up_player,
            "out_ranks": out_ranks,
            "uncertain_ranks": uncertain_ranks,
            # "Unavailable" means the official report says Out — the same rule the page's
            # KPI and notes state. Doubtful/Questionable starters are counted separately
            # as at risk: they still project to play.
            "starter_unavailable": bool(rank1 and starter_designation in OUT_STATUSES),
            "starter_at_risk": bool(
                rank1 and (
                    starter_designation in UNCERTAIN_STATUSES
                    or (not rank1["game_status"]
                        and rank1["practice_status"] == "Did Not Participate In Practice"))),
            "chain": chain,
            # Where the chain itself came from (the official club chart), alongside the
            # designation source on `source` (the official injury report).
            "chart_source": ch.get("chart_source"),
            "source": "https://www.nfl.com/injuries/",
        })

    rows.sort(key=lambda r: (r["team"], r["unit"] or "", r["position"] or "", r["slot"] or 0))
    return rows


def summarise_by_club(rows: list[dict]) -> list[dict]:
    """Per-club summary: how many positions are down to the 2nd, 3rd or 4th string."""
    clubs: dict[str, dict] = {}
    for r in rows:
        c = clubs.setdefault(r["team"], {
            "team": r["team"],
            "positions_tracked": 0,
            "positions_starter_unavailable": 0,
            "positions_starter_at_risk": 0,
            "positions_down_to_2nd": 0,
            "positions_down_to_3rd": 0,
            "positions_down_to_4th_or_beyond": 0,
            "no_healthy_player_listed": 0,
            "defensive_positions_starter_unavailable": 0,
            "offensive_positions_starter_unavailable": 0,
            "source": "https://www.nfl.com/injuries/",
        })
        c["positions_tracked"] += 1
        s = r.get("projected_string")
        if r["starter_unavailable"]:
            c["positions_starter_unavailable"] += 1
            unit = (r.get("unit") or "").lower()
            if unit.startswith("def"):
                c["defensive_positions_starter_unavailable"] += 1
            elif unit.startswith("off"):
                c["offensive_positions_starter_unavailable"] += 1
        if r.get("starter_at_risk"):
            c["positions_starter_at_risk"] += 1
        if s == 2:
            c["positions_down_to_2nd"] += 1
        elif s == 3:
            c["positions_down_to_3rd"] += 1
        elif s is not None and s >= 4:
            c["positions_down_to_4th_or_beyond"] += 1
        elif s is None:
            c["no_healthy_player_listed"] += 1
    return [clubs[k] for k in sorted(clubs)]
