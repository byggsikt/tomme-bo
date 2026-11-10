# -*- coding: utf-8 -*-
"""B2 PREDICTORS — per-estate table, univariate tables (Wilson CI), IRLS logistic regression, ranking.
Reads B2-01-extract.csv (+ B2-03-postnr.csv) produced by the READ-ONLY SQL in this folder.
Writes: B2-per-estate.csv, B2-tables.md (all tables), B2-model.json (coefficients), B2-log.txt.
No lifelines/statsmodels: Wilson CI, IRLS logistic regression, LR tests, AUC and CV are implemented here.
"""
import json, math, sys, io, warnings
warnings.simplefilter("ignore")
import numpy as np, pandas as pd
from scipy import stats

HERE = "../data/"
MAP = "../../del-1-hovedstudien/data/bransjekart-v3_2026-08-30.json"
ASOF = pd.Timestamp("2026-08-24"); FULL_CUT = pd.Timestamp("2024-08-24"); H = 730
log = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a); print(s); log.write(s + "\n")

# ------------------------------------------------------------------ load
df = pd.read_csv(HERE + "B2-01-extract.csv", dtype={"orgnr": str, "sak_postnr": str, "tingrett": str})
pn = pd.read_csv(HERE + "B2-03-postnr.csv", dtype={"orgnr": str, "min_postnr_24m": str, "max_postnr_24m": str})
df = df.merge(pn, on="orgnr", how="left")
assert len(df) == 5165, len(df)
for c in ["opened", "innstilt", "avsluttet", "siste_godkjent", "stiftet", "nyreg_dato", "forste_kunngj_any", "siste_varsel", "fristdag", "siste_revisor_dato"]:
    df[c] = pd.to_datetime(df[c])
for c in df.columns:
    if not pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_datetime64_any_dtype(df[c]):
        u = set(df[c].dropna().astype(str).unique())
        if u and u <= {"t", "f"}:
            df[c] = df[c].astype(str).map({"t": True, "f": False}).astype(bool)
vc = df.utfall.value_counts()
assert (vc["innstilt"], vc["avsluttet"], vc["aapen"]) == (3897, 917, 351), vc
P("Sanity: n=5165 innstilt=3897 avsluttet=917 aapen=351 OK")

# ------------------------------------------------------------------ outcomes
df["y_asof"] = (df.utfall == "innstilt")
df["full"] = df.opened <= FULL_CUT
df["y730"] = df.innstilt.notna() & (df.dager_til_innstilt <= H)
df["avsl730"] = df.avsluttet.notna() & (df.dager_til_avsluttet <= H) & ~df.y730
P("Full-window sub-cohort (opened <= 2024-08-24):", int(df.full.sum()), " innstilt<=730d:", int(df.loc[df.full, "y730"].sum()),
  " avsluttet<=730d:", int(df.loc[df.full, "avsl730"].sum()), " open at 730d:", int((df.full & ~df.y730 & ~df.avsl730).sum()))

# ------------------------------------------------------------------ industry (study's v3 map, keyed on the printed label)
kart = json.load(open(MAP, encoding="utf-8"))["kart"]
kmap = {r["etikett"].replace("\u00a0", " "): r for r in kart}
IKKE = {"Uoppgitt", "Enheten er slettet", "Ikke oppgitt"}
def industry(lbl):
    if not isinstance(lbl, str) or not lbl.strip():
        return None, "tom"
    raw = lbl.replace(" || ", "\n").replace("\u00a0", " ")
    r = kmap.get(raw) or kmap.get(raw.strip()) or kmap.get(raw.split("\n")[0].strip())
    if r is None:
        return None, "ikke_i_kart"
    code = r.get("kanonisk_sn2007")
    if not code:
        return None, ("ikke_naering" if r.get("metode") == "IKKE_NAERING" or raw.split("\n")[0].strip() in IKKE else "ingen_kode")
    return code.split("|")[0], r.get("metode")
codes = df.bransje.map(industry)
df["nace"] = [c for c, m in codes]; df["nace_metode"] = [m for c, m in codes]
P("Industry map hits:", df.nace.notna().sum(), " misses by reason:", df.loc[df.nace.isna(), "nace_metode"].value_counts().to_dict())
def bygg_utf(k):  # study's primary definition: SN2007 41.2 + 42 + 43 (not 41.1 property development)
    return isinstance(k, str) and (k.startswith("42") or k.startswith("43") or (k.startswith("41") and not k.startswith("41.1")))
def grp(k, lbl):
    if not isinstance(k, str):
        first = (lbl if isinstance(lbl, str) else "").split(" || ")[0].strip()
        return "Uoppgitt (ingen næring i kunngjøringen)" if first in IKKE else "Uklassifisert etikett"
    n2 = int(k[:2])
    if bygg_utf(k): return "F Bygg og anlegg, utførende (41.2, 42, 43)"
    if k.startswith("41.1"): return "F 41.1 Eiendomsutvikling"
    if 45 <= n2 <= 47: return "G Varehandel og bilverksted"
    if 49 <= n2 <= 53: return "H Transport og lagring"
    if 55 <= n2 <= 56: return "I Overnatting og servering"
    if n2 == 68: return "L Fast eiendom (utleie, forvaltning, kjøp/salg)"
    if 69 <= n2 <= 75: return "M Faglig, vitenskapelig og teknisk tjenesteyting"
    if 77 <= n2 <= 82: return "N Forretningsmessig tjenesteyting (bemanning, renhold, utleie)"
    if 10 <= n2 <= 33: return "C Industri"
    if 58 <= n2 <= 66: return "J-K Informasjon, kommunikasjon og finans"
    if 1 <= n2 <= 9: return "A-B Primærnæringer og bergverk"
    if 35 <= n2 <= 39: return "D-E Kraft, vann og renovasjon"
    return "O-S Undervisning, helse, kultur og annen tjenesteyting"
df["bransjegruppe"] = [grp(k, l) for k, l in zip(df.nace, df.bransje)]
df["bygg_utf"] = df.nace.map(bygg_utf)
P("Bygg utførende:", int(df.bygg_utf.sum()), "(study: 1 280)")

# ------------------------------------------------------------------ unit rule (documented in the report) — all cohort rows are whole NOK
P("aa_unit values among selected pre-opening accounts:", df.loc[df.aa_fy.notna(), "aa_unit"].value_counts(dropna=False).to_dict())
P("Companies with a pre-opening account (FY < opening year, NOK):", int(df.aa_fy.notna().sum()),
  " companies with any account row:", int(df.aa_n_rows.notna().sum()),
  " companies whose only account(s) are FY >= opening year:", int((df.aa_n_rows.notna() & df.aa_fy.isna()).sum()))

# ------------------------------------------------------------------ derived predictors
def band(x, edges, labels, none_label):
    if pd.isna(x): return none_label
    for e, l in zip(edges, labels):
        if x < e: return l
    return labels[-1]
NA_ACC = "Ingen regnskap før åpning"
df["ta_band"] = df.total_assets.map(lambda x: band(x, [1e5, 5e5, 1e6, 5e6, 2e7, np.inf], ["<100 000", "100 000–<500 000", "500 000–<1 mill.", "1–<5 mill.", "5–<20 mill.", "≥20 mill."], NA_ACC))
df["ta_band3"] = df.total_assets.map(lambda x: band(x, [1e6, 5e6, np.inf], ["<1 mill.", "1–<5 mill.", "≥5 mill."], NA_ACC))
df["ek_band"] = df.equity.map(lambda x: band(x, [0, 1e5, 1e6, np.inf], ["Negativ", "0–<100 000", "100 000–<1 mill.", "≥1 mill."], NA_ACC))
df["ek_neg"] = df.equity.notna() & (df.equity < 0)
df["gjeld_band"] = df.liabilities.map(lambda x: band(x, [5e5, 1e6, 5e6, 2e7, np.inf], ["<500 000", "500 000–<1 mill.", "1–<5 mill.", "5–<20 mill.", "≥20 mill."], NA_ACC))
df["oml_band"] = df.current_assets.map(lambda x: band(x, [1e5, 5e5, 1e6, 5e6, np.inf], ["<100 000", "100 000–<500 000", "500 000–<1 mill.", "1–<5 mill.", "≥5 mill."], NA_ACC))
df["inntekt_band"] = df.apply(lambda r: NA_ACC if pd.isna(r.aa_fy) else ("Ikke oppgitt" if pd.isna(r.operating_revenue) else band(r.operating_revenue, [1, 1e6, 5e6, 2e7, np.inf], ["0", "<1 mill.", "1–<5 mill.", "5–<20 mill.", "≥20 mill."], NA_ACC)), axis=1)
df["ekandel"] = df.equity / df.total_assets.where(df.total_assets > 0)
df["ekandel_band"] = df.apply(lambda r: NA_ACC if pd.isna(r.aa_fy) else ("Eiendeler = 0" if pd.isna(r.ekandel) else band(r.ekandel, [0, 0.2, 0.5, np.inf], ["Negativ egenkapital", "0–<20 %", "20–<50 %", "≥50 %"], NA_ACC)), axis=1)
df["res_band"] = df.apply(lambda r: NA_ACC if pd.isna(r.aa_fy) else ("Ikke oppgitt" if pd.isna(r.annual_result) else ("Underskudd" if r.annual_result < 0 else "Overskudd/null")), axis=1)
# balance-sheet age at opening (fiscal year assumed calendar; period_label was calendar for all labelled rows)
df["balanse_alder_mnd"] = (df.opened - pd.to_datetime(df.aa_fy.fillna(1900).astype(int).astype(str) + "-12-31")).dt.days / 30.44
df.loc[df.aa_fy.isna(), "balanse_alder_mnd"] = np.nan
df["balanse_alder_band"] = df.balanse_alder_mnd.map(lambda x: band(x, [12, 24, np.inf], ["≤12 mnd", "12–24 mnd", ">24 mnd"], NA_ACC))
# was the selected account announced as approved before the opening? (proxy: a «Godkjent årsregnskap» dated on/after 1 Jan of FY+1 and before opening)
df["aa_levert_for_apning"] = df.apply(lambda r: (pd.notna(r.aa_fy) and pd.notna(r.siste_godkjent) and r.siste_godkjent >= pd.Timestamp(int(r.aa_fy) + 1, 1, 1)), axis=1)
# months since last approved annual account
df["mnd_siden_godkjent"] = df.dager_siden_godkjent / 30.44
df["godkjent_band"] = df.mnd_siden_godkjent.map(lambda x: band(x, [6, 12, 18, 24, np.inf], ["≤6 mnd", "6–12 mnd", "12–18 mnd", "18–24 mnd", ">24 mnd"], "Aldri godkjent regnskap"))
df["godkjent_band4"] = df.mnd_siden_godkjent.map(lambda x: band(x, [12, 18, np.inf], ["≤12 mnd", "12–18 mnd", ">18 mnd"], "Aldri godkjent regnskap"))
# «last due account filed?» — FY Y accounts are due 31 July Y+1; with a 2-month grace, an opening on/after 1 Oct expects an approval announced in the same calendar year, else in the previous calendar year
def levert(r):
    Y = r.opened.year if r.opened.month >= 10 else r.opened.year - 1
    st = r.stiftet if pd.notna(r.stiftet) else r.nyreg_dato
    if pd.notna(st) and st >= pd.Timestamp(Y - 1, 7, 1):
        return "Ikke aktuelt (for ungt til å ha regnskapsplikt for siste frist)"
    return "Ja" if (pd.notna(r.siste_godkjent) and r.siste_godkjent >= pd.Timestamp(Y, 1, 1)) else "Nei"
df["levert_siste_frist"] = df.apply(levert, axis=1)
# age
df["stiftet_eff"] = df.stiftet.fillna(df.nyreg_dato)
df["alder_aar"] = (df.opened - df.stiftet_eff).dt.days / 365.25
df["alder_band"] = df.alder_aar.map(lambda x: band(x, [2, 5, 10, 15, np.inf], ["<2 år", "2–<5 år", "5–<10 år", "10–<15 år", "≥15 år"], "?"))
old = df.alder_band.eq("?") & (df.forste_kunngj_any <= pd.Timestamp("2001-12-31"))
P("Age unknown (no stiftet/Nyregistrering):", int(df.alder_band.eq('?').sum()), " of which first announcement 1999–2001 (pre-corpus, => >=15 yrs):", int(old.sum()))
df.loc[old, "alder_band"] = "≥15 år"; df.loc[df.alder_band.eq("?"), "alder_band"] = "Ukjent"
# share capital (latest announced before opening)
df["kap_band"] = df.kapital_siste_for.map(lambda x: band(x, [30000, 30000.01, 100000.01, 1000000.01, np.inf], ["<30 000", "30 000 (lovens minimum)", "30 001–100 000", "100 001–1 mill.", ">1 mill."], "Ukjent"))
df["kap_forhoyet"] = df.kapital_siste_for.notna() & df.kapital_ved_reg.notna() & (df.kapital_siste_for > df.kapital_ved_reg)
# varsel
def varsel_cat(r, win):
    if not r[win]: return "Ingen"
    if r.varsel_regnskap: return "Regnskapsregisteret (manglende årsregnskap)"
    if r.varsel_foretak: return "Foretaksregisteret (manglende styre/DL/revisor)"
    return "Ukjent register (feed 2)"
df["varsel24_cat"] = df.apply(lambda r: varsel_cat(r, "varsel_24m"), axis=1)
df["varsel_ever_cat"] = df.apply(lambda r: ("Ingen" if r.n_varsel == 0 else ("Regnskapsregisteret (manglende årsregnskap)" if r.varsel_regnskap else ("Foretaksregisteret (manglende styre/DL/revisor)" if r.varsel_foretak else "Ukjent register (feed 2)"))), axis=1)
df["varsel24_any"] = df.varsel_24m
# roles / auditor / name / address
df["fratradt12"] = df.n_fratradt_12m > 0
df["styreendring12"] = df.n_styreendring_12m > 0
df["dlendring12"] = df.n_dlendring_12m > 0
df["revisorendring12"] = df.n_revisorendring_12m > 0
df["har_revisor"] = df.n_revisorrader_for > 0
df["navnebytte24"] = (df.n_navnebytte_24m > 0) | (df.n_navneendring_24m > 0)
df["navnebytte12"] = (df.n_navnebytte_12m > 0) | (df.n_navneendring_12m > 0)
df["adresseendring24"] = df.n_adresseendring_24m > 0
df["adresseendring12"] = df.n_adresseendring_12m > 0
df["flyttet_postnr24"] = df.n_postnr_24m >= 2
df["flyttet_region24"] = df.n_postnr2_24m >= 2
df["kreditorvarsel24"] = df.n_kreditorvarsel_24m > 0
df["kapitalendring24"] = df.n_kapitalendring_24m > 0
df["aar"] = df.opened.dt.year
df["oppbud_lbl"] = df.oppbud.map({True: "Oppbud (skyldnerens egen begjæring)", False: "Ikke oppbud (begjæring fra kreditor/det offentlige)"})
df["bygg_lbl"] = df.bygg_utf.map({True: "Bygg og anlegg, utførende", False: "Øvrige næringer"})
df["fristdag_band"] = df.dager_fristdag_til_apning.map(lambda x: band(x, [1, 15, 61, np.inf], ["Samme dag", "1–14 dager", "15–60 dager", ">60 dager"], "Ukjent"))

# ------------------------------------------------------------------ per-estate table
cols = ["orgnr", "opened", "aar", "utfall", "innstilt", "avsluttet", "dager_til_innstilt", "dager_til_avsluttet", "full", "y_asof", "y730", "avsl730",
        "oppbud", "tingrett", "bransje", "nace", "bransjegruppe", "bygg_utf", "fristdag", "dager_fristdag_til_apning",
        "aa_fy", "aa_source", "aa_unit", "aa_currency", "total_assets", "equity", "liabilities", "current_assets", "current_liabilities", "operating_revenue", "operating_result", "result_before_tax", "annual_result", "payroll_expenses", "employee_count",
        "aa_n_rows", "aa_min_fy", "aa_max_fy", "aa_levert_for_apning", "balanse_alder_mnd", "ta_band", "ek_band", "ek_neg", "ekandel", "inntekt_band",
        "siste_godkjent", "n_godkjent", "dager_siden_godkjent", "mnd_siden_godkjent", "godkjent_band", "levert_siste_frist",
        "stiftet", "nyreg_dato", "forste_kunngj_any", "alder_aar", "alder_band", "kapital_ved_reg", "kapital_siste", "kapital_siste_for", "kap_band", "kap_forhoyet",
        "n_varsel", "siste_varsel", "varsel_24m", "varsel_12m", "varsel_regnskap", "varsel_foretak", "varsel24_cat",
        "n_fratradt_12m", "n_dl_fratradt_12m", "n_styre_fratradt_12m", "n_fratradt_for", "n_rollerader_12m", "dl_utgaar_12m", "dl_utgaar_24m", "n_styreendring_12m", "n_dlendring_12m",
        "n_revisorrader_for", "revisor_utgaar_12m", "revisor_utgaar_24m", "n_revisorendring_12m", "n_revisjonsvalg_24m", "fravalg_revisjon_ved_stiftelse",
        "n_navnebytte_24m", "n_navnebytte_12m", "n_navneendring_24m", "n_adresseendring_24m", "n_adresseendring_12m", "n_postnr_24m", "n_postnr2_24m", "flyttet_postnr24", "flyttet_region24",
        "n_kreditorvarsel_24m", "n_kapitalendring_24m", "n_hendelser_for", "sak_postnr"]
df[cols].to_csv(HERE + "B2-per-estate.csv", index=False, encoding="utf-8")

# ------------------------------------------------------------------ helpers
def wilson(k, n, z=1.959964):
    if n == 0: return (float("nan"), float("nan"))
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)
def fmt_pct(k, n):
    if n == 0: return "–"
    lo, hi = wilson(k, n); return f"{100*k/n:.1f} % [{100*lo:.1f}–{100*hi:.1f}]"
md = io.StringIO()
def T(s=""): md.write(s + "\n")

def uni(var, title, order=None, note=None):
    sub = df; f = df[df.full]
    levels = order or list(pd.Series(sub[var]).value_counts().index)
    T(f"### {title}"); T()
    T("| Nivå | n (alle 5 165) | Innstilt as-of 24.08.2026, k / n = % [Wilson 95 %] | n (full 730-d-vindu) | Innstilt innen 730 d, k / n = % [Wilson 95 %] |")
    T("|---|---:|---|---:|---|")
    rows = []
    for lv in levels:
        a = sub[sub[var] == lv]; b = f[f[var] == lv]
        if len(a) == 0: continue
        k1 = int(a.y_asof.sum()); k2 = int(b.y730.sum())
        T(f"| {lv} | {len(a)} | {k1} / {len(a)} = {fmt_pct(k1, len(a))} | {len(b)} | {k2} / {len(b)} = {fmt_pct(k2, len(b))} |")
        rows.append((lv, len(a), k1, len(b), k2))
    k1 = int(sub.y_asof.sum()); k2 = int(f.y730.sum())
    T(f"| **Alle** | {len(sub)} | {k1} / {len(sub)} = {fmt_pct(k1, len(sub))} | {len(f)} | {k2} / {len(f)} = {fmt_pct(k2, len(f))} |")
    # chi-square test on the as-of and 730 d tables
    ct1 = pd.crosstab(sub[var], sub.y_asof); ct2 = pd.crosstab(f[var], f.y730)
    p1 = stats.chi2_contingency(ct1)[1] if ct1.shape[0] > 1 and ct1.shape[1] > 1 else float("nan")
    p2 = stats.chi2_contingency(ct2)[1] if ct2.shape[0] > 1 and ct2.shape[1] > 1 else float("nan")
    T(); T(f"χ²-test (uavhengighet): as-of p = {p1:.2g}; 730 d p = {p2:.2g}." + (f" {note}" if note else "")); T()
    return rows

# ------------------------------------------------------------------ univariate tables
T("## 1. Univariate tabeller"); T()
T("Alle andeler: teller / nevner. «as-of» = innstilt per 24.08.2026 (åpne bo teller i nevneren, som studiens 75,5 %). «730 d» = innstilt innen 730 dager i delkohorten åpnet t.o.m. 24.08.2024 (full observasjonstid; ordinært avsluttet og fortsatt åpne ved dag 730 teller som ikke-innstilt — et gulv). Alle prediktorer er målt strengt før åpningsdatoen."); T()
uni("oppbud_lbl", "1.1 Åpningsgrunnlag (felt «Åpnet etter» på åpningskunngjøringen; dekning 5 165/5 165)", ["Oppbud (skyldnerens egen begjæring)", "Ikke oppbud (begjæring fra kreditor/det offentlige)"])
uni("bygg_lbl", "1.2 Bygg og anlegg (utførende, studiens primærdefinisjon) mot øvrige", ["Bygg og anlegg, utførende", "Øvrige næringer"])
gorder = list(df.groupby("bransjegruppe").size().sort_values(ascending=False).index)
uni("bransjegruppe", "1.3 Næringsgruppe (SN2007 fra åpningskunngjøringens etikett via studiens kart v3; dekning: se «Uoppgitt»/«Uklassifisert»)", gorder)
uni("ta_band", "1.4 Sum eiendeler i siste balanse før åpning (hele kroner; «ingen regnskap» = ingen årsregnskap med regnskapsår før åpningsåret)", [NA_ACC, "<100 000", "100 000–<500 000", "500 000–<1 mill.", "1–<5 mill.", "5–<20 mill.", "≥20 mill."])
uni("ek_band", "1.5 Egenkapital i siste balanse før åpning", [NA_ACC, "Negativ", "0–<100 000", "100 000–<1 mill.", "≥1 mill."])
uni("ekandel_band", "1.6 Egenkapitalandel (egenkapital / sum eiendeler) i siste balanse", [NA_ACC, "Eiendeler = 0", "Negativ egenkapital", "0–<20 %", "20–<50 %", "≥50 %"])
uni("gjeld_band", "1.7 Sum gjeld i siste balanse", [NA_ACC, "<500 000", "500 000–<1 mill.", "1–<5 mill.", "5–<20 mill.", "≥20 mill."])
uni("oml_band", "1.8 Omløpsmidler i siste balanse", [NA_ACC, "<100 000", "100 000–<500 000", "500 000–<1 mill.", "1–<5 mill.", "≥5 mill."])
uni("inntekt_band", "1.9 Driftsinntekter i siste regnskap før åpning", [NA_ACC, "Ikke oppgitt", "0", "<1 mill.", "1–<5 mill.", "5–<20 mill.", "≥20 mill."])
uni("res_band", "1.10 Årsresultat i siste regnskap før åpning", [NA_ACC, "Ikke oppgitt", "Underskudd", "Overskudd/null"])
uni("balanse_alder_band", "1.11 Alder på siste balanse ved åpning (måneder fra 31.12. i regnskapsåret til åpningen)", [NA_ACC, "≤12 mnd", "12–24 mnd", ">24 mnd"])
uni("godkjent_band", "1.12 Tid siden siste «Godkjent årsregnskap» kunngjort av Regnskapsregisteret før åpning", ["≤6 mnd", "6–12 mnd", "12–18 mnd", "18–24 mnd", ">24 mnd", "Aldri godkjent regnskap"])
uni("levert_siste_frist", "1.13 Var siste pliktige årsregnskap levert ved åpningen? (frist 31. juli året etter regnskapsåret + 2 mnd slingring; «for ungt» = stiftet etter 30. juni to år før)", ["Ja", "Nei", "Ikke aktuelt (for ungt til å ha regnskapsplikt for siste frist)"])
uni("alder_band", "1.14 Selskapets alder ved åpning (kunngjoring.selskap.stiftet, ellers Nyregistrering; 258 uten dato er eldre enn korpuset og satt til ≥15 år)", ["<2 år", "2–<5 år", "5–<10 år", "10–<15 år", "≥15 år", "Ukjent"])
uni("kap_band", "1.15 Aksjekapital, siste kunngjorte før åpning (kunngjoring.kapital)", ["30 000 (lovens minimum)", "<30 000", "30 001–100 000", "100 001–1 mill.", ">1 mill.", "Ukjent"])
uni("kap_forhoyet", "1.16 Aksjekapital forhøyet etter stiftelsen (siste kapital > kapital ved registrering)", [False, True])
uni("varsel24_cat", "1.17 «Varsel om tvangsoppløsning» i de 24 månedene før åpning, etter hvilket register som varslet", ["Ingen", "Regnskapsregisteret (manglende årsregnskap)", "Foretaksregisteret (manglende styre/DL/revisor)", "Ukjent register (feed 2)"])
uni("varsel_ever_cat", "1.18 «Varsel om tvangsoppløsning» noen gang før åpning", ["Ingen", "Regnskapsregisteret (manglende årsregnskap)", "Foretaksregisteret (manglende styre/DL/revisor)", "Ukjent register (feed 2)"])
uni("fratradt12", "1.19 Fratrådt-rad i person_rolle (styre/DL/signatur) i de 12 månedene før åpning", [False, True])
uni("dl_utgaar_12m", "1.20 Daglig leder «Utgår» (kunngjort uten etterfølger) i de 12 månedene før åpning", [False, True])
uni("styreendring12", "1.21 «Endring av styre» kunngjort i de 12 månedene før åpning", [False, True])
uni("dlendring12", "1.22 «Endring av daglig leder» kunngjort i de 12 månedene før åpning", [False, True])
uni("har_revisor", "1.23 Har hatt registrert revisor (kunngjoring.revisor-rad før åpning)", [False, True])
uni("revisor_utgaar_12m", "1.24 Revisor «Utgår» (fratreden/fravalg kunngjort) i de 12 månedene før åpning", [False, True])
uni("revisorendring12", "1.25 «Endring av revisor» kunngjort i de 12 månedene før åpning", [False, True])
uni("navnebytte24", "1.26 Navneendring i de 24 månedene før åpning (navnebytte-tabell eller «Endring av foretaksnavn»)", [False, True])
uni("navnebytte12", "1.27 Navneendring i de 12 månedene før åpning", [False, True])
uni("adresseendring24", "1.28 «Endring av forretningsadresse» kunngjort i de 24 månedene før åpning", [False, True])
uni("flyttet_postnr24", "1.29 Flyttet: ≥2 ulike postnumre på kunngjorte adresser i de 24 månedene før åpning", [False, True])
uni("flyttet_region24", "1.30 Flyttet til annen region: ≥2 ulike tosifrede postnummerprefikser i de 24 månedene før åpning", [False, True])
uni("kreditorvarsel24", "1.31 «Kreditorvarsel» (oppløsning/kapitalnedsettelse/fusjon) i de 24 månedene før åpning", [False, True])
uni("kapitalendring24", "1.32 «Endring av kapital» i de 24 månedene før åpning", [False, True])
uni("fristdag_band", "1.33 Dager fra fristdag (dekningsloven § 1-2, satt ved åpning) til åpning — ikke et før-åpning-signal, bare deskriptivt", ["Samme dag", "1–14 dager", "15–60 dager", ">60 dager", "Ukjent"])
uni("aar", "1.34 Åpningsår (kalenderkontroll)", [2023, 2024])

# ------------------------------------------------------------------ cross-tabs a lawyer can use
T("### 1.35 Kryss: sum eiendeler × siste pliktige regnskap levert (730 d, full-vindu-delkohort)"); T()
f = df[df.full]
T("| Sum eiendeler | Levert: Ja | Levert: Nei | Ikke aktuelt (ungt) |"); T("|---|---|---|---|")
for lv in [NA_ACC, "<1 mill.", "1–<5 mill.", "≥5 mill."]:
    cells = []
    for lf in ["Ja", "Nei", "Ikke aktuelt (for ungt til å ha regnskapsplikt for siste frist)"]:
        b = f[(f.ta_band3 == lv) & (f.levert_siste_frist == lf)]; k = int(b.y730.sum())
        cells.append(f"{k} / {len(b)} = {fmt_pct(k, len(b))}" if len(b) else "–")
    T(f"| {lv} | " + " | ".join(cells) + " |")
T()

# scorecard: count of red flags
flags = {"Eiendeler < 1 mill. eller ingen regnskap": (df.ta_band3.isin(["<1 mill.", NA_ACC])),
         "Siste pliktige årsregnskap ikke levert": (df.levert_siste_frist == "Nei"),
         "Aksjekapital på lovens minimum (30 000) eller ukjent": (df.kap_band.isin(["30 000 (lovens minimum)", "<30 000", "Ukjent"]))}
df["n_flagg"] = sum(v.astype(int) for v in flags.values())
T("### 1.36a Sjekkliste (variant med aksjekapital): antall røde flagg av tre (" + "; ".join(flags.keys()) + ")"); T()
uni("n_flagg", "Antall flagg (variant a)", [0, 1, 2, 3])
flags2 = {"Eiendeler < 1 mill. i siste balanse, eller ingen balanse": (df.ta_band3.isin(["<1 mill.", NA_ACC])),
          "Ingen revisor registrert": (~df.har_revisor),
          "Siste pliktige årsregnskap ikke levert (eller selskapet er for ungt til å ha levert noe)": (df.levert_siste_frist != "Ja")}
df["n_flagg2"] = sum(v.astype(int) for v in flags2.values())
T("### 1.36b Sjekkliste (anbefalt): antall røde flagg av tre (" + "; ".join(flags2.keys()) + ")"); T()
uni("n_flagg2", "Antall flagg (variant b)", [0, 1, 2, 3])
T("### 1.37 Kryss: sum eiendeler × revisor registrert (730 d, full-vindu-delkohort; as-of i parentes)"); T()
f = df[df.full]
T("| Sum eiendeler | Revisor: nei | Revisor: ja |"); T("|---|---|---|")
for lv in [NA_ACC, "<1 mill.", "1–<5 mill.", "≥5 mill."]:
    cells = []
    for hv in [False, True]:
        b = f[(f.ta_band3 == lv) & (f.har_revisor == hv)]; k = int(b.y730.sum())
        a = df[(df.ta_band3 == lv) & (df.har_revisor == hv)]; ka = int(a.y_asof.sum())
        cells.append((f"{k} / {len(b)} = {fmt_pct(k, len(b))}" if len(b) else "–") + f" (as-of {ka}/{len(a)} = {100*ka/len(a):.1f} %)" if len(a) else "–")
    T(f"| {lv} | " + " | ".join(cells) + " |")
T()
T("### 1.38 Kryss: revisor × siste pliktige regnskap levert (730 d, full-vindu-delkohort)"); T()
T("| Revisor | Levert: Ja | Levert: Nei | Ikke aktuelt (ungt) |"); T("|---|---|---|---|")
for hv, lab in [(False, "Nei"), (True, "Ja")]:
    cells = []
    for lf in ["Ja", "Nei", "Ikke aktuelt (for ungt til å ha regnskapsplikt for siste frist)"]:
        b = f[(f.har_revisor == hv) & (f.levert_siste_frist == lf)]; k = int(b.y730.sum())
        cells.append(f"{k} / {len(b)} = {fmt_pct(k, len(b))}" if len(b) else "–")
    T(f"| {lab} | " + " | ".join(cells) + " |")
T()

# ------------------------------------------------------------------ logistic regression (IRLS)
def design(d, spec):
    X = [np.ones(len(d))]; names = ["(konstant)"]; groups = {}
    for var, kind, ref in spec:
        if kind == "bin":
            X.append(d[var].astype(float).values); names.append(var); groups[var] = [len(names) - 1]
        else:
            lv = [l for l in d[var].unique() if l != ref]; lv = sorted(lv, key=lambda s: str(s)); groups[var] = []
            for l in lv:
                X.append((d[var] == l).astype(float).values); names.append(f"{var}={l}"); groups[var].append(len(names) - 1)
    return np.column_stack(X), names, groups
def irls(X, y, max_iter=100, tol=1e-9):
    beta = np.zeros(X.shape[1]); ll_old = -np.inf
    for it in range(max_iter):
        eta = X @ beta; p = 1 / (1 + np.exp(-eta)); p = np.clip(p, 1e-12, 1 - 1e-12); w = p * (1 - p)
        z = eta + (y - p) / w
        XtW = X.T * w; Hm = XtW @ X
        beta_new = np.linalg.solve(Hm, XtW @ z)
        ll = float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
        if np.max(np.abs(beta_new - beta)) < tol: beta = beta_new; break
        beta = beta_new
    eta = X @ beta; p = 1 / (1 + np.exp(-eta)); p = np.clip(p, 1e-12, 1 - 1e-12); w = p * (1 - p)
    Hm = (X.T * w) @ X; cov = np.linalg.inv(Hm)
    ll = float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
    return beta, cov, ll, p, it + 1
def ex(v):
    return math.exp(min(max(v, -700), 700))
def auc(y, s):
    r = stats.rankdata(s); n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
def cv_auc(X, y, k=10, seed=1):
    rng = np.random.default_rng(seed); idx = rng.permutation(len(y)); folds = np.array_split(idx, k); preds = np.zeros(len(y))
    for fo in folds:
        tr = np.setdiff1d(idx, fo); b, *_ = irls(X[tr], y[tr]); preds[fo] = 1 / (1 + np.exp(-(X[fo] @ b)))
    return auc(y, preds)

def fit_report(title, d, spec, tag):
    X, names, groups = design(d, spec); y = d.y730.astype(float).values
    P(f"[{tag}] design: n={X.shape[0]} p={X.shape[1]} rank={np.linalg.matrix_rank(X)}")
    for j in range(1, X.shape[1]):
        cj = X[:, j]; ev = y[cj == 1].sum(); nn = (cj == 1).sum()
        if nn == 0 or ev == 0 or ev == nn: P(f"[{tag}] WARNING separation/empty column: {names[j]} n={nn} events={ev}")
    beta, cov, ll, p, iters = irls(X, y); se = np.sqrt(np.diag(cov)); z = beta / se; pv = 2 * stats.norm.sf(np.abs(z))
    for j in range(X.shape[1]):
        if abs(beta[j]) > 8 or se[j] > 8: P(f"[{tag}] WARNING unstable coefficient: {names[j]} beta={beta[j]:.2f} se={se[j]:.2f}")
    b0, *_ = irls(np.ones((len(y), 1)), y); ll0 = irls(np.ones((len(y), 1)), y)[2]
    T(f"### {title}"); T()
    T(f"n = {len(d)}, hendelser (innstilt ≤ 730 d) = {int(y.sum())}, IRLS-iterasjoner = {iters}, log-likelihood = {ll:.1f} (kun konstant: {ll0:.1f}), McFadden pseudo-R² = {1 - ll/ll0:.3f}, AUC (in-sample) = {auc(y, p):.3f}, AUC (10-fold CV) = {cv_auc(X, y):.3f}."); T()
    T("| Variabel (nivå mot referanse) | OR | 95 % KI | p (Wald) | n i nivå | LR-test for hele variabelen |"); T("|---|---:|---|---:|---:|---|")
    lr = {}
    for var, kind, ref in spec:
        cols_ = groups[var]; keep = [i for i in range(X.shape[1]) if i not in cols_]
        llr = irls(X[:, keep], y)[2]; stat = 2 * (ll - llr); lr[var] = (stat, len(cols_), stats.chi2.sf(stat, len(cols_)))
    out = []
    for var, kind, ref in spec:
        s, dfree, pl = lr[var]; first = True
        for i in groups[var]:
            lvl = names[i].split("=", 1)[1] if "=" in names[i] else "ja (mot nei)"
            nlv = int((d[var] == (lvl if kind != "bin" else True)).sum()) if kind != "bin" else int(d[var].sum())
            if kind != "bin":
                # recover the original level object for counting
                nlv = int((d[var].astype(str) == lvl).sum())
            T(f"| {var}: {lvl}" + (f" (ref. {ref})" if first and kind != "bin" else "") + f" | {ex(beta[i]):.2f} | {ex(beta[i]-1.96*se[i]):.2f}–{ex(beta[i]+1.96*se[i]):.2f} | {pv[i]:.3g} | {nlv} | " + (f"χ²({dfree}) = {s:.1f}, p = {pl:.2g}" if first else "") + " |")
            out.append({"var": var, "level": lvl, "or": ex(beta[i]), "lo": ex(beta[i]-1.96*se[i]), "hi": ex(beta[i]+1.96*se[i]), "p": float(pv[i]), "n": nlv, "lr_chi2": s, "lr_df": dfree, "lr_p": pl})
            first = False
    T()
    # calibration by decile
    dec = pd.qcut(p, 10, labels=False, duplicates="drop"); T("Kalibrering (desiler av predikert sannsynlighet): predikert gj.snitt / observert andel innstilt ≤ 730 d (n)"); T()
    T("| Desil | Predikert | Observert | n |"); T("|---|---|---|---:|")
    for q in sorted(set(dec)):
        m = dec == q; T(f"| {q+1} | {100*p[m].mean():.1f} % | {100*y[m].mean():.1f} % | {int(m.sum())} |")
    T()
    json.dump({"title": title, "n": len(d), "events": int(y.sum()), "ll": ll, "ll0": ll0, "auc": auc(y, p), "coef": out, "names": names, "beta": beta.tolist(), "se": se.tolist()}, open(HERE + f"B2-model-{tag}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return beta, names, p

T("## 2. Multivariabel logistisk regresjon — innstilt innen 730 dager, full-vindu-delkohort"); T()
T("Metode: IRLS (Newton–Raphson) i numpy; Wald-KI fra invers Fisher-informasjon; LR-test per variabel ved re-tilpasning uten variabelen; AUC in-sample og 10-fold kryssvalidert. Manglende data: håndtert som egne nivåer («Ingen regnskap før åpning», «Aldri godkjent regnskap», «Ukjent» kapital); ingen rad er fjernet. Egenkapital-dummyen er 0 når regnskap mangler (fanges av regnskaps-nivået). Utfallet er fast horisont: bo som var ordinært avsluttet eller fortsatt åpne ved dag 730 er 0."); T()
f = df[df.full].copy()
f["ta_m"] = f.ta_band3; f["godk_m"] = f.godkjent_band4
f["inntekt_m"] = f.inntekt_band.replace({NA_ACC: "1–<5 mill.", "Ikke oppgitt": "Ikke oppgitt/0", "0": "Ikke oppgitt/0"})  # no-account rows -> reference (their indicator lives in ta_m)
f["levert_m"] = f.levert_siste_frist.replace({"Ikke aktuelt (for ungt til å ha regnskapsplikt for siste frist)": "Ikke aktuelt (ungt)"})
f["varsel_m"] = f.varsel24_cat.replace({"Ukjent register (feed 2)": "Foretaksregisteret (manglende styre/DL/revisor)"})
f["kap_m"] = f.kap_band.replace({"<30 000": "30 000 (lovens minimum)", "Ukjent": "30 000 (lovens minimum)"})
f["alder_m"] = f.alder_band.replace({"Ukjent": "≥15 år"})
f["aar_2024"] = (f.aar == 2024)
f["bransje_m"] = f.bransjegruppe.replace({"A-B Primærnæringer og bergverk": "Øvrige/uklassifisert", "D-E Kraft, vann og renovasjon": "Øvrige/uklassifisert", "O-S Undervisning, helse, kultur og annen tjenesteyting": "Øvrige/uklassifisert", "J-K Informasjon, kommunikasjon og finans": "Øvrige/uklassifisert", "Uklassifisert etikett": "Øvrige/uklassifisert", "Uoppgitt (ingen næring i kunngjøringen)": "Uoppgitt", "F 41.1 Eiendomsutvikling": "L Fast eiendom (utleie, forvaltning, kjøp/salg)"})
SPEC_A = [("oppbud", "bin", None), ("bransje_m", "cat", "Øvrige/uklassifisert"), ("ta_m", "cat", "1–<5 mill."), ("inntekt_m", "cat", "1–<5 mill."), ("ek_neg", "bin", None),
          ("levert_m", "cat", "Ja"), ("alder_m", "cat", "5–<10 år"), ("kap_m", "cat", "30 000 (lovens minimum)"), ("varsel_m", "cat", "Ingen"),
          ("fratradt12", "bin", None), ("dl_utgaar_12m", "bin", None), ("styreendring12", "bin", None), ("har_revisor", "bin", None), ("revisor_utgaar_12m", "bin", None),
          ("navnebytte24", "bin", None), ("adresseendring24", "bin", None), ("flyttet_region24", "bin", None), ("kreditorvarsel24", "bin", None), ("aar_2024", "bin", None)]
betaA, namesA, pA = fit_report("2.1 Hovedmodell (modell A): alle før-åpning-prediktorer", f, SPEC_A, "A")
SPEC_A2 = [x for x in SPEC_A if x[0] != "levert_m"] + [("godk_m", "cat", "≤12 mnd")]
fit_report("2.1b Variant (modell A2): som A, men tid siden siste godkjente årsregnskap (≤12 / 12–18 / >18 mnd / aldri) i stedet for «levert siste frist»", f, SPEC_A2, "A2")
# sensitivity B: + tingrett fixed effects
f["tingrett_m"] = f.tingrett.fillna("Ukjent")
SPEC_B = SPEC_A + [("tingrett_m", "cat", "OSLO TINGRETT")]
fit_report("2.2 Sensitivitet (modell B): som A + tingrett som faste effekter (referanse Oslo)", f, SPEC_B, "B")
# sensitivity C: only accounts announced approved before opening count as «having accounts»
fC = f.copy(); m = fC.aa_fy.notna() & ~fC.aa_levert_for_apning
fC.loc[m, "ta_m"] = NA_ACC; fC.loc[m, "ek_neg"] = False
P("Model C: accounts re-coded as missing because not announced approved before opening:", int(m.sum()))
fit_report("2.3 Sensitivitet (modell C): som A, men balanser som ikke var kunngjort godkjent før åpningen regnes som «ingen regnskap» (n omkodet: %d)" % int(m.sum()), fC, SPEC_A, "C")
# compact model D: three lawyer-checkable signals
SPEC_D = [("ta_m", "cat", "1–<5 mill."), ("har_revisor", "bin", None), ("levert_m", "cat", "Ja")]
fit_report("2.4 Kompakt modell (modell D): bare de tre signalene en advokat kan slå opp på fem minutter (sum eiendeler, revisor, siste pliktige regnskap levert)", f, SPEC_D, "D")
SPEC_E = SPEC_D + [("oppbud", "bin", None), ("bygg_utf", "bin", None), ("dl_utgaar_12m", "bin", None)]
fit_report("2.5 Kompakt modell + åpningsgrunnlag, bygg og DL utgår (modell E)", f, SPEC_E, "E")
SPEC_F = [("kap_m", "cat", "30 000 (lovens minimum)"), ("alder_m", "cat", "5–<10 år"), ("oppbud", "bin", None)]
fit_report("2.6 Kontrast (modell F): bare aksjekapital, alder og åpningsgrunnlag — signalene som IKKE overlever justering", f, SPEC_F, "F")

# single-variable AUCs for ranking
T("## 3. Rangering av enkeltsignaler (full-vindu-delkohort, 730 d)"); T()
T("| Signal | Nivåer | Univariat AUC | Risikodifferanse ytterpunkter (pp) | Andel av boene i «rødt» nivå |"); T("|---|---|---:|---:|---:|")
rank = []
for var, lab in [("ta_band", "Sum eiendeler (6 bånd + ingen)"), ("ta_band3", "Sum eiendeler (3 bånd + ingen)"), ("godkjent_band", "Tid siden siste godkjente årsregnskap"), ("levert_siste_frist", "Siste pliktige regnskap levert"), ("ek_band", "Egenkapital"), ("ekandel_band", "Egenkapitalandel"), ("gjeld_band", "Sum gjeld"), ("oml_band", "Omløpsmidler"), ("inntekt_band", "Driftsinntekter"), ("alder_band", "Alder"), ("kap_band", "Aksjekapital"), ("oppbud_lbl", "Åpningsgrunnlag"), ("bransjegruppe", "Næringsgruppe"), ("varsel24_cat", "Varsel om tvangsoppløsning 24 mnd"), ("fratradt12", "Fratrådt rolle 12 mnd"), ("dl_utgaar_12m", "DL utgår 12 mnd"), ("styreendring12", "Styreendring 12 mnd"), ("har_revisor", "Har revisor"), ("revisor_utgaar_12m", "Revisor utgår 12 mnd"), ("navnebytte24", "Navneendring 24 mnd"), ("adresseendring24", "Adresseendring 24 mnd"), ("flyttet_region24", "Flyttet region 24 mnd"), ("kreditorvarsel24", "Kreditorvarsel 24 mnd"), ("n_flagg", "Antall røde flagg, variant a (0–3)"), ("n_flagg2", "Antall røde flagg, variant b (0–3)"), ("godkjent_band4", "Tid siden siste godkjente årsregnskap (4 nivå)")]:
    g = f.groupby(var).y730.agg(["mean", "size"]); score = f[var].map(g["mean"]).values; a = auc(f.y730.astype(float).values, score)
    rd = 100 * (g["mean"].max() - g["mean"].min()); red = g["size"][g["mean"].idxmax()] / len(f)
    T(f"| {lab} | {len(g)} | {a:.3f} | {rd:.1f} | {100*red:.1f} % ({g['mean'].idxmax()}) |"); rank.append((lab, a, rd))
T()

# ------------------------------------------------------------------ 5. what the bands mean concretely: three-state outcome at 730 d, timing, and the bygg ladder
T("## 5. Hva båndene betyr konkret — tre-tilstandsutfall ved dag 730, tid til innstilling, og «byggstigen»"); T()
def three_state(var, title, order):
    T(f"### {title}"); T()
    T("| Nivå | n (full-vindu) | Innstilt ≤730 d | Ordinært avsluttet ≤730 d (utlodning) | Fortsatt åpent ved dag 730 | Median dager til innstilling (blant innstilte ≤730 d) | Median dager til avslutning (blant avsluttede ≤730 d) |")
    T("|---|---:|---|---|---|---:|---:|")
    for lv in order:
        b = f[f[var] == lv]
        if len(b) == 0: continue
        k1 = int(b.y730.sum()); k2 = int(b.avsl730.sum()); k3 = len(b) - k1 - k2
        m1 = b.loc[b.y730, "dager_til_innstilt"].median(); m2 = b.loc[b.avsl730, "dager_til_avsluttet"].median()
        T(f"| {lv} | {len(b)} | {k1} = {100*k1/len(b):.1f} % | {k2} = {100*k2/len(b):.1f} % | {k3} = {100*k3/len(b):.1f} % | {m1:.0f} | {m2:.0f} |")
    k1 = int(f.y730.sum()); k2 = int(f.avsl730.sum()); k3 = len(f) - k1 - k2
    T(f"| **Alle** | {len(f)} | {k1} = {100*k1/len(f):.1f} % | {k2} = {100*k2/len(f):.1f} % | {k3} = {100*k3/len(f):.1f} % | {f.loc[f.y730, 'dager_til_innstilt'].median():.0f} | {f.loc[f.avsl730, 'dager_til_avsluttet'].median():.0f} |"); T()
f = df[df.full].copy()
three_state("ta_band", "5.1 Etter sum eiendeler i siste balanse", [NA_ACC, "<100 000", "100 000–<500 000", "500 000–<1 mill.", "1–<5 mill.", "5–<20 mill.", "≥20 mill."])
three_state("inntekt_band", "5.2 Etter driftsinntekter i siste regnskap", [NA_ACC, "Ikke oppgitt", "0", "<1 mill.", "1–<5 mill.", "5–<20 mill.", "≥20 mill."])
three_state("har_revisor", "5.3 Etter revisor registrert", [False, True])
three_state("levert_siste_frist", "5.4 Etter om siste pliktige regnskap var levert", ["Ja", "Nei", "Ikke aktuelt (for ungt til å ha regnskapsplikt for siste frist)"])
three_state("n_flagg2", "5.5 Etter antall røde flagg (variant b: eiendeler < 1 mill./ingen balanse; ingen revisor; siste pliktige regnskap ikke levert/for ungt)", [0, 1, 2, 3])
three_state("oppbud_lbl", "5.6 Etter åpningsgrunnlag", ["Oppbud (skyldnerens egen begjæring)", "Ikke oppbud (begjæring fra kreditor/det offentlige)"])
three_state("bransjegruppe", "5.7 Etter næringsgruppe", gorder)
T("### 5.8 Åpningsgrunnlag × sum eiendeler (innstilt ≤730 d, full-vindu-delkohort)"); T()
T("| Sum eiendeler | Oppbud | Ikke oppbud |"); T("|---|---|---|")
for lv in [NA_ACC, "<1 mill.", "1–<5 mill.", "≥5 mill."]:
    cells = []
    for ob in [True, False]:
        b = f[(f.ta_band3 == lv) & (f.oppbud == ob)]; k = int(b.y730.sum()); cells.append(f"{k} / {len(b)} = {fmt_pct(k, len(b))}" if len(b) else "–")
    T(f"| {lv} | " + " | ".join(cells) + " |")
T()
T("### 5.9 «Byggstigen»: hvor mye av bygg-effekten forklares av størrelse? (logistisk regresjon, innstilt ≤730 d, full-vindu-delkohort; OR for bygg utførende mot øvrige)"); T()
T("| Modell | OR bygg | 95 % KI | p |"); T("|---|---:|---|---:|")
ladder = [("Bygg alene", [("bygg_utf", "bin", None)]),
          ("+ sum eiendeler (3 bånd + ingen)", [("bygg_utf", "bin", None), ("ta_m", "cat", "1–<5 mill.")]),
          ("+ driftsinntekter", [("bygg_utf", "bin", None), ("ta_m", "cat", "1–<5 mill."), ("inntekt_m", "cat", "1–<5 mill.")]),
          ("+ revisor", [("bygg_utf", "bin", None), ("ta_m", "cat", "1–<5 mill."), ("inntekt_m", "cat", "1–<5 mill."), ("har_revisor", "bin", None)]),
          ("+ siste pliktige regnskap levert, egenkapital negativ", [("bygg_utf", "bin", None), ("ta_m", "cat", "1–<5 mill."), ("inntekt_m", "cat", "1–<5 mill."), ("har_revisor", "bin", None), ("levert_m", "cat", "Ja"), ("ek_neg", "bin", None)]),
          ("+ tingrett", [("bygg_utf", "bin", None), ("ta_m", "cat", "1–<5 mill."), ("inntekt_m", "cat", "1–<5 mill."), ("har_revisor", "bin", None), ("levert_m", "cat", "Ja"), ("ek_neg", "bin", None), ("tingrett_m", "cat", "OSLO TINGRETT")])]
f["ta_m"] = f.ta_band3; f["inntekt_m"] = f.inntekt_band.replace({NA_ACC: "1–<5 mill.", "Ikke oppgitt": "Ikke oppgitt/0", "0": "Ikke oppgitt/0"})
f["levert_m"] = f.levert_siste_frist.replace({"Ikke aktuelt (for ungt til å ha regnskapsplikt for siste frist)": "Ikke aktuelt (ungt)"}); f["tingrett_m"] = f.tingrett.fillna("Ukjent")
for lab, spec in ladder:
    X, names, groups = design(f, spec); y = f.y730.astype(float).values; beta, cov, ll, p_, it = irls(X, y); se = np.sqrt(np.diag(cov)); i = names.index("bygg_utf")
    T(f"| {lab} | {ex(beta[i]):.2f} | {ex(beta[i]-1.96*se[i]):.2f}–{ex(beta[i]+1.96*se[i]):.2f} | {2*stats.norm.sf(abs(beta[i]/se[i])):.3g} |")
T()
T("### 5.10 Sammensetning: driftsinntekter og revisor, bygg mot øvrige (alle 5 165)"); T()
T("| Gruppe | n | Driftsinntekter ≥5 mill. | Driftsinntekter <1 mill., 0, ikke oppgitt eller ingen regnskap | Revisor registrert | Sum eiendeler ≥5 mill. | Ingen balanse før åpning |"); T("|---|---:|---:|---:|---:|---:|---:|")
for lab, m in [("Bygg og anlegg, utførende", df.bygg_utf), ("Øvrige næringer", ~df.bygg_utf)]:
    b = df[m]
    T(f"| {lab} | {len(b)} | {100*b.inntekt_band.isin(['5–<20 mill.','≥20 mill.']).mean():.1f} % | {100*b.inntekt_band.isin(['<1 mill.','0','Ikke oppgitt',NA_ACC]).mean():.1f} % | {100*b.har_revisor.mean():.1f} % | {100*b.ta_band3.eq('≥5 mill.').mean():.1f} % | {100*b.ta_band3.eq(NA_ACC).mean():.1f} % |")
T()
T("### 5.11 Predikerte sannsynligheter fra den kompakte modellen D for typiske profiler (innstilt ≤730 d)"); T()
X, names, groups = design(f, SPEC_D); y = f.y730.astype(float).values; bD, covD, *_ = irls(X, y)
def pred(ta, rev, lev):
    v = np.zeros(len(names)); v[0] = 1
    if ta != "1–<5 mill.": v[names.index(f"ta_m={ta}")] = 1
    v[names.index("har_revisor")] = float(rev)
    if lev != "Ja": v[names.index(f"levert_m={lev}")] = 1
    eta = v @ bD; se = math.sqrt(v @ covD @ v); return 1/(1+math.exp(-eta)), 1/(1+math.exp(-(eta-1.96*se))), 1/(1+math.exp(-(eta+1.96*se)))
T("| Profil | Predikert andel innstilt ≤730 d | 95 % KI | Observert i samme celle (k / n) |"); T("|---|---:|---|---|")
for ta, rev, lev, lab in [("≥5 mill.", True, "Ja", "Eiendeler ≥5 mill., revisor, regnskap levert"), ("1–<5 mill.", True, "Ja", "Eiendeler 1–5 mill., revisor, regnskap levert"), ("1–<5 mill.", False, "Ja", "Eiendeler 1–5 mill., ingen revisor, regnskap levert"),
                          ("<1 mill.", False, "Ja", "Eiendeler <1 mill., ingen revisor, regnskap levert"), ("<1 mill.", False, "Nei", "Eiendeler <1 mill., ingen revisor, siste regnskap ikke levert"), (NA_ACC, False, "Nei", "Ingen balanse, ingen revisor, siste regnskap ikke levert"), (NA_ACC, False, "Ikke aktuelt (ungt)", "Ingen balanse, ingen revisor, for ungt")]:
    pm, lo, hi = pred(ta, rev, lev); b = f[(f.ta_m == ta) & (f.har_revisor == rev) & (f.levert_m == lev)]; k = int(b.y730.sum())
    T(f"| {lab} | {100*pm:.1f} % | {100*lo:.1f}–{100*hi:.1f} | {k} / {len(b)}" + (f" = {100*k/len(b):.1f} %" if len(b) else "") + " |")
T()

# ------------------------------------------------------------------ coverage summary
T("## 4. Dekning per variabel (av 5 165)"); T()
T("| Variabel | Finnes for | Andel |"); T("|---|---:|---:|")
for lab, m in [("Åpningsgrunnlag (felt Åpnet etter, tilstede/fraværende)", df.oppbud.notna()), ("Bransjeetikett på åpningen", df.bransje.notna()), ("NACE-kode via kart v3", df.nace.notna()),
               ("Årsregnskap med regnskapsår før åpningsåret (NOK)", df.aa_fy.notna()), ("— derav kunngjort godkjent før åpning", df.aa_levert_for_apning), ("Minst ett «Godkjent årsregnskap» før åpning", df.siste_godkjent.notna()),
               ("Stiftelsesdato (selskap.stiftet / Nyregistrering)", df.stiftet_eff.notna()), ("Aksjekapital kunngjort før åpning", df.kapital_siste_for.notna()), ("Person_rolle-rad før åpning", df.n_personer_for > 0),
               ("Revisor-rad før åpning", df.har_revisor), ("Adresse med postnr i 24-mnd-vinduet", df.n_postnr_24m > 0), ("Lønnskostnad / ansatte (annual_account)", df.payroll_expenses.notna() | df.employee_count.notna())]:
    T(f"| {lab} | {int(m.sum())} | {100*m.mean():.1f} % |")
T()
open(HERE + "B2-tables.md", "w", encoding="utf-8").write(md.getvalue())
open(HERE + "B2-log.txt", "w", encoding="utf-8").write(log.getvalue())
P("DONE")
