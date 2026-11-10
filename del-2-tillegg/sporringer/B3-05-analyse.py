# B3 construction-mechanism analysis. Input: B3-03-kohort-klassifisert.tsv (5 165 rows). Output: B3-05-results.md + .json
import pandas as pd, numpy as np, json, math, sys
from scipy import stats
rng = np.random.default_rng(20260912)
CENSOR = pd.Timestamp("2026-08-24")
df = pd.read_csv("B3-03-kohort-klassifisert.tsv", sep="\t", dtype=str, keep_default_na=False, encoding="utf-8")
assert len(df) == 5165
num = lambda s: pd.to_numeric(s.replace("", np.nan), errors="coerce")
for c in ["total_assets","current_assets","equity","liabilities","current_liabilities","operating_revenue","operating_result","annual_result","kapital_ved_reg","kapital_siste","n_acc_before","n_acc_any","n_varsel_for","fiscal_year"]:
    df[c] = num(df[c])
for c in ["opened","innstilt","avsluttet","stiftet","fristdag"]:
    df[c] = pd.to_datetime(df[c].replace("", np.nan), errors="coerce")
df["bygg"] = df.bygg_U.astype(int); df["byggF"] = df.bygg_F.astype(int); df["uklass"] = df.uklass.astype(int)
df["oppbud"] = (df.oppbud == "t").astype(int)
df["y_asof"] = (df.utfall == "innstilt").astype(int)
df["open_asof"] = (df.utfall == "aapen").astype(int)
df["fu"] = (CENSOR - df.opened).dt.days
df["t_inn"] = (df.innstilt - df.opened).dt.days
df["t_avs"] = (df.avsluttet - df.opened).dt.days
df["full730"] = (df.fu >= 730).astype(int)
df["y730"] = ((df.t_inn.notna()) & (df.t_inn <= 730)).astype(int)
df["open730"] = (~((df.t_inn.notna()) & (df.t_inn <= 730)) & ~((df.t_avs.notna()) & (df.t_avs <= 730))).astype(int)
# accounts
df["has_acc"] = df.fiscal_year.notna().astype(int)
rate = {"EUR": 11.5, "USD": 10.5, "NOK": 1.0, "": np.nan}
df["fx"] = df.currency.map(rate)
df["ta_nok"] = df.total_assets * df.fx
df["ca_nok"] = df.current_assets * df.fx
df["eq_nok"] = df.equity * df.fx
df["rev_nok"] = df.operating_revenue * df.fx
df["liab_nok"] = df.liabilities * df.fx
df["fa_nok"] = df.ta_nok - df.ca_nok
df["ca_share"] = np.where(df.ta_nok > 0, df.ca_nok / df.ta_nok, np.nan)
df["fa_share"] = np.where(df.ta_nok > 0, df.fa_nok / df.ta_nok, np.nan)
df["eq_ratio"] = np.where(df.ta_nok > 0, df.eq_nok / df.ta_nok, np.nan)
df["neg_eq"] = np.where(df.has_acc == 1, (df.eq_nok < 0).astype(float), np.nan)
df["ta_zero"] = np.where(df.has_acc == 1, (df.ta_nok == 0).astype(float), np.nan)
def band4(x, has):
    if not has: return "0 ingen regnskap"
    if x < 1e6: return "1 <1 MNOK"
    if x < 5e6: return "2 1-5 MNOK"
    return "3 >=5 MNOK"
def band7(x, has):
    if not has: return "0 ingen regnskap"
    if x == 0: return "1 =0"
    if x < 5e5: return "2 <0,5 MNOK"
    if x < 1e6: return "3 0,5-1 MNOK"
    if x < 5e6: return "4 1-5 MNOK"
    if x < 2e7: return "5 5-20 MNOK"
    return "6 >=20 MNOK"
df["size4"] = [band4(x, h) for x, h in zip(df.ta_nok, df.has_acc)]
df["size7"] = [band7(x, h) for x, h in zip(df.ta_nok, df.has_acc)]
df["gap"] = np.where(df.has_acc == 1, df.opened.dt.year - df.fiscal_year, np.nan)
df["gapcat"] = np.where(df.has_acc == 0, "1 aar", np.where(df.gap <= 1, "1 aar", "2+ aar"))  # no-accounts effect carried by size7 level, avoids collinearity
df["age"] = (df.opened - df.stiftet).dt.days / 365.25
df["agecat"] = np.where(df.age.isna(), "ukjent", np.where(df.age < 3, "<3 aar", np.where(df.age < 10, "3-10 aar", ">=10 aar")))
df["varsel"] = (df.n_varsel_for > 0).astype(int)
df["logta"] = np.where(df.has_acc == 1, np.log10(df.ta_nok.clip(lower=1e3)), np.nan)
df["grp"] = np.where(df.bygg == 1, "bygg", np.where(df.uklass == 1, "uklass", "ovrig_klass"))
df.to_csv("B3-05-analysedata.tsv", sep="\t", index=False, encoding="utf-8")

out = {}; md = []
def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z*z/n; c = (p + z*z/(2*n)) / d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (100*(c-h), 100*(c+h))
def newcombe(k1, n1, k2, n2, z=1.96):
    l1, u1 = [v/100 for v in wilson(k1, n1, z)]; l2, u2 = [v/100 for v in wilson(k2, n2, z)]
    p1, p2 = k1/n1, k2/n2; d = p1 - p2
    lo = d - math.sqrt((p1-l1)**2 + (u2-p2)**2); hi = d + math.sqrt((u1-p1)**2 + (p2-l2)**2)
    return (100*lo, 100*hi)
def pct(k, n): return f"{100*k/n:.1f}" if n else "-"
def share_row(name, mask_b, mask_o, y):
    kb, nb = int(y[mask_b].sum()), int(mask_b.sum()); ko, no = int(y[mask_o].sum()), int(mask_o.sum())
    if not (nb and no): return f"| {name} | {kb}/{nb} | {ko}/{no} | - |"
    lb = wilson(kb, nb); lo = wilson(ko, no); rd = newcombe(kb, nb, ko, no)
    return f"| {name} | {kb}/{nb} = {pct(kb,nb)} % [{lb[0]:.1f}-{lb[1]:.1f}] | {ko}/{no} = {pct(ko,no)} % [{lo[0]:.1f}-{lo[1]:.1f}] | {100*kb/nb-100*ko/no:+.1f} pp [{rd[0]:+.1f}; {rd[1]:+.1f}] |"

# ---------------- 0. sanity + headline
md.append("# B3 - resultater (generert av B3-05-analyse.py, as-of 24.08.2026)\n")
md.append(f"Kohort {len(df)}: innstilt {df.y_asof.sum()}, avsluttet {(df.utfall=='avsluttet').sum()}, aapne {df.open_asof.sum()}. Bygg utfoerende {df.bygg.sum()} (innstilt {df[df.bygg==1].y_asof.sum()}), omraade F {df.byggF.sum()}, uklassifisert {df.uklass.sum()}. Full 730-d delkohort: {df.full730.sum()} (bygg {df[(df.full730==1)&(df.bygg==1)].shape[0]}), innstilt innen 730 d {df[df.full730==1].y730.sum()}.\n")
B = df.bygg == 1; O = df.bygg == 0; F7 = df.full730 == 1
md.append("## 1. Hovedkontraster (bygg utfoerende vs oevrige inkl. uklassifiserbar)\n")
md.append("| Maal | Bygg | Oevrige | Differanse [95 % Newcombe] |\n|---|---|---|---|")
md.append(share_row("Innstilt as-of 24.08.2026", B, O, df.y_asof))
md.append(share_row("Innstilt innen 730 d (delkohort aapnet <= 24.08.2024)", B & F7, O & F7, df.y730))
md.append(share_row("Fortsatt aapen as-of", B, O, df.open_asof))
md.append(share_row("Verken innstilt eller avsluttet innen 730 d (delkohort)", B & F7, O & F7, df.open730))
Oe = (df.bygg == 0) & (df.uklass == 0)
md.append(share_row("Innstilt as-of, oevrige EKSKL. uklassifiserbar (155)", B, Oe, df.y_asof))
md.append(share_row("Innstilt innen 730 d, oevrige EKSKL. uklassifiserbar", B & F7, Oe & F7, df.y730))

# ---------------- AJ CIF
def aj_cif(t, cause, horizon=730):
    order = np.argsort(t, kind="stable"); t = t[order]; cause = cause[order]
    S = 1.0; cif = 0.0
    uniq = np.unique(t[cause > 0]); uniq = uniq[uniq <= horizon]
    for u in uniq:
        at_risk = np.sum(t >= u); d1 = np.sum((t == u) & (cause == 1)); d2 = np.sum((t == u) & (cause == 2))
        cif += S * d1 / at_risk; S *= (1 - (d1 + d2) / at_risk)
    return cif
def aj_inputs(d):
    t = np.where(d.t_inn.notna(), d.t_inn, np.where(d.t_avs.notna(), d.t_avs, d.fu)).astype(float)
    cause = np.where(d.t_inn.notna(), 1, np.where(d.t_avs.notna(), 2, 0))
    return t, cause
def aj_boot(d, Bn=400):
    t, c = aj_inputs(d); n = len(t); est = aj_cif(t, c)
    bs = []
    for _ in range(Bn):
        i = rng.integers(0, n, n); bs.append(aj_cif(t[i], c[i]))
    bs = np.array(bs)
    return (est, np.percentile(bs, 2.5), np.percentile(bs, 97.5))
cif_b = aj_boot(df[B]); cif_o = aj_boot(df[O]); cif_oe = aj_boot(df[Oe]); cif_all = aj_boot(df)
md.append(f"\nAalen-Johansen CIF(par. 135) ved 730 d [bootstrap 95 %, 400 rep]: alle {100*cif_all[0]:.2f} [{100*cif_all[1]:.1f}-{100*cif_all[2]:.1f}]; bygg {100*cif_b[0]:.2f} [{100*cif_b[1]:.1f}-{100*cif_b[2]:.1f}]; oevrige {100*cif_o[0]:.2f} [{100*cif_o[1]:.1f}-{100*cif_o[2]:.1f}]; oevrige ekskl. uklass {100*cif_oe[0]:.2f} [{100*cif_oe[1]:.1f}-{100*cif_oe[2]:.1f}]. (Studien: 74,82 / 70,54 / 76,23.)\n")
out["headline"] = {"cif730_all": cif_all, "cif730_bygg": cif_b, "cif730_ovrig": cif_o, "cif730_ovrig_ekskl_uklass": cif_oe}

# ---------------- 2. Descriptives (Table 1)
md.append("## 2. Siste regnskap foer aapningsaaret - bygg vs oevrige (hele kroner; blank amount_unit = hele kroner, 313/313 par identiske)\n")
def q(s):
    s = s.dropna()
    return (s.median(), s.quantile(.25), s.quantile(.75), len(s)) if len(s) else (np.nan, np.nan, np.nan, 0)
def fmt_money(v): return "-" if pd.isna(v) else (f"{v/1e6:.2f} MNOK" if abs(v) >= 1e5 else f"{v:,.0f} NOK".replace(",", " "))
def mw(a, b):
    a = a.dropna(); b = b.dropna()
    if len(a) < 5 or len(b) < 5: return np.nan
    return stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
groups = [("Bygg utfoerende", B), ("Oevrige (inkl. uklass.)", O), ("Oevrige ekskl. uklass.", Oe), ("Uklassifiserbar (155)", df.uklass == 1)]
md.append("| Variabel | " + " | ".join(g[0] for g in groups) + " | p (bygg vs oevrige) |\n|---|" + "---|" * (len(groups) + 1))
def line(label, f, test="share"):
    cells = []; vals = []
    for name, m in groups:
        r = f(df[m]); cells.append(r[0]); vals.append(r[1])
    p = np.nan
    if test == "share":
        (kb, nb), (ko, no) = vals[0], vals[1]
        if nb and no and min(kb, nb-kb, ko, no-ko) >= 0:
            p = stats.chi2_contingency([[kb, nb-kb], [ko, no-ko]], correction=True)[1]
    elif test == "mw": p = mw(vals[0], vals[1])
    ps = "-" if pd.isna(p) else f"{p:.2g}"
    md.append(f"| {label} | " + " | ".join(cells) + f" | {ps} |")
    out.setdefault("table1", {})[label] = {g[0]: c for g, c in zip(groups, cells)}
def sh(mask_col):
    def f(d):
        k = int(d[mask_col].sum()); n = int(d[mask_col].notna().sum()); w = wilson(k, n)
        return (f"{k}/{n} = {pct(k,n)} % [{w[0]:.1f}-{w[1]:.1f}]", (k, n))
    return f
def med(col, money=True):
    def f(d):
        m, lo, hi, n = q(d[col])
        s = f"{fmt_money(m)} (IQR {fmt_money(lo)}-{fmt_money(hi)}; n={n})" if money else f"{m:.3f} (IQR {lo:.3f}-{hi:.3f}; n={n})"
        return (s, d[col])
    return f
def cnt(pred, denom):
    def f(d):
        k = int(pred(d).sum()); n = int(denom(d)); return (f"{k}/{n} = {pct(k,n)} %", (k, n))
    return f
line("N", lambda d: (str(len(d)), (len(d), len(d))), test=None)
line("Har regnskap foer aapningsaaret", sh("has_acc"))
line("Regnskap: sum eiendeler = 0", sh("ta_zero"))
line("Sum eiendeler, median (IQR)", med("ta_nok"), "mw")
line("Sum eiendeler >= 5 MNOK (andel av alle)", cnt(lambda d: d.size4 == "3 >=5 MNOK", len))
line("Sum eiendeler >= 1 MNOK (andel av alle)", cnt(lambda d: d.size4.isin(["2 1-5 MNOK", "3 >=5 MNOK"]), len))
line("Omloepsmidler, median", med("ca_nok"), "mw")
line("Anleggsmidler (sum eiendeler - omloepsmidler), median", med("fa_nok"), "mw")
line("Omloepsmiddelandel (OM/sum eiendeler), median", med("ca_share", False), "mw")
line("Anleggsmiddelandel > 25 % (blant sum eiendeler > 0)", cnt(lambda d: d.fa_share > .25, lambda d: int(d.fa_share.notna().sum())))
line("Egenkapitalandel (EK/sum eiendeler), median", med("eq_ratio", False), "mw")
line("Negativ egenkapital", sh("neg_eq"))
line("Driftsinntekter, median", med("rev_nok"), "mw")
line("Driftsinntekter >= 5 MNOK (andel av alle)", cnt(lambda d: d.rev_nok >= 5e6, len))
line("Sum gjeld, median", med("liab_nok"), "mw")
line("Regnskapsaar = aapningsaar - 1 (blant dem med regnskap)", cnt(lambda d: d.gap == 1, lambda d: int(d.has_acc.sum())))
line("Oppbud (felt Aapnet etter)", sh("oppbud"))
line("Alder ved aapning, median aar", med("age", False), "mw")
line("Alder < 3 aar (blant kjente)", cnt(lambda d: d.age < 3, lambda d: int(d.age.notna().sum())))
line("Varsel om tvangsopploesning foer aapning", sh("varsel"))
line("Aksjekapital (siste), median", med("kapital_siste"), "mw")
line("Loennskostnad / ansatte tilgjengelig", lambda d: ("0 av %d (NULL paa alle rader)" % len(d), (0, len(d))), test=None)

# ---------------- 3. Stratified shares
md.append("\n## 3. Stratifiserte andeler - holder byggfordelen innenfor strata?\n")
def strat_table(var, title, order=None):
    md.append(f"\n### {title} (`{var}`)\n")
    md.append("| Stratum | Bygg: innstilt as-of | Oevrige: innstilt as-of | Diff as-of | Bygg: innen 730 d | Oevrige: innen 730 d | Diff 730 d [Newcombe] | Bygg CIF730 | Oevrige CIF730 |\n|---|---|---|---|---|---|---|---|---|")
    levels = order or sorted(df[var].dropna().unique())
    res = []
    for lv in levels:
        m = df[var] == lv
        kb, nb = int(df[m & B].y_asof.sum()), int((m & B).sum()); ko, no = int(df[m & O].y_asof.sum()), int((m & O).sum())
        kb7, nb7 = int(df[m & B & F7].y730.sum()), int((m & B & F7).sum()); ko7, no7 = int(df[m & O & F7].y730.sum()), int((m & O & F7).sum())
        cb = aj_cif(*aj_inputs(df[m & B])) if nb >= 10 else np.nan; co = aj_cif(*aj_inputs(df[m & O])) if no >= 10 else np.nan
        d7 = newcombe(kb7, nb7, ko7, no7) if (nb7 and no7) else (np.nan, np.nan)
        da = (100*kb/nb-100*ko/no) if (nb and no) else np.nan
        d7p = (100*kb7/nb7-100*ko7/no7) if (nb7 and no7) else np.nan
        md.append(f"| {lv} | {kb}/{nb} = {pct(kb,nb)} % | {ko}/{no} = {pct(ko,no)} % | {da:+.1f} pp | {kb7}/{nb7} = {pct(kb7,nb7)} % | {ko7}/{no7} = {pct(ko7,no7)} % | {d7p:+.1f} pp [{d7[0]:+.1f}; {d7[1]:+.1f}] | {100*cb:.1f} % | {100*co:.1f} % |")
        res.append(dict(stratum=str(lv), kb=kb, nb=nb, ko=ko, no=no, kb7=kb7, nb7=nb7, ko7=ko7, no7=no7, cif_b=cb, cif_o=co))
    num_, den_ = 0, 0; stdz_num, stdz_den = 0, 0; crude_b = df[B & F7].y730.mean(); crude_o = df[O & F7].y730.mean()
    for r in res:
        n = r["nb7"] + r["no7"]
        if n == 0 or r["nb7"] == 0 or r["no7"] == 0: continue
        a, b_, c, d_ = r["kb7"], r["nb7"] - r["kb7"], r["ko7"], r["no7"] - r["ko7"]
        num_ += a * d_ / n; den_ += b_ * c / n
        stdz_num += (r["kb7"] / r["nb7"]) * r["no7"]; stdz_den += r["no7"]
    mh = num_ / den_ if den_ else np.nan
    stdz = stdz_num / stdz_den
    md.append(f"\nRaa differanse (730 d): {100*(crude_b-crude_o):+.1f} pp. Bygg standardisert til oevriges {var}-fordeling: {100*stdz:.1f} % mot oevrige {100*crude_o:.1f} % -> standardisert differanse {100*(stdz-crude_o):+.1f} pp. Mantel-Haenszel OR (bygg, 730 d) paa tvers av strata: {mh:.3f}.\n")
    out.setdefault("strata", {})[var] = {"rows": res, "mh_or_730": mh, "stdz_bygg_730": stdz, "crude_b": crude_b, "crude_o": crude_o}
strat_table("size4", "(i) Balansestoerrelse, siste regnskap foer aapningsaaret (4 baand)")
strat_table("size7", "(i b) Balansestoerrelse, finere baand")
strat_table("oppbud", "(ii) Aapningsgrunnlag: 1 = oppbud, 0 = ikke oppbud (begjaering)", order=[1, 0])
strat_table("has_acc", "(iii) Regnskap levert foer aapningsaaret: 1 = ja, 0 = nei", order=[1, 0])
strat_table("gapcat", "(iii b) Avstand fra siste regnskapsaar til aapningsaar")
strat_table("agecat", "Alder ved aapning", order=["<3 aar", "3-10 aar", ">=10 aar", "ukjent"])
strat_table("tingrett", "Rettskrets (domstolsmiks)")
md.append("\n### (ii x i) Oppbud x balansestoerrelse\n")
md.append("| Oppbud | Stoerrelse | Bygg innen 730 d | Oevrige innen 730 d | Diff [Newcombe] |\n|---|---|---|---|---|")
for ob in [1, 0]:
    for lv in sorted(df.size4.unique()):
        m = (df.oppbud == ob) & (df.size4 == lv) & F7
        kb, nb = int(df[m & B].y730.sum()), int((m & B).sum()); ko, no = int(df[m & O].y730.sum()), int((m & O).sum())
        d7 = newcombe(kb, nb, ko, no) if (nb and no) else (np.nan, np.nan)
        dd_ = (100*kb/nb-100*ko/no) if (nb and no) else np.nan
        md.append(f"| {ob} | {lv} | {kb}/{nb} = {pct(kb,nb)} % | {ko}/{no} = {pct(ko,no)} % | {dd_:+.1f} pp [{d7[0]:+.1f}; {d7[1]:+.1f}] |")

# ---------------- 4. Logistic regression (IRLS)
REF = {"size4": "1 <1 MNOK", "size7": "2 <0,5 MNOK", "gapcat": "1 aar", "agecat": "3-10 aar", "tingrett": "OSLO TINGRETT"}
def design(d, terms, inter=()):
    cols = {"const": np.ones(len(d))}
    for t in terms:
        if t in ("bygg", "oppbud", "has_acc", "varsel"): cols[t] = d[t].values.astype(float)
        elif t == "logta":
            cols["logta"] = np.where(d.has_acc == 1, d.logta.fillna(0), 0); cols["logta_sq"] = cols["logta"] ** 2
        else:
            ref = REF[t]
            for lv in sorted(d[t].unique()):
                if lv == ref: continue
                cols[f"{t}={lv}"] = (d[t] == lv).values.astype(float)
    for a, b_ in inter:
        for k in list(cols):
            if k.startswith(b_ + "=") or k == b_:
                cols[f"byggX{k}"] = cols["bygg"] * cols[k]
    X = np.column_stack(list(cols.values())); return X, list(cols)
def irls(X, y, ridge=1e-8, maxit=100):
    beta = np.zeros(X.shape[1])
    for _ in range(maxit):
        eta = X @ beta; p = 1 / (1 + np.exp(-eta)); W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + ridge * np.eye(X.shape[1]); g = X.T @ (y - p)
        step = np.linalg.solve(H, g); beta = beta + step
        if np.max(np.abs(step)) < 1e-9: break
    p = 1 / (1 + np.exp(-(X @ beta))); W = p * (1 - p)
    H = X.T @ (X * W[:, None]) + ridge * np.eye(X.shape[1]); cov = np.linalg.inv(H)
    ll = np.sum(y * np.log(p + 1e-300) + (1 - y) * np.log(1 - p + 1e-300))
    return beta, cov, ll
def marginal_rd(X, names, beta):
    i = names.index("bygg"); X1 = X.copy(); X0 = X.copy(); X1[:, i] = 1; X0[:, i] = 0
    for j, nm in enumerate(names):
        if nm.startswith("byggX"):
            base = nm[5:]; k = names.index(base); X1[:, j] = X1[:, k]; X0[:, j] = 0
    p1 = 1 / (1 + np.exp(-(X1 @ beta))); p0 = 1 / (1 + np.exp(-(X0 @ beta)))
    return p1.mean() - p0.mean()
def fit_report(d, y, terms, inter=(), label="", boot=300):
    X, names = design(d, terms, inter); yy = d[y].values.astype(float)
    beta, cov, ll = irls(X, yy)
    i = names.index("bygg"); se = math.sqrt(cov[i, i]); orr = math.exp(beta[i]); lo, hi = math.exp(beta[i] - 1.96 * se), math.exp(beta[i] + 1.96 * se)
    rd = marginal_rd(X, names, beta)
    bs = []; n = len(d)
    for _ in range(boot):
        idx = rng.integers(0, n, n)
        try:
            b_, _, _ = irls(X[idx], yy[idx]); bs.append(marginal_rd(X[idx], names, b_))
        except np.linalg.LinAlgError: pass
    bs = np.array(bs); rdlo, rdhi = (np.percentile(bs, 2.5), np.percentile(bs, 97.5)) if len(bs) else (np.nan, np.nan)
    coefs = {nm: (float(beta[j]), float(math.sqrt(cov[j, j]))) for j, nm in enumerate(names)}
    return dict(label=label, n=int(n), k=len(names), or_bygg=orr, ci=(lo, hi), p=2 * (1 - stats.norm.cdf(abs(beta[i] / se))), rd=rd, rd_ci=(rdlo, rdhi), ll=ll, coefs=coefs, names=names)
md.append("\n## 4. Logistisk regresjon - utfall = innstilt innen 730 d (delkohort med full oppfoelging, n = %d)\n" % int(F7.sum()))
md.append("Marginal risikodifferanse = gjennomsnittlig predikert sannsynlighet med bygg = 1 minus bygg = 0 for alle (standardisering), bootstrap-KI (300 rep).\n")
md.append("| Modell | n | par. | OR bygg [95 %] | p | Marginal RD bygg [95 %] |\n|---|---|---|---|---|---|")
d7 = df[F7].copy()
models = [
    ("M0 bygg alene", ["bygg"], ()),
    ("M1 + balansestoerrelse (7 baand)", ["bygg", "size7"], ()),
    ("M1b + log10(sum eiendeler) + kvadrat + ingen-regnskap", ["bygg", "has_acc", "logta"], ()),
    ("M2 + oppbud", ["bygg", "oppbud"], ()),
    ("M3 + regnskap levert (ja/nei)", ["bygg", "has_acc"], ()),
    ("M4 stoerrelse + oppbud + regnskapsavstand + alder", ["bygg", "size7", "oppbud", "gapcat", "agecat"], ()),
    ("M5 = M4 + rettskrets (23 faste effekter)", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett"], ()),
    ("M6 = M5 + varsel foer aapning", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett", "varsel"], ()),
]
fits = {}
for lab, terms, inter in models:
    r = fit_report(d7, "y730", terms, inter, lab); fits[lab] = r
    md.append(f"| {lab} | {r['n']} | {r['k']} | {r['or_bygg']:.3f} [{r['ci'][0]:.3f}; {r['ci'][1]:.3f}] | {r['p']:.2g} | {100*r['rd']:+.1f} pp [{100*r['rd_ci'][0]:+.1f}; {100*r['rd_ci'][1]:+.1f}] |")
md.append("\n### Interaksjoner (LR-test mot samme modell uten interaksjon)\n")
base = fits["M5 = M4 + rettskrets (23 faste effekter)"]
md.append("| Modell | LR chi2 | df | p | OR bygg i referansestratum | Interaksjonsledd (OR-multiplikator, se) |\n|---|---|---|---|---|---|")
for lab, terms, inter in [("M5 + bygg x oppbud", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett"], (("bygg", "oppbud"),)),
                          ("M5 + bygg x stoerrelse(7)", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett"], (("bygg", "size7"),)),
                          ("M5 + bygg x regnskap levert", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett", "has_acc"], (("bygg", "has_acc"),))]:
    r = fit_report(d7, "y730", terms, inter, lab, boot=50); fits[lab] = r
    X0, n0 = design(d7, terms); b0, c0, ll0 = irls(X0, d7.y730.values.astype(float))
    lr = 2 * (r["ll"] - ll0); dfree = r["k"] - len(n0); p = 1 - stats.chi2.cdf(lr, dfree)
    ints = "; ".join(f"{nm[5:]}: x{math.exp(r['coefs'][nm][0]):.2f} (se {r['coefs'][nm][1]:.2f})" for nm in r["names"] if nm.startswith("byggX"))
    md.append(f"| {lab} | {lr:.2f} | {dfree} | {p:.3f} | {r['or_bygg']:.3f} [{r['ci'][0]:.3f}; {r['ci'][1]:.3f}] | {ints} |")
md.append("\n### Sekundaert: utfall = innstilt as-of 24.08.2026, alle 5 165\n")
md.append("| Modell | n | OR bygg [95 %] | p | Marginal RD [95 %] |\n|---|---|---|---|---|")
for lab, terms, inter in [("M0 bygg alene", ["bygg"], ()), ("M5 full (stoerrelse, oppbud, avstand, alder, rettskrets)", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett"], ())]:
    r = fit_report(df, "y_asof", terms, inter, lab, boot=200)
    md.append(f"| {lab} | {r['n']} | {r['or_bygg']:.3f} [{r['ci'][0]:.3f}; {r['ci'][1]:.3f}] | {r['p']:.2g} | {100*r['rd']:+.1f} pp [{100*r['rd_ci'][0]:+.1f}; {100*r['rd_ci'][1]:+.1f}] |")
md.append("\n### Kovariateffekter i M5 (OR, 730 d)\n")
md.append("| Ledd | OR | 95 % |\n|---|---|---|")
for nm, (b_, se) in base["coefs"].items():
    if nm.startswith("tingrett=") or nm == "const": continue
    ex = lambda v: math.exp(min(v, 50))
    md.append(f"| {nm} | {ex(b_):.2f} | [{ex(b_-1.96*se):.2f}; {ex(b_+1.96*se):.2f}] |")
out["models"] = {k: {kk: vv for kk, vv in v.items() if kk not in ("coefs", "names")} for k, v in fits.items()}
r0 = fits["M0 bygg alene"]["rd"]; r1 = fits["M1 + balansestoerrelse (7 baand)"]["rd"]; r2 = fits["M2 + oppbud"]["rd"]; r4 = fits["M4 stoerrelse + oppbud + regnskapsavstand + alder"]["rd"]; r5 = base["rd"]
md.append(f"\nAndel av raa-differansen ({100*r0:+.1f} pp) som 'forklares' (attenuering av marginal RD): stoerrelse alene {100*(1-r1/r0):.0f} %; oppbud alene {100*(1-r2/r0):.0f} %; stoerrelse+oppbud+avstand+alder {100*(1-r4/r0):.0f} %; + rettskrets {100*(1-r5/r0):.0f} %. Negativ attenuering = differansen blir STOERRE etter justering.\n")

# ---------------- 5. Alternative explanations
md.append("\n## 5. Alternative forklaringer\n")
md.append("### (a) Umodenhet\n")
md.append("| Maal | Bygg | Oevrige | Diff [Newcombe] |\n|---|---|---|---|")
md.append(share_row("Fortsatt aapen as-of (alle)", B, O, df.open_asof))
md.append(share_row("Verken innstilt eller avsluttet innen 730 d (delkohort)", B & F7, O & F7, df.open730))
L = 365
openL = (~((df.t_inn.notna()) & (df.t_inn <= L))) & (~((df.t_avs.notna()) & (df.t_avs <= L)))
md.append(share_row("Landemerke: aapne ved dag 365 -> innstilt innen 24.08.2026", B & openL, O & openL, df.y_asof))
md.append(share_row("Landemerke: aapne ved dag 365 -> ordinaert avsluttet innen 24.08.2026", B & openL, O & openL, (df.utfall == "avsluttet").astype(int)))
L2 = 730; openL2 = (~((df.t_inn.notna()) & (df.t_inn <= L2))) & (~((df.t_avs.notna()) & (df.t_avs <= L2))) & F7
md.append(share_row("Landemerke: aapne ved dag 730 (delkohort) -> innstilt innen 24.08.2026", B & openL2, O & openL2, df.y_asof))
kb, nb = int(df[B].y_asof.sum() + df[B].open_asof.sum()), int(B.sum()); ko, no = int(df[O].y_asof.sum()), int(O.sum())
md.append(f"| Verste tilfelle: alle aapne byggbo innstilles, ingen aapne oevrige | {kb}/{nb} = {pct(kb,nb)} % | {ko}/{no} = {pct(ko,no)} % | {100*kb/nb-100*ko/no:+.1f} pp |")
md.append("\n### (b) Domstolsmiks\n")
ct = df.groupby("tingrett").agg(n=("orgnr", "size"), bygg=("bygg", "sum"), inn=("y_asof", "sum")).sort_values("n", ascending=False)
ct["bygg_pst"] = 100 * ct.bygg / ct.n; ct["inn_pst"] = 100 * ct.inn / ct.n
md.append("| Rettskrets | n | byggandel % | innstilt as-of % |\n|---|---|---|---|")
for k_, r in ct.iterrows(): md.append(f"| {k_} | {int(r.n)} | {r.bygg_pst:.1f} | {r.inn_pst:.1f} |")
md.append(f"\nKorrelasjon over 23 kretser mellom byggandel og innstiltandel: Pearson r = {np.corrcoef(ct.bygg_pst, ct.inn_pst)[0,1]:.2f}; Spearman {stats.spearmanr(ct.bygg_pst, ct.inn_pst).correlation:.2f}.\n")
md.append("\n### (c) Den uklassifiserbare bunken (155)\n")
u = df[df.uklass == 1]
md.append(f"155 bo: 118 Uoppgitt, 2 Enheten er slettet, 35 med etikett uten treff i kaskaden. Innstilt as-of {int(u.y_asof.sum())}/155 = {pct(int(u.y_asof.sum()),155)} %. Regnskap foer aapningsaaret: {int(u.has_acc.sum())}/155 = {pct(int(u.has_acc.sum()),155)} % (bygg {pct(int(df[B].has_acc.sum()),int(B.sum()))} %, oevrige klass. {pct(int(df[Oe].has_acc.sum()),int(Oe.sum()))} %). Median sum eiendeler blant dem med regnskap: {fmt_money(u.ta_nok.median())}. Oppbud: {int(u.oppbud.sum())}/155 = {pct(int(u.oppbud.sum()),155)} %. Sum eiendeler = 0 eller ingen regnskap: {int(((u.has_acc==0)|(u.ta_nok==0)).sum())}/155.")
uo = u[u.bransje == "Uoppgitt"]
md.append(f"Bare Uoppgitt (118): innstilt {int(uo.y_asof.sum())}/118; regnskap foer aapningsaaret {int(uo.has_acc.sum())}/118; median sum eiendeler {fmt_money(uo.ta_nok.median())}; oppbud {int(uo.oppbud.sum())}/118; alder < 3 aar {int((uo.age<3).sum())}/{int(uo.age.notna().sum())}.\n")

# ---------------- 6. Bygg F sensitivity
md.append("\n## 6. Foelsomhet: omraade F (41-43) i stedet for utfoerende\n")
BF = df.byggF == 1; OF = df.byggF == 0
md.append("| Maal | Bygg F | Oevrige | Diff |\n|---|---|---|---|")
md.append(share_row("Innstilt as-of", BF, OF, df.y_asof)); md.append(share_row("Innstilt innen 730 d", BF & F7, OF & F7, df.y730))
rF = fit_report(d7.assign(bygg=d7.byggF), "y730", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett"], (), "F full", boot=100)
md.append(f"\nM5 med omraade F som byggmerke: OR {rF['or_bygg']:.3f} [{rF['ci'][0]:.3f}; {rF['ci'][1]:.3f}], marginal RD {100*rF['rd']:+.1f} pp [{100*rF['rd_ci'][0]:+.1f}; {100*rF['rd_ci'][1]:+.1f}].\n")
md.append("\n## 7. Fordeling paa stoerrelsesbaand (andel av gruppen)\n")
md.append("| Baand | Bygg | Oevrige |\n|---|---|---|")
for lv in sorted(df.size7.unique()):
    md.append(f"| {lv} | {int((df.size7[B]==lv).sum())} = {pct(int((df.size7[B]==lv).sum()), int(B.sum()))} % | {int((df.size7[O]==lv).sum())} = {pct(int((df.size7[O]==lv).sum()), int(O.sum()))} % |")
md.append("\n| Oppbud | Bygg | Oevrige |\n|---|---|---|")
for ob in [1, 0]:
    md.append(f"| {ob} | {int((df.oppbud[B]==ob).sum())} = {pct(int((df.oppbud[B]==ob).sum()), int(B.sum()))} % | {int((df.oppbud[O]==ob).sum())} = {pct(int((df.oppbud[O]==ob).sum()), int(O.sum()))} % |")
md.append("\n## 8. Innstilt-andel etter stoerrelse, hele kohorten (as-of / 730 d)\n")
md.append("| Baand | n | innstilt as-of | n730 | innen 730 d |\n|---|---|---|---|---|")
for lv in sorted(df.size7.unique()):
    m = df.size7 == lv
    md.append(f"| {lv} | {int(m.sum())} | {pct(int(df[m].y_asof.sum()), int(m.sum()))} % | {int((m&F7).sum())} | {pct(int(df[m&F7].y730.sum()), int((m&F7).sum()))} % |")
md.append("\n## 9. Sammensetning (omloepsmiddelandel, EK-andel) mot utfall innen 730 d, blant bo med regnskap og sum eiendeler > 0\n")
md.append("| Gruppe | Omloepsmiddelandel-tertil | n730 | innen 730 d |\n|---|---|---|---|")
dd = d7[(d7.has_acc == 1) & (d7.ta_nok > 0)].copy()
dd["ca_t"] = pd.qcut(dd.ca_share, 3, labels=["lav", "middels", "hoey"])
for g, m in [("bygg", dd.bygg == 1), ("oevrige", dd.bygg == 0)]:
    for t in ["lav", "middels", "hoey"]:
        mm = m & (dd.ca_t == t)
        md.append(f"| {g} | {t} ({dd[dd.ca_t==t].ca_share.min():.2f}-{dd[dd.ca_t==t].ca_share.max():.2f}) | {int(mm.sum())} | {pct(int(dd[mm].y730.sum()), int(mm.sum()))} % |")
md.append("\n| Gruppe | EK-andel | n730 | innen 730 d |\n|---|---|---|---|")
dd["eq_c"] = np.where(dd.eq_ratio < 0, "negativ", np.where(dd.eq_ratio < 0.2, "0-20 %", ">=20 %"))
for g, m in [("bygg", dd.bygg == 1), ("oevrige", dd.bygg == 0)]:
    for t in ["negativ", "0-20 %", ">=20 %"]:
        mm = m & (dd.eq_c == t)
        md.append(f"| {g} | {t} | {int(mm.sum())} | {pct(int(dd[mm].y730.sum()), int(mm.sum()))} % |")
rC = fit_report(dd, "y730", ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett"], (), "comp base", boot=100)
Xc, nc = design(dd, ["bygg", "size7", "oppbud", "gapcat", "agecat", "tingrett"])
Xc2 = np.column_stack([Xc, dd.ca_share.values, np.clip(dd.eq_ratio.values, -5, 5)]); nc2 = nc + ["ca_share", "eq_ratio_clip"]
b2, c2, ll2 = irls(Xc2, dd.y730.values.astype(float)); i = nc2.index("bygg"); j1 = nc2.index("ca_share"); j2 = nc2.index("eq_ratio_clip")
md.append(f"\nBlant bo med regnskap og sum eiendeler > 0 (n = {len(dd)}): OR bygg i M5-spesifikasjonen {rC['or_bygg']:.3f} [{rC['ci'][0]:.3f}; {rC['ci'][1]:.3f}]; med omloepsmiddelandel og EK-andel lagt til: OR bygg {math.exp(b2[i]):.3f} [{math.exp(b2[i]-1.96*math.sqrt(c2[i,i])):.3f}; {math.exp(b2[i]+1.96*math.sqrt(c2[i,i])):.3f}]; OR per +1,0 i omloepsmiddelandel {math.exp(b2[j1]):.2f} (se {math.sqrt(c2[j1,j1]):.2f}); OR per +1,0 i EK-andel (klippet til [-5,5]) {math.exp(b2[j2]):.2f} (se {math.sqrt(c2[j2,j2]):.2f}).\n")

open("B3-05-results.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
def conv(o):
    if isinstance(o, dict): return {str(k): conv(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [conv(v) for v in o]
    if isinstance(o, (np.floating, float)): return None if (isinstance(o, float) and math.isnan(o)) else float(o)
    if isinstance(o, (np.integer,)): return int(o)
    return o
json.dump(conv(out), open("B3-05-results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n".join(md))
