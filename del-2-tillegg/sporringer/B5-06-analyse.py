# B5/06 Analyse: plausibilitet (grunnlag) + timing + de 351 apne boene.
# Leser B5-05-kohortuttrekk.tsv (5 165 bo) og B5-01/B5-02-utdata. Skriver B5-06-analyse.txt.
import json, math, collections, io, sys, os

D = os.path.dirname(os.path.abspath(__file__))
OUT = []
def p(*a):
    s = " ".join(str(x) for x in a)
    OUT.append(s)
    print(s)

def wilson(k, n, z=1.959963985):
    if n == 0: return (float('nan'), float('nan'), float('nan'))
    ph = k / n
    d = 1 + z*z/n
    c = (ph + z*z/(2*n)) / d
    h = z*math.sqrt(ph*(1-ph)/n + z*z/(4*n*n)) / d
    return (100*ph, 100*max(0.0, c-h), 100*min(1.0, c+h))

def pct(k, n):
    a, lo, hi = wilson(k, n)
    return "%d/%d = %.1f %% [%.1f-%.1f]" % (k, n, a, lo, hi)

# ---------- last extract ----------
COLS = ["orgnr","opened","utfall","t_dager","grunnlag","tingrett","bransje","fy",
        "total_assets","equity","liabilities","operating_revenue","payroll_expenses",
        "amount_unit","currency","source_name","oppfolging"]
rows = []
with io.open(os.path.join(D,"B5-05-kohortuttrekk.tsv"), encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line.strip(): continue
        parts = line.split("\t")
        assert len(parts) == len(COLS), (len(parts), line[:80])
        r = dict(zip(COLS, parts))
        r["t_dager"] = int(r["t_dager"]) if r["t_dager"] else None
        r["oppfolging"] = int(r["oppfolging"])
        for k in ("total_assets","equity","liabilities","operating_revenue","payroll_expenses"):
            r[k] = float(r[k]) if r[k] not in ("", None) else None
        rows.append(r)

p("=" * 100)
p("B5 — PLAUSIBILITET OG TIMING. Datauttak as-of 24.08.2026. n =", len(rows))
p("=" * 100)
assert len(rows) == 5165
utf = collections.Counter(r["utfall"] for r in rows)
p("Utfall:", dict(utf))
assert utf["innstilt"] == 3897 and utf["avsluttet"] == 917 and utf["aapen"] == 351
p("Oppfolging (dager): min %d, median %d, max %d" % (
    min(r["oppfolging"] for r in rows),
    sorted(r["oppfolging"] for r in rows)[len(rows)//2],
    max(r["oppfolging"] for r in rows)))
gr = collections.Counter(r["grunnlag"] for r in rows)
p("Grunnlag:", dict(gr), " oppbudsandel:", pct(gr["oppbud"], len(rows)))
p("Valuta i regnskapsraden:", dict(collections.Counter(r["currency"] for r in rows)))
p("amount_unit:", dict(collections.Counter(r["amount_unit"] for r in rows)))
p("Regnskapsdekning (siste balanse FOR aapningsaaret):", pct(sum(1 for r in rows if r["total_assets"] is not None), len(rows)))
p("Regnskapsaar (fy):", dict(collections.Counter(r["fy"] for r in rows)))

# ---------- bygg-klassifisering fra studiens kart v3 ----------
byggmap = {}
try:
    km = json.load(io.open("../../del-1-hovedstudien/data/bransjekart-v3_2026-08-30.json", encoding="utf-8"))
    for e in km["kart"]:
        byggmap[e["etikett"]] = bool(e.get("er_bygg_F"))
except Exception as ex:
    p("ADVARSEL: klarte ikke lese bransjekart:", ex)
nmatch = sum(1 for r in rows if r["bransje"] in byggmap)
for r in rows:
    r["bygg"] = byggmap.get(r["bransje"])
p("Bransjekart v3: treff", pct(nmatch, len(rows)), " bygg(F):",
  pct(sum(1 for r in rows if r["bygg"]), nmatch))

# ---------- 1. TIMING ETTER GRUNNLAG ----------
p("")
p("#" * 100)
p("# 1. TIMING — andel innstilt innen faste horisonter (ingen sensurering under 601 dager)")
p("#" * 100)
HOR = [(91,"3 mnd"),(183,"6 mnd"),(274,"9 mnd"),(365,"12 mnd"),(548,"18 mnd"),(601,"601 d")]

def horizon_table(sub, label):
    n = len(sub)
    p("")
    p("%s (n = %d)" % (label, n))
    p("%-8s | %-28s | %-28s | %-24s" % ("horisont","innstilt (kum.)","ordinaert avsluttet (kum.)","uavklart"))
    for d, nm in HOR:
        ki = sum(1 for r in sub if r["utfall"] == "innstilt" and r["t_dager"] <= d)
        ka = sum(1 for r in sub if r["utfall"] == "avsluttet" and r["t_dager"] <= d)
        ku = n - ki - ka
        p("%-8s | %-28s | %-28s | %-24s" % (nm, pct(ki,n), "%d/%d = %.1f %%"%(ka,n,100*ka/n), "%d/%d = %.1f %%"%(ku,n,100*ku/n)))

horizon_table(rows, "ALLE")
for g in ("oppbud","ingen_felt"):
    horizon_table([r for r in rows if r["grunnlag"] == g], "GRUNNLAG = " + g)

# 24 mnd = delkohort med fullt 730-dagers vindu
sub730 = [r for r in rows if r["opened"] <= "2024-08-24"]
p("")
p("24 MND (730 d) — delkohort aapnet <= 2024-08-24, n = %d" % len(sub730))
for lab, sel in (("alle", sub730),
                 ("oppbud", [r for r in sub730 if r["grunnlag"]=="oppbud"]),
                 ("ingen_felt", [r for r in sub730 if r["grunnlag"]=="ingen_felt"])):
    n = len(sel)
    ki = sum(1 for r in sel if r["utfall"]=="innstilt" and r["t_dager"] <= 730)
    ka = sum(1 for r in sel if r["utfall"]=="avsluttet" and r["t_dager"] <= 730)
    p("  %-11s innstilt %s | ordinaert %d/%d = %.1f %% | uavklart %d/%d = %.1f %%"
      % (lab, pct(ki,n), ka,n,100*ka/n, n-ki-ka,n,100*(n-ki-ka)/n))

# kvantiler
p("")
p("Kvantiler, dager fra aapning til innstilling (kun de innstilte):")
p("%-12s | %6s | %5s %5s %5s %5s %5s" % ("gruppe","n","p10","p25","p50","p75","p90"))
for lab, sel in (("alle", rows), ("oppbud",[r for r in rows if r["grunnlag"]=="oppbud"]),
                 ("ingen_felt",[r for r in rows if r["grunnlag"]=="ingen_felt"])):
    v = sorted(r["t_dager"] for r in sel if r["utfall"]=="innstilt")
    q = lambda f: v[min(len(v)-1, int(f*len(v)))]
    p("%-12s | %6d | %5d %5d %5d %5d %5d" % (lab, len(v), q(.10), q(.25), q(.50), q(.75), q(.90)))
p("Kvantiler, dager til ORDINAER avslutning (kun de ordinaert avsluttede):")
for lab, sel in (("alle", rows), ("oppbud",[r for r in rows if r["grunnlag"]=="oppbud"]),
                 ("ingen_felt",[r for r in rows if r["grunnlag"]=="ingen_felt"])):
    v = sorted(r["t_dager"] for r in sel if r["utfall"]=="avsluttet")
    q = lambda f: v[min(len(v)-1, int(f*len(v)))]
    p("%-12s | %6d | %5d %5d %5d %5d %5d" % (lab, len(v), q(.10), q(.25), q(.50), q(.75), q(.90)))

# ---------- 2. TIMING PER TINGRETT ----------
p("")
p("#" * 100)
p("# 2. TIMING PER TINGRETT — de 10 storste domstolene i kohorten")
p("#" * 100)
bycourt = collections.defaultdict(list)
for r in rows: bycourt[r["tingrett"]].append(r)
top = sorted(bycourt.items(), key=lambda kv: -len(kv[1]))[:10]
p("")
p("%-36s | %5s | %7s | %7s %7s %7s %7s %7s %7s | %7s | %6s | %7s" % (
  "tingrett","n","oppbud","3 mnd","6 mnd","9 mnd","12 mnd","18 mnd","601 d","24 mnd*","median","apne na"))
for name, sel in top:
    n = len(sel)
    cells = []
    for d, nm in HOR:
        k = sum(1 for r in sel if r["utfall"]=="innstilt" and r["t_dager"] <= d)
        cells.append("%.1f" % (100*k/n))
    s730 = [r for r in sel if r["opened"] <= "2024-08-24"]
    k730 = sum(1 for r in s730 if r["utfall"]=="innstilt" and r["t_dager"] <= 730)
    v = sorted(r["t_dager"] for r in sel if r["utfall"]=="innstilt")
    med = v[len(v)//2] if v else -1
    op = sum(1 for r in sel if r["utfall"]=="aapen")
    p("%-36s | %5d | %6.1f%% | %6s%% %6s%% %6s%% %6s%% %6s%% %6s%% | %5.1f%% | %6d | %5.1f%%" % (
      name, n, 100*sum(1 for r in sel if r["grunnlag"]=="oppbud")/n,
      cells[0],cells[1],cells[2],cells[3],cells[4],cells[5],
      100*k730/len(s730), med, 100*op/n))
p("* 24 mnd er regnet paa delkohorten aapnet <= 2024-08-24 (n per domstol i egen tabell under).")
p("")
p("Tellere og nevnere for de 10 storste (samme rekkefolge):")
for name, sel in top:
    n = len(sel); s730=[r for r in sel if r["opened"]<="2024-08-24"]
    p("  %-36s n=%d  3m=%d 6m=%d 9m=%d 12m=%d 18m=%d 601d=%d | 730d: %d/%d | uavklart601=%d | apne=%d | oppbud=%d" % (
      name, n,
      *[sum(1 for r in sel if r["utfall"]=="innstilt" and r["t_dager"]<=d) for d,_ in HOR],
      sum(1 for r in s730 if r["utfall"]=="innstilt" and r["t_dager"]<=730), len(s730),
      sum(1 for r in sel if r["t_dager"] is None or r["t_dager"]>601),
      sum(1 for r in sel if r["utfall"]=="aapen"),
      sum(1 for r in sel if r["grunnlag"]=="oppbud")))
p("")
p("Spredning over ALLE 23 domstoler i kohorten (andel innstilt innen 601 d):")
allc = []
for name, sel in sorted(bycourt.items(), key=lambda kv: -len(kv[1])):
    n=len(sel); k=sum(1 for r in sel if r["utfall"]=="innstilt" and r["t_dager"]<=601)
    allc.append((100*k/n, name, k, n))
for v,name,k,n in sorted(allc, reverse=True):
    p("  %-36s %s" % (name, pct(k,n)))

# ---------- 3. UAVKLART VED 601 DAGER + DE 351 ----------
p("")
p("#" * 100)
p("# 3. UAVKLARTE BO — fast horisont 601 dager, og de 351 som stod apne 24.08.2026")
p("#" * 100)
p("")
p("Uavklart ved dag 601 (alle 5 165 har minst 601 dagers oppfolging):")
for lab, sel in (("alle", rows), ("oppbud",[r for r in rows if r["grunnlag"]=="oppbud"]),
                 ("ingen_felt",[r for r in rows if r["grunnlag"]=="ingen_felt"])):
    n=len(sel); k=sum(1 for r in sel if r["t_dager"] is None or r["t_dager"]>601)
    p("  %-11s %s" % (lab, pct(k,n)))
p("")
p("Fortsatt apent 24.08.2026 (as-of, ulik oppfolgingstid 601-1088 d):")
for lab, sel in (("alle", rows), ("oppbud",[r for r in rows if r["grunnlag"]=="oppbud"]),
                 ("ingen_felt",[r for r in rows if r["grunnlag"]=="ingen_felt"])):
    n=len(sel); k=sum(1 for r in sel if r["utfall"]=="aapen")
    p("  %-11s %s" % (lab, pct(k,n)))
op = [r for r in rows if r["utfall"]=="aapen"]
v = sorted(r["oppfolging"] for r in op)
p("")
p("Hvor lenge har de 351 statt apne (dager siden apning): min %d, p25 %d, median %d, p75 %d, maks %d"
  % (v[0], v[len(v)//4], v[len(v)//2], v[3*len(v)//4], v[-1]))
p("  over 730 d: %s | over 900 d: %s" % (
    pct(sum(1 for x in v if x>730), len(v)), pct(sum(1 for x in v if x>900), len(v))))

p("")
p("GRUNNLAGSMIKS blant de 351 vs kohorten:")
for g in ("oppbud","ingen_felt"):
    p("  %-11s apne %s | kohort %s" % (g, pct(sum(1 for r in op if r["grunnlag"]==g), len(op)),
                                        pct(sum(1 for r in rows if r["grunnlag"]==g), len(rows))))
p("")
p("DOMSTOLSMIKS blant de 351 (topp 12) — andel av domstolens egne bo som star apne:")
oc = collections.Counter(r["tingrett"] for r in op)
p("  %-36s | %6s | %6s | %-26s" % ("tingrett","apne","kohort","apenandel i domstolen"))
for name, k in oc.most_common(12):
    n = len(bycourt[name])
    p("  %-36s | %6d | %6d | %s" % (name, k, n, pct(k,n)))
p("  Domstoler helt uten apne bo: %d av %d" % (
    sum(1 for nm in bycourt if oc.get(nm,0)==0), len(bycourt)))

p("")
p("BYGG vs OVRIGE blant de 351:")
for lab, f in (("bygg (F)", lambda r: r["bygg"] is True), ("ovrige", lambda r: r["bygg"] is False)):
    k = sum(1 for r in op if f(r)); n = sum(1 for r in rows if f(r))
    p("  %-10s apne %s (av kohortens %d)" % (lab, pct(k, n), n))

# ---------- 4. STORRELSE ----------
p("")
p("#" * 100)
p("# 4. STORRELSE — er de apne boene de store?  (siste balanse for aapningsaaret, hele kroner)")
p("#" * 100)
def band(r):
    ta = r["total_assets"]
    if ta is None: return "uten regnskap"
    if ta >= 5e6: return "5 MNOK+"
    if ta >= 1e6: return "1-5 MNOK"
    return "under 1 MNOK"
BANDS = ["5 MNOK+","1-5 MNOK","under 1 MNOK","uten regnskap"]
p("")
p("%-14s | %6s | %-26s | %-26s | %-26s" % ("balansegruppe","n","innstilt","ordinaert avsluttet","fortsatt apent"))
for b in BANDS:
    sel = [r for r in rows if band(r)==b]; n=len(sel)
    p("%-14s | %6d | %-26s | %-26s | %-26s" % (b, n,
      pct(sum(1 for r in sel if r["utfall"]=="innstilt"), n),
      pct(sum(1 for r in sel if r["utfall"]=="avsluttet"), n),
      pct(sum(1 for r in sel if r["utfall"]=="aapen"), n)))
p("")
p("Fordelingen INNAD i hver utfallsgruppe (kolonneprosent):")
p("%-14s | %-18s | %-18s | %-18s | %-18s" % ("balansegruppe","kohort","innstilt","avsluttet","apen"))
for b in BANDS:
    line = ["%-14s" % b]
    for sel in (rows, [r for r in rows if r["utfall"]=="innstilt"],
                [r for r in rows if r["utfall"]=="avsluttet"], op):
        k = sum(1 for r in sel if band(r)==b)
        line.append("%-18s" % ("%d/%d = %.1f %%" % (k, len(sel), 100*k/len(sel))))
    p(" | ".join(line))
p("")
def med(vals):
    v = sorted(x for x in vals if x is not None)
    return (len(v), v[len(v)//4] if v else 0, v[len(v)//2] if v else 0, v[3*len(v)//4] if v else 0)
p("Totalkapital (NOK) etter utfall: n, p25, median, p75")
for lab, sel in (("kohort",rows),("innstilt",[r for r in rows if r["utfall"]=="innstilt"]),
                 ("avsluttet",[r for r in rows if r["utfall"]=="avsluttet"]),("apen",op)):
    n,q1,q2,q3 = med([r["total_assets"] for r in sel])
    p("  %-10s n=%4d  p25=%12s  median=%12s  p75=%12s" % (lab,n,"%.0f"%q1,"%.0f"%q2,"%.0f"%q3))
p("Driftsinntekter (NOK) etter utfall: n, p25, median, p75")
for lab, sel in (("kohort",rows),("innstilt",[r for r in rows if r["utfall"]=="innstilt"]),
                 ("avsluttet",[r for r in rows if r["utfall"]=="avsluttet"]),("apen",op)):
    n,q1,q2,q3 = med([r["operating_revenue"] for r in sel])
    p("  %-10s n=%4d  p25=%12s  median=%12s  p75=%12s" % (lab,n,"%.0f"%q1,"%.0f"%q2,"%.0f"%q3))
p("Lonnskostnad (NOK, ansatt-proxy) etter utfall: n med verdi, andel > 0, median blant >0")
for lab, sel in (("kohort",rows),("innstilt",[r for r in rows if r["utfall"]=="innstilt"]),
                 ("avsluttet",[r for r in rows if r["utfall"]=="avsluttet"]),("apen",op)):
    vals = [r["payroll_expenses"] for r in sel if r["payroll_expenses"] is not None]
    pos = sorted(x for x in vals if x and x > 0)
    p("  %-10s n=%4d  >0: %-24s median(>0)=%s" % (lab, len(vals),
      pct(len(pos), len(vals)) if vals else "-", "%.0f" % pos[len(pos)//2] if pos else "-"))

p("")
p("Balansegruppe x grunnlag (andel innstilt) — er storrelsen eller grunnlaget som styrer?")
p("%-14s | %-26s | %-26s" % ("balansegruppe","oppbud","ingen_felt"))
for b in BANDS:
    cells=[]
    for g in ("oppbud","ingen_felt"):
        sel=[r for r in rows if band(r)==b and r["grunnlag"]==g]
        cells.append(pct(sum(1 for r in sel if r["utfall"]=="innstilt"), len(sel)) if sel else "-")
    p("%-14s | %-26s | %-26s" % (b, cells[0], cells[1]))
p("")
p("Grunnlagsmiks innad i hver balansegruppe (oppbudsandel):")
for b in BANDS:
    sel=[r for r in rows if band(r)==b]
    p("  %-14s %s" % (b, pct(sum(1 for r in sel if r["grunnlag"]=="oppbud"), len(sel))))

with io.open(os.path.join(D,"B5-06-analyse.txt"),"w",encoding="utf-8") as f:
    f.write("\n".join(OUT) + "\n")
print("\nSKREV B5-06-analyse.txt")
