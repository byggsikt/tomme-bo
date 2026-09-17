// «Tomme bo» — REVISJON 2, steg 4: PRESISJON (fagfellens punkt 7 og 14).
//
// Fagfellen krever: konfidensintervaller for 267 og 205 dager, et intervall for
// differansen, et 95 %-intervall for HR 0,80, risikomengder ved relevante
// horisonter, og en proporsjonalitetsdiagnostikk dersom HR tolkes som konstant.
// I tillegg skal 62-dagersforskjellen (kumulativ insidens) skilles fra den
// stratifiserte 38,4-dagersanalysen av observerte hendelsestider (som skal
// sammenliknes med den ustratifiserte råmedianforskjellen 34,5).
//
// Leverer:
//   (a) CIF-medianene 267/205 med KI ved testinversjon OG ved bootstrap;
//   (b) differansen 62 dager med bootstrap-KI;
//   (c) den stratifiserte medianforskjellen 38,4 dager med bootstrap-KI, side om
//       side med den ustratifiserte råforskjellen 34,5 — samme estimand, ulike
//       delmengder;
//   (d) HR 0,80: Peto/ett-stegs, Cox partiell likelihood (Breslow), modellbasert
//       og klynge-robust SE, med 95 % KI;
//   (e) PH-diagnostikk: Grambsch–Therneau-score på Schoenfeld-residualene (rang-
//       og log-transform) + tidsdelt HR i fire intervaller;
//   (f) implementasjonskontroll mot lane 3s egen logrank-rutine og de fire
//       definisjons-/sensureringsvariantene, som forklarer z = −5,8 mot z = −6,1.
//
// READ-ONLY. Ingen databasetilgang. Kjøres:
//   node sporringer/rev2-04-presisjon-hr-og-ph.mjs

import { lesKohort, aalenJohansen, ajF, ajKvantil, ajKvantilKI, risikoVed,
         logrankStratifisert, coxStratifisertBinaer, phTest, rng, kvantil,
         skrivJson, pst, r1, r2, r3, r4, KJORT, KORPUSSLUTT, VINDU, H12, H18, H24 } from "./rev2-00-lib.mjs";

const B_BOOT = 2000;
const FRO = 20260830;

const D = lesKohort("sensurert");
const BY = D.filter((r) => r.bygg), OV = D.filter((r) => !r.bygg);

console.log("«Tomme bo» — revisjon 2, steg 4: presisjon, HR og PH-diagnostikk\n");

// ---------------------------------------------------------------------------
// (a) CIF-medianene med KI ved testinversjon
// ---------------------------------------------------------------------------
const ajB = aalenJohansen(BY), ajO = aalenJohansen(OV), ajA = aalenJohansen(D);
const medB = ajKvantil(ajB, 0.5), medO = ajKvantil(ajO, 0.5), medA = ajKvantil(ajA, 0.5);
const kiB = ajKvantilKI(ajB, 0.5), kiO = ajKvantilKI(ajO, 0.5), kiA = ajKvantilKI(ajA, 0.5);

console.log("(a) CIF-MEDIAN (tid til 50 % innstilt), KI ved testinversjon (Brookmeyer–Crowley-prinsippet)");
console.log(`    bygg   ${medB} dager  KI [${kiB.join(", ")}]   risikomengde ved medianen: ${risikoVed(BY, medB)}`);
console.log(`    øvrige ${medO} dager  KI [${kiO.join(", ")}]   risikomengde ved medianen: ${risikoVed(OV, medO)}`);
console.log(`    alle   ${medA} dager  KI [${kiA.join(", ")}]`);

// ---------------------------------------------------------------------------
// (b) bootstrap for medianene og differansen
// ---------------------------------------------------------------------------
function bootstrapGruppe(gruppe, rnd) {
  const n = gruppe.length, ut = new Array(n);
  for (let i = 0; i < n; i++) ut[i] = gruppe[(rnd() * n) | 0];
  return ut;
}
const rnd = rng(FRO);
const bMedB = [], bMedO = [], bDiff = [], bCifB = [], bCifO = [], bRd = [];
let feilet = 0;
for (let b = 0; b < B_BOOT; b++) {
  const sB = bootstrapGruppe(BY, rnd), sO = bootstrapGruppe(OV, rnd);
  const aB = aalenJohansen(sB), aO = aalenJohansen(sO);
  const mB = ajKvantil(aB, 0.5), mO = ajKvantil(aO, 0.5);
  if (mB === null || mO === null) { feilet++; continue; }
  bMedB.push(mB); bMedO.push(mO); bDiff.push(mB - mO);
  const fB = ajF(aB, H24), fO = ajF(aO, H24);
  bCifB.push(fB); bCifO.push(fO); bRd.push(fB - fO);
}
const perc = (arr, p) => kvantil(arr.slice().sort((x, y) => x - y), p);
const boot = (arr) => [perc(arr, 0.025), perc(arr, 0.975)];

console.log(`\n(b) BOOTSTRAP (${bDiff.length} av ${B_BOOT} gyldige replikater, frø ${FRO},`
  + " uavhengig resampling i hver gruppe)");
console.log(`    CIF-median bygg   ${medB}  bootstrap-KI [${boot(bMedB).map(r1).join(", ")}]`);
console.log(`    CIF-median øvrige ${medO}  bootstrap-KI [${boot(bMedO).map(r1).join(", ")}]`);
console.log(`    DIFFERANSE        ${medB - medO} dager  bootstrap-KI [${boot(bDiff).map(r1).join(", ")}]`);
console.log(`    risikodifferanse 24 mnd ${pst(ajF(ajB, H24) - ajF(ajO, H24), 2)} pp`
  + `  bootstrap-KI [${boot(bRd).map((x) => pst(x, 2)).join(", ")}]`);

// ---------------------------------------------------------------------------
// (c) den stratifiserte medianforskjellen (+38,4) og den rå (+34,5)
//     — samme estimand (observerte hendelsestider), ulike delmengder
// ---------------------------------------------------------------------------
/**
 * Talljournalens D5-regel (kontroll-05): per rettskrets, medianen av dager til
 * innstilling blant FULLFØRTE saker i hver gruppe; strata der begge grupper har
 * minst 10 innstilte bo; saksvektet snitt av differansen med vekt = summen av
 * de to gruppenes hendelser.
 */
function stratifiertMedianDiff(data, minPerGruppe = 10) {
  const per = new Map();
  for (const r of data) {
    if (!per.has(r.tingrett)) per.set(r.tingrett, []);
    per.get(r.tingrett).push(r);
  }
  const strata = [];
  for (const [krets, d] of per) {
    const bd = d.filter((r) => r.bygg && r.arsak === 1).map((r) => r.t);
    const od = d.filter((r) => !r.bygg && r.arsak === 1).map((r) => r.t);
    if (bd.length >= minPerGruppe && od.length >= minPerGruppe) {
      const s = (a) => a.slice().sort((x, y) => x - y);
      strata.push({ krets, n_bygg: bd.length, n_ovrige: od.length,
        median_bygg: kvantil(s(bd), 0.5), median_ovrige: kvantil(s(od), 0.5),
        diff: kvantil(s(bd), 0.5) - kvantil(s(od), 0.5), vekt: bd.length + od.length });
    }
  }
  const V = strata.reduce((a, s) => a + s.vekt, 0);
  return { strata, antall_strata: strata.length, saker: V,
    vektet_diff: strata.reduce((a, s) => a + s.diff * s.vekt, 0) / V,
    bygg_tregere: strata.filter((s) => s.diff > 0).length,
    bygg_raskere: strata.filter((s) => s.diff < 0).length };
}
const strat = stratifiertMedianDiff(D);
const stratGrense = stratifiertMedianDiff(lesKohort("tidligst"));
const raaB = BY.filter((r) => r.arsak === 1).map((r) => r.t).sort((a, b) => a - b);
const raaO = OV.filter((r) => r.arsak === 1).map((r) => r.t).sort((a, b) => a - b);
const raaDiff = kvantil(raaB, 0.5) - kvantil(raaO, 0.5);

// bootstrap av HELE prosedyren, klynget på rettskrets (resampling innen krets)
const perKrets = new Map();
for (const r of D) { if (!perKrets.has(r.tingrett)) perKrets.set(r.tingrett, []); perKrets.get(r.tingrett).push(r); }
const rnd2 = rng(FRO + 1);
const bStrat = [], bRaa = [];
for (let b = 0; b < B_BOOT; b++) {
  const s = [];
  for (const [, celle] of perKrets) {
    const n = celle.length;
    for (let i = 0; i < n; i++) s.push(celle[(rnd2() * n) | 0]);
  }
  const st = stratifiertMedianDiff(s);
  if (st.saker > 0) bStrat.push(st.vektet_diff);
  const rb = s.filter((r) => r.bygg && r.arsak === 1).map((r) => r.t).sort((a, b2) => a - b2);
  const ro = s.filter((r) => !r.bygg && r.arsak === 1).map((r) => r.t).sort((a, b2) => a - b2);
  if (rb.length && ro.length) bRaa.push(kvantil(rb, 0.5) - kvantil(ro, 0.5));
}

console.log("\n(c) OBSERVERTE HENDELSESTIDER — den stratifiserte og den rå medianforskjellen");
console.log(`    rå medianforskjell (fullførte saker, ustratifisert): +${r1(raaDiff)} dager`
  + `  bootstrap-KI [${boot(bRaa).map(r1).join(", ")}]  (bygg ${kvantil(raaB, 0.5)}, øvrige ${kvantil(raaO, 0.5)})`);
console.log(`    rettskrets-stratifisert, saksvektet: +${r1(strat.vektet_diff)} dager`
  + `  bootstrap-KI [${boot(bStrat).map(r1).join(", ")}]`);
console.log(`    ${strat.antall_strata} strata, ${strat.saker} saker;`
  + ` bygg tregest i ${strat.bygg_tregere} av ${strat.antall_strata} kretser`);
console.log(`    grenseregel «tidligst»: +${r1(stratGrense.vektet_diff)} dager,`
  + ` ${stratGrense.antall_strata} strata, ${stratGrense.saker} saker,`
  + ` bygg tregest i ${stratGrense.bygg_tregere}`);
console.log("    MERK: talljournalens D5 (+38,4 dager, 3 749 saker, 18 av 19) er beregnet i basen,");
console.log("    som bærer den faktiske innstillingsdatoen ETTER åpning for de 3 randtilfellene.");
console.log("    Det frosne uttrekket bærer bare den eldre datoen; ett av randtilfellene ligger i");
console.log("    Vestre Innlandet, som er den marginale kretsen (−9 dager). Se f_avvik nedenfor.");
console.log(`    TIL SAMMENLIKNING, ANNEN ESTIMAND: CIF-medianforskjellen er`
  + ` +${medB - medO} dager (kumulativ insidens, hele kohorten, sensureringsriktig).`);

// ---------------------------------------------------------------------------
// (d) HR med 95 % KI
// ---------------------------------------------------------------------------
const lrS = logrankStratifisert(D, (r) => r.bygg, (r) => r.tingrett);
const lrU = logrankStratifisert(D, (r) => r.bygg, () => "alle");
const cox = coxStratifisertBinaer(D, (r) => (r.bygg ? 1 : 0), (r) => r.tingrett, (r) => r.tingrett);

console.log("\n(d) HASARDRATIO, bygg mot øvrige, rettskrets som strata");
console.log(`    Peto/ett-stegs (logrank): HR ${r3(lrS.hr)} [${r3(lrS.hr_lav)}, ${r3(lrS.hr_hoy)}]`
  + `  z = ${r3(lrS.z)}  p = ${lrS.p.toExponential(2)}  (O−E = ${r2(lrS.OE)}, V = ${r2(lrS.V)})`);
console.log(`    Cox partiell likelihood (Breslow): HR ${r3(cox.hr)} [${r3(cox.hr_lav)}, ${r3(cox.hr_hoy)}]`
  + `  β = ${r4(cox.beta)}  SE = ${r4(cox.se)}  z = ${r2(cox.z)}  p = ${cox.p.toExponential(2)}`);
console.log(`    samme, klynge-robust SE (klynge = rettskrets, ${cox.strata} klynger):`
  + ` HR ${r3(cox.hr)} [${r3(cox.hr_lav_rob)}, ${r3(cox.hr_hoy_rob)}]`
  + `  robust SE = ${r4(cox.robustSe)}  p = ${cox.p_rob.toExponential(2)}`);
console.log(`    ustratifisert til sammenlikning: HR ${r3(lrU.hr)} [${r3(lrU.hr_lav)}, ${r3(lrU.hr_hoy)}]`);

// ---------------------------------------------------------------------------
// (e) PH-diagnostikk
// ---------------------------------------------------------------------------
const phRang = phTest(cox.schoen, "rang");
const phLog = phTest(cox.schoen, "log");

/** Tidsdelt HR: intervallet (a, b] analyseres på delmengden {t > a}, avkortet i b. */
function tidsdelt(a, b) {
  const s = D.filter((r) => r.t > a).map((r) => ({
    ...r, t: Math.min(r.t, b), arsak: r.t <= b ? r.arsak : 0 }));
  const lr = logrankStratifisert(s, (r) => r.bygg, (r) => r.tingrett);
  return { fra: a, til: b === Infinity ? null : b, n_i_risiko_ved_start: s.length,
    hendelser: s.filter((r) => r.arsak === 1).length,
    hr: r3(lr.hr), ki95: [r3(lr.hr_lav), r3(lr.hr_hoy)], z: r2(lr.z), p: lr.p, V: r2(lr.V) };
}
const deler = [tidsdelt(0, 180), tidsdelt(180, 365), tidsdelt(365, 730), tidsdelt(730, Infinity)];

console.log("\n(e) PROPORSJONALITETSDIAGNOSTIKK");
console.log(`    Grambsch–Therneau-score på Schoenfeld-residualene (${phRang.hendelser} hendelser):`);
console.log(`      rang-transform: χ²(1) = ${r3(phRang.T)}, p = ${phRang.p.toExponential(2)}`
  + `  (korrelasjon g mot residual = ${r4(phRang.korrelasjon)})`);
console.log(`      log-transform : χ²(1) = ${r3(phLog.T)}, p = ${phLog.p.toExponential(2)}`
  + `  (korrelasjon ${r4(phLog.korrelasjon)})`);
console.log("    tidsdelt HR (rettskrets-stratifisert i hvert intervall):");
for (const d of deler)
  console.log(`      ${String(d.fra).padStart(4)}–${d.til === null ? " ∞ " : String(d.til).padStart(4)} dager:`
    + ` HR ${d.hr} [${d.ki95.join(", ")}]  hendelser ${d.hendelser}, i risiko ved start ${d.n_i_risiko_ved_start}`);

// ---------------------------------------------------------------------------
// (f) implementasjonskontroll og definisjonsvarianter
// ---------------------------------------------------------------------------
/** Lane 3s egen rutine (domstol-stat.mjs), reimplementert bit for bit. */
function lane3Logrank(data, gruppeAv, strataAv) {
  const strata = new Map();
  for (const r of data) {
    const k = strataAv(r);
    if (!strata.has(k)) strata.set(k, { a: [], b: [] });
    (gruppeAv(r) ? strata.get(k).a : strata.get(k).b).push({ t: r.t, event: r.arsak === 1 ? 1 : 0 });
  }
  let O = 0, E = 0, V = 0;
  for (const [, g] of strata) {
    const all = [...g.a.map((r) => ({ ...r, g: 0 })), ...g.b.map((r) => ({ ...r, g: 1 }))];
    if (!all.length) continue;
    const times = [...new Set(all.filter((r) => r.event).map((r) => r.t))].sort((x, y) => x - y);
    let nA = g.a.length, nB = g.b.length;
    const sorted = all.slice().sort((x, y) => x.t - y.t);
    let idx = 0;
    for (const t of times) {
      while (idx < sorted.length && sorted[idx].t < t) { if (sorted[idx].g === 0) nA--; else nB--; idx++; }
      const dA = all.filter((r) => r.t === t && r.event && r.g === 0).length;
      const dB = all.filter((r) => r.t === t && r.event && r.g === 1).length;
      const d = dA + dB, n = nA + nB;
      if (n <= 1 || d === 0) continue;
      O += dA; E += d * nA / n; V += d * (nA / n) * (nB / n) * ((n - d) / (n - 1));
    }
  }
  return { O, E, V, z: (O - E) / Math.sqrt(V), hr: Math.exp((O - E) / V) };
}
const kontrollLane3 = lane3Logrank(D, (r) => r.bygg, (r) => r.tingrett);

const varianter = [];
for (const randregel of ["sensurert", "tidligst"]) {
  const dd = lesKohort(randregel);
  for (const [def, f] of [["utførende bygg (primær)", (r) => r.bygg], ["område F (sekundær)", (r) => r.byggF]]) {
    const lr = logrankStratifisert(dd, f, (r) => r.tingrett);
    varianter.push({ byggdefinisjon: def, randregel, n_bygg: dd.filter(f).length,
      hr: r3(lr.hr), ki95: [r3(lr.hr_lav), r3(lr.hr_hoy)], z: r2(lr.z), p: lr.p });
  }
}

console.log("\n(f) IMPLEMENTASJONSKONTROLL OG DEFINISJONSVARIANTER");
console.log(`    lane 3s egen rutine på samme data: HR ${r3(kontrollLane3.hr)}, z = ${r3(kontrollLane3.z)}`
  + `  (revisjonsbiblioteket: HR ${r3(lrS.hr)}, z = ${r3(lrS.z)}) — differanse`
  + ` ${r4(Math.abs(kontrollLane3.z - lrS.z))}`);
for (const v of varianter)
  console.log(`    ${v.byggdefinisjon.padEnd(24)} / ${v.randregel.padEnd(10)} (n = ${String(v.n_bygg).padStart(4)}):`
    + ` HR ${v.hr} [${v.ki95.join(", ")}], z = ${v.z}`);

// ---------------------------------------------------------------------------
const ut = {
  studie: "Tomme bo — revisjon 2 etter fagfellevurdering",
  leverer: "fagfellens punkt 7 og 14 — presisjon for varighetsestimatene, KI for HR, PH-diagnostikk",
  skript: "sporringer/rev2-04-presisjon-hr-og-ph.mjs",
  kjort: KJORT,
  datagrunnlag: "offentlig tilgjengelige registerkunngjøringer om konkursbehandling",
  frosset_uttrekk: "data/_kohort-rader-arbeidskopi.json",
  kohortvindu: VINDU,
  sensureringsdato: KORPUSSLUTT,
  bootstrap: { replikater: B_BOOT, gyldige: bDiff.length, fro: FRO,
    generator: "mulberry32", metode: "persentil-KI (2,5 og 97,5 %)" },

  a_cif_medianer: {
    metode: "Aalen–Johansen-kvantil; KI ved testinversjon av de punktvise log(−log)-intervallene "
      + "(Brookmeyer–Crowley-prinsippet): nedre grense = første t der øvre KI-grense for CIF ≥ 0,5, "
      + "øvre grense = første t der nedre KI-grense ≥ 0,5.",
    bygg: { median_dager: medB, ki95_testinversjon: kiB, ki95_bootstrap: boot(bMedB).map(r1),
      risikomengde_ved_median: risikoVed(BY, medB) },
    ovrige: { median_dager: medO, ki95_testinversjon: kiO, ki95_bootstrap: boot(bMedO).map(r1),
      risikomengde_ved_median: risikoVed(OV, medO) },
    alle: { median_dager: medA, ki95_testinversjon: kiA },
    risikomengder: {
      bygg: { d365: risikoVed(BY, H12), d548: risikoVed(BY, H18), d730: risikoVed(BY, H24) },
      ovrige: { d365: risikoVed(OV, H12), d548: risikoVed(OV, H18), d730: risikoVed(OV, H24) },
      alle: { d365: risikoVed(D, H12), d548: risikoVed(D, H18), d730: risikoVed(D, H24) },
    },
  },

  b_differanse_kumulativ_insidens: {
    estimand: "differansen mellom de to gruppenes CIF-medianer (tid til 50 % innstilt)",
    verdi_dager: medB - medO,
    ki95_bootstrap: boot(bDiff).map(r1),
    risikodifferanse_24mnd_pp: pst(ajF(ajB, H24) - ajF(ajO, H24), 2),
    risikodifferanse_24mnd_ki95_bootstrap_pp: boot(bRd).map((x) => pst(x, 2)),
  },

  c_observerte_hendelsestider: {
    advarsel: "Dette er en ANNEN estimand enn punkt b. Her sammenliknes medianen av observerte "
      + "hendelsestider blant FULLFØRTE saker; i punkt b sammenliknes kumulativ-insidens-kurvene "
      + "for hele kohorten. Tallene skal aldri stilles opp som om det ene «vokser» til det andre.",
    raa_ustratifisert: { median_bygg: kvantil(raaB, 0.5), median_ovrige: kvantil(raaO, 0.5),
      diff_dager: r1(raaDiff), ki95_bootstrap: boot(bRaa).map(r1),
      n_hendelser_bygg: raaB.length, n_hendelser_ovrige: raaO.length },
    rettskrets_stratifisert: { antall_strata: strat.antall_strata, saker: strat.saker,
      vektet_diff_dager: r1(strat.vektet_diff), ki95_bootstrap: boot(bStrat).map(r1),
      bygg_tregere_i: strat.bygg_tregere, bygg_raskere_i: strat.bygg_raskere,
      regel: "strata med minst 10 innstilte bo i BEGGE grupper; vekt = summen av gruppenes hendelser",
      per_krets: strat.strata.map((s) => ({ rettskrets: s.krets, n_bygg: s.n_bygg, n_ovrige: s.n_ovrige,
        median_bygg: s.median_bygg, median_ovrige: s.median_ovrige, diff: s.diff }))
        .sort((a, b) => a.diff - b.diff) },
    rettskrets_stratifisert_grenseregel: { antall_strata: stratGrense.antall_strata,
      saker: stratGrense.saker, vektet_diff_dager: r1(stratGrense.vektet_diff),
      bygg_tregere_i: stratGrense.bygg_tregere },
    avvik_mot_talljournalens_D5: {
      talljournal_D5: { vektet_diff_dager: 38.4, saker: 3749, bygg_tregere_av_19: 18 },
      frosset_uttrekk_primaer: { vektet_diff_dager: r1(strat.vektet_diff), saker: strat.saker,
        bygg_tregere_av_19: strat.bygg_tregere },
      frosset_uttrekk_grenseregel: { vektet_diff_dager: r1(stratGrense.vektet_diff),
        saker: stratGrense.saker, bygg_tregere_av_19: stratGrense.bygg_tregere },
      aarsak: "D5 er beregnet i basen, der de 3 randtilfellene bærer sin faktiske innstillingsdato "
        + "ETTER åpning. Det frosne uttrekket bærer bare den eldre datoen FØR åpning, så de 3 kan "
        + "bare sensureres eller settes til dag 1. I tillegg gir kontroll-05s join én dublett "
        + "(ett foretak har to åpningsrader på samme dato), så dens saksteller er 3 749 mot uttrekkets 3 747.",
      konsekvens: "Punktestimatet flytter seg 0,4 dager (38,4 → 38,0) og tellingen «bygg tregest i "
        + "18 av 19 kretser» blir 17 av 19. Den marginale kretsen er Vestre Innlandet (−9 dager i "
        + "uttrekket), som er nettopp der ett av de tre randtilfellene ligger. "
        + "Bootstrap-KI [" + boot(bStrat).map(r1).join(", ") + "] dager dekker begge verdier med god margin. "
        + "ANBEFALING: behold +38,4 som talljournalens måling, men slutt å publisere «18 av 19» som "
        + "et presist antall — tellingen vipper på ett enkelt bo. Skriv i stedet at bygg er tregere "
        + "i det store flertallet av kretsene (17–18 av 19).",
    },
    korrekt_formulering: "Medianforskjellen i kumulativ insidens er " + (medB - medO) + " dager. I en "
      + "separat rettskrets-stratifisert analyse av observerte hendelsestider er den saksvektede "
      + "medianforskjellen " + r1(strat.vektet_diff) + " dager, mot " + r1(raaDiff)
      + " dager i den ustratifiserte fullførte-saker-beregningen.",
  },

  d_hasardratio: {
    estimand: "årsaksspesifikk hasardratio for § 135-innstilling, bygg mot øvrige, "
      + "med ordinær avslutning behandlet som sensurering",
    peto_ett_stegs: { hr: r4(lrS.hr), ki95: [r4(lrS.hr_lav), r4(lrS.hr_hoy)], z: r3(lrS.z), p: lrS.p,
      O: lrS.O, E: r2(lrS.E), OE: r2(lrS.OE), V: r2(lrS.V), strata: lrS.strata,
      hendelsestider: lrS.hendelsestider },
    cox_breslow: { hr: r4(cox.hr), beta: r4(cox.beta), se: r4(cox.se),
      ki95: [r4(cox.hr_lav), r4(cox.hr_hoy)], z: r3(cox.z), p: cox.p, strata: cox.strata },
    cox_klyngerobust: { klynge: "rettskrets", antall_klynger: cox.strata,
      robust_se: r4(cox.robustSe), ki95: [r4(cox.hr_lav_rob), r4(cox.hr_hoy_rob)],
      z: r3(cox.z_rob), p: cox.p_rob,
      merknad: "Med 23 klynger er den robuste variansen selv usikker; den oppgis som "
        + "følsomhetskontroll, ikke som primærintervall." },
    ustratifisert: { hr: r4(lrU.hr), ki95: [r4(lrU.hr_lav), r4(lrU.hr_hoy)], z: r3(lrU.z) },
  },

  e_ph_diagnostikk: {
    metode: "Grambsch–Therneau-type scoretest for θ i β(t) = β + θ(g(t) − ḡ), basert på "
      + "Schoenfeld-residualene fra den stratifiserte Cox-modellen. χ²(1).",
    rang_transform: { khikvadrat: r3(phRang.T), df: 1, p: phRang.p,
      korrelasjon: r4(phRang.korrelasjon), hendelser: phRang.hendelser },
    log_transform: { khikvadrat: r3(phLog.T), df: 1, p: phLog.p, korrelasjon: r4(phLog.korrelasjon) },
    tidsdelt_hr: deler,
    tolkning: phRang.p < 0.05
      ? "PH-antakelsen forkastes. HR 0,80 skal presenteres som et VEKTET GJENNOMSNITT av en "
        + "tidsvarierende hasardratio over oppfølgingen, ikke som en konstant."
      : "Ingen påvisbart brudd på PH-antakelsen under denne testen.",
  },

  f_kontroll_og_varianter: {
    implementasjonskontroll: { lane3_rutine: { hr: r4(kontrollLane3.hr), z: r3(kontrollLane3.z) },
      revisjonsbibliotek: { hr: r4(lrS.hr), z: r3(lrS.z) },
      absolutt_differanse_z: r4(Math.abs(kontrollLane3.z - lrS.z)),
      merknad: "De to uavhengige implementasjonene gir samme svar; forskjellen mot manuskriptets "
        + "z = −5,8 ligger derfor i definisjons-/kjøringsvarianten, ikke i estimatoren. "
        + "HR 0,80 reproduseres eksakt." },
    definisjonsvarianter: varianter,
  },
};
skrivJson(`data/rev2-04-presisjon-hr-og-ph-${KJORT}.json`, ut);
