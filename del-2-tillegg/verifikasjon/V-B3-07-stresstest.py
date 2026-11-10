# V-B3: adversarial stress tests of B3's conclusions (no bootstrap, fast).
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
exec(open(os.path.join(HERE,"V-B3-03-lib.py"),encoding="utf-8").read())
df = load()
S = df[df.full730].copy()
T = {}

# --- (1) "smaller share >= 5 MNOK" is sensitive to the denominator (all vs accounts-only)
Bacc=df[(df.bygg)&df.har_regnskap]; Oacc=df[(~df.bygg)&df.har_regnskap]
T["ge5_denominator"] = dict(
  av_alle=prop_row("TA>=5 MNOK / alle", (df[df.bygg].total_assets>=5e6).sum(), int(df.bygg.sum()),
                   (df[~df.bygg].total_assets>=5e6).sum(), int((~df.bygg).sum())),
  av_med_regnskap=prop_row("TA>=5 MNOK / med regnskap", (Bacc.total_assets>=5e6).sum(), len(Bacc),
                           (Oacc.total_assets>=5e6).sum(), len(Oacc)),
  rev_ge5_av_med_regnskap=prop_row("Rev>=5 MNOK / med regnskap", (Bacc.operating_revenue>=5e6).sum(), len(Bacc),
                           (Oacc.operating_revenue>=5e6).sum(), len(Oacc)))

# --- (2) "advantage persists in EVERY size band": test with 7 bands, both windows
def bands(strat, order, d, outcome):
    r=[]
    for k in order:
        sub=d[d[strat].astype(str)==k]; b=sub[sub.bygg]; o=sub[~sub.bygg]
        if len(b)==0 or len(o)==0: continue
        r.append(prop_row(k, b[outcome].sum(), len(b), o[outcome].sum(), len(o)))
    return r
T["size7_730"]  = bands("band_ta7", ["ingen regnskap","=0","<0,5","0,5-1","1-5","5-20",">=20"], S, "innstilt730")
T["size7_asof"] = bands("band_ta7", ["ingen regnskap","=0","<0,5","0,5-1","1-5","5-20",">=20"], df, "innstilt_flag")
T["size4_asof"] = bands("band_ta",  ["ingen regnskap","<1 MNOK","1-5 MNOK",">=5 MNOK"], df, "innstilt_flag")
T["antall_baand_negativ"] = dict(
  size7_730=sum(1 for r in T["size7_730"] if r["diff_pp"]<0), n7=len(T["size7_730"]),
  size7_asof=sum(1 for r in T["size7_asof"] if r["diff_pp"]<0), n7a=len(T["size7_asof"]))

# --- (3) inventory/WIP sits inside CURRENT assets: is the "stock/unfinished projects" half of the
#         hypothesis actually contradicted? compare current assets in kroner and per band.
Bp=Bacc[Bacc.total_assets>0]; Op=Oacc[Oacc.total_assets>0]
T["omlop_vs_anlegg"] = dict(
  ca_median_MNOK=dict(bygg=round(float(Bacc.current_assets.median())/1e6,3), ovrige=round(float(Oacc.current_assets.median())/1e6,3)),
  fa_median_MNOK=dict(bygg=round(float((Bacc.total_assets-Bacc.current_assets).median())/1e6,3),
                      ovrige=round(float((Oacc.total_assets-Oacc.current_assets).median())/1e6,3)),
  ca_over_1MNOK=prop_row("Omløpsmidler > 1 MNOK (av dem med regnskap)",(Bacc.current_assets>1e6).sum(),len(Bacc),
                         (Oacc.current_assets>1e6).sum(),len(Oacc)),
  fa_over_05MNOK=prop_row("Anleggsmidler > 0,5 MNOK (av dem med regnskap)",((Bacc.total_assets-Bacc.current_assets)>5e5).sum(),len(Bacc),
                         ((Oacc.total_assets-Oacc.current_assets)>5e5).sum(),len(Oacc)),
  merk="annual_account har ingen varelager-, driftsmiddel- eller fordringslinje; anleggsmidler = TA - CA er en RESTPOST")

# --- (4) is «Åpnet etter» presence a court/publication artefact? oppbud share by court and by opening year
by_court=[]
for c,g in df.groupby("tingrett"):
    by_court.append(dict(krets=c, n=len(g), oppbud_pct=round(100*float(g.oppbud.mean()),1),
                         bygg_pct=round(100*float(g.bygg.mean()),1)))
by_court.sort(key=lambda r:-r["oppbud_pct"])
T["oppbud_per_krets"]=by_court
T["oppbud_krets_spenn"]=dict(min=by_court[-1]["oppbud_pct"], max=by_court[0]["oppbud_pct"])
T["oppbud_per_aapningsmnd"]={str(k):round(100*float(v),1) for k,v in df.groupby(df.opened.dt.to_period("Q").astype(str)).oppbud.mean().items()}
# does bygg's lower oppbud share survive court adjustment?
v,orate,tab = standardise(df.assign(innstilt730=df.oppbud), "tingrett")
T["oppbud_bygg_std_til_ovriges_krets"]=dict(std=round(100*v,1), ovrige=round(100*orate,1), diff=round(100*(v-orate),1))

# --- (5) reverse standardisation: øvrige standardised to BYGG's revenue distribution
def std_rev(dd, strat, to_group="bygg"):
    b=dd[dd.bygg]; o=dd[~dd.bygg]
    w = b[strat].value_counts(normalize=True)
    rates = o.groupby(strat)["innstilt730"].mean()
    common=[s for s in w.index if s in rates.index]
    wt=w.loc[common]/w.loc[common].sum()
    return float((rates.loc[common]*wt).sum())
T["revers_standardisering"]=dict(
  ovrige_std_til_byggs_revfordeling=round(100*std_rev(S,"band_rev"),1), bygg_raa=round(100*float(S[S.bygg].innstilt730.mean()),1),
  ovrige_std_til_byggs_storrelse=round(100*std_rev(S,"band_ta"),1))

# --- (6) within-band residual size: is revenue homogeneous inside the bands?
rows=[]
for k in ["<1 MNOK","1-5 MNOK","5-20 MNOK",">=20 MNOK"]:
    sub=S[S.band_rev==k]
    b=sub[sub.bygg]; o=sub[~sub.bygg]
    rows.append(dict(band=k, bygg_median_MNOK=round(float(b.operating_revenue.median())/1e6,2),
                     ovrige_median_MNOK=round(float(o.operating_revenue.median())/1e6,2),
                     bygg_n=len(b), ovrige_n=len(o)))
T["rest_storrelse_i_revband"]=rows

# --- (7) the revenue-standardisation weight on cells with few bygg estates
w = S[~S.bygg].band_rev.value_counts(normalize=True)
cells=[]
for k,wt in w.items():
    b=S[(S.bygg)&(S.band_rev==k)]
    cells.append(dict(band=k, vekt_pct=round(100*float(wt),1), bygg_n=len(b),
                      bygg_rate=round(100*float(b.innstilt730.mean()),1)))
T["standardiseringsvekter_rev"]=cells

# --- (8) sensitivity: drop the two non-NOK rows entirely
d2 = df[~df.currency.isin(["EUR","USD"])]
S2 = d2[d2.full730]
T["uten_EUR_USD"]=dict(n=len(d2), rå=prop_row("730 d", S2[S2.bygg].innstilt730.sum(), int(S2.bygg.sum()),
                                              S2[~S2.bygg].innstilt730.sum(), int((~S2.bygg).sum())))

# --- (9) the study's own frozen rows: does the tag agree in the aggregate?
import io as _io
frz=json.load(_io.open(r"../../del-1-hovedstudien/data/_kohort-rader-arbeidskopi.json",encoding="utf-8"))
fb=[r for r in frz if r.get("bygg_utforende")]
T["studiens_frosne_rader"]=dict(n=len(frz), bygg_utforende=len(fb),
    bygg_innstilt=sum(1 for r in fb if r.get("utfall")=="innstilt"),
    bygg_F=sum(1 for r in frz if r.get("bygg_F")),
    bygg_F_innstilt=sum(1 for r in frz if r.get("bygg_F") and r.get("utfall")=="innstilt"),
    uklass=sum(1 for r in frz if not r.get("nace")),
    utfall=dict(pd.Series([r.get("utfall") for r in frz]).value_counts()))
# label-level agreement between the frozen file and my re-derivation
kl = pd.read_csv(os.path.join(DIR,"V-B3-02-kohort-klassifisert.tsv"), sep="\t", dtype={"orgnr":str},
                 keep_default_na=False, na_values=[""])
mine = kl.assign(lab=kl.bransje.fillna("").str.replace("<NL>","\n",regex=False)).groupby("lab").agg(
    n=("orgnr","size"), U=("bygg_U","max"), F=("bygg_F","max"), nace=("nace","first"))
frzdf = pd.DataFrame([{"lab":(r.get("bransje") or ""), "U":bool(r.get("bygg_utforende")),
                       "F":bool(r.get("bygg_F")), "nace":r.get("nace") or ""} for r in frz])
frzag = frzdf.groupby("lab").agg(n=("lab","size"), U=("U","max"), F=("F","max"), nace=("nace","first"))
j = mine.join(frzag, how="outer", lsuffix="_min", rsuffix="_frz")
dis = j[(j.U_min.fillna(-1)!=j.U_frz.fillna(-1).astype(float)) | (j.n_min.fillna(-1)!=j.n_frz.fillna(-1))]
T["etikett_uenighet"]=dict(etiketter_totalt=len(j), uenige=len(dis),
                           eksempler=dis.head(10).to_dict(orient="index"))

json.dump(T, open(os.path.join(DIR,"V-B3-07-stresstest.json"),"w",encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
for k,v in T.items(): print("==",k,"==\n",json.dumps(v,ensure_ascii=False,indent=1,default=str)[:2600])
