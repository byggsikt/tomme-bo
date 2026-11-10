# -*- coding: utf-8 -*-
"""Maaler hver <text> i figur-3-byggfag.svg med de faktiske fallback-fontene
(Segoe UI og Arial) og rapporterer overflyt og kollisjoner."""
import os, re, xml.etree.ElementTree as ET
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SVG = os.path.join(os.path.dirname(HERE), "figur-3-byggfag.svg")

FONTS = {
    "SegoeUI": {400: "C:/Windows/Fonts/segoeui.ttf", 600: "C:/Windows/Fonts/segoeuisb.ttf"},
    "Arial":   {400: "C:/Windows/Fonts/arial.ttf",   600: "C:/Windows/Fonts/arialbd.ttf"},
}
CACHE = {}


def font(fam, w, size):
    key = (fam, w, round(size * 4))
    if key not in CACHE:
        path = FONTS[fam][w]
        if not os.path.exists(path):
            path = FONTS[fam][400]
        CACHE[key] = ImageFont.truetype(path, int(round(size * 4)))
    return CACHE[key]


def width(fam, txt, size, w=400, ls=0.0):
    f = font(fam, w, size)
    adv = f.getlength(txt) / 4.0
    return adv + ls * size * len(txt)


NS = "{http://www.w3.org/2000/svg}"
tree = ET.parse(SVG)
root = tree.getroot()

vb = [float(v) for v in root.get("viewBox").split()]
print("viewBox:", vb)

items = []
for t in root.iter(NS + "text"):
    size = float(t.get("font-size", 12))
    weight = 600 if t.get("font-weight") == "600" else 400
    ls = float((t.get("letter-spacing") or "0em").replace("em", "")) if t.get("letter-spacing") else 0.0
    anchor = t.get("text-anchor", "start")
    tx, ty = float(t.get("x")), float(t.get("y"))
    parts = []
    if t.text:
        parts.append((t.text, weight))
    for sp in t:
        sw = 600 if sp.get("font-weight") == "600" else weight
        if sp.text:
            parts.append((sp.text, sw))
        if sp.tail:
            parts.append((sp.tail, weight))
    full = "".join(p[0] for p in parts)
    items.append(dict(x=tx, y=ty, size=size, anchor=anchor, ls=ls,
                      parts=parts, text=full))

print("\n%d tekstelementer\n" % len(items))

problems = []
for fam in ("SegoeUI", "Arial"):
    print("=== %s ===" % fam)
    boxes = []
    for it in items:
        w = sum(width(fam, s, it["size"], wt, it["ls"]) for s, wt in it["parts"])
        if it["anchor"] == "end":
            x0 = it["x"] - w
        elif it["anchor"] == "middle":
            x0 = it["x"] - w / 2.0
        else:
            x0 = it["x"]
        x1 = x0 + w
        y0 = it["y"] - it["size"] * 0.78
        y1 = it["y"] + it["size"] * 0.24
        boxes.append((x0, y0, x1, y1, it["text"]))
        if x1 > 1144.5:
            problems.append("%s OVERFLYT HOYRE x1=%.1f (>1144): %r" % (fam, x1, it["text"][:60]))
        if x0 < 75.5:
            problems.append("%s OVERFLYT VENSTRE x0=%.1f (<76): %r" % (fam, x0, it["text"][:60]))
        if x1 > vb[2] or x0 < 0 or y1 > vb[3] or y0 < 0:
            problems.append("%s UTENFOR VIEWBOX: %r" % (fam, it["text"][:60]))
    # parvise kollisjoner
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            if ox > 0.5 and oy > 0.5:
                problems.append("%s TEKSTKOLLISJON (%.1f x %.1f): %r  <->  %r"
                                % (fam, ox, oy, a[4][:42], b[4][:42]))
    for bx in sorted(boxes, key=lambda b: (b[1], b[0])):
        print("  x %7.1f..%7.1f  y %6.1f..%6.1f  %s" % (bx[0], bx[2], bx[1], bx[3], bx[4][:78]))
    print()

# ---- tekst vs. datastreker / rutenett -------------------------------------
BARS = [(908.43, 1010.54, 220), (874.66, 1011.34, 286), (839.28, 1020.99, 352),
        (811.14, 1003.30, 418), (865.01, 925.31, 484), (783.00, 953.45, 550)]
GRID = [822.4, 983.2]
REFS = [912.4, 947.0]
KNOCKS = []

print("=== tekst mot bjelker/rutenett (Segoe UI) ===")
for it in items:
    w = sum(width("SegoeUI", s, it["size"], wt, it["ls"]) for s, wt in it["parts"])
    x0 = it["x"] - w if it["anchor"] == "end" else (it["x"] - w / 2 if it["anchor"] == "middle" else it["x"])
    x1, y0, y1 = x0 + w, it["y"] - it["size"] * 0.78, it["y"] + it["size"] * 0.24
    for bl, br, by in BARS:
        if x0 < br + 8 and x1 > bl - 8 and y0 < by + 9 and y1 > by - 9:
            problems.append("TEKST OVER BJELKE y=%d: %r" % (by, it["text"][:50]))
    inside_knock = any(x0 >= k[0] - 1 and x1 <= k[2] + 1
                       and y0 >= k[1] - 1 and y1 <= k[3] + 1 for k in KNOCKS)
    for gx in GRID:
        if x0 - 1 < gx < x1 + 1 and 206 <= y1 and y0 <= 580 and not inside_knock:
            problems.append("TEKST KRYSSER RUTENETT x=%.1f: %r" % (gx, it["text"][:50]))
    for rx in REFS:
        if x0 - 1 < rx < x1 + 1 and 178 <= y1 and y0 <= 580 and not inside_knock:
            problems.append("TEKST KRYSSER REFERANSELINJE x=%.1f: %r" % (rx, it["text"][:50]))

print()
if problems:
    print("!!! %d FUNN" % len(problems))
    for p in problems:
        print("  -", p)
else:
    print("INGEN FUNN — ingen overflyt, ingen kollisjon.")
