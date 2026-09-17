# -*- coding: utf-8 -*-
"""D2-03 — modell A (B2s fulle spesifikasjon) med korrigert revisorflagg: ALLE odds-ratioer, gammelt flagg ved siden av. Kun lesing."""
import sys, math
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import numpy as np, pandas as pd
from scipy import stats
ROOT = "./"
NA = "Ingen regnskap før åpning"
def band(x, edges, labels, na):
    if pd.isna(x): return na
    for e, l in zip(edges, labels):
        if x < e: return l
    return labels[-1]
def design(d, spec):
    X = [np.ones(len(d))]; names = ["(konstant)"]
    for var, kind, ref in spec:
        if kind == "bin": X.append(d[var].astype(float).values); names.append(var)
        else:
            for l in sorted([l for l in d[var].unique() if l != ref], key=str): X.append((d[var] == l).astype(float).values); names.append(f"{var}={l}")
    return np.column_stack(X), names
def irls(X, y):
    b = np.zeros(X.shape[1])
    for _ in range(200):
        p = 1 / (1 + np.exp(-np.clip(X @ b, -35, 35))); w = np.clip(p * (1 - p), 1e-10, None)
        step = np.linalg.solve((X.T * w) @ X, X.T @ (y - p)); b = b + step
        if np.max(np.abs(step)) < 1e-10: break
    p = 1 / (1 + np.exp(-np.clip(X @ b, -35, 35))); w = np.clip(p * (1 - p), 1e-10, None)
    return b, np.sqrt(np.diag(np.linalg.inv((X.T * w) @ X)))
b2 = pd.read_csv(ROOT + "data/B2-per-estate.csv", dtype={"orgnr": str}).set_index("orgnr")
rv = pd.read_csv(ROOT + "verifikasjon/V-B2-04-revisorfelt.csv", dtype={"orgnr": str}).set_index("orgnr").rev_state
g = b2[b2.full.astype(bool)].copy(); y = g.y730.astype(bool).astype(float).values
g["oppbud"] = g.oppbud.astype(bool)
g["ta_m"] = g.total_assets.map(lambda x: band(x, [1e6, 5e6, np.inf], ["<1 mill.", "1–<5 mill.", "≥5 mill."], NA))
g["inntekt_m"] = g.inntekt_band.replace({NA: "1–<5 mill.", "Ikke oppgitt": "Ikke oppgitt/0", "0": "Ikke oppgitt/0"})
g["levert_m"] = g.levert_siste_frist.map(lambda s: "Ikke aktuelt (ungt)" if s.startswith("Ikke aktuelt") else s)
g["varsel_m"] = g.varsel24_cat.replace({"Ukjent register (feed 2)": "Foretaksregisteret (manglende styre/DL/revisor)"})
g["kap_m"] = g.kap_band.replace({"<30 000": "30 000 (lovens minimum)", "Ukjent": "30 000 (lovens minimum)"})
g["alder_m"] = g.alder_band.replace({"Ukjent": "≥15 år"}); g["aar_2024"] = g.aar == 2024
g["bransje_m"] = g.bransjegruppe.replace({"A-B Primærnæringer og bergverk": "Øvrige/uklassifisert", "D-E Kraft, vann og renovasjon": "Øvrige/uklassifisert", "O-S Undervisning, helse, kultur og annen tjenesteyting": "Øvrige/uklassifisert", "J-K Informasjon, kommunikasjon og finans": "Øvrige/uklassifisert", "Uklassifisert etikett": "Øvrige/uklassifisert", "Uoppgitt (ingen næring i kunngjøringen)": "Uoppgitt", "F 41.1 Eiendomsutvikling": "L Fast eiendom (utleie, forvaltning, kjøp/salg)"})
for c in ["ek_neg", "dl_utgaar_12m", "revisor_utgaar_12m"]: g[c] = g[c].astype(bool)
g["fratradt12"] = g.n_fratradt_12m > 0; g["styreendring12"] = g.n_styreendring_12m > 0; g["har_revisor"] = g.n_revisorrader_for > 0
g["navnebytte24"] = (g.n_navnebytte_24m > 0) | (g.n_navneendring_24m > 0); g["adresseendring24"] = g.n_adresseendring_24m > 0
g["flyttet_region24"] = g.n_postnr2_24m >= 2; g["kreditorvarsel24"] = g.n_kreditorvarsel_24m > 0
g["rev_open"] = (g.index.map(rv) == "navngitt")
SPEC = [("oppbud", "bin", None), ("bransje_m", "cat", "Øvrige/uklassifisert"), ("ta_m", "cat", "1–<5 mill."), ("inntekt_m", "cat", "1–<5 mill."), ("ek_neg", "bin", None),
        ("levert_m", "cat", "Ja"), ("alder_m", "cat", "5–<10 år"), ("kap_m", "cat", "30 000 (lovens minimum)"), ("varsel_m", "cat", "Ingen"),
        ("fratradt12", "bin", None), ("dl_utgaar_12m", "bin", None), ("styreendring12", "bin", None), ("REV", "bin", None), ("revisor_utgaar_12m", "bin", None),
        ("navnebytte24", "bin", None), ("adresseendring24", "bin", None), ("flyttet_region24", "bin", None), ("kreditorvarsel24", "bin", None), ("aar_2024", "bin", None)]
Xo, no = design(g.assign(REV=g.har_revisor), SPEC); bo, so = irls(Xo, y)
Xn, nn = design(g.assign(REV=g.rev_open), SPEC); bn, sn = irls(Xn, y)
print("| Variabel (nivå) | OR gammelt flagg [95 % KI] | OR korrigert flagg [95 % KI] | p (korrigert) |"); print("|---|---|---|---:|")
for i in range(1, len(nn)):
    pv = 2 * stats.norm.sf(abs(bn[i] / sn[i]))
    print(f"| {nn[i]} | {math.exp(bo[i]):.2f} [{math.exp(bo[i]-1.96*so[i]):.2f}–{math.exp(bo[i]+1.96*so[i]):.2f}] | {math.exp(bn[i]):.2f} [{math.exp(bn[i]-1.96*sn[i]):.2f}–{math.exp(bn[i]+1.96*sn[i]):.2f}] | {pv:.3g} |")
