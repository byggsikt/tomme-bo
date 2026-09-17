# -*- coding: utf-8 -*-
"""Genererer figur-5-rettskretser.svg.

Leser domstol-punktdiagram.tsv og skriver en handskrevet SVG (ingen bibliotek).
Layout: 0-basert andelsakse (0-90 %), sensureringsbevisst median dager vannrett,
flate = antall saker. Etikettene plasseres i en fire-trinns skinne under skyen,
med loddrette harstreker som klippes bak etikettbokser de passerer.
"""
import csv
import math
import random
import io

SRC = r"./domstol-punktdiagram.tsv"
OUT = r"./figur-5-rettskretser.svg"

PAPIR = "#f5f0e6"
BLEKK = "#171815"
DEMPET = "#625e55"
HAAR = "#d8cfbe"
MESSING = "#b9782f"
FONT = "Euclid Circular B, Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif"

W, H = 1200, 818

# ---------------------------------------------------------------- data
rows = []
with io.open(SRC, encoding="utf-8") as fh:
    for line in fh:
        if line.startswith("#") or not line.strip():
            continue
        rows.append(line.rstrip("\n").split("\t"))
head, body = rows[0], rows[1:]
idx = {k: i for i, k in enumerate(head)}

PEN = {  # skrivemate: fullt navn, normal kasus
    "HORDALAND TINGRETT": "Hordaland tingrett",
    "SØR-ROGALAND TINGRETT": "Sør-Rogaland tingrett",
    "TELEMARK TINGRETT": "Telemark tingrett",
    "RINGERIKE, ASKER OG BÆRUM TINGRETT": "Ringerike, Asker og Bærum tingrett",
    "SØNDRE ØSTFOLD TINGRETT": "Søndre Østfold tingrett",
    "AGDER TINGRETT": "Agder tingrett",
    "VESTFOLD TINGRETT": "Vestfold tingrett",
    "ØSTRE INNLANDET TINGRETT": "Østre Innlandet tingrett",
    "VESTRE INNLANDET TINGRETT": "Vestre Innlandet tingrett",
    "ROMERIKE OG GLÅMDAL TINGRETT": "Romerike og Glåmdal tingrett",
    "OSLO TINGRETT": "Oslo tingrett",
    "FOLLO OG NORDRE ØSTFOLD TINGRETT": "Follo og Nordre Østfold tingrett",
    "NORD-TROMS OG SENJA TINGRETT": "Nord-Troms og Senja tingrett",
    "BUSKERUD TINGRETT": "Buskerud tingrett",
    "TRØNDELAG TINGRETT": "Trøndelag tingrett",
    "MØRE OG ROMSDAL TINGRETT": "Møre og Romsdal tingrett",
}

P = []
for r in body:
    P.append(dict(
        navn=PEN[r[idx["rettskrets"]]],
        n=int(r[idx["saker"]]),
        p=float(r[idx["andel_innstilt"]]) * 100.0,
        lo=float(r[idx["cp95_lav"]]) * 100.0,
        hi=float(r[idx["cp95_hoy"]]) * 100.0,
        d=float(r[idx["km_median_dager"]]),
    ))
assert len(P) == 16

# ---------------------------------------------------------------- skala
GX0, GX1 = 76.0, 1104.0         # harstrekenes utstrekning
DX0, DX1 = 116.0, 1030.0        # dataomrade vannrett
DAG0, DAG1 = 100.0, 320.0
YBASE = 664.0                    # 0 %
PPP = 5.475                      # px per prosentpoeng (samme skala som figur 4)
PTOP = YBASE - 90.0 * PPP        # 90 % = toppen av aksen

def fx(d):
    return DX0 + (d - DAG0) * (DX1 - DX0) / (DAG1 - DAG0)

def fy(p):
    return YBASE - p * PPP

RMAX = 15.0
K = RMAX / math.sqrt(max(q["n"] for q in P))
for q in P:
    q["x"] = fx(q["d"])
    q["y"] = fy(q["p"])
    q["r"] = K * math.sqrt(q["n"])
    q["ytop"] = fy(q["hi"])
    q["ybot"] = fy(q["lo"])
    q["capx0"] = q["x"] - max(q["r"], 5.0)
    q["capx1"] = q["x"] + max(q["r"], 5.0)
    q["bot"] = max(q["ybot"], q["y"] + q["r"])
    q["top"] = min(q["ytop"], q["y"] - q["r"])

# ---------------------------------------------------------------- tekstbredde
EM = {
    " ": .26, ".": .27, ",": .27, ":": .28, ";": .28, "-": .33, "\u2013": .55,
    "\u2014": .90, "\u00b7": .33, "%": .85, "\u00a7": .55, "(": .33, ")": .33,
    "/": .40, "\u00a0": .26,
    "a": .55, "b": .57, "c": .51, "d": .57, "e": .55, "f": .33, "g": .57,
    "h": .56, "i": .25, "j": .25, "k": .53, "l": .25, "m": .86, "n": .56,
    "o": .57, "p": .57, "q": .57, "r": .36, "s": .49, "t": .35, "u": .56,
    "v": .50, "w": .75, "x": .50, "y": .50, "z": .47,
    "\u00e6": .85, "\u00f8": .57, "\u00e5": .55,
    "A": .66, "B": .64, "C": .68, "D": .70, "E": .58, "F": .55, "G": .72,
    "H": .70, "I": .27, "J": .47, "K": .63, "L": .54, "M": .86, "N": .70,
    "O": .75, "P": .62, "Q": .75, "R": .63, "S": .61, "T": .60, "U": .69,
    "V": .65, "W": .95, "X": .62, "Y": .61, "Z": .58,
    "\u00c6": .95, "\u00d8": .77, "\u00c5": .66,
}
for c in "0123456789":
    EM[c] = .58

def tw(s, size, weight=400):
    e = sum(EM.get(c, .58) for c in s)
    return e * size * (1.03 if weight >= 600 else 1.0)

# ---------------------------------------------------------------- etikettskinne
LSIZE = 12.5
TIERS = [178.0, 358.0, 382.0, 406.0, 430.0]   # 0 = over skyen, 1-4 = skinne under
NT = len(TIERS)
ASC, DESC = 9.5, 3.5
GAP, INSET = 18.0, 16.0


def above(t):
    return t == 0

for q in P:
    q["w"] = tw(q["navn"], LSIZE) * 1.03 + 2.0

def solve_tier(members):
    """members: liste av punkt sortert etter x. Returnerer venstrekant eller None."""
    if not members:
        return {}
    n = len(members)
    minL = [0.0] * n
    prev = GX0 - GAP
    for i, q in enumerate(members):
        ins = min(INSET, q["w"] / 2.0 - 2.0)
        lo = max(q["ax"] - q["w"] + ins, GX0, prev + GAP)
        minL[i] = lo
        prev = lo + q["w"]
    maxL = [0.0] * n
    nxt = GX1 + GAP
    for i in range(n - 1, -1, -1):
        q = members[i]
        ins = min(INSET, q["w"] / 2.0 - 2.0)
        hi = min(q["ax"] - ins, GX1 - q["w"], nxt - GAP - q["w"])
        maxL[i] = hi
        nxt = hi
    out = {}
    prev = GX0 - GAP
    for i, q in enumerate(members):
        if minL[i] > maxL[i] + 1e-9:
            return None
        ins = min(INSET, q["w"] / 2.0 - 2.0)
        lo = max(q["ax"] - q["w"] + ins, GX0, prev + GAP)
        if lo > maxL[i] + 1e-9:
            return None
        c = q["ax"] - q["w"] / 2.0
        L = min(max(c, lo), maxL[i])
        out[q["navn"]] = L
        prev = L + q["w"]
    return out


TAK = TIERS[0] + DESC + 8.0          # etikett over skyen krever klaring hit

# --- pekerkorridor -------------------------------------------------------
# En peker er en loddrett harstrek. Den skal aldri ga gjennom en annen
# markor. Vi soker det minste sidesteget som gir fri bane, og starter
# pekeren rett under (eller over) punktets egen markor i den korridoren.
KLAR = 2.0
BUNN_RAIL = TIERS[-1] - ASC - 4.0
TOPP_RAIL = TIERS[0] + DESC + 4.0


def blokkert(px, y0, y1, egen):
    for o in P:
        if o is egen:
            continue
        if o["x"] - o["r"] - KLAR <= px <= o["x"] + o["r"] + KLAR:
            if not (y1 < o["y"] - o["r"] - KLAR or y0 > o["y"] + o["r"] + KLAR):
                return True
        if o["x"] - 4.0 - KLAR <= px <= o["x"] + 4.0 + KLAR:
            if not (y1 < o["ytop"] - KLAR or y0 > o["ybot"] + KLAR):
                return True
    return False


def egen_bunn(q, px):
    b = -1e9
    dx = abs(px - q["x"])
    if dx <= 4.0:
        b = max(b, q["ybot"])
    if dx < q["r"]:
        b = max(b, q["y"] + math.sqrt(q["r"] ** 2 - dx ** 2))
    return b


def egen_topp(q, px):
    t = 1e9
    dx = abs(px - q["x"])
    if dx <= 4.0:
        t = min(t, q["ytop"])
    if dx < q["r"]:
        t = min(t, q["y"] - math.sqrt(q["r"] ** 2 - dx ** 2))
    return t


SIDESTEG = [0.0, 5.0, -5.0, 9.0, -9.0, 13.0, -13.0]
MAKS_PEKER_OPP = 45.0
for q in P:
    q["pxd"], q["startd"] = q["x"], egen_bunn(q, q["x"]) + 4.0
    for s in SIDESTEG:
        px = q["x"] + s
        st = egen_bunn(q, px) + 4.0
        if not blokkert(px, st, BUNN_RAIL, q):
            q["pxd"], q["startd"] = px, st
            break
    q["kan_over"] = False
    for s in SIDESTEG:
        px = q["x"] + s
        en = egen_topp(q, px) - 4.0
        if en - TOPP_RAIL > MAKS_PEKER_OPP:
            continue
        if not blokkert(px, TOPP_RAIL, en, q):
            q["pxu"], q["startu"] = px, en
            q["kan_over"] = True
            break


def evaluate(assign):
    boxes = {}
    for q in P:
        if above(assign[q["navn"]]):
            if not q["kan_over"]:
                return None, None
            q["ax"] = q["pxu"]
        else:
            q["ax"] = q["pxd"]
    for t in range(NT):
        mem = sorted([q for q in P if assign[q["navn"]] == t], key=lambda z: z["ax"])
        sol = solve_tier(mem)
        if sol is None:
            return None, None
        for k, v in sol.items():
            boxes[k] = (v, t)
    cost = 0.0
    for q in P:
        t = assign[q["navn"]]
        L, _ = boxes[q["navn"]]
        if above(t):
            cost += 0.85 * (q["startu"] - TOPP_RAIL)
            cost += 0.90 * abs(L + q["w"] / 2.0 - q["ax"])   # kort peker: ma sentreres
        else:
            dl = TIERS[t] - ASC - q["startd"]
            cost += 0.85 * dl + 0.016 * dl * dl              # kort peker er best
            cost += 0.30 * abs(L + q["w"] / 2.0 - q["ax"])   # helst sentrert
        for o in P:
            if o is q:
                continue
            ot = assign[o["navn"]]
            if above(t) or above(ot) or ot >= t:
                continue
            oL, _ = boxes[o["navn"]]
            if oL - 7 <= q["ax"] <= oL + o["w"] + 7:
                cost += 220.0                                # peker krysser etikett
    return cost, boxes


order = sorted(range(16), key=lambda i: P[i]["x"])
start = {P[order[i]]["navn"]: 1 + i % 4 for i in range(16)}
best = (None, None, None)
ITER = 260000
for frø in (11, 23, 37, 51, 73, 97, 131):
    random.seed(frø)
    cand = dict(start)
    cur, bx0 = evaluate(cand)
    if cur is None:
        continue
    if best[0] is None or cur < best[0]:
        best = (cur, dict(cand), bx0)
    for it in range(ITER):
        temp = 70.0 * (0.02 / 70.0) ** (it / float(ITER - 1))
        trial = dict(cand)
        q = random.choice(P)
        trial[q["navn"]] = random.randrange(NT)
        if random.random() < 0.30:
            a, b = random.sample(P, 2)
            trial[a["navn"]], trial[b["navn"]] = trial[b["navn"]], trial[a["navn"]]
        c, bx = evaluate(trial)
        if c is None:
            continue
        if c < cur or random.random() < math.exp(-(c - cur) / temp):
            cand, cur = trial, c
            if c < best[0]:
                best = (c, dict(trial), bx)
    # grådig etterpuss: flytt ett og ett merke til beste lag
    cand = dict(best[1])
    cur = best[0]
    endret = True
    while endret:
        endret = False
        for q in P:
            for t in range(NT):
                if cand[q["navn"]] == t:
                    continue
                trial = dict(cand)
                trial[q["navn"]] = t
                c, bx = evaluate(trial)
                if c is not None and c < cur - 1e-9:
                    cand, cur, endret = trial, c, True
                    best = (c, dict(trial), bx)
cost, assign, boxes = best
assert assign is not None, "fant ingen gyldig etikettplassering"

for q in P:
    L, t = boxes[q["navn"]]
    q["lx"], q["tier"] = L, t
    q["ly"] = TIERS[t]

for q in P:
    if above(q["tier"]):
        q["px"] = q["pxu"]
        q["pstart"] = q["ly"] + DESC + 4.0
        q["pend"] = q["startu"]
    else:
        q["px"] = q["pxd"]
        q["pstart"] = q["startd"]
        q["pend"] = q["ly"] - ASC - 4.0
    assert not blokkert(q["px"], min(q["pstart"], q["pend"]),
                        max(q["pstart"], q["pend"]), q), \
        "peker gjennom annen markor: " + q["navn"]

# ---------------------------------------------------------------- svg
SVGBUF = []
A = SVGBUF.append


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace("\u00a0", "&#160;"))


TEKSTBOKS = []


def T(x, y, s, size=12.5, fill=DEMPET, weight=None, anchor=None, ls=None, extra=""):
    wpx = tw(s, size, weight or 400)
    if ls:
        wpx += 0.14 * size * max(len(s) - 1, 0)
    if anchor == "end":
        TEKSTBOKS.append((x - wpx, x, y, s))
    elif anchor == "middle":
        TEKSTBOKS.append((x - wpx / 2.0, x + wpx / 2.0, y, s))
    else:
        TEKSTBOKS.append((x, x + wpx, y, s))
    st = "font-variant-numeric:tabular-nums"
    a = ['<text x="%s" y="%s"' % (fmt(x), fmt(y)),
         'font-family="%s"' % FONT, 'font-size="%s"' % fmt(size), 'fill="%s"' % fill]
    if weight:
        a.append('font-weight="%d"' % weight)
    if anchor:
        a.append('text-anchor="%s"' % anchor)
    if ls:
        a.append('letter-spacing="%s"' % ls)
        st = "letter-spacing:%s;%s" % (ls, st)
    if extra:
        a.append(extra)
    a.append('font-variant-numeric="tabular-nums" style="%s"' % st)
    A(" ".join(a) + ">" + esc(s) + "</text>")


def fmt(v):
    if isinstance(v, str):
        return v
    s = "%.2f" % v
    s = s.rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


A('<?xml version="1.0" encoding="UTF-8"?>')
A('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
  'preserveAspectRatio="xMidYMid meet" role="img" '
  'aria-labelledby="fig5-tittel fig5-desc" width="%d" height="%d">' % (W, H, W, H))
A('  <title id="fig5-tittel">Rettskretsene: andel tomme bo mot tid</title>')

desc = (
    "Punktdiagram over de 16 norske rettskretsene med minst 100 konkurssaker i kohorten. "
    "Vannrett akse: sensureringsbevisst median antall dager fra konkurs\u00e5pning til innstilling, "
    "fra 127 dager til 309 dager. Loddrett akse: andel bo innstilt etter konkursloven \u00a7 135, "
    "med nullpunkt og eksakte Clopper\u2013Pearson-intervaller tegnet som loddrette usikkerhetsstreker. "
    "Andelene ligger mellom 66,8 og 82,0 prosent, og 14 av de 16 intervallene dekker kohortens "
    "samlede niv\u00e5 p\u00e5 75,5 prosent, som er tegnet som vannrett referanselinje i messing. "
    "Flatestørrelsen viser antall saker, fra 106 til 911. Alle kretsene er merket direkte med fullt "
    "navn. Figuren er deskriptiv og ikke en rangering: av 120 parvise sammenlikninger overlever tre "
    "Holm-korreksjonen, alle med den samme kretsen i den lave enden, og ingen krets i den h\u00f8ye "
    "enden skiller seg. Hva som forklarer variasjonen er ikke kjent; saksmiksen \u2014 oppbud mot "
    "kreditorbegj\u00e6ring \u2014 er ikke observerbar i materialet, og retningen p\u00e5 den effekten "
    "er ukjent. Sju rettskretser med under 100 saker er ikke vist."
)
A('  <desc id="fig5-desc">%s</desc>' % esc(desc))
A('  <g font-family="%s" font-variant-numeric="tabular-nums" '
  'style="font-variant-numeric:tabular-nums">' % FONT)
A('<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (W, H, PAPIR))

# tittelblokk
T(76, 46, "FIGUR 5", 11, DEMPET, weight=500, ls="0.14em")
T(76, 78, "Rettskretsene: andel tomme bo mot tid", 21, BLEKK, weight=600)
T(76, 106, "Seksten rettskretser med minst 100 saker. Vannrett: sensureringsbevisst median antall "
           "dager fra \u00e5pning til innstilling \u2014", 14.5, DEMPET)
T(76, 126, "ikke medianen blant fullf\u00f8rte saker. Loddrett: andel innstilt etter \u00a7\u00a0135, "
           "med Clopper\u2013Pearson-intervall. Flate: antall saker, fra 106 til 911.",
  14.5, DEMPET)

# harstreker + akseverdier
for pct in (0, 20, 40, 60, 80):
    y = fy(pct)
    A('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1"/>'
      % (fmt(GX0), fmt(y), fmt(GX1), fmt(y), HAAR))
    lab = "80\u00a0%" if pct == 80 else str(pct)
    T(GX1 + 10, y + 4.3, lab, 12.5, DEMPET)

# referanselinje 75,5 %
yref = fy(75.5)
A('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.5" '
  'stroke-dasharray="7 4"/>' % (fmt(GX0), fmt(yref), fmt(GX1), fmt(yref), MESSING))
T(76, yref + 17, "Kohorten samlet 75,5\u00a0%", 12.5, MESSING, weight=600)

# usikkerhetsstrek (Clopper-Pearson) + bobler
for q in sorted(P, key=lambda z: -z["n"]):
    A('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1" '
      'stroke-opacity="0.42"/>'
      % (fmt(q["x"]), fmt(q["ytop"]), fmt(q["x"]), fmt(q["ybot"]), BLEKK))
    for yy in (q["ytop"], q["ybot"]):
        A('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1" '
          'stroke-opacity="0.42"/>' % (fmt(q["x"] - 4), fmt(yy), fmt(q["x"] + 4),
                                       fmt(yy), BLEKK))
for q in sorted(P, key=lambda z: -z["n"]):
    A('<circle cx="%s" cy="%s" r="%s" fill="%s"/>'
      % (fmt(q["x"]), fmt(q["y"]), fmt(q["r"] + 0.85), PAPIR))
    A('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.13" stroke="%s" '
      'stroke-opacity="0.9" stroke-width="1.7"/>'
      % (fmt(q["x"]), fmt(q["y"]), fmt(q["r"]), BLEKK, BLEKK))

# pekere med klipp bak etikettbokser
for q in P:
    segs = [(q["pstart"], q["pend"])] if not above(q["tier"]) \
        else [(q["pend"], q["pstart"])]
    if not above(q["tier"]):
        for o in P:
            if o is q or above(o["tier"]) or o["tier"] >= q["tier"]:
                continue
            if not (o["lx"] - 7 <= q["px"] <= o["lx"] + o["w"] + 7):
                continue
            bt, bb = o["ly"] - ASC - 4.0, o["ly"] + DESC + 4.0
            ns = []
            for (a, b) in segs:
                if bb <= a or bt >= b:
                    ns.append((a, b))
                    continue
                if a < bt:
                    ns.append((a, bt))
                if bb < b:
                    ns.append((bb, b))
            segs = ns
    for (a, b) in segs:
        if b - a < 3:
            continue
        A('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1" '
          'stroke-dasharray="1.5 3"/>'
          % (fmt(q["px"]), fmt(a), fmt(q["px"]), fmt(b), HAAR))

# etiketter
for q in P:
    T(q["lx"], q["ly"], q["navn"], LSIZE, DEMPET, weight=500)

# x-akse
for dag in (100, 150, 200, 250, 300):
    x = fx(dag)
    A('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1"/>'
      % (fmt(x), fmt(YBASE), fmt(x), fmt(YBASE + 6), HAAR))
    T(x, 690, str(dag), 12.5, DEMPET, anchor="middle")
T(76, 716, "Sensureringsbevisst median dager fra \u00e5pning til innstilling", 12.5, DEMPET)

# paskrifter
NOTES = [
    (76.0, 508.0, "Posisjon er ikke en rangering.", [
        "Av 120 parvise sammenlikninger",
        "mellom de 16 kretsene overlever tre Holm-korreksjonen, alle med den samme",
        "kretsen i den lave enden; ingen krets i den h\u00f8ye enden skiller seg. En hierarkisk",
        "modell krymper spennet fra 66,8\u201382,0\u00a0% til 69,5\u201378,9\u00a0%.",
    ]),
    (616.0, 488.0, "Hva som forklarer variasjonen, er ikke kjent.", [
        "Saksmiksen \u2014 oppbud mot",
        "kreditorbegj\u00e6ring \u2014 er den n\u00e6rmeste uobserverte forklaringen, og den er ikke",
        "observerbar i materialet. Retningen p\u00e5 effekten er ikke kjent: de eneste",
        "historiske tallene som er funnet, peker motsatt vei av den intuitive gjetningen.",
    ]),
]
NY = [470.0, 494.0, 518.0, 542.0]
for x0, wmax, lead, lines in NOTES:
    lw = tw(lead, LSIZE, 600)
    assert lw + 6 + tw(lines[0], LSIZE) <= wmax, "notatlinje 1 for bred"
    T(x0, NY[0], lead, LSIZE, BLEKK, weight=600)
    T(x0 + lw + 6, NY[0], lines[0], LSIZE, DEMPET)
    for i in range(1, 4):
        assert tw(lines[i], LSIZE) <= wmax, "notatlinje for bred: " + lines[i]
        T(x0, NY[i], lines[i], LSIZE, DEMPET)

# fotnoter og kilde
T(76, 748, "Sju rettskretser med under 100 saker ligger under publiseringsgrensen og er ikke vist. "
            "Byggandelen per krets i grunnlaget spenner fra 15,7 til 34,8\u00a0%.", 11, DEMPET)
T(76, 764, "Feltet spenner fra 66,8 til 82,0\u00a0% og fra 127 til 309 dager. Medianen blant "
            "fullf\u00f8rte saker (97\u2013213 dager) h\u00f8rer hjemme i grunnlagsfila, ikke p\u00e5 aksen.", 11, DEMPET)
T(76, 790, "Byggsikt \u00b7 offentlig tilgjengelige registerkunngj\u00f8ringer \u00b7 utfall "
            "observert til 24.08.2026", 11, DEMPET)

A('  </g>')
A('</svg>')

with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(SVGBUF) + "\n")

# --------------------------------------------------------------- kontroll
print("kostnad %.1f" % cost)
kryss = 0
for q in P:
    for oo in P:
        if oo is q or above(q["tier"]) or above(oo["tier"]) or oo["tier"] >= q["tier"]:
            continue
        if oo["lx"] - 7 <= q["px"] <= oo["lx"] + oo["w"] + 7:
            kryss += 1
print("pekerkryss:", kryss)
for t in range(NT):
    mem = sorted([q for q in P if q["tier"] == t], key=lambda z: z["lx"])
    print("tier", t, [(q["navn"], round(q["lx"]), round(q["lx"] + q["w"])) for q in mem])
    for i in range(len(mem) - 1):
        assert mem[i]["lx"] + mem[i]["w"] + 2 <= mem[i + 1]["lx"], "etikettkollisjon"
    for q in mem:
        assert q["lx"] >= GX0 - 0.01 and q["lx"] + q["w"] <= GX1 + 0.01, "utenfor felt"
        assert q["lx"] <= q["px"] <= q["lx"] + q["w"], "peker utenfor etikett"
for (a, b, y, s) in TEKSTBOKS:
    assert a >= 26.0, "tekst utenfor venstre kant: " + s
    assert b <= 1152.0, "tekst utenfor hoyre kant (%.0f): %s" % (b, s)
    assert 20.0 <= y <= H - 14.0, "tekst utenfor loddrett: " + s
for i in range(len(TEKSTBOKS)):
    for j in range(i + 1, len(TEKSTBOKS)):
        a1, b1, y1, s1 = TEKSTBOKS[i]
        a2, b2, y2, s2 = TEKSTBOKS[j]
        if abs(y1 - y2) < 13.0 and a1 < b2 + 4 and a2 < b1 + 4:
            raise AssertionError("tekstkollisjon: %r / %r" % (s1, s2))
print("bredeste tekst %.0f px (grense 1152)" % max(b for (a, b, y, s) in TEKSTBOKS))
print("lengste peker %.0f px"
      % max(abs(q["pend"] - q["pstart"]) for q in P))
print("laveste usikkerhetsbunn %.1f  (60%%-strek %.1f)"
      % (max(q["ybot"] for q in P), fy(60)))
print("hoyeste usikkerhetstopp %.1f  (aksetopp %.1f)"
      % (min(q["ytop"] for q in P), PTOP))
print("dager %.0f-%.0f  andel %.4f-%.4f"
      % (min(q["d"] for q in P), max(q["d"] for q in P),
         min(q["p"] for q in P), max(q["p"] for q in P)))
# bobleoverlapp
for i in range(16):
    for j in range(i + 1, 16):
        a, b = P[i], P[j]
        dd = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
        if dd < a["r"] + b["r"]:
            print("boble-overlapp: %s / %s (%.1f < %.1f)"
                  % (a["navn"], b["navn"], dd, a["r"] + b["r"]))
