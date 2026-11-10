# B1-03: supplements — (1) where the two CIF curves cross (explains Gray p=0.63 vs RD24 p=1.5e-4),
# (2) competing-event side of the four basis×construction cells, (3) does court variation survive
# adjustment for basis? (manuscript ch. 13.3 hypothesis), (4) quantile ladder per basis.
import sys, json, collections
import numpy as np
from scipy import stats as st
sys.path.insert(0, r"../data")
from B1_lib import AJ, gray_test, wilson, newcombe, logit_fit, H12, H18, H24, Z, chi2_yates

W = r"../data"
rows = [l.rstrip("\n").split("\t") for l in open(f"{W}/B1-cohort-tagged.tsv", encoding="utf-8")][1:]
t = np.array([int(r[3]) for r in rows]); cause = np.array([int(r[4]) for r in rows])
opp = np.array([r[5] == "1" for r in rows]); bygg = np.array([r[6] == "1" for r in rows])
court = np.array([r[8] for r in rows]); full = np.array([r[9] == "1" for r in rows]); inn730 = np.array([r[10] == "1" for r in rows])
N = len(rows); innstilt = cause == 1; avsl = cause == 2; open_ = cause == 0
md = []; res = {}
def P(s=""):
    md.append(s)
def pct(x, d=1): return f"{100*x:.{d}f}"

# ---------------------------------------------------------------- (1) crossing
ajO = AJ(t[opp], cause[opp]); ajB = AJ(t[~opp], cause[~opp])
P("## S1. Hvor krysser kurvene? CIF innstilling per grunnlag på flere horisonter")
P()
P("| dag | CIF oppbud % [delta 95 %] | CIF begjæring % [delta 95 %] | RD begjæring − oppbud pp [Wald] | z | CIF ordinær avslutning oppbud / begjæring % | uavgjort oppbud / begjæring % |")
P("|---:|---:|---:|---:|---:|---:|---:|")
res["ladder"] = {}
for h in (30, 60, 90, 120, 150, 180, 240, 270, 300, 365, 450, 548, 640, 730, 900):
    fo, fb = ajO.F1(h), ajB.F1(h); lo_o, hi_o, _ = ajO.ci(h); lo_b, hi_b, _ = ajB.ci(h)
    se = np.sqrt(ajO.var(h) + ajB.var(h)); rd = fb - fo
    P(f"| {h} | {pct(fo,2)} [{pct(lo_o,1)}–{pct(hi_o,1)}] | {pct(fb,2)} [{pct(lo_b,1)}–{pct(hi_b,1)}] | {100*rd:+.2f} [{100*(rd-Z*se):+.2f}; {100*(rd+Z*se):+.2f}] | {rd/se:.2f} | {pct(ajO.Fcomp(h),1)} / {pct(ajB.Fcomp(h),1)} | {pct(ajO.S(h),1)} / {pct(ajB.S(h),1)} |")
    res["ladder"][h] = dict(F_opp=fo, F_begj=fb, rd=rd, se=se, Fc_opp=ajO.Fcomp(h), Fc_begj=ajB.Fcomp(h), S_opp=ajO.S(h), S_begj=ajB.S(h))
# crossing day: last day where F_opp > F_begj, and first day after which F_begj >= F_opp for all later days
T = min(ajO.T, ajB.T)
diff = ajB.F[:T] - ajO.F[:T]
neg = np.nonzero(diff < 0)[0]
last_neg = int(neg[-1]) if len(neg) else None
pos_first = int(np.nonzero(diff > 0)[0][0]) if (diff > 0).any() else None
max_neg_day = int(np.argmin(diff)); max_neg = float(diff[max_neg_day])
P()
P(f"Oppbudskurven ligger **over** begjæringskurven fra dag {pos_first if pos_first is not None and diff[pos_first] > 0 and pos_first < 30 else '—'}… nei: se tallene — største forsprang for oppbud er {100*(-max_neg):.2f} pp på dag {max_neg_day}; siste dag der oppbud ligger foran er dag **{last_neg}**; deretter ligger begjæringskurven foran til korpusslutt.")
res["crossing"] = dict(last_day_oppbud_ahead=last_neg, max_oppbud_lead_pp=-max_neg, max_lead_day=max_neg_day)
# Gray restricted to t > 365 (post-crossing) as a descriptive check (not a pre-specified test)
P()
P("## S2. Kvantilstige per grunnlag (CIF-baserte dager til X % innstilt)")
P()
P("| Grunnlag | 25 % | 40 % | 50 % | 60 % | 70 % | 75 % |")
P("|---|---:|---:|---:|---:|---:|---:|")
for lab, a in (("oppbud", ajO), ("begjæring", ajB)):
    P(f"| {lab} | " + " | ".join(str(a.quantile(p)) for p in (0.25, 0.40, 0.50, 0.60, 0.70, 0.75)) + " |")
res["quantiles"] = {lab: {p: a.quantile(p) for p in (0.25, 0.40, 0.50, 0.60, 0.70, 0.75)} for lab, a in (("oppbud", ajO), ("begjaering", ajB))}

# ---------------------------------------------------------------- (2) four cells, competing side
P()
P("## S3. De fire cellene — alle tre utfall (as-of og ved 24 mnd)")
P()
P("| Næring | Grunnlag | n | as-of innstilt % | as-of ordinær avslutning % | as-of åpne % | CIF 24 mnd innstilling % | CIF 24 mnd ordinær avslutning % [delta 95 %] | uavgjort ved 24 mnd % | risikomengde 730 d | as-of «bo med bobehandling» (avsluttet + åpne) % [Wilson] |")
P("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
res["cells"] = {}
cellaj = {}
for bl, bm in (("bygg", bygg), ("øvrige", ~bygg)):
    for gl, gm in (("oppbud", opp), ("begjæring", ~opp)):
        m = bm & gm; n = int(m.sum()); ki, ka, ko = int((m & innstilt).sum()), int((m & avsl).sum()), int((m & open_).sum())
        a = AJ(t[m], cause[m]); a2 = AJ(t[m], np.where(cause[m] == 1, 2, np.where(cause[m] == 2, 1, 0)))
        lo2, hi2, _ = a2.ci(H24)
        cellaj[(bl, gl)] = (a, a2, m)
        nb = ka + ko
        P(f"| {bl} | {gl} | {n} | {pct(ki/n)} ({ki}) | {pct(ka/n)} ({ka}) | {pct(ko/n)} ({ko}) | {pct(a.F1(H24),1)} | {pct(a2.F1(H24),1)} [{pct(lo2,1)}–{pct(hi2,1)}] | {pct(a.S(H24),1)} | {a.at_risk(H24)} | {pct(nb/n)} [{pct(wilson(nb,n)[0])}–{pct(wilson(nb,n)[1])}] |")
        res["cells"][f"{bl}/{gl}"] = dict(n=n, innstilt=ki, avsluttet=ka, aapen=ko, cif24=a.F1(H24), cif24_avsl=a2.F1(H24), cif24_avsl_ci=(lo2, hi2), S24=a.S(H24))
P()
# contrasts on the competing event within oppbud: bygg vs øvrige
for gl in ("oppbud", "begjæring"):
    aB2, mB = cellaj[("bygg", gl)][1], cellaj[("bygg", gl)][2]; aO2, mO = cellaj[("øvrige", gl)][1], cellaj[("øvrige", gl)][2]
    rd = aB2.F1(H24) - aO2.F1(H24); se = np.sqrt(aB2.var(H24) + aO2.var(H24))
    c2 = np.where(cause == 1, 2, np.where(cause == 2, 1, 0))
    _, _, gz, gp = gray_test(t[mB], c2[mB], t[mO], c2[mO])
    P(f"- Ordinær avslutning ved 24 mnd, bygg − øvrige innen **{gl}**: RD {100*rd:+.2f} pp [{100*(rd-Z*se):+.2f}; {100*(rd+Z*se):+.2f}]; Grays test på avslutningskurven z = {gz:.2f}, p = {gp:.1e}.")
    res[f"avsl_contrast_{gl}"] = dict(rd=rd, wald=(rd-Z*se, rd+Z*se), gray_z=gz, gray_p=gp)
P()

# ---------------------------------------------------------------- (3) court variation after basis adjustment
P("## S4. Forklarer åpningsgrunnlaget domstolsvariasjonen? (manus kap. 13.3-hypotesen)")
P()
levels = sorted(set(court)); levels.remove("OSLO TINGRETT")
def X_of(mask, with_court, with_basis, with_bygg):
    cols = [np.ones(mask.sum())]
    if with_basis: cols.append((~opp[mask]).astype(float))
    if with_bygg: cols.append(bygg[mask].astype(float))
    if with_court:
        for L in levels: cols.append((court[mask] == L).astype(float))
    return np.column_stack(cols)
P("| vindu | modell | LR-test for rettskrets (22 df) χ² | p |")
P("|---|---|---:|---:|")
res["court_lr"] = {}
for lab, mask, y in (("as-of", np.ones(N, bool), innstilt.astype(float)), ("fast 730 d", full, inn730.astype(float))):
    for bl, (wb, wg) in (("uten kovariater", (False, False)), ("justert for grunnlag", (True, False)), ("justert for grunnlag + bygg", (True, True))):
        _, _, ll0 = logit_fit(X_of(mask, False, wb, wg), y[mask]); _, _, ll1 = logit_fit(X_of(mask, True, wb, wg), y[mask])
        lr = 2 * (ll1 - ll0); p = st.chi2.sf(lr, 22)
        P(f"| {lab} | {bl} | {lr:.1f} | {p:.4f} |")
        res["court_lr"][f"{lab} / {bl}"] = dict(lr=lr, p=p)
P()
# does oppbud share correlate with court innstilling share? (23 courts)
cs = collections.Counter(court)
xs = []; ys = []; ns = []
for c in cs:
    m = court == c; xs.append(opp[m].mean()); ys.append(innstilt[m].mean()); ns.append(m.sum())
r, pr = st.pearsonr(xs, ys); rs, prs = st.spearmanr(xs, ys)
P(f"Korrelasjon over 23 kretser mellom oppbudsandel og as-of innstilt-andel: Pearson r = {r:.2f} (p = {pr:.2f}), Spearman ρ = {rs:.2f} (p = {prs:.2f}). "
  f"Med kretsvekting (n): r = {np.corrcoef(np.repeat(xs, ns), np.repeat(ys, ns))[0,1]:.2f}.")
res["court_corr"] = dict(pearson=r, p=pr, spearman=rs, p_s=prs)
P()

# ---------------------------------------------------------------- (4) fixed-window check within cells for 730d
P("## S5. Antakelsesfri 730-dagers kontroll innen de fire cellene (delkohort åpnet ≤ 24.08.2024)")
P()
P("| Næring | Grunnlag | n | innstilt ≤ 730 d | % [Wilson] | [Clopper–Pearson] |")
P("|---|---|---:|---:|---:|---:|")
from B1_lib import clopper_pearson
for bl, bm in (("bygg", bygg), ("øvrige", ~bygg)):
    for gl, gm in (("oppbud", opp), ("begjæring", ~opp)):
        m = bm & gm & full; n = int(m.sum()); k = int((m & inn730).sum())
        P(f"| {bl} | {gl} | {n} | {k} | {pct(k/n)} [{pct(wilson(k,n)[0])}–{pct(wilson(k,n)[1])}] | [{pct(clopper_pearson(k,n)[0])}–{pct(clopper_pearson(k,n)[1])}] |")
P()

json.dump(res, open(f"{W}/B1-supplement-results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
open(f"{W}/B1-supplement-tables.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
print("\n".join(md))
