# -*- coding: utf-8 -*-
"""
Genererer figur-4-kumulativ.svg for forskningsstudien «Tomme bo».

Alle tall er lest fra figurer/domstol-modningskurve-cif.tsv. De faa tallene som
IKKE staar i den fila, staar i FERDIG-MANUS.md og er paalagt av figurteksten:
267 / 205 dager (kap. 6-tabellen), +62 dager [36-98], og ett-aarsverdiene
57,1 % / 65,2 % (fasthorisont-tabellen i kap. 4, harmonisert i 13.12).

Designsystemet er laast og delt med de sju soesterfigurene; y-etikettene,
tittelblokkens baselinjer og fotkonvensjonen foelger figur-1-historikk.svg.
"""
import io, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TSV = os.path.join(ROOT, "domstol-modningskurve-cif.tsv")
OUT = os.path.join(ROOT, "svg", "figur-4-kumulativ.svg")

# ---------------------------------------------------------------- palett (laast)
PAPIR, BAND = "#f5f0e6", "#e9e1d4"
BLEKK, DEMPET, HAAR = "#171815", "#625e55", "#d8cfbe"
BYGG, OVRIGE, AKSENT = "#9a4d35", "#2e6f91", "#b9782f"

FONT = "Euclid Circular B, Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif"
TABS = "font-variant-numeric:tabular-nums"

# ---------------------------------------------------------------- data
rows = []
with io.open(TSV, encoding="utf-8") as fh:
    for line_ in fh:
        s = line_.strip()
        if not s or s.startswith("#") or s.startswith("dager\t"):
            continue
        d, b, o, rb, ro = s.split("\t")
        rows.append((int(d), float(b), float(o), int(rb), int(ro)))

DAY_MAX = rows[-1][0]
byggm = dict((r[0], r[1]) for r in rows)
ovrm  = dict((r[0], r[2]) for r in rows)
riskb = dict((r[0], r[3]) for r in rows)
risko = dict((r[0], r[4]) for r in rows)
days  = sorted(byggm)

# kurven skal avsluttes der risikomengden i EN av gruppene faller under ti bo
assert min(riskb[DAY_MAX], risko[DAY_MAX]) >= 10, "siste punkt bryter minstecelleregelen"

# ---------------------------------------------------------------- geometri
W, H = 1200, 818
ML = 76                                # venstre marg: tittel, y-etiketter, foter
PX0, PX1 = 100.0, 982.0                # plottets x-utstrekning (dag 0 .. dag 980)
GUT = 998.0                            # etikettrenne til hoyre (direkte merking)
PY0, PY1 = 180.0, 618.0                # y for 80 % og 0 %
YMAX = 0.80

def X(day): return PX0 + day * (PX1 - PX0) / DAY_MAX
def Y(p):   return PY1 - p * ((PY1 - PY0) / YMAX)

def interp(m, day):
    if day in m: return m[day]
    lo = max(d for d in m if d <= day)
    hi = min(d for d in m if d >= day)
    return m[lo] + (day - lo) / float(hi - lo) * (m[hi] - m[lo])

def nb(n):                              # tusenskille = hardt mellomrom
    s = str(n)
    return s if len(s) <= 3 else s[:-3] + "&#160;" + s[-3:]

def pct1(x):                            # norsk desimalskilletegn
    return ("%.1f" % (x * 100)).replace(".", ",")

def f(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")

# ---------------------------------------------------------------- byggeklosser
out = []
add = out.append

def text(x, y, s, size=12.5, fill=DEMPET, weight=None, anchor=None, ls=None):
    a = ['<text x="%s" y="%s" font-family="%s" font-size="%s" fill="%s"'
         % (f(x), f(y), FONT, size, fill)]
    if weight: a.append('font-weight="%s"' % weight)
    if anchor: a.append('text-anchor="%s"' % anchor)
    style = TABS
    if ls:
        a.append('letter-spacing="%s"' % ls)
        style = "letter-spacing:%s;%s" % (ls, TABS)
    a.append('font-variant-numeric="tabular-nums" style="%s"' % style)
    add(" ".join(a) + ">" + s + "</text>")

def line(x1, y1, x2, y2, stroke=HAAR, w=1, dash=None):
    a = ['<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"'
         % (f(x1), f(y1), f(x2), f(y2), stroke, w)]
    if dash: a.append('stroke-dasharray="%s"' % dash)
    add(" ".join(a) + "/>")

# ---------------------------------------------------------------- dokument
add('<?xml version="1.0" encoding="UTF-8"?>')
add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
    'preserveAspectRatio="xMidYMid meet" role="img" '
    'aria-labelledby="fig4-tittel fig4-desc" width="%d" height="%d">' % (W, H, W, H))
add('  <title id="fig4-tittel">Hvor lang tid tar det før boet erklæres tomt?</title>')
add('  <desc id="fig4-desc">Kurvediagram med verdiakse fra 0 til 80 prosent og tidsakse fra '
    'dag 0 til dag 980. To kumulative insidenskurver (Aalen–Johansen) for innstilling av '
    'konkursbo etter konkursloven § 135, med ordinær avslutning som konkurrerende hendelse: '
    'utførende bygg og anlegg i varm rust, øvrige næringer i kjølig blå. Byggkurven ligger '
    'under den øvrige gjennom hele forløpet og krysser den aldri; feltet mellom kurvene er '
    'tonet. Halvparten av boene er innstilt etter 205 dager i øvrige næringer og etter '
    '267 dager i bygg, en medianforskjell på 62 dager. Ved ett år er 65,2 prosent av de '
    'øvrige boene innstilt mot 57,1 prosent i bygg, en forskjell på 8,1 prosentpoeng. Ved '
    'dag 980 står bygg på 72,1 prosent og øvrige på 77,7 prosent; der avsluttes kurvene '
    'fordi risikomengden nærmer seg ti bo. Risikomengden er skrevet som en tallrekke under '
    'aksen: 1 280 og 3 885 bo ved dag 0, 434 og 1 049 ved dag 364, 12 og 25 ved dag 980.</desc>')
add('  <g font-family="%s" font-variant-numeric="tabular-nums" style="%s">' % (FONT, TABS))
add('<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (W, H, PAPIR))

# ---- tittelblokk (venstrestilt mot samme marg som y-etikettene og foten)
text(ML, 46, "FIGUR 4", 11, DEMPET, "500", ls="0.14em")
text(ML, 78, "Hvor lang tid tar det før boet erklæres tomt?", 21, BLEKK, "600")
text(ML, 106, "Kumulativ insidens (Aalen–Johansen) for innstilling etter konkursloven "
              "§&#160;135, med ordinær avslutning som konkurrerende hendelse.", 14.5, DEMPET)
text(ML, 126, "Leses som andelen bo innstilt innen dag x — ikke som en overlevelseskurve. "
              "Byggkurven ligger under den øvrige gjennom hele forløpet.", 14.5, DEMPET)

# ---- rutenett bak dataene; linja brytes rundt etiketten, aksen ved 0 er den ene akselinja
for p, x1 in ((0.20, PX0), (0.40, PX0), (0.60, PX0), (0.80, 122.0)):
    line(x1, Y(p), PX1, Y(p), HAAR, 1)
line(PX0, Y(0), PX1, Y(0), HAAR, 1.5)
for p in (0, 0.20, 0.40, 0.60, 0.80):
    lab = "%d" % round(p * 100) + ("&#160;%" if p == 0.80 else "")
    text(ML, Y(p) - 5, lab, 12.5, DEMPET)

# ---- feltet mellom kurvene: differansen er funnet
top = ["%s,%s" % (f(X(d)), f(Y(ovrm[d]))) for d in days]
bot = ["%s,%s" % (f(X(d)), f(Y(byggm[d]))) for d in reversed(days)]
add('<path d="M %s L %s Z" fill="%s"/>' % (top[0], " L ".join(top[1:] + bot), BAND))

# ---- 50 %-terskelen (messing)
y50, xb50, xo50 = Y(0.50), X(267), X(205)
line(124.0, y50, xb50 + 7, y50, AKSENT, 1, dash="5 5")
text(ML, y50 - 5, "50&#160;%", 12.5, AKSENT, "600")

# ---- kurvene: bygg er hovedserien og faar den tyngste streken
for m, col, wdt in ((ovrm, OVRIGE, 2.5), (byggm, BYGG, 3.0)):
    pts = " ".join("%s,%s" % (f(X(d)), f(Y(m[d]))) for d in days)
    add('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" '
        'stroke-linejoin="round" stroke-linecap="round"/>' % (pts, col, wdt))

for x, col in ((xo50, OVRIGE), (xb50, BYGG)):
    add('<circle cx="%s" cy="%s" r="4.6" fill="%s" stroke="%s" stroke-width="2"/>'
        % (f(x), f(y50), col, PAPIR))

# ---- direkte merking ved kurveenden (ingen legende)
xe = X(DAY_MAX)
yb_e, yo_e = Y(byggm[DAY_MAX]), Y(ovrm[DAY_MAX])
for y, col in ((yo_e, OVRIGE), (yb_e, BYGG)):
    add('<circle cx="%s" cy="%s" r="3.6" fill="%s"/>' % (f(xe), f(y), col))
text(GUT, yo_e - 7, "Øvrige næringer", 13, OVRIGE, "600")
text(GUT, yo_e + 12, pct1(ovrm[DAY_MAX]) + "&#160;%", 12.5, OVRIGE)
text(GUT, yb_e + 7, "Bygg og anlegg", 13, BYGG, "600")
text(GUT, yb_e + 26, pct1(byggm[DAY_MAX]) + "&#160;%", 12.5, BYGG)

# ---- annotasjon: ett år
x365 = X(365)
yb365, yo365 = Y(interp(byggm, 365)), Y(interp(ovrm, 365))
line(x365, yo365, x365, yb365, AKSENT, 1)
line(x365 - 5, yo365, x365 + 5, yo365, AKSENT, 1)
line(x365 - 5, yb365, x365 + 5, yb365, AKSENT, 1)
line(x365, yb365, x365, 319, AKSENT, 1)
line(x365, 319, x365 + 8, 319, AKSENT, 1)
text(x365 + 14, 328, 'Ved ett år er <tspan fill="%s" font-weight="600">65,2&#160;%%</tspan> '
     'av de øvrige boene innstilt,' % OVRIGE, 12.5, BLEKK)
text(x365 + 14, 346, 'mot <tspan fill="%s" font-weight="600">57,1&#160;%%</tspan> i bygg '
     '— 8,1 prosentpoeng lavere.' % BYGG, 12.5, BLEKK)

# ---- annotasjon: median
line(xb50, y50 + 8, xb50, 388, AKSENT, 1)
line(xb50, 388, xb50 + 8, 388, AKSENT, 1)
text(xb50 + 14, 394, '<tspan fill="%s" font-weight="600">267</tspan> dager før halvparten av '
     'byggeboene er innstilt — mot <tspan fill="%s" font-weight="600">205</tspan> dager i '
     'øvrige næringer.' % (BYGG, OVRIGE), 12.5, BLEKK)
text(xb50 + 14, 413, "Medianforskjell +62 dager [bootstrap-KI 36–98].", 11, DEMPET)

# ---- annotasjon: hvor kurven stopper
line(PX1, 586, PX1, 614, AKSENT, 1)
text(PX1, 560, "Kurven avsluttes ved dag 980.", 12.5, BLEKK, anchor="end")
text(PX1, 578, "Fra dag 987 er færre enn ti byggebo igjen i risikomengden.",
     11, DEMPET, anchor="end")

# ---- x-akse og risikomengde (samme kolonner)
TICKS = [0, 182, 364, 546, 728, 910, 980]
def anc(d):
    return None if d == TICKS[0] else ("end" if d == TICKS[-1] else "middle")

for d in TICKS:
    text(X(d), 642, str(d), 12.5, DEMPET, anchor=anc(d))
text(GUT, 642, "dager", 12.5, DEMPET)

text(ML, 674, "BO I RISIKOMENGDEN", 11, DEMPET, "500", ls="0.14em")
for d in TICKS:
    text(X(d), 697, nb(riskb[d]), 12.5, BYGG, anchor=anc(d))
    text(X(d), 718, nb(risko[d]), 12.5, OVRIGE, anchor=anc(d))
text(GUT, 697, "bygg", 12.5, BYGG)
text(GUT, 718, "øvrige", 12.5, OVRIGE)

# ---- noter og kilde
text(ML, 748, "Bygg = utførende bygg og anlegg (SN2007 41.2&#160;+&#160;42&#160;+&#160;43), "
              "n&#160;=&#160;1&#160;280; øvrige næringer n&#160;=&#160;3&#160;885. "
              "Kohort: konkursåpning 01.09.2023–31.12.2024.", 11, DEMPET)
text(ML, 764, "Ett-årstallene er fasthorisontverdiene ved dag 365; kurvens ukespunkt ved "
              "dag 364 leser 57,2 mot 65,1&#160;%. Differansen er ett enkeltbo på "
              "dag-365-grensen.", 11, DEMPET)
text(ML, 790, "Byggsikt · offentlig tilgjengelige registerkunngjøringer · utfall observert "
              "til 24.08.2026", 11, DEMPET)

add('  </g>')
add('</svg>')

with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(out) + "\n")

print("skrevet:", OUT)
print("dag 980  bygg %s  ovrige %s" % (pct1(byggm[980]), pct1(ovrm[980])))
print("dag 364  bygg %s  ovrige %s" % (pct1(byggm[364]), pct1(ovrm[364])))
print("x(205)=%.2f x(267)=%.2f x(365)=%.2f  y50=%.2f" % (xo50, xb50, x365, y50))
print("yb365=%.2f yo365=%.2f  yb_end=%.2f yo_end=%.2f" % (yb365, yo365, yb_e, yo_e))
print("risiko siste: bygg %d / ovrige %d" % (riskb[DAY_MAX], risko[DAY_MAX]))
