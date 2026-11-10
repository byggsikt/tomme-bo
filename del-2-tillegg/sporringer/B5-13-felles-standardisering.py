# B5/13 Felles standardisering: bygg-effekten justert for BADE balansestorrelse og apningsgrunnlag.
import io, os, math, json
import numpy as np
D=os.path.dirname(os.path.abspath(__file__)); OUT=[]
def p(*a):
    s=" ".join(str(x) for x in a); OUT.append(s); print(s.encode("ascii","replace").decode())
COLS=["orgnr","opened","utfall","t_dager","grunnlag","tingrett","bransje","fy","total_assets",
      "equity","liabilities","operating_revenue","payroll_expenses","amount_unit","currency","source_name","oppfolging"]
rows=[]
for line in io.open(os.path.join(D,"B5-05-kohortuttrekk.tsv"),encoding="utf-8"):
    line=line.rstrip("\n")
    if not line.strip(): continue
    r=dict(zip(COLS,line.split("\t")))
    r["t_dager"]=int(r["t_dager"]) if r["t_dager"] else None
    r["total_assets"]=float(r["total_assets"]) if r["total_assets"] else None
    rows.append(r)
km=json.load(io.open("../../del-1-hovedstudien/data/bransjekart-v3_2026-08-30.json",encoding="utf-8"))
bm=dict((e["etikett"],bool(e.get("er_bygg_F"))) for e in km["kart"])
for r in rows: r["bygg"]=bm.get(r["bransje"])
def band(r):
    ta=r["total_assets"]
    if ta is None: return "uten regnskap"
    return "5 MNOK+" if ta>=5e6 else ("1-5 MNOK" if ta>=1e6 else "under 1 MNOK")
for r in rows: r["band"]=band(r)
kl=[r for r in rows if r["bygg"] is not None]
CELLS=[(b,g) for b in ["5 MNOK+","1-5 MNOK","under 1 MNOK","uten regnskap"] for g in ["oppbud","ingen_felt"]]
w={c: sum(1 for r in kl if (r["band"],r["grunnlag"])==c)/len(kl) for c in CELLS}
p("Cellestorrelser i den felles standarden (balansegruppe x grunnlag), n = %d:" % len(kl))
for c in CELLS:
    nb=sum(1 for r in kl if r["bygg"] and (r["band"],r["grunnlag"])==c)
    no=sum(1 for r in kl if not r["bygg"] and (r["band"],r["grunnlag"])==c)
    p("  %-14s %-11s vekt %.3f | bygg n=%4d | ovrige n=%4d" % (c[0],c[1],w[c],nb,no))
def std(sel):
    num=0.0
    for c in CELLS:
        s=[r for r in sel if (r["band"],r["grunnlag"])==c]
        if not s: return float('nan')
        num+=w[c]*sum(1 for r in s if r["utfall"]=="innstilt")/len(s)
    return num
bygg=[r for r in kl if r["bygg"]]; ovr=[r for r in kl if not r["bygg"]]
a,b_=std(bygg),std(ovr)
p("")
p("Andel innstilt, standardisert for BADE balansestorrelse og apningsgrunnlag:")
p("  bygg    %.1f %%" % (100*a))
p("  ovrige  %.1f %%" % (100*b_))
p("  differanse: %+.1f pp" % (100*(a-b_)))
rng=np.random.default_rng(20260912); idx=np.arange(len(kl)); boots=[]
for _ in range(2000):
    s=[kl[i] for i in rng.choice(idx,size=len(kl),replace=True)]
    x=std([r for r in s if r["bygg"]]); y=std([r for r in s if not r["bygg"]])
    if not (math.isnan(x) or math.isnan(y)): boots.append(x-y)
lo,hi=np.percentile(boots,[2.5,97.5])
p("  95 %% bootstrap-intervall: [%+.1f, %+.1f] pp (%d gyldige trekk)" % (100*lo,100*hi,len(boots)))
p("")
p("Og motsatt: grunnlagskontrasten standardisert for BADE balansestorrelse og bransje:")
CELLS2=[(b,g) for b in ["5 MNOK+","1-5 MNOK","under 1 MNOK","uten regnskap"] for g in [True,False]]
w2={c: sum(1 for r in kl if (r["band"],r["bygg"])==c)/len(kl) for c in CELLS2}
def std2(sel):
    num=0.0
    for c in CELLS2:
        s=[r for r in sel if (r["band"],r["bygg"])==c]
        if not s: return float('nan')
        num+=w2[c]*sum(1 for r in s if r["utfall"]=="innstilt")/len(s)
    return num
o=[r for r in kl if r["grunnlag"]=="oppbud"]; i=[r for r in kl if r["grunnlag"]=="ingen_felt"]
x,y=std2(o),std2(i)
p("  oppbud %.1f %% | ikke-oppbud %.1f %% | differanse %+.1f pp" % (100*x,100*y,100*(y-x)))
boots=[]
for _ in range(2000):
    s=[kl[i2] for i2 in rng.choice(idx,size=len(kl),replace=True)]
    xx=std2([r for r in s if r["grunnlag"]=="oppbud"]); yy=std2([r for r in s if r["grunnlag"]=="ingen_felt"])
    if not (math.isnan(xx) or math.isnan(yy)): boots.append(yy-xx)
lo,hi=np.percentile(boots,[2.5,97.5])
p("  95 %% bootstrap-intervall: [%+.1f, %+.1f] pp" % (100*lo,100*hi))
io.open(os.path.join(D,"B5-13-felles.txt"),"w",encoding="utf-8").write("\n".join(OUT)+"\n")
