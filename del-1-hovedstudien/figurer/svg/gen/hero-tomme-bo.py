# -*- coding: utf-8 -*-
"""
Genererer hero-bildet til «Tomme bo» — en unit-visualisering der hver markør er
ett konkursbo i kohorten. Rutenettet er 100 markører per rad; 5 165 markører
totalt, fordelt 3 897 / 258 / 659 / 351.

Datagrunnlag: figurer/fossefall-per-1000-bo-2026-08-30.csv
  ALLE  : bo 5165, innstilt 3897, kun_avsluttet 917, fortsatt_apne 351
  BYGG  : bo 1280, innstilt  911, kun_avsluttet 258, fortsatt_apne 111
  ØVRIGE: bo 3885, innstilt 2986, kun_avsluttet 659, fortsatt_apne 240

Kjør:  python hero-tomme-bo.py
"""

import csv
import io
import os

HER = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.abspath(os.path.join(HER, "..", "..", "fossefall-per-1000-bo-2026-08-30.csv"))
UT = os.path.abspath(os.path.join(HER, "..", "hero-tomme-bo.svg"))

# ---------------------------------------------------------------- data ------
rader = {}
with io.open(CSV, "r", encoding="utf-8") as f:
    for rad in csv.DictReader(f, delimiter=";"):
        if rad.get("gruppe"):
            rader[rad["gruppe"]] = rad

ALLE = rader["ALLE næringer"]
BYGG = rader["BYGG (utførende)"]
OVRIGE = rader["ØVRIGE næringer"]

N_TOTAL = int(ALLE["bo"])                 # 5165
N_INNSTILT = int(ALLE["innstilt"])        # 3897
N_AVSLUTTET = int(ALLE["kun_avsluttet"])  # 917
N_APNE = int(ALLE["fortsatt_apne"])       # 351

N_BYGG_AVSL = int(BYGG["kun_avsluttet"])      # 258
N_OVR_AVSL = int(OVRIGE["kun_avsluttet"])     # 659
N_BYGG_INNST = int(BYGG["innstilt"])          # 911
N_OVR_INNST = int(OVRIGE["innstilt"])         # 2986

assert N_INNSTILT + N_AVSLUTTET + N_APNE == N_TOTAL
assert N_BYGG_AVSL + N_OVR_AVSL == N_AVSLUTTET
assert N_BYGG_INNST + N_OVR_INNST == N_INNSTILT
assert int(BYGG["fortsatt_apne"]) + int(OVRIGE["fortsatt_apne"]) == N_APNE

# ---------------------------------------------------------------- palett ----
PAPIR = "#f5f0e6"
PAPIR_DYP = "#e9e1d4"
BLEKK = "#171815"
DEMPET = "#625e55"
HAARSTREK = "#d8cfbe"
BYGG_F = "#9a4d35"
OVRIG_F = "#2e6f91"
NOYTRAL = "#8c9a8e"

FONT = "Euclid Circular B, Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif"
TAB = ' font-variant-numeric="tabular-nums" style="font-variant-numeric:tabular-nums"'

W, H = 1600, 900

# ------------------------------------------------------------- geometri -----
KOL = 100                # markører per rad — hver rad er nøyaktig 100 bo
GRUPPE = 10              # kolonnegruppe: 10 grupper à 10 kolonner
CX0 = 79.0               # senter, første kolonne (optisk venstrekant = 76)
P = 9.7798               # kolonnesteg
G = 3.2                  # ekstra luft mellom kolonnegrupper
CY0 = 296.0              # senter, første rad
Q = 9.70                 # radsteg

R_RING = 3.05            # hule markører (innstilt)
SW_RING = 1.18
R_DISK = 3.15            # fylte sirkler (øvrige avsluttet, uavgjort)
SIDE_KVAD = 5.58         # fylt kvadrat (bygg avsluttet) — arealmatchet disken


def x_av(kol):
    return CX0 + kol * P + (kol // GRUPPE) * G


def y_av(rad):
    return CY0 + rad * Q


def n(v):
    """Kort tallformat uten etterslepende nuller."""
    s = "%.2f" % v
    return s.rstrip("0").rstrip(".")


# Sekvensen leses radvis, ovenfra og ned. Fire segmenter i rekkefølge.
SEGMENTER = [
    ("innstilt", N_INNSTILT),
    ("bygg_avsluttet", N_BYGG_AVSL),
    ("ovrig_avsluttet", N_OVR_AVSL),
    ("uavgjort", N_APNE),
]

markorer = {navn: [] for navn, _ in SEGMENTER}
i = 0
for navn, antall in SEGMENTER:
    for _ in range(antall):
        markorer[navn].append((x_av(i % KOL), y_av(i // KOL)))
        i += 1
assert i == N_TOTAL
for navn, antall in SEGMENTER:
    assert len(markorer[navn]) == antall

SISTE_RAD = (N_TOTAL - 1) // KOL
FELT_TOPP = CY0 - R_RING - SW_RING / 2
FELT_BUNN = y_av(SISTE_RAD) + R_DISK
FELT_HOYRE = x_av(KOL - 1) + R_DISK

# Vertikale midtpunkt for hvert bånd (brukes til å sikte lederstrekene).
grenser = {}
lop = 0
for navn, antall in SEGMENTER:
    grenser[navn] = (y_av(lop // KOL), y_av((lop + antall - 1) // KOL))
    lop += antall

# ------------------------------------------------------------- tegning ------
o = []
a = o.append

a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
  'preserveAspectRatio="xMidYMid meet" role="img" '
  'aria-labelledby="hero-tittel hero-desc" font-family="%s">' % (W, H, FONT))
a('<title id="hero-tittel">Tomme bo — 5&#160;165 konkursbo etter norske aksjeselskaper, '
  'ett bo per markør</title>')
a('<desc id="hero-desc">Feltet inneholder 5&#160;165 markører, én for hvert konkursbo i '
  'kohorten som ble åpnet 1. september 2023 til 31. desember 2024. Markørene leses radvis '
  'ovenfra og ned, hundre bo per rad. De 3&#160;897 øverste — 75,5 prosent, nesten trettini '
  'hele rader — er tegnet som hule ringer og er bo som ble innstilt etter konkursloven '
  '§ 135 fordi midlene ikke dekket omkostningene ved fortsatt bobehandling. Under dem ligger '
  '917 fylte markører for bo som nådde ordinær avslutning: 258 rustrøde kvadrater for bygg og '
  'anlegg og 659 blå sirkler for øvrige næringer. Nederst ligger 351 grågrønne sirkler for bo '
  'som fortsatt var uavgjorte 24. august 2026.</desc>')
a('<rect width="%d" height="%d" fill="%s"/>' % (W, H, PAPIR))

# --- tittelblokk ------------------------------------------------------------
a('<text x="76" y="82" font-size="11" letter-spacing="0.14em" fill="%s">'
  'REGISTERSTUDIE &#183; INSOLVENS &#183; NORGE &#183; BYGGSIKT DATA</text>' % DEMPET)
a('<text x="76" y="148" font-size="60" font-weight="600" fill="%s">Tomme bo</text>' % BLEKK)
a('<text x="76" y="188" font-size="20.5" fill="%s">Tre av fire konkursbo etter norske '
  'aksjeselskaper lukkes uten midler</text>' % BLEKK)
a('<text x="76" y="214" font-size="14.5" fill="%s"%s>Utfallet av 5&#160;165 '
  'selskapskonkursbo (AS og ASA) åpnet 1.&#160;september 2023 &#8211; 31.&#160;desember '
  '2024,</text>' % (DEMPET, TAB))
a('<text x="76" y="234" font-size="14.5" fill="%s"%s>etter næring, rettskrets og tid til '
  'innstilling. Utfall observert til 24.&#160;august 2026.</text>' % (DEMPET, TAB))

# bærende tall, høyrestilt mot samme grunnlinje som tittelen
a('<text x="1544" y="148" text-anchor="end" font-size="72" font-weight="600" fill="%s"%s>'
  '75,5&#160;%%</text>' % (BLEKK, TAB))
a('<text x="1544" y="182" text-anchor="end" font-size="13" fill="%s"%s>av de 5&#160;165 '
  'konkursboene ble innstilt etter</text>' % (DEMPET, TAB))
a('<text x="1544" y="200" text-anchor="end" font-size="13" fill="%s"%s>konkursloven '
  '§&#160;135 og lukket uten midler</text>' % (DEMPET, TAB))
a('<text x="1544" y="226" text-anchor="end" font-size="11.5" fill="%s"%s>Observert per '
  '24.08.2026. Ved en fast horisont på 24 måneder</text>' % (DEMPET, TAB))
a('<text x="1544" y="242" text-anchor="end" font-size="11.5" fill="%s"%s>er den kumulative '
  'insidensen for innstilling 74,8&#160;%%.</text>' % (DEMPET, TAB))

a('<line x1="76" y1="254" x2="1544" y2="254" stroke="%s" stroke-width="1"/>' % HAARSTREK)
a('<text x="76" y="278" font-size="12" fill="%s"%s>Hver markør er ett konkursbo &#183; '
  '5&#160;165 markører &#183; hver rad er 100 bo</text>' % (DEMPET, TAB))
a('<text x="%s" y="278" text-anchor="end" font-size="12" fill="%s"%s>Sekvensen leses radvis, '
  'ovenfra og ned</text>' % (n(FELT_HOYRE), DEMPET, TAB))

# --- markørfeltet -----------------------------------------------------------
a('<g fill="none" stroke="%s" stroke-width="%s">' % (DEMPET, n(SW_RING)))
for (cx, cy) in markorer["innstilt"]:
    a('<circle cx="%s" cy="%s" r="%s"/>' % (n(cx), n(cy), n(R_RING)))
a('</g>')

a('<g fill="%s">' % BYGG_F)
for (cx, cy) in markorer["bygg_avsluttet"]:
    a('<rect x="%s" y="%s" width="%s" height="%s"/>'
      % (n(cx - SIDE_KVAD / 2), n(cy - SIDE_KVAD / 2), n(SIDE_KVAD), n(SIDE_KVAD)))
a('</g>')

a('<g fill="%s">' % OVRIG_F)
for (cx, cy) in markorer["ovrig_avsluttet"]:
    a('<circle cx="%s" cy="%s" r="%s"/>' % (n(cx), n(cy), n(R_DISK)))
a('</g>')

a('<g fill="%s">' % NOYTRAL)
for (cx, cy) in markorer["uavgjort"]:
    a('<circle cx="%s" cy="%s" r="%s"/>' % (n(cx), n(cy), n(R_DISK)))
a('</g>')

# --- direkte etiketter i høyrespalten ---------------------------------------
LED_X1, LED_X2 = 1092.0, 1116.0     # lederstrek fra feltet
GLYF_X = 1124.0                     # markørnøkkel ved etiketten
TXT_X = 1140.0                      # tekstkant


def leder(y, farge):
    a('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1"/>'
      % (n(LED_X1), n(y), n(LED_X2), n(y), farge))


# 1 — innstilt (de hule markørene)
leder(418, DEMPET)
a('<circle cx="%s" cy="418" r="4.3" fill="none" stroke="%s" stroke-width="1.5"/>'
  % (n(GLYF_X), DEMPET))
a('<text x="%s" y="422" font-size="11" letter-spacing="0.13em" fill="%s"%s>'
  'INNSTILT ETTER KONKURSLOVEN §&#160;135</text>' % (n(TXT_X), DEMPET, TAB))
a('<text x="%s" y="452" font-size="17" font-weight="600" fill="%s"%s>3&#160;897 av '
  '5&#160;165 bo</text>' % (n(TXT_X), BLEKK, TAB))
for k, linje in enumerate([
        "Bobehandlingen stanset fordi boets midler ikke dekket",
        "omkostningene ved fortsatt bobehandling. Ingen utbetaling",
        "fra boet til kreditorene &#8212; pantsikrede krav og lønnskrav",
        "kan likevel være dekket utenfor boet."]):
    a('<text x="%s" y="%s" font-size="12.5" fill="%s">%s</text>'
      % (n(TXT_X), 480 + k * 18, DEMPET, linje))

# 2 — ordinær avslutning, med byggsporet skilt ut
a('<text x="%s" y="638" font-size="11" letter-spacing="0.13em" fill="%s"%s>'
  'ORDINÆR AVSLUTNING &#183; 917 BO &#183; 17,8&#160;%%</text>' % (n(TXT_X), DEMPET, TAB))

leder(670, BYGG_F)
a('<rect x="%s" y="%s" width="7.9" height="7.9" fill="%s"/>'
  % (n(GLYF_X - 3.95), n(670 - 3.95), BYGG_F))
a('<text x="%s" y="674" font-size="13.5" font-weight="600" fill="%s"%s>Bygg og anlegg '
  '&#183; 258 bo &#183; 5,0&#160;%%</text>' % (n(TXT_X), BYGG_F, TAB))

leder(718, OVRIG_F)
a('<circle cx="%s" cy="718" r="4.4" fill="%s"/>' % (n(GLYF_X), OVRIG_F))
a('<text x="%s" y="722" font-size="13.5" font-weight="600" fill="%s"%s>Øvrige næringer '
  '&#183; 659 bo &#183; 12,8&#160;%%</text>' % (n(TXT_X), OVRIG_F, TAB))

# 3 — fortsatt uavgjort
a('<text x="%s" y="758" font-size="11" letter-spacing="0.13em" fill="%s"%s>'
  'FORTSATT UAVGJORT PER 24.08.2026</text>' % (n(TXT_X), DEMPET, TAB))
leder(782, NOYTRAL)
a('<circle cx="%s" cy="782" r="4.4" fill="%s"/>' % (n(GLYF_X), NOYTRAL))
a('<text x="%s" y="786" font-size="13.5" font-weight="600" fill="%s"%s>351 bo &#183; '
  '6,8&#160;%% av kohorten</text>' % (n(TXT_X), DEMPET, TAB))

# presisering: farge-skillet gjelder bare de avsluttede boene
for k, linje in enumerate([
        "Bygg og øvrige næringer er skilt ut bare blant de boene",
        "som nådde ordinær avslutning. Av de 3&#160;897 innstilte er",
        "911 i bygg og anlegg og 2&#160;986 i øvrige næringer."]):
    a('<text x="%s" y="%s" font-size="11.5" fill="%s"%s>%s</text>'
      % (n(TXT_X), 812 + k * 15, DEMPET, TAB, linje))

# --- kolofonbånd ------------------------------------------------------------
a('<rect x="0" y="862" width="%d" height="%d" fill="%s"/>' % (W, H - 862, PAPIR_DYP))
a('<text x="76" y="885" font-size="11" fill="%s"%s>Byggsikt &#183; offentlig tilgjengelige '
  'registerkunngjøringer &#183; utfall observert til 24.08.2026</text>' % (DEMPET, TAB))

a('</svg>')

with io.open(UT, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(o) + "\n")

# ---------------------------------------------------------------- kontroll --
print("skrevet:", UT)
print("markører  innstilt        :", len(markorer["innstilt"]))
print("markører  bygg avsluttet  :", len(markorer["bygg_avsluttet"]))
print("markører  øvrig avsluttet :", len(markorer["ovrig_avsluttet"]))
print("markører  uavgjort        :", len(markorer["uavgjort"]))
print("markører  SUM             :", sum(len(v) for v in markorer.values()))
print("rader i feltet            :", SISTE_RAD + 1, "(siste rad har",
      N_TOTAL - SISTE_RAD * KOL, "markører)")
print("feltets utstrekning       : x %.1f-%.1f  y %.1f-%.1f"
      % (CX0 - R_RING, FELT_HOYRE, FELT_TOPP, FELT_BUNN))
for navn, _ in SEGMENTER:
    print("bånd %-16s: y %.1f - %.1f" % (navn, grenser[navn][0], grenser[navn][1]))
print("andeler: innstilt %.2f %%  avsluttet %.2f %%  uavgjort %.2f %%"
      % (100.0 * N_INNSTILT / N_TOTAL, 100.0 * N_AVSLUTTET / N_TOTAL,
         100.0 * N_APNE / N_TOTAL))
print("         bygg avsl %.2f %%  øvrig avsl %.2f %%"
      % (100.0 * N_BYGG_AVSL / N_TOTAL, 100.0 * N_OVR_AVSL / N_TOTAL))
