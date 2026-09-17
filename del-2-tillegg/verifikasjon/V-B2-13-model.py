# -*- coding: utf-8 -*-
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import pandas as pd, numpy as np, math, io, json
H="../data/"
df=pd.read_pickle(H+"V-B2-feat2.pkl"); NA="Ingen regnskap"
f=df[df.full].copy()
# ---------------- model-level recodes (same level definitions as the analyst, so ORs are comparable)
f["ta_m"]=f.ta3
f["rev_m"]=f.rev_band.replace({NA:"1–<5 mill.","Ikke oppgitt":"Ikke oppgitt/0","0":"Ikke oppgitt/0"})
f["lev_m"]=f.levert.replace({"For ungt":"Ikke aktuelt (ungt)","Ikke levert":"Nei","Levert":"Ja"})
f["kap_m"]=f.kap_band.replace({"<30 000":"30 000 (minimum)","Ukjent":"30 000 (minimum)"})
f["ald_m"]=f.alder_band.replace({"≥15 år (fra første kunngjøring)":"≥15 år","Ukjent":"≥15 år"})
f["ald_m"]=f.ald_m.map(lambda x:"≥15 år" if str(x).startswith("Ukjent") else x)
f["vt_m"]=f.vt24_cat.replace({"Ingen varsel siste 24 mnd":"Ingen","Varsel 24m, Regnskapsreg.":"Regnskapsreg.",
                              "Varsel 24m, Foretaksreg.":"Foretaksreg.","Varsel 24m, ukjent":"Foretaksreg."})
def grp(k):
    if not isinstance(k,str): return None
    n2=int(k[:2])
    if k.startswith("42") or k.startswith("43") or (k.startswith("41") and not k.startswith("41.1")): return "F Bygg utførende"
    if k.startswith("41.1") or n2==68: return "L Fast eiendom"
    if 45<=n2<=47: return "G Varehandel"
    if 49<=n2<=53: return "H Transport"
    if 55<=n2<=56: return "I Overnatting/servering"
    if 69<=n2<=75: return "M Faglig/teknisk"
    if 77<=n2<=82: return "N Forretningsmessig"
    if 10<=n2<=33: return "C Industri"
    return "Øvrige/uklassifisert"
IKKE={"Uoppgitt","Ikke oppgitt","","Uoppgitt næring"}
f["br_m"]=[ (grp(k) if isinstance(k,str) else ("Uoppgitt" if (l or "").strip() in IKKE or (l or "").strip()=="" else "Øvrige/uklassifisert")) for k,l in zip(f.nace,f.lab)]
f["br_m"]=f.br_m.fillna("Øvrige/uklassifisert")
f["bygg"]=(f.nace.map(lambda k: isinstance(k,str) and (k.startswith("42") or k.startswith("43") or (k.startswith("41") and not k.startswith("41.1"))))).astype(bool)
f["aar2024"]=(f.opened.dt.year==2024).astype(float)
print("br_m:",f.br_m.value_counts().to_dict()); print("bygg (full-vindu):",int(f.bygg.sum()))
# ---------------- IRLS logistic
def design(d,spec):
    cols=[np.ones(len(d))]; names=["(konstant)"]
    for v,kind,ref in spec:
        if kind=="bin": cols.append(d[v].astype(float).values); names.append(v)
        else:
            for lv in sorted([x for x in d[v].unique() if x!=ref]):
                cols.append((d[v]==lv).astype(float).values); names.append(f"{v}={lv}")
    return np.column_stack(cols),names
def irls(X,y,maxit=200,tol=1e-10):
    b=np.zeros(X.shape[1])
    for _ in range(maxit):
        eta=X@b; p=1/(1+np.exp(-np.clip(eta,-35,35))); W=np.clip(p*(1-p),1e-10,None)
        XtW=X.T*W; H=XtW@X; g=X.T@(y-p)
        try: step=np.linalg.solve(H,g)
        except np.linalg.LinAlgError: step=np.linalg.lstsq(H,g,rcond=None)[0]
        b=b+step
        if np.max(np.abs(step))<tol: break
    eta=X@b; p=1/(1+np.exp(-np.clip(eta,-35,35))); W=np.clip(p*(1-p),1e-10,None)
    cov=np.linalg.inv((X.T*W)@X); se=np.sqrt(np.diag(cov))
    ll=float(np.sum(y*np.log(np.clip(p,1e-12,1))+(1-y)*np.log(np.clip(1-p,1e-12,1))))
    return b,se,ll,p
def auc(y,s):
    y=np.asarray(y); r=pd.Series(np.asarray(s,float)).rank().values; n1=y.sum(); n0=len(y)-n1
    return (r[y==1].sum()-n1*(n1+1)/2)/(n1*n0)
def cvauc(d,spec,y,k=10,seed=7):
    rng=np.random.default_rng(seed); idx=rng.permutation(len(d)); folds=np.array_split(idx,k); pr=np.zeros(len(d))
    for fo in folds:
        m=np.ones(len(d),bool); m[fo]=False
        Xtr,nm=design(d[m],spec); Xte,_=design(d[~m],spec)
        if Xte.shape[1]!=Xtr.shape[1]:
            Xte=np.column_stack([np.ones((~m).sum())]+[ (d[~m][v]==lv).astype(float).values if "=" in n else d[~m][n].astype(float).values
                for n,(v,lv) in []]) if False else Xte
        b,_,_,_=irls(Xtr,y[m]); pr[~m]=Xte@b
    return auc(y,pr)
def pv(z): return 2*(1-0.5*(1+math.erf(abs(z)/math.sqrt(2))))
def report(title,d,spec,y):
    X,nm=design(d,spec); b,se,ll,p=irls(X,y)
    X0=np.ones((len(d),1)); b0,_,ll0,_=irls(X0,y)
    print(f"\n### {title}\n  n={len(d)} events={int(y.sum())} logLik={ll:.4f} ll0={ll0:.4f} AUC={auc(y,p):.4f}")
    rows=[]
    for n,bb,ss in zip(nm,b,se):
        rows.append((n,math.exp(bb),math.exp(bb-1.96*ss),math.exp(bb+1.96*ss),pv(bb/ss)))
        print(f"   {n:58s} OR={math.exp(bb):7.3f} [{math.exp(bb-1.96*ss):6.3f}-{math.exp(bb+1.96*ss):7.3f}] p={pv(bb/ss):.4f}")
    return dict(names=nm,beta=b.tolist(),se=se.tolist(),ll=ll,ll0=ll0,auc=auc(y,p),n=len(d),events=int(y.sum())),rows
y=f.y730.values.astype(float)
SPEC_A=[("oppbud","bin",None),("br_m","cat","Øvrige/uklassifisert"),("ta_m","cat","1–<5 mill."),("rev_m","cat","1–<5 mill."),
        ("ek_neg","bin",None),("lev_m","cat","Ja"),("ald_m","cat","5–<10 år"),("kap_m","cat","30 000 (minimum)"),
        ("vt_m","cat","Ingen"),("rev_ever","bin",None),("dl_utgaar_12m","bin",None),("aar2024","bin",None)]
f["oppbud"]=f.oppbud.astype(bool); f["ek_neg"]=f.ek_neg.astype(bool)
mA,_=report("MODEL A (verifier) — innstilt ≤730 d, full-vindu",f,SPEC_A,y)
print(f"  10-fold CV AUC (seed 7): {cvauc(f,SPEC_A,y):.4f}   (seed 1: {cvauc(f,SPEC_A,y,seed=1):.4f}, seed 42: {cvauc(f,SPEC_A,y,seed=42):.4f})")
json.dump(mA,open(H+"V-B2-model-A.json","w"),ensure_ascii=False)
# LR tests
def lrtest(spec_full,drop):
    Xf,_=design(f,spec_full); bf,_,llf,_=irls(Xf,y)
    sp=[s for s in spec_full if s[0]!=drop]; Xr,_=design(f,sp); br,_,llr,_=irls(Xr,y)
    dfree=Xf.shape[1]-Xr.shape[1]
    from scipy.stats import chi2
    st=2*(llf-llr); return st,dfree,1-chi2.cdf(st,dfree)
print("\n### LR-tester (drop én blokk fra modell A)")
for v in ["ta_m","rev_m","ek_neg","lev_m","rev_ever","dl_utgaar_12m","br_m","oppbud","kap_m","ald_m","vt_m","aar2024"]:
    st,dd,pp=lrtest(SPEC_A,v); print(f"   {v:16s} chi2({dd})={st:8.2f}  p={pp:.3g}")
