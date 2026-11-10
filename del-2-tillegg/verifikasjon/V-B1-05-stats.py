# V-B1-05: ADVERSARIAL re-computation of B1. Everything written from scratch.
# Aalen-Johansen is implemented as an explicit loop over sorted distinct event days
# (not a vectorised bincount), so it is a different code path from the analyst code.
import csv, sys, math, json, collections
import numpy as np
from scipy import stats
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
W = r"../data/"
END = date(2026, 8, 24)
Z = stats.norm.ppf(0.975)


def d(s):
    y, m, dd = s.split("-")
    return date(int(y), int(m), int(dd))


rows = []
with open(W + "V-B1-04-tagged.tsv", encoding="utf-8") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        op = d(r["opened"])
        inn = d(r["innstilt"]) if r["innstilt"] else None
        avs = d(r["avsluttet"]) if r["avsluttet"] else None
        if inn is not None:
            cause, t = 1, (inn - op).days
        elif avs is not None:
            cause, t = 2, (avs - op).days
        else:
            cause, t = 0, (END - op).days
        rows.append(dict(orgnr=r["orgnr"], opened=op, basis=r["basis"], bygg=r["bygg"] == "1",
                         tingrett=r["tingrett"], cause=cause, t=t, fu=(END - op).days))
print("n =", len(rows))
print("cause split:", dict(collections.Counter(r["cause"] for r in rows)))
print("negative event times:", sum(1 for r in rows if r["t"] < 0))


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


P = lambda x: f"{100 * x:.2f}"
P1 = lambda x: f"{100 * x:.1f}"

out = {}
BAR = "=" * 78
print()
print(BAR); print("1. BASIS - as-of 24.08.2026 (all 5165, mixed follow-up)"); print(BAR)
for b in ("oppbud", "ikke_oppbud"):
    g = [r for r in rows if r["basis"] == b]
    n = len(g)
    k1 = sum(1 for r in g if r["cause"] == 1)
    k2 = sum(1 for r in g if r["cause"] == 2)
    k0 = n - k1 - k2
    lo, hi = wilson(k1, n)
    print(f"  {b:12s} n={n:5d}  innstilt {k1}/{n} = {P1(k1/n)} % [{P1(lo)}-{P1(hi)}]  ordinary {P1(k2/n)} %  open {P1(k0/n)} %")
    out[f"asof_{b}"] = dict(n=n, k=k1, pct=100 * k1 / n, lo=100 * lo, hi=100 * hi,
                            ord_pct=100 * k2 / n, open_pct=100 * k0 / n)
o = [r for r in rows if r["basis"] == "oppbud"]
p = [r for r in rows if r["basis"] == "ikke_oppbud"]
k1o = sum(1 for r in o if r["cause"] == 1)
k1p = sum(1 for r in p if r["cause"] == 1)
nlo, nhi = newcombe(k1p, len(p), k1o, len(o))
x2, pv = chi2y(k1p, len(p) - k1p, k1o, len(o) - k1o)
print(f"  RD (petition - oppbud) = {100*(k1p/len(p)-k1o/len(o)):+.1f} pp  Newcombe [{100*nlo:+.1f}; {100*nhi:+.1f}]  chi2Y={x2:.1f} p={pv:.4g}")
out["asof_rd"] = dict(rd=100 * (k1p / len(p) - k1o / len(o)), lo=100 * nlo, hi=100 * nhi, chi2=x2, p=pv)

print()
print(BAR); print("2. BASIS - assumption-free 730-day window (opened <= 2024-08-24)"); print(BAR)
CUT = date(2024, 8, 24)
sub = [r for r in rows if r["opened"] <= CUT]
print(f"  sub-cohort n={len(sub)}  excluded {len(rows)-len(sub)}")
for b in ("oppbud", "ikke_oppbud"):
    g = [r for r in sub if r["basis"] == b]
    n = len(g)
    k = sum(1 for r in g if r["cause"] == 1 and r["t"] <= 730)
    kasof = sum(1 for r in g if r["cause"] == 1)
    lo, hi = wilson(k, n)
    print(f"  {b:12s} n={n:5d}  innstilt<=730d {k}/{n} = {P1(k/n)} % [{P1(lo)}-{P1(hi)}]   (as-of same sub-cohort {kasof}/{n} = {P1(kasof/n)} %)")
    out[f"w730_{b}"] = dict(n=n, k=k, pct=100 * k / n, lo=100 * lo, hi=100 * hi, kasof=kasof)
go = [r for r in sub if r["basis"] == "oppbud"]
gp = [r for r in sub if r["basis"] == "ikke_oppbud"]
ko = sum(1 for r in go if r["cause"] == 1 and r["t"] <= 730)
kp = sum(1 for r in gp if r["cause"] == 1 and r["t"] <= 730)
nlo, nhi = newcombe(kp, len(gp), ko, len(go))
x2, pv = chi2y(kp, len(gp) - kp, ko, len(go) - ko)
print(f"  RD = {100*(kp/len(gp)-ko/len(go)):+.1f} pp  Newcombe [{100*nlo:+.1f}; {100*nhi:+.1f}]  chi2Y={x2:.1f} p={pv:.4g}")
out["w730_rd"] = dict(rd=100 * (kp / len(gp) - ko / len(go)), lo=100 * nlo, hi=100 * nhi, chi2=x2, p=pv)

print()
print(BAR); print("3. AALEN-JOHANSEN CIF by basis (my own implementation)"); print(BAR)
ajs = {}
for b, g in (("oppbud", o), ("ikke_oppbud", p)):
    t, c = mk(g)
    aj = AJ(t, c)
    ajs[b] = aj
    lo, hi, se = aj.ci(730)
    lw, hw, _ = aj.ci(730, "wald")
    compl = [r["t"] for r in g if r["cause"] == 1]
    print(f"  {b:12s} n={len(g):5d}  CIF12={P(aj.cif(365))}  CIF18={P(aj.cif(548))}  CIF24={P(aj.cif(730))} [loglog {P(lo)}-{P(hi)}] [wald {P(lw)}-{P(hw)}] se={se:.5f}")
    print(f"               CIF ordinary 24m = {P(aj.cif2(730))}   CIF-days to 50 % = {aj.qday(0.5)}   raw median among innstilt = {int(np.median(compl))}")
    out[f"cif_{b}"] = dict(n=len(g), c12=100 * aj.cif(365), c18=100 * aj.cif(548), c24=100 * aj.cif(730),
                           lo=100 * lo, hi=100 * hi, comp24=100 * aj.cif2(730), q50=aj.qday(0.5),
                           rawmed=float(np.median(compl)))
for h, lbl in ((365, "12 m"), (548, "18 m"), (730, "24 m")):
    r, lo, hi, se, pv = rd_delta(ajs["ikke_oppbud"], ajs["oppbud"], h)
    print(f"  RD at {lbl}: {100*r:+.2f} pp  Wald-delta [{100*lo:+.2f}; {100*hi:+.2f}]  z={r/se:.2f} p={pv:.3g}")
    out[f"cifrd_{h}"] = dict(rd=100 * r, lo=100 * lo, hi=100 * hi, z=r / se, p=pv)
U, V, z, pv = gray(*mk(p), *mk(o))
print(f"  Gray rho=0 (petition vs oppbud): U={U:.2f} V={V:.2f} z={z:.2f} p={pv:.3g}")
out["gray_basis"] = dict(U=U, V=V, z=z, p=pv)
grid = list(range(1, 1096))
cross = [t for t in grid if ajs["ikke_oppbud"].cif(t) > ajs["oppbud"].cif(t)]
lead = [(t, ajs["oppbud"].cif(t) - ajs["ikke_oppbud"].cif(t)) for t in grid]
mx = max(lead, key=lambda x: x[1])
print(f"  first day petition CIF exceeds oppbud CIF: {cross[0] if cross else None}")
print(f"  max oppbud lead: {100*mx[1]:.1f} pp at day {mx[0]}")
out["cross_day"] = cross[0] if cross else None
out["max_lead"] = dict(day=mx[0], pp=100 * mx[1])
bt, ba, bb = boot_rd(p, o, 730, B=2000)
print(f"  bootstrap B=2000 seed 20260912: RD24 [{100*bt[0]:+.2f}; {100*bt[1]:+.2f}]  petition CIF24 [{P(ba[0])}-{P(ba[1])}]  oppbud CIF24 [{P(bb[0])}-{P(bb[1])}]")
out["boot_rd24"] = dict(lo=100 * bt[0], hi=100 * bt[1])

print()
print(BAR); print("4. FOLLOW-UP BALANCE CHECK (is the as-of gap a censoring artifact?)"); print(BAR)
for b, g in (("oppbud", o), ("ikke_oppbud", p)):
    fu = np.array([r["fu"] for r in g])
    print(f"  {b:12s} median follow-up {int(np.median(fu))} d, mean {fu.mean():.0f} d, opened median {sorted(r['opened'] for r in g)[len(g)//2]}")
byq = collections.defaultdict(lambda: [0, 0])
for r in rows:
    q = f"{r['opened'].year}Q{(r['opened'].month-1)//3+1}"
    byq[q][0] += 1
    byq[q][1] += (r["basis"] == "oppbud")
print("  oppbud share by opening quarter:")
for q in sorted(byq):
    n, k = byq[q]
    print(f"    {q}  {k}/{n} = {100*k/n:.1f} %")
out["oppbud_share_by_quarter"] = {q: dict(n=byq[q][0], k=byq[q][1], pct=100 * byq[q][1] / byq[q][0]) for q in sorted(byq)}

json.dump(out, open(W + "V-B1-05-results.json", "w", encoding="utf-8"), indent=1, default=str)
print()
print("wrote V-B1-05-results.json")
