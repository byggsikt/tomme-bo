# B1_lib.py — statistics for "outcome by petition basis" (Tomme bo, Q4 core analyst).
# Pure numpy/scipy. Every estimator is written out so it can be checked line by line.
#
# Event model (three absorbing states from the opening date):
#   cause 1 = innstilling under konkursloven § 135
#   cause 2 = ordinary closure ("Konkurs - avslutning av bobehandlingen"), competing event
#   cause 0 = still open at corpus end 2026-08-24 (right-censored)
# Time t = whole days from opening date. Risk set at day t = all with t_i >= t
# (identical to the study's rev2-00-lib.mjs `risikoVed`).
import numpy as np
from scipy import stats

Z = 1.959963984540054
H12, H18, H24 = 365, 548, 730


# ---------------------------------------------------------------- proportions
def wilson(k, n, z=Z):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return ((c - h) / d, (c + h) / d)


def clopper_pearson(k, n, alpha=0.05):
    lo = 0.0 if k == 0 else stats.beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else stats.beta.ppf(1 - alpha / 2, k + 1, n - k)
    return (lo, hi)


def newcombe(k1, n1, k2, n2, z=Z):
    """Newcombe method 10 CI for p1 - p2."""
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    p1, p2 = k1 / n1, k2 / n2
    d = p1 - p2
    return (d - np.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2),
            d + np.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def chi2_yates(a, b, c, d):
    n = a + b + c + d
    x2 = n * (abs(a * d - b * c) - n / 2) ** 2 / ((a + b) * (c + d) * (a + c) * (b + d))
    return x2, stats.chi2.sf(x2, 1)


# ---------------------------------------------------------------- Aalen–Johansen
class AJ:
    """Aalen–Johansen CIF for cause 1 on a daily grid, with delta-method variance
    (Marubini & Valsecchi 1995; Klein & Moeschberger ch. 4) — the same formula as the
    study's rev2-00-lib.mjs:
      V[F1(t)] = Σ [F1(t)−F1(ti)]² · di/(ni(ni−di))
               + Σ S(ti−)² · ((ni−d1i)/ni) · d1i/ni²
               − 2 Σ [F1(t)−F1(ti)] · S(ti−) · d1i/ni²
    """

    def __init__(self, t, cause):
        t = np.asarray(t, dtype=np.int64)
        cause = np.asarray(cause, dtype=np.int64)
        assert t.min() >= 0
        T = int(t.max()) + 1
        self.T = T
        self.N = len(t)
        d1 = np.bincount(t[cause == 1], minlength=T).astype(float)
        d2 = np.bincount(t[cause == 2], minlength=T).astype(float)
        c = np.bincount(t[cause == 0], minlength=T).astype(float)
        tot = d1 + d2 + c
        d = d1 + d2
        n = self.N - np.cumsum(tot) + tot          # at risk at day s: t_i >= s
        with np.errstate(divide="ignore", invalid="ignore"):
            h = np.where(n > 0, d / n, 0.0)
            h1 = np.where(n > 0, d1 / n, 0.0)
        S_after = np.cumprod(1 - h)
        S_before = np.concatenate(([1.0], S_after[:-1]))
        F = np.cumsum(S_before * h1)                # F1 after the step at s
        F2 = np.cumsum(S_before * np.where(n > 0, d2 / n, 0.0))  # CIF of competing event
        self.n, self.d1, self.d2, self.c = n, d1, d2, c
        self.S_before, self.S_after, self.F, self.F2 = S_before, S_after, F, F2
        with np.errstate(divide="ignore", invalid="ignore"):
            a = np.where(n > d, d / (n * (n - d)), 0.0)
            b = np.where(n > 0, S_before ** 2 * ((n - d1) / n) * (d1 / (n * n)), 0.0)
            cc = np.where(n > 0, S_before * (d1 / (n * n)), 0.0)
        self.A = np.cumsum(a)
        self.FA = np.cumsum(F * a)
        self.FFA = np.cumsum(F * F * a)
        self.B = np.cumsum(b)
        self.C = np.cumsum(cc)
        self.FC = np.cumsum(F * cc)

    def _idx(self, t):
        return min(int(t), self.T - 1)

    def F1(self, t):
        if t < 0:
            return 0.0
        return float(self.F[self._idx(t)])

    def Fcomp(self, t):
        if t < 0:
            return 0.0
        return float(self.F2[self._idx(t)])

    def S(self, t):
        if t < 0:
            return 1.0
        return float(self.S_after[self._idx(t)])

    def var(self, t):
        i = self._idx(t)
        Ft = self.F[i]
        v = (Ft * Ft * self.A[i] - 2 * Ft * self.FA[i] + self.FFA[i]
             + self.B[i] - 2 * (Ft * self.C[i] - self.FC[i]))
        return float(max(v, 0.0))

    def ci(self, t, kind="loglog"):
        F = self.F1(t)
        se = np.sqrt(self.var(t))
        if F <= 0 or F >= 1:
            return (F, F, se)
        if kind == "wald":
            return (max(0.0, F - Z * se), min(1.0, F + Z * se), se)
        s_theta = se / abs(F * np.log(F))
        return (F ** np.exp(Z * s_theta), F ** np.exp(-Z * s_theta), se)

    def at_risk(self, t):
        i = self._idx(t)
        return int(self.n[i]) if t < self.T else 0

    def quantile(self, p):
        """First day where F1 >= p; None if never reached."""
        w = np.nonzero(self.F >= p)[0]
        return int(w[0]) if len(w) else None

    def quantile_ci(self, p, kind="loglog"):
        """Test-inversion (Brookmeyer–Crowley-type): lower = first t with upper CI >= p,
        upper = first t with lower CI >= p."""
        lo = hi = None
        for s in range(self.T):
            if self.d1[s] + self.d2[s] == 0:
                continue
            l, u, _ = self.ci(s, kind)
            if lo is None and u >= p:
                lo = s
            if hi is None and l >= p:
                hi = s
            if lo is not None and hi is not None:
                break
        return (lo, hi)


# ---------------------------------------------------------------- Gray's test (rho = 0)
def _gray_track(t, cause, T):
    d1 = np.bincount(t[cause == 1], minlength=T).astype(float)
    d2 = np.bincount(t[cause == 2], minlength=T).astype(float)
    c = np.bincount(t[cause == 0], minlength=T).astype(float)
    tot = d1 + d2 + c
    n = len(t) - np.cumsum(tot) + tot
    d = d1 + d2
    with np.errstate(divide="ignore", invalid="ignore"):
        h = np.where(n > 0, d / n, 0.0)
        h1 = np.where(n > 0, d1 / n, 0.0)
    S_after = np.cumprod(1 - h)
    S_before = np.concatenate(([1.0], S_after[:-1]))
    F_after = np.cumsum(S_before * h1)
    F_before = np.concatenate(([0.0], F_after[:-1]))
    with np.errstate(divide="ignore", invalid="ignore"):
        R = np.where((S_before > 0) & (n > 0), n * (1 - F_before) / S_before, 0.0)
    return R, d1


def gray_test(t1, c1, t2, c2):
    """Gray (1988), rho = 0: log-rank-type test on the subdistribution risk set
    R_g(t) = Y_g(t) * (1 - F1g(t-)) / Sg(t-), each estimated within its own group.
    Returns (U, V, z, p). Identical construction to the study's grayTest."""
    t1 = np.asarray(t1, dtype=np.int64); t2 = np.asarray(t2, dtype=np.int64)
    c1 = np.asarray(c1, dtype=np.int64); c2 = np.asarray(c2, dtype=np.int64)
    T = int(max(t1.max(), t2.max())) + 1
    Ra, d1a = _gray_track(t1, c1, T)
    Rb, d1b = _gray_track(t2, c2, T)
    dt = d1a + d1b
    Rt = Ra + Rb
    m = (dt > 0) & (Rt > 1)
    U = float(np.sum(d1a[m] - (Ra[m] / Rt[m]) * dt[m]))
    V = float(np.sum((Ra[m] * Rb[m]) / (Rt[m] ** 2) * dt[m] * (Rt[m] - dt[m]) / (Rt[m] - 1)))
    z = U / np.sqrt(V) if V > 0 else float("nan")
    p = 2 * stats.norm.sf(abs(z)) if V > 0 else float("nan")
    return U, V, z, p


def gray_stratified(groups):
    """groups: list of (t1,c1,t2,c2) per stratum. Sums U and V over strata."""
    U = V = 0.0
    used = 0
    for (t1, c1, t2, c2) in groups:
        if len(t1) == 0 or len(t2) == 0:
            continue
        u, v, _, _ = gray_test(t1, c1, t2, c2)
        if np.isfinite(v) and v > 0:
            U += u; V += v; used += 1
    z = U / np.sqrt(V)
    return U, V, z, 2 * stats.norm.sf(abs(z)), used


# ---------------------------------------------------------------- bootstrap
def boot_indices(rng, n, B):
    return rng.integers(0, n, size=(B, n))


def boot_cif(rng, t, cause, horizons, B=2000, quantile_p=0.5):
    """Percentile bootstrap (resample companies with replacement) of F1(h) for each h
    and of the CIF-based day to reach quantile_p. Returns dict of arrays."""
    t = np.asarray(t); cause = np.asarray(cause)
    n = len(t)
    out = {h: np.empty(B) for h in horizons}
    q = np.full(B, np.nan)
    idx = boot_indices(rng, n, B)
    for b in range(B):
        aj = AJ(t[idx[b]], cause[idx[b]])
        for h in horizons:
            out[h][b] = aj.F1(h)
        qq = aj.quantile(quantile_p)
        q[b] = np.nan if qq is None else qq
    return out, q


def pct_ci(arr, alpha=0.05):
    arr = np.asarray(arr, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return (float("nan"), float("nan"))
    return (float(np.percentile(arr, 100 * alpha / 2)), float(np.percentile(arr, 100 * (1 - alpha / 2))))


# ---------------------------------------------------------------- logistic regression (IRLS)
def logit_fit(X, y, max_iter=100, tol=1e-10):
    """Plain Newton–Raphson / IRLS for logistic regression. Returns beta, cov, ll."""
    X = np.asarray(X, dtype=float); y = np.asarray(y, dtype=float)
    n, p = X.shape
    beta = np.zeros(p)
    for _ in range(max_iter):
        eta = X @ beta
        mu = 1 / (1 + np.exp(-eta))
        W = mu * (1 - mu)
        grad = X.T @ (y - mu)
        H = (X * W[:, None]).T @ X
        step = np.linalg.solve(H, grad)
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            break
    eta = X @ beta
    mu = 1 / (1 + np.exp(-eta))
    W = mu * (1 - mu)
    H = (X * W[:, None]).T @ X
    cov = np.linalg.inv(H)
    ll = float(np.sum(y * np.log(mu + 1e-300) + (1 - y) * np.log(1 - mu + 1e-300)))
    return beta, cov, ll


def or_ci(beta, cov, j):
    se = np.sqrt(cov[j, j])
    return (np.exp(beta[j]), np.exp(beta[j] - Z * se), np.exp(beta[j] + Z * se), beta[j] / se, 2 * stats.norm.sf(abs(beta[j] / se)))


# ---------------------------------------------------------------- Mantel–Haenszel
def mh_or(tables):
    """tables: list of (a,b,c,d) = (exposed event, exposed non-event, unexposed event, unexposed non-event).
    MH common OR with Robins–Breslow–Greenland variance. Returns OR, lo, hi."""
    num = den = 0.0
    P = Q = R = S = 0.0
    sPR = sPSQR = sQS = 0.0
    for (a, b, c, d) in tables:
        n = a + b + c + d
        if n == 0:
            continue
        r = a * d / n; s = b * c / n
        p = (a + d) / n; q = (b + c) / n
        num += r; den += s
        sPR += p * r; sPSQR += p * s + q * r; sQS += q * s
    if den == 0 or num == 0:
        return (float("nan"),) * 3
    orr = num / den
    var = sPR / (2 * num * num) + sPSQR / (2 * num * den) + sQS / (2 * den * den)
    se = np.sqrt(var)
    return (orr, np.exp(np.log(orr) - Z * se), np.exp(np.log(orr) + Z * se))


def pooled_rd(strata):
    """strata: list of (k1,n1,k0,n0). Cochran–MH weighted risk difference w_k = n1 n0 / n,
    variance by Sato (1989) approximation replaced with the simple weighted variance
    Σ w² var_k / (Σ w)² using binomial variances per stratum."""
    W = 0.0; num = 0.0; V = 0.0
    for (k1, n1, k0, n0) in strata:
        if n1 == 0 or n0 == 0:
            continue
        w = n1 * n0 / (n1 + n0)
        p1, p0 = k1 / n1, k0 / n0
        num += w * (p1 - p0); W += w
        V += w * w * (p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)
    rd = num / W
    se = np.sqrt(V) / W
    return rd, rd - Z * se, rd + Z * se


def iv_pooled(estimates, variances):
    """Inverse-variance pooled estimate and 95 % CI."""
    w = 1 / np.asarray(variances)
    est = float(np.sum(w * np.asarray(estimates)) / np.sum(w))
    se = float(np.sqrt(1 / np.sum(w)))
    return est, est - Z * se, est + Z * se, se


def fmt_pct(x, d=1):
    return f"{100 * x:.{d}f}"
