# B1-02: outcome by PETITION BASIS (oppbud vs not registered as oppbud), Tomme bo cohort.
# Input : B1-01-master.tsv (5 165 rows from Postgres, read-only extract, as-of 2026-08-24)
#         bransjekart-v3_2026-08-30.json (study's label -> NACE map, READ ONLY)
#         _kohort-rader-arbeidskopi.json  (study's frozen rows, READ ONLY, cross-check only)
# Output: B1-results.json, B1-tables.md (all tables), B1-cohort-tagged.tsv (per-company work file)
import json, sys, re, unicodedata, datetime as dt, collections
import numpy as np
sys.path.insert(0, r"../data")
from B1_lib import (AJ, gray_test, gray_stratified, wilson, clopper_pearson, newcombe, chi2_yates,
                    boot_cif, pct_ci, boot_indices, logit_fit, or_ci, mh_or, pooled_rd, iv_pooled,
                    H12, H18, H24, Z)

W = r"../data"
V3 = r"../../del-1-hovedstudien/data/bransjekart-v3_2026-08-30.json"
FROZEN = r"../../del-1-hovedstudien/data/_kohort-rader-arbeidskopi.json"
END = dt.date(2026, 8, 24)
FULL730_CUTOFF = dt.date(2024, 8, 24)
SEED = 20260912
B_MAIN, B_COURT = 2000, 1000
rng = np.random.default_rng(SEED)

md = []          # markdown tables
res = {}         # machine-readable results
def P(s=""):
    md.append(s)
def pct(x, d=1):
    return f"{100*x:.{d}f}"
def ci_s(lo, hi, d=1):
    return f"[{100*lo:.{d}f}–{100*hi:.{d}f}]"

# ------------------------------------------------------------------ 1. load master
rows = []
for line in open(f"{W}/B1-01-master.tsv", encoding="utf-8"):
    f = line.rstrip("\n").split("\t")
    orgnr, opened, innstilt, avsluttet, oppbud, tingrett, bransje, saksnr, fristdag, apn = f
    rows.append(dict(orgnr=orgnr, opened=dt.date.fromisoformat(opened),
                     innstilt=dt.date.fromisoformat(innstilt) if innstilt else None,
                     avsluttet=dt.date.fromisoformat(avsluttet) if avsluttet else None,
                     oppbud=oppbud == "1", tingrett=tingrett,
                     bransje_raw=bransje.replace(" \\n ", "\n"), saksnr=saksnr,
                     fristdag=dt.date.fromisoformat(fristdag) if fristdag else None,
                     apningsrader=int(apn)))
N = len(rows)
for r in rows:
    r["oppf"] = (END - r["opened"]).days
    if r["innstilt"]:
        r["utfall"] = "innstilt"; r["t"] = (r["innstilt"] - r["opened"]).days; r["cause"] = 1
    elif r["avsluttet"]:
        r["utfall"] = "avsluttet"; r["t"] = (r["avsluttet"] - r["opened"]).days; r["cause"] = 2
    else:
        r["utfall"] = "aapen"; r["t"] = r["oppf"]; r["cause"] = 0
    r["full730"] = r["opened"] <= FULL730_CUTOFF
    r["inn730"] = r["cause"] == 1 and r["t"] <= H24
cnt = collections.Counter(r["utfall"] for r in rows)
assert (N, cnt["innstilt"], cnt["avsluttet"], cnt["aapen"]) == (5165, 3897, 917, 351), cnt
n_opp = sum(r["oppbud"] for r in rows)
assert n_opp == 3734, n_opp
print("sanity OK: 5165/3897/917/351, oppbud", n_opp)
res["sanity"] = dict(n=N, innstilt=cnt["innstilt"], avsluttet=cnt["avsluttet"], aapen=cnt["aapen"], oppbud=n_opp,
                     oppf_min=min(r["oppf"] for r in rows), oppf_max=max(r["oppf"] for r in rows),
                     apningsrader_max=max(r["apningsrader"] for r in rows))

# ------------------------------------------------------------------ 2. construction tag (study's classifier)
def nfc(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s or "")).strip()
kart = json.load(open(V3, encoding="utf-8"))["kart"]
kmap = {}
collisions = 0
for k in kart:
    key = nfc(k["etikett"])
    if key in kmap and kmap[key] != k["kanonisk_sn2007"]:
        collisions += 1
    kmap[key] = k["kanonisk_sn2007"]
def er_utforende(code):
    if not code:
        return False
    for c in code.split("|"):
        if re.match(r"^(42|43)", c) or (re.match(r"^41", c) and not re.match(r"^41\.1", c)):
            return True
    return False
unmapped = collections.Counter()
for r in rows:
    key = nfc(r["bransje_raw"])
    if key not in kmap:
        # fall back to first line (multi-industry labels)
        key1 = nfc(r["bransje_raw"].split("\n")[0])
        code = kmap.get(key1)
        if key1 not in kmap:
            unmapped[key] += 1
    else:
        code = kmap[key]
    r["nace"] = code
    r["bygg"] = er_utforende(code)
nb = sum(r["bygg"] for r in rows)
cb = collections.Counter(r["utfall"] for r in rows if r["bygg"])
print("bygg utforende:", nb, dict(cb), "unmapped labels:", sum(unmapped.values()), "collisions:", collisions)
res["bygg_tag"] = dict(n_bygg=nb, innstilt=cb["innstilt"], avsluttet=cb["avsluttet"], aapen=cb["aapen"],
                       unmapped_companies=sum(unmapped.values()), unmapped_top=unmapped.most_common(10),
                       expected="1280 / 911 / 258 / 111 (TALLJOURNAL B1-B3)")

# cross-check against the study's frozen rows (no orgnr there -> tuple key)
frozen = json.load(open(FROZEN, encoding="utf-8"))
fkey = collections.defaultdict(list)
for fr in frozen:
    k = (fr["aapning"], fr["tingrett"], nfc((fr["bransje"] or "").split("\n")[0]), fr["innstilling"] or "", fr["avslutning"] or "")
    fkey[k].append(fr["bygg_utforende"] is True)
matched = agree = ambiguous = 0
for r in rows:
    k = (r["opened"].isoformat(), r["tingrett"], nfc(r["bransje_raw"].split("\n")[0]),
         r["innstilt"].isoformat() if r["innstilt"] else "", r["avsluttet"].isoformat() if r["avsluttet"] else "")
    if k in fkey:
        tags = set(fkey[k])
        if len(tags) == 1:
            matched += 1
            agree += (tags.pop() == r["bygg"])
        else:
            ambiguous += 1
res["bygg_crosscheck_frozen"] = dict(matched=matched, agree=agree, ambiguous=ambiguous, unmatched=N - matched - ambiguous)
print("frozen cross-check: matched", matched, "agree", agree, "ambiguous", ambiguous)

# save per-company work file
with open(f"{W}/B1-cohort-tagged.tsv", "w", encoding="utf-8") as fh:
    fh.write("orgnr\topened\tutfall\tt_days\tcause\toppbud\tbygg\tnace\ttingrett\tfull730\tinn730\n")
    for r in rows:
        fh.write(f"{r['orgnr']}\t{r['opened']}\t{r['utfall']}\t{r['t']}\t{r['cause']}\t{int(r['oppbud'])}\t{int(r['bygg'])}\t{r['nace'] or ''}\t{r['tingrett']}\t{int(r['full730'])}\t{int(r['inn730'])}\n")

# numpy arrays
t = np.array([r["t"] for r in rows]); cause = np.array([r["cause"] for r in rows])
opp = np.array([r["oppbud"] for r in rows]); bygg = np.array([r["bygg"] for r in rows])
full = np.array([r["full730"] for r in rows]); inn730 = np.array([r["inn730"] for r in rows])
court = np.array([r["tingrett"] for r in rows])
innstilt = cause == 1; avsl = cause == 2; open_ = cause == 0
G = {"oppbud": opp, "begjaering": ~opp}   # begjaering = not registered as oppbud
GLAB = {"oppbud": "Oppbud (felt «Åpnet etter: Oppbud»)", "begjaering": "Ikke registrert som oppbud (= begjæring fra andre)"}

# ------------------------------------------------------------------ (a) as-of shares
P("## (a) Utfall per 24.08.2026 etter åpningsgrunnlag (as-of, hele kohorten)")
P()
P("| Grunnlag | n | innstilt § 135 | % [Wilson 95 %] | ordinær avslutning | % [95 %] | fortsatt åpne | % [95 %] |")
P("|---|---:|---:|---:|---:|---:|---:|---:|")
res["asof"] = {}
for g, m in G.items():
    n = int(m.sum()); ki = int((m & innstilt).sum()); ka = int((m & avsl).sum()); ko = int((m & open_).sum())
    wi, wa, wo = wilson(ki, n), wilson(ka, n), wilson(ko, n)
    P(f"| {GLAB[g]} | {n} | {ki} | {pct(ki/n)} {ci_s(*wi)} | {ka} | {pct(ka/n)} {ci_s(*wa)} | {ko} | {pct(ko/n)} {ci_s(*wo)} |")
    res["asof"][g] = dict(n=n, innstilt=ki, avsluttet=ka, aapen=ko, p_innstilt=ki/n, wilson=wi, cp=clopper_pearson(ki, n))
n1, k1 = int((~opp).sum()), int((~opp & innstilt).sum()); n0, k0 = int(opp.sum()), int((opp & innstilt).sum())
d = k1/n1 - k0/n0; nc = newcombe(k1, n1, k0, n0); x2, px = chi2_yates(k1, n1-k1, k0, n0-k0)
P(f"| **Differanse begjæring − oppbud** | | | **{100*d:+.1f} pp** [Newcombe {100*nc[0]:+.1f}; {100*nc[1]:+.1f}] | | | | |")
P()
P(f"χ²(Yates) = {x2:.2f}, p = {px:.2e}. Dekning: grunnlaget er definert for 5 165/5 165 (100,0 %).")
P()
res["asof"]["diff"] = dict(rd=d, newcombe=nc, chi2=x2, p=px)

# ------------------------------------------------------------------ (b) 730-day fixed window
P("## (b) Antakelsesfri 24-månedersandel — delkohort åpnet ≤ 24.08.2024 (full 730-dagers oppfølging)")
P()
P("| Grunnlag | n (åpnet ≤ 2024-08-24) | innstilt innen 730 d | % [Wilson 95 %] | [Clopper–Pearson] | avsluttet innen 730 d (uten innstilling) | % | verken innen 730 d | % |")
P("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
res["fixed730"] = {}
for g, m in G.items():
    mm = m & full; n = int(mm.sum()); k = int((mm & inn730).sum())
    ka = int((mm & avsl & (t <= H24)).sum()); ko = n - k - ka
    P(f"| {GLAB[g]} | {n} | {k} | {pct(k/n)} {ci_s(*wilson(k, n))} | {ci_s(*clopper_pearson(k, n))} | {ka} | {pct(ka/n)} | {ko} | {pct(ko/n)} |")
    res["fixed730"][g] = dict(n=n, innstilt730=k, avsluttet730=ka, verken=ko, p=k/n, wilson=wilson(k, n), cp=clopper_pearson(k, n))
n1, k1 = int((~opp & full).sum()), int((~opp & full & inn730).sum()); n0, k0 = int((opp & full).sum()), int((opp & full & inn730).sum())
d = k1/n1 - k0/n0; nc = newcombe(k1, n1, k0, n0); x2, px = chi2_yates(k1, n1-k1, k0, n0-k0)
P(f"| **Differanse begjæring − oppbud** | {n1+n0} | | **{100*d:+.1f} pp** [Newcombe {100*nc[0]:+.1f}; {100*nc[1]:+.1f}] | | | | | |")
P()
P(f"χ²(Yates) = {x2:.2f}, p = {px:.2e}. Ingen sensurering innenfor vinduet; ren binomisk andel, ingen konkurrerende-risiko-estimator.")
P()
res["fixed730"]["diff"] = dict(rd=d, newcombe=nc, chi2=x2, p=px)

# ------------------------------------------------------------------ (c) Aalen–Johansen by basis
P("## (c) Kumulativ insidens av innstilling (Aalen–Johansen, ordinær avslutning som konkurrerende hendelse)")
P()
P("Daglig tidsrutenett (hele dager fra åpningsdato). Risikomengde ved dag t = bo med observert tid ≥ t (verken innstilt, avsluttet eller sensurert før t). "
  "Sensurering 24.08.2026. Intervaller: deltametode-varians med log(−log)-transformasjon (Greenwood-type, samme formel som studiens rev2-00-lib) OG "
  f"perkentil-bootstrap ({B_MAIN} omtrekk av bo innen gruppen, frø {SEED}).")
P()
P("| Grunnlag | horisont | CIF innstilling % | [delta log(−log) 95 %] | [bootstrap 95 %] | CIF ordinær avslutning % | fortsatt uavgjort % | risikomengde | hendelser innen horisont |")
P("|---|---|---:|---:|---:|---:|---:|---:|---:|")
aj = {}; boot = {}; bootq = {}
res["cif"] = {}
for g, m in G.items():
    aj[g] = AJ(t[m], cause[m])
    boot[g], bootq[g] = boot_cif(rng, t[m], cause[m], (H12, H18, H24), B=B_MAIN)
    res["cif"][g] = {}
    for h, lab in ((H12, "12 mnd"), (H18, "18 mnd"), (H24, "24 mnd")):
        F = aj[g].F1(h); lo, hi, se = aj[g].ci(h); blo, bhi = pct_ci(boot[g][h])
        Fk = aj[g].Fcomp(h); S = aj[g].S(h)
        ev = int(((cause == 1) & (t <= h) & m).sum())
        P(f"| {GLAB[g]} | {lab} ({h} d) | **{pct(F,2)}** | {ci_s(lo, hi, 2)} | {ci_s(blo, bhi, 2)} | {pct(Fk,2)} | {pct(S,2)} | {aj[g].at_risk(h)} | {ev} |")
        res["cif"][g][h] = dict(F=F, se=se, loglog=(lo, hi), boot=(blo, bhi), Fcomp=Fk, S=S, at_risk=aj[g].at_risk(h), events=ev, sum=F+Fk+S)
P()
# contrasts
P("### Kontrast begjæring − oppbud (risikodifferanse i CIF, prosentpoeng)")
P()
P("| horisont | CIF begjæring % | CIF oppbud % | RD pp | [Wald, delta 95 %] | [bootstrap 95 %] | z | p | RR | [RR 95 %] |")
P("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
res["cif"]["contrast"] = {}
for h, lab in ((H12, "12 mnd"), (H18, "18 mnd"), (H24, "24 mnd")):
    fB, fO = aj["begjaering"].F1(h), aj["oppbud"].F1(h)
    vB, vO = aj["begjaering"].var(h), aj["oppbud"].var(h)
    rd = fB - fO; se = np.sqrt(vB + vO); z = rd / se
    from scipy import stats as st
    p = 2 * st.norm.sf(abs(z))
    rr = fB / fO; selr = np.sqrt(vB / fB**2 + vO / fO**2)
    bd = boot["begjaering"][h] - boot["oppbud"][h]; blo, bhi = pct_ci(bd)
    P(f"| {lab} | {pct(fB,2)} | {pct(fO,2)} | **{100*rd:+.2f}** | [{100*(rd-Z*se):+.2f}; {100*(rd+Z*se):+.2f}] | [{100*blo:+.2f}; {100*bhi:+.2f}] | {z:.2f} | {p:.1e} | {rr:.3f} | [{np.exp(np.log(rr)-Z*selr):.3f}; {np.exp(np.log(rr)+Z*selr):.3f}] |")
    res["cif"]["contrast"][h] = dict(rd=rd, se=se, wald=(rd-Z*se, rd+Z*se), boot=(blo, bhi), z=z, p=p, rr=rr)
U, V, zg, pg = gray_test(t[~opp], cause[~opp], t[opp], cause[opp])
P()
P(f"**Grays test** (Gray 1988, ρ = 0, subdistribusjonsrisikomengde, H0: CIF_begjæring(t) = CIF_oppbud(t) for alle t): U = {U:.3f}, V = {V:.3f}, z = {zg:.3f}, χ²(1) = {zg*zg:.3f}, p = {pg:.2e}.")
P()
res["cif"]["gray"] = dict(U=U, V=V, z=zg, chi2=zg*zg, p=pg)

# ------------------------------------------------------------------ (d) time to innstilling
P("## (d) Tid til innstilling")
P()
P("To ulike størrelser — de skal aldri blandes:")
P()
P("| Grunnlag | **CIF-basert dager til 50 % innstilt** (Aalen–Johansen-kvantil, sensureringsriktig, konkurrerende hendelse tatt hensyn til) | [testinversjon 95 %] | [bootstrap 95 %] | dager til 60 % | **Rå median blant fullførte innstillinger** (kun bo som ER innstilt; sensureringsbiasert, underdriver) | [bootstrap 95 %] | Q1 / Q3 | n innstilt |")
P("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
res["time"] = {}
for g, m in G.items():
    q50 = aj[g].quantile(0.5); qlo, qhi = aj[g].quantile_ci(0.5); blo, bhi = pct_ci(bootq[g]); q60 = aj[g].quantile(0.6)
    dd = t[m & innstilt]; med = float(np.median(dd)); q1, q3 = np.percentile(dd, [25, 75])
    bm = np.array([np.median(dd[idx]) for idx in boot_indices(rng, len(dd), B_MAIN)]); mlo, mhi = pct_ci(bm)
    P(f"| {GLAB[g]} | **{q50}** | [{qlo}–{qhi}] | [{blo:.0f}–{bhi:.0f}] | {q60} | **{med:.1f}** | [{mlo:.1f}–{mhi:.1f}] | {q1:.0f} / {q3:.0f} | {len(dd)} |")
    res["time"][g] = dict(cif_days50=q50, cif_days50_inv=(qlo, qhi), cif_days50_boot=(blo, bhi), cif_days60=q60,
                          raw_median=med, raw_median_boot=(mlo, mhi), q1=float(q1), q3=float(q3), n=int(len(dd)))
dq = bootq["begjaering"] - bootq["oppbud"]; dlo, dhi = pct_ci(dq)
P(f"| **Differanse begjæring − oppbud** | **{aj['begjaering'].quantile(0.5) - aj['oppbud'].quantile(0.5):+d} dager** | | [{dlo:+.0f}; {dhi:+.0f}] | | {float(np.median(t[~opp & innstilt])) - float(np.median(t[opp & innstilt])):+.1f} dager | | | |")
P()
res["time"]["diff_cif50_boot"] = (dlo, dhi)

# ------------------------------------------------------------------ (e) construction split
P("## (e) Samme splitt innen utførende bygg og anlegg mot øvrige næringer")
P()
nb_opp = int((bygg & opp).sum()); nb = int(bygg.sum()); no_opp = int((~bygg & opp).sum()); no = int((~bygg).sum())
P(f"Byggmerket er reprodusert med studiens klassifikator (åpningsradens trykte etikett → SN2007 via `bransjekart-v3_2026-08-30.json`; utførende = 41.2, 42, 43): "
  f"**{nb} bo** (studien: 1 280), utfall {cb['innstilt']}/{cb['avsluttet']}/{cb['aapen']} (studien: 911/258/111). Øvrige = komplementet, {no} bo (inkl. uoppgitt).")
P()
P(f"Oppbudsandel: bygg **{nb_opp}/{nb} = {pct(nb_opp/nb)} %** {ci_s(*wilson(nb_opp, nb))} mot øvrige **{no_opp}/{no} = {pct(no_opp/no)} %** {ci_s(*wilson(no_opp, no))}; "
  f"differanse {100*(nb_opp/nb - no_opp/no):+.1f} pp [Newcombe {100*newcombe(nb_opp, nb, no_opp, no)[0]:+.1f}; {100*newcombe(nb_opp, nb, no_opp, no)[1]:+.1f}].")
P()
res["e"] = dict(oppbud_share=dict(bygg=(nb_opp, nb), ovrige=(no_opp, no), newcombe=newcombe(nb_opp, nb, no_opp, no)))

cells = {}
P("### Fire celler: grunnlag × næring")
P()
P("| Næring | Grunnlag | n | innstilt as-of | % [Wilson] | n full 730 d | innstilt ≤ 730 d | % [Wilson] | CIF 12 mnd % | CIF 18 mnd % | **CIF 24 mnd %** | [delta 95 %] | [bootstrap 95 %] | CIF-dager til 50 % | rå median (fullførte) |")
P("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
res["e"]["cells"] = {}
for bl, bm in (("bygg", bygg), ("ovrige", ~bygg)):
    for g, m in G.items():
        mm = bm & m; n = int(mm.sum()); k = int((mm & innstilt).sum())
        nf = int((mm & full).sum()); kf = int((mm & full & inn730).sum())
        a = AJ(t[mm], cause[mm]); bt, bq = boot_cif(rng, t[mm], cause[mm], (H24,), B=B_MAIN)
        lo, hi, se = a.ci(H24); blo, bhi = pct_ci(bt[H24])
        cells[(bl, g)] = dict(aj=a, boot24=bt[H24], bootq=bq, n=n, k=k, nf=nf, kf=kf)
        med = float(np.median(t[mm & innstilt]))
        P(f"| {bl} | {g} | {n} | {k} | {pct(k/n)} {ci_s(*wilson(k, n))} | {nf} | {kf} | {pct(kf/nf)} {ci_s(*wilson(kf, nf))} | {pct(a.F1(H12),1)} | {pct(a.F1(H18),1)} | **{pct(a.F1(H24),2)}** | {ci_s(lo, hi, 2)} | {ci_s(blo, bhi, 2)} | {a.quantile(0.5)} | {med:.0f} |")
        res["e"]["cells"][f"{bl}/{g}"] = dict(n=n, innstilt=k, n_full=nf, innstilt730=kf, cif12=a.F1(H12), cif18=a.F1(H18), cif24=a.F1(H24), se24=se, loglog=(lo, hi), boot=(blo, bhi),
                                              cif_days50=a.quantile(0.5), raw_median=med)
P()

def contrast(name, A, Bc, h=H24):
    """RD = A - B at horizon h with delta Wald CI, bootstrap CI, Gray test."""
    fA, fB = A["aj"].F1(h), Bc["aj"].F1(h); se = np.sqrt(A["aj"].var(h) + Bc["aj"].var(h)); rd = fA - fB
    blo, bhi = pct_ci(A["boot24"] - Bc["boot24"])
    return dict(name=name, rd=rd, se=se, wald=(rd - Z*se, rd + Z*se), boot=(blo, bhi), z=rd/se, p=2*st.norm.sf(abs(rd/se)))

P("### Kontraster ved 24 måneder (CIF-risikodifferanse, pp) og Grays test")
P()
P("| Kontrast | innen | RD pp | [Wald delta 95 %] | [bootstrap 95 %] | z | p | Grays z | Grays p | as-of RD pp [Newcombe] | 730-d RD pp [Newcombe] |")
P("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
res["e"]["contrasts"] = {}
def asof_nc(mA, mB):
    kA, nA = int((mA & innstilt).sum()), int(mA.sum()); kB, nB = int((mB & innstilt).sum()), int(mB.sum())
    nc = newcombe(kA, nA, kB, nB); return kA/nA - kB/nB, nc
def f730_nc(mA, mB):
    kA, nA = int((mA & full & inn730).sum()), int((mA & full).sum()); kB, nB = int((mB & full & inn730).sum()), int((mB & full).sum())
    nc = newcombe(kA, nA, kB, nB); return kA/nA - kB/nB, nc
for name, (A, Bc, mA, mB, within) in {
    "bygg − øvrige": (cells[("bygg", "oppbud")], cells[("ovrige", "oppbud")], bygg & opp, ~bygg & opp, "oppbud"),
    "bygg − øvrige ": (cells[("bygg", "begjaering")], cells[("ovrige", "begjaering")], bygg & ~opp, ~bygg & ~opp, "begjæring"),
    "begjæring − oppbud": (cells[("bygg", "begjaering")], cells[("bygg", "oppbud")], bygg & ~opp, bygg & opp, "bygg"),
    "begjæring − oppbud ": (cells[("ovrige", "begjaering")], cells[("ovrige", "oppbud")], ~bygg & ~opp, ~bygg & opp, "øvrige"),
}.items():
    c = contrast(name, A, Bc); _, _, gz, gp = gray_test(t[mA], cause[mA], t[mB], cause[mB])
    ad, anc = asof_nc(mA, mB); fd, fnc = f730_nc(mA, mB)
    P(f"| {name.strip()} | {within} | **{100*c['rd']:+.2f}** | [{100*c['wald'][0]:+.2f}; {100*c['wald'][1]:+.2f}] | [{100*c['boot'][0]:+.2f}; {100*c['boot'][1]:+.2f}] | {c['z']:.2f} | {c['p']:.1e} | {gz:.2f} | {gp:.1e} | {100*ad:+.1f} [{100*anc[0]:+.1f}; {100*anc[1]:+.1f}] | {100*fd:+.1f} [{100*fnc[0]:+.1f}; {100*fnc[1]:+.1f}] |")
    res["e"]["contrasts"][f"{name.strip()} within {within}"] = dict(rd24=c["rd"], wald=c["wald"], boot=c["boot"], z=c["z"], p=c["p"], gray_z=gz, gray_p=gp, asof_rd=ad, asof_newcombe=anc, f730_rd=fd, f730_newcombe=fnc)
P()
# overall bygg - øvrige for reference (DB data)
cB = AJ(t[bygg], cause[bygg]); cO = AJ(t[~bygg], cause[~bygg])
rdBO = cB.F1(H24) - cO.F1(H24); seBO = np.sqrt(cB.var(H24) + cO.var(H24))
P(f"Referanse (samme data, uten grunnlagssplitt): bygg {pct(cB.F1(H24),2)} % mot øvrige {pct(cO.F1(H24),2)} % ved 24 mnd, RD {100*rdBO:+.2f} pp [{100*(rdBO-Z*seBO):+.2f}; {100*(rdBO+Z*seBO):+.2f}] (studien I2b: −5,70 [−8,56; −2,83]).")
P()
res["e"]["bygg_vs_ovrige_total"] = dict(cif_bygg=cB.F1(H24), cif_ovrige=cO.F1(H24), rd=rdBO, wald=(rdBO-Z*seBO, rdBO+Z*seBO))

# interaction: difference of differences with bootstrap; and standardization
dd_boot = (cells[("bygg", "oppbud")]["boot24"] - cells[("ovrige", "oppbud")]["boot24"]) - (cells[("bygg", "begjaering")]["boot24"] - cells[("ovrige", "begjaering")]["boot24"])
dd = (cells[("bygg", "oppbud")]["aj"].F1(H24) - cells[("ovrige", "oppbud")]["aj"].F1(H24)) - (cells[("bygg", "begjaering")]["aj"].F1(H24) - cells[("ovrige", "begjaering")]["aj"].F1(H24))
ddlo, ddhi = pct_ci(dd_boot)
# standardization: bygg CIF24 if bygg had øvrige's basis mix
w_opp_o = no_opp / no
std_bygg = w_opp_o * cells[("bygg", "oppbud")]["aj"].F1(H24) + (1 - w_opp_o) * cells[("bygg", "begjaering")]["aj"].F1(H24)
std_boot = w_opp_o * cells[("bygg", "oppbud")]["boot24"] + (1 - w_opp_o) * cells[("bygg", "begjaering")]["boot24"] - cO.F1(H24)
# bootstrap for øvrige total too — approximate: use fixed cO (its se small); report composition-adjusted gap
P("### Interaksjon og standardisering")
P()
P(f"- **Forskjell i forskjeller** (byggfordel innen oppbud minus byggfordel innen begjæring, CIF 24 mnd): **{100*dd:+.2f} pp** [bootstrap {100*ddlo:+.2f}; {100*ddhi:+.2f}].")
P(f"- **Sammensetningsjustert byggfordel**: gir vi bygg samme oppbudsandel som øvrige ({pct(w_opp_o)} %), blir byggs 24-mnd CIF {pct(std_bygg,2)} % mot øvrige {pct(cO.F1(H24),2)} % — justert RD **{100*(std_bygg - cO.F1(H24)):+.2f} pp** (ujustert {100*rdBO:+.2f} pp). Andelen av byggfordelen som skyldes ulik oppbudsandel: {100*(1 - (std_bygg - cO.F1(H24))/rdBO):.0f} %.")
P()
res["e"]["interaction"] = dict(dd=dd, dd_boot=(ddlo, ddhi), std_bygg_cif24=std_bygg, adj_rd=std_bygg - cO.F1(H24), unadj_rd=rdBO, w_opp_ovrige=w_opp_o)

# logistic regression with interaction (as-of and 730d)
def design(mask, inter=False, courts=True):
    cols = [np.ones(mask.sum()), (~opp[mask]).astype(float), bygg[mask].astype(float)]
    names = ["intercept", "begjaering", "bygg"]
    if inter:
        cols.append(((~opp[mask]) & bygg[mask]).astype(float)); names.append("begjaering×bygg")
    if courts:
        levels = sorted(set(court)); levels.remove("OSLO TINGRETT")
        for L in levels:
            cols.append((court[mask] == L).astype(float)); names.append("court:" + L)
    return np.column_stack(cols), names
P("### Logistisk regresjon (IRLS, egen implementasjon) — innstilt ~ begjæring + bygg (+ interaksjon) + rettskrets (22 dummyer, ref. Oslo)")
P()
P("| Modell | vindu | n | OR begjæring [95 %] | p | OR bygg [95 %] | p | OR interaksjon begjæring×bygg [95 %] | p |")
P("|---|---|---:|---:|---:|---:|---:|---:|---:|")
res["e"]["logit"] = {}
allm = np.ones(N, bool)
for lab, mask, y in (("as-of 24.08.2026 (alle 5 165; ulik oppfølging 601–1 088 d)", allm, innstilt.astype(float)),
                     ("fast 730 d (delkohort åpnet ≤ 24.08.2024)", full, inn730.astype(float))):
    for inter in (False, True):
        X, names = design(mask, inter=inter)
        b, cov, ll = logit_fit(X, y[mask])
        o1 = or_ci(b, cov, 1); o2 = or_ci(b, cov, 2)
        s = f"| {'med' if inter else 'uten'} interaksjon, krets-justert | {lab} | {int(mask.sum())} | {o1[0]:.3f} [{o1[1]:.3f}; {o1[2]:.3f}] | {o1[4]:.1e} | {o2[0]:.3f} [{o2[1]:.3f}; {o2[2]:.3f}] | {o2[4]:.1e} |"
        if inter:
            o3 = or_ci(b, cov, 3); s += f" {o3[0]:.3f} [{o3[1]:.3f}; {o3[2]:.3f}] | {o3[4]:.2f} |"
        else:
            s += " — | — |"
        P(s)
        res["e"]["logit"][f"{lab} inter={inter}"] = dict(n=int(mask.sum()), begjaering=o1, bygg=o2, inter=(or_ci(b, cov, 3) if inter else None))
    # crude (no courts)
    X, names = design(mask, inter=False, courts=False); b, cov, ll = logit_fit(X, y[mask]); o1 = or_ci(b, cov, 1); o2 = or_ci(b, cov, 2)
    P(f"| uten interaksjon, IKKE krets-justert | {lab} | {int(mask.sum())} | {o1[0]:.3f} [{o1[1]:.3f}; {o1[2]:.3f}] | {o1[4]:.1e} | {o2[0]:.3f} [{o2[1]:.3f}; {o2[2]:.3f}] | {o2[4]:.1e} | — | — |")
    res["e"]["logit"][f"{lab} crude"] = dict(begjaering=o1, bygg=o2)
P()

# ------------------------------------------------------------------ (f) courts
P("## (f) Etter rettskrets — de 10 største tingrettene (åpningsradens tingrettsnavn; 23 kretser i kohortvinduet)")
P()
courts_n = collections.Counter(court)
top10 = [c for c, _ in courts_n.most_common(10)]
P("| Tingrett | n | oppbud n (%) | as-of innstilt oppbud % | as-of innstilt begjæring % | as-of RD pp [Newcombe] | 730-d innstilt oppbud (k/n) | 730-d begjæring (k/n) | CIF 24 mnd oppbud % [delta] | CIF 24 mnd begjæring % [delta] | **RD 24 mnd pp** [delta Wald] | [bootstrap] | Grays p | CIF-dager til 50 % oppbud / begjæring |")
P("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
res["courts"] = {}
court_strata_asof = []; court_strata_730 = []; gray_groups = []; rd_est = []; rd_var = []; court_rd_rows = []
for c in sorted(courts_n, key=lambda x: -courts_n[x]):
    mc = court == c; mo = mc & opp; mb = mc & ~opp
    n = int(mc.sum()); no_ = int(mo.sum()); nb_ = int(mb.sum())
    ko, kb = int((mo & innstilt).sum()), int((mb & innstilt).sum())
    court_strata_asof.append((kb, nb_ - kb, ko, no_ - ko))
    fo_n, fo_k = int((mo & full).sum()), int((mo & full & inn730).sum()); fb_n, fb_k = int((mb & full).sum()), int((mb & full & inn730).sum())
    court_strata_730.append((fb_k, fb_n - fb_k, fo_k, fo_n - fo_k))
    gray_groups.append((t[mb], cause[mb], t[mo], cause[mo]))
    ao = AJ(t[mo], cause[mo]); ab = AJ(t[mb], cause[mb])
    Fo, Fb = ao.F1(H24), ab.F1(H24); vo, vb = ao.var(H24), ab.var(H24)
    rd = Fb - Fo; se = np.sqrt(vo + vb)
    if no_ >= 10 and nb_ >= 10 and 0 < Fo < 1 and 0 < Fb < 1:
        rd_est.append(rd); rd_var.append(vo + vb)
    entry = dict(n=n, n_oppbud=no_, n_begj=nb_, asof_opp=(ko, no_), asof_begj=(kb, nb_), f730_opp=(fo_k, fo_n), f730_begj=(fb_k, fb_n),
                 cif24_opp=Fo, cif24_begj=Fb, rd24=rd, se=se, days50_opp=ao.quantile(0.5), days50_begj=ab.quantile(0.5))
    if c in top10:
        _, _, gz, gp = gray_test(t[mb], cause[mb], t[mo], cause[mo])
        bo_, _ = boot_cif(rng, t[mo], cause[mo], (H24,), B=B_COURT); bb_, _ = boot_cif(rng, t[mb], cause[mb], (H24,), B=B_COURT)
        blo, bhi = pct_ci(bb_[H24] - bo_[H24])
        ad, anc = asof_nc(mb, mo)
        lo_o, hi_o, _ = ao.ci(H24); lo_b, hi_b, _ = ab.ci(H24)
        P(f"| {c} | {n} | {no_} ({pct(no_/n)}) | {pct(ko/no_)} ({ko}/{no_}) | {pct(kb/nb_)} ({kb}/{nb_}) | {100*ad:+.1f} [{100*anc[0]:+.1f}; {100*anc[1]:+.1f}] | {pct(fo_k/fo_n)} ({fo_k}/{fo_n}) | {pct(fb_k/fb_n)} ({fb_k}/{fb_n}) | {pct(Fo)} {ci_s(lo_o, hi_o)} | {pct(Fb)} {ci_s(lo_b, hi_b)} | **{100*rd:+.1f}** [{100*(rd-Z*se):+.1f}; {100*(rd+Z*se):+.1f}] | [{100*blo:+.1f}; {100*bhi:+.1f}] | {gp:.3f} | {ao.quantile(0.5)} / {ab.quantile(0.5)} |")
        entry.update(gray_z=gz, gray_p=gp, boot=(blo, bhi), asof_rd=ad, asof_newcombe=anc)
    res["courts"][c] = entry
P()
# pooled / stratified
Us, Vs, zs, ps, used = gray_stratified(gray_groups)
orA, loA, hiA = mh_or(court_strata_asof); or7, lo7, hi7 = mh_or(court_strata_730)
rdA = pooled_rd([(a, a + b, c_, c_ + d_) for (a, b, c_, d_) in court_strata_asof])
rd7 = pooled_rd([(a, a + b, c_, c_ + d_) for (a, b, c_, d_) in court_strata_730])
ivrd = iv_pooled(rd_est, rd_var)
# Cochran Q heterogeneity for the 24 m RDs
w = 1 / np.asarray(rd_var); Q = float(np.sum(w * (np.asarray(rd_est) - ivrd[0]) ** 2)); dfQ = len(rd_est) - 1; pQ = st.chi2.sf(Q, dfQ)
P("### Overlever begjæringseffekten innen rettskretsene? (alle 23 kretser som strata)")
P()
P("| Metode | vindu | estimat begjæring vs oppbud | 95 % | p |")
P("|---|---|---:|---:|---:|")
P(f"| Grays test stratifisert på rettskrets (ΣU/√ΣV, {used} strata) | AJ-kurver | z = {zs:.3f} | | {ps:.2e} |")
P(f"| Inverse-varians-poolet CIF-risikodifferanse ved 24 mnd ({len(rd_est)} kretser med ≥ 10 bo i hver gruppe) | fast 730 d, AJ | {100*ivrd[0]:+.2f} pp | [{100*ivrd[1]:+.2f}; {100*ivrd[2]:+.2f}] | Cochran Q = {Q:.1f}, df = {dfQ}, p_het = {pQ:.2f} |")
P(f"| Mantel–Haenszel OR (RBG-varians) | as-of | {orA:.3f} | [{loA:.3f}; {hiA:.3f}] | |")
P(f"| Mantel–Haenszel OR (RBG-varians) | fast 730 d, delkohort | {or7:.3f} | [{lo7:.3f}; {hi7:.3f}] | |")
P(f"| Cochran–MH-vektet risikodifferanse | as-of | {100*rdA[0]:+.2f} pp | [{100*rdA[1]:+.2f}; {100*rdA[2]:+.2f}] | |")
P(f"| Cochran–MH-vektet risikodifferanse | fast 730 d, delkohort | {100*rd7[0]:+.2f} pp | [{100*rd7[1]:+.2f}; {100*rd7[2]:+.2f}] | |")
P()
res["courts_pooled"] = dict(gray_strat=dict(z=zs, p=ps, strata=used), iv_rd24=ivrd, Q=Q, dfQ=dfQ, pQ=pQ, mh_or_asof=(orA, loA, hiA), mh_or_730=(or7, lo7, hi7), rd_asof=rdA, rd_730=rd7)
# sign count
signs = sum(1 for c in res["courts"] if res["courts"][c]["rd24"] > 0)
P(f"Fortegn: begjæringsboene har høyere 24-mnd CIF enn oppbudsboene i **{signs} av 23** kretser (as-of-andel: {sum(1 for (a,b,c_,d_) in court_strata_asof if a/(a+b) > c_/(c_+d_))} av 23).")
P()
res["courts_pooled"]["sign_positive"] = signs

# construction within courts, stratified by basis: does the construction advantage survive within courts AND within basis?
P("### Byggfordelen innen rettskrets, per grunnlag (Grays test stratifisert på rettskrets)")
P()
P("| Delmengde | bygg n | øvrige n | Grays z (stratifisert på krets) | p | ustratifisert Grays z | p |")
P("|---|---:|---:|---:|---:|---:|---:|")
res["e"]["bygg_within_courts"] = {}
for lab, base in (("innen oppbud", opp), ("innen begjæring", ~opp), ("alle grunnlag", np.ones(N, bool))):
    groups = []
    for c in courts_n:
        mc = (court == c) & base
        groups.append((t[mc & bygg], cause[mc & bygg], t[mc & ~bygg], cause[mc & ~bygg]))
    Us_, Vs_, zs_, ps_, used_ = gray_stratified(groups)
    _, _, zu, pu = gray_test(t[base & bygg], cause[base & bygg], t[base & ~bygg], cause[base & ~bygg])
    P(f"| {lab} | {int((base & bygg).sum())} | {int((base & ~bygg).sum())} | {zs_:.3f} | {ps_:.2e} | {zu:.3f} | {pu:.2e} |")
    res["e"]["bygg_within_courts"][lab] = dict(z_strat=zs_, p_strat=ps_, z=zu, p=pu)
P()

# ------------------------------------------------------------------ write
json.dump(res, open(f"{W}/B1-results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
open(f"{W}/B1-tables.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
print("written B1-results.json, B1-tables.md")
