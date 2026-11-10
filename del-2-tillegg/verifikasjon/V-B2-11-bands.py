# -*- coding: utf-8 -*-
import pandas as pd, numpy as np, math, io, sys
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
H="../data/"
df=pd.read_pickle(H+"V-B2-core.pkl")
NA="Ingen regnskap"
def wilson(k,n,z=1.959964):
    if n==0: return (float('nan'),float('nan'))
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))
    return ((c-h)/d,(c+h)/d)
def band(x,edges,labels,na=NA):
    if pd.isna(x): return na
    for e,l in zip(edges,labels):
        if x<e: return l
    return labels[-1]
TA_E=[1e5,5e5,1e6,5e6,2e7,np.inf]; TA_L=["<100 000","100 000–<500 000","500 000–<1 mill.","1–<5 mill.","5–<20 mill.","≥20 mill."]
df["ta_band"]=df.total_assets.map(lambda x: band(x,TA_E,TA_L))
ORDER=[NA]+TA_L
f=df[df.full]
out=io.StringIO()
def P(s=""): out.write(s+"\n"); print(s)

# ---- Aalen-Johansen: cumulative incidence of innstilling at 730 d, competing risk = ordinary closure
def aalen_johansen(sub, horizon=730, asof=pd.Timestamp("2026-08-24")):
    """sub: rows with opened, innstilt, avsluttet. Event1=innstilt, Event2=ordinary closure, censor at min(horizon, asof-opened)."""
    t=[];ev=[]
    for _,r in sub.iterrows():
        cens=min(horizon,(asof-r.opened).days)
        t1=r.d_innstilt; t2=r.d_avsluttet
        # competing: innstilt wins if present
        if pd.notna(t1) and t1<=cens: t.append(t1); ev.append(1)
        elif pd.notna(t2) and t2<=cens and (pd.isna(t1) or t1>cens): t.append(t2); ev.append(2)
        else: t.append(cens); ev.append(0)
    t=np.array(t,float); ev=np.array(ev,int)
    order=np.argsort(t); t=t[order]; ev=ev[order]
    n=len(t); at_risk=n; S=1.0; ci1=0.0
    ut=np.unique(t)
    for tt in ut:
        m=(t==tt); d1=int(((ev==1)&m).sum()); d2=int(((ev==2)&m).sum()); d0=int(((ev==0)&m).sum())
        if at_risk<=0: break
        if d1>0: ci1 += S*(d1/at_risk)
        S *= (1-(d1+d2)/at_risk)
        at_risk -= (d1+d2+d0)
    return ci1, n

P("## V-B2 — INDEPENDENT RECOMPUTATION: balance-sheet size vs innstilling")
P()
P("| Sum eiendeler (hele NOK) | n (full-vindu) | Innstilt ≤730 d | Wilson 95 % | Ord. avsl ≤730 d | Åpen d730 | Aalen–Johansen 730 d (alle 5 165) | as-of innstilt (alle 5 165) |")
P("|---|---:|---|---|---|---|---|---|")
for lv in ORDER:
    b=f[f.ta_band==lv]; a=df[df.ta_band==lv]
    if len(b)==0: continue
    k=int(b.y730.sum()); lo,hi=wilson(k,len(b))
    aj,naj=aalen_johansen(a)
    ka=int(a.y_asof.sum())
    P(f"| {lv} | {len(b)} | {k} / {len(b)} = {100*k/len(b):.1f} % | {100*lo:.1f}–{100*hi:.1f} | {100*b.avsl730.mean():.1f} % | {100*b.open730.mean():.1f} % | {100*aj:.1f} % (n={naj}) | {ka} / {len(a)} = {100*ka/len(a):.1f} % |")
k=int(f.y730.sum()); lo,hi=wilson(k,len(f)); aj,naj=aalen_johansen(df); ka=int(df.y_asof.sum())
P(f"| **Alle** | {len(f)} | {k} / {len(f)} = {100*k/len(f):.1f} % | {100*lo:.1f}–{100*hi:.1f} | {100*f.avsl730.mean():.1f} % | {100*f.open730.mean():.1f} % | {100*aj:.1f} % (n={naj}) | {ka} / {len(df)} = {100*ka/len(df):.1f} % |")
P()
# univariate AUC of total_assets (full-window), no-account excluded and included as lowest
def auc(y,s):
    y=np.asarray(y); s=np.asarray(s,float)
    r=pd.Series(s).rank().values
    n1=y.sum(); n0=len(y)-n1
    return (r[y==1].sum()-n1*(n1+1)/2)/(n1*n0)
g=f[f.total_assets.notna()]
P(f"Univariat AUC, log(1+sum eiendeler), kun estates med balanse (n={len(g)}): {auc(g.y730.values, np.log1p(g.total_assets.clip(lower=0))):.3f}")
s=f.total_assets.fillna(-1).clip(lower=-1)
P(f"Univariat AUC, sum eiendeler med «ingen regnskap» som laveste verdi (n={len(f)}): {auc(f.y730.values, s.rank(ascending=True)):.3f}  (retning: lav = innstilt)")
P(f"  -> AUC for «stor balanse => ikke innstilt» = {1-auc(f.y730.values, s.rank(ascending=True)):.3f}")
P()
# median days to innstilling per band
P("| Band | median dager til innstilling (innstilte, full-vindu) | n |")
P("|---|---:|---:|")
for lv in ORDER:
    b=f[(f.ta_band==lv)&(f.y730==1)]
    if len(b)==0: continue
    P(f"| {lv} | {b.d_innstilt.median():.0f} | {len(b)} |")
open(H+"V-B2-11-bands.md","w",encoding="utf-8").write(out.getvalue())
