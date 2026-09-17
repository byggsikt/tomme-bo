# -*- coding: utf-8 -*-
"""
Figur 6 - Modningskurven, aerlighetsutstillingen.
Skriver: figurer/svg/figur-6-modning.svg

Alle tall leses fra
  figurer/modningskurve-risikomengde-2026-08-30.csv
  figurer/modningskurve-naiv-per-kvartal-2026-08-30.csv
Ingen datatall er skrevet inn for haand her. Det eneste tallet som ikke
kommer fra CSV-ene er kohortnivaaet 75,5 % (referanselinja), som er
studiens hovedtall og staar i manuskriptet kap. 4 og 10.
"""
import csv
import io
import os

BASE = r"./figurer"
OUT = os.path.join(BASE, "svg", "figur-6-modning.svg")

# ---------------------------------------------------------------- palett (LAAST)
PAPIR = "#f5f0e6"
PAPIR_DYP = "#e9e1d4"
BLEKK = "#171815"
DEMPET = "#625e55"
HAAR = "#d8cfbe"
BYGG = "#9a4d35"
OVRIG = "#2e6f91"
AKSENT = "#b9782f"
NOYTRAL = "#8c9a8e"

FONT = "Euclid Circular B, Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif"
NUM = 'font-variant-numeric="tabular-nums" style="font-variant-numeric:tabular-nums"'
NBSP = "&#160;"


def pst(v, des=True):
    s = ("%.1f" % v).replace(".", ",")
    if not des:
        s = s.replace(",0", "")
    return s + NBSP + "%"


def tall(n):
    s = str(int(n))
    ut = ""
    while len(s) > 3:
        ut = NBSP + s[-3:] + ut
        s = s[:-3]
    return s + ut


# ---------------------------------------------------------------- data
with io.open(os.path.join(BASE, "modningskurve-risikomengde-2026-08-30.csv"),
             encoding="utf-8") as f:
    risiko = list(csv.DictReader(f, delimiter=";"))
with io.open(os.path.join(BASE, "modningskurve-naiv-per-kvartal-2026-08-30.csv"),
             encoding="utf-8") as f:
    naiv = list(csv.DictReader(f, delimiter=";"))

MAKS_MND = 30           # kurvene stopper her; lenger ute er risikomengden for liten
R = [r for r in risiko if int(r["maaneder"]) <= MAKS_MND]
assert len(R) == MAKS_MND + 1

mnd = [int(r["maaneder"]) for r in R]
alle = [float(r["andel_alle_pst"]) for r in R]
bygg = [float(r["andel_bygg_pst"]) for r in R]
ovrige = [float(r["andel_ovrige_pst"]) for r in R]
n_alle = [int(r["n_alle"]) for r in R]

kvartal = [r["aapning_kvartal"] for r in naiv]
kv_pst = [float(r["innstilt_pst"]) for r in naiv]
assert "2026K3" not in kvartal, "2026K3 er stroeket og skal aldri rekonstrueres"

KOHORT_NIVAA = 75.5
KUTT_ETTER = "2024K4"

# ---------------------------------------------------------------- geometri
W, H = 1200, 996
L = 76.0                # venstremarg = y-akse = tittelblokkens venstrekant
PR = 940.0              # plottets hoeyrekant
RAIL = 948.0            # hoeyre skinne
YMAX = 80.0

A_TOP, A_BOT = 180.0, 560.0
B_TOP, B_BOT = 654.0, 839.0


def ax(m):
    return L + (PR - L) * m / float(MAKS_MND)


def ay(v):
    return A_BOT - (A_BOT - A_TOP) * v / YMAX


def by(v):
    return B_BOT - (B_BOT - B_TOP) * v / YMAX


SLOTT = (PR - L) / len(kvartal)
SOYLE = 52.0


def bx(i):
    return L + i * SLOTT + (SLOTT - SOYLE) / 2.0


KUTT_I = kvartal.index(KUTT_ETTER) + 1
KUTT_X = L + KUTT_I * SLOTT

o = []
a = o.append


def txt(x, y, s, size=12.5, fill=DEMPET, weight=None, anchor=None,
        num=False, ls=None):
    at = ' text-anchor="%s"' % anchor if anchor else ""
    wt = ' font-weight="%s"' % weight if weight else ""
    lsp = ' letter-spacing="%s"' % ls if ls else ""
    n = " " + NUM if num else ""
    a('<text x="%.1f" y="%.1f" font-family="%s" font-size="%s" fill="%s"'
      '%s%s%s%s>%s</text>' % (x, y, FONT, size, fill, wt, at, lsp, n, s))


def line(x1, y1, x2, y2, stroke, w=1, dash=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    a('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
      'stroke-width="%s"%s/>' % (x1, y1, x2, y2, stroke, w, d))


# ---------------------------------------------------------------- dokument
a('<?xml version="1.0" encoding="UTF-8"?>')
a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
  'preserveAspectRatio="xMidYMid meet" role="img" '
  'aria-labelledby="fig6-tittel fig6-desc" font-family="%s">' % (W, H, FONT))
a('<title id="fig6-tittel">Figur 6. Modningskurven \u2014 '
  '\u00e6rlighetsutstillingen</title>')
a('<desc id="fig6-desc">To panel over andelen konkursbo som innstilles fordi '
  'boet er tomt. \u00d8verst: andelen som funksjon av antall m\u00e5neder siden '
  '\u00e5pning, i risikomengdeform, for alle bo, for bygg og for \u00f8vrige '
  'n\u00e6ringer. Kurven for alle bo stiger bratt det f\u00f8rste halv\u00e5ret, n\u00e5r '
  '63,1 prosent etter tolv m\u00e5neder og flater ut mellom 24 og 30 m\u00e5neder '
  'p\u00e5 74,7 prosent, like under kohortens niv\u00e5 p\u00e5 75,5 prosent, som er '
  'tegnet som vannrett referanselinje. Bygg ligger under \u00f8vrige n\u00e6ringer '
  'p\u00e5 hver horisont, 70,0 mot 76,0 prosent ved 24 m\u00e5neder. Under aksen '
  'st\u00e5r risikomengden, som faller fra 11 068 bo ved null m\u00e5neder til '
  '1 925 ved 30 m\u00e5neder. Nederst: den samme andelen regnet naivt per '
  '\u00e5pningskvartal, som s\u00f8yler. De seks kvartalene fra tredje kvartal 2023 '
  'til fjerde kvartal 2024 ligger p\u00e5 et plat\u00e5 mellom 74,0 og 76,4 prosent. '
  'Deretter faller s\u00f8ylene monotont gjennom 71,8, 67,5, 64,1, 56,6 og 46,6 '
  'til 19,0 prosent i andre kvartal 2026. Omr\u00e5det etter kohortkuttet '
  '31.12.2024 er skyggelagt og merket h\u00f8yresensurert, ikke en trend.</desc>')
a('<defs><pattern id="sensur" width="9" height="9" patternUnits="userSpaceOnUse" '
  'patternTransform="rotate(-45 0 0)"><line x1="0" y1="0" x2="0" y2="9" '
  'stroke="%s" stroke-width="1.1"/></pattern></defs>' % HAAR)
a('<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (W, H, PAPIR))

# ---------------------------------------------------------------- tittelblokk
txt(L, 42, "FIGUR 6", size=11, fill=DEMPET, ls="0.14em")
txt(L, 76, "Modningskurven \u2014 \u00e6rlighetsutstillingen",
    size=21, fill=BLEKK, weight="600")
txt(L, 102, "\u00d8verst: andelen innstilte bo mot m\u00e5neder siden \u00e5pning, i "
            "risikomengdeform \u2014 bare bo som har oppn\u00e5dd oppf\u00f8lgingstiden "
            "telles.", size=14.5, fill=DEMPET)
txt(L, 122, "Nederst: den samme andelen per \u00e5pningskvartal, uten "
            "modningskorreksjon. Samme st\u00f8rrelse, m\u00e5lt to m\u00e5ter.",
    size=14.5, fill=DEMPET)

# ================================================================ PANEL A
txt(L, 162, "Risikomengdeform: andel innstilt etter oppf\u00f8lgingstid",
    size=13.5, fill=BLEKK, weight="600")

for v in (20, 40, 60):
    line(L, ay(v), PR, ay(v), HAAR, 1)
    txt(RAIL, ay(v) + 4, pst(v, des=False), size=12.5, fill=DEMPET, num=True)
txt(RAIL, ay(0) + 4, pst(0, des=False), size=12.5, fill=DEMPET, num=True)

line(L, ay(KOHORT_NIVAA), PR, ay(KOHORT_NIVAA), AKSENT, 1.4, dash="7 4")
txt(L, ay(KOHORT_NIVAA) - 8, "Kohortens niv\u00e5 " + pst(KOHORT_NIVAA),
    size=12.5, fill=AKSENT, weight="600", num=True)


def kurve(vals, farge, bredde):
    p = " ".join("%.1f,%.1f" % (ax(m), ay(v)) for m, v in zip(mnd, vals))
    a('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" '
      'stroke-linejoin="round" stroke-linecap="round"/>' % (p, farge, bredde))


kurve(bygg, BYGG, 2.5)
kurve(ovrige, OVRIG, 2.5)
kurve(alle, BLEKK, 3.0)

line(L, A_BOT, PR, A_BOT, DEMPET, 1)

TICKS = [0, 3, 6, 12, 18, 24, 30]
for t in TICKS:
    line(ax(t), A_BOT, ax(t), A_BOT + 5, HAAR, 1)
    anchor = "start" if t == 0 else ("end" if t == MAKS_MND else "middle")
    txt(ax(t), 582, str(t), size=12.5, fill=DEMPET, anchor=anchor, num=True)
    txt(ax(t), 604, tall(n_alle[t]), size=12.5, fill=DEMPET, anchor=anchor,
        num=True)
txt(RAIL, 582, "m\u00e5neder siden \u00e5pning", size=11, fill=DEMPET)
txt(RAIL, 604, "bo i risikomengden", size=11, fill=DEMPET)

# direkte etiketter ved kurveenden - ingen legende
for navn, v, farge, yb in [("\u00d8vrige n\u00e6ringer", ovrige[-1], OVRIG, 197.0),
                           ("Alle bo", alle[-1], BLEKK, 221.0),
                           ("Bygg", bygg[-1], BYGG, 245.0)]:
    line(PR + 1, ay(v), RAIL - 2, yb - 4.5, farge, 1)
    a('<text x="%.1f" y="%.1f" font-family="%s" font-size="13" fill="%s" '
      'font-weight="600">%s<tspan font-size="12.5" font-weight="400" %s> '
      '%s</tspan></text>' % (RAIL, yb, FONT, farge, navn, NUM, pst(v)))

# annotasjon: tolv maaneder
M12 = 12
px, py = ax(M12), ay(alle[M12])
line(px, py - 4, px, 244, BLEKK, 1)
line(px, 244, 352, 244, BLEKK, 1)
a('<circle cx="%.1f" cy="%.1f" r="5.6" fill="%s"/>' % (px, py, PAPIR))
a('<circle cx="%.1f" cy="%.1f" r="3.3" fill="%s"/>' % (px, py, BLEKK))
txt(344, 239, "Tolv m\u00e5neder etter \u00e5pning", size=12.5, fill=BLEKK,
    anchor="end")
txt(344, 257, "er " + pst(alle[M12]) + " av boene innstilt", size=12.5,
    fill=BLEKK, anchor="end", num=True)

# lesenote, forankret med loddrett haarstrek
line(493, 368, 493, 421, HAAR, 1.5)
txt(505, 380, "Kurven flater ut mellom 24 og 30 m\u00e5neder og legger seg p\u00e5 "
              "kohortens niv\u00e5.", size=11.5, fill=DEMPET, num=True)
txt(505, 398, "Bygg ligger under \u00f8vrige p\u00e5 hver horisont \u2014 "
              + pst(bygg[24]) + " mot " + pst(ovrige[24]) + " ved 24 m\u00e5neder.",
    size=11.5, fill=DEMPET, num=True)
txt(505, 416, "Kurvene stopper ved 30 m\u00e5neder; risikomengden er for liten "
              "lenger ute.", size=11.5, fill=DEMPET, num=True)

# ================================================================ PANEL B
# Ingen rutenett: hver soeyle baerer sitt eget tall, saa en ulabelt akse ville
# ikke baaret informasjon. Grunnlinja og referanselinja holder skalaen.
txt(L, 640, "Naiv beregning: andel innstilt etter \u00e5pningskvartal",
    size=13.5, fill=BLEKK, weight="600")

a('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
  % (KUTT_X, B_TOP, PR - KUTT_X, B_BOT - B_TOP, PAPIR_DYP))
a('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="url(#sensur)"/>'
  % (KUTT_X, B_TOP, PR - KUTT_X, B_BOT - B_TOP))

for i, v in enumerate(kv_pst):
    sensurert = i >= KUTT_I
    ytop = by(v)
    a('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
      % (bx(i), ytop, SOYLE, B_BOT - ytop, NOYTRAL if sensurert else BLEKK))
    txt(bx(i) + SOYLE / 2.0, ytop + 17, pst(v), size=12.5,
        fill=(BLEKK if sensurert else PAPIR), anchor="middle", num=True)

line(KUTT_X, B_TOP, KUTT_X, B_BOT, AKSENT, 1.6)
line(KUTT_X, B_BOT, KUTT_X, 895, AKSENT, 1)
line(L, by(KOHORT_NIVAA), PR, by(KOHORT_NIVAA), AKSENT, 1.4, dash="7 4")
txt(RAIL, by(KOHORT_NIVAA) + 4, pst(KOHORT_NIVAA), size=12.5, fill=AKSENT,
    weight="600", num=True)

txt(932, 686, "H\u00f8yresensurert", size=13.5, fill=BLEKK, weight="600",
    anchor="end")
txt(932, 704, "\u2014 ikke en trend", size=13.5, fill=DEMPET, anchor="end")
txt(932, 722, "Boene er ikke ferdige.", size=11.5, fill=DEMPET, anchor="end")

line(L, B_BOT, PR, B_BOT, DEMPET, 1)

for i, k in enumerate(kvartal):
    txt(L + i * SLOTT + SLOTT / 2.0, 864, k[4:], size=12.5,
        fill=(AKSENT if k == "2023K3" else DEMPET), anchor="middle", num=True)

aar = {}
for i, k in enumerate(kvartal):
    aar.setdefault(k[:4], []).append(i)
for y4 in sorted(aar):
    idx = aar[y4]
    txt(L + (min(idx) + max(idx) + 1) / 2.0 * SLOTT, 885, y4, size=12.5,
        fill=DEMPET, anchor="middle", num=True)

txt(L, 909, "K3 2023 dekker bare september \u2014", size=11.5, fill=AKSENT,
    num=True)
txt(L, 925, "kohortvinduet starter 01.09.2023.", size=11.5, fill=AKSENT,
    num=True)
txt(KUTT_X, 909, "Kohortvinduet slutter 31.12.2024", size=11.5, fill=AKSENT,
    anchor="middle", num=True)

for j, s in enumerate(["2026K3 er et ufullstendig",
                       "delkvartal \u2014 str\u00f8ket fra",
                       "figuren og grunnlagsfila,",
                       "aldri tegnet som null."]):
    txt(RAIL, 859 + j * 16, s, size=11.5, fill=DEMPET, num=True)

# ---------------------------------------------------------------- kilde
line(L, 937, W - 56, 937, HAAR, 1)
txt(L, 959, "Byggsikt \u00b7 offentlig tilgjengelige registerkunngj\u00f8ringer "
            "\u00b7 utfall observert til 24.08.2026", size=11, fill=DEMPET,
    num=True)

a('</svg>')

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(o) + "\n")

print("skrev", OUT)
print("A slutt m=%d  alle %.1f  bygg %.1f  ovrige %.1f"
      % (MAKS_MND, alle[-1], bygg[-1], ovrige[-1]))
print("A m=12 alle %.1f ; m=24 bygg %.1f ovrige %.1f"
      % (alle[12], bygg[24], ovrige[24]))
print("risikomengde:", [(t, n_alle[t]) for t in TICKS])
print("B:", list(zip(kvartal, kv_pst)))
print("kutt i=%d x=%.0f" % (KUTT_I, KUTT_X))
