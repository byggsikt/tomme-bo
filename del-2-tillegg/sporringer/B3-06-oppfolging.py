# B3 follow-up: revenue band as scale/employee proxy; models within oppbud / non-oppbud; time-to-event medians.
import pandas as pd, numpy as np, math
from scipy import stats
rng = np.random.default_rng(20260912)
df = pd.read_csv("B3-05-analysedata.tsv", sep="\t", encoding="utf-8", low_memory=False)
for c in ["opened", "innstilt", "avsluttet"]: df[c] = pd.to_datetime(df[c], errors="coerce")
# no-accounts group is mapped to the reference band: its effect is carried by the size7 level (avoids collinearity)
df["revband"] = np.where(df.has_acc == 0, "2 <1 MNOK", np.where(df.rev_nok.isna(), "1 mangler", np.where(df.rev_nok < 1e6, "2 <1 MNOK", np.where(df.rev_nok < 5e6, "3 1-5 MNOK", np.where(df.rev_nok < 2e7, "4 5-20 MNOK", "5 >=20 MNOK")))))
df["revband_tab"] = np.where(df.has_acc == 0, "0 ingen regnskap", df.revband)
REF = {"size7": "2 <0,5 MNOK", "gapcat": "1 aar", "agecat": "3-10 aar", "tingrett": "OSLO TINGRETT", "revband": "2 <1 MNOK"}
def design(d, terms):
    cols = {"const": np.ones(len(d))}
    for t in terms:
        if t in ("bygg", "oppbud", "has_acc", "varsel"): cols[t] = d[t].values.astype(float)
        else:
            for lv in sorted(d[t].unique()):
                if lv == REF[t]: continue
                cols[f"{t}={lv}"] = (d[t] == lv).values.astype(float)
    return np.column_stack(list(cols.values())), list(cols)
def irls(X, y, ridge=1e-8, maxit=100):
    beta = np.zeros(X.shape[1])
    for _ in range(maxit):
        p = 1 / (1 + np.exp(-(X @ beta))); W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + ridge * np.eye(X.shape[1]); step = np.linalg.solve(H, X.T @ (y - p)); beta += step
        if np.max(np.abs(step)) < 1e-9: break
    p = 1 / (1 + np.exp(-(X @ beta))); W = p * (1 - p)
    cov = np.linalg.inv(X.T @ (X * W[:, None]) + ridge * np.eye(X.shape[1]))
    return beta, cov
def rd(X, names, beta):
    i = names.index("bygg"); X1 = X.copy(); X0 = X.copy(); X1[:, i] = 1; X0[:, i] = 0
    return (1 / (1 + np.exp(-(X1 @ beta)))).mean() - (1 / (1 + np.exp(-(X0 @ beta)))).mean()
def fit(d, y, terms, boot=200):
    X, names = design(d, terms); yy = d[y].values.astype(float); b, c = irls(X, yy); i = names.index("bygg"); se = math.sqrt(c[i, i])
    r = rd(X, names, b); bs = []
    for _ in range(boot):
        idx = rng.integers(0, len(d), len(d));
        try: b_, _ = irls(X[idx], yy[idx]); bs.append(rd(X[idx], names, b_))
        except np.linalg.LinAlgError: pass
    return dict(n=len(d), OR=math.exp(b[i]), lo=math.exp(b[i] - 1.96 * se), hi=math.exp(b[i] + 1.96 * se), p=2 * (1 - stats.norm.cdf(abs(b[i] / se))), rd=r, rdlo=np.percentile(bs, 2.5), rdhi=np.percentile(bs, 97.5), coefs={n_: (b[j], math.sqrt(c[j, j])) for j, n_ in enumerate(names)})
d7 = df[df.full730 == 1].copy()
out = []
out.append("# B3-06 oppfoelging (730-d utfall, delkohort n=%d)\n" % len(d7))
out.append("## Driftsinntekter (siste regnskap foer aapningsaaret) som proxy for driftsomfang/ansatte\n")
out.append("| Baand | Bygg n (andel) | Oevrige n (andel) | Bygg innen 730 d | Oevrige innen 730 d | Diff |\n|---|---|---|---|---|---|")
B = d7.bygg == 1
for lv in sorted(d7.revband_tab.unique()):
    m = d7.revband_tab == lv; nb, no = int((m & B).sum()), int((m & ~B).sum()); kb, ko = int(d7[m & B].y730.sum()), int(d7[m & ~B].y730.sum())
    out.append(f"| {lv} | {nb} ({100*nb/B.sum():.1f} %) | {no} ({100*no/(~B).sum():.1f} %) | {kb}/{nb} = {100*kb/nb:.1f} % | {ko}/{no} = {100*ko/no:.1f} % | {100*kb/nb-100*ko/no:+.1f} pp |")
out.append("\n| Modell | n | OR bygg [95 %] | p | Marginal RD [95 %] |\n|---|---|---|---|---|")
specs = [("M0 bygg alene", ["bygg"]),
         ("M5 (stoerrelse, oppbud, avstand, alder, rettskrets)", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett"]),
         ("M7 = M5 + driftsinntektsbaand", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett", "revband"]),
         ("M7b = bygg + driftsinntektsbaand alene", ["bygg", "revband"])]
for lab, terms in specs:
    r = fit(d7, "y730", terms); out.append(f"| {lab} | {r['n']} | {r['OR']:.3f} [{r['lo']:.3f}; {r['hi']:.3f}] | {r['p']:.2g} | {100*r['rd']:+.1f} pp [{100*r['rdlo']:+.1f}; {100*r['rdhi']:+.1f}] |")
    if lab.startswith("M7 ="):
        out.append("\nDriftsinntektsledd i M7 (OR mot <1 MNOK): " + "; ".join(f"{k[8:]}: {math.exp(min(v[0],50)):.2f} [{math.exp(min(v[0]-1.96*v[1],50)):.2f}; {math.exp(min(v[0]+1.96*v[1],50)):.2f}]" for k, v in r["coefs"].items() if k.startswith("revband=")) + "\n")
        out.append("Stoerrelsesledd i M7 (OR mot <0,5 MNOK): " + "; ".join(f"{k[6:]}: {math.exp(v[0]):.2f}" for k, v in r["coefs"].items() if k.startswith("size7=")) + "\n")
        out.append("| Modell | n | OR bygg [95 %] | p | Marginal RD [95 %] |\n|---|---|---|---|---|")
out.append("\n## Innenfor aapningsgrunnlag\n")
out.append("| Delmengde | Modell | n | OR bygg [95 %] | p | Marginal RD [95 %] |\n|---|---|---|---|---|---|")
for sub, m in [("oppbud", d7.oppbud == 1), ("ikke oppbud (begjaering)", d7.oppbud == 0)]:
    dd = d7[m]
    for lab, terms in [("M0 bygg alene", ["bygg"]), ("M5 uten oppbud-ledd", ["bygg", "size7", "gapcat", "agecat", "tingrett"]), ("M7 (+ driftsinntekt)", ["bygg", "size7", "gapcat", "agecat", "tingrett", "revband"])]:
        r = fit(dd, "y730", terms, boot=150); out.append(f"| {sub} | {lab} | {r['n']} | {r['OR']:.3f} [{r['lo']:.3f}; {r['hi']:.3f}] | {r['p']:.2g} | {100*r['rd']:+.1f} pp [{100*r['rdlo']:+.1f}; {100*r['rdhi']:+.1f}] |")
out.append("\n## Balanse og drift etter aapningsgrunnlag (hele kohorten)\n")
out.append("| Gruppe | n | har regnskap | median sum eiendeler | median driftsinntekter | driftsinntekter >= 5 MNOK | negativ EK |\n|---|---|---|---|---|---|---|")
for g, m in [("bygg, oppbud", (df.bygg == 1) & (df.oppbud == 1)), ("bygg, begjaering", (df.bygg == 1) & (df.oppbud == 0)), ("oevrige, oppbud", (df.bygg == 0) & (df.oppbud == 1)), ("oevrige, begjaering", (df.bygg == 0) & (df.oppbud == 0))]:
    d = df[m]
    out.append(f"| {g} | {len(d)} | {100*d.has_acc.mean():.1f} % | {d.ta_nok.median()/1e6:.2f} MNOK | {d.rev_nok.median()/1e6:.2f} MNOK | {100*(d.rev_nok>=5e6).sum()/len(d):.1f} % | {100*d.neg_eq.mean():.1f} % |")
out.append("\n## Tid til innstilling (dager, blant innstilte innen 730 d i delkohorten) og tid til ordinaer avslutning\n")
out.append("| Gruppe | n innstilt | median dager | Q1-Q3 | n avsluttet innen 730 d | median dager |\n|---|---|---|---|---|---|")
for g, m in [("bygg", d7.bygg == 1), ("oevrige", d7.bygg == 0), ("bygg oppbud", (d7.bygg == 1) & (d7.oppbud == 1)), ("oevrige oppbud", (d7.bygg == 0) & (d7.oppbud == 1)), ("bygg begjaering", (d7.bygg == 1) & (d7.oppbud == 0)), ("oevrige begjaering", (d7.bygg == 0) & (d7.oppbud == 0))]:
    d = d7[m]; ti = d.t_inn[(d.y730 == 1)]; ta = d.t_avs[(d.t_avs.notna()) & (d.t_avs <= 730) & (d.y730 == 0)]
    out.append(f"| {g} | {len(ti)} | {ti.median():.0f} | {ti.quantile(.25):.0f}-{ti.quantile(.75):.0f} | {len(ta)} | {ta.median():.0f} |")
# Chi-square: oppbud share bygg vs other
kb, nb = int(df[df.bygg == 1].oppbud.sum()), int((df.bygg == 1).sum()); ko, no = int(df[df.bygg == 0].oppbud.sum()), int((df.bygg == 0).sum())
chi = stats.chi2_contingency([[kb, nb - kb], [ko, no - ko]])
out.append(f"\nOppbud-andel bygg {kb}/{nb} = {100*kb/nb:.1f} % mot oevrige {ko}/{no} = {100*ko/no:.1f} %: chi2 = {chi[0]:.1f}, p = {chi[1]:.2g}.\n")
# among bygg: oppbud share by size band
out.append("| Stoerrelse | Bygg: oppbud-andel | Oevrige: oppbud-andel |\n|---|---|---|")
for lv in sorted(df.size4.unique()):
    m = df.size4 == lv
    out.append(f"| {lv} | {100*df[m & (df.bygg==1)].oppbud.mean():.1f} % (n={int((m&(df.bygg==1)).sum())}) | {100*df[m & (df.bygg==0)].oppbud.mean():.1f} % (n={int((m&(df.bygg==0)).sum())}) |")
open("B3-06-oppfolging.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
