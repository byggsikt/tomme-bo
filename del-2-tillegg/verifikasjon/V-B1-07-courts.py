# V-B1-07: courts, pooling, LR tests, court-adjusted logistic. Independent.
import sys, math, json, collections
import numpy as np
from scipy import stats
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
W = r"../data/"
sys.path.insert(0, W)
from V_B1_shared import AJ, gray, wilson, newcombe, chi2y, rd_delta, load, mk

END = date(2026, 8, 24); CUT = date(2024, 8, 24)
Z = stats.norm.ppf(0.975); BAR = "=" * 78
rows = load(W + "V-B1-04-tagged.tsv", END)
sub = [r for r in rows if r["opened"] <= CUT]
out = {}

courts = sorted(set(r["tingrett"] for r in rows))
print("distinct court strings:", len(courts))
print("blank court rows:", sum(1 for r in rows if not r["tingrett"]))
cnt = collections.Counter(r["tingrett"] for r in rows)
for c, n in cnt.most_common():
    print(f"   {n:5d}  {c}")
out["n_courts"] = len(courts)

print()
print(BAR); print("PER-COURT PETITION EFFECT (10 largest)"); print(BAR)
print(f"{'court':32s} {'n':>5s} {'oppb n':>7s} {'%':>6s} {'asof opp':>12s} {'asof pet':>12s} {'CIF24 o':>8s} {'CIF24 p':>8s} {'RD':>8s} {'[wald]':>20s} {'Gray p':>8s}")
strata_asof = []; strata_730 = []; iv_est = []; iv_var = []; signs = []
percourt = {}
for c, n in cnt.most_common():
    g = [r for r in rows if r["tingrett"] == c]
    go = [r for r in g if r["basis"] == "oppbud"]; gp = [r for r in g if r["basis"] == "ikke_oppbud"]
    if not go or not gp:
        continue
    ko = sum(1 for r in go if r["cause"] == 1); kp = sum(1 for r in gp if r["cause"] == 1)
    ajo = AJ(*mk(go)); ajp = AJ(*mk(gp))
    r24, lo, hi, se, pv = rd_delta(ajp, ajo, 730)
    U, V, z, gp_ = gray(*mk(gp), *mk(go))
    strata_asof.append((kp, len(gp), ko, len(go)))
    gs = [r for r in sub if r["tingrett"] == c]
    gso = [r for r in gs if r["basis"] == "oppbud"]; gsp = [r for r in gs if r["basis"] == "ikke_oppbud"]
    if gso and gsp:
        strata_730.append((sum(1 for r in gsp if r["cause"] == 1 and r["t"] <= 730), len(gsp),
                           sum(1 for r in gso if r["cause"] == 1 and r["t"] <= 730), len(gso)))
    if se > 0 and np.isfinite(se):
        iv_est.append(r24); iv_var.append(se * se); signs.append(r24 > 0)
    percourt[c] = dict(n=len(g), noppb=len(go), pct_oppb=100 * len(go) / len(g),
                       asof_o=100 * ko / len(go), asof_p=100 * kp / len(gp),
                       cif_o=100 * ajo.cif(730), cif_p=100 * ajp.cif(730),
                       rd=100 * r24, lo=100 * lo, hi=100 * hi, grayp=gp_)
    if len(g) >= 231:
        print(f"{c:32s} {len(g):5d} {len(go):7d} {100*len(go)/len(g):6.1f} {ko:5d}/{len(go):<6d} {kp:5d}/{len(gp):<6d} "
              f"{100*ajo.cif(730):8.1f} {100*ajp.cif(730):8.1f} {100*r24:+8.1f} [{100*lo:+6.1f}; {100*hi:+6.1f}] {gp_:8.3f}")
out["percourt"] = percourt

# ---- Mantel-Haenszel OR (Robins-Breslow-Greenland variance)
def mh(tables):
    num = den = 0.0; sPR = sPSQR = sQS = 0.0
    for (a, b, c, d) in tables:
        n = a + b + c + d
        if n == 0: continue
        R = a * d / n; S = b * c / n
        P_ = (a + d) / n; Q = (b + c) / n
        num += R; den += S
        sPR += P_ * R; sPSQR += P_ * S + Q * R; sQS += Q * S
    orr = num / den
    v = sPR / (2 * num * num) + sPSQR / (2 * num * den) + sQS / (2 * den * den)
    se = math.sqrt(v)
    return orr, math.exp(math.log(orr) - Z * se), math.exp(math.log(orr) + Z * se)

tA = [(kp, np_ - kp, ko, no - ko) for (kp, np_, ko, no) in strata_asof]
tB = [(kp, np_ - kp, ko, no - ko) for (kp, np_, ko, no) in strata_730]
orA = mh(tA); orB = mh(tB)
print()
print(f"  MH OR as-of  = {orA[0]:.3f} [{orA[1]:.3f}; {orA[2]:.3f}]   strata used {len(tA)}")
print(f"  MH OR 730 d  = {orB[0]:.3f} [{orB[1]:.3f}; {orB[2]:.3f}]   strata used {len(tB)}")
w = 1 / np.array(iv_var)
ivp = float(np.sum(w * np.array(iv_est)) / np.sum(w)); ivse = float(math.sqrt(1 / np.sum(w)))
Q = float(np.sum(w * (np.array(iv_est) - ivp) ** 2)); dfq = len(iv_est) - 1
print(f"  IV-pooled CIF24 RD = {100*ivp:+.2f} pp [{100*(ivp-Z*ivse):+.2f}; {100*(ivp+Z*ivse):+.2f}]  Cochran Q={Q:.1f} df={dfq} p={stats.chi2.sf(Q,dfq):.2f}  strata {len(iv_est)}")
print(f"  sign positive in {sum(signs)}/{len(signs)} courts (of {len(cnt)} total)")
out["mh"] = dict(asof=orA, w730=orB)
out["iv"] = dict(rd=100 * ivp, lo=100 * (ivp - Z * ivse), hi=100 * (ivp + Z * ivse), Q=Q, df=dfq,
                 p=float(stats.chi2.sf(Q, dfq)), npos=int(sum(signs)), ntot=len(signs))
Us = Vs = 0.0
for c in cnt:
    go = [r for r in rows if r["tingrett"] == c and r["basis"] == "oppbud"]
    gp = [r for r in rows if r["tingrett"] == c and r["basis"] == "ikke_oppbud"]
    if not go or not gp: continue
    U, V, z, _ = gray(*mk(gp), *mk(go))
    if np.isfinite(V) and V > 0:
        Us += U; Vs += V
zs = Us / math.sqrt(Vs)
print(f"  stratified Gray z = {zs:.2f} p = {2*stats.norm.sf(abs(zs)):.3f}")
out["gray_strat"] = dict(z=zs, p=float(2 * stats.norm.sf(abs(zs))))

# ---------------------------------------------------------- logistic + LR tests
def logit(X, y):
    X = np.asarray(X, float); y = np.asarray(y, float)
    b = np.zeros(X.shape[1])
    for _ in range(500):
        mu = 1 / (1 + np.exp(-(X @ b)))
        Wd = np.clip(mu * (1 - mu), 1e-12, None)
        st = np.linalg.solve((X * Wd[:, None]).T @ X, X.T @ (y - mu))
        b = b + st
        if np.max(np.abs(st)) < 1e-12: break
    mu = 1 / (1 + np.exp(-(X @ b)))
    Wd = np.clip(mu * (1 - mu), 1e-12, None)
    cov = np.linalg.inv((X * Wd[:, None]).T @ X)
    ll = float(np.sum(y * np.log(np.clip(mu, 1e-300, 1)) + (1 - y) * np.log(np.clip(1 - mu, 1e-300, 1))))
    return b, cov, ll

print()
print(BAR); print("LOGISTIC: court-adjusted, and LR test for court before/after basis"); print(BAR)
lv = sorted(set(r["tingrett"] for r in rows)); ref = "OSLO TINGRETT"; lv2 = [x for x in lv if x != ref]
for lbl, dat, yf in (("as-of", rows, lambda r: r["cause"] == 1),
                     ("730 d", sub, lambda r: r["cause"] == 1 and r["t"] <= 730)):
    y = np.array([1.0 if yf(r) else 0.0 for r in dat])
    one = np.ones(len(dat))
    pet = np.array([1.0 if r["basis"] == "ikke_oppbud" else 0.0 for r in dat])
    byg = np.array([1.0 if r["bygg"] else 0.0 for r in dat])
    CD = np.column_stack([[1.0 if r["tingrett"] == L else 0.0 for r in dat] for L in lv2])
    # (i) petition OR adjusted for 22 court dummies
    b, cov, _ = logit(np.column_stack([one, pet, CD]), y)
    se = math.sqrt(cov[1, 1])
    print(f"  {lbl}: petition OR adj. for court = {math.exp(b[1]):.3f} [{math.exp(b[1]-Z*se):.3f}; {math.exp(b[1]+Z*se):.3f}]")
    out[f"logit_court_{lbl}"] = [math.exp(b[1]), math.exp(b[1] - Z * se), math.exp(b[1] + Z * se)]
    # (ii) interaction WITH court dummies (the analyst spec)
    b2, cov2, _ = logit(np.column_stack([one, pet, byg, pet * byg, CD]), y)
    se2 = math.sqrt(cov2[3, 3])
    print(f"         interaction OR WITH 22 court dummies = {math.exp(b2[3]):.3f} [{math.exp(b2[3]-Z*se2):.3f}; {math.exp(b2[3]+Z*se2):.3f}]")
    b3, cov3, _ = logit(np.column_stack([one, pet, byg, pet * byg]), y)
    se3 = math.sqrt(cov3[3, 3])
    print(f"         interaction OR crude (saturated 2x2x2) = {math.exp(b3[3]):.3f} [{math.exp(b3[3]-Z*se3):.3f}; {math.exp(b3[3]+Z*se3):.3f}]")
    out[f"inter_courtadj_{lbl}"] = [math.exp(b2[3]), math.exp(b2[3] - Z * se2), math.exp(b2[3] + Z * se2)]
    out[f"inter_crude_{lbl}"] = [math.exp(b3[3]), math.exp(b3[3] - Z * se3), math.exp(b3[3] + Z * se3)]
    # (iii) LR test for court, before and after adjusting for basis
    _, _, ll0 = logit(one.reshape(-1, 1), y)
    _, _, ll1 = logit(np.column_stack([one, CD]), y)
    _, _, ll0b = logit(np.column_stack([one, pet]), y)
    _, _, ll1b = logit(np.column_stack([one, pet, CD]), y)
    lrA = 2 * (ll1 - ll0); lrB = 2 * (ll1b - ll0b); dfc = len(lv2)
    print(f"         LR chi2({dfc}) for court: unadjusted {lrA:.1f} (p={stats.chi2.sf(lrA,dfc):.3g})  ->  adjusted for basis {lrB:.1f} (p={stats.chi2.sf(lrB,dfc):.3g})")
    out[f"lr_{lbl}"] = dict(unadj=lrA, adj=lrB, df=dfc)
    # (iv) interaction stratum effects
    bb, cc, _ = logit(np.column_stack([one, pet, byg, pet * byg]), y)
    print(f"         petition effect within OTHER (log-odds OR) = {math.exp(bb[1]):.3f}; within BYGG = {math.exp(bb[1]+bb[3]):.3f}")

# court oppbud share vs innstilling share
xs = [percourt[c]["pct_oppb"] for c in percourt]
ys = [100 * sum(1 for r in rows if r["tingrett"] == c and r["cause"] == 1) / percourt[c]["n"] for c in percourt]
rr, pp = stats.pearsonr(xs, ys)
print()
print(f"  court oppbud share vs court as-of innstilt share: Pearson r = {rr:.2f} (p = {pp:.2f}), k = {len(xs)} courts")
out["court_corr"] = dict(r=rr, p=pp, k=len(xs))

json.dump(out, open(W + "V-B1-07-results.json", "w", encoding="utf-8"), indent=1, default=str)
print()
print("wrote V-B1-07-results.json")
