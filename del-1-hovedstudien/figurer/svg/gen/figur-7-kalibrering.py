# -*- coding: utf-8 -*-
"""Genererer figur 7 - Kalibrering mot offisiell statistikk, kvartal for kvartal.

Kilder (kun disse to filene leses):
  figurer/F5-ssb-kalibrering-bransje_2026-08-30.csv   (SSB 09122, foretakskonkurser)
  data/ssb-kalibrering-2026-08-30.csv                 (SSB 07165, AS/ASA)

Ingen tall er handskrevet i SVG-en; alt hentes fra CSV-ene.
"""
import csv
import os

ROT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
F5 = os.path.join(ROT, "figurer", "F5-ssb-kalibrering-bransje_2026-08-30.csv")
KAL = os.path.join(ROT, "data", "ssb-kalibrering-2026-08-30.csv")
UT = os.path.join(ROT, "figurer", "svg", "figur-7-kalibrering.svg")

# ---------------------------------------------------------------- data
with open(F5, encoding="utf-8") as fh:
    f5 = list(csv.DictReader(fh))
with open(KAL, encoding="utf-8") as fh:
    kal = list(csv.DictReader(fh, delimiter=";"))

KV = [r["kvartal"] for r in f5]                      # 2023K1 .. 2026K2 (14)
assert KV[0] == "2023K1" and KV[-1] == "2026K2" and len(KV) == 14

f = lambda r, k: float(r[k])
tf_alle = [f(r, "dekning_alle_pst") for r in f5]      # 09122, alle naeringer
tf_bygg = [f(r, "dekning_bygg_pst") for r in f5]      # 09122, bygg (SN2007-tilbakefoert)
and_ssb = [f(r, "ssb_byggandel_pst") for r in f5]
and_var = [f(r, "vaar_byggandel_pst") for r in f5]

kal_kv = [r["kvartal"] for r in kal]                  # 2023K3 .. 2026K2 (12)
tf_asa = [f(r, "dekning_AS_ASA_pst") for r in kal]    # 07165, AS/ASA
assert kal_kv == KV[2:]

# kohortkvartalene: de fem hele kvartalene 2023K4-2024K4
KOH = [i for i, k in enumerate(KV) if k in ("2023K4", "2024K1", "2024K2", "2024K3", "2024K4")]
koh_var = sum(int(f5[i]["vaart_materiale_alle"]) for i in KOH)
koh_ssb = sum(int(f5[i]["ssb_foretakskonkurser_alle"]) for i in KOH)
koh_tf = 100.0 * koh_var / koh_ssb
koh_var_b = sum(int(f5[i]["vaart_materiale_bygg"]) for i in KOH)
koh_ssb_b = sum(int(f5[i]["ssb_foretakskonkurser_bygg"]) for i in KOH)
koh_and_var = 100.0 * koh_var_b / koh_var
koh_and_ssb = 100.0 * koh_ssb_b / koh_ssb

asa_min, asa_maks = min(tf_asa), max(tf_asa)

# ---------------------------------------------------------------- norsk format
NBSP = "&#160;"


def n1(v):
    return ("%.1f" % v).replace(".", ",")


def n2(v):
    return ("%.2f" % v).replace(".", ",")


def tusen(v):
    s = "%d" % v
    ut = ""
    while len(s) > 3:
        ut = NBSP + s[-3:] + ut
        s = s[:-3]
    return s + ut


def pst1(v):
    return n1(v) + NBSP + "%"


def pst2(v):
    return n2(v) + NBSP + "%"


# ---------------------------------------------------------------- palett
PAPIR = "#f5f0e6"
PAPIRD = "#e9e1d4"
BLEKK = "#171815"
DEMPET = "#625e55"
HAAR = "#d8cfbe"
BYGG = "#9a4d35"
OVRIG = "#2e6f91"
AKSENT = "#b9782f"
NOYTRAL = "#8c9a8e"
SKRIFT = "Euclid Circular B, Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif"
TAB = 'font-variant-numeric="tabular-nums" style="font-variant-numeric:tabular-nums"'

# ---------------------------------------------------------------- geometri
W, H = 1200, 832
X0, X1 = 76.0, 996.0                 # plottflate
LBL = 1006.0                         # kolonne for direkte serie-etiketter
STEG = (X1 - X0) / (len(KV) - 1)
X = [X0 + STEG * i for i in range(len(KV))]
SKRAV_X1 = (X[1] + X[2]) / 2.0       # skravur dekker 2023K1-2023K2

PA_T, PA_B, PA_LO, PA_HI = 176.0, 400.0, 96.6, 104.4
PB_T, PB_B, PB_LO, PB_HI = 456.0, 552.0, 98.0, 104.0
PC_T, PC_B, PC_LO, PC_HI = 604.0, 730.0, 0.0, 40.0


def ya(v):
    return PA_B - (v - PA_LO) * (PA_B - PA_T) / (PA_HI - PA_LO)


def yb(v):
    return PB_B - (v - PB_LO) * (PB_B - PB_T) / (PB_HI - PB_LO)


def yc(v):
    return PC_B - (v - PC_LO) * (PC_B - PC_T) / (PC_HI - PC_LO)


def bane(xs, ys):
    return "M " + " L ".join("%.2f %.2f" % (x, y) for x, y in zip(xs, ys))


def txt(x, y, s, farge=DEMPET, storrelse=12.5, vekt=400, anker="start",
        tabular=False, spacing=None, ekstra=""):
    a = ' text-anchor="%s"' % anker if anker != "start" else ""
    ls = ' letter-spacing="%s"' % spacing if spacing else ""
    tb = " " + TAB if tabular else ""
    return ('<text x="%.2f" y="%.2f" font-size="%s" font-weight="%d" fill="%s"%s%s%s%s>%s</text>'
            % (x, y, storrelse, vekt, farge, a, ls, tb, ekstra, s))


o = []
o.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
         'preserveAspectRatio="xMidYMid meet" role="img" '
         'aria-labelledby="tittel7 beskr7" font-family="%s">' % (W, H, SKRIFT))
o.append('<title id="tittel7">Figur 7. Kalibrering mot offisiell statistikk, '
         'kvartal for kvartal.</title>')
o.append('<desc id="beskr7">Tre panel med felles kvartalsakse fra f&#248;rste kvartal 2023 til '
         'andre kvartal 2026. &#216;verste panel viser telleforholdet mellom v&#229;r telling av '
         'konkurs&#229;pninger og Statistisk sentralbyr&#229;s foretakskonkurser (tabell 09122), '
         'for alle n&#230;ringer i bl&#229;tt og for bygge- og anleggsvirksomhet i rust; begge '
         'serier ligger mellom %s og %s prosent fra tredje kvartal 2023 og ut serien, rundt '
         'referanselinjen p&#229; 100 prosent i messing. Midtpanelet viser det samme '
         'telleforholdet for aksje- og allmennaksjeselskaper (tabell 07165), med kvartalsvis '
         'spenn %s til %s prosent. Nederste panel viser byggandelen av foretakskonkursene i '
         'begge kilder; de to kurvene f&#248;lger hverandre nesten punkt for punkt. De to '
         'f&#248;rste kvartalene i 2023 er skravert som utenfor det observerbare vinduet.</desc>'
         % (n1(min(min(tf_alle[2:]), min(tf_bygg[2:]))),
            n1(max(max(tf_alle[2:]), max(tf_bygg[2:]))),
            n1(asa_min), n1(asa_maks)))

o.append('<defs><pattern id="skravur" width="9" height="9" patternUnits="userSpaceOnUse" '
         'patternTransform="rotate(45)">'
         '<rect width="9" height="9" fill="%s"/>'
         '<line x1="0" y1="0" x2="0" y2="9" stroke="%s" stroke-width="1.3"/>'
         '</pattern></defs>' % (PAPIRD, HAAR))

o.append('<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (W, H, PAPIR))

# ---------------------------------------------------------------- tittelblokk
o.append(txt(X0, 46, "FIGUR 7 &#183; EKSTERN KALIBRERING", DEMPET, 11, 400,
             spacing="0.14em"))
o.append(txt(X0, 76, "Kalibrering mot offisiell statistikk, kvartal for kvartal",
             BLEKK, 21, 600))
o.append(txt(X0, 103, "Telleforhold: v&#229;r telling av konkurs&#229;pninger delt p&#229; "
             "byr&#229;ets, kvartal for kvartal. Referanselinjen 100&#160;% er byr&#229;ets tall.",
             DEMPET, 14.5))
o.append(txt(X0, 122, "Et telleforhold er ikke en dekningsgrad: verdier litt over 100&#160;% "
             "er revisjonsetterslep og avgrensningsforskjell, ikke overtelling.",
             DEMPET, 14.5))

# ---------------------------------------------------------------- panelrubrikker
def rubrikk(y, hoved, tabell):
    return ('<text x="%.2f" y="%.2f" font-size="13" font-weight="600" fill="%s">%s'
            '<tspan dx="14" font-size="12.5" font-weight="400" fill="%s" %s>%s</tspan>'
            '</text>' % (X0, y, BLEKK, hoved, DEMPET, TAB, tabell))


o.append(rubrikk(163, "Telleforhold i prosent &#183; foretakskonkurser",
                 "SSB-tabell 09122"))
o.append(rubrikk(444, "Telleforhold i prosent &#183; aksje- og allmennaksjeselskaper",
                 "SSB-tabell 07165"))
o.append(rubrikk(592, "Byggandel i prosent &#183; foretakskonkurser",
                 "SSB-tabell 09122"))

# ---------------------------------------------------------------- skravur (bak alt)
for t, b in ((PA_T, PA_B), (PB_T, PB_B), (PC_T, PC_B)):
    o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="url(#skravur)"/>'
             % (X0, t, SKRAV_X1 - X0, b - t))

# ---------------------------------------------------------------- harstreker + akseverdier
def haar(y):
    return ('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="1"/>'
            % (X0, y, X1, y, HAAR))


def referanse(y):
    return ('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="1.6"/>'
            % (X0, y, X1, y, AKSENT))


for v in (104, 102, 98):
    o.append(haar(ya(v)))
for v in (98, 102):
    o.append(haar(yb(v)))
for v in (0, 10, 20, 30, 40):
    o.append(haar(yc(v)))
o.append(referanse(ya(100)))
o.append(referanse(yb(100)))

for v in (104, 102, 98):
    o.append(txt(68, ya(v) + 4.4, "%d" % v, DEMPET, 12.5, 400, "end", True))
o.append(txt(68, ya(100) + 4.4, "100", AKSENT, 12.5, 500, "end", True))
for v in (102, 98):
    o.append(txt(68, yb(v) + 4.4, "%d" % v, DEMPET, 12.5, 400, "end", True))
o.append(txt(68, yb(100) + 4.4, "100", AKSENT, 12.5, 500, "end", True))
for v in (40, 30, 20, 10, 0):
    o.append(txt(68, yc(v) + 4.4, "%d" % v, DEMPET, 12.5, 400, "end", True))

# ---------------------------------------------------------------- skravurmerking
for i, s in enumerate(("UTENFOR DET", "OBSERVERBARE", "VINDUET")):
    o.append(txt(82, 202 + 16 * i, s, NOYTRAL, 11, 500, spacing="0.08em"))

# ---------------------------------------------------------------- panel A: data
xa = X[2:]
o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.8" stroke-linejoin="round" '
         'stroke-linecap="round"/>' % (bane(xa, [ya(v) for v in tf_alle[2:]]), OVRIG))
o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.8" stroke-linejoin="round" '
         'stroke-linecap="round"/>' % (bane(xa, [ya(v) for v in tf_bygg[2:]]), BYGG))
for x, v in zip(xa, tf_alle[2:]):
    o.append('<circle cx="%.2f" cy="%.2f" r="2.6" fill="%s"/>' % (x, ya(v), OVRIG))
# bygg-serien far rombe, ikke sirkel: de to seriene krysser hverandre, og rust og bla
# skiller seg lite i lyshet - formen barer forskjellen ogsa uten farge.
for x, v in zip(xa, tf_bygg[2:]):
    y, d = ya(v), 3.5
    o.append('<path d="M %.2f %.2f L %.2f %.2f L %.2f %.2f L %.2f %.2f Z" fill="%s"/>'
             % (x, y - d, x + d, y, x, y + d, x - d, y, BYGG))

# ytterpunkter i panel A, ringmerket
i_max = 2 + tf_bygg[2:].index(max(tf_bygg[2:]))
i_min = 2 + tf_alle[2:].index(min(tf_alle[2:]))
o.append('<circle cx="%.2f" cy="%.2f" r="5.6" fill="none" stroke="%s" stroke-width="1.4"/>'
         % (X[i_max], ya(tf_bygg[i_max]), BYGG))
o.append(txt(X[i_max] + 12, ya(tf_bygg[i_max]) - 3, pst1(tf_bygg[i_max]), BYGG, 12.5, 600,
             tabular=True))
o.append('<circle cx="%.2f" cy="%.2f" r="5.6" fill="none" stroke="%s" stroke-width="1.4"/>'
         % (X[i_min], ya(tf_alle[i_min]), OVRIG))
o.append(txt(X[i_min] + 12, ya(tf_alle[i_min]) + 8, pst1(tf_alle[i_min]), OVRIG, 12.5, 600,
             tabular=True))

# merknad om det utelatte vinduet
merk = [
    "I de to skraverte kvartalene er telleforholdet %s og" % pst1(tf_alle[0]),
    "%s &#8212; langt under panelets skala. Kunngj&#248;ringer eldre" % pst1(tf_alle[1]),
    "enn oppbevaringsperioden er ikke tilgjengelige hos kilden.",
]
for i, s in enumerate(merk):
    o.append(txt(196, 202 + 18 * i, s, BLEKK, 12.5, 400, tabular=True))

# direkte etiketter, panel A
o.append('<line x1="999" y1="%.2f" x2="1003" y2="266" stroke="%s" stroke-width="1"/>'
         % (ya(tf_alle[-1]), OVRIG))
o.append('<line x1="999" y1="%.2f" x2="1003" y2="288" stroke="%s" stroke-width="1"/>'
         % (ya(tf_bygg[-1]), BYGG))
o.append(txt(LBL, 270, "Alle n&#230;ringer", OVRIG, 13, 600))
o.append(txt(LBL, 292, "Bygg og anlegg", BYGG, 13, 600))
o.append(txt(LBL, 308, "SN2007-tilbakef&#248;rt", DEMPET, 11, 400, tabular=True))

# ---------------------------------------------------------------- kohortmarkor
ky = 416.0
o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="1.5"/>'
         % (X[KOH[0]], ky, X[KOH[-1]], ky, AKSENT))
for i in (KOH[0], KOH[-1]):
    o.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="1.5"/>'
             % (X[i], ky - 4.5, X[i], ky + 4.5, AKSENT))
o.append(txt(X[KOH[-1]] + 14, ky + 4.2,
             "Kohortkvartalene 2023K4&#8211;2024K4 &#183; %s mot %s = %s"
             % (tusen(koh_var), tusen(koh_ssb), pst1(koh_tf)), BLEKK, 12.5, 400, tabular=True))

# ---------------------------------------------------------------- panel B: data
o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.8" stroke-linejoin="round" '
         'stroke-linecap="round"/>' % (bane(xa, [yb(v) for v in tf_asa]), OVRIG))
for x, v in zip(xa, tf_asa):
    o.append('<circle cx="%.2f" cy="%.2f" r="2.4" fill="%s"/>' % (x, yb(v), OVRIG))
for j, v in enumerate(tf_asa):
    if v in (asa_min, asa_maks):
        o.append('<circle cx="%.2f" cy="%.2f" r="6.0" fill="none" stroke="%s" '
                 'stroke-width="1.4"/>' % (xa[j], yb(v), OVRIG))
j_maks = tf_asa.index(asa_maks)
o.append(txt(xa[j_maks], yb(asa_maks) - 11, pst1(asa_maks), OVRIG, 12.5, 600, "middle", True))
o.append(txt(196, 480, "Kvartalsvis spenn %s&#8211;%s over de tolv kvartalene i det "
             "observerbare vinduet." % (n1(asa_min), pst1(asa_maks)),
             BLEKK, 12.5, 400, tabular=True))
o.append('<line x1="999" y1="%.2f" x2="1003" y2="498" stroke="%s" stroke-width="1"/>'
         % (yb(tf_asa[-1]), OVRIG))
o.append(txt(LBL, 502, "AS og ASA", OVRIG, 13, 600))

# ---------------------------------------------------------------- panel C: data
o.append('<path d="%s" fill="none" stroke="%s" stroke-width="3.8" stroke-linejoin="round" '
         'stroke-linecap="round"/>' % (bane(X, [yc(v) for v in and_ssb]), OVRIG))
o.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.8" stroke-linejoin="round" '
         'stroke-linecap="round"/>' % (bane(X, [yc(v) for v in and_var]), BYGG))
o.append(txt(196, 716,
             "De fem kohortkvartalene 2023K4&#8211;2024K4: byggandelen er %s i v&#229;rt "
             "materiale mot %s hos byr&#229;et." % (pst2(koh_and_var), pst2(koh_and_ssb)),
             BLEKK, 12.5, 400, tabular=True))
o.append('<line x1="999" y1="%.2f" x2="1003" y2="642" stroke="%s" stroke-width="1"/>'
         % (yc(and_var[-1]), BYGG))
o.append('<line x1="999" y1="%.2f" x2="1003" y2="662" stroke="%s" stroke-width="1"/>'
         % (yc(and_ssb[-1]), OVRIG))
o.append(txt(LBL, 646, "V&#229;rt materiale", BYGG, 13, 600))
o.append(txt(LBL, 666, "Byr&#229;et", OVRIG, 13, 600))
o.append(txt(LBL, 684, "begge %s i 2026K2" % pst1(and_var[-1]), DEMPET, 11, 400, tabular=True))

# ---------------------------------------------------------------- x-akse
for i, k in enumerate(KV):
    o.append(txt(X[i], 750, k[4:], DEMPET, 12.5, 400, "middle", True))
aar = {}
for i, k in enumerate(KV):
    aar.setdefault(k[:4], []).append(X[i])
for a, xs in aar.items():
    o.append(txt((xs[0] + xs[-1]) / 2.0, 770, a, DEMPET, 12.5, 600, "middle", True))

# ---------------------------------------------------------------- fotnoter
o.append(txt(X0, 792, "Byggserien er f&#248;rt tilbake til SN2007-standarden; uten "
             "tilbakef&#248;ringen er serien ikke sammenliknbar. En dekningsgrad kan per "
             "definisjon ikke overstige 100&#160;% &#8212; et telleforhold kan det.",
             DEMPET, 11, 400, tabular=True))
o.append(txt(X0, 810, "Byggsikt &#183; offentlig tilgjengelige registerkunngj&#248;ringer "
             "&#183; utfall observert til 24.08.2026 &#183; Statistisk sentralbyr&#229;, "
             "statistikkbanktabell 09122 og 07165, hentet 30.08.2026", DEMPET, 11, 400,
             tabular=True))

o.append("</svg>")

with open(UT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(o) + "\n")

print("skrev", UT)
print("kohort  %s mot %s = %s" % (tusen(koh_var), tusen(koh_ssb), pst1(koh_tf)))
print("byggandel kohort  vaar %s  ssb %s" % (pst2(koh_and_var), pst2(koh_and_ssb)))
print("AS/ASA spenn  %s - %s" % (n1(asa_min), n1(asa_maks)))
print("09122 spenn i vindu  alle %s-%s  bygg %s-%s"
      % (n1(min(tf_alle[2:])), n1(max(tf_alle[2:])),
         n1(min(tf_bygg[2:])), n1(max(tf_bygg[2:]))))
