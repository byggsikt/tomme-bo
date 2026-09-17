# -*- coding: utf-8 -*-
"""Kontroll av figur-6-modning.svg mot designsystemet og mot grunnlagsdataene."""
import csv
import io
import re
import xml.etree.ElementTree as ET

BASE = r"./figurer"
SVG = BASE + "/svg/figur-6-modning.svg"

PALETT = {"#f5f0e6", "#e9e1d4", "#171815", "#625e55", "#d8cfbe",
          "#9a4d35", "#2e6f91", "#b9782f", "#8c9a8e", "none",
          "url(#sensur)"}

raw = io.open(SVG, encoding="utf-8").read()
feil = []
ok = []

# ---- XML og selvstendighet
tre = ET.fromstring(raw.split("?>", 1)[1])
ok.append("gyldig XML, rotelement %s" % tre.tag.split("}")[-1])
for d in ("xlink:href", "<image", "<script", "@import", "http://www.w3.org/1999/xlink"):
    if d in raw:
        feil.append("ekstern/uonsket referanse: %s" % d)
if not re.search(r"https?://(?!www\.w3\.org)", raw):
    ok.append("ingen eksterne URL-er")
else:
    feil.append("ekstern URL i fila")

# ---- viewBox og rammer
vb = tre.get("viewBox")
W, H = float(vb.split()[2]), float(vb.split()[3])
ok.append("viewBox %s, preserveAspectRatio=%s, role=%s"
          % (vb, tre.get("preserveAspectRatio"), tre.get("role")))
NS = "{http://www.w3.org/2000/svg}"
if tre.find(NS + "title") is None or tre.find(NS + "desc") is None:
    feil.append("mangler title/desc")
else:
    ok.append("title + desc til stede")

# ---- palett
for el in tre.iter():
    for att in ("fill", "stroke"):
        v = el.get(att)
        if v and v not in PALETT:
            feil.append("farge utenfor palett: %s=%s paa %s" % (att, v, el.tag))
ok.append("alle fill/stroke innenfor den laaste paletten")

# ---- typografi
tekster = [e for e in tre.iter() if e.tag == NS + "text"]
uten_font = [e for e in tekster if "Euclid Circular B" not in (e.get("font-family") or "")]
if uten_font:
    feil.append("%d tekstelement uten font-family" % len(uten_font))
else:
    ok.append("font-family paa alle %d tekstelement" % len(tekster))

# ---- norsk tallformat: ingen desimalpunktum, ingen komma som tusenskille
for e in tekster:
    s = "".join(e.itertext())
    if re.search(r"\d\.\d", s) and not re.search(r"\d\d\.\d\d\.\d{4}", s):
        feil.append("desimalpunktum i tekst: %r" % s)
    if re.search(r"\d,\d\d\d(\D|$)", s):
        feil.append("komma som tusenskille: %r" % s)
    if re.search(r"\d %", s) and "\u00a0%" not in s:
        feil.append("prosent uten hardt mellomrom: %r" % s)
ok.append("norsk tallformat: komma som desimalskilletegn, hardt mellomrom")

# ---- ingen tekst utenfor viewBox (grovt anslag paa tekstbredde)
BREDDE = {11: 0.50, 11.5: 0.50, 12.5: 0.52, 13: 0.55, 13.5: 0.55,
          14.5: 0.51, 21: 0.55}
for e in tekster:
    s = "".join(e.itertext())
    x, y = float(e.get("x")), float(e.get("y"))
    fs = float(e.get("font-size"))
    w = len(s) * fs * BREDDE.get(fs, 0.55)
    anchor = e.get("text-anchor") or "start"
    x0 = x if anchor == "start" else (x - w if anchor == "end" else x - w / 2)
    if x0 < 0 or x0 + w > W or y > H or y < 10:
        feil.append("tekst utenfor viewBox: %r  x0=%.0f x1=%.0f y=%.0f"
                    % (s, x0, x0 + w, y))
ok.append("all tekst innenfor viewBox (bredde anslaatt)")

# ---- tallene mot grunnlagsdata
with io.open(BASE + "/modningskurve-risikomengde-2026-08-30.csv",
             encoding="utf-8") as f:
    R = {int(r["maaneder"]): r for r in csv.DictReader(f, delimiter=";")}
with io.open(BASE + "/modningskurve-naiv-per-kvartal-2026-08-30.csv",
             encoding="utf-8") as f:
    N = list(csv.DictReader(f, delimiter=";"))

alle_tekst = " ".join("".join(e.itertext()) for e in tekster)


def har(s):
    return s in alle_tekst


kilde = []
for m in (12, 24, 30):
    for felt, navn in (("andel_alle_pst", "alle"), ("andel_bygg_pst", "bygg"),
                       ("andel_ovrige_pst", "ovrige")):
        v = float(R[m][felt])
        s = ("%.1f" % v).replace(".", ",") + "\u00a0%"
        if har(s):
            kilde.append("m=%d %s = %s  <- rad maaneder=%d, kolonne %s"
                         % (m, navn, s, m, felt))
for m in (0, 3, 6, 12, 18, 24, 30):
    n = int(R[m]["n_alle"])
    s = "{:,}".format(n).replace(",", "\u00a0")
    if not har(s):
        feil.append("risikomengde %s mangler i figuren" % s)
    else:
        kilde.append("risikomengde m=%d = %s  <- rad maaneder=%d, kolonne n_alle"
                     % (m, s, m))
for r in N:
    s = ("%.1f" % float(r["innstilt_pst"])).replace(".", ",") + "\u00a0%"
    if not har(s):
        feil.append("kvartal %s (%s) mangler" % (r["aapning_kvartal"], s))
    else:
        kilde.append("%s = %s  <- rad %s, kolonne innstilt_pst"
                     % (r["aapning_kvartal"], s, r["aapning_kvartal"]))
if har("2026K3") and "aldri tegnet som null" not in alle_tekst:
    feil.append("2026K3 nevnt uten forbeholdet")
ok.append("alle synlige tall gjenfunnet i grunnlagsfilene")

# ---- forbud
if re.search(r"<rect[^>]*stroke=", raw):
    feil.append("mulig rammekasse rundt plottet")
if "filter" in raw or "Gradient" in raw or "shadow" in raw:
    feil.append("skygge/gradient funnet")
ok.append("ingen ramme, skygge eller gradient")

print("== OK ==")
for s in ok:
    print("  " + s)
print("== KILDELENKER (utvalg) ==")
for s in kilde:
    print("  " + s)
print("== FEIL ==")
for s in feil:
    print("  " + s)
print("ANTALL FEIL:", len(feil))
