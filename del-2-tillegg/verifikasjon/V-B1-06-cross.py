# V-B1-06: construction x basis, courts, crossing day, DiD, LR tests. Independent.
import csv, sys, math, json, collections
import numpy as np
from scipy import stats
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
W = r"../data/"
sys.path.insert(0, W)
END = date(2026, 8, 24)
CUT = date(2024, 8, 24)
Z = stats.norm.ppf(0.975)
BAR = "=" * 78

from V_B1_shared import AJ, gray, wilson, newcombe, chi2y, rd_delta, load, mk, boot_rd

rows = load(W + "V-B1-04-tagged.tsv", END)
out = {}

# ----------------------------------------------------------------- crossing day
o = [r for r in rows if r["basis"] == "oppbud"]
p = [r for r in rows if r["basis"] == "ikke_oppbud"]
A = AJ(*mk(p))   # petition
B = AJ(*mk(o))   # oppbud
grid = list(range(1, 1096))
diff = np.array([A.cif(t) - B.cif(t) for t in grid])
first_pos = next((grid[i] for i in range(len(grid)) if diff[i] > 0), None)
# durable crossing = last day on which oppbud is still >= petition
last_nonpos = max((grid[i] for i in range(len(grid)) if diff[i] <= 0), default=None)
durable = None
for i in range(len(grid)):
    if all(diff[j] > 0 for j in range(i, len(grid))):
        durable = grid[i]
        break
print(BAR); print("CROSSING OF THE TWO CIF CURVES"); print(BAR)
print(f"  first day petition > oppbud (transient)        : {first_pos}")
print(f"  last day oppbud >= petition                    : {last_nonpos}")
print(f"  durable crossing (petition ahead from here on) : {durable}")
for t in (30, 43, 60, 90, 125, 200, 300, 310, 316, 320, 365, 500, 730):
    print(f"    day {t:4d}: petition {100*A.cif(t):6.2f}  oppbud {100*B.cif(t):6.2f}  diff {100*(A.cif(t)-B.cif(t)):+6.2f}")
out["cross"] = dict(first_pos=first_pos, last_nonpos=last_nonpos, durable=durable)

# ------------------------------------------------------- construction x basis
print()
print(BAR); print("CONSTRUCTION x BASIS"); print(BAR)
cells = {}
sub = [r for r in rows if r["opened"] <= CUT]
for bygg in (True, False):
    for bas in ("oppbud", "ikke_oppbud"):
        g = [r for r in rows if r["bygg"] == bygg and r["basis"] == bas]
        gs = [r for r in sub if r["bygg"] == bygg and r["basis"] == bas]
        n = len(g)
        k = sum(1 for r in g if r["cause"] == 1)
        ks = sum(1 for r in gs if r["cause"] == 1 and r["t"] <= 730)
        aj = AJ(*mk(g))
        lo, hi, se = aj.ci(730)
        lo2, hi2, _ = aj.ci(730, "wald")
        c2 = aj.cif2(730)
        wl, wh = wilson(ks, len(gs))
        nm = ("bygg" if bygg else "other") + "/" + ("oppbud" if bas == "oppbud" else "petition")
        cells[nm] = dict(rows=g, aj=aj, n=n, k=k, ks=ks, ns=len(gs))
        print(f"  {nm:16s} n={n:5d}  as-of {k}/{n}={100*k/n:5.1f} %   730d {ks}/{len(gs)}={100*ks/len(gs):5.1f} % [{100*wl:.1f}-{100*wh:.1f}]"
              f"   CIF24={100*aj.cif(730):6.2f} [loglog {100*lo:.2f}-{100*hi:.2f}]  CIFord24={100*c2:5.2f}  open24={100*(1-aj.cif(730)-c2):5.1f}  q50={aj.qday(0.5)}")
        out[nm] = dict(n=n, k=k, asof=100 * k / n, ks=ks, ns=len(gs), w730=100 * ks / len(gs),
                       cif24=100 * aj.cif(730), lo=100 * lo, hi=100 * hi, ciford24=100 * c2, q50=aj.qday(0.5))

def contrast(a, b, label):
    ca, cb = cells[a], cells[b]
    r, lo, hi, se, pv = rd_delta(ca["aj"], cb["aj"], 730)
    U, V, z, gp = gray(*mk(ca["rows"]), *mk(cb["rows"]))
    nl, nh = newcombe(ca["k"], ca["n"], cb["k"], cb["n"])
    nl2, nh2 = newcombe(ca["ks"], ca["ns"], cb["ks"], cb["ns"])
    bt, _, _ = boot_rd(ca["rows"], cb["rows"], 730, B=2000, seed=20260912)
    print(f"  {label:30s} CIF24 RD {100*r:+7.2f} [{100*lo:+.2f}; {100*hi:+.2f}]  boot [{100*bt[0]:+.2f}; {100*bt[1]:+.2f}]"
          f"  Gray z={z:+.2f} p={gp:.2g}  as-of RD {100*(ca['k']/ca['n']-cb['k']/cb['n']):+.1f} [{100*nl:+.1f}; {100*nh:+.1f}]"
          f"  730d RD {100*(ca['ks']/ca['ns']-cb['ks']/cb['ns']):+.1f} [{100*nl2:+.1f}; {100*nh2:+.1f}]")
    return dict(rd=100 * r, lo=100 * lo, hi=100 * hi, boot=[100 * bt[0], 100 * bt[1]], grayz=z, grayp=gp)

print()
out["c_bygg_oppbud"] = contrast("bygg/oppbud", "other/oppbud", "bygg-other WITHIN oppbud")
out["c_bygg_pet"] = contrast("bygg/petition", "other/petition", "bygg-other WITHIN petition")
out["c_pet_bygg"] = contrast("bygg/petition", "bygg/oppbud", "petition-oppbud WITHIN bygg")
out["c_pet_other"] = contrast("other/petition", "other/oppbud", "petition-oppbud WITHIN other")
did = out["c_bygg_oppbud"]["rd"] - out["c_bygg_pet"]["rd"]
print(f"  difference-in-differences (CIF24) = {did:+.2f} pp")
out["did"] = did

# ------------------------------------------------------------------- logistic
def logit(X, y):
    X = np.asarray(X, float); y = np.asarray(y, float)
    b = np.zeros(X.shape[1])
    for _ in range(200):
        eta = X @ b
        mu = 1 / (1 + np.exp(-eta))
        Wd = np.clip(mu * (1 - mu), 1e-12, None)
        H = (X * Wd[:, None]).T @ X
        step = np.linalg.solve(H, X.T @ (y - mu))
        b = b + step
        if np.max(np.abs(step)) < 1e-11:
            break
    eta = X @ b
    mu = 1 / (1 + np.exp(-eta))
    Wd = np.clip(mu * (1 - mu), 1e-12, None)
    cov = np.linalg.inv((X * Wd[:, None]).T @ X)
    ll = float(np.sum(y * np.log(np.clip(mu, 1e-300, 1)) + (1 - y) * np.log(np.clip(1 - mu, 1e-300, 1))))
    return b, cov, ll

print()
print(BAR); print("LOGISTIC INTERACTION (as-of and 730-day)"); print(BAR)
for lbl, dat, yf in (("as-of", rows, lambda r: r["cause"] == 1),
                     ("730 d", sub, lambda r: r["cause"] == 1 and r["t"] <= 730)):
    X = np.array([[1.0, float(r["basis"] == "ikke_oppbud"), float(r["bygg"]),
                   float(r["basis"] == "ikke_oppbud") * float(r["bygg"])] for r in dat])
    y = np.array([1.0 if yf(r) else 0.0 for r in dat])
    b, cov, ll = logit(X, y)
    se = math.sqrt(cov[3, 3])
    print(f"  {lbl}: interaction OR = {math.exp(b[3]):.2f} [{math.exp(b[3]-Z*se):.2f}; {math.exp(b[3]+Z*se):.2f}]  z={b[3]/se:.2f} p={2*stats.norm.sf(abs(b[3]/se)):.3g}")
    out[f"interactionOR_{lbl}"] = dict(OR=math.exp(b[3]), lo=math.exp(b[3] - Z * se), hi=math.exp(b[3] + Z * se))

print()
print(BAR); print("OPPBUD SHARE BY INDUSTRY + COMPOSITION"); print(BAR)
for bygg in (True, False):
    g = [r for r in rows if r["bygg"] == bygg]
    k = sum(1 for r in g if r["basis"] == "oppbud")
    lo, hi = wilson(k, len(g))
    print(f"  {'bygg' if bygg else 'other':6s}  oppbud {k}/{len(g)} = {100*k/len(g):.1f} % [{100*lo:.1f}-{100*hi:.1f}]")
    out[f"oppbudshare_{bygg}"] = dict(k=k, n=len(g), pct=100 * k / len(g))
# direct standardisation of the bygg-other CIF24 gap to the OTHER group basis mix
wo = out["oppbudshare_False"]["pct"] / 100
raw = (out["bygg/oppbud"]["cif24"] * out["oppbudshare_True"]["pct"] / 100
       + out["bygg/petition"]["cif24"] * (1 - out["oppbudshare_True"]["pct"] / 100)) \
      - (out["other/oppbud"]["cif24"] * wo + out["other/petition"]["cif24"] * (1 - wo))
adj = (out["bygg/oppbud"]["cif24"] * wo + out["bygg/petition"]["cif24"] * (1 - wo)) \
      - (out["other/oppbud"]["cif24"] * wo + out["other/petition"]["cif24"] * (1 - wo))
print(f"  unadjusted bygg-other CIF24 gap (own mix)          = {raw:+.2f} pp")
print(f"  basis-standardised to the OTHER group basis mix    = {adj:+.2f} pp")
ajb = AJ(*mk([r for r in rows if r["bygg"]]))
ajo = AJ(*mk([r for r in rows if not r["bygg"]]))
print(f"  marginal CIF24 bygg={100*ajb.cif(730):.2f}  other={100*ajo.cif(730):.2f}  crude gap {100*(ajb.cif(730)-ajo.cif(730)):+.2f} pp")
out["comp"] = dict(unadj=raw, adj=adj, marg_bygg=100 * ajb.cif(730), marg_other=100 * ajo.cif(730))

json.dump(out, open(W + "V-B1-06-results.json", "w", encoding="utf-8"), indent=1, default=str)
print()
print("wrote V-B1-06-results.json")
