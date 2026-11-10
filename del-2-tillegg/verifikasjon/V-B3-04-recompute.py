# V-B3: independent recomputation of every headline, balance-sheet and stratified number in B3.
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"V-B3-03-lib.py"),encoding="utf-8").read())

df = load()
R = {}
B = df[df.bygg]; O = df[~df.bygg]
S = df[df.full730]; SB = S[S.bygg]; SO = S[~S.bygg]

# ---------- 1. population + headline ----------
R["populasjon"] = dict(N=len(df), innstilt=int(df.innstilt_flag.sum()),
                       avsluttet=int(df.utfall.eq("avsluttet").sum()), aapen=int(df.utfall.eq("aapen").sum()),
                       bygg=int(df.bygg.sum()), ovrige=int((~df.bygg).sum()),
                       bygg_F=int((df.bygg_F==1).sum()), uklass=int(df.nace.isna().sum()),
                       full730=int(df.full730.sum()), innstilt730=int(S.innstilt730.sum()),
                       har_regnskap=int(df.har_regnskap.sum()),
                       ingen_regnskap_i_det_hele=int((df.n_acc_any==0).sum()),
                       bare_regnskap_fra_apningsaret=int(((df.n_acc_any>0)&(~df.har_regnskap)).sum()),
                       oppbud=int(df.oppbud.sum()), rettskretser=int(df.tingrett.nunique()))

hd = []
hd.append(prop_row("Innstilt as-of", B.innstilt_flag.sum(), len(B), O.innstilt_flag.sum(), len(O)))
hd.append(prop_row("Innstilt innen 730 d", SB.innstilt730.sum(), len(SB), SO.innstilt730.sum(), len(SO)))
hd.append(prop_row("Fortsatt åpen as-of", B.utfall.eq("aapen").sum(), len(B), O.utfall.eq("aapen").sum(), len(O)))
Oex = O[O.nace.notna()]; SOex = SO[SO.nace.notna()]
hd.append(prop_row("Innstilt as-of, øvrige ekskl. 155", B.innstilt_flag.sum(), len(B), Oex.innstilt_flag.sum(), len(Oex)))
hd.append(prop_row("Innstilt 730 d, øvrige ekskl. 155", SB.innstilt730.sum(), len(SB), SOex.innstilt730.sum(), len(SOex)))
# område F as the tag
BF = df[df.bygg_F==1]; OF = df[df.bygg_F!=1]
hd.append(prop_row("Område F as-of", BF.innstilt_flag.sum(), len(BF), OF.innstilt_flag.sum(), len(OF)))
R["headline"] = hd

# Aalen-Johansen
aj = {}
for nm, d in [("bygg",B),("ovrige",O),("alle",df),("ovrige_ex155",Oex)]:
    c = aj_cif(d.t.values, d.ev.values, 730)
    lo,hi = aj_boot(d.t.values, d.ev.values, 730, B=400)
    aj[nm] = dict(cif730=round(100*c,2), lo=round(100*lo,2), hi=round(100*hi,2))
R["aj"] = aj

# ---------- 2. accounts / balance sheet ----------
def med(x):
    x=pd.Series(x).dropna()
    return float(x.median()) if len(x) else float("nan")
def q(x,p):
    x=pd.Series(x).dropna()
    return float(x.quantile(p)) if len(x) else float("nan")

Bacc = B[B.har_regnskap]; Oacc = O[O.har_regnskap]
U = df[df.nace.isna()]; Uacc = U[U.har_regnskap]
acc = {}
acc["har_regnskap"] = prop_row("Har regnskap", len(Bacc), len(B), len(Oacc), len(O))
acc["har_regnskap_p"] = float(stats.chi2_contingency([[len(Bacc),len(B)-len(Bacc)],[len(Oacc),len(O)-len(Oacc)]])[1])
acc["ta_null"] = prop_row("Sum eiendeler = 0", (Bacc.total_assets==0).sum(), len(Bacc), (Oacc.total_assets==0).sum(), len(Oacc))
acc["ta_median_MNOK"] = dict(bygg=round(med(Bacc.total_assets)/1e6,3), ovrige=round(med(Oacc.total_assets)/1e6,3),
                             uklass=round(med(Uacc.total_assets)/1e6,3),
                             bygg_iqr=[round(q(Bacc.total_assets,.25)/1e6,2), round(q(Bacc.total_assets,.75)/1e6,2)],
                             ovrige_iqr=[round(q(Oacc.total_assets,.25)/1e6,2), round(q(Oacc.total_assets,.75)/1e6,2)],
                             p=float(stats.mannwhitneyu(Bacc.total_assets.dropna(), Oacc.total_assets.dropna())[1]))
acc["ta_ge5_av_alle"] = prop_row("Sum eiendeler >= 5 MNOK (av alle)", (B.total_assets>=5e6).sum(), len(B), (O.total_assets>=5e6).sum(), len(O))
acc["ta_ge5_p"] = float(stats.chi2_contingency([[int((B.total_assets>=5e6).sum()), len(B)-int((B.total_assets>=5e6).sum())],
                                                [int((O.total_assets>=5e6).sum()), len(O)-int((O.total_assets>=5e6).sum())]])[1])
acc["ta_ge1_av_alle"] = prop_row("Sum eiendeler >= 1 MNOK (av alle)", (B.total_assets>=1e6).sum(), len(B), (O.total_assets>=1e6).sum(), len(O))
acc["ta_ge20_av_alle"] = prop_row("Sum eiendeler >= 20 MNOK (av alle)", (B.total_assets>=20e6).sum(), len(B), (O.total_assets>=20e6).sum(), len(O))
acc["ta_lt05_av_alle"] = prop_row("Sum eiendeler < 0,5 MNOK (av alle m/regnskap-band)", (B.band_ta7=="<0,5").sum(), len(B), (O.band_ta7=="<0,5").sum(), len(O))

# composition
for d in (df,):
    d["om_andel"] = d.current_assets/d.total_assets
    d["anlegg"]   = d.total_assets - d.current_assets
    d["ek_andel"] = d.equity/d.total_assets
B = df[df.bygg]; O = df[~df.bygg]; Bacc=B[B.har_regnskap]; Oacc=O[O.har_regnskap]
U = df[df.nace.isna()]; Uacc=U[U.har_regnskap]
Bpos = Bacc[Bacc.total_assets>0]; Opos = Oacc[Oacc.total_assets>0]; Upos = Uacc[Uacc.total_assets>0]
acc["om_median"] = dict(bygg=round(med(Bacc.current_assets)/1e6,3), ovrige=round(med(Oacc.current_assets)/1e6,3),
                        p=float(stats.mannwhitneyu(Bacc.current_assets.dropna(),Oacc.current_assets.dropna())[1]))
acc["anlegg_median"] = dict(bygg=round(med(Bacc.anlegg)/1e6,3), ovrige=round(med(Oacc.anlegg)/1e6,3),
                        p=float(stats.mannwhitneyu(Bacc.anlegg.dropna(),Oacc.anlegg.dropna())[1]))
acc["om_andel_median"] = dict(bygg=round(med(Bpos.om_andel),3), ovrige=round(med(Opos.om_andel),3),
                              uklass=round(med(Upos.om_andel),3), n_bygg=len(Bpos), n_ovrige=len(Opos),
                              bygg_iqr=[round(q(Bpos.om_andel,.25),2),round(q(Bpos.om_andel,.75),2)],
                              ovrige_iqr=[round(q(Opos.om_andel,.25),2),round(q(Opos.om_andel,.75),2)],
                              p=float(stats.mannwhitneyu(Bpos.om_andel.dropna(),Opos.om_andel.dropna())[1]))
b_an = (Bpos.anlegg/Bpos.total_assets)>0.25; o_an = (Opos.anlegg/Opos.total_assets)>0.25
acc["anleggsandel_over25"] = prop_row("Anleggsmiddelandel > 25 %", b_an.sum(), len(Bpos), o_an.sum(), len(Opos))
acc["anleggsandel_over25_p"] = float(stats.chi2_contingency([[int(b_an.sum()), len(Bpos)-int(b_an.sum())],
                                                             [int(o_an.sum()), len(Opos)-int(o_an.sum())]])[1])
acc["anleggsandel_over25_uklass_pct"] = round(100*float(((Upos.anlegg/Upos.total_assets)>0.25).mean()),1)
acc["neg_ek"] = prop_row("Negativ egenkapital", (Bacc.equity<0).sum(), len(Bacc), (Oacc.equity<0).sum(), len(Oacc))
acc["neg_ek_p"] = float(stats.chi2_contingency([[int((Bacc.equity<0).sum()), len(Bacc)-int((Bacc.equity<0).sum())],
                                                [int((Oacc.equity<0).sum()), len(Oacc)-int((Oacc.equity<0).sum())]])[1])
acc["ek_andel_median"] = dict(bygg=round(med(Bpos.ek_andel),3), ovrige=round(med(Opos.ek_andel),3))
Brev = Bacc[Bacc.operating_revenue.notna()]; Orev = Oacc[Oacc.operating_revenue.notna()]; Urev=Uacc[Uacc.operating_revenue.notna()]
acc["rev_median_MNOK"] = dict(bygg=round(med(Brev.operating_revenue)/1e6,3), ovrige=round(med(Orev.operating_revenue)/1e6,3),
                              uklass=round(med(Urev.operating_revenue)/1e6,3), n_bygg=len(Brev), n_ovrige=len(Orev),
                              bygg_iqr=[round(q(Brev.operating_revenue,.25)/1e6,2),round(q(Brev.operating_revenue,.75)/1e6,2)],
                              ovrige_iqr=[round(q(Orev.operating_revenue,.25)/1e6,2),round(q(Orev.operating_revenue,.75)/1e6,2)],
                              p=float(stats.mannwhitneyu(Brev.operating_revenue,Orev.operating_revenue)[1]))
acc["rev_ge5_av_alle"] = prop_row("Driftsinntekter >= 5 MNOK (av alle)", (B.operating_revenue>=5e6).sum(), len(B), (O.operating_revenue>=5e6).sum(), len(O))
acc["rev_ge5_p"] = float(stats.chi2_contingency([[int((B.operating_revenue>=5e6).sum()), len(B)-int((B.operating_revenue>=5e6).sum())],
                                                 [int((O.operating_revenue>=5e6).sum()), len(O)-int((O.operating_revenue>=5e6).sum())]])[1])
acc["gjeld_median_MNOK"] = dict(bygg=round(med(Bacc.liabilities)/1e6,3), ovrige=round(med(Oacc.liabilities)/1e6,3),
                                p=float(stats.mannwhitneyu(Bacc.liabilities.dropna(),Oacc.liabilities.dropna())[1]))
acc["rev_per_ta_median"] = dict(bygg=round(med((Bpos.operating_revenue/Bpos.total_assets).dropna()),2),
                                ovrige=round(med((Opos.operating_revenue/Opos.total_assets).dropna()),2))
acc["gap1ar"] = prop_row("Regnskapsår = åpningsår - 1", (Bacc.gap_ar==1).sum(), len(Bacc), (Oacc.gap_ar==1).sum(), len(Oacc))
acc["oppbud"] = prop_row("Oppbud", B.oppbud.sum(), len(B), O.oppbud.sum(), len(O))
acc["oppbud_p"] = float(stats.chi2_contingency([[int(B.oppbud.sum()), len(B)-int(B.oppbud.sum())],
                                                [int(O.oppbud.sum()), len(O)-int(O.oppbud.sum())]])[1])
acc["oppbud_uklass_pct"] = round(100*float(U.oppbud.mean()),1)
Bal = B[B.alder_ar.notna()]; Oal = O[O.alder_ar.notna()]
acc["alder_median"] = dict(bygg=round(med(Bal.alder_ar),2), ovrige=round(med(Oal.alder_ar),2), n_bygg=len(Bal), n_ovrige=len(Oal),
                           p=float(stats.mannwhitneyu(Bal.alder_ar,Oal.alder_ar)[1]))
acc["alder_under3"] = prop_row("Alder < 3 år", (Bal.alder_ar<3).sum(), len(Bal), (Oal.alder_ar<3).sum(), len(Oal))
acc["alder_under3_p"] = float(stats.chi2_contingency([[int((Bal.alder_ar<3).sum()), len(Bal)-int((Bal.alder_ar<3).sum())],
                                                      [int((Oal.alder_ar<3).sum()), len(Oal)-int((Oal.alder_ar<3).sum())]])[1])
acc["rev_mangler"] = prop_row("Driftsinntekter mangler i regnskapet (av alle)", (B.band_rev=="mangler").sum(), len(B), (O.band_rev=="mangler").sum(), len(O))
R["regnskap"] = acc

# size distribution per group (7 bands)
R["stbaand_fordeling"] = {k: dict(bygg=round(100*float((B.band_ta7==k).mean()),1), ovrige=round(100*float((O.band_ta7==k).mean()),1))
                          for k in ["ingen regnskap","=0","<0,5","0,5-1","1-5","5-20",">=20"]}
R["fiscal_year_fordeling"] = {int(k):int(v) for k,v in df.fiscal_year.value_counts().sort_index().items()}
R["gap_fordeling_pct"] = dict(ett_ar=round(100*float((df[df.har_regnskap].gap_ar==1).mean()),1),
                              to_pluss=round(100*float((df[df.har_regnskap].gap_ar>=2).mean()),1))

# ---------- 3. stratified, fixed 730-day window ----------
def strat_table(strat, order=None, d=None, outcome="innstilt730"):
    d = S if d is None else d
    rows=[]
    keys = order if order else sorted(d[strat].astype(str).unique())
    for k in keys:
        sub=d[d[strat].astype(str)==k]
        b=sub[sub.bygg]; o=sub[~sub.bygg]
        if len(b)==0 or len(o)==0: continue
        r = prop_row(k, b[outcome].sum(), len(b), o[outcome].sum(), len(o))
        r["aj_bygg"]=round(100*aj_cif(b.t.values,b.ev.values,730),1)
        r["aj_ovrige"]=round(100*aj_cif(o.t.values,o.ev.values,730),1)
        rows.append(r)
    return rows

R["strat_ta"]  = strat_table("band_ta", ["ingen regnskap","<1 MNOK","1-5 MNOK",">=5 MNOK"])
R["strat_ta7"] = strat_table("band_ta7", ["ingen regnskap","=0","<0,5","0,5-1","1-5","5-20",">=20"])
R["strat_rev"] = strat_table("band_rev", ["ingen regnskap","mangler","<1 MNOK","1-5 MNOK","5-20 MNOK",">=20 MNOK"])
S2=S.copy(); S2["grunnlag"]=np.where(S2.oppbud,"oppbud","begjæring")
R["strat_oppbud"] = strat_table("grunnlag", ["oppbud","begjæring"], d=S2)
S2["harreg"]=np.where(S2.har_regnskap,"regnskap","ingen regnskap")
R["strat_regnskap"] = strat_table("harreg", ["regnskap","ingen regnskap"], d=S2)
S2["gapb"]=np.where(~S2.har_regnskap,"ingen", np.where(S2.gap_ar==1,"1 år","2+ år"))
R["strat_gap"] = strat_table("gapb", ["1 år","2+ år"], d=S2)
R["strat_court"] = strat_table("tingrett", d=S)

# standardisation + MH OR
std = {}
for nm, strat, d in [("storrelse4","band_ta",S), ("storrelse7","band_ta7",S), ("driftsinntekt","band_rev",S),
                     ("rettskrets","tingrett",S), ("oppbud","grunnlag",S2), ("gap","gapb",S2)]:
    v,orate,tab = standardise(d, strat)
    std[nm]=dict(bygg_standardisert=round(100*v,1), ovrige=round(100*orate,1),
                 diff_pp=round(100*(v-orate),1), mh_or=round(mh_or([(a,n1-a,c,n2-c) for a,n1,c,n2 in tab]),3))
crude_or = mh_or([(int(SB.innstilt730.sum()), len(SB)-int(SB.innstilt730.sum()),
                   int(SO.innstilt730.sum()), len(SO)-int(SO.innstilt730.sum()))])
std["raa_or"]=round(crude_or,3)
R["standardisering"]=std

# ---------- 4. immaturity landmark ----------
def landmark(L):
    d = df[(ASOF-df.opened).dt.days >= L]
    open_at_L = d[((d.innstilt.isna()) | ((d.innstilt-d.opened).dt.days > L)) &
                  ((d.avsluttet.isna()) | ((d.avsluttet-d.opened).dt.days > L))]
    b=open_at_L[open_at_L.bygg]; o=open_at_L[~open_at_L.bygg]
    return dict(L=L, n_bygg=len(b), n_ovrige=len(o),
                **prop_row(f"§135 eventually, open at day {L}", b.innstilt_flag.sum(), len(b), o.innstilt_flag.sum(), len(o)),
                ord_bygg=round(100*float(b.utfall.eq("avsluttet").mean()),1),
                ord_ovrige=round(100*float(o.utfall.eq("avsluttet").mean()),1))
R["landmark"]=[landmark(365), landmark(730)]
# worst case
wc_b = int(B.innstilt_flag.sum()+B.utfall.eq("aapen").sum()); wc_o=int(O.innstilt_flag.sum())
R["verste_tilfelle"]=prop_row("Verste tilfelle", wc_b, len(B), wc_o, len(O))

# ---------- 5. the 155 ----------
R["uklass"]=dict(n=len(U), innstilt=int(U.innstilt_flag.sum()), pct=round(pct(U.innstilt_flag.sum(),len(U)),1),
                 har_regnskap=int(U.har_regnskap.sum()),
                 med_ta_MNOK=round(med(Uacc.total_assets)/1e6,3), med_rev_MNOK=round(med(Urev.operating_revenue)/1e6,3),
                 rev_ge5_pct=round(100*float((U.operating_revenue>=5e6).mean()),1),
                 ta_zero_pct=round(100*float((Uacc.total_assets==0).mean()),1),
                 etiketter=U.bransje.value_counts().head(6).to_dict())
aj_ex = aj_cif(Oex.t.values, Oex.ev.values, 730)
R["aj_ovrige_ex155"]=round(100*aj_ex,1)

json.dump(R, open(os.path.join(DIR,"V-B3-04-results.json"),"w",encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
print(json.dumps(R, indent=1, ensure_ascii=False, default=str))
