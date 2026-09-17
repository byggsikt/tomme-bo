"""F-profil-analyse.py — are the forced-liquidation companies empty shells? Same pre-decision measures for the forced cohort
(data/F-tvang-profil.tsv, 12.09.2026) and the bankruptcy cohort (data/B2-01-extract.csv, B2's per-estate extract), side by side,
plus outcome by balance-sheet band inside the forced cohort and the balance sheets of the forced estates that paid out.
Appends section 6 to analyser/F-TVANGSAVVIKLING-utfall.md and prints it.
"""
import os, csv, statistics, datetime as dt, collections, json
here = os.path.dirname(os.path.abspath(__file__))
F_PATH = os.path.join(here, "..", "data", "F-tvang-profil.tsv")
K_PATH = os.path.join(here, "..", "data", "B2-01-extract.csv")
DIV_PATH = os.path.join(here, "..", "data", "F-avslutning-dividende-parsed.jsonl")
OUT = os.path.join(here, "..", "analyser", "F-TVANGSAVVIKLING-utfall.md")

def num(x):
    try:
        if x is None or x == "" or x == "<NULL>":
            return None
        return float(x)
    except ValueError:
        return None

def date(x):
    try:
        return dt.date.fromisoformat(x[:10]) if x else None
    except ValueError:
        return None

def load_f():
    rows = []
    with open(F_PATH, encoding="utf-8") as f:
        rd = csv.DictReader(f, delimiter="\t")
        for r in rd:
            rows.append(r)
    return rows

def load_k():
    rows = []
    with open(K_PATH, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            rows.append(r)
    return rows

F = load_f()
K = load_k()
for r in F:
    r["_ref"] = date(r["tv"]); r["_utf"] = r["utfall"]
for r in K:
    r["_ref"] = date(r["opened"]); r["_utf"] = r["utfall"]

def band(a):
    if a is None:
        return "0 ingen regnskap før"
    if a < 100_000: return "1 < 100k"
    if a < 500_000: return "2 100k–500k"
    if a < 1_000_000: return "3 0,5–1 M"
    if a < 5_000_000: return "4 1–5 M"
    if a < 20_000_000: return "5 5–20 M"
    return "6 ≥ 20 M"

def measures(rows, godkj_col="siste_godkjent", dl_col=None, varsel=False):
    n = len(rows)
    m = collections.OrderedDict()
    has_aa = [r for r in rows if r.get("aa_fy") and r.get("aa_source") != "proff-public-next-data"]
    m["Har årsregnskap med regnskapsår før vedtaks-/åpningsåret (Proff-kilden utelatt)"] = (len(has_aa), n)
    old = [r for r in has_aa if r["_ref"].year - int(float(r["aa_fy"])) >= 3]
    m["… og siste regnskapsår ligger ≥ 3 år tilbake (sluttet å levere)"] = (len(old), len(has_aa))
    m["Siste regnskapsår ≥ 3 år tilbake ELLER ingen regnskap"] = (len(old) + (n - len(has_aa)), n)
    bysrc = collections.Counter((r.get("aa_source"), r["_ref"].year - int(float(r["aa_fy"])) >= 3) for r in has_aa)
    m["… stale-andel per kilde (kontroll på kildeartefakt)"] = (" / ".join("%s %d/%d" % (src, bysrc[(src, True)], bysrc[(src, True)] + bysrc[(src, False)]) for src in sorted({k[0] for k in bysrc})), len(has_aa))
    g_none = [r for r in rows if not r.get(godkj_col)]
    m["Aldri kunngjort «Godkjent årsregnskap» før"] = (len(g_none), n)
    dsg = [num(r.get("dager_siden_godkjent")) for r in rows if num(r.get("dager_siden_godkjent")) is not None]
    m["Median dager siden siste godkjente regnskap (der det finnes)"] = ("median %d" % statistics.median(dsg), len(dsg))
    ta = [num(r.get("total_assets")) for r in has_aa]
    ta_known = [x for x in ta if x is not None]
    m["Sum eiendeler i siste regnskap: median (kr)"] = ("median %s" % format(int(statistics.median(ta_known)), ",").replace(",", " "), len(ta_known))
    m["Sum eiendeler < 100 000 kr"] = (sum(1 for x in ta_known if x < 100_000), len(ta_known))
    m["Sum eiendeler < 1 mill. kr"] = (sum(1 for x in ta_known if x < 1_000_000), len(ta_known))
    m["Sum eiendeler ≥ 5 mill. kr"] = (sum(1 for x in ta_known if x >= 5_000_000), len(ta_known))
    rev = [num(r.get("operating_revenue")) for r in has_aa]
    present = [x for x in rev if x is not None]
    m["Driftsinntekt-feltet finnes i raden (kildeavhengig: `brreg_regnskapsregister` mangler feltet i alle rader)"] = (len(present), len(rev))
    m["… og er lik 0, av radene der feltet finnes"] = (sum(1 for x in present if x == 0), len(present))
    rev_known = [x for x in present if x > 0]
    m["Driftsinntekter: median der > 0 (kr)"] = ("median %s" % format(int(statistics.median(rev_known)), ",").replace(",", " "), len(rev_known))
    eq = [(num(r.get("equity")), num(r.get("liabilities"))) for r in has_aa]
    m["Negativ egenkapital i siste regnskap"] = (sum(1 for e, l in eq if e is not None and e < 0), sum(1 for e, l in eq if e is not None))
    st = [r for r in rows if date(r.get("stiftet"))]
    ages = [(r["_ref"] - date(r["stiftet"])).days / 365.25 for r in st]
    m["Alder ved vedtak/åpning: median år (bare selskaper i kunngjoring.selskap)"] = ("median %.1f" % statistics.median(ages), len(ages))
    m["Yngre enn 3 år"] = (sum(1 for a in ages if a < 3), len(ages))
    kap = [num(r.get("kapital_ved_reg")) for r in rows]
    m["Aksjekapital ved registrering = 30 000 kr (minimum)"] = (sum(1 for x in kap if x is not None and x == 30_000), sum(1 for x in kap if x is not None))
    if dl_col:
        dl = [r.get(dl_col) for r in rows]
        m["Har hatt daglig leder registrert (bare selskaper med rolleposter i korpuset)"] = (sum(1 for x in dl if x == "t"), sum(1 for x in dl if x in ("t", "f")))
    if varsel:
        m["Varsel om tvangsoppløsning før vedtaket: fra Regnskapsregisteret (regnskap ikke levert)"] = (sum(1 for r in rows if r.get("varsel_regnskap") == "t"), n)
        m["… fra Foretaksregisteret (styre/daglig leder/revisor mangler)"] = (sum(1 for r in rows if r.get("varsel_foretak") == "t"), n)
        m["… ingen varsel funnet før vedtaket"] = (sum(1 for r in rows if not r.get("siste_varsel")), n)
        d = [num(r.get("dager_varsel_til_vedtak")) for r in rows if num(r.get("dager_varsel_til_vedtak")) is not None]
        m["Median dager fra siste varsel til vedtak"] = ("median %d" % statistics.median(d), len(d))
        tt = collections.Counter(r.get("tv_type") or "?" for r in rows)
        m["Kunngjøringstype: Tvangsoppløsning / Tvangsavvikling"] = ("%d / %d" % (tt.get("Tvangsoppløsning", 0), tt.get("Tvangsavvikling", 0)), n)
    else:
        m["Varsel om tvangsoppløsning noen gang før åpningen"] = (sum(1 for r in rows if r.get("n_varsel") not in (None, "", "0")), n)
    return m

mf = measures(F, dl_col="har_dl", varsel=True)
mk = measures(K, dl_col="har_dl_noen_gang", varsel=False)

def fmt(v):
    a, b = v
    if isinstance(a, str):
        return f"{a} (n = {b})"
    return f"{a} / {b} = {100.0 * a / b:.1f} %" if b else "—"

L = []
A = L.append
A("")
A("## 6. Er tvangsavviklingsboene tomme skall? Profil FØR vedtaket, mot konkursboene (12.09.2026 kl. 18; `sporringer/F-profil-extract.py`, `F-profil-analyse.py`; én kjøring)")
A("")
A("Samme mål på begge kohorter, målt strengt før vedtaksdatoen (tvangsavvikling) / åpningsdatoen (konkurs). Regnskap: `company_intel.annual_account`, siste regnskapsår før vedtaks-/åpningsåret, hele kroner (B2s regel). Konkurskohorten er B2s uttrekk (`data/B2-01-extract.csv`).")
A("")
A("| Mål | Tvangsavviklingsbo (2 571) | Konkursbo (5 165) |")
A("|---|---:|---:|")
keys = list(mf.keys())
for k in keys:
    A(f"| {k} | {fmt(mf[k])} | {fmt(mk[k]) if k in mk else '—'} |")
A("")

# outcome by band inside F
A("### 6.1 Utfall etter siste balanse — tvangsavviklingsboene (as-of 24.08.2026)")
A("")
A("| Sum eiendeler i siste regnskap før vedtaket | Bo | Innstilt | Ordinært avsluttet | Uten utfall |")
A("|---|---:|---:|---:|---:|")
byb = collections.defaultdict(collections.Counter)
for r in F:
    b = band(num(r.get("total_assets")) if r.get("aa_fy") else None)
    byb[b][r["_utf"]] += 1
for b in sorted(byb):
    c = byb[b]; n = sum(c.values())
    A(f"| {b} | {n} | {c['innstilt']} ({100.0 * c['innstilt'] / n:.1f} %) | {c['avsluttet']} ({100.0 * c['avsluttet'] / n:.1f} %) | {c['aapen']} |")
A("")
A("Konkursboene til sammenlikning (B2/V-B2, 730 d): ingen regnskap 87,0 %; < 100k 93,7 %; 100k–500k 86,0; 0,5–1 M 75,7; 1–5 M 66,4; 5–20 M 52,6; ≥ 20 M 37,8 % innstilt.")
A("")

# reason x outcome
A("### 6.2 Utfall etter hvem som varslet")
A("")
A("| Siste varsel før vedtaket | Bo | Innstilt |")
A("|---|---:|---:|")
byv = collections.defaultdict(collections.Counter)
for r in F:
    if not r.get("siste_varsel"):
        v = "ingen varsel i korpuset før vedtaket"
    elif r.get("varsel_regnskap") == "t" and r.get("varsel_foretak") == "t":
        v = "varslet av begge registre"
    elif r.get("varsel_regnskap") == "t":
        v = "Regnskapsregisteret (regnskap ikke levert)"
    elif r.get("varsel_foretak") == "t":
        v = "Foretaksregisteret (styre/daglig leder/revisor mangler)"
    else:
        v = "varsel finnes, register ikke oppgitt i korpuset"
    byv[v][r["_utf"]] += 1
for v in sorted(byv, key=lambda x: -sum(byv[x].values())):
    c = byv[v]; n = sum(c.values())
    A(f"| {v} | {n} | {c['innstilt']} ({100.0 * c['innstilt'] / n:.1f} %) |")
A("")

# the 175 that paid out
paid = [r for r in F if r["_utf"] == "avsluttet"]
ta = [num(r.get("total_assets")) for r in paid if r.get("aa_fy") and num(r.get("total_assets")) is not None]
eq = [num(r.get("equity")) for r in paid if r.get("aa_fy") and num(r.get("equity")) is not None]
A("### 6.3 De 175 tvangsavviklingsboene som endte med utlodning")
A("")
A(f"- Med regnskap før vedtaksåret: {sum(1 for r in paid if r.get('aa_fy'))} av {len(paid)}; sum eiendeler median {format(int(statistics.median(ta)), ',').replace(',', ' ') if ta else '—'} kr; ≥ 1 mill.: {sum(1 for x in ta if x >= 1_000_000)} av {len(ta)}; positiv egenkapital: {sum(1 for x in eq if x > 0)} av {len(eq)}.")
# 100 % payers
try:
    recs = [json.loads(l) for l in open(DIV_PATH, encoding="utf-8")]
    full = set()
    for rec in recs:
        for d in rec.get("dividende") or []:
            if d["pct"] >= 100 and (d["til"].lower().startswith("alle") or "uprior" in d["til"].lower() or "alminnelig" in d["til"].lower()):
                full.add(rec["orgnr"])
    fr = [r for r in paid if r["orgnr"] in full]
    ta2 = [num(r.get("total_assets")) for r in fr if r.get("aa_fy") and num(r.get("total_assets")) is not None]
    eq2 = [num(r.get("equity")) for r in fr if r.get("aa_fy") and num(r.get("equity")) is not None]
    A(f"- De {len(fr)} som betalte 100 prosent til uprioriterte/alle krav: regnskap før vedtaksåret {sum(1 for r in fr if r.get('aa_fy'))} av {len(fr)}; sum eiendeler median {format(int(statistics.median(ta2)), ',').replace(',', ' ') if ta2 else '—'} kr; positiv egenkapital {sum(1 for x in eq2 if x > 0)} av {len(eq2)}; varslet av Regnskapsregisteret {sum(1 for r in fr if r.get('varsel_regnskap') == 't')}, av Foretaksregisteret {sum(1 for r in fr if r.get('varsel_foretak') == 't')}.")
except FileNotFoundError:
    pass
A("")
A("**Dekningsforbehold:** kunngjøringsbaserte mål (godkjent årsregnskap, varsel, alder, kapital, daglig leder) hviler på korpuset, som bare har hentet kunngjøringer per selskap for 700 av de 2 571 (`kunngjoring.selskap`); tvangsavviklingsboene har sjeldnere full kunngjøringshistorikk i uttrekket. Regnskapsmålene (`annual_account`, Regnskapsregisterets API per orgnr) er de robuste: 1 925 av 2 571 har minst ett regnskap; resten har enten aldri levert eller ligger utenfor tabellens dekning (dokumentert 82 % for tvangsoppløste). Konkurskohortens tall er B2s.")
A("")
A("**Rettelse 12.09 kl. 21 (etter gjenkjøringen):** den tidligere setningen «82,1 % oppgav null driftsinntekter» var et kildeartefakt — feltet mangler i alle 1 358 rader fra `brreg_regnskapsregister`; bare 90 rader har eksplisitt null. Driftsinntekt brukes ikke lenger som skallbevis. Tre Proff-rader er utelatt. Stale-andelen er kontrollert per kilde og holder i alle kilder.")
A("")
A("Tolkning holdes til det målte: «tomt skall» er ikke en registerkategori. Det som kan vises, er hvor mange som hadde sluttet å levere regnskap, hva siste balanse inneholdt, hvem som varslet, og at utfallet følger balansen på samme måte som for konkursboene.")
md = "\n".join(L) + "\n"
s = open(OUT, encoding="utf-8").read()
if "## 6. Er tvangsavviklingsboene tomme skall" in s:
    s = s[:s.index("\n## 6. Er tvangsavviklingsboene tomme skall")]
open(OUT, "w", encoding="utf-8").write(s.rstrip("\n") + "\n" + md)
print(md)
