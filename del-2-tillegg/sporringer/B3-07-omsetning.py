# B3-07: revenue strata with CIs + AJ, log-revenue specification, bygg x revenue interaction, F-definition under M7.
import pandas as pd, numpy as np, math
from scipy import stats
rng = np.random.default_rng(20260912)
df = pd.read_csv("B3-05-analysedata.tsv", sep="\t", encoding="utf-8", low_memory=False)
df["revband"] = np.where(df.has_acc == 0, "2 <1 MNOK", np.where(df.rev_nok.isna(), "1 mangler", np.where(df.rev_nok < 1e6, "2 <1 MNOK", np.where(df.rev_nok < 5e6, "3 1-5 MNOK", np.where(df.rev_nok < 2e7, "4 5-20 MNOK", "5 >=20 MNOK")))))
df["revband_tab"] = np.where(df.has_acc == 0, "0 ingen regnskap", df.revband)
df["logrev"] = np.where(df.rev_nok.notna() & (df.has_acc == 1), np.log10(df.rev_nok.clip(lower=1e4)), 0.0)
df["rev_missing"] = ((df.has_acc == 1) & df.rev_nok.isna()).astype(int)
REF = {"size7": "2 <0,5 MNOK", "gapcat": "1 aar", "agecat": "3-10 aar", "tingrett": "OSLO TINGRETT", "revband": "2 <1 MNOK"}
def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z*z/n; c = (p + z*z/(2*n)) / d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (100*(c-h), 100*(c+h))
def newcombe(k1, n1, k2, n2):
    l1, u1 = [v/100 for v in wilson(k1, n1)]; l2, u2 = [v/100 for v in wilson(k2, n2)]
    p1, p2 = k1/n1, k2/n2; d = p1 - p2
    return (100*(d - math.sqrt((p1-l1)**2 + (u2-p2)**2)), 100*(d + math.sqrt((u1-p1)**2 + (p2-l2)**2)))
def aj_cif(t, cause, horizon=730):
    order = np.argsort(t, kind="stable"); t = t[order]; cause = cause[order]; S = 1.0; cif = 0.0
    for u in np.unique(t[(cause > 0) & (t <= horizon)]):
        ar = np.sum(t >= u); d1 = np.sum((t == u) & (cause == 1)); d2 = np.sum((t == u) & (cause == 2)); cif += S * d1 / ar; S *= (1 - (d1 + d2) / ar)
    return cif
def aj(d):
    t = np.where(d.t_inn.notna(), d.t_inn, np.where(d.t_avs.notna(), d.t_avs, d.fu)).astype(float); c = np.where(d.t_inn.notna(), 1, np.where(d.t_avs.notna(), 2, 0)); return aj_cif(t, c)
def design(d, terms, inter=()):
    cols = {"const": np.ones(len(d))}
    for t in terms:
        if t in ("bygg", "oppbud", "has_acc", "rev_missing"): cols[t] = d[t].values.astype(float)
        elif t == "logrev": cols["logrev"] = d.logrev.values; cols["logrev_sq"] = d.logrev.values ** 2
        else:
            for lv in sorted(d[t].unique()):
                if lv == REF[t]: continue
                cols[f"{t}={lv}"] = (d[t] == lv).values.astype(float)
    for a, b_ in inter:
        for k in list(cols):
            if k.startswith(b_ + "="): cols[f"byggX{k}"] = cols["bygg"] * cols[k]
    return np.column_stack(list(cols.values())), list(cols)
def irls(X, y, ridge=1e-8, maxit=100):
    beta = np.zeros(X.shape[1])
    for _ in range(maxit):
        p = 1 / (1 + np.exp(-(X @ beta))); W = p * (1 - p); step = np.linalg.solve(X.T @ (X * W[:, None]) + ridge * np.eye(X.shape[1]), X.T @ (y - p)); beta += step
        if np.max(np.abs(step)) < 1e-9: break
    p = 1 / (1 + np.exp(-(X @ beta))); W = p * (1 - p); cov = np.linalg.inv(X.T @ (X * W[:, None]) + ridge * np.eye(X.shape[1]))
    ll = np.sum(y * np.log(p + 1e-300) + (1 - y) * np.log(1 - p + 1e-300)); return beta, cov, ll
def rd(X, names, beta):
    i = names.index("bygg"); X1 = X.copy(); X0 = X.copy(); X1[:, i] = 1; X0[:, i] = 0
    for j, nm in enumerate(names):
        if nm.startswith("byggX"): k = names.index(nm[5:]); X1[:, j] = X1[:, k]; X0[:, j] = 0
    return (1 / (1 + np.exp(-(X1 @ beta)))).mean() - (1 / (1 + np.exp(-(X0 @ beta)))).mean()
def fit(d, y, terms, inter=(), boot=200):
    X, names = design(d, terms, inter); yy = d[y].values.astype(float); b, c, ll = irls(X, yy); i = names.index("bygg"); se = math.sqrt(c[i, i]); r = rd(X, names, b); bs = []
    for _ in range(boot):
        idx = rng.integers(0, len(d), len(d))
        try: b_, _, _ = irls(X[idx], yy[idx]); bs.append(rd(X[idx], names, b_))
        except np.linalg.LinAlgError: pass
    return dict(n=len(d), k=len(names), OR=math.exp(b[i]), lo=math.exp(b[i]-1.96*se), hi=math.exp(b[i]+1.96*se), p=2*(1-stats.norm.cdf(abs(b[i]/se))), rd=r, rdlo=np.percentile(bs, 2.5), rdhi=np.percentile(bs, 97.5), ll=ll, coefs={n_: (b[j], math.sqrt(c[j, j])) for j, n_ in enumerate(names)}, names=names)
d7 = df[df.full730 == 1].copy(); B = df.bygg == 1; O = ~B; F7 = df.full730 == 1
out = ["# B3-07 driftsinntekter (as-of 24.08.2026 / fasthorisont 730 d)\n"]
out.append("## Stratifisert paa driftsinntektsbaand (siste regnskap foer aapningsaaret)\n")
out.append("| Baand | Bygg n / andel | Oevrige n / andel | Bygg innstilt as-of | Oevrige as-of | Bygg innen 730 d | Oevrige innen 730 d | Diff 730 d [Newcombe] | Bygg CIF730 | Oevrige CIF730 |\n|---|---|---|---|---|---|---|---|---|---|")
rows = []
for lv in sorted(df.revband_tab.unique()):
    m = df.revband_tab == lv
    nb, no = int((m & B).sum()), int((m & O).sum()); kb, ko = int(df[m & B].y_asof.sum()), int(df[m & O].y_asof.sum())
    nb7, no7 = int((m & B & F7).sum()), int((m & O & F7).sum()); kb7, ko7 = int(df[m & B & F7].y730.sum()), int(df[m & O & F7].y730.sum())
    nc = newcombe(kb7, nb7, ko7, no7); cb, co = aj(df[m & B]), aj(df[m & O])
    out.append(f"| {lv} | {nb} ({100*nb/B.sum():.1f} %) | {no} ({100*no/O.sum():.1f} %) | {kb}/{nb} = {100*kb/nb:.1f} % | {ko}/{no} = {100*ko/no:.1f} % | {kb7}/{nb7} = {100*kb7/nb7:.1f} % | {ko7}/{no7} = {100*ko7/no7:.1f} % | {100*kb7/nb7-100*ko7/no7:+.1f} pp [{nc[0]:+.1f}; {nc[1]:+.1f}] | {100*cb:.1f} % | {100*co:.1f} % |")
    rows.append((kb7, nb7, ko7, no7))
num_ = den_ = 0; sn = sd = 0
for kb7, nb7, ko7, no7 in rows:
    n = nb7 + no7; num_ += kb7 * (no7 - ko7) / n; den_ += (nb7 - kb7) * ko7 / n; sn += (kb7 / nb7) * no7; sd += no7
crude_o = df[O & F7].y730.mean(); crude_b = df[B & F7].y730.mean()
out.append(f"\nRaa 730-d differanse {100*(crude_b-crude_o):+.1f} pp; bygg standardisert til oevriges driftsinntektsfordeling {100*sn/sd:.1f} % mot oevrige {100*crude_o:.1f} % -> {100*(sn/sd-crude_o):+.1f} pp; Mantel-Haenszel OR {num_/den_:.3f}.\n")
out.append("## Modeller (730 d, n = %d)\n" % len(d7))
out.append("| Modell | par. | OR bygg [95 %] | p | Marginal RD [95 %] |\n|---|---|---|---|---|")
res = {}
for lab, terms, inter in [("M0 bygg", ["bygg"], ()), ("bygg + log10(driftsinntekter) + kvadrat + mangler-flagg + ingen-regnskap", ["bygg", "logrev", "rev_missing", "has_acc"], ()),
                          ("M7 full (stoerrelse, oppbud, avstand, alder, rettskrets, driftsinntektsbaand)", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett", "revband"], ()),
                          ("M7 + bygg x driftsinntektsbaand", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett", "revband"], (("bygg", "revband"),)),
                          ("M7 + bygg x oppbud", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett", "revband"], (("bygg", "oppbud"),))]:
    r = fit(d7, "y730", terms, inter); res[lab] = r
    out.append(f"| {lab} | {r['k']} | {r['OR']:.3f} [{r['lo']:.3f}; {r['hi']:.3f}] | {r['p']:.2g} | {100*r['rd']:+.1f} pp [{100*r['rdlo']:+.1f}; {100*r['rdhi']:+.1f}] |")
base = res["M7 full (stoerrelse, oppbud, avstand, alder, rettskrets, driftsinntektsbaand)"]
for lab in ["M7 + bygg x driftsinntektsbaand", "M7 + bygg x oppbud"]:
    r = res[lab]; lr = 2 * (r["ll"] - base["ll"]); dfree = r["k"] - base["k"]
    ints = "; ".join(f"{nm[5:]}: x{math.exp(min(r['coefs'][nm][0],50)):.2f} (se {r['coefs'][nm][1]:.2f})" for nm in r["names"] if nm.startswith("byggX"))
    out.append(f"\nLR-test {lab}: chi2 = {lr:.2f}, df = {dfree}, p = {1-stats.chi2.cdf(lr, dfree):.3f}; ledd: {ints}")
# bygg x oppbud under M7: note oppbud interaction handled via prefix "oppbud=" not present -> add manual
X, names = design(d7, ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett", "revband"]); Xi = np.column_stack([X, d7.bygg.values * d7.oppbud.values]); ni = names + ["byggXoppbud"]
b, c, ll = irls(Xi, d7.y730.values.astype(float)); lr = 2 * (ll - base["ll"]); j = ni.index("byggXoppbud"); i = ni.index("bygg")
out.append(f"\nM7 + bygg x oppbud (manuelt ledd): LR chi2 = {lr:.2f}, df 1, p = {1-stats.chi2.cdf(lr,1):.3f}; OR bygg blant begjaering {math.exp(b[i]):.3f} [{math.exp(b[i]-1.96*math.sqrt(c[i,i])):.3f}; {math.exp(b[i]+1.96*math.sqrt(c[i,i])):.3f}]; multiplikator for oppbud x{math.exp(b[j]):.2f} (se {math.sqrt(c[j,j]):.2f}) -> OR bygg blant oppbud {math.exp(b[i]+b[j]):.3f}.\n")
rF = fit(d7.assign(bygg=d7.byggF), "y730", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett", "revband"], (), boot=100)
out.append(f"M7 med omraade F (41-43) som byggmerke: OR {rF['OR']:.3f} [{rF['lo']:.3f}; {rF['hi']:.3f}], RD {100*rF['rd']:+.1f} pp [{100*rF['rdlo']:+.1f}; {100*rF['rdhi']:+.1f}].\n")
ra = fit(df, "y_asof", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett", "revband"], (), boot=150)
out.append(f"M7 paa as-of-utfallet, alle 5 165: OR {ra['OR']:.3f} [{ra['lo']:.3f}; {ra['hi']:.3f}], RD {100*ra['rd']:+.1f} pp [{100*ra['rdlo']:+.1f}; {100*ra['rdhi']:+.1f}].\n")
# revenue vs size: are they the same thing? Spearman among those with both
m = df.rev_nok.notna() & df.ta_nok.notna()
out.append(f"Spearman(driftsinntekter, sum eiendeler) blant {int(m.sum())} med begge: {stats.spearmanr(df[m].rev_nok, df[m].ta_nok).correlation:.2f}. Bygg: median driftsinntekter/sum eiendeler {(df[B & m].rev_nok/df[B & m].ta_nok.replace(0,np.nan)).median():.2f}; oevrige {(df[O & m].rev_nok/df[O & m].ta_nok.replace(0,np.nan)).median():.2f}.\n")
# revenue-missing composition
out.append(f"Driftsinntekter mangler (NULL) blant dem med regnskap: bygg {int((B & (df.has_acc==1) & df.rev_nok.isna()).sum())}/{int((B & (df.has_acc==1)).sum())}, oevrige {int((O & (df.has_acc==1) & df.rev_nok.isna()).sum())}/{int((O & (df.has_acc==1)).sum())}; driftsinntekter = 0 (rapportert null): bygg {int((B & (df.rev_nok==0)).sum())}, oevrige {int((O & (df.rev_nok==0)).sum())}.\n")
open("B3-07-omsetning.md", "w", encoding="utf-8").write("\n".join(out) + "\n"); print("\n".join(out))
