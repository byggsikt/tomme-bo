# -*- coding: utf-8 -*-
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import pandas as pd, numpy as np, math
H="../data/"
exec(open(H+"V-B2-13-model.py",encoding="utf-8").read().split("json.dump(mA")[0])
def wilson(k,n,z=1.959964):
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return ((c-h)/d,(c+h)/d)
# balance age in months from FY-end to opening
f["bal_alder"]=[(op-pd.Timestamp(int(fy),12,31)).days/30.44 if pd.notna(fy) else np.nan for fy,op in zip(f.acc_fy,f.opened)]
b=f.bal_alder
print("=== Alder på den valgte balansen ved åpning (full-vindu) ===")
for lab,m in [("≤12 mnd",(b<=12)),("12–24 mnd",(b>12)&(b<=24)),(">24 mnd",(b>24)),("ingen balanse",b.isna())]:
    print(f"  {lab:15s} n={int(m.sum()):5d}   innstilt ≤730 d {int(f[m].y730.sum())}/{int(m.sum())} = {100*f[m].y730.mean():.1f} %")
print(f"  (analytikerens kavat: «for åpninger jan–sep er balansen ofte 12–24 mnd gammel — 2 095 av 3 772»; min telling 12–24 mnd + >24 mnd = {int(((b>12)).sum())})")
# statutory availability: FY Y accounts are due 31 July Y+1
f["frist"]=[pd.Timestamp(int(fy)+1,7,31) if pd.notna(fy) else pd.NaT for fy in f.acc_fy]
f["etter_frist"]=f.opened>f.frist
# and: was an approval actually announced for that FY before the opening?
f["gk_for_fy"]=[(pd.notna(fy) and pd.notna(g) and g>=pd.Timestamp(int(fy)+1,1,1)) for fy,g in zip(f.acc_fy,f.gk_siste)]
hasb=f[f.acc_fy.notna()]
print("\n=== Var tallene offentlig tilgjengelige da boet ble åpnet? (kun de 3 518 med balanse i full-vindu) ===")
print(f"  åpning ETTER innleveringsfristen (31.7 året etter): {int(hasb.etter_frist.sum())}/{len(hasb)} = {100*hasb.etter_frist.mean():.1f} %")
print(f"  åpning FØR fristen (tallene fantes ikke i Regnskapsregisteret): {int((~hasb.etter_frist).sum())}/{len(hasb)} = {100*(~hasb.etter_frist).mean():.1f} %")
print(f"  godkjent årsregnskap for DET regnskapsåret kunngjort før åpning: {int(hasb.gk_for_fy.sum())}/{len(hasb)} = {100*hasb.gk_for_fy.mean():.1f} %")
print(f"  IKKE kunngjort godkjent for det året før åpning: {int((~hasb.gk_for_fy).sum())}  (analytikerens kavat: 89)")
print("\n  Innstilt ≤730 d etter tilgjengelighet:")
for lab,m in [("tallene var offentlige (godkjent kunngjort)",hasb.gk_for_fy),("tallene var IKKE offentlige",~hasb.gk_for_fy)]:
    s=hasb[m]; print(f"    {lab:45s} {int(s.y730.sum())}/{len(s)} = {100*s.y730.mean():.1f} %")
# ROBUSTNESS: refit model A only on estates where the numbers were publicly available at opening
sub=f[(f.acc_fy.isna())|(f.gk_for_fy)].copy(); ys=sub.y730.values.astype(float)
X,names=design(sub,SPEC_A); bb,se,_,ps=irls(X,ys)
print(f"\n=== ROBUSTHET: modell A kun på bo der tallene var offentlige ved åpning (n={len(sub)}, hendelser={int(ys.sum())}, AUC={auc(ys,ps):.3f}) ===")
for nm in ["ta_m=<1 mill.","ta_m=Ingen regnskap","ta_m=≥5 mill.","rev_m=<1 mill.","rev_m=≥20 mill.","rev_ever","lev_m=Nei","ek_neg","oppbud","br_m=F Bygg utførende"]:
    i=names.index(nm); print(f"  {nm:28s} OR={math.exp(bb[i]):6.3f} [{math.exp(bb[i]-1.96*se[i]):.3f}–{math.exp(bb[i]+1.96*se[i]):.3f}] p={pv(bb[i]/se[i]):.4f}")
# size bands restricted to publicly available balances
print("\n=== Størrelsesbånd kun der tallene var offentlige ved åpning ===")
hb=hasb[hasb.gk_for_fy]
for lv in ["<1 mill.","1–<5 mill.","≥5 mill."]:
    s=hb[hb.ta3==lv]; lo,hi=wilson(int(s.y730.sum()),len(s))
    s2=hasb[hasb.ta3==lv]
    print(f"  {lv:12s} offentlig: {int(s.y730.sum())}/{len(s)} = {100*s.y730.mean():.1f} % [{100*lo:.1f}–{100*hi:.1f}]   alle m/balanse: {int(s2.y730.sum())}/{len(s2)} = {100*s2.y730.mean():.1f} %")
