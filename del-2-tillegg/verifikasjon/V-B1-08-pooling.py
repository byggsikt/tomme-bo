# V-B1-08: diagnose the two court-level discrepancies (IV pooling; logistic OR spec).
import sys, math, json, collections
import numpy as np
from scipy import stats
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
W = r"../data/"
sys.path.insert(0, W)
from V_B1_shared import AJ, rd_delta, load, mk

END = date(2026, 8, 24); CUT = date(2024, 8, 24)
Z = stats.norm.ppf(0.975); BAR = "=" * 78
rows = load(W + "V-B1-04-tagged.tsv", END)
out = {}
cnt = collections.Counter(r["tingrett"] for r in rows)

print(BAR); print("PER-COURT CIF24 RD, SE AND IV WEIGHT (all 23 courts)"); print(BAR)
print(f"{'court':36s} {'n_opp':>6s} {'n_pet':>6s} {'RD pp':>8s} {'se pp':>7s} {'weight':>10s} {'w*RD':>9s}")
rec = []
for c, n in cnt.most_common():
    go = [r for r in rows if r["tingrett"] == c and r["basis"] == "oppbud"]
    gp = [r for r in rows if r["tingrett"] == c and r["basis"] == "ikke_oppbud"]
    if not go or not gp: continue
    r24, lo, hi, se, pv = rd_delta(AJ(*mk(gp)), AJ(*mk(go)), 730)
    w = 1 / (se * se)
    rec.append(dict(court=c, no=len(go), npp=len(gp), rd=r24, se=se, w=w))
    print(f"{c:36s} {len(go):6d} {len(gp):6d} {100*r24:+8.2f} {100*se:7.2f} {w:10.1f} {w*r24:9.3f}")

def pool(sel, label):
    est = np.array([x["rd"] for x in sel]); var = np.array([x["se"] ** 2 for x in sel])
    w = 1 / var
    p = float(np.sum(w * est) / np.sum(w)); se = math.sqrt(1 / np.sum(w))
    Q = float(np.sum(w * (est - p) ** 2)); df = len(sel) - 1
    print(f"  {label:52s} RD {100*p:+.2f} pp [{100*(p-Z*se):+.2f}; {100*(p+Z*se):+.2f}]  Q={Q:.1f} df={df} p_het={stats.chi2.sf(Q,df):.2f}  k={len(sel)}")
    return dict(rd=100 * p, lo=100 * (p - Z * se), hi=100 * (p + Z * se), Q=Q, df=df,
                p=float(stats.chi2.sf(Q, df)), k=len(sel))

print()
print(BAR); print("IV POOLING UNDER DIFFERENT STRATUM-INCLUSION RULES"); print(BAR)
out["all23"] = pool(rec, "all 23 courts (no restriction)")
out["ge10"] = pool([x for x in rec if x["no"] >= 10 and x["npp"] >= 10], "courts with >= 10 estates in EACH group")
out["ge20"] = pool([x for x in rec if x["no"] >= 20 and x["npp"] >= 20], "courts with >= 20 estates in EACH group")
out["ge30"] = pool([x for x in rec if min(x["no"], x["npp"]) >= 30], "courts with >= 30 estates in EACH group")
drop = [x["court"] for x in rec if not (x["no"] >= 10 and x["npp"] >= 10)]
print(f"  courts dropped by the >=10 rule: {drop}")
for x in rec:
    if x["court"] in drop:
        print(f"     {x['court']:38s} n_opp={x['no']:3d} n_pet={x['npp']:3d} RD={100*x['rd']:+7.2f} pp  se={100*x['se']:6.2f}  weight={x['w']:9.1f}")
out["dropped"] = drop

# random-effects (DerSimonian-Laird) on all 23, since Q is significant there
est = np.array([x["rd"] for x in rec]); var = np.array([x["se"] ** 2 for x in rec])
w = 1 / var
p = float(np.sum(w * est) / np.sum(w))
Q = float(np.sum(w * (est - p) ** 2)); df = len(rec) - 1
C = float(np.sum(w) - np.sum(w ** 2) / np.sum(w))
tau2 = max(0.0, (Q - df) / C)
w2 = 1 / (var + tau2)
pr = float(np.sum(w2 * est) / np.sum(w2)); ser = math.sqrt(1 / np.sum(w2))
print()
print(f"  DerSimonian-Laird random-effects (23 courts): RD {100*pr:+.2f} pp [{100*(pr-Z*ser):+.2f}; {100*(pr+Z*ser):+.2f}]  tau = {100*math.sqrt(tau2):.2f} pp")
out["dl23"] = dict(rd=100 * pr, lo=100 * (pr - Z * ser), hi=100 * (pr + Z * ser), tau=100 * math.sqrt(tau2))

# ---------------------------------------------------------------- logistic spec
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
    return b, np.linalg.inv((X * Wd[:, None]).T @ X)

print()
print(BAR); print("LOGISTIC PETITION OR - WHICH SPEC GIVES 1.38 ?"); print(BAR)
sub = [r for r in rows if r["opened"] <= CUT]
lv = sorted(set(r["tingrett"] for r in rows)); lv2 = [x for x in lv if x != "OSLO TINGRETT"]
for lbl, dat, yf in (("as-of", rows, lambda r: r["cause"] == 1),
                     ("730 d", sub, lambda r: r["cause"] == 1 and r["t"] <= 730)):
    y = np.array([1.0 if yf(r) else 0.0 for r in dat])
    one = np.ones(len(dat))
    pet = np.array([1.0 if r["basis"] == "ikke_oppbud" else 0.0 for r in dat])
    byg = np.array([1.0 if r["bygg"] else 0.0 for r in dat])
    CD = np.column_stack([[1.0 if r["tingrett"] == L else 0.0 for r in dat] for L in lv2])
    for nm, X in (("petition only", np.column_stack([one, pet])),
                  ("petition + 22 courts", np.column_stack([one, pet, CD])),
                  ("petition + bygg", np.column_stack([one, pet, byg])),
                  ("petition + bygg + 22 courts", np.column_stack([one, pet, byg, CD]))):
        b, cov = logit(X, y)
        se = math.sqrt(cov[1, 1])
        print(f"  {lbl}  {nm:30s} OR = {math.exp(b[1]):.3f} [{math.exp(b[1]-Z*se):.3f}; {math.exp(b[1]+Z*se):.3f}]")
        out[f"logit_{lbl}_{nm}"] = [math.exp(b[1]), math.exp(b[1] - Z * se), math.exp(b[1] + Z * se)]
    print()

json.dump(out, open(W + "V-B1-08-results.json", "w", encoding="utf-8"), indent=1, default=str)
print("wrote V-B1-08-results.json")
