# V-B3: the light (non-bootstrap) parts of the final check.
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
exec(open(os.path.join(HERE,"V-B3-03-lib.py"),encoding="utf-8").read())
df = load()
df["gapc"] = np.where(~df.har_regnskap,"0 1aar", np.where(df.gap_ar<=1,"0 1aar","1 2plus"))
df["agec"] = np.where(df.alder_ar.isna(),"3 ukjent", np.where(df.alder_ar<3,"1 <3", np.where(df.alder_ar<10,"0 3-10","2 >=10")))
df["size7"]= df.band_ta7.map({"<0,5":"0 <0,5","ingen regnskap":"1 ingen","=0":"2 =0","0,5-1":"3 0,5-1","1-5":"4 1-5","5-20":"5 5-20",">=20":"6 >=20"})
df["revb"] = df.band_rev.map({"<1 MNOK":"0 <1","ingen regnskap":"1 ingen","mangler":"2 mangler","1-5 MNOK":"3 1-5","5-20 MNOK":"4 5-20",">=20 MNOK":"5 >=20"})
df["court"]= np.where(df.tingrett.eq("OSLO TINGRETT"),"a OSLO","z"+df.tingrett.fillna("UKJENT"))
df["oppb"] = df.oppbud.astype(int); df["hasacc"]=df.har_regnskap.astype(int)
S = df[df.full730].copy(); y=S.innstilt730.astype(float).values
T={}
def lr_terms(d, base_cats, inter_col, drop_levels=()):
    X0,_=design(d,base_cats); yv=d["innstilt730"].astype(float).values
    b0,_=logit_fit(X0,yv); ll0=loglik(X0,yv,b0)
    lv=[l for l in sorted(d[inter_col].astype(str).unique())[1:] if l not in drop_levels]
    ex=[((d[inter_col].astype(str)==l).astype(float).values*d.bygg.astype(float).values) for l in lv]
    X1=np.column_stack([X0]+ex); b1,_=logit_fit(X1,yv); ll1=loglik(X1,yv,b1)
    st=2*(ll1-ll0); return dict(chi2=round(st,3), df=len(lv), p=round(float(1-stats.chi2.cdf(st,len(lv))),3), ledd=lv)
base7=["size7","oppb","gapc","agec","court","revb"]
T["inter_rev_df5"]=lr_terms(S,base7,"revb")
T["inter_rev_df4_uten_ingen_regnskap"]=lr_terms(S,base7,"revb",drop_levels=("1 ingen",))
Sp=S[S.har_regnskap & (S.total_assets>0)].copy(); Sp["ca_share"]=Sp.current_assets/Sp.total_assets
Sp["tert"]=pd.qcut(Sp.ca_share,3,labels=["lav","middels","hoy"])
T["ca_tertiler"]={str(k): dict(bygg=round(100*float(g[g.bygg].innstilt730.mean()),1), n_b=int(g.bygg.sum()),
                               ovrige=round(100*float(g[~g.bygg].innstilt730.mean()),1), n_o=int((~g.bygg).sum()))
                  for k,g in Sp.groupby("tert", observed=True)}
Sp["ek_andel"]=(Sp.equity/Sp.total_assets).clip(-5,5)
Xa,_=design(Sp,["size7","oppb","gapc","agec","court"]); ya=Sp.innstilt730.astype(float).values
ba,_=logit_fit(Xa,ya); Xb=np.column_stack([Xa, Sp.ca_share.values, Sp.ek_andel.values]); bb,_=logit_fit(Xb,ya)
T["sammensetning_logOR"]=dict(n=len(Sp), M5_OR=round(math.exp(ba[1]),3), M5_pluss_OR=round(math.exp(bb[1]),3), B3=[0.713,0.743])
rows=[]
for k in ["ingen regnskap","mangler","<1 MNOK","1-5 MNOK","5-20 MNOK",">=20 MNOK"]:
    sub=df[df.band_rev==k]; b=sub[sub.bygg]; o=sub[~sub.bygg]
    rows.append(dict(band=k, bygg=f"{len(b)} ({round(100*len(b)/1280,1)} %)", ovrige=f"{len(o)} ({round(100*len(o)/3885,1)} %)",
                     bygg_asof=f"{int(b.innstilt_flag.sum())}/{len(b)}={round(100*float(b.innstilt_flag.mean()),1)}",
                     ovrige_asof=f"{int(o.innstilt_flag.sum())}/{len(o)}={round(100*float(o.innstilt_flag.mean()),1)}"))
T["rev_asof"]=rows
noev=S[~(((S.ev==1)|(S.ev==2))&(S.t<=730))]
T["uten_hendelse_innen_730"]=prop_row("uten hendelse innen 730 d", int(noev.bygg.sum()), int(S.bygg.sum()),
                                      int((~noev.bygg).sum()), int((~S.bygg).sum()))
T["rev_null_rapportert"]=dict(bygg=int((df[df.bygg].operating_revenue==0).sum()), ovrige=int((df[~df.bygg].operating_revenue==0).sum()), B3=[22,177])
m=df.operating_revenue.notna()&df.total_assets.notna()
T["spearman_rev_ta"]=round(float(stats.spearmanr(df.loc[m,"operating_revenue"], df.loc[m,"total_assets"])[0]),2)
T["rev_per_ta_median"]=dict(bygg=round(float((df[(df.bygg)&(df.total_assets>0)].operating_revenue/df[(df.bygg)&(df.total_assets>0)].total_assets).median()),2),
                            ovrige=round(float((df[(~df.bygg)&(df.total_assets>0)].operating_revenue/df[(~df.bygg)&(df.total_assets>0)].total_assets).median()),2), B3=[3.47,2.48])
json.dump(T, open(os.path.join(DIR,"V-B3-09-lett.json"),"w",encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
print(json.dumps(T, indent=1, ensure_ascii=False, default=str))
