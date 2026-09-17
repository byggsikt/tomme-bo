# -*- coding: utf-8 -*-
"""
Genererer figur-3-byggfag.svg — «Innstillingsandel per byggfag, med eksakte
konfidensintervaller».

Alle tall leses fra F1-byggfag-innstillingsandel_2026-08-30.csv. Kun rader med
vises_i_figur3 = true tegnes. Referansenivaaene 75,5 % (kohorten samlet) og
71,2 % (utfoerende bygg) er paalagt av figurteksten i FERDIG-MANUS.md.
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH = os.path.join(ROOT, "F1-byggfag-innstillingsandel_2026-08-30.csv")
OUT_PATH = os.path.join(ROOT, "svg", "figur-3-byggfag.svg")

# ---------------------------------------------------------------- palett (laast)
PAPIR = "#f5f0e6"
BLEKK = "#171815"
DEMPET = "#625e55"
HAIR = "#d8cfbe"
BYGG = "#9a4d35"
AKSENT = "#b9782f"

FONT = "Euclid Circular B, Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif"
NUM = 'font-variant-numeric="tabular-nums" style="font-variant-numeric:tabular-nums"'

NBSP = " "          # hardt mellomrom  -> &#160;
EMSP = " "          # em-mellomrom     -> &#8195;
SEP = EMSP + "·" + EMSP

# ---------------------------------------------------------------- geometri
W, H = 1200, 780
M_L, M_R = 76, 56
X0 = 340.0                       # 0 % — verdiaksens nullpunkt
X100 = float(W - M_R)            # 100 %
SPAN = X100 - X0

Y_ROW0, PITCH = 220.0, 66.0
GRID_TOP, GRID_BOT = 206.0, 564.0
REF_TOP = 178.0
ANN_RIGHT = 812.0                # felles hoyrekant for begge annotasjoner

REF_LINES = [(71.2, "Utførende bygg 71,2" + NBSP + "%", "end"),
             (75.5, "Kohorten samlet 75,5" + NBSP + "%", "start")]


def x(p):
    return X0 + (p / 100.0) * SPAN


def nb(v):
    return ("%.1f" % v).replace(".", ",")


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace(NBSP, "&#160;").replace(EMSP, "&#8195;"))


def text(x_, y_, s, size, fill, weight=None, anchor=None, ls=None, raw=False):
    at = ['x="%s"' % (("%.2f" % x_).rstrip("0").rstrip(".")), 'y="%.1f"' % y_,
          'font-family="%s"' % FONT, 'font-size="%s"' % size, 'fill="%s"' % fill]
    if weight:
        at.append('font-weight="%s"' % weight)
    if anchor:
        at.append('text-anchor="%s"' % anchor)
    if ls:
        at.append('letter-spacing="%s"' % ls)
    at.append(NUM)
    return "<text %s>%s</text>" % (" ".join(at), s if raw else esc(s))


# ---------------------------------------------------------------- data
rows = []
with open(CSV_PATH, encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        if r["vises_i_figur3"].strip().lower() == "true":
            rows.append({"navn": r["naering"].strip(),
                         "n": int(r["n_apnede_bo"]),
                         "innstilt": int(r["innstilt"]),
                         "ikke": int(r["ikke_innstilt"]),
                         "pst": float(r["innstilt_pst"]),
                         "lo": float(r["ki95_lav"]),
                         "hi": float(r["ki95_hoy"])})
rows.sort(key=lambda d: -d["pst"])

assert len(rows) == 6, rows
for d in rows:                                    # personvern: minste celle er 10
    assert d["innstilt"] >= 10 and d["ikke"] >= 10, d
    assert d["lo"] <= d["pst"] <= d["hi"], d
# paastanden i noten under figuren:
assert all(d["lo"] <= 71.2 <= d["hi"] for d in rows)
assert rows[0]["navn"].startswith("Snekker") and rows[-1]["navn"].startswith("Rørlegger")
NARROW = min(range(6), key=lambda i: rows[i]["hi"] - rows[i]["lo"])
assert rows[NARROW]["n"] == max(d["n"] for d in rows)   # smalest == flest bo

o = []
a = o.append

a('<?xml version="1.0" encoding="UTF-8"?>')
a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
  'preserveAspectRatio="xMidYMid meet" role="img" '
  'aria-labelledby="fig3-tittel fig3-desc" font-family="%s">' % (W, H, FONT))
a('<title id="fig3-tittel">Figur 3 · Innstillingsandel per byggfag, med '
  'eksakte konfidensintervaller</title>')
a('<desc id="fig3-desc">Seks byggfag tegnet som vannrette 95 %-intervaller på '
  'en prosentakse som begynner på null. Innstillingsandelen spenner fra 66,3 '
  'prosent (rørleggerarbeid, 83 bo) til 77,5 prosent (snekkerarbeid, 178 bo). '
  'Intervallene overlapper gjennomgående, og alle seks inneholder nivået for '
  'utførende bygg på 71,2 prosent. To loddrette referanselinjer markerer '
  'kohortens samlede nivå 75,5 prosent og utførende bygg 71,2 prosent. '
  'Rekkefølgen mellom fagene er ikke statistisk etablert.</desc>')

a('<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (W, H, PAPIR))

# ---------------------------------------------------------------- rutenett
# Harstrek bare der verdiene faktisk leses av. Nullpunktet baeres av etiketten
# «0» i aksesporet; en loddrett strek der ville vaert en skillelinje uten data.
for p in (60, 80):
    a('<line x1="%.2f" y1="%.1f" x2="%.2f" y2="%.1f" stroke="%s" stroke-width="1"/>'
      % (x(p), GRID_TOP, x(p), GRID_BOT, HAIR))

# ---------------------------------------------------------------- referanselinjer
for p, _lab, _anc in REF_LINES:
    a('<line x1="%.2f" y1="%.1f" x2="%.2f" y2="%.1f" stroke="%s" stroke-width="1" '
      'stroke-dasharray="6 5" opacity="0.9"/>' % (x(p), REF_TOP, x(p), GRID_BOT, AKSENT))

# ---------------------------------------------------------------- intervaller
for i, d in enumerate(rows):
    y = Y_ROW0 + i * PITCH
    xl, xh, xp = x(d["lo"]), x(d["hi"]), x(d["pst"])
    a('<g>')
    a('  <line x1="%.2f" y1="%.1f" x2="%.2f" y2="%.1f" stroke="%s" stroke-width="3" '
      'stroke-linecap="butt"/>' % (xl, y, xh, y, BYGG))
    for xc in (xl, xh):
        a('  <line x1="%.2f" y1="%.1f" x2="%.2f" y2="%.1f" stroke="%s" '
          'stroke-width="2.5"/>' % (xc, y - 7, xc, y + 7, BYGG))
    a('  <circle cx="%.2f" cy="%.1f" r="3.6" fill="%s" stroke="%s" stroke-width="1.8"/>'
      % (xp, y, BYGG, PAPIR))
    a('</g>')

# ---------------------------------------------------------------- radetiketter
for i, d in enumerate(rows):
    y = Y_ROW0 + i * PITCH
    a(text(M_L, y - 4, d["navn"], 13, BYGG, weight="600"))
    a(text(M_L, y + 15, "%d bo%s%s%s%s%sKI %s–%s"
           % (d["n"], SEP, nb(d["pst"]), NBSP, "%", SEP, nb(d["lo"]), nb(d["hi"])),
           12.5, DEMPET))

# ---------------------------------------------------------------- verdiakse
a(text(M_L, 164, "Andel innstilt etter § 135", 12.5, DEMPET))
for p in (0, 20, 40, 60, 80, 100):
    lab = "100" + NBSP + "%" if p == 100 else str(p)
    anchor = "start" if p == 0 else ("end" if p == 100 else "middle")
    a(text(x(p), 164, lab, 12.5, DEMPET, anchor=anchor))

# ---------------------------------------------------------------- referanseetiketter
for p, lab, anchor in REF_LINES:
    a(text(x(p) - 8 if anchor == "end" else x(p) + 8, 190, lab, 12.5, AKSENT,
           anchor=anchor))

# ---------------------------------------------------------------- annotasjoner
ANN = [
    # (rad, linjer, y for vannrett foring, x for loddrett foring, y-slutt)
    # foringen lander paa strekens underside midt i spennet — aldri under en endehake,
    # ellers ser haken ut som en forlenget loddrett strek
    (0, ["Ytterpunktene: snekkerarbeid mot",
         "rørleggerarbeid gir p = 0,069 i eksakt test."], 243.0, 935.0, 225.0),
    (NARROW, ["Strekens bredde følger antall bo, ikke hvor",
              "sikker bransjen er: dette faget har flest bo."], 506.0, 880.0, 489.0),
]
for ridx, lines, y_lead, x_lead, y_end in ANN:
    yr = Y_ROW0 + ridx * PITCH
    for j, line in enumerate(lines):
        a(text(ANN_RIGHT, yr - 4 + j * 19, line, 12.5, BLEKK, anchor="end"))
    a('<polyline points="%.1f,%.1f %.2f,%.1f %.2f,%.1f" fill="none" stroke="%s" '
      'stroke-width="1"/>' % (ANN_RIGHT + 6, y_lead, x_lead, y_lead, x_lead, y_end, DEMPET))

# ---------------------------------------------------------------- noter
a(text(M_L, 628,
       '<tspan font-weight="600">Rekkefølgen mellom fagene er ikke statistisk '
       'etablert.</tspan> Alle seks intervallene inneholder nivået for '
       'utførende bygg på 71,2&#160;%.', 12.5, BLEKK, raw=True))
a(text(M_L, 662,
       "Ikke tegnet som fag: byggnæringer med under ti bo i én utfallskolonne "
       "(samlet i grunnlagets restkategori), samlekategorien", 12.5, DEMPET))
a(text(M_L, 680,
       "annen spesialisert bygge- og anleggsvirksomhet (43.990) og "
       "eiendomsutvikling (41.1). Alle tre ligger i figurgrunnlaget, utenfor "
       "fagoppstillingen.", 12.5, DEMPET))

# ---------------------------------------------------------------- tittelblokk
a(text(M_L, 44, "FIGUR 3", 11, DEMPET, ls="0.14em"))
a(text(M_L, 76, "Innstillingsandel per byggfag, med eksakte konfidensintervaller",
       21, BLEKK, weight="600"))
a(text(M_L, 105, "Seks byggfag med minst ti bo i begge utfallskolonner, sortert "
       "etter punktestimat. Streken er det eksakte", 14.5, DEMPET))
a(text(M_L, 127, "95" + NBSP + "%-intervallet (Clopper–Pearson), prikken er andelen. "
       "Bo åpnet 24.08.2023–31.12.2024; næring fra åpningskunngjøringen.", 14.5, DEMPET))

# ---------------------------------------------------------------- kildelinje
a(text(M_L, 734, "Byggsikt · offentlig tilgjengelige registerkunngjøringer · "
       "utfall observert til 24.08.2026", 11, DEMPET))

a('</svg>')

with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(o) + "\n")

print("skrevet:", OUT_PATH)
for i, d in enumerate(rows):
    print("  %-30s n=%-4d %5s%%  [%s-%s]  x %7.2f..%7.2f  pt %7.2f"
          % (d["navn"], d["n"], nb(d["pst"]), nb(d["lo"]), nb(d["hi"]),
             x(d["lo"]), x(d["hi"]), x(d["pst"])))
print("  ref 71,2 -> x=%.2f   ref 75,5 -> x=%.2f" % (x(71.2), x(75.5)))
print("  smalest strek: %s (n=%d, bredde %.1f pp)"
      % (rows[NARROW]["navn"], rows[NARROW]["n"], rows[NARROW]["hi"] - rows[NARROW]["lo"]))
