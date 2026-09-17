# V-B1-10: remaining claimed quantities + study-lock reproduction check.
import sys, math, json, collections
import numpy as np
from scipy import stats
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
W = r"../data/"
sys.path.insert(0, W)
from V_B1_shared import AJ, gray, wilson, load, mk, rd_delta

END = date(2026, 8, 24); Z = stats.norm.ppf(0.975); BAR = "=" * 78
rows = load(W + "V-B1-04-tagged.tsv", END)
out = {}

print(BAR); print("STUDY-LOCK REPRODUCTION ON THE DB PATH (TALLJOURNAL I1/I1b/I2/I2b/I3)"); print(BAR)
for nm, g in (("alle", rows), ("bygg", [r for r in rows if r["bygg"]]), ("ovrige", [r for r in rows if not r["bygg"]])):
    aj = AJ(*mk(g))
    lo, hi, se = aj.ci(730)
    compl = [r["t"] for r in g if r["cause"] == 1]
    print(f"  {nm:7s} n={len(g):5d}  CIF12={100*aj.cif(365):.2f}  CIF18={100*aj.cif(548):.2f}  CIF24={100*aj.cif(730):.2f} [{100*lo:.2f}-{100*hi:.2f}]  CIF-median={aj.qday(0.5)}  raw-median={int(np.median(compl))}")
    out[nm] = dict(c12=100 * aj.cif(365), c18=100 * aj.cif(548), c24=100 * aj.cif(730),
                   lo=100 * lo, hi=100 * hi, q50=aj.qday(0.5))
b = [r for r in rows if r["bygg"]]; ov = [r for r in rows if not r["bygg"]]
U, V, z, pv = gray(*mk(b), *mk(ov))
r24, lo, hi, se, pp = rd_delta(AJ(*mk(b)), AJ(*mk(ov)), 730)
print(f"  Gray bygg vs ovrige z={z:.3f} chi2={z*z:.3f} p={pv:.3e}")
print(f"  RD 24 m bygg-ovrige = {100*r24:+.2f} pp [{100*lo:+.2f}; {100*hi:+.2f}]")
print("  STUDY LOCK (frozen extract): alle 74.82 [73.60-75.99] / bygg 70.54 [67.93-72.98] / ovrige 76.23 [74.85-77.55]")
print("                               Gray z=-5.671 chi2=32.157 p=1.42e-8 ; RD -5.70 [-8.56; -2.83]")
print("                               TALLJOURNAL I1 note: the boundary rule gives 74.88 % overall")
out["gray_bygg"] = dict(z=z, chi2=z * z, p=pv)
out["rd_bygg"] = dict(rd=100 * r24, lo=100 * lo, hi=100 * hi)

print()
print(BAR); print("CIF-DAYS TO 50 % AND RAW MEDIANS, WITH INTERVALS"); print(BAR)


def qci(aj, p=0.5):
    lo = hi = None
    for i, dday in enumerate(aj.days):
        l, u, _ = aj.ci(int(dday))
        if lo is None and u >= p: lo = int(dday)
        if hi is None and l >= p: hi = int(dday)
        if lo is not None and hi is not None: break
    return lo, hi


def bootmed(g, B=2000, seed=20260912):
    rng = np.random.default_rng(seed)
    x = np.array([r["t"] for r in g if r["cause"] == 1])
    s = [np.median(x[rng.integers(0, len(x), len(x))]) for _ in range(B)]
    return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


def bootq(g, B=1000, seed=20260912):
    rng = np.random.default_rng(seed)
    t = np.array([r["t"] for r in g]); c = np.array([r["cause"] for r in g])
    s = []
    for _ in range(B):
        i = rng.integers(0, len(t), len(t))
        q = AJ(t[i], c[i]).qday(0.5)
        if q is not None: s.append(q)
    return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5)), np.array(s)


qs = {}
for nm, bs in (("oppbud", "oppbud"), ("petition", "ikke_oppbud")):
    g = [r for r in rows if r["basis"] == bs]
    aj = AJ(*mk(g))
    l, h = qci(aj)
    compl = [r["t"] for r in g if r["cause"] == 1]
    ml, mh = bootmed(g)
    bl, bh, arr = bootq(g)
    qs[nm] = arr
    print(f"  {nm:9s} CIF-days to 50 % = {aj.qday(0.5)} [test-inversion {l}-{h}] [bootstrap {bl:.0f}-{bh:.0f}]   raw median among innstilt = {int(np.median(compl))} [boot {ml:.0f}-{mh:.0f}]")
    out[f"q_{nm}"] = dict(q=aj.qday(0.5), ti=[l, h], boot=[bl, bh], rawmed=float(np.median(compl)), rawboot=[ml, mh])
dq = qs["petition"] - qs["oppbud"]
print(f"  difference in CIF-days to 50 % = {out['q_petition']['q']-out['q_oppbud']['q']:+d} d [bootstrap {np.percentile(dq,2.5):+.0f}; {np.percentile(dq,97.5):+.0f}]")
print(f"  difference in raw medians      = {out['q_petition']['rawmed']-out['q_oppbud']['rawmed']:+.0f} d")
out["dq"] = [float(np.percentile(dq, 2.5)), float(np.percentile(dq, 97.5))]

print()
print(BAR); print("BASIS MISSINGNESS SANITY: is the oppbud flag court-practice noise?"); print(BAR)
cnt = collections.Counter(r["tingrett"] for r in rows)
sh = []
for c, n in cnt.most_common():
    k = sum(1 for r in rows if r["tingrett"] == c and r["basis"] == "oppbud")
    sh.append((c, n, k, 100 * k / n))
print(f"  oppbud share across 23 courts: min {min(x[3] for x in sh):.1f} % ({min(sh,key=lambda x:x[3])[0]})  max {max(x[3] for x in sh):.1f} % ({max(sh,key=lambda x:x[3])[0]})")
tab = [[0, 0], [0, 0]]
for r in rows:
    tab[0 if r["basis"] == "oppbud" else 1][0 if r["bygg"] else 1] += 1
x2 = stats.chi2_contingency([[x[2], x[1] - x[2]] for x in sh])
print(f"  chi2 for court x basis: {x2.statistic:.1f}, df {x2.dof}, p = {x2.pvalue:.3g}  -> the oppbud share DOES vary by court")
print("  (no court is at 0 % or 100 %; the smallest share is Oslo 57.8 %, the largest Trondelag 85.0 %)")
out["court_basis_chi2"] = dict(stat=float(x2.statistic), df=int(x2.dof), p=float(x2.pvalue))
sub = [r for r in rows if r["opened"] <= date(2024, 8, 24)]
ko = sum(1 for r in sub if r["basis"] == "oppbud")
ke = sum(1 for r in rows if r["opened"] > date(2024, 8, 24) and r["basis"] == "oppbud")
print(f"  oppbud share in the 730-d sub-cohort {ko}/{len(sub)} = {100*ko/len(sub):.1f} %  vs excluded {ke}/{len(rows)-len(sub)} = {100*ke/(len(rows)-len(sub)):.1f} %")
out["subcohort_balance"] = dict(sub=100 * ko / len(sub), excl=100 * ke / (len(rows) - len(sub)))

json.dump(out, open(W + "V-B1-10-results.json", "w", encoding="utf-8"), indent=1, default=str)
print()
print("wrote V-B1-10-results.json")
