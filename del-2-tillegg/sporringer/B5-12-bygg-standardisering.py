# B5/12 Tilleggstest: overlever byggforskjellen en storrelsesstandardisering?
import io, os, math, json, collections
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
OUT=[]
def p(*a):
    s=" ".join(str(x) for x in a); OUT.append(s); print(s.encode("ascii","replace").decode())
def wilson(k,n,z=1.959963985):
    if n==0: return (float('nan'),)*3
    ph=k/n; d=1+z*z/n; c=(ph+z*z/(2*n))/d
    h=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/d
    return (100*ph,100*max(0.,c-h),100*min(1.,c+h))
def pct(k,n):
    if n==0: return "-"
    a,lo,hi=wilson(k,n); return "%d/%d = %.1f %% [%.1f-%.1f]"%(k,n,a,lo,hi)

COLS=["orgnr","opened","utfall","t_dager","grunnlag","tingrett","bransje","fy","total_assets",
      "equity","liabilities","operating_revenue","payroll_expenses","amount_unit","currency","source_name","oppfolging"]
rows=[]
for line in io.open(os.path.join(D,"B5-05-kohortuttrekk.tsv"),encoding="utf-8"):
    line=line.rstrip("\n")
    if not line.strip(): continue
    r=dict(zip(COLS,line.split("\t")))
    r["t_dager"]=int(r["t_dager"]) if r["t_dager"] else None
    for k in ("total_assets","operating_revenue"):
        r[k]=float(r[k]) if r[k] else None
    rows.append(r)
km=json.load(io.open("../../del-1-hovedstudien/data/bransjekart-v3_2026-08-30.json",encoding="utf-8"))
bm=dict((e["etikett"], bool(e.get("er_bygg_F"))) for e in km["kart"])
for r in rows: r["bygg"]=bm.get(r["bransje"])
def band(r):
    ta=r["total_assets"]
    if ta is None: return "uten regnskap"
    if ta>=5e6: return "5 MNOK+"
    if ta>=1e6: return "1-5 MNOK"
    return "under 1 MNOK"
BANDS=["5 MNOK+","1-5 MNOK","under 1 MNOK","uten regnskap"]
for r in rows: r["band"]=band(r)
kl=[r for r in rows if r["bygg"] is not None]

p("="*100)
p("B5/12 — OVERLEVER BYGGFORSKJELLEN EN STORRELSESSTANDARDISERING?")
p("Bygg = SN2007 naeringshovedomrade F, studiens eget kart v3 pa bransjeetiketten i kunngjoringen.")
p("Klassifisert: %s av kohorten." % pct(len(kl),len(rows)))
p("="*100)
bygg=[r for r in kl if r["bygg"]]; ovr=[r for r in kl if not r["bygg"]]
p("")
p("Raa andel innstilt (as-of 24.08.2026):")
p("  bygg    %s" % pct(sum(1 for r in bygg if r["utfall"]=="innstilt"),len(bygg)))
p("  ovrige  %s" % pct(sum(1 for r in ovr if r["utfall"]=="innstilt"),len(ovr)))
raw=100*(sum(1 for r in bygg if r["utfall"]=="innstilt")/len(bygg)-sum(1 for r in ovr if r["utfall"]=="innstilt")/len(ovr))
p("  differanse bygg minus ovrige: %+.1f pp" % raw)
p("")
p("Balansefordelingen er ULIK — byggboene er storre:")
p("%-14s | %-24s | %-24s" % ("balansegruppe","bygg","ovrige"))
for b in BANDS:
    kb=sum(1 for r in bygg if r["band"]==b); ko=sum(1 for r in ovr if r["band"]==b)
    p("%-14s | %-24s | %-24s" % (b,"%d/%d = %.1f %%"%(kb,len(bygg),100*kb/len(bygg)),
      "%d/%d = %.1f %%"%(ko,len(ovr),100*ko/len(ovr))))
p("")
p("Andel innstilt INNAD i hver balansegruppe:")
p("%-14s | %-27s | %-27s | %-9s" % ("balansegruppe","bygg","ovrige","differanse"))
for b in BANDS:
    sb=[r for r in bygg if r["band"]==b]; so=[r for r in ovr if r["band"]==b]
    kb=sum(1 for r in sb if r["utfall"]=="innstilt"); ko=sum(1 for r in so if r["utfall"]=="innstilt")
    p("%-14s | %-27s | %-27s | %+8.1f pp" % (b,pct(kb,len(sb)),pct(ko,len(so)),
      100*(kb/len(sb)-ko/len(so))))
w=dict((b,sum(1 for r in kl if r["band"]==b)/len(kl)) for b in BANDS)
def std(sel,dlim=None):
    num=0.0
    for b in BANDS:
        s=[r for r in sel if r["band"]==b]
        if not s: return float('nan')
        if dlim is None: k=sum(1 for r in s if r["utfall"]=="innstilt")
        else: k=sum(1 for r in s if r["utfall"]=="innstilt" and r["t_dager"]<=dlim)
        num+=w[b]*k/len(s)
    return num
sb_,so_=std(bygg),std(ovr)
p("")
p("Direkte standardisert til kohortens balansefordeling:")
p("  bygg    %.1f %%" % (100*sb_))
p("  ovrige  %.1f %%" % (100*so_))
p("  standardisert differanse: %+.1f pp (raa var %+.1f pp)" % (100*(sb_-so_),raw))
rng=np.random.default_rng(20260912); idx=np.arange(len(kl)); boots=[]
for _ in range(2000):
    s=[kl[i] for i in rng.choice(idx,size=len(kl),replace=True)]
    a=std([r for r in s if r["bygg"]]); b_=std([r for r in s if not r["bygg"]])
    if not (math.isnan(a) or math.isnan(b_)): boots.append(a-b_)
lo,hi=np.percentile(boots,[2.5,97.5])
p("  95 %% bootstrap-intervall: [%+.1f, %+.1f] pp — %s" % (100*lo,100*hi,
  "forskjellen OVERLEVER" if hi<0 or lo>0 else "forskjellen forsvinner"))
p("")
p("Samme test pa 12-manedershorisonten:")
p("  raa: bygg %.1f %% / ovrige %.1f %% (%+.1f pp) | standardisert: %.1f %% / %.1f %% (%+.1f pp)" % (
  100*sum(1 for r in bygg if r["utfall"]=="innstilt" and r["t_dager"]<=365)/len(bygg),
  100*sum(1 for r in ovr if r["utfall"]=="innstilt" and r["t_dager"]<=365)/len(ovr),
  100*(sum(1 for r in bygg if r["utfall"]=="innstilt" and r["t_dager"]<=365)/len(bygg)
      -sum(1 for r in ovr if r["utfall"]=="innstilt" and r["t_dager"]<=365)/len(ovr)),
  100*std(bygg,365),100*std(ovr,365),100*(std(bygg,365)-std(ovr,365))))
p("")
p("Kontroll — oppbudsandel og apenandel etter bransje:")
p("  bygg    oppbud %s | apne %s" % (pct(sum(1 for r in bygg if r["grunnlag"]=="oppbud"),len(bygg)),
                                      pct(sum(1 for r in bygg if r["utfall"]=="aapen"),len(bygg))))
p("  ovrige  oppbud %s | apne %s" % (pct(sum(1 for r in ovr if r["grunnlag"]=="oppbud"),len(ovr)),
                                      pct(sum(1 for r in ovr if r["utfall"]=="aapen"),len(ovr))))
p("  median totalkapital: bygg %.0f NOK, ovrige %.0f NOK" % (
  sorted(r["total_assets"] for r in bygg if r["total_assets"] is not None)[sum(1 for r in bygg if r["total_assets"] is not None)//2],
  sorted(r["total_assets"] for r in ovr if r["total_assets"] is not None)[sum(1 for r in ovr if r["total_assets"] is not None)//2]))
with io.open(os.path.join(D,"B5-12-bygg.txt"),"w",encoding="utf-8") as f:
    f.write("\n".join(OUT)+"\n")
print("\nSKREV B5-12-bygg.txt")
