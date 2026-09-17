# -*- coding: utf-8 -*-
"""
Genererer figur-1-historikk.svg — «Femti år med tall — og tre diskrete målepunkter».

Alle tall hentes fra ../../historisk-maalepunkter-2026-08-30.csv.
Skriptet regner ut koordinater, klipper hårstrekene rundt tekst, og
kontrollerer at ingen tekst går utenfor plottet eller kolliderer.
"""
import csv, io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "historisk-maalepunkter-2026-08-30.csv"))
OUT = os.path.normpath(os.path.join(HERE, "..", "figur-1-historikk.svg"))

# ---------------------------------------------------------------- data
rows = []
with io.open(DATA, encoding="utf-8") as fh:
    for r in csv.DictReader(fh, delimiter=";"):
        rows.append(r)

plottable = [r for r in rows if r["plottes"] == "ja"]
assert len(plottable) == 3, plottable
V = {r["periode"]: r["verdi"] for r in plottable}
assert V["1976"] == "40" and V["1996"] == "75" and V["2023/24-kohorten"] == "75.5", V
P1976, P1996, PKOH = 40.0, 75.0, 75.5

# ---------------------------------------------------------------- palett
PAPIR    = "#f5f0e6"
PAPIRDYP = "#e9e1d4"
BLEKK    = "#171815"
DEMPET   = "#625e55"
HAAR     = "#d8cfbe"
BYGG     = "#9a4d35"   # rust  — denne studiens måling
OVRIG    = "#2e6f91"   # blå   — departementets gjengitte tall
AKSENT   = "#b9782f"   # messing — referanselinje
NOYTRAL  = "#8c9a8e"   # ikke-data

# Kun paletten brukes; sjaktene tegnes som palettfarge med gjennomsiktighet.
# Hårstrekene klippes ved sjaktene, så ingenting skinner gjennom.
A_MAALT = 0.28    # den målte andelen
A_REST = 0.30     # (ubrukt — resten tegnes i papir dyp)

FONT = "Euclid Circular B, Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif"
NB = "@@NBSP@@"

# ---------------------------------------------------------------- geometri
W, H = 1200, 824
L, R = 76, 1144            # plottets venstre/høyre kant
Y100, Y0 = 180.0, 480.0    # verdiakse 0–100 %
X_MIN, X_MAX = 1972.0, 2027.0
KX = (R - L) / (X_MAX - X_MIN)

def x(year):  return L + (year - X_MIN) * KX
def y(pct):   return Y0 - (pct / 100.0) * (Y0 - Y100)

SHAFTS = {
    "1976":  (x(1976.0), x(1977.0)),
    "1996":  (x(1996.0), x(1997.0)),
    "koh":   (x(2023.0 + 243.0 / 365.0), x(2025.0)),   # 01.09.2023 – 31.12.2024
}
CX = {k: (a + b) / 2.0 for k, (a, b) in SHAFTS.items()}

Y_YEAR   = 500.0     # årsetiketter
Y_BRACK  = 528.0     # spennklammer
Y_BRLBL  = 548.0
Y_RULE   = 570.0     # registerskille
Y_HEAD   = 594.0
Y_EXPL   = (618.0, 636.0, 654.0)
Y_TAB    = (686.0, 705.0, 724.0, 743.0)
Y_SRC    = (786.0, 804.0)

# ---------------------------------------------------------------- tekstbredde
NARROW = set("iljt.,:;!|'’()[]/ ")
WIDE = set("mwMW%")
def cw(ch):
    if ch == " " or ch == " ": return 0.29
    if ch in "iljt.,:;!|'’": return 0.30
    if ch in "fr()[]-–—/\\": return 0.37
    if ch in WIDE: return 0.86
    if ch.isdigit(): return 0.56
    if ch.isupper(): return 0.67
    return 0.53

def tw(s, size, weight=400, ls=0.0):
    s = s.replace(NB, " ")
    base = sum(cw(c) for c in s) * size
    if weight >= 600: base *= 1.045
    return base + ls * size * max(0, len(s) - 1)

# ---------------------------------------------------------------- utskrift
parts = []
boxes = []          # (x0,x1,y0,y1,label) — for hårstrek-klipping og kollisjonstest

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace("@@NBSP@@", "&#160;"))

def text(tx, ty, s, size, fill, weight=400, anchor="start", ls=None, extra="", track=True,
         name=""):
    wpx = tw(s, size, weight, ls or 0.0)
    if anchor == "start":   x0 = tx
    elif anchor == "end":   x0 = tx - wpx
    else:                   x0 = tx - wpx / 2.0
    y0, y1 = ty - size * 0.76, ty + size * 0.09
    if track:
        boxes.append((x0, x0 + wpx, y0, y1, name or s[:28]))
    a = ['x="%.2f"' % tx, 'y="%.2f"' % ty, 'font-size="%g"' % size, 'fill="%s"' % fill]
    if weight != 400: a.append('font-weight="%d"' % weight)
    if anchor != "start": a.append('text-anchor="%s"' % anchor)
    if ls: a.append('letter-spacing="%gem"' % ls)
    if extra: a.append(extra)
    parts.append("  <text %s>%s</text>" % (" ".join(a), esc(s)))
    return x0, x0 + wpx

def line(x1, y1, x2, y2, stroke, w=1, dash=None, op=None, cap=None):
    a = ['x1="%.2f"' % x1, 'y1="%.2f"' % y1, 'x2="%.2f"' % x2, 'y2="%.2f"' % y2,
         'stroke="%s"' % stroke, 'stroke-width="%g"' % w]
    if dash: a.append('stroke-dasharray="%s"' % dash)
    if op is not None: a.append('stroke-opacity="%g"' % op)
    if cap: a.append('stroke-linecap="%s"' % cap)
    parts.append("  <line %s/>" % " ".join(a))

def rect(x1, y1, w_, h_, fill, op=None):
    o = '' if op is None else ' fill-opacity="%g"' % op
    parts.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s"%s/>'
                 % (x1, y1, w_, h_, fill, o))

# ---------------------------------------------------------------- innhold
TITTEL = "Femti år med tall — og tre diskrete målepunkter"
SUB1 = ("Andelen konkursbo som innstilles fordi midlene ikke dekker bobehandlingen. "
        "Tre målinger på femti år — med tre ulike nevnere.")
SUB2 = "Punktene er derfor aldri bundet sammen med en kurve. Aksen begynner på null."

B1976 = [
    (334.0, "40 %", 20, 600, OVRIG),
    (358.0, "«to av fem boer»", 13, 600, OVRIG),
    (382.0, "Kilde: Ot.prp. nr. 26 (1998-99), del 4 pkt. 1.1", 12.5, 400, DEMPET),
    (400.0, "Nevner: avsluttede bo — innstilte etter § 135", 12.5, 400, DEMPET),
    (418.0, "mot ordinært sluttede etter § 128", 12.5, 400, DEMPET),
    (436.0, "(nevneren dokumentert i NOU 1993: 16 s. 133)", 12.5, 400, DEMPET),
]
B1996 = [
    (228.0, "75 %", 20, 600, OVRIG),
    (252.0, "«tre av fire boer»", 13, 600, OVRIG),
    (276.0, "Kilde: Ot.prp. nr. 26 (1998-99), del 4 pkt. 1.1", 12.5, 400, DEMPET),
    (294.0, "Nevner: ikke oppgitt i kilden", 12.5, 400, DEMPET),
]
BKOH_OVER = [
    (204.0, "75,5 %", 23, 600, BYGG),
    (228.0, "denne studiens måling — 2023/24-kohorten", 13, 600, BYGG),
]
BKOH_UNDER = [
    (282.0, "Byggsikt · 5" + NB + "165 bo åpnet 01.09.2023–31.12.2024", 12.5, 400, DEMPET),
    (300.0, "Nevner: åpningskohorten, hvert bo fulgt til utfall", 12.5, 400, DEMPET),
    (318.0, "Kumulativ insidens ved 24 mnd.: 74,8 %", 12.5, 400, DEMPET),
]

TAB = [
    # (periode, verdi, nevnertype)
    ("1999",           "3" + NB + "005 innstilte bo",            "råtall for kalenderåret"),
    ("2000",           "3" + NB + "577 innstilte bo",            "råtall for kalenderåret"),
    ("2002",           "2" + NB + "767 innstilte bo",            "råtall for kalenderåret"),
    ("1. halvår 2003", "1" + NB + "691 + 524 innstilte bo",      "råtall, konkurs + tvangsavvikling"),
    ("ca. 2000",       "75–80 %",                                "av avslutningene"),
    ("udatert utvalg", "53 % og 77 %",                           "undergrupper etter rekvirent"),
    ("2010–2019",      "89,9 % (18" + NB + "345 av 20" + NB + "413)", "av avsluttede saker"),
    ("2023 og 2026",   "«90 prosent»",                           "kilden regner av avslutningene"),
]

HEAD = "Mellomrommet er ikke tomt for tall — men ingen av dem kan tegnes inn på denne aksen"
EXPL = [
    "Det finnes offisielle tallfestinger for 1999, 2000, 2002, første halvår 2003 og for tiåret 2010–2019. De er ført opp under, med nevnertype.",
    "Ingen av dem har åpningskohorten som nevner: de teller innstillinger i et kalenderår uten hensyn til når boene ble åpnet, eller de er andeler av bo som",
    "alt var avsluttet, eller av undergrupper etter hvem som begjærte konkursen. Statistisk sentralbyrå og Brønnøysundregistrene teller åpninger, ikke utfall.",
]
SRC = [
    "Byggsikt · offentlig tilgjengelige registerkunngjøringer · utfall observert til 24.08.2026. Historiske punkter: Ot.prp. nr. 26 (1998-99) del 4 pkt. 1.1 og del 6 pkt. I.1 med NOU 1993: 16.",
    "Tall i mellomrommet: Ot.prp. nr. 23 (2003-2004) pkt. 2, 7.1 og 16.2 · Mjøs, Kostøl og Pelja (2021) tabell 4 panel E · høringsnotat 13.01.2023 · Prop. 56 L (2025–2026) · Statistisk sentralbyrå.",
]

# ================================================================ SVG
parts.append('<?xml version="1.0" encoding="UTF-8"?>')
parts.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
             'preserveAspectRatio="xMidYMid meet" role="img" '
             'aria-labelledby="fig1-tittel fig1-desc" width="%d" height="%d">' % (W, H, W, H))
parts.append('  <title id="fig1-tittel">Femti år med tall — og tre diskrete målepunkter</title>')
parts.append('  <desc id="fig1-desc">Punktdiagram med verdiakse fra 0 til 100 prosent. '
             'Tre målepunkter for andelen konkursbo som innstilles etter konkursloven § 135: '
             '1976 = 40 prosent og 1996 = 75 prosent, begge gjengitt fra Ot.prp. nr. 26 (1998-99) '
             'og tegnet som åpne ringer i kjølig blå; 2023/24-kohorten = 75,5 prosent, denne studiens '
             'egen måling på 5 165 bo, tegnet som et fylt punkt i varm rust. Punktene er ikke bundet '
             'sammen: mellomrommene 1977–1995 og 1997–2023 er markert som spenn uten kohortkoblet '
             'observasjon. Under diagrammet står de offisielle tallene fra 1999 til 2019 som '
             'finnes, men som ikke kan tegnes inn fordi de har en annen nevner.</desc>')
parts.append('  <g font-family="%s" font-variant-numeric="tabular-nums" '
             'style="font-variant-numeric:tabular-nums">' % FONT)

# bakgrunn
rect(0, 0, W, H, PAPIR)

# ---- tittelblokk
text(L, 46, "FIGUR 1", 11, DEMPET, 500, ls=0.14,
     extra='style="letter-spacing:0.14em;font-variant-numeric:tabular-nums"')
text(L, 78, TITTEL, 21, BLEKK, 600)
text(L, 106, SUB1, 14.5, DEMPET)
text(L, 126, SUB2, 14.5, DEMPET)

# ---- y-etiketter (over hårstrekene, venstrestilt mot samme marg som tittelen)
YLAB = [(100.0, "100 %"), (75.0, "75"), (50.0, "50"), (25.0, "25"), (0.0, "0")]
for pv, lab in YLAB:
    text(L, y(pv) - 5, lab, 12.5, DEMPET,
         extra='style="font-variant-numeric:tabular-nums"')
x0t, x1t = text(L + 24, y(75.0) - 5, "tre av fire", 12.5, AKSENT,
                extra='style="font-variant-numeric:tabular-nums"')

# ---- serieblokker (tekst registreres i boxes før hårstrekene klippes)
def block(x_anchor, lines, anchor="start"):
    for by, s, size, wt, col in lines:
        text(x_anchor, by, s, size, col, wt, anchor=anchor,
             extra='style="font-variant-numeric:tabular-nums"')

# tegnes senere; her registreres bare bokser ved å kjøre tekst inn i egen buffer
buf_start = len(parts)
block(SHAFTS["1976"][1] + 16, B1976)
block(SHAFTS["1996"][0] - 16, B1996, anchor="end")
block(R, BKOH_OVER, anchor="end")
block(R, BKOH_UNDER, anchor="end")
serie_txt = parts[buf_start:]
del parts[buf_start:]

# spennklammer-etiketter og årsetiketter registreres etter plottet (ingen hårstrek der)

# ---- hårstreker, klippet rundt tekst
def gridline(yv, stroke, w=1, dash=None, op=None):
    padx, pady = 9.0, 4.0
    ivs = [SHAFTS[k] for k in SHAFTS]           # sjaktene ligger over hårstrekene
    for (bx0, bx1, by0, by1, nm) in boxes:
        if by0 - pady <= yv <= by1 + pady:
            ivs.append((bx0 - padx, bx1 + padx))
    ivs.sort()
    segs, cur = [], L
    for a, b in ivs:
        a, b = max(a, L), min(b, R)
        if b <= cur: continue
        if a > cur: segs.append((cur, a))
        cur = max(cur, b)
    if cur < R: segs.append((cur, R))
    for a, b in segs:
        if b - a > 2:
            line(a, yv, b, yv, stroke, w, dash, op)

for pv, _ in YLAB:
    if pv == 0.0:
        continue
    if pv == 75.0:
        gridline(y(pv), AKSENT, 1, "1.5 4.5", 0.85)
    else:
        gridline(y(pv), HAAR, 1)

# ---- sjaktene: målevinduene, delt ved den målte andelen
SPEC = [("1976", P1976, OVRIG), ("1996", P1996, OVRIG), ("koh", PKOH, BYGG)]
for key, pv, col in SPEC:
    a, b = SHAFTS[key]
    yv = y(pv)
    rect(a, Y100, b - a, yv - Y100, PAPIRDYP)              # resten opp til 100 %
    rect(a, yv, b - a, Y0 - yv, col, A_MAALT)              # den målte andelen

# ---- nullinje / akse
line(L, Y0, R, Y0, DEMPET, 1)

# ---- tiårsmerker
for yr in (1980, 1990, 2000, 2010, 2020):
    line(x(yr), Y0, x(yr), Y0 + 5, HAAR, 1)

# ---- toppstrek + punkt
for key, pv, col in SPEC:
    a, b = SHAFTS[key]
    yv = y(pv)
    line(a - 3, yv, b + 3, yv, col, 3, cap="butt")
    if key == "koh":
        parts.append('  <circle cx="%.2f" cy="%.2f" r="7" fill="%s"/>' % (CX[key], yv, col))
    else:
        parts.append('  <circle cx="%.2f" cy="%.2f" r="6.5" fill="%s" stroke="%s" '
                     'stroke-width="2.75"/>' % (CX[key], yv, PAPIR, col))

# ---- hårstreker fra punkt til etikett
line(SHAFTS["1976"][1] + 3, y(P1976), SHAFTS["1976"][1] + 13, y(P1976), OVRIG, 1, op=0.55)
line(SHAFTS["1996"][0] - 13, y(P1996), SHAFTS["1996"][0] - 3, y(P1996), OVRIG, 1, op=0.55)

# ---- serietekst på toppen
parts.extend(serie_txt)

# ---- årsetiketter
for yr in (1980, 1990, 2000, 2010, 2020):
    text(x(yr), Y_YEAR, str(yr), 12.5, DEMPET, anchor="middle",
         extra='style="font-variant-numeric:tabular-nums"')
for key, lab, col in (("1976", "1976", OVRIG), ("1996", "1996", OVRIG),
                      ("koh", "2023/24", BYGG)):
    text(CX[key], Y_YEAR, lab, 12.5, col, 600, anchor="middle",
         extra='style="font-variant-numeric:tabular-nums"')

# ---- spennklammer over mellomrommene
def bracket(xa, xb, label):
    line(xa, Y_BRACK, xb, Y_BRACK, NOYTRAL, 1, op=0.85)
    line(xa, Y_BRACK - 5, xa, Y_BRACK, NOYTRAL, 1, op=0.85)
    line(xb, Y_BRACK - 5, xb, Y_BRACK, NOYTRAL, 1, op=0.85)
    text((xa + xb) / 2.0, Y_BRLBL, label, 12.5, NOYTRAL, anchor="middle",
         extra='style="font-variant-numeric:tabular-nums"')

bracket(SHAFTS["1976"][1], SHAFTS["1996"][0], "1977–1995 · ingen observasjon")
bracket(SHAFTS["1996"][1], SHAFTS["koh"][0],
        "1997–2023 · ingen kohortkoblet observasjon — tallene som finnes, står under")

# ---- nedre register
line(L, Y_RULE, R, Y_RULE, HAAR, 1)
text(L, Y_HEAD, HEAD, 14.5, BLEKK, 600)
for i, s in enumerate(EXPL):
    text(L, Y_EXPL[i], s, 12.5, DEMPET,
         extra='style="font-variant-numeric:tabular-nums"')

COL_X = (L, L + 534.0)
OFF_P, OFF_V, OFF_R = 0.0, 108.0, 296.0
for i, (per, val, nev) in enumerate(TAB):
    cx0 = COL_X[i // 4]
    ty = Y_TAB[i % 4]
    text(cx0 + OFF_P, ty, per, 12.5, DEMPET, 600,
         extra='style="font-variant-numeric:tabular-nums"')
    text(cx0 + OFF_V, ty, val, 12.5, DEMPET,
         extra='style="font-variant-numeric:tabular-nums"')
    text(cx0 + OFF_R, ty, nev, 12.5, NOYTRAL,
         extra='style="font-variant-numeric:tabular-nums"')

# ---- kildelinje
for i, s in enumerate(SRC):
    text(L, Y_SRC[i], s, 11, DEMPET,
         extra='style="font-variant-numeric:tabular-nums"')

parts.append("  </g>")
parts.append("</svg>")

svg = "\n".join(parts) + "\n"
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(svg)

# ================================================================ kontroll
problems = []
for (bx0, bx1, by0, by1, nm) in boxes:
    if bx1 > R + 0.5:
        problems.append("OVERFLOW høyre  %7.1f  %s" % (bx1, nm))
    if bx0 < L - 0.5:
        problems.append("OVERFLOW venstre %7.1f  %s" % (bx0, nm))
    if by1 > H - 8 or by0 < 8:
        problems.append("OVERFLOW vertikal %s" % nm)

for i in range(len(boxes)):
    for j in range(i + 1, len(boxes)):
        a, b = boxes[i], boxes[j]
        if a[0] < b[1] - 1 and b[0] < a[1] - 1 and a[2] < b[3] - 1 and b[2] < a[3] - 1:
            problems.append("KOLLISJON  «%s»  ×  «%s»" % (a[4], b[4]))

print("fil:", OUT, "%.1f kB" % (len(svg.encode("utf-8")) / 1024.0))
print("plott: x %.0f–%.0f   y(100%%)=%.0f  y(0%%)=%.0f   H=%d" % (L, R, Y100, Y0, H))
for k in ("1976", "1996", "koh"):
    print("  sjakt %-5s x %.1f–%.1f  senter %.1f" % (k, SHAFTS[k][0], SHAFTS[k][1], CX[k]))
print("  y(40)=%.2f  y(75)=%.2f  y(75,5)=%.2f" % (y(40), y(75), y(75.5)))
print("bredeste tekstbokser:")
for b in sorted(boxes, key=lambda t: -(t[1]))[:6]:
    print("   slutt x=%7.1f  %s" % (b[1], b[4]))
if problems:
    print("\nPROBLEMER (%d):" % len(problems))
    for p in problems: print("  ", p)
    sys.exit(1)
print("\nOK — ingen overflow, ingen kollisjon.")
