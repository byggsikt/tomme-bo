# -*- coding: utf-8 -*-
"""
D2 — sjekklisten (tre flagg) kjørt på nytt med «revisor registrert ved åpningen».
Lane D2 (checklist re-runner), 12.09.2026.

Leser (kun lesing):
  data/V-B2-03-extract.csv                  V-B2s uavhengige uttrekk, én rad per bo (5 165) — bekreftet mot B2 i V-B2-VERIFIKASJON.md
  data/B2-per-estate.csv                    B2s per-bo-tabell (bare til (a) kryssjekk av avledede variabler og (b) modell A med B2s fulle spesifikasjon)
  workflow-final/D2-01-revisor-ved-apning.csv   egen SQL-dump av alle «Revisor»-felt t.o.m. åpningsdagen (klasse, ikke navn)
Skriver (kun her):
  workflow-final/D2-resultater.md, workflow-final/D2-resultater.json

Alle tall: enhet = boet. «730 d» = fullvindu-delkohorten åpnet ≤ 24.08.2024 (n = 3 772), fast horisont, ingen sensurering.
«as-of» = observert per 24.08.2026, alle 5 165. «AJ» = Aalen–Johansen kumulativ insidens ved 730 d med ordinær avslutning som konkurrerende hendelse.
"""
import sys, math, json, io
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import numpy as np, pandas as pd
from scipy import stats

ROOT = "./"
OUT = ROOT + "workflow-final/"
ASOF = pd.Timestamp("2026-08-24"); FULLCUT = pd.Timestamp("2024-08-24"); NA = "Ingen regnskap"
out = io.StringIO(); RES = {}
def P(s=""): out.write(s + "\n"); print(s)

# ------------------------------------------------------------------ helpers
def wilson(k, n, z=1.959964):
    if n == 0: return (float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)
def newcombe(k1, n1, k2, n2):
    p1, p2 = k1 / n1, k2 / n2; l1, u1 = wilson(k1, n1); l2, u2 = wilson(k2, n2); d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
def pct(k, n): return f"{k} / {n} = {100 * k / n:.1f} %"
def wci(k, n): lo, hi = wilson(k, n); return f"[{100 * lo:.1f}–{100 * hi:.1f}]"
def band(x, edges, labels, na=NA):
    if pd.isna(x): return na
    for e, l in zip(edges, labels):
        if x < e: return l
    return labels[-1]
def aalen_johansen(sub, horizon=730, asof=ASOF):
    """Kumulativ insidens av innstilling ved `horizon` dager; ordinær avslutning = konkurrerende hendelse; sensur ved min(horizon, as-of − åpning)."""
    t = []; ev = []
    for op, t1, t2 in zip(sub.opened, sub.d_innstilt, sub.d_avsluttet):
        cens = min(horizon, (asof - op).days)
        if pd.notna(t1) and t1 <= cens: t.append(t1); ev.append(1)
        elif pd.notna(t2) and t2 <= cens: t.append(t2); ev.append(2)
        else: t.append(cens); ev.append(0)
    t = np.array(t, float); ev = np.array(ev, int); o = np.argsort(t, kind="stable"); t = t[o]; ev = ev[o]
    at_risk = len(t); S = 1.0; ci1 = 0.0
    for tt in np.unique(t):
        m = t == tt; d1 = int(((ev == 1) & m).sum()); d2 = int(((ev == 2) & m).sum()); d0 = int(((ev == 0) & m).sum())
        if at_risk <= 0: break
        if d1 > 0: ci1 += S * d1 / at_risk
        S *= 1 - (d1 + d2) / at_risk; at_risk -= d1 + d2 + d0
    return ci1

# logistic regression (IRLS), same conventions as B2/V-B2 so ORs are comparable
def design(d, spec):
    X = [np.ones(len(d))]; names = ["(konstant)"]; groups = {}
    for var, kind, ref in spec:
        if kind == "bin":
            X.append(d[var].astype(float).values); names.append(var); groups[var] = [len(names) - 1]
        else:
            lv = sorted([l for l in d[var].unique() if l != ref], key=str); groups[var] = []
            for l in lv:
                X.append((d[var] == l).astype(float).values); names.append(f"{var}={l}"); groups[var].append(len(names) - 1)
    return np.column_stack(X), names, groups
def irls(X, y, max_iter=200, tol=1e-10):
    b = np.zeros(X.shape[1])
    for it in range(max_iter):
        eta = X @ b; p = 1 / (1 + np.exp(-np.clip(eta, -35, 35))); w = np.clip(p * (1 - p), 1e-10, None)
        H = (X.T * w) @ X; g = X.T @ (y - p)
        step = np.linalg.solve(H, g); b = b + step
        if np.max(np.abs(step)) < tol: break
    eta = X @ b; p = 1 / (1 + np.exp(-np.clip(eta, -35, 35))); w = np.clip(p * (1 - p), 1e-10, None)
    cov = np.linalg.inv((X.T * w) @ X)
    ll = float(np.sum(y * np.log(np.clip(p, 1e-12, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-12, 1))))
    return b, cov, ll, p
def auc(y, s):
    y = np.asarray(y).astype(int); r = stats.rankdata(np.asarray(s, float)); n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
def cv_auc(X, y, k=10, seed=1):
    rng = np.random.default_rng(seed); idx = rng.permutation(len(y)); folds = np.array_split(idx, k); pr = np.zeros(len(y))
    for fo in folds:
        tr = np.setdiff1d(idx, fo); b, *_ = irls(X[tr], y[tr]); pr[fo] = X[fo] @ b
    return auc(y, pr)
def fit(title, d, spec, ycol="y730", show=None, cv_seeds=(1, 7, 42)):
    X, names, groups = design(d, spec); y = d[ycol].astype(float).values
    b, cov, ll, p = irls(X, y); se = np.sqrt(np.diag(cov)); z = b / se; pv = 2 * stats.norm.sf(np.abs(z))
    ll0 = irls(np.ones((len(y), 1)), y)[2]
    cvs = {s: cv_auc(X, y, seed=s) for s in cv_seeds}; cv20 = float(np.mean([cv_auc(X, y, seed=s) for s in range(1, 21)]))
    a = auc(y, p)
    P(f"**{title}** — n = {len(d)}, hendelser = {int(y.sum())}, log-likelihood {ll:.1f} (konstant {ll0:.1f}), AUC in-sample = {a:.3f}, "
      f"10-fold CV AUC = {cvs[1]:.3f} (seed 1) / {cvs[7]:.3f} (seed 7) / {cvs[42]:.3f} (seed 42); snitt over 20 seeds {cv20:.3f}."); P()
    P("| Variabel (nivå mot referanse) | OR | 95 % KI | p (Wald) | n i nivå |"); P("|---|---:|---|---:|---:|")
    rows = {}
    for var, kind, ref in spec:
        if show and var not in show: continue
        for i in groups[var]:
            lvl = names[i].split("=", 1)[1] if "=" in names[i] else "ja (mot nei)"
            nlv = int(d[var].sum()) if kind == "bin" else int((d[var].astype(str) == lvl).sum())
            P(f"| {var}: {lvl}" + (f" (ref. {ref})" if kind != "bin" and i == groups[var][0] else "") + f" | {math.exp(b[i]):.3f} | {math.exp(b[i] - 1.96 * se[i]):.3f}–{math.exp(b[i] + 1.96 * se[i]):.3f} | {pv[i]:.3g} | {nlv} |")
            rows[names[i]] = dict(or_=math.exp(b[i]), lo=math.exp(b[i] - 1.96 * se[i]), hi=math.exp(b[i] + 1.96 * se[i]), p=float(pv[i]), n=nlv)
    P()
    return dict(names=names, beta=b, cov=cov, auc=a, cv=cvs, cv20=cv20, ll=ll, rows=rows)

# ------------------------------------------------------------------ 1. load the verified extract and rebuild every derived variable ourselves
df = pd.read_csv(ROOT + "data/V-B2-03-extract.csv", dtype={"orgnr": str, "tingrett": str, "bransje": str})
for c in ["opened", "innstilt", "avsluttet", "gk_siste", "rev_siste", "stiftet", "nyreg", "forste_any", "fristdag", "vt_siste"]:
    df[c] = pd.to_datetime(df[c], errors="coerce")
for c in ["oppbud", "rev_siste_fratradt", "vt_24m", "vt_12m", "vt_regn", "vt_foretak", "dl_utgaar_12m", "rev_utgaar_12m"]:
    df[c] = df[c].map({"t": True, "f": False, True: True, False: False})
assert len(df) == 5165 and df.orgnr.nunique() == 5165
df["y_asof"] = df.utfall == "innstilt"; df["avsl_asof"] = df.utfall == "avsluttet"; df["open_asof"] = df.utfall == "aapen"
df["full"] = df.opened <= FULLCUT
df["y730"] = df.d_innstilt.notna() & (df.d_innstilt <= 730)
df["avsl730"] = (~df.y730) & df.d_avsluttet.notna() & (df.d_avsluttet <= 730)
df["open730"] = (~df.y730) & (~df.avsl730)
df["ta3"] = df.total_assets.map(lambda x: band(x, [1e6, 5e6, np.inf], ["<1 mill.", "1–<5 mill.", "≥5 mill."]))
df["ta7"] = df.total_assets.map(lambda x: band(x, [1e5, 5e5, 1e6, 5e6, 2e7, np.inf], ["<100 000", "100 000–<500 000", "500 000–<1 mill.", "1–<5 mill.", "5–<20 mill.", "≥20 mill."]))
df["stift_eff"] = df.stiftet.fillna(df.nyreg)
def levert(r):  # B2/V-B2s regel: regnskapsår Y forfaller 31.7. Y+1; 2 mnd slingring → åpning ≥ 1.10. krever godkjenning kunngjort i år Y, ellers i år Y−1
    Y = r.opened.year if r.opened.month >= 10 else r.opened.year - 1
    st = r.stift_eff
    if pd.notna(st) and st >= pd.Timestamp(Y - 1, 7, 1): return "For ungt"
    return "Levert" if (pd.notna(r.gk_siste) and r.gk_siste >= pd.Timestamp(Y, 1, 1)) else "Ikke levert"
df["levert"] = df.apply(levert, axis=1)

# ------------------------------------------------------------------ 2. auditor registered at the opening — from our own row-level dump
rv = pd.read_csv(OUT + "D2-01-revisor-ved-apning.csv", dtype={"orgnr": str})
rv["dato"] = pd.to_datetime(rv.dato); rv["opened"] = pd.to_datetime(rv.opened)
def derive_state(rows, strict):
    s = rows[rows.dato < rows.opened] if strict else rows[rows.dato <= rows.opened]
    mx = s.groupby("orgnr").dato.transform("max"); last = s[s.dato == mx]
    return last.groupby("orgnr").klasse.agg(lambda x: "tvetydig" if x.nunique() > 1 else x.iloc[0])
st_lt = derive_state(rv, True); st_le = derive_state(rv, False)
df["rev_state"] = df.orgnr.map(st_lt).fillna("ingen"); df["rev_state_le"] = df.orgnr.map(st_le).fillna("ingen")
df["rev_siste_dato"] = df.orgnr.map(rv[rv.dato < rv.opened].groupby("orgnr").dato.max())
df["rev_open"] = df.rev_state == "navngitt"          # KORRIGERT flagg: revisor registrert ved åpningen
df["rev_open_le"] = df.rev_state_le == "navngitt"    # sensitivitet: Revisor-felt datert på åpningsdagen teller med
df["rev_ever"] = df.rev_n > 0                        # B2s variabel: har noen gang hatt en revisorkunngjøring før åpningen
vb2 = pd.read_csv(ROOT + "verifikasjon/V-B2-04-revisorfelt.csv", dtype={"orgnr": str}).set_index("orgnr").rev_state
df["rev_state_vb2"] = df.orgnr.map(vb2)

# flags
df["fl_ta"] = df.total_assets.isna() | (df.total_assets < 1e6)
df["fl_lev"] = df.levert.isin(["Ikke levert", "For ungt"])       # B2/V-B2: «ikke levert, eller for ungt til å ha levert noe»
df["fl_lev_strict"] = df.levert.eq("Ikke levert")                 # sensitivitet: bare «ikke levert»
df["fl_rev"] = ~df.rev_open; df["fl_rev_old"] = ~df.rev_ever; df["fl_rev_le"] = ~df.rev_open_le
df["nfl"] = df.fl_ta.astype(int) + df.fl_rev.astype(int) + df.fl_lev.astype(int)
df["nfl_old"] = df.fl_ta.astype(int) + df.fl_rev_old.astype(int) + df.fl_lev.astype(int)
df["nfl_le"] = df.fl_ta.astype(int) + df.fl_rev_le.astype(int) + df.fl_lev.astype(int)
df["nfl_strict"] = df.fl_ta.astype(int) + df.fl_rev.astype(int) + df.fl_lev_strict.astype(int)
f = df[df.full].copy()

# ------------------------------------------------------------------ 0. validation against the verified numbers (B2 + V-B2)
P("# D2 — resultater (generert av D2-sjekkliste.py, 12.09.2026)"); P()
P("## 0. Kontroll mot verifiserte tall (må stemme før noe nytt regnes)"); P()
chk = {
 "kohort / innstilt / avsluttet / åpne (as-of)": (f"{len(df)} / {int(df.y_asof.sum())} / {int(df.avsl_asof.sum())} / {int(df.open_asof.sum())}", "5165 / 3897 / 917 / 351"),
 "fullvindu n / innstilt ≤730 d / ord. avsl ≤730 d / åpne d730": (f"{len(f)} / {int(f.y730.sum())} / {int(f.avsl730.sum())} / {int(f.open730.sum())}", "3772 / 2812 / 670 / 290"),
 "sum eiendeler 3 bånd + ingen (fullvindu): <1 / 1–5 / ≥5 / ingen": (" / ".join(str(int((f.ta3 == l).sum())) for l in ["<1 mill.", "1–<5 mill.", "≥5 mill.", NA]), "1929 / 1006 / 583 / 254"),
 "siste pliktige regnskap: levert / ikke levert / for ungt (fullvindu)": (" / ".join(str(int((f.levert == l).sum())) for l in ["Levert", "Ikke levert", "For ungt"]), "2960 / 435 / 377"),
 "samme, alle 5 165": (" / ".join(str(int((df.levert == l).sum())) for l in ["Levert", "Ikke levert", "For ungt"]), "4014 / 667 / 484"),
 "Revisor-tilstand alle 5 165: ingen / navngitt / utgaar / tvetydig": (" / ".join(str(int((df.rev_state == l).sum())) for l in ["ingen", "navngitt", "utgaar", "tvetydig"]), "3151 / 1382 / 632 / 0 (V-B2-04)"),
 "egen avledning = V-B2-04 rad for rad": (str(int((df.rev_state == df.rev_state_vb2).sum())) + " av 5165", "5165"),
 "B2s «har noen gang hatt revisor» (fullvindu) / derav Utgår som siste verdi": (f"{int(f.rev_ever.sum())} / {int((f.rev_ever & (f.rev_state == 'utgaar')).sum())}", "1466 / 458"),
 "revisor navngitt ved åpningen (fullvindu) / ikke": (f"{int(f.rev_open.sum())} / {int((~f.rev_open).sum())}", "1008 / 2764"),
 "B2s sjekkliste (gammelt flagg), n per 0/1/2/3": (" / ".join(str(int((f.nfl_old == k).sum())) for k in range(4)), "966 / 895 / 1327 / 584"),
 "B2s sjekkliste, innstilt ≤730 d %": (" / ".join(f"{100 * f[f.nfl_old == k].y730.mean():.1f}" for k in range(4)), "53.1 / 73.1 / 84.5 / 89.7"),
 "B2s sjekkliste, median dager": (" / ".join(f"{f[(f.nfl_old == k) & f.y730].d_innstilt.median():.0f}" for k in range(4)), "247 / 161 / 128 / 120"),
 "B2s sjekkliste as-of n": (" / ".join(str(int((df.nfl_old == k).sum())) for k in range(4)), "1294 / 1245 / 1838 / 788"),
 "revisor univariat (B2-flagg) med / uten": (f"{pct(int(f[f.rev_ever].y730.sum()), int(f.rev_ever.sum()))} / {pct(int(f[~f.rev_ever].y730.sum()), int((~f.rev_ever).sum()))}", "891/1466 = 60.8 / 1921/2306 = 83.3"),
 "revisor univariat (korrigert) med / uten": (f"{pct(int(f[f.rev_open].y730.sum()), int(f.rev_open.sum()))} / {pct(int(f[~f.rev_open].y730.sum()), int((~f.rev_open).sum()))}", "535/1008 = 53.1 / 2277/2764 = 82.4"),
}
P("| Kontroll | D2 | Forventet (B2 / V-B2) |"); P("|---|---|---|")
for k, (a, b) in chk.items(): P(f"| {k} | {a} | {b} |")
P()
ties_lt = int((df.rev_state == "tvetydig").sum()); ties_le = int((df.rev_state_le == "tvetydig").sum())
same_day = int(((df.rev_state_le != df.rev_state)).sum())
P(f"Tvetydige siste-dager (to ulike Revisor-verdier samme dag): {ties_lt} (strengt før) / {ties_le} (t.o.m. åpningsdagen). "
  f"Bo hvis tilstand endres når Revisor-felt datert på selve åpningsdagen telles med: {same_day} av 5 165 "
  f"({int(((df.rev_state_le == 'navngitt') & ~df.rev_open).sum())} blir «navngitt», {int(((df.rev_state_le != 'navngitt') & df.rev_open).sum())} mister revisor)."); P()
# cross-check of our derived variables against B2's per-estate table
b2 = pd.read_csv(ROOT + "data/B2-per-estate.csv", dtype={"orgnr": str}).set_index("orgnr")
m = df.set_index("orgnr")
xta = int((m.ta3.map({"<1 mill.": "<1 mill.", "1–<5 mill.": "1–<5 mill.", "≥5 mill.": "≥5 mill.", NA: NA}) ==
           b2.total_assets.map(lambda x: band(x, [1e6, 5e6, np.inf], ["<1 mill.", "1–<5 mill.", "≥5 mill."])).reindex(m.index)).sum())
xlev = int((m.levert.map({"Levert": "Ja", "Ikke levert": "Nei", "For ungt": "Ikke aktuelt"}) == b2.levert_siste_frist.reindex(m.index).str.slice(0, 12).map(lambda s: s if s in ("Ja", "Nei") else "Ikke aktuelt")).sum())
xy = int((m.y730 == b2.y730.reindex(m.index).astype(bool)).sum()); xr = int((m.rev_ever == (b2.n_revisorrader_for.reindex(m.index) > 0)).sum())
P(f"Rad-for-rad mot B2-per-estate.csv: sum eiendeler-bånd like {xta}/5165; leveringsstatus like {xlev}/5165; y730 like {xy}/5165; «har hatt revisor» like {xr}/5165."); P()
RES["kontroll"] = {k: a for k, (a, b) in chk.items()}

# ------------------------------------------------------------------ 3. the checklist with the corrected auditor flag
def ladder(col, title, note):
    P(f"### {title}"); P(); P(note); P()
    P("| Flagg | n (730 d) | Innstilt innen 730 d | Wilson 95 % | Ordinært avsluttet ≤730 d | Fortsatt åpent dag 730 | Median dager til innstilling (innstilte ≤730 d) | AJ 730 d (alle 5 165) | n (as-of) | Innstilt as-of 24.08.2026 | Wilson 95 % | Ord. avsl. as-of | Åpne as-of | Median dager (innstilte as-of) |")
    P("|---|---:|---|---|---|---|---:|---|---:|---|---|---|---|---:|")
    tab = {}
    for k in range(4):
        b = f[f[col] == k]; a = df[df[col] == k]
        kk = int(b.y730.sum()); ka = int(a.y_asof.sum())
        aj = aalen_johansen(a)
        P(f"| {k} | {len(b)} | {pct(kk, len(b))} | {wci(kk, len(b))} | {int(b.avsl730.sum())} = {100 * b.avsl730.mean():.1f} % | {int(b.open730.sum())} = {100 * b.open730.mean():.1f} % | {b[b.y730].d_innstilt.median():.0f} | {100 * aj:.1f} % | {len(a)} | {pct(ka, len(a))} | {wci(ka, len(a))} | {int(a.avsl_asof.sum())} = {100 * a.avsl_asof.mean():.1f} % | {int(a.open_asof.sum())} = {100 * a.open_asof.mean():.1f} % | {a[a.y_asof].d_innstilt.median():.0f} |")
        tab[k] = dict(n730=len(b), k730=kk, p730=kk / len(b), wilson730=wilson(kk, len(b)), avsl730=int(b.avsl730.sum()), open730=int(b.open730.sum()),
                      med730=float(b[b.y730].d_innstilt.median()), aj730=aj, n_asof=len(a), k_asof=ka, p_asof=ka / len(a), wilson_asof=wilson(ka, len(a)),
                      avsl_asof=int(a.avsl_asof.sum()), open_asof=int(a.open_asof.sum()), med_asof=float(a[a.y_asof].d_innstilt.median()))
    kk = int(f.y730.sum()); ka = int(df.y_asof.sum())
    P(f"| **Alle** | {len(f)} | {pct(kk, len(f))} | {wci(kk, len(f))} | {int(f.avsl730.sum())} = {100 * f.avsl730.mean():.1f} % | {int(f.open730.sum())} = {100 * f.open730.mean():.1f} % | {f[f.y730].d_innstilt.median():.0f} | {100 * aalen_johansen(df):.1f} % | {len(df)} | {pct(ka, len(df))} | {wci(ka, len(df))} | {int(df.avsl_asof.sum())} = {100 * df.avsl_asof.mean():.1f} % | {int(df.open_asof.sum())} = {100 * df.open_asof.mean():.1f} % | {df[df.y_asof].d_innstilt.median():.0f} |")
    d, lo, hi = newcombe(tab[3]["k730"], tab[3]["n730"], tab[0]["k730"], tab[0]["n730"])
    da, loa, hia = newcombe(tab[3]["k_asof"], tab[3]["n_asof"], tab[0]["k_asof"], tab[0]["n_asof"])
    ct = pd.crosstab(f[col], f.y730); chi = stats.chi2_contingency(ct.values)[1]
    P(); P(f"Differanse 3 mot 0 flagg: {100 * d:+.1f} pp [{100 * lo:+.1f}; {100 * hi:+.1f}] (730 d); {100 * da:+.1f} pp [{100 * loa:+.1f}; {100 * hia:+.1f}] (as-of). "
           f"Univariat AUC for antall flagg (730 d): {auc(f.y730.values, f[col].values):.3f}; χ²-test p = {chi:.2g}."); P()
    tab["diff730"] = (d, lo, hi); tab["diff_asof"] = (da, loa, hia); tab["auc730"] = float(auc(f.y730.values, f[col].values))
    return tab

P("## 1. Sjekklisten med korrigert revisorflagg"); P()
P("Flaggene: (1) sum eiendeler i siste balanse før åpningsåret under 1 mill. kr, eller ingen balanse; (2) INGEN revisor registrert ved åpningen "
  "(siste «Revisor»-felt på kunngjøringene før åpningen bærer ikke et navn — enten er feltet aldri kunngjort, eller siste verdi er «Utgår»); "
  "(3) siste pliktige årsregnskap ikke levert (godkjenning ikke kunngjort før åpningen), eller selskapet for ungt til å ha levert noe — samme definisjon som B2/V-B2."); P()
RES["ladder_new"] = ladder("nfl", "1.1 Hovedtabell — korrigert flagg (revisor registrert ved åpningen)", "Kun flagg (2) er endret mot B2/V-B2; flagg (1) og (3) er identiske.")
RES["ladder_old"] = ladder("nfl_old", "1.2 Til sammenlikning — B2s gamle flagg («har noen gang hatt revisor», 458 strøkne telt som registrert)", "Reproduksjon av B2 § 1.36b / 5.5 og V-B2 § 1 (skal være 966/895/1 327/584 og 53,1/73,1/84,5/89,7).")
RES["ladder_le"] = ladder("nfl_le", "1.3 Sensitivitet — Revisor-felt datert på selve åpningsdagen teller med (dato ≤ åpning)", "53 bo har et Revisor-felt datert på åpningsdagen; hovedvarianten teller bare felt strengt før åpningen (V-B2-04).")
RES["ladder_strict"] = ladder("nfl_strict", "1.4 Sensitivitet — flagg (3) bare «ikke levert» (for unge selskaper får ikke flagget)", "Korrigert revisorflagg; flagg (3) uten «for ungt».")

# 8 cells
P("### 1.5 De åtte flaggkombinasjonene (korrigert flagg)"); P()
P("| Balanse < 1 mill./ingen | Ingen revisor ved åpningen | Siste pliktige regnskap ikke levert/for ungt | Flagg | n (730 d) | Innstilt innen 730 d | Wilson 95 % | n (as-of) | Innstilt as-of |")
P("|---|---|---|---:|---:|---|---|---:|---|")
cells = []
for a_ in [False, True]:
    for r_ in [False, True]:
        for l_ in [False, True]:
            b = f[(f.fl_ta == a_) & (f.fl_rev == r_) & (f.fl_lev == l_)]; a = df[(df.fl_ta == a_) & (df.fl_rev == r_) & (df.fl_lev == l_)]
            kk = int(b.y730.sum()); ka = int(a.y_asof.sum())
            P(f"| {'ja' if a_ else 'nei'} | {'ja' if r_ else 'nei'} | {'ja' if l_ else 'nei'} | {int(a_) + int(r_) + int(l_)} | {len(b)} | {pct(kk, len(b))} | {wci(kk, len(b))} | {len(a)} | {pct(ka, len(a))} |")
            cells.append(dict(fl_ta=a_, fl_rev=r_, fl_lev=l_, n730=len(b), k730=kk, n_asof=len(a), k_asof=ka))
P(); RES["cells"] = cells

# cross tables with the corrected flag (replace B2 §1.37/1.38)
P("### 1.6 Kryss: sum eiendeler × revisor registrert ved åpningen (730 d; as-of i parentes)"); P()
P("| Sum eiendeler | Ingen revisor ved åpningen | Revisor registrert ved åpningen |"); P("|---|---|---|")
for lv in [NA, "<1 mill.", "1–<5 mill.", "≥5 mill."]:
    cells_ = []
    for rv_ in [False, True]:
        b = f[(f.ta3 == lv) & (f.rev_open == rv_)]; a = df[(df.ta3 == lv) & (df.rev_open == rv_)]
        kk = int(b.y730.sum()); ka = int(a.y_asof.sum())
        cells_.append(f"{pct(kk, len(b))} {wci(kk, len(b))} (as-of {pct(ka, len(a))})")
    P(f"| {lv} | {cells_[0]} | {cells_[1]} |")
P()
P("### 1.7 Kryss: revisor registrert ved åpningen × siste pliktige regnskap (730 d)"); P()
P("| Revisor ved åpningen | Levert | Ikke levert | For ungt |"); P("|---|---|---|---|")
for rv_ in [False, True]:
    cells_ = []
    for lv in ["Levert", "Ikke levert", "For ungt"]:
        b = f[(f.rev_open == rv_) & (f.levert == lv)]; kk = int(b.y730.sum()); cells_.append(f"{pct(kk, len(b))} {wci(kk, len(b))}")
    P(f"| {'ja' if rv_ else 'nei'} | {cells_[0]} | {cells_[1]} | {cells_[2]} |")
P()

# ------------------------------------------------------------------ 4. out-of-sample check
P("## 2. Ut-av-utvalg-kontroll (50/50-splitt)"); P()
def ladder_split(tr, te, col):
    return [(int(tr[tr[col] == k].y730.sum()), int((tr[col] == k).sum()), int(te[te[col] == k].y730.sum()), int((te[col] == k).sum())) for k in range(4)]
rng = np.random.default_rng(2026); idx = rng.permutation(len(f)); half = len(idx) // 2
tr = f.iloc[idx[:half]]; te = f.iloc[idx[half:]]
P("### 2.1 Samme splitt som V-B2 (seed 2026), terskler faste (1 mill.; revisor ved åpningen; levert)"); P()
P("| Flagg | Treningshalvdel | Testhalvdel | Wilson 95 % (test) |"); P("|---|---|---|---|")
sp = ladder_split(tr, te, "nfl"); RES["split2026"] = {}
for k, (ktr, ntr, kte, nte) in enumerate(sp):
    P(f"| {k} | {pct(ktr, ntr)} | {pct(kte, nte)} | {wci(kte, nte)} |"); RES["split2026"][k] = dict(k_tr=ktr, n_tr=ntr, k_te=kte, n_te=nte)
a_in = auc(f.y730.values, f.nfl.values); a_te = auc(te.y730.values, te.nfl.values); a_tr = auc(tr.y730.values, tr.nfl.values)
P(); P(f"AUC for antall flagg: hele fullvinduet {a_in:.3f}; treningshalvdel {a_tr:.3f}; testhalvdel {a_te:.3f}. (V-B2 med gammelt flagg: 0,693 i utvalget, 0,707 på testhalvdelen.)"); P()
RES["split2026"]["auc_in"] = float(a_in); RES["split2026"]["auc_tr"] = float(a_tr); RES["split2026"]["auc_te"] = float(a_te)
# same split, old flag, for the record
spo = ladder_split(tr, te, "nfl_old")
P("Samme splitt med B2s gamle flagg (skal gi V-B2s 51,8 / 75,7 / 85,3 / 91,2 på testhalvdelen): " + " / ".join(f"{100 * kte / nte:.1f}" for (ktr, ntr, kte, nte) in spo) + f"; AUC test {auc(te.y730.values, te.nfl_old.values):.3f}."); P()
# genuine threshold freezing: choose the asset threshold on the training half
P("### 2.2 Terskelen for balansen valgt på treningshalvdelen (kandidater 0,1 / 0,25 / 0,5 / 1 / 2 / 5 mill.), deretter låst og anvendt på testhalvdelen"); P()
cands = [1e5, 2.5e5, 5e5, 1e6, 2e6, 5e6]
def nfl_thr(d, thr): return (d.total_assets.isna() | (d.total_assets < thr)).astype(int) + d.fl_rev.astype(int) + d.fl_lev.astype(int)
P("| Terskel | AUC trening | AUC test | Test: 0 / 1 / 2 / 3 flagg |"); P("|---|---:|---:|---|")
best = None
for thr in cands:
    s_tr = nfl_thr(tr, thr); s_te = nfl_thr(te, thr); atr = auc(tr.y730.values, s_tr.values); ate = auc(te.y730.values, s_te.values)
    shares = " / ".join(f"{100 * te[s_te == k].y730.mean():.1f}" if (s_te == k).sum() else "–" for k in range(4))
    P(f"| {thr / 1e6:g} mill. | {atr:.3f} | {ate:.3f} | {shares} |")
    if best is None or atr > best[1]: best = (thr, atr, ate)
P(); P(f"Valgt på treningshalvdelen: {best[0] / 1e6:g} mill. (AUC trening {best[1]:.3f}); på testhalvdelen gir den AUC {best[2]:.3f}."); P()
RES["thr_search"] = dict(chosen=best[0], auc_tr=best[1], auc_te=best[2])
# many random splits
P("### 2.3 500 tilfeldige 50/50-splitter (terskler faste): fordelingen av testhalvdelens andeler"); P()
rows = []; picks = []
for s in range(500):
    r = np.random.default_rng(1000 + s); ix = r.permutation(len(f)); h = len(ix) // 2; tr_ = f.iloc[ix[:h]]; te_ = f.iloc[ix[h:]]
    rows.append([te_[te_.nfl == k].y730.mean() for k in range(4)] + [auc(te_.y730.values, te_.nfl.values)])
    picks.append(max(cands, key=lambda t: auc(tr_.y730.values, nfl_thr(tr_, t).values)))
rows = np.array(rows)
P("| Størrelse | Snitt over 500 testhalvdeler | 2,5–97,5-persentil |"); P("|---|---:|---|")
for j, lab in enumerate(["0 flagg", "1 flagg", "2 flagg", "3 flagg", "AUC antall flagg"]):
    P(f"| {lab} | {rows[:, j].mean() * (100 if j < 4 else 1):.{1 if j < 4 else 3}f}{' %' if j < 4 else ''} | {np.percentile(rows[:, j], 2.5) * (100 if j < 4 else 1):.{1 if j < 4 else 3}f}–{np.percentile(rows[:, j], 97.5) * (100 if j < 4 else 1):.{1 if j < 4 else 3}f}{' %' if j < 4 else ''} |")
pk = pd.Series(picks).value_counts()
P(); P("Terskel valgt på treningshalvdelen (500 splitter): " + ", ".join(f"{t / 1e6:g} mill. {c} ganger" for t, c in pk.items()) + "."); P()
RES["splits500"] = dict(mean=rows.mean(axis=0).tolist(), p2_5=np.percentile(rows, 2.5, axis=0).tolist(), p97_5=np.percentile(rows, 97.5, axis=0).tolist(), picks={str(t): int(c) for t, c in pk.items()})

# ------------------------------------------------------------------ 5. compact three-signal model (model D) and the profile range
P("## 3. Den kompakte tre-signal-modellen (modell D) med korrigert flagg"); P()
f["lev_m"] = f.levert; f["ta_m"] = f.ta3
SPEC_D_NEW = [("ta_m", "cat", "1–<5 mill."), ("rev_open", "bin", None), ("lev_m", "cat", "Levert")]
SPEC_D_OLD = [("ta_m", "cat", "1–<5 mill."), ("rev_ever", "bin", None), ("lev_m", "cat", "Levert")]
mD_old = fit("3.0 Reproduksjon: modell D med B2s gamle flagg (skal gi AUC 0,710, CV 0,703, OR revisor 0,56)", f, SPEC_D_OLD)
mD = fit("3.1 Modell D med revisor registrert ved åpningen", f, SPEC_D_NEW)
RES["modelD_old"] = dict(auc=mD_old["auc"], cv=mD_old["cv"], cv20=mD_old["cv20"], rows=mD_old["rows"]); RES["modelD_new"] = dict(auc=mD["auc"], cv=mD["cv"], cv20=mD["cv20"], rows=mD["rows"])
def profile(m, ta, rev, lev, revcol):
    names, b, cov = m["names"], m["beta"], m["cov"]; v = np.zeros(len(names)); v[0] = 1
    if ta != "1–<5 mill.": v[names.index(f"ta_m={ta}")] = 1
    v[names.index(revcol)] = float(rev)
    if lev != "Levert": v[names.index(f"lev_m={lev}")] = 1
    eta = float(v @ b); se = math.sqrt(float(v @ cov @ v)); g = lambda z: 1 / (1 + math.exp(-z))
    return g(eta), g(eta - 1.96 * se), g(eta + 1.96 * se)
PROFILES = [("≥5 mill.", True, "Levert", "Eiendeler ≥ 5 mill., revisor registrert ved åpningen, regnskap levert"),
            ("1–<5 mill.", True, "Levert", "Eiendeler 1–5 mill., revisor registrert, regnskap levert"),
            ("1–<5 mill.", False, "Levert", "Eiendeler 1–5 mill., ingen revisor, regnskap levert"),
            ("<1 mill.", False, "Levert", "Eiendeler < 1 mill., ingen revisor, regnskap levert"),
            ("<1 mill.", False, "Ikke levert", "Eiendeler < 1 mill., ingen revisor, siste regnskap ikke levert"),
            (NA, False, "Ikke levert", "Ingen balanse, ingen revisor, siste regnskap ikke levert"),
            (NA, False, "For ungt", "Ingen balanse, ingen revisor, for ungt")]
P("### 3.2 Predikerte sannsynligheter for typiske profiler (innstilt innen 730 d), korrigert flagg; B2s gamle tall i siste kolonne"); P()
P("| Profil | Predikert (modell D, korrigert) | 95 % KI | Observert i cellen (730 d) | Observert as-of (alle 5 165) | B2/V-B2 (gammelt flagg): predikert / observert |"); P("|---|---:|---|---|---|---|")
RES["profiles"] = []
for ta, rev, lev, lab in PROFILES:
    pm, lo, hi = profile(mD, ta, rev, lev, "rev_open"); po, _, _ = profile(mD_old, ta, rev, lev, "rev_ever")
    b = f[(f.ta_m == ta) & (f.rev_open == rev) & (f.lev_m == lev)]; a = df[(df.ta3 == ta) & (df.rev_open == rev) & (df.levert == lev)]
    bo = f[(f.ta_m == ta) & (f.rev_ever == rev) & (f.lev_m == lev)]
    kk = int(b.y730.sum()); ka = int(a.y_asof.sum()); ko = int(bo.y730.sum())
    P(f"| {lab} | {100 * pm:.1f} % | {100 * lo:.1f}–{100 * hi:.1f} | {pct(kk, len(b))} {wci(kk, len(b))} | {pct(ka, len(a))} | {100 * po:.1f} % / {pct(ko, len(bo))} |")
    RES["profiles"].append(dict(label=lab, pred=pm, lo=lo, hi=hi, k730=kk, n730=len(b), k_asof=ka, n_asof=len(a), pred_old=po, k_old=ko, n_old=len(bo)))
P()

# ------------------------------------------------------------------ 6. univariate auditor contrast and adjusted OR in model A
P("## 4. Revisorkontrasten: univariat og justert"); P()
P("### 4.1 Univariat (tre tilstander ved dag 730 og as-of)"); P()
P("| Revisor ved åpningen | n (730 d) | Innstilt innen 730 d | Wilson 95 % | Ord. avsl. ≤730 d | Åpent dag 730 | Median dager | AJ 730 d | n (as-of) | Innstilt as-of | Wilson 95 % | Ord. avsl. as-of | Åpne as-of |"); P("|---|---:|---|---|---|---|---:|---|---:|---|---|---|---|")
RES["rev_uni"] = {}
for rv_, lab in [(True, "registrert (siste Revisor-felt = navn)"), (False, "ikke registrert (aldri kunngjort, eller «Utgår»)")]:
    b = f[f.rev_open == rv_]; a = df[df.rev_open == rv_]; kk = int(b.y730.sum()); ka = int(a.y_asof.sum())
    P(f"| {lab} | {len(b)} | {pct(kk, len(b))} | {wci(kk, len(b))} | {100 * b.avsl730.mean():.1f} % | {100 * b.open730.mean():.1f} % | {b[b.y730].d_innstilt.median():.0f} | {100 * aalen_johansen(a):.1f} % | {len(a)} | {pct(ka, len(a))} | {wci(ka, len(a))} | {100 * a.avsl_asof.mean():.1f} % | {100 * a.open_asof.mean():.1f} % |")
    RES["rev_uni"][str(rv_)] = dict(n730=len(b), k730=kk, n_asof=len(a), k_asof=ka, avsl730=float(b.avsl730.mean()), open730=float(b.open730.mean()), aj=aalen_johansen(a))
for st_, lab in [("ingen", "— derav aldri kunngjort revisor"), ("utgaar", "— derav siste verdi «Utgår» (strøket)")]:
    b = f[f.rev_state == st_]; a = df[df.rev_state == st_]; kk = int(b.y730.sum()); ka = int(a.y_asof.sum())
    P(f"| {lab} | {len(b)} | {pct(kk, len(b))} | {wci(kk, len(b))} | {100 * b.avsl730.mean():.1f} % | {100 * b.open730.mean():.1f} % | {b[b.y730].d_innstilt.median():.0f} | {100 * aalen_johansen(a):.1f} % | {len(a)} | {pct(ka, len(a))} | {wci(ka, len(a))} | {100 * a.avsl_asof.mean():.1f} % | {100 * a.open_asof.mean():.1f} % |")
d, lo, hi = newcombe(int(f[~f.rev_open].y730.sum()), int((~f.rev_open).sum()), int(f[f.rev_open].y730.sum()), int(f.rev_open.sum()))
da, loa, hia = newcombe(int(df[~df.rev_open].y_asof.sum()), int((~df.rev_open).sum()), int(df[df.rev_open].y_asof.sum()), int(df.rev_open.sum()))
do, loo, hio = newcombe(int(f[~f.rev_ever].y730.sum()), int((~f.rev_ever).sum()), int(f[f.rev_ever].y730.sum()), int(f.rev_ever.sum()))
P(); P(f"Differanse uten − med revisor: {100 * d:+.1f} pp [{100 * lo:+.1f}; {100 * hi:+.1f}] (730 d); {100 * da:+.1f} pp [{100 * loa:+.1f}; {100 * hia:+.1f}] (as-of). B2s gamle flagg: {100 * do:+.1f} pp [{100 * loo:+.1f}; {100 * hio:+.1f}] (730 d)."); P()
RES["rev_diff"] = dict(d730=(d, lo, hi), d_asof=(da, loa, hia), d730_old=(do, loo, hio))

# model A — V-B2's specification (rebuilt here from the extract; industry code from B2's map via B2-per-estate, grouping as V-B2)
f["nace"] = f.orgnr.map(b2.nace); f["lab"] = f.bransje
def grp(k):
    if not isinstance(k, str): return None
    n2 = int(k[:2])
    if k.startswith("42") or k.startswith("43") or (k.startswith("41") and not k.startswith("41.1")): return "F Bygg utførende"
    if k.startswith("41.1") or n2 == 68: return "L Fast eiendom"
    if 45 <= n2 <= 47: return "G Varehandel"
    if 49 <= n2 <= 53: return "H Transport"
    if 55 <= n2 <= 56: return "I Overnatting/servering"
    if 69 <= n2 <= 75: return "M Faglig/teknisk"
    if 77 <= n2 <= 82: return "N Forretningsmessig"
    if 10 <= n2 <= 33: return "C Industri"
    return "Øvrige/uklassifisert"
IKKE = {"Uoppgitt", "Ikke oppgitt", "", "Uoppgitt næring", "Enheten er slettet"}
f["br_m"] = [(grp(k) if isinstance(k, str) else ("Uoppgitt" if (l or "").split(" || ")[0].strip() in IKKE else "Øvrige/uklassifisert")) for k, l in zip(f.nace, f.lab)]
f["rev_m"] = f.apply(lambda r: "1–<5 mill." if pd.isna(r.acc_fy) else ("Ikke oppgitt/0" if (pd.isna(r.operating_revenue) or r.operating_revenue < 1) else band(r.operating_revenue, [1e6, 5e6, 2e7, np.inf], ["<1 mill.", "1–<5 mill.", "5–<20 mill.", "≥20 mill."])), axis=1)
f["ek_neg"] = f.equity.notna() & (f.equity < 0)
f["alder"] = (f.opened - f.stift_eff).dt.days / 365.25
def aband(x, first_any, opened):
    if pd.isna(x):
        return "≥15 år" if (pd.notna(first_any) and (opened - first_any).days / 365.25 >= 15) else "≥15 år"
    return band(x, [2, 5, 10, 15, np.inf], ["<2 år", "2–<5 år", "5–<10 år", "10–<15 år", "≥15 år"], "≥15 år")
f["ald_m"] = [aband(x, fa, op) for x, fa, op in zip(f.alder, f.forste_any, f.opened)]
f["kap_m"] = f.kap_siste_for.map(lambda x: band(x, [30000.01, 100000.01, 1000000.01, np.inf], ["30 000 (minimum)", "30 001–100 000", "100 001–1 mill.", ">1 mill."], "30 000 (minimum)"))
f["vt_m"] = f.apply(lambda r: "Ingen" if not r.vt_24m else ("Regnskapsreg." if r.vt_regn else "Foretaksreg."), axis=1)
f["aar2024"] = (f.opened.dt.year == 2024)
SPEC_A_V = [("oppbud", "bin", None), ("br_m", "cat", "Øvrige/uklassifisert"), ("ta_m", "cat", "1–<5 mill."), ("rev_m", "cat", "1–<5 mill."), ("ek_neg", "bin", None),
            ("lev_m", "cat", "Levert"), ("ald_m", "cat", "5–<10 år"), ("kap_m", "cat", "30 000 (minimum)"), ("vt_m", "cat", "Ingen"), ("REV", "bin", None), ("dl_utgaar_12m", "bin", None), ("aar2024", "bin", None)]
P("### 4.2 Modell A, V-B2s spesifikasjon (12 blokker) — justert OR for revisor"); P()
SHOW = ["REV", "ta_m", "lev_m", "oppbud", "dl_utgaar_12m"]
mAv_old = fit("4.2a Gammelt flagg (skal gi V-B2s 0,665 [0,521–0,848], AUC 0,749)", f.assign(REV=f.rev_ever), SPEC_A_V, show=SHOW)
mAv_new = fit("4.2b Korrigert flagg (V-B2 fant 0,655 [0,507–0,847])", f.assign(REV=f.rev_open), SPEC_A_V, show=SHOW)
RES["modelA_vb2"] = dict(old=dict(auc=mAv_old["auc"], cv=mAv_old["cv"], cv20=mAv_old["cv20"], rev=mAv_old["rows"]["REV"]), new=dict(auc=mAv_new["auc"], cv=mAv_new["cv"], cv20=mAv_new["cv20"], rev=mAv_new["rows"]["REV"]))
# both flags in one model
mAv_both = fit("4.2c Begge revisorvariabler i samme modell (V-B2s spesifikasjon)", f.assign(REV=f.rev_open, REV2=f.rev_ever), SPEC_A_V + [("REV2", "bin", None)], show=["REV", "REV2"])
RES["modelA_vb2"]["both"] = dict(rev_open=mAv_both["rows"]["REV"], rev_ever=mAv_both["rows"]["REV2"])

# model A — B2's full specification (19 blocks), rebuilt from B2-per-estate.csv, auditor flag swapped
g = b2[b2.full.astype(bool)].copy()
g["y730"] = g.y730.astype(bool); g["oppbud"] = g.oppbud.astype(bool)
g["ta_m"] = g.total_assets.map(lambda x: band(x, [1e6, 5e6, np.inf], ["<1 mill.", "1–<5 mill.", "≥5 mill."], "Ingen regnskap før åpning"))
g["inntekt_m"] = g.inntekt_band.replace({"Ingen regnskap før åpning": "1–<5 mill.", "Ikke oppgitt": "Ikke oppgitt/0", "0": "Ikke oppgitt/0"})
g["levert_m"] = g.levert_siste_frist.map(lambda s: "Ikke aktuelt (ungt)" if s.startswith("Ikke aktuelt") else s)
g["varsel_m"] = g.varsel24_cat.replace({"Ukjent register (feed 2)": "Foretaksregisteret (manglende styre/DL/revisor)"})
g["kap_m"] = g.kap_band.replace({"<30 000": "30 000 (lovens minimum)", "Ukjent": "30 000 (lovens minimum)"})
g["alder_m"] = g.alder_band.replace({"Ukjent": "≥15 år"})
g["aar_2024"] = g.aar == 2024
g["bransje_m"] = g.bransjegruppe.replace({"A-B Primærnæringer og bergverk": "Øvrige/uklassifisert", "D-E Kraft, vann og renovasjon": "Øvrige/uklassifisert", "O-S Undervisning, helse, kultur og annen tjenesteyting": "Øvrige/uklassifisert", "J-K Informasjon, kommunikasjon og finans": "Øvrige/uklassifisert", "Uklassifisert etikett": "Øvrige/uklassifisert", "Uoppgitt (ingen næring i kunngjøringen)": "Uoppgitt", "F 41.1 Eiendomsutvikling": "L Fast eiendom (utleie, forvaltning, kjøp/salg)"})
g["ek_neg"] = g.ek_neg.astype(bool); g["dl_utgaar_12m"] = g.dl_utgaar_12m.astype(bool); g["revisor_utgaar_12m"] = g.revisor_utgaar_12m.astype(bool)
g["fratradt12"] = g.n_fratradt_12m > 0; g["styreendring12"] = g.n_styreendring_12m > 0; g["har_revisor"] = g.n_revisorrader_for > 0
g["navnebytte24"] = (g.n_navnebytte_24m > 0) | (g.n_navneendring_24m > 0); g["adresseendring24"] = g.n_adresseendring_24m > 0
g["flyttet_region24"] = g.n_postnr2_24m >= 2; g["kreditorvarsel24"] = g.n_kreditorvarsel_24m > 0
g["rev_open"] = g.index.map(df.set_index("orgnr").rev_open).astype(bool)
assert len(g) == 3772 and int(g.y730.sum()) == 2812
SPEC_A_B2 = [("oppbud", "bin", None), ("bransje_m", "cat", "Øvrige/uklassifisert"), ("ta_m", "cat", "1–<5 mill."), ("inntekt_m", "cat", "1–<5 mill."), ("ek_neg", "bin", None),
             ("levert_m", "cat", "Ja"), ("alder_m", "cat", "5–<10 år"), ("kap_m", "cat", "30 000 (lovens minimum)"), ("varsel_m", "cat", "Ingen"),
             ("fratradt12", "bin", None), ("dl_utgaar_12m", "bin", None), ("styreendring12", "bin", None), ("REV", "bin", None), ("revisor_utgaar_12m", "bin", None),
             ("navnebytte24", "bin", None), ("adresseendring24", "bin", None), ("flyttet_region24", "bin", None), ("kreditorvarsel24", "bin", None), ("aar_2024", "bin", None)]
P("### 4.3 Modell A, B2s fulle spesifikasjon (19 blokker, 41 koeffisienter) — justert OR for revisor"); P()
SHOW2 = ["REV", "ta_m", "levert_m", "oppbud", "dl_utgaar_12m", "revisor_utgaar_12m", "bransje_m"]
mAb_old = fit("4.3a Gammelt flagg (skal gi B2s 0,65 [0,51–0,84], AUC 0,750, CV 0,735)", g.assign(REV=g.har_revisor), SPEC_A_B2, show=SHOW2)
mAb_new = fit("4.3b Korrigert flagg", g.assign(REV=g.rev_open), SPEC_A_B2, show=SHOW2)
RES["modelA_b2"] = dict(old=dict(auc=mAb_old["auc"], cv=mAb_old["cv"], cv20=mAb_old["cv20"], rev=mAb_old["rows"]["REV"], rows=mAb_old["rows"]),
                        new=dict(auc=mAb_new["auc"], cv=mAb_new["cv"], cv20=mAb_new["cv20"], rev=mAb_new["rows"]["REV"], rows=mAb_new["rows"]))

# model without any accounting data (V-B2's T5) — the D16 line "modell UTEN regnskapstall"
P("### 4.4 Modell helt uten regnskapstall (V-B2s T5: oppbud, næring, alder, aksjekapital, varsel, revisor, regnskap levert, åpningsår)"); P()
SPEC_NOACC = [("oppbud", "bin", None), ("br_m", "cat", "Øvrige/uklassifisert"), ("ald_m", "cat", "5–<10 år"), ("kap_m", "cat", "30 000 (minimum)"), ("vt_m", "cat", "Ingen"), ("REV", "bin", None), ("lev_m", "cat", "Levert"), ("aar2024", "bin", None)]
mN_old = fit("4.4a Gammelt flagg (V-B2: AUC 0,690, CV 0,673)", f.assign(REV=f.rev_ever), SPEC_NOACC, show=["REV"])
mN_new = fit("4.4b Korrigert flagg", f.assign(REV=f.rev_open), SPEC_NOACC, show=["REV"])
RES["model_noacc"] = dict(old=dict(auc=mN_old["auc"], cv=mN_old["cv"], cv20=mN_old["cv20"]), new=dict(auc=mN_new["auc"], cv=mN_new["cv"], cv20=mN_new["cv20"], rev=mN_new["rows"]["REV"]))

# ------------------------------------------------------------------ 7. write
open(OUT + "D2-resultater.md", "w", encoding="utf-8").write(out.getvalue())
def conv(o):
    if isinstance(o, (np.floating, np.integer)): return o.item()
    if isinstance(o, np.ndarray): return o.tolist()
    if isinstance(o, (np.bool_,)): return bool(o)
    if isinstance(o, dict): return {str(k): conv(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [conv(v) for v in o]
    return o
json.dump(conv(RES), open(OUT + "D2-resultater.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nOK — skrevet D2-resultater.md og D2-resultater.json")
