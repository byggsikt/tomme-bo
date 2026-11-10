# V-B3: the decisive sensitivity -- does "revenue absorbs the construction gap" survive
# dropping the two non-comparable cells (no accounts, revenue missing), which carry 17,2 % of the
# standardisation weight but only 111 of 934 construction estates?
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
exec(open(os.path.join(HERE,"V-B3-03-lib.py"),encoding="utf-8").read())
df = load(); S = df[df.full730].copy()
T={}
CC = S[S.operating_revenue.notna()].copy()          # complete cases on revenue
T["komplett_sak"] = dict(n=len(CC), bygg=int(CC.bygg.sum()), ovrige=int((~CC.bygg).sum()))
T["raa_i_komplett_sak"] = prop_row("innstilt 730 d, komplette saker",
    CC[CC.bygg].innstilt730.sum(), int(CC.bygg.sum()), CC[~CC.bygg].innstilt730.sum(), int((~CC.bygg).sum()))
v,orate,tab = standardise(CC,"band_rev")
T["std_rev_komplett"] = dict(bygg_std=round(100*v,1), ovrige=round(100*orate,1), diff=round(100*(v-orate),1),
                             mh_or=round(mh_or([(a,n1-a,c,n2-c) for a,n1,c,n2 in tab]),3))
v,orate,tab = standardise(CC,"band_ta")
T["std_storrelse_komplett"] = dict(bygg_std=round(100*v,1), ovrige=round(100*orate,1), diff=round(100*(v-orate),1),
                                   mh_or=round(mh_or([(a,n1-a,c,n2-c) for a,n1,c,n2 in tab]),3))
# finer revenue strata (deciles of the pooled distribution) -- does the null survive finer control?
for nq in (6,10,20):
    C2=CC.copy(); C2["q"]=pd.qcut(C2.operating_revenue.rank(method="first"), nq, labels=False).astype(str)
    v,orate,tab = standardise(C2,"q")
    T[f"std_rev_{nq}_kvantiler"]=dict(bygg_std=round(100*v,1), ovrige=round(100*orate,1),
        diff=round(100*(v-orate),1), mh_or=round(mh_or([(a,n1-a,c,n2-c) for a,n1,c,n2 in tab]),3))
# logistic, complete cases, revenue as a smooth function
CC["lr"]=np.log10(CC.operating_revenue.clip(lower=1e3)); CC["lr2"]=CC.lr**2; CC["lr3"]=CC.lr**3
X,_=design(CC,[],["lr","lr2","lr3"]); y=CC.innstilt730.astype(float).values
b,c=logit_fit(X,y); se=math.sqrt(c[1,1])
T["logistisk_komplett_kubisk_logrev"]=dict(OR=round(math.exp(b[1]),3),
    lo=round(math.exp(b[1]-1.96*se),3), hi=round(math.exp(b[1]+1.96*se),3), RD_pp=round(100*marginal_rd(X,y,b),1))
# and with size + court on top
CC["size7"]=CC.band_ta7.map({"<0,5":"0 <0,5","ingen regnskap":"1 ingen","=0":"2 =0","0,5-1":"3 0,5-1","1-5":"4 1-5","5-20":"5 5-20",">=20":"6 >=20"})
CC["court"]=np.where(CC.tingrett.eq("OSLO TINGRETT"),"a OSLO","z"+CC.tingrett.fillna("UKJENT"))
CC["oppb"]=CC.oppbud.astype(int)
X,_=design(CC,["size7","oppb","court"],["lr","lr2","lr3"]); b,c=logit_fit(X,y); se=math.sqrt(c[1,1])
T["logistisk_komplett_full"]=dict(OR=round(math.exp(b[1]),3), lo=round(math.exp(b[1]-1.96*se),3),
    hi=round(math.exp(b[1]+1.96*se),3), RD_pp=round(100*marginal_rd(X,y,b),1))
# how much weight sits in the two non-comparable cells, and how few bygg estates carry it
w=S[~S.bygg].band_rev.value_counts(normalize=True)
T["vekt_i_ikke_sammenliknbare_celler"]=dict(
    andel_vekt=round(100*float(w.get("ingen regnskap",0)+w.get("mangler",0)),1),
    bygg_n=int(((S.bygg)&(S.band_rev.isin(["ingen regnskap","mangler"]))).sum()),
    ovrige_n=int(((~S.bygg)&(S.band_rev.isin(["ingen regnskap","mangler"]))).sum()))
json.dump(T, open(os.path.join(DIR,"V-B3-13-rev-sensitivitet.json"),"w",encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(T, indent=1, ensure_ascii=False))
