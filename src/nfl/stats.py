"""Dependency-free statistics: correlations, bootstrap intervals, small fits.

Pure standard library on purpose - the pipeline must run anywhere without a
scientific stack, because reproducibility is part of the verification story.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Iterable, Sequence


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def stdev(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Pearson product-moment correlation. nan for degenerate input."""
    n = len(xs)
    if n < 3 or n != len(ys):
        return float("nan")
    sx, sy = stdev(xs), stdev(ys)
    if sx == 0 or sy == 0 or math.isnan(sx) or math.isnan(sy):
        return float("nan")
    mx, my = mean(xs), mean(ys)
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / (n - 1)
    return cov / (sx * sy)


def _rank(xs: Sequence[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) < 3 or len(xs) != len(ys):
        return float("nan")
    return pearson(_rank(list(xs)), _rank(list(ys)))


def t_statistic(r: float, n: int) -> float:
    """t statistic for H0: rho = 0."""
    if n < 3 or math.isnan(r) or abs(r) >= 1.0:
        return float("nan")
    return r * math.sqrt((n - 2) / (1 - r * r))


def bootstrap_ci(xs, ys, fn: Callable[[Sequence[float], Sequence[float]], float],
                 draws: int = 4000, alpha: float = 0.05,
                 seed: int = 20261112) -> tuple[float, float]:
    """Percentile bootstrap CI. Seeded, so the published interval is stable."""
    n = len(xs)
    if n < 4:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    out: list[float] = []
    for _ in range(draws):
        idx = [rng.randrange(n) for _ in range(n)]
        v = fn([xs[i] for i in idx], [ys[i] for i in idx])
        if not math.isnan(v):
            out.append(v)
    if len(out) < draws * 0.5:
        return (float("nan"), float("nan"))
    out.sort()
    lo = out[max(0, int((alpha / 2) * len(out)))]
    hi = out[min(len(out) - 1, int((1 - alpha / 2) * len(out)))]
    return (lo, hi)


def linfit(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float, float]:
    """OLS y = a + b*x. Returns (a, b, r2)."""
    n = len(xs)
    if n < 2:
        return (float("nan"),) * 3
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return (float("nan"),) * 3
    b = sxy / sxx
    a = my - b * mx
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return (a, b, 1.0 - ss_res / ss_tot if ss_tot else float("nan"))


def golden_section_min(f: Callable[[float], float], lo: float, hi: float,
                       tol: float = 1e-7) -> tuple[float, float]:
    """Minimise unimodal f on [lo, hi]. Used to fit the Pythagorean exponent."""
    invphi = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = lo, hi
    c = b - invphi * (b - a)
    d = a + invphi * (b - a)
    fc, fd = f(c), f(d)
    while abs(b - a) > tol:
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - invphi * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + invphi * (b - a)
            fd = f(d)
    xm = (a + b) / 2.0
    return xm, f(xm)


def clean_pairs(xs, ys) -> list[tuple[float, float]]:
    """Drop rows where either side is missing - never impute."""
    out = []
    for a, b in zip(xs, ys):
        if a is None or b is None:
            continue
        if isinstance(a, float) and math.isnan(a):
            continue
        if isinstance(b, float) and math.isnan(b):
            continue
        out.append((float(a), float(b)))
    return out


def rmse(pred: Iterable[float], actual: Iterable[float]) -> float:
    rows = list(zip(pred, actual))
    if not rows:
        return float("nan")
    return math.sqrt(sum((p - a) ** 2 for p, a in rows) / len(rows))


def mae(pred: Iterable[float], actual: Iterable[float]) -> float:
    rows = list(zip(pred, actual))
    if not rows:
        return float("nan")
    return sum(abs(p - a) for p, a in rows) / len(rows)
