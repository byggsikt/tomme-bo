# -*- coding: utf-8 -*-
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import pandas as pd, numpy as np, math, json
exec(open("./V-B2-13-model.py",encoding="utf-8").read().split("json.dump(mA")[0])
H="../data/"
def wilson(k,n,z=1.959964):
    if n==0: return (float('nan'),float('nan'))
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return ((c-h)/d,(c+h)/d)
print("\n\n========== BYGGSTIGEN (verifier) ==========")
f["byggf"]=f.bygg.astype(bool); f["tingrett_m"]=f.tingrett.fillna("Ukjent")
LAD=[("Bygg alene",[("byggf","bin",None)]),
     ("+ sum eiendeler",[("byggf","bin",None),("ta_m","cat","1–<5 mill.")]),
     ("+ driftsinntekter",[("byggf","bin",None),("ta_m","cat","1–<5 mill."),("rev_m","cat","1–<5 mill.")]),
     ("+ revisor",[("byggf","bin",None),("ta_m","cat","1–<5 mill."),("rev_m","cat","1–<5 mill."),("rev_ever","bin",None)]),
     ("+ regnskap levert, neg. EK",[("byggf","bin",None),("ta_m","cat","1–<5 mill."),("rev_m","cat","1–<5 mill."),("rev_ever","bin",None),("lev_m","cat","Ja"),("ek_neg","bin",None)]),
     ("+ tingrett (faste effekter)",[("byggf","bin",None),("ta_m","cat","1–<5 mill."),("rev_m","cat","1–<5 mill."),("rev_ever","bin",None),("lev_m","cat","Ja"),("ek_neg","bin",None),("tingrett_m","cat","OSLO TINGRETT")])]
print("| Modell | OR bygg | 95 % KI | p |"); print("|---|---:|---|---:|")
for nm,sp in LAD:
    X,names=design(f,sp); b,se,ll,p=irls(X,y); i=names.index("byggf")
    print(f"| {nm} | {math.exp(b[i]):.2f} | {math.exp(b[i]-1.96*se[i]):.2f}–{math.exp(b[i]+1.96*se[i]):.2f} | {pv(b[i]/se[i]):.4f} |")
bb=f[f.byggf]; oo=f[~f.byggf]
print(f"\nSammensetning: driftsinntekter ≥5 mill. hos {100*bb.rev_m.isin(['5–<20 mill.','≥20 mill.']).mean():.1f} % av byggkonkursene mot {100*oo.rev_m.isin(['5–<20 mill.','≥20 mill.']).mean():.1f} % i øvrige")
print(f"Ingen/ubetydelig omsetning (<1 mill., ikke oppgitt/0, ingen regnskap): bygg {100*((bb.rev_band.isin(['<1 mill.','0','Ikke oppgitt']))|(bb.acc_fy.isna())).mean():.1f} % mot øvrige {100*((oo.rev_band.isin(['<1 mill.','0','Ikke oppgitt']))|(oo.acc_fy.isna())).mean():.1f} %")
print(f"Bygg univariat, full-vindu: {int(bb.y730.sum())}/{len(bb)} = {100*bb.y730.mean():.1f} %  vs øvrige {int(oo.y730.sum())}/{len(oo)} = {100*oo.y730.mean():.1f} %")
ab=df[df.bygg==True]; ao=df[df.bygg!=True]
print(f"Bygg as-of (alle 5 165): {int(ab.y_asof.sum())}/{len(ab)} = {100*ab.y_asof.mean():.1f} %  vs øvrige {int(ao.y_asof.sum())}/{len(ao)} = {100*ao.y_asof.mean():.1f} %  (studien: 70,5 % vs 76,2 % ved 24 mnd)")

print("\n\n========== SJEKKLISTE (verifier) ==========")
for d_,tag in [(f,"full-vindu"),(df,"alle 5 165")]:
    d_=d_.copy()
    d_["fl_ta"]=(d_.total_assets.isna())|(d_.total_assets<1e6)
    d_["fl_rev"]=~(d_.rev_n>0)
    d_["fl_lev"]=d_.levert.isin(["Ikke levert","For ungt"])
    d_["nfl"]=d_.fl_ta.astype(int)+d_.fl_rev.astype(int)+d_.fl_lev.astype(int)
    if tag=="full-vindu": fchk=d_
    else: achk=d_
print("| Flagg | n (full) | Innstilt ≤730 d | Wilson 95 % | Ord. avsl | Åpen d730 | Median dager | as-of (alle 5 165) |")
print("|---|---:|---|---|---|---|---:|---|")
for k in [0,1,2,3]:
    b=fchk[fchk.nfl==k]; a=achk[achk.nfl==k]
    kk=int(b.y730.sum()); lo,hi=wilson(kk,len(b)); md=b[b.y730==1].d_innstilt.median()
    print(f"| {k} | {len(b)} | {kk} / {len(b)} = {100*kk/len(b):.1f} % | {100*lo:.1f}–{100*hi:.1f} | {100*b.avsl730.mean():.1f} % | {100*b.open730.mean():.1f} % | {md:.0f} | {int(a.y_asof.sum())}/{len(a)} = {100*a.y_asof.mean():.1f} % |")

print("\n--- ÆRLIG (out-of-sample) sjekkliste: 50/50 split, terskler frosset på treningshalvdelen ---")
rng=np.random.default_rng(2026); idx=rng.permutation(len(fchk)); half=len(idx)//2
tr=fchk.iloc[idx[:half]]; te=fchk.iloc[idx[half:]]
for k in [0,1,2,3]:
    a=tr[tr.nfl==k]; b=te[te.nfl==k]
    print(f"   {k} flagg: trening {int(a.y730.sum())}/{len(a)} = {100*a.y730.mean():.1f} %   test {int(b.y730.sum())}/{len(b)} = {100*b.y730.mean():.1f} %")
print(f"   AUC nfl (in-sample) {auc(fchk.y730.values,fchk.nfl.values):.3f}   AUC nfl på testhalvdel {auc(te.y730.values,te.nfl.values):.3f}")

print("\n\n========== ADVERSARIELLE TESTER ==========")
# T1: is "ingen regnskap" a source-coverage artifact?
na=f[f.acc_fy.isna()]
print(f"T1  «ingen regnskap før åpning» full-vindu n={len(na)}; av disse har {int((na.gk_n>0).sum())} en kunngjort godkjent årsregnskap før åpning (= vi mangler TALLENE, ikke selskapet)")
g1=na[na.gk_n>0]; g2=na[na.gk_n==0]
print(f"    innstilt ≤730 d: har levert men mangler tall {int(g1.y730.sum())}/{len(g1)} = {100*g1.y730.mean():.1f} %   aldri levert {int(g2.y730.sum())}/{len(g2)} = {100*g2.y730.mean():.1f} %")
f2=f[~((f.acc_fy.isna())&(f.gk_n>0))].copy(); y2=f2.y730.values.astype(float)
X,names=design(f2,SPEC_A); b,se,ll,p=irls(X,y2); i=names.index("ta_m=Ingen regnskap")
print(f"    Modell A uten de {len(f)-len(f2)} «levert men mangler tall»: OR(ingen regnskap)={math.exp(b[i]):.2f} [{math.exp(b[i]-1.96*se[i]):.2f}–{math.exp(b[i]+1.96*se[i]):.2f}] (hoved: 3,33)")
# T2: strict auditor definition
for col,lab in [("rev_ever","noen gang (analytikerens)"),("rev_36m","siste 36 mnd")]:
    sp=[s for s in SPEC_A if s[0]!="rev_ever"]+[(col,"bin",None)]
    X,names=design(f,sp); b,se,_,_=irls(X,y); i=names.index(col)
    print(f"T2  revisor «{lab}»: OR={math.exp(b[i]):.3f} [{math.exp(b[i]-1.96*se[i]):.3f}–{math.exp(b[i]+1.96*se[i]):.3f}] p={pv(b[i]/se[i]):.4f}")
# T3: rare flags — how rare?
print(f"T3  dl_utgaar_12m: n={int(f.dl_utgaar_12m.sum())} ({int(f[f.dl_utgaar_12m].y730.sum())}/{int(f.dl_utgaar_12m.sum())} = {100*f[f.dl_utgaar_12m].y730.mean():.1f} % innstilt)")
u=f[f.br_m=='Uoppgitt']; ua=df[(df.nace.isna())]
print(f"    br_m=Uoppgitt: full-vindu n={len(u)} ({int(u.y730.sum())}/{len(u)} = {100*u.y730.mean():.1f} %); alle 5 165 uten NACE n={len(ua)} ({int(ua.y_asof.sum())}/{len(ua)} = {100*ua.y_asof.mean():.1f} %)")
# T4: oppbud within the <1 MNOK band
for bnd in ["<1 mill.","1–<5 mill.","≥5 mill.","Ingen regnskap"]:
    s=f[f.ta_m==bnd]; a=s[s.oppbud]; b_=s[~s.oppbud]
    print(f"T4  oppbud innenfor {bnd:16s}: oppbud {int(a.y730.sum())}/{len(a)} = {100*a.y730.mean():.1f} %  vs begjæring {int(b_.y730.sum())}/{len(b_)} = {100*b_.y730.mean():.1f} %")
# T5: model WITHOUT any accounting data (what a lawyer can see with zero lookups)
SPEC_NOACC=[("oppbud","bin",None),("br_m","cat","Øvrige/uklassifisert"),("ald_m","cat","5–<10 år"),("kap_m","cat","30 000 (minimum)"),("vt_m","cat","Ingen"),("rev_ever","bin",None),("lev_m","cat","Ja"),("aar2024","bin",None)]
X,names=design(f,SPEC_NOACC); b,se,ll,p=irls(X,y)
print(f"T5  Modell uten regnskapstall i det hele tatt: AUC={auc(y,p):.3f}  (full modell 0,749)  CV={cvauc(f,SPEC_NOACC,y):.3f}")
# T6: 3-signal compact model
SPEC_D=[("ta_m","cat","1–<5 mill."),("rev_ever","bin",None),("lev_m","cat","Ja")]
X,names=design(f,SPEC_D); b,se,ll,p=irls(X,y)
print(f"T6  Kompakt 3-signal-modell: AUC={auc(y,p):.3f}  CV={cvauc(f,SPEC_D,y):.3f}  (analytiker: CV 0,70)")
