# -*- coding: utf-8 -*-
"""
D2-02 — avstemming mot V-B2s egne variabler (V-B2-feat2.pkl i arbeidsmappen) med V-B2s egne funksjoner (design/irls/auc/cvauc fra V-B2-13-model.py).
Formål: (a) reprodusere V-B2s «modell uten regnskapstall» 0,690 (CV 0,673) og V-B2s justerte OR 0,655 med korrigert flagg,
        (b) regne de samme modellene med korrigert flagg på NØYAKTIG V-B2s kovariatkoding, så D2s tall kan sammenliknes epler mot epler.
Kun lesing; skriver bare til stdout (fanget i D2-02-avstemming-vb2.txt).
"""
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import pandas as pd, numpy as np, math
V = "./"
src = open(V + "V-B2-13-model.py", encoding="utf-8").read().split("json.dump(mA")[0]
exec(src)   # laster V-B2-feat2.pkl, definerer f, y, SPEC_A, design, irls, auc, cvauc, pv, report; kjører modell A (V-B2) og skriver den ut
rs = pd.read_csv(V + "V-B2-04-revisorfelt.csv", dtype={"orgnr": str}).set_index("orgnr").rev_state
f["rev_open"] = (f.orgnr.map(rs) == "navngitt")
print("\n=== D2-02: kovariatnivåer hos V-B2 (fullvindu) ===")
for c in ["br_m", "ald_m", "kap_m", "vt_m", "lev_m", "ta_m"]:
    print(f"  {c}: {f[c].value_counts().to_dict()}")
print(f"  rev_ever {int(f.rev_ever.sum())}  rev_open {int(f.rev_open.sum())}")
def cv3(spec):
    return " / ".join(f"{cvauc(f, spec, y, seed=s):.3f}" for s in (1, 7, 42))
print("\n=== D2-02: modell A (V-B2s spesifikasjon) ===")
for col, lab in [("rev_ever", "gammelt flagg"), ("rev_open", "korrigert flagg")]:
    sp = [s for s in SPEC_A if s[0] != "rev_ever"] + [(col, "bin", None)]
    X, names = design(f, sp); b, se, ll, p = irls(X, y); i = names.index(col)
    print(f"  {lab:16s}: OR={math.exp(b[i]):.3f} [{math.exp(b[i]-1.96*se[i]):.3f}–{math.exp(b[i]+1.96*se[i]):.3f}] p={pv(b[i]/se[i]):.4f}  AUC={auc(y, p):.3f}  CV(seed 1/7/42)={cv3(sp)}")
print("\n=== D2-02: modell uten regnskapstall (V-B2s T5-spesifikasjon) ===")
for col, lab in [("rev_ever", "gammelt flagg"), ("rev_open", "korrigert flagg")]:
    sp = [("oppbud", "bin", None), ("br_m", "cat", "Øvrige/uklassifisert"), ("ald_m", "cat", "5–<10 år"), ("kap_m", "cat", "30 000 (minimum)"), ("vt_m", "cat", "Ingen"), (col, "bin", None), ("lev_m", "cat", "Ja"), ("aar2024", "bin", None)]
    X, names = design(f, sp); b, se, ll, p = irls(X, y); i = names.index(col)
    print(f"  {lab:16s}: OR={math.exp(b[i]):.3f} [{math.exp(b[i]-1.96*se[i]):.3f}–{math.exp(b[i]+1.96*se[i]):.3f}]  AUC={auc(y, p):.3f}  CV(seed 1/7/42)={cv3(sp)}")
print("\n=== D2-02: kompakt modell D (V-B2s koding) ===")
for col, lab in [("rev_ever", "gammelt flagg"), ("rev_open", "korrigert flagg")]:
    sp = [("ta_m", "cat", "1–<5 mill."), (col, "bin", None), ("lev_m", "cat", "Ja")]
    X, names = design(f, sp); b, se, ll, p = irls(X, y); i = names.index(col)
    print(f"  {lab:16s}: OR={math.exp(b[i]):.3f} [{math.exp(b[i]-1.96*se[i]):.3f}–{math.exp(b[i]+1.96*se[i]):.3f}]  AUC={auc(y, p):.3f}  CV(seed 1/7/42)={cv3(sp)}")
