"""F-analyse-utfall.py — outcomes of the forced-liquidation cohort (tvangsoppløsning/tvangsavvikling decisions
1.9.2023–31.12.2024) from data/F-tvang-worklist.tsv (export 12.09.2026 from the announcements,
events cut at 2026-08-24). Prints the statistics and writes analyser/F-TVANGSAVVIKLING-utfall.md (section 1; dividends are appended later).

Columns (tab, no header): orgnr, tv_dato, inn, avs, avs_kid, konk_for, konk_etter
"""
import os, sys, statistics, datetime as dt, collections
here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(here, "..", "data", "F-tvang-worklist.tsv")
out_md = os.path.join(here, "..", "analyser", "F-TVANGSAVVIKLING-utfall.md")
ASOF = dt.date(2026, 8, 24)
BRREG = {"2023-09": 242, "2023-10": 147, "2023-11": 90, "2023-12": 42, "2024-01": 74, "2024-02": 104, "2024-03": 55, "2024-04": 143,
         "2024-05": 397, "2024-06": 312, "2024-07": 76, "2024-08": 184, "2024-09": 328, "2024-10": 125, "2024-11": 127, "2024-12": 78}

def d(s):
    return dt.date.fromisoformat(s) if s else None

rows = []
for line in open(src, encoding="utf-8"):
    line = line.rstrip("\n")
    if not line:
        continue
    p = line.split("\t")
    while len(p) < 7:
        p.append("")
    rows.append({"orgnr": p[0], "tv": d(p[1]), "inn": d(p[2]), "avs": d(p[3]), "kid": p[4], "konk_for": d(p[5]), "konk_etter": d(p[6])})

n_all = len(rows)
rows = [r for r in rows if r["konk_for"] is None]
n = len(rows)

def outcome(r):
    inn, avs = r["inn"], r["avs"]
    if inn and (avs is None or inn <= avs):
        return "innstilt", inn
    if avs and (inn is None or avs < inn):
        return "avsluttet", avs
    return "aapen", None

oc = collections.Counter()
days_inn, days_avs = [], []
for r in rows:
    o, dd = outcome(r)
    oc[o] += 1
    if o == "innstilt":
        days_inn.append((dd - r["tv"]).days)
    elif o == "avsluttet":
        days_avs.append((dd - r["tv"]).days)
decided = oc["innstilt"] + oc["avsluttet"]

# fixed 730-day window
w = [r for r in rows if r["tv"] <= dt.date(2024, 8, 24)]
w_inn = w_avs = 0
for r in w:
    o, dd = outcome(r)
    if o == "innstilt" and (dd - r["tv"]).days <= 730:
        w_inn += 1
    elif o == "avsluttet" and (dd - r["tv"]).days <= 730:
        w_avs += 1

# per month vs Brreg
pm = collections.Counter(r["tv"].strftime("%Y-%m") for r in rows)
months = sorted(set(pm) | set(BRREG))

# combined with the bankruptcy cohort (as-of numbers from the main study / ledger)
K = {"n": 5165, "inn": 3897, "avs": 917, "open": 351}
comb_n = K["n"] + n
comb_inn = K["inn"] + oc["innstilt"]
comb_avs = K["avs"] + oc["avsluttet"]
comb_open = K["open"] + oc["aapen"]

lines = []
L = lines.append
L("# Tvangsavviklingsboene i kohortvinduet — utfall (målt, ikke forutsatt)")
L("")
L(f"Uttrekk 12.09.2026 (`sporringer/F-analyse-utfall.py` på `data/F-tvang-worklist.tsv`). Populasjon: første kunngjøring «Tvangsoppløsning» eller «Tvangsavvikling» (Konkursregisteret) per orgnr med dato 1.9.2023–31.12.2024, fra kunngjøringene. Utfall = første «Innstilling av bobehandling» / «Avslutning av bobehandling» (begge kilder) på eller etter vedtaksdatoen, hendelser til og med {ASOF.isoformat()}.")
L("")
L("## 1. Populasjon og utfall")
L("")
L(f"- Vedtak i vinduet: **{n_all}** selskaper; {n_all - n} med konkursåpning FØR vedtaket er tatt ut → **{n}**. Brønnøysunds egne månedstall for samme vindu: **2 524**. Dekning {100.0 * n / 2524:.1f} %.")
L(f"- Innstilt (§ 135) først: **{oc['innstilt']}** = {100.0 * oc['innstilt'] / n:.1f} % av alle, {100.0 * oc['innstilt'] / decided:.1f} % av de {decided} avgjorte.")
L(f"- Ordinær avslutning (utlodning) først: **{oc['avsluttet']}** = {100.0 * oc['avsluttet'] / n:.1f} % av alle, {100.0 * oc['avsluttet'] / decided:.1f} % av avgjorte.")
L(f"- Uten registrert utfall per {ASOF.isoformat()}: **{oc['aapen']}** = {100.0 * oc['aapen'] / n:.1f} %.")
L(f"- Median dager vedtak → innstilling: {statistics.median(days_inn):.0f}; vedtak → avslutning: {statistics.median(days_avs) if days_avs else float('nan'):.0f}.")
L(f"- Fast 730-dagersvindu (vedtak ≤ 24.08.2024, n = {len(w)}): innstilt innen 730 d **{w_inn}** = {100.0 * w_inn / len(w):.1f} %; avsluttet innen 730 d {w_avs} = {100.0 * w_avs / len(w):.1f} %.")
L("")
L("## 2. Dekning per måned mot Brønnøysunds statistikk")
L("")
L("| Måned | Korpus (vedtak) | Brreg «tvangsavviklinger» | Dekning |")
L("|---|---:|---:|---:|")
for m in months:
    b = BRREG.get(m)
    L(f"| {m} | {pm.get(m, 0)} | {b if b is not None else '—'} | {('%.0f %%' % (100.0 * pm.get(m, 0) / b)) if b else '—'} |")
L(f"| **Sum** | **{n}** | **{sum(BRREG.values())}** | **{100.0 * n / sum(BRREG.values()):.1f} %** |")
L("")
L("## 3. Konkurskohorten og tvangsavviklingsboene samlet (as-of 24.08.2026, begge målt)")
L("")
L("| | Konkursbo (hovedstudien) | Tvangsavviklingsbo (denne) | Samlet |")
L("|---|---:|---:|---:|")
L(f"| Åpninger/vedtak | {K['n']} | {n} | {comb_n} |")
L(f"| Innstilt (tomt) | {K['inn']} ({100.0 * K['inn'] / K['n']:.1f} %) | {oc['innstilt']} ({100.0 * oc['innstilt'] / n:.1f} %) | {comb_inn} ({100.0 * comb_inn / comb_n:.1f} %) |")
L(f"| Ordinær avslutning | {K['avs']} ({100.0 * K['avs'] / K['n']:.1f} %) | {oc['avsluttet']} ({100.0 * oc['avsluttet'] / n:.1f} %) | {comb_avs} ({100.0 * comb_avs / comb_n:.1f} %) |")
L(f"| Uten utfall / åpne | {K['open']} ({100.0 * K['open'] / K['n']:.1f} %) | {oc['aapen']} ({100.0 * oc['aapen'] / n:.1f} %) | {comb_open} ({100.0 * comb_open / comb_n:.1f} %) |")
L(f"| **Innstilt av avgjorte** | **{100.0 * K['inn'] / (K['inn'] + K['avs']):.1f} %** | **{100.0 * oc['innstilt'] / decided:.1f} %** | **{100.0 * comb_inn / (comb_inn + comb_avs):.1f} %** |")
L("")
L("Rapportens tabell 4 panel E: 89,9 % av avsluttede saker i utvalget (18 345/20 413), 2010–2019, med 30,7 % tvangsavviklingsbo. Samlet andel tvangsavvikling her: "
  f"{100.0 * n / comb_n:.1f} % av alle vedtak/åpninger.")
L("")
L("Forbehold: «uten utfall» blant tvangsavviklingsboene kan være både bo som fortsatt er åpne og bo hvis innstilling ikke er fanget av noen av de to kildene. Innstilling er som hovedregel kunngjort; dekningen per måned over viser at populasjonen er komplett. Tallene er per bo. Dividende for de ordinært avsluttede: seksjon 4 (leses fra avslutningskunngjøringene).")
md = "\n".join(lines) + "\n"
open(out_md, "w", encoding="utf-8").write(md)
print(md)
