# V-B3: independent logistic models, interaction tests, court table and extra probes.
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
exec(open(os.path.join(HERE,"V-B3-03-lib.py"),encoding="utf-8").read())
BOOT = os.environ.get("VB3_BOOT","1")=="1"

df = load()
va = pd.read_csv(os.path.join(DIR,"V-B3-02b-varsel.txt"), sep="|", header=None,
                 names=["orgnr","n_varsel_for"], dtype={"orgnr":str})
df = df.merge(va, on="orgnr", how="left", validate="1:1")
df["varsel"] = (df.n_varsel_for>0).astype(int)
df["gapcat"] = np.where(~df.har_regnskap, "1 aar", np.where(df.gap_ar<=1, "1 aar", "2+ aar"))
df["gapcat_ren"] = np.where(~df.har_regnskap, "0 ingen", np.where(df.gap_ar<=1, "1 aar", "2+ aar"))
df["agecat"] = np.where(df.alder_ar.isna(), "ukjent",
                 np.where(df.alder_ar<3, "<3 aar", np.where(df.alder_ar<10, "3-10 aar", ">=10 aar")))
df["hasacc"] = df.har_regnskap.astype(int)
df["logta"] = np.where(df.har_regnskap, np.log10(df.total_assets.clip(lower=1e3)), np.nan)
df["logrev"] = np.where(df.operating_revenue.notna(), np.log10(df.operating_revenue.clip(lower=1e3)), np.nan)
# reference-code the reference level first so `design` drops it (design drops level[0] alphabetically)
df["size7"] = df.band_ta7.map({"<0,5":"0 <0,5","ingen regnskap":"1 ingen","=0":"2 =0","0,5-1":"3 0,5-1",
                               "1-5":"4 1-5","5-20":"5 5-20",">=20":"6 >=20"})
df["size4"] = df.band_ta.map({"<1 MNOK":"0 <1","ingen regnskap":"1 ingen","1-5 MNOK":"2 1-5",">=5 MNOK":"3 >=5"})
df["revb"]  = df.band_rev.map({"<1 MNOK":"0 <1","ingen regnskap":"1 ingen","mangler":"2 mangler",
                               "1-5 MNOK":"3 1-5","5-20 MNOK":"4 5-20",">=20 MNOK":"5 >=20"})
df["agec"]  = df.agecat.map({"3-10 aar":"0 3-10","<3 aar":"1 <3",">=10 aar":"2 >=10","ukjent":"3 ukjent"})
df["court"] = "z"+df.tingrett.fillna("UKJENT")
df.loc[df.tingrett.eq("OSLO TINGRETT"),"court"]="a OSLO"
df["oppb"] = df.oppbud.astype(int)
df["gapc"] = df.gapcat.map({"1 aar":"0 1aar","2+ aar":"1 2plus"})

S = df[df.full730].copy()
out = {}

def run(name, d, cats, nums=(), y="innstilt730", boot=BOOT, B=200):
    r = model(d, cats, nums, y=y, B=B, boot=boot)
    out[name] = dict(n=len(d), OR=round(r["OR"],3), lo=round(r["OR_lo"],3), hi=round(r["OR_hi"],3),
                     p=float(f'{r["p"]:.3g}'), RD=round(r["RD_pp"],1),
                     RDlo=round(r["RD_lo_pp"],1), RDhi=round(r["RD_hi_pp"],1))
    return r

r0  = run("M0 rå", S, [])
raw_rd = r0["RD_pp"]
r1  = run("M1 size7", S, ["size7"])
r1b = run("M1b log ta", S, ["hasacc"], ["logta_f","logta2_f"]) if False else None
# M1b with log(TA): impute reference value for no-accounts, with hasacc dummy
S["logta_f"]  = S.logta.fillna(0.0); S["logta2_f"] = S["logta_f"]**2
r1b = run("M1b log10(TA)+sq+ingen regnskap", S, ["hasacc"], ["logta_f","logta2_f"])
r2  = run("M2 oppbud", S, ["oppb"])
r3  = run("M3 regnskap levert", S, ["hasacc"])
r4  = run("M4 size7+oppbud+gap+alder", S, ["size7","oppb","gapc","agec"])
r5  = run("M5 = M4 + rettskrets", S, ["size7","oppb","gapc","agec","court"])
r6  = run("M6 = M5 + varsel", S, ["size7","oppb","gapc","agec","court","varsel"])
rrev= run("bygg + driftsinntektsbånd", S, ["revb"])
S["logrev_f"]=S.logrev.fillna(0.0); S["logrev2_f"]=S["logrev_f"]**2
S["revmiss"]=S.operating_revenue.isna().astype(int)
rrevc=run("bygg + log10(rev)+sq+mangler+ingen regnskap", S, ["revmiss","hasacc"], ["logrev_f","logrev2_f"])
r7  = run("M7 = M5 + driftsinntektsbånd", S, ["size7","oppb","gapc","agec","court","revb"])

# forklart andel
for k,v in out.items():
    v["forklart_pct"] = None if k.startswith("M0") else round(100*(1 - v["RD"]/raw_rd),0)

# M7 with område F as the tag
SF = S.copy(); SF["bygg"] = SF.bygg_F.fillna(0).astype(int)==1
r7F = run("M7 med område F", SF, ["size7","oppb","gapc","agec","court","revb"])
# M7 on the as-of outcome, all 5165
D = df.copy(); D["innstilt730"]=D.innstilt_flag
r7A = run("M7 as-of, alle 5165", D, ["size7","oppb","gapc","agec","court","revb"])

# within petition basis
So = S[S.oppbud]; Sb = S[~S.oppbud]
run("oppbud rå", So, []); run("oppbud M5", So, ["size7","gapc","agec","court"])
run("oppbud M7", So, ["size7","gapc","agec","court","revb"])
run("begjæring rå", Sb, []); run("begjæring M5", Sb, ["size7","gapc","agec","court"])
run("begjæring M7", Sb, ["size7","gapc","agec","court","revb"])

# ---- interaction LR tests ----
def lr(d, base_cats, inter_col, y="innstilt730"):
    X0,_ = design(d, base_cats); yv=d[y].astype(float).values
    b0,_ = logit_fit(X0,yv); ll0=loglik(X0,yv,b0)
    # add bygg x level interactions
    lv = sorted(d[inter_col].astype(str).unique())[1:]
    extra=[((d[inter_col].astype(str)==l).astype(float).values*d["bygg"].astype(float).values) for l in lv]
    X1=np.column_stack([X0]+extra)
    b1,_=logit_fit(X1,yv); ll1=loglik(X1,yv,b1)
    stat=2*(ll1-ll0); dfree=len(lv)
    return dict(chi2=round(stat,3), df=dfree, p=float(f"{1-stats.chi2.cdf(stat,dfree):.3g}"))

inter={}
inter["bygg x oppbud (M5)"]   = lr(S, ["size7","oppb","gapc","agec","court"], "oppb")
inter["bygg x oppbud (M7)"]   = lr(S, ["size7","oppb","gapc","agec","court","revb"], "oppb")
inter["bygg x størrelse (M5)"]= lr(S, ["size7","oppb","gapc","agec","court"], "size7")
inter["bygg x regnskap (M5)"] = lr(S, ["size7","oppb","gapc","agec","court","hasacc"], "hasacc")
inter["bygg x driftsinnt (M5)"]=lr(S, ["size7","oppb","gapc","agec","court","revb"], "revb")
out["_interaksjoner"]=inter

# ---- covariate ORs in M7 ----
X,names = design(S, ["size7","oppb","gapc","agec","court","revb"])
beta,cov = logit_fit(X, S.innstilt730.astype(float).values)
cov_or = {}
for i,nm in enumerate(names):
    if nm in ("const",): continue
    if nm.startswith("court=") : continue
    se=math.sqrt(cov[i,i])
    cov_or[nm]=dict(OR=round(math.exp(beta[i]),3), lo=round(math.exp(beta[i]-1.96*se),3), hi=round(math.exp(beta[i]+1.96*se),3))
out["_M7_kovariater"]=cov_or

# ---- court table (as-of), correlation ----
ct=[]
for c,g in df.groupby("tingrett"):
    b=g[g.bygg]; o=g[~g.bygg]
    if len(b)==0 or len(o)==0: continue
    ct.append(dict(krets=c, n=len(g), byggandel=round(100*len(b)/len(g),1),
                   b=round(100*b.innstilt_flag.mean(),1), o=round(100*o.innstilt_flag.mean(),1),
                   d=round(100*(b.innstilt_flag.mean()-o.innstilt_flag.mean()),1)))
neg=sum(1 for r in ct if r["d"]<0)
x=np.array([r["byggandel"] for r in ct]); yv=np.array([100*df[df.tingrett==r["krets"]].innstilt_flag.mean() for r in ct])
out["_rettskrets"]=dict(n_kretser=len(ct), negativ_i=neg, pearson_r=round(float(np.corrcoef(x,yv)[0,1]),3), tabell=ct)

# ---- har_regnskap standardisation (B3 §4 iii) ----
S["harreg"]=np.where(S.har_regnskap,"regnskap","ingen")
v,orate,tab = standardise(S,"harreg")
out["_std_regnskap"]=dict(std=round(100*v,1), ovrige=round(100*orate,1), diff=round(100*(v-orate),1),
                          mh_or=round(mh_or([(a,n1-a,c,n2-c) for a,n1,c,n2 in tab]),3))
v,orate,tab = standardise(S,"agec")
out["_std_alder"]=dict(std=round(100*v,1), diff=round(100*(v-orate),1), mh_or=round(mh_or([(a,n1-a,c,n2-c) for a,n1,c,n2 in tab]),3))
# correct "gap" strat excluding the no-accounts fold
Sg=S[S.har_regnskap].copy()
rows=[]
for k in ["1 aar","2+ aar"]:
    sub=Sg[Sg.gapcat==k]; b=sub[sub.bygg]; o=sub[~sub.bygg]
    rows.append(prop_row(k,b.innstilt730.sum(),len(b),o.innstilt730.sum(),len(o)))
out["_gap_uten_ingen_regnskap"]=rows
# and the folded version B3 printed
rows=[]
for k in ["1 aar","2+ aar"]:
    sub=S[S.gapcat==k]; b=sub[sub.bygg]; o=sub[~sub.bygg]
    rows.append(prop_row(k+" (B3-fold: inkl. ingen regnskap)",b.innstilt730.sum(),len(b),o.innstilt730.sum(),len(o)))
out["_gap_B3_fold"]=rows

# ---- oppbud share by size, revenue within oppbud ----
def medm(x):
    x=pd.Series(x).dropna(); return round(float(x.median())/1e6,2) if len(x) else None
out["_oppbud_profil"]=dict(
  bygg_oppbud_rev_median=medm(df[(df.bygg)&(df.oppbud)].operating_revenue),
  bygg_oppbud_rev_ge5=round(100*float((df[(df.bygg)&(df.oppbud)].operating_revenue>=5e6).mean()),1),
  ovrige_oppbud_rev_median=medm(df[(~df.bygg)&(df.oppbud)].operating_revenue),
  bygg_begj_rev_median=medm(df[(df.bygg)&(~df.oppbud)].operating_revenue),
  oppbudsandel_bygg_per_size={k: round(100*float(df[(df.bygg)&(df.band_ta==k)].oppbud.mean()),1) for k in ["ingen regnskap","<1 MNOK","1-5 MNOK",">=5 MNOK"]},
  oppbudsandel_ovrige_per_size={k: round(100*float(df[(~df.bygg)&(df.band_ta==k)].oppbud.mean()),1) for k in ["ingen regnskap","<1 MNOK","1-5 MNOK",">=5 MNOK"]})

# ---- oppbud x size stratified (730d) ----
ox=[]
for gname, gmask in [("oppbud", S.oppbud),("begjæring", ~S.oppbud)]:
    for k in ["ingen regnskap","<1 MNOK","1-5 MNOK",">=5 MNOK"]:
        sub=S[gmask & S.band_ta.eq(k)]; b=sub[sub.bygg]; o=sub[~sub.bygg]
        if len(b)<5 or len(o)<5: continue
        r=prop_row(f"{gname} / {k}", b.innstilt730.sum(), len(b), o.innstilt730.sum(), len(o)); ox.append(r)
out["_oppbud_x_size"]=ox

json.dump(out, open(os.path.join(DIR,("V-B3-05-modeller.json" if BOOT else "V-B3-05-modeller-noboot.json")),"w",encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
for k,v in out.items():
    if not k.startswith("_"): print(f"{k:45s} {json.dumps(v,ensure_ascii=False)}")
print("\nINTER", json.dumps(inter,ensure_ascii=False))
print("\nSTD regnskap", json.dumps(out["_std_regnskap"],ensure_ascii=False), " alder", json.dumps(out["_std_alder"],ensure_ascii=False))
print("\nGAP ren", json.dumps(out["_gap_uten_ingen_regnskap"],ensure_ascii=False))
print("GAP B3-fold", json.dumps(out["_gap_B3_fold"],ensure_ascii=False))
print("\nKRETS", out["_rettskrets"]["n_kretser"], "negativ i", out["_rettskrets"]["negativ_i"], "r=", out["_rettskrets"]["pearson_r"])
print("\nOPPBUDPROFIL", json.dumps(out["_oppbud_profil"],ensure_ascii=False))
print("\nOPPBUDxSIZE"); [print(" ", json.dumps(r,ensure_ascii=False)) for r in ox]
print("\nM7 kovariater", json.dumps(cov_or,ensure_ascii=False))
