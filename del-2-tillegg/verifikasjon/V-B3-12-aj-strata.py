# V-B3: which population do B3's stratified "AJ CIF730" columns come from -- the fixed-730d subcohort
# (where AJ == the raw share) or the FULL cohort (where censoring makes it differ)?
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
exec(open(os.path.join(HERE,"V-B3-03-lib.py"),encoding="utf-8").read())
df = load(); S = df[df.full730]
T={}
def aj_by(strat, order, d, tag):
    r={}
    for k in order:
        sub=d[d[strat].astype(str)==k]; b=sub[sub.bygg]; o=sub[~sub.bygg]
        if len(b)==0 or len(o)==0: continue
        r[k]=dict(bygg=round(100*aj_cif(b.t.values,b.ev.values,730),1),
                  ovrige=round(100*aj_cif(o.t.values,o.ev.values,730),1), n_b=len(b), n_o=len(o))
    T[tag]=r
aj_by("band_ta",["ingen regnskap","<1 MNOK","1-5 MNOK",">=5 MNOK"], S, "size4_delkohort")
aj_by("band_ta",["ingen regnskap","<1 MNOK","1-5 MNOK",">=5 MNOK"], df, "size4_hele_kohorten")
aj_by("band_rev",["ingen regnskap","mangler","<1 MNOK","1-5 MNOK","5-20 MNOK",">=20 MNOK"], df, "rev_hele_kohorten")
d2=df.copy(); d2["grunnlag"]=np.where(d2.oppbud,"oppbud","begjæring")
aj_by("grunnlag",["oppbud","begjæring"], d2, "oppbud_hele_kohorten")
T["B3_trykte_AJ"]=dict(size4=[[83.9,89.4],[83.7,85.9],[60.6,68.4],[40.6,52.8]],
                       rev=[[83.9,89.4],[91.1,87.5],[88.5,87.9],[80.0,76.6],[56.2,58.6],[32.6,41.3]],
                       oppbud=[[63.9,75.9],[79.9,77.7]])
json.dump(T, open(os.path.join(DIR,"V-B3-12-aj-strata.json"),"w",encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(T, indent=1, ensure_ascii=False))
