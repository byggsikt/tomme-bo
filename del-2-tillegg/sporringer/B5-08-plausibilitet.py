# B5/08 Plausibilitet: oppbudsandelens niva og utvikling, mot 2021-rapporten og Konkursradet.
import io, os, math, collections
import numpy as np
from scipy import stats

D = os.path.dirname(os.path.abspath(__file__))
OUT = []
def p(*a):
    s = " ".join(str(x) for x in a); OUT.append(s); print(s.encode("ascii","replace").decode())

def wilson(k, n, z=1.959963985):
    if n == 0: return (float('nan'),)*3
    ph = k/n; d = 1+z*z/n
    c = (ph+z*z/(2*n))/d
    h = z*math.sqrt(ph*(1-ph)/n + z*z/(4*n*n))/d
    return (100*ph, 100*max(0.,c-h), 100*min(1.,c+h))
def pct(k,n):
    a,lo,hi = wilson(k,n); return "%d/%d = %.1f %% [%.1f-%.1f]" % (k,n,a,lo,hi)
def newcombe(k1,n1,k2,n2):
    # risikodifferanse p1-p2 med Newcombes Wilson-baserte intervall
    _,l1,u1 = wilson(k1,n1); _,l2,u2 = wilson(k2,n2)
    l1,u1,l2,u2 = l1/100,u1/100,l2/100,u2/100
    p1,p2 = k1/n1, k2/n2
    d = p1-p2
    lo = d - math.sqrt((p1-l1)**2 + (u2-p2)**2)
    hi = d + math.sqrt((u1-p1)**2 + (p2-l2)**2)
    return 100*d, 100*lo, 100*hi

def parse_blocks(path):
    blocks, cur = {}, None
    for line in io.open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("==="):
            cur = line.strip("= ").strip(); blocks[cur] = []
        elif cur and line.strip():
            blocks[cur].append([c.strip() for c in line.split(" | ")])
    return blocks

B1 = parse_blocks(os.path.join(D,"B5-01-grunnlag-per-aar.txt"))
B2 = parse_blocks(os.path.join(D,"B5-02-grunnlag-per-tingrett.txt"))
B7 = parse_blocks(os.path.join(D,"B5-07-kontroller.txt"))

p("="*100)
p("B5 — PLAUSIBILITET: hvor mange konkurser apnes pa skyldnerens eget oppbud?")
p("Datauttak as-of 24.08.2026. Populasjon: alle konkursapninger i kunngjoringskorpuset")
p("(distinkte selskaper, forste 'Konkurs - apning'). ALLE er AS/ASA — korpuset har ingen ENK-konkurser.")
p("="*100)

# ---------- 1. per ar ----------
p("")
p("## 1.1 Andel med feltet «Apnet etter: Oppbud» per ar")
p("%-6s | %6s | %7s | %-28s | %-22s" % ("ar","apninger","oppbud","andel [95 % Wilson]","ikke-oppbud"))
years = []
for r in B1["per_aar"]:
    y, n, k = int(r[0]), int(r[1]), int(r[2])
    years.append((y,n,k))
    a,lo,hi = wilson(k,n)
    p("%-6s | %6d | %7d | %.1f %% [%.1f-%.1f]%s | %d (%.1f %%)" %
      (y,n,k,a,lo,hi," "*max(0,28-len("%.1f %% [%.1f-%.1f]"%(a,lo,hi))),n-k,100*(n-k)/n))
p("(2026 dekker 01.01-24.08. 2021-2022 er tynnet av retensjon: konkurskunngjoringer purges etter ~5 ar,")
p(" landmine L1 — 106 og 599 apninger mot Norges reelle ~3 000 per ar.)")

p("")
p("## 1.2 Er stigningen reell? Differanser med Newcombe-intervall")
d = dict((y,(n,k)) for y,n,k in years)
for a_,b_ in ((2023,2026),(2023,2025),(2024,2026),(2022,2025)):
    n1,k1 = d[b_]; n2,k2 = d[a_]
    rd,lo,hi = newcombe(k1,n1,k2,n2)
    p("  %d vs %d: %+.1f pp [%+.1f, %+.1f]" % (b_,a_,rd,lo,hi))
tab = np.array([[k, n-k] for y,n,k in years if y >= 2023])
chi2, pv, dof, _ = stats.chi2_contingency(tab)
p("  Heterogenitet 2023-2026 (khikvadrat, df=%d): chi2 = %.1f, p = %.2g" % (dof, chi2, pv))
# Cochran-Armitage trendtest
ys = np.array([y for y,n,k in years if y>=2023], float)
ks = np.array([k for y,n,k in years if y>=2023], float)
ns = np.array([n for y,n,k in years if y>=2023], float)
pbar = ks.sum()/ns.sum(); ybar = (ns*ys).sum()/ns.sum()
T = (ns*(ks/ns - pbar)*(ys-ybar)).sum()
V = pbar*(1-pbar)*(ns*(ys-ybar)**2).sum()
z = T/math.sqrt(V)
p("  Cochran-Armitage trendtest 2023-2026: z = %.2f, p = %.2g (tosidig)" % (z, 2*(1-stats.norm.cdf(abs(z)))))

p("")
p("## 1.3 Stiger oppbudene, eller faller begjaringene? Volum per ar (2026 skalert til helar x 365/236)")
p("%-6s | %9s | %9s | %9s" % ("ar","apninger","oppbud","ikke-oppbud"))
for y,n,k in years:
    f = 365/236 if y == 2026 else 1.0
    mark = " (skalert)" if y == 2026 else ""
    p("%-6s | %9.0f | %9.0f | %9.0f%s" % (y, n*f, k*f, (n-k)*f, mark))
p("  Endring 2024 -> 2026 (skalert helar): oppbud %+.0f %%, ikke-oppbud %+.0f %%" % (
   100*(d[2026][1]*365/236)/d[2024][1]-100, 100*((d[2026][0]-d[2026][1])*365/236)/(d[2024][0]-d[2024][1])-100))

p("")
p("## 1.4 Manedsserie 2025-2026 — er 2026-nivaet stabilt?")
p("%-9s | %5s | %6s | %6s | %6s" % ("mnd","n","oppbud","andel","ikke-opp"))
for r in B7["maaned_2026"]:
    m,n,k = r[0], int(r[1]), int(r[2])
    p("%-9s | %5d | %6d | %5.1f%% | %6d" % (m,n,k,100*k/n,n-k))

# ---------- 2. per tingrett ----------
p("")
p("="*100)
p("## 2. Per tingrett, alle apninger 2023-01-01..2026-08-24 (n = 12 821, tingrett utfylt 100,0 %)")
p("="*100)
MERGE = {
 "ASKER OG BÆRUM TINGRETT":"RINGERIKE, ASKER OG BÆRUM TINGRETT",
 "RINGERIKE OG HALLINGDAL TINGRETT":"RINGERIKE, ASKER OG BÆRUM TINGRETT",
 "NEDRE TELEMARK TINGRETT":"TELEMARK TINGRETT",
 "ØVRE TELEMARK TINGRETT":"TELEMARK TINGRETT",
 "SUNNMØRE TINGRETT":"MØRE OG ROMSDAL TINGRETT",
 "NORDMØRE OG ROMSDAL TINGRETT":"MØRE OG ROMSDAL TINGRETT",
 "VESTOPPLAND OG VALDRES TINGRETT":"VESTRE INNLANDET TINGRETT",
 "GUDBRANDSDAL TINGRETT":"VESTRE INNLANDET TINGRETT",
 "HEDMARKEN OG ØSTERDAL TINGRETT":"ØSTRE INNLANDET TINGRETT",
 "HARDANGER OG VOSS TINGRETT":"HORDALAND TINGRETT",
}
tot = collections.Counter(); opp = collections.Counter()
for r in B2["per_tingrett"]:
    nm = MERGE.get(r[0], r[0]); tot[nm] += int(r[1]); opp[nm] += int(r[2])
p("%-36s | %6s | %6s | %-26s" % ("tingrett (slatt sammen etter 2025-delingen)","n","oppbud","andel [95 %]"))
for nm,n in tot.most_common():
    p("%-36s | %6d | %6d | %s" % (nm, n, opp[nm], pct(opp[nm], n)))
p("  Spenn: %.1f %% til %.1f %% — ingen domstol pa 0 eller 100 %%." % (
   100*min(opp[nm]/tot[nm] for nm in tot), 100*max(opp[nm]/tot[nm] for nm in tot)))
tab = np.array([[opp[nm], tot[nm]-opp[nm]] for nm in tot if tot[nm] >= 50])
chi2, pv, dof, _ = stats.chi2_contingency(tab)
p("  Heterogenitet mellom domstoler (n >= 50, df=%d): chi2 = %.0f, p = %.2g" % (dof, chi2, pv))

# per tingrett per ar -> standardisering
cell = {}
for r in B2["per_tingrett_per_aar"]:
    nm = MERGE.get(r[0], r[0]); y = int(r[1])
    a,b = cell.get((nm,y),(0,0)); cell[(nm,y)] = (a+int(r[2]), b+int(r[3]))
p("")
p("## 2.1 Er stigningen en sammensetningseffekt (domstolsmiks) eller skjer den innad i domstolene?")
p("Direkte standardisering: hvert ars andeler veid med den SAMLEDE domstolsmiksen 2023-2026.")
w = dict((nm, tot[nm]/sum(tot.values())) for nm in tot)
p("%-6s | %-12s | %-14s | %-10s" % ("ar","raa andel","standardisert","domstoler"))
for y in (2023,2024,2025,2026):
    num = den = 0.0; nd = 0
    raw_n = raw_k = 0
    for nm in tot:
        n,k = cell.get((nm,y),(0,0))
        raw_n += n; raw_k += k
        if n >= 10:
            num += w[nm]*(k/n); den += w[nm]; nd += 1
    p("%-6s | %11.1f%% | %13.1f%% | %d av %d" % (y, 100*raw_k/raw_n, 100*num/den, nd, len(tot)))
p("Antall domstoler som steg / falt fra 2023 til 2026 (n >= 40 begge ar):")
up = dn = 0; det=[]
for nm in tot:
    n3,k3 = cell.get((nm,2023),(0,0)); n6,k6 = cell.get((nm,2026),(0,0))
    if n3 >= 40 and n6 >= 40:
        diff = 100*(k6/n6 - k3/n3); det.append((diff,nm,k3,n3,k6,n6))
        up += diff > 0; dn += diff <= 0
p("  steg: %d, falt: %d" % (up, dn))
for diff,nm,k3,n3,k6,n6 in sorted(det, reverse=True):
    p("    %-36s 2023 %5.1f%% (%d/%d) -> 2026 %5.1f%% (%d/%d)  %+.1f pp" %
      (nm, 100*k3/n3, k3,n3, 100*k6/n6, k6,n6, diff))

# ---------- 3. ekstern triangulering ----------
p("")
p("="*100)
p("## 3. Mot de eksterne holdepunktene")
p("="*100)
p("")
p("(a) 2021-rapporten, tabell 4 panel C, utvalg 2010-2019 (alle apninger ekskl. ENK):")
p("    begjaring 25,7 %% | oppbud 43,6 %% | tvangsavvikling 30,7 %%")
p("    Konkurs alene (tvangsavvikling er en egen kunngjoringstype hos oss):")
p("    43,6/(43,6+25,7) = %.1f %% oppbud." % (100*43.6/(43.6+25.7)))
n22 = sum(n for y,n,k in years if y <= 2022); k22 = sum(k for y,n,k in years if y <= 2022)
p("    Var maling i de arene korpuset rekker tilbake til (2021-2022): %s" % pct(k22,n22))
p("    A2s poolede 2019-2022: %s" % pct(int(B1["pooled_2019_2022"][0][2]), int(B1["pooled_2019_2022"][0][1])))
rd,lo,hi = newcombe(496,810,int(round(0.629*810)),810)
p("    Differanse mot 62,9 %%: %+.1f pp [%+.1f, %+.1f] — rapportens verdi ligger INNE i vart intervall." % (rd,lo,hi))
p("")
p("(b) Konkursradet 25.11.2025: begjaringer fra PRIVATE parter utgjor «noen fa prosentpoeng»;")
p("    ved Oslo tingrett under 2 %. Hva folger av det for var ikke-oppbudsgruppe?")
p("%-28s | %-24s | %-34s" % ("populasjon","ikke-oppbud","implisert offentlig andel AV ikke-oppbud"))
def implied(label, k, n):
    share = 100*(n-k)/n
    rows = []
    for priv in (2.0, 3.0, 5.0):
        pub = share - priv
        rows.append("%.0f %%" % (100*pub/share))
    p("%-28s | %-24s | privat 2/3/5 pp -> %s / %s / %s" % (label, "%d/%d = %.1f %%" % (n-k,n,share), *rows))
for y,n,k in years:
    if y >= 2023: implied("apninger %d" % y, k, n)
implied("kohorten 2023-09..2024-12", 3734, 5165)
osl = [r for r in B2["per_tingrett"] if r[0].startswith("OSLO")][0]
implied("OSLO 2023-2026", int(osl[2]), int(osl[1]))
p("    NB: dette er aritmetikk pa en EKSTERN pastand, ikke en maling i vart materiale.")
p("    Registeret navngir aldri rekvirenten: vi kan IKKE skille privat fra offentlig begjaring.")

with io.open(os.path.join(D,"B5-08-plausibilitet.txt"),"w",encoding="utf-8") as f:
    f.write("\n".join(OUT)+"\n")
print("\nSKREV B5-08-plausibilitet.txt")
