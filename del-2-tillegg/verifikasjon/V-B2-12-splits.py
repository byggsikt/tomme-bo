# -*- coding: utf-8 -*-
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import pandas as pd, numpy as np, math, io
H="../data/"
df=pd.read_pickle(H+"V-B2-core.pkl")
NA="Ingen regnskap"
def wilson(k,n,z=1.959964):
    if n==0: return (float('nan'),float('nan'))
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return ((c-h)/d,(c+h)/d)
def band(x,edges,labels,na=NA):
    if pd.isna(x): return na
    for e,l in zip(edges,labels):
        if x<e: return l
    return labels[-1]
# ---------------- derived
df["ta_band"]=df.total_assets.map(lambda x: band(x,[1e5,5e5,1e6,5e6,2e7,np.inf],["<100 000","100 000–<500 000","500 000–<1 mill.","1–<5 mill.","5–<20 mill.","≥20 mill."]))
df["ta3"]=df.total_assets.map(lambda x: band(x,[1e6,5e6,np.inf],["<1 mill.","1–<5 mill.","≥5 mill."]))
df["rev_band"]=df.apply(lambda r: NA if pd.isna(r.acc_fy) else ("Ikke oppgitt" if pd.isna(r.operating_revenue) else band(r.operating_revenue,[1,1e6,5e6,2e7,np.inf],["0","<1 mill.","1–<5 mill.","5–<20 mill.","≥20 mill."])),axis=1)
df["ek_neg"]=df.equity.notna()&(df.equity<0)
# --- AGE: my own construction. stiftet, else Nyregistrering, else first announcement
df["stift_eff"]=df.stiftet.fillna(df.nyreg)
df["alder"]=(df.opened-df.stift_eff).dt.days/365.25
def aband(x,first_any,opened):
    if pd.isna(x):
        if pd.notna(first_any):
            a=(opened-first_any).days/365.25
            return "≥15 år (fra første kunngjøring)" if a>=15 else f"Ukjent (første kunngj. {a:.0f} år før)"
        return "Ukjent"
    return band(x,[2,5,10,15,np.inf],["<2 år","2–<5 år","5–<10 år","10–<15 år","≥15 år"],"Ukjent")
df["alder_band"]=[aband(x,fa,op) for x,fa,op in zip(df.alder,df.forste_any,df.opened)]
# --- PRIOR WARNING
def vcat(r):
    if r.vt_n==0: return "Ingen varsel"
    if r.vt_regn: return "Varsel, Regnskapsregisteret"
    if r.vt_foretak: return "Varsel, Foretaksregisteret"
    return "Varsel, ukjent register"
df["vt_cat"]=df.apply(vcat,axis=1)
df["vt24_cat"]=df.apply(lambda r:("Ingen varsel siste 24 mnd" if not r.vt_24m else ("Varsel 24m, Regnskapsreg." if r.vt_regn else ("Varsel 24m, Foretaksreg." if r.vt_foretak else "Varsel 24m, ukjent"))),axis=1)
# --- AUDITOR (two definitions, to attack the analyst's)
df["rev_ever"]=df.rev_n>0                       # analyst's definition: any auditor announcement ever before opening
df["rev_36m"]=df.rev_n_36m>0                    # stricter: auditor announcement in the 36 months before opening
df["rev_aktiv"]=(df.rev_n>0)&(df.rev_siste_fratradt!=True)   # last auditor row is not a resignation
# --- accounts filed by the last statutory deadline (my own rule, same law: FY Y due 31 July Y+1)
def levert(r):
    Y=r.opened.year if r.opened.month>=10 else r.opened.year-1   # last FY whose deadline has passed (+2 mo grace)
    st=r.stift_eff
    if pd.notna(st) and st>=pd.Timestamp(Y-1,7,1): return "For ungt"
    return "Levert" if (pd.notna(r.gk_siste) and r.gk_siste>=pd.Timestamp(Y,1,1)) else "Ikke levert"
df["levert"]=df.apply(levert,axis=1)
df["kap_band"]=df.kap_siste_for.map(lambda x: band(x,[30000,30000.01,100000.01,1000000.01,np.inf],["<30 000","30 000 (minimum)","30 001–100 000","100 001–1 mill.",">1 mill."],"Ukjent"))
df["oppbud_lbl"]=df.oppbud.map({True:"Oppbud",False:"Begjæring (kreditor/det offentlige)"})
f=df[df.full]
out=io.StringIO()
def P(s=""): out.write(s+"\n"); print(s)
def tab(var,title,order=None):
    P(f"### {title}"); P()
    P("| Nivå | n (full-vindu) | Innstilt ≤730 d | Wilson 95 % | n (alle 5 165) | as-of innstilt |")
    P("|---|---:|---|---|---:|---|")
    levels=order or sorted(df[var].dropna().unique().tolist())
    for lv in levels:
        b=f[f[var]==lv]; a=df[df[var]==lv]
        if len(a)==0: continue
        if len(b)==0:
            P(f"| {lv} | 0 | – | – | {len(a)} | {int(a.y_asof.sum())} / {len(a)} = {100*a.y_asof.mean():.1f} % |"); continue
        k=int(b.y730.sum()); lo,hi=wilson(k,len(b)); ka=int(a.y_asof.sum())
        P(f"| {lv} | {len(b)} | {k} / {len(b)} = {100*k/len(b):.1f} % | {100*lo:.1f}–{100*hi:.1f} | {len(a)} | {ka} / {len(a)} = {100*ka/len(a):.1f} % |")
    P()
P("## V-B2 — uavhengige univariate splitt (full-vindu-delkohort n=3 772; as-of alle 5 165)"); P()
tab("alder_band","Selskapets alder ved åpning (egen konstruksjon: stiftet → Nyregistrering → første kunngjøring)",
    ["<2 år","2–<5 år","5–<10 år","10–<15 år","≥15 år","≥15 år (fra første kunngjøring)","Ukjent"]+[x for x in df.alder_band.unique() if x.startswith("Ukjent (")])
tab("vt_cat","Varsel om tvangsoppløsning noen gang før åpning",["Ingen varsel","Varsel, Regnskapsregisteret","Varsel, Foretaksregisteret","Varsel, ukjent register"])
tab("vt24_cat","Varsel om tvangsoppløsning siste 24 mnd før åpning",["Ingen varsel siste 24 mnd","Varsel 24m, Regnskapsreg.","Varsel 24m, Foretaksreg.","Varsel 24m, ukjent"])
tab("rev_band","Driftsinntekter i siste balanse",[NA,"Ikke oppgitt","0","<1 mill.","1–<5 mill.","5–<20 mill.","≥20 mill."])
tab("levert","Siste pliktige årsregnskap levert (godkjent kunngjort)",["Levert","Ikke levert","For ungt"])
tab("kap_band","Aksjekapital, sist kunngjort før åpning",["<30 000","30 000 (minimum)","30 001–100 000","100 001–1 mill.",">1 mill.","Ukjent"])
tab("oppbud_lbl","Åpningsgrunnlag",["Oppbud","Begjæring (kreditor/det offentlige)"])
P("### Revisor — tre definisjoner (angrep på analytikerens «Revisor registrert»)"); P()
P("| Definisjon | n (full) | Innstilt ≤730 d | | n uten | Innstilt uten |")
P("|---|---:|---|---|---:|---|")
for nm,col in [("Revisorkunngjøring noen gang før åpning (analytikerens)","rev_ever"),
               ("Revisorkunngjøring siste 36 mnd","rev_36m"),
               ("Siste revisorrad ikke «fratrådt»","rev_aktiv")]:
    a=f[f[col]]; b=f[~f[col]]
    P(f"| {nm} | {len(a)} | {int(a.y730.sum())} / {len(a)} = {100*a.y730.mean():.1f} % | | {len(b)} | {int(b.y730.sum())} / {len(b)} = {100*b.y730.mean():.1f} % |")
P()
P(f"Negativ egenkapital: {int(f[f.ek_neg].y730.sum())} / {len(f[f.ek_neg])} = {100*f[f.ek_neg].y730.mean():.1f} %  |  ikke negativ (m/balanse): "
  f"{int(f[(~f.ek_neg)&f.acc_fy.notna()].y730.sum())} / {len(f[(~f.ek_neg)&f.acc_fy.notna()])} = {100*f[(~f.ek_neg)&f.acc_fy.notna()].y730.mean():.1f} %")
df.to_pickle(H+"V-B2-feat.pkl")
open(H+"V-B2-12-splits.md","w",encoding="utf-8").write(out.getvalue())
