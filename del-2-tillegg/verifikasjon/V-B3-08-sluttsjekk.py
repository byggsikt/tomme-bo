# V-B3: remaining checks — bootstrap stability of the marginal RD, composition/U-shape,
# as-of revenue strata, open-without-event shares, and the interaction df question.
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
exec(open(os.path.join(HERE,"V-B3-03-lib.py"),encoding="utf-8").read())
df = load()
va = pd.read_csv(os.path.join(DIR,"V-B3-02b-varsel.txt"), sep="|", header=None, names=["orgnr","n_varsel_for"], dtype={"orgnr":str})
df = df.merge(va, on="orgnr", how="left", validate="1:1"); df["varsel"]=(df.n_varsel_for>0).astype(int)
df["gapc"] = np.where(~df.har_regnskap,"0 1aar", np.where(df.gap_ar<=1,"0 1aar","1 2plus"))
df["agec"] = np.where(df.alder_ar.isna(),"3 ukjent", np.where(df.alder_ar<3,"1 <3", np.where(df.alder_ar<10,"0 3-10","2 >=10")))
df["size7"]= df.band_ta7.map({"<0,5":"0 <0,5","ingen regnskap":"1 ingen","=0":"2 =0","0,5-1":"3 0,5-1","1-5":"4 1-5","5-20":"5 5-20",">=20":"6 >=20"})
df["revb"] = df.band_rev.map({"<1 MNOK":"0 <1","ingen regnskap":"1 ingen","mangler":"2 mangler","1-5 MNOK":"3 1-5","5-20 MNOK":"4 5-20",">=20 MNOK":"5 >=20"})
df["court"]= np.where(df.tingrett.eq("OSLO TINGRETT"),"a OSLO","z"+df.tingrett.fillna("UKJENT"))
df["oppb"] = df.oppbud.astype(int); df["hasacc"]=df.har_regnskap.astype(int)
S = df[df.full730].copy()
T={}

# --- (A) bootstrap stability of the M0 marginal RD, which has a closed form
X,_=design(S,[]); y=S.innstilt730.astype(float).values
beta,_=logit_fit(X,y); rd0=marginal_rd(X,y,beta)
kb=int(S[S.bygg].innstilt730.sum()); nb=int(S.bygg.sum()); ko=int(S[~S.bygg].innstilt730.sum()); no=int((~S.bygg).sum())
nc=newcombe(kb,nb,ko,no)
def boot_rd(X,y,B,seed):
    rng=np.random.default_rng(seed); n=len(y); out=[]
    for _ in range(B):
        i=rng.integers(0,n,n); b,_=logit_fit(X[i],y[i]); out.append(marginal_rd(X[i],y[i],b))
    return round(100*float(np.percentile(out,2.5)),1), round(100*float(np.percentile(out,97.5)),1)
T["M0_RD_stabilitet"]=dict(punkt=round(100*rd0,1), newcombe=[round(100*nc[0],1),round(100*nc[1],1)],
    boot_B150=[boot_rd(X,y,150,s) for s in (1,2,3)], boot_B300=[boot_rd(X,y,300,s) for s in (11,12,13)],
    boot_B4000=list(boot_rd(X,y,4000,99)),
    B3_hovedrapport=[-8.9,-2.6], B3_07_fil=[-9.8,-2.7])

# --- (B) M7 marginal RD with a large bootstrap
X7,n7=design(S,["size7","oppb","gapc","agec","court","revb"])
b7,_=logit_fit(X7,y); rd7=marginal_rd(X7,y,b7)
T["M7_RD"]=dict(punkt=round(100*rd7,1), boot_B800=list(boot_rd(X7,y,800,2026)), B3=[-5.8,0.9])
# bygg + revb only
Xr,_=design(S,["revb"]); br,_=logit_fit(Xr,y)
T["Mrev_RD"]=dict(punkt=round(100*marginal_rd(Xr,y,br),1), boot_B800=list(boot_rd(Xr,y,800,2027)), B3=[-3.3,2.1])

# --- (C) interaction df question: bygg x revband with and without the collinear "ingen regnskap" term
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

# --- (D) composition: current-asset-share tertiles and the "12 % of the log-OR" claim
Sp=S[S.har_regnskap & (S.total_assets>0)].copy()
Sp["ca_share"]=Sp.current_assets/Sp.total_assets
Sp["tert"]=pd.qcut(Sp.ca_share,3,labels=["lav","middels","hoy"])
T["ca_tertiler"]={str(k): dict(bygg=round(100*float(g[g.bygg].innstilt730.mean()),1), n_b=int(g.bygg.sum()),
                               ovrige=round(100*float(g[~g.bygg].innstilt730.mean()),1), n_o=int((~g.bygg).sum()))
                  for k,g in Sp.groupby("tert", observed=True)}
Sp["ek_andel"]=Sp.equity/Sp.total_assets
Xa,_=design(Sp,["size7","oppb","gapc","agec","court"]); ya=Sp.innstilt730.astype(float).values
ba,_=logit_fit(Xa,ya)
Xb=np.column_stack([Xa, Sp.ca_share.values, Sp.ek_andel.clip(-5,5).values])
bb,_=logit_fit(Xb,ya)
T["sammensetning_logOR"]=dict(n=len(Sp), M5_OR=round(math.exp(ba[1]),3), M5_pluss_sammensetning_OR=round(math.exp(bb[1]),3),
                              B3=dict(fra=0.713, til=0.743))

# --- (E) as-of revenue strata (B3-07 table) and open-without-event within 730 d
rows=[]
for k in ["ingen regnskap","mangler","<1 MNOK","1-5 MNOK","5-20 MNOK",">=20 MNOK"]:
    sub=df[df.band_rev==k]; b=sub[sub.bygg]; o=sub[~sub.bygg]
    rows.append(dict(band=k, bygg_n=len(b), bygg_andel_av_gruppe=round(100*len(b)/int(df.bygg.sum()),1),
                     ovrige_n=len(o), ovrige_andel=round(100*len(o)/int((~df.bygg).sum()),1),
                     bygg_asof=f"{int(b.innstilt_flag.sum())}/{len(b)} = {round(100*float(b.innstilt_flag.mean()),1)}",
                     ovrige_asof=f"{int(o.innstilt_flag.sum())}/{len(o)} = {round(100*float(o.innstilt_flag.mean()),1)}"))
T["rev_asof"]=rows
noev = S[(S.t>730) | ((S.ev==0))]
noev730 = S[~(((S.ev==1)|(S.ev==2)) & (S.t<=730))]
T["uten_hendelse_innen_730"]=prop_row("uten hendelse innen 730 d",
    int(noev730.bygg.sum()) - int(noev730[noev730.bygg].innstilt730.sum()) if False else int(noev730.bygg.sum()),
    int(S.bygg.sum()), int((~noev730.bygg).sum()), int((~S.bygg).sum()))
T["rev_null_rapportert"]=dict(bygg=int((df[df.bygg].operating_revenue==0).sum()), ovrige=int((df[~df.bygg].operating_revenue==0).sum()),
                              B3=dict(bygg=22, ovrige=177))
T["spearman_rev_ta"]=round(float(stats.spearmanr(df.operating_revenue.dropna(), df.loc[df.operating_revenue.notna(),"total_assets"])[0]),2)

json.dump(T, open(os.path.join(DIR,"V-B3-08-sluttsjekk.json"),"w",encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
print(json.dumps(T, indent=1, ensure_ascii=False, default=str))
