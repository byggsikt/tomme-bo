# -*- coding: utf-8 -*-
"""
Figur 2 - "Fossefallet: hva som skjer med 5 165 bo"
Genererer ./figur-2-fossefall.svg

Alle tall leses fra figurgrunnlaget:
  figurer/fossefall-per-1000-bo-2026-08-30.csv
Ingen tall er skrevet inn for hand.
"""
import csv
import io
import os

BASE = r"./figurer"
CSV = os.path.join(BASE, "fossefall-per-1000-bo-2026-08-30.csv")
OUT = os.path.join(BASE, "svg", "figur-2-fossefall.svg")

# ---------------------------------------------------------------- data
with io.open(CSV, "r", encoding="utf-8") as fh:
    rows = {r["gruppe"]: r for r in csv.DictReader(fh, delimiter=";")}

ALLE = rows[u"ALLE n\u00e6ringer"]
BYGG = rows[u"BYGG (utf\u00f8rende)"]

N_ALLE = int(ALLE["bo"])                 # 5165
A_INN = int(ALLE["innstilt"])            # 3897
A_AVS = int(ALLE["kun_avsluttet"])       # 917
A_APN = int(ALLE["fortsatt_apne"])       # 351
A_SEKS = int(ALLE["herav_begge_kunngjoringer_annotasjon"])   # 6

N_BYGG = int(BYGG["bo"])                 # 1280
B_INN = int(BYGG["innstilt"])            # 911
B_AVS = int(BYGG["kun_avsluttet"])       # 258
B_APN = int(BYGG["fortsatt_apne"])       # 111
B_SEKS = int(BYGG["herav_begge_kunngjoringer_annotasjon"])   # 0

assert A_INN + A_AVS + A_APN == N_ALLE, "kohorten summerer ikke"
assert B_INN + B_AVS + B_APN == N_BYGG, "byggsporet summerer ikke"

# andeler i promille fra fila -> prosent med en desimal (norsk komma)
def pct(promille_felt):
    p = int(promille_felt)
    return (u"%.1f" % (p / 10.0)).replace(".", ",")

A_INN_P = pct(ALLE["per1000_innstilt"])          # 75,5
A_AVS_P = pct(ALLE["per1000_kun_avsluttet"])     # 17,8
A_APN_P = pct(ALLE["per1000_fortsatt_apne"])     # 6,8
B_INN_P = pct(BYGG["per1000_innstilt"])          # 71,2
B_AVS_P = pct(BYGG["per1000_kun_avsluttet"])     # 20,2
B_APN_P = pct(BYGG["per1000_fortsatt_apne"])     # 8,7

NBSP = "&#160;"


def n(v):
    """Norsk tusenskille med hardt mellomrom."""
    s = str(v)
    out = ""
    while len(s) > 3:
        out = NBSP + s[-3:] + out
        s = s[:-3]
    return s + out


# ---------------------------------------------------------------- palett
PAPIR = "#f5f0e6"
PAPIR_DYP = "#e9e1d4"
BLEKK = "#171815"
DEMPET = "#625e55"
HAARSTREK = "#d8cfbe"
RUST = "#9a4d35"       # innstilt etter § 135
BLAA = "#2e6f91"       # ordinaer avslutning
MESSING = "#b9782f"    # referanse / terskel / annotasjon
NOYTRAL = "#8c9a8e"    # fortsatt uavgjort (ikke-avklart)

FONT = ("Euclid Circular B, Inter, system-ui, -apple-system, "
        "Segoe UI, Arial, sans-serif")

# ---------------------------------------------------------------- geometri
W = 1200
H = 712
L = 76.0                 # venstremarg
R = W - 56.0             # 1144 hoyremarg
PLOT = R - L             # 1068

GAP = 44.0               # luft mellom de tre utfallene i hovedsoylen (ikke data)
GAP_B = 18.0             # samme luft ville sprengt det korte byggsporet
DATAW = PLOT - 2 * GAP   # 980 px baerer 5 165 bo
SCALE = DATAW / N_ALLE   # px per bo - IDENTISK for begge sporene

# baand (kilden til fossefallet): full bredde, ingen luft
BAND_Y, BAND_H = 168.0, 28.0
band_s = PLOT / float(N_ALLE)
b1 = L + A_INN * band_s
b2 = b1 + A_AVS * band_s

# fossefallets stroemmer
RIB_TOP = BAND_Y + BAND_H          # 196
RIB_BOT = 244.0

# hovedsoylen
BAR_Y, BAR_H = 244.0, 92.0
BAR_B = BAR_Y + BAR_H              # 372
s1x, s1w = L, A_INN * SCALE
s2x, s2w = s1x + s1w + GAP, A_AVS * SCALE
s3x, s3w = s2x + s2w + GAP, A_APN * SCALE
s1r, s2r, s3r = s1x + s1w, s2x + s2w, s3x + s3w
assert abs(s3r - R) < 0.01, s3r

# byggsporet - samme SCALE, samme luft, venstrestilt mot samme marg
BY_Y, BY_H = 510.0, 40.0
BY_B = BY_Y + BY_H
t1x, t1w = L, B_INN * SCALE
t2x, t2w = t1x + t1w + GAP_B, B_AVS * SCALE
t3x, t3w = t2x + t2w + GAP_B, B_APN * SCALE
t3r = t3x + t3w

out = []
add = out.append


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, size=12.5, fill=DEMPET, weight=None, anchor=None,
        ls=None, opacity=None, raw=False):
    a = ['x="%.2f"' % x, 'y="%.2f"' % y, 'font-size="%s"' % size,
         'fill="%s"' % fill]
    if weight:
        a.append('font-weight="%s"' % weight)
    if anchor:
        a.append('text-anchor="%s"' % anchor)
    style = "font-variant-numeric:tabular-nums"
    if ls:
        a.append('letter-spacing="%s"' % ls)
        style = "letter-spacing:%s;%s" % (ls, style)
    if opacity:
        a.append('fill-opacity="%s"' % opacity)
    a.append('style="%s"' % style)
    add('  <text %s>%s</text>' % (" ".join(a), s if raw else esc(s)))


def rect(x, y, w, h, fill, opacity=None):
    o = ' fill-opacity="%s"' % opacity if opacity else ""
    add('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s"%s/>'
        % (x, y, w, h, fill, o))


def line(x1, y1, x2, y2, stroke=HAARSTREK, w=1):
    add('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
        'stroke-width="%s"/>' % (x1, y1, x2, y2, stroke, w))


def ribbon(xa, xb, xc, xd, fill):
    """Trapes fra baandet (xa..xb ved RIB_TOP) til soylen (xc..xd ved RIB_BOT)."""
    add('  <path d="M %.2f %.2f L %.2f %.2f L %.2f %.2f L %.2f %.2f Z" '
        'fill="%s" fill-opacity="0.13"/>'
        % (xa, RIB_TOP, xb, RIB_TOP, xd, RIB_BOT, xc, RIB_BOT, fill))


# ---------------------------------------------------------------- SVG
add('<?xml version="1.0" encoding="UTF-8"?>')
add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
    'preserveAspectRatio="xMidYMid meet" role="img" '
    'aria-labelledby="fig2-tittel fig2-desc" width="%d" height="%d">' % (W, H, W, H))
add('  <title id="fig2-tittel">Fossefallet: hva som skjer med 5 165 bo</title>')
add('  <desc id="fig2-desc">Fossefallsdiagram. Et b\u00e5nd \u00f8verst rommer hele '
    'kohorten p\u00e5 5 165 konkursbo, og deles i tre str\u00f8mmer ned til en '
    's\u00f8yle med tre gjensidig utelukkende utfall per 24.08.2026: innstilt etter '
    'konkursloven \u00a7 135, 3 897 bo eller 75,5 prosent, i varm rust; ordin\u00e6r '
    'avslutning, 917 bo eller 17,8 prosent, i kj\u00f8lig bl\u00e5tt; fortsatt '
    'uavgjort, 351 bo eller 6,8 prosent, i dempet gr\u00f8nngr\u00e5tt. Hvert felt er '
    'merket direkte med navn og tall, slik at figuren kan leses uten farge. Et smalt '
    'messingmerke i h\u00f8yre kant av innstillingsfeltet markerer de seks boene som '
    'b\u00e6rer b\u00e5de en innstillings- og en avslutningskunngj\u00f8ring; de er talt '
    'som innstilt og utgj\u00f8r ingen fjerde kategori. Under st\u00e5r byggsporet som '
    'delmengde i n\u00f8yaktig samme skala: 1 280 bo, hvorav 911 innstilt, 258 '
    'ordin\u00e6rt avsluttet og 111 fortsatt uavgjort. Figuren teller bo, ikke '
    'kroner.</desc>')
add('  <g font-family="%s" font-variant-numeric="tabular-nums" '
    'style="font-variant-numeric:tabular-nums">' % FONT)

rect(0, 0, W, H, PAPIR)

# --- tittelblokk
txt(L, 46, "FIGUR 2", 11, DEMPET, weight="500", ls="0.14em")
txt(L, 78, u"Fossefallet: hva som skjer med %s bo" % n(N_ALLE), 21, BLEKK,
    weight="600", raw=True)
txt(L, 106, u"Alle %s konkursbo i kohorten fordelt p\u00e5 tre gjensidig "
            u"utelukkende utfall, slik de st\u00e5r 24.08.2026. Byggsporet ligger "
            u"inne som" % n(N_ALLE), 14.5, DEMPET, raw=True)
txt(L, 126, u"delmengde i n\u00f8yaktig samme skala. Figuren viser den observerte "
            u"as-of-fordelingen, ikke fasthorisont-estimatet.", 14.5, DEMPET)

# --- baandet: hele kohorten
rect(L, BAND_Y, PLOT, BAND_H, PAPIR_DYP)
add('  <text x="%.2f" y="%.2f" font-size="12.5" fill="%s" '
    'style="font-variant-numeric:tabular-nums">'
    '<tspan font-size="13" font-weight="600" fill="%s">%s bo</tspan>'
    '<tspan dx="7">\u00b7 konkursbo etter aksje- og allmennaksjeselskaper '
    '\u00e5pnet 01.09.2023\u201331.12.2024</tspan></text>'
    % (L + 16, BAND_Y + 18.5, DEMPET, BLEKK, n(N_ALLE)))
txt(R - 16, BAND_Y + 18.5, u"hvert bo teller \u00e9tt utfall \u2014 det f\u00f8rste "
    u"etter \u00e5pningen", 12.5, DEMPET, anchor="end")

# --- fossefallet
ribbon(L, b1, s1x, s1r, RUST)
ribbon(b1, b2, s2x, s2r, BLAA)
ribbon(b2, R, s3x, s3r, NOYTRAL)
# skillekantene i fallet tegnes som harstrek, slik at delingen blir skarp
for xt, xb_ in [(b1, s1r), (b1, s2x), (b2, s2r), (b2, s3x)]:
    line(xt, RIB_TOP, xb_, RIB_BOT, HAARSTREK, 1)

# --- hovedsoylen
rect(s1x, BAR_Y, s1w, BAR_H, RUST)
rect(s2x, BAR_Y, s2w, BAR_H, BLAA)
rect(s3x, BAR_Y, s3w, BAR_H, NOYTRAL)

# innstilt: direkte merking inne i det dominerende feltet
txt(s1x + 24, BAR_Y + 44, u"Innstilt etter konkursloven \u00a7 135", 15, PAPIR,
    weight="600")
txt(s1x + 24, BAR_Y + 67, u"%s bo \u00b7 %s&#160;%% av kohorten" % (n(A_INN), A_INN_P),
    13, PAPIR, opacity="0.86", raw=True)

# merket for de seks boene: smal messingstripe INNE i innstillingsfeltet,
# slik at soylen ikke blir lengre og summen ikke overstiger kohorten
rect(s1r - 3.2, BAR_Y, 3.2, BAR_H, MESSING)

# --- direkte merking av de to smale feltene, under soylen
line(s2x, BAR_B, s2x, BAR_B + 12, HAARSTREK, 1)
txt(s2x, BAR_B + 26, u"Ordin\u00e6r avslutning", 13, BLAA, weight="600")
txt(s2x, BAR_B + 45, u"%s bo \u00b7 %s&#160;%%" % (n(A_AVS), A_AVS_P), 12.5, DEMPET,
    raw=True)

line(s3x + s3w / 2.0, BAR_B, s3x + s3w / 2.0, BAR_B + 58, HAARSTREK, 1)
txt(R, BAR_B + 72, u"Fortsatt uavgjort", 13, NOYTRAL, weight="600", anchor="end")
txt(R, BAR_B + 91, u"%s bo \u00b7 %s&#160;%%" % (n(A_APN), A_APN_P), 12.5, DEMPET,
    anchor="end", raw=True)

# --- annotasjon 1: konkursloven § 135, henger i venstre hjorne av rustfeltet
ANN_TOP, ANN_BOT = BAR_B, BAR_B + 92
rect(L, ANN_TOP, 1.6, ANN_BOT - ANN_TOP, MESSING)
for i, s in enumerate([
        u"Konkursloven \u00a7 135: bobehandlingen innstilles",
        u"n\u00e5r boets midler ikke dekker omkostningene ved",
        u"fortsatt behandling. Boet lukkes uten at det skjer",
        u"noen utbetaling fra boet til kreditorene."]):
    txt(L + 18, ANN_TOP + 24 + i * 18, s, 12.5, BLEKK)

# --- annotasjon 2: de seks boene, henger i hoyre hjorne av rustfeltet
rect(s1r - 1.6, ANN_TOP, 1.6, ANN_BOT - ANN_TOP, MESSING)
for i, s in enumerate([
        u"Seks bo b\u00e6rer b\u00e5de en innstillings- og en",
        u"avslutningskunngj\u00f8ring. De er talt som innstilt,",
        u"aldri som en fjerde kategori \u2014 summen ville da",
        u"overstige kohorten. Ingen av de seks er byggbo."]):
    txt(s1r - 14, ANN_TOP + 24 + i * 18, s, 12.5, BLEKK, anchor="end")

# --- byggsporet som delmengde
txt(L, BY_Y - 22, u"HERAV UTF\u00d8RENDE BYGG OG ANLEGG \u2014 %s AV %s BO, "
    u"SAMME SKALA" % (n(N_BYGG), n(N_ALLE)), 11, DEMPET, weight="500",
    ls="0.14em", raw=True)

rect(t1x, BY_Y, t1w, BY_H, RUST)
rect(t2x, BY_Y, t2w, BY_H, BLAA)
rect(t3x, BY_Y, t3w, BY_H, NOYTRAL)

LX = t3r + 42
for i, (num, share, col, tail) in enumerate([
        (B_INN, B_INN_P, RUST, u"innstilt etter konkursloven \u00a7 135"),
        (B_AVS, B_AVS_P, BLAA, u"ordin\u00e6rt avsluttet"),
        (B_APN, B_APN_P, NOYTRAL, u"fortsatt uavgjort")]):
    add('  <text x="%.2f" y="%.2f" font-size="12.5" fill="%s" '
        'style="font-variant-numeric:tabular-nums">'
        '<tspan font-size="13" font-weight="600" fill="%s">%s bo \u00b7 %s&#160;%%'
        '</tspan><tspan dx="11" fill="%s">%s</tspan></text>'
        % (LX, BY_Y + 10 + i * 19, DEMPET, col, n(num), share, DEMPET, tail))
txt(LX, BY_Y + 10 + 3 * 19 + 4,
    u"andelene er regnet av byggsporets %s bo" % n(N_BYGG), 11, DEMPET,
    raw=True)

# byggsporet er en delmengde, ikke en parallell populasjon
txt(R, BY_Y + 12, u"Byggsporet er en delmengde av de %s boene i" % n(N_ALLE),
    12.5, BLEKK, anchor="end", raw=True)
txt(R, BY_Y + 31, u"søylen over, ikke en parallell populasjon.", 12.5, BLEKK,
    anchor="end")

# --- fotnoter
txt(L, 628, u"Figuren teller bo, ikke kroner: materialet inneholder ingen "
            u"opplysninger om hvor store krav som gikk tapt.", 12.5, BLEKK)
line(L, 656, R, 656, HAARSTREK, 1)
txt(L, 678, u"Byggsikt \u00b7 offentlig tilgjengelige registerkunngj\u00f8ringer "
            u"\u00b7 utfall observert til 24.08.2026", 11, DEMPET)

add('  </g>')
add('</svg>')
add('')

with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(u"\n".join(out))

print("skrev", OUT)
print("scale px/bo  %.6f" % SCALE)
print("soyle  s1 %.2f..%.2f  s2 %.2f..%.2f  s3 %.2f..%.2f" %
      (s1x, s1r, s2x, s2r, s3x, s3r))
print("bygg   t1 %.2f..%.2f  t2 %.2f..%.2f  t3 %.2f..%.2f  (LX %.2f)" %
      (t1x, t1x + t1w, t2x, t2x + t2w, t3x, t3r, LX))
print("baand  b1 %.2f  b2 %.2f" % (b1, b2))
