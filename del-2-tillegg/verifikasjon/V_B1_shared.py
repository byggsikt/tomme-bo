# V_B1_shared: estimator library extracted verbatim from my own V-B1-05-stats.py.
import csv, sys, math, json, collections
import numpy as np
from scipy import stats
from datetime import date
Z = stats.norm.ppf(0.975)

def _d(s):
    y, m, dd = s.split("-")
    return date(int(y), int(m), int(dd))

def load(path, END):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="	"):
            op = _d(r["opened"])
            inn = _d(r["innstilt"]) if r["innstilt"] else None
            avs = _d(r["avsluttet"]) if r["avsluttet"] else None
            if inn is not None:
                cause, t = 1, (inn - op).days
            elif avs is not None:
                cause, t = 2, (avs - op).days
            else:
                cause, t = 0, (END - op).days
            rows.append(dict(orgnr=r["orgnr"], opened=op, basis=r["basis"], bygg=r["bygg"] == "1",
                             tingrett=r["tingrett"], cause=cause, t=t, fu=(END - op).days))
    return rows

# ------------------------------------------------------------------ proportions
def wilson(k, n):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / den
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return (c - h, c + h)


def newcombe(k1, n1, k2, n2):
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    dd = k1 / n1 - k2 / n2
    return (dd - math.sqrt((k1 / n1 - l1) ** 2 + (u2 - k2 / n2) ** 2),
            dd + math.sqrt((u1 - k1 / n1) ** 2 + (k2 / n2 - l2) ** 2))


def chi2y(a, b, c, dd):
    n = a + b + c + dd
    x2 = n * (abs(a * dd - b * c) - n / 2) ** 2 / ((a + b) * (c + dd) * (a + c) * (b + dd))
    return x2, stats.chi2.sf(x2, 1)


# ------------------------------------------- Aalen-Johansen (explicit day loop)
class AJ:
    def __init__(self, t, cause):
        t = [int(x) for x in t]
        cause = [int(x) for x in cause]
        n0 = len(t)
        ev = collections.defaultdict(lambda: [0, 0, 0])
        for ti, ci in zip(t, cause):
            ev[ti][0 if ci == 1 else (1 if ci == 2 else 2)] += 1
        days = sorted(ev)
        self.n0 = n0
        D, F, F2 = [], [], []
        A = FA = FFA = B = C = FC = 0.0
        AL, FAL, FFAL, BL, CL, FCL = [], [], [], [], [], []
        atrisk = n0
        S = 1.0
        F1 = 0.0
        F2c = 0.0
        for day in days:
            d1, d2, cn = ev[day]
            nr = atrisk
            de = d1 + d2
            Sm = S
            if nr > 0 and de > 0:
                F1 += Sm * d1 / nr
                F2c += Sm * d2 / nr
                S *= (1 - de / nr)
                a = de / (nr * (nr - de)) if nr > de else 0.0
                A += a
                FA += F1 * a
                FFA += F1 * F1 * a
                B += Sm * Sm * ((nr - d1) / nr) * (d1 / (nr * nr))
                C += Sm * (d1 / (nr * nr))
                FC += F1 * Sm * (d1 / (nr * nr))
            D.append(day)
            F.append(F1)
            F2.append(F2c)
            AL.append(A)
            FAL.append(FA)
            FFAL.append(FFA)
            BL.append(B)
            CL.append(C)
            FCL.append(FC)
            atrisk -= (d1 + d2 + cn)
        self.days = np.array(D)
        self.F = np.array(F)
        self.F2 = np.array(F2)
        self.A = np.array(AL)
        self.FA = np.array(FAL)
        self.FFA = np.array(FFAL)
        self.B = np.array(BL)
        self.C = np.array(CL)
        self.FC = np.array(FCL)

    def _i(self, t):
        return int(np.searchsorted(self.days, t, side="right")) - 1

    def cif(self, t):
        j = self._i(t)
        return 0.0 if j < 0 else float(self.F[j])

    def cif2(self, t):
        j = self._i(t)
        return 0.0 if j < 0 else float(self.F2[j])

    def var(self, t):
        j = self._i(t)
        if j < 0:
            return 0.0
        Ft = self.F[j]
        v = (Ft * Ft * self.A[j] - 2 * Ft * self.FA[j] + self.FFA[j]
             + self.B[j] - 2 * (Ft * self.C[j] - self.FC[j]))
        return float(max(v, 0.0))

    def ci(self, t, kind="loglog"):
        F = self.cif(t)
        se = math.sqrt(self.var(t))
        if F <= 0 or F >= 1:
            return (F, F, se)
        if kind == "wald":
            return (max(0.0, F - Z * se), min(1.0, F + Z * se), se)
        s = se / abs(F * math.log(F))
        return (F ** math.exp(Z * s), F ** math.exp(-Z * s), se)

    def qday(self, p=0.5):
        w = np.nonzero(self.F >= p)[0]
        return int(self.days[w[0]]) if len(w) else None


def mk(rs):
    return [r["t"] for r in rs], [r["cause"] for r in rs]


# ------------------------------------------------------------------ Gray rho=0
def gray_parts(t, cause, grid):
    ev = collections.defaultdict(lambda: [0, 0, 0])
    for ti, ci in zip(t, cause):
        ev[ti][0 if ci == 1 else (1 if ci == 2 else 2)] += 1
    R = np.zeros(len(grid))
    D1 = np.zeros(len(grid))
    atrisk = len(t)
    S = 1.0
    F1 = 0.0
    for k, day in enumerate(grid):
        d1, d2, cn = ev.get(day, [0, 0, 0])
        Sm, F1m, nr = S, F1, atrisk
        R[k] = nr * (1 - F1m) / Sm if (Sm > 0 and nr > 0) else 0.0
        D1[k] = d1
        de = d1 + d2
        if nr > 0 and de > 0:
            F1 += Sm * d1 / nr
            S *= (1 - de / nr)
        atrisk -= (d1 + d2 + cn)
    return R, D1


def gray(t1, c1, t2, c2):
    grid = sorted(set(t1) | set(t2))
    Ra, D1a = gray_parts(t1, c1, grid)
    Rb, D1b = gray_parts(t2, c2, grid)
    dt = D1a + D1b
    Rt = Ra + Rb
    m = (dt > 0) & (Rt > 1)
    U = float(np.sum(D1a[m] - (Ra[m] / Rt[m]) * dt[m]))
    V = float(np.sum((Ra[m] * Rb[m]) / (Rt[m] ** 2) * dt[m] * (Rt[m] - dt[m]) / (Rt[m] - 1)))
    z = U / math.sqrt(V) if V > 0 else float("nan")
    return U, V, z, (2 * stats.norm.sf(abs(z)) if V > 0 else float("nan"))


def rd_delta(a, b, h=730):
    fa, fb = a.cif(h), b.cif(h)
    se = math.sqrt(a.var(h) + b.var(h))
    r = fa - fb
    return r, r - Z * se, r + Z * se, se, 2 * stats.norm.sf(abs(r / se))


def boot_rd(rsA, rsB, h=730, B=2000, seed=20260912):
    rng = np.random.default_rng(seed)
    tA = np.array([r["t"] for r in rsA]); cA = np.array([r["cause"] for r in rsA])
    tB = np.array([r["t"] for r in rsB]); cB = np.array([r["cause"] for r in rsB])
    out = np.empty(B); oa = np.empty(B); ob = np.empty(B)
    for b in range(B):
        ia = rng.integers(0, len(tA), len(tA)); ib = rng.integers(0, len(tB), len(tB))
        fa = AJ(tA[ia], cA[ia]).cif(h); fb = AJ(tB[ib], cB[ib]).cif(h)
        oa[b] = fa; ob[b] = fb; out[b] = fa - fb
    q = lambda a: (float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5)))
    return q(out), q(oa), q(ob)


