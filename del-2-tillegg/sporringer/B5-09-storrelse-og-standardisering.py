# B5/09 Storrelsen som forklaring: horisonter per balansegruppe, og storrelsesstandardisert
# sammenligning av de to apningsgrunnlagene. Pluss detaljer om de 351 apne boene.
import io, os, math, collections
import numpy as np
from scipy import stats

D = os.path.dirname(os.path.abspath(__file__))
OUT = []
def p(*a):
    s = " ".join(str(x) for x in a); OUT.append(s); print(s.encode("ascii","replace").decode())
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
    r["oppfolging"]=int(r["oppfolging"])
    for k in ("total_assets","operating_revenue"):
        r[k]=float(r[k]) if r[k] else None
    rows.append(r)
assert len(rows)==5165

def band(r):
    ta=r["total_assets"]
    if ta is None: return "uten regnskap"
    if ta>=5e6: return "5 MNOK+"
    if ta>=1e6: return "1-5 MNOK"
    return "under 1 MNOK"
BANDS=["5 MNOK+","1-5 MNOK","under 1 MNOK","uten regnskap"]
for r in rows: r["band"]=band(r)
HOR=[(91,"3 mnd"),(183,"6 mnd"),(274,"9 mnd"),(365,"12 mnd"),(548,"18 mnd"),(601,"601 d")]

p("="*104)
p("B5/09 — STORRELSE OG STANDARDISERING. n = 5 165, as-of 24.08.2026")
p("Balansegruppe = totalkapital i siste arsregnskap MED regnskapsar FOR apningsaret (dekning 4 833/5 165 = 93,6 %).")
p("Enhet: hele kroner. Kontrollert: 2 683 selskapsar finnes i BEGGE regnskapskilder med IDENTISK total_assets")
p("(forhold 1,0000, null avvik) — 'amount_unit' blank vs whole_kroner er en merkelapp, ikke en skala.")
p("2 av 4 833 rader er merket i utenlandsk valuta (USD 14,9 mill., EUR 66,8 mill.); begge ligger i toppgruppen uansett.")
p("="*104)

p("")
p("## 1. TID TIL INNSTILLING PER BALANSEGRUPPE — tabellen advokaten kan bruke pa en konkret klient")
p("%-14s | %6s | %-7s %-7s %-7s %-7s %-7s %-7s | %-9s | %-8s" %
  ("balansegruppe","n","3 mnd","6 mnd","9 mnd","12 mnd","18 mnd","601 d","24 mnd*","median"))
for b in BANDS:
    sel=[r for r in rows if r["band"]==b]; n=len(sel)
    cells=["%.1f%%"%(100*sum(1 for r in sel if r["utfall"]=="innstilt" and r["t_dager"]<=d)/n) for d,_ in HOR]
    s7=[r for r in sel if r["opened"]<="2024-08-24"]
    k7=sum(1 for r in s7 if r["utfall"]=="innstilt" and r["t_dager"]<=730)
    v=sorted(r["t_dager"] for r in sel if r["utfall"]=="innstilt")
    p("%-14s | %6d | %-7s %-7s %-7s %-7s %-7s %-7s | %5.1f%% (%d) | %6d d" %
      (b,n,*cells,100*k7/len(s7),len(s7),v[len(v)//2]))
p("* 24 mnd pa delkohorten apnet <= 2024-08-24; n i parentes.")
p("")
p("Tellere: ")
for b in BANDS:
    sel=[r for r in rows if r["band"]==b]; n=len(sel)
    p("  %-14s n=%d  " % (b,n) + "  ".join("%s=%d"%(nm,sum(1 for r in sel if r["utfall"]=="innstilt" and r["t_dager"]<=d)) for d,nm in HOR))
p("")
p("Samme tabell, ENDELIG utfall per balansegruppe (as-of):")
p("%-14s | %6s | %-27s | %-27s | %-27s" % ("balansegruppe","n","innstilt","ordinaert avsluttet","fortsatt apent"))
for b in BANDS:
    sel=[r for r in rows if r["band"]==b]; n=len(sel)
    p("%-14s | %6d | %-27s | %-27s | %-27s" % (b,n,
      pct(sum(1 for r in sel if r["utfall"]=="innstilt"),n),
      pct(sum(1 for r in sel if r["utfall"]=="avsluttet"),n),
      pct(sum(1 for r in sel if r["utfall"]=="aapen"),n)))

# ---------- standardisering ----------
p("")
p("="*104)
p("## 2. ER FORSKJELLEN MELLOM OPPBUD OG IKKE-OPPBUD EGENTLIG EN STORRELSESFORSKJELL?")
p("="*104)
p("")
p("Oppbudsandel innad i hver balansegruppe (oppbudsboene er systematisk STORRE):")
for b in BANDS:
    sel=[r for r in rows if r["band"]==b]
    p("  %-14s %s" % (b, pct(sum(1 for r in sel if r["grunnlag"]=="oppbud"),len(sel))))
p("")
p("Ustandardisert (raa) andel innstilt:")
for g in ("oppbud","ingen_felt"):
    sel=[r for r in rows if r["grunnlag"]==g]
    p("  %-11s %s" % (g, pct(sum(1 for r in sel if r["utfall"]=="innstilt"),len(sel))))
raw_d = (sum(1 for r in rows if r["grunnlag"]=="ingen_felt" and r["utfall"]=="innstilt")/sum(1 for r in rows if r["grunnlag"]=="ingen_felt")
       - sum(1 for r in rows if r["grunnlag"]=="oppbud" and r["utfall"]=="innstilt")/sum(1 for r in rows if r["grunnlag"]=="oppbud"))
p("  raa differanse (ikke-oppbud minus oppbud): %+.1f pp" % (100*raw_d))
p("")
p("Direkte standardisert til kohortens egen balansefordeling (vekt = n i gruppen / 5 165):")
w = dict((b, sum(1 for r in rows if r["band"]==b)/len(rows)) for b in BANDS)
def std_rate(sel):
    num=0.0
    for b in BANDS:
        s=[r for r in sel if r["band"]==b]
        if not s: return float('nan')
        num += w[b]*sum(1 for r in s if r["utfall"]=="innstilt")/len(s)
    return num
so = std_rate([r for r in rows if r["grunnlag"]=="oppbud"])
si = std_rate([r for r in rows if r["grunnlag"]=="ingen_felt"])
p("  oppbud      standardisert %.1f %%" % (100*so))
p("  ingen_felt  standardisert %.1f %%" % (100*si))
p("  standardisert differanse: %+.1f pp" % (100*(si-so)))
rng=np.random.default_rng(20260912)
idx=np.arange(len(rows)); boots=[]
for _ in range(2000):
    s=rng.choice(idx,size=len(rows),replace=True)
    sample=[rows[i] for i in s]
    a=std_rate([r for r in sample if r["grunnlag"]=="oppbud"]); b_=std_rate([r for r in sample if r["grunnlag"]=="ingen_felt"])
    if not (math.isnan(a) or math.isnan(b_)): boots.append(b_-a)
lo,hi=np.percentile(boots,[2.5,97.5])
p("  95 %% bootstrap-intervall (2 000 trekk): [%+.1f, %+.1f] pp" % (100*lo,100*hi))
p("  -> Av den raa forskjellen pa %+.1f pp blir %+.1f pp igjen nar balansestorrelsen holdes fast." % (100*raw_d,100*(si-so)))
p("")
p("Samme oving pa 3- og 6-manedershorisontene (andel innstilt innen):")
for dlim,nm in ((91,"3 mnd"),(183,"6 mnd"),(365,"12 mnd")):
    def sr(sel):
        num=0.0
        for b in BANDS:
            s=[r for r in sel if r["band"]==b]
            num += w[b]*sum(1 for r in s if r["utfall"]=="innstilt" and r["t_dager"]<=dlim)/len(s)
        return num
    o=[r for r in rows if r["grunnlag"]=="oppbud"]; i=[r for r in rows if r["grunnlag"]=="ingen_felt"]
    ro=sum(1 for r in o if r["utfall"]=="innstilt" and r["t_dager"]<=dlim)/len(o)
    ri=sum(1 for r in i if r["utfall"]=="innstilt" and r["t_dager"]<=dlim)/len(i)
    p("  %-6s raa: oppbud %.1f %% / ikke-oppbud %.1f %% (%+.1f pp) | standardisert: %.1f %% / %.1f %% (%+.1f pp)" %
      (nm,100*ro,100*ri,100*(ri-ro),100*sr(o),100*sr(i),100*(sr(i)-sr(o))))

# ---------- de 351 ----------
p("")
p("="*104)
p("## 3. DE 351 APNE BOENE — hvem er de?")
p("="*104)
op=[r for r in rows if r["utfall"]=="aapen"]
p("")
p("Apningsar:")
for y in ("2023","2024"):
    sel=[r for r in rows if r["opened"][:4]==y]
    p("  apnet %s: %s" % (y, pct(sum(1 for r in sel if r["utfall"]=="aapen"),len(sel))))
p("")
p("Halvar (apningskohortens egne vinduer) — apenandel faller ikke bare med tiden:")
def half(s):
    y,m=int(s[:4]),int(s[5:7]); return "%dH%d"%(y,1 if m<=6 else 2)
for h in sorted(set(half(r["opened"]) for r in rows)):
    sel=[r for r in rows if half(r["opened"])==h]
    p("  %-7s %s  (median oppfolging %d d)" % (h, pct(sum(1 for r in sel if r["utfall"]=="aapen"),len(sel)),
       sorted(r["oppfolging"] for r in sel)[len(sel)//2]))
p("")
p("Balansefordeling: de 351 mot kohorten")
p("%-14s | %-20s | %-20s | %-26s" % ("balansegruppe","andel av de 351","andel av kohorten","apenandel i gruppen"))
for b in BANDS:
    k=sum(1 for r in op if r["band"]==b); n=sum(1 for r in rows if r["band"]==b)
    p("%-14s | %-20s | %-20s | %-26s" % (b,"%d/%d = %.1f %%"%(k,len(op),100*k/len(op)),
      "%d/%d = %.1f %%"%(n,len(rows),100*n/len(rows)), pct(k,n)))
p("")
tot_ta=sum(r["total_assets"] for r in rows if r["total_assets"] is not None)
op_ta=sum(r["total_assets"] for r in op if r["total_assets"] is not None)
p("De 351 er 6,8 %% av boene, men %.1f %% av kohortens samlede bokforte totalkapital (%.0f av %.0f mill. kr)."
  % (100*op_ta/tot_ta, op_ta/1e6, tot_ta/1e6))
inn=[r for r in rows if r["utfall"]=="innstilt"]
inn_ta=sum(r["total_assets"] for r in inn if r["total_assets"] is not None)
p("De 3 897 innstilte er 75,5 %% av boene, men bare %.1f %% av totalkapitalen." % (100*inn_ta/tot_ta))
p("")
p("Storrelsesfordeling i tall (totalkapital, NOK):")
for lab,sel in (("kohort",rows),("innstilt",inn),("avsluttet",[r for r in rows if r["utfall"]=="avsluttet"]),("apen",op)):
    v=sorted(r["total_assets"] for r in sel if r["total_assets"] is not None)
    p("  %-10s n=%4d  p10=%10.0f p25=%10.0f p50=%10.0f p75=%11.0f p90=%12.0f" %
      (lab,len(v),v[int(.10*len(v))],v[int(.25*len(v))],v[len(v)//2],v[int(.75*len(v))],v[int(.90*len(v))]))
u=stats.mannwhitneyu([r["total_assets"] for r in op if r["total_assets"] is not None],
                     [r["total_assets"] for r in inn if r["total_assets"] is not None],alternative="greater")
p("  Mann-Whitney apen vs innstilt (totalkapital): U = %.0f, p = %.2g (ensidig storre)" % (u.statistic,u.pvalue))

p("")
p("Kontroll: er 'apen' bare en langsom innstilling? Blant de som ALLEREDE er avgjort,")
p("hvor stor andel av hver balansegruppe endte ordinaert avsluttet (dvs. hadde midler):")
for b in BANDS:
    sel=[r for r in rows if r["band"]==b and r["utfall"]!="aapen"]
    p("  %-14s %s" % (b, pct(sum(1 for r in sel if r["utfall"]=="avsluttet"),len(sel))))

# sign test for retten-trenden (fra B5/08)
p("")
p("Tilleggstest til B5/08: 16 av 16 domstoler med n >= 40 i bade 2023 og 2026 steg.")
p("  Fortegnstest (binomial, p = 0,5): p = %.2g" % (stats.binomtest(16,16,0.5).pvalue))

with io.open(os.path.join(D,"B5-09-storrelse.txt"),"w",encoding="utf-8") as f:
    f.write("\n".join(OUT)+"\n")
print("\nSKREV B5-09-storrelse.txt")
