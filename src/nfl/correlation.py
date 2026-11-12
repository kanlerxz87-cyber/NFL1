"""Correlation screening with honest uncertainty and multiple-testing control.

Screening 21 signals against 2 targets means 42 simultaneous hypothesis tests.
On n=28-32 observations a naive p<0.05 screen would be expected to produce
about two false positives purely by chance - which is exactly the "luck" the
brief asks to remove. Every result here is therefore reported with a bootstrap
interval AND a Benjamini-Hochberg false-discovery-rate adjusted q-value, and
nothing is called a finding unless it survives FDR control.
"""
from __future__ import annotations

import math
from typing import Any

from . import stats
from .provenance import DERIVED

FDR_ALPHA = 0.10


def _pairs(matrix: dict[str, dict[str, Any]], teams: list[str],
           a: str, b: str) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    for t in teams:
        va, vb = matrix[t].get(a), matrix[t].get(b)
        if va is None or vb is None:
            continue
        if isinstance(va, float) and math.isnan(va):
            continue
        if isinstance(vb, float) and math.isnan(vb):
            continue
        xs.append(float(va))
        ys.append(float(vb))
    return xs, ys


def benjamini_hochberg(pvals: list[float]) -> list[float]:
    """BH step-up q-values. Monotone, capped at 1."""
    n = len(pvals)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: pvals[i])
    q = [0.0] * n
    prev = 1.0
    for rank in range(n, 0, -1):
        i = order[rank - 1]
        val = min(prev, pvals[i] * n / rank)
        q[i] = val
        prev = val
    return q


def _p_from_t(t: float, df: int) -> float:
    """Two-sided p from a t statistic via the regularised incomplete beta fn."""
    if math.isnan(t) or df <= 0:
        return float("nan")
    x = df / (df + t * t)
    return _betainc(df / 2.0, 0.5, x)


def _betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a,b) - Lentz continued fraction."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0 - x))
    front = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + b * math.log(1.0 - x) + a * math.log(x)) * _betacf(b, a, 1.0 - x) / b


def _betacf(a: float, b: float, x: float) -> float:
    MAXIT, EPS, FPMIN = 300, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def screen(matrix: dict[str, dict[str, Any]], teams: list[str],
           targets: list[str], signals: list[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for tgt in targets:
        for sig in signals:
            if sig == tgt:
                continue
            xs, ys = _pairs(matrix, teams, sig, tgt)
            n = len(xs)
            r = stats.pearson(xs, ys) if n >= 5 else float("nan")
            rho = stats.spearman(xs, ys) if n >= 5 else float("nan")
            t = stats.t_statistic(r, n)
            p = _p_from_t(t, n - 2)
            lo, hi = stats.bootstrap_ci(xs, ys, stats.pearson) if n >= 8 else (float("nan"),) * 2
            rows.append({"target": tgt, "signal": sig, "n": n,
                         "pearson_r": None if math.isnan(r) else round(r, 4),
                         "spearman_rho": None if math.isnan(rho) else round(rho, 4),
                         "t": None if math.isnan(t) else round(t, 3),
                         "p": None if math.isnan(p) else round(p, 5),
                         "ci95_lo": None if math.isnan(lo) else round(lo, 4),
                         "ci95_hi": None if math.isnan(hi) else round(hi, 4),
                         "tier": DERIVED})
    usable = [r for r in rows if r["p"] is not None]
    q = benjamini_hochberg([r["p"] for r in usable])
    for r, qq in zip(usable, q):
        r["q_bh"] = round(qq, 5)
        r["survives_fdr"] = bool(qq <= FDR_ALPHA)
    for r in rows:
        r.setdefault("q_bh", None)
        r.setdefault("survives_fdr", None)
        r["verdict"] = (
            "SURVIVES FDR" if r["survives_fdr"] else
            ("NOT SIGNIFICANT AFTER FDR CONTROL" if r["q_bh"] is not None else
             "INSUFFICIENT SAMPLE"))
    return {"rows": rows, "targets": targets, "signals": signals,
            "fdr_alpha": FDR_ALPHA, "tests_run": len(usable),
            "expected_false_positives_at_005": round(0.05 * len(usable), 2),
            "survivors": [r for r in usable if r["survives_fdr"]],
            "tier": DERIVED}


def pairwise_matrix(matrix: dict[str, dict[str, Any]], teams: list[str],
                    ids: list[str]) -> dict[str, Any]:
    """Full signal-vs-signal Pearson matrix on pairwise-complete observations."""
    cells: list[dict[str, Any]] = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            xs, ys = _pairs(matrix, teams, a, b)
            r = stats.pearson(xs, ys) if len(xs) >= 5 else float("nan")
            cells.append({"a": a, "b": b, "n": len(xs),
                          "pearson_r": None if math.isnan(r) else round(r, 4),
                          "abs_r": None if math.isnan(r) else round(abs(r), 4)})
    strong = sorted([c for c in cells if c["abs_r"] is not None and c["abs_r"] >= 0.60],
                    key=lambda c: -c["abs_r"])
    return {"cells": cells, "strong": strong, "threshold": 0.60, "tier": DERIVED,
            "note": "Pairwise-complete observations; n varies by cell and is "
                    "printed for every pair. A high |r| between two candidate "
                    "signals means they are redundant, not that either is "
                    "predictive - see the correlation-control gate."}


# ---------------------------------------------------------------------------
# Interpretation layer
# ---------------------------------------------------------------------------
#: Signals that are all functions of the SAME set of game outcomes. Any pair
#: drawn from this family is definitional, not empirical: a team that scores
#: more than it concedes wins more games, and no amount of data can make that a
#: discovery. Publishing these as findings would be the most common way to
#: manufacture a fake edge.
OUTCOME_FAMILY = {
    "win_pct", "conf_win_pct", "div_win_pct", "home_win_pct", "road_win_pct",
    "streak_signed", "net_pg", "ppg", "papg", "pyth_win_pct", "pyth_delta",
}
#: Signals measured from the official injury report / official news.
AVAILABILITY_FAMILY = {
    "report_entries", "dnp_count", "lp_count", "off_dnp", "def_dnp", "out_count",
    "qb_entries", "key_position_entries", "availability_pressure", "qb_disruption",
}
#: Above this |r| two signals are treated as one signal, not two.
REDUNDANCY_THRESHOLD = 0.80

CLASS_NOTES = {
    "MECHANICAL": "Both variables are computed from the same game outcomes, so "
                  "the association is definitional. Reported for completeness and "
                  "EXCLUDED from the findings list.",
    "CANDIDATE": "One side is an availability/news signal and the other is an "
                 "outcome, so this association is not definitional. It is a "
                 "research lead only: it is contemporaneous, not predictive, and "
                 "n is small.",
    "REDUNDANT": "|r| at or above the redundancy threshold. These two signals "
                 "must never be used as separate legs of the same multi-leg bet "
                 "(see gate G8).",
}


def classify(pair: dict[str, Any]) -> str:
    a, b = pair.get("a") or pair.get("signal"), pair.get("b") or pair.get("target")
    r = pair.get("pearson_r")
    # Definitional relationships are checked FIRST: a tautology is still a
    # tautology when it is strong, and must never be reported as a finding.
    if a in OUTCOME_FAMILY and b in OUTCOME_FAMILY:
        return "MECHANICAL"
    if r is not None and abs(r) >= REDUNDANCY_THRESHOLD:
        return "REDUNDANT"
    if {a, b} & AVAILABILITY_FAMILY:
        return "CANDIDATE"
    return "MECHANICAL"


def annotate(screen_result: dict[str, Any],
             pairwise_result: dict[str, Any]) -> dict[str, Any]:
    """Tag every correlation with its interpretation class."""
    for r in screen_result["rows"]:
        r["classification"] = classify(r)
        r["classification_note"] = CLASS_NOTES[r["classification"]]
    for c in pairwise_result["cells"]:
        c["classification"] = classify(c)
        c["classification_note"] = CLASS_NOTES[c["classification"]]
    # A finding must survive FDR control AND be neither definitional nor a
    # restatement of another signal.
    findings = [r for r in screen_result["rows"]
                if r.get("survives_fdr")
                and r["classification"] not in ("MECHANICAL", "REDUNDANT")]
    screen_result["findings"] = findings
    screen_result["mechanical_survivors"] = [
        r for r in screen_result["rows"]
        if r.get("survives_fdr") and r["classification"] in ("MECHANICAL", "REDUNDANT")]
    pairwise_result["redundant_pairs"] = [
        c for c in pairwise_result["cells"] if c["classification"] == "REDUNDANT"]
    return {"screen": screen_result, "pairwise": pairwise_result,
            "notes": CLASS_NOTES,
            "redundancy_threshold": REDUNDANCY_THRESHOLD,
            "outcome_family": sorted(OUTCOME_FAMILY),
            "availability_family": sorted(AVAILABILITY_FAMILY)}
