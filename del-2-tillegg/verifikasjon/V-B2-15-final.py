# -*- coding: utf-8 -*-
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import pandas as pd, numpy as np, math
H="../data/"
exec(open(H+"V-B2-13-model.py",encoding="utf-8").read().split("json.dump(mA")[0])
def wilson(k,n,z=1.959964):
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return ((c-h)/d,(c+h)/d)
rs=pd.read_csv(H+"V-B2-04-revisorfelt.csv",dtype={"orgnr":str}).set_index("orgnr").rev_state
df["rev_state"]=df.orgnr.map(rs); f["rev_state"]=f.orgnr.map(rs)
f["rev_open"]=(f.rev_state=="navngitt")
print("=== T2b: revisor ved åpning (siste felt «Revisor» = et navn) vs analytikerens «noen gang revisorkunngjøring» ===")
print("  kryss:", pd.crosstab(f.rev_ever,f.rev_open).to_dict())
for col,lab in [("rev_ever","noen gang revisorrad (analytikerens «Revisor registrert»)"),("rev_open","revisor navngitt i siste Revisor-felt før åpning")]:
    a=f[f[col]]; b=f[~f[col]]
    print(f"  univariat {lab}: med {int(a.y730.sum())}/{len(a)} = {100*a.y730.mean():.1f} %   uten {int(b.y730.sum())}/{len(b)} = {100*b.y730.mean():.1f} %")
    sp=[s for s in SPEC_A if s[0]!="rev_ever"]+[(col,"bin",None)]
    X,names=design(f,sp); b2,se,_,p_=irls(X,y); i=names.index(col)
    print(f"    justert OR={math.exp(b2[i]):.3f} [{math.exp(b2[i]-1.96*se[i]):.3f}–{math.exp(b2[i]+1.96*se[i]):.3f}] p={pv(b2[i]/se[i]):.4f}  modell-AUC={auc(y,p_):.4f}")
# both in the same model
sp=[s for s in SPEC_A if s[0]!="rev_ever"]+[("rev_ever","bin",None),("rev_open","bin",None)]
X,names=design(f,sp); b2,se,_,_=irls(X,y)
for nm in ["rev_ever","rev_open"]:
    i=names.index(nm); print(f"    begge i samme modell: {nm:9s} OR={math.exp(b2[i]):.3f} [{math.exp(b2[i]-1.96*se[i]):.3f}–{math.exp(b2[i]+1.96*se[i]):.3f}] p={pv(b2[i]/se[i]):.4f}")

print("\n=== Sammensetning bygg vs øvrige — begge nevnere ===")
for d_,tag,ycol in [(f,"full-vindu n=3 772","y730"),(df,"alle 5 165","y_asof")]:
    bb=d_[d_.bygg==True]; oo=d_[d_.bygg!=True]
    def hi(s): return 100*((s.operating_revenue.notna())&(s.operating_revenue>=5e6)).mean()
    def lo(s): return 100*(((s.operating_revenue.isna())|(s.operating_revenue<1e6))).mean()
    print(f"  {tag}: ≥5 mill. oms. bygg {hi(bb):.1f} % vs øvrige {hi(oo):.1f} %  |  <1 mill./ingen: bygg {lo(bb):.1f} % vs øvrige {lo(oo):.1f} %  (analytiker: 36,6/23,9 og 28,1/44,7)")

print("\n=== «Uoppgitt næring» — analytikerens definisjon (etikett finnes, men er «Uoppgitt») ===")
IKKE2={"Uoppgitt","Ikke oppgitt","Uoppgitt næring",""}
df["uoppgitt"]=[ (not isinstance(k,str)) and ((l or "").strip() in IKKE2) for k,l in zip(df.nace,df.lab)]
u=df[df.uoppgitt]; uf=f[[(not isinstance(k,str)) and ((l or "").strip() in IKKE2) for k,l in zip(f.nace,f.lab)]]
print(f"  alle 5 165: n={len(u)}  innstilt as-of {int(u.y_asof.sum())}/{len(u)} = {100*u.y_asof.mean():.1f} %   (analytiker: 120 stk, 96,4 %)")
print(f"  full-vindu: n={len(uf)}  innstilt ≤730 d {int(uf.y730.sum())}/{len(uf)} = {100*uf.y730.mean():.1f} %")
print(f"  etiketter i gruppen: {df.loc[df.uoppgitt,'lab'].value_counts().to_dict()}")
print(f"  uklassifisert etikett (etikett finnes, ingen NACE, ikke «Uoppgitt»): n={int((df.nace.isna()&~df.uoppgitt).sum())}")

print("\n=== Journalistens spennvidde: predikert sannsynlighet for de to ytterprofilene ===")
SPEC_D=[("ta_m","cat","1–<5 mill."),("rev_ever","bin",None),("lev_m","cat","Ja")]
X,names=design(f,SPEC_D); b2,se,_,p_=irls(X,y)
cov=np.linalg.inv((X.T*np.clip(p_*(1-p_),1e-10,None))@X)
def prof(ta,rev,lev):
    v=np.zeros(len(names)); v[0]=1
    if ta!="1–<5 mill.": v[names.index(f"ta_m={ta}")]=1
    if rev: v[names.index("rev_ever")]=1
    if lev!="Ja": v[names.index(f"lev_m={lev}")]=1
    eta=v@b2; s=math.sqrt(v@cov@v)
    g=lambda z:1/(1+math.exp(-z)); return g(eta),g(eta-1.96*s),g(eta+1.96*s)
print("| Profil | predikert | 95 % KI | observert (full-vindu) |")
print("|---|---:|---|---|")
for ta,rev,lev,lbl in [("≥5 mill.",True,"Ja","≥5 mill. eiendeler, revisor, regnskap levert"),
                       ("1–<5 mill.",True,"Ja","1–5 mill., revisor, levert"),
                       ("<1 mill.",False,"Nei","<1 mill. eiendeler, ingen revisor, ikke levert"),
                       ("Ingen regnskap",False,"Nei","Ingen regnskap, ingen revisor, ikke levert")]:
    pm,lo_,hi_=prof(ta,rev,lev)
    s=f[(f.ta_m==ta)&(f.rev_ever==rev)&(f.lev_m==lev)]
    obs=f"{int(s.y730.sum())}/{len(s)} = {100*s.y730.mean():.1f} %" if len(s)>0 else "–"
    print(f"| {lbl} | {100*pm:.1f} % | {100*lo_:.1f}–{100*hi_:.1f} | {obs} |")

print("\n=== Desil-kalibrering, modell A (full-vindu) ===")
X,names=design(f,SPEC_A); b2,se,_,pA=irls(X,y)
q=pd.qcut(pd.Series(pA),10,labels=False,duplicates="drop")
print("| Desil | n | predikert snitt | observert | avvik (pp) |"); print("|---|---:|---:|---:|---:|")
for d_ in sorted(pd.unique(q)):
    m=(q==d_).values; print(f"| {d_+1} | {m.sum()} | {100*pA[m].mean():.1f} % | {100*y[m].mean():.1f} % | {100*(y[m].mean()-pA[m].mean()):+.1f} |")
hl=sum(((y[(q==d_).values].sum()-pA[(q==d_).values].sum())**2)/(pA[(q==d_).values].sum()*(1-pA[(q==d_).values].mean())) for d_ in sorted(pd.unique(q)))
from scipy.stats import chi2
print(f"  Hosmer–Lemeshow chi2(8) = {hl:.2f}  p = {1-chi2.cdf(hl,8):.3f}")
