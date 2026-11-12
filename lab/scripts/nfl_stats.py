#!/usr/bin/env python3
"""Small, dependency-free statistics library for the NFL decision lab.

Why hand-rolled instead of scipy: the Arena sandbox and the GitHub-hosted runner used
here are not guaranteed to have numpy/scipy, and every number published on the site must
be reproducible from this repository alone. Each routine below is a textbook formula and
cites the reference it implements in its docstring.
"""

from __future__ import annotations

import math
import random


# ---------------------------------------------------------------------------
# Linear algebra
# ---------------------------------------------------------------------------

def solve(a, b):
    """Solve Ax = b by Gaussian elimination with partial pivoting.

    Used for the least-squares normal equations. O(n^3); the largest system here is
    33x33 (32 club ratings + home-field term + the zero-sum constraint row).
    """
    n = len(a)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            raise ValueError("singular matrix")
        m[col], m[piv] = m[piv], m[col]
        pv = m[col][col]
        for r in range(col + 1, n):
            f = m[r][col] / pv
            if f == 0.0:
                continue
            for c in range(col, n + 1):
                m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = m[r][n] - sum(m[r][c] * x[c] for c in range(r + 1, n))
        x[r] = s / m[r][r]
    return x


def ols(X, y, ridge=0.0):
    """Ordinary least squares via the normal equations with an optional ridge term.

    Normal equations: (X'X + lambda*I) beta = X'y.  Ridge is applied to every column
    except none here (the intercept is regularised too, which is why lambda is kept
    tiny and is published alongside every model that uses it).
    """
    p = len(X[0])
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for row, target in zip(X, y):
        for i in range(p):
            xty[i] += row[i] * target
            for j in range(p):
                xtx[i][j] += row[i] * row[j]
    for i in range(p):
        xtx[i][i] += ridge
    return solve(xtx, xty)


# ---------------------------------------------------------------------------
# Distributions
# ---------------------------------------------------------------------------

def betacf(a, b, x, itmax=200, eps=3e-12):
    """Continued fraction for the incomplete beta function (Numerical Recipes 6.4)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def betai(a, b, x):
    """Regularised incomplete beta function I_x(a, b) (Numerical Recipes 6.4)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0 - x))
    bt = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * betacf(a, b, x) / a
    return 1.0 - bt * betacf(b, a, 1.0 - x) / b


def norm_cdf(z):
    """Standard normal CDF via the complementary error function."""
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def t_sf(t, df):
    """Upper-tail P(T > t) for Student's t with df degrees of freedom."""
    if df <= 0:
        return float("nan")
    x = df / (df + t * t)
    p = 0.5 * betai(df / 2.0, 0.5, x)
    return p if t > 0 else 1.0 - p


def t_two_sided_p(t, df):
    """Two-sided p-value for a t statistic."""
    return 2.0 * t_sf(abs(t), df)


def pearson(xs, ys):
    """Pearson correlation coefficient. Returns (r, n)."""
    n = len(xs)
    if n < 3:
        return float("nan"), n
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return float("nan"), n
    return sxy / math.sqrt(sxx * syy), n


def pearson_p(r, n):
    """Two-sided p-value for a Pearson r with n pairs: t = r*sqrt((n-2)/(1-r^2))."""
    if n < 3 or not (abs(r) < 1.0):
        return float("nan")
    t = r * math.sqrt((n - 2) / (1.0 - r * r))
    return t_two_sided_p(t, n - 2)


def fisher_ci(r, n, alpha=0.05):
    """Fisher z confidence interval for a Pearson correlation.

    NIST/SEMATECH e-Handbook, "Correlation" -
    https://www.itl.nist.gov/div898/handbook/eda/section3/eda367.htm
    """
    if n < 4 or not (abs(r) < 1.0):
        return (float("nan"), float("nan"))
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    zc = 1.959963984540054
    lo = math.tanh(z - zc * se)
    hi = math.tanh(z + zc * se)
    return (lo, hi)


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------

def bootstrap_mean_ci(xs, iters=10000, alpha=0.05, seed=20261112):
    """Percentile bootstrap CI for the mean. Fixed seed => reproducible on the site."""
    n = len(xs)
    if n == 0:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    mus = []
    for _ in range(iters):
        s = 0.0
        for _ in range(n):
            s += xs[rng.randrange(n)]
        mus.append(s / n)
    mus.sort()
    lo = mus[int(math.floor((alpha / 2) * iters))]
    hi = mus[min(iters - 1, int(math.ceil((1 - alpha / 2) * iters)) - 1)]
    return (lo, hi)


def permutation_p(xs, pool, iters=10000, seed=20261112):
    """How surprising is mean(xs) compared with same-size random draws from `pool`?

    This is the luck-removal test: `pool` is every game the strategy could have bet in
    the same weeks. If a random set of the same size usually does as well, the result is
    luck, not skill.
    """
    if not xs or not pool:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    obs = sum(xs) / len(xs)
    n = len(xs)
    ge = 0
    for _ in range(iters):
        s = 0.0
        for _ in range(n):
            s += pool[rng.randrange(len(pool))]
        if s / n >= obs:
            ge += 1
    return (ge + 1.0) / (iters + 1.0), obs


def binomial_two_sided_p(k, n, p=0.5):
    """Exact two-sided binomial test."""
    if n == 0:
        return float("nan")
    probs = [math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(n + 1)]
    obs = probs[k]
    return min(1.0, sum(pr for pr in probs if pr <= obs * (1 + 1e-12)))


def benjamini_hochberg(pvals, alpha=0.10):
    """Benjamini-Hochberg FDR correction.

    Benjamini & Hochberg (1995), J. R. Statist. Soc. B 57(1), 289-300.
    Returns (adjusted p-values in the input order, reject flags).
    """
    m = len(pvals)
    if m == 0:
        return [], []
    order = sorted(range(m), key=lambda i: (pvals[i] is None, pvals[i]))
    adj = [None] * m
    prev = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        i = m - rank + 1
        val = min(prev, pvals[idx] * m / i)
        adj[idx] = min(1.0, val)
        prev = adj[idx]
    rej = [bool(adj[i] is not None and adj[i] <= alpha) for i in range(m)]
    return adj, rej


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def sd(xs):
    n = len(xs)
    if n < 2:
        return float("nan")
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
